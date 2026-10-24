"""Genera el lote de 10 casos de prueba para S2 (incluyendo imágenes de remisiones físicas con Pillow)."""
import json
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parent
EMISOR_NORMAL = "AAA010101AAA"
EMISOR_69B_REAL = "AAA080808AAA"  # RFC real incluido en datasets/cache/sat_69b_real.csv (EFOS Definitivo)
RECEPTOR = "BBB020202BBB"
TASA_IVA = Decimal("0.16")

OC_LINEAS_BASE = [
    {
        "sku": "TORN-001",
        "descripcion": "Tornillo hexagonal 1/2",
        "cantidad": 100,
        "precio_unitario": "12.50",
        "tasa_iva": "0.16",
    },
    {
        "sku": "CABL-010",
        "descripcion": "Cable calibre 10 (rollo)",
        "cantidad": 50,
        "precio_unitario": "80.00",
        "tasa_iva": "0.16",
    },
]

OC_LINEAS_ALTO_MONTO = [
    {
        "sku": "TORN-001",
        "descripcion": "Tornillo hexagonal 1/2",
        "cantidad": 100,
        "precio_unitario": "12.50",
        "tasa_iva": "0.16",
    },
    {
        "sku": "CABL-010",
        "descripcion": "Cable calibre 10 (rollo)",
        "cantidad": 150,
        "precio_unitario": "80.00",
        "tasa_iva": "0.16",
    },
]


def dibujar_remision_png(ruta_destino: Path, case_id: str, cant_torn: int, cant_cabl: int, nota: str, borrosa: bool = False):
    """Dibuja una imagen PNG realista de remisión de almacén con tabla, sello, firma y nota a mano."""
    img = Image.new("RGB", (780, 520), color=(252, 251, 247))
    draw = ImageDraw.Draw(img)

    # Marco exterior y encabezado
    draw.rectangle([20, 20, 760, 500], outline=(40, 40, 40), width=2)
    draw.rectangle([20, 20, 760, 85], fill=(24, 52, 74), outline=(40, 40, 40), width=2)
    draw.text((40, 35), f"REMISION DE ALMACEN  |  FOLIO: REM-{case_id[-3:]}", fill=(255, 255, 255))
    draw.text((40, 58), f"ORDEN DE COMPRA REF: {case_id}   |   FECHA: 2026-10-24   |   RFC: {EMISOR_NORMAL}", fill=(210, 230, 245))

    # Encabezado de tabla
    draw.rectangle([40, 110, 740, 145], fill=(230, 234, 240), outline=(80, 80, 80), width=1)
    draw.text((55, 122), "SKU", fill=(20, 20, 20))
    draw.text((190, 122), "DESCRIPCION DEL ARTICULO", fill=(20, 20, 20))
    draw.text((560, 122), "CANTIDAD RECIBIDA", fill=(20, 20, 20))

    # Filas de productos
    draw.rectangle([40, 145, 740, 195], outline=(120, 120, 120), width=1)
    draw.text((55, 162), "TORN-001", fill=(10, 10, 10))
    draw.text((190, 162), "Tornillo hexagonal 1/2 pulgada", fill=(10, 10, 10))
    draw.text((610, 162), f"{cant_torn}", fill=(10, 10, 10))

    draw.rectangle([40, 195, 740, 245], outline=(120, 120, 120), width=1)
    draw.text((55, 212), "CABL-010", fill=(10, 10, 10))
    draw.text((190, 212), "Cable calibre 10 (rollo 100m)", fill=(10, 10, 10))
    draw.text((610, 212), f"{cant_cabl}", fill=(10, 10, 10))

    # Nota manuscrita en tinta roja/azul
    draw.rectangle([40, 270, 740, 335], fill=(255, 248, 230), outline=(190, 140, 60), width=1)
    draw.text((55, 282), "OBSERVACIONES DE RECEPCION (MANUSCRITO ALMACEN):", fill=(140, 60, 20))
    draw.text((55, 305), nota, fill=(180, 20, 20))

    # Sello de almacén (tinta azul)
    draw.rectangle([60, 365, 330, 465], outline=(20, 70, 170), width=3)
    draw.text((85, 382), "ALMACEN CENTRAL COTEJAI", fill=(20, 70, 170))
    draw.text((105, 408), "RECIBIDO CONFORME", fill=(20, 70, 170))
    draw.text((95, 432), "SELLO OFICIAL #04 - 2026", fill=(20, 70, 170))

    # Firma de recepción
    draw.line([450, 445, 700, 445], fill=(30, 30, 30), width=2)
    draw.line([480, 430, 530, 395, 560, 435, 620, 400, 660, 425], fill=(15, 25, 90), width=3)
    draw.text((505, 455), "Firma Jefe de Almacen", fill=(60, 60, 60))

    if borrosa:
        # Desenfoque fuerte que vuelve ilegibles los números (para probar RECEIPT_UNREADABLE)
        img = img.filter(ImageFilter.GaussianBlur(radius=9))

    img.save(ruta_destino, format="PNG")


