"""Cotejo determinista de tres vías: orden de compra, remisión y CFDI.

Regla base: se paga lo recibido, al precio pactado, nunca más de lo ordenado.
"""
from decimal import Decimal, ROUND_HALF_UP

IVA = Decimal("0.16")
TOL_PRECIO_PCT = Decimal("0.02")
TOL_PRECIO_MXN = Decimal("1")
TOL_REDONDEO = Decimal("1")
CENT = Decimal("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def cotejar(oc: dict, remision: dict, cfdi: dict) -> dict:
    """Devuelve discrepancias, monto a pagar y fuga, todo en MXN con Decimal."""
    ordenado = {l["sku"]: l for l in oc["lineas"]}
    recibido = {l["sku"]: Decimal(str(l["cantidad_recibida"])) for l in remision["lineas"]}
    codigos, detalle = set(), []
    subtotal_pagar = Decimal("0")

    for c in cfdi["conceptos"]:
        sku = c["sku"]
        if sku not in ordenado:
            codigos.add("SKU_UNMAPPED")
            detalle.append({"sku": sku, "problema": "Concepto facturado que no está en la OC",
                            "importe": str(c["importe"])})
            continue
        l = ordenado[sku]
        q_oc, p_oc = Decimal(str(l["cantidad"])), Decimal(str(l["precio_unitario"]))
        q_rec = recibido.get(sku, Decimal("0"))
        q_fac, p_fac = c["cantidad"], c["valor_unitario"]

        tol_p = min(p_oc * TOL_PRECIO_PCT, TOL_PRECIO_MXN)
        precio_alto = p_fac - p_oc > tol_p
        p_pagar = p_oc if precio_alto else min(p_fac, p_oc)
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
        subtotal_pagar += q_pagar * p_pagar

    monto_pagar = _q(subtotal_pagar * (1 + IVA))
    fuga = _q(cfdi["total"] - monto_pagar)
    if not codigos and abs(fuga) > TOL_REDONDEO:
        codigos.add("TAX_MISMATCH")
        detalle.append({"problema": "El total no cuadra con lo calculado sin otra causa",
                        "total_cfdi": str(cfdi["total"]), "calculado": str(monto_pagar)})
    if not codigos:
        codigos.add("MATCH_OK")
        fuga = Decimal("0.00")
    return {"codigos": sorted(codigos), "total_cfdi_mxn": str(cfdi["total"]),
            "monto_a_pagar_mxn": str(monto_pagar),
            "fuga_detectada_mxn": str(max(fuga, Decimal("0.00"))),
            "detalle": detalle}
