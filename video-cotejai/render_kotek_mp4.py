"""Renderizador de Video MP4 fluido (1920x1080, 24 fps) para CotejAI S2.

Combina las capturas reales de la nueva interfaz web en vivo (http://localhost:8000),
el modelo 3D oficial de Kótek generado en Tripo Studio (tripo-showcase),
las imágenes reales de remisiones físicas (OC-004 y OC-005), tarjetas de herramientas
con ajuste automático de texto por píxeles (cero desbordes) y posiciones dinámicas,
y las 6 locuciones masculinas reales generadas con ElevenLabs.
"""
import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
AUDIO_DIR = ASSETS / "audio"

FFMPEG_BIN = Path(
    r"C:\Users\tomas\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
)
FFMPEG = str(FFMPEG_BIN / "ffmpeg.exe")
FFPROBE = str(FFMPEG_BIN / "ffprobe.exe")

W, H = 1920, 1080
FPS = 24  # 24 fps cinematográfico para movimiento fluido


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
FONT_H2 = cargar_fuente(28, bold=True)
FONT_BODY = cargar_fuente(19, bold=False)
FONT_BODY_B = cargar_fuente(19, bold=True)
FONT_SUB = cargar_fuente(22, bold=False)
FONT_MONO_B = cargar_fuente(19, bold=True, mono=True)
FONT_MONO_S = cargar_fuente(17, bold=True, mono=True)


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


def envolver_texto_px(draw: ImageDraw.ImageDraw, texto: str, font, max_width_px: int, indent: str = "") -> list[str]:
    """Envuelve un texto por palabras garantizando que ninguna línea supere max_width_px."""
    palabras = texto.split(" ")
    lineas: list[str] = []
    actual = ""
    for pal in palabras:
        candidato = pal if not actual else f"{actual} {pal}"
        if draw.textlength(candidato, font=font) <= max_width_px:
            actual = candidato
        else:
            if actual:
                lineas.append(actual)
                actual = f"{indent}{pal}"
            else:
                lineas.append(pal)
                actual = ""
    if actual:
        lineas.append(actual)
    return lineas or [texto]


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


