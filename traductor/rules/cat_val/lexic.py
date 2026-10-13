"""
cat_val/lexic.py -- Lookup invers de lèxic general: el MATEIX
`traductor/data/lexic_mauricio.json` que fa servir `rules/val_cat/lexic.py`,
ara indexat per `catalan`.

Verificat contra les dades reals abans d'escriure codi (vore
`documentacio/hoja_de_ruta_traductor_invers.md`): de 1.240 formes
catalanes úniques (d'una sola paraula), només 10 (0,8%) tenen mes d'un
candidat valencià real (p.ex. "noi" -> "xiquet"/"xic") -- s'exclouen,
mateix criteri que `conjugacions_dict.py`.

**Lèxic multi-paraula català (implementat 13/10/2026)**: 8 entrades reals
de `lexic_mauricio.json` tenen el català en 2-3 paraules i el valencià
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

**"tard" excluit (13/10/2026, RC067)**: `lexic_mauricio.json` confon
l'adverbi "tard" (late) amb el nom "tarda" (afternoon) per l'ambigüitat
del castellà d'origen "tarde" -- vore comentari de `_BUG_DADES_CONEGUTS_CAT`
més avall per al detall complet.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import (
    CATEGORIA_GRAMATICAL_PATH,
    Token,
    aplica_amb_prefix_elidit,
    carrega_categoria_gramatical,
    corregeix_contraccio_al_abans,
    corregeix_determinant_abans,
    paraules_segudents_son,
    pos_compatible,
    preserva_majuscula,
    separa_prefix_elidit,
)

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
MAURICIO_PATH = _DATA / "lexic_mauricio.json"
ACENTUACIO_MAURICIO_PATH = _DATA / "lexic_acentuacio_mauricio.json"
FLEXIO_GENERE_PATH = _DATA / "flexio_genere_avl.json"
CANVI_GENERE_PATH = _DATA / "canvi_genere_lexic_avl.json"

# Mateix bug de dades conegut que `rules/val_cat/lexic.py` ("después" no és una
# excepció dialectal, és un error de transcripció del fitxer font) --
# s'exclou pel costat català ("desprès"), equivalent invers.
#
# "ensenyament" (afegit 13/10/2026, trobat mesurant): `lexic_mauricio.json`
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
# `lexic_acentuacio_mauricio.json` té {"valenciano": "qué", "catalan":
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
# "tard" (afegit 13/10/2026, trobat investigant RC067): `lexic_mauricio.json`
# té {"valenciano": "vesprada", "catalan": "tard"} (id E0100, camp
# `espanol: "tarde"`) -- el castellà "tarde" és ambigu entre l'ADVERBI
# ("late") i el NOM ("afternoon"), i la font ha confós els dos sentits:
# "vesprada" és la traducció correcta nomes per al NOM ("tarda" en
# català, no "tard"), mai per a l'adverbi. L'ÚNICA aparició real
# d'esta entrada a tot el benchmark (RC067, "més tard" = "later",
# adverbi) confirma l'error -- la referència valenciana vol "tard" sense
# tocar. S'exclou; "tarda"->"vesprada" (el nom, el parell correcte) no
# té cap entrada pròpia encara perque no hi ha evidencia real al
# benchmark (0 aparicions de "tarda" trobades).
_BUG_DADES_CONEGUTS_CAT = {"desprès", "ensenyament", "què", "tard"}

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


def _formes_demostratius_coneguts_cat() -> set[str]:
    from .demostratius import formes_cobertes_per_demostratius_invers

    return formes_cobertes_per_demostratius_invers()


def _invertix_sense_ambiguitat(entrades: list[tuple[str, str]]) -> dict[str, str]:
    """Agrupa parells `(valenciano, catalan)` per `catalan` i es queda
    NOMÉS amb els que tenen un únic candidat valencià real -- mateixa
    tècnica, verificada contra les dades, que `conjugacions_dict.py`."""
    candidats: dict[str, set[str]] = {}
    for valenciano, catalan in entrades:
        candidats.setdefault(catalan, set()).add(valenciano)
    return {cat: next(iter(vals)) for cat, vals in candidats.items() if len(vals) == 1}


def _carrega_mauricio_lexic_invers(path: Path) -> dict[str, str]:
    demostratius_coneguts = _formes_demostratius_coneguts_cat()
    dades = json.loads(path.read_text(encoding="utf-8"))
    entrades: list[tuple[str, str]] = []
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan:
            continue
        if " " in valenciano or " " in catalan:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        if catalan.lower() in _BUG_DADES_CONEGUTS_CAT:
            continue
        if catalan.lower() in demostratius_coneguts:
            continue
        entrades.append((valenciano.lower(), catalan.lower()))
    return _invertix_sense_ambiguitat(entrades)


def carrega_frases_invers(path: Path = MAURICIO_PATH) -> dict[tuple[str, ...], str]:
    """Llig `lexic_mauricio.json` quedant-se NOMÉS amb les entrades on el
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
    candidats: dict[tuple[str, ...], set[str]] = {}
    for entrada in dades:
        if "PENDENT" in (entrada.get("tipo") or ""):
            continue
        if entrada.get("tipo") == "v:top_gva":
            continue
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano or " " not in catalan:
            continue
        paraules = tuple(p.lower() for p in catalan.split())
        candidats.setdefault(paraules, set()).add(valenciano.lower())
    return {k: next(iter(v)) for k, v in candidats.items() if len(v) == 1}


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


