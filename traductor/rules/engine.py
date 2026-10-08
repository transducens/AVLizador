"""
engine.py -- RuleEngine: orquesta totes les capes del pipeline, en orde fix.

Capa 0 OPCIONAL (07/10/2026, vore `pos_tagger.py`): abans de les 9 capes de
regles, s'intenta etiquetar cada token amb la seua categoria gramatical
(spaCy, `ca_core_news_sm`). Nomes la fa servir `ConjugacionsDictRule` (capa
2), per a no aplicar una conjugacio verbal RARA sobre una paraula que en
eixe context es, de veres, un substantiu/preposicio/etc. ("persones",
"pobles", "projectes"... vore `pos_tagger.py` per als casos reals). Es
estrictament opcional: si spaCy no esta instal·lat, `etiqueta()` no fa res
i el pipeline es comporta exactament igual que abans.

Orde de les capes (30/09/2026, arquitectura reduïda a pur lookup de
diccionari + 2 regles de sufix productives -- vore `traductor/README.md`
per l'abast complet i el raonament del canvi):

    1. lexic               (lookup directe al diccionari general +
                            accentuació, font_mauricio)
    2. conjugacions_dict   (lookup directe de formes verbals, font_mauricio)
    3. possessius          (lookup directe de possessius, font_mauricio)
    4. numerals            (lookup directe de numerals, font_mauricio)
    5. concordanca_dos_dues (corregix "dos"->"dues" darrere d'un marcador
                            de femení plural -- "les"/"estes"/"eixes"...,
                            afegida 01/10/2026, vore docstring del mòdul)
    6. relatiu_on          (corregix "a on"->"on" com a relatiu/interrogatiu
                            locatiu, afegida 02/10/2026, vore docstring
                            del mòdul)
    7. demostratius        (lookup directe de demostratius, AVL-only --
                            recreada 30/09/2026, cap fitxer de Mauricio
                            llista un paradigma gramatical tancat com est)
    8. accentuacio         (sufix -és->-ès i -éixer->-èixer, patró
                            productiu, afegida 30/09/2026)
    9. incoatius           (sufix -ix->-eix, patró productiu, afegida
                            30/09/2026)

Les capes 1-4 i 7 són lookups exactes; 5-6 són regles de CONCORDANÇA/PATRÓ
(miren els tokens veïns, no un diccionari) i 8-9 són regles de SUFIX
(patró productiu, no llista tancada) -- per això van DESPRÉS de les de
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
from . import pos_tagger
from .accentuacio import AccentuacioRule
from .concordanca_dos_dues import ConcordancaDosDuesRule
from .conjugacions_dict import ConjugacionsDictRule
from .demostratius import DemostratiusRule
from .incoatius import IncoatiusRule
from .lexic import LexicRule
from .numerals import NumeralsRule
from .possessius import PossessiusRule
from .relatiu_on import RelatiuOnRule


class RuleEngine:
    """Encadena les capes de `self._regles` sobre el text tokenitzat, en
    l'orde fix documentat dalt.

    >>> engine = RuleEngine()
    >>> engine.translate("Tinc huitanta anys i el meu amic francés parla.")
    'Tinc vuitanta anys i el meu amic francès parla.'
    >>> engine.translate("Vull que els oferisca ajuda encara que tinguen pressa.")
    'Vull que els ofereixi ajuda encara que tinguen pressa.'
    >>> engine.translate("La meua casa i la seua obra.")
    'La meva casa i la seva obra.'
    >>> engine.translate("Vull conéixer qui establix esta norma.")
    'Vull conèixer qui estableix aquesta norma.'
    >>> engine.translate("Este xiquet i eixa dona i aquella casa.")
    'Aquest nen i aquesta dona i aquella casa.'
    >>> engine.translate("Estes dos germanes i les dos institucions.")
    'Aquestes dues germanes i les dues institucions.'
    >>> engine.translate("La casa a on vivia era menuda.")
    'La casa on vivia era menuda.'
    """

    def __init__(self) -> None:
        self._regles = [
            LexicRule(),
            ConjugacionsDictRule(),
            PossessiusRule(),
            NumeralsRule(),
            ConcordancaDosDuesRule(),
            RelatiuOnRule(),
            DemostratiusRule(),
            AccentuacioRule(),
            IncoatiusRule(),
        ]

    def translate(self, text: str) -> str:
        tokens: list[Token] = tokenize(text)
        marca_noms_propis(tokens)
        pos_tagger.etiqueta(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return detokenize(tokens)
