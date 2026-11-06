"""Generador de datasets CotejAI.

- S2: 10 casos fijos en datasets/OC-0XX (con imágenes Pillow).
- S3: 36 casos balanceados, reproducibles con semilla, en datasets/s3/S3-0XX, cada uno con
  oc.json, cfdi.xml, remision (pdf digital o foto png), remision.json y esperado.json (ground truth
  calculado de forma independiente del motor con Decimal, al centavo).

Uso:  python datasets/generate.py [--s2] [--s3] [--semilla 42]   (sin banderas genera ambos)
- S4: 1,000 casos (--s4 [--n N]) en datasets/s4/S4-XXXX, iterador streaming iter_casos_s4().
"""
import argparse
import json
import random
import uuid as uuidlib
from decimal import ROUND_HALF_UP, Decimal
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


def dibujar_remision_png(
    ruta_destino: Path,
    case_id: str,
    cant_torn: int,
    cant_cabl: int,
    nota: str,
    borrosa: bool = False,
    emisor_rfc: str = EMISOR_NORMAL,
    proveedor_nombre: str = "PROVEEDOR INDUSTRIAL",
):
    """Dibuja una imagen PNG realista de remisión de almacén con tabla, sello, firma y nota a mano."""
    img = Image.new("RGB", (780, 520), color=(252, 251, 247))
    draw = ImageDraw.Draw(img)

    # Marco exterior y encabezado
    draw.rectangle([20, 20, 760, 500], outline=(40, 40, 40), width=2)
    draw.rectangle([20, 20, 760, 88], fill=(24, 52, 74), outline=(40, 40, 40), width=2)
    draw.text((40, 32), f"REMISION DE ALMACEN  |  FOLIO: REM-{case_id[-3:]}  |  {proveedor_nombre[:38]}", fill=(255, 255, 255))
    draw.text((40, 58), f"ORDEN DE COMPRA REF: {case_id}   |   FECHA: 2026-10-24   |   RFC: {emisor_rfc}", fill=(210, 230, 245))

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
    # S1 Base + Imágenes físicas de remisión para todos los casos (OC-001 a OC-010)
    "OC-001": {
        "uuid": "00000001-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Ferretería Industrial del Bajío S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Recepcion completa conforme a OC-001: 100 TORN-001 y 50 CABL-010. Sin merma."},
    },
    "OC-002": {
        "uuid": "00000002-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Aceros y Fijaciones Monterrey S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 80, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Se reciben 80 pzas de TORN-001 (faltaron 20 pzas en caja) y 50 rollos CABL-010."},
    },
    "OC-003": {
        "uuid": "00000003-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Conductores Eléctricos del Centro S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "88.00")},
        "imagen": {"borrosa": False, "nota": "Recepcion fisica completa (100 TORN-001 y 50 CABL-010). Verificar tarifa en factura."},
    },
    # S2 Nuevos escenarios con herramientas reales
    "OC-004": {
        "uuid": "00000004-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Metales & Manufacturas de Toluca S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 80, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Se reciben 80 pzas de TORN-001; faltaron 20 por merma en transporte."},
    },
    "OC-005": {
        "uuid": "00000005-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Suministros Industriales de Occidente S.A.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": True, "nota": "Foto tomada con camara desenfocada e ilegible."},
    },
    "OC-006": {
        "uuid": "00000006-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Global Wire & Fasteners Corp (USD)",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "moneda": "USD",
        "tipo_cambio": "21.85",  # Tipo de cambio inflado frente al oficial (~18.69 MXN/USD)
        "imagen": {"borrosa": False, "nota": "Recibidos 100 TORN-001 y 50 CABL-010 completos. Factura emitida en USD."},
    },
    "OC-007": {
        "uuid": "00000007-0000-4000-8000-000000000000",
        "emisor": EMISOR_69B_REAL,  # Proveedor EFOS Definitivo en Lista 69-B oficial del SAT
        "proveedor_nombre": "Comercializadora Fantasma del Sur S.A. (EFOS 69-B)",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Mercancia ingresada a almacen. Pendiente validacion fiscal RFC AAA080808AAA."},
    },
    "OC-008": {
        "uuid": "00000008-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Distribuidora Fronteriza de Insumos S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "tasa_iva_cfdi": Decimal("0.08"),  # Discrepancia de tasa de IVA (8% vs 16% pactado en OC)
        "imagen": {"borrosa": False, "nota": "100 TORN-001 y 50 CABL-010 recibidos conformes. Revisar tasa IVA en CFDI."},
    },
    "OC-009": {
        "uuid": "00000001-0000-4000-8000-000000000000",  # UUID duplicado idéntico al de OC-001
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Ferretería Industrial del Bajío S.A. de C.V.",
        "oc_lineas": OC_LINEAS_BASE,
        "recibido": {"TORN-001": 100, "CABL-010": 50},
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("50", "80.00")},
        "imagen": {"borrosa": False, "nota": "Mercancia recibida. ATENCION: proveedor adjunto UUID ya registrado en OC-001."},
    },
    "OC-010": {
        "uuid": "00000010-0000-4000-8000-000000000000",
        "emisor": EMISOR_NORMAL,
        "proveedor_nombre": "Consorcio Mayorista de Cableado Pesado S.A.",
        "oc_lineas": OC_LINEAS_ALTO_MONTO,
        "recibido": {"TORN-001": 100, "CABL-010": 50},  # Faltan 100 rollos -> Fuga $9,280 MXN (> $5,000 límite)
        "facturado": {"TORN-001": ("100", "12.50"), "CABL-010": ("150", "80.00")},
        "simular_caida_sat": True,  # Dispara el Circuit Breaker del SAT (SAT_NO_VERIFICADO)
        "imagen": {"borrosa": False, "nota": "FALTANTE CRITICO: Solo llegaron 50 rollos CABL-010 de 150 pedidos (-100 rollos)."},
    },
}


