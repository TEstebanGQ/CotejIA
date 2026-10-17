"""Ciclo del agente: Grok decide qué herramienta llamar; el código calcula los números."""
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Literal

import openai
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from .cfdi import leer_cfdi
from .matching import cotejar

DATASETS = Path(__file__).resolve().parent.parent / "datasets"
MAX_PASOS = 6
LIMITE_AUTONOMO_MXN = Decimal("5000")
CODIGOS_RECLAMABLES = {"QTY_SHORT", "PRICE_UP"}
REINTENTABLES = (openai.APITimeoutError, openai.APIConnectionError,
                 openai.RateLimitError, openai.InternalServerError)

SYSTEM_PROMPT = f"""Eres CotejAI, un agente de cuentas por pagar. Auditas un caso: orden de compra (OC),
remisión (lo recibido) y factura CFDI (lo cobrado).
Proceso obligatorio:
1. Llama a cotejar_caso. Los montos ya vienen calculados por código: NO los recalcules ni los cambies.
2. Decide el estado final:
   - APROBADO: solo si los códigos son únicamente MATCH_OK.
   - EN_RECLAMO: los códigos son solo QTY_SHORT y/o PRICE_UP y la fuga es de {LIMITE_AUTONOMO_MXN:,} MXN o menos; se pedirá nota de crédito al proveedor.
   - ESCALADO: cualquier otro código, fuga mayor a {LIMITE_AUTONOMO_MXN:,} MXN o cualquier duda.
3. Termina SIEMPRE llamando a cerrar_caso con los códigos y montos exactos de cotejar_caso y un resumen de 2 o 3 frases para cuentas por pagar.
Si cerrar_caso es rechazado, corrige según el motivo y vuelve a llamarlo."""

TOOLS = [
    {"type": "function", "function": {
        "name": "cotejar_caso",
        "description": "Corre el cotejo determinista del caso y devuelve códigos de discrepancia, monto a pagar y fuga en MXN.",
        "parameters": {"type": "object", "properties": {"case_id": {"type": "string", "description": "Id del caso, por ejemplo OC-001"}},
                       "required": ["case_id"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "cerrar_caso",
        "description": "Emite el veredicto final del caso y termina el ciclo.",
        "parameters": {"type": "object", "properties": {
            "case_id": {"type": "string"},
            "estado_final": {"type": "string", "enum": ["APROBADO", "EN_RECLAMO", "ESCALADO"]},
            "codigos": {"type": "array", "items": {"type": "string"}},
            "fuga_detectada_mxn": {"type": "string", "description": "Tomada tal cual de cotejar_caso"},
            "monto_a_pagar_mxn": {"type": "string", "description": "Tomada tal cual de cotejar_caso"},
            "resumen": {"type": "string", "description": "Dos o tres frases para cuentas por pagar"}},
            "required": ["case_id", "estado_final", "codigos", "fuga_detectada_mxn", "monto_a_pagar_mxn", "resumen"],
            "additionalProperties": False}}},
]


class Veredicto(BaseModel):
    case_id: str
    estado_final: Literal["APROBADO", "EN_RECLAMO", "ESCALADO"]
    codigos: list[str]
    fuga_detectada_mxn: Decimal
    monto_a_pagar_mxn: Decimal
    resumen: str = Field(min_length=1)


def cargar_caso(case_id: str) -> tuple[dict, dict, dict]:
    d = DATASETS / case_id
    oc = json.loads((d / "oc.json").read_text(encoding="utf-8"))
    remision = json.loads((d / "remision.json").read_text(encoding="utf-8"))
    return oc, remision, leer_cfdi(str(d / "cfdi.xml"))


def listar_casos() -> list[str]:
    """Solo las carpetas que son casos completos."""
    return sorted(d.name for d in DATASETS.iterdir()
                  if d.is_dir() and all((d / f).exists() for f in ("oc.json", "remision.json", "cfdi.xml")))


def tool_cotejar_caso(case_id: str) -> dict:
    oc, remision, cfdi = cargar_caso(case_id)
    return cotejar(oc, remision, cfdi)


def estados_permitidos(cotejo: dict) -> set[str]:
    """Qué estados finales admite la compuerta según el resultado del cotejo."""
    codigos = set(cotejo["codigos"])
    if codigos == {"MATCH_OK"}:
        return {"APROBADO", "ESCALADO"}
    if codigos <= CODIGOS_RECLAMABLES and Decimal(cotejo["fuga_detectada_mxn"]) <= LIMITE_AUTONOMO_MXN:
        return {"EN_RECLAMO", "ESCALADO"}
    return {"ESCALADO"}


def validar_veredicto(v: Veredicto, case_id: str, cotejo: dict | None) -> str | None:
    """Compuerta del cierre. Devuelve None si se acepta o el motivo del rechazo."""
    if cotejo is None:
        return "Primero llama a cotejar_caso; no se puede cerrar sin cotejo."
    if v.case_id != case_id:
        return f"El case_id debe ser {case_id}."
    if sorted(v.codigos) != cotejo["codigos"]:
        return f"Los códigos deben ser exactamente {cotejo['codigos']}."
    if v.monto_a_pagar_mxn != Decimal(cotejo["monto_a_pagar_mxn"]):
        return f"monto_a_pagar_mxn debe ser {cotejo['monto_a_pagar_mxn']}, el calculado por el cotejo."
    if v.fuga_detectada_mxn != Decimal(cotejo["fuga_detectada_mxn"]):
        return f"fuga_detectada_mxn debe ser {cotejo['fuga_detectada_mxn']}, la calculada por el cotejo."
    permitidos = estados_permitidos(cotejo)
    if v.estado_final not in permitidos:
        return f"Con estos códigos y esta fuga el estado debe ser uno de {sorted(permitidos)}."
    return None


def veredicto_escalado(case_id: str, motivo: str, cotejo: dict | None = None) -> dict:
    """Veredicto de respaldo con el mismo esquema que cerrar_caso."""
    return {"case_id": case_id, "estado_final": "ESCALADO",
            "codigos": cotejo["codigos"] if cotejo else [],
            "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"] if cotejo else None,
            "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"] if cotejo else None,
            "resumen": motivo}


