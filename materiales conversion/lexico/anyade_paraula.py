#!/usr/bin/env python3
"""anyade_paraula.py — Añade una palabra a lexico_fiable.json sin tener que
editar el JSON a mano.

ÚS:
    python anyade_paraula.py --val xiquet --cat nen --cast niño
    python anyade_paraula.py --val meua --val meues --cat meva --cat meves
    python anyade_paraula.py --val "eixe" --cat "aqueix" --cat "aquell" --origen manual

Por defecto marca la entrada con `--origen manual` (para distinguirla de las
que vienen de Apertium o de la fuente externa) — cambia con `--origen` si
hace falta.
"""
import argparse
import json
from pathlib import Path

LEXIC_PATH = Path(__file__).resolve().parent / "lexico_fiable.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--val", action="append", required=True, help="Forma valenciana (repetible si hay varias)")
    parser.add_argument("--cat", action="append", required=True, help="Forma catalana equivalente (repetible)")
    parser.add_argument("--cast", action="append", default=[], help="Forma castellana (opcional, repetible)")
    parser.add_argument("--categoria", default="palabra", help="palabra | nombre (por defecto: palabra)")
    parser.add_argument("--origen", default="manual", help="Etiqueta de procedencia (por defecto: manual)")
    args = parser.parse_args()

    data = json.loads(LEXIC_PATH.read_text(encoding="utf-8"))
    entrades = data["entradas"]

    ja_existents = {e["valenciano"][0].strip().lower() for e in entrades}
    for fv in args.val:
        if fv.strip().lower() in ja_existents:
            print(f"AVÍS: '{fv}' ya existe en el léxico — no se añade de nuevo.")
            return

    nova = {
        "valenciano": args.val,
        "catalan": args.cat,
        "castellano": args.cast,
        "categoria": args.categoria,
        "origen": args.origen,
    }
    entrades.append(nova)
    entrades.sort(key=lambda e: e["valenciano"][0].lower())
    data["entradas"] = entrades
    data["total_entradas"] = len(entrades)

    LEXIC_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Añadida: {' / '.join(args.val)} -> {' / '.join(args.cat)}")
    print(f"Total entradas ahora: {len(entrades)}")


if __name__ == "__main__":
    main()
