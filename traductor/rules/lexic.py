"""
lexic.py -- Capa 1 del pipeline: substitució directa per lèxic diferencial.
Fusiona 2 fonts, totes dos còpies de fitxers de
`02_reglas_dialectales/lexico/font_mauricio/` (equip AVLizador), per orde
de prioritat quan es contradiuen (la primera que definix una paraula
guanya):

    1. lexic_mauricio.json            -- lèxic general (còpia de
       `lexico_general_limpio.json`), filtrat: descarta entrades
       "_PENDENT" (sense verificar), topònims (`tipo: "v:top_gva"`, el
       motor mai els aplicaria -- protegix noms propis), entrades on
       valencià==català (sense diferència real), i valencians de més
       d'una paraula (esta capa fa lookup d'un sol token). Quan una
       mateixa paraula té més d'una traducció possible, prioritza la
       marcada `canonica: true`; si cap ho és o n'hi ha més d'una, es
       queda la primera trobada.
    2. lexic_acentuacio_mauricio.json -- patrons d'accentuació (còpia de
       `acentuacion_limpio.json`), 695 parelles.

DECISIÓ (30/09/2026): esta capa ara és NOMÉS diccionari de Mauricio --
s'han llevat les fonts Apertium-368, Paula Guerrero i els parells AVL-only
(`vos/vindre/valdre`, `tindre/obtindre/vore`, `últim/darrer`...), junt amb
totes les regles morfològiques/de sufix (`demostratius.py`,
`gentilicis.py`, `morfologia_verbal.py`, `perfet.py`, `locucions.py`,
`elisio.py`) i els seus fitxers AVL-only associats. El traductor complet
ara és pur lookup de diccionari (`lexic.py` + `conjugacions_dict.py` +
`numerals.py` + `possessius.py`) més la separació de prefixos elidits
(`separa_prefix_elidit`) -- res de generalització per sufix ni de
reconstrucció algorítmica. Vore `traductor/README.md` per l'abast i les
pèrdues de cobertura que això implica.

Regressió coneguda i acceptada (30/09/2026): "xiquet" tenia dos entrades a
Mauricio amb `canonica: false` totes dos ("chiquillo"->"noi",
"nene"->"nen") -- abans guanyava "nen" perquè `lexic_paula_guerrero.json`
(font ara retirada) el confirmava sense ambigüitat. Ara `_resol_mauricio`
es queda amb la primera del fitxer ("noi") sense cap manera de triar
millor només amb dades de Mauricio. Acceptat a propòsit com a conseqüència
de fer esta capa pur-Mauricio; no s'ha afegit cap override extern.

Excepció mantinguda (bug de dades, no regla dialectal): "després" ve
llistat a `acentuacion_limpio.json` com si seguira el patró d'accentuació
general ("després" -> "desprès"), però és un error del fitxer font --
"després" mai canvia en cap dels dos dialectes (confirmat empíricament,
afectava 10 de les 150 frases del benchmark). Es descarta ací a mà, no
perquè siga una "regla" sinó perquè és l'única manera de no repetir un
error de transcripció ja conegut al fitxer font.

Esta és la ÚNICA capa que fa lookup en un diccionari en compte d'aplicar una
regla morfològica -- cobrix paraules que canvien de forma per motius
purament lèxics, sense cap patró gramatical que ho prediga (p.ex. "roig" ->
"vermell" en el sentit de color). Justament per això és la MÉS perillosa de
les capes si no es filtren bé els noms propis i els homògrafs: "roig"
també és un cognom/nom (en eixe cas mai s'ha de traduir), i el projecte ja
es va trobar el mateix problema abans amb "blanca" (adjectiu) vs. "Blanca"
(nom de dona). Per això LexicRule mai toca un token amb
`is_proper_noun = True` (fixat per `marca_noms_propis()` abans de córrer
cap regla).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

_DATA = Path(__file__).resolve().parent.parent / "data"
MAURICIO_PATH = _DATA / "lexic_mauricio.json"
ACENTUACIO_MAURICIO_PATH = _DATA / "lexic_acentuacio_mauricio.json"

# Bug de dades conegut al fitxer font (vore docstring del mòdul): "després"
# no és una excepció dialectal, és un error de transcripció confirmat.
_BUG_DADES_CONEGUTS = {"després"}


def _resol_mauricio(entries: list[dict]) -> str:
    """Tria quina forma catalana usar quan una paraula valenciana de
    Mauricio té més d'una entrada (polisèmia): la marcada `canonica: true`
    si n'hi ha exactament una, si no la primera trobada al fitxer."""
    canoniques = [e for e in entries if e.get("canonica") is True]
    triada = canoniques[0] if len(canoniques) == 1 else entries[0]
    return triada["catalan"].strip()


