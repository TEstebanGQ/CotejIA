"""S4: generador de 1,000 casos (distribución, ground truth, reproducibilidad) y máquina de resiliencia."""
import json
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "datasets"))
import generate  # noqa: E402
from src import resilience as R  # noqa: E402


def generate_uuid(carpeta: Path) -> str:
    return (carpeta / "cfdi.xml").read_text(encoding="utf-8").split('UUID="')[1].split('"')[0]


# ── Generador S4 ──────────────────────────────────────────────────────────────
def test_cuotas_suman_n_y_respetan_distribucion():
    cuotas = dict(generate.cuotas_s4(1000))
    assert cuotas == {"MATCH_OK": 400, "QTY_SHORT": 250, "PRICE_TAX": 150, "FX_OVERCHARGE": 100,
                      "SUPPLIER_69B": 50, "FISCAL_RECHAZO": 50}
    for n in (1, 7, 33, 999):
        assert sum(dict(generate.cuotas_s4(n)).values()) == n


def test_iterador_es_streaming_y_reproducible():
    it = generate.iter_casos_s4(3, 60)
    assert iter(it) is it                       # generador, no lista
    a = [(s["id"], s["tipo"], s["uuid"]) for s in generate.iter_casos_s4(3, 60)]
    b = [(s["id"], s["tipo"], s["uuid"]) for s in generate.iter_casos_s4(3, 60)]
    c = [(s["id"], s["tipo"], s["uuid"]) for s in generate.iter_casos_s4(4, 60)]
    assert a == b and a != c


@pytest.fixture(scope="module")
def s4(tmp_path_factory):
    d = tmp_path_factory.mktemp("s4")
    generate.generar_s4(11, d, 100)
    return d


def test_estructura_de_cada_caso(s4):
    casos = sorted(p for p in s4.iterdir() if p.is_dir())
    assert len(casos) == 100 and casos[0].name == "S4-0001"
    for p in casos:
        assert (p / "oc.json").exists() and (p / "cfdi.xml").exists() and (p / "esperado.json").exists()
        assert (p / "remision.pdf").exists() or (p / "remision.png").exists()
        xml = (p / "cfdi.xml").read_text(encoding="utf-8")
        assert 'Version="4.0"' in xml and "Sello=" in xml and "SelloSAT=" in xml and "Traslado" in xml


