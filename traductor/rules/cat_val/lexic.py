"""
cat_val/lexic.py -- Lookup invers de lèxic general: el MATEIX
`traductor/data/lexic_general.json` que fa servir `rules/val_cat/lexic.py`,
ara indexat per `catalan`.

Verificat contra les dades reals abans d'escriure codi (vore
`documentacio/hoja_de_ruta_traductor_invers.md`): de 1.240 formes
catalanes úniques (d'una sola paraula), només 10 (0,8%) tenen mes d'un
candidat valencià real (p.ex. "noi" -> "xiquet"/"xic") -- s'exclouen,
mateix criteri que `conjugacions_dict.py`.

**Lèxic multi-paraula català (implementat 13/10/2026)**: 8 entrades reals
de `lexic_general.json` tenen el català en 2-3 paraules i el valencià
en una ("blat de moro"->"dacsa", "demà passat"->"despús-demà", "trucar
per telèfon"->"telefonar", "cop de porta"->"portada", "cop de puny"->
"punyada", "gall dindi"->"polit", "pioc salvatge"->"avitarda",
"obra de paleta"->"construcció" -- esta última ja activa en sentit
val->cat, inclosa per coherència encara que semànticament siga una
correspondència ampla). Es busca la frase MES LLARGA que comence en cada
token (per si mai coincidixen un prefix de 2 paraules amb una frase de
3) abans de l'intent d'una sola paraula -- aixina "moro" solt (dins
"blat de moro") mai arriba a la capa de lookup d'un sol token.

**Concordança de gènere invertida (13/10/2026)**: "blat de moro"->"dacsa"
canvia el determinant masculí que acompanyava el català ("el blat de
moro") pel femení valencià ("la dacsa") -- el mateix cas que
`canvi_genere_lexic_avl.json` ja documenta per al sentit contrari
("dacsa": "m", el genere que pren el CATALÀ). En sentit invers el genere
necessari és l'OPOSAT (si el català es "m", el valencià original era
"f", i és eixe el que cal restaurar) -- es reutilitza directament
`corregeix_determinant_abans` (`rules/__init__.py`), sense cap fitxer de
dades nou, nomes invertint "m"<->"f" sobre el mateix fitxer.

Protecció igual que `rules/val_cat/lexic.py`: les formes que ja gestiona
`cat_val/demostratius.py` amb autoritat pròpia ("aqueix", "aquest"...) es
quedarien fora encara que aparegueren per accident en el lèxic general.

`flexio_genere_avl.json` en sentit invers (afegit 08/10/2026, trobat
mesurant contra el benchmark -- RC004 "nena" es quedava sense tocar):
el mateix fitxer que fa servir `rules/val_cat/lexic.py`, invertit. Els `regulars`
(xiquet/xic/corder) reverteixen nets, mateixa derivació +a/+s/+es que el
costat val->cat. Els `irregulars` (xicoteta/petita, els dos -> "menuda")
NO reverteixen nets -- "menuda" és ambigua de veres (podria vindre de
"xicoteta" o de "petita", dos paraules valencianes reals i distintes),
així que s'exclouen de la taula inversa sencera, preferint fals negatiu.

**Contracció "al"/"del" desfeta davant de vocal (13/10/2026, RC016)**:
"sortir" (consonant inicial) es tradueix a "eixir" (vocal inicial), així
que "Al sortir..." (català) es convertia en "Al eixir..." en compte
d'"A l'eixir...". Corregit cridant `corregeix_contraccio_al_abans`
(`rules/__init__.py`) just després del lookup d'una paraula -- mirall
invers d'`aplica_amb_prefix_elidit`, que fa la contracció contrària
(DESFÀ "l'" quan la paraula deixa de començar en vocal).

**"tard" excluit (13/10/2026, RC067)**: `lexic_general.json` confon
l'adverbi "tard" (late) amb el nom "tarda" (afternoon) per l'ambigüitat
del castellà d'origen "tarde" -- vore comentari de `_BUG_DADES_CONEGUTS_CAT`
més avall per al detall complet.

**Homonimia_lexica (19/10/2026, nou)**: la guia oficial del proveïdor
(`diccionarios/Funcionamiento listas de palabras.pdf`) confirma que
les entrades `problema: "homonimia_lexica"` amb `lemas` de categories
gramaticals DIFERENTS es resolen amb PoS (spaCy); amb categories
iguals/solapades fa falta un LLM. S'amplia `categoria_gramatical_lexic.json`
(ja actiu ací des de 13/10/2026 per a "nou"/"anou") amb 6 entrades més on
l'ambigüitat cau d'este costat (`lado: "val"`): "exitosa(a)"/"exitoses"
(ADJ), "carència"/"carències" (NOUN), "llavadora"/"llavadores" (NOUN).
Cas real confirmat amb el benchmark gplsi (+2 frases): "manca" com a VERB
("mancar", falta) mai es tocava abans d'esta correcció -- es convertia
sempre a "carència" encara que el verb i el nom compartixen la mateixa
grafia catalana. Les altres 4 entrades amb `lado: "val"` i categories
DIFERENTS ("falaguera", "brollador", "brulla(es)", "panolla(es)",
"fartada(es)") encara són `_PENDENT` (sense verificar) a
`lexico_general.json` -- no activades, afegir-les quan deixen de ser-ho.
Les que SÍ tenen categories iguals/solapades ("bes", "bragues"/"calces",
"hamaca"/"gandula") es queden sense resoldre, tal com diu la guia.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import (
    CATEGORIA_GRAMATICAL_PATH,
    Token,
    aplica_amb_prefix_elidit,
    carrega_categoria_gramatical,
    corregeix_article_abans,
    corregeix_contraccio_al_abans,
    corregeix_determinant_abans,
    paraules_segudents_son,
    pos_compatible,
    preserva_majuscula,
    separa_prefix_elidit,
)

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
LEXIC_GENERAL_PATH = _DATA / "lexic_general.json"
FLEXIO_GENERE_PATH = _DATA / "flexio_genere_avl.json"
CANVI_GENERE_PATH = _DATA / "canvi_genere_lexic_avl.json"

# Mateix bug de dades conegut que `rules/val_cat/lexic.py` ("después" no és una
# excepció dialectal, és un error de transcripció del fitxer font) --
# s'exclou pel costat català ("desprès"), equivalent invers.
#
# "ensenyament" (afegit 13/10/2026, trobat mesurant): `lexic_general.json`
# té {"valenciano": "ensenyança", "catalan": "ensenyament"}, tècnicament
# un parell dialectal real. Pero mesurant les 6 aparicions reals de
# "ensenyament" al benchmark invertit, 5 de 6 volen la paraula SENSE
# TOCAR (el valencià de referència fa servir "ensenyament" igual que el
# català ahí) i només 1 (RC093) vol "ensenyança" -- ambigüitat real amb
# majoria clara. S'exclou (preferix la majoria, mateix criteri que
# "aquest"->"este" a `demostratius.py`, pero ací la majoria diu "no
# toques res" en compte de "tria un valor per defecte").
#
# "què" (afegit 13/10/2026, trobat mesurant -- RC053/RC057/RC094):
# `lexic_acentuacio_general.json` té {"valenciano": "qué", "catalan":
# "què"}, seguint el mateix patró general que francés/francès. Pero
# comptant totes les aparicions reals de "qué"/"què" al costat valencià
# del benchmark: 7 de 9 fan servir "què" (accent OBERT, com el català),
# nomes 2 "qué" -- majoria clara en sentit contrari al que diu esta
# entrada en concret. S'exclou, mateix criteri que "ensenyament" --
# CASUALITAT ACCEPTADA: RC055 és un dels 2 casos minoritaris que SI
# volien "qué", i ara es queda sense tocar (abans eixia be per
# casualitat, convertint-ho SEMPRE). Net +3 (+4 casos majoritaris, -1
# minoritari) -- mateixa filosofia que "aquest"->"este" (77/23).
#
# CONFIRMAT PER NORMATIVA (19/10/2026, GNV -- Gramàtica Normativa
# Valenciana de l'AVL, `docs_gramatica/gnv_complet.txt`, §5.1.2.1,
# "Observacions sobre l'accentuació de les ee"): el comptatge de dalt NO
# és nomes majoria empírica, és la regla oficial. La norma general
# valenciana és accent AGUT per a qualsevol "e" tancada tònica (cinqué,
# francés, comprés...), pero el text normatiu fa una EXCEPCIÓ EXPLÍCITA
# justa per a dos paraules: "A fi d'evitar una excessiva discrepància
# entre les diferents varietats de la llengua, també porten accent greu
# -- tot i pronunciar-se habitualment amb e tancada en valencià -- dos
# paraules gramaticals d'ús freqüent (el pronom relatiu i interrogatiu
# tònic QUÈ i la conjunció PERQUÈ)". És a dir: "què" amb accent greu NO
# és un catalanisme ni una preferència del corpus, és l'ortografia
# normativa valenciana en si mateixa -- "qué" (accent agut) és la grafia
# NO normativa, encara que es pronuncie aixina. Per això esta exclusió es
# queda encara que algun text (com RC055) faça servir "qué" de manera
# informal/fonètica.
#
# "tard" ELIMINAT d'esta llista (16/10/2026): la nova font
# (`lexico_general.json`, vore hoja_de_ruta_migracio_diccionarios_v1.md)
# ja no porta cap entrada amb catalan=="tard" -- el bug "vesprada"/"tard"
# ve corregit en origen ("vesprada"->"tarda" ara), confirmat que cap
# entrada col·lidix ja amb "tard". Es queda documentat ací per
# l'historial (RC067 original) pero ja no cal excloure'l.
#
# RETIRADA SENCERA 19/10/2026 a petició explícita de l'usuari (vore
# CLAUDE.md, "Pendent per a la propera sessió" -- no vol llistes
# d'exclusió a mà, vol que el dato font es corregisca ell mateix amb el
# seu permís). Regressions conegudes i acceptades mentre no s'arreglen en
# origen: "desprès" tornarà a eixir "després" (mateix error de
# transcripció que l'altre costat); "ensenyament" tornarà a perdre la
# concordança de gènere amb "ensenyança"; "què" tornarà a convertir-se en
# "qué" encara que el GNV (§5.1.2.1, vore dalt) confirme "què" com
# l'ortografia normativa valenciana -- este últim és la regressió que més
# pes té, ja no és nomes majoria de corpus sinó normativa oficial.
# Abans: `_BUG_DADES_CONEGUTS_CAT = {"desprès", "ensenyament", "què"}`.

# Categories de `lexico_general.json` (16/10/2026, mateix criteri que
# `rules/val_cat/lexic.py` -- vore hoja_de_ruta_migracio_diccionarios_v1.md):
# "num"/"det" es queden fora, cada un amb el seu propi mòdul/font.
_CATEGORIES_LEXIC_GENERAL = {"n", "adj", "adv", "cnjadv", "pr", "ij", "prn"}

# Filtre POS general per categoria gramatical (13/10/2026, vore
# `rules/__init__.py::pos_compatible` i
# `traductor/data/categoria_gramatical_lexic.json`): abans nomes hi havia
# "nou" com a set solt ací mateix (`_EXIGEIX_NOUN_CAT = {"nou"}`, homògraf
# TRIPLE "nou"=new/ADJ, nine/NUM, walnut/NOUN -- RC070/RC076/RC097
# volien el sentit "new" sense tocar). Ara és un mecanisme ÚNIC i OBERT:
# qualsevol paraula classificada al fitxer de dades es comprova igual,
# sense fer falta tocar codi cada vegada que apareix un cas nou -- vore
# el fitxer de dades per a l'estat de la classificació (de moment nomes
# "anou"/"nou", pendent d'ampliar-se).

# Paraules perdudes de veres migrant a `lexico_general.json` (16/10/2026,
# mateix criteri que `rules/val_cat/lexic.py::_LEXIC_PERDUT_RESTAURAT`):
# confirmades amb regressió real de benchmark (RC022, RC025).
_LEXIC_PERDUT_RESTAURAT_CAT = {
    "empentar": "espentar",
    "rentar": "llavar",
}

# Ordinals bàsics 5é/7é/9é/10é en sentit adjectiu (16/10/2026, RC144):
# `lexico_general.json` SÍ te l'entrada correcta ("cinqué"->"cinquè" amb
# `canonica: true`, colisionant amb una altra entrada "cinqué"->"cinqué"
# sentit nom, `canonica: false`) -- `_carrega_lexic_general` (val->cat)
# la resol be triant la `canonica`, pero `_invertix_sense_ambiguitat`
# (agrupa per CATALAN) exclou "cinquè" sencer perque, mirat des d'eixe
# costat, hi ha mes d'un candidat valencià real. Mateix patró de
# conservadorisme ja documentat (preferix fals negatiu), restaurat a mà
# amb l'evidencia d'esta regressió real.
_ORDINALS_BASICS_PERDUTS_CAT = {
    "cinquè": "cinqué",
    "sisè": "sisé",
    "setè": "seté",
    "novè": "nové",
}

# Ordinals masculins singulars en "-è", sentit invers (16/10/2026, vore
# `rules/val_cat/lexic.py::_ORDINALS_PERDUTS` per a l'evidència completa).
_ORDINALS_PERDUTS_CAT = {
    "divuitè": "dihuitè",
    "vuitens": "huitens",
    "vuitè": "huitè",
    "vint-i-vuitè": "vint-i-huitè",
    "trenta-vuitè": "trenta-huitè",
    "quaranta-vuitè": "quaranta-huitè",
    "cinquanta-vuitè": "cinquanta-huitè",
    "seixanta-vuitè": "seixanta-huitè",
    "setanta-vuitè": "setanta-huitè",
    "noranta-vuitè": "noranta-huitè",
    "vuitanta-unè": "huitanta-unè",
    "vuitanta-dosè": "huitanta-dosè",
    "vuitanta-tresè": "huitanta-tresè",
    "vuitanta-quatrè": "huitanta-quatrè",
    "vuitanta-cinquè": "huitanta-cinquè",
    "vuitanta-sisè": "huitanta-sisè",
    "vuitanta-setè": "huitanta-setè",
    "vuitanta-vuitè": "huitanta-huitè",
    "vuitanta-novè": "huitanta-novè",
    "vuitantenes": "huitantenes",
    "vuit-centè": "huit-centè",
    "vuitantena": "huitantena",
    "vuitantè": "huitantè",
    "dinovè": "denovè",
    "dissetè": "dessetè",
}


def _formes_demostratius_coneguts_cat() -> set[str]:
    from .demostratius import formes_cobertes_per_demostratius_invers

    return formes_cobertes_per_demostratius_invers()


def _invertix_sense_ambiguitat(entrades: list[tuple[str, str, bool]]) -> dict[str, str]:
    """Agrupa parells `(valenciano, catalan, canonica)` per `catalan`. Si hi
    ha un únic candidat valencià, es queda amb ell. Si n'hi ha més d'un,
    REGLA FIXA de l'usuari (20/10/2026): en cas de dubte mana el camp
    `canonica` del proveïdor -- es tria el candidat marcat `canonica: true`
    si n'hi ha exactament un; si no n'hi ha cap (o n'hi ha més d'un),
    s'exclou igual que abans (preferix fals negatiu).

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


