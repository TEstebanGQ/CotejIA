"""Resiliencia para corridas largas (S4): reintentos con backoff+jitter, fallbacks por servicio y bitácora.

    @with_resilience(max_retries=3, backoff_factor=1.5, servicio="grok")
    def llamar(...): ...

Errores transitorios (red, timeouts, HTTP 429/5xx) se reintentan con espera exponencial más jitter
(respetando `Retry-After`). Si se agotan, se aplica el `fallback` del servicio (si existe); sin fallback
la excepción original se propaga. Cada incidente produce un `Incidente` con
`error: str | None` y `estrategia_recuperacion: str | None` y se anexa a la bitácora JSONL.
"""
from __future__ import annotations

import functools
import json
import random
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import httpx

ROOT = Path(__file__).resolve().parent.parent
BITACORA_PATH = ROOT / "runs" / "bitacora_resiliencia.jsonl"
STATUS_TRANSITORIOS = {408, 425, 429, 500, 502, 503, 504}

# Inyectables para pruebas (evitan esperas reales y hacen el jitter determinista).
_sleep: Callable[[float], None] = time.sleep
_rng = random.Random()


@dataclass
class Incidente:
    servicio: str
    funcion: str
    intentos: int
    error: str | None = None                       # último error observado (None si no hubo)
    estrategia_recuperacion: str | None = None     # p. ej. "reintento_exitoso", "fallback:cfdi_sintactico"
    recuperado: bool = True
    esperas_s: list[float] = field(default_factory=list)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def a_dict(self) -> dict:
        return asdict(self)


