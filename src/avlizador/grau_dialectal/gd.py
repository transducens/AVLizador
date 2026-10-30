#!/usr/bin/env python3
"""
gd.py -- Grau Dialectal (GD): quin percentatge de les
paraules dialectalment marcades d'un text son formes OCCIDENTALS
(valencianes) en compte d'ORIENTALS (catalanes).

    GD = total_paraules_occidentals / (total_occidentals + total_orientals)

Un GD d'1.0 vol dir "cap paraula catalana marcada en tot el text", 0.0
vol dir el contrari.

TEXT SENSE CAP PARAULA MARCADA (decisió de l'usuari, 26/10/2026): què
val el GD depén de la tasca, així que el tria el paràmetre `dialecte`:

  - sense `dialecte` (per defecte, `None`): el GD és `None` -- el text no
    diu res sobre el dialecte i no entra en cap mitjana. És la mesura
    neutra, la que no afavorix cap dels dos dialectes.
  - `dialecte="val"`: 1.0 -- el text s'avalua com a valencià i, com que
    no té res que el desmentisca, compta com a valencià pur.
  - `dialecte="cat"`: 0.0 -- el mateix, avaluat com a català.

Amb `"val"`/`"cat"` el resultat queda condicionat per la tasca (un text
sense marcadors afavorix el costat que s'avalua): servix per a
comprovar que un text o una traducció és pur en el dialecte esperat, no
per a comparar dialectes. 0.5 es va provar i es va descartar perquè es
confon amb un text mesclat a parts iguals. Amb qualsevol mode,
`total_marcades == 0` diu que el GD no ve de cap marcador.

ORIGEN (13/10/2026, vore `documentacio/hoja_de_ruta_gd_y_proxima_fase.md`):
`pipeline/01_extraccio_i_neteja/estudi_dialectal.py` ja calculava una mètrica molt
semblant (`ratio_occ`), pero contra dos llistes curades a mà d'una
vuitantena de paraules cadascuna (`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`
en eixe fitxer). Este mòdul fa el mateix càlcul pero contra l'índex de
parells dialectals que JA manté `traductor/` per a traduir de veres --
uns 53.000 parells (1.471 de lèxic general + ~52.000 formes verbals
conjugades + demostratius/possessius/numerals), no reinventant cap dada
nova. Avantages sobre l'enfocament antic:

  1. Molt mes vocabulari cobert (uns 500 cops mes paraules).
  2. Una sola font de veritat: si una paraula es dialectal segons el
     motor de traducció, també ho és segons el GD -- no hi ha dos
     llistes que es puguen desincronitzar.
  3. Funciona per a QUALSEVOL text (una frase solta, un fitxer, un
     corpus JSONL sencer), no només per als documents ja carregats a
     `dades/avl/final/unified.jsonl` com calia amb l'script antic.

LIMITACIÓ CONEGUDA, ACCEPTADA DE MOMENT: només compta paraules que
apareixen LITERALMENT a algun dels diccionaris de lookup exacte (lèxic,
conjugacions, demostratius, numerals, possessius). Els patrons
PRODUCTIUS de sufix del motor (p.ex. `-és`(occ)/`-ès`(or) a
`accentuacio.py`, o l'alternança incoativa d'`incoatius.py`) NO estan
inclosos encara -- cobrixen un patró obert (qualsevol paraula que
acabe aixina, no una llista tancada), i incorporar-los ací faria falta
el mateix tipus de regex que ya tenen eixos mòduls. Es deixa fora
expressament per no barrejar dos mecanismes distints en la primera
versió -- ampliar-ho és un pas pendent documentat, no un oblit.

AMBIGÜITAT: si una mateixa forma apareix com a VALENCIANA en un parell
i com a CATALANA en un atre (col·lisió entre entrades no relacionades,
p.ex. per homografia accidental), no es fiable com a marcador de cap
dels dos costats -- se'n descarta dels dos conjunts (preferix fals
negatiu, mateix criteri que la resta del projecte).

MARCADORS NO FIABLES PER REGISTRE (15/10/2026, vore `_MARCADORS_NO_FIABLES_REGISTRE`):
diferent de l'ambigüitat de dalt -- ací el parell és real i el traductor
el convertix bé (`translate("Açò no és correcte.")` -> "Això no és
correcte."), pero la seua presencia NO és fiable com a senyal de dialecte
en registre formal/institucional. Mesurat DIRECTAMENT sobre el BOE
complet (267.962 documents reals, mai sobre l'eixida del motor): "qué"
nomes apareix 1 volta per cada 17.584 "què" (0,0%) i "açò" nomes 65
voltes per cada 5.708 "això" (1,1%) al costat VALENCIÀ real -- el mateix
patró ja confirmat a menor escala amb el benchmark de 151 (7/9 "què").
S'exclouen dels DOS costats de l'índex del GD (ni compten com a
marcador occidental ni oriental), PERO NO es toca
`traductor/rules/val_cat/lexic.py::_BUG_DADES_CONEGUTS` -- eixe set
alimenta la TRADUCCIÓ de veres (`carrega_lexic()`), i ja es va mesurar
(15/10/2026) que excloure "qué" ahí trenca una traducció real (RC055).
Els dos mecanismes són independents a propòsit: el GD pot decidir que
una paraula no és un bon marcador sense que això canvie com es traduïx.

HOMÒGRAFS ENTRE CATEGORIES I FORMES AMBIGÜES (21/10/2026, sense cap
llista a mà -- només camps de les dades + spaCy). Des que es van retirar
les llistes d'exclusió del traductor (19/10/2026), alguns parells reals
es colaven com a marcadors falsos perquè la forma té un HOMÒGRAF comú
als dos dialectes. Cas tipus: E0977 empareja l'ADJECTIU català "desprès"
(que es desprèn del que té) amb l'adjectiu valencià "després" -- parell
correcte --, pero l'ADVERBI "després" (més tard) s'escriu igual i és
compartit; sense filtre, qualsevol text català amb "després" sumava
marcadors valencians.

Solució (vore `_carrega_homografs`): spaCy es consulta NOMÉS per als
homògrafs que el proveïdor ja declara -- entrades `problema:
"homonimia_lexica"`, que porten `forma_problematica` (la grafia
homògrafa), `lemas` (la categoria de cada lectura, p.ex. "manc [adj]",
"manca [n]") i `categoria` (la de la lectura dialectal). Si la lectura
dialectal té una categoria que cap altra lectura comparteix ("manca": n
vs. adj; "nou": n vs. adj/num), la forma compta com a marcador NOMÉS quan
spaCy li dona eixa categoria. Si la comparteix ("bes": be [n] / bes [n];
"blanca"), spaCy no pot decidir i la forma no compta mai. Totes les
altres paraules no passen per spaCy: spaCy (català central) no coneix
moltes formes valencianes ("hui", "faena", "seua") i n'inventa
l'etiqueta, fins i tot amb seguretat alta -- un filtre general per
categoria (provat i descartat 21/10/2026, amb i sense llindar de
seguretat) perdia marcadors bons.

Conseqüència: un homògraf només es filtra si les dades el declaren. Hui
"després" (E0977) i "tancat" no ho estan, i seguixen comptant com a
marcador fals -- es resol marcant-los `homonimia_lexica` a l'origen, no
amb una llista ací. Tampoc es resolen les paraules compartides per
registre ("estat", "avui", "últim").

Mateixa mesura feta sobre uns atres candidats del BOE que NO entren en
esta categoria, per contrast: "estat" i "recull" són col·lisions
d'homògraf (participi/verb vs. nom, mateix problema que ja cobrix el
mecanisme d'homògrafs de `rules/__init__.py::carrega_homografs`,
pero el lèxic encara no les marca com a `homonimia_lexica` -- pendent
de les dades, no d'este fitxer). "afecte"/"carinyo"
sembla un error de dades del lexicó (el mateix patró que "vesprada"/"tard"),
pendent de confirmar -- cap dels dos es toca ací.

ÚS des de la línia d'ordres (paquet `avlizador` instal·lat; abans,
`python gd.py` des de `pipeline/09_grau_dialectal/`):

    avlizador gd --text "Este xiquet vol vindre hui."
    avlizador gd --text "Aquest nen vol venir avui." --dialecte cat
    avlizador gd --fitxer un_document.txt
    avlizador gd --corpus ../../dades/avl/final/unified.jsonl --camp text

    # Informe HTML per a VORE i depurar frase a frase (paraules
    # ressaltades, verd=occidental/taronja=oriental), amb dos columnes
    # una al costat de l'altra quan el corpus en té (com el benchmark
    # del projecte, "occidental"/"oriental"; afegiu `--dialecte val
    # --dialecte-alt cat` per a comptar com a purs els textos sense
    # marcadors):
    avlizador gd --corpus ../03_seleccio_de_model/benchmark_corpus.json \
        --camp occidental --camp-alt oriental --html informe.html

ÚS com a mòdul:

    from avlizador.grau_dialectal import calcula_gd
    calcula_gd("Este xiquet vol vindre hui.")["gd"]  # -> 1.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator

from ..traductor_cat_val.rules import Token, carrega_homografs, marca_noms_propis, pos_tagger, separa_prefix_elidit, tokenize
from ..traductor_cat_val.rules.cat_val.demostratius import carrega_demostratius_invers
from ..traductor_cat_val.rules.cat_val.lexic import LEXIC_GENERAL_PATH, carrega_lexic_invers
from ..traductor_cat_val.rules.cat_val.numerals import carrega_numerals_invers
from ..traductor_cat_val.rules.cat_val.possessius import carrega_possessius_invers
from ..traductor_cat_val.rules.val_cat.conjugacions_dict import (
    DEFAULT_CONJUGACIONS_PATH,
    SEMPRE_VERB,
    es_risc_mode_3a_plural,
)
from ..traductor_cat_val.rules.val_cat.demostratius import carrega_demostratius
from ..traductor_cat_val.rules.val_cat.lexic import carrega_lexic
from ..traductor_cat_val.rules.val_cat.numerals import carrega_numerals
from ..traductor_cat_val.rules.val_cat.possessius import _carrega_possessius

# Nomes per a `WORD_RE` (vore `_processa_corpus`/`resalta_html`, que
# encara necessiten un regex simple de paraula per a construir l'HTML
# ressaltat caràcter a caràcter -- el recompte de debò ara tokenitza amb
# el motor de veres, vore `calcula_gd`).
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_CACHE: "Formes | None" = None

# Vore "MARCADORS NO FIABLES PER REGISTRE" al docstring del mòdul.
# S'exclouen els DOS costats de cada parell -- ni "qué" ni "què", ni
# "açò" ni "això" compten com a marcador, encara que el traductor seguïx
# convertint-los bé.
_MARCADORS_NO_FIABLES_REGISTRE = {"qué", "què", "açò", "això"}

# Homògrafs declarats pel proveïdor: el mecanisme viu des del 22/10/2026 a
# `traductor/rules/__init__.py::carrega_homografs`, compartit amb el
# traductor (abans era una còpia local d'este fitxer).
_carrega_homografs = carrega_homografs


class Formes:
    """Les formes dialectals carregades, separades en dos grups perquè
    cadascun necessita un criteri distint de confiança (vore
    `calcula_gd` i "BUG REAL" al docstring del mòdul):

    - `occ_simple`/`or_simple`: paraules de lèxic/demostratius/numerals/
      possessius -- lookup directe.
    - `occ_verbal`/`or_verbal`: formes que vénen de `conjugacions_dialectals.json`
      -- moltes són formes RARES d'un verb que per casualitat coincidixen
      amb una paraula comuna d'una altra categoria ("entre" preposició vs.
      "entre" = "jo entre" d'"entrar"; "pobles" nom comú vs. "pobles" =
      "que tu pobles" de "poblar"). Només es confien quan spaCy etiqueta
      el token com a VERB/AUX en eixe context -- exactament el mateix
      filtre que ja fa servir `ConjugacionsDictRule`/`ConjugacionsDictInversRule`
      per a traduir, reaprofitat ací.
    - `homografs`: `{forma: etiquetes spaCy de la lectura dialectal}`, els
      homògrafs resolubles declarats pel proveïdor (vore `_carrega_homografs`).
    """

    __slots__ = ("occ_simple", "or_simple", "occ_verbal", "or_verbal", "homografs")

    def __init__(self, occ_simple, or_simple, occ_verbal, or_verbal, homografs=None):
        self.occ_simple = occ_simple
        self.or_simple = or_simple
        self.occ_verbal = occ_verbal
        self.or_verbal = or_verbal
        self.homografs = homografs or {}


def _carrega_conjugacions_pures(path: Path = DEFAULT_CONJUGACIONS_PATH) -> dict[str, str]:
    """Llig `conjugacions_dialectals.json` DIRECTAMENT (no reutilitza
    `carrega_conjugacions()`/`carrega_conjugacions_invers()`) perquè
    cap de les dos aplica els filtres que fan falta ACÍ -- vore "BUG
    REAL" al docstring del mòdul. Torna `{valenciano: catalan}` només
    amb entrades:

    1. Sense `problematica: true` (ambigües indicatiu/subjuntiu per
       disseny, documentat al propi fitxer de dades).
    2. Sense risc de col·lisió de mode en 3a plural
       (`es_risc_mode_3a_plural`, el mateix càlcul que
       `rules/val_cat/conjugacions_dict.py` ja fa per a protegir la
       TRADUCCIÓ -- ací protegix l'ÍNDEX).
    3. Amb un ÚNIC candidat en les DOS direccions (ni el valencià ni el
       català de l'entrada apareixen en cap atra parella neta) --
       mes estricte que les dos funcions originals, que només exigixen
       unicitat EN LA DIRECCIÓ QUE TRADUÏXEN.

    >>> conj = _carrega_conjugacions_pures()
    >>> conj["oferisca"]
    'ofereixi'
    >>> "base" in conj
    False
    >>> "entre" in conj
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    candidats_val: dict[str, set[str]] = {}
    candidats_cat: dict[str, set[str]] = {}
    parells: list[tuple[str, str]] = []
    for entrada in dades.get("entradas", []):
        if entrada.get("problematica"):
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if not valenciano or not catalan or valenciano == catalan:
            continue
        if valenciano not in SEMPRE_VERB and es_risc_mode_3a_plural(valenciano, catalan):
            continue
        parells.append((valenciano, catalan))
        candidats_val.setdefault(valenciano, set()).add(catalan)
        candidats_cat.setdefault(catalan, set()).add(valenciano)

    return {
        valenciano: catalan
        for valenciano, catalan in parells
        if len(candidats_val[valenciano]) == 1 and len(candidats_cat[catalan]) == 1
    }


def carrega_formes_dialectals(forcar_recarrega: bool = False) -> Formes:
    """Fusiona tots els diccionaris diferencials que ja fa servir
    `traductor/` (les dos direccions per al lèxic/demostratius/numerals/
    possessius, mes `_carrega_conjugacions_pures()` per a les
    conjugacions -- vore eixa funció i "BUG REAL" al docstring del
    mòdul). Torna un `Formes` amb 4 conjunts disjunts de paraules en
    minúscules.

    Es guarda en cache de mòdul (`forcar_recarrega=True` per ignorar-la).

    >>> formes = carrega_formes_dialectals()
    >>> "xiquet" in formes.occ_simple
    True
    >>> "nen" in formes.or_simple
    True
    >>> "oferisca" in formes.occ_verbal
    True
    >>> "entre" in formes.occ_verbal or "entre" in formes.occ_simple
    False

    "qué"/"què" i "açò"/"això" són parells reals (el traductor els
    convertix bé) pero no fiables com a marcador en registre formal --
    vore "MARCADORS NO FIABLES PER REGISTRE" al docstring del mòdul:

    >>> "qué" in formes.occ_simple or "què" in formes.or_simple
    False
    >>> "açò" in formes.occ_simple or "això" in formes.or_simple
    False
    """
    global _CACHE
    if _CACHE is not None and not forcar_recarrega:
        return _CACHE

    occ: set[str] = set()
    orr: set[str] = set()

    def afig_val_a_cat(parells: dict[str, str]) -> None:
        for valenciano, catalan in parells.items():
            occ.add(valenciano.lower())
            orr.add(catalan.lower())

    def afig_cat_a_val(parells: dict[str, str]) -> None:
        for catalan, valenciano in parells.items():
            occ.add(valenciano.lower())
            orr.add(catalan.lower())

    afig_val_a_cat(carrega_lexic())
    afig_val_a_cat(carrega_demostratius())
    afig_val_a_cat(carrega_numerals())
    afig_val_a_cat(_carrega_possessius())

    afig_cat_a_val(carrega_lexic_invers())
    afig_cat_a_val(carrega_demostratius_invers())
    afig_cat_a_val(carrega_numerals_invers())
    afig_cat_a_val(carrega_possessius_invers())

    occ_verbal: set[str] = set()
    or_verbal: set[str] = set()
    for valenciano, catalan in _carrega_conjugacions_pures().items():
        occ_verbal.add(valenciano)
        or_verbal.add(catalan)

    # Col·lisions entre QUALSEVOL dels 4 conjunts (vore docstring del
    # mòdul, "AMBIGÜITAT") -- es descarten de tots a la vegada.
    tot_occ = occ | occ_verbal
    tot_or = orr | or_verbal
    ambigues = tot_occ & tot_or
    occ -= ambigues
    orr -= ambigues
    occ_verbal -= ambigues
    or_verbal -= ambigues

    occ -= _MARCADORS_NO_FIABLES_REGISTRE
    orr -= _MARCADORS_NO_FIABLES_REGISTRE

    # Homògrafs declarats pel proveïdor (vore `_carrega_homografs`): els
    # irresolubles no compten mai; els resolubles els decidix spaCy a
    # `_classifica_token`.
    homografs, irresolubles = _carrega_homografs()
    occ -= irresolubles
    orr -= irresolubles
    occ_verbal -= irresolubles
    or_verbal -= irresolubles

    _CACHE = Formes(
        frozenset(occ), frozenset(orr), frozenset(occ_verbal), frozenset(or_verbal), homografs
    )
    return _CACHE


def _tokenitza_amb_pos(text: str) -> list[Token]:
    """Tokenitza `text` amb el tokenitzador de veres del motor (no el
    `WORD_RE` simple) i, si spaCy esta instal·lat, omple `tok.pos` --
    necessari per a poder confiar en `Formes.occ_verbal`/`or_verbal`
    (vore "BUG REAL" al docstring del mòdul). Marca noms propis perquè
    tampoc compten com a marcador (una majúscula capturada per casualitat
    per una paraula dialectal no és senyal de res)."""
    tokens = tokenize(text)
    marca_noms_propis(tokens)
    pos_tagger.etiqueta(tokens)
    return tokens


def _paraula_per_lookup(surface: str) -> str | None:
    """Torna la paraula "neta" que cal buscar als diccionaris: la pròpia
    `surface` si ja és una paraula normal, o la part sense el prefix
    elidit si en porta un ("d'aquestes" -> "aquestes"). Torna `None` si
    `surface` no és ni l'una ni l'altra cosa (puntuació, espais...).

    BUG REAL trobat i corregit (13/10/2026, a petició de l'usuari --
    "aquestes" quasi mai es detectava com a marcador oriental): el
    tokenitzador de veres tracta l'apòstrof com a PART de la paraula
    (vore `rules/__init__.py`), així que "d'aquestes" arriba com UN SOL
    token -- mai casava amb l'entrada "aquestes" dels diccionaris. Un
    bon grapat de les aparicions reals d'"aquestes" al benchmark van
    precedides d'un prefix elidit ("d'aquestes festes", "d'aquestes
    tecnologies"...), així que el problema no era anecdòtic.

    >>> _paraula_per_lookup("aquestes")
    'aquestes'
    >>> _paraula_per_lookup("d'aquestes")
    'aquestes'
    >>> _paraula_per_lookup(",") is None
    True
    """
    if WORD_RE.fullmatch(surface) is not None:
        return surface
    prefix_resta = separa_prefix_elidit(surface)
    if prefix_resta is not None:
        return prefix_resta[1]
    return None


def _classifica_token(tok: Token, formes: Formes) -> str | None:
    """Torna `"occ"`, `"or"` o `None` per a `tok`, aplicant els dos
    filtres de seguretat trobats mesurant contra el benchmark real (vore
    `_paraula_per_lookup` per al prefix elidit, i baix per al filtre de
    POS dels marcadors verbals)."""
    if tok.surface.isspace() or tok.is_proper_noun:
        return None
    paraula = _paraula_per_lookup(tok.surface)
    if paraula is None:
        return None
    baix = paraula.lower()
    es_verb_segur = not tok.pos or tok.pos in ("VERB", "AUX")

    # Homògraf declarat pel proveïdor (vore "HOMÒGRAFS ENTRE CATEGORIES" al
    # docstring del mòdul): només compta si spaCy li dona la categoria de
    # la lectura dialectal ("manca" NOUN = carència; "manca" VERB/ADJ no).
    # Sense etiqueta d'spaCy, no compta (preferix fals negatiu).
    lectura_dialectal = formes.homografs.get(baix)
    if lectura_dialectal is not None and tok.pos not in lectura_dialectal:
        return None

    if baix in formes.occ_simple or (baix in formes.occ_verbal and es_verb_segur):
        return "occ"
    if baix in formes.or_simple or (baix in formes.or_verbal and es_verb_segur):
        return "or"
    return None


DIALECTES = ("val", "cat")


def _gd(total_occ: int, total_or: int, dialecte: str | None = None) -> float | None:
    """GD a partir dels comptes. Sense cap marcador: `None` si no es dona
    `dialecte`, 1.0 per a `"val"` i 0.0 per a `"cat"` (vore "TEXT SENSE
    CAP PARAULA MARCADA" al docstring del mòdul).

    >>> _gd(3, 1), _gd(3, 1, "cat")
    (0.75, 0.75)
    >>> _gd(0, 0) is None, _gd(0, 0, "val"), _gd(0, 0, "cat")
    (True, 1.0, 0.0)
    """
    if dialecte is not None and dialecte not in DIALECTES:
        raise ValueError(f"dialecte ha de ser None o un de {DIALECTES}, no {dialecte!r}")
    total = total_occ + total_or
    if not total:
        if dialecte is None:
            return None
        return 1.0 if dialecte == "val" else 0.0
    return round(total_occ / total, 4)


def calcula_gd(
    text: str, formes: Formes | None = None, dialecte: str | None = None
) -> dict:
    """Calcula el GD d'un text solt (una frase, un paràgraf, un
    document sencer). Si no es passa `formes`, carrega (o reutilitza)
    l'índex complet amb `carrega_formes_dialectals()`. `dialecte`
    (`None`, `"val"` o `"cat"`) només canvia el resultat quan no hi ha
    cap paraula marcada: `None`, 1.0 o 0.0 respectivament.

    DOS BUGS REALS trobats i corregits (13/10/2026, a petició de
    l'usuari revisant el seu propi benchmark -- vore
    `documentacio/hoja_de_ruta_gd_y_proxima_fase.md` per al detall
    complet i les xifres abans/després):

    1. **Filtre de POS per als marcadors verbals** (vore
       `_classifica_token`): la primera versió feia lookup directe de
       QUALSEVOL paraula contra les 53.000 formes, sense cap filtre de
       categoria gramatical. Provat contra el benchmark: 80 "marcadors
       occidentals" dins de frases 100% catalanes eren en realitat
       paraules COMUNES ("entre", "poden", "sobre", "base", "pobles"...)
       que només coincidixen per casualitat amb una forma verbal RARA i
       exclusiva d'un dialecte (p.ex. "entre" = preposició universal,
       pero també "jo entre" d'"entrar" en valencià) -- el mateix
       problema que `rules/val_cat/conjugacions_dict.py` ja documenta i
       resol per a TRADUIR (filtre POS amb spaCy), reaplicat ací.
    2. **Prefix elidit** (vore `_paraula_per_lookup`): "d'aquestes" és
       UN SOL token per al tokenitzador de veres, així que mai casava
       amb l'entrada "aquestes".

    "vindre" compta des de la integració de `conjugaciones_general.json`
    (19/10/2026), que porta els infinitius:

    >>> r = calcula_gd("Este xiquet vol vindre hui.")
    >>> r["total_occidentals"], r["total_orientals"], r["gd"]
    (4, 0, 1.0)
    >>> r["marcadors_occidentals"]
    ['este', 'xiquet', 'vindre', 'hui']

    >>> r = calcula_gd("El xiquet jugava amb el nen del veí.")
    >>> r["total_occidentals"], r["total_orientals"], r["gd"]
    (1, 1, 0.5)

    Sense cap paraula marcada: `None` per defecte; pur per al dialecte
    que s'avalua si es dona `dialecte` (1.0 en valencià, 0.0 en català):

    >>> r = calcula_gd("La casa és gran i té un jardí.")
    >>> r["total_marcades"], r["gd"]
    (0, None)
    >>> calcula_gd("La casa és gran i té un jardí.", dialecte="val")["gd"]
    1.0
    >>> calcula_gd("La casa és gran i té un jardí.", dialecte="cat")["gd"]
    0.0

    "entre" (preposició) ja NO es compta com a marcador verbal fals
    (bug 1 dalt):

    >>> r = calcula_gd("El llibre és entre els dos prestatges.")
    >>> r["total_marcades"]
    0

    "d'aquestes" ara SÍ es detecta com a marcador oriental (bug 2 dalt):

    >>> r = calcula_gd("En el decurs d'aquestes estades.")
    >>> r["marcadors_orientals"]
    ['aquestes']

    Homògrafs declarats (vore "HOMÒGRAFS ENTRE CATEGORIES" al docstring
    del mòdul): només compta la lectura dialectal. "nou" adjectiu no
    compta (spaCy tampoc reconeix mai el nom "nou" = nuez, l'etiqueta NUM,
    així que eixa lectura es perd: fals negatiu acceptat). "manca" nom
    (lectura dialectal, "carència") comptava fins al 29/10/2026; des que
    els `lemas` de l'entrada diuen "manc [adj, n]" (dada del proveïdor),
    la categoria nom la compartixen dos lectures i ja no compta mai
    (mateix cas que "calces" o "gandula"):

    >>> calcula_gd("Hem comprat un cotxe nou.")["total_marcades"]
    0
    >>> calcula_gd("Hi ha una manca de recursos.")["marcadors_orientals"]
    []
    """
    if formes is None:
        formes = carrega_formes_dialectals()

    tokens = _tokenitza_amb_pos(text)
    marcadors_occ: list[str] = []
    marcadors_or: list[str] = []
    total_paraules = 0
    for tok in tokens:
        if tok.surface.isspace():
            continue
        paraula = _paraula_per_lookup(tok.surface)
        if paraula is None:
            continue
        total_paraules += 1
        classe = _classifica_token(tok, formes)
        if classe == "occ":
            marcadors_occ.append(paraula.lower())
        elif classe == "or":
            marcadors_or.append(paraula.lower())

    total_occ = len(marcadors_occ)
    total_or = len(marcadors_or)
    total_marcades = total_occ + total_or

    return {
        "total_paraules": total_paraules,
        "total_occidentals": total_occ,
        "total_orientals": total_or,
        "total_marcades": total_marcades,
        "gd": _gd(total_occ, total_or, dialecte),
        "marcadors_occidentals": marcadors_occ,
        "marcadors_orientals": marcadors_or,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _llig_jsonl(path: Path) -> Iterator[dict]:
    """Llig `path` com a corpus de documents -- accepta DOS formats sense
    que calga dir quin és: JSONL (un objecte per linia, com
    `dades/avl/final/unified.jsonl`) o un JSON normal amb un array
    d'objectes (com `pipeline/03_seleccio_de_model/benchmark_corpus.json`)."""
    contingut = path.read_text(encoding="utf-8").strip()
    if contingut.startswith("["):
        dades = json.loads(contingut)
        for doc in dades:
            yield doc
        return
    for lineno, raw in enumerate(contingut.splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            yield json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"AVÍS: línia {lineno} de {path} il·legible ({exc})", file=sys.stderr)


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def resalta_html(text: str, formes: Formes | None = None) -> str:
    """Torna `text` com a HTML amb cada paraula marcada envoltada en un
    `<span>` (classe `mk-occ` les occidentals, `mk-or` les orientals) --
    pensat per a `--html` (vore baix), per a poder VORE d'un colp d'ull
    quines paraules concretes fan pujar o baixar el GD d'una frase, en
    compte de només el número final. Fa EXACTAMENT la mateixa
    classificació que `calcula_gd` (mateix filtre de POS per als
    marcadors verbals -- vore "BUG REAL" al docstring del mòdul), perquè
    el ressaltat visual i el número calculat mai es contradiguen.

    >>> formes = Formes(frozenset({"xiquet", "hui"}), frozenset({"nen"}), frozenset(), frozenset())
    >>> resalta_html("El xiquet i el nen juguen hui.", formes)
    'El <span class="mk-occ">xiquet</span> i el <span class="mk-or">nen</span> juguen <span class="mk-occ">hui</span>.'
    """
    if formes is None:
        formes = carrega_formes_dialectals()

    tokens = _tokenitza_amb_pos(text)
    out: list[str] = []
    pos = 0
    for tok in tokens:
        out.append(_esc(text[pos : tok.start]))
        paraula = tok.surface
        pos = tok.start + len(paraula)

        classe = _classifica_token(tok, formes)
        if classe == "occ":
            out.append(f'<span class="mk-occ">{_esc(paraula)}</span>')
        elif classe == "or":
            out.append(f'<span class="mk-or">{_esc(paraula)}</span>')
        else:
            out.append(_esc(paraula))
    out.append(_esc(text[pos:]))
    return "".join(out)


def _text_gd(gd: float | None, total_marcades: int) -> str:
    """GD per a la consola, amb una nota si no ve de cap marcador."""
    if gd is None:
        return "-- (cap paraula marcada)"
    text = f"{gd:.4f}"
    if not total_marcades:
        text += " (cap paraula marcada: pur per al dialecte avaluat)"
    return text


def _mostra_text(etiqueta: str, resultat: dict, mostra: int) -> None:
    gd_text = _text_gd(resultat["gd"], resultat["total_marcades"])
    print(f"{etiqueta}")
    print(f"  GD: {gd_text}")
    print(
        f"  occidentals={resultat['total_occidentals']}  "
        f"orientals={resultat['total_orientals']}  "
        f"paraules totals={resultat['total_paraules']}"
    )
    if mostra > 0:
        if resultat["marcadors_occidentals"]:
            print(f"  marcadors occidentals: {resultat['marcadors_occidentals'][:mostra]}")
        if resultat["marcadors_orientals"]:
            print(f"  marcadors orientals:   {resultat['marcadors_orientals'][:mostra]}")


def _resum_camp(
    path: Path, camp: str, formes, limit: int | None = None,
    dialecte: str | None = None,
) -> tuple[list[dict], int, int]:
    """Calcula el GD de `camp` a cada linia de `path` (com a molt `limit`
    documents, si es dona -- util per a corpus grans com el del BOE,
    ~268.000 linies, on cada frase es tokenitza amb spaCy i provar amb
    tot no es practic la primera vegada). Torna `(resultats_per_doc,
    total_occidentals, total_orientals)`."""
    resultats = []
    total_occ = total_or = 0
    for i, doc in enumerate(_llig_jsonl(path)):
        if limit is not None and i >= limit:
            break
        text = doc.get(camp) or ""
        r = calcula_gd(text, formes, dialecte)
        total_occ += r["total_occidentals"]
        total_or += r["total_orientals"]
        resultats.append({"id": doc.get("id") or doc.get("corpus_id"), "text": text, **r})
    return resultats, total_occ, total_or


def _gd_color(gd: float | None, sense_marcadors: bool = False) -> str:
    if gd is None or sense_marcadors:
        return "#9a9ba5"
    if gd >= 0.8:
        return "#1a9850"
    if gd >= 0.5:
        return "#d6a300"
    return "#d1372f"


def _html_gd(gd: float | None) -> str:
    return "—" if gd is None else str(gd)


def genera_informe_html(
    path: Path, camp: str, camp_alt: str | None, formes,
    res_a: list[dict], gd_a: float | None,
    res_b: list[dict] | None, gd_b: float | None,
    sortida: Path,
) -> None:
    """Genera un informe HTML autònom (sense dependencies externes) amb
    una fila per document: el text ressaltat paraula a paraula (verd =
    marcador occidental, taronja = marcador oriental) i el GD de cada
    columna -- pensat per a VORE i depurar per què un benchmark puntua
    com puntua, no només llegir el número agregat. Si `camp_alt` es
    dona (p.ex. "occidental"/"oriental" del benchmark del projecte),
    mostra les dos columnes una al costat de l'altra per al mateix
    document.

    Rep els resultats ja calculats (`res_a`/`res_b`, vore `_resum_camp`)
    en compte de recalcular-los -- `_processa_corpus` els reutilitza
    també per a `--sortida`, així que no es tokenitza dos vegades el
    mateix corpus (14/10/2026).
    """
    files_html = []
    for i, ra in enumerate(res_a):
        rb = res_b[i] if res_b is not None else None
        id_doc = _esc(str(ra["id"] if ra["id"] is not None else i))
        cela_a = (
            f'<td class="txt">{resalta_html(ra["text"], formes)}</td>'
            f'<td class="score" style="color:{_gd_color(ra["gd"], not ra["total_marcades"])}">'
            f'{_html_gd(ra["gd"])}</td>'
        )
        cela_b = ""
        if rb is not None:
            cela_b = (
                f'<td class="txt">{resalta_html(rb["text"], formes)}</td>'
                f'<td class="score" style="color:{_gd_color(rb["gd"], not rb["total_marcades"])}">'
                f'{_html_gd(rb["gd"])}</td>'
            )
        cerca = _esc((ra["text"] + " " + (rb["text"] if rb else "")).lower())
        files_html.append(
            f'<tr data-cerca="{cerca}"><td class="mono">{id_doc}</td>{cela_a}{cela_b}</tr>'
        )

    capcalera_b = (
        f'<th>{_esc(camp_alt)}</th><th>GD</th>' if camp_alt is not None else ""
    )
    resum_b = (
        f'<div class="card"><div class="label">GD global "{_esc(camp_alt)}"</div>'
        f'<div class="value" style="color:{_gd_color(gd_b)}">{_html_gd(gd_b)}</div></div>'
        if camp_alt is not None else ""
    )

    html = f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informe GD -- {_esc(path.name)}</title>
<style>
  :root {{
    --bg:#f7f7f8; --panel:#fff; --border:#e2e2e6; --text:#1c1c1f; --text-dim:#6b6b74;
    --mk-occ-bg:#d7f3d9; --mk-occ-text:#16652b; --mk-or-bg:#ffe2c7; --mk-or-text:#9c4b0a;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#17181c; --panel:#202128; --border:#33343c; --text:#eceef2; --text-dim:#9a9ba5;
      --mk-occ-bg:#163a22; --mk-occ-text:#7fe39a; --mk-or-bg:#4a2f16; --mk-or-text:#f0a35e;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,"Segoe UI",Arial,sans-serif; padding:22px 26px 50px; }}
  h1 {{ font-size:1.3rem; margin:0 0 4px; }}
  .subt {{ color:var(--text-dim); font-size:.85rem; margin:0 0 16px; }}
  .cards {{ display:flex; gap:14px; margin-bottom:16px; flex-wrap:wrap; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:10px 16px; }}
  .card .label {{ color:var(--text-dim); font-size:.72rem; text-transform:uppercase; letter-spacing:.03em; }}
  .card .value {{ font-size:1.4rem; font-weight:700; }}
  .legend {{ font-size:.82rem; color:var(--text-dim); margin-bottom:14px; }}
  .legend span {{ padding:1px 7px; border-radius:5px; margin-right:4px; }}
  input#cerca {{ width:100%; max-width:420px; padding:7px 11px; border-radius:8px; border:1px solid var(--border); background:var(--panel); color:var(--text); margin-bottom:12px; }}
  table {{ border-collapse:collapse; width:100%; font-size:.86rem; background:var(--panel); }}
  th,td {{ padding:6px 10px; text-align:left; border-bottom:1px solid var(--border); vertical-align:top; }}
  th {{ color:var(--text-dim); font-weight:600; position:sticky; top:0; background:var(--panel); cursor:pointer; }}
  td.score {{ font-variant-numeric:tabular-nums; font-weight:700; white-space:nowrap; }}
  td.mono {{ font-family:ui-monospace,Consolas,monospace; white-space:nowrap; }}
  td.txt {{ line-height:1.5; }}
  .mk-occ {{ background:var(--mk-occ-bg); color:var(--mk-occ-text); padding:0 2px; border-radius:3px; }}
  .mk-or {{ background:var(--mk-or-bg); color:var(--mk-or-text); padding:0 2px; border-radius:3px; }}
</style>
</head>
<body>
  <h1>Informe GD -- {_esc(path.name)}</h1>
  <p class="subt">{len(res_a)} documents. Verd = marcador occidental (valencià), taronja = marcador oriental (català).</p>
  <div class="cards">
    <div class="card"><div class="label">GD global "{_esc(camp)}"</div>
      <div class="value" style="color:{_gd_color(gd_a)}">{_html_gd(gd_a)}</div></div>
    {resum_b}
  </div>
  <div class="legend"><span class="mk-occ">occidental</span><span class="mk-or">oriental</span></div>
  <input id="cerca" type="search" placeholder="Cerca per id o text...">
  <div style="overflow-x:auto">
  <table id="taula">
    <thead><tr><th>ID</th><th>{_esc(camp)}</th><th>GD</th>{capcalera_b}</tr></thead>
    <tbody>{"".join(files_html)}</tbody>
  </table>
  </div>
<script>
document.getElementById('cerca').addEventListener('input', function (e) {{
  var q = e.target.value.toLowerCase();
  document.querySelectorAll('#taula tbody tr').forEach(function (tr) {{
    tr.style.display = tr.getAttribute('data-cerca').indexOf(q) !== -1 ? '' : 'none';
  }});
}});
</script>
</body>
</html>
"""
    sortida.write_text(html, encoding="utf-8")


def _processa_corpus(
    path: Path, camp: str, camp_alt: str | None, mostra: int,
    sortida_json: Path | None, sortida_html: Path | None, limit: int | None,
    dialecte: str | None = None, dialecte_alt: str | None = None,
) -> None:
    formes = carrega_formes_dialectals()
    res_a, occ_a, or_a = _resum_camp(path, camp, formes, limit, dialecte)
    gd_a = _gd(occ_a, or_a, dialecte)

    res_b = gd_b = None
    if camp_alt is not None:
        res_b, occ_b, or_b = _resum_camp(path, camp_alt, formes, limit, dialecte_alt)
        gd_b = _gd(occ_b, or_b, dialecte_alt)

    limit_text = f", limit a {limit}" if limit is not None else ""
    com_a = f" com a '{dialecte}'" if dialecte is not None else ""
    print(f"Corpus: {path}  ({len(res_a)} documents, camp '{camp}'{com_a}{limit_text})")
    print(f"  GD global: {_text_gd(gd_a, occ_a + or_a)}")
    print(f"  occidentals={occ_a}  orientals={or_a}")

    if sortida_json is not None:
        # Si hi ha camp_alt (p.ex. "occidental"/"oriental" del benchmark),
        # el document inclou també les claus "_alt" amb el mateix detall
        # per a eixa segona columna -- així un sol JSON basta per a
        # reconstruir la comparativa de dos columnes sense tornar a
        # executar res (vore visor_gd.html, pensat per a llegir este
        # format, 14/10/2026).
        documents = []
        for i, ra in enumerate(res_a):
            doc = dict(ra)
            if res_b is not None:
                rb = res_b[i]
                doc["text_alt"] = rb["text"]
                doc["gd_alt"] = rb["gd"]
                doc["total_occidentals_alt"] = rb["total_occidentals"]
                doc["total_orientals_alt"] = rb["total_orientals"]
                doc["marcadors_occidentals_alt"] = rb["marcadors_occidentals"]
                doc["marcadors_orientals_alt"] = rb["marcadors_orientals"]
            documents.append(doc)
        sortida_json.write_text(
            json.dumps(
                {
                    "camp": camp, "camp_alt": camp_alt,
                    "dialecte": dialecte,
                    "dialecte_alt": dialecte_alt if camp_alt is not None else None,
                    "gd_global": gd_a, "total_occidentals": occ_a, "total_orientals": or_a,
                    "gd_global_alt": gd_b,
                    "documents": documents,
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  Guardat detall per document a {sortida_json}")

    if sortida_html is not None:
        genera_informe_html(path, camp, camp_alt, formes, res_a, gd_a, res_b, gd_b, sortida_html)
        extra = f" / '{camp_alt}'={gd_b}" if camp_alt is not None else ""
        print(f"  Informe HTML guardat a {sortida_html} (GD '{camp}'={gd_a}{extra})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="avlizador gd",
        description="Calcula el Grau Dialectal (GD) d'un text, fitxer o corpus JSONL."
    )
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--text", help="Frase o text solt a analitzar.")
    grup.add_argument("--fitxer", type=Path, help="Fitxer de text pla a analitzar sencer.")
    grup.add_argument("--corpus", type=Path, help="Fitxer JSONL amb un document per linia.")
    parser.add_argument(
        "--camp", default="text",
        help="Camp de text dins de cada linia del --corpus (per defecte: 'text').",
    )
    parser.add_argument(
        "--camp-alt", default=None,
        help="Amb --corpus: segon camp a comparar al costat del primer "
             "(p.ex. --camp occidental --camp-alt oriental per al benchmark del projecte).",
    )
    parser.add_argument(
        "--dialecte", choices=DIALECTES, default=None,
        help="Dialecte amb què s'avalua el text (--text, --fitxer o --camp). "
             "Només importa si no hi ha cap paraula marcada: sense l'opció "
             "el GD és buit (None); amb 'val' és 1.0 i amb 'cat' 0.0 (text pur).",
    )
    parser.add_argument(
        "--dialecte-alt", choices=DIALECTES, default=None,
        help="Igual que --dialecte, per a --camp-alt.",
    )
    parser.add_argument(
        "--mostra", type=int, default=10,
        help="Quants marcadors trobats mostrar de cada dialecte (nomes per a --text/--fitxer).",
    )
    parser.add_argument(
        "--sortida", type=Path, default=None,
        help="Amb --corpus: fitxer JSON on guardar el detall per document.",
    )
    parser.add_argument(
        "--html", type=Path, default=None,
        help="Amb --corpus: genera un informe HTML (frase a frase, paraules "
             "ressaltades) per a vore i depurar visualment per que puntua aixina.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Amb --corpus: analitza nomes les primeres N files -- util per a "
             "corpus grans (p.ex. el del BOE, ~268.000 linies) abans de llançar-ho sencer.",
    )
    args = parser.parse_args(argv)

    if args.text is not None:
        _mostra_text(
            "(text solt)", calcula_gd(args.text, dialecte=args.dialecte), args.mostra
        )
    elif args.fitxer is not None:
        text = args.fitxer.read_text(encoding="utf-8")
        _mostra_text(
            str(args.fitxer), calcula_gd(text, dialecte=args.dialecte), args.mostra
        )
    else:
        _processa_corpus(
            args.corpus, args.camp, args.camp_alt, args.mostra,
            args.sortida, args.html, args.limit, args.dialecte, args.dialecte_alt,
        )


if __name__ == "__main__":
    main()
