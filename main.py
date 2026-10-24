"""CLI, Servidor Web y Chat Interactivo de CotejAI (S2).
Ejemplos:
    python main.py                         # Inicia el modo interactivo en terminal
    python main.py web                     # Levanta el servidor FastAPI en http://localhost:8000
    python main.py chat                    # Modo interactivo conversacional
    python main.py audit --case OC-004     # Audita un caso con Grok 4.6 y sus herramientas reales
    python main.py audit --all             # Audita el lote completo (10 casos) con tabla resumen
    python main.py cotejo --case OC-002    # Solo motor determinista
"""
import argparse
import json
import sys
from decimal import Decimal

from dotenv import load_dotenv

from src.agent import (
    conversar,
    ejecutar_caso,
    formatear_resumen_caso,
    listar_casos,
    tiene_llave_configurada,
    tool_cotejar_caso,
    veredicto_escalado,
)
from src.db import init_db, obtener_metricas_db


def _responder_localmente(entrada: str, caso_activo: str | None) -> str:
    """Respuestas directas para evaluación cuando RETO_KEY no está configurada."""
    e = entrada.lower()
    if caso_activo:
        cotejo = tool_cotejar_caso(caso_activo)
        if any(w in e for w in ("por qué", "porque", "retuviste", "retencion", "motivo", "explic")):
            fuga = cotejo.get("fuga_detectada_mxn", "0.00")
            detalles = cotejo.get("detalle", [])
            txt_det = "; ".join(f"{d.get('sku', 'FISCAL')}: {d.get('problema')}" for d in detalles)
            return (
                f"En el caso {caso_activo}, retuve ${fuga} MXN debido a: {txt_det}. "
                "De acuerdo con las reglas, se retiene la diferencia y se solicita nota de crédito (CFDI tipo E con relación 01)."
            )
    if "iva" in e or "impuesto" in e:
        return (
            "CotejAI valida los impuestos por concepto: tasa 16% general, 8% frontera norte, 0% o exentos. "
            "Cualquier discrepancia de tasa con la OC o error de cálculo se clasifica como TAX_MISMATCH."
        )
    return (
        "Para conversar libremente con razonamiento en vivo de Grok 4.6, agrega tu RETO_KEY en el archivo .env. "
        "Mientras tanto, puedes presionar 1 a 4 para auditar los casos con el motor fiscal exacto."
    )


def _mostrar_auditoria_caso(case_id: str, tiene_llave: bool, historial: list):
    veredicto = None
    if tiene_llave:
        try:
            r = ejecutar_caso(case_id)
            veredicto = r["veredicto"]
        except Exception as err:
            print(f"Aviso: Grok reportó {err}; usando veredicto calculado.", file=sys.stderr)

    resumen = formatear_resumen_caso(case_id, veredicto=veredicto)
    print(resumen)

    cotejo = tool_cotejar_caso(case_id)
    historial.append({
        "role": "assistant",
        "content": (
            f"Audité el caso {case_id}: total CFDI ${cotejo['total_cfdi_mxn']} MXN, "
            f"monto a pagar ${cotejo['monto_a_pagar_mxn']} MXN, "
            f"fuga retenida ${cotejo['fuga_detectada_mxn']} MXN, "
            f"códigos: {cotejo['codigos']}. Detalle: {cotejo['detalle']}."
        ),
    })


