"""
cat_val/conjugacions_dict.py -- Lookup exacte INVERS de formes verbals:
`traductor/data/conjugacions_dialectals.json` (el MATEIX fitxer que fa
servir `rules/val_cat/conjugacions_dict.py`, sense cap còpia -- cada entrada ja
porta els dos camps `valenciano`/`catalan`), ara indexat per `catalan`.

Verificat contra les dades reals (08/10/2026, vore
`documentacio/hoja_de_ruta_traductor_invers.md`) abans d'escriure cap
línia de codi: de 50.526 formes catalanes úniques a tot el fitxer, NOMÉS
346 (0,68%) tenen més d'un candidat valencià real -- es calcula
directament ací (agrupant per `catalan`), no es confia nomes en el camp
`ambigu_cat_a_val` del proveïdor (verificar les dades, no el nom del camp).
Eixes 346 (sinònims que convergixen en català, p.ex. "sofreixin" podria
vindre de "sofrisquen" o de "patisquen") s'EXCLOUEN del lookup -- mateix
criteri de sempre, preferix fals negatiu.

**Per què esta direcció NO necessita cap equivalent de
`es_risc_mode_3a_plural`** (el problema mes gran de `rules/val_cat/conjugacions_dict.py`,
9.220 formes, 20% de la taula): eixe problema existix perquè el VALENCIÀ
fon indicatiu i subjuntiu en la mateixa grafia. El CATALÀ d'entrada ací
SEMPRE els distingix per escrit ("creuen" indicatiu / "creuin" subjuntiu),
així que el lookup "creuin"->"creuen" és net, sense ambigüitat -- el
mode ja ve resolt per com està escrit el català d'entrada.

**Correcció important (08/10/2026, trobada mesurant contra el benchmark
invertit, no suposada)**: la hoja de ruta deia que el filtre POS gairebé
no faria falta ací perquè el patró "persones"->"personis" és asimètric
(la paraula comuna cau sempre del costat valencià). ERA INCOMPLET: eixe
raonament només val per a verbs RARS com "personar"/"parar"/"poblar". Hi
ha ALTRES col·lisions amb verbs COMUNS que SÍ amenacen esta direcció --
trobades mesurant de veres, no per intuïció: "moro" (català, "jo moro",
present de "morir", un verb ben normal) col·lidix amb "moro" dins "blat
de moro"; "través" col·lidix amb una forma de "travar"; "signes"
col·lidix amb "tu signes" de "signar". Els 3 són NOMS comuns en el seu
context real, i spaCy (`ca_core_news_sm`) els etiqueta "NOUN" correctament
(verificat un a un abans d'escriure este filtre). Per això SÍ cal el
mateix filtre POS que `rules/val_cat/conjugacions_dict.py` -- i ara amb MES
fiabilitat, perquè l'entrada ja és català real (spaCy entrenat en català,
vore la hoja de ruta).

**Homògrafs segons el diccionari (22/10/2026, decisió de l'usuari)**: el
filtre POS ja no s'aplica a totes les formes. `conjugaciones_general.json`
porta dins de `morfologia` les lectures no verbals de cada forma ("estat":
`['n','m','sg']` + `['pp','m','sg']`; "través", "obres", "moro"...; vore
`carrega_homografs_conjugacions`). Una forma AMB lectura no verbal només es
tradueix si spaCy diu verb (o participi); una forma SENSE, sempre, llevat
que spaCy diga nom propi (PROPN: "París", "Mano", "Camino" -- noms i
castellà que coincidixen amb formes verbals). Substituïx les llistes a mà
`SEMPRE_VERB_INVERS = {"sigui"}` i `EXCLUSIONS_HOMOGRAF_INVERS` (buida):
"sigui", "sapigueu", "disposo"... ja es tradueixen encara que spaCy els
etiquete NOUN.

Excepció per fitxer d'origen: les files de `verbos_diferentes_conjugados.json`
(verbs d'arrel distinta, signar->firmar, prémer->polsar, espatllar->
desbaratar; es reconeixen pel camp `infinitiu_cat`) sempre necessiten que
spaCy diga verb. Este fitxer no marca cap homògraf a `morfologies`, i un
error ahí canvia la paraula sencera ("els premis" -> "les polses", "els
signes" -> "les firmes", "l'espatlla" -> "desbarata"). Mesurat 22/10/2026:
amb la marca només per a `conjugaciones_general.json` el 151 baixava de
147 a 143 i gplsi de 1479 a 1470; amb esta excepció, 146 i 1479 (BOE
estricte 8857, +13 sobre la llista "sigui"). L'única pèrdua és una cita
llatina ("del llatí confinis... finis").

**"sigui" dins d'"o sigui" (13/10/2026, RC067)**: spaCy etiqueta "sigui"
com a NOUN (no VERB/AUX) quan funciona com a marcador discursiu ("o
sigui" = "és a dir") -- el mateix tipus d'error de tagger ja documentat a
`rules/val_cat/conjugacions_dict.py::SEMPRE_VERB`, pero aplicat ací en
sentit contrari. **Mentres investigava açò es va trobar un bug relacionat
en l'altra direcció**: `rules/val_cat/conjugacions_dict.py` tenia una
protecció que assumia que "o siga" era una locució CONGELADA (mai
canviava als dos dialectes) -- fals, l'únic cas real del benchmark
(RC067) mostra que és un parell dialectal normal ("o siga"/"o sigui").
Es va corregir amb una llista a mà (`SEMPRE_VERB_INVERS`), retirada el
22/10/2026: ara el resol la marca d'homògraf del diccionari (vore dalt).

**Elisió combinada** (cas real trobat al propi benchmark invertit,
RC032): "d'escalfar-nos" (català, UN sol token amb prefix elidit "d'" I
sufix enclític "-nos" alhora) ha de tornar "de calfar-nos" (valencià,
"calfar" torna a ser consonant inicial -- cal DESFER l'elisió, igual que
`aplica_amb_prefix_elidit` ja sap fer, mes re-enganxar el sufix després).
Este és el PRIMER cas real d'esta capa que combina prefix I sufix a la
vegada -- `rules/val_cat/conjugacions_dict.py` (val->cat) mai ho necessitava
perquè el valencià d'entrada mai porta "d'" davant d'un verb consonàntic.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import (
    Token,
    aplica_amb_prefix_elidit,
    corregeix_article_abans,
    corregeix_contraccio_al_abans,
    corregeix_elisio_de_abans,
    preserva_majuscula,
    separa_prefix_elidit,
    separa_sufix_elidit,
)

DEFAULT_CONJUGACIONS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "conjugacions_dialectals.json"
)

# Codis de `morfologia` que NO són d'una forma verbal: les categories del
# lèxic ("n", "adj", "adv", "prn", "ij"...) i els prefixos (":mini<adj").
# "vbmod"/"vbhaver"/":haver<vaux" són verbs (modals i auxiliars).
_CATEGORIES_NO_VERBALS = {"n", "adj", "adv", "prn", "ij", "pr", "num", "det", "cnj"}


def _es_lectura_no_verbal(codi: str) -> bool:
    return codi in _CATEGORIES_NO_VERBALS or codi.endswith(("<n", "<adj"))


def carrega_formes_arrel_distinta(path: Path = DEFAULT_CONJUGACIONS_PATH) -> frozenset[str]:
    """Formes catalanes de les files de `verbos_diferentes_conjugados.json`
    (camp `infinitiu_cat`), que sempre passen pel filtre POS (vore
    docstring del mòdul).

    >>> a = carrega_formes_arrel_distinta()
    >>> sorted(w for w in ("premis", "signes", "espatlla", "sigui", "ofereixi") if w in a)
    ['espatlla', 'premis', 'signes']
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    return frozenset(
        (entrada.get("catalan") or "").strip().lower()
        for entrada in dades.get("entradas", [])
        if "infinitiu_cat" in entrada
    )


