"""Punto de entrada para evaluadores externos (harness): audita casos que viven en cualquier carpeta.

Un caso es una carpeta con:
    oc.json          (obligatorio) Orden de compra
    cfdi.xml         (obligatorio) Factura CFDI 4.0
    remision.json    (al menos uno de los tres) Remisión estructurada
    remision.pdf     Remisión digital (se extrae localmente, sin red)
    remision.png     Foto de la remisión física (se lee con Grok Vision)
    sat_estatus.json (opcional) Acuse de estatus SAT, p. ej. {"uuid": "...", "estado": "Cancelado"}

Lo usan `python main.py audit --dir <carpeta>` y `POST /api/v1/auditar`.
"""
from __future__ import annotations

import base64
import contextlib
import os
import re
import tempfile
import threading
import time
from decimal import Decimal
from pathlib import Path

from . import agent, vision
from .db import COSTO_INPUT_1M, COSTO_OUTPUT_1M

ARCHIVOS_REMISION = ("remision.json", "remision.pdf", "remision.png")
PATRON_CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")
_LOCK = threading.RLock()


def es_caso(d: Path) -> bool:
    return (
        d.is_dir()
        and (d / "oc.json").exists()
        and (d / "cfdi.xml").exists()
        and any((d / f).exists() for f in ARCHIVOS_REMISION)
    )


def descubrir_casos(ruta: Path) -> tuple[Path, list[str]]:
    """Acepta la carpeta de un caso o una carpeta con varios casos. Devuelve (base, ids)."""
    ruta = ruta.resolve()
    if not ruta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta {ruta}")
    if es_caso(ruta):
        return ruta.parent, [ruta.name]
    ids = sorted(d.name for d in ruta.iterdir() if es_caso(d))
    if not ids:
        raise FileNotFoundError(
            f"{ruta} no contiene casos: cada caso necesita oc.json, cfdi.xml y remision.json|pdf|png"
        )
    return ruta, ids


@contextlib.contextmanager
def usar_carpeta(base: Path):
    """Apunta el agente y la visión a otra carpeta de casos. Serializado: el agente usa estado global."""
    with _LOCK:
        previo = (agent.DATASETS, vision.DATASETS)
        agent.DATASETS = vision.DATASETS = Path(base).resolve()
        try:
            yield
        finally:
            agent.DATASETS, vision.DATASETS = previo


def _estado_por_politica(cotejo: dict) -> str:
    permitidos = agent.estados_permitidos(cotejo)
    return next(e for e in ("APROBADO", "EN_RECLAMO", "ESCALADO") if e in permitidos)


def _costo_usd(tok_in: int, tok_out: int) -> float:
    return round((tok_in * COSTO_INPUT_1M + tok_out * COSTO_OUTPUT_1M) / 1_000_000, 6)


def _resultado(case_id, veredicto, modo, uso=None, error=None, segundos=0.0) -> dict:
    uso = uso or {}
    tok_in = int(uso.get("prompt_tokens", 0))
    tok_out = int(uso.get("completion_tokens", 0))
    return {
        "case_id": case_id,
        "estado_final": veredicto.get("estado_final", "ESCALADO"),
        "codigos": veredicto.get("codigos", []),
        "monto_a_pagar_mxn": str(veredicto.get("monto_a_pagar_mxn") or "0.00"),
        "fuga_detectada_mxn": str(veredicto.get("fuga_detectada_mxn") or "0.00"),
        "resumen": veredicto.get("resumen", ""),
        "modo": modo,
        "herramientas": uso.get("herramientas", []),
        "uso": {
            "llamadas_llm": int(uso.get("llamadas", 0)),
            "tokens_in": tok_in,
            "tokens_out": tok_out,
            "costo_usd": _costo_usd(tok_in, tok_out),
            "latencia_s": round(segundos, 3),
        },
        "error": error,
    }


def _auditar_determinista(case_id: str) -> dict:
    cotejo = agent._cotejar_con_reintentos(case_id, None)
    estado = _estado_por_politica(cotejo)
    return {
        "case_id": case_id,
        "estado_final": estado,
        "codigos": cotejo["codigos"],
        "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"],
        "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"],
        "resumen": f"Veredicto determinista por policy_gate (códigos: {', '.join(cotejo['codigos'])}).",
    }


