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

**Regles de la guia de traducció dialectal (21/10/2026)**, mesurades als
corpus oficials (AVL + BOE, vore `documentacio/hoja_de_ruta_traductor_invers.md`):
- C2: `per_a_infinitiu.py` ("per" + infinitiu -> "per a", excepte "per
  haver"; 92-97% als corpus oficials).
- D1: "aquí" -> "ací" és un parell del diccionari (`lexico_general.json`,
  E1648), el fa `lexic.py` sense codi nou.
- C3: `relatiu_on.py` ("on" -> "a on") **RETIRAT**: només el recolzava el
  benchmark de 151 (estil propi d'eixos textos); la AVL usa "on" sense
  "a" el 79,7%, el BOE el 99,6%, i la guia diu que el registre formal
  preferix "on". La regla de val->cat ("a on" -> "on") es manté.

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

from .. import Token, detokenize, tokenize
from .. import pos_tagger
from .accentuacio import AccentuacioInversRule
from .concordanca_dos_dues import ConcordancaDosDuesInversRule
from .conjugacions_dict import ConjugacionsDictInversRule
from .demostratius import DemostratiusInversRule
from .incoatius import IncoatiusInversRule
from .lexic import LexicInversRule
from .numerals import NumeralsInversRule
from .per_a_infinitiu import PerAInfinitiuInversRule
from .possessius import PossessiusInversRule


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
            PerAInfinitiuInversRule(),
        ]

    def tradueix_tokens(self, text: str, protegits: frozenset[int] = frozenset()) -> list[Token]:
        """Com `translate`, pero torna els tokens abans de detokenitzar --
        útil per a inspeccionar què ha fet cada regla abans d'ajuntar el
        text. (La capa de LLM de cat->val que el va motivar es va retirar el
        21/10/2026: no canviava cap frase.)

        `protegits` (23/10/2026, per a `traductor/model_llengua/`): índexs
        de tokens que cap regla toca; la resta de la frase es tradueix
        igual.

        >>> toks = RuleEngineInvers().tradueix_tokens("La meva nou.", protegits=frozenset({4}))
        >>> detokenize(toks)
        'La meua nou.'
        """
        tokens: list[Token] = tokenize(text)
        for i in protegits:
            tokens[i].is_translated = True
        # Sense `marca_noms_propis` (22/10/2026, decisió de l'usuari): el BOE
        # posa en majúscula moltes paraules comunes ("Servei de Salut",
        # "Comitè de...", "Despeses de personal") i el valencià les tradueix;
        # protegir-les per la majúscula deixava 439 frases mal al BOE
        # estricte (8442 -> 8844 sense la protecció). Decidixen el diccionari
        # i spaCy, com a la resta. Límit conegut: noms de lloc que
        # coincidixen amb paraules comunes ("les Garrigues", "la Noguera",
        # "Maó") i títols ("Cementiri Britànic") es tradueixen.
        pos_tagger.etiqueta(tokens)
        for regla in self._regles:
            tokens = regla.apply(tokens)
        return tokens

    def translate(self, text: str) -> str:
        return detokenize(self.tradueix_tokens(text))
