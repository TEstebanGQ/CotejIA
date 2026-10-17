from decimal import Decimal

from src.agent import tool_cotejar_caso


def test_caso_limpio():
    r = tool_cotejar_caso("OC-001")
    assert r["codigos"] == ["MATCH_OK"]
    assert Decimal(r["fuga_detectada_mxn"]) == 0
    assert Decimal(r["monto_a_pagar_mxn"]) == Decimal("6090.00")


def test_faltante():
    r = tool_cotejar_caso("OC-002")
    assert r["codigos"] == ["QTY_SHORT"]
    assert Decimal(r["monto_a_pagar_mxn"]) == Decimal("5800.00")
    assert Decimal(r["fuga_detectada_mxn"]) == Decimal("290.00")


def test_alza_de_precio():
    r = tool_cotejar_caso("OC-003")
    assert r["codigos"] == ["PRICE_UP"]
    assert Decimal(r["monto_a_pagar_mxn"]) == Decimal("6090.00")
    assert Decimal(r["fuga_detectada_mxn"]) == Decimal("464.00")
