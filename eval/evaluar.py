"""Evaluador S3: compara los veredictos de CotejAI contra el ground truth (`esperado.json`).

    python -m eval.evaluar --set datasets/s3 --salida runs/eval_2026-11-03.json            # local, sin red
    python -m eval.evaluar --set datasets/s3 --modo grok --corridas 3 --salida runs/x.json  # con Grok real

Modo `local`: motor determinista + policy_gate, Nivel 1 de extracción sin red y visión simulada con
`remision.json` (sin llave ni costo). Modo `grok`: ciclo real del agente; mide tokens y costo.
Todo el dinero se maneja con Decimal.
"""
import argparse
import contextlib
import json
import os
import statistics
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MXN_POR_USD = Decimal("18.70")   # mismo tipo de cambio de referencia que src/db.py
METAS = {  # métrica: (comparador, umbral)
    "aprobaciones_indebidas": ("<=", 0.0), "reclamos_indebidos": ("<", 5.0),
    "exactitud_importes": (">", 95.0), "exactitud_codigos": (">", 90.0), "exactitud_extraccion": (">", 90.0),
}


def cargar_esperados(carpeta: Path) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(carpeta.glob("*/esperado.json"))}


@contextlib.contextmanager
def entorno_aislado(carpeta: Path, modo: str, db_path: str):
    """Apunta el agente a `carpeta` y a una BD temporal; en modo local sin llave (nada sale a la red).
    Al salir restaura módulos y variables de entorno."""
    import src.agent as agent
    import src.vision as vision
    previo = (agent.DATASETS, vision.DATASETS)
    vars_ = {"SQLITE_PATH": db_path, "DATABASE_URL": ""}
    if modo == "local":
        vars_["RETO_KEY"] = ""
    guardadas = {k: os.environ.get(k) for k in vars_}
    agent.DATASETS = vision.DATASETS = carpeta
    os.environ.update(vars_)
    try:
        yield agent
    finally:
        agent.DATASETS, vision.DATASETS = previo
        for k, v in guardadas.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def veredicto_local(cotejo: dict) -> dict:
    """Veredicto del agente 'ideal': aplica exactamente lo que permite la compuerta policy_gate."""
    from src.agent import estados_permitidos
    permitidos = estados_permitidos(cotejo)
    estado = next(e for e in ("APROBADO", "EN_RECLAMO", "ESCALADO") if e in permitidos)
    return {"estado_final": estado, "codigos": cotejo["codigos"], "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"],
            "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"]}


def costo_usd(uso: dict) -> Decimal:
    from src.db import COSTO_INPUT_1M, COSTO_OUTPUT_1M
    return (Decimal(uso.get("prompt_tokens", 0)) * Decimal(str(COSTO_INPUT_1M))
            + Decimal(uso.get("completion_tokens", 0)) * Decimal(str(COSTO_OUTPUT_1M))) / Decimal(1_000_000)


def correr_set(carpeta: Path, esperados: dict, modo: str) -> list[dict]:
    """Audita cada caso en orden (los duplicados requieren que el original ya esté registrado)."""
    with tempfile.TemporaryDirectory() as tmp, entorno_aislado(carpeta, modo, str(Path(tmp) / "eval.db")) as agent:
        if modo == "grok":
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env", override=True)
            if not agent.tiene_llave_configurada():
                raise SystemExit("Modo grok: falta RETO_KEY en el entorno o en .env")
        resultados = []
        for cid, esp in esperados.items():
            fila = {"case_id": cid, "tipo_caso": esp["tipo_caso"], "nivel": 2, "costo_usd": Decimal(0), "tokens": 0}
            try:
                if modo == "local":
                    vision = agent.leer_remision_imagen(cid) if (carpeta / cid / "remision.png").exists() else None
                    cotejo = agent.tool_cotejar_caso(cid, vision_res=vision)
                    ver = veredicto_local(cotejo)
                else:
                    r = agent.ejecutar_caso(cid)
                    ver, cotejo = r["veredicto"], r.get("cotejo") or {}
                    fila["costo_usd"] = costo_usd(r["uso"])
                    fila["tokens"] = r["uso"]["prompt_tokens"] + r["uso"]["completion_tokens"]
                fila["nivel"] = cotejo.get("extraccion_nivel", 2)
                fila["remision_usada"] = cotejo.get("remision_usada")
                fila["obtenido"] = ver
            except Exception as e:  # un caso que revienta cuenta como fallo, no detiene la corrida
                fila["obtenido"] = {"estado_final": "ERROR", "codigos": [], "monto_a_pagar_mxn": None,
                                    "fuga_detectada_mxn": None, "error": f"{type(e).__name__}: {e}"}
            resultados.append(fila)
    return resultados


