"""Verificación de que FastAPI sirve correctamente el frontend web estático."""
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_serve_index_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "CotejAI" in res.text
    assert "Three-Way Matching" in res.text
    assert "modal-upload" in res.text


def test_serve_static_app_js():
    res = client.get("/static/app.js")
    assert res.status_code == 200
    assert "inicializarApp" in res.text
    assert "enviarCargaManual" in res.text
