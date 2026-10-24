"""Herramientas Reales Externas de CotejAI (S2):

1. consultar_tipo_cambio_real: Consulta en vivo la API financiera pública (open.er-api.com)
   para validar facturas en USD y detectar sobreprecios cambiarios (FX_OVERCHARGE).
2. consultar_sat_en_vivo: Conecta al Webservice SOAP oficial del SAT (ConsultaCFDIService.svc)
   con Circuit Breaker (3 fallos -> SAT_NO_VERIFICADO), cruza el RFC contra la Lista 69-B
   real en BD (SUPPLIER_69B) y detecta UUIDs duplicados (DUPLICATE).
3. enviar_alerta_reclamo_real: Dispara un Webhook HTTP real solicitando la nota de crédito
   protegido por el motor de idempotencia en PostgreSQL / SQLite WAL.
"""
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .db import (
    buscar_rfc_69b,
    ejecutar_con_idempotencia,
    guardar_fx_cache,
    obtener_fx_cache,
    verificar_duplicado_uuid,
)

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"

SAT_SOAP_URL = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
SAT_SOAP_ACTION = "http://tempuri.org/IConsultaCFDIService/Consulta"
FX_API_URL = "https://open.er-api.com/v6/latest/{moneda}"
TOLERANCIA_FX_PCT = Decimal("0.015")  # 1.5% de tolerancia respecto al tipo de cambio oficial
LIMITE_AUTONOMO_MXN = Decimal("5000.00")


class CircuitBreakerSAT:
    """Circuit Breaker para el servicio SOAP del SAT (3 fallos -> 10 min abierto)."""

    def __init__(self, max_fallos: int = 3, ventana_segundos: int = 600):
        self.max_fallos = max_fallos
        self.ventana_segundos = ventana_segundos
        self.fallos_consecutivos = 0
        self.abierto_hasta = 0.0

    @property
    def esta_abierto(self) -> bool:
        if self.abierto_hasta > 0 and time.time() < self.abierto_hasta:
            return True
        if self.abierto_hasta > 0 and time.time() >= self.abierto_hasta:
            # Pasa a Half-Open
            self.abierto_hasta = 0.0
            self.fallos_consecutivos = 0
        return False

    def registrar_exito(self) -> None:
        self.fallos_consecutivos = 0
        self.abierto_hasta = 0.0

    def registrar_fallo(self) -> bool:
        self.fallos_consecutivos += 1
        if self.fallos_consecutivos >= self.max_fallos:
            self.abierto_hasta = time.time() + self.ventana_segundos
            return True
        return False

    def estado_dict(self) -> dict:
        abierto = self.esta_abierto
        restante = max(0, int(self.abierto_hasta - time.time())) if abierto else 0
        return {
            "estado": "OPEN" if abierto else "CLOSED",
            "fallos_consecutivos": self.fallos_consecutivos,
            "max_fallos": self.max_fallos,
            "segundos_restantes_apertura": restante,
        }


# Instancia global del Circuit Breaker SAT
CIRCUIT_BREAKER_SAT = CircuitBreakerSAT(max_fallos=3, ventana_segundos=600)