def test_esperado_decimal_al_centavo_y_alias(s4):
    for f in s4.glob("*/esperado.json"):
        e = json.loads(f.read_text())
        for k in ("monto_autorizado_mxn", "fuga_retenida_mxn", "total_cfdi_mxn"):
            assert Decimal(e[k]) == Decimal(e[k]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert e["monto_autorizado_mxn"] == e["monto_a_pagar_mxn"]
        assert e["estado_final"] in {"APROBADO", "EN_RECLAMO", "ESCALADO"}
        assert isinstance(e["codigos_discrepancia"], list)
        if e["estado_final"] == "APROBADO":
            assert e["fuga_retenida_mxn"] == "0.00" and e["codigos_discrepancia"] == []


def test_69b_usa_efos_definitivos_reales_del_csv(s4):
    reales = {r["rfc"] for r in generate.cargar_efos_definitivos()}
    assert "VDI1508142W6" not in reales and "AAA080808AAA" in reales      # el Presunto no entra
    for p in s4.glob("*/oc.json"):
        e = json.loads((p.parent / "esperado.json").read_text())
        if e["familia_s4"] == "SUPPLIER_69B":
            assert json.loads(p.read_text())["proveedor_rfc"] in reales
            assert e["codigos"] == ["SUPPLIER_69B"] and e["monto_autorizado_mxn"] == "0.00"


def test_fx_cancelado_y_duplicado(s4):
    tipos = Counter()
    for f in s4.glob("*/esperado.json"):
        e = json.loads(f.read_text())
        tipos[e["tipo_caso"]] += 1
        if e["tipo_caso"] == "FX_OVERCHARGE":
            tc, fix = Decimal(e["tipo_cambio_cfdi"]), Decimal(e["fix_oficial_referencia"])
            assert (tc - fix) / fix > Decimal("0.015") and 'Moneda="USD"' in (f.parent / "cfdi.xml").read_text()
            assert Decimal(e["fuga_retenida_mxn"]) > 0
        if e["tipo_caso"] == "CFDI_CANCELADO":
            assert (f.parent / "sat_estatus.json").exists() and e["estado_final"] == "ESCALADO"
        if e["tipo_caso"] == "DUPLICATE":
            uuid = generate_uuid(f.parent)
            assert sum(generate_uuid(q.parent) == uuid for q in f.parent.parent.glob("*/cfdi.xml")) >= 2
            assert e["codigos"] == ["DUPLICATE"] and e["monto_autorizado_mxn"] == "0.00"
    assert tipos["MATCH_OK"] > 0 and tipos["FX_OVERCHARGE"] > 0


def test_generador_s4_reproducible_byte_a_byte(tmp_path):
    generate.generar_s4(5, tmp_path / "a", 20)
    generate.generar_s4(5, tmp_path / "b", 20)
    h = lambda d: {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}
    assert h(tmp_path / "a") == h(tmp_path / "b")


# ── Resiliencia ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch, tmp_path):
    esperas = []
    monkeypatch.setattr(R, "_sleep", esperas.append)
    monkeypatch.setattr(R, "BITACORA_PATH", tmp_path / "bitacora.jsonl")
    R._FIX_CACHE.clear()
    return esperas


def _http_error(status, retry_after=None):
    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(status, request=req, headers={"Retry-After": retry_after} if retry_after else {})
    return httpx.HTTPStatusError("boom", request=req, response=resp)


def test_reintenta_y_recupera(sin_esperas):
    llamadas = []

    @R.with_resilience(max_retries=3, backoff_factor=2, servicio="grok")
    def f():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise httpx.ConnectTimeout("t")
        return {"ok": True}

    r = f()
    assert len(llamadas) == 3 and r["ok"] and len(sin_esperas) == 2
    assert r["resiliencia"]["estrategia_recuperacion"] == "reintento_exitoso_2x_backoff"
    linea = json.loads(R.BITACORA_PATH.read_text().splitlines()[0])
    assert linea["error"].startswith("ConnectTimeout") and linea["recuperado"] is True


def test_backoff_exponencial_con_jitter_y_tope(sin_esperas):
    @R.with_resilience(max_retries=3, backoff_factor=2, base_delay=1, max_delay=100)
    def f():
        raise httpx.ReadTimeout("t")

    with pytest.raises(httpx.ReadTimeout):
        f()
    assert len(sin_esperas) == 3
    for i, e in enumerate(sin_esperas):
        base = 2 ** i
        assert base <= e <= base * 1.25                    # jitter entre 0 y 25 %
    assert R.calcular_espera(10, 2, 1, 5) == 5               # tope max_delay


def test_429_respeta_retry_after(sin_esperas):
    n = []

    @R.with_resilience(max_retries=2, base_delay=0.1)
    def f():
        n.append(1)
        if len(n) == 1:
            raise _http_error(429, "7")
        return "ok"

    assert f() == "ok" and sin_esperas[0] >= 7


def test_error_no_transitorio_no_reintenta(sin_esperas):
    n = []

    @R.with_resilience(max_retries=3)
    def f():
        n.append(1)
        raise ValueError("lógica")

    with pytest.raises(ValueError):
        f()
    assert len(n) == 1 and not sin_esperas
    with pytest.raises(httpx.HTTPStatusError):               # 400 tampoco es transitorio
        R.with_resilience(max_retries=3)(lambda: (_ for _ in ()).throw(_http_error(400)))()


def test_agota_reintentos_sin_fallback_registra_incidente(sin_esperas):
    visto = []

    @R.with_resilience(max_retries=2, on_incident=visto.append)
    def f():
        raise _http_error(503)

    with pytest.raises(httpx.HTTPStatusError):
        f()
    assert visto[0].recuperado is False and visto[0].estrategia_recuperacion is None
    assert visto[0].intentos == 3 and json.loads(R.BITACORA_PATH.read_text().splitlines()[-1])["recuperado"] is False


def test_fallback_sat_sintactico(sin_esperas):
    @R.con_resiliencia_sat
    def soap(case_id, uuid, rfc_emisor, rfc_receptor, total):
        raise httpx.ConnectTimeout("SAT caído")

    r = soap("S4-0001", "6F1B2C3D-4E5F-4A6B-8C7D-9E0F1A2B3C4D", "FHN150312K41", "BBB020202BBB", "100.00")
    assert r["codigos_fiscales"] == ["SAT_NO_VERIFICADO"] and r["validacion_sintactica"]["sintaxis_ok"]
    assert r["resiliencia"]["estrategia_recuperacion"] == "fallback:cfdi_sintactico"
    assert r["resiliencia"]["error"].startswith("ConnectTimeout")
    mal = R.validar_cfdi_sintactico("no-uuid", "xx", "BBB020202BBB", "-5")
    assert not mal["sintaxis_ok"] and len(mal["problemas"]) == 3


def test_fallback_banxico_usa_ultimo_fix_del_dia(sin_esperas):
    estado = {"cae": False}

    def fix(moneda="USD"):
        if estado["cae"]:
            raise httpx.ConnectError("corte")
        return {"ok": True, "tasa_oficial_mxn": "18.7345"}

    f = R.con_resiliencia_banxico(fix)
    assert f("USD")["tasa_oficial_mxn"] == "18.7345"
    estado["cae"] = True
    r = f("USD")
    assert r["tasa_oficial_mxn"] == "18.7345" and r["contingencia_cache"]
    assert r["resiliencia"]["estrategia_recuperacion"] == "fallback:cache_fix_dia"
    with pytest.raises(RuntimeError):                          # sin FIX del día para otra moneda
        f("EUR")
