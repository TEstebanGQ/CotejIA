"""Genera 3 casos sintéticos (limpio, faltante, alza de precio) para S1."""
import json
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).parent
EMISOR, RECEPTOR = "AAA010101AAA", "BBB020202BBB"  # RFC ficticios

CASOS = {
    "OC-001": {"recibido": {"TORN-001": 100, "CABL-010": 50},
               "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")}},
    "OC-002": {"recibido": {"TORN-001": 80, "CABL-010": 50},
               "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")}},
    "OC-003": {"recibido": {"TORN-001": 100, "CABL-010": 50},
               "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "88.00")}},
}
TASA_IVA = Decimal("0.16")
OC_LINEAS = [
    {"sku": "TORN-001", "descripcion": "Tornillo hexagonal 1/2", "cantidad": 100, "precio_unitario": "12.50",
     "tasa_iva": "0.16"},
    {"sku": "CABL-010", "descripcion": "Cable calibre 10 (rollo)", "cantidad": 50, "precio_unitario": "80.00",
     "tasa_iva": "0.16"},
]


def xml(idx, facturado):
    conceptos, sub, iva_total = "", Decimal("0"), Decimal("0")
    for sku, (q, p) in facturado.items():
        imp = Decimal(q) * Decimal(p)
        iva = (imp * TASA_IVA).quantize(Decimal("0.01"))
        sub += imp
        iva_total += iva
        conceptos += (
            f'    <cfdi:Concepto NoIdentificacion="{sku}" Descripcion="{sku}" Cantidad="{q}" '
            f'ValorUnitario="{p}" Importe="{imp:.2f}" ObjetoImp="02">\n'
            '      <cfdi:Impuestos><cfdi:Traslados>\n'
            f'        <cfdi:Traslado Base="{imp:.2f}" Impuesto="002" TipoFactor="Tasa" '
            f'TasaOCuota="{TASA_IVA:.6f}" Importe="{iva:.2f}"/>\n'
            '      </cfdi:Traslados></cfdi:Impuestos>\n'
            '    </cfdi:Concepto>\n')
    total = sub + iva_total
    uuid = f"0000000{idx}-0000-4000-8000-000000000000"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" TipoDeComprobante="I" '
        f'Moneda="MXN" SubTotal="{sub:.2f}" Total="{total:.2f}">\n'
        f'  <cfdi:Emisor Rfc="{EMISOR}"/>\n  <cfdi:Receptor Rfc="{RECEPTOR}"/>\n'
        f'  <cfdi:Conceptos>\n{conceptos}  </cfdi:Conceptos>\n'
        f'  <cfdi:Impuestos TotalImpuestosTrasladados="{iva_total:.2f}"/>\n'
        '  <cfdi:Complemento>\n'
        f'    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" UUID="{uuid}"/>\n'
        '  </cfdi:Complemento>\n</cfdi:Comprobante>\n')


for idx, (caso, d) in enumerate(CASOS.items(), start=1):
    p = OUT / caso
    p.mkdir(exist_ok=True)
    (p / "oc.json").write_text(json.dumps(
        {"oc": caso, "proveedor_rfc": EMISOR, "lineas": OC_LINEAS}, indent=2, ensure_ascii=False), encoding="utf-8")
    (p / "remision.json").write_text(json.dumps(
        {"oc_referencia": caso, "tiene_sello_almacen": True, "tiene_firma_recepcion": True,
         "lineas": [{"sku": k, "cantidad_recibida": v} for k, v in d["recibido"].items()]}, indent=2), encoding="utf-8")
    (p / "cfdi.xml").write_text(xml(idx, d["facturado"]), encoding="utf-8")
print("Casos generados:", ", ".join(CASOS))
