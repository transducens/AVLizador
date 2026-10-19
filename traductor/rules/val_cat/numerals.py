"""
numerals.py -- Lookup exacte dels CARDINALS (categoria "num" de
`traductor/data/lexic_general.json`, còpia de `lexico_general.json`
del proveïdor oficial, 16/10/2026): huit->vuit, huitanta->vuitanta,
dènou->dinou... Els ORDINALS (categoria "adj": huitena, huitens...) ja
els agafa `LexicRule` ABANS que esta regla córrega (vore engine.py) --
esta capa nomes necessita cobrir els cardinals purs.

Inclou "díhuit"->"divuit" sense necessitat de cap cas especial, perquè
és lookup exacte, no substitució de subcadena.

Migrat 16/10/2026 des de `numerals_general.json` (vore
documentacio/hoja_de_ruta_migracio_diccionarios_v1.md): mesurat abans de
canviar -- de les 176 formes antigues, 153 ja coincidixen via
`LexicRule` (categoria "adj", ordinals) + esta regla (categoria "num",
cardinals); nomes 25 (un únic patró, l'ordinal masculí singular en "-è":
"huitè", "dihuitè"...) falten de veres a la font nova -- restaurades a
mà en `_ORDINALS_PERDUTS` de `rules/val_cat/lexic.py` (hi pertanyen per
categoria gramatical real, no ací).

DECISIÓ (30/09/2026, encara vigent): continua sense cap substitució de
subcadena (`huit->vuit` com a fallback), ni concordança `dos/dues`
(heurística algorítmica a banda, vore `concordanca_dos_dues.py`). Pur
lookup de diccionari.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula

LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lexic_general.json"


def carrega_numerals(path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    """
    >>> lookup = carrega_numerals()
    >>> lookup["huitanta"]
    'vuitanta'
    >>> lookup["díhuit"]
    'divuit'
    >>> lookup["dènou"]
    'dinou'
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        if entrada.get("categoria") != "num":
            continue
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip()
        if not valenciano or not catalan:
            continue
        lookup.setdefault(valenciano, catalan)
    return lookup


class NumeralsRule:
    """Substitueix numerals valencians coneguts per la seua forma
    catalana (vore docstring del mòdul).

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Tinc huitanta anys i en fea díhuit quan vaig anar.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('huitanta', 'vuitanta'), ('díhuit', 'divuit')]
    """

    def __init__(self, path: Path = LEXIC_GENERAL_PATH) -> None:
        self._lookup = carrega_numerals(path)

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