def _carrega_lexic_general_invers(path: Path) -> dict[str, str]:
    demostratius_coneguts = _formes_demostratius_coneguts_cat()
    dades = json.loads(path.read_text(encoding="utf-8"))
    entrades: list[tuple[str, str, bool]] = []
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        if entrada.get("categoria") not in _CATEGORIES_LEXIC_GENERAL:
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan:
            continue
        if " " in valenciano or " " in catalan:
            continue
        if catalan.lower() in demostratius_coneguts:
            continue
        entrades.append((valenciano.lower(), catalan.lower(), bool(entrada.get("canonica"))))
    # Les entrades IDÈNTIQUES als dos costats (21/10/2026) participen en la
    # tria per `canonica` i es lleven DESPRÉS: si la canònica d'un grup és
    # "mentre"->"mentre" (E1647, en col·lisió amb E0040 "mentres"->"mentre"),
    # vol dir "no traduïsques", i "mentre" no ha d'acabar en "mentres" per
    # ser l'únic candidat que quedava. Abans es descartaven ABANS de triar.
    return {cat: val for cat, val in _invertix_sense_ambiguitat(entrades).items() if cat != val}


def carrega_frases_invers(path: Path = LEXIC_GENERAL_PATH) -> dict[tuple[str, ...], str]:
    """Llig `lexic_general.json` quedant-se NOMÉS amb les entrades on el
    català és 2-3 paraules i el valencià UNA -- vore docstring del mòdul.
    Torna `{(paraula1, paraula2, ...): forma_valenciana}`, totes en
    minúscules.

    >>> frases = carrega_frases_invers()
    >>> frases[("blat", "de", "moro")]
    'dacsa'
    >>> frases[("gall", "dindi")]
    'polit'
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    entrades: list[tuple[str, tuple[str, ...], bool]] = []
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        if entrada.get("categoria") not in _CATEGORIES_LEXIC_GENERAL:
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano or " " not in catalan:
            continue
        paraules = tuple(p.lower() for p in catalan.split())
        entrades.append((valenciano.lower(), paraules, bool(entrada.get("canonica"))))
    return _invertix_sense_ambiguitat(entrades)


def carrega_canvis_genere_invers(
    frases: dict[tuple[str, ...], str], canvi_genere_path: Path = CANVI_GENERE_PATH
) -> dict[tuple[str, ...], str]:
    """Creua `frases` (frase catalana -> paraula valenciana) amb
    `canvi_genere_lexic_avl.json` (paraula valenciana -> gènere català
    resultant) per a obtindre `{frase_catalana: gènere VALENCIÀ a
    restaurar}` -- l'oposat del gènere català documentat (vore docstring
    del mòdul).

    >>> frases = carrega_frases_invers()
    >>> canvis = carrega_canvis_genere_invers(frases)
    >>> canvis[("blat", "de", "moro")]
    'f'
    """
    dades = json.loads(Path(canvi_genere_path).read_text(encoding="utf-8"))
    canvis_val = dades.get("canvis", {})
    oposat = {"m": "f", "f": "m"}
    resultat: dict[tuple[str, ...], str] = {}
    for paraules, valenciano in frases.items():
        genere_cat = canvis_val.get(valenciano)
        if genere_cat is not None:
            resultat[paraules] = oposat[genere_cat]
    return resultat


def _deriva_genere_nombre_invers(masc_cat: str, masc_val: str) -> dict[str, str]:
    """Mirall invers de `_deriva_genere_nombre` de `rules/val_cat/lexic.py`.

    >>> _deriva_genere_nombre_invers("nen", "xiquet")
    {'nena': 'xiqueta', 'nens': 'xiquets', 'nenes': 'xiquetes'}
    """
    return {
        masc_cat + "a": masc_val + "a",
        masc_cat + "s": masc_val + "s",
        masc_cat + "es": masc_val + "es",
    }


def _carrega_flexio_genere_invers(path: Path = FLEXIO_GENERE_PATH) -> dict[str, str]:
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for masc_val, masc_cat in dades["regulars"].items():
        if masc_val == "descripcio":
            continue
        lookup[masc_cat] = masc_val
        lookup.update(_deriva_genere_nombre_invers(masc_cat, masc_val))
    # Els "irregulars" NO reverteixen nets -- vore docstring del mòdul
    # ("menuda" ambigua entre "xicoteta"/"petita"). S'exclouen sencers.
    return lookup


def carrega_lexic_invers(
    lexic_general_path: Path = LEXIC_GENERAL_PATH,
    flexio_genere_path: Path = FLEXIO_GENERE_PATH,
) -> dict[str, str]:
    """Fusiona el lèxic general i la flexió de gènere en sentit invers
    (el primer que definix una paraula guanya, mateixa prioritat que
    `rules/val_cat/lexic.py`). La capa d'accentuació a banda es va
    retirar 16/10/2026 -- vore docstring de `rules/val_cat/lexic.py`.

    >>> lookup = carrega_lexic_invers()
    >>> lookup["nen"]
    'xiquet'
    >>> lookup["nena"]
    'xiqueta'
    >>> lookup["signant"]
    'firmant'
    >>> lookup["acetilè"]
    'acetilé'
    >>> lookup["avui"]
    'hui'
    >>> "menuda" in lookup
    False
    >>> lookup["empentar"]
    'espentar'
    >>> lookup["vuitè"]
    'huitè'

    19/10/2026: `_BUG_DADES_CONEGUTS_CAT` retirada a petició de l'usuari
    (vore CLAUDE.md). "desprès" (adjectiu català) -> "després" (adjectiu
    valencià) és un parell real; "ensenyament" perd la concordança de
    gènere mentre no s'arregle en origen:

    >>> lookup["desprès"]
    'després'
    >>> lookup["ensenyament"]
    'ensenyança'

    Dades corregides al merge del 21/10/2026: "qué"/"què" ja no és un
    parell ("què" és normatiu als dos dialectes), i la canònica
    "mentre"->"mentre" vol dir que "mentre" no es toca:

    >>> "què" in lookup
    False
    >>> "mentre" in lookup
    False
    """
    lookup: dict[str, str] = {}
    for carregador, path in (
        (_carrega_flexio_genere_invers, flexio_genere_path),
        (_carrega_lexic_general_invers, lexic_general_path),
    ):
        for cat, val in carregador(path).items():
            lookup.setdefault(cat, val)
    for cat, val in _LEXIC_PERDUT_RESTAURAT_CAT.items():
        lookup.setdefault(cat, val)
    # Els ordinals de l'usuari SOBREESCRIUEN (20/10/2026): des que les
    # col·lisions es resolen per `canonica`, "cinquè" ja tindria valor
    # ("quint", la forma culta canònica) i `setdefault` no el canviaria --
    # pero el corpus real vol la forma popular ("cinqué"). Decisió explícita
    # de l'usuari: mantindre estes llistes per damunt de la canònica.
    lookup.update(_ORDINALS_PERDUTS_CAT)
    lookup.update(_ORDINALS_BASICS_PERDUTS_CAT)
    return lookup


class LexicInversRule:
    """Substitueix paraules catalanes conegudes per la seua forma
    valenciana (vore docstring del mòdul). Mai toca un token ja traduït
    ni un possible nom propi.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Vull parlar amb el meu servei.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('servei', 'servici')]

    Nom propi protegit:

    >>> toks = tokenize("Coneixes a Nen, el meu gos?")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Paraula enganxada a un prefix elidit:

    >>> toks = tokenize("Parlem d'algarvès.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'algarvès", "d'algarvés")]

    Frase catalana multi-paraula -> una sola paraula valenciana (vore
    docstring del mòdul): "moro" sol mai arriba al lookup d'una paraula,
    perquè la frase de 3 paraules es prova primer, i el determinant
    anterior es corregix de gènere ("el"->"la", dacsa és femení):

    >>> from .. import detokenize
    >>> toks = tokenize("Mengem el blat de moro cada estiu.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> detokenize(toks)
    'Mengem la dacsa cada estiu.'

    Filtre POS per a "nou" (homògraf): com a ADJ ("new", el cas real
    conegut) mai es toca -- vore docstring del mòdul per a per què el
    sentit NOUN ("walnut") no es pot demostrar encara (spaCy no el
    distingix fiablement, cap cas real tampoc el necessita):

    >>> from .. import pos_tagger
    >>> toks = tokenize("En un nou procés d'expansió.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Filtre POS per a "manca" (homonimia_lexica, 19/10/2026 -- vore
    docstring del mòdul): com a VERB ("mancar", "faltar") mai es toca,
    com a NOUN sí ("carència"):

    >>> toks = tokenize("Aquesta regió manca relativament de grans cràters.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    >>> toks = tokenize("Patix una gran manca afectiva.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('manca', 'carència')]

    Contracció "al" desfeta en "a l'" quan la paraula substituïda passa a
    començar en vocal (RC016, vore docstring del mòdul):

    >>> toks = tokenize("Es va mirar al mirall.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> detokenize(toks)
    "Es va mirar a l'espill."

    "tard" (adverbi) mai es toca -- vore docstring del mòdul (RC067):

    >>> toks = tokenize("Ho vaig saber més tard.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def __init__(
        self,
        lexic_general_path: Path = LEXIC_GENERAL_PATH,
        flexio_genere_path: Path = FLEXIO_GENERE_PATH,
        frases_path: Path = LEXIC_GENERAL_PATH,
        canvi_genere_path: Path = CANVI_GENERE_PATH,
        categoria_path: Path = CATEGORIA_GRAMATICAL_PATH,
    ) -> None:
        self._lookup = carrega_lexic_invers(lexic_general_path, flexio_genere_path)
        self._categories = carrega_categoria_gramatical(categoria_path)
        frases = carrega_frases_invers(frases_path)
        self._canvis_genere = carrega_canvis_genere_invers(frases, canvi_genere_path)
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
            genere_nou = self._canvis_genere.get(paraules)
            if genere_nou is not None:
                corregeix_determinant_abans(tokens, i, genere_nou)
            return True
        return False

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            if self._intenta_frase(tokens, i):
                continue
            minuscules = tok.surface.lower()
            forma = self._lookup.get(minuscules)
            if forma is not None:
                if not pos_compatible(tok.pos, forma, self._categories):
                    continue
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                corregeix_contraccio_al_abans(tokens, i)
                corregeix_article_abans(tokens, i)
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = self._lookup.get(resta.lower())
            if forma is not None and not pos_compatible(tok.pos, forma, self._categories):
                continue
            if forma is not None:
                aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma)
                tok.is_translated = True
        return tokens
