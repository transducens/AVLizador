"""
cat_val/possessius.py -- Possessius àtons femenins en sentit invers:
meva/teva/seva (oriental) -> meua/teua/seua (occidental). Mateix fitxer
font que `rules/val_cat/possessius.py` (`traductor/data/possessius_mauricio.json`),
sense copiar-lo -- nomes indexat per `catalan`, amb el mateix filtre de
número (`_mateix_nombre`) que ja evitava el producte cartesià sense
filtrar del fitxer font (singular amb singular, plural amb plural). La
primera comprovació feta per a la hoja de ruta (comptant sobre les dades
en brut) va donar "6 de 6 ambigües" -- fals: era l'efecte de NO aplicar
este filtre, que `rules/val_cat/possessius.py` ja aplicava des del 30/09/2026.
Aplicant-lo, la inversió és neta del tot.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula

MAURICIO_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "possessius_mauricio.json"


def _mateix_nombre(valenciano: str, catalan: str) -> bool:
    return valenciano.endswith("es") == catalan.endswith("es")


def carrega_possessius_invers(path: Path = MAURICIO_PATH) -> dict[str, str]:
    """
    >>> lookup = carrega_possessius_invers()
    >>> lookup["meva"]
    'meua'
    >>> lookup["seves"]
    'seues'
    """
    dades = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        valenciano = entrada["valenciano"].strip().lower()
        catalan = entrada["catalan"].strip().lower()
        if not _mateix_nombre(valenciano, catalan):
            continue
        lookup[catalan] = valenciano
    return lookup


class PossessiusInversRule:
    """Substitueix possessius febles femenins orientals per la forma
    occidental. Les formes masculines/tòniques no apareixen a la taula a
    propòsit (mai canvien, vore `rules/val_cat/possessius.py`).

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("La meva casa i la seva obra, el meu gos.")
    >>> marca_noms_propis(toks)
    >>> toks = PossessiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('meva', 'meua'), ('seva', 'seua')]
    """

    def __init__(self, path: Path = MAURICIO_PATH) -> None:
        self._lookup = carrega_possessius_invers(path)

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