def generar_todos():
    for caso, d in CASOS.items():
        p = OUT / caso
        p.mkdir(exist_ok=True)
        oc_data = {
            "oc": caso,
            "proveedor_rfc": d["emisor"],
            "proveedor_nombre": d.get("proveedor_nombre", f"Proveedor {caso}"),
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
                emisor_rfc=d["emisor"],
                proveedor_nombre=d.get("proveedor_nombre", f"Proveedor {caso}"),
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


# ════════════════════════════════════════════════════════════════════════════
# S3 · 36 casos balanceados con ground truth (esperado.json)
# ════════════════════════════════════════════════════════════════════════════
SEMILLA_DEFAULT = 42
FECHA_REMISION = "2026-10-24"
LIMITE_AUTONOMO = Decimal("5000")
CENT = Decimal("0.01")
OUT_S3 = OUT / "s3"

PROVEEDORES = [
    {"rfc": "FHN150312K41", "razon_social": "Ferretera Herrera del Norte SA de CV", "regimen": "601"},
    {"rfc": "CMS090715QX2", "razon_social": "Cableados y Materiales del Sur SA de CV", "regimen": "601"},
    {"rfc": "DIP120930T55", "razon_social": "Distribuidora Industrial del Pacifico SA de CV", "regimen": "601"},
]
PROVEEDOR_69B = {"rfc": EMISOR_69B_REAL, "razon_social": "COMERCIALIZADORA Y DISTRIBUIDORA DEL SURESTE SA DE CV", "regimen": "601"}

# (prefijo, descripcion, unidad, tasa IVA o "exento"). 30 de ticket bajo y 10 de ticket alto.
_SKUS_BARATOS = [
    ("TORN", "Tornillo hexagonal 1/2", "pza", "0.16"), ("TUER", "Tuerca hexagonal 1/2", "pza", "0.16"),
    ("ROND", "Rondana plana 1/2", "pza", "0.16"), ("CLAV", "Clavo de acero 2 pulgadas", "kg", "0.16"),
    ("CABL", "Cable calibre 10 (rollo)", "pza", "0.16"), ("CINT", "Cinta de aislar negra", "pza", "0.16"),
    ("PINT", "Pintura vinilica blanca", "litro", "0.16"), ("THIN", "Thinner estandar", "litro", "0.16"),
    ("GUAN", "Guantes de carnaza", "pza", "0.16"), ("CASC", "Casco de seguridad", "pza", "0.16"),
    ("LENT", "Lentes de seguridad", "pza", "0.16"), ("TAPO", "Tapon auditivo (caja 100)", "caja", "0.16"),
    ("TUBO", "Tubo PVC 2 pulgadas", "pza", "0.16"), ("CODO", "Codo PVC 2 pulgadas", "pza", "0.16"),
    ("PEGA", "Pegamento PVC", "litro", "0.16"), ("SELL", "Sellador de silicon", "pza", "0.16"),
    ("LIJA", "Lija de agua grano 220", "pza", "0.16"), ("DISC", "Disco de corte 4.5 pulgadas", "pza", "0.16"),
    ("BROC", "Broca para concreto 3/8", "pza", "0.16"), ("FOCO", "Foco LED 12W", "caja", "0.16"),
    ("ALAM", "Alambre galvanizado", "kg", "0.16"), ("ARNE", "Arnes de seguridad", "pza", "0.16"),
    ("ARRO", "Arroz en grano para comedor", "kg", "0.00"), ("FRIJ", "Frijol para comedor", "kg", "0.00"),
    ("AGUA", "Garrafon de agua 20 litros", "pza", "0.00"), ("LECH", "Leche entera caja 12 litros", "caja", "0.00"),
    ("FRON", "Fertilizante zona frontera", "kg", "0.08"), ("SEMF", "Semilla zona frontera", "kg", "0.08"),
    ("LIBR", "Libro tecnico de seguridad", "pza", "exento"), ("MANU", "Manual de capacitacion impreso", "pza", "exento"),
]
_SKUS_CAROS = [
    ("TALA", "Taladro percutor industrial", "pza", "0.16"), ("SOLD", "Soldadora inversora 200A", "pza", "0.16"),
    ("COMP", "Compresor de aire 50 litros", "pza", "0.16"), ("MOTO", "Motor electrico 5HP", "pza", "0.16"),
    ("BOMB", "Bomba centrifuga 2HP", "pza", "0.16"), ("TRAN", "Transformador 45kVA", "pza", "0.16"),
    ("GENE", "Generador portatil 5kW", "pza", "0.16"), ("ANDA", "Andamio tubular certificado", "pza", "0.16"),
    ("EXTI", "Extintor PQS 9kg", "pza", "0.16"), ("CASE", "Caseta de vigilancia prefabricada", "pza", "0.16"),
]
CARGOS_NO_PACTADOS = [
    ("FLET-001", "Flete y acarreo"), ("MANI-001", "Maniobras de descarga"),
    ("SEGU-001", "Seguro de transporte"), ("EMBA-001", "Embalaje especial"),
]


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def construir_catalogo(rng: random.Random) -> list[dict]:
    """40 SKUs con unidad, precio (Decimal, 2 decimales), tasa de IVA y descripción. Determinista por semilla."""
    catalogo = []
    for i, (pref, desc, unidad, tasa) in enumerate(_SKUS_BARATOS + _SKUS_CAROS, start=1):
        centavos = rng.randint(300, 40000) if i <= len(_SKUS_BARATOS) else rng.randint(60000, 250000)
        catalogo.append({
            "sku": f"{pref}-{i:03d}", "descripcion": desc, "unidad": unidad,
            "precio": Decimal(centavos) / 100, "tasa": None if tasa == "exento" else Decimal(tasa),
        })
    assert len(catalogo) == 40
    return catalogo


# ── CFDI 4.0 con impuestos por concepto (admite IVA exento y overrides de error) ──────────────
def generar_xml_s3(spec: dict) -> tuple[str, Decimal]:
    """Devuelve (xml, total). `facturado` es una lista de conceptos con sku, desc, q, p, tasa y iva_override."""
    conceptos, sub, iva_total = "", Decimal("0"), Decimal("0")
    for c in spec["facturado"]:
        imp = _q(Decimal(c["q"]) * c["p"])
        if c["tasa"] is None:
            traslado = f'        <cfdi:Traslado Base="{imp:.2f}" Impuesto="002" TipoFactor="Exento"/>\n'
            iva = Decimal("0")
        else:
            iva = c["iva_override"] if c.get("iva_override") is not None else _q(imp * c["tasa"])
            traslado = (f'        <cfdi:Traslado Base="{imp:.2f}" Impuesto="002" TipoFactor="Tasa" '
                        f'TasaOCuota="{c["tasa"]:.6f}" Importe="{iva:.2f}"/>\n')
        sub += imp
        iva_total += iva
        conceptos += (
            f'    <cfdi:Concepto NoIdentificacion="{c["sku"]}" Descripcion="{c["desc"]}" Cantidad="{c["q"]}" '
            f'ValorUnitario="{c["p"]:.2f}" Importe="{imp:.2f}" ObjetoImp="02">\n'
            f"      <cfdi:Impuestos><cfdi:Traslados>\n{traslado}      </cfdi:Traslados></cfdi:Impuestos>\n"
            "    </cfdi:Concepto>\n"
        )
    total = sub + iva_total + spec.get("ajuste_total", Decimal("0"))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" TipoDeComprobante="I" '
        f'{spec.get("comprobante_attrs", "")}Moneda="{spec.get("moneda", "MXN")}" '
        f'{spec.get("tipo_cambio_attr", "")}SubTotal="{sub:.2f}" Total="{total:.2f}">\n'
        f'  <cfdi:Emisor Rfc="{spec["proveedor"]["rfc"]}"/>\n  <cfdi:Receptor Rfc="{RECEPTOR}"/>\n'
        f"  <cfdi:Conceptos>\n{conceptos}  </cfdi:Conceptos>\n"
        f'  <cfdi:Impuestos TotalImpuestosTrasladados="{iva_total:.2f}"/>\n'
        "  <cfdi:Complemento>\n"
        f'    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" UUID="{spec["uuid"]}"{spec.get("tfd_attrs", "")}/>\n'
        "  </cfdi:Complemento>\n</cfdi:Comprobante>\n"
    )
    return xml, total


