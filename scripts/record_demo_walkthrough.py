import asyncio
import os
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT / "docs" / "videos"
TEMP_DIR = VIDEOS_DIR / "temp_record"
OUTPUT_MP4 = VIDEOS_DIR / "demo_cotejai_agente.mp4"

CURSOR_JS = """
(() => {
    if (document.getElementById('virtual-cursor-container')) return;
    
    const container = document.createElement('div');
    container.id = 'virtual-cursor-container';
    container.innerHTML = `
        <div id="v-cursor" style="
            position: fixed;
            top: 0; left: 0;
            width: 20px; height: 20px;
            pointer-events: none;
            z-index: 9999999;
            transform: translate(-100px, -100px);
            transition: transform 0.28s cubic-bezier(0.25, 1, 0.5, 1);
        ">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="#10b981" stroke="#ffffff" stroke-width="1.5">
                <path d="M3 3l7 18 3-7 7-3L3 3z"/>
            </svg>
        </div>
    `;
    document.body.appendChild(container);

    window.updateVirtualCursor = (x, y) => {
        const cursor = document.getElementById('v-cursor');
        if (cursor) {
            cursor.style.transform = `translate(${x}px, ${y}px)`;
        }
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
        ripple.style.backgroundColor = 'rgba(16, 185, 129, 0.25)';
        ripple.style.pointerEvents = 'none';
        ripple.style.zIndex = '9999998';
        ripple.style.transform = 'scale(0.5)';
        ripple.style.opacity = '1';
        ripple.style.transition = 'transform 0.35s ease-out, opacity 0.35s ease-out';
        document.body.appendChild(ripple);
        
        requestAnimationFrame(() => {
            ripple.style.transform = 'scale(1.8)';
            ripple.style.opacity = '0';
        });
        setTimeout(() => ripple.remove(), 400);
    };
})();
"""

async def smooth_move_to_element(page, selector, offset_x=0, offset_y=0):
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=4000)
        box = await el.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + offset_x
            y = box["y"] + box["height"] / 2 + offset_y
            await page.evaluate(f"window.updateVirtualCursor({x}, {y})")
            await page.wait_for_timeout(320)
            return x, y
    except Exception as e:
        pass
    return None

async def smooth_click(page, selector):
    pos = await smooth_move_to_element(page, selector)
    if pos:
        x, y = pos
        await page.evaluate(f"window.showClickRipple({x}, {y})")
        await page.wait_for_timeout(150)
    await page.click(selector)
    await page.wait_for_timeout(400)

