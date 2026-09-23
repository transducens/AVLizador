"""
possessius.py -- Possessius àtons febles i femenins: meua/teua/seua
(occidental) -> meva/teva/seva (oriental). Taula copiada literalment de
final/02_reglas_dialectales/reglas_dialectales.md, secció 2.

Només afecta les formes FEBLES FEMENINES (meua, teua, seua i els seus
plurals). Les formes masculines (meu, teu, seu, meus, teus, seus) i les
tòniques (mia, tua, sua) NO canvien -- coincidixen als dos dialectes, i per
això no tenen entrada en la taula: si algun dia falta a faltar alguna
d'estes formes en un text convertit, NO és un bug d'esta regla, és que
mai havien de tocar-se.
"""

from __future__ import annotations

from . import Token, preserva_majuscula

_POSSESSIUS = {
    "meua": "meva",
    "meues": "meves",
    "teua": "teva",
    "teues": "teves",
    "seua": "seva",
    "seues": "seves",
}


class PossessiusRule:
    """Substitueix possessius febles femenins occidentals per la forma
    oriental. Les formes masculines/tòniques no apareixen en la taula a
    propòsit (vore docstring del mòdul) -- esta regla les deixa intactes.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("La meua casa i el meu gos.")
    >>> marca_noms_propis(toks)
    >>> toks = PossessiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('meua', 'meva')]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = _POSSESSIUS.get(tok.surface.lower())
            if forma is None:
                continue
            tok.translated = preserva_majuscula(tok.surface, forma)
            tok.is_translated = True
        return tokens
