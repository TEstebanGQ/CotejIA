"""Capa de persistencia transaccional para CotejAI (PostgreSQL 16 + Fallback SQLite WAL).

Provee:
- Tablas: cases, actions (idempotencia estricta), llm_calls, invoices_seen, sat_69b_efos, fx_cache.
- Precarga automática del listado público oficial del Artículo 69-B del SAT (EFOS).
- Conexión híbrida: usa PostgreSQL si DATABASE_URL está activo; de lo contrario SQLite en modo WAL.
"""
import csv
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = ROOT / "cotejai.db"
CSV_69B_PATH = ROOT / "datasets" / "cache" / "sat_69b_real.csv"

# Costos referenciales por 1M de tokens para telemetría de ROI
COSTO_INPUT_1M = 2.00
COSTO_OUTPUT_1M = 10.00


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usar_postgres() -> bool:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url.startswith("postgres"):
        return False
    try:
        import psycopg
        with psycopg.connect(url, connect_timeout=2) as _:
            return True
    except Exception:
        return False


class _DBConn:
    """Adaptador unificado que normaliza placeholders (? vs %s) entre SQLite WAL y PostgreSQL."""

    def __init__(self):
        self.es_postgres = _usar_postgres()
        if self.es_postgres:
            import psycopg
            self.conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=False)
        else:
            db_path = os.environ.get("SQLITE_PATH", str(DEFAULT_SQLITE_PATH))
            self.conn = sqlite3.connect(db_path, timeout=5.0)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA busy_timeout = 5000;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")

    def execute(self, sql: str, params: tuple = ()):
        if self.es_postgres:
            sql_pg = sql.replace("?", "%s")
            cur = self.conn.cursor()
            cur.execute(sql_pg, params)
            return cur
        return self.conn.execute(sql, params)

    def fetchone_dict(self, sql: str, params: tuple = ()) -> dict | None:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        if self.es_postgres:
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
        return dict(row)

    def fetchall_dict(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self.execute(sql, params)
        rows = cur.fetchall()
        if self.es_postgres:
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        return [dict(r) for r in rows]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()


def init_db() -> str:
    """Inicializa el esquema de base de datos y precarga el catálogo real 69-B del SAT."""
    with _DBConn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                estado_final TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                codigos_json TEXT NOT NULL,
                total_cfdi_mxn TEXT,
                monto_a_pagar_mxn TEXT,
                fuga_detectada_mxn TEXT,
                resumen TEXT,
                herramientas_json TEXT,
                actualizado_en TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                llave_idempotencia TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                herramienta TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                resultado_json TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                modelo TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                latencia_s REAL NOT NULL,
                costo_usd REAL NOT NULL,
                creado_en TEXT NOT NULL
            )
        """ if not db.es_postgres else """
            CREATE TABLE IF NOT EXISTS llm_calls (
                id SERIAL PRIMARY KEY,
                case_id TEXT NOT NULL,
                modelo TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                latencia_s REAL NOT NULL,
                costo_usd REAL NOT NULL,
                creado_en TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS invoices_seen (
                uuid TEXT PRIMARY KEY,
                rfc_emisor TEXT NOT NULL,
                total_mxn TEXT NOT NULL,
                case_id TEXT NOT NULL,
                visto_en TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS sat_69b_efos (
                rfc TEXT PRIMARY KEY,
                nombre_contribuyente TEXT NOT NULL,
                situacion TEXT NOT NULL,
                oficio_definitivo_dof TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS fx_cache (
                moneda TEXT PRIMARY KEY,
                tasa_mxn REAL NOT NULL,
                fuente TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            )
        """)

        # Precargar datos públicos reales de la Lista 69-B del SAT si existe el CSV
        if CSV_69B_PATH.exists():
            with open(CSV_69B_PATH, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rfc = (row.get("rfc") or "").strip().upper()
                    if not rfc:
                        continue
                    existe = db.fetchone_dict("SELECT rfc FROM sat_69b_efos WHERE rfc = ?", (rfc,))
                    if not existe:
                        db.execute(
                            "INSERT INTO sat_69b_efos (rfc, nombre_contribuyente, situacion, oficio_definitivo_dof) VALUES (?, ?, ?, ?)",
                            (
                                rfc,
                                row.get("nombre_contribuyente", "").strip(),
                                row.get("situacion", "Definitivo").strip(),
                                row.get("oficio_definitivo_dof", "").strip(),
                            ),
                        )
        motor = "PostgreSQL 16" if db.es_postgres else "SQLite WAL"
    return motor


def buscar_rfc_69b(rfc: str) -> dict | None:
    """Consulta en la tabla sat_69b_efos si el RFC emisor está en la lista negra del SAT."""
    init_db()
    with _DBConn() as db:
        return db.fetchone_dict(
            "SELECT rfc, nombre_contribuyente, situacion, oficio_definitivo_dof FROM sat_69b_efos WHERE rfc = ?",
            (rfc.strip().upper(),),
        )


def verificar_duplicado_uuid(uuid: str, rfc_emisor: str, total_mxn: str, case_id: str) -> dict:
    """Verifica si el UUID ya fue procesado en otro expediente (DUPLICATE) o lo registra."""
    init_db()
    if not uuid:
        return {"es_duplicado": False, "caso_previo": None}
    uuid_norm = uuid.strip().upper()
    with _DBConn() as db:
        previo = db.fetchone_dict("SELECT uuid, case_id, visto_en FROM invoices_seen WHERE uuid = ?", (uuid_norm,))
        if previo and previo["case_id"] != case_id:
            return {
                "es_duplicado": True,
                "caso_previo": previo["case_id"],
                "visto_en": previo["visto_en"],
            }
        if not previo:
            db.execute(
                "INSERT INTO invoices_seen (uuid, rfc_emisor, total_mxn, case_id, visto_en) VALUES (?, ?, ?, ?, ?)",
                (uuid_norm, rfc_emisor, str(total_mxn), case_id, _now_iso()),
            )
        return {"es_duplicado": False, "caso_previo": case_id}


def ejecutar_con_idempotencia(
    llave_idempotencia: str,
    case_id: str,
    herramienta: str,
    payload: dict,
    accion_fn: Callable[[], dict],
) -> dict:
    """Ejecuta una acción externa garantizando que jamás se duplique la misma llave_idempotencia."""
    init_db()
    with _DBConn() as db:
        existente = db.fetchone_dict(
            "SELECT llave_idempotencia, resultado_json, creado_en FROM actions WHERE llave_idempotencia = ?",
            (llave_idempotencia,),
        )
        if existente:
            res_previo = json.loads(existente["resultado_json"])
            return {
                "ok": True,
                "llave_idempotencia": llave_idempotencia,
                "idempotencia_bloqueada": True,
                "mensaje_idempotencia": f"Acción ya ejecutada en {existente['creado_en']}; se evitó envío duplicado.",
                "resultado": res_previo,
            }

    # Ejecutar acción real fuera de la transacción de lectura
    resultado_real = accion_fn()

    with _DBConn() as db:
        # Doble verificación por concurrencia
        existente = db.fetchone_dict(
            "SELECT llave_idempotencia, resultado_json, creado_en FROM actions WHERE llave_idempotencia = ?",
            (llave_idempotencia,),
        )
        if not existente:
            db.execute(
                "INSERT INTO actions (llave_idempotencia, case_id, herramienta, payload_json, resultado_json, creado_en) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    llave_idempotencia,
                    case_id,
                    herramienta,
                    json.dumps(payload, ensure_ascii=False),
                    json.dumps(resultado_real, ensure_ascii=False),
                    _now_iso(),
                ),
            )
    return {
        "ok": True,
        "llave_idempotencia": llave_idempotencia,
        "idempotencia_bloqueada": False,
        "mensaje_idempotencia": "Acción registrada y enviada por primera vez.",
        "resultado": resultado_real,
    }


def guardar_fx_cache(moneda: str, tasa_mxn: float, fuente: str) -> None:
    init_db()
    mon = moneda.strip().upper()
    with _DBConn() as db:
        existe = db.fetchone_dict("SELECT moneda FROM fx_cache WHERE moneda = ?", (mon,))
        if existe:
            db.execute(
                "UPDATE fx_cache SET tasa_mxn = ?, fuente = ?, actualizado_en = ? WHERE moneda = ?",
                (float(tasa_mxn), fuente, _now_iso(), mon),
            )
        else:
            db.execute(
                "INSERT INTO fx_cache (moneda, tasa_mxn, fuente, actualizado_en) VALUES (?, ?, ?, ?)",
                (mon, float(tasa_mxn), fuente, _now_iso()),
            )


def obtener_fx_cache(moneda: str) -> dict | None:
    init_db()
    with _DBConn() as db:
        return db.fetchone_dict("SELECT moneda, tasa_mxn, fuente, actualizado_en FROM fx_cache WHERE moneda = ?", (moneda.strip().upper(),))


def guardar_resultado_caso(
    case_id: str,
    veredicto: dict,
    total_cfdi_mxn: str | None = None,
    herramientas: list[str] | None = None,
    uso: dict | None = None,
    modelo: str = "grok-4.6",
) -> None:
    """Persiste el estado final del caso y la telemetría de tokens en la base de datos."""
    init_db()
    ahora = _now_iso()
    codigos_json = json.dumps(veredicto.get("codigos", []), ensure_ascii=False)
    tools_json = json.dumps(herramientas or [], ensure_ascii=False)
    fuga = str(veredicto.get("fuga_detectada_mxn") or "0.00")
    monto = str(veredicto.get("monto_a_pagar_mxn") or "0.00")
    estado = veredicto.get("estado_final", "ESCALADO")
    resumen = veredicto.get("resumen", "")

    with _DBConn() as db:
        prev = db.fetchone_dict("SELECT version FROM cases WHERE case_id = ?", (case_id,))
        if prev:
            nueva_ver = int(prev["version"]) + 1
            db.execute(
                """UPDATE cases SET estado_final = ?, version = ?, codigos_json = ?,
                   total_cfdi_mxn = COALESCE(?, total_cfdi_mxn), monto_a_pagar_mxn = ?,
                   fuga_detectada_mxn = ?, resumen = ?, herramientas_json = ?, actualizado_en = ?
                   WHERE case_id = ?""",
                (estado, nueva_ver, codigos_json, total_cfdi_mxn, monto, fuga, resumen, tools_json, ahora, case_id),
            )
        else:
            db.execute(
                """INSERT INTO cases (case_id, estado_final, version, codigos_json, total_cfdi_mxn,
                   monto_a_pagar_mxn, fuga_detectada_mxn, resumen, herramientas_json, actualizado_en)
                   VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
                (case_id, estado, codigos_json, total_cfdi_mxn or "0.00", monto, fuga, resumen, tools_json, ahora),
            )

        if uso and (uso.get("prompt_tokens", 0) > 0 or uso.get("completion_tokens", 0) > 0):
            p_tok = int(uso.get("prompt_tokens", 0))
            c_tok = int(uso.get("completion_tokens", 0))
            lat = float(uso.get("segundos", 0.0))
            costo = round((p_tok / 1_000_000) * COSTO_INPUT_1M + (c_tok / 1_000_000) * COSTO_OUTPUT_1M, 6)
            db.execute(
                """INSERT INTO llm_calls (case_id, modelo, prompt_tokens, completion_tokens, latencia_s, costo_usd, creado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (case_id, modelo, p_tok, c_tok, lat, costo, ahora),
            )


def obtener_casos_db() -> dict[str, dict]:
    """Devuelve un diccionario {case_id: fila_dict} con todos los casos persistidos."""
    init_db()
    with _DBConn() as db:
        filas = db.fetchall_dict("SELECT * FROM cases ORDER BY case_id")
        res = {}
        for f in filas:
            f["codigos"] = json.loads(f.get("codigos_json") or "[]")
            f["herramientas"] = json.loads(f.get("herramientas_json") or "[]")
            res[f["case_id"]] = f
        return res


def listar_acciones_db(case_id: str | None = None) -> list[dict]:
    init_db()
    with _DBConn() as db:
        if case_id:
            filas = db.fetchall_dict("SELECT * FROM actions WHERE case_id = ? ORDER BY creado_en DESC", (case_id,))
        else:
            filas = db.fetchall_dict("SELECT * FROM actions ORDER BY creado_en DESC")
        for f in filas:
            f["payload"] = json.loads(f.get("payload_json") or "{}")
            f["resultado"] = json.loads(f.get("resultado_json") or "{}")
        return filas


def obtener_metricas_db() -> dict:
    """Calcula métricas financieras y de uso de tokens desde la base de datos."""
    init_db()
    casos = obtener_casos_db()
    total_fuga = sum(float(c.get("fuga_detectada_mxn") or 0) for c in casos.values())
    total_pagar = sum(float(c.get("monto_a_pagar_mxn") or 0) for c in casos.values())
    total_cfdi = sum(float(c.get("total_cfdi_mxn") or 0) for c in casos.values())
    conteo_estados = {"APROBADO": 0, "EN_RECLAMO": 0, "ESCALADO": 0}
    for c in casos.values():
        est = c.get("estado_final", "ESCALADO")
        conteo_estados[est] = conteo_estados.get(est, 0) + 1

    with _DBConn() as db:
        llamadas = db.fetchall_dict("SELECT prompt_tokens, completion_tokens, latencia_s, costo_usd FROM llm_calls")
        acciones = db.fetchall_dict("SELECT llave_idempotencia FROM actions")
        efos_count = db.fetchone_dict("SELECT COUNT(*) AS n FROM sat_69b_efos")
        motor = "PostgreSQL 16" if db.es_postgres else "SQLite WAL"

    costo_total_usd = round(sum(float(l.get("costo_usd") or 0) for l in llamadas), 4)
    tokens_in = sum(int(l.get("prompt_tokens") or 0) for l in llamadas)
    tokens_out = sum(int(l.get("completion_tokens") or 0) for l in llamadas)
    costo_mxn = max(costo_total_usd * 18.70, 0.01)
    roi_veces = round(total_fuga / costo_mxn, 1) if total_fuga > 0 else 0.0

    return {
        "motor_db": motor,
        "casos_auditados": len(casos),
        "conteo_estados": conteo_estados,
        "total_facturado_mxn": f"{total_cfdi:.2f}",
        "total_a_pagar_mxn": f"{total_pagar:.2f}",
        "fuga_total_retenida_mxn": f"{total_fuga:.2f}",
        "acciones_idempotentes_registradas": len(acciones),
        "rfcs_69b_cargados": int(efos_count["n"]) if efos_count else 0,
        "telemetria_llm": {
            "llamadas_totales": len(llamadas),
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "costo_total_usd": costo_total_usd,
            "roi_estimado_x": roi_veces,
        },
    }
