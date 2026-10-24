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


def test_upload_remision_case():
    # Usar la imagen de OC-004 para subirla y restaurar archivos originales al finalizar
    img_path = DATASETS / "OC-004" / "remision.png"
    json_path = DATASETS / "OC-004" / "remision.json"
    img_real = img_path.read_bytes()
    json_real = json_path.read_text(encoding="utf-8")
    try:
        files = {
            "file": ("remision_nueva.png", io.BytesIO(img_real), "image/png"),
        }
        response = client.post("/api/cases/OC-004/upload-remision", files=files)
        assert response.status_code == 200
        res = response.json()
        assert res["ok"] is True
        assert res["case_id"] == "OC-004"
        assert "nitidez" in res
        assert res["es_nitida"] is True
        assert "estado_final" in res
    finally:
        img_path.write_bytes(img_real)
        json_path.write_text(json_real, encoding="utf-8")