def es_transitorio(exc: BaseException) -> bool:
    """Red caída, timeouts, 429 y 5xx. Funciona con httpx y con el SDK de openai (status_code / response)."""
    if isinstance(exc, (httpx.TransportError, TimeoutError, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return int(status) in STATUS_TRANSITORIOS
    return type(exc).__name__ in {"APITimeoutError", "APIConnectionError", "RateLimitError", "InternalServerError"}


def _retry_after(exc: BaseException) -> float | None:
    resp = getattr(exc, "response", None)
    valor = getattr(resp, "headers", {}).get("Retry-After") if resp is not None else None
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def calcular_espera(intento: int, backoff_factor: float, base_delay: float, max_delay: float,
                    retry_after: float | None = None) -> float:
    """base * factor^intento + jitter aleatorio (0..25 %), acotado a max_delay; Retry-After manda si es mayor."""
    espera = base_delay * (backoff_factor ** intento)
    espera += _rng.uniform(0, espera * 0.25)
    if retry_after is not None:
        espera = max(espera, retry_after)
    return min(espera, max_delay)


def registrar_incidente(inc: Incidente, ruta: Path | None = None) -> None:
    """Anexa el incidente a la bitácora. Nunca lanza: la bitácora no debe tumbar el lote."""
    try:
        destino = ruta or BITACORA_PATH
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("a", encoding="utf-8") as f:
            f.write(json.dumps(inc.a_dict(), ensure_ascii=False) + "\n")
    except OSError:
        pass


def with_resilience(max_retries: int = 3, backoff_factor: float = 1.5, *, servicio: str = "generico",
                    fallback: Callable[..., Any] | None = None, fallback_nombre: str | None = None,
                    base_delay: float = 1.0, max_delay: float = 30.0,
                    bitacora: Path | None = None, on_incident: Callable[[Incidente], None] | None = None):
    """Decorador: hasta `max_retries` reintentos tras el primer intento (max_retries+1 llamadas en total).

    `fallback(*args, error=<exc>, **kwargs)` se invoca al agotar los reintentos de un error transitorio;
    los errores de lógica (ValueError, etc.) se propagan de inmediato, sin reintentar ni fallback.
    Si el resultado es un dict y hubo incidente, se le agrega la clave `resiliencia`.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            esperas: list[float] = []
            ultimo: BaseException | None = None
            for intento in range(max_retries + 1):
                try:
                    valor = fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    if not es_transitorio(exc):
                        raise
                    ultimo = exc
                    if intento == max_retries:
                        break
                    espera = calcular_espera(intento, backoff_factor, base_delay, max_delay, _retry_after(exc))
                    esperas.append(round(espera, 3))
                    _sleep(espera)
                    continue
                if intento == 0:
                    return valor
                inc = Incidente(servicio, fn.__name__, intento + 1, error=f"{type(ultimo).__name__}: {ultimo}"[:300],
                                estrategia_recuperacion=f"reintento_exitoso_{intento}x_backoff", esperas_s=esperas)
                _emitir(inc, bitacora, on_incident)
                return _anotar(valor, inc)
            err = f"{type(ultimo).__name__}: {ultimo}"[:300]
            if fallback is None:
                inc = Incidente(servicio, fn.__name__, max_retries + 1, error=err, estrategia_recuperacion=None,
                                recuperado=False, esperas_s=esperas)
                _emitir(inc, bitacora, on_incident)
                raise ultimo  # type: ignore[misc]
            valor = fallback(*args, error=ultimo, **kwargs)
            inc = Incidente(servicio, fn.__name__, max_retries + 1, error=err,
                            estrategia_recuperacion=f"fallback:{fallback_nombre or fallback.__name__}", esperas_s=esperas)
            _emitir(inc, bitacora, on_incident)
            return _anotar(valor, inc)
        return wrapper
    return deco


def _emitir(inc: Incidente, bitacora: Path | None, on_incident: Callable[[Incidente], None] | None) -> None:
    registrar_incidente(inc, bitacora)
    if on_incident:
        on_incident(inc)


def _anotar(valor: Any, inc: Incidente) -> Any:
    if isinstance(valor, dict):
        valor = {**valor, "resiliencia": {"error": inc.error, "estrategia_recuperacion": inc.estrategia_recuperacion,
                                          "intentos": inc.intentos, "recuperado": inc.recuperado}}
    return valor


# ── Fallback SAT: validación sintáctica del CFDI cuando el SOAP no responde ────────────────────
_RE_UUID = re.compile(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$")
_RE_RFC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")


def validar_cfdi_sintactico(uuid: str, rfc_emisor: str, rfc_receptor: str, total: str | float) -> dict:
    """Validación local sin red: formato de UUID, RFC emisor/receptor y total positivo."""
    problemas = []
    if not _RE_UUID.match((uuid or "").strip().upper()):
        problemas.append("UUID con formato inválido")
    for nombre, rfc in (("emisor", rfc_emisor), ("receptor", rfc_receptor)):
        if not _RE_RFC.match((rfc or "").strip().upper()):
            problemas.append(f"RFC {nombre} con formato inválido")
    try:
        if Decimal(str(total)) <= 0:
            problemas.append("Total no positivo")
    except Exception:  # noqa: BLE001
        problemas.append("Total no numérico")
    return {"sintaxis_ok": not problemas, "problemas": problemas}


def fallback_sat_sintactico(case_id: str, uuid: str, rfc_emisor: str, rfc_receptor: str, total: str | float,
                            *, error: BaseException | None = None, **_: Any) -> dict:
    """Degradación del SAT: el lote continúa con SAT_NO_VERIFICADO + validación de sintaxis."""
    return {"ok": True, "case_id": case_id, "uuid": uuid, "rfc_emisor": rfc_emisor,
            "sat_soap": {"estado": "SAT_NO_VERIFICADO", "detalle": f"SOAP del SAT caído: {type(error).__name__}"},
            "validacion_sintactica": validar_cfdi_sintactico(uuid, rfc_emisor, rfc_receptor, total),
            "codigos_fiscales": ["SAT_NO_VERIFICADO"]}


# ── Fallback Banxico FIX: último FIX válido del día ─────────────────────────────────────────────
_FIX_CACHE: dict[str, tuple[str, Decimal]] = {}     # moneda -> (fecha ISO, tasa)


def _hoy() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def guardar_fix_valido(moneda: str, tasa: Decimal | float | str) -> None:
    _FIX_CACHE[moneda.upper()] = (_hoy(), Decimal(str(tasa)))


def fallback_fix_cache(moneda: str = "USD", *args: Any, error: BaseException | None = None, **_: Any) -> dict:
    """Micro-corte de Banxico: usa el último FIX válido de HOY; si no hay, vuelve a propagar el error."""
    fecha, tasa = _FIX_CACHE.get(moneda.upper(), (None, None))
    if fecha != _hoy():
        raise RuntimeError(f"Sin FIX válido del día para {moneda}") from error
    return {"ok": True, "moneda": moneda.upper(), "tasa_oficial_mxn": f"{tasa:.4f}", "fuente": f"cache_fix_{fecha}",
            "contingencia_cache": True}


def con_resiliencia_sat(fn: Callable[..., dict], **kw):
    return with_resilience(servicio="sat_soap", fallback=fallback_sat_sintactico, fallback_nombre="cfdi_sintactico", **kw)(fn)


def con_resiliencia_banxico(fn: Callable[..., dict], **kw):
    """Envuelve una consulta de FIX; los éxitos alimentan el caché del día."""
    @functools.wraps(fn)
    def y_guardar(moneda: str = "USD", *a, **k):
        res = fn(moneda, *a, **k)
        if isinstance(res, dict) and res.get("tasa_oficial_mxn") and not res.get("contingencia_cache"):
            guardar_fix_valido(moneda, res["tasa_oficial_mxn"])
        return res
    return with_resilience(servicio="banxico_fix", fallback=fallback_fix_cache, fallback_nombre="cache_fix_dia", **kw)(y_guardar)