# ── Ground truth: regla contractual, calculada sin usar src/ ───────────────────────────────────
def calcular_esperado(spec: dict, total: Decimal) -> dict:
    """Se paga lo recibido, al precio pactado, sin exceder lo ordenado; IVA a la tasa pactada en la OC."""
    oc = {l["sku"]: l for l in spec["oc_lineas"]}
    monto, codigos = Decimal("0"), set()
    for c in spec["facturado"]:
        if c["sku"] not in oc:
            codigos.add("SKU_UNMAPPED")
            continue
        l = oc[c["sku"]]
        p_oc, q_oc = l["precio"], l["cantidad"]
        q_rec = spec["recibido"].get(c["sku"], 0)
        tol = min(p_oc * Decimal("0.02"), Decimal("1"))
        precio_alto = c["p"] - p_oc > tol
        p_pagar = p_oc if precio_alto else c["p"]
        q_pagar = max(min(c["q"], q_rec, q_oc), 0)
        tasa = l["tasa"] or Decimal("0")
        monto += _q(Decimal(q_pagar) * p_pagar * (1 + tasa))
        if precio_alto:
            codigos.add("PRICE_UP")
        if c["q"] > q_rec:
            codigos.add("QTY_SHORT")
        if c.get("iva_override") is not None and c["tasa"] is not None:
            if abs(_q(_q(Decimal(c["q"]) * c["p"]) * c["tasa"]) - c["iva_override"]) > Decimal("0.02"):
                codigos.add("TAX_MISMATCH")
    if spec.get("ajuste_total", Decimal("0")) != 0:
        codigos.add("TAX_MISMATCH")
    monto = _q(monto)
    fuga = _q(max(total - monto, Decimal("0")))
    if spec.get("es_69b"):
        codigos, monto, fuga = {"SUPPLIER_69B"}, Decimal("0.00"), total
    elif spec.get("duplicado_de"):
        codigos, monto, fuga = {"DUPLICATE"}, Decimal("0.00"), total
    elif spec.get("remision_ilegible"):
        codigos = {"RECEIPT_UNREADABLE"}
    elif not codigos:
        codigos = {"MATCH_OK"}
    if codigos == {"MATCH_OK"}:
        estado = "APROBADO"
    elif codigos <= {"QTY_SHORT", "PRICE_UP"} and fuga <= LIMITE_AUTONOMO:
        estado = "EN_RECLAMO"
    else:
        estado = "ESCALADO"
    return {
        "case_id": spec["id"], "tipo_caso": spec["tipo"], "estado_final": estado,
        "codigos": sorted(codigos),
        # Con remisión ilegible no hay monto determinable: null y se excluye de la exactitud de importes.
        "monto_a_pagar_mxn": None if spec.get("remision_ilegible") else f"{monto:.2f}",
        "fuga_detectada_mxn": f"{fuga:.2f}" if not spec.get("remision_ilegible") else "0.00",
        "total_cfdi_mxn": f"{total:.2f}",
        "fuente_remision": "foto" if spec.get("foto") else "pdf",
        "remision": {"lineas": [{"sku": k, "cantidad_recibida": v} for k, v in spec["recibido"].items()]},
    }


