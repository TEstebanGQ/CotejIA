"""Convierte reports/REPORTE_TECNICO_FINAL_COTEJAI.md en docs/Reporte_Tecnico_Final_CotejAI.pdf (A4, máx. 3 páginas).

Uso: python scripts/generate_final_report_pdf.py   (requiere `pip install markdown playwright` y `playwright install chromium`)
"""
import asyncio
from pathlib import Path

import markdown
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
FUENTE = ROOT / "reports" / "REPORTE_TECNICO_FINAL_COTEJAI.md"
SALIDA = ROOT / "docs" / "Reporte_Tecnico_Final_CotejAI.pdf"
MAX_PAGINAS = 3

CSS = """
@page { size: A4; margin: 13mm 15mm; }
body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: #18181b; }
h1 { font-size: 17pt; margin: 0 0 4px; color: #0f172a; }
h1 + p { color: #3f3f46; margin-top: 0; border-bottom: 2px solid #10b981; padding-bottom: 6px; }
h2 { font-size: 11.5pt; margin: 12px 0 4px; color: #047857; border-bottom: 1px solid #e4e4e7; padding-bottom: 2px; }
p, li { margin: 3px 0; }
ul, ol { padding-left: 18px; margin: 3px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 9pt; }
th, td { border: 1px solid #d4d4d8; padding: 3px 7px; text-align: left; }
th { background: #f4f4f5; }
td:nth-child(n+2) { text-align: right; }
code { font-family: Consolas, 'Roboto Mono', monospace; font-size: 8.4pt; background: #f4f4f5; padding: 0 3px; border-radius: 3px; }
pre { background: #0f172a; color: #e2e8f0; padding: 7px 10px; border-radius: 5px; font-size: 8.4pt; }
pre code { background: none; color: inherit; padding: 0; }
a { color: #047857; text-decoration: none; }
strong { color: #0f172a; }
"""


async def main() -> None:
    cuerpo = markdown.markdown(FUENTE.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
    html = f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cuerpo}</body></html>"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        await page.pdf(path=str(SALIDA), format="A4", print_background=True, prefer_css_page_size=True)
        await browser.close()
    try:
        import pdfplumber

        with pdfplumber.open(SALIDA) as pdf:
            n = len(pdf.pages)
        print(f"{SALIDA} · {n} páginas")
        if n > MAX_PAGINAS:
            raise SystemExit(f"El reporte excede {MAX_PAGINAS} páginas ({n}); recorta el Markdown.")
    except ImportError:
        print(SALIDA)


if __name__ == "__main__":
    asyncio.run(main())