def carrega_homografs_conjugacions(path: Path = DEFAULT_CONJUGACIONS_PATH) -> frozenset[str]:
    """Formes catalanes que el diccionari de conjugacions marca també amb
    una lectura no verbal dins de `morfologia`.

    >>> h = carrega_homografs_conjugacions()
    >>> sorted(w for w in ("estat", "través", "obres", "moro", "sigui", "hagi", "pugui") if w in h)
    ['estat', 'moro', 'obres', 'través']
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    homografs: set[str] = set()
    for entrada in dades.get("entradas", []):
        # `morfologia` (conjugaciones_general.json) o `morfologies`
        # (verbos_diferentes_conjugados.json, sempre llista de llistes).
        morfologia = entrada.get("morfologia") or entrada.get("morfologies") or []
        lectures = morfologia if morfologia and isinstance(morfologia[0], list) else [morfologia]
        if any(lectura and _es_lectura_no_verbal(lectura[0]) for lectura in lectures):
            homografs.add((entrada.get("catalan") or "").strip().lower())
    return frozenset(homografs)


def carrega_conjugacions_invers(path: Path = DEFAULT_CONJUGACIONS_PATH) -> dict[str, str]:
    """Llig el mateix JSON que `rules/val_cat/conjugacions_dict.py`, pero
    construïx `{forma_catalana_en_minuscules: forma_valenciana}`,
    descartant les formes catalanes amb mes d'un candidat valencià real
    (calculat directament, vore docstring del mòdul).

    >>> lookup = carrega_conjugacions_invers()
    >>> lookup["ofereixi"]
    'oferisca'
    >>> lookup["treure"]
    'traure'
    >>> lookup["creuin"]
    'creuen'

    REGLA DE LA CANÒNICA també a les conjugacions (21/10/2026, decisió de
    l'usuari): si una forma catalana té diversos candidats, es descarten
    els marcats `canonica: false`. "sofreixin" tenia dos candidats,
    "patisquen" (proveïdor, `verbos_diferentes_conjugados.json`) i
    "sofrisquen" (fila LIMPIO_864, nostra, ara `canonica: false`); guanya
    la preferència del proveïdor. La fila nostra es queda per a val->cat
    ("sofrisquen" -> "sofreixin"):

    >>> lookup["sofreixin"]
    'patisquen'

    Una forma amb diversos candidats SENSE cap `canonica: false` es
    continua excloent (preferix fals negatiu):

    >>> "busqueu" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    candidats: dict[str, set[str]] = {}
    admesos: dict[str, set[str]] = {}  # candidats d'alguna fila que NO és `canonica: false`
    for entrada in dades.get("entradas", []):
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if not valenciano or not catalan:
            continue
        candidats.setdefault(catalan, set()).add(valenciano)
        if entrada.get("canonica") is not False:
            admesos.setdefault(catalan, set()).add(valenciano)
    lookup: dict[str, str] = {}
    for cat, vals in candidats.items():
        if len(vals) > 1 and admesos.get(cat):
            vals = vals & admesos[cat]
        if len(vals) == 1:
            lookup[cat] = next(iter(vals))
    return lookup


def _descompon(surface: str) -> list[tuple[str | None, str, str | None]]:
    """Totes les maneres plausibles de descompondre `surface` en
    (prefix_elidit, arrel, sufix_enclitic), de mes a menys especifica --
    `ConjugacionsDictInversRule.apply()` prova cada una fins trobar una
    arrel coneguda al diccionari. Inclou el cas COMBINAT (prefix I sufix
    alhora, vore docstring del mòdul).

    >>> _descompon("escalfar")
    [(None, 'escalfar', None)]
    >>> _descompon("d'escalfar")
    [(None, "d'escalfar", None), ("d'", 'escalfar', None)]
    >>> _descompon("escalfar-nos")
    [(None, 'escalfar-nos', None), (None, 'escalfar', '-nos')]
    >>> _descompon("d'escalfar-nos")
    [(None, "d'escalfar-nos", None), (None, "d'escalfar", '-nos'), ("d'", 'escalfar', '-nos')]
    """
    opcions: list[tuple[str | None, str, str | None]] = [(None, surface, None)]
    sufix_resta = separa_sufix_elidit(surface)
    if sufix_resta is not None:
        arrel_amb_prefix, sufix = sufix_resta
        opcions.append((None, arrel_amb_prefix, sufix))
        prefix_resta = separa_prefix_elidit(arrel_amb_prefix)
        if prefix_resta is not None:
            prefix, arrel = prefix_resta
            opcions.append((prefix, arrel, sufix))
    else:
        prefix_resta = separa_prefix_elidit(surface)
        if prefix_resta is not None:
            prefix, arrel = prefix_resta
            opcions.append((prefix, arrel, None))
    return opcions


class ConjugacionsDictInversRule:
    """Substitueix formes verbals catalanes conegudes per la seua forma
    valenciana (vore docstring del mòdul). Mai toca un token ja traduït
    ni un possible nom propi.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Els vaig ofereixi ajuda.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('ofereixi', 'oferisca')]

    El mode ja ve resolt pel català d'entrada -- "creuin" (subjuntiu) es
    tradueix a "creuen", i "creuen" (indicatiu) ja és idèntic als dos
    dialectes, així que no té entrada al diccionari i es queda sense
    tocar (no fa falta EXCLOURE'L a proposit, com calia fer en sentit
    contrari amb `es_risc_mode_3a_plural`):

    >>> from .. import detokenize
    >>> toks = tokenize("Vull que creuin aixo, encara que molts ja creuen aixo.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> detokenize(toks)
    'Vull que creuen aixo, encara que molts ja creuen aixo.'

    Formes amb mes d'un candidat valencià real no es toquen (sinònims que
    convergixen en català, vore docstring del mòdul), llevat que les dades
    marquen la no preferida amb `canonica: false` (21/10/2026): "sofreixin"
    tenia "patisquen" (proveïdor) i "sofrisquen" (fila nostra, no
    canònica), i guanya la del proveïdor. "busqueu" (cercau/cerqueu, sense
    cap marca) es continua sense tocar:

    >>> from .. import pos_tagger
    >>> toks = tokenize("Vull que sofreixin poc i que busqueu la clau.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)  # "sofreixin" és d'arrel distinta: cal spaCy
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('sofreixin', 'patisquen')]

    Prefix elidit sol ("s'ofereixi" -> "s'oferisca"):

    >>> toks = tokenize("Vull que s'ofereixi ajuda.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("s'ofereixi", "s'oferisca")]

    Sufix enclític sol ("treure'n" -> "traure'n"):

    >>> toks = tokenize("Per a treure'n algun profit.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("treure'n", "traure'n")]

    Filtre POS (vore docstring del mòdul, "Correcció important 08/10/2026"):
    "moro" dins "blat de moro" és NOM, no el verb "morir" -- sense spaCy
    es traduiria mal a "muir":

    >>> from .. import pos_tagger
    >>> toks = tokenize("El blat de moro és bo.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Participi usat com a adjectiu (21/10/2026, RC107): spaCy etiqueta
    "ofertes" com a ADJ en "les informacions ofertes", pero amb
    `VerbForm=Part`; el filtre el deixa passar. Mesurat: benchmark de 151
    +1 (RC107), BOE +5 frases exactes amb 41 canvis, 37 confirmats per la
    referència ("establert" -> "establit", "establertes" -> "establides"):

    >>> toks = tokenize("Les condicions establertes per la llei.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in ConjugacionsDictInversRule().apply(toks) if t.is_translated]
    [('establertes', 'establides')]

    Només quan spaCy marca el participi. Amb `ca_core_news_md` (des del
    22/10/2026) "ofertes" en la frase de RC107 ja ix ADJ sense `VerbForm` i
    no es toca (fals negatiu acceptat; amb `sm` sí que es traduïa):

    >>> toks = tokenize("Les informacions ofertes a través d'aquest mitjà tenen caràcter il·lustratiu.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in ConjugacionsDictInversRule().apply(toks) if t.is_translated]
    []

    "sigui" (RC067) no és homògraf al diccionari: es tradueix encara que
    spaCy l'etiquete NOUN. "l'Estat" i "través" sí que ho són (nom) i no
    es toquen; un nom propi que coincidix amb una forma verbal tampoc:

    >>> toks = tokenize("el recompte, o sigui, el 29 de febrer.")
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.pos, t.translated) for t in ConjugacionsDictInversRule().apply(toks) if t.surface == "sigui"]
    [('sigui', 'NOUN', 'siga')]
    >>> toks = tokenize("Ho paga l'Estat, a través de la seua delegació a París.")
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in ConjugacionsDictInversRule().apply(toks) if t.is_translated]
    []

    Verbs d'arrel distinta: només si spaCy diu verb ("premis" nom es queda):

    >>> toks = tokenize("Els premis i els signes. Vull que sofreixin poc.")
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in ConjugacionsDictInversRule().apply(toks) if t.is_translated]
    [('sofreixin', 'patisquen')]

    Prefix I sufix alhora -- el cas real del benchmark invertit (RC032):
    "escalfar" (vocal inicial en català) torna "calfar" (consonant
    inicial en valencià), així que l'elisió "d'" ja no té sentit i es
    desfà, igual que fa `aplica_amb_prefix_elidit` per a un sol prefix,
    mes el sufix re-enganxat després:

    >>> from .. import detokenize
    >>> toks = tokenize("La manera d'escalfar-nos.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = ConjugacionsDictInversRule().apply(toks)
    >>> detokenize(toks)
    'La manera de calfar-nos.'
    """

    def __init__(self, path: Path = DEFAULT_CONJUGACIONS_PATH) -> None:
        self._lookup = carrega_conjugacions_invers(path)
        # Formes que només es tradueixen si spaCy diu verb: homògrafs marcats
        # al diccionari + totes les de verbs d'arrel distinta.
        self._amb_filtre_pos = carrega_homografs_conjugacions(path) | carrega_formes_arrel_distinta(path)

    def _pos_admet(self, tok: Token, arrel: str) -> bool:
        """Vore "Homògrafs segons el diccionari" al docstring del mòdul."""
        if arrel.lower() in self._amb_filtre_pos:
            # Participi usat com a adjectiu ("les condicions establertes"):
            # spaCy l'etiqueta ADJ amb VerbForm=Part (21/10/2026).
            es_participi = tok.pos == "ADJ" and tok.verb_form == "Part"
            return tok.pos in ("VERB", "AUX") or es_participi
        return tok.pos != "PROPN"

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            for prefix, arrel, sufix in _descompon(tok.surface):
                forma = self._lookup.get(arrel.lower())
                if forma is None:
                    continue
                if not self._pos_admet(tok, arrel):
                    break
                if prefix is None:
                    tok.translated = preserva_majuscula(arrel, forma) + (sufix or "")
                    corregeix_contraccio_al_abans(tokens, i)
                    corregeix_article_abans(tokens, i)
                    corregeix_elisio_de_abans(tokens, i)  # "de sortir" -> "d'eixir"
                else:
                    aplica_amb_prefix_elidit(tokens, i, prefix, arrel, forma)
                    if sufix:
                        tok.translated += sufix
                tok.is_translated = True
                break
        return tokens
