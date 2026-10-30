"""Ordre `avlizador` amb subordres:

    avlizador tradueix "Aquest noi necessita ajuda."   # català -> valencià
    avlizador tradueix --fitxer entrada.txt > eixida.txt
    echo "Aquest noi..." | avlizador tradueix
    avlizador tradueix --motor "..."                   # motor sol, sense FLOR
    avlizador gd  --text "Este xiquet vol vindre hui." # Grau Dialectal
    avlizador gdv --text "..."                         # GDV
    avlizador gdc --text "..."                         # GDC
    avlizador avalua --benchmarks manual               # avaluació (extra [avaluacio])

`avlizador <subordre> --help` per a les opcions de cada una.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUBORDRES = {
    "tradueix": "Traduïx de català a valencià (motor + FLOR-760M).",
    "gd": "Grau Dialectal (0 = català, 1 = valencià).",
    "gdv": "Grau Dialectal Valencià (1 = valencià pur).",
    "gdc": "Grau Dialectal Català (1 = català pur).",
    "avalua": "Avalua el traductor en els benchmarks de dades/benchmarks/.",
}


def tradueix(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="avlizador tradueix",
        description="Traduïx text de català oriental a valencià occidental (norma AVL), "
                    "línia a línia. Sense text ni --fitxer, llig de l'entrada estàndard.",
    )
    parser.add_argument("text", nargs="*", help="Text a traduir.")
    parser.add_argument("--fitxer", type=Path, help="Fitxer de text (UTF-8), una frase o paràgraf per línia.")
    parser.add_argument("--motor", action="store_true",
                        help="Només el motor de regles, sense el model de llengua.")
    args = parser.parse_args(argv)

    from .traductor_cat_val import translate_cat_val, translate_cat_val_motor

    funcio = translate_cat_val_motor if args.motor else translate_cat_val
    if args.text:
        linies = [" ".join(args.text)]
    elif args.fitxer:
        linies = args.fitxer.read_text(encoding="utf-8").splitlines()
    else:
        linies = sys.stdin.read().splitlines()
    for linia in linies:
        print(funcio(linia) if linia.strip() else linia)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not argv or argv[0] in ("-h", "--help"):
        from . import __version__

        print(__doc__.strip())
        print(f"\nSubordres (avlizador {__version__}):")
        for nom, ajuda in SUBORDRES.items():
            print(f"  {nom:<9} {ajuda}")
        return 0
    if argv[0] in ("-V", "--version"):
        from . import __version__

        print(f"avlizador {__version__}")
        return 0

    subordre, resta = argv[0], argv[1:]
    if subordre == "tradueix":
        return tradueix(resta)
    if subordre in ("gd", "gdv", "gdc"):
        from importlib import import_module

        return import_module(f".grau_dialectal.{subordre}", __package__).main(resta) or 0
    if subordre == "avalua":
        from .avaluacio.avalua import main as avalua

        return avalua(resta)
    print(f"Subordre desconeguda: {subordre!r}. Opcions: {', '.join(SUBORDRES)}.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