# ── Composición de casos ───────────────────────────────────────────────────────────────────────
def _oc_linea(sku_cat: dict, q: int) -> dict:
    return {"sku": sku_cat["sku"], "descripcion": sku_cat["descripcion"], "unidad": sku_cat["unidad"],
            "cantidad": q, "precio": sku_cat["precio"], "tasa": sku_cat["tasa"]}


def _spec_base(rng: random.Random, catalogo: list[dict], idx: int, tipo: str,
               n_lineas: int | None = None, caros: bool = False) -> dict:
    pool = [s for s in catalogo if (s["precio"] >= 600) == caros] if caros else [s for s in catalogo if s["precio"] < 600]
    elegidos = rng.sample(pool, n_lineas or rng.randint(1, 3))
    oc_lineas = [_oc_linea(s, rng.randint(5, 40) if caros else rng.randint(10, 300)) for s in elegidos]
    return {
        "id": f"S3-{idx:03d}", "tipo": tipo, "proveedor": rng.choice(PROVEEDORES),
        "uuid": str(uuidlib.UUID(int=rng.getrandbits(128), version=4)),
        "oc_lineas": oc_lineas,
        "recibido": {l["sku"]: l["cantidad"] for l in oc_lineas},
        "facturado": [{"sku": l["sku"], "desc": l["descripcion"], "q": l["cantidad"], "p": l["precio"], "tasa": l["tasa"]}
                      for l in oc_lineas],
    }


def construir_casos(semilla: int) -> list[dict]:
    rng = random.Random(semilla)
    catalogo = construir_catalogo(rng)
    casos, n = [], 0

    def nuevo(tipo, **kw):
        nonlocal n
        n += 1
        s = _spec_base(rng, catalogo, n, tipo, **kw)
        casos.append(s)
        return s

    for k in range(10):                                   # Limpios (2 con precio dentro de tolerancia)
        s = nuevo("MATCH_OK")
        if k < 2:
            c = s["facturado"][0]
            c["p"] += Decimal("0.01")
    for k in range(6):                                    # Faltante parcial (el último supera el límite autónomo)
        s = nuevo("QTY_SHORT", n_lineas=1 if k == 5 else None, caros=(k == 5))
        l = s["oc_lineas"][0]
        faltan = max(1, int(l["cantidad"] * rng.randint(15, 60) / 100))
        s["recibido"][l["sku"]] = l["cantidad"] - faltan
    for _ in range(5):                                    # Alza de precio
        s = nuevo("PRICE_UP")
        c = rng.choice(s["facturado"])
        c["p"] = _q(c["p"] * (1 + Decimal(rng.randint(6, 15)) / 100))
    for k in range(4):                                    # Cargo no pactado (flete, maniobras...)
        s = nuevo("UNAGREED_CHARGE")
        sku, desc = CARGOS_NO_PACTADOS[k]
        s["facturado"].append({"sku": sku, "desc": desc, "q": 1, "p": Decimal(rng.randint(15000, 90000)) / 100,
                               "tasa": Decimal("0.16")})
    for k in range(3):                                    # Duplicado: mismo UUID que un limpio ya auditado
        orig = casos[k]
        s = nuevo("DUPLICATE")
        s.update({"proveedor": orig["proveedor"], "uuid": orig["uuid"], "oc_lineas": orig["oc_lineas"],
                  "recibido": dict(orig["recibido"]), "facturado": [dict(c) for c in orig["facturado"]],
                  "duplicado_de": orig["id"]})
    # IVA mal calculado: sobrecargado, subcargado y total que no cuadra con los conceptos.
    s = nuevo("TAX_MISMATCH", n_lineas=2)
    c = next(c for c in s["facturado"] if c["tasa"])
    c["iva_override"] = _q(_q(Decimal(c["q"]) * c["p"]) * c["tasa"]) + Decimal(rng.randint(2500, 9000)) / 100
    s = nuevo("TAX_MISMATCH", n_lineas=2)
    c = next(c for c in s["facturado"] if c["tasa"])
    c["iva_override"] = _q(_q(Decimal(c["q"]) * c["p"]) * c["tasa"]) - Decimal("5.00")
    s = nuevo("TAX_MISMATCH")
    s["ajuste_total"] = Decimal(rng.randint(3000, 12000)) / 100
    for _ in range(2):                                    # Proveedor en Lista 69-B (bloqueo sin excepción)
        s = nuevo("SUPPLIER_69B")
        s.update({"proveedor": PROVEEDOR_69B, "es_69b": True})
    # Remisión: ilegible (foto borrosa), sin firma, y tachada con nota a mano (lo tachado manda).
    s = nuevo("RECEIPT_UNREADABLE", n_lineas=2)
    s.update({"foto": True, "borrosa": True, "con_firma": True, "remision_ilegible": True,
              "nota": "Foto tomada con camara desenfocada."})
    s = nuevo("RECEIPT_UNSIGNED", n_lineas=2)
    s.update({"foto": True, "borrosa": False, "con_firma": False, "remision_ilegible": True,
              "nota": "Recibido sin firma del jefe de almacen."})
    s = nuevo("RECEIPT_HANDWRITTEN", n_lineas=2)
    l = s["oc_lineas"][0]
    s["recibido"][l["sku"]] = l["cantidad"] - max(1, l["cantidad"] // 5)
    s.update({"foto": True, "borrosa": False, "con_firma": True, "tachado": l["sku"],
              "nota": f"Se reciben {s['recibido'][l['sku']]}; faltaron {l['cantidad'] - s['recibido'][l['sku']]}."})
    assert len(casos) == 36
    return casos


# ── Remisión digital PDF (sin dependencias: PDF mínimo, texto seleccionable, bytes deterministas) ──
def _pdf_esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def escribir_pdf(ruta: Path, textos: list[tuple], lineas: list[tuple], rects: list[tuple]):
    """textos: (x, top, fuente, tamaño, texto); lineas: (x1,top1,x2,top2,grosor); rects: (x, top, w, h)."""
    H = 792
    ops = []
    for x, top, f, size, t in textos:
        ops.append(f"BT /{f} {size} Tf {x} {H - top} Td ({_pdf_esc(t)}) Tj ET")
    for x1, t1, x2, t2, w in lineas:
        ops.append(f"{w} w {x1} {H - t1} m {x2} {H - t2} l S")
    for x, top, w, h in rects:
        ops.append(f"1 w {x} {H - top - h} {w} {h} re S")
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font "
        b"<< /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Oblique /Encoding /WinAnsiEncoding >>",
    ]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, start=1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    ruta.write_bytes(bytes(out))


