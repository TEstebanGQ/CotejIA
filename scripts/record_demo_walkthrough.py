import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT / "docs" / "videos"
TEMP_DIR = VIDEOS_DIR / "temp_record"
VOICEOVER_MP3 = VIDEOS_DIR / "voiceover_cotejai_walkthrough.mp3"
OUTPUT_MP4 = VIDEOS_DIR / "demo_cotejai_agente.mp4"

CURSOR_AND_SUBTITLES_JS = """
(() => {
    if (document.getElementById('virtual-cursor-container')) return;
    
    // Contenedor Cursor
    const container = document.createElement('div');
    container.id = 'virtual-cursor-container';
    container.innerHTML = `
        <div id="v-cursor" style="
            position: fixed;
            top: 0; left: 0;
            width: 22px; height: 22px;
            pointer-events: none;
            z-index: 9999999;
            transform: translate(-100px, -100px);
            transition: transform 0.28s cubic-bezier(0.25, 1, 0.5, 1);
            filter: drop-shadow(0 2px 5px rgba(0,0,0,0.45));
        ">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="#10b981" stroke="#ffffff" stroke-width="1.6">
                <path d="M3 3l7 18 3-7 7-3L3 3z"/>
            </svg>
        </div>
    `;
    document.body.appendChild(container);

    // Contenedor Subtítulos Flotantes Broadcast
    const sub = document.createElement('div');
    sub.id = 'v-subtitle';
    sub.style.cssText = `
        position: fixed;
        bottom: 26px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(12, 13, 16, 0.94);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(16, 185, 129, 0.45);
        color: #f4f4f5;
        padding: 9px 26px;
        border-radius: 9999px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13.5px;
        font-weight: 500;
        z-index: 9999990;
        box-shadow: 0 12px 35px -5px rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        gap: 12px;
        opacity: 0;
        transition: opacity 0.35s ease, transform 0.35s ease;
        max-width: 84%;
        text-align: center;
        pointer-events: none;
        line-height: 1.4;
    `;
    document.body.appendChild(sub);

    window.updateVirtualCursor = (x, y) => {
        const cursor = document.getElementById('v-cursor');
        if (cursor) cursor.style.transform = `translate(${x}px, ${y}px)`;
    };

    window.showClickRipple = (x, y) => {
        const ripple = document.createElement('div');
        ripple.style.position = 'fixed';
        ripple.style.left = `${x - 16}px`;
        ripple.style.top = `${y - 16}px`;
        ripple.style.width = '32px';
        ripple.style.height = '32px';
        ripple.style.borderRadius = '50%';
        ripple.style.border = '2px solid #10b981';
        ripple.style.backgroundColor = 'rgba(16, 185, 129, 0.28)';
        ripple.style.pointerEvents = 'none';
        ripple.style.zIndex = '9999998';
        ripple.style.transform = 'scale(0.5)';
        ripple.style.opacity = '1';
        ripple.style.transition = 'transform 0.35s ease-out, opacity 0.35s ease-out';
        document.body.appendChild(ripple);
        
        requestAnimationFrame(() => {
            ripple.style.transform = 'scale(1.85)';
            ripple.style.opacity = '0';
        });
        setTimeout(() => ripple.remove(), 400);
    };

    window.setSubtitle = (text) => {
        const el = document.getElementById('v-subtitle');
        if (!el) return;
        if (!text) {
            el.style.opacity = '0';
            el.style.transform = 'translateX(-50%) translateY(20px)';
        } else {
            el.innerHTML = `<span style="background: rgba(16,185,129,0.18); color: #34d399; font-weight: 700; padding: 2px 10px; border-radius: 6px; font-size: 12px; border: 1px solid rgba(16,185,129,0.35); text-transform: uppercase; letter-spacing: 0.5px;">CotejAI Audio</span> <span>${text}</span>`;
            el.style.opacity = '1';
            el.style.transform = 'translateX(-50%) translateY(0)';
        }
    };
})();
"""