def _dec(x):
    return None if x is None else Decimal(str(x))


def _pct(num: int, den: int) -> float | None:
    return None if den == 0 else round(100 * num / den, 2)


def calcular_metricas(resultados: list[dict], esperados: dict) -> dict:
    con_disc = [r for r in resultados if esperados[r["case_id"]]["estado_final"] != "APROBADO"]
    limpios = [r for r in resultados if esperados[r["case_id"]]["estado_final"] == "APROBADO"]
    aprobadas_mal = [r for r in con_disc if r["obtenido"]["estado_final"] == "APROBADO"]
    reclamos_mal = [r for r in limpios if r["obtenido"]["estado_final"] == "EN_RECLAMO"]
    con_monto = [r for r in resultados if esperados[r["case_id"]]["monto_a_pagar_mxn"] is not None]
    monto_ok = [r for r in con_monto if _dec(r["obtenido"].get("monto_a_pagar_mxn")) == _dec(esperados[r["case_id"]]["monto_a_pagar_mxn"])]
    cod_ok = [r for r in resultados if sorted(r["obtenido"]["codigos"]) == sorted(esperados[r["case_id"]]["codigos"])]
    estado_ok = [r for r in resultados if r["obtenido"]["estado_final"] == esperados[r["case_id"]]["estado_final"]]

    campos = ok_campos = 0
    for r in resultados:
        usado = {l["sku"]: l["cantidad_recibida"] for l in (r.get("remision_usada") or [])}
        for l in esperados[r["case_id"]]["remision"]["lineas"]:
            campos += 1
            ok_campos += _dec(usado.get(l["sku"])) == _dec(l["cantidad_recibida"])

    fuga_real = sum((_dec(esperados[r["case_id"]]["fuga_detectada_mxn"]) for r in resultados), Decimal(0))
    fuga_detectada = sum((_dec(r["obtenido"].get("fuga_detectada_mxn")) or Decimal(0) for r in resultados), Decimal(0))
    fuga_retenida = sum((min(_dec(esperados[r["case_id"]]["fuga_detectada_mxn"]),
                             _dec(r["obtenido"].get("fuga_detectada_mxn")) or Decimal(0))
                         for r in resultados if r["obtenido"]["estado_final"] not in ("APROBADO", "ERROR")), Decimal(0))
    fuga_aprobada = sum((_dec(esperados[r["case_id"]]["fuga_detectada_mxn"]) for r in aprobadas_mal), Decimal(0))
    costo = sum((r["costo_usd"] for r in resultados), Decimal(0))
    costo_mxn = costo * MXN_POR_USD
    n = len(resultados)
    por_nivel = {f"nivel_{k}": _pct(sum(r["nivel"] == k for r in resultados), n) for k in (1, 2)}
    return {
        "casos": n,
        "aprobaciones_indebidas": _pct(len(aprobadas_mal), len(con_disc)),
        "reclamos_indebidos": _pct(len(reclamos_mal), len(limpios)),
        "exactitud_importes": _pct(len(monto_ok), len(con_monto)),
        "exactitud_codigos": _pct(len(cod_ok), n),
        "exactitud_estado": _pct(len(estado_ok), n),
        "exactitud_extraccion": _pct(ok_campos, campos),
        "resolucion_autonoma": _pct(sum(r["obtenido"]["estado_final"] in ("APROBADO", "EN_RECLAMO") for r in resultados), n),
        "extraccion_por_nivel_pct": por_nivel,
        "fuga_real_mxn": str(fuga_real), "fuga_detectada_mxn": str(fuga_detectada),
        "fuga_retenida_mxn": str(fuga_retenida), "fuga_aprobada_por_error_mxn": str(fuga_aprobada),
        "costo_total_usd": f"{costo:.6f}", "costo_por_caso_usd": f"{(costo / n if n else Decimal(0)):.6f}",
        "costo_total_mxn": f"{costo_mxn:.4f}",
        # ROI = $ fuga retenida / $ costo de inferencia; sin costo de inferencia (modo local) no está definido.
        "roi_veces": None if costo_mxn == 0 else f"{(fuga_retenida / costo_mxn):.1f}",
    }


