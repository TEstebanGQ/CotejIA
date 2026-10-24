"""Pruebas automatizadas de las herramientas reales S2, Persistencia BD y FastAPI."""
from fastapi.testclient import TestClient

from src.agent import tool_cotejar_caso
from src.api import app
from src.db import buscar_rfc_69b, init_db
from src.external_tools import (
    CIRCUIT_BREAKER_SAT,
    consultar_sat_en_vivo,
    consultar_tipo_cambio_real,
    enviar_alerta_reclamo_real,
)
from src.vision import leer_remision_imagen


def test_herramienta_vision_nitida_vs_borrosa(monkeypatch):
    # Probamos en modo determinista/óptico sin depender de cuota de red
    monkeypatch.setenv("RETO_KEY", "pk_xxx_test")
    r_nitida = leer_remision_imagen("OC-004")
    assert r_nitida["ok"] is True
    assert r_nitida["legible"] is True
    assert r_nitida["codigo_alerta"] is None
    assert r_nitida["remision_extraida"]["tiene_sello_almacen"] is True

    r_borrosa = leer_remision_imagen("OC-005")
    assert r_borrosa["ok"] is True
    assert r_borrosa["legible"] is False
    assert r_borrosa["codigo_alerta"] == "RECEIPT_UNREADABLE"


def test_herramienta_tipo_cambio_detecta_sobreprecio():
    r = consultar_tipo_cambio_real(moneda="USD", tipo_cambio_cfdi="25.00")
    assert r["ok"] is True
    assert r["moneda"] == "USD"
    assert r["codigo_alerta"] == "FX_OVERCHARGE"


def test_herramienta_sat_69b_real_y_circuit_breaker(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test_cotejai.db"))
    init_db()
    # Verificar que el RFC real del listado 69-B está cargado en la base de datos
    efos = buscar_rfc_69b("AAA080808AAA")
    assert efos is not None
    assert efos["situacion"] == "Definitivo"

    # Reiniciar estado del circuit breaker antes de probar
    CIRCUIT_BREAKER_SAT.registrar_exito()
    res_caida = consultar_sat_en_vivo(
        case_id="OC-010",
        uuid="00000010-0000-4000-8000-000000000000",
        rfc_emisor="AAA010101AAA",
        rfc_receptor="BBB020202BBB",
        total="15080.00",
        simular_caida_sat=True,
    )
    assert "SAT_NO_VERIFICADO" in res_caida["codigos_fiscales"]
    assert CIRCUIT_BREAKER_SAT.esta_abierto is True
    CIRCUIT_BREAKER_SAT.registrar_exito()


def test_idempotencia_y_limite_politica_reclamo(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test_idemp.db"))
    # Primera llamada: envía y registra en BD
    r1 = enviar_alerta_reclamo_real(
        case_id="OC-002",
        rfc_proveedor="AAA010101AAA",
        uuid_factura="00000002-0000-4000-8000-000000000000",
        monto_nota_credito_mxn="290.00",
        motivo="Faltante de 20 piezas TORN-001",
    )
    assert r1["ok"] is True
    assert r1["idempotencia_bloqueada"] is False

    # Segunda llamada con el mismo caso/llave: bloquea duplicado
    r2 = enviar_alerta_reclamo_real(
        case_id="OC-002",
        rfc_proveedor="AAA010101AAA",
        uuid_factura="00000002-0000-4000-8000-000000000000",
        monto_nota_credito_mxn="290.00",
        motivo="Reintento duplicado",
    )
    assert r2["ok"] is True
    assert r2["idempotencia_bloqueada"] is True

    # Monto mayor a $5,000 MXN: rechazado por compuerta policy_gate
    r_exceso = enviar_alerta_reclamo_real(
        case_id="OC-010",
        rfc_proveedor="AAA010101AAA",
        uuid_factura="00000010-0000-4000-8000-000000000000",
        monto_nota_credito_mxn="9280.00",
        motivo="Faltante mayor al límite autónomo",
    )
    assert r_exceso["ok"] is False
    assert r_exceso["rechazado_por_politica"] is True


def test_cotejo_10_casos_s2(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test_lote.db"))
    CIRCUIT_BREAKER_SAT.registrar_exito()
    assert tool_cotejar_caso("OC-001")["codigos"] == ["MATCH_OK"]
    assert tool_cotejar_caso("OC-002")["codigos"] == ["QTY_SHORT"]
    assert tool_cotejar_caso("OC-003")["codigos"] == ["PRICE_UP"]
    assert tool_cotejar_caso("OC-004")["codigos"] == ["QTY_SHORT"]
    assert "RECEIPT_UNREADABLE" in tool_cotejar_caso("OC-005")["codigos"]
    assert "FX_OVERCHARGE" in tool_cotejar_caso("OC-006")["codigos"]
    assert "SUPPLIER_69B" in tool_cotejar_caso("OC-007")["codigos"]
    assert "TAX_MISMATCH" in tool_cotejar_caso("OC-008")["codigos"]
    assert "DUPLICATE" in tool_cotejar_caso("OC-009")["codigos"]
    c10 = tool_cotejar_caso("OC-010")
    assert "QTY_SHORT" in c10["codigos"] and "SAT_NO_VERIFICADO" in c10["codigos"]
    CIRCUIT_BREAKER_SAT.registrar_exito()


def test_endpoints_fastapi(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test_api.db"))
    client = TestClient(app)

    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["ok"] is True

    lista = client.get("/api/cases")
    assert lista.status_code == 200
    assert lista.json()["total"] == 10

    det = client.get("/api/cases/OC-004")
    assert det.status_code == 200
    assert det.json()["tiene_imagen_remision"] is True

    img = client.get("/api/cases/OC-004/image")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
