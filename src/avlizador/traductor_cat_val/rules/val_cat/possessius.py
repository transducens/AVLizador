"""
possessius.py -- Possessius àtons febles i femenins: meua/teua/seua
(occidental) -> meva/teva/seva (oriental).

Font de dades (19/10/2026): `traductor/data/lexic_general.json` (còpia
de `lexico_general.json`), el MATEIX fitxer que fa servir `lexic.py` --
l'usuari va enganxar les 12 files de l'antic `posesivos_cat_val.json`
dins de `lexico_general.json` directament (`categoria: "det"`,
`tipo: "v:lexic_val_avl"`, `fuente: "avl_equip"`). **Esta regla filtra
expressament per `fuente == "avl_equip"`**, no només per `categoria ==
"det"`: la categoria "det" també la fan servir els demostratius dins del
mateix fitxer, i `lexic.py` els deixa fora expressament (cada un amb el
seu propi mòdul) -- confondre'ls ací tornaria a barrejar les dos coses.
El fitxer és un producte cartesià sense filtrar (per cada arrel dona les
4 combinacions singular/plural, incloent les 2 que barregen números:
"meua"->"meves"), així que `_carrega_possessius` es queda només amb els
parells on singular casa amb singular i plural amb plural.

Només afecta les formes FEBLES FEMENINES (meua, teua, seua i els seus
plurals). Les formes masculines (meu, teu, seu, meus, teus, seus) i les
tòniques (mia, tua, sua) NO canvien -- coincidixen als dos dialectes, i per
això no tenen entrada en la taula: si algun dia falta a faltar alguna
d'estes formes en un text convertit, NO és un bug d'esta regla, és que
mai havien de tocar-se.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula

LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lexic_general.json"


def _mateix_nombre(valenciano: str, catalan: str) -> bool:
    return valenciano.endswith("es") == catalan.endswith("es")


def _carrega_possessius(path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        if entrada.get("fuente") != "avl_equip":
            continue
        valenciano = entrada["valenciano"].strip().lower()
        catalan = entrada["catalan"].strip()
        if not _mateix_nombre(valenciano, catalan):
            continue
        lookup[valenciano] = catalan
    return lookup


class PossessiusRule:
    """Substitueix possessius febles femenins occidentals per la forma
    oriental. Les formes masculines/tòniques no apareixen en la taula a
    propòsit (vore docstring del mòdul) -- esta regla les deixa intactes.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("La meua casa i la seua obra, el meu gos.")
    >>> marca_noms_propis(toks)
    >>> toks = PossessiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('meua', 'meva'), ('seua', 'seva')]
    """

    def __init__(self, path: Path = LEXIC_GENERAL_PATH) -> None:
        self._lookup = _carrega_possessius(path)

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
