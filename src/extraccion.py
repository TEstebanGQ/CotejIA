"""Extracción de remisiones por niveles. El Nivel 1 es local y determinista: sin red, sin LLM.

- PDF digital (texto seleccionable): `pdfplumber` lee la tabla de líneas.
- Escaneo/foto nítida: OCR local con `rapidocr` (opcional, carga perezosa).

Si todas las líneas cuadran con el formato esperado y tienen confianza >= UMBRAL_NIVEL1, el caso se
resuelve en Nivel 1 y el LLM recibe texto. En cualquier otro caso (tachones, notas a mano, líneas que no
cuadran) `resuelto` es False y debe intervenir el Nivel 2 (Grok Visión). El sello y la firma NUNCA se
validan aquí: un lector de texto no sabe si una firma existe.
"""
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

UMBRAL_NIVEL1 = 0.90
# SKU  descripción  [unidad]  cantidad
_FILA = re.compile(r"^(?P<sku>[A-Z]{3,5}-\d{3})\s+(?P<desc>.+?)\s+(?:(?P<unidad>pza|kg|caja|litro)\s+)?(?P<cant>\d+(?:\.\d+)?)$")
_TOL_Y = 6  # px: palabras con "top" cercano pertenecen a la misma fila


def _resultado(metodo: str, lineas: list[dict], motivo: str | None = None, forzar_nivel2: bool = False) -> dict:
    conf_min = min((l["confianza"] for l in lineas), default=0.0)
    resuelto = bool(lineas) and conf_min >= UMBRAL_NIVEL1 and not forzar_nivel2
    return {"nivel": 1 if resuelto else 2, "resuelto": resuelto, "metodo": metodo, "lineas": lineas,
            "confianza_minima": round(conf_min, 2),
            "motivo": None if resuelto else (motivo or "Sin líneas legibles con confianza suficiente")}


def _cant(txt: str):
    try:
        d = Decimal(txt)
    except InvalidOperation:
        return None
    return int(d) if d == d.to_integral_value() else float(d)


def extraer_pdf(ruta: Path) -> dict:
    """Nivel 1 sobre PDF digital. Una línea tachada (trazo que cruza el texto) baja la confianza a 0.40."""
    import pdfplumber
    lineas, descartadas = [], 0
    with pdfplumber.open(ruta) as pdf:
        pagina = pdf.pages[0]
        tachones = [l for l in pagina.lines if abs(l["top"] - l["bottom"]) < 8 and abs(l["x1"] - l["x0"]) > 6]
        filas: dict[int, list[dict]] = {}
        for w in pagina.extract_words(keep_blank_chars=False):
            clave = next((k for k in filas if abs(k - w["top"]) <= _TOL_Y), round(w["top"]))
            filas.setdefault(clave, []).append(w)
        for _, palabras in sorted(filas.items()):
            palabras.sort(key=lambda w: w["x0"])
            m = _FILA.match(" ".join(w["text"] for w in palabras))
            if not m:
                if palabras and re.match(r"^[A-Z]{3,5}-\d{3}$", palabras[0]["text"]):
                    descartadas += 1   # parece fila de producto pero no cuadra con el formato
                continue
            tachada = any(t["x0"] - 2 <= w["x1"] and t["x1"] + 2 >= w["x0"] and w["top"] - 2 <= t["top"] <= w["bottom"] + 2
                          for t in tachones for w in palabras[-1:])
            lineas.append({"sku": m["sku"], "cantidad_recibida": _cant(m["cant"]),
                           "confianza": 0.40 if tachada else 0.99})
    motivo = f"{descartadas} fila(s) no cuadran con el formato de remisión" if descartadas else None
    return _resultado("pdfplumber", lineas, motivo, forzar_nivel2=bool(descartadas))


def extraer_imagen_ocr(ruta: Path) -> dict:
    """Nivel 1b: OCR local (rapidocr). Solo útil con escaneos nítidos; fotos y manuscritos pasan a Nivel 2."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return {"nivel": 2, "resuelto": False, "metodo": "rapidocr", "lineas": [], "confianza_minima": 0.0,
                "motivo": "rapidocr no instalado"}
    resultado, _ = RapidOCR()(str(ruta))
    filas: dict[int, list[tuple]] = {}
    for caja, texto, conf in resultado or []:
        y = caja[0][1]
        clave = next((k for k in filas if abs(k - y) <= _TOL_Y * 2), round(y))
        filas.setdefault(clave, []).append((caja[0][0], texto, float(conf)))
    lineas = []
    for _, cajas in sorted(filas.items()):
        cajas.sort()
        m = _FILA.match(" ".join(t for _, t, _ in cajas))
        if m:
            lineas.append({"sku": m["sku"], "cantidad_recibida": _cant(m["cant"]),
                           "confianza": round(min(c for _, _, c in cajas), 2)})
    return _resultado("rapidocr", lineas)


def extraer_remision_local(carpeta: Path, usar_ocr: bool = False) -> dict | None:
    """Intenta el Nivel 1 en la carpeta del caso. None si no hay PDF (ni OCR habilitado con imagen)."""
    pdf = carpeta / "remision.pdf"
    if pdf.exists():
        return extraer_pdf(pdf)
    png = carpeta / "remision.png"
    if usar_ocr and png.exists():
        return extraer_imagen_ocr(png)
    return None
