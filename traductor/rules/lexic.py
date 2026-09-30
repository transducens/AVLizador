"""
lexic.py -- Capa 1 del pipeline: substitució directa per lèxic diferencial.
Fusiona 3 fonts, per orde de prioritat quan es contradiuen (la primera que
definix una paraula guanya):

    1. flexio_genere_avl.json         -- derivació de gènere/nombre per a
       un grapat de paraules CURADES A MÀ (no cap fitxer de Mauricio),
       vore docstring de `_carrega_flexio_genere`.
    2. lexic_mauricio.json            -- lèxic general (còpia de
       `lexico_general_limpio.json`), filtrat: descarta entrades
       "_PENDENT" (sense verificar), topònims (`tipo: "v:top_gva"`, el
       motor mai els aplicaria -- protegix noms propis), entrades on
       valencià==català (sense diferència real), i valencians de més
       d'una paraula (esta capa fa lookup d'un sol token). Quan una
       mateixa paraula té més d'una traducció possible, prioritza la
       marcada `canonica: true`; si cap ho és o n'hi ha més d'una, es
       queda la primera trobada.
    3. lexic_acentuacio_mauricio.json -- patrons d'accentuació (còpia de
       `acentuacion_limpio.json`), 695 parelles.

DECISIÓ (30/09/2026): esta capa és sobretot diccionari de Mauricio --
s'han llevat les fonts Apertium-368, Paula Guerrero i els parells AVL-only
originals (`vos/vindre/valdre`, `tindre/obtindre/vore`, `últim/darrer`...),
junt amb totes les regles morfològiques/de sufix generalitzades
(`gentilicis.py`, `morfologia_verbal.py`, `perfet.py`, `locucions.py`,
`elisio.py`, encara retirades). `demostratius.py` es va recrear el mateix
dia (vore eixe mòdul), i `flexio_genere_avl.json` (vore baix) és la segona
peça no-Mauricio que torna, per la mateixa raó: un diccionari diferencial
mai llista totes les formes de gènere/nombre d'una paraula, només la que
algú va confirmar.

Gènere i nombre (`flexio_genere_avl.json`, afegit 30/09/2026): es va
provar ESCANEJAR tot `lexic_mauricio.json` buscant paraules acabades en
consonant "segura" (t/l/m/n/r) per a derivar automàticament fem/plural, i
la majoria eren GARBAGE -- la immensa majoria del lèxic són verbs
infinitius o adverbis sense gènere ("cercar"->"buscar" hauria donat
"cercara"->"buscara", sense sentit; "verdaderament" hauria donat
"verdaderamenta"). Per això esta NO és una regla automàtica sobre tot el
lèxic, és una llista CURADA a mà de parells base confirmats un a un
(sustantius de persona/animal amb variació real de gènere), amb dos
categories:
  - `regulars`: es deriva fem (+a), plural masculí (+s) i plural femení
    (+es sobre l'arrel) automàticament -- només per a paraules on este
    patró és segur als dos costats (p.ex. "xiquet"->"nen").
  - `irregulars`: formes exactes a mà, per a quan el patró regular NO val
    -- el cas més comú és "-ut" participial ("menut"->"menuda", com
    "vengut"->"venguda"), que mai es pot generalitzar amb seguretat
    perquè paraules com "petit" acaben igual (vocal+t) però SÍ són
    regulars ("petita", no "petida").

De pas, esta font resol la regressió que s'havia documentat ahí baix
sobre "xiquet" (abans guanyava "noi" per ambigüitat a Mauricio): ara
"xiquet"->"nen" ve explícitament confirmat en esta llista, amb prioritat
màxima.

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
FLEXIO_GENERE_PATH = _DATA / "flexio_genere_avl.json"

# Bug de dades conegut al fitxer font (vore docstring del mòdul): "després"
# no és una excepció dialectal, és un error de transcripció confirmat.
_BUG_DADES_CONEGUTS = {"després"}


def _deriva_genere_nombre(masc_val: str, masc_cat: str) -> dict[str, str]:
    """Deriva fem singular (+a), plural masculí (+s) i plural femení (+es
    sobre l'arrel, mai "+as") a partir d'un parell masculí singular. Només
    seria correcte per a paraules on el patró "+a" no xoca amb cap
    irregularitat -- per això `_carrega_flexio_genere` només l'invoca
    sobre la llista curada `regulars`, mai sobre tot el lèxic.

    >>> _deriva_genere_nombre("xiquet", "nen")
    {'xiqueta': 'nena', 'xiquets': 'nens', 'xiquetes': 'nenes'}
    """
    return {
        masc_val + "a": masc_cat + "a",
        masc_val + "s": masc_cat + "s",
        masc_val + "es": masc_cat + "es",
    }


def _carrega_flexio_genere(path: Path) -> dict[str, str]:
    dades = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for masc_val, masc_cat in dades["regulars"].items():
        if masc_val == "descripcio":
            continue
        lookup[masc_val] = masc_cat
        lookup.update(_deriva_genere_nombre(masc_val, masc_cat))
    for val, cat in dades["irregulars"].items():
        if val == "descripcio":
            continue
        lookup[val] = cat
    return lookup


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
    flexio_genere_path: Path = FLEXIO_GENERE_PATH,
) -> dict[str, str]:
    """Fusiona les 3 fonts documentades al mòdul, per orde de prioritat
    (la primera font que definix una paraula guanya sobre les següents).

    >>> lookup = carrega_lexic()
    >>> lookup["xiquet"]
    'nen'
    >>> lookup["xiqueta"], lookup["xiquets"], lookup["xiquetes"]
    ('nena', 'nens', 'nenes')
    >>> lookup["xicoteta"]
    'menuda'
    >>> lookup["firmant"]
    'signant'
    >>> lookup["acetilé"]
    'acetilè'
    >>> "després" in lookup
    False
    """
    lookup: dict[str, str] = {}
    for carregador, path in (
        (_carrega_flexio_genere, flexio_genere_path),
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
        flexio_genere_path: Path = FLEXIO_GENERE_PATH,
    ) -> None:
        self._lookup = carrega_lexic(mauricio_path, acentuacio_path, flexio_genere_path)

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
