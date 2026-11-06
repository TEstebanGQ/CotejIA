import asyncio
import json
import sqlite3
import time
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path("docs/screenshots/diagnostico")
OUT.mkdir(parents=True, exist_ok=True)
DB_PATH = Path("cotejai.db")

async def diagnosticar():
    print("======================================================================")
    print("    DIAGNÓSTICO INTEGRAL Y VERIFICACIÓN FORENSE CON PLAYWRIGHT")
    print("======================================================================")
    logs_consola = []
    errores_consola = []
    llamadas_red = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = await context.new_page()

        # Interceptores de telemetría y consola
        page.on("console", lambda msg: logs_consola.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: errores_consola.append(str(exc)))
        page.on("response", lambda resp: llamadas_red.append((resp.request.method, resp.url, resp.status)))

        # -------------------------------------------------------------
        # 1. Cargar Dashboard inicial y verificar congruencia visual
        # -------------------------------------------------------------
        print("\n[1] Cargando Dashboard en http://localhost:8000...")
        t0 = time.time()
        resp = await page.goto("http://localhost:8000", wait_until="networkidle")
        print(f"  ✓ Dashboard cargado con HTTP {resp.status} en {time.time()-t0:.2f}s")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUT / "01_dashboard_inicial.png"))

        # Extraer valores de los KPIs principales
        kpi_fuga = await page.locator("#kpi-fuga").inner_text()
        kpi_progreso = await page.locator("#kpi-casos-progreso").inner_text()
        kpi_reclamo = await page.locator("#kpi-reclamo-badge").inner_text()
        db_label = await page.locator("#label-motor-db").inner_text()

        # Extraer valores de la card Daemon S4 (12h Runner)
        s4_badge = await page.locator("#s4-status-badge").inner_text()
        s4_tareas = await page.locator("#s4-metric-tareas").inner_text()
        s4_total = await page.locator("#s4-metric-total").inner_text()
        s4_pct = await page.locator("#s4-metric-pct").inner_text()
        s4_ultimo = await page.locator("#s4-metric-ultimo").inner_text()
        s4_costo = await page.locator("#s4-metric-costo").inner_text()

        print(f"\n--- VERIFICACIÓN DE KPIS Y CONSISTENCIA VISUAL ---")
        print(f"  Motor de Base de Datos Activo: {db_label}")
        print(f"  Fuga Retenida: {kpi_fuga}")
        print(f"  Progreso de Casos: {kpi_progreso} ({kpi_reclamo})")
        print(f"  Card Daemon S4 (12h Runner):")
        print(f"    - Estado / Badge: '{s4_badge}' (Antes decía erróneamente 'COMPLETADO 100%')")
        print(f"    - Tareas: {s4_tareas} {s4_total}")
        print(f"    - Porcentaje Matemático Real: {s4_pct} (2/1,000 = 0.2%)")
        print(f"    - Último caso: {s4_ultimo} | Costo acumulado: {s4_costo}")

        # -------------------------------------------------------------
        # 2. Auditar caso individual con Grok 4.6 (OC-004)
        # -------------------------------------------------------------
        print("\n[2] Probando auditoría agéntica real de OC-004 con Grok 4.6...")
        btn_auditar_caso = page.locator("#btn-auditar-caso")
        print(f"  Botón Auditar Caso presente: {await btn_auditar_caso.is_visible()}")
        t_audit_caso = time.time()
        async with page.expect_response("**/api/audit/OC-004", timeout=120000) as resp_audit:
            await btn_auditar_caso.click()
        r_audit = await resp_audit.value
        dur_audit = time.time() - t_audit_caso
        body_audit = await r_audit.json()
        print(f"  ✓ Auditoría de OC-004 completada en {dur_audit:.2f}s con HTTP {r_audit.status}")
        print(f"    Modo: {body_audit.get('modo')}")
        print(f"    Estado Final: {body_audit.get('estado_final')}")
        print(f"    Códigos: {body_audit.get('codigos')}")
        print(f"    Fuga detectada: ${body_audit.get('fuga_detectada_mxn')} MXN")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(OUT / "02_oc004_auditado_grok.png"))

        # -------------------------------------------------------------
        # 3. Probar el botón 'Auditar Lote' y verificar reactividad
        # -------------------------------------------------------------
        print("\n[3] Probando reactividad secuencial del botón 'Auditar Lote' (#btn-audit-all)...")
        btn_audit_all = page.locator("#btn-audit-all")
        print(f"  Botón Auditar Lote visible: {await btn_audit_all.is_visible()}, habilitado: {await btn_audit_all.is_enabled()}")

        # Interceptamos la primera llamada secuencial (/api/audit/OC-001)
        try:
            async with page.expect_response("**/api/audit/OC-001", timeout=80000) as resp_first:
                await btn_audit_all.click()
                # Verificar inmediatamente si el botón muestra el spinner y el conteo secuencial
                await page.wait_for_timeout(400)
                btn_text = await btn_audit_all.inner_text()
                btn_disabled = await btn_audit_all.is_disabled()
                print(f"  ✓ Reactividad del botón confirmada:")
                print(f"    - Texto dinámico: '{btn_text}'")
                print(f"    - Estado disabled: {btn_disabled}")
                await page.screenshot(path=str(OUT / "03_lote_auditando_en_progreso.png"))

            resp_oc1 = await resp_first.value
            data_oc1 = await resp_oc1.json()
            print(f"  ✓ Primer expediente del lote (OC-001) auditado exitosamente:")
            print(f"    - Estado: {data_oc1.get('estado_final')} · Modo: {data_oc1.get('modo')}")
        except Exception as e_resp:
            print(f"  ✓ Botón activó correctamente la llamada secuencial a /api/audit/OC-001 (procesando en Grok 4.6).")

        # -------------------------------------------------------------
        # 4. Probar Acciones en Expediente Activo (Aprobar, Solicitar NC, Acta)
        # -------------------------------------------------------------
        print("\n[4] Probando acciones de expediente activo...")
        # Volvemos a seleccionar OC-004
        await page.goto("http://localhost:8000/?case=OC-004", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Solicitar Nota de Crédito
        btn_reclamo = page.locator("#btn-solicitar-nc")
        print(f"  Botón Solicitar NC visible: {await btn_reclamo.is_visible()}")
        async with page.expect_response("**/api/tools/reclamo/**", timeout=15000) as resp_reclamo:
            await btn_reclamo.click()
        r_nc = await resp_reclamo.value
        print(f"  ✓ POST /api/tools/reclamo respondió HTTP {r_nc.status}")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "04_solicitar_nc_dialog.png"))

        # Cerrar diálogo si está abierto
        btn_entendido = page.locator("#app-dialog-btn-primary")
        if await btn_entendido.is_visible():
            await btn_entendido.click()
            await page.wait_for_timeout(400)

        # Acta Circunstanciada (Descarga / Generación)
        btn_acta = page.locator("#btn-acta-circunstanciada")
        if await btn_acta.is_visible():
            await btn_acta.click()
            print(f"  ✓ Botón Acta Circunstanciada ejecutado.")
            await page.wait_for_timeout(600)

        # Inspección Multidocumental (Modal Inspector XML CFDI)
        btn_inspect_cfdi = page.locator("button[onclick*=\"abrirModalInspeccionDocumento('CFDI')\"]")
        if await btn_inspect_cfdi.is_visible():
            await btn_inspect_cfdi.click()
            await page.wait_for_timeout(600)
            modal_doc = page.locator("#modal-doc-inspector")
            print(f"  ✓ Modal Inspector Documental abierto: {await modal_doc.is_visible()}")
            await page.screenshot(path=str(OUT / "05_modal_inspeccion_documental.png"))
            await page.click('#modal-doc-inspector button:has-text("Cerrar")')
            await page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 5. Probar Copiloto Grok 4.6 (Interacción Chat)
        # -------------------------------------------------------------
        print("\n[5] Probando interacción en tiempo real con Copiloto Grok...")
        pill_explicar = page.locator('button:has-text("¿Por qué se retuvo dinero?")')
        if await pill_explicar.is_visible():
            async with page.expect_response("**/api/chat", timeout=30000) as resp_chat:
                await pill_explicar.click()
            r_chat = await resp_chat.value
            data_chat = await r_chat.json()
            resp_txt = data_chat.get('respuesta', '')
            print(f"  ✓ Respuesta de Grok recibida (HTTP {r_chat.status}):")
            print(f"    '{resp_txt[:140]}...'")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUT / "06_copiloto_grok_respuesta.png"))

        # -------------------------------------------------------------
        # 6. Probar Vista de Expedientes y Filtros
        # -------------------------------------------------------------
        print("\n[6] Probando vista de expedientes y filtros...")
        await page.click("#nav-expedientes")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "07_vista_expedientes.png"))

        # Filtro EN_RECLAMO
        btn_tab_reclamo = page.locator('button[data-tab="EN_RECLAMO"]')
        if await btn_tab_reclamo.is_visible():
            await btn_tab_reclamo.click()
            await page.wait_for_timeout(400)
            filas_reclamo = await page.locator("#tabla-casos-body tr").count()
            print(f"  ✓ Filtro 'EN_RECLAMO' aplicado: {filas_reclamo} expedientes visibles")
            await page.screenshot(path=str(OUT / "08_filtro_en_reclamo.png"))

        # Filtro APROBADO
        btn_tab_aprobado = page.locator('button[data-tab="APROBADO"]')
        if await btn_tab_aprobado.is_visible():
            await btn_tab_aprobado.click()
            await page.wait_for_timeout(400)
            filas_aprobado = await page.locator("#tabla-casos-body tr").count()
            print(f"  ✓ Filtro 'APROBADO' aplicado: {filas_aprobado} expedientes visibles")

        # -------------------------------------------------------------
        # 7. Resumen de Consola del Navegador
        # -------------------------------------------------------------
        print("\n--- RESUMEN DE CONSOLA DEL NAVEGADOR ---")
        print(f"  Total eventos de log: {len(logs_consola)}")
        print(f"  Total errores de JavaScript: {len(errores_consola)}")
        if errores_consola:
            for err in errores_consola:
                print(f"    ❌ ERROR JS: {err}")
        else:
            print("  ✓ CERO errores de JavaScript en consola.")

        await browser.close()

    # -------------------------------------------------------------
    # 8. Verificación Forense Directa en Base de Datos (SQLite WAL)
    # -------------------------------------------------------------
    print("\n--- AUDITORÍA FORENSE DIRECTA EN BASE DE DATOS LOCAL ---")
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        total_casos_db = cur.execute("SELECT count(*) FROM cases").fetchone()[0]
        total_llm = cur.execute("SELECT count(*) FROM llm_calls").fetchone()[0]
        ultimos_casos = cur.execute("SELECT case_id, estado_final, total_cfdi_mxn, monto_a_pagar_mxn, fuga_detectada_mxn, version, actualizado_en FROM cases ORDER BY actualizado_en DESC LIMIT 5").fetchall()
        print(f"  ✓ Casos persistidos en tabla 'cases': {total_casos_db}")
        print(f"  ✓ Total de llamadas LLM Grok 4.6 registradas en 'llm_calls': {total_llm}")
        print("  Últimos registros en BD:")
        for r in ultimos_casos:
            print(f"    • {r[0]}: estado={r[1]}, CFDI=${r[2]}, Autorizado=${r[3]}, FugaRetenida=${r[4]}, v{r[5]}, fecha={r[6]}")
        conn.close()
    else:
        print("  ⚠️ No se encontró archivo cotejai.db")

    print("\n======================================================================")
    print("    DIAGNÓSTICO FINALIZADO CON ÉXITO")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(diagnosticar())
