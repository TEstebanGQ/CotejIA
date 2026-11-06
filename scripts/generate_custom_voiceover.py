import asyncio
import subprocess
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = ROOT / "docs" / "videos" / "audio_clips"
CONCAT_AUDIO = ROOT / "docs" / "videos" / "voiceover_cotejai_walkthrough.mp3"

VOICE = "es-CO-GonzaloNeural"

# Guion técnico descriptivo redactado específicamente para las acciones de la pantalla
SCENE_SCRIPTS = [
    (
        "clip_01_intro_dashboard.mp3",
        "En esta demostración técnica en vivo, observamos la plataforma CotejAI operando sobre un lote real de cuentas por pagar. "
        "En la parte superior, el tablero de mando refleja más de cuarenta y dos mil pesos en fugas de capital retenidas preventivamente, "
        "con una tasa de resolución autónoma del noventa y cuatro por ciento y un costo de inferencia de apenas cincuenta y tres centavos por expediente."
    ),
    (
        "clip_02_oc004_remision.mp3",
        "Comenzamos examinando el expediente OC cero cero cuatro. En el panel izquierdo, el sistema despliega la fotografía física de la remisión de almacén. "
        "Al pulsar en el botón de datos, el visor forense revela la lectura óptica de Grok Vision, "
        "la cual detectó con precisión el sello oficial, la firma del receptor y una anotación manuscrita que reporta la llegada de solo ochenta piezas debido a una merma durante el traslado."
    ),
    (
        "clip_03_triada_matching.mp3",
        "En el centro de la pantalla, el motor de conciliación a tres vías compara de manera simultánea la Orden de Compra por cien unidades, "
        "la remisión física que ampara únicamente ochenta piezas recibidas y la factura electrónica emitida por el total original. "
        "El sistema calcula una retención preventiva inmediata de cinco mil ochocientos pesos con IVA incluido."
    ),
    (
        "clip_04_tabs_cfdi_oc.mp3",
        "La interfaz multidocumental permite una auditoría profunda. "
        "Al cambiar a la pestaña de Factura CFDI cuatro punto cero e ingresar a la inspección forense, se comprueba el folio fiscal UUID, el RFC del emisor y la cadena digital timbrada. "
        "De igual forma, la pestaña de la Orden de Compra ERP valida los precios unitarios pactados contractualmente."
    ),
    (
        "clip_05_oc006_divisas.mp3",
        "Pasemos ahora al caso OC cero cero seis, facturado en moneda extranjera. "
        "En la barra superior, CotejAI mantiene una conexión en tiempo real con el catálogo de ciento ochenta divisas del SAT y las cotizaciones oficiales de Banxico. "
        "Al auditar esta factura en dólares, el agente detecta un tipo de cambio sobrevaluado a veintiún pesos con ochenta y cinco centavos, "
        "congelando diecinueve mil setecientos pesos por concepto de sobrecargo cambiario."
    ),
    (
        "clip_06_sat_69b_dialogs.mp3",
        "La seguridad fiscal está blindada mediante dos verificaciones en línea. "
        "Primero, la consulta SOAP del SAT confirma la vigencia legal del comprobante. "
        "Segundo, la auditoría automática contra el listado del artículo sesenta y nueve B del Código Fiscal descarta que el emisor sea una empresa catalogada como facturadora de operaciones simuladas."
    ),
    (
        "clip_07_acciones_policy_gate.mp3",
        "Regresando al caso con discrepancia, procedemos a autorizar el pago parcial de las piezas efectivamente recibidas. "
        "Al solicitar la nota de crédito, la compuerta de políticas o Policy Gate verifica que la diferencia se encuentre dentro del umbral de cinco mil pesos para su trámite autónomo, "
        "registrando el evento de forma idempotente en la base de datos para impedir cualquier reclamo duplicado."
    ),
    (
        "clip_08_tabla_expedientes.mp3",
        "Por último, ingresamos al registro central de expedientes. "
        "La tabla consolida el universo de facturas auditadas con filtros instantáneos por estatus, ya sean casos en reclamo, escalados o aprobados. "
        "El buscador inteligente con atajo comando K localiza de inmediato cualquier expediente, número de orden o proveedor."
    ),
    (
        "clip_09_cierre.mp3",
        "Con esto concluimos la demostración de CotejAI: la plataforma donde la inteligencia artificial razona con visión multimodal y las reglas matemáticas garantizan la protección absoluta de la tesorería."
    )
]

async def generate_all_clips():
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    clip_files = []
    
    print(f"🎙️ Generando {len(SCENE_SCRIPTS)} segmentos de locución técnica descriptiva...")
    for idx, (filename, text) in enumerate(SCENE_SCRIPTS, 1):
        target_path = CLIPS_DIR / filename
        print(f"  [{idx}/{len(SCENE_SCRIPTS)}] Generando {filename}...")
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(target_path))
        clip_files.append(target_path)

    # Medir duraciones de cada clip
    print("\n⏱️ Duraciones exactas por escena:")
    concat_txt_lines = []
    total_dur = 0.0
    for clip in clip_files:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(clip)
        ]
        dur = float(subprocess.check_output(cmd).decode().strip())
        total_dur += dur
        print(f"  - {clip.name}: {dur:.2f} s")
        concat_txt_lines.append(f"file '{clip.resolve()}'")

    concat_list_file = CLIPS_DIR / "concat_list.txt"
    with open(concat_list_file, "w") as f:
        f.write("\n".join(concat_txt_lines) + "\n")

    print(f"\n📦 Duración total estimada: {total_dur:.2f} s ({int(total_dur // 60)}m {int(total_dur % 60)}s)")
    print(f"🔗 Concatenando clips en {CONCAT_AUDIO.name} con FFmpeg...")

    ffmpeg_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(CONCAT_AUDIO)
    ]
    subprocess.run(ffmpeg_concat, check=True)
    print(f"✅ Audio maestro generado con éxito en: {CONCAT_AUDIO}")

if __name__ == "__main__":
    asyncio.run(generate_all_clips())
