"""S3: dataset de 36 casos, evaluador y extracción por niveles (Nivel 1 local)."""
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "datasets"))
import generate  # noqa: E402
from eval import evaluar  # noqa: E402
from src import agent  # noqa: E402
from src.extraccion import extraer_pdf, extraer_remision_local  # noqa: E402

S3 = ROOT / "datasets" / "s3"
COMPOSICION = {"MATCH_OK": 10, "QTY_SHORT": 6, "PRICE_UP": 5, "UNAGREED_CHARGE": 4, "DUPLICATE": 3,
               "TAX_MISMATCH": 3, "SUPPLIER_69B": 2, "RECEIPT_UNREADABLE": 1, "RECEIPT_UNSIGNED": 1,
               "RECEIPT_HANDWRITTEN": 1}


def _hashes(carpeta: Path) -> dict[str, bytes]:
    return {str(p.relative_to(carpeta)): p.read_bytes() for p in sorted(carpeta.rglob("*")) if p.is_file()}


def test_generador_reproducible_con_semilla(tmp_path):
    generate.generar_s3(7, tmp_path / "a")
    generate.generar_s3(7, tmp_path / "b")
    generate.generar_s3(8, tmp_path / "c")
    assert _hashes(tmp_path / "a") == _hashes(tmp_path / "b")
    assert _hashes(tmp_path / "a") != _hashes(tmp_path / "c")


def test_dataset_versionado_coincide_con_semilla_por_defecto(tmp_path):
    generate.generar_s3(generate.SEMILLA_DEFAULT, tmp_path)
    assert _hashes(tmp_path) == _hashes(S3)


def test_composicion_y_ground_truth():
    esperados = evaluar.cargar_esperados(S3)
    assert len(esperados) == 36
    assert Counter(e["tipo_caso"] for e in esperados.values()) == COMPOSICION
    for e in esperados.values():
        for campo in ("monto_a_pagar_mxn", "fuga_detectada_mxn", "total_cfdi_mxn"):
            if e[campo] is not None:
                assert Decimal(e[campo]) == Decimal(e[campo]).quantize(Decimal("0.01"))
    assert any(e["estado_final"] == "ESCALADO" and e["codigos"] == ["QTY_SHORT"] for e in esperados.values())


def test_catalogo_40_skus_con_iva_variado():
    import random
    cat = generate.construir_catalogo(random.Random(1))
    assert len({s["sku"] for s in cat}) == 40
    assert {None, Decimal("0"), Decimal("0.08"), Decimal("0.16")} <= {s["tasa"] for s in cat}
    assert {s["unidad"] for s in cat} == {"pza", "kg", "caja", "litro"}


def test_evaluador_local_cumple_metas():
    esperados = evaluar.cargar_esperados(S3)
    res = evaluar.correr_set(S3, esperados, "local")
    m = evaluar.calcular_metricas(res, esperados)
    assert m["aprobaciones_indebidas"] == 0
    assert m["exactitud_importes"] > 95 and m["exactitud_codigos"] > 90
    assert evaluar.listar_fallos(res, esperados) == []
    assert m["extraccion_por_nivel_pct"]["nivel_1"] > 85
    assert m["roi_veces"] is None   # sin costo de inferencia el ROI no está definido


def test_evaluador_no_contamina_estado_global():
    previo = agent.DATASETS
    evaluar.correr_set(S3, evaluar.cargar_esperados(S3), "local")
    assert agent.DATASETS == previo


def test_evaluador_detecta_aprobaciones_indebidas_y_calcula_roi():
    esperados = evaluar.cargar_esperados(S3)
    res = [{"case_id": c, "tipo_caso": e["tipo_caso"], "nivel": 1, "tokens": 100, "costo_usd": Decimal("0.01"),
            "remision_usada": e["remision"]["lineas"],
            "obtenido": {"estado_final": "APROBADO", "codigos": ["MATCH_OK"],
                         "monto_a_pagar_mxn": e["total_cfdi_mxn"], "fuga_detectada_mxn": "0.00"}}
           for c, e in esperados.items()]
    m = evaluar.calcular_metricas(res, esperados)
    assert m["aprobaciones_indebidas"] == 100.0
    assert Decimal(m["fuga_aprobada_por_error_mxn"]) == Decimal(m["fuga_real_mxn"]) > 0
    assert m["fuga_retenida_mxn"] == "0"

    bien = [{**r, "obtenido": {"estado_final": "ESCALADO", "codigos": esperados[r["case_id"]]["codigos"],
                               "monto_a_pagar_mxn": esperados[r["case_id"]]["monto_a_pagar_mxn"],
                               "fuga_detectada_mxn": esperados[r["case_id"]]["fuga_detectada_mxn"]}} for r in res]
    m2 = evaluar.calcular_metricas(bien, esperados)
    assert Decimal(m2["fuga_retenida_mxn"]) == Decimal(m2["fuga_real_mxn"])
    costo_mxn = Decimal("0.36") * evaluar.MXN_POR_USD
    assert Decimal(m2["roi_veces"]) == (Decimal(m2["fuga_retenida_mxn"]) / costo_mxn).quantize(Decimal("0.1"))


def test_resumen_de_corridas_promedio_y_desviacion():
    r = evaluar.resumir_corridas([{"x": 90.0}, {"x": 100.0}])
    assert r["x"] == {"promedio": 95.0, "desv": 5.0}


# ── Extracción por niveles ──────────────────────────────────────────────────────────────────────
def test_nivel1_resuelve_pdf_limpio_sin_red(monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("Nivel 1 no debe usar la red"))
    esp = json.loads((S3 / "S3-001" / "esperado.json").read_text())
    r = extraer_remision_local(S3 / "S3-001")
    assert r["nivel"] == 1 and r["resuelto"] and r["metodo"] == "pdfplumber"
    assert [(l["sku"], l["cantidad_recibida"]) for l in r["lineas"]] == \
           [(l["sku"], l["cantidad_recibida"]) for l in esp["remision"]["lineas"]]


def test_nivel1_no_toma_fotos_y_escala_a_nivel2(tmp_path):
    assert extraer_remision_local(S3 / "S3-036") is None   # foto: sin PDF, lo atiende la visión
    with evaluar.entorno_aislado(S3, "local", str(tmp_path / "t.db")) as ag:
        assert ag.tool_cotejar_caso("S3-036")["extraccion_nivel"] == 2
        assert ag.tool_cotejar_caso("S3-001")["extraccion_nivel"] == 1


def test_nivel1_pdf_tachado_o_ilegible_pasa_a_nivel2(tmp_path):
    base = [(50, 60, "F1", 10, "TORN-001"), (135, 60, "F1", 10, "Tornillo"), (385, 60, "F1", 10, "pza"),
            (455, 60, "F1", 10, "100")]
    generate.escribir_pdf(tmp_path / "tachado.pdf", base, [(448, 57, 480, 57, 2)], [])
    r = extraer_pdf(tmp_path / "tachado.pdf")
    assert not r["resuelto"] and r["nivel"] == 2 and r["confianza_minima"] < 0.90

    generate.escribir_pdf(tmp_path / "raro.pdf", base[:3] + [(455, 60, "F1", 10, "cien")], [], [])
    r = extraer_pdf(tmp_path / "raro.pdf")
    assert not r["resuelto"] and "no cuadran" in r["motivo"]

    generate.escribir_pdf(tmp_path / "ok.pdf", base, [], [])
    assert extraer_pdf(tmp_path / "ok.pdf")["resuelto"]
