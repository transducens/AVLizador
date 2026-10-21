"""
lexic.py -- Capa 1 del pipeline: substitució directa per lèxic diferencial.
Fusiona 3 fonts, per orde de prioritat quan es contradiuen (la primera que
definix una paraula guanya):

    0. TEMPORAL_hui_avui_pendent_fusio.json -- PEGAT TEMPORAL, no una font
       permanent (vore docstring de `_carrega_temporal`). Si el fitxer no
       existix (ja fusionat i esborrat), esta font simplement no aporta
       res -- no cal llevar la crida a mà.
    1. flexio_genere_avl.json         -- derivació de gènere/nombre per a
       un grapat de paraules CURADES A MÀ (no cap fitxer del proveïdor),
       vore docstring de `_carrega_flexio_genere`.
    2. lexic_general.json             -- lèxic general (còpia de
       `lexico_general.json` des de 16/10/2026, abans `unificado.json`),
       filtrat: descarta entrades "_PENDENT" (sense verificar), topònims
       (`tipo: "v:top_gva"`, el motor mai els aplicaria -- protegix noms
       propis), categories que no pertanyen a esta capa ("num"/"det",
       vore `_CATEGORIES_LEXIC_GENERAL`), entrades on valencià==català
       (sense diferència real), valencians de més d'una paraula (esta
       capa fa lookup d'un sol token), el bug de dades conegut de
       "després" (vore baix), i qualsevol forma que ja cobrixca
       `demostratius.py` amb autoritat pròpia (bug real trobat
       05/10/2026: la font portava `eixa->aqueixa`, tècnicament vàlid
       pero que ignorava la decisió ja presa de col·lapsar
       este/eixe/aqueix cap a "aquest" -- vore
       `_formes_demostratius_conegudes`). Quan una mateixa paraula té més
       d'una traducció possible, prioritza la marcada `canonica: true`;
       si cap ho és o n'hi ha més d'una, es queda la primera trobada.

**Capa d'accentuació RETIRADA (16/10/2026)**: `lexic_acentuacio_general.json`
(695 parelles, còpia de `acentuacion_limpio.json`) ja no es carrega a
banda -- mesurat que 681 de les 682 parelles reals (després de filtres)
ja ixen be NOMÉS amb la categoria "adj" de `lexico_general.json` (p.ex.
"francés"->"francès" ara ve del lèxic general, no d'un fitxer a banda).
L'única perduda ("tèlexs"->"tèlexs") no és ni una alternança dialectal
real. A més, el patró productiu de sufix "-és"->"-ès" ja el cobrix
`accentuacio.py` de forma general (qualsevol paraula, no nomes les
enumerades), independentment d'este fitxer -- vore eixe mòdul.

DECISIÓ (30/09/2026): esta capa és sobretot diccionari del proveïdor
oficial -- s'han llevat les fonts Apertium-368, Paula Guerrero i els
parells AVL-only originals (`vos/vindre/valdre`, `tindre/obtindre/vore`,
`últim/darrer`...), junt amb totes les regles morfològiques/de sufix
generalitzades (`gentilicis.py`, `morfologia_verbal.py`, `perfet.py`,
`locucions.py`, `elisio.py`, encara retirades). `demostratius.py` es va
recrear el mateix dia (vore eixe mòdul), i `flexio_genere_avl.json` (vore
baix) és la segona peça que no ve del proveïdor que torna, per la mateixa
raó: un diccionari diferencial mai llista totes les formes de gènere/
nombre d'una paraula, només la que algú va confirmar.

Gènere i nombre (`flexio_genere_avl.json`, afegit 30/09/2026): es va
provar ESCANEJAR tot `lexic_general.json` buscant paraules acabades en
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
sobre "xiquet" (abans guanyava "noi" per ambigüitat al lèxic del
proveïdor): ara
"xiquet"->"nen" ve explícitament confirmat en esta llista, amb prioritat
màxima.

Excepció mantinguda (bug de dades, no regla dialectal): "després" ve
llistat a `acentuacion_limpio.json` com si seguira el patró d'accentuació
general ("després" -> "desprès"), però és un error del fitxer font --
"després" mai canvia en cap dels dos dialectes (confirmat empíricament,
afectava 10 de les 150 frases del benchmark). Es descarta ací a mà, no
perquè siga una "regla" sinó perquè és l'única manera de no repetir un
error de transcripció ja conegut al fitxer font. Des de 05/10/2026
`_BUG_DADES_CONEGUTS` s'aplica als DOS loaders (lèxic general i
accentuació), perquè "unificado.json" va reintroduir el mateix parell
erroni pel costat del lèxic general -- un bug de dades el pot reintroduir
qualsevol font nova, així que l'exclusió ha de ser global, no lligada a
un sol fitxer.

Dos bugs de dades més (15/10/2026, trobats validant l'IPD contra textos
reals de l'usuari, vore `cat_val/lexic.py` per als mateixos bugs mirats
des de l'altre costat): "vesprada" (el nom, "afternoon") ve llistat a
`unificado.json` amb `catalan: "tard"`, confonent el nom amb l'adverbi
"tard" (late) -- `translate("La vesprada va ser bonica.")` donava
"La tard va ser bonica." abans d'exclòure-ho. "ensenyança" ve amb
`catalan: "ensenyament"`, un sinònim real pero de gènere DIFERENT
(fem->masc) que `LexicRule` no sap arreglar sol -- `translate("L'ensenyança
pública és important.")` donava "L'ensenyament pública és important.",
sense concordar l'adjectiu. Cap benchmark (151 ni gplsi, 1.958 frases) conté
cap de les dos paraules, així que no hi ha cap xifra que puga confirmar-ho
ni refutar-ho -- l'evidència és la traducció directa, no el benchmark. Com
"qué" sí apareix al benchmark de 151 i EXCLOURE'L hi causa una regressió
real (RC055: `translate("Qué fas?")` ja dona bé "Què fas?" hui), "qué" NO
s'afig a `_BUG_DADES_CONEGUTS` encara que sí estiga exclòs al costat
cat->val (`_BUG_DADES_CONEGUTS_CAT`) -- els dos costats filtren camps
distints de la mateixa taula (`valenciano` ací, `catalan` allà) per motius
distints, no són el mateix set mirat del revés. **Confirmat per normativa
(19/10/2026)**: no és nomes que el benchmark preferisca "què" -- el GNV
(`docs_gramatica/gnv_complet.txt`, §5.1.2.1) fa una excepció EXPLÍCITA per
a esta paraula exacta ("què" i "perquè" porten accent greu en valencià
normatiu "a fi d'evitar una excessiva discrepància entre les diferents
varietats de la llengua", encara que es pronuncien amb e tancada) --
convertir "qué"->"què" ací no és un parell dialectal, és corregir una
grafia no normativa cap a l'única grafia correcta als dos dialectes. Vore
el mateix comentari, mes extens, a `cat_val/lexic.py::_BUG_DADES_CONEGUTS_CAT`.

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

Filtre POS per a homonimia_lexica (19/10/2026): la guia oficial del
proveïdor (`diccionarios/Funcionamiento listas de palabras.pdf`)
confirma el mecanisme de les 24 entrades `problema: "homonimia_lexica"`
de `lexico_general.json`: quan els `lemas` tenen categories gramaticals
DIFERENTS, es resol amb PoS (spaCy); quan són iguals/solapades, fa falta
un LLM. `LexicRule` ara reutilitza `categoria_gramatical_lexic.json`/
`pos_compatible()` (el mateix mecanisme ja actiu a `cat_val/lexic.py`
des del 13/10/2026 per a "nou"/"anou") per a les entrades on l'ambigüitat
cau de este costat (`lado: "cat"`) -- de moment "tancada"/"tancades"
("vallado" NOUN vs "tancat/tancada" ADJ, RC144), substituint l'exclusió
en bloc anterior. Nota: el camp `categoria` de l'entrada diu "adj" per a
estes dos files, pero és un error de dades (`espanol: "vallado"` és nom)
-- s'ha fet servir el sentit real dels `lemas`, no una confiança cega en
eixe camp. Verificat amb spaCy real: detecta bé el cas ADJ sempre, i el
cas NOUN en frases amb prou context ("La tancada del corral..."), encara
que en frases curtes de vegades també etiqueta ADJ -- pitjor cas, mateix
fals negatiu que ja hi havia abans amb l'exclusió en bloc, mai un fals
positiu nou.

Concordança de gènere tras substitució lèxica (afegit 08/10/2026, RC044):
una substitució d'esta capa pot canviar el GÈNERE gramatical de la paraula
sencera, no només la seua forma ("dacsa", femení, -> "blat de moro",
masculí) -- `canvi_genere_lexic_avl.json` llista a mà els pocs casos
coneguts (cap font del proveïdor documenta gènere). Quan n'hi ha un, es
corregix NOMÉS el determinant IMMEDIATAMENT anterior (un token arrere,
saltant espais) amb una taula tancada la/el, una/un, esta/este... --
s'accepta com a límit conegut que un adjectiu posposat o un determinant
més llunyà no es corregisca (preferix fals negatiu, mateixa filosofia que
la resta del projecte). Com `LexicRule` és la PRIMERA capa del pipeline,
el determinant encara no l'ha tocat cap regla (demostratius.py va després),
així que es compara contra la seua forma VALENCIANA original, no la
catalana. El mecanisme (`corregeix_determinant_abans`, la taula
`DET_FEM_A_MASC`/`DET_MASC_A_FEM`) viu a `rules/__init__.py` des del
08/10/2026 -- es comparteix amb la direcció inversa (català->valencià,
vore `traductor/rules/cat_val/`), que necessita exactament el mateix
mecanisme en sentit contrari.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import (
    CATEGORIA_GRAMATICAL_PATH,
    Token,
    aplica_amb_prefix_elidit,
    carrega_categoria_gramatical,
    corregeix_determinant_abans,
    pos_compatible,
    preserva_majuscula,
    separa_prefix_elidit,
)

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
LEXIC_GENERAL_PATH = _DATA / "lexic_general.json"
FLEXIO_GENERE_PATH = _DATA / "flexio_genere_avl.json"
TEMPORAL_PATH = _DATA / "TEMPORAL_hui_avui_pendent_fusio.json"
CANVI_GENERE_PATH = _DATA / "canvi_genere_lexic_avl.json"

# Bug de dades conegut al fitxer font (vore docstring del mòdul): "després"
# no és una excepció dialectal, és un error de transcripció confirmat.
# S'exclou dels DOS loaders (abans només de l'accentuació) des que
# "unificado.json" (05/10/2026) va reintroduir el mateix parell per una
# via distinta -- vore conversa 05/10/2026.
#
# "vesprada" i "ensenyança" (15/10/2026, vore docstring del mòdul): dos bugs
# de dades més trobats validant l'IPD, confirmats per traducció directa
# (cap benchmark conté cap de les dos paraules). "qué" es queda FORA
# d'esta llista a propòsit -- ahí sí hi ha evidència de benchmark (RC055)
# que excloure'l és una regressió real en este sentit, encara que estiga
# exclòs al costat cat->val per un motiu distint (vore
# `cat_val/lexic.py::_BUG_DADES_CONEGUTS_CAT`).
#
# "vesprada" ELIMINAT d'esta llista (16/10/2026): la nova font
# (`lexico_general.json`, vore hoja_de_ruta_migracio_diccionarios_v1.md)
# ja porta "vesprada"->"tarda" (abans "tard", l'error) -- confirmat
# directament al fitxer sincronitzat, ja no fa falta excloure'l.
# "ensenyança" es queda, el bug persistix a la font nova.
#
# "alcalde" i "tancada" afegits 16/10/2026 (regressions reals RC136/RC144
# trobades migrant a `lexico_general.json`, vore hoja_de_ruta_migracio_diccionarios_v1.md):
# - "alcalde"->"batlle" (`canonica: true`, `problema: "colision"`): mateix
#   patró que "ensenyança"/"qué" -- parell dialectal real pero este
#   registre formal/institucional prefereix la paraula compartida.
# - "tancada"->"closa" (`problema: "homonimia_lexica"`, `lemas: ["tancada
#   [n]", "tancat [adj]"]`): homògraf nom/adjectiu -- l'entrada és nomes
#   per al sentit NOM ("vallado"), pero s'aplicava també a l'adjectiu
#   (RC144, "e tancada" = "e closed", un terme lingüístic).
#   **RESOLT 19/10/2026, deixa de ser exclusió en bloc**: amb la guia
#   oficial del proveïdor (`diccionarios/Funcionamiento listas de
#   palabras.pdf`) confirmant que `homonimia_lexica` amb categories
#   gramaticals DIFERENTS als `lemas` es resol per PoS, es passa a
#   `categoria_gramatical_lexic.json` (`"tancada"/"tancades": "NOUN"`) +
#   el filtre `pos_compatible()` nou d'esta mateixa regla (vore baix) --
#   ara només es bloqueja quan spaCy etiqueta el token ADJ, en compte de
#   sempre. Nota: el camp `categoria` de l'entrada diu "adj" (sembla un
#   error de dades, l'`espanol` és "vallado", nom), s'ha fet servir el
#   sentit real (`lemas`) en compte del camp, no una confiança cega.
#   De les 24 entrades `homonimia_lexica` en total, esta i "falaguera"/
#   "brollador"/"carència"/"llavadora"/"exitosa"... ja tenen categories
#   gramaticals DIFERENTS als `lemas` (POS-resolubles); "bes", "bragues",
#   "hamaca" i "blanca" tenen categories IGUALS o solapades als dos
#   lemas -- eixes SÍ necessiten un LLM (vore guia), es queden pendents.
#
# RETIRAT 19/10/2026 a petició explícita de l'usuari (vore CLAUDE.md,
# "Pendent per a la propera sessió" -- no vol llistes d'exclusió a mà,
# vol que el dato font es corregisca ell mateix amb el seu permís).
# Regressions conegudes i acceptades mentre no s'arreglen en origen:
# "després" tornarà a eixir "desprès" (error de transcripció al fitxer
# font, mai canvia de veres entre dialectes); "ensenyança" tornarà a
# perdre la concordança de gènere amb "ensenyament"; "alcalde" (`canonica:
# true` cap a "batlle") tornarà a convertir-se encara que este registre
# formal/institucional preferisca la paraula compartida (mateix patró que
# "qué"/RC055). Abans: `_BUG_DADES_CONEGUTS = {"després", "ensenyança", "alcalde"}`.

# Paraules perdudes de veres migrant a `lexico_general.json` (16/10/2026,
# vore hoja_de_ruta_migracio_diccionarios_v1.md §4ter): la font nova no
# les porta per cap categoria ni com a verb d'arrel distinta -- es
# restauren a mà des de la font vella (`unificado.json`) per no perdre
# cobertura real mentre no arriben en una entrega futura. "llavar" i
# "espentar" confirmats amb regressió real de benchmark (RC002/RC022/RC025);
# la resta no tenien cap cas al benchmark pero es restauren igual per
# coherència (podrien aparéixer en gplsi/BOE).
_LEXIC_PERDUT_RESTAURAT = {
    "llavar": "rentar",
    "espentar": "empentar",
    "encollir": "encongir",
    "enllandar": "enllaunar",
    "bollir": "bullir",
    "solejar": "assolellar",
    "amprar": "manllevar",
    "subdesenrotllar": "subdesenvolupar",
    "invadir": "envair",
    "i+d": "R+D",
    "i+d+i": "R+D+I",
}

# Ordinals masculins singulars en "-è" (16/10/2026, vore docstring de
# `numerals.py`): únic patró real que falta a `lexico_general.json`
# (categoria "adj") respecte a `numerals_general.json` -- mesurat
# exhaustivament (153/176 ja coincidixen, nomes estos 25 falten). Van
# ací, no a `numerals.py`, perquè per categoria gramatical real són
# ADJECTIUS (ordinals), igual que la resta que ja agafa esta capa.
_ORDINALS_PERDUTS = {
    "dihuitè": "divuitè",
    "huitens": "vuitens",
    "huitè": "vuitè",
    "vint-i-huitè": "vint-i-vuitè",
    "trenta-huitè": "trenta-vuitè",
    "quaranta-huitè": "quaranta-vuitè",
    "cinquanta-huitè": "cinquanta-vuitè",
    "seixanta-huitè": "seixanta-vuitè",
    "setanta-huitè": "setanta-vuitè",
    "noranta-huitè": "noranta-vuitè",
    "huitanta-unè": "vuitanta-unè",
    "huitanta-dosè": "vuitanta-dosè",
    "huitanta-tresè": "vuitanta-tresè",
    "huitanta-quatrè": "vuitanta-quatrè",
    "huitanta-cinquè": "vuitanta-cinquè",
    "huitanta-sisè": "vuitanta-sisè",
    "huitanta-setè": "vuitanta-setè",
    "huitanta-huitè": "vuitanta-vuitè",
    "huitanta-novè": "vuitanta-novè",
    "huitantenes": "vuitantenes",
    "huit-centè": "vuit-centè",
    "huitantena": "vuitantena",
    "huitantè": "vuitantè",
    "denovè": "dinovè",
    "dessetè": "dissetè",
}


def _formes_demostratius_conegudes() -> set[str]:
    """Formes font (valencià) que ja cobrix `demostratius.py` amb
    autoritat pròpia -- este lèxic general les ha d'ignorar encara que
    aparega una entrada per a elles en una font nova (bug real trobat
    05/10/2026: "unificado.json" porta `eixa->aqueixa`, una traducció
    "correcta" en abstracte pero que ignora la decisió ja presa de
    col·lapsar este/eixe/aqueix tots cap a "aquest" -- vore
    `demostratius.py` per al raonament complet). Import diferit (no al
    nivell de mòdul) per a evitar cap problema d'orde d'importació."""
    from .demostratius import carrega_demostratius

    return set(carrega_demostratius().keys())


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


def _carrega_temporal(path: Path) -> dict[str, str]:
    """Carrega el pegat TEMPORAL (vore docstring del mòdul). Si el fitxer
    no existix -- s'ha fusionat a una font permanent i s'ha esborrat, tal
    com indica el seu propi `descripcio` -- torna buit sense error, perquè
    esta funció no haja de llevar-se a mà de `carrega_lexic()`.
    """
    if not path.exists():
        return {}
    dades = json.loads(path.read_text(encoding="utf-8"))
    return {val: cat for val, cat in dades.items() if val != "descripcio"}


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


def _resol_polisemia(entries: list[dict]) -> str:
    """Tria quina forma catalana usar quan una paraula valenciana del
    lèxic general té més d'una entrada (polisèmia): la marcada
    `canonica: true` si n'hi ha exactament una, si no la primera trobada
    al fitxer."""
    canoniques = [e for e in entries if e.get("canonica") is True]
    triada = canoniques[0] if len(canoniques) == 1 else entries[0]
    return triada["catalan"].strip()


# Categories de `lexico_general.json` (16/10/2026, vore docstring del
# mòdul i documentacio/hoja_de_ruta_migracio_diccionarios_v1.md) que
# pertanyen a ESTA capa -- "num" (numerals.py) i "det" (demostratius.py,
# que a sobre té un conflicte real mesurat: "eixe"->"aqueix" literal del
# fitxer NO val, el motor ja mesurava "eixe"->"aquest") es queden fora,
# cada un amb el seu propi mòdul/font.
_CATEGORIES_LEXIC_GENERAL = {"n", "adj", "adv", "cnjadv", "pr", "ij", "prn"}

# Bug de dades conegut, sense corregir a l'origen encara (16/10/2026,
# vore hoja_de_ruta_migracio_diccionarios_v1.md §4ter): "xicotet" ve
# marcat `canonica: true` cap a "menut", pero mesurat contra 1.958
# frases reals de gplsi (14/10/2026) la traducció real és SEMPRE
# "petit". Override explícit per a no perdre eixa evidència mentre la
# font no ho corregisca.
_CANONICA_OVERRIDES = {"xicotet": "petit"}


def _carrega_lexic_general(path: Path) -> dict[str, str]:
    demostratius_coneguts = _formes_demostratius_conegudes()
    dades = json.loads(path.read_text(encoding="utf-8"))
    per_paraula: dict[str, list[dict]] = {}
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        if entrada.get("categoria") not in _CATEGORIES_LEXIC_GENERAL:
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        if valenciano.lower() in demostratius_coneguts:
            continue
        per_paraula.setdefault(valenciano.lower(), []).append(entrada)
    lookup = {val: _resol_polisemia(entries) for val, entries in per_paraula.items()}
    for val, cat in _CANONICA_OVERRIDES.items():
        if val in lookup:
            lookup[val] = cat
    return lookup


def carrega_canvis_genere(path: Path = CANVI_GENERE_PATH) -> dict[str, str]:
    """Llig `canvi_genere_lexic_avl.json`: `{forma_valenciana: "m"|"f"}`
    per a les poques paraules on `LexicRule` canvia el gènere gramatical
    sencer (vore docstring del mòdul).

    >>> carrega_canvis_genere()["dacsa"]
    'm'
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(dades.get("canvis", {}))