def crear_cliente() -> OpenAI:
    return OpenAI(api_key=os.environ["RETO_KEY"],
                  base_url=os.environ.get("BASE_URL", "https://api.reto.pltk.mx/v1"), timeout=300)


@retry(retry=retry_if_exception_type(REINTENTABLES), wait=wait_exponential_jitter(initial=1, max=30),
       stop=stop_after_attempt(5), reraise=True)
def llamar_grok(client, model: str, messages: list):
    return client.chat.completions.create(model=model, messages=messages, tools=TOOLS,
                                          tool_choice="required", parallel_tool_calls=False)


def ejecutar_caso(case_id: str, client: OpenAI | None = None) -> dict:
    client = client or crear_cliente()
    model = os.environ.get("MODEL", "grok-4.6")
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Audita el caso {case_id}."}]
    uso = {"prompt_tokens": 0, "completion_tokens": 0, "llamadas": 0, "segundos": 0.0, "rechazos": 0}
    cotejo = None

    for _ in range(MAX_PASOS):
        t0 = time.perf_counter()
        resp = llamar_grok(client, model, messages)
        uso["segundos"] += time.perf_counter() - t0
        uso["llamadas"] += 1
        if resp.usage:
            uso["prompt_tokens"] += resp.usage.prompt_tokens
            uso["completion_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        for tc in msg.tool_calls or []:
            resultado = None
            try:
                args = json.loads(tc.function.arguments or "{}")
                if tc.function.name == "cerrar_caso":
                    v = Veredicto(**args)
                    motivo = validar_veredicto(v, case_id, cotejo)
                    if motivo is None:
                        return {"veredicto": json.loads(v.model_dump_json()), "uso": uso}
                    uso["rechazos"] += 1
                    resultado = {"ok": False, "rechazado": motivo}
                elif tc.function.name == "cotejar_caso":
                    # Siempre el caso que se está auditando, aunque Grok pida otro id.
                    try:
                        cotejo = tool_cotejar_caso(case_id)
                    except Exception as e:  # sin cotejo no hay nada que decidir: escalar ya
                        return {"veredicto": veredicto_escalado(
                            case_id, f"No se pudo cotejar el caso: {type(e).__name__}: {e}"), "uso": uso}
                    resultado = {"ok": True, "case_id": case_id, **cotejo}
                else:
                    resultado = {"ok": False, "error": f"herramienta desconocida: {tc.function.name}"}
            except (json.JSONDecodeError, ValidationError) as e:
                resultado = {"ok": False, "error": "argumentos inválidos", "detalle": str(e)[:500]}
            except Exception as e:  # el error vuelve a Grok, no tumba el lote
                resultado = {"ok": False, "error": type(e).__name__, "detalle": str(e)[:500]}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(resultado, ensure_ascii=False)})

    return {"veredicto": veredicto_escalado(case_id, "El agente agotó sus pasos sin cerrar el caso", cotejo),
            "uso": uso}