def generar_xml(
    uuid: str,
    facturado: dict,
    emisor: str = EMISOR_NORMAL,
    moneda: str = "MXN",
    tipo_cambio: str | None = None,
    tasa_iva_override: Decimal | None = None,
) -> str:
    conceptos, sub, iva_total = "", Decimal("0"), Decimal("0")
    tasa_usar = tasa_iva_override if tasa_iva_override is not None else TASA_IVA
    for sku, (q, p) in facturado.items():
        imp = Decimal(q) * Decimal(p)
        iva = (imp * tasa_usar).quantize(Decimal("0.01"))
        sub += imp
        iva_total += iva
        conceptos += (
            f'    <cfdi:Concepto NoIdentificacion="{sku}" Descripcion="{sku}" Cantidad="{q}" '
            f'ValorUnitario="{p}" Importe="{imp:.2f}" ObjetoImp="02">\n'
            "      <cfdi:Impuestos><cfdi:Traslados>\n"
            f'        <cfdi:Traslado Base="{imp:.2f}" Impuesto="002" TipoFactor="Tasa" '
            f'TasaOCuota="{tasa_usar:.6f}" Importe="{iva:.2f}"/>\n'
            "      </cfdi:Traslados></cfdi:Impuestos>\n"
            "    </cfdi:Concepto>\n"
        )
    total = sub + iva_total
    tc_attr = f' TipoCambio="{tipo_cambio}"' if tipo_cambio else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" TipoDeComprobante="I" '
        f'Moneda="{moneda}"{tc_attr} SubTotal="{sub:.2f}" Total="{total:.2f}">\n'
        f'  <cfdi:Emisor Rfc="{emisor}"/>\n  <cfdi:Receptor Rfc="{RECEPTOR}"/>\n'
        f"  <cfdi:Conceptos>\n{conceptos}  </cfdi:Conceptos>\n"
        f'  <cfdi:Impuestos TotalImpuestosTrasladados="{iva_total:.2f}"/>\n'
        "  <cfdi:Complemento>\n"
        f'    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" UUID="{uuid}"/>\n'
        "  </cfdi:Complemento>\n</cfdi:Comprobante>\n"
    )


CASOS = {
    # S1 Base (Intactos para los 35 tests existentes)
    "OC-001": {
        "uuid": "00000001-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
    },
    "OC-002": {
        "uuid": "00000002-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 80, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
    },
    "OC-003": {
        "uuid": "00000003-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "88.00")},
    },
    # S2 Nuevos escenarios con herramientas reales
    "OC-004": {
        "uuid": "00000004-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 80, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Se reciben 80 pzas de TORN-001; faltaron 20 por merma en transporte."},
    },
    "OC-005": {
        "uuid": "00000005-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": True, "nota": "Foto tomada con camara desenfocada e ilegible."},
    },
    "OC-006": {
        "uuid": "00000006-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "moneda": "USD",
        "tipo_cambio": "21.85",  # Tipo de cambio inflado frente al oficial (~18.69 MXN/USD)
    },
    "OC-007": {
        "uuid": "00000007-0000-4000-8000-000000000000",
        "emisor": EMISOR_69B_REAL,  # Proveedor EFOS Definitivo en Lista 69-B oficial del SAT
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
    },
    "OC-008": {
        "uuid": "00000008-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "tasa_iva_cfdi": Decimal("0.08"),  # Discrepancia de tasa de IVA (8% vs 16% pactado en OC)
    },
    "OC-009": {
        "uuid": "00000001-0000-4000-8000-000000000000",  # UUID duplicado idéntico al de OC-001
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
    },
    "OC-010": {
        "uuid": "00000010-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "oc_lineas": OC_LINEAS_ALTO_MONTO,
        "recibido": {"TORN-001": 100, "CABL-010": 50},  # Faltan 100 rollos -> Fuga $9,280 MXN (> $5,000 límite)
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("150", "80.00")},
        "simular_caida_sat": True,  # Dispara el Circuit Breaker del SAT (SAT_NO_VERIFICADO)
    },
}


def generar_todos():
    for caso, d in CASOS.items():
        p = OUT / caso
        p.mkdir(exist_ok=True)
        oc_data = {
            "oc": caso,
            "proveedor_rfc": d["emisor"],
            "moneda": d.get("moneda", "MXN"),
            "simular_caida_sat": d.get("simular_caida_sat", False),
            "lineas": d["oc_lineas"],
        }
        (p / "oc.json").write_text(json.dumps(oc_data, indent=2, ensure_ascii=False), encoding="utf-8")

        rem_data = {
            "oc_referencia": caso,
            "tiene_sello_almacen": True,
            "tiene_firma_recepcion": True,
            "requiere_vision": "imagen" in d,
            "lineas": [{"sku": k, "cantidad_recibida": v} for k, v in d["recibido"].items()],
        }
        if "imagen" in d:
            rem_data["observaciones_manuales"] = d["imagen"]["nota"]
            dibujar_remision_png(
                p / "remision.png",
                case_id=caso,
                cant_torn=d["recibido"]["TORN-001"],
                cant_cabl=d["recibido"]["CABL-010"],
                nota=d["imagen"]["nota"],
                borrosa=d["imagen"]["borrosa"],
            )
        (p / "remision.json").write_text(json.dumps(rem_data, indent=2, ensure_ascii=False), encoding="utf-8")

        xml_str = generar_xml(
            uuid=d["uuid"],
            facturado=d["facturado"],
            emisor=d["emisor"],
            moneda=d.get("moneda", "MXN"),
            tipo_cambio=d.get("tipo_cambio"),
            tasa_iva_override=d.get("tasa_iva_cfdi"),
        )
        (p / "cfdi.xml").write_text(xml_str, encoding="utf-8")


if __name__ == "__main__":
    generar_todos()
    print("Casos S2 generados (10 casos + imágenes PNG):", ", ".join(CASOS))
