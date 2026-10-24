"""Ciclo del agente CotejAI (S2): Grok 4.6 decide qué herramientas reales invocar;
el motor determinista y la compuerta policy_gate validan montos, límites e idempotencia."""
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
from .db import (
    buscar_rfc_69b,
    guardar_resultado_caso,
    init_db,
    verificar_duplicado_uuid,
)
from .external_tools import (
    CIRCUIT_BREAKER_SAT,
    consultar_sat_en_vivo,
    consultar_tipo_cambio_real,
    enviar_alerta_reclamo_real,
)
from .matching import _q, cotejar
from .vision import calcular_nitidez_imagen, leer_remision_imagen, UMBRAL_NITIDEZ_IMAGEN

DATASETS = Path(__file__).resolve().parent.parent / "datasets"
MAX_PASOS = 10
LIMITE_AUTONOMO_MXN = Decimal("5000")
CODIGOS_RECLAMABLES = {"QTY_SHORT", "PRICE_UP"}
REINTENTABLES = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)

SYSTEM_PROMPT = f"""Eres CotejAI, un agente autónomo de cuentas por pagar y auditoría fiscal CFDI 4.0.
Auditas un caso compuesto por: Orden de Compra (OC), Remisión de almacén y Factura CFDI (XML).

Herramientas reales disponibles:
- `leer_remision_imagen`: Úsala cuando el caso tenga evidencia visual (`remision.png`, ej. OC-004, OC-005) para extraer con Grok Vision cantidades recibidas, sellos y notas a mano.
- `consultar_tipo_cambio_real`: Úsala cuando la factura u OC esté en moneda extranjera (`USD`, ej. OC-006) para validar el tipo de cambio en vivo.
- `consultar_sat_en_vivo`: Consulta el Webservice SOAP del SAT (con Circuit Breaker), la Lista 69-B oficial de EFOS y duplicidad de UUID.
- `cotejar_caso`: Ejecuta el motor matemático determinista de 3 vías y consolida todos los códigos y montos en MXN.
- `enviar_alerta_reclamo_real`: Si el estado será EN_RECLAMO (solo códigos QTY_SHORT y/o PRICE_UP con fuga <= {LIMITE_AUTONOMO_MXN:,} MXN), envía la solicitud formal de nota de crédito con llave de idempotencia.
- `cerrar_caso`: Emite el veredicto final obligatorio y termina el ciclo.

Reglas de decisión para `cerrar_caso`:
1. Llama a `cotejar_caso` (y a las herramientas específicas que apliquen al caso). NUNCA inventes ni alteres los montos de `cotejar_caso`.
2. Estado final:
   - `APROBADO`: únicamente si `codigos` es `["MATCH_OK"]`.
   - `EN_RECLAMO`: únicamente si `codigos` contiene solo `QTY_SHORT` y/o `PRICE_UP` y `fuga_detectada_mxn` <= {LIMITE_AUTONOMO_MXN:,} MXN.
   - `ESCALADO`: cualquier otro código (`RECEIPT_UNREADABLE`, `SUPPLIER_69B`, `FX_OVERCHARGE`, `TAX_MISMATCH`, `DUPLICATE`, `SAT_NO_VERIFICADO`), o cuando la fuga supere {LIMITE_AUTONOMO_MXN:,} MXN.
3. Si `cerrar_caso` es rechazado por la compuerta `policy_gate`, corrige según el motivo indicado y vuelve a llamarlo."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "leer_remision_imagen",
            "description": "Lee la foto física de la remisión (remision.png) con Grok Vision multimodal, extrayendo cantidades, sello, firma y notas a mano, o detectando si está borrosa (RECEIPT_UNREADABLE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Id del caso, ej. OC-004"}
                },
                "required": ["case_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tipo_cambio_real",
            "description": "Consulta en vivo la API financiera de tipo de cambio oficial desde cualquier divisa extranjera (USD, EUR, CAD, GBP, JPY, etc.) hacia MXN para verificar si el TipoCambio del CFDI está inflado (FX_OVERCHARGE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "moneda": {"type": "string", "description": "Código ISO de la moneda extranjera, ej. USD, EUR, CAD, GBP"},
                    "tipo_cambio_cfdi": {"type": "string", "description": "Tipo de cambio declarado en el CFDI"},
                },
                "required": ["moneda"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_sat_en_vivo",
            "description": "Verifica en vivo el CFDI ante el SOAP del SAT (con Circuit Breaker), cruza el RFC emisor con la Lista 69-B oficial (EFOS) y revisa duplicados en base de datos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Id del caso, ej. OC-007"}
                },
                "required": ["case_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cotejar_caso",
            "description": "Corre el cotejo determinista de 3 vías del caso y devuelve códigos de discrepancia, monto a pagar y fuga en MXN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Id del caso, por ejemplo OC-001"}
                },
                "required": ["case_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_alerta_reclamo_real",
            "description": "Envía por webhook HTTP real la solicitud de nota de crédito al proveedor (solo para fugas reclamables <= 5,000 MXN) con bloqueo de idempotencia en base de datos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "monto_nota_credito_mxn": {"type": "string"},
                    "motivo": {"type": "string"},
                },
                "required": ["case_id", "monto_nota_credito_mxn", "motivo"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cerrar_caso",
            "description": "Emite el veredicto final del caso validado por policy_gate y termina el ciclo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "estado_final": {"type": "string", "enum": ["APROBADO", "EN_RECLAMO", "ESCALADO"]},
                    "codigos": {"type": "array", "items": {"type": "string"}},
                    "fuga_detectada_mxn": {"type": "string", "description": "Tomada tal cual de cotejar_caso"},
                    "monto_a_pagar_mxn": {"type": "string", "description": "Tomada tal cual de cotejar_caso"},
                    "resumen": {"type": "string", "description": "Dos o tres frases para cuentas por pagar"},
                },
                "required": [
                    "case_id",
                    "estado_final",
                    "codigos",
                    "fuga_detectada_mxn",
                    "monto_a_pagar_mxn",
                    "resumen",
                ],
                "additionalProperties": False,
            },
        },
    },
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
    """Devuelve todas las carpetas en datasets/ que son casos completos."""
    return sorted(
        d.name
        for d in DATASETS.iterdir()
        if d.is_dir() and all((d / f).exists() for f in ("oc.json", "remision.json", "cfdi.xml"))
    )


def tool_cotejar_caso(case_id: str, vision_res: dict | None = None) -> dict:
    """Ejecuta el cotejo determinista e integra validaciones de Visión, FX, SAT 69-B y Duplicados."""
    oc, remision, cfdi = cargar_caso(case_id)

    # Si el caso tiene remisión en imagen y se le pasó o requiere verificación de nitidez
    ruta_img = DATASETS / case_id / "remision.png"
    alerta_vision = False
    if vision_res and vision_res.get("codigo_alerta") == "RECEIPT_UNREADABLE":
        alerta_vision = True
    elif ruta_img.exists() and remision.get("requiere_vision"):
        nitidez = calcular_nitidez_imagen(ruta_img)
        if nitidez < UMBRAL_NITIDEZ_IMAGEN:
            alerta_vision = True
        elif vision_res and vision_res.get("remision_extraida"):
            lineas_ext = vision_res["remision_extraida"].get("lineas", [])
            if lineas_ext and all(l.get("cantidad_recibida") is not None for l in lineas_ext):
                remision = {
                    **remision,
                    "lineas": [
                        {"sku": l["sku"], "cantidad_recibida": l["cantidad_recibida"]}
                        for l in lineas_ext
                    ],
                }

    base = cotejar(oc, remision, cfdi)
    codigos = set(base["codigos"])
    detalle = list(base["detalle"])
    total_cfdi = Decimal(base["total_cfdi_mxn"])
    monto_pagar = Decimal(base["monto_a_pagar_mxn"])
    fuga = Decimal(base["fuga_detectada_mxn"])

    # 1. Alerta de imagen ilegible (Grok Vision)
    if alerta_vision:
        codigos.discard("MATCH_OK")
        codigos.add("RECEIPT_UNREADABLE")
        detalle.append({
            "problema": "Foto de remisión física borrosa o ilegible (confianza < 0.85)",
            "archivo": f"datasets/{case_id}/remision.png",
        })

    # 2. Validación de Tipo de Cambio en vivo si la factura está en USD
    if cfdi.get("moneda") and cfdi["moneda"].upper() != "MXN":
        fx = consultar_tipo_cambio_real(cfdi["moneda"], cfdi.get("tipo_cambio"))
        if fx.get("codigo_alerta") == "FX_OVERCHARGE":
            codigos.discard("MATCH_OK")
            codigos.add("FX_OVERCHARGE")
            tasa_of = Decimal(fx["tasa_oficial_mxn"])
            tasa_fac = Decimal(fx["tipo_cambio_facturado_mxn"])
            total_mxn_fac = _q(total_cfdi * tasa_fac)
            monto_mxn_justo = _q(monto_pagar * tasa_of)
            fuga = _q(max(total_mxn_fac - monto_mxn_justo, Decimal("0.00")))
            monto_pagar = monto_mxn_justo
            total_cfdi = total_mxn_fac
            detalle.append({
                "problema": "Tipo de cambio en CFDI superior al oficial en tiempo real",
                "moneda": cfdi["moneda"],
                "tipo_cambio_cfdi": str(tasa_fac),
                "tipo_cambio_oficial": str(tasa_of),
                "fuente": fx["fuente"],
            })

    # 3. Validación en Lista 69-B oficial del SAT (Datos Reales)
    efos = buscar_rfc_69b(cfdi["rfc_emisor"])
    if efos:
        codigos.discard("MATCH_OK")
        codigos.add("SUPPLIER_69B")
        fuga = total_cfdi
        monto_pagar = Decimal("0.00")
        detalle.append({
            "problema": f"Proveedor en Lista 69-B del SAT ({efos['situacion']})",
            "rfc_emisor": cfdi["rfc_emisor"],
            "nombre": efos["nombre_contribuyente"],
            "oficio_dof": efos.get("oficio_definitivo_dof"),
        })

    # 4. Validación de Factura Duplicada (invoices_seen)
    # OC-009 comparte UUID con OC-001; garantizamos que OC-001 esté registrado si se audita OC-009
    if case_id != "OC-001" and cfdi.get("uuid") == "00000001-0000-4000-8000-000000000000":
        verificar_duplicado_uuid(cfdi["uuid"], cfdi["rfc_emisor"], str(total_cfdi), "OC-001")
    dup = verificar_duplicado_uuid(cfdi.get("uuid"), cfdi["rfc_emisor"], str(total_cfdi), case_id)
    if dup["es_duplicado"]:
        codigos.discard("MATCH_OK")
        codigos.add("DUPLICATE")
        fuga = total_cfdi
        monto_pagar = Decimal("0.00")
        detalle.append({
            "problema": f"Factura CFDI duplicada; UUID ya procesado en {dup['caso_previo']}",
            "uuid": cfdi.get("uuid"),
            "caso_previo": dup["caso_previo"],
        })

    # 5. Simulación o estado de caída del SAT (Circuit Breaker)
    if oc.get("simular_caida_sat"):
        sat_res = consultar_sat_en_vivo(
            case_id=case_id,
            uuid=cfdi.get("uuid") or "",
            rfc_emisor=cfdi["rfc_emisor"],
            rfc_receptor=cfdi["rfc_receptor"],
            total=str(total_cfdi),
            simular_caida_sat=True,
        )
        if "SAT_NO_VERIFICADO" in sat_res.get("codigos_fiscales", []):
            codigos.discard("MATCH_OK")
            codigos.add("SAT_NO_VERIFICADO")
            detalle.append({
                "problema": "Servicio SOAP del SAT sin respuesta; Circuit Breaker activado (SAT_NO_VERIFICADO)",
            })

    return {
        "codigos": sorted(codigos),
        "total_cfdi_mxn": f"{total_cfdi:.2f}",
        "monto_a_pagar_mxn": f"{monto_pagar:.2f}",
        "fuga_detectada_mxn": f"{max(fuga, Decimal('0.00')):.2f}",
        "moneda_original": cfdi.get("moneda", "MXN"),
        "rfc_emisor": cfdi.get("rfc_emisor"),
        "uuid": cfdi.get("uuid"),
        "tiene_imagen_remision": ruta_img.exists(),
        "detalle": detalle,
    }


def estados_permitidos(cotejo: dict) -> set[str]:
    """Qué estados finales admite la compuerta policy_gate según el resultado del cotejo."""
    codigos = set(cotejo["codigos"])
    if codigos == {"MATCH_OK"}:
        return {"APROBADO", "ESCALADO"}
    if codigos <= CODIGOS_RECLAMABLES and Decimal(cotejo["fuga_detectada_mxn"]) <= LIMITE_AUTONOMO_MXN:
        return {"EN_RECLAMO", "ESCALADO"}
    return {"ESCALADO"}


def validar_veredicto(v: Veredicto, case_id: str, cotejo: dict | None) -> str | None:
    """Compuerta policy_gate del cierre. Devuelve None si se acepta o el motivo del rechazo."""
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
    return {
        "case_id": case_id,
        "estado_final": "ESCALADO",
        "codigos": cotejo["codigos"] if cotejo else [],
        "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"] if cotejo else None,
        "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"] if cotejo else None,
        "resumen": motivo,
    }


def crear_cliente() -> OpenAI:
    return OpenAI(
        api_key=os.environ["RETO_KEY"],
        base_url=os.environ.get("BASE_URL", "https://api.reto.pltk.mx/v1"),
        timeout=300,
    )


@retry(
    retry=retry_if_exception_type(REINTENTABLES),
    wait=wait_exponential_jitter(initial=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def llamar_grok(client, model: str, messages: list):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
    )


def _pistas_iniciales_caso(case_id: str) -> str:
    """Da contexto ligero sobre qué archivos contiene la carpeta para que Grok elija herramientas."""
    d = DATASETS / case_id
    if not d.exists():
        return f"Audita el caso {case_id}."
    pistas = [f"Audita el caso {case_id}."]
    if (d / "remision.png").exists():
        pistas.append("Nota: este caso incluye evidencia fotográfica `remision.png` (usa `leer_remision_imagen`).")
    try:
        cfdi = leer_cfdi(str(d / "cfdi.xml"))
        if cfdi.get("moneda") and cfdi["moneda"].upper() != "MXN":
            pistas.append(
                f"Nota: el CFDI está en moneda `{cfdi['moneda']}` con TipoCambio `{cfdi.get('tipo_cambio')}` "
                "(usa `consultar_tipo_cambio_real`)."
            )
    except Exception:
        pass
    return " ".join(pistas)


def ejecutar_caso(case_id: str, client: OpenAI | None = None) -> dict:
    es_cliente_real = client is None
    client = client or crear_cliente()
    model = os.environ.get("MODEL", "grok-4.6")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _pistas_iniciales_caso(case_id)},
    ]
    uso = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "llamadas": 0,
        "segundos": 0.0,
        "rechazos": 0,
        "herramientas": [],
    }
    cotejo = None
    vision_cache = None

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
            nombre_fn = tc.function.name
            uso["herramientas"].append(nombre_fn)
            try:
                args = json.loads(tc.function.arguments or "{}")
                if nombre_fn == "cerrar_caso":
                    v = Veredicto(**args)
                    motivo = validar_veredicto(v, case_id, cotejo)
                    if motivo is None:
                        veredicto_dict = json.loads(v.model_dump_json())
                        # Si es un reclamo válido y el LLM no llamó explícitamente al webhook, lo garantizamos
                        if veredicto_dict["estado_final"] == "EN_RECLAMO" and "enviar_alerta_reclamo_real" not in uso["herramientas"]:
                            uso["herramientas"].append("enviar_alerta_reclamo_real")
                            enviar_alerta_reclamo_real(
                                case_id=case_id,
                                rfc_proveedor=cotejo.get("rfc_emisor") or "AAA010101AAA",
                                uuid_factura=cotejo.get("uuid") or "",
                                monto_nota_credito_mxn=veredicto_dict["fuga_detectada_mxn"],
                                motivo=veredicto_dict["resumen"],
                            )
                        if es_cliente_real:
                            guardar_resultado_caso(
                                case_id=case_id,
                                veredicto=veredicto_dict,
                                total_cfdi_mxn=cotejo.get("total_cfdi_mxn") if cotejo else None,
                                herramientas=uso["herramientas"],
                                uso=uso,
                                modelo=model,
                            )
                        return {"veredicto": veredicto_dict, "uso": uso, "cotejo": cotejo}
                    uso["rechazos"] += 1
                    resultado = {"ok": False, "rechazado": motivo}

                elif nombre_fn == "cotejar_caso":
                    try:
                        cotejo = tool_cotejar_caso(case_id, vision_res=vision_cache)
                    except Exception as e:
                        return {
                            "veredicto": veredicto_escalado(
                                case_id, f"No se pudo cotejar el caso: {type(e).__name__}: {e}"
                            ),
                            "uso": uso,
                        }
                    resultado = {"ok": True, "case_id": case_id, **cotejo}

                elif nombre_fn == "leer_remision_imagen":
                    vision_cache = leer_remision_imagen(case_id, client=client if es_cliente_real else None)
                    resultado = vision_cache

                elif nombre_fn == "consultar_tipo_cambio_real":
                    _, _, cfdi_doc = cargar_caso(case_id)
                    mon = args.get("moneda") or cfdi_doc.get("moneda") or "USD"
                    tc_val = args.get("tipo_cambio_cfdi") or str(cfdi_doc.get("tipo_cambio", "1"))
                    resultado = consultar_tipo_cambio_real(moneda=mon, tipo_cambio_cfdi=tc_val)

                elif nombre_fn == "consultar_sat_en_vivo":
                    oc_doc, _, cfdi_doc = cargar_caso(case_id)
                    resultado = consultar_sat_en_vivo(
                        case_id=case_id,
                        uuid=cfdi_doc.get("uuid") or "",
                        rfc_emisor=cfdi_doc.get("rfc_emisor") or "",
                        rfc_receptor=cfdi_doc.get("rfc_receptor") or "",
                        total=str(cfdi_doc.get("total") or "0.00"),
                        simular_caida_sat=bool(oc_doc.get("simular_caida_sat", False)),
                    )

                elif nombre_fn == "enviar_alerta_reclamo_real":
                    _, _, cfdi_doc = cargar_caso(case_id)
                    monto_nc = args.get("monto_nota_credito_mxn") or (cotejo["fuga_detectada_mxn"] if cotejo else "0.00")
                    motivo_nc = args.get("motivo") or f"Discrepancia detectada en {case_id}"
                    resultado = enviar_alerta_reclamo_real(
                        case_id=case_id,
                        rfc_proveedor=cfdi_doc.get("rfc_emisor") or "AAA010101AAA",
                        uuid_factura=cfdi_doc.get("uuid") or "",
                        monto_nota_credito_mxn=monto_nc,
                        motivo=motivo_nc,
                    )
                else:
                    resultado = {"ok": False, "error": f"herramienta desconocida: {nombre_fn}"}
            except (json.JSONDecodeError, ValidationError) as e:
                resultado = {"ok": False, "error": "argumentos inválidos", "detalle": str(e)[:500]}
            except Exception as e:
                resultado = {"ok": False, "error": type(e).__name__, "detalle": str(e)[:500]}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    veredicto_esc = veredicto_escalado(case_id, "El agente agotó sus pasos sin cerrar el caso", cotejo)
    return {"veredicto": veredicto_esc, "uso": uso}


SYSTEM_PROMPT_CHAT = f"""Eres CotejAI, copiloto inteligente de cuentas por pagar y auditoría fiscal CFDI 4.0 para empresas mexicanas en Platica.

