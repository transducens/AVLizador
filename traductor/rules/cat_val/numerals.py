"""
cat_val/numerals.py -- Lookup invers dels CARDINALS (categoria "num" de
`traductor/data/lexic_general.json`, el MATEIX fitxer que fa servir
`rules/val_cat/numerals.py`, ara indexat per `catalan`). Cobrix
vuitanta->huitanta, divuit->díhuit, dinou->dènou... Els ORDINALS
(categoria "adj") ja els agafa `LexicInversRule` abans que esta regla
córrega -- vore docstring de `rules/val_cat/numerals.py` per al detall
complet de la migració (16/10/2026).
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula

LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lexic_general.json"


def carrega_numerals_invers(path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    """
    >>> lookup = carrega_numerals_invers()
    >>> lookup["vuitanta"]
    'huitanta'
    >>> lookup["divuit"]
    'díhuit'
    >>> lookup["dinou"]
    'dènou'
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        if entrada.get("categoria") != "num":
            continue
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        valenciano = (entrada.get("valenciano") or "").strip()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if not valenciano or not catalan:
            continue
        lookup.setdefault(catalan, valenciano)
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

    def __init__(self, path: Path = LEXIC_GENERAL_PATH) -> None:
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