def crear_mascot_hero(img_src: Image.Image, size: int, border_color=(6, 182, 212, 255)) -> Image.Image:
    im = img_src.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((4, 4, size - 5, size - 5), radius=36, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    d_out = ImageDraw.Draw(out)
    d_out.rounded_rectangle((2, 2, size - 3, size - 3), radius=36, outline=border_color, width=5)
    return out


def indice_ping_pong(f_idx: int, total: int) -> int:
    if total <= 1:
        return 0
    ciclo = 2 * total - 2
    pos = f_idx % ciclo
    return pos if pos < total else ciclo - pos


def dibujar_dock_kotek(
    frame: Image.Image,
    avatar_pip: Image.Image,
    t_global: float,
    escena_num: int,
    titulo_escena: str,
    subtitulo: str,
    progreso_global: float,
):
    """Dibuja a Kótek 3D en la barra inferior con movimiento flotante, ondas de voz y subtítulos ajustados."""
    draw = ImageDraw.Draw(frame, "RGBA")

    box_x1, box_y1, box_x2, box_y2 = 40, 885, 1880, 1052
    draw.rounded_rectangle(
        (box_x1, box_y1, box_x2, box_y2),
        radius=22,
        fill=(9, 13, 22, 242),
        outline=(6, 182, 212, 195),
        width=3,
    )

    # Movimiento natural sinusoidal de Kótek 3D
    dy = int(math.sin(t_global * 3.4) * 6)
    ax, ay = 64, 898 + dy

    # Anillos de voz pulsantes detrás del avatar 3D
    pulso = int((math.sin(t_global * 8.0) + 1.0) * 6)
    cx, cy = ax + 68, ay + 68
    draw.ellipse(
        (cx - 72 - pulso, cy - 72 - pulso, cx + 72 + pulso, cy + 72 + pulso),
        outline=(16, 185, 129, 130),
        width=3,
    )
    draw.ellipse(
        (cx - 66 - pulso // 2, cy - 66 - pulso // 2, cx + 66 + pulso // 2, cy + 66 + pulso // 2),
        outline=(6, 182, 212, 185),
        width=2,
    )
    frame.paste(avatar_pip, (ax, ay), avatar_pip)

    # Etiqueta y título de escena
    draw.rounded_rectangle((222, 902, 480, 936), radius=8, fill=(16, 185, 129, 45), outline=(16, 185, 129, 180), width=1)
    draw.text((236, 908), f"KÓTEK 3D · ESCENA {escena_num}/6", font=FONT_MONO_S, fill=(52, 211, 153))
    draw.text((498, 903), titulo_escena, font=FONT_H2, fill=(255, 255, 255))

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

    # Subtítulo sincronizado envuelto por ancho en píxeles (nunca se sale del recuadro)
    max_sub_w = box_x2 - 222 - 36
    lineas_sub = envolver_texto_px(draw, subtitulo, FONT_SUB, max_sub_w)
    for idx, l_sub in enumerate(lineas_sub[:2]):
        color_txt = (235, 242, 250) if idx == 0 else (203, 213, 225)
        draw.text((222, 950 + idx * 32), l_sub, font=FONT_SUB, fill=color_txt)

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
    x=1100,
    y=95,
    max_w=680,
):
    """Dibuja una tarjeta de herramienta midiendo cada línea en píxeles para evitar cualquier desborde."""
    if t_local < t_aparicion:
        return
    progreso = min(1.0, (t_local - t_aparicion) / 0.45)
    ease = 1.0 - (1.0 - progreso) ** 3
    offset_y = int((1.0 - ease) * 30)
    alpha = int(ease * 246)

    draw = ImageDraw.Draw(frame, "RGBA")
    pad_x = 24
    pad_top = 16
    pad_bot = 16
    max_text_w = max_w - (pad_x * 2)

    # Envolver título y viñetas garantizando cero texto fuera del recuadro
    titulo_env = envolver_texto_px(draw, titulo, FONT_MONO_B, max_text_w)
    cuerpo_env: list[str] = []
    for lin in lineas:
        cuerpo_env.extend(envolver_texto_px(draw, lin, FONT_BODY, max_text_w, indent="  "))

    # Calcular ancho real exacto según las líneas medidas
    anchos_medidos = [draw.textlength(t_l, font=FONT_MONO_B) for t_l in titulo_env] + [
        draw.textlength(c_l, font=FONT_BODY) for c_l in cuerpo_env
    ]
    w_box = int(max(anchos_medidos, default=420)) + (pad_x * 2) + 8
    w_box = max(460, min(w_box, max_w + 16))

    line_h_title = 27
    line_h_body = 28
    sep_gap = 10
    h_box = pad_top + len(titulo_env) * line_h_title + sep_gap + len(cuerpo_env) * line_h_body + pad_bot

    # Asegurar que las coordenadas nunca se salgan de la pantalla ni pisen el dock inferior
    bx1 = max(36, min(x, W - w_box - 36))
    by1 = max(56, min(y + offset_y, 870 - h_box))
    bx2, by2 = bx1 + w_box, by1 + h_box

    # Sombra suave detrás de la tarjeta para legibilidad
    draw.rounded_rectangle(
        (bx1 + 4, by1 + 6, bx2 + 4, by2 + 6),
        radius=16,
        fill=(0, 0, 0, int(alpha * 0.55)),
    )
    draw.rounded_rectangle(
        (bx1, by1, bx2, by2),
        radius=16,
        fill=(9, 13, 22, alpha),
        outline=(*color_borde, min(255, alpha)),
        width=3,
    )

    curr_y = by1 + pad_top
    for t_l in titulo_env:
        draw.text((bx1 + pad_x, curr_y), t_l, font=FONT_MONO_B, fill=(*color_borde, alpha))
        curr_y += line_h_title

    curr_y += sep_gap // 2
    draw.line((bx1 + pad_x, curr_y, bx2 - pad_x, curr_y), fill=(*color_borde, int(alpha * 0.35)), width=1)
    curr_y += sep_gap // 2 + 2

    for c_l in cuerpo_env:
        draw.text((bx1 + pad_x, curr_y), c_l, font=FONT_BODY, fill=(241, 245, 249, alpha))
        curr_y += line_h_body


def main():
    print("Cargando cuadros 3D de Tripo Studio (Kótek) y audios de ElevenLabs...")
    dir_frames = ASSETS / "frames_3d"
    # Omitimos los primeros 38 cuadros (1.5s) donde el fondo de Tripo aún está vacío antes de entrar el búho 3D
    frames_hero_raw = sorted((dir_frames / "hero").glob("*.png"))[38:]
    frames_pres_raw = sorted((dir_frames / "presenter").glob("*.png"))[72:]
    frames_scan_raw = sorted((dir_frames / "scanning").glob("*.png"))[38:]
    frames_alert_raw = sorted((dir_frames / "alert").glob("*.png"))[72:]

    print(
        f"Cuadros 3D Tripo encontrados: Hero ({len(frames_hero_raw)}), "
        f"Presenter ({len(frames_pres_raw)}), Scanning ({len(frames_scan_raw)}), Alert ({len(frames_alert_raw)})"
    )

    frames_hero_3d = [crear_mascot_hero(Image.open(f), 470, border_color=(6, 182, 212, 255)) for f in frames_hero_raw]
    frames_pres_3d = [crear_avatar_circular(Image.open(f), 136, border_color=(16, 185, 129)) for f in frames_pres_raw]
    frames_scan_3d = [crear_avatar_circular(Image.open(f), 136, border_color=(6, 182, 212)) for f in frames_scan_raw]
    frames_alert_3d = [crear_avatar_circular(Image.open(f), 136, border_color=(239, 68, 68)) for f in frames_alert_raw]

    if not frames_hero_3d:
        mascota_raw = Image.open(ASSETS / "mascota_cotejai.jpg").convert("RGB")
        frames_hero_3d = [crear_mascot_hero(mascota_raw, 470)]
    if not frames_pres_3d:
        mascota_raw = Image.open(ASSETS / "mascota_cotejai.jpg").convert("RGB")
        frames_pres_3d = [crear_avatar_circular(mascota_raw, 136)]
        frames_scan_3d = frames_pres_3d
        frames_alert_3d = frames_pres_3d

    scr_oc004 = Image.open(ASSETS / "screen_oc004.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc006 = Image.open(ASSETS / "screen_oc006.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc005 = Image.open(ASSETS / "screen_oc005.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc007 = Image.open(ASSETS / "screen_oc007.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_oc010 = Image.open(ASSETS / "screen_oc010.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    scr_exp = Image.open(ASSETS / "screen_expedientes.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    rem_004 = Image.open(ASSETS / "remision-oc004.png").convert("RGB").resize((620, 415), Image.Resampling.LANCZOS)
    rem_005 = Image.open(ASSETS / "remision-oc005.png").convert("RGB").resize((620, 415), Image.Resampling.LANCZOS)

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

    # Preparar placa base para Escena 1 (Intro Hero 3D + Preview nueva interfaz)
    bg_s1 = Image.new("RGB", (W, H), (9, 13, 22))
    d_s1 = ImageDraw.Draw(bg_s1, "RGBA")
    dash_mini = scr_oc004.resize((980, 540), Image.Resampling.LANCZOS)
    bg_s1.paste(dash_mini, (860, 130))
    d_s1.rounded_rectangle((858, 128, 1842, 672), radius=14, outline=(16, 185, 129, 200), width=3)
    d_s1.rounded_rectangle((70, 55, 790, 110), radius=12, fill=(16, 185, 129, 35), outline=(16, 185, 129, 180), width=2)
    d_s1.text((92, 68), "PLATICA MAGIA 2026 · HITO S2 (HERRAMIENTAS Y RESILIENCIA)", font=FONT_MONO_S, fill=(52, 211, 153))
    d_s1.text((70, 130), "CotejAI: Auditor Autónomo", font=FONT_H1, fill=(255, 255, 255))
    d_s1.text((70, 190), "Three-Way Matching con Grok 4.6 + PostgreSQL 16", font=FONT_H2, fill=(6, 182, 212))

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

        s_idx = 0
        t_local = t
        for i, (ini, fin) in enumerate(limites):
            if ini <= t <= fin or i == len(limites) - 1:
                s_idx = i
                t_local = t - ini
                break

        idx_hero = indice_ping_pong(f_idx, len(frames_hero_3d))
        idx_pres = indice_ping_pong(f_idx, len(frames_pres_3d))
        idx_scan = indice_ping_pong(f_idx, len(frames_scan_3d))
        idx_alert = indice_ping_pong(f_idx, len(frames_alert_3d))

        if s_idx == 0:
            # ESCENA 1: Intro Hero con Kótek 3D de Tripo Studio en grande + Tarjeta inferior derecha
            frame = bg_s1.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            dy_hero = int(math.sin(t * 2.8) * 10)
            hx, hy = 160, 265 + dy_hero

            pulso = int((math.sin(t * 6.5) + 1.0) * 9)
            draw.rounded_rectangle(
                (hx - 10 - pulso, hy - 10 - pulso, hx + 480 + pulso, hy + 480 + pulso),
                radius=42,
                outline=(6, 182, 212, 160),
                width=4,
            )
            hero_3d = frames_hero_3d[idx_hero]
            frame.paste(hero_3d, (hx, hy), hero_3d)

            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                1.0,
                "ARQUITECTURA HÍBRIDA COTEJAI (S2)",
                [
                    "• 1. Ojos LED Cian: Grok Vision 4.6 lee remisiones físicas y notas a mano.",
                    "• 2. Tercer Lente Esmeralda: Motor Determinista 3-Way Matching en centavos.",
                    "• 3. Escudo en Pecho: PostgreSQL 16 + SAT SOAP + Lista 69-B + Idempotencia.",
                ],
                color_borde=(16, 185, 129),
                x=860,
                y=684,
                max_w=980,
            )
            sub = (
                "¡Hola! Soy Kótek, el búho auditor de tres lentes de CotejAI. Nacimos para detener la fuga de capital en cuentas por pagar "
                "combinando el razonamiento multimodal de Grok 4.6 con un motor determinista y PostgreSQL 16."
            )
            dibujar_dock_kotek(
                frame,
                frames_pres_3d[idx_pres],
                t,
                1,
                "Introducción: ¿Qué es CotejAI y por qué nace?",
                sub,
                progreso_global,
            )

        elif s_idx == 1:
            # ESCENA 2: 180 Divisas ISO 4217 / SAT Anexo 20 (OC-006)
            # Posición de la tarjeta: ABAJO-IZQUIERDA (x=340, y=545) para dejar libre el selector TC BANXICO y Copiloto Grok
            frame = scr_oc006.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            pulso = int((math.sin(t * 7.0) + 1.0) * 4)
            draw.rounded_rectangle(
                (920 - pulso, 6 - pulso, 1625 + pulso, 52 + pulso),
                radius=10,
                outline=(6, 182, 212, 240),
                width=3,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.8,
                'HERRAMIENTA EN VIVO: consultar_tipo_cambio_real("USD", "21.85")',
                [
                    "• Catálogo conectado: 180 Divisas ISO 4217 / SAT Anexo 20 en tiempo real",
                    "• TC en CFDI (OC-006): $21.85 MXN/USD vs Oficial Banxico: $18.69 MXN/USD",
                    "• Código detectado: FX_OVERCHARGE · Fuga retenida: $19,230.39 MXN",
                    "• Resiliencia: Caché automático en PostgreSQL 16 (fx_rates_cache)",
                ],
                color_borde=(6, 182, 212),
                x=340,
                y=540,
                max_w=760,
            )
            sub = (
                "Conectamos en tiempo real las 180 divisas oficiales del Anexo 20 del SAT contra el peso mexicano. "
                "En OC-006 invoco consultar_tipo_cambio_real, detecto un dólar inflado a $21.85 y retengo $19,230.39 MXN."
            )
            dibujar_dock_kotek(
                frame,
                frames_pres_3d[idx_pres],
                t,
                2,
                "API Financiera en Vivo (180 Divisas) · Caso OC-006",
                sub,
                progreso_global,
            )

        elif s_idx == 2:
            # ESCENA 3: Caso Completo OC-004 + Grok Vision escaneando la remisión física
            # Posición de la tarjeta: ARRIBA-IZQUIERDA (x=340, y=90) mientras la remisión escaneada está a la derecha
            frame = scr_oc004.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            rx, ry = 1210, 88
            frame.paste(rem_004, (rx, ry))
            draw.rounded_rectangle((rx - 3, ry - 3, rx + 623, ry + 418), radius=12, outline=(6, 182, 212, 255), width=4)

            scan_y = ry + int(((math.sin(t_local * 2.6) + 1.0) / 2.0) * 395)
            draw.line((rx + 4, scan_y, rx + 616, scan_y), fill=(6, 182, 212, 255), width=4)
            draw.rectangle((rx + 4, max(ry, scan_y - 22), rx + 616, scan_y), fill=(6, 182, 212, 55))
            draw.rounded_rectangle((rx + 26, ry + 210, rx + 594, ry + 275), radius=8, outline=(245, 158, 11, 255), width=3)

            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.8,
                'HERRAMIENTA: leer_remision_imagen("OC-004") — Grok Vision 4.6',
                [
                    "• Nitidez óptica: 41.89 (Legible >= 28.0) · Sello y Firma: Verificados",
                    '• Nota manuscrita: "Se reciben 80 pzas de TORN-001; faltaron 20 por merma"',
                    "• Motor Determinista (cotejar_caso): Retiene $290.00 MXN (20 pzas + IVA 16%)",
                ],
                color_borde=(6, 182, 212),
                x=340,
                y=88,
                max_w=760,
            )
            sub = (
                "En el expediente OC-004 el proveedor facturó 100 piezas, pero al invocar leer_remision_imagen con Grok Vision "
                "sobre la foto física del almacén, leo la nota escrita a mano que reporta solo 80 piezas y retengo $290.00 MXN."
            )
            dibujar_dock_kotek(
                frame,
                frames_scan_3d[idx_scan],
                t,
                3,
                "Grok Vision Multimodal & Three-Way Matching · Caso OC-004",
                sub,
                progreso_global,
            )

        elif s_idx == 3:
            # ESCENA 4: Webhook en Vivo + Bloqueo de Idempotencia en PostgreSQL 16
            # Tarjetas escalonadas en dos columnas distintas (Izquierda Superior y Derecha Media-Baja)
            frame = scr_oc004.copy() if t_local < 11.0 else scr_exp.copy()
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.5,
                '1er DISPARO: enviar_alerta_reclamo_real("OC-004")',
                [
                    "• Compuerta Policy Gate: Fuga $290.00 MXN <= $5,000 MXN (Autorizado)",
                    "• Webhook HTTP POST enviado en vivo solicitando Nota de Crédito CFDI",
                    "• Llave registrada en PostgreSQL 16: OC-004:nota_credito:v1",
                ],
                color_borde=(16, 185, 129),
                x=340,
                y=92,
                max_w=730,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                5.5,
                "2do DISPARO BLOQUEADO: IDEMPOTENCIA EN POSTGRESQL 16",
                [
                    "• idempotencia_bloqueada: true (Tabla transaccional acciones_idempotentes)",
                    "• La llave única ya existe en PostgreSQL 16 desde el primer envío",
                    "• Resultado: Cero correos o notas de crédito duplicadas al proveedor",
                ],
                color_borde=(245, 158, 11),
                x=1100,
                y=520,
                max_w=730,
            )
            sub = (
                "Como la diferencia es menor a $5,000 MXN, policy_gate autoriza invocar enviar_alerta_reclamo_real por webhook. "
                "Si se intenta enviar por segunda vez, nuestra llave de idempotencia en PostgreSQL 16 bloquea el duplicado."
            )
            dibujar_dock_kotek(
                frame,
                frames_pres_3d[idx_pres],
                t,
                4,
                "Webhook en Vivo & Idempotencia Transaccional en PostgreSQL 16",
                sub,
                progreso_global,
            )

        elif s_idx == 4:
            # ESCENA 5: Fallos: Foto Borrosa (OC-005) y Lista Negra 69-B (OC-007)
            if t_local < 12.2:
                frame = scr_oc005.copy()
                draw = ImageDraw.Draw(frame, "RGBA")
                rx, ry = 1210, 88
                frame.paste(rem_005, (rx, ry))
                draw.rounded_rectangle((rx - 3, ry - 3, rx + 623, ry + 418), radius=12, outline=(239, 68, 68, 255), width=4)
                dibujar_tarjeta_herramienta(
                    frame,
                    t_local,
                    0.6,
                    "FALLO ÓPTICO (OC-005): BARRERA ANTI-ALUCINACIÓN",
                    [
                        "• Nitidez medida: 14.82 < 28.0 (Fotografía desenfocada / ilegible)",
                        "• Código activado: RECEIPT_UNREADABLE · Estado: ESCALADO",
                        "• Grok Vision se niega a inventar números y protege la auditoría",
                    ],
                    color_borde=(239, 68, 68),
                    x=1130,
                    y=535,
                    max_w=710,
                )
            else:
                frame = scr_oc007.copy()
                # Ubicada al centro-izquierda para dejar libre el panel derecho de Validación Regulatoria SAT
                dibujar_tarjeta_herramienta(
                    frame,
                    t_local,
                    12.4,
                    'ALERTA FISCAL SAT 69-B (OC-007): consultar_sat_en_vivo("OC-007")',
                    [
                        "• RFC Emisor: AAA080808AAA detectado en tabla sat_69b (PostgreSQL 16)",
                        "• Situación SAT: EFOS Definitivo (Art. 69-B CFF — Operaciones Simuladas)",
                        "• Código: SUPPLIER_69B · Bloqueo del 100% ($6,090.00 MXN retenidos)",
                    ],
                    color_borde=(239, 68, 68),
                    x=340,
                    y=535,
                    max_w=750,
                )
            sub = (
                "¿Y qué hago cuando algo falla? En OC-005 la foto está borrosa: activo RECEIPT_UNREADABLE sin alucinar cifras. "
                "Y en OC-007 cruzo el padrón oficial 69-B del SAT y bloqueo el 100% del pago por ser un proveedor EFOS."
            )
            dibujar_dock_kotek(
                frame,
                frames_alert_3d[idx_alert],
                t,
                5,
                "Manejo de Fallos: Foto Borrosa (OC-005) y Lista 69-B SAT (OC-007)",
                sub,
                progreso_global,
            )

        else:
            # ESCENA 6: Caída del SAT SOAP (Circuit Breaker) + Policy Gate $5,000 MXN (OC-010)
            # Posiciones alternadas: Arriba-Derecha y Abajo-Izquierda
            frame = scr_oc010.copy()
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                0.8,
                "CIRCUIT BREAKER SAT SOAP: OPEN (OC-010)",
                [
                    "• Webservice SOAP del SAT sin respuesta tras 3 intentos consecutivos",
                    "• Circuit Breaker abre el circuito por 600s y emite SAT_NO_VERIFICADO",
                    "• El agente no se cuelga: degrada con elegancia y continúa la auditoría",
                ],
                color_borde=(245, 158, 11),
                x=1110,
                y=88,
                max_w=730,
            )
            dibujar_tarjeta_herramienta(
                frame,
                t_local,
                7.2,
                "COMPUERTA POLICY GATE ($5,000 MXN) EN ACCIÓN",
                [
                    "• Faltante en almacén en OC-010: 100 rollos -> Fuga de $9,280.00 MXN",
                    "• Supera el umbral autónomo ($9,280.00 > $5,000.00 MXN)",
                    "• Policy Gate bloquea el reclamo automático y escala a Tesorería",
                ],
                color_borde=(239, 68, 68),
                x=340,
                y=545,
                max_w=730,
            )
            sub = (
                "En OC-010, ante la caída del SOAP del SAT, nuestro Circuit Breaker abre el circuito marcando SAT_NO_VERIFICADO sin colgarse, "
                "y como la fuga supera $5,000 MXN, el Policy Gate bloquea el reclamo autónomo y lo escala a gerencia."
            )
            dibujar_dock_kotek(
                frame,
                frames_pres_3d[idx_pres],
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