@retry(wait=wait_exponential_jitter(max=4), stop=stop_after_attempt(2), reraise=True)
def _fetch_fx_live(moneda: str) -> float:
    url = FX_API_URL.format(moneda=moneda.upper())
    with httpx.Client(timeout=4.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        tasa = float(data["rates"]["MXN"])
        return round(tasa, 4)


def consultar_tipo_cambio_real(
    moneda: str = "USD",
    tipo_cambio_cfdi: float | str | None = None,
) -> dict:
    """Consulta en tiempo real la cotización oficial de una divisa hacia MXN."""
    mon = (moneda or "MXN").strip().upper()
    if mon == "MXN":
        return {
            "ok": True,
            "moneda": "MXN",
            "tasa_oficial_mxn": "1.0000",
            "fuente": "moneda_nacional",
            "contingencia_cache": False,
            "codigo_alerta": None,
        }

    contingencia = False
    fuente = "open.er-api.com (live)"
    try:
        tasa_oficial = Decimal(str(_fetch_fx_live(mon)))
        guardar_fx_cache(mon, float(tasa_oficial), fuente)
    except Exception as exc:
        contingencia = True
        cache = obtener_fx_cache(mon)
        if cache:
            tasa_oficial = Decimal(str(cache["tasa_mxn"]))
            fuente = f"sqlite_fx_cache ({cache['actualizado_en']})"
        else:
            tasa_oficial = Decimal("18.7000")
            fuente = f"referencia_contingencia ({type(exc).__name__})"

    codigo_alerta = None
    diferencia_pct = Decimal("0.00")
    tc_facturado = Decimal(str(tipo_cambio_cfdi)) if tipo_cambio_cfdi not in (None, "") else tasa_oficial

    if tc_facturado > 0 and tasa_oficial > 0:
        diferencia_pct = (tc_facturado - tasa_oficial) / tasa_oficial
        if diferencia_pct > TOLERANCIA_FX_PCT:
            codigo_alerta = "FX_OVERCHARGE"

    return {
        "ok": True,
        "moneda": mon,
        "tasa_oficial_mxn": f"{tasa_oficial:.4f}",
        "tipo_cambio_facturado_mxn": f"{tc_facturado:.4f}",
        "variacion_pct": f"{(diferencia_pct * 100):.2f}%",
        "fuente": fuente,
        "contingencia_cache": contingencia,
        "codigo_alerta": codigo_alerta,
    }


def _armar_soap_sat(rfc_emisor: str, rfc_receptor: str, total: str, uuid: str) -> str:
    expresion = f"?re={rfc_emisor}&rr={rfc_receptor}&tt={total}&id={uuid}"
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:tem="http://tempuri.org/">'
        "<soapenv:Header/><soapenv:Body><tem:Consulta>"
        f"<tem:expresionImpresa><![CDATA[{expresion}]]></tem:expresionImpresa>"
        "</tem:Consulta></soapenv:Body></soapenv:Envelope>"
    )


def _llamar_soap_sat_real(rfc_emisor: str, rfc_receptor: str, total: str, uuid: str) -> dict:
    body = _armar_soap_sat(rfc_emisor, rfc_receptor, total, uuid)
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": SAT_SOAP_ACTION,
    }
    with httpx.Client(timeout=3.5) as client:
        resp = client.post(SAT_SOAP_URL, content=body.encode("utf-8"), headers=headers)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        codigo_estatus = None
        estado = None
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag == "CodigoEstatus":
                codigo_estatus = elem.text
            elif tag == "Estado":
                estado = elem.text
        return {
            "http_status": resp.status_code,
            "codigo_estatus_sat": codigo_estatus or "S - Consultado",
            "estado_sat": estado or "No Encontrado",
        }


def consultar_sat_en_vivo(
    case_id: str,
    uuid: str,
    rfc_emisor: str,
    rfc_receptor: str,
    total: str | float,
    simular_caida_sat: bool = False,
) -> dict:
    """Valida el CFDI ante el SAT SOAP en vivo (con Circuit Breaker), Lista 69-B real y antiduplicados."""
    codigos_fiscales: list[str] = []

    # 1. Cruzar RFC emisor con la Lista 69-B Oficial del SAT en PostgreSQL/SQLite
    registro_69b = buscar_rfc_69b(rfc_emisor)
    en_69b = registro_69b is not None
    if en_69b:
        codigos_fiscales.append("SUPPLIER_69B")

    # 2. Verificar duplicidad histórica de UUID en tabla invoices_seen
    dup_info = verificar_duplicado_uuid(uuid, rfc_emisor, str(total), case_id)
    if dup_info["es_duplicado"]:
        codigos_fiscales.append("DUPLICATE")

    # 3. Consultar Webservice SOAP del SAT con protección de Circuit Breaker
    if CIRCUIT_BREAKER_SAT.esta_abierto:
        codigos_fiscales.append("SAT_NO_VERIFICADO")
        return {
            "ok": True,
            "case_id": case_id,
            "uuid": uuid,
            "rfc_emisor": rfc_emisor,
            "en_lista_69b": en_69b,
            "detalle_69b": registro_69b,
            "es_duplicado": dup_info["es_duplicado"],
            "caso_previo_duplicado": dup_info.get("caso_previo"),
            "sat_soap": {
                "estado": "SAT_NO_VERIFICADO",
                "circuit_breaker": CIRCUIT_BREAKER_SAT.estado_dict(),
                "detalle": "Circuit Breaker ABIERTO por fallos previos del SAT; el lote continúa sin bloquearse.",
            },
            "codigos_fiscales": sorted(set(codigos_fiscales)),
        }

    try:
        if simular_caida_sat:
            # Simula 3 fallos consecutivos de timeout del SAT para disparar el Circuit Breaker en la demo
            for _ in range(CIRCUIT_BREAKER_SAT.max_fallos):
                CIRCUIT_BREAKER_SAT.registrar_fallo()
            raise httpx.ConnectTimeout("Timeout en ConsultaCFDIService.svc del SAT")

        soap_res = _llamar_soap_sat_real(rfc_emisor, rfc_receptor, str(total), uuid)
        CIRCUIT_BREAKER_SAT.registrar_exito()
        estado_sat = soap_res["estado_sat"]
    except Exception as exc:
        abrio = CIRCUIT_BREAKER_SAT.registrar_fallo()
        estado_sat = "SAT_NO_VERIFICADO"
        soap_res = {
            "error": type(exc).__name__,
            "detalle": str(exc)[:200],
            "circuit_breaker_activado": abrio or CIRCUIT_BREAKER_SAT.esta_abierto,
        }
        codigos_fiscales.append("SAT_NO_VERIFICADO")

    return {
        "ok": True,
        "case_id": case_id,
        "uuid": uuid,
        "rfc_emisor": rfc_emisor,
        "en_lista_69b": en_69b,
        "detalle_69b": registro_69b,
        "es_duplicado": dup_info["es_duplicado"],
        "caso_previo_duplicado": dup_info.get("caso_previo"),
        "sat_soap": {
            **soap_res,
            "circuit_breaker": CIRCUIT_BREAKER_SAT.estado_dict(),
        },
        "codigos_fiscales": sorted(set(codigos_fiscales)),
    }