def _carrega_acentuacio_invers(path: Path) -> dict[str, str]:
    dades = json.loads(path.read_text(encoding="utf-8"))
    entrades: list[tuple[str, str]] = []
    for entrada in dades:
        valenciano = entrada.get("valenciano", "").strip()
        catalan = entrada.get("catalan", "").strip()
        if not valenciano or not catalan or " " in valenciano or " " in catalan:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        if catalan.lower() in _BUG_DADES_CONEGUTS_CAT:
            continue
        entrades.append((valenciano.lower(), catalan.lower()))
    return _invertix_sense_ambiguitat(entrades)


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
    mauricio_path: Path = MAURICIO_PATH,
    acentuacio_path: Path = ACENTUACIO_MAURICIO_PATH,
    flexio_genere_path: Path = FLEXIO_GENERE_PATH,
) -> dict[str, str]:
    """Fusiona el lèxic general, el d'accentuació i la flexió de gènere
    en sentit invers (el primer que definix una paraula guanya, mateixa
    prioritat que `rules/val_cat/lexic.py`).

    >>> lookup = carrega_lexic_invers()
    >>> lookup["nen"]
    'xiquet'
    >>> lookup["nena"]
    'xiqueta'
    >>> lookup["signant"]
    'firmant'
    >>> lookup["acetilè"]
    'acetilé'
    >>> "desprès" in lookup
    False
    >>> lookup["avui"]
    'hui'
    >>> "menuda" in lookup
    False
    """
    lookup: dict[str, str] = {}
    for carregador, path in (
        (_carrega_flexio_genere_invers, flexio_genere_path),
        (_carrega_mauricio_lexic_invers, mauricio_path),
        (_carrega_acentuacio_invers, acentuacio_path),
    ):
        for cat, val in carregador(path).items():
            lookup.setdefault(cat, val)
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

    Contracció "al" desfeta en "a l'" quan la paraula substituïda passa a
    començar en vocal (RC016, vore docstring del mòdul):

    >>> toks = tokenize("Al sortir a l'exterior.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> detokenize(toks)
    "A l'eixir a l'exterior."

    "tard" (adverbi) mai es toca -- vore docstring del mòdul (RC067):

    >>> toks = tokenize("Ho vaig saber més tard.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def __init__(
        self,
        mauricio_path: Path = MAURICIO_PATH,
        acentuacio_path: Path = ACENTUACIO_MAURICIO_PATH,
        flexio_genere_path: Path = FLEXIO_GENERE_PATH,
        frases_path: Path = MAURICIO_PATH,
        canvi_genere_path: Path = CANVI_GENERE_PATH,
        categoria_path: Path = CATEGORIA_GRAMATICAL_PATH,
    ) -> None:
        self._lookup = carrega_lexic_invers(mauricio_path, acentuacio_path, flexio_genere_path)
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
