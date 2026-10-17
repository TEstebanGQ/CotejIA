"""SKU repetido en varias líneas de la factura, la remisión o la OC."""
from decimal import Decimal as D

import pytest

from src.matching import cotejar


def concepto(q, precio="80"):
    imp = D(q) * D(precio)
    return {"sku": "A", "cantidad": D(q), "valor_unitario": D(precio), "importe": imp, "descuento": D("0"),
            "traslados": [{"impuesto": "002", "tipo_factor": "Tasa", "tasa": D("0.16"), "base": imp,
                           "importe": (imp * D("0.16")).quantize(D("0.01"))}],
            "retenciones": []}


def factura(*cantidades):
    conceptos = [concepto(q) for q in cantidades]
    total = sum(c["importe"] + c["traslados"][0]["importe"] for c in conceptos)
    return {"conceptos": conceptos, "total": total}


OC = {"lineas": [{"sku": "A", "cantidad": 100, "precio_unitario": "80"}]}


def remision(*cantidades):
    return {"lineas": [{"sku": "A", "cantidad_recibida": q} for q in cantidades]}


def test_mismo_sku_facturado_dos_veces_no_se_paga_doble():
    r = cotejar(OC, remision(100), factura("100", "100"))
    assert "QTY_SHORT" in r["codigos"] and "QTY_OVER_PO" in r["codigos"]
    assert D(r["monto_a_pagar_mxn"]) == D("9280.00")      # solo las 100 recibidas
    assert D(r["fuga_detectada_mxn"]) == D("9280.00")


def test_mismo_sku_en_dos_lineas_que_suman_lo_recibido():
    r = cotejar(OC, remision(100), factura("60", "40"))
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["monto_a_pagar_mxn"]) == D("9280.00")


def test_remision_con_sku_partido_en_dos_lineas():
    r = cotejar(OC, remision(50, 50), factura("100"))
    assert r["codigos"] == ["MATCH_OK"]
    assert D(r["fuga_detectada_mxn"]) == 0


def test_oc_con_sku_repetido_mismo_precio_se_suma():
    oc = {"lineas": [{"sku": "A", "cantidad": 60, "precio_unitario": "80"},
                     {"sku": "A", "cantidad": 40, "precio_unitario": "80"}]}
    r = cotejar(oc, remision(100), factura("100"))
    assert r["codigos"] == ["MATCH_OK"]


def test_oc_con_sku_repetido_a_dos_precios_es_error():
    oc = {"lineas": [{"sku": "A", "cantidad": 60, "precio_unitario": "80"},
                     {"sku": "A", "cantidad": 40, "precio_unitario": "70"}]}
    with pytest.raises(ValueError):
        cotejar(oc, remision(100), factura("100"))
