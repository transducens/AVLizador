"""
cat_val/numerals.py -- Lookup invers de numerals: el MATEIX
`traductor/data/numerals_mauricio.json` que fa servir `rules/val_cat/numerals.py`,
indexat per `catalan`. Cobrix vuitanta->huitanta, divuit->díhuit,
dinou->dènou... Mateixa exclusió de les 4 files "vuitavat" corruptes al
fitxer font (vore `rules/val_cat/numerals.py`) -- ara pel costat català, ja que
les 4 files comparteixen el mateix "vuitavat" com a clau.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula

MAURICIO_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "numerals_mauricio.json"

_VUITAVAT_EXCLOS = "vuitavat"


def carrega_numerals_invers(path: Path = MAURICIO_PATH) -> dict[str, str]:
    """
    >>> lookup = carrega_numerals_invers()
    >>> lookup["vuitanta"]
    'huitanta'
    >>> lookup["divuit"]
    'díhuit'
    >>> lookup["dinou"]
    'dènou'
    >>> "vuitavat" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        catalan = entrada["catalan"].strip().lower()
        if catalan == _VUITAVAT_EXCLOS:
            continue
        lookup.setdefault(catalan, entrada["valenciano"].strip())
    return lookup


class NumeralsInversRule:
    """Substitueix numerals catalans coneguts per la seua forma
    valenciana (vore docstring del mòdul).

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Tinc vuitanta anys i en feia divuit quan vaig anar.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('vuitanta', 'huitanta'), ('divuit', 'díhuit')]
    """

    def __init__(self, path: Path = MAURICIO_PATH) -> None:
        self._lookup = carrega_numerals_invers(path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = self._lookup.get(tok.surface.lower())
            if forma is None:
                continue
            tok.translated = preserva_majuscula(tok.surface, forma)
            tok.is_translated = True
        return tokens