def _carrega_mauricio_lexic(path: Path) -> dict[str, str]:
    dades = json.loads(path.read_text(encoding="utf-8"))
    per_paraula: dict[str, list[dict]] = {}
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        per_paraula.setdefault(valenciano.lower(), []).append(entrada)
    return {val: _resol_mauricio(entries) for val, entries in per_paraula.items()}


def _carrega_acentuacio_mauricio(path: Path) -> dict[str, str]:
    dades = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        if valenciano.lower() in _BUG_DADES_CONEGUTS:
            continue
        lookup.setdefault(valenciano.lower(), catalan)
    return lookup


def carrega_lexic(
    mauricio_path: Path = MAURICIO_PATH,
    acentuacio_path: Path = ACENTUACIO_MAURICIO_PATH,
) -> dict[str, str]:
    """Fusiona les 2 fonts documentades al mòdul, per orde de prioritat
    (la primera font que definix una paraula guanya sobre la segona).

    >>> lookup = carrega_lexic()
    >>> lookup["xiquet"]
    'noi'
    >>> lookup["firmant"]
    'signant'
    >>> lookup["acetilé"]
    'acetilè'
    >>> "després" in lookup
    False
    """
    lookup: dict[str, str] = {}
    for carregador, path in (
        (_carrega_mauricio_lexic, mauricio_path),
        (_carrega_acentuacio_mauricio, acentuacio_path),
    ):
        for val, cat in carregador(path).items():
            lookup.setdefault(val, cat)
    return lookup


class LexicRule:
    """Substitueix paraules valencianes conegudes per la seua forma
    catalana (vore docstring del mòdul per a l'orde de fonts). Mai toca un
    token ja traduït per una capa anterior (`is_translated`) ni un
    possible nom propi (`is_proper_noun`, fixat per `marca_noms_propis()`
    abans de córrer cap regla -- vore rules/__init__.py).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Hui vull parlar amb el meu servici.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('servici', 'servei')]

    Nom propi protegit encara que casualment coincidisca amb una entrada
    del lèxic:

    >>> toks = tokenize("Coneixes a Xiquet, el meu gos?")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Paraula enganxada a un prefix elidit ("d'", "l'", "s'"...): el
    tokenitzador la dona com un sol token (vore `separa_prefix_elidit` a
    rules/__init__.py), així que cal separar el prefix per a poder-la
    trobar al diccionari, i tornar-lo a enganxar al resultat:

    >>> toks = tokenize("Parlem d'algarvés.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'algarvés", "d'algarvès")]

    Quan la paraula trobada canvia de vocal inicial a consonant inicial,
    l'elisió original ja no té sentit i es desfà (bug real, 30/09/2026--
    vore `aplica_amb_prefix_elidit` a rules/__init__.py):

    >>> from . import detokenize
    >>> toks = tokenize("A l'eixir carrec la caixa.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> detokenize(toks)
    'Al sortir carrec la caixa.'
    """

    def __init__(
        self,
        mauricio_path: Path = MAURICIO_PATH,
        acentuacio_path: Path = ACENTUACIO_MAURICIO_PATH,
    ) -> None:
        self._lookup = carrega_lexic(mauricio_path, acentuacio_path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = self._lookup.get(tok.surface.lower())
            if forma is not None:
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = self._lookup.get(resta.lower())
            if forma is not None:
                aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma)
                tok.is_translated = True
        return tokens
