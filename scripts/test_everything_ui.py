import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path("docs/screenshots/live_run")
OUT.mkdir(parents=True, exist_ok=True)

async def run_ui_sweep():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 920})
        page = await context.new_page()

        print("[1] Cargando Dashboard inicial (http://localhost:8000)...")
        await page.goto("http://localhost:8000")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(OUT / "01_dashboard_inicial_oc004.png"))
        print("  ✓ 01_dashboard_inicial_oc004.png")

        # 2. Probar Modal de Datos de Remisión Física en OC-004
        print("[2] Probando Modal de Remisión Física (OC-004)...")
        await page.click('#pane-doc-remision #view-remision-activa button:has-text("Datos")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "02_modal_remision_oc004_datos.png"))
        print("  ✓ 02_modal_remision_oc004_datos.png")
        await page.click('#modal-doc-btn-copy')
        await page.wait_for_timeout(200)
        await page.click('#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(400)

        # 3. Probar navegación a OC-001 (Caso Digital sin foto)
        print("[3] Navegando a OC-001 (Digital)...")
        await page.evaluate("inspeccionarYIrADashboard('OC-001')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "03_dashboard_oc001.png"))
        print("  ✓ 03_dashboard_oc001.png")

        # 4. Probar Ficha Digital de Recepción en OC-001
        print("[4] Probando Ficha Digital de Recepción...")
        await page.click('#pane-doc-remision #view-remision-empty button:has-text("Revisar Documento")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "04_modal_remision_digital_oc001.png"))
        print("  ✓ 04_modal_remision_digital_oc001.png")
        await page.click('#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(300)

        # 5. Probar Pestaña Factura XML y su Modal
        print("[5] Probando Pestaña Factura XML y visor SAT...")
        await page.click('#tab-doc-btn-cfdi')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "05_tab_cfdi_xml.png"))
        print("  ✓ 05_tab_cfdi_xml.png")
        await page.click('#pane-doc-cfdi button:has-text("Inspeccionar XML SAT")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "06_modal_inspeccion_cfdi_xml.png"))
        print("  ✓ 06_modal_inspeccion_cfdi_xml.png")
        await page.click('#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(300)

        # 6. Probar Pestaña Orden ERP y su Modal
        print("[6] Probando Pestaña Orden ERP y partidas...")
        await page.click('#tab-doc-btn-oc')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "07_tab_orden_compra.png"))
        print("  ✓ 07_tab_orden_compra.png")
        await page.click('#pane-doc-oc button:has-text("Revisar Partidas de OC")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "08_modal_inspeccion_orden_compra.png"))
        print("  ✓ 08_modal_inspeccion_orden_compra.png")
        await page.click('#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(300)

        # 7. Probar Clic en las 3 cajas de la Tríada
        print("[7] Probando interacción clickeable en la Tríada de 3 vías...")
        await page.click('#box-remision-triad')
        await page.wait_for_timeout(200)
        await page.click('div[onclick*="\'CFDI\'"]')
        await page.wait_for_timeout(200)
        await page.click('div[onclick*="\'OC\'"]')
        await page.wait_for_timeout(200)

        # 8. Probar Navegación de Flechas (Anterior / Siguiente)
        print("[8] Probando flechas de navegación de casos...")
        await page.click('button[onclick*="navegarCasoSiguiente"]')
        await page.wait_for_timeout(400)
        await page.click('button[onclick*="navegarCasoAnterior"]')
        await page.wait_for_timeout(400)

        # 9. Probar Caso OC-006 (Sobreprecio Cambiario Banxico)
        print("[9] Probando Caso OC-006 (Sobreprecio Cambiario Banxico)...")
        await page.evaluate("inspeccionarYIrADashboard('OC-006')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "09_caso_oc006_fx_overcharge.png"))
        print("  ✓ 09_caso_oc006_fx_overcharge.png")

        # 10. Probar Cambio de Moneda en Dropdown de Divisas
        print("[10] Probando selector de 180 divisas...")
        await page.wait_for_selector('#select-fx-moneda')
        await page.select_option('#select-fx-moneda', 'EUR')
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "10_selector_divisa_eur.png"))
        print("  ✓ 10_selector_divisa_eur.png")
        await page.select_option('#select-fx-moneda', 'USD')
        await page.wait_for_timeout(300)

        # 11. Probar Diálogo In-App SAT 4.0
        print("[11] Probando Diálogo In-App SAT 4.0...")
        await page.click('button:has-text("Conciliación SAT 4.0")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "11_dialog_inapp_sat.png"))
        print("  ✓ 11_dialog_inapp_sat.png")
        await page.click('#app-dialog-btn-primary')
        await page.wait_for_timeout(300)

        # 12. Probar Diálogo In-App Lista 69-B
        print("[12] Probando Diálogo In-App Lista 69-B...")
        await page.click('button:has-text("Lista 69-B (EFOS)")')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "12_dialog_inapp_69b.png"))
        print("  ✓ 12_dialog_inapp_69b.png")
        await page.click('#app-dialog-btn-primary')
        await page.wait_for_timeout(300)

        # 13. Probar Grok Vision en Vivo (en OC-004)
        print("[13] Probando Diálogo Grok Vision en Vivo...")
        await page.evaluate("inspeccionarYIrADashboard('OC-004')")
        await page.wait_for_timeout(500)
        await page.evaluate("probarVisionEnVivo()")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "13_dialog_inapp_grok_vision.png"))
        print("  ✓ 13_dialog_inapp_grok_vision.png")
        await page.click('#app-dialog-btn-primary')
        await page.wait_for_timeout(300)

        # 14. Probar Toasts y Diálogos de Acciones (Aprobar, Acta, Nota de Crédito)
        print("[14] Probando botones de acción y Toasts...")
        await page.click('#btn-aprobar-parcial')
        await page.wait_for_timeout(400)
        await page.click('button:has-text("Acta Circunstanciada")')
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "14_toasts_acciones.png"))
        print("  ✓ 14_toasts_acciones.png")

        # Probar Solicitar Nota de Crédito (Policy Gate Dialog)
        await page.click('#btn-solicitar-nc')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "15_dialog_policy_gate_nc.png"))
        print("  ✓ 15_dialog_policy_gate_nc.png")
        await page.click('#app-dialog-btn-primary')
        await page.wait_for_timeout(300)

        # 15. Probar Modal de Carga Manual de Documentos (+ Nuevo Cotejo)
        print("[15] Probando Modal de Carga Manual (Nuevo Cotejo)...")
        await page.click('button[onclick*="abrirModalUpload"]')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "16_modal_carga_manual.png"))
        print("  ✓ 16_modal_carga_manual.png")
        await page.click('#modal-upload button:has-text("Cancelar")')
        await page.wait_for_timeout(300)

        # 16. Probar Vista de Tabla de Expedientes, Filtros y Buscador
        print("[16] Probando Tabla de Expedientes, Filtros y Buscador...")
        await page.click('#nav-expedientes')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "17_tabla_expedientes_general.png"))
        print("  ✓ 17_tabla_expedientes_general.png")

        # Probar filtro EN_RECLAMO
        await page.click('button[data-tab="EN_RECLAMO"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "18_tabla_filtro_reclamo.png"))
        print("  ✓ 18_tabla_filtro_reclamo.png")

        # Probar filtro ESCALADO
        await page.click('button[data-tab="ESCALADO"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "19_tabla_filtro_escalado.png"))
        print("  ✓ 19_tabla_filtro_escalado.png")

        # Probar Buscador ⌘K
        await page.click('button[data-tab="TODOS"]')
        await page.wait_for_timeout(200)
        await page.fill('#buscador-expediente', 'OC-006')
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "20_buscador_filtrado.png"))
        print("  ✓ 20_buscador_filtrado.png")

        await browser.close()
        print("\n🎉 ¡TODAS las pruebas de UI, modales, pestañas, diálogos y acciones se ejecutaron exitosamente!")

asyncio.run(run_ui_sweep())
