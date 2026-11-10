"""Entrada para evaluadores externos: CLI `audit --dir` y endpoint `POST /api/v1/auditar`."""
import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import agent, harness

ROOT = Path(__file__).resolve().parent.parent
S4 = ROOT / "datasets" / "s4"
S3 = ROOT / "datasets" / "s3"


@pytest.fixture(autouse=True)
def bd_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "harness_test.db"))
    monkeypatch.setenv("RETO_KEY", "")


def _caso_s3(case_id: str, destino: Path) -> Path:
    shutil.copytree(S3 / case_id, destino / case_id)
    return destino / case_id


def test_descubre_un_caso_o_una_carpeta_de_casos(tmp_path):
    _caso_s3("S3-001", tmp_path)
    _caso_s3("S3-002", tmp_path)
    assert harness.descubrir_casos(tmp_path) == (tmp_path.resolve(), ["S3-001", "S3-002"])
    assert harness.descubrir_casos(tmp_path / "S3-001") == (tmp_path.resolve(), ["S3-001"])
    with pytest.raises(FileNotFoundError):
        harness.descubrir_casos(tmp_path / "no-existe")


def test_dataset_s3_completo_coincide_en_modo_determinista(tmp_path):
    base, ids = harness.descubrir_casos(S3)
    fallos = []
    for cid in ids:
        r = harness.auditar_caso(base, cid, modo="determinista")
        cmp = harness.comparar_con_esperado(base / cid, r)
        if not all(cmp.values()):
            fallos.append((cid, r["codigos"]))
    assert fallos == []


def test_la_carpeta_del_harness_no_contamina_el_dashboard(tmp_path):
    _caso_s3("S3-001", tmp_path)
    antes = agent.DATASETS
    harness.auditar_caso(tmp_path, "S3-001", modo="determinista")
    assert agent.DATASETS == antes


@pytest.mark.skipif(not S4.exists(), reason="datasets/s4 se genera con datasets/generate.py --s4")
def test_cfdi_cancelado_se_escala_y_no_se_paga(tmp_path):
    shutil.copytree(S4 / "S4-0015", tmp_path / "S4-0015")
    r = harness.auditar_caso(tmp_path, "S4-0015", modo="determinista")
    assert r["estado_final"] == "ESCALADO"
    assert r["codigos"] == ["CFDI_CANCELADO"]
    assert r["monto_a_pagar_mxn"] == "0.00"


def test_acuse_sat_cancelado_bloquea_un_caso_limpio(tmp_path):
    d = _caso_s3("S3-001", tmp_path)
    assert harness.auditar_caso(tmp_path, d.name, modo="determinista")["estado_final"] == "APROBADO"
    uuid = agent.leer_cfdi(str(d / "cfdi.xml"))["uuid"]
    (d / "sat_estatus.json").write_text(json.dumps({"uuid": uuid, "estado": "Cancelado"}), encoding="utf-8")
    r = harness.auditar_caso(tmp_path, d.name, modo="determinista")
    assert (r["estado_final"], r["codigos"], r["monto_a_pagar_mxn"]) == ("ESCALADO", ["CFDI_CANCELADO"], "0.00")


def test_remision_sin_firma_no_se_aprueba(tmp_path):
    d = _caso_s3("S3-035", tmp_path)
    r = harness.auditar_caso(tmp_path, d.name, modo="determinista")
    assert r["estado_final"] == "ESCALADO"
    assert "RECEIPT_UNREADABLE" in r["codigos"]


def test_caso_solo_con_pdf_de_remision(tmp_path):
    d = _caso_s3("S3-001", tmp_path)
    assert (d / "remision.pdf").exists()
    (d / "remision.json").unlink()
    r = harness.auditar_caso(tmp_path, d.name, modo="determinista")
    assert r["error"] is None
    assert r["estado_final"] == json.loads((d / "esperado.json").read_text(encoding="utf-8"))["estado_final"]


def test_expediente_roto_escala_con_system_error_en_vez_de_lanzar(tmp_path):
    d = _caso_s3("S3-001", tmp_path)
    (d / "cfdi.xml").write_text("<esto no es un cfdi", encoding="utf-8")
    r = harness.auditar_caso(tmp_path, d.name, modo="determinista")
    assert r["estado_final"] == "ESCALADO"
    assert r["codigos"] == ["SYSTEM_ERROR"]
    assert r["error"]


def test_cli_audit_dir_emite_un_json_por_caso(tmp_path):
    _caso_s3("S3-001", tmp_path)
    _caso_s3("S3-005", tmp_path)
    out = tmp_path / "res.jsonl"
    p = subprocess.run(
        [sys.executable, "main.py", "audit", "--dir", str(tmp_path), "--modo", "determinista", "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    assert p.returncode == 0, p.stderr
    lineas = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
    assert [l["case_id"] for l in lineas] == ["S3-001", "S3-005"]
    assert all(l["comparacion_esperado"]["estado"] for l in lineas)
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def _payload(case_id: str) -> dict:
    d = S3 / case_id
    p = {
        "case_id": case_id,
        "oc": json.loads((d / "oc.json").read_text(encoding="utf-8")),
        "cfdi_xml": (d / "cfdi.xml").read_text(encoding="utf-8"),
        "remision": json.loads((d / "remision.json").read_text(encoding="utf-8")),
        "modo": "determinista",
    }
    if (d / "remision.pdf").exists():
        p["remision_pdf_base64"] = base64.b64encode((d / "remision.pdf").read_bytes()).decode()
    return p


def test_endpoint_v1_auditar():
    from src.api import app

    client = TestClient(app)
    res = client.post("/api/v1/auditar", json=_payload("S3-005"))
    assert res.status_code == 200, res.text
    body = res.json()
    esperado = json.loads((S3 / "S3-005" / "esperado.json").read_text(encoding="utf-8"))
    assert body["estado_final"] == esperado["estado_final"]
    assert sorted(body["codigos"]) == sorted(esperado["codigos"])
    assert body["case_id"] == "S3-005"


def test_endpoint_v1_valida_entrada():
    from src.api import app

    client = TestClient(app)
    malo = _payload("S3-001")
    malo["case_id"] = "../../etc"
    assert client.post("/api/v1/auditar", json=malo).status_code == 422
    sin_remision = _payload("S3-001")
    sin_remision.pop("remision")
    sin_remision.pop("remision_pdf_base64", None)
    assert client.post("/api/v1/auditar", json=sin_remision).status_code == 422


def test_endpoint_v1_lote():
    from src.api import app

    client = TestClient(app)
    res = client.post("/api/v1/auditar-lote", json={"casos": [_payload("S3-001"), _payload("S3-002")]})
    assert res.status_code == 200
    assert res.json()["total"] == 2
