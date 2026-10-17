"""Cotejo determinista de tres vías: orden de compra, remisión y CFDI.

Regla base: se paga lo recibido, al precio pactado, nunca más de lo ordenado.
Los impuestos se toman de cada concepto del CFDI (IVA 16 %, 8 % frontera, 0 %, exento, IEPS, retenciones).
"""
from decimal import Decimal, ROUND_HALF_UP

TOL_PRECIO_PCT = Decimal("0.02")
TOL_PRECIO_MXN = Decimal("1")
TOL_REDONDEO = Decimal("1")        # diferencia aceptada en totales
TOL_IMPUESTO = Decimal("0.02")     # diferencia aceptada entre Base × Tasa e Importe de un traslado
TASAS_IVA_VALIDAS = {Decimal("0"), Decimal("0.08"), Decimal("0.16")}
IVA = "002"
CENT = Decimal("0.01")
CERO = Decimal("0")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _tasa_neta(concepto: dict) -> Decimal:
    """Tasa total de impuestos del concepto: traslados menos retenciones (los exentos no suman)."""
    traslados = sum((t["tasa"] for t in concepto["traslados"]
                     if t["tipo_factor"] == "Tasa"), CERO)
    retenciones = sum((r["tasa"] for r in concepto["retenciones"]
                       if r["tipo_factor"] == "Tasa"), CERO)
    return traslados - retenciones


def _revisar_impuestos(sku: str, c: dict, linea_oc: dict) -> list[dict]:
    """Problemas de impuestos del concepto: importe mal calculado, tasa inválida o distinta a la pactada."""
    problemas = []
    for t in c["traslados"] + c["retenciones"]:
        if t["tipo_factor"] != "Tasa":
            continue
        esperado = _q(t["base"] * t["tasa"])
        if abs(esperado - t["importe"]) > TOL_IMPUESTO:
            problemas.append({"sku": sku, "problema": "Importe de impuesto mal calculado",
                              "impuesto": t["impuesto"], "base": str(t["base"]), "tasa": str(t["tasa"]),
                              "importe_cfdi": str(t["importe"]), "esperado": str(esperado)})
    tasas_iva = [t["tasa"] for t in c["traslados"] if t["impuesto"] == IVA and t["tipo_factor"] == "Tasa"]
    for tasa in tasas_iva:
        if tasa not in TASAS_IVA_VALIDAS:
            problemas.append({"sku": sku, "problema": "Tasa de IVA no válida", "tasa": str(tasa)})
    if "tasa_iva" in linea_oc:
        pactada = Decimal(str(linea_oc["tasa_iva"]))
        facturada = tasas_iva[0] if tasas_iva else CERO
        if facturada != pactada:
            problemas.append({"sku": sku, "problema": "Tasa de IVA distinta a la de la OC",
                              "tasa_oc": str(pactada), "tasa_cfdi": str(facturada)})
    return problemas


def _total_segun_conceptos(cfdi: dict) -> Decimal:
    """Total que debería tener el CFDI sumando sus propios conceptos e impuestos."""
    total = CERO
    for c in cfdi["conceptos"]:
        total += c["importe"] - c["descuento"]
        total += sum((t["importe"] for t in c["traslados"]), CERO)
        total -= sum((r["importe"] for r in c["retenciones"]), CERO)
    return _q(total)


def cotejar(oc: dict, remision: dict, cfdi: dict) -> dict:
    """Devuelve discrepancias, monto a pagar y fuga, todo en MXN con Decimal."""
    ordenado = {l["sku"]: l for l in oc["lineas"]}
    recibido = {l["sku"]: Decimal(str(l["cantidad_recibida"])) for l in remision["lineas"]}
    codigos, detalle = set(), []
    monto_pagar = CERO

    for c in cfdi["conceptos"]:
        sku = c["sku"]
        if sku not in ordenado:
            codigos.add("SKU_UNMAPPED")
            detalle.append({"sku": sku, "problema": "Concepto facturado que no está en la OC",
                            "importe": str(c["importe"])})
            continue
        l = ordenado[sku]
        q_oc, p_oc = Decimal(str(l["cantidad"])), Decimal(str(l["precio_unitario"]))
        q_rec = recibido.get(sku, CERO)
        q_fac, p_fac = c["cantidad"], c["valor_unitario"]

        tol_p = min(p_oc * TOL_PRECIO_PCT, TOL_PRECIO_MXN)
        precio_alto = p_fac - p_oc > tol_p
        # Dentro de tolerancia se paga lo facturado; fuera, el precio pactado.
        p_pagar = p_oc if precio_alto else p_fac
        q_pagar = min(q_fac, q_rec, q_oc)

        if q_fac > q_rec:
            codigos.add("QTY_SHORT")
            detalle.append({"sku": sku, "problema": "Se facturó más de lo recibido",
                            "facturada": str(q_fac), "recibida": str(q_rec)})
        if q_fac > q_oc or q_rec > q_oc:
            codigos.add("QTY_OVER_PO")
            detalle.append({"sku": sku, "problema": "Cantidad mayor a lo ordenado",
                            "ordenada": str(q_oc), "facturada": str(q_fac), "recibida": str(q_rec)})
        if precio_alto:
            codigos.add("PRICE_UP")
            detalle.append({"sku": sku, "problema": "Precio unitario mayor al pactado",
                            "precio_oc": str(p_oc), "precio_facturado": str(p_fac)})
        problemas_imp = _revisar_impuestos(sku, c, l)
        if problemas_imp:
            codigos.add("TAX_MISMATCH")
            detalle.extend(problemas_imp)

        # El descuento del concepto se reparte por unidad facturada.
        desc_unit = c["descuento"] / q_fac if q_fac else CERO
        base_pagar = q_pagar * (p_pagar - desc_unit)
        monto_pagar += _q(base_pagar * (1 + _tasa_neta(c)))

    monto_pagar = _q(monto_pagar)
    total_interno = _total_segun_conceptos(cfdi)
    if abs(total_interno - cfdi["total"]) > TOL_REDONDEO:
        codigos.add("TAX_MISMATCH")
        detalle.append({"problema": "El total del CFDI no cuadra con sus conceptos e impuestos",
                        "total_cfdi": str(cfdi["total"]), "suma_conceptos": str(total_interno)})

    fuga = _q(cfdi["total"] - monto_pagar)
    if not codigos:
        if abs(fuga) > TOL_REDONDEO:   # salvaguarda: no debería ocurrir sin otra causa
            codigos.add("TAX_MISMATCH")
            detalle.append({"problema": "Diferencia sin causa identificada",
                            "total_cfdi": str(cfdi["total"]), "calculado": str(monto_pagar)})
        else:
            codigos.add("MATCH_OK")
            fuga = Decimal("0.00")
    return {"codigos": sorted(codigos), "total_cfdi_mxn": str(cfdi["total"]),
            "monto_a_pagar_mxn": str(monto_pagar),
            "fuga_detectada_mxn": str(max(fuga, Decimal("0.00"))),
            "detalle": detalle}
