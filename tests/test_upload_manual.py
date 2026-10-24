"""Prueba automatizada de carga manual de expedientes en FastAPI."""
import io
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from src.api import app, DATASETS

client = TestClient(app)


def test_upload_manual_cfdi_y_cotejo():
    # Usar el XML de OC-001 como archivo de prueba
    xml_real = (DATASETS / "OC-001" / "cfdi.xml").read_bytes()
    
    files = {
        "cfdi_file": ("factura_test.xml", io.BytesIO(xml_real), "text/xml"),
    }
    data = {
        "proveedor_nombre": "Proveedor Manual Test S.A. de C.V.",
        "notas": "Prueba de carga manual desde test automatizado",
    }
    
    response = client.post("/api/cases/upload-manual", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    try:
        assert res["ok"] is True
        assert "OC-MANUAL-" in res["case_id"]
        assert res["veredicto"]["estado_final"] in ["APROBADO", "EN_RECLAMO", "ESCALADO"]
        assert "fuga_detectada_mxn" in res["veredicto"]
        assert (DATASETS / res["case_id"] / "cfdi.xml").exists()
        assert (DATASETS / res["case_id"] / "remision.json").exists()
        assert (DATASETS / res["case_id"] / "oc.json").exists()
    finally:
        # Limpieza para no ensuciar datasets permanentes
        shutil.rmtree(DATASETS / res["case_id"], ignore_errors=True)
