"""Audita la bitácora de la corrida S4 (runs/bitacora_s4.csv) contra el ground truth de datasets/s4.

Separa tres cosas que la bitácora original mezclaba:
  1. Decisiones correctas del agente.
  2. Escalamientos por falla del sistema (veredicto sin códigos: el cotejo nunca llegó a correr).
  3. Errores de criterio (el agente decidió con códigos, pero distinto a lo esperado).

Uso:  python eval/analizar_bitacora_s4.py [--md eval/analisis_bitacora_s4.md]
Requiere datasets/s4 (python datasets/generate.py --s4).
"""
import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BITACORA = ROOT / "runs" / "bitacora_s4.csv"
S4 = ROOT / "datasets" / "s4"


def _codigos(celda: str) -> list[str]:
    celda = (celda or "").strip()
    if celda in ("", "[]"):
        return []
    return sorted(c for c in celda.split(";") if c)


def analizar() -> dict:
    filas = list(csv.DictReader(open(BITACORA, encoding="utf-8")))
    s4 = [f for f in filas if f["case_id"].startswith("S4-")]
    res = Counter()
    matriz = Counter()
    criterio = Counter()
    for f in s4:
        esp = json.loads((S4 / f["case_id"] / "esperado.json").read_text(encoding="utf-8"))
        cods = _codigos(f["codigos_discrepancia"])
        matriz[(esp["estado_final"], f["estado_final"])] += 1
        if not cods:
            res["falla_sistema"] += 1
        elif esp["estado_final"] == f["estado_final"] and sorted(esp["codigos"]) == cods:
            res["correcto"] += 1
        else:
            res["error_criterio"] += 1
            criterio[(tuple(esp["codigos"]), tuple(cods))] += 1
    lat = [float(f["latencia_segundos"]) for f in s4]
    ts = sorted(f["timestamp_inicio"] for f in s4)
    return {
        "filas_totales": len(filas),
        "casos_s4": len(s4),
        "ventana": (ts[0], ts[-1]),
        "resultado": dict(res),
        "matriz": {f"{a}->{b}": n for (a, b), n in sorted(matriz.items())},
        "errores_criterio": {f"{list(a)}->{list(b)}": n for (a, b), n in criterio.most_common()},
        "tokens_in": sum(int(f["tokens_in"]) for f in filas),
        "tokens_out": sum(int(f["tokens_out"]) for f in filas),
        "costo_usd": round(sum(float(f["costo_usd"]) for f in filas), 4),
        "latencia_p50": round(statistics.median(lat), 2),
        "latencia_p95": round(sorted(lat)[int(len(lat) * 0.95)], 2),
    }


def a_markdown(a: dict) -> str:
    r = a["resultado"]
    n = a["casos_s4"]
    con_cod = r.get("correcto", 0) + r.get("error_criterio", 0)
    lineas = [
        "# Análisis de la bitácora S4 contra ground truth",
        "",
        f"Generado con `python eval/analizar_bitacora_s4.py` sobre `runs/bitacora_s4.csv` "
        f"({a['filas_totales']} filas; {n} casos S4; ventana {a['ventana'][0][:16]} → {a['ventana'][1][:16]} UTC).",
        "",
        "| Resultado | Casos | % |",
        "|---|---:|---:|",
        f"| Correcto (estado y códigos = esperado) | {r.get('correcto', 0)} | {r.get('correcto', 0) / n:.1%} |",
        f"| Escalado por falla del sistema (sin códigos) | {r.get('falla_sistema', 0)} | {r.get('falla_sistema', 0) / n:.1%} |",
        f"| Error de criterio | {r.get('error_criterio', 0)} | {r.get('error_criterio', 0) / n:.1%} |",
        "",
        f"Precisión cuando el cotejo sí corrió: **{r.get('correcto', 0)}/{con_cod} "
        f"({r.get('correcto', 0) / max(con_cod, 1):.1%})**.",
        "",
        "Errores de criterio (esperado → obtenido):",
        "",
    ]
    lineas += [f"- `{k}`: {v}" for k, v in a["errores_criterio"].items()] or ["- ninguno"]
    lineas += [
        "",
        f"Consumo registrado: {a['tokens_in']:,} tokens de entrada, {a['tokens_out']:,} de salida, "
        f"USD {a['costo_usd']}. Latencia p50 {a['latencia_p50']} s, p95 {a['latencia_p95']} s.",
        "",
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="Escribe el análisis en Markdown")
    args = ap.parse_args()
    a = analizar()
    print(json.dumps(a, indent=2, ensure_ascii=False))
    if args.md:
        Path(args.md).write_text(a_markdown(a), encoding="utf-8")
