"""Ciclo del agente: Grok decide qué herramienta llamar; el código calcula los números."""
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from .cfdi import leer_cfdi
from .matching import cotejar

DATASETS = Path(__file__).resolve().parent.parent / "datasets"
MAX_PASOS = 6

SYSTEM_PROMPT = """Eres CotejAI, un agente de cuentas por pagar. Auditas un caso: orden de compra (OC),
remisión (lo recibido) y factura CFDI (lo cobrado).
Proceso obligatorio:
1. Llama a cotejar_caso con el id del caso. Los montos ya vienen calculados por código: NO los recalcules ni los cambies.
2. Decide el estado final:
   - APROBADO: solo si los códigos son únicamente MATCH_OK.
   - EN_RECLAMO: hay QTY_SHORT o PRICE_UP y la fuga es de 5,000 MXN o menos; se pedirá nota de crédito al proveedor.
   - ESCALADO: TAX_MISMATCH, SKU_UNMAPPED, QTY_OVER_PO, fuga mayor a 5,000 MXN o cualquier duda.
3. Termina SIEMPRE llamando a cerrar_caso con tu veredicto y un resumen de 2 o 3 frases para cuentas por pagar."""

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


def tool_cotejar_caso(case_id: str) -> dict:
    oc, remision, cfdi = cargar_caso(case_id)
    return cotejar(oc, remision, cfdi)


def crear_cliente() -> OpenAI:
    return OpenAI(api_key=os.environ["RETO_KEY"],
                  base_url=os.environ.get("BASE_URL", "https://api.reto.pltk.mx/v1"), timeout=300)


def ejecutar_caso(case_id: str, client: OpenAI | None = None) -> dict:
    client = client or crear_cliente()
    model = os.environ.get("MODEL", "grok-4.6")
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Audita el caso {case_id}."}]
    uso = {"prompt_tokens": 0, "completion_tokens": 0, "llamadas": 0, "segundos": 0.0}

    for _ in range(MAX_PASOS):
        t0 = time.perf_counter()
        resp = client.chat.completions.create(model=model, messages=messages, tools=TOOLS,
                                              tool_choice="required", parallel_tool_calls=False)
        uso["segundos"] += time.perf_counter() - t0
        uso["llamadas"] += 1
        if resp.usage:
            uso["prompt_tokens"] += resp.usage.prompt_tokens
            uso["completion_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        for tc in msg.tool_calls or []:
            args = json.loads(tc.function.arguments)
            if tc.function.name == "cerrar_caso":
                v = Veredicto(**args)
                return {"veredicto": json.loads(v.model_dump_json()), "uso": uso}
            if tc.function.name == "cotejar_caso":
                resultado = tool_cotejar_caso(args["case_id"])
            else:
                resultado = {"error": f"herramienta desconocida: {tc.function.name}"}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(resultado, ensure_ascii=False)})

    return {"veredicto": {"case_id": case_id, "estado_final": "ESCALADO", "codigos": [],
                          "resumen": "El agente agotó sus pasos sin cerrar el caso"}, "uso": uso}