def dibujar_remision_pdf(ruta: Path, spec: dict):
    folio = f"REM-{spec['id']}"
    t = [(50, 55, "F2", 15, "REMISION DE ALMACEN"),
         (50, 78, "F1", 10, f"Folio: {folio}    OC: {spec['id']}    Fecha: {FECHA_REMISION}"),
         (50, 92, "F1", 10, f"Proveedor: {spec['proveedor']['razon_social']}    RFC: {spec['proveedor']['rfc']}"),
         (50, 135, "F2", 10, "SKU"), (135, 135, "F2", 10, "DESCRIPCION"),
         (385, 135, "F2", 10, "UNIDAD"), (455, 135, "F2", 10, "CANT. RECIBIDA")]
    top = 158
    for l in spec["oc_lineas"]:
        t += [(50, top, "F1", 10, l["sku"]), (135, top, "F1", 10, l["descripcion"]),
              (385, top, "F1", 10, l["unidad"]), (455, top, "F1", 10, str(spec["recibido"][l["sku"]]))]
        top += 20
    t += [(60, 640, "F2", 10, "ALMACEN CENTRAL"), (60, 655, "F2", 10, "RECIBIDO CONFORME"),
          (350, 700, "F1", 9, "Firma Jefe de Almacen")]
    firma = [(360, 690, 390, 665, 2), (390, 665, 410, 688, 2), (410, 688, 440, 662, 2), (440, 662, 480, 684, 2),
             (340, 695, 520, 695, 1)]
    escribir_pdf(ruta, t, firma, [(50, 625, 170, 45), (40, 120, 532, top - 120 + 8)])


def dibujar_foto_remision(ruta: Path, spec: dict, rng: random.Random):
    """Foto de remisión: tabla, sello, firma opcional, tachón con nota a mano, ligera rotación y desenfoque opcional."""
    img = Image.new("RGB", (780, 520), color=(250, 248, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 760, 500], outline=(40, 40, 40), width=2)
    d.rectangle([20, 20, 760, 85], fill=(24, 52, 74))
    d.text((40, 35), f"REMISION DE ALMACEN  |  FOLIO: REM-{spec['id']}", fill=(255, 255, 255))
    d.text((40, 58), f"OC: {spec['id']}  |  FECHA: {FECHA_REMISION}  |  RFC: {spec['proveedor']['rfc']}", fill=(210, 230, 245))
    d.rectangle([40, 105, 740, 135], fill=(230, 234, 240), outline=(80, 80, 80))
    d.text((55, 114), "SKU", fill=(20, 20, 20)); d.text((190, 114), "DESCRIPCION", fill=(20, 20, 20))
    d.text((560, 114), "CANTIDAD RECIBIDA", fill=(20, 20, 20))
    y = 135
    for l in spec["oc_lineas"]:
        d.rectangle([40, y, 740, y + 40], outline=(120, 120, 120))
        d.text((55, y + 14), l["sku"], fill=(10, 10, 10)); d.text((190, y + 14), l["descripcion"], fill=(10, 10, 10))
        if spec.get("tachado") == l["sku"]:
            d.text((610, y + 14), str(l["cantidad"]), fill=(10, 10, 10))
            d.line([600, y + 12, 650, y + 30], fill=(180, 20, 20), width=3)         # tachón
            d.text((670, y + 14), str(spec["recibido"][l["sku"]]), fill=(180, 20, 20))
        else:
            d.text((610, y + 14), str(spec["recibido"][l["sku"]]), fill=(10, 10, 10))
        y += 40
    d.rectangle([40, 290, 740, 345], fill=(255, 248, 230), outline=(190, 140, 60))
    d.text((55, 300), "OBSERVACIONES (MANUSCRITO):", fill=(140, 60, 20)); d.text((55, 322), spec["nota"], fill=(180, 20, 20))
    d.rectangle([60, 375, 330, 470], outline=(20, 70, 170), width=3)
    d.text((85, 392), "ALMACEN CENTRAL", fill=(20, 70, 170)); d.text((105, 418), "RECIBIDO CONFORME", fill=(20, 70, 170))
    d.line([450, 450, 700, 450], fill=(30, 30, 30), width=2)
    if spec["con_firma"]:
        d.line([480, 435, 530, 400, 560, 440, 620, 405, 660, 430], fill=(15, 25, 90), width=3)
    d.text((505, 458), "Firma Jefe de Almacen", fill=(60, 60, 60))
    img = img.rotate(rng.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=(250, 248, 242))
    if spec["borrosa"]:
        img = img.filter(ImageFilter.GaussianBlur(radius=9))
    img.save(ruta, format="PNG")