SYSTEM_PROMPT_CHAT = f"""Eres CotejAI, un agente autónomo de cuentas por pagar y conciliación de facturas CFDI 4.0 para empresas mexicanas en la plataforma Platica.
Tus responsabilidades:
1. Explicar claramente a los analistas de cuentas por pagar o proveedores el estado de las facturas, retenciones y discrepancias.
2. Si el usuario te pide auditar o revisar un caso (ej. OC-001, OC-002, OC-003), puedes usar la herramienta `cotejar_caso` para obtener los datos exactos calculados por el motor determinista.
3. Reglas de negocio:
   - APROBADO: sólo si no hay discrepancias (MATCH_OK).
   - EN_RECLAMO: faltantes (QTY_SHORT) o alza de precios (PRICE_UP) con fuga de hasta ${LIMITE_AUTONOMO_MXN:,.2f} MXN. Se retiene la diferencia y se solicita nota de crédito (CFDI de Egreso tipo E con relación 01).
   - ESCALADO: diferencias mayores al límite, discrepancia de impuestos (TAX_MISMATCH), CFDI cancelado o proveedor en lista 69-B del SAT.
4. Responde de forma concisa, profesional y fundamentada en pesos mexicanos (MXN) y normas del SAT."""


def tiene_llave_configurada() -> bool:
    """Verifica si hay una API key del reto válida en el entorno."""
    key = os.environ.get("RETO_KEY", "").strip()
    return bool(key and not key.startswith("pk_xxx"))


def formatear_resumen_caso(case_id: str, veredicto: dict | None = None, cotejo: dict | None = None) -> str:
    """Genera una tarjeta de resumen legible para la terminal."""
    if cotejo is None:
        try:
            cotejo = tool_cotejar_caso(case_id)
        except Exception as e:
            return f"Error al cargar caso {case_id}: {e}"

    codigos = ", ".join(cotejo.get("codigos", []))
    total = cotejo.get("total_cfdi_mxn", "0.00")
    pagar = cotejo.get("monto_a_pagar_mxn", "0.00")
    fuga = cotejo.get("fuga_detectada_mxn", "0.00")

    estado = veredicto.get("estado_final") if veredicto else (
        "APROBADO" if codigos == "MATCH_OK" else "EN_RECLAMO"
    )
    resumen_txt = veredicto.get("resumen") if veredicto else None

    lineas = [
        "----------------------------------------------------------------------",
        f" [CASO: {case_id}] - Estado: {estado}",
        "----------------------------------------------------------------------",
        f"  Total facturado (CFDI):    ${Decimal(total):>10,.2f} MXN",
        f"  Monto neto a pagar:        ${Decimal(pagar):>10,.2f} MXN",
        f"  Fuga detectada / retenida: ${Decimal(fuga):>10,.2f} MXN",
        f"  Códigos de discrepancia:   {codigos}",
    ]
    detalles = cotejo.get("detalle", [])
    if detalles:
        lineas.append("  Detalle de incidencias:")
        for d in detalles:
            sku = d.get("sku", "-")
            prob = d.get("problema", "")
            extra = " ".join(f"{k}={v}" for k, v in d.items() if k not in ("sku", "problema"))
            lineas.append(f"    • [{sku}] {prob} ({extra})")
    if resumen_txt:
        lineas.append("  Veredicto del Agente:")
        lineas.append(f"    \"{resumen_txt}\"")
    lineas.append("----------------------------------------------------------------------")
    return "\n".join(lineas)


@retry(retry=retry_if_exception_type(REINTENTABLES), wait=wait_exponential_jitter(initial=1, max=30),
       stop=stop_after_attempt(5), reraise=True)
def llamar_grok_chat(client, model: str, messages: list):
    """Llama a Grok en modo conversacional con tool calling opcional (auto)."""
    tools_chat = [{"type": "function", "function": TOOLS[0]["function"]}]
    return client.chat.completions.create(model=model, messages=messages, tools=tools_chat,
                                          tool_choice="auto", parallel_tool_calls=False)


def conversar(mensaje_usuario: str, historial: list | None = None, client: OpenAI | None = None) -> tuple[str, list, dict]:
    """Envía un mensaje al agente en modo chat interactivo y devuelve (respuesta, nuevo_historial, uso)."""
    historial = list(historial or [])
    if not historial:
        historial.append({"role": "system", "content": SYSTEM_PROMPT_CHAT})
    historial.append({"role": "user", "content": mensaje_usuario})

    uso = {"prompt_tokens": 0, "completion_tokens": 0, "llamadas": 0}
    model = os.environ.get("MODEL", "grok-4.6")
    client = client or crear_cliente()

    for _ in range(3):
        resp = llamar_grok_chat(client, model, historial)
        uso["llamadas"] += 1
        if resp.usage:
            uso["prompt_tokens"] += resp.usage.prompt_tokens
            uso["completion_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message
        historial.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content or "", historial, uso

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            if tc.function.name == "cotejar_caso":
                cid = args.get("case_id", "OC-001")
                try:
                    res = {"ok": True, "case_id": cid, **tool_cotejar_caso(cid)}
                except Exception as e:
                    res = {"ok": False, "error": f"Error al cotejar {cid}: {e}"}
            else:
                res = {"ok": False, "error": f"Herramienta no permitida: {tc.function.name}"}
            historial.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(res, ensure_ascii=False)})

    return "No pude generar una respuesta de texto adicional.", historial, uso

