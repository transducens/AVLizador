"""
engine.py -- RuleEngine: orquesta totes les capes del pipeline, en orde fix.

Orde de les capes (30/09/2026, arquitectura reduïda a pur lookup de
diccionari + 2 regles de sufix productives -- vore `traductor/README.md`
per l'abast complet i el raonament del canvi):

    1. lexic               (lookup directe al diccionari general +
                            accentuació, font_mauricio)
    2. conjugacions_dict   (lookup directe de formes verbals, font_mauricio)
    3. possessius          (lookup directe de possessius, font_mauricio)
    4. numerals            (lookup directe de numerals, font_mauricio)
    5. accentuacio         (sufix -és->-ès i -éixer->-èixer, patró
                            productiu, afegida 30/09/2026)
    6. incoatius           (sufix -ix->-eix, patró productiu, afegida
                            30/09/2026)

Les capes 1-4 són lookups exactes; 5-6 són regles de SUFIX (patró
productiu, no llista tancada) -- per això van DESPRÉS de les de
diccionari: si una forma ja es coneix amb exactitud (p.ex. "francés" ja
és a `lexic_acentuacio_mauricio.json`), no té sentit deixar que una regla
de sufix més feble la reprocesse. Cada capa salta qualsevol token ja
marcat `is_translated` per una capa anterior.

Cada capa és un objecte amb `.apply(tokens: list[Token]) -> list[Token]`;
RuleEngine només encadena crides en este orde i marca els noms propis abans
de començar -- no conté cap lògica lingüística pròpia. Si un dia cal
reordenar o traure una capa, este és l'ÚNIC lloc a tocar.
"""

from __future__ import annotations

from . import Token, detokenize, marca_noms_propis, tokenize
from .accentuacio import AccentuacioRule
from .conjugacions_dict import ConjugacionsDictRule
from .incoatius import IncoatiusRule
from .lexic import LexicRule
from .numerals import NumeralsRule
from .possessius import PossessiusRule


class RuleEngine:
    """Encadena les capes de `self._regles` sobre el text tokenitzat, en
    l'orde fix documentat dalt.

    >>> engine = RuleEngine()
    >>> engine.translate("Tinc huitanta anys i el meu amic francés parla.")
    'Tinc vuitanta anys i el meu amic francès parla.'
    >>> engine.translate("Vull que els oferisca ajuda encara que tinguen pressa.")
    'Vull que els ofereixi ajuda encara que tinguin pressa.'
    >>> engine.translate("La meua casa i la seua obra.")
    'La meva casa i la seva obra.'
    >>> engine.translate("Vull conéixer qui establix esta norma.")
    'Vull conèixer qui estableix esta norma.'
    """

    def __init__(self) -> None:
        self._regles = [
            LexicRule(),
            ConjugacionsDictRule(),
            PossessiusRule(),
            NumeralsRule(),
            AccentuacioRule(),
            IncoatiusRule(),
        ]

    def translate(self, text: str) -> str:
        tokens: list[Token] = tokenize(text)
        marca_noms_propis(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return detokenize(tokens)