def generar_s3(semilla: int = SEMILLA_DEFAULT, salida: Path = OUT_S3) -> list[str]:
    salida.mkdir(parents=True, exist_ok=True)
    rng_img = random.Random(semilla + 1)
    ids = []
    for spec in construir_casos(semilla):
        p = salida / spec["id"]
        p.mkdir(exist_ok=True)
        xml, total = generar_xml_s3(spec)
        (p / "cfdi.xml").write_text(xml, encoding="utf-8")
        oc = {"oc": spec["id"], "proveedor_rfc": spec["proveedor"]["rfc"], "proveedor": spec["proveedor"]["razon_social"],
              "moneda": "MXN", "simular_caida_sat": False,
              "lineas": [{"sku": l["sku"], "descripcion": l["descripcion"], "unidad": l["unidad"], "cantidad": l["cantidad"],
                          "precio_unitario": f"{l['precio']:.2f}", "tasa_iva": str(l["tasa"] or Decimal("0")),
                          **({"exento": True} if l["tasa"] is None else {})} for l in spec["oc_lineas"]]}
        (p / "oc.json").write_text(json.dumps(oc, indent=2, ensure_ascii=False), encoding="utf-8")
        rem = {"oc_referencia": spec["id"], "tiene_sello_almacen": True,
               "tiene_firma_recepcion": spec.get("con_firma", True), "requiere_vision": bool(spec.get("foto")),
               "lineas": [{"sku": k, "cantidad_recibida": v} for k, v in spec["recibido"].items()]}
        if spec.get("foto"):
            rem["observaciones_manuales"] = spec["nota"]
            dibujar_foto_remision(p / "remision.png", spec, rng_img)
        else:
            dibujar_remision_pdf(p / "remision.pdf", spec)
        (p / "remision.json").write_text(json.dumps(rem, indent=2, ensure_ascii=False), encoding="utf-8")
        (p / "esperado.json").write_text(json.dumps(calcular_esperado(spec, total), indent=2, ensure_ascii=False),
                                         encoding="utf-8")
        ids.append(spec["id"])
    return ids



# ════════════════════════════════════════════════════════════════════════════
# S4 · 1,000 casos para la semana de carga (iterador streaming, reproducible por semilla)
# ════════════════════════════════════════════════════════════════════════════
OUT_S4 = OUT / "s4"
N_S4 = 1000
SEMILLA_S4 = 4
CSV_69B = OUT / "cache" / "sat_69b_real.csv"
FIX_REFERENCIA_USD = Decimal("18.7000")   # FIX de referencia fijo: el ground truth no depende de la red
TOLERANCIA_FX = Decimal("0.015")
FUGA_TIPICA_MAX = Decimal("4500")          # mermas/sobreprecios típicos quedan bajo el límite autónomo de 5,000
# Distribución objetivo (fracción de N). El último cubo absorbe el redondeo.
DISTRIBUCION_S4 = [("MATCH_OK", Decimal("0.40")), ("QTY_SHORT", Decimal("0.25")), ("PRICE_TAX", Decimal("0.15")),
                   ("FX_OVERCHARGE", Decimal("0.10")), ("SUPPLIER_69B", Decimal("0.05")), ("FISCAL_RECHAZO", Decimal("0.05"))]


def cargar_efos_definitivos(ruta: Path = CSV_69B) -> list[dict]:
    """EFOS 'Definitivo' reales del CSV de la Lista 69-B (se excluyen los 'Presunto')."""
    import csv
    with ruta.open(encoding="utf-8", newline="") as f:
        return [{"rfc": r["rfc"], "razon_social": r["nombre_contribuyente"], "regimen": "601"}
                for r in csv.DictReader(f) if r["situacion"].strip().lower() == "definitivo"]


def cuotas_s4(n: int) -> list[tuple[str, int]]:
    """Cuotas enteras por tipo (método del mayor resto): suman exactamente n."""
    base = [(t, int(n * f)) for t, f in DISTRIBUCION_S4]
    resto = n - sum(c for _, c in base)
    orden = sorted(range(len(DISTRIBUCION_S4)), key=lambda i: (n * DISTRIBUCION_S4[i][1]) % 1, reverse=True)
    cuotas = dict(base)
    for i in orden[:resto]:
        cuotas[DISTRIBUCION_S4[i][0]] += 1
    return [(t, cuotas[t]) for t, _ in DISTRIBUCION_S4]


def _sello(rng: random.Random, largo: int) -> str:
    import base64
    return base64.b64encode(rng.getrandbits(8 * largo).to_bytes(largo, "big")).decode()


def _atributos_cfdi40(rng: random.Random, idx: int, extra_mxn: bool = True) -> dict:
    """Atributos estándar CFDI 4.0 (Serie/Folio/Fecha/FormaPago/MetodoPago/Sello simulado)."""
    cert = f"{rng.getrandbits(80):020d}"[:20]
    return {
        "comprobante_attrs": (f'Serie="S4" Folio="{idx:04d}" Fecha="2026-10-2{rng.randint(0, 4)}T1{rng.randint(0, 9)}:{rng.randint(10, 59)}:00" '
                              f'FormaPago="03" MetodoPago="PUE" LugarExpedicion="64000" Exportacion="01" '
                              f'NoCertificado="{cert}" Sello="{_sello(rng, 48)}" '),
        "tfd_attrs": (f' Version="1.1" FechaTimbrado="2026-10-24T12:00:00" RfcProvCertif="SAT970701NN3" '
                      f'SelloCFD="{_sello(rng, 32)}" NoCertificadoSAT="00001000000504465028" SelloSAT="{_sello(rng, 48)}"'),
    }


def _spec_s4(rng: random.Random, catalogo: list[dict], idx: int, tipo: str, tipo_s4: str, **kw) -> dict:
    s = _spec_base(rng, catalogo, idx, tipo, **kw)
    s["id"] = f"S4-{idx:04d}"
    s.update(_atributos_cfdi40(rng, idx))
    # ~30% de las remisiones llega como foto escaneada (Nivel 2 visión); el resto es PDF digital (Nivel 1).
    if rng.random() < 0.30:
        s.update({"foto": True, "borrosa": False, "con_firma": True, "nota": rng.choice(
            ["Recibido conforme.", "Entrega completa en anden 3.", "Sin novedad.", "Recibio turno matutino."])})
    s["tipo_s4"] = tipo_s4
    return s