async def record_walkthrough():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEMP_DIR.glob("*.webm"):
        f.unlink()

    print("🚀 [1/3] Iniciando navegador en 1080p con motor de video de alta fidelidad...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(TEMP_DIR),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        print("🎬 [2/3] Grabando recorrido desatendido del agente y los casos...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.evaluate(CURSOR_JS)
        await page.evaluate("window.updateVirtualCursor(960, 540)")
        await page.wait_for_timeout(800)

        # 1. Explorar el Banner de KPIs Ejecutivos
        await smooth_move_to_element(page, '#kpi-fuga-retenida')
        await page.wait_for_timeout(1200)
        await smooth_move_to_element(page, '#kpi-casos-auditados')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, '#kpi-resolucion-autonoma')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, '#kpi-costo-promedio')
        await page.wait_for_timeout(1200)

        # 2. Caso OC-004: Remisión Física con Merma y Visión Grok
        await page.evaluate("seleccionarCaso('OC-004')")
        await page.wait_for_timeout(1200)

        # Mover al panel de Remisión y abrir Inspección
        await smooth_move_to_element(page, '#pane-doc-remision')
        await page.wait_for_timeout(800)
        await smooth_click(page, '#pane-doc-remision #view-remision-activa button:has-text("Datos")')
        await page.wait_for_timeout(2000) # Dejar ver el modal con la transcripción
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(800)

        # Tríada: Mover sobre los 3 componentes del 3-Way Match
        await smooth_move_to_element(page, 'div[onclick*="\'OC\'"]')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, '#box-remision-triad')
        await page.wait_for_timeout(1000)
        await smooth_move_to_element(page, 'div[onclick*="\'CFDI\'"]')
        await page.wait_for_timeout(1200)

        # 3. Pestañas Multidocumentales: CFDI XML y Orden ERP
        await smooth_click(page, '#tab-doc-btn-cfdi')
        await page.wait_for_timeout(1200)
        await smooth_click(page, '#pane-doc-cfdi button:has-text("Inspeccionar XML SAT")')
        await page.wait_for_timeout(2000)
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(800)

        await smooth_click(page, '#tab-doc-btn-oc')
        await page.wait_for_timeout(1200)
        await smooth_click(page, '#pane-doc-oc button:has-text("Revisar Partidas de OC")')
        await page.wait_for_timeout(1800)
        await smooth_click(page, '#modal-doc-inspector button:has-text("Cerrar")')
        await page.wait_for_timeout(800)

        # 4. Caso OC-006: Sobreprecio Cambiario Banxico (FX_OVERCHARGE)
        await page.evaluate("inspeccionarYIrADashboard('OC-006')")
        await page.wait_for_timeout(1500)
        await smooth_move_to_element(page, '#select-fx-moneda')
        await page.wait_for_timeout(800)
        await page.select_option('#select-fx-moneda', 'EUR')
        await page.wait_for_timeout(1500)
        await page.select_option('#select-fx-moneda', 'USD')
        await page.wait_for_timeout(1200)

        # 5. Diálogos In-App: SAT 4.0 SOAP y Lista 69-B (EFOS)
        await smooth_click(page, 'button:has-text("Conciliación SAT 4.0")')
        await page.wait_for_timeout(2000)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(800)

        await smooth_click(page, 'button:has-text("Lista 69-B (EFOS)")')
        await page.wait_for_timeout(2000)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(800)

        # 6. Grok Vision en Vivo (Diálogo modal)
        await page.evaluate("inspeccionarYIrADashboard('OC-004')")
        await page.wait_for_timeout(1000)
        await page.evaluate("probarVisionEnVivo()")
        await page.wait_for_timeout(2200)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(800)

        # 7. Botones de Acción y Notificaciones Toast
        await smooth_click(page, '#btn-aprobar-parcial')
        await page.wait_for_timeout(1200)
        await smooth_click(page, 'button:has-text("Acta Circunstanciada")')
        await page.wait_for_timeout(1500)
        await smooth_click(page, '#btn-solicitar-nc')
        await page.wait_for_timeout(1800)
        await smooth_click(page, '#app-dialog-btn-primary')
        await page.wait_for_timeout(1000)

        # 8. Vista General de Tabla de Expedientes, Filtros y Búsqueda ⌘K
        await smooth_click(page, '#nav-expedientes')
        await page.wait_for_timeout(1500)
        await smooth_click(page, 'button[data-tab="EN_RECLAMO"]')
        await page.wait_for_timeout(1200)
        await smooth_click(page, 'button[data-tab="ESCALADO"]')
        await page.wait_for_timeout(1200)
        await smooth_click(page, 'button[data-tab="TODOS"]')
        await page.wait_for_timeout(1000)

        await smooth_move_to_element(page, '#buscador-expediente')
        await page.fill('#buscador-expediente', 'OC-006')
        await page.wait_for_timeout(1800)
        await page.fill('#buscador-expediente', '')
        await page.wait_for_timeout(1200)

        # Regresar a Dashboard para cierre elegante
        await smooth_click(page, '#nav-dashboard')
        await page.wait_for_timeout(2000)

        video_path = await page.video.path()
        await context.close()
        await browser.close()

    print(f"📦 [3/3] Codificando video final con FFmpeg a 1080p MP4...")
    if video_path and os.path.exists(video_path):
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            str(OUTPUT_MP4)
        ]
        res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            file_size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
            print(f"✅ ¡Video grabado y exportado exitosamente!")
            print(f"   Destino: {OUTPUT_MP4}")
            print(f"   Tamaño: {file_size_mb:.2f} MB")
        else:
            print("❌ Error en FFmpeg:", res.stderr)
    else:
        print("❌ No se encontró el archivo de video temporal.")

if __name__ == "__main__":
    asyncio.run(record_walkthrough())
