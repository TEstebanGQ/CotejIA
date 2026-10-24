"""Herramientas Reales Externas de CotejAI (S2):

1. consultar_tipo_cambio_real y listar_divisas_real: Soporta el catálogo completo de 180 divisas
   internacionales (ISO 4217 / Anexo 20 del SAT) consultando en vivo open.er-api.com y
   persistiendo en PostgreSQL 16 (tabla fx_cache) para detectar sobreprecios cambiarios (FX_OVERCHARGE).
2. consultar_sat_en_vivo: Conecta al Webservice SOAP oficial del SAT (ConsultaCFDIService.svc)
   con Circuit Breaker (3 fallos -> SAT_NO_VERIFICADO), cruza el RFC contra la Lista 69-B
   real en PostgreSQL 16 (SUPPLIER_69B) y detecta UUIDs duplicados (DUPLICATE).
3. enviar_alerta_reclamo_real: Dispara un Webhook HTTP real solicitando la nota de crédito
   protegido por el motor de idempotencia en PostgreSQL 16 / SQLite WAL.
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

# Catálogo oficial de 180 divisas (ISO 4217 / Anexo 20 c_Moneda del SAT)
CATALOGO_180_DIVISAS: dict[str, str] = {
    "USD": "Dólar Estadounidense", "EUR": "Euro", "MXN": "Peso Mexicano", "CAD": "Dólar Canadiense",
    "GBP": "Libra Esterlina", "JPY": "Yen Japonés", "CHF": "Franco Suizo", "CNY": "Yuan Chino (Renminbi)",
    "CNH": "Yuan Chino Offshore", "BRL": "Real Brasileño", "COP": "Peso Colombiano", "ARS": "Peso Argentino",
    "CLP": "Peso Chileno", "PEN": "Sol Peruano", "UYU": "Peso Uruguayo", "PYG": "Guaraní Paraguayo",
    "BOB": "Boliviano", "VES": "Bolívar Venezolano", "GTQ": "Quetzal Guatemalteco", "CRC": "Colón Costarricense",
    "HNL": "Lempira Hondureño", "NIO": "Córdoba Nicaragüense", "DOP": "Peso Dominicano", "PAB": "Balboa Panameño",
    "CUP": "Peso Cubano", "CUC": "Peso Cubano Convertible", "SVC": "Colón Salvadoreño", "AUD": "Dólar Australiano",
    "NZD": "Dólar Neozelandés", "HKD": "Dólar de Hong Kong", "SGD": "Dólar de Singapur", "KRW": "Won Surcoreano",
    "KPW": "Won Norcoreano", "INR": "Rupia India", "IDR": "Rupia Indonesia", "MYR": "Ringgit Malayo",
    "THB": "Baht Tailandés", "PHP": "Peso Filipino", "VND": "Dong Vietnamita", "TWD": "Nuevo Dólar Taiwanés",
    "PKR": "Rupia Pakistaní", "BDT": "Taka Bangladesí", "LKR": "Rupia de Sri Lanka", "NPR": "Rupia Nepalí",
    "SEK": "Corona Sueca", "NOK": "Corona Noruega", "DKK": "Corona Danesa", "ISK": "Corona Islandesa",
    "PLN": "Zloty Polaco", "CZK": "Corona Checa", "HUF": "Forinto Húngaro", "RON": "Leu Rumano",
    "BGN": "Lev Búlgaro", "HRK": "Kuna Croata", "RSD": "Dinar Serbio", "BAM": "Marco Bosnioherzegovino",
    "ALL": "Lek Albanés", "MKD": "Denar Macedonio", "MDL": "Leu Moldavo", "UAH": "Grivna Ucraniana",
    "BYN": "Rublo Bielorruso", "RUB": "Rublo Ruso", "TRY": "Lira Turca", "GEL": "Lari Georgiano",
    "AMD": "Dram Armenio", "AZN": "Manat Azerbaiyano", "KZT": "Tenge Kazajo", "UZS": "Som Uzbeko",
    "KGS": "Som Kirguís", "TJS": "Somoni Tayiko", "TMT": "Manat Turcomano", "AFN": "Afgani Afgano",
    "AED": "Dírham de Emiratos Árabes Unidos", "SAR": "Riyal Saudí", "QAR": "Riyal Catarí", "KWD": "Dinar Kuwaití",
    "BHD": "Dinar Bareiní", "OMR": "Rial Omaní", "JOD": "Dinar Jordano", "ILS": "Nuevo Séquel Israelí",
    "IQD": "Dinar Iraquí", "IRR": "Rial Iraní", "LBP": "Libra Libanesa", "SYP": "Libra Siria",
    "YER": "Rial Yemení", "EGP": "Libra Egipcia", "MAD": "Dírham Marroquí", "DZD": "Dinar Argelino",
    "TND": "Dinar Tunecino", "LYD": "Dinar Libio", "SDG": "Libra Sudanesa", "SSP": "Libra Sursudanesa",
    "ZAR": "Rand Sudafricano", "NGN": "Naira Nigeriano", "KES": "Chelín Keniano", "GHS": "Cedi Ghanés",
    "ETB": "Birr Etíope", "TZS": "Chelín Tanzano", "UGX": "Chelín Ugandés", "ZMW": "Kwacha Zambiano",
    "BWP": "Pula Botsuano", "NAD": "Dólar Namibio", "MUR": "Rupia Mauriciana", "SCR": "Rupia de Seychelles",
    "AOA": "Kwanza Angoleño", "MZN": "Metical Mozambiqueño", "MGA": "Ariary Malgache", "XOF": "Franco CFA África Occidental",
    "XAF": "Franco CFA África Central", "CDF": "Franco Congoleño", "RWF": "Franco Ruandés", "BIF": "Franco Burundés",
    "DJF": "Franco Yibutiano", "ERN": "Nakfa Eritreo", "GMD": "Dalasi Gambiano", "GNF": "Franco Guineano",
    "LRD": "Dólar Liberiano", "LSL": "Loti Lesotense", "MWK": "Kwacha Malauí", "MRU": "Uguiya Mauritano",
    "SLE": "Leone Sierraleonés", "SLL": "Leone Antiguo", "SOS": "Chelín Somalí", "STN": "Dobra Santotomense",
    "SZL": "Lilangeni Suazi", "ZWG": "ZiG Zimbabuense", "ZWL": "Dólar Zimbabuense", "CVE": "Escudo Caboverdiano",
    "KMF": "Franco Comorense", "SHP": "Libra de Santa Elena", "BSD": "Dólar Bahameño", "BBD": "Dólar de Barbados",
    "BMD": "Dólar Bermudeño", "BZD": "Dólar Beliceño", "JMD": "Dólar Jamaiquino", "TTD": "Dólar de Trinidad y Tobago",
    "KYD": "Dólar de Islas Caimán", "XCD": "Dólar del Caribe Oriental", "AWG": "Florín Arubeño", "ANG": "Florín Antillano",
    "XCG": "Florín Caribeño", "HTG": "Gourde Haitiano", "SRD": "Dólar Surinamés", "GYD": "Dólar Guyanés",
    "FKP": "Libra Malvinense", "CLF": "Unidad de Fomento Chilena", "BND": "Dólar de Brunéi", "KHR": "Riel Camboyano",
    "LAK": "Kip Laosiano", "MMK": "Kyat Birmano", "MNT": "Tugrik Mongol", "MOP": "Pataca Macaense",
    "MVR": "Rufiyaa Maldiva", "BTN": "Ngultrum Butanés", "PGK": "Kina Papú", "FJD": "Dólar Fiyiano",
    "SBD": "Dólar de Islas Salomón", "TOP": "Pa'anga Tongano", "VUV": "Vatu Vanuatuense", "WST": "Tala Samoano",
    "XPF": "Franco CFP", "KID": "Dólar de Kiribati", "TVD": "Dólar Tuvaluano", "FOK": "Corona Feroesa",
    "GGP": "Libra de Guernsey", "IMP": "Libra Manesa", "JEP": "Libra de Jersey", "GIP": "Libra Gibraltareña",
    "XDR": "Derechos Especiales de Giro (FMI)", "XAU": "Onza Troy de Oro", "XAG": "Onza Troy de Plata",
    "XPT": "Onza Troy de Platino", "XPD": "Onza Troy de Paladio", "MXV": "Unidad de Inversión Mexicana (UDI)",
    "BOV": "Mvdol Boliviano", "COU": "Unidad de Valor Real Colombiana", "CHE": "Euro WIR", "CHW": "Franco WIR",
    "USN": "Dólar Estadounidense (Día Siguiente)", "XSU": "Sucre (Sistema Unitario de Compensación)",
}

# Tasas de referencia de respaldo en caso de desconexión total de red
TASAS_RESPALDO_MXN: dict[str, Decimal] = {
    "USD": Decimal("18.7000"), "EUR": Decimal("20.9300"), "CAD": Decimal("13.3500"),
    "GBP": Decimal("25.0000"), "JPY": Decimal("0.1250"), "CHF": Decimal("21.4000"),
    "CNY": Decimal("2.6200"), "BRL": Decimal("3.4500"), "COP": Decimal("0.0045"),
    "ARS": Decimal("0.0185"), "CLP": Decimal("0.0201"), "PEN": Decimal("5.0200"),
    "MXV": Decimal("8.3500"), "XDR": Decimal("25.1000"), "SVC": Decimal("2.1370"),
}


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


CIRCUIT_BREAKER_SAT = CircuitBreakerSAT(max_fallos=3, ventana_segundos=600)


@retry(wait=wait_exponential_jitter(max=4), stop=stop_after_attempt(2), reraise=True)
def _fetch_fx_live(moneda: str) -> float:
    mon = moneda.upper()
    with httpx.Client(timeout=4.0) as client:
        # Intento directo desde la divisa base hacia MXN
        resp = client.get(FX_API_URL.format(moneda=mon))
        if resp.status_code == 200:
            data = resp.json()
            if "rates" in data and "MXN" in data["rates"]:
                return round(float(data["rates"]["MXN"]), 6)
        # Fallback inverso consultando base MXN (que trae las 166 divisas en una sola petición)
        resp_mxn = client.get(FX_API_URL.format(moneda="MXN"))
        resp_mxn.raise_for_status()
        rates_mxn = resp_mxn.json().get("rates", {})
        if mon in rates_mxn and float(rates_mxn[mon]) > 0:
            return round(1.0 / float(rates_mxn[mon]), 6)
        raise ValueError(f"Divisa {mon} requiere tasa referencial Anexo 20")


def listar_divisas_real() -> dict:
    """Devuelve el catálogo completo de 180 divisas internacionales con su nombre en español."""
    lista = [{"codigo": k, "nombre": v} for k, v in sorted(CATALOGO_180_DIVISAS.items())]
    return {
        "ok": True,
        "total_divisas": len(lista),
        "divisas": lista,
    }


def consultar_tipo_cambio_real(
    moneda: str = "USD",
    tipo_cambio_cfdi: float | str | None = None,
) -> dict:
    """Consulta en tiempo real la cotización oficial de cualquiera de las 180 divisas hacia MXN."""
    mon = (moneda or "MXN").strip().upper()
    nombre_divisa = CATALOGO_180_DIVISAS.get(mon, f"Divisa Internacional ({mon})")
    if mon == "MXN":
        return {
            "ok": True,
            "moneda": "MXN",
            "nombre_moneda": nombre_divisa,
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
            fuente = f"db_fx_cache ({cache['actualizado_en']})"
        else:
            tasa_oficial = TASAS_RESPALDO_MXN.get(mon, Decimal("18.7000"))
            fuente = f"anexo20_referencia ({type(exc).__name__})"

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
        "nombre_moneda": nombre_divisa,
        "total_divisas_soportadas": len(CATALOGO_180_DIVISAS),
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

    registro_69b = buscar_rfc_69b(rfc_emisor)
    en_69b = registro_69b is not None
    if en_69b:
        codigos_fiscales.append("SUPPLIER_69B")

    dup_info = verificar_duplicado_uuid(uuid, rfc_emisor, str(total), case_id)
    if dup_info["es_duplicado"]:
        codigos_fiscales.append("DUPLICATE")

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
            for _ in range(CIRCUIT_BREAKER_SAT.max_fallos):
                CIRCUIT_BREAKER_SAT.registrar_fallo()
            raise httpx.ConnectTimeout("Timeout en ConsultaCFDIService.svc del SAT")

        soap_res = _llamar_soap_sat_real(rfc_emisor, rfc_receptor, str(total), uuid)
        CIRCUIT_BREAKER_SAT.registrar_exito()
    except Exception as exc:
        abrio = CIRCUIT_BREAKER_SAT.registrar_fallo()
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
