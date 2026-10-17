"""Casos de borde del motor: tolerancia de precio, tasas de IVA, retenciones y descuentos."""
from decimal import Decimal as D

from src.matching import cotejar

REM = {"lineas": [{"sku": "A", "cantidad_recibida": 100}]}


def oc(precio="80.00", **extra):
    return {"lineas": [{"sku": "A", "cantidad": 100, "precio_unitario": precio, **extra}]}


def cfdi(precio, tasa, *, importe_iva=None, retencion=None, descuento="0", total=None):
    imp = D("100") * D(precio)
    desc = D(descuento)
    base = imp - desc
    traslados = []
    if tasa == "exento":
        traslados = [{"impuesto": "002", "tipo_factor": "Exento", "tasa": D("0"), "base": base, "importe": D("0")}]
    else:
        iva = D(importe_iva) if importe_iva else (base * D(tasa)).quantize(D("0.01"))
        traslados = [{"impuesto": "002", "tipo_factor": "Tasa", "tasa": D(tasa), "base": base, "importe": iva}]
    retenciones = []
    if retencion:
        retenciones = [{"impuesto": "002", "tipo_factor": "Tasa", "tasa": D(retencion), "base": base,
                        "importe": (base * D(retencion)).quantize(D("0.01"))}]
    calc = base + sum(t["importe"] for t in traslados) - sum(r["importe"] for r in retenciones)
    return {"total": D(total) if total else calc, "conceptos": [{
        "sku": "A", "cantidad": D("100"), "valor_unitario": D(precio), "importe": imp, "descuento": desc,
        "traslados": traslados, "retenciones": retenciones}]}


def test_precio_dentro_de_tolerancia_es_match_ok():
    r = cotejar(oc(), REM, cfdi("80.50", "0.16"))   # tolerancia = min(2 %, $1) = $1
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["monto_a_pagar_mxn"]) == D("9338.00")


def test_precio_fuera_de_tolerancia_es_price_up():
    r = cotejar(oc(), REM, cfdi("81.50", "0.16"))
    assert r["codigos"] == ["PRICE_UP"]
    assert D(r["fuga_detectada_mxn"]) == D("174.00")   # 100 × 1.50 × 1.16


def test_iva_cero():
    r = cotejar(oc(), REM, cfdi("80.00", "0"))
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["monto_a_pagar_mxn"]) == D("8000.00")


def test_iva_frontera_ocho():
    r = cotejar(oc(), REM, cfdi("80.00", "0.08"))
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["monto_a_pagar_mxn"]) == D("8640.00")


def test_exento():
    r = cotejar(oc(), REM, cfdi("80.00", "exento"))
    assert r["codigos"] == ["MATCH_OK"]


def test_retencion_de_iva():
    r = cotejar(oc(), REM, cfdi("80.00", "0.16", retencion="0.106667"))
    assert r["codigos"] == ["MATCH_OK"]


def test_descuento_en_concepto():
    r = cotejar(oc(), REM, cfdi("80.00", "0.16", descuento="400"))
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["monto_a_pagar_mxn"]) == D("8816.00")   # (8000 - 400) × 1.16


def test_importe_de_iva_mal_calculado():
    r = cotejar(oc(), REM, cfdi("80.00", "0.16", importe_iva="1500.00"))
    assert "TAX_MISMATCH" in r["codigos"]


def test_tasa_iva_invalida():
    r = cotejar(oc(), REM, cfdi("80.00", "0.15"))
    assert "TAX_MISMATCH" in r["codigos"]


def test_tasa_distinta_a_la_oc():
    r = cotejar(oc(tasa_iva="0.16"), REM, cfdi("80.00", "0.08"))
    assert r["codigos"] == ["TAX_MISMATCH"]


def test_total_no_cuadra_con_conceptos():
    r = cotejar(oc(), REM, cfdi("80.00", "0.16", total="9500.00"))
    assert "TAX_MISMATCH" in r["codigos"]
