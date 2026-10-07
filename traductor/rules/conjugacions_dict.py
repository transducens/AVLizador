"""
conjugacions_dict.py -- Capa 2 del pipeline (justa despres de lexic.py):
lookup exacte de formes verbals a `traductor/data/conjugacions_dialectals.json`,
que fusiona dos fonts de Mauricio (equip AVLizador): `conjugaciones_limpio.json`
(969 formes, 111 verbs, 29/09/2026) i `verbos_no_ambiguos.json` (261 formes
mes, 45 verbs FORA dels 111 originals, 30/09/2026, totes explicitament
marcades com a no ambigues). `verbos_no_ambiguos.json` va PRIMER en la
fusio (vore `traductor/sync_data.py`): 16 formes de "eixir" (isca/isquen/
isc/ixes...) apareixen a totes dos fitxers amb traduccio diferent ("ixi"
vs "surti"), i guanya "surti" per coherencia amb la decisio ja presa a
`lexic.py` (`eixir -> sortir`).

Com lexic.py, esta capa fa un LOOKUP exacte (forma valenciana -> forma
catalana), no una regla morfologica -- i per aixo va MOLT PRIMERENCA al
pipeline (posicio 2, abans de morfologia_verbal.py): quan una forma ja es
coneguda amb precisio (p.ex. "oferisca" -> "ofereixi", una alternanca
irregular que la regla de sufix de fase 6 mai tocaria perque acaba en "-a"
no en "-ix"), no te sentit deixar que una regla de sufix mes feble intente
endevinar-la despres. Les regles de morfologia_verbal.py (fase 1/2/6) ja
salten qualsevol token amb `is_translated = True`, aixi que esta capa i
aquelles no es xoquen mai -- esta capa nomes cobrix EL SUBCONJUNT dels 111
verbs de la font, la resta seguix depenent de les regles de sufix generals.

Exclusio deliberada -- formes "problematica" (65 de les 969): en valencia
hi ha verbs on la mateixa forma escrita servix per al present d'indicatiu
I al de subjuntiu ("abalance" = "jo abalanco" en indicatiu / "que jo
abalanci" en subjuntiu), mentre que en catala son formes diferents
("abalanco" / "abalanci"). Sense pos-tagging no hi ha manera fiable de
saber quin dels dos toca -- Mauricio mateix ho documenta com "hara falta
un mecanisme de desambiguacio". Esta capa, seguint el mateix criteri
conservador que la resta del projecte (preferir un fals negatiu -- deixar
la paraula sense traduir -- abans que un fals positiu), EXCLOU del lookup
qualsevol entrada marcada `problematica: true`. Es queden documentades al
JSON de dades per si en el futur s'afig eixe mecanisme de desambiguacio.

Excepcio real (bug trobat 30/09/2026): "siga" (verb "ser", subjuntiu) ja
ve net a les dades de Mauricio i es traduiria ací sense cap protecció --
pero "o siga" es una locucio fixa ("es a dir") que mai canvia als dos
dialectes (RC067, vore morfologia_verbal.py). Com esta capa va ABANS que
morfologia_verbal.py al pipeline, la proteccio original (nomes alla)
mai arribava a executar-se: "o siga" es traduia mal a "o sigui" des que
esta capa es va afegir. Corregit mirant la paraula anterior amb
`paraula_anterior_es` (rules/__init__.py).

Col·lisions homògraf verb/paraula comuna (05/10/2026, des que
`conjugaciones_nuevo.json` va afegir 5.465 verbs en compte dels 156
originals): amb tants verbs, és molt mes probable que una forma
conjugada RARA coincidisca per casualitat amb una paraula comuna d'una
altra categoria gramatical. Cas trobat: "germanes" (substantiu, "hermanas",
ultra-comú) és identica a la 2a persona del present de subjuntiu del verb
"germanar" ("que tu germanes"), una forma que ningú fa servir mai en eixe
sentit -- sense pos-tagging, `ConjugacionsDictRule` no pot distingir-les,
i sense esta exclusio traduiria "germanes" (el substantiu) a "germanis"
(el verb) sempre. `EXCLUSIONS_HOMOGRAF` és una llista CURADA a mà, afegida
cas a cas conforme es descobrixen.

Filtre POS general (07/10/2026, vore `pos_tagger.py`): `EXCLUSIONS_HOMOGRAF`
nomes cobrix "germanes" perque va caldre trobar-ho a mà revisant el
benchmark. El mateix problema és MOLT mes ampli -- "persones", "pares",
"projectes", "pobles", "plomes"... cada un amb una unica entrada al seu
fitxer font (per aixo `_marca_ambigues_dins_del_mateix_fitxer` mai els
marca `problematica`) que coincidix amb un substantiu ultra-comú que cap
lexicó llista (els lexicons de Mauricio son diferencials: no canvien entre
dialectes, per això no hi ha cap fitxer que els continga). Curar-los un a
un no escala (42.625 entrades sense esta proteccio, vore
`sync_data.py`). En compte d'una llista, `apply()` consulta ara
`tok.pos` (si `pos_tagger.etiqueta()` l'ha omplit -- dependencia opcional,
vore eixe modul): si spaCy diu que la paraula NO es un VERB (ni un AUX, vore
baix) en eixe context concret, no s'aplica el lookup, siga quina siga la
paraula. `EXCLUSIONS_HOMOGRAF` es queda com a xarxa de seguretat per a quan
spaCy no esta instal·lat (dependencia opcional, no obligatoria).

Bug real trobat i corregit (07/10/2026, primer intent d'esta mateixa capa):
acceptar NOMES "VERB" causava regressions reals al benchmark de 150 -- 11
frases que abans eixien EXACTES van deixar de ser-ho. Causa: spaCy fa
servir l'etiqueta universal "AUX" (no "VERB") per als verbs auxiliars/
copulatius ("ser", "haver", "estar" quan acompanyen un atre verb o
adjectiu), i precisament els verbs mes freqüents d'esta taula son formes
de "ser" ("sigut", "siga") i "haver" ("haja") -- "ha sigut" (AUX+AUX),
"que siga externa" (copula+adjectiu). Filtrar nomes per "VERB" bloquejava
EIXACTAMENT els casos mes importants. Corregit acceptant "VERB" i "AUX"
tots dos: 7 de les 11 regressions desapareixen, sense perdre cap millora.

Les 4 regressions restants ("vinga"/"traure" a l'inici de frase, "haja" en
mig de frase, "siga" davant d'un adjectiu) son un atre bug d'spaCy, no del
filtre: el model `ca_core_news_sm` esta entrenat en català central
(corpus AnCora) i mai ha vist estes formes EXCLUSIVAMENT valencianes
escrites aixina -- les etiqueta "PROPN" (nom propi, el "calaix de sastre"
d'spaCy per a paraules desconegudes) o, en el cas de "siga" davant
d'adjectiu, "ADJ". Son errors reals del tagger, confirmats revisant cada
frase (vore el benchmark de 150). Com NO son casos de col·lisio real (cap
d'estes 5 formes coincidix mai amb un substantiu/adjectiu d'un atre
sentit -- a diferencia de "persones"/"pobles"/etc., que SI col·lidixen),
es tracten com una llista tancada de SEGURETAT ("confia sempre en la
taula de conjugacions per a estes formes concretes, ignora el que diga
spaCy"), seguint el mateix criteri que `EXCLUSIONS_HOMOGRAF` pero en
sentit invers. `SEMPRE_VERB` es amplia nomes amb evidencia (revisant el
benchmark o el corpus), mai per endevinar.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import (
    Token,
    aplica_amb_prefix_elidit,
    paraula_anterior_es,
    preserva_majuscula,
    separa_prefix_elidit,
    separa_sufix_elidit,
)

DEFAULT_CONJUGACIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "conjugacions_dialectals.json"
)

# Vore docstring del modul: formes conjugades RARES que coincidixen per
# casualitat amb una paraula comuna d'una altra categoria gramatical.
EXCLUSIONS_HOMOGRAF = {"germanes"}

# Vore docstring del modul ("Les 4 regressions restants..."): formes
# verbals SENSE cap col·lisio coneguda que spaCy (ca_core_news_sm,
# entrenat en català central) etiqueta de manera no fiable com a "PROPN"
# o "ADJ" perque mai les ha vist en valencia -- es confia sempre en la
# taula per a estes, ignorant `tok.pos`.
SEMPRE_VERB = {"sigut", "siga", "haja", "vinga", "traure"}


def carrega_conjugacions(path: Path = DEFAULT_CONJUGACIONS_PATH) -> dict[str, str]:
    """Llig el JSON de conjugacions i el converteix en un diccionari pla
    `{forma_valenciana_en_minuscules: forma_catalana}`, descartant les
    entrades `problematica: true` i les de `EXCLUSIONS_HOMOGRAF` (vore
    docstring del modul).

    >>> lookup = carrega_conjugacions()
    >>> lookup["oferisca"]
    'ofereixi'
    >>> lookup["tinguen"]
    'tinguin'
    >>> lookup["traure"]
    'treure'
    >>> "abalance" in lookup
    False
    >>> "germanes" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades.get("entradas", []):
        if entrada.get("problematica"):
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip()
        if not valenciano or not catalan:
            continue
        if valenciano in EXCLUSIONS_HOMOGRAF:
            continue
        lookup.setdefault(valenciano, catalan)
    return lookup


