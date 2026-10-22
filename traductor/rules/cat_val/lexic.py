"""
cat_val/lexic.py -- Lookup invers de lèxic general: el MATEIX
`traductor/data/lexic_general.json` que fa servir `rules/val_cat/lexic.py`,
ara indexat per `catalan`.

**Només el diccionari (22/10/2026, decisió de l'usuari)**: esta capa ja no
té cap llista feta a mà. Es van retirar `flexio_genere_avl.json` (derivava
fem./plural de 3 parells i tapava el lèxic: "noies" -> "xices" en compte
de "xiques"), `canvi_genere_lexic_avl.json` (una sola paraula, "dacsa"),
`categoria_gramatical_lexic.json` (9 homògrafs a mà) i les llistes
`_LEXIC_PERDUT_RESTAURAT_CAT` (rentar/empentar), `_ORDINALS_PERDUTS_CAT`
(25 ordinals amb accent greu, "dihuitè", quan el lèxic ja porta "dihuité")
i `_ORDINALS_BASICS_PERDUTS_CAT` (cinquè -> cinqué...: ara mana la
`canonica` del lèxic, "quint"). Les etiquetes `_PENDENT` del camp `tipo`
són metadades del proveïdor: les entrades s'usen igual que les altres.

**Col·lisions**: si una forma catalana té més d'un candidat valencià, mana
`canonica: true` (regla fixa de l'usuari, 20/10/2026); sense canònica
única, s'exclou (preferix fals negatiu).

**Lèxic multi-paraula català (13/10/2026)**: entrades amb el català en 2-3
paraules i el valencià en una ("blat de moro"->"dacsa", "gall
dindi"->"polit"...). Es busca la frase MES LLARGA que comence en cada
token abans de l'intent d'una sola paraula.

**Homògrafs (22/10/2026)**: les entrades `problema: "homonimia_lexica"` del
lèxic diuen quina forma és ambigua i quines lectures té ("nou": adj, n,
num). Si la categoria de l'entrada no la comparteix cap altra lectura,
només es tradueix quan spaCy li dona eixa categoria ("manca" NOUN ->
"carència"; "manca" VERB, no). Vore `rules/__init__.py::carrega_homografs`.

**Gènere i article (22/10/2026)**: quan un nom canvia de gènere en
traduir-se ("el blat de moro" -> "la dacsa", "les despeses" -> "els
gastos"), es corregix el determinant d'abans, contraccions incloses
("del" <-> "de la"), i després l'apòstrof ("la sortida" -> "l'eixida",
`corregeix_article_abans`). El gènere original el dona spaCy dins de la
frase; el nou, spaCy sobre la paraula traduïda (vore
`pos_tagger.genere_tras_substitucio`). Límit conegut: només es mira el
determinant immediatament anterior, no els adjectius.

**Contracció "al"/"del" desfeta davant de vocal (13/10/2026, RC016)**:
"Al sortir" -> "A l'eixir" (`corregeix_contraccio_al_abans`).
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import (
    Token,
    aplica_amb_prefix_elidit,
    carrega_homografs,
    corregeix_article_abans,
    corregeix_contraccio_al_abans,
    corregeix_determinant_abans,
    corregeix_elisio_de_abans,
    homograf_compatible,
    paraules_segudents_son,
    preserva_majuscula,
    separa_prefix_elidit,
)
from ..pos_tagger import genere_tras_substitucio

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
LEXIC_GENERAL_PATH = _DATA / "lexic_general.json"

# Categories de `lexico_general.json` que pertanyen a esta capa: "num" i
# "det" van als seus propis mòduls (numerals, demostratius, possessius),
# que lligen el mateix fitxer.
_CATEGORIES_LEXIC_GENERAL = {"n", "adj", "adv", "cnjadv", "pr", "ij", "prn"}


def _invertix_sense_ambiguitat(entrades: list[tuple[str, str, bool]]) -> dict[str, str]:
    """Agrupa parells `(valenciano, catalan, canonica)` per `catalan`. Si hi
    ha un únic candidat valencià, es queda amb ell. Si n'hi ha més d'un,
    REGLA FIXA de l'usuari (20/10/2026): en cas de dubte mana el camp
    `canonica` del proveïdor -- es tria el candidat marcat `canonica: true`
    si n'hi ha exactament un; si no n'hi ha cap (o n'hi ha més d'un),
    s'exclou (preferix fals negatiu).

    >>> _invertix_sense_ambiguitat([("xic", "noi", True), ("xiquet", "noi", False)])
    {'noi': 'xic'}
    >>> _invertix_sense_ambiguitat([("a", "x", False), ("b", "x", False)])
    {}
    """
    candidats: dict[str, set[str]] = {}
    canoniques: dict[str, set[str]] = {}
    for valenciano, catalan, canonica in entrades:
        candidats.setdefault(catalan, set()).add(valenciano)
        if canonica:
            canoniques.setdefault(catalan, set()).add(valenciano)
    resultat: dict[str, str] = {}
    for cat, vals in candidats.items():
        if len(vals) == 1:
            resultat[cat] = next(iter(vals))
        elif len(canoniques.get(cat, ())) == 1:
            resultat[cat] = next(iter(canoniques[cat]))
    return resultat


def _entrades_lexic(path: Path) -> list[tuple[str, str, bool]]:
    """`(valenciano, catalan, canonica)` de les entrades d'esta capa, en
    minúscules. Els topònims (`tipo: "v:top_gva"`) no s'apliquen mai."""
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    entrades: list[tuple[str, str, bool]] = []
    for entrada in dades:
        if entrada.get("tipo") == "v:top_gva":
            continue
        if entrada.get("categoria") not in _CATEGORIES_LEXIC_GENERAL:
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if valenciano and catalan:
            entrades.append((valenciano, catalan, bool(entrada.get("canonica"))))
    return entrades