def listar_fallos(resultados: list[dict], esperados: dict) -> list[dict]:
    fallos = []
    for r in resultados:
        e, o = esperados[r["case_id"]], r["obtenido"]
        dif = {}
        if o["estado_final"] != e["estado_final"]:
            dif["estado_final"] = (e["estado_final"], o["estado_final"])
        if sorted(o["codigos"]) != sorted(e["codigos"]):
            dif["codigos"] = (e["codigos"], o["codigos"])
        if e["monto_a_pagar_mxn"] is not None and _dec(o.get("monto_a_pagar_mxn")) != _dec(e["monto_a_pagar_mxn"]):
            dif["monto_a_pagar_mxn"] = (e["monto_a_pagar_mxn"], o.get("monto_a_pagar_mxn"))
        if dif:
            fallos.append({"case_id": r["case_id"], "tipo_caso": e["tipo_caso"], "diferencias": dif,
                           **({"error": o["error"]} if "error" in o else {})})
    return fallos


def resumir_corridas(metricas: list[dict]) -> dict:
    """Promedio y desviación estándar de las métricas numéricas entre corridas."""
    out = {}
    for k in metricas[0]:
        vals = [m[k] for m in metricas]
        if all(isinstance(v, (int, float)) for v in vals):
            out[k] = {"promedio": round(statistics.mean(vals), 2), "desv": round(statistics.pstdev(vals), 2)}
    return out


def _cumple(nombre: str, valor) -> bool | None:
    if nombre not in METAS or valor is None:
        return None
    op, umbral = METAS[nombre]
    return {"<=": valor <= umbral, "<": valor < umbral, ">": valor > umbral}[op]


def imprimir(informe: dict):
    m = informe["metricas_promedio"]
    print(f"\nCotejAI · evaluación S3 · modo={informe['modo']} · {informe['casos']} casos · {informe['corridas']} corrida(s)\n")
    print(f"{'Métrica':34}{'Valor':>10}{'Meta':>10}  OK")
    for k in ("aprobaciones_indebidas", "reclamos_indebidos", "exactitud_importes", "exactitud_codigos",
              "exactitud_extraccion", "exactitud_estado", "resolucion_autonoma"):
        v = m[k]["promedio"] if k in m else None
        meta = f"{METAS[k][0]}{METAS[k][1]}%" if k in METAS else "-"
        ok = _cumple(k, v)
        print(f"{k:34}{('n/d' if v is None else f'{v:.2f}%'):>10}{meta:>10}  {'-' if ok is None else ('✓' if ok else '✗')}")
    u = informe["ultima_corrida"]
    print(f"\nExtracción: {u['extraccion_por_nivel_pct']}")
    print(f"Fuga real {u['fuga_real_mxn']} · detectada {u['fuga_detectada_mxn']} · retenida {u['fuga_retenida_mxn']} "
          f"· aprobada por error {u['fuga_aprobada_por_error_mxn']} (MXN)")
    print(f"Costo inferencia: {u['costo_total_usd']} USD ({u['costo_por_caso_usd']}/caso) · "
          f"ROI: {u['roi_veces'] + ' MXN retenidos por cada MXN gastado' if u['roi_veces'] else 'n/d (costo de inferencia $0 en modo local)'}")
    for f in informe["fallos"]:
        print(f"  ✗ {f['case_id']} [{f['tipo_caso']}] {f['diferencias']}")
    if not informe["fallos"]:
        print("Sin fallos.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default=str(ROOT / "datasets" / "s3"), help="Carpeta con casos y esperado.json")
    ap.add_argument("--modo", choices=("local", "grok"), default="local")
    ap.add_argument("--corridas", type=int, default=None, help="Default: 1 en local (determinista), 3 en grok")
    ap.add_argument("--salida", help="Ruta del JSON de resultados")
    ap.add_argument("--estricto", action="store_true", help="Código de salida 1 si alguna meta no se cumple")
    a = ap.parse_args(argv)

    carpeta = Path(a.set).resolve()
    esperados = cargar_esperados(carpeta)
    if not esperados:
        raise SystemExit(f"No hay esperado.json en {carpeta}")
    n_corridas = a.corridas or (3 if a.modo == "grok" else 1)
    corridas = [correr_set(carpeta, esperados, a.modo) for _ in range(n_corridas)]
    metricas = [calcular_metricas(c, esperados) for c in corridas]
    informe = {"modo": a.modo, "casos": len(esperados), "corridas": n_corridas, "metricas_promedio": resumir_corridas(metricas),
               "metricas_por_corrida": metricas, "ultima_corrida": metricas[-1], "fallos": listar_fallos(corridas[-1], esperados)}
    imprimir(informe)
    if a.salida:
        Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.salida).write_text(json.dumps(informe, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    if a.estricto:
        return int(any(_cumple(k, informe["metricas_promedio"].get(k, {}).get("promedio")) is False for k in METAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
