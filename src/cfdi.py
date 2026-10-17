"""Lectura determinista de un CFDI 4.0 (XML). Sin LLM."""
from decimal import Decimal
from xml.etree import ElementTree as ET

NS = {"cfdi": "http://www.sat.gob.mx/cfd/4",
      "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"}


def _dec(x: str | None) -> Decimal:
    return Decimal(x) if x not in (None, "") else Decimal("0")


def _impuestos(nodo, ruta: str) -> list[dict]:
    """Traslados o retenciones de un concepto. Impuesto: 001 ISR, 002 IVA, 003 IEPS."""
    return [{
        "impuesto": t.get("Impuesto"),
        "tipo_factor": t.get("TipoFactor"),          # Tasa, Cuota o Exento
        "tasa": _dec(t.get("TasaOCuota")),
        "base": _dec(t.get("Base")),
        "importe": _dec(t.get("Importe")),
    } for t in nodo.findall(ruta, NS)]


def leer_cfdi(ruta_xml: str) -> dict:
    root = ET.parse(ruta_xml).getroot()
    tfd = root.find(".//tfd:TimbreFiscalDigital", NS)
    conceptos = [{
        "sku": c.get("NoIdentificacion"),
        "descripcion": c.get("Descripcion"),
        "cantidad": _dec(c.get("Cantidad")),
        "valor_unitario": _dec(c.get("ValorUnitario")),
        "importe": _dec(c.get("Importe")),
        "descuento": _dec(c.get("Descuento")),
        "objeto_imp": c.get("ObjetoImp"),
        "traslados": _impuestos(c, "cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado"),
        "retenciones": _impuestos(c, "cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion"),
    } for c in root.findall("cfdi:Conceptos/cfdi:Concepto", NS)]
    return {
        "uuid": tfd.get("UUID").upper() if tfd is not None else None,
        "tipo": root.get("TipoDeComprobante"),
        "rfc_emisor": root.find("cfdi:Emisor", NS).get("Rfc"),
        "rfc_receptor": root.find("cfdi:Receptor", NS).get("Rfc"),
        "moneda": root.get("Moneda"),
        "subtotal": _dec(root.get("SubTotal")),
        "descuento": _dec(root.get("Descuento")),
        "total": _dec(root.get("Total")),
        "conceptos": conceptos,
    }
