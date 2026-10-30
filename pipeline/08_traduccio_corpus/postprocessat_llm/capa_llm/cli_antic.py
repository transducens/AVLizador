"""
cli.py -- Entrada de línia de comandes: `python -m traductor.cli "text"`.

Ferralla mínima sobre translate.py/translate_invers.py -- no conté cap
lògica de conversió, només llig els arguments, crida la funció que toque
segons `--direccio` i imprimix el resultat.

TODO (futur, no demanat en l'especificació original): argparse més
complet, i probablement una opció --fitxer per a traduir un .txt/.jsonl
sencer (línia a línia) en compte d'una sola frase per crida.
"""

from __future__ import annotations

import sys

from .translate import translate
from .translate_invers import translate_cat_val

_DIRECCIONS = {
    "val-cat": translate,
    "cat-val": translate_cat_val,
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    direccio = "val-cat"
    if argv[:1] == ["--direccio"]:
        if len(argv) < 2 or argv[1] not in _DIRECCIONS:
            print(f"--direccio ha de ser {'|'.join(_DIRECCIONS)}", file=sys.stderr)
            return 1
        direccio = argv[1]
        argv = argv[2:]
    if not argv:
        print('Ús: python -m traductor.cli [--direccio val-cat|cat-val] "text a traduir"', file=sys.stderr)
        return 1
    print(_DIRECCIONS[direccio](" ".join(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