def auditar_caso(base: Path, case_id: str, modo: str = "auto", client=None) -> dict:
    """Audita un caso y devuelve siempre un veredicto (nunca lanza excepción).

    modo: "auto" (Grok si hay RETO_KEY, si no determinista), "grok" o "determinista".
    """
    t0 = time.perf_counter()
    if modo == "auto":
        modo = "grok" if agent.tiene_llave_configurada() else "determinista"
    with usar_carpeta(base):
        if modo == "grok":
            try:
                # Se pasa el cliente explícito para no mezclar los casos del harness con el dashboard
                r = agent.ejecutar_caso(case_id, client=client or agent.crear_cliente())
                return _resultado(case_id, r["veredicto"], "grok-4.6", r.get("uso"),
                                  (r.get("uso") or {}).get("error_sistema"), time.perf_counter() - t0)
            except Exception as e:  # el gateway cayó: el caso no se pierde
                error = f"{type(e).__name__}: {str(e)[:300]}"
                try:
                    v = _auditar_determinista(case_id)
                    v["resumen"] = f"Gateway LLM no disponible ({type(e).__name__}); " + v["resumen"]
                    return _resultado(case_id, v, "fallback_determinista", None, error, time.perf_counter() - t0)
                except Exception as e2:
                    v = agent.veredicto_escalado(case_id, f"Error: {e2}", agent.cotejo_error_sistema())
                    return _resultado(case_id, v, "error", None, f"{error} | {type(e2).__name__}: {e2}",
                                      time.perf_counter() - t0)
        try:
            return _resultado(case_id, _auditar_determinista(case_id), "determinista", None, None,
                              time.perf_counter() - t0)
        except Exception as e:
            v = agent.veredicto_escalado(case_id, f"No se pudo cotejar: {e}", agent.cotejo_error_sistema())
            return _resultado(case_id, v, "error", None, f"{type(e).__name__}: {e}", time.perf_counter() - t0)


def comparar_con_esperado(carpeta_caso: Path, resultado: dict) -> dict | None:
    """Si el caso trae esperado.json, indica si el estado y los códigos coinciden."""
    ruta = carpeta_caso / "esperado.json"
    if not ruta.exists():
        return None
    import json

    esperado = json.loads(ruta.read_text(encoding="utf-8"))
    ok_estado = esperado.get("estado_final") == resultado["estado_final"]
    ok_codigos = sorted(esperado.get("codigos", [])) == sorted(resultado["codigos"])
    ok_monto = True
    if esperado.get("monto_a_pagar_mxn") is not None:
        ok_monto = Decimal(str(esperado["monto_a_pagar_mxn"])) == Decimal(resultado["monto_a_pagar_mxn"])
    return {"estado": ok_estado, "codigos": ok_codigos, "monto": ok_monto}


def escribir_caso_temporal(payload: dict) -> tuple[Path, str, tempfile.TemporaryDirectory]:
    """Materializa en disco un caso recibido por HTTP. El llamador debe cerrar el TemporaryDirectory."""
    import json

    case_id = str(payload.get("case_id") or "HARNESS-001").strip()
    if not PATRON_CASE_ID.match(case_id):
        raise ValueError("case_id inválido: usa letras, números, '-', '_' o '.' (máx. 64)")
    if not isinstance(payload.get("oc"), dict):
        raise ValueError("Falta 'oc' (objeto JSON de la orden de compra)")
    if not payload.get("cfdi_xml"):
        raise ValueError("Falta 'cfdi_xml' (texto del CFDI 4.0)")
    if not any(payload.get(k) for k in ("remision", "remision_pdf_base64", "remision_png_base64")):
        raise ValueError("Falta la remisión: 'remision' (JSON), 'remision_pdf_base64' o 'remision_png_base64'")

    tmp = tempfile.TemporaryDirectory(prefix="cotejai_harness_", ignore_cleanup_errors=True)
    d = Path(tmp.name) / case_id
    d.mkdir(parents=True)
    (d / "oc.json").write_text(json.dumps(payload["oc"], ensure_ascii=False), encoding="utf-8")
    (d / "cfdi.xml").write_text(payload["cfdi_xml"], encoding="utf-8")
    if isinstance(payload.get("remision"), dict):
        (d / "remision.json").write_text(json.dumps(payload["remision"], ensure_ascii=False), encoding="utf-8")
    for clave, nombre in (("remision_pdf_base64", "remision.pdf"), ("remision_png_base64", "remision.png")):
        if payload.get(clave):
            (d / nombre).write_bytes(base64.b64decode(payload[clave]))
    if isinstance(payload.get("sat_estatus"), dict):
        (d / "sat_estatus.json").write_text(json.dumps(payload["sat_estatus"]), encoding="utf-8")
    return Path(tmp.name), case_id, tmp


def bd_aislada() -> tempfile.TemporaryDirectory:
    """SQLite temporal para que una corrida del harness no se contamine con corridas previas."""
    tmp = tempfile.TemporaryDirectory(prefix="cotejai_bd_", ignore_cleanup_errors=True)
    os.environ["DATABASE_URL"] = ""
    os.environ["SQLITE_PATH"] = str(Path(tmp.name) / "harness.db")
    return tmp
