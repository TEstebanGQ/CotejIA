import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT / "docs" / "videos"
TEMP_DIR = VIDEOS_DIR / "temp_record"
TEMP_WEBM = TEMP_DIR / "screen_capture.webm"
VOICEOVER_MP3 = ROOT / "video-cotejai" / "assets" / "audio" / "master_voiceover.mp3"
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
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));
        ">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="#10b981" stroke="#ffffff" stroke-width="1.6">
                <path d="M3 3l7 18 3-7 7-3L3 3z"/>
            </svg>
        </div>
    `;
    document.body.appendChild(container);

    // Contenedor Subtítulos
    const sub = document.createElement('div');
    sub.id = 'v-subtitle';
    sub.style.cssText = `
        position: fixed;
        bottom: 28px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(14, 15, 18, 0.94);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(16, 185, 129, 0.45);
        color: #f4f4f5;
        padding: 9px 24px;
        border-radius: 9999px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13.5px;
        font-weight: 500;
        z-index: 9999990;
        box-shadow: 0 12px 30px -5px rgba(0, 0, 0, 0.65);
        display: flex;
        align-items: center;
        gap: 10px;
        opacity: 0;
        transition: opacity 0.35s ease, transform 0.35s ease;
        max-width: 82%;
        text-align: center;
        pointer-events: none;
        line-height: 1.35;
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
            el.innerHTML = `<span style="background: rgba(16,185,129,0.15); color: #34d399; font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 11.5px; border: 1px solid rgba(16,185,129,0.3);">Kótek 🦉</span> <span>${text}</span>`;
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

    print("🚀 [1/4] Iniciando Chromium 1080p con motor de video y sincronización de voz...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(TEMP_DIR),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        print("🎬 [2/4] Grabando recorrido sincronizado con la locución de Kótek...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.evaluate(CURSOR_AND_SUBTITLES_JS)
        await page.evaluate("window.updateVirtualCursor(960, 540)")

        start_time = time.time()

        # ==========================================
        # ESCENA 1 (0.0s – 20.5s): Introducción CotejAI, 3 Lentes, Arquitectura y KPIs
        # ==========================================
        print("  ▶ [0:00 - 0:20] Escena 1: Introducción y Dashboard")
        await page.evaluate("window.setSubtitle('¡Hola! Soy Kótek, el búho auditor de 3 lentes de CotejAI. Nacimos para resolver la fuga de capital en cuentas por pagar.')")
        await page.evaluate("seleccionarCaso('OC-004')")
        await smooth_move_to_element(page, '#kpi-fuga-retenida')
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, '#kpi-casos-auditados')
        await page.wait_for_timeout(1500)

        await page.evaluate("window.setSubtitle('Combino el razonamiento multimodal de Grok 4.6 con un motor determinista y persistencia en PostgreSQL 16.')")
        await smooth_move_to_element(page, '#kpi-resolucion-autonoma')
        await page.wait_for_timeout(1600)
        await smooth_move_to_element(page, '#kpi-costo-promedio')
        await page.wait_for_timeout(1600)
        await smooth_move_to_element(page, '#label-motor-db')
        await wait_until_target(page, start_time, 20.5)

        # ==========================================
        # ESCENA 2 (20.5s – 41.5s): 180 Divisas en Vivo + OC-006 (FX_OVERCHARGE)
        # ==========================================
        print("  ▶ [0:20 - 0:41] Escena 2: 180 Divisas y Sobreprecio Cambiario Banxico")
        await page.evaluate("window.setSubtitle('En nuestra barra conectamos en tiempo real las 180 divisas oficiales del SAT (Anexo 20) contra el peso mexicano.')")
        await smooth_move_to_element(page, '#select-fx-moneda')
        await page.wait_for_timeout(800)
        await page.select_option('#select-fx-moneda', 'EUR')
        await page.wait_for_timeout(1800)
        await page.select_option('#select-fx-moneda', 'USD')
        await page.wait_for_timeout(1500)

        await page.evaluate("window.setSubtitle('En OC-006 detecto un tipo de cambio inflado de $21.85 vs $18.69 y retengo $19,230 MXN por sobrecargo cambiario.')")
        await page.evaluate("inspeccionarYIrADashboard('OC-006')")
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, '#badge-status-dashboard')
        await page.wait_for_timeout(2000)
        await smooth_move_to_element(page, 'div:has-text("FX_OVERCHARGE")')
        await wait_until_target(page, start_time, 41.5)

        # ==========================================
        # ESCENA 3 (41.5s – 62.5s): Caso Real OC-004: Grok Vision y Merma Manuscrita
        # ==========================================
        print("  ▶ [0:41 - 1:02] Escena 3: Grok Vision sobre Remisión Física con Merma")
        await page.evaluate("window.setSubtitle('En OC-004, invoco leer_remision_imagen con Grok Vision sobre la foto física de almacén...')")
        await page.evaluate("inspeccionarYIrADashboard('OC-004')")
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, '#pane-doc-remision')
        await page.wait_for_timeout(800)
        await smooth_click(page, '#pane-doc-remision #view-remision-activa button:has-text("Datos")')
        await page.wait_for_timeout(2200)

        await page.evaluate("window.setSubtitle('Detecto el sello, firma y nota manuscrita: solo 80 pzas por merma. Mi motor retiene exactamente $5,800 MXN.')")
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(800)

        # Tríada
        await smooth_move_to_element(page, 'div[onclick*="\'OC\'"]')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, '#box-remision-triad')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, 'div[onclick*="\'CFDI\'"]')
        await wait_until_target(page, start_time, 62.5)

        # ==========================================
        # ESCENA 4 (62.5s – 80.5s): Webhook de Reclamo y Bloqueo de Idempotencia en DB
        # ==========================================
        print("  ▶ [1:02 - 1:20] Escena 4: Policy Gate, Webhook e Idempotencia")
        await page.evaluate("window.setSubtitle('Como la diferencia es menor a $5,000 MXN, Policy Gate autoriza disparar el webhook de solicitud de nota de crédito.')")
        await smooth_click(page, '#btn-aprobar-parcial')
        await page.wait_for_timeout(1400)
        await smooth_click(page, '#btn-solicitar-nc')
        await page.wait_for_timeout(1800)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(1200)

        await page.evaluate("window.setSubtitle('Nuestra llave de idempotencia en base de datos bloquea duplicados para nunca reclamar dos veces la misma factura.')")
        await smooth_click(page, 'button:has-text("Acta Circunstanciada")')
        await wait_until_target(page, start_time, 80.5)

        # ==========================================
        # ESCENA 5 (80.5s – 105.1s): Manejo de Fallos: Foto Borrosa (OC-005) y Lista 69-B (OC-007)
        # ==========================================
        print("  ▶ [1:20 - 1:45] Escena 5: Foto Borrosa (RECEIPT_UNREADABLE) y Lista 69-B SAT")
        await page.evaluate("window.setSubtitle('En OC-005, la foto está borrosa. Sin alucinar cantidades, activo RECEIPT_UNREADABLE y escalo a revisión humana.')")
        await page.evaluate("inspeccionarYIrADashboard('OC-005')")
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, 'span:has-text("RECEIPT_UNREADABLE")')
        await page.wait_for_timeout(2500)

        await page.evaluate("window.setSubtitle('En OC-007, al cruzar el RFC contra el Art. 69-B del SAT, bloqueo el 100% por ser una empresa EFOS facturadora.')")
        await page.evaluate("inspeccionarYIrADashboard('OC-007')")
        await page.wait_for_timeout(1800)
        await smooth_click(page, 'button:has-text("Lista 69-B (EFOS)")')
        await page.wait_for_timeout(2400)
        await smooth_click(page, '#app-dialog-btn-primary')
        await wait_until_target(page, start_time, 105.1)

        # ==========================================
        # ESCENA 6 (105.1s – 131.8s): Circuit Breaker SAT SOAP, Policy Gate > $5,000 y Cierre
        # ==========================================
        print("  ▶ [1:45 - 2:11] Escena 6: Circuit Breaker SAT, Tabla General y Cierre")
        await page.evaluate("window.setSubtitle('En OC-010, ante caídas del SAT, el Circuit Breaker abre el circuito tras 3 fallos sin colgar el sistema...')")
        await page.evaluate("inspeccionarYIrADashboard('OC-010')")
        await page.wait_for_timeout(1500)
        await smooth_click(page, 'button:has-text("Conciliación SAT 4.0")')
        await page.wait_for_timeout(2200)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(1000)

        await page.evaluate("window.setSubtitle('Superando el umbral de $5,000, Policy Gate escala a gerencia. CotejAI: la IA razona y la matemática gobierna.')")
        await smooth_click(page, '#nav-expedientes')
        await page.wait_for_timeout(1800)
        await smooth_move_to_element(page, '#buscador-expediente')
        await page.fill('#buscador-expediente', 'OC-006')
        await page.wait_for_timeout(1800)
        await page.fill('#buscador-expediente', '')
        await page.wait_for_timeout(1200)

        await smooth_click(page, '#nav-dashboard')
        await page.evaluate("window.setSubtitle('CotejAI · Platica.mx × Campuslands 🦉')")
        await wait_until_target(page, start_time, 131.8)

        video_path = await page.video.path()
        await context.close()
        await browser.close()

    print(f"📦 [3/4] Video capturado en: {video_path}")
    print(f"🎙️ [4/4] Muxing de audio oficial ({VOICEOVER_MP3.name}) y renderizado final en 1080p MP4...")

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
            print(f"🎉 ¡VIDEO CON AUDIO NARRADO GENERADO EXITOSAMENTE!")
            print(f"   Destino: {OUTPUT_MP4}")
            print(f"   Tamaño: {size_mb:.2f} MB")
            print(f"   Resolución: 1080p (1920x1080, 30fps) con audio estéreo AAC 192k")
        else:
            print("❌ Error en FFmpeg:", res.stderr)
    else:
        print("❌ Faltan archivos de video o audio para el render final.")

if __name__ == "__main__":
    asyncio.run(record_walkthrough())