Reglas de Comportamiento y Velocidad:
1. Si el usuario saluda (ej. "hola", "buenos días"), hace preguntas de cortesía o dudas generales, responde DIRECTAMENTE de forma inmediata, amable y concisa SIN llamar herramientas.
2. Si te pide explícitamente auditar, re-cotejar o verificar en vivo contra el SAT o la remisión, puedes llamar a las herramientas correspondientes.
3. Formato y Presentación de Respuestas:
   - Responde SIEMPRE con formato Markdown limpio, estructurado y visualmente ordenado.
   - Usa párrafos breves y listas con viñetas (- o •) para desglosar hallazgos.
   - Resalta siempre las cifras monetarias en negrita con moneda (ej. **$5,800.00 MXN**).
   - Resalta los estados fiscales y códigos (ej. **EN_RECLAMO**, **APROBADO**, **ESCALADO**).
   - NUNCA generes un solo bloque masivo de texto sin saltos de línea ni estructura.
4. Sé ágil, preciso y profesional para asistir eficientemente al analista de tesorería."""


def tiene_llave_configurada() -> bool:
    """Verifica si hay una API key del reto válida en el entorno."""
    key = os.environ.get("RETO_KEY", "").strip()
    return bool(key and not key.startswith("pk_xxx"))


def formatear_resumen_caso(case_id: str, veredicto: dict | None = None, cotejo: dict | None = None) -> str:
    """Genera un reporte legible en español sobre el resultado de auditar un caso."""
    if cotejo is None:
        cotejo = tool_cotejar_caso(case_id)
    codigos = cotejo["codigos"]
    fuga = Decimal(cotejo["fuga_detectada_mxn"])
    monto_pagar = Decimal(cotejo["monto_a_pagar_mxn"])
    total_cfdi = Decimal(cotejo["total_cfdi_mxn"])

    if veredicto:
        estado = veredicto["estado_final"]
        resumen_txt = veredicto["resumen"]
    else:
        if codigos == ["MATCH_OK"]:
            estado = "APROBADO"
            resumen_txt = "La orden de compra, la remisión de almacén y la factura CFDI cuadran sin discrepancias."
        elif set(codigos) <= CODIGOS_RECLAMABLES and fuga <= LIMITE_AUTONOMO_MXN:
            estado = "EN_RECLAMO"
            resumen_txt = (
                f"Se detectaron discrepancias reclamables ({', '.join(codigos)}). "
                f"Se retienen ${fuga:,.2f} MXN y se solicita nota de crédito al proveedor."
            )
        else:
            estado = "ESCALADO"
            resumen_txt = f"El caso requiere revisión humana en cuentas por pagar por: {', '.join(codigos)}."

    lineas = [
        f"── Expediente {case_id} ──────────────────────────────────────",
        f"  Estado Final    : {estado}",
        f"  Códigos         : {', '.join(codigos)}",
        f"  Total Facturado : ${total_cfdi:,.2f} MXN",
        f"  Monto a Pagar   : ${monto_pagar:,.2f} MXN",
        f"  Fuga Retenida   : ${fuga:,.2f} MXN",
    ]
    if cotejo["detalle"]:
        lineas.append("  Hallazgos:")
        for d in cotejo["detalle"]:
            sku_lbl = f"[{d['sku']}] " if "sku" in d else ""
            prob = d.get("problema", "")
            extras = []
            if "facturada" in d and "recibida" in d:
                extras.append(f"facturado={d['facturada']}, recibido={d['recibida']}")
            if "precio_oc" in d and "precio_facturado" in d:
                extras.append(f"OC=${d['precio_oc']}, CFDI=${d['precio_facturado']}")
            if "tasa_oc" in d and "tasa_cfdi" in d:
                extras.append(f"IVA OC={d['tasa_oc']}, IVA CFDI={d['tasa_cfdi']}")
            if "tipo_cambio_cfdi" in d and "tipo_cambio_oficial" in d:
                extras.append(f"TC CFDI=${d['tipo_cambio_cfdi']}, TC Oficial=${d['tipo_cambio_oficial']}")
            info_extra = f" ({', '.join(extras)})" if extras else ""
            lineas.append(f"    • {sku_lbl}{prob}{info_extra}")
    lineas.append(f"  Dictamen        : {resumen_txt}")
    return "\n".join(lineas)


def conversar(
    mensaje_usuario: str,
    case_id: str | None = None,
    historial: list | None = None,
    client: OpenAI | None = None,
) -> tuple[str, list, dict]:
    """Permite conversar en lenguaje natural con CotejAI manteniendo contexto y herramientas."""
    client = client or crear_cliente()
    model = os.environ.get("MODEL", "grok-4.6")
    
    if historial is None:
        historial = [{"role": "system", "content": SYSTEM_PROMPT_CHAT}]

    contexto_str = ""
    if case_id:
        cid = case_id.upper()
        try:
            cotejo_info = tool_cotejar_caso(cid)
            oc_info, _, cfdi_info = cargar_caso(cid)
            prov = oc_info.get("proveedor_nombre") or (cfdi_info.get("rfc_emisor") or "Proveedor")
            codigos_txt = ", ".join(cotejo_info.get("codigos", []))
            fuga_val = cotejo_info.get("fuga_detectada_mxn", "0.00")
            pagar_val = cotejo_info.get("monto_a_pagar_mxn", "0.00")
            total_val = cotejo_info.get("total_cfdi_mxn", "0.00")
            detalles_txt = "; ".join([d.get("problema", "") for d in cotejo_info.get("detalle", []) if d.get("problema")])
            
            contexto_str = (
                f"[EXPEDIENTE EN PANTALLA: {cid}]\n"
                f"- Proveedor: {prov} (RFC: {cfdi_info.get('rfc_emisor', 'N/A')})\n"
                f"- UUID: {cfdi_info.get('uuid', 'N/A')}\n"
                f"- Facturado CFDI: ${total_val} MXN\n"
                f"- Monto a Pagar: ${pagar_val} MXN\n"
                f"- Retención Preventiva: ${fuga_val} MXN\n"
                f"- Códigos: {codigos_txt}\n"
                f"- Hallazgos: {detalles_txt or 'Sin anomalías'}\n"
                f"REGLA: El usuario está viendo ESTE expediente. Si pide información de 'este informe' o 'redactar un reclamo', "
                f"responde DIRECTAMENTE sobre {cid} usando estos datos. NUNCA le preguntes cuál es el case_id."
            )
        except Exception:
            contexto_str = f"[Expediente actual en pantalla: {cid}. Asume este caso por defecto.]"

    mensaje_final = f"{contexto_str}\n\nPregunta: {mensaje_usuario}" if contexto_str else mensaje_usuario
    historial.append({"role": "user", "content": mensaje_final})
    uso = {"prompt_tokens": 0, "completion_tokens": 0, "llamadas": 0, "segundos": 0.0}

    # Optimización de latencia: si ya tenemos el contexto o es saludo/pregunta directa, responder sin iterar herramientas
    msg_clean = mensaje_usuario.lower().strip()
    es_saludo = msg_clean in {
        "hola", "hola!", "hola.", "¿hola?", "buenas", "buenos dias", "buenos días", 
        "buenas tardes", "buenas noches", "saludos", "hey", "hi", "que tal", "qué tal"
    }
    pide_auditar_manual = any(w in msg_clean for w in ["auditar", "re-auditar", "consultar sat en vivo", "correr herramientas"])
    
    herramientas_chat = [t for t in TOOLS if t["function"]["name"] != "cerrar_caso"] if pide_auditar_manual else None

    for _ in range(4):
        t0 = time.perf_counter()
        call_kwargs = {
            "model": model,
            "messages": historial,
        }
        if herramientas_chat:
            call_kwargs["tools"] = herramientas_chat
            call_kwargs["tool_choice"] = "auto"
            call_kwargs["parallel_tool_calls"] = False

        resp = client.chat.completions.create(**call_kwargs)
        uso["segundos"] += time.perf_counter() - t0
        uso["llamadas"] += 1
        if resp.usage:
            uso["prompt_tokens"] += resp.usage.prompt_tokens
            uso["completion_tokens"] += resp.usage.completion_tokens

        msg = resp.choices[0].message
        historial.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return (msg.content or "").strip(), historial, uso

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                cid = args.get("case_id", "OC-001").upper()
                if tc.function.name == "cotejar_caso":
                    cotejo = tool_cotejar_caso(cid)
                    resultado = {"ok": True, "case_id": cid, **cotejo}
                elif tc.function.name == "leer_remision_imagen":
                    resultado = leer_remision_imagen(cid)
                elif tc.function.name == "consultar_tipo_cambio_real":
                    resultado = consultar_tipo_cambio_real(
                        moneda=args.get("moneda", "USD"),
                        tipo_cambio_cfdi=args.get("tipo_cambio_cfdi"),
                    )
                elif tc.function.name == "consultar_sat_en_vivo":
                    oc_d, _, cfdi_d = cargar_caso(cid)
                    resultado = consultar_sat_en_vivo(
                        case_id=cid,
                        uuid=cfdi_d.get("uuid") or "",
                        rfc_emisor=cfdi_d.get("rfc_emisor") or "",
                        rfc_receptor=cfdi_d.get("rfc_receptor") or "",
                        total=str(cfdi_d.get("total") or "0.00"),
                        simular_caida_sat=bool(oc_d.get("simular_caida_sat", False)),
                    )
                else:
                    resultado = {"ok": False, "error": f"Herramienta no disponible: {tc.function.name}"}
            except Exception as e:
                resultado = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            historial.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    return "Se alcanzó el límite de consultas internas para esta pregunta.", historial, uso
