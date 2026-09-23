"""
cli.py -- Entrada de línia de comandes: `python -m traductor.cli "text"`.

Ferralla mínima sobre translate.py -- no conté cap lògica de conversió,
només llig l'argument, crida translate() i imprimix el resultat.

TODO (futur, no demanat en l'especificació original): argparse més
complet, i probablement una opció --fitxer per a traduir un .txt/.jsonl
sencer (línia a línia) en compte d'una sola frase per crida.
"""

from __future__ import annotations

import sys

from .translate import translate


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print('Ús: python -m traductor.cli "text a traduir"', file=sys.stderr)
        return 1
    print(translate(" ".join(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
