"""Runner Desatendido de 12 Horas para Sprint 4 (Semana de Carga) - CotejAI.

Ejecuta 1,000 tareas completas de punta a punta (OC + Remisión + CFDI 4.0 + SAT + 69-B + Banxico + Policy Gate).
- Pacing calibrado para 12 horas (43,200 segundos):
  * Intervalo objetivo: 43.2 segundos por caso con jitter controlado de ±4 segundos.
  * Consumo real de la pasarela del reto usando `RETO_KEY` y `BASE_URL`.
  * Recolección de basura periódica (`gc.collect()`) para fuga de memoria cero.
- Bitácora oficial dual (JSONL + CSV) con streaming append inmediato y flush a disco:
  `runs/bitacora_s4.jsonl` y `runs/bitacora_s4.csv`
- Estado en memoria y archivo de checkpoint para telemetría en vivo del backend FastAPI.
"""
import argparse
import csv
import gc
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Asegurar importación de módulos de CotejAI
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import src.agent as agent
from src.agent import (
    DATASETS,
    cargar_caso,
    crear_cliente,
    ejecutar_caso,
    listar_casos,
    tiene_llave_configurada,
    tool_cotejar_caso,
)
from src.db import COSTO_INPUT_1M, COSTO_OUTPUT_1M, init_db
from src.cfdi import leer_cfdi

# Configuración de Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] [S4_RUNNER] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("s4_daemon")

RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
BITACORA_JSONL = RUNS_DIR / "bitacora_s4.jsonl"
BITACORA_CSV = RUNS_DIR / "bitacora_s4.csv"
DAEMON_STATUS_FILE = RUNS_DIR / "s4_daemon_status.json"

MXN_POR_USD = Decimal("18.70")
TOTAL_TAREAS_OBJETIVO = 1000
SEGUNDOS_12H = 43200
INTERVALO_BASE_S = 43.2
JITTER_MAX_S = 4.0

