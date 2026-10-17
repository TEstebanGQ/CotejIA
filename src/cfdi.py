"""Lectura determinista de un CFDI 4.0 (XML). Sin LLM."""
from decimal import Decimal
from xml.etree import ElementTree as ET

NS = {"cfdi": "http://www.sat.gob.mx/cfd/4",
      "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"}


def leer_cfdi(ruta_xml: str) -> dict:
    root = ET.parse(ruta_xml).getroot()
    tfd = root.find(".//tfd:TimbreFiscalDigital", NS)
    conceptos = [{
        "sku": c.get("NoIdentificacion"),
        "descripcion": c.get("Descripcion"),
        "cantidad": Decimal(c.get("Cantidad")),
        "valor_unitario": Decimal(c.get("ValorUnitario")),
        "importe": Decimal(c.get("Importe")),
    } for c in root.findall("cfdi:Conceptos/cfdi:Concepto", NS)]
    return {
        "uuid": tfd.get("UUID").upper() if tfd is not None else None,
        "tipo": root.get("TipoDeComprobante"),
        "rfc_emisor": root.find("cfdi:Emisor", NS).get("Rfc"),
        "rfc_receptor": root.find("cfdi:Receptor", NS).get("Rfc"),
        "moneda": root.get("Moneda"),
        "subtotal": Decimal(root.get("SubTotal")),
        "total": Decimal(root.get("Total")),
        "conceptos": conceptos,
    }