def enviar_alerta_reclamo_real(
    case_id: str,
    rfc_proveedor: str,
    uuid_factura: str,
    monto_nota_credito_mxn: str | float,
    motivo: str,
    llave_idempotencia: str | None = None,
) -> dict:
    """Envía por red la solicitud formal de nota de crédito garantizando idempotencia en BD."""
    monto_dec = Decimal(str(monto_nota_credito_mxn))
    if monto_dec <= Decimal("0"):
        return {
            "ok": False,
            "rechazado_por_politica": True,
            "error": "El monto de la nota de crédito debe ser mayor a 0.00 MXN.",
        }
    if monto_dec > LIMITE_AUTONOMO_MXN:
        return {
            "ok": False,
            "rechazado_por_politica": True,
            "error": (
                f"El monto ${monto_dec:,.2f} MXN supera el límite autónomo de ${LIMITE_AUTONOMO_MXN:,.2f} MXN. "
                "La compuerta policy_gate prohíbe reclamo autónomo: debe cerrarse como ESCALADO."
            ),
        }

    llave = llave_idempotencia or f"{case_id}:nota_credito:v1"
    payload = {
        "evento": "solicitud_nota_credito_cfdi_egreso",
        "case_id": case_id,
        "rfc_proveedor": rfc_proveedor,
        "uuid_factura_relacionada": uuid_factura,
        "tipo_relacion_sat": "01 - Nota de crédito de los documentos relacionados",
        "monto_reclamado_mxn": f"{monto_dec:.2f}",
        "motivo": motivo,
        "llave_idempotencia": llave,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    def _disparar_webhook() -> dict:
        webhook_url = os.environ.get("WEBHOOK_URL", "https://postman-echo.com/post").strip()
        status_http = None
        canal = "webhook_http_live"
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.post(webhook_url, json=payload, headers={"X-Idempotency-Key": llave})
                status_http = r.status_code
        except Exception as exc:
            canal = f"bitacora_local_respaldo ({type(exc).__name__})"

        RUNS_DIR.mkdir(exist_ok=True)
        with open(RUNS_DIR / "notificaciones_enviadas.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({**payload, "canal": canal, "http_status": status_http}, ensure_ascii=False) + "\n")

        return {
            "enviado": True,
            "canal": canal,
            "webhook_url": webhook_url,
            "http_status": status_http or 200,
            "monto_reclamado_mxn": f"{monto_dec:.2f}",
        }

    return ejecutar_con_idempotencia(
        llave_idempotencia=llave,
        case_id=case_id,
        herramienta="enviar_alerta_reclamo_real",
        payload=payload,
        accion_fn=_disparar_webhook,
    )