def _imprimir_tabla_ejecutiva(filas_resumen: list[dict]) -> None:
    """Imprime la tabla ejecutiva de cierre de lote para la demostración de S2."""
    if not filas_resumen:
        return
    print("\n" + "=" * 96, file=sys.stderr)
    print(" RESUMEN EJECUTIVO DE AUDITORIA AUTONOMA — COTEJAI S2 (GROK 4.6 + HERRAMIENTAS REALES)", file=sys.stderr)
    print("=" * 96, file=sys.stderr)
    encabezado = f"{'CASO':<8} | {'ESTADO':<11} | {'CODIGOS DETECTADOS':<30} | {'A PAGAR MXN':>13} | {'FUGA RETENIDA':>13} | {'TOOLS'}"
    print(encabezado, file=sys.stderr)
    print("-" * 96, file=sys.stderr)
    total_fuga = Decimal("0.00")
    total_pagar = Decimal("0.00")
    for f in filas_resumen:
        v = f["veredicto"]
        fuga_d = Decimal(str(v.get("fuga_detectada_mxn") or "0.00"))
        pagar_d = Decimal(str(v.get("monto_a_pagar_mxn") or "0.00"))
        total_fuga += fuga_d
        total_pagar += pagar_d
        cods = ", ".join(v.get("codigos", []))[:30]
        tools_str = ", ".join(dict.fromkeys(f.get("herramientas", [])))
        print(
            f"{v['case_id']:<8} | {v['estado_final']:<11} | {cods:<30} | "
            f"${pagar_d:>11,.2f} | ${fuga_d:>11,.2f} | {tools_str}",
            file=sys.stderr,
        )
    print("-" * 96, file=sys.stderr)
    metricas = obtener_metricas_db()
    tel = metricas.get("telemetria_llm", {})
    print(
        f"TOTALES  | Casos: {len(filas_resumen):<4} | Motor BD: {metricas.get('motor_db'):<20} | "
        f"${total_pagar:>11,.2f} | ${total_fuga:>11,.2f} | Costo LLM: ${tel.get('costo_total_usd', 0):.4f} USD",
        file=sys.stderr,
    )
    print("=" * 96 + "\n", file=sys.stderr)


def iniciar_chat_interactivo() -> int:
    init_db()
    tiene_llave = tiene_llave_configurada()
    print("=" * 70)
    print(" CotejAI — Agente Autónomo de Cuentas por Pagar (Platica × Grok)")
    print("=" * 70)
    print("Bienvenido al modo interactivo de evaluación.")
    if tiene_llave:
        print("✓ Conexión con Grok activa en el gateway del reto.")
    else:
        print("ℹ Modo local determinista activo (configura RETO_KEY en .env para Grok).")
    print("\nElige una opción rápida o escribe una pregunta en lenguaje natural:")
    print("  [1] Auditar caso OC-001 (Caso limpio - Aprobado)")
    print("  [2] Auditar caso OC-002 (Faltante de piezas - Retención de pago)")
    print("  [3] Auditar caso OC-003 (Sobreprecio de cable - Retención de pago)")
    print("  [4] Auditar todos los casos en lote (OC-001 a OC-010)")
    print("\nO escribe tu duda:")
    print("  Ej: '¿Por qué retuviste el pago del caso 2?' o '¿Cómo manejas el IVA?'")
    print("  (Escribe 'salir' o 'exit' para terminar)")
    print("-" * 70)

    historial = []
    caso_activo = None

    while True:
        try:
            entrada = input("\nTú > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta pronto!")
            break

        if not entrada:
            continue
        if entrada.lower() in ("salir", "exit", "quit", "q"):
            print("CotejAI > ¡Hasta luego! Auditoría finalizada.")
            break

        if entrada in ("1", "oc-001", "OC-001"):
            caso_activo = "OC-001"
            print(f"\n[CotejAI] Procesando caso {caso_activo}...")
            _mostrar_auditoria_caso(caso_activo, tiene_llave, historial)
            continue
        elif entrada in ("2", "oc-002", "OC-002"):
            caso_activo = "OC-002"
            print(f"\n[CotejAI] Procesando caso {caso_activo}...")
            _mostrar_auditoria_caso(caso_activo, tiene_llave, historial)
            continue
        elif entrada in ("3", "oc-003", "OC-003"):
            caso_activo = "OC-003"
            print(f"\n[CotejAI] Procesando caso {caso_activo}...")
            _mostrar_auditoria_caso(caso_activo, tiene_llave, historial)
            continue
        elif entrada.upper() in listar_casos():
            caso_activo = entrada.upper()
            print(f"\n[CotejAI] Procesando caso {caso_activo}...")
            _mostrar_auditoria_caso(caso_activo, tiene_llave, historial)
            continue
        elif entrada in ("4", "todos", "all", "lote"):
            print("\n[CotejAI] Procesando todos los casos en lote...")
            for c in listar_casos():
                _mostrar_auditoria_caso(c, tiene_llave, historial)
            continue

        if tiene_llave:
            try:
                print("CotejAI > Analizando...", end="\r", flush=True)
                resp, historial, uso = conversar(entrada, historial=historial)
                print(f"CotejAI > {resp}")
                if uso.get("completion_tokens", 0):
                    print(f"         [Tokens: in={uso['prompt_tokens']}, out={uso['completion_tokens']}]", file=sys.stderr)
            except Exception as e:
                print(f"CotejAI > Ocurrió un error al consultar a Grok ({type(e).__name__}: {e}).")
        else:
            resp_local = _responder_localmente(entrada, caso_activo)
            print(f"CotejAI > {resp_local}")

    return 0


