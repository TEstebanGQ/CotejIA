"""CLI de CotejAI.  Ejemplos:
    python main.py audit --case OC-002
    python main.py audit --all
    python main.py cotejo --case OC-002     # solo el motor determinista, sin Grok
"""
import argparse
import json
import sys

from dotenv import load_dotenv

from src.agent import DATASETS, ejecutar_caso, tool_cotejar_caso


def main() -> int:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p =argparse.ArgumentParser(prog="cotejai")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Audita casos con el agente (usa Grok)")
    a.add_argument("--case")
    a.add_argument("--all", action="store_true")
    c = sub.add_parser("cotejo", help="Corre solo el cotejo determinista")
    c.add_argument("--case", required=True)
    args = p.parse_args()

    if args.cmd == "cotejo":
        print(json.dumps(tool_cotejar_caso(args.case), indent=2, ensure_ascii=False))
        return 0

    casos = sorted(d.name for d in DATASETS.iterdir() if d.is_dir()) if args.all else [args.case]
    if not casos or casos == [None]:
        p.error("indica --case OC-001 o --all")
    for case_id in casos:
        r = ejecutar_caso(case_id)
        print(json.dumps(r["veredicto"], indent=2, ensure_ascii=False))
        u = r["uso"]
        print(f"[{case_id}] llamadas={u['llamadas']} tokens_in={u['prompt_tokens']} "
              f"tokens_out={u['completion_tokens']} latencia={u['segundos']:.1f}s\n", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
