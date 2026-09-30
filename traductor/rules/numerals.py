"""
numerals.py -- Lookup exacte contra `traductor/data/numerals_mauricio.json`
(còpia de `numerales_limpio.json`, equip AVLizador): cobrix tota la
família huit/vuit (huitanta->vuitanta, huitanta-huité->vuitanta-vuitè...)
I les arrels "dinou"/"disset" + derivats ("dènou"->"dinou",
"denové"->"dinovè"). Inclou "díhuit"->"divuit" (fila 82 del fitxer font)
sense necessitat de cap cas especial, perquè és lookup exacte, no
substitució de subcadena.

Exclusió: 4 files de "vuitavat" al fitxer font semblen una extracció
trencada (el mateix català "vuitavat" repetit per a 4 valencians
diferents -- probablement havien de ser les 4 formes de gènere/nombre i es
va perdre l'alineació); s'exclouen explícitament del lookup.

DECISIÓ (30/09/2026): s'ha llevat d'ací tot el que NO era lookup exacte de
Mauricio -- la substitució de subcadena `huit->vuit` (fallback per a
compostos no enumerats), els ordinals `-é->-è` (taula AVL-only, sense
fitxer font), i la concordança de gènere `dos/dues` (heurística
algorítmica). El traductor complet ara és pur lookup de diccionari --
vore `traductor/README.md` per l'abast i les pèrdues de cobertura que
això implica (numerals compostos no enumerats, ordinals, "dos/dues").
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Token, preserva_majuscula

MAURICIO_PATH = Path(__file__).resolve().parent.parent / "data" / "numerals_mauricio.json"

# Vore docstring del mòdul: extracció trencada al fitxer font, s'exclouen.
_VUITAVAT_EXCLOSOS = {"huitavdes", "huitavda", "huitavts", "huitavt"}


def carrega_numerals(path: Path = MAURICIO_PATH) -> dict[str, str]:
    """
    >>> lookup = carrega_numerals()
    >>> lookup["huitanta"]
    'vuitanta'
    >>> lookup["díhuit"]
    'divuit'
    >>> lookup["dènou"]
    'dinou'
    >>> "huitavdes" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        valenciano = entrada["valenciano"].strip().lower()
        if valenciano in _VUITAVAT_EXCLOSOS:
            continue
        lookup.setdefault(valenciano, entrada["catalan"].strip())
    return lookup


class NumeralsRule:
    """Substitueix numerals valencians coneguts per la seua forma
    catalana (vore docstring del mòdul).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Tinc huitanta anys i en fea díhuit quan vaig anar.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('huitanta', 'vuitanta'), ('díhuit', 'divuit')]
    """

    def __init__(self, path: Path = MAURICIO_PATH) -> None:
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