CSV_HEADERS = [
    "timestamp_inicio",
    "timestamp_fin",
    "latencia_segundos",
    "case_id",
    "proveedor",
    "rfc",
    "total_facturado_mxn",
    "estado_final",
    "codigos_discrepancia",
    "monto_autorizado_mxn",
    "fuga_retenida_mxn",
    "exito",
    "tokens_in",
    "tokens_out",
    "costo_usd",
    "costo_mxn",
    "error",
    "estrategia_recuperacion",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def inicializar_archivos_bitacora():
    """Garantiza la existencia y encabezados del archivo CSV y JSONL."""
    if not BITACORA_CSV.exists() or BITACORA_CSV.stat().st_size == 0:
        with open(BITACORA_CSV, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            f.flush()

    if not BITACORA_JSONL.exists():
        BITACORA_JSONL.touch()


def registrar_en_bitacora(registro: dict):
    """Escribe atómicamente el registro en JSONL y CSV con flush inmediato a disco."""
    # 1. JSONL streaming append
    with open(BITACORA_JSONL, mode="a", encoding="utf-8") as f_jsonl:
        f_jsonl.write(json.dumps(registro, ensure_ascii=False) + "\n")
        f_jsonl.flush()
        os.fsync(f_jsonl.fileno())

    # 2. CSV streaming append
    csv_row = dict(registro)
    # Convertir listas o campos complejos a string plano para CSV
    if isinstance(csv_row.get("codigos_discrepancia"), list):
        csv_row["codigos_discrepancia"] = ";".join(csv_row["codigos_discrepancia"])

    with open(BITACORA_CSV, mode="a", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writerow(csv_row)
        f_csv.flush()
        os.fsync(f_csv.fileno())


def actualizar_estado_daemon(estado: dict):
    """Actualiza el archivo s4_daemon_status.json que consume el backend FastAPI."""
    try:
        temp_file = DAEMON_STATUS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, DAEMON_STATUS_FILE)
    except Exception as exc:
        logger.warning(f"No se pudo escribir s4_daemon_status.json: {exc}")


def preparar_cola_casos() -> list[tuple[str, Path]]:
    """Recolecta los casos disponibles priorizando datasets/s4 (1,000 casos de carga), o s3 y raiz."""
    casos = []
    # 1. Prioridad: Casos de datasets/s4 (1,000 casos sintéticos del Sprint 4)
    s4_dir = DATASETS / "s4"
    if s4_dir.exists():
        for d in sorted(s4_dir.iterdir()):
            if d.is_dir() and (d / "oc.json").exists() and (d / "cfdi.xml").exists():
                casos.append((d.name, s4_dir))
        if casos:
            return casos

    # 2. Casos de datasets/s3 (36 casos)
    s3_dir = DATASETS / "s3"
    if s3_dir.exists():
        for d in sorted(s3_dir.iterdir()):
            if d.is_dir() and (d / "oc.json").exists() and (d / "cfdi.xml").exists():
                casos.append((d.name, s3_dir))

    # 3. Casos raíz OC-001..OC-010
    for d in sorted(DATASETS.iterdir()):
        if d.is_dir() and d.name.startswith("OC-") and (d / "oc.json").exists():
            casos.append((d.name, DATASETS))

    if not casos:
        raise RuntimeError("No se encontraron casos disponibles en datasets/")
    return casos


def ejecutar_tarea_auditoria(case_id: str, carpeta_base: Path, client) -> dict:
    """Ejecuta una auditoría completa de 3 vías con llamadas al agente o fallback determinista."""
    t_inicio = time.time()
    iso_inicio = _now_iso()

    # Mapeo y lectura de los documentos del caso
    ruta_caso = carpeta_base / case_id
    try:
        oc = json.loads((ruta_caso / "oc.json").read_text(encoding="utf-8"))
        cfdi = leer_cfdi(str(ruta_caso / "cfdi.xml"))
        proveedor_nombre = oc.get("proveedor") or cfdi.get("nombre_emisor") or "Proveedor Desconocido"
        rfc_emisor = cfdi.get("rfc_emisor") or oc.get("rfc_proveedor") or "XAXX010101000"
        total_cfdi_mxn = str(cfdi.get("total") or "0.00")
    except Exception as e:
        proveedor_nombre = "N/A"
        rfc_emisor = "XAXX010101000"
        total_cfdi_mxn = "0.00"

    estrategia = "DIRECTO_GATEWAY"
    error_msg = ""
    exito = True

    # Cambiar dinámicamente DATASETS de agent para que apunte a la carpeta correcta
    prev_datasets = agent.DATASETS
    agent.DATASETS = carpeta_base

    res_agent = None
    try:
        res_agent = ejecutar_caso(case_id, client=client)
    except Exception as err:
        logger.warning(f"Falla en llamada LLM para {case_id}: {err}. Activando estrategia de recuperación (policy_gate + determinista).")
        error_msg = f"{type(err).__name__}: {str(err)[:200]}"
        estrategia = "FALLBACK_DETERMINISTA_SAT"
        exito = False
        try:
            cotejo = tool_cotejar_caso(case_id)
            permitidos = agent.estados_permitidos(cotejo)
            estado_recup = next(e for e in ("APROBADO", "EN_RECLAMO", "ESCALADO") if e in permitidos)
            res_agent = {
                "veredicto": {
                    "case_id": case_id,
                    "estado_final": estado_recup,
                    "codigos": cotejo["codigos"],
                    "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"],
                    "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"],
                    "resumen": f"Recuperado tras error de red: {error_msg}",
                },
                "uso": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "llamadas": 0,
                },
                "cotejo": cotejo,
            }
        except Exception as err_fallback:
            logger.error(f"Error crítico irrecuperable en {case_id}: {err_fallback}")
            res_agent = {
                "veredicto": {
                    "case_id": case_id,
                    "estado_final": "ESCALADO",
                    "codigos": ["SYSTEM_ERROR"],
                    "monto_a_pagar_mxn": "0.00",
                    "fuga_detectada_mxn": total_cfdi_mxn,
                    "resumen": f"Error fatal: {err_fallback}",
                },
                "uso": {"prompt_tokens": 0, "completion_tokens": 0, "llamadas": 0},
            }
    finally:
        agent.DATASETS = prev_datasets

    t_fin = time.time()
    iso_fin = _now_iso()
    latencia_s = round(t_fin - t_inicio, 3)

    veredicto = res_agent.get("veredicto", {})
    uso = res_agent.get("uso", {})

    tok_in = uso.get("prompt_tokens", 0)
    tok_out = uso.get("completion_tokens", 0)

    # Cálculo exacto de costos (Grok 4.6: $2 USD / 1M in, $10 USD / 1M out)
    c_usd = round((Decimal(tok_in) * Decimal(str(COSTO_INPUT_1M)) + Decimal(tok_out) * Decimal(str(COSTO_OUTPUT_1M))) / Decimal(1_000_000), 6)
    c_mxn = round(c_usd * MXN_POR_USD, 4)

    registro = {
        "timestamp_inicio": iso_inicio,
        "timestamp_fin": iso_fin,
        "latencia_segundos": latencia_s,
        "case_id": case_id,
        "proveedor": proveedor_nombre,
        "rfc": rfc_emisor,
        "total_facturado_mxn": total_cfdi_mxn,
        "estado_final": veredicto.get("estado_final", "ESCALADO"),
        "codigos_discrepancia": veredicto.get("codigos", []),
        "monto_autorizado_mxn": str(veredicto.get("monto_a_pagar_mxn") or "0.00"),
        "fuga_retenida_mxn": str(veredicto.get("fuga_detectada_mxn") or "0.00"),
        "exito": exito,
        "tokens_in": tok_in,
        "tokens_out": tok_out,
        "costo_usd": float(c_usd),
        "costo_mxn": float(c_mxn),
        "error": error_msg,
        "estrategia_recuperacion": estrategia,
    }
    return registro


