"""
engine.py -- RuleEngine: orquesta totes les capes del pipeline, en orde fix.

Orde de les capes (per què este orde i no un altre -- vore
final/05_motor_reglas/README.md per la justificació completa):

    1. lexic              (lookup directe al diccionari -- el més "sec")
    2. demostratius
    3. possessius
    4. numerals            (inclou la concordança de gènere "dos/dues")
    5. gentilicis
    6. morfologia_verbal   (només fase 1, present d'indicatiu -- vore mòdul)
    7. perfet              (pretèrit simple -> perifràstic)
    8. elisio              (VA LA ÚLTIMA a propòsit: opera sobre parelles
                            de tokens ja consolidats -- si anara abans,
                            una regla posterior que canviara la paraula
                            següent podria deixar l'elisió apuntant a una
                            vocal/consonant que ja no hi és; secció 11.2
                            de la font ho diu explícitament: "cal aplicar
                            [l'elisió] cada vegada que una altra regla la
                            dispara")
    9. (futur) capa de model -- ara mateix no existix cap classe, la llista
       simplement s'acaba ací fins que n'hi haja una

Cada capa és un objecte amb `.apply(tokens: list[Token]) -> list[Token]`;
RuleEngine només encadena crides en este orde i marca els noms propis abans
de començar -- no conté cap lògica lingüística pròpia. Si un dia cal
reordenar o traure una capa, este és l'ÚNIC lloc a tocar.
"""

from __future__ import annotations

from . import Token, detokenize, marca_noms_propis, tokenize
from .demostratius import DemostratiusRule
from .elisio import ElisioRule
from .gentilicis import GentilicisRule
from .lexic import LexicRule
from .morfologia_verbal import MorfologiaVerbalRule
from .numerals import NumeralsRule
from .perfet import PerfetRule
from .possessius import PossessiusRule


class RuleEngine:
    """Encadena les capes de `self._regles` sobre el text tokenitzat, en
    l'orde fix documentat dalt.

    >>> engine = RuleEngine()
    >>> engine.translate("Este llibre és la meua obra preferida.")
    'Aquest llibre és la meva obra preferida.'
    >>> engine.translate("Tinc huitanta anys i vaig ser el cinqué.")
    'Tinc vuitanta anys i vaig ser el cinquè.'
    >>> engine.translate("El meu amic francés parla de amagat.")
    "El meu amic francès parla d'amagat."
    """

    def __init__(self) -> None:
        self._regles = [
            LexicRule(),
            DemostratiusRule(),
            PossessiusRule(),
            NumeralsRule(),
            GentilicisRule(),
            MorfologiaVerbalRule(),
            PerfetRule(),
            ElisioRule(),
        ]

    def translate(self, text: str) -> str:
        tokens: list[Token] = tokenize(text)
        marca_noms_propis(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return detokenize(tokens)
