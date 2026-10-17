"""CLI y Chat Interactivo de CotejAI.
Ejemplos:
    python main.py                         # Inicia el modo interactivo sin comandos
    python main.py chat                    # Modo interactivo
    python main.py audit --case OC-002     # Audita con Grok
    python main.py audit --all             # Audita lote completo
    python main.py cotejo --case OC-002    # Solo motor determinista
"""
import argparse
import json
import sys

from dotenv import load_dotenv

from src.agent import (
    ejecutar_caso,
    listar_casos,
    tool_cotejar_caso,
    veredicto_escalado,
    tiene_llave_configurada,
    formatear_resumen_caso,
    conversar,
)


def _responder_localmente(entrada: str, caso_activo: str | None) -> str:
    """Respuestas directas para evaluación cuando RETO_KEY no está configurada."""
    e = entrada.lower()
    if caso_activo:
        cotejo = tool_cotejar_caso(caso_activo)
        if any(w in e for w in ("por qué", "porque", "retuviste", "retencion", "motivo", "explic")):
            fuga = cotejo.get("fuga_detectada_mxn", "0.00")
            detalles = cotejo.get("detalle", [])
            txt_det = "; ".join(f"{d.get('sku')}: {d.get('problema')}" for d in detalles)
            return (f"En el caso {caso_activo}, retuve ${fuga} MXN debido a: {txt_det}. "
                    "De acuerdo con las reglas, se retiene la diferencia y se solicita nota de crédito (CFDI tipo E con relación 01).")
    if "iva" in e or "impuesto" in e:
        return ("CotejAI valida los impuestos por concepto: tasa 16% general, 8% frontera norte, 0% o exentos. "
                "Cualquier discrepancia de tasa con la OC o error de cálculo se clasifica como TAX_MISMATCH.")
    return ("Para conversar libremente con razonamiento en vivo de Grok 4.6, agrega tu RETO_KEY en el archivo .env. "
            "Mientras tanto, puedes presionar 1, 2 o 3 para auditar los casos con el motor fiscal exacto.")


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
        "content": (f"Audité el caso {case_id}: total CFDI ${cotejo['total_cfdi_mxn']} MXN, "
                    f"monto a pagar ${cotejo['monto_a_pagar_mxn']} MXN, "
                    f"fuga retenida ${cotejo['fuga_detectada_mxn']} MXN, "
                    f"códigos: {cotejo['codigos']}. Detalle: {cotejo['detalle']}.")
    })


def iniciar_chat_interactivo() -> int:
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
    print("  [4] Auditar todos los casos en lote")
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
        elif entrada in ("4", "todos", "all", "lote"):
            print("\n[CotejAI] Procesando todos los casos en lote...")
            for c in listar_casos():
                _mostrar_auditoria_caso(c, tiene_llave, historial)
            continue

        # Pregunta conversacional en lenguaje natural
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

    # Si se invoca sin argumentos o con comando chat, ir a la terminal interactiva
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ("chat", "-i", "--interactive")):
        return iniciar_chat_interactivo()

    p = argparse.ArgumentParser(prog="cotejai", description="Auditor de facturas CotejAI")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat", help="Modo interactivo conversacional")
    a = sub.add_parser("audit", help="Audita casos con el agente (usa Grok)")
    a.add_argument("--case")
    a.add_argument("--all", action="store_true")
    c = sub.add_parser("cotejo", help="Corre solo el cotejo determinista")
    c.add_argument("--case", required=True)

    args = p.parse_args()

    if args.cmd == "chat":
        return iniciar_chat_interactivo()

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
    for case_id in casos:
        try:
            r = ejecutar_caso(case_id)
        except Exception as e:  # un caso que falla no detiene el lote
            fallidos += 1
            r = {"veredicto": veredicto_escalado(case_id, f"Error al ejecutar el caso: {type(e).__name__}: {e}"),
                 "uso": None}
        print(json.dumps(r["veredicto"], indent=2, ensure_ascii=False))
        if u := r["uso"]:
            print(f"[{case_id}] llamadas={u['llamadas']} tokens_in={u['prompt_tokens']} "
                  f"tokens_out={u['completion_tokens']} rechazos={u['rechazos']} "
                  f"latencia={u['segundos']:.1f}s\n", file=sys.stderr)
        else:
            print(f"[{case_id}] falló y quedó ESCALADO\n", file=sys.stderr)
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())