class ConjugacionsDictRule:
    """Substitueix formes verbals valencianes conegudes per la seua forma
    catalana, segons `conjugacions_dialectals.json`. Mai toca un token ja
    traduit per una capa anterior (`is_translated`) ni un possible nom
    propi (`is_proper_noun`).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Els vaig oferisca ajuda encara que tinguen pressa.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('oferisca', 'ofereixi'), ('tinguen', 'tinguin')]

    Formes "problematica" (ambigues entre indicatiu i subjuntiu) no es
    toquen -- vore docstring del modul:

    >>> toks = tokenize("Jo abalance la pilota.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Forma enganxada a un prefix elidit ("s'", "l'"...), mateix mecanisme
    que `lexic.py` (vore `separa_prefix_elidit` a rules/__init__.py):

    >>> toks = tokenize("Vull que s'oferisca ajuda.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("s'oferisca", "s'ofereixi")]

    "o siga" (locució fixa, "és a dir") no és el verb "ser" en subjuntiu,
    encara que "siga" sí és una forma neta a les dades de Mauricio:

    >>> toks = tokenize("El recompte acaba hui, o siga, el 29 de febrer.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Però "siga" SÍ es tradueix quan és de veres el verb (no precedit de "o"):

    >>> toks = tokenize("Vull que siga possible.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('siga', 'sigui')]

    Filtre POS (07/10/2026, nomes actiu si spaCy esta instal·lat -- vore
    `pos_tagger.py`): "persones" té una entrada neta a les dades de
    Mauricio ("personis", del verb rar "personar"), però ací funciona com
    a substantiu -- `pos_tagger.etiqueta()` ho detecta ("NOUN") i esta capa
    no l'toca:

    >>> from .pos_tagger import etiqueta
    >>> toks = tokenize("Hi havia moltes persones al carrer.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    El mateix filtre NO bloqueja un verb de veres -- "oferisca"/"tinguen"
    seguixen traduint-se igual que sense POS (vore doctest de dalt):

    >>> toks = tokenize("Els vaig oferisca ajuda encara que tinguen pressa.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('oferisca', 'ofereixi'), ('tinguen', 'tinguin')]

    Paraula enganxada a un pronom feble enclític ("'n", "-li"...), mateix
    mecanisme que el prefix elidit pero pel costat contrari (07/10/2026,
    vore `separa_sufix_elidit` a rules/__init__.py -- cas real trobat al
    benchmark: "traure'n" no es traduia mai a "treure'n"):

    >>> toks = tokenize("Per a traure'n algun profit.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("traure'n", "treure'n")]
    """

    def __init__(self, path: Path = DEFAULT_CONJUGACIONS_PATH) -> None:
        self._lookup = carrega_conjugacions(path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            if minuscules == "siga" and paraula_anterior_es(tokens, i, "o"):
                continue
            if tok.pos and tok.pos not in ("VERB", "AUX") and minuscules not in SEMPRE_VERB:
                continue
            forma = self._lookup.get(minuscules)
            if forma is not None:
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is not None:
                prefix, resta = prefix_resta
                forma = self._lookup.get(resta.lower())
                if forma is not None:
                    aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma)
                    tok.is_translated = True
                continue
            sufix_resta = separa_sufix_elidit(tok.surface)
            if sufix_resta is not None:
                arrel, sufix = sufix_resta
                forma = self._lookup.get(arrel.lower())
                if forma is not None:
                    tok.translated = preserva_majuscula(arrel, forma) + sufix
                    tok.is_translated = True
        return tokens