async def smooth_move_to_element(page, selector, offset_x=0, offset_y=0):
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=3000)
        box = await el.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + offset_x
            y = box["y"] + box["height"] / 2 + offset_y
            await page.evaluate(f"window.updateVirtualCursor({x}, {y})")
            await page.wait_for_timeout(280)
            return x, y
    except Exception:
        pass
    return None

async def smooth_click(page, selector):
    pos = await smooth_move_to_element(page, selector)
    if pos:
        x, y = pos
        await page.evaluate(f"window.showClickRipple({x}, {y})")
        await page.wait_for_timeout(140)
    try:
        await page.click(selector, timeout=3000)
    except Exception:
        pass
    await page.wait_for_timeout(350)

async def wait_until_target(page, start_time, target_sec):
    elapsed = time.time() - start_time
    rem = target_sec - elapsed
    if rem > 0:
        await page.wait_for_timeout(int(rem * 1000))

async def record_walkthrough():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEMP_DIR.glob("*.webm"):
        f.unlink()

    print("🚀 [1/4] Iniciando Chromium 1080p para grabación técnica sincronizada...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(TEMP_DIR),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        print("🎬 [2/4] Ejecutando recorrido de pantalla al compás del audio generado...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.evaluate(CURSOR_AND_SUBTITLES_JS)
        await page.evaluate("window.updateVirtualCursor(960, 540)")

        start_time = time.time()

        # ==========================================
        # ESCENA 1 (0.00s – 21.00s): Dashboard General y KPIs
        # ==========================================
        print("  ▶ [0:00 - 0:21] Escena 1: Introducción Técnica y Métricas Clave")
        await page.evaluate("window.setSubtitle('Plataforma CotejAI operando sobre un lote real de cuentas por pagar.')")
        await page.evaluate("seleccionarCaso('OC-004')")
        await page.wait_for_timeout(1000)

        await smooth_move_to_element(page, '#kpi-fuga-retenida')
        await page.wait_for_timeout(1800)
        await smooth_move_to_element(page, '#kpi-casos-auditados')
        await page.wait_for_timeout(1800)

        await page.evaluate("window.setSubtitle('Fuga retenida de más de $42,000 MXN con 94% de resolución autónoma a $0.53 MXN por factura.')")
        await smooth_move_to_element(page, '#kpi-resolucion-autonoma')
        await page.wait_for_timeout(1800)
        await smooth_move_to_element(page, '#kpi-costo-promedio')
        await page.wait_for_timeout(1800)
        await smooth_move_to_element(page, '#label-motor-db')
        await wait_until_target(page, start_time, 21.00)

        # ==========================================
        # ESCENA 2 (21.00s – 44.86s): Caso OC-004 y Remisión Física con Merma
        # ==========================================
        print("  ▶ [0:21 - 0:44] Escena 2: Remisión Física y Lectura de Merma con Grok Vision")
        await page.evaluate("window.setSubtitle('Expediente OC-004: fotografía física de la remisión escaneada en almacén.')")
        await smooth_move_to_element(page, '#pane-doc-remision')
        await page.wait_for_timeout(1400)
        await smooth_click(page, '#pane-doc-remision #view-remision-activa button:has-text("Datos")')
        await page.wait_for_timeout(2500)

        await page.evaluate("window.setSubtitle('Grok Vision identifica sello oficial, firma y nota manuscrita: solo 80 piezas recibidas por merma.')")
        await page.wait_for_timeout(3500)
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await wait_until_target(page, start_time, 44.86)

        # ==========================================
        # ESCENA 3 (44.86s – 64.18s): Tríada de Conciliación a Tres Vías
        # ==========================================
        print("  ▶ [0:44 - 1:04] Escena 3: Tríada de 3 Vías (OC 100 vs Remisión 80 vs Factura 100)")
        await page.evaluate("window.setSubtitle('Conciliación a 3 vías: Orden por 100 pzas, Remisión física por 80 pzas y Factura CFDI por 100.')")
        await smooth_move_to_element(page, 'div[onclick*="\'OC\'"]')
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, '#box-remision-triad')
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, 'div[onclick*="\'CFDI\'"]')
        await page.wait_for_timeout(1500)

        await page.evaluate("window.setSubtitle('Retención preventiva calculada de $5,800.00 MXN con IVA incluido antes del pago.')")
        await smooth_move_to_element(page, 'div:has-text("Fuga Retenida")')
        await wait_until_target(page, start_time, 64.18)

        # ==========================================
        # ESCENA 4 (64.18s – 84.63s): Pestañas CFDI 4.0 XML y Orden ERP
        # ==========================================
        print("  ▶ [1:04 - 1:24] Escena 4: Pestaña Factura XML SAT y Pestaña Orden ERP")
        await page.evaluate("window.setSubtitle('Pestaña CFDI 4.0 XML: comprobación de Folio Fiscal UUID, RFC de emisor y sello digital SAT.')")
        await smooth_click(page, '#tab-doc-btn-cfdi')
        await page.wait_for_timeout(1200)
        await smooth_click(page, '#pane-doc-cfdi button:has-text("Inspeccionar XML SAT")')
        await page.wait_for_timeout(2500)
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(800)

        await page.evaluate("window.setSubtitle('Pestaña Orden ERP: verificación de precios unitarios pactados contractualmente.')")
        await smooth_click(page, '#tab-doc-btn-oc')
        await page.wait_for_timeout(1200)
        await smooth_click(page, '#pane-doc-oc button:has-text("Revisar Partidas de OC")')
        await page.wait_for_timeout(2000)
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await wait_until_target(page, start_time, 84.63)

        # ==========================================
        # ESCENA 5 (84.63s – 109.57s): Caso OC-006 y Auditoría Cambiaria Banxico (180 Divisas)
        # ==========================================
        print("  ▶ [1:24 - 1:49] Escena 5: Caso OC-006 y Catálogo Oficial de 180 Divisas Banxico")
        await page.evaluate("window.setSubtitle('Caso OC-006 facturado en dólares: conexión en tiempo real con 180 divisas del SAT y Banxico.')")
        await page.evaluate("inspeccionarYIrADashboard('OC-006')")
        await page.wait_for_timeout(1200)

        await smooth_move_to_element(page, '#select-fx-moneda')
        await page.wait_for_timeout(800)
        await page.select_option('#select-fx-moneda', 'EUR')
        await page.wait_for_timeout(2000)
        await page.select_option('#select-fx-moneda', 'USD')
        await page.wait_for_timeout(1600)

        await page.evaluate("window.setSubtitle('Tipo de cambio inflado detectado a $21.85: congelando $19,707 MXN por sobrecargo cambiario.')")
        await smooth_move_to_element(page, '#badge-status-dashboard')
        await page.wait_for_timeout(2200)
        await smooth_move_to_element(page, 'div:has-text("FX_OVERCHARGE")')
        await wait_until_target(page, start_time, 109.57)

        # ==========================================
        # ESCENA 6 (109.57s – 129.32s): Seguridad Fiscal SAT y Lista Negra 69-B
        # ==========================================
        print("  ▶ [1:49 - 2:09] Escena 6: Consulta SOAP del SAT y Verificación Anti-EFOS 69-B")
        await page.evaluate("window.setSubtitle('Consulta SOAP del SAT: comprobación de vigencia del CFDI y estatus ante la autoridad fiscal.')")
        await smooth_click(page, 'button:has-text("Conciliación SAT 4.0")')
        await page.wait_for_timeout(2800)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(1000)

        await page.evaluate("window.setSubtitle('Auditoría automática contra el Art. 69-B del CFF descartando empresas facturadoras simuladas (EFOS).')")
        await smooth_click(page, 'button:has-text("Lista 69-B (EFOS)")')
        await page.wait_for_timeout(2800)
        await smooth_click(page, '#app-dialog-btn-primary')
        await wait_until_target(page, start_time, 129.32)

        # ==========================================
        # ESCENA 7 (129.32s – 150.32s): Aprobación Parcial, Nota de Crédito y Policy Gate
        # ==========================================
        print("  ▶ [2:09 - 2:30] Escena 7: Autorización de Pago Parcial y Policy Gate (< $5,000 MXN)")
        await page.evaluate("window.setSubtitle('Autorización de pago parcial de las piezas recibidas y solicitud formal de Nota de Crédito.')")
        await page.evaluate("inspeccionarYIrADashboard('OC-004')")
        await page.wait_for_timeout(1000)

        await smooth_click(page, '#btn-aprobar-parcial')
        await page.wait_for_timeout(1400)
        await smooth_click(page, '#btn-solicitar-nc')
        await page.wait_for_timeout(2200)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(1200)

        await page.evaluate("window.setSubtitle('Policy Gate verifica el umbral de $5,000 MXN y registra la acción de forma idempotente en la base de datos.')")
        await smooth_click(page, 'button:has-text("Acta Circunstanciada")')
        await wait_until_target(page, start_time, 150.32)

        # ==========================================
        # ESCENA 8 (150.32s – 169.30s): Tabla de Expedientes y Buscador Instantáneo ⌘K
        # ==========================================
        print("  ▶ [2:30 - 2:49] Escena 8: Registro Central de Expedientes y Filtrado ⌘K")
        await page.evaluate("window.setSubtitle('Registro central de expedientes con filtrado instantáneo por En Reclamo, Escalados o Aprobados.')")
        await smooth_click(page, '#nav-expedientes')
        await page.wait_for_timeout(1500)
        await smooth_click(page, 'button[data-tab="EN_RECLAMO"]')
        await page.wait_for_timeout(1200)
        await smooth_click(page, 'button[data-tab="ESCALADO"]')
        await page.wait_for_timeout(1200)
        await smooth_click(page, 'button[data-tab="TODOS"]')
        await page.wait_for_timeout(1000)

        await page.evaluate("window.setSubtitle('Buscador inteligente con atajo ⌘K localizando cualquier folio, expediente o proveedor al instante.')")
        await smooth_move_to_element(page, '#buscador-expediente')
        await page.fill('#buscador-expediente', 'OC-006')
        await page.wait_for_timeout(1800)
        await page.fill('#buscador-expediente', '')
        await wait_until_target(page, start_time, 169.30)

        # ==========================================
        # ESCENA 9 (169.30s – 180.12s): Cierre de Demostración
        # ==========================================
        print("  ▶ [2:49 - 3:00] Escena 9: Cierre de Demostración")
        await page.evaluate("window.setSubtitle('CotejAI: la IA razona con visión multimodal y las matemáticas blindan la tesorería.')")
        await smooth_click(page, '#nav-dashboard')
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, '#kpi-fuga-retenida')
        await wait_until_target(page, start_time, 180.12)

        video_path = await page.video.path()
        await context.close()
        await browser.close()

    print(f"📦 [3/4] Video capturado en: {video_path}")
    print(f"🎙️ [4/4] Muxing de nueva locución oficial técnica ({VOICEOVER_MP3.name}) y renderizado final en 1080p MP4...")

    if video_path and os.path.exists(video_path) and VOICEOVER_MP3.exists():
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", str(VOICEOVER_MP3),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(OUTPUT_MP4)
        ]
        res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
            print(f"🎉 ¡VIDEO 100% PERSONALIZADO CON NUEVA LOCUCIÓN TÉCNICA GENERADO!")
            print(f"   Destino: {OUTPUT_MP4}")
            print(f"   Tamaño: {size_mb:.2f} MB")
            print(f"   Resolución: 1080p (1920x1080, 30fps) con audio estéreo AAC 192k")
        else:
            print("❌ Error en FFmpeg:", res.stderr)
    else:
        print("❌ Faltan archivos de video o audio para el render final.")

if __name__ == "__main__":
    asyncio.run(record_walkthrough())