def carrega_lexic(
    lexic_general_path: Path = LEXIC_GENERAL_PATH,
    flexio_genere_path: Path = FLEXIO_GENERE_PATH,
    temporal_path: Path = TEMPORAL_PATH,
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
    >>> lookup["vesprada"]
    'tarda'
    >>> lookup["xicotet"]
    'petit'
    >>> "qué" in lookup  # parell retirat de les dades al merge del 21/10/2026
    False
    >>> lookup["hui"]
    'avui'
    >>> lookup["llavar"]
    'rentar'
    >>> lookup["huitè"]
    'vuitè'

    19/10/2026: `_BUG_DADES_CONEGUTS` retirada a petició de l'usuari (vore
    CLAUDE.md, "Pendent per a la propera sessió"). Regressions conegudes i
    acceptades mentre no s'arreglen en origen -- "després" (mai hauria de
    canviar) i "ensenyança" (perd la concordança de gènere) tornen a
    convertir-se, i "alcalde" torna a "batlle" encara que este registre
    preferisca la paraula compartida:

    >>> lookup["després"]
    'desprès'
    >>> lookup["ensenyança"]
    'ensenyament'
    >>> lookup["alcalde"]
    'batlle'
    """
    lookup: dict[str, str] = {}
    for carregador, path in (
        (_carrega_temporal, temporal_path),
        (_carrega_flexio_genere, flexio_genere_path),
        (_carrega_lexic_general, lexic_general_path),
    ):
        for val, cat in carregador(path).items():
            lookup.setdefault(val, cat)
    for val, cat in _LEXIC_PERDUT_RESTAURAT.items():
        lookup.setdefault(val, cat)
    for val, cat in _ORDINALS_PERDUTS.items():
        lookup.setdefault(val, cat)
    return lookup


class LexicRule:
    """Substitueix paraules valencianes conegudes per la seua forma
    catalana (vore docstring del mòdul per a l'orde de fonts). Mai toca un
    token ja traduït per una capa anterior (`is_translated`) ni un
    possible nom propi (`is_proper_noun`, fixat per `marca_noms_propis()`
    abans de córrer cap regla -- vore rules/__init__.py).

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Vull parlar amb el meu servici.")
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

    >>> from .. import detokenize
    >>> toks = tokenize("Han penjat l'espill a la paret.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> detokenize(toks)
    'Han penjat el mirall a la paret.'

    Concordança de gènere tras substitució (RC044 -- vore docstring del
    mòdul i `canvi_genere_lexic_avl.json`):

    >>> toks = tokenize("Entre els cereals estan el blat i la dacsa.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> detokenize(toks)
    'Entre els cereals estan el blat i el blat de moro.'

    Filtre POS per a "tancada" (homonimia_lexica, 19/10/2026 -- vore
    docstring del mòdul): com a NOUN ("vallado") sí es toca, com a ADJ
    ("tancat/tancada", "closed") mai:

    >>> from .. import pos_tagger
    >>> toks = tokenize("La tancada del corral es va trencar.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('tancada', 'closa')]
    >>> toks = tokenize("La porta estava tancada.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def __init__(
        self,
        lexic_general_path: Path = LEXIC_GENERAL_PATH,
        flexio_genere_path: Path = FLEXIO_GENERE_PATH,
        temporal_path: Path = TEMPORAL_PATH,
        canvi_genere_path: Path = CANVI_GENERE_PATH,
        categoria_path: Path = CATEGORIA_GRAMATICAL_PATH,
    ) -> None:
        self._lookup = carrega_lexic(lexic_general_path, flexio_genere_path, temporal_path)
        self._canvis_genere = carrega_canvis_genere(canvi_genere_path)
        self._categories = carrega_categoria_gramatical(categoria_path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            forma = self._lookup.get(minuscules)
            if forma is not None:
                if not pos_compatible(tok.pos, minuscules, self._categories):
                    continue
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                genere_nou = self._canvis_genere.get(minuscules)
                if genere_nou is not None:
                    corregeix_determinant_abans(tokens, i, genere_nou)
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = self._lookup.get(resta.lower())
            if forma is not None and not pos_compatible(tok.pos, resta.lower(), self._categories):
                continue
            if forma is not None:
                aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma)
                tok.is_translated = True
        return tokens
