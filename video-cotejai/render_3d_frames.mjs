import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log('Iniciando motor de renderizado 3D de Kótek...');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 512, height: 512 } });

  const htmlPath = path.resolve(__dirname, 'kotek_3d_engine.html');
  const fileUrl = 'file:///' + htmlPath.replace(/\\/g, '/');
  await page.goto(fileUrl);
  await page.waitForFunction(() => window.__ready === true);

  const baseDir = path.resolve(__dirname, 'assets/frames_3d');

  const anims = [
    { name: 'hero', state: 'HERO_TALK', frames: 48, duration: 2.0 },
    { name: 'presenter', state: 'PRESENTER_TALK', frames: 48, duration: 2.0 },
    { name: 'scanning', state: 'SCANNING', frames: 24, duration: 1.0 },
    { name: 'alert', state: 'ALERT', frames: 24, duration: 1.0 },
  ];

  for (const anim of anims) {
    const dir = path.join(baseDir, anim.name);
    fs.mkdirSync(dir, { recursive: true });
    console.log(`Renderizando animación 3D [${anim.name}] (${anim.frames} cuadros)...`);

    for (let i = 0; i < anim.frames; i++) {
      const t = (i / anim.frames) * anim.duration;
      const dataUrl = await page.evaluate(
        ({ state, t }) => window.setAnimationState(state, t),
        { state: anim.state, t }
      );
      const base64Data = dataUrl.replace(/^data:image\/png;base64,/, '');
      fs.writeFileSync(path.join(dir, `frame_${String(i).padStart(3, '0')}.png`), Buffer.from(base64Data, 'base64'));
    }
  }

  // Exportar el archivo binario 3D .GLB
  try {
    console.log('Exportando modelo 3D independiente (kotek.glb)...');
    const glbBase64 = await page.evaluate(() => window.exportToGLB());
    if (glbBase64) {
      const glbPath = path.resolve(__dirname, 'assets/kotek.glb');
      fs.writeFileSync(glbPath, Buffer.from(glbBase64, 'base64'));
      console.log('¡Modelo 3D exportado a video-cotejai/assets/kotek.glb!');
    }
  } catch (err) {
    console.warn('Nota sobre exportación GLB:', err.message);
  }

  await browser.close();
  console.log('¡Todos los cuadros 3D articulados de Kótek han sido generados exitosamente!');
}

main().catch(console.error);
