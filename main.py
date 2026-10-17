"""CLI de CotejAI.  Ejemplos:
    python main.py audit --case OC-002
    python main.py audit --all
    python main.py cotejo --case OC-002     # solo el motor determinista, sin Grok
"""
import argparse
import json
import sys

from dotenv import load_dotenv

from src.agent import ejecutar_caso, listar_casos, tool_cotejar_caso, veredicto_escalado


def main() -> int:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="cotejai")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Audita casos con el agente (usa Grok)")
    a.add_argument("--case")
    a.add_argument("--all", action="store_true")
    c = sub.add_parser("cotejo", help="Corre solo el cotejo determinista")
    c.add_argument("--case", required=True)
    args = p.parse_args()
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