def main() -> int:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    init_db()

    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ("chat", "-i", "--interactive")):
        return iniciar_chat_interactivo()

    p = argparse.ArgumentParser(prog="cotejai", description="Auditor autónomo de facturas CotejAI")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat", help="Modo interactivo conversacional")
    w = sub.add_parser("web", help="Inicia el servidor FastAPI y el Dashboard Web")
    w.add_argument("--host", default="0.0.0.0")
    w.add_argument("--port", type=int, default=8000)
    a = sub.add_parser("audit", help="Audita casos con el agente (usa Grok 4.6)")
    a.add_argument("--case")
    a.add_argument("--all", action="store_true")
    c = sub.add_parser("cotejo", help="Corre solo el cotejo determinista")
    c.add_argument("--case", required=True)

    args = p.parse_args()

    if args.cmd == "chat":
        return iniciar_chat_interactivo()

    if args.cmd == "web":
        import uvicorn
        print(f"Iniciando CotejAI Backend + Web en http://localhost:{args.port} ...")
        uvicorn.run("src.api:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.case and args.case not in listar_casos():
        p.error(f"no existe el caso {args.case} en datasets/ (debe tener oc.json, remision.json y cfdi.xml)")

    if args.cmd == "cotejo":
        print(json.dumps(tool_cotejar_caso(args.case), indent=2, ensure_ascii=False))
        return 0

    if args.all:
        casos = listar_casos()
    elif args.case:
        casos = [args.case]
    else:
        p.error("indica --case OC-001 o --all")

    fallidos = 0
    filas_resumen = []
    for case_id in casos:
        try:
            r = ejecutar_caso(case_id)
        except Exception as e:
            fallidos += 1
            cotejo_fb = None
            try:
                cotejo_fb = tool_cotejar_caso(case_id)
            except Exception:
                pass
            r = {
                "veredicto": veredicto_escalado(case_id, f"Error al ejecutar el caso: {type(e).__name__}: {e}", cotejo_fb),
                "uso": None,
            }
        print(json.dumps(r["veredicto"], indent=2, ensure_ascii=False))
        u = r.get("uso")
        if u:
            tools_usadas = u.get("herramientas", [])
            print(
                f"[{case_id}] llamadas={u['llamadas']} tokens_in={u['prompt_tokens']} "
                f"tokens_out={u['completion_tokens']} rechazos={u['rechazos']} "
                f"tools={tools_usadas} latencia={u['segundos']:.1f}s\n",
                file=sys.stderr,
            )
            filas_resumen.append({"veredicto": r["veredicto"], "herramientas": tools_usadas})
        else:
            print(f"[{case_id}] falló y quedó ESCALADO\n", file=sys.stderr)
            filas_resumen.append({"veredicto": r["veredicto"], "herramientas": ["fallback_escalado"]})

    if len(filas_resumen) > 1:
        _imprimir_tabla_ejecutiva(filas_resumen)
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