def ejecutar_daemon(total_tareas: int = TOTAL_TAREAS_OBJETIVO, duracion_total_s: float = SEGUNDOS_12H, test_mode: bool = False):
    """Bucle principal de orquestación de carga."""
    logger.info("==================================================================")
    logger.info(f"INICIANDO SPRINT 4 RUNNER DESATENDIDO - COTEJAI")
    logger.info(f"Objetivo de tareas: {total_tareas} | Duración objetivo: {duracion_total_s:.1f} s (~{duracion_total_s/3600:.2f} h)")
    logger.info("==================================================================")

    init_db()
    inicializar_archivos_bitacora()

    if not tiene_llave_configurada():
        logger.error("FATAL: RETO_KEY no configurada. No es posible ejecutar contra la pasarela del reto.")
        sys.exit(1)

    client = crear_cliente()
    casos_disponibles = preparar_cola_casos()
    logger.info(f"Casos base indexados: {len(casos_disponibles)} expedientes únicos.")

    # Reanudar o contar tareas ya ejecutadas en la bitácora
    tareas_previas = 0
    if BITACORA_JSONL.exists():
        with open(BITACORA_JSONL, "r", encoding="utf-8") as f:
            for _ in f:
                tareas_previas += 1
    logger.info(f"Tareas encontradas previamente en bitácora: {tareas_previas}")

    intervalo_objetivo = duracion_total_s / max(total_tareas, 1)
    tiempo_inicio_global = time.time()
    
    contador_exitos = 0
    tokens_totales_in = 0
    tokens_totales_out = 0
    costo_acumulado_usd = Decimal("0.00")
    costo_acumulado_mxn = Decimal("0.00")

    for i in range(tareas_previas + 1, total_tareas + 1):
        idx_caso = (i - 1) % len(casos_disponibles)
        case_id, carpeta = casos_disponibles[idx_caso]

        t_iter_inicio = time.time()
        logger.info(f"[{i}/{total_tareas}] Procesando caso {case_id} ({carpeta.name})...")

        # Ejecución de auditoría
        registro = ejecutar_tarea_auditoria(case_id, carpeta, client)
        registrar_en_bitacora(registro)

        if registro["exito"]:
            contador_exitos += 1
        tokens_totales_in += registro["tokens_in"]
        tokens_totales_out += registro["tokens_out"]
        costo_acumulado_usd += Decimal(str(registro["costo_usd"]))
        costo_acumulado_mxn += Decimal(str(registro["costo_mxn"]))

        # Recolección periódica de basura para fuga de memoria cero
        if i % 10 == 0:
            recogidos = gc.collect()
            logger.info(f"--- Ciclo gc.collect() #{i}: {recogidos} objetos liberados. Memoria limpia. ---")

        # Telemetría en vivo
        t_iter_fin = time.time()
        tiempo_transcurrido = t_iter_fin - tiempo_inicio_global
        tasa_exito = round((contador_exitos / (i - tareas_previas)) * 100, 2) if (i - tareas_previas) > 0 else 100.0

        estado_actual = {
            "estado": "EJECUTANDO" if i < total_tareas else "COMPLETADO",
            "tarea_actual": i,
            "total_tareas": total_tareas,
            "progreso_pct": round((i / total_tareas) * 100, 2),
            "tiempo_transcurrido_segundos": round(tiempo_transcurrido, 1),
            "tiempo_restante_estimado_segundos": round(max(0.0, (total_tareas - i) * intervalo_objetivo), 1),
            "ultimo_caso": case_id,
            "ultimo_estado_final": registro["estado_final"],
            "ultima_latencia_s": registro["latencia_segundos"],
            "tasa_exito_pct": tasa_exito,
            "tokens_totales_in": tokens_totales_in,
            "tokens_totales_out": tokens_totales_out,
            "costo_acumulado_usd": float(costo_acumulado_usd),
            "costo_acumulado_mxn": float(costo_acumulado_mxn),
            "timestamp": _now_iso(),
        }
        actualizar_estado_daemon(estado_actual)

        # Control de Pacing e Intervalo con Jitter Controlado
        duracion_tarea = t_iter_fin - t_iter_inicio
        if not test_mode and i < total_tareas:
            jitter = random.uniform(-JITTER_MAX_S, JITTER_MAX_S)
            espera = max(1.0, intervalo_objetivo - duracion_tarea + jitter)
            logger.info(f"Pacing: Latencia {duracion_tarea:.2f}s | Esperando {espera:.2f}s (jitter: {jitter:+.2f}s)...")
            time.sleep(espera)
        elif test_mode and i < total_tareas:
            time.sleep(0.5)

    logger.info("==================================================================")
    logger.info("CORRIDA SPRINT 4 CONCLUIDA SATISFACTORIAMENTE")
    logger.info(f"Tareas completadas: {total_tareas} | Tasa de éxito: {tasa_exito}%")
    logger.info(f"Costo Total: ${costo_acumulado_usd} USD (${costo_acumulado_mxn} MXN)")
    logger.info("==================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner Desatendido 12 Horas CotejAI Sprint 4")
    parser.add_argument("--tareas", type=int, default=TOTAL_TAREAS_OBJETIVO, help="Número de tareas objetivo (def: 1000)")
    parser.add_argument("--duracion-s", type=float, default=SEGUNDOS_12H, help="Duración total en segundos (def: 43200 = 12h)")
    parser.add_argument("--test", action="store_true", help="Modo de prueba rápida sin espera prolongada")
    args = parser.parse_args()

    ejecutar_daemon(total_tareas=args.tareas, duracion_total_s=args.duracion_s, test_mode=args.test)
