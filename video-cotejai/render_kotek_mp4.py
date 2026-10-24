"""Renderizador de Video MP4 fluido (1920x1080, 30 fps) para CotejAI S2.

Combina las capturas reales de la aplicación web en vivo (http://localhost:8000),
las imágenes reales de remisiones físicas (OC-004 y OC-005), animaciones fluidas
a 30 fps de la mascota oficial Kótek (flotación sinusoidal, anillos de voz,
ecualizador dinámico, escáner láser cian y tarjetas de herramientas en vivo)
y las 6 locuciones masculinas reales generadas con ElevenLabs.
"""
import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
AUDIO_DIR = ASSETS / "audio"

FFMPEG_BIN = Path(
    r"C:\Users\tomas\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
)
FFMPEG = str(FFMPEG_BIN / "ffmpeg.exe")
FFPROBE = str(FFMPEG_BIN / "ffprobe.exe")

W, H = 1920, 1080
FPS = 24  # 24 fps cinematográfico para render rápido y movimiento fluido


def cargar_fuente(size: int, bold: bool = False, mono: bool = False):
    candidatos = []
    if mono:
        candidatos = [
            r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\courbd.ttf" if bold else r"C:\Windows\Fonts\cour.ttf",
        ]
    else:
        candidatos = [
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        ]
    for c in candidatos:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


FONT_H1 = cargar_fuente(46, bold=True)
FONT_H2 = cargar_fuente(30, bold=True)
FONT_BODY = cargar_fuente(22, bold=False)
FONT_BODY_B = cargar_fuente(22, bold=True)
FONT_SUB = cargar_fuente(23, bold=False)
FONT_MONO_B = cargar_fuente(22, bold=True, mono=True)
FONT_MONO_S = cargar_fuente(18, bold=True, mono=True)


def duracion_mp3(ruta: Path) -> float:
    out = subprocess.check_output(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(ruta),
        ],
        text=True,
    ).strip()
    return float(out)