def carrega_lexic_invers(lexic_general_path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    """`{forma catalana: forma valenciana}` d'una sola paraula.

    >>> lookup = carrega_lexic_invers()
    >>> lookup["nen"], lookup["nena"], lookup["noies"]
    ('xiquet', 'xiqueta', 'xiques')
    >>> lookup["signant"], lookup["acetilè"], lookup["avui"]
    ('firmant', 'acetilé', 'hui')
    >>> lookup["divuitè"], lookup["cinquè"], lookup["vuitè"]
    ('dihuité', 'quint', 'octau')
    >>> lookup["durada"]  # entrada `_PENDENT`, s'usa igual
    'duració'
    >>> lookup["desprès"], lookup["ensenyament"]
    ('després', 'ensenyança')

    "què" no és un parell (normatiu als dos dialectes) i la canònica
    "mentre"->"mentre" vol dir que "mentre" no es toca:

    >>> "què" in lookup, "mentre" in lookup
    (False, False)
    """
    entrades = [
        (val, cat, canonica)
        for val, cat, canonica in _entrades_lexic(lexic_general_path)
        if " " not in val and " " not in cat
    ]
    # Les entrades IDÈNTIQUES als dos costats (21/10/2026) participen en la
    # tria per `canonica` i es lleven DESPRÉS: si la canònica d'un grup és
    # "mentre"->"mentre" (E1647, en col·lisió amb E0040 "mentres"->"mentre"),
    # vol dir "no traduïsques".
    return {cat: val for cat, val in _invertix_sense_ambiguitat(entrades).items() if cat != val}


def carrega_frases_invers(path: Path = LEXIC_GENERAL_PATH) -> dict[tuple[str, ...], str]:
    """Entrades on el català és 2-3 paraules i el valencià UNA:
    `{(paraula1, paraula2, ...): forma_valenciana}`, en minúscules.

    >>> frases = carrega_frases_invers()
    >>> frases[("blat", "de", "moro")]
    'dacsa'
    >>> frases[("gall", "dindi")]
    'polit'
    """
    entrades = [
        (val, tuple(cat.split()), canonica)
        for val, cat, canonica in _entrades_lexic(path)
        if " " not in val and " " in cat
    ]
    return _invertix_sense_ambiguitat(entrades)


class LexicInversRule:
    """Substitueix paraules catalanes conegudes per la seua forma
    valenciana (vore docstring del mòdul). Mai toca un token ja traduït
    ni un possible nom propi.

    >>> from .. import tokenize, marca_noms_propis, detokenize, pos_tagger
    >>> def tradueix(text):
    ...     toks = tokenize(text)
    ...     marca_noms_propis(toks)
    ...     pos_tagger.etiqueta(toks)
    ...     return detokenize(LexicInversRule().apply(toks))
    >>> tradueix("Vull parlar amb el meu servei.")
    'Vull parlar amb el meu servici.'

    Nom propi protegit i prefix elidit:

    >>> tradueix("Coneixes a Nen, el meu gos?")
    'Coneixes a Nen, el meu gos?'
    >>> tradueix("Parlem d'algarvès.")
    "Parlem d'algarvés."

    Gènere: el determinant d'abans concorda amb el nom nou, contraccions
    incloses, i l'apòstrof es posa o es lleva segons la paraula nova:

    >>> tradueix("El pagament de les despeses.")
    'El pagament dels gastos.'
    >>> tradueix("El preu de l'habitatge.")
    'El preu de la vivenda.'
    >>> tradueix("Agafa l'escombra.")
    'Agafa la granera.'
    >>> tradueix("Va ser el darrer viatge.")
    "Va ser l'últim viatge."

    Límit conegut: si spaCy no sap el gènere de la paraula nova, el
    determinant es queda com estava (vore `pos_tagger.genere_de`):

    >>> tradueix("Mengem el blat de moro cada estiu.")
    'Mengem el dacsa cada estiu.'
    >>> tradueix("Menjo el préssec.")
    'Menjo el bresquilla.'

    Homògrafs del lèxic (`homonimia_lexica`): "nou" adjectiu no es toca;
    "manca" com a verb tampoc, com a nom sí:

    >>> tradueix("En un nou procés d'expansió.")
    "En un nou procés d'expansió."
    >>> tradueix("Aquesta regió manca relativament de grans cràters.")
    'Aquesta regió manca relativament de grans cràters.'
    >>> tradueix("Patix una gran manca afectiva.")
    'Patix una gran carència afectiva.'

    Contracció "al" desfeta en "a l'" quan la paraula nova comença en vocal,
    i "de" apostrofat (22/10/2026; abans "de investigació"):

    >>> tradueix("Es va mirar al mirall.")
    "Es va mirar a l'espill."
    >>> tradueix("Un projecte de recerca.")
    "Un projecte d'investigació."

    Majúscules: les paraules comunes en majúscula es tradueixen (el motor
    ja no les protegix com a nom propi, vore `engine.py`), i una paraula
    sencera en majúscules es queda en majúscules, article inclòs:

    >>> from .engine import RuleEngineInvers
    >>> RuleEngineInvers().translate("El Servei de Salut i L’HABITATGE.")
    'El Servici de Salut i LA VIVENDA.'
    """

    def __init__(
        self,
        lexic_general_path: Path = LEXIC_GENERAL_PATH,
        frases_path: Path = LEXIC_GENERAL_PATH,
    ) -> None:
        self._lookup = carrega_lexic_invers(lexic_general_path)
        self._homografs, _ = carrega_homografs(lexic_general_path)
        frases = carrega_frases_invers(frases_path)
        self._frases_per_inici: dict[str, list[tuple[tuple[str, ...], str]]] = {}
        for paraules, forma in frases.items():
            self._frases_per_inici.setdefault(paraules[0], []).append((paraules, forma))
        for candidats in self._frases_per_inici.values():
            candidats.sort(key=lambda pf: -len(pf[0]))  # mes llarga primer

    def _intenta_frase(self, tokens: list[Token], i: int) -> bool:
        candidats = self._frases_per_inici.get(tokens[i].surface.lower())
        if not candidats:
            return False
        for paraules, forma in candidats:
            if len(paraules) > 1 and not paraules_segudents_son(tokens, i, list(paraules[1:])):
                continue
            tokens[i].translated = preserva_majuscula(tokens[i].surface, forma)
            tokens[i].is_translated = True
            pendents = len(paraules) - 1
            j = i + 1
            while pendents > 0 and j < len(tokens):
                if not tokens[j].surface.isspace():
                    pendents -= 1
                tokens[j].translated = ""
                tokens[j].is_translated = True
                j += 1
            self._concorda(tokens, i, forma)
            return True
        return False

    def _concorda(self, tokens: list[Token], i: int, forma: str) -> None:
        """Determinant i apòstrof d'abans, un cop `tokens[i]` ja porta `forma`."""
        genere, canvia = genere_tras_substitucio(tokens[i], forma)
        if canvia:
            corregeix_determinant_abans(tokens, i, genere)
        corregeix_contraccio_al_abans(tokens, i)
        corregeix_article_abans(tokens, i)
        corregeix_elisio_de_abans(tokens, i)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            if self._intenta_frase(tokens, i):
                continue
            minuscules = tok.surface.lower()
            forma = self._lookup.get(minuscules)
            if forma is not None:
                if not homograf_compatible(tok.pos, minuscules, self._homografs):
                    continue
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                self._concorda(tokens, i, forma)
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = self._lookup.get(resta.lower())
            if forma is None or not homograf_compatible(tok.pos, resta.lower(), self._homografs):
                continue
            genere, _ = genere_tras_substitucio(tok, forma, resta)
            aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma, genere)
            tok.is_translated = True
        return tokens