def iter_casos_s4(semilla: int = SEMILLA_S4, n: int = N_S4):
    """Generador streaming: produce los `n` specs de S4 uno por uno (nunca los retiene todos en memoria).

    El orden de tipos es una permutación barajada reproducible; un DUPLICATE siempre apunta a un caso
    limpio ya emitido, por eso nunca se coloca antes del primer MATCH_OK.
    """
    rng = random.Random(semilla)
    catalogo = construir_catalogo(rng)
    efos = cargar_efos_definitivos()
    tipos = [t for t, c in cuotas_s4(n) for _ in range(c)]
    rng.shuffle(tipos)
    limpios: list[dict] = []   # ventana acotada de originales posibles para duplicados
    for idx, tipo_s4 in enumerate(tipos, start=1):
        if tipo_s4 == "MATCH_OK":
            s = _spec_s4(rng, catalogo, idx, "MATCH_OK", tipo_s4)
            if rng.random() < 0.15:                       # precio dentro de tolerancia (centavo arriba)
                s["facturado"][0]["p"] += Decimal("0.01")
            limpios.append(s)
            del limpios[:-50]
        elif tipo_s4 == "QTY_SHORT":
            caros = rng.random() < 0.08                   # unos pocos exceden el límite autónomo y se escalan
            s = _spec_s4(rng, catalogo, idx, "QTY_SHORT", tipo_s4, n_lineas=1 if caros else None, caros=caros)
            for l in rng.sample(s["oc_lineas"], 1 if not caros else 1):
                faltan = max(1, int(l["cantidad"] * rng.randint(5, 60) / 100))
                if not caros:   # merma típica: la fuga queda bajo el límite autónomo (reclamable)
                    tope = int(FUGA_TIPICA_MAX / (l["precio"] * (1 + (l["tasa"] or 0))))
                    faltan = max(1, min(faltan, tope))
                s["recibido"][l["sku"]] = l["cantidad"] - faltan
        elif tipo_s4 == "PRICE_TAX":
            if rng.random() < 0.65:                       # sobreprecio unitario no pactado
                s = _spec_s4(rng, catalogo, idx, "PRICE_UP", tipo_s4)
                c = rng.choice(s["facturado"])
                tope_pct = FUGA_TIPICA_MAX / (Decimal(c["q"]) * c["p"] * (1 + (c["tasa"] or 0)))
                pct = Decimal(rng.randint(3, 25)) / 100
                c["p"] = _q(c["p"] * (1 + max(Decimal("0.03"), min(pct, tope_pct))))
            else:                                         # cálculo fiscal erróneo
                s = _spec_s4(rng, catalogo, idx, "TAX_MISMATCH", tipo_s4, n_lineas=2)
                if rng.random() < 0.5:
                    c = next((c for c in s["facturado"] if c["tasa"]), s["facturado"][0])
                    if c["tasa"]:
                        c["iva_override"] = _q(_q(Decimal(c["q"]) * c["p"]) * c["tasa"]) + Decimal(rng.randint(300, 9000)) / 100
                    else:
                        s["ajuste_total"] = Decimal(rng.randint(3000, 12000)) / 100
                else:
                    s["ajuste_total"] = Decimal(rng.randint(3000, 12000)) / 100
        elif tipo_s4 == "FX_OVERCHARGE":
            s = _spec_s4(rng, catalogo, idx, "FX_OVERCHARGE", tipo_s4)
            desvio = Decimal(rng.randint(300, 1500)) / 10000          # +3.00% .. +15.00% sobre el FIX
            tc = (FIX_REFERENCIA_USD * (1 + desvio)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            s.update({"moneda": "USD", "tipo_cambio": tc, "tipo_cambio_attr": f'TipoCambio="{tc:.4f}" '})
        elif tipo_s4 == "SUPPLIER_69B":
            s = _spec_s4(rng, catalogo, idx, "SUPPLIER_69B", tipo_s4)
            s.update({"proveedor": rng.choice(efos), "es_69b": True})
        else:  # FISCAL_RECHAZO: duplicado (UUID repetido) o factura cancelada ante el SAT
            if limpios and rng.random() < 0.5:
                orig = rng.choice(limpios)
                s = _spec_s4(rng, catalogo, idx, "DUPLICATE", tipo_s4)
                s.update({"proveedor": orig["proveedor"], "uuid": orig["uuid"], "oc_lineas": orig["oc_lineas"],
                          "recibido": dict(orig["recibido"]), "facturado": [dict(c) for c in orig["facturado"]],
                          "duplicado_de": orig["id"], "foto": False})
            else:
                s = _spec_s4(rng, catalogo, idx, "CFDI_CANCELADO", tipo_s4)
                s["cancelado"] = True
        yield s


def calcular_esperado_s4(spec: dict, total: Decimal) -> dict:
    """Ground truth S4: Decimal + ROUND_HALF_UP al centavo, sin usar src/. Reutiliza la regla contractual de S3.

    FX: los montos del CFDI/OC están en USD; lo justo se convierte al FIX oficial y lo facturado al TC del CFDI.
    """
    base = calcular_esperado({**spec, "id": spec["id"]}, total)
    codigos, estado = set(base["codigos"]), base["estado_final"]
    monto, fuga, total_mxn = Decimal(base["monto_a_pagar_mxn"]), Decimal(base["fuga_detectada_mxn"]), total
    if spec.get("moneda") == "USD":
        tc = spec["tipo_cambio"]
        total_mxn = _q(total * tc)
        if (tc - FIX_REFERENCIA_USD) / FIX_REFERENCIA_USD > TOLERANCIA_FX:
            codigos.discard("MATCH_OK")
            codigos.add("FX_OVERCHARGE")
            monto = _q(monto * FIX_REFERENCIA_USD)
            fuga = _q(max(total_mxn - monto, Decimal("0")))
        else:  # TC dentro de tolerancia: se paga al TC del CFDI
            monto, fuga = _q(monto * tc), _q(fuga * tc)
        estado = "APROBADO" if codigos == {"MATCH_OK"} else (
            "EN_RECLAMO" if codigos <= {"QTY_SHORT", "PRICE_UP"} and fuga <= LIMITE_AUTONOMO else "ESCALADO")
    if spec.get("cancelado"):
        codigos, monto, fuga, estado = {"CFDI_CANCELADO"}, Decimal("0.00"), total, "ESCALADO"
    resultado = {
        **base, "tipo_caso": spec["tipo"], "estado_final": estado, "codigos": sorted(codigos),
        "monto_a_pagar_mxn": f"{monto:.2f}", "fuga_detectada_mxn": f"{fuga:.2f}", "total_cfdi_mxn": f"{total_mxn:.2f}",
        # Alias con la nomenclatura del Sprint 4
        "monto_autorizado_mxn": f"{monto:.2f}",
        "fuga_retenida_mxn": f"{(Decimal('0') if estado == 'APROBADO' else fuga):.2f}",
        "codigos_discrepancia": sorted(codigos - {"MATCH_OK"}),
        "moneda": spec.get("moneda", "MXN"), "familia_s4": spec["tipo_s4"],
    }
    if spec.get("moneda") == "USD":
        resultado.update({"tipo_cambio_cfdi": f"{spec['tipo_cambio']:.4f}", "fix_oficial_referencia": f"{FIX_REFERENCIA_USD:.4f}",
                          "total_cfdi_usd": f"{total:.2f}"})
    return resultado


def escribir_caso_s4(spec: dict, salida: Path, rng_img: random.Random) -> None:
    p = salida / spec["id"]
    p.mkdir(parents=True, exist_ok=True)
    xml, total = generar_xml_s3(spec)
    (p / "cfdi.xml").write_text(xml, encoding="utf-8")
    oc = {"oc": spec["id"], "proveedor_rfc": spec["proveedor"]["rfc"], "proveedor": spec["proveedor"]["razon_social"],
          "moneda": spec.get("moneda", "MXN"), "simular_caida_sat": False, "fecha": "2026-10-20",
          "terminos": {"pago": "30 dias", "entrega": "LAB almacen central", "moneda_pago": "MXN"},
          "lineas": [{"sku": l["sku"], "descripcion": l["descripcion"], "unidad": l["unidad"], "cantidad": l["cantidad"],
                      "precio_unitario": f"{l['precio']:.2f}", "tasa_iva": str(l["tasa"] or Decimal("0")),
                      **({"exento": True} if l["tasa"] is None else {})} for l in spec["oc_lineas"]]}
    (p / "oc.json").write_text(json.dumps(oc, indent=2, ensure_ascii=False), encoding="utf-8")
    rem = {"oc_referencia": spec["id"], "tiene_sello_almacen": True, "tiene_firma_recepcion": True,
           "requiere_vision": bool(spec.get("foto")),
           "lineas": [{"sku": k, "cantidad_recibida": v} for k, v in spec["recibido"].items()]}
    if spec.get("foto"):
        rem["observaciones_manuales"] = spec["nota"]
        dibujar_foto_remision(p / "remision.png", spec, rng_img)
    else:
        dibujar_remision_pdf(p / "remision.pdf", spec)
    (p / "remision.json").write_text(json.dumps(rem, indent=2, ensure_ascii=False), encoding="utf-8")
    if spec.get("cancelado"):
        (p / "sat_estatus.json").write_text(json.dumps(
            {"uuid": spec["uuid"], "estado": "Cancelado", "es_cancelable": "Cancelable sin aceptacion",
             "fecha_cancelacion": "2026-10-26"}, indent=2), encoding="utf-8")
    (p / "esperado.json").write_text(json.dumps(calcular_esperado_s4(spec, total), indent=2, ensure_ascii=False),
                                     encoding="utf-8")


def generar_s4(semilla: int = SEMILLA_S4, salida: Path = OUT_S4, n: int = N_S4) -> list[str]:
    """Escribe n casos en `salida/S4-XXXX`. Reproducible byte a byte con la misma semilla."""
    salida.mkdir(parents=True, exist_ok=True)
    rng_img = random.Random(semilla + 1)
    ids = []
    for spec in iter_casos_s4(semilla, n):
        escribir_caso_s4(spec, salida, rng_img)
        ids.append(spec["id"])
    return ids


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--s2", action="store_true", help="Solo los 10 casos S2")
    ap.add_argument("--s3", action="store_true", help="Solo los 36 casos S3")
    ap.add_argument("--s4", action="store_true", help="Solo los 1,000 casos S4 (carga) en datasets/s4")
    ap.add_argument("--n", type=int, default=N_S4, help="Casos S4 a generar (default 1000)")
    ap.add_argument("--semilla", type=int, default=None)
    a = ap.parse_args()
    if a.s4:
        ids = generar_s4(a.semilla if a.semilla is not None else SEMILLA_S4, n=a.n)
        print(f"S4: {len(ids)} casos en datasets/s4: {ids[0]} .. {ids[-1]}")
        raise SystemExit(0)
    a.semilla = SEMILLA_DEFAULT if a.semilla is None else a.semilla
    if a.s2 or not a.s3:
        generar_todos()
        print("S2: 10 casos generados:", ", ".join(CASOS))
    if a.s3 or not a.s2:
        ids = generar_s3(a.semilla)
        print(f"S3: {len(ids)} casos en datasets/s3 (semilla {a.semilla}): {ids[0]} .. {ids[-1]}")
