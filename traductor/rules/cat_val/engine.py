"""
cat_val/engine.py -- Motor de regles en sentit invers (català->valencià).
Mirall de `rules/val_cat/engine.py`, pero NO amb el mateix conjunt de capes --
vore `documentacio/hoja_de_ruta_traductor_invers.md` per al perquè de
cada diferència.

`incoatius.py` i `relatiu_on.py` SÍ s'han implementat (13/10/2026):
- `incoatius.py`: llista TANCADA de 7 arrels verbals amb evidència real
  (establir/servir/aconseguir/requerir/oferir/exhaurir/coincidir) -- NO
  una regla de sufix general, perquè en català "estableix" (ha de
  canviar) i "apareix" (mai canvia) acaben IGUAL, i la distinció és
  LÈXICA, no ortogràfica (a diferència de l'original val->cat, on mirar
  la lletra abans d'"ix" sí que distingix els dos grups). Vore
  `incoatius.py` per al detall.
- `relatiu_on.py`: 8 casos reals al benchmark invertit, els 8 volen
  "on"->"a on", amb 2 excepcions conegudes (construccions d'èmfasi
  temporal "és on"/"ha sigut...on") acceptades sense heurística nova
  (massa poca evidència) -- vore `relatiu_on.py` per a l'evidència
  completa.

Pos_tagger (spaCy) es crida igual que en `rules/val_cat/engine.py` -- i ací amb
MES fiabilitat, perquè l'entrada ja és català real (vore hoja de ruta,
secció sobre spaCy).
"""

from __future__ import annotations

from .. import Token, detokenize, marca_noms_propis, tokenize
from .. import pos_tagger
from .accentuacio import AccentuacioInversRule
from .concordanca_dos_dues import ConcordancaDosDuesInversRule
from .conjugacions_dict import ConjugacionsDictInversRule
from .demostratius import DemostratiusInversRule
from .incoatius import IncoatiusInversRule
from .lexic import LexicInversRule
from .numerals import NumeralsInversRule
from .possessius import PossessiusInversRule
from .preposicions_locucions import PreposicionsLocucionsInversRule
from .relatiu_on import RelatiuOnInversRule


class RuleEngineInvers:
    """Encadena les capes inverses sobre el text tokenitzat.

    >>> engine = RuleEngineInvers()
    >>> engine.translate("Tinc vuitanta anys i el meu amic francès parla.")
    'Tinc huitanta anys i el meu amic francés parla.'
    >>> engine.translate("La meva casa i la seva obra.")
    'La meua casa i la seua obra.'
    >>> engine.translate("Aqueixa dona i aquella casa.")
    'Eixa dona i aquella casa.'
    >>> engine.translate("Les dues institucions i les dues germanes.")
    'Les dos institucions i les dos germanes.'
    """

    def __init__(self) -> None:
        self._regles = [
            LexicInversRule(),
            ConjugacionsDictInversRule(),
            PossessiusInversRule(),
            NumeralsInversRule(),
            ConcordancaDosDuesInversRule(),
            DemostratiusInversRule(),
            IncoatiusInversRule(),
            AccentuacioInversRule(),
            PreposicionsLocucionsInversRule(),
            RelatiuOnInversRule(),
        ]

    def translate(self, text: str) -> str:
        tokens: list[Token] = tokenize(text)
        marca_noms_propis(tokens)
        pos_tagger.etiqueta(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return detokenize(tokens)
