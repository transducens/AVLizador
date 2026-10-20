"""
cat_val/engine.py -- Motor de regles en sentit invers (català->valencià).
Mirall de `rules/val_cat/engine.py`, pero NO amb el mateix conjunt de capes --
vore `documentacio/hoja_de_ruta_traductor_invers.md` per al perquè de
cada diferència.

**`incoatius.py` REESCRIT sense llista a mà (20/10/2026)**: abans era
una llista TANCADA de 7 arrels verbals (establir/servir/aconseguir/
requerir/oferir/exhaurir/coincidir). Ara decidix spaCy (VERB + lema en
"-ir") validat contra els infinitius reals de
`conjugacions_dialectals.json` -- cap verb escrit a mà. Vore
`incoatius.py` per a l'explicació completa del problema.

`relatiu_on.py` SÍ s'ha implementat (13/10/2026):
- `relatiu_on.py`: 8 casos reals al benchmark invertit, els 8 volen
  "on"->"a on", amb 2 excepcions conegudes (construccions d'èmfasi
  temporal "és on"/"ha sigut...on") acceptades sense heurística nova
  (massa poca evidència) -- vore `relatiu_on.py` per a l'evidència
  completa.

Pos_tagger (spaCy) es crida igual que en `rules/val_cat/engine.py` -- i ací amb
MES fiabilitat, perquè l'entrada ja és català real (vore hoja de ruta,
secció sobre spaCy).

**`preposicions_locucions.py` RETIRADA del pipeline (14/10/2026)**: vore
`rules/val_cat/engine.py` per l'explicació completa (la regla "a"/"en"
no generalitzava i la regla general C1 mesurada contra els dos
benchmarks (151 + gplsi, 1.958 frases) va eixir amb nomes 1,5% de
conversions reals -- es descarta del tot, no és soroll que valga la pena
perseguir). S'ha llevat també l'única entrada que quedava ("per a
acabar"->"per acabar", un marcador discursiu fix sense relació amb la
regla C1) perquè l'usuari va decidir llevar el fitxer sencer -- si cal
recuperar eixe cas puntual (2 evidències, RC112/RC118), fer-ho en un
fitxer nou a banda, no ressuscitar este.
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
            RelatiuOnInversRule(),
        ]

    def translate(self, text: str) -> str:
        tokens: list[Token] = tokenize(text)
        marca_noms_propis(tokens)
        pos_tagger.etiqueta(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return detokenize(tokens)