def crear_avatar_circular(img_src: Image.Image, size: int, border_color=(16, 185, 129)) -> Image.Image:
    im = img_src.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((4, 4, size - 5, size - 5), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    d_out = ImageDraw.Draw(out)
    d_out.ellipse((2, 2, size - 3, size - 3), outline=border_color, width=5)
    return out


def crear_mascot_hero(img_src: Image.Image, size: int) -> Image.Image:
    im = img_src.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((4, 4, size - 5, size - 5), radius=36, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    d_out = ImageDraw.Draw(out)
    d_out.rounded_rectangle((2, 2, size - 3, size - 3), radius=36, outline=(6, 182, 212, 255), width=5)
    return out


def dibujar_dock_kotek(
    frame: Image.Image,
    avatar_pip: Image.Image,
    t_global: float,
    escena_num: int,
    titulo_escena: str,
    subtitulo: str,
    progreso_global: float,
):
    """Dibuja a Kótek en la parte inferior con movimiento flotante, ondas de voz y subtítulos."""
    draw = ImageDraw.Draw(frame, "RGBA")

    # Barra contenedora inferior translúcida
    box_x1, box_y1, box_x2, box_y2 = 40, 885, 1880, 1052
    draw.rounded_rectangle(
        (box_x1, box_y1, box_x2, box_y2),
        radius=22,
        fill=(9, 13, 22, 238),
        outline=(6, 182, 212, 185),
        width=3,
    )

    # Movimiento natural sinusoidal de Kótek (flota y respira)
    dy = int(math.sin(t_global * 3.4) * 7)
    ax, ay = 64, 898 + dy

    # Anillos de voz pulsantes detrás de Kótek
    pulso = int((math.sin(t_global * 8.0) + 1.0) * 6)
    cx, cy = ax + 68, ay + 68
    draw.ellipse(
        (cx - 72 - pulso, cy - 72 - pulso, cx + 72 + pulso, cy + 72 + pulso),
        outline=(16, 185, 129, 120),
        width=3,
    )
    draw.ellipse(
        (cx - 66 - pulso // 2, cy - 66 - pulso // 2, cx + 66 + pulso // 2, cy + 66 + pulso // 2),
        outline=(6, 182, 212, 180),
        width=2,
    )
    frame.paste(avatar_pip, (ax, ay), avatar_pip)

    # Etiqueta y ecualizador de voz masculino en vivo
    draw.rounded_rectangle((222, 902, 480, 936), radius=8, fill=(16, 185, 129, 45), outline=(16, 185, 129, 180), width=1)
    draw.text((236, 907), f"KÓTEK AUDITOR · ESCENA {escena_num}/6", font=FONT_MONO_S, fill=(52, 211, 153))
    draw.text((500, 903), titulo_escena, font=FONT_H2, fill=(255, 255, 255))

    # Ecualizador animado de 18 barras a la derecha del encabezado
    eq_x = 1560
    for i in range(18):
        onda = abs(math.sin(t_global * 9.5 + i * 0.55) * math.cos(t_global * 4.2 - i * 0.3))
        bh = int(6 + onda * 24)
        bx = eq_x + i * 14
        by_top = 922 - bh // 2
        by_bot = 922 + bh // 2
        col = (6, 182, 212, 235) if i % 2 == 0 else (16, 185, 129, 235)
        draw.rounded_rectangle((bx, by_top, bx + 8, by_bot), radius=3, fill=col)

    # Subtítulo sincronizado
    draw.text((222, 952), subtitulo[:118], font=FONT_SUB, fill=(235, 242, 250))
    if len(subtitulo) > 118:
        draw.text((222, 984), subtitulo[118:236], font=FONT_SUB, fill=(203, 213, 225))

    # Barra de progreso inferior
    bar_w = int((box_x2 - 222 - 30) * max(0.02, min(1.0, progreso_global)))
    draw.rounded_rectangle((222, 1028, box_x2 - 30, 1038), radius=5, fill=(30, 41, 59, 220))
    draw.rounded_rectangle((222, 1028, 222 + bar_w, 1038), radius=5, fill=(16, 185, 129, 255))


def dibujar_tarjeta_herramienta(
    frame: Image.Image,
    t_local: float,
    t_aparicion: float,
    titulo: str,
    lineas: list[str],
    color_borde=(16, 185, 129),
    x=1140,
    y=95,
):
    if t_local < t_aparicion:
        return
    progreso = min(1.0, (t_local - t_aparicion) / 0.45)
    # Ease out cubic
    ease = 1.0 - (1.0 - progreso) ** 3
    offset_y = int((1.0 - ease) * 35)
    alpha = int(ease * 245)

    draw = ImageDraw.Draw(frame, "RGBA")
    w_box, h_box = 735, 62 + len(lineas) * 34
    bx1, by1 = x, y + offset_y
    bx2, by2 = bx1 + w_box, by1 + h_box

    draw.rounded_rectangle(
        (bx1, by1, bx2, by2),
        radius=16,
        fill=(9, 13, 22, alpha),
        outline=(*color_borde, min(255, alpha)),
        width=3,
    )
    draw.text((bx1 + 22, by1 + 14), titulo, font=FONT_MONO_B, fill=(*color_borde, alpha))
    for idx, lin in enumerate(lineas):
        draw.text((bx1 + 22, by1 + 52 + idx * 32), lin, font=FONT_BODY, fill=(241, 245, 249, alpha))


def main():
    print("Cargando recursos visuales y audios de ElevenLabs...")
    mascota_raw = Image.open(ASSETS / "mascota_cotejai.jpg").convert("RGB")
    avatar_pip = crear_avatar_circular(mascota_raw, 136)
    mascot_hero = crear_mascot_hero(mascota_raw, 470)

    scr_oc004 = Image.open(ASSETS / "screen_oc004.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc006 = Image.open(ASSETS / "screen_oc006.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc005 = Image.open(ASSETS / "screen_oc005.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc007 = Image.open(ASSETS / "screen_oc007.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc010 = Image.open(ASSETS / "screen_oc010.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_exp = Image.open(ASSETS / "screen_expedientes.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    rem_004 = Image.open(ASSETS / "remision-oc004.png").convert("RGB").resize((660, 440), Image.Resampling.LANCZOS)
    rem_005 = Image.open(ASSETS / "remision-oc005.png").convert("RGB").resize((660, 440), Image.Resampling.LANCZOS)

    # Concatenar los 6 audios de ElevenLabs en una pista maestra continua
    audios = [
        AUDIO_DIR / "escena_1_intro.mp3",
        AUDIO_DIR / "escena_2_arquitectura_divisas.mp3",
        AUDIO_DIR / "escena_3_vision_merma.mp3",
        AUDIO_DIR / "escena_4_idempotencia.mp3",
        AUDIO_DIR / "escena_5_fallos_vision_69b.mp3",
        AUDIO_DIR / "escena_6_circuit_breaker_cierre.mp3",
    ]
    duraciones = [duracion_mp3(a) for a in audios]
    dur_total = sum(duraciones)
    print("Duraciones por escena (s):", [round(d, 2) for d in duraciones], "-> Total:", round(dur_total, 2))

    concat_list = AUDIO_DIR / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{a.resolve().as_posix()}'" for a in audios),
        encoding="utf-8",
    )
    audio_master = AUDIO_DIR / "master_voiceover.mp3"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(audio_master),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Preparar placa base para Escena 1 (Intro Hero + Preview Dashboard)
    bg_s1 = Image.new("RGB", (W, H), (9, 13, 22))
    d_s1 = ImageDraw.Draw(bg_s1, "RGBA")
    # Mini preview del dashboard real a la derecha
    dash_mini = scr_oc004.resize((980, 550), Image.Resampling.LANCZOS)
    bg_s1.paste(dash_mini, (860, 140))
    d_s1.rounded_rectangle((858, 138, 1842, 692), radius=14, outline=(16, 185, 129, 200), width=3)
    d_s1.rounded_rectangle((70, 55, 790, 110), radius=12, fill=(16, 185, 129, 35), outline=(16, 185, 129, 180), width=2)
    d_s1.text((92, 68), "PLATICA MAGIA 2026 · HITO S2 (HERRAMIENTAS Y RESILIENCIA)", font=FONT_MONO_S, fill=(52, 211, 153))
    d_s1.text((70, 130), "CotejAI: Auditor Autónomo", font=FONT_H1, fill=(255, 255, 255))
    d_s1.text((70, 190), "Three-Way Matching con Grok 4.6 + PostgreSQL 16", font=FONT_H2, fill=(6, 182, 212))

    # Límites acumulados de tiempo por escena
    limites = []
    acum = 0.0
    for d in duraciones:
        limites.append((acum, acum + d))
        acum += d

    out_mp4 = ROOT / "cotejai-demo.mp4"
    out_mp4_s2 = ROOT / "cotejai-s2-kotek-2min.mp4"

    cmd = [
        FFMPEG,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        str(audio_master),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out_mp4),
    ]

    total_frames = int(dur_total * FPS)
    print(f"Renderizando {total_frames} cuadros ({round(dur_total, 1)}s @ {FPS} fps) en 1920x1080...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    for f_idx in range(total_frames):
        t = f_idx / FPS
        progreso_global = t / dur_total

        # Determinar en qué escena estamos
        s_idx = 0
        t_local = t
        for i, (ini, fin) in enumerate(limites):
            if ini <= t <= fin or i == len(limites) - 1:
                s_idx = i
                t_local = t - ini
                break

        if s_idx == 0:
            # ESCENA 1: Intro Hero con Kótek flotando en grande + Dashboard real a la derecha
            frame = bg_s1.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            dy_hero = int(math.sin(t * 2.8) * 14)
            hx, hy = 160, 265 + dy_hero

            # Halo pulsante detrás de Kótek Hero
            pulso = int((math.sin(t * 6.5) + 1.0) * 10)
            draw.rounded_rectangle(
                (hx - 12 - pulso, hy - 12 - pulso, hx + 482 + pulso, hy + 482 + pulso),
                radius=44,
                outline=(6, 182, 212, 150),
                width=4,
            )
            frame.paste(mascot_hero, (hx, hy), mascot_hero)

            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                1.2,
                "🦉 ARQUITECTURA HÍBRIDA COTEJAI (S2)",
                [
                    "• 1. Ojos LED Cian: Grok Vision 4.6 lee remisiones físicas y notas a mano.",
                    "• 2. Tercer Lente Esmeralda: Motor Determinista 3-Way Matching en centavos.",
                    "• 3. Escudo en Pecho: PostgreSQL 16 + SAT SOAP + Lista 69-B + Idempotencia.",
                ],
                color_borde=(16, 185, 129),
                x=860,
                y=708,
            )
            sub = (
                "¡Hola! Soy Kótek, el búho auditor de tres lentes de CotejAI. Nacimos para detener la fuga de capital en cuentas por pagar "
                "combinando el razonamiento multimodal de Grok 4.6 con un motor determinista y PostgreSQL 16."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                1,
                "Introducción: ¿Qué es CotejAI y por qué nace?",
                sub,
                progreso_global,
            )

        elif s_idx == 1:
            # ESCENA 2: 180 Divisas ISO 4217 / SAT Anexo 20 + Sobrecargo Cambiario en OC-006
            frame = scr_oc006.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            # Resaltar el selector de 180 divisas en la barra superior
            pulso = int((math.sin(t * 7.0) + 1.0) * 4)
            draw.rounded_rectangle(
                (1175 - pulso, 8 - pulso, 1465 + pulso, 48 + pulso),
                radius=10,
                outline=(6, 182, 212, 240),
                width=3,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                1.0,
                '💱 HERRAMIENTA EN VIVO: consultar_tipo_cambio_real("USD", "21.85")',
                [
                    "• Catálogo conectado: 180 Divisas ISO 4217 / SAT Anexo 20 en tiempo real",
                    "• Tipo de cambio en CFDI (OC-006): $21.85 MXN/USD vs Oficial: $18.69 MXN/USD",
                    "• Código detectado: FX_OVERCHARGE · Fuga retenida: $19,230.39 MXN",
                    "• Resiliencia: Caché automático en PostgreSQL 16 (fx_rates_cache)",
                ],
                color_borde=(6, 182, 212),
                x=1120,
                y=88,
            )
            sub = (
                "Conectamos en tiempo real las 180 divisas oficiales del Anexo 20 del SAT contra el peso mexicano. "
                "En OC-006 invoco consultar_tipo_cambio_real, detecto un dólar inflado a $21.85 y retengo $19,230.39 MXN."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                2,
                "API Financiera en Vivo (180 Divisas) · Caso OC-006",
                sub,
                progreso_global,
            )

        elif s_idx == 2:
            # ESCENA 3: Caso Completo OC-004 + Grok Vision escaneando la remisión física con rayo láser
            frame = scr_oc004.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            # Superponer zoom de la remisión física OC-004 con escáner láser animado
            rx, ry = 1160, 82
            frame.paste(rem_004, (rx, ry))
            draw.rounded_rectangle((rx - 3, ry - 3, rx + 663, ry + 443), radius=12, outline=(6, 182, 212, 255), width=4)

            # Línea láser cian barriendo de arriba a abajo
            scan_y = ry + int(((math.sin(t_local * 2.6) + 1.0) / 2.0) * 420)
            draw.line((rx + 4, scan_y, rx + 656, scan_y), fill=(6, 182, 212, 255), width=4)
            draw.rectangle((rx + 4, max(ry, scan_y - 22), rx + 656, scan_y), fill=(6, 182, 212, 55))

            # Recuadro resaltando la nota manuscrita en la foto
            draw.rounded_rectangle((rx + 28, ry + 225, rx + 632, ry + 290), radius=8, outline=(245, 158, 11, 255), width=3)

            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                1.0,
                '👁️ HERRAMIENTA: leer_remision_imagen("OC-004") — Grok Vision 4.6',
                [
                    "• Nitidez óptica: 95.38 (Legible >= 28.0) · Sello y Firma: Verificados",
                    '• Nota manuscrita leída: "Se reciben 80 pzas de TORN-001; faltaron 20 por merma"',
                    "• Motor Determinista (cotejar_caso): Retiene $290.00 MXN (20 pzas + IVA 16%)",
                ],
                color_borde=(6, 182, 212),
                x=1140,
                y=540,
            )
            sub = (
                "En el expediente OC-004 el proveedor facturó 100 piezas, pero al invocar leer_remision_imagen con Grok Vision "
                "sobre la foto física del almacén, leo la nota escrita a mano que reporta solo 80 piezas y retengo $290.00 MXN."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                3,
                "Grok Vision Multimodal & Three-Way Matching · Caso OC-004",
                sub,
                progreso_global,
            )

        elif s_idx == 3:
            # ESCENA 4: Webhook en Vivo + Bloqueo de Idempotencia en PostgreSQL 16
            frame = scr_oc004.copy() if t_local < 11.0 else scr_exp.copy()
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.5,
                '🚀 1er DISPARO: enviar_alerta_reclamo_real("OC-004")',
                [
                    "• Compuerta Policy Gate: Fuga $290.00 MXN <= $5,000 MXN (Autorizado)",
                    "• Webhook HTTP POST enviado en vivo al proveedor solicitando Nota de Crédito",
                    "• Llave guardada en PostgreSQL 16: reclamo_OC-004_00000004..._290.00",
                ],
                color_borde=(16, 185, 129),
                x=1120,
                y=95,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                5.8,
                "🛡️ 2do DISPARO BLOQUEADO: IDEMPOTENCIA EN POSTGRESQL 16",
                [
                    "• idempotencia_bloqueada: true (Tabla transaccional actions)",
                    "• La llave primaria ya existe en PostgreSQL 16 desde el primer envío",
                    "• Resultado: Cero correos o notas de crédito duplicadas hacia el proveedor",
                ],
                color_borde=(245, 158, 11),
                x=1120,
                y=330,
            )
            sub = (
                "Como la diferencia es menor a $5,000 MXN, policy_gate autoriza invocar enviar_alerta_reclamo_real por webhook. "
                "Si se intenta enviar por segunda vez, nuestra llave de idempotencia en PostgreSQL 16 bloquea el duplicado."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                4,
                "Webhook en Vivo & Idempotencia Transaccional en PostgreSQL 16",
                sub,
                progreso_global,
            )

        elif s_idx == 4:
            # ESCENA 5: Qué hace cuando algo falla: Foto Borrosa (OC-005) y Lista Negra 69-B (OC-007)
            if t_local < 12.2:
                frame = scr_oc005.copy()
                draw = ImageDraw.Draw(frame, "RGBA")
                rx, ry = 1160, 85
                frame.paste(rem_005, (rx, ry))
                draw.rounded_rectangle((rx - 3, ry - 3, rx + 663, ry + 443), radius=12, outline=(239, 68, 68, 255), width=4)
                dibujar_tarjeta_herramienta(
                    frame,
                    t_local,
                    0.6,
                    "⚠️ FALLO ÓPTICO (OC-005): BARRERA ANTI-ALUCINACIÓN",
                    [
                        "• Nitidez medida: 14.82 < 28.0 (Fotografía desenfocada / ilegible)",
                        "• Código activado: RECEIPT_UNREADABLE · Estado: ESCALADO",
                        "• Grok Vision se niega a inventar números y protege la auditoría",
                    ],
                    color_borde=(239, 68, 68),
                    x=1140,
                    y=550,
                )
            else:
                frame = scr_oc007.copy()
                dibujar_tarjeta_herramienta(
                    frame,
                    t_local,
                    12.4,
                    '⛔ ALERTA FISCAL SAT 69-B (OC-007): consultar_sat_en_vivo("OC-007")',
                    [
                        "• RFC Emisor: AAA080808AAA detectado en tabla sat_69b (PostgreSQL 16)",
                        "• Situación SAT: EFOS Definitivo (Art. 69-B CFF — Operaciones Simuladas)",
                        "• Código: SUPPLIER_69B · Bloqueo del 100% ($6,090.00 MXN retenidos)",
                    ],
                    color_borde=(239, 68, 68),
                    x=1120,
                    y=110,
                )
            sub = (
                "¿Y qué hago cuando algo falla? En OC-005 la foto está borrosa: activo RECEIPT_UNREADABLE sin alucinar cifras. "
                "Y en OC-007 cruzo el padrón oficial 69-B del SAT y bloqueo el 100% del pago por ser un proveedor EFOS."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                5,
                "Manejo de Fallos: Foto Borrosa (OC-005) y Lista 69-B SAT (OC-007)",
                sub,
                progreso_global,
            )

        else:
            # ESCENA 6: Caída del SAT SOAP (Circuit Breaker) + Policy Gate $5,000 MXN (OC-010)
            frame = scr_oc010.copy()
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.8,
                "🔌 CIRCUIT BREAKER SAT SOAP: OPEN (OC-010)",
                [
                    "• Webservice SOAP del SAT sin respuesta tras 3 intentos consecutivos",
                    "• Circuit Breaker abre el circuito por 600s y emite SAT_NO_VERIFICADO",
                    "• El agente no se cuelga: degrada con elegancia y continúa la auditoría",
                ],
                color_borde=(245, 158, 11),
                x=1120,
                y=95,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                7.5,
                "🔒 COMPUERTA POLICY GATE ($5,000 MXN) EN ACCIÓN",
                [
                    "• Faltante en almacén en OC-010: 100 rollos -> Fuga de $9,280.00 MXN",
                    "• Supera el umbral autónomo ($9,280.00 > $5,000.00 MXN)",
                    "• Policy Gate bloquea el reclamo automático y escala a Gerencia de Tesorería",
                ],
                color_borde=(239, 68, 68),
                x=1120,
                y=335,
            )
            sub = (
                "En OC-010, ante la caída del SOAP del SAT, nuestro Circuit Breaker abre el circuito marcando SAT_NO_VERIFICADO sin colgarse, "
                "y como la fuga supera $5,000 MXN, el Policy Gate bloquea el reclamo autónomo y lo escala a gerencia."
            )
            dibujar_dock_kotek(
                frame,
                avatar_pip,
                t,
                6,
                "Circuit Breaker SAT SOAP & Compuerta Policy Gate ($5,000 MXN)",
                sub,
                progreso_global,
            )

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    shutil.copy2(out_mp4, out_mp4_s2)
    shutil.copy2(out_mp4, ROOT.parent / "web" / "assets" / "cotejai-demo-kotek.mp4")
    print(f"Video MP4 renderizado con éxito: {out_mp4} ({out_mp4.stat().st_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    main()
