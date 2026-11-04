"""Script de automatización Playwright para actualizar capturas en docs/screenshots/."""
import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"

async def capture_all():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[Playwright] Navegando a http://localhost:8000...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # 1. Dashboard Principal con OC-004 activo
        print("[Playwright] Capturando 01_dashboard_principal_oc004.png...")
        await page.evaluate("cambiarVista('DASHBOARD')")
        await page.evaluate("seleccionarCaso('OC-004')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_dashboard_principal_oc004.png"))
        await page.screenshot(path=str(SCREENSHOTS_DIR / "01_dashboard_principal.png"))

        # 2. Modal Inspección Remisión Física (OC-004)
        print("[Playwright] Capturando 02_modal_inspeccion_remision_fisica.png...")
        await page.evaluate("abrirModalInspeccionDocumento('REMISION')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "02_modal_inspeccion_remision_fisica.png"))
        await page.evaluate("cerrarModalInspeccionDocumento()")
        await page.wait_for_timeout(400)

        # 3. Dashboard con OC-001 (Ficha Digital)
        print("[Playwright] Capturando 03_dashboard_oc001_digital.png...")
        await page.evaluate("seleccionarCaso('OC-001')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "03_dashboard_oc001_digital.png"))

        # 4. Modal Inspección Remisión Digital (OC-001)
        print("[Playwright] Capturando 04_modal_inspeccion_remision_digital.png...")
        await page.evaluate("abrirModalInspeccionDocumento('REMISION')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "04_modal_inspeccion_remision_digital.png"))
        await page.evaluate("cerrarModalInspeccionDocumento()")
        await page.wait_for_timeout(400)

        # 5. Tab Panel CFDI XML (OC-001)
        print("[Playwright] Capturando 05_tab_panel_cfdi_xml.png...")
        await page.evaluate("cambiarTabDocumento('CFDI')")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "05_tab_panel_cfdi_xml.png"))

        # 6. Modal Inspección CFDI XML
        print("[Playwright] Capturando 06_modal_inspeccion_cfdi_xml.png...")
        await page.evaluate("abrirModalInspeccionDocumento('CFDI')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "06_modal_inspeccion_cfdi_xml.png"))
        await page.evaluate("cerrarModalInspeccionDocumento()")
        await page.wait_for_timeout(400)

        # 7. Tab Panel Orden de Compra ERP (OC-001)
        print("[Playwright] Capturando 07_tab_panel_orden_compra.png...")
        await page.evaluate("cambiarTabDocumento('OC')")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "07_tab_panel_orden_compra.png"))

        # 8. Modal Inspección Orden de Compra ERP
        print("[Playwright] Capturando 08_modal_inspeccion_orden_compra.png...")
        await page.evaluate("abrirModalInspeccionDocumento('OC')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "08_modal_inspeccion_orden_compra.png"))
        await page.evaluate("cerrarModalInspeccionDocumento()")
        await page.wait_for_timeout(400)

        # 9. Caso OC-006 Sobreprecio Cambiario (FX_OVERCHARGE)
        print("[Playwright] Capturando 09_caso_oc006_fx_overcharge.png...")
        await page.evaluate("seleccionarCaso('OC-006')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "09_caso_oc006_fx_overcharge.png"))

        # 10. Diálogo In-App SAT SOAP
        print("[Playwright] Capturando 10_dialog_inapp_sat_soap.png...")
        await page.evaluate("probarSatEnVivo()")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "10_dialog_inapp_sat_soap.png"))
        await page.evaluate("cerrarAppDialog()")
        await page.wait_for_timeout(400)

        # 11. Vista Tabla General de Expedientes Lote S2
        print("[Playwright] Capturando 11_vista_tabla_expedientes.png...")
        await page.evaluate("cambiarVista('EXPEDIENTES')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "11_vista_tabla_expedientes.png"))

        await browser.close()
        print("[Playwright] ¡Todas las capturas actualizadas con éxito en docs/screenshots/!")

if __name__ == "__main__":
    asyncio.run(capture_all())
