"""
pos_tagger.py -- Etiquetatge POS OPCIONAL (spaCy), cridat per `engine.py`
just despres de `marca_noms_propis()` i abans de les 9 capes de regles.

Per que fa falta (07/10/2026): `ConjugacionsDictRule` fa un lookup exacte
forma_valenciana -> forma_catalana sobre `conjugacions_dialectals.json`.
Eixe fitxer ve de conjugar milers de verbs (`conjugaciones_nuevo.json` en
sol aporta 5.465), i amb tants verbs es inevitable que una forma conjugada
RARA coincidisca per casualitat amb una paraula MOLT mes freqüent d'una
atra categoria gramatical. Casos reals trobats al benchmark de 150 frases:

    "persones" (substantiu, "people")   -> lookup diu "personis" (verb "personar")
    "pares"    (substantiu, "parents")  -> lookup diu "paris"    (verb "parar")
    "projectes"(substantiu, "projects") -> lookup diu "projectis"(verb "projectar")
    "pobles"   (substantiu, "peoples")  -> lookup diu "poblis"   (verb "poblar")
    "plomes"   (substantiu, "feathers substantiu")  -> lookup diu "plomis" (verb "plomar")

`_marca_ambigues_dins_del_mateix_fitxer` (sync_data.py) NOMES detecta
col·lisions INTERNES: la mateixa paraula valenciana amb >=2 traduccions
catalanes DINS del mateix fitxer font del proveïdor (aixo es el que marca
`problematica: true`, p.ex. "base"/"entre"/"centre"). Els 5 casos de dalt
NOMES tenen UNA entrada cadascun al seu fitxer font (el verb rar nomes es
conjuga una vegada per a eixa persona), aixi que mai es marquen
`problematica` -- la col·lisio es amb una paraula d'un fitxer QUE NI TAN
SOLS EXISTIX, perque els lexicons del proveïdor son DIFERENCIALS (nomes
llisten parelles que canvien d'un dialecte a l'atre; "persones", "pobles",
"projectes"... son identiques als dos dialectes, per aixo cap fitxer les
llista). No hi ha cap llista "de l'atra categoria gramatical" contra la
que comparar -- l'unica senyal possible es el CONTEXT de la frase, i aixo
es justament el que fa un POS tagger.

Verificat amb el benchmark real (07/10/2026, ca_core_news_sm): spaCy
etiqueta correctament les 5 paraules de dalt com a NOUN en les seues
frases reals del benchmark, i NO trenca cap cas ja conegut de
`ConjugacionsDictRule` (oferisca/tinguen -> VERB, germanes -> NOUN ja
protegida per `EXCLUSIONS_HOMOGRAF`).

DEPENDENCIA OPCIONAL de veres (vore el camp `Token.pos` a `rules/__init__.py`,
que ja existia per a aixo mateix): si `spacy` o el model `ca_core_news_sm`
no estan instal·lats, `etiqueta()` no fa res -- cap token rep `pos`, i
`ConjugacionsDictRule` cau exactament al comportament d'abans (aplica el
lookup sense cap filtre). El pipeline de `traductor/` mai falla ni
requerix spaCy per a funcionar; nomes guanya esta protecció extra quan
spaCy esta disponible.

Segon problema, mateixa arrel, trobat el 08/10/2026 -- col·lisió
d'INDICATIU/SUBJUNTIU en 3a persona del plural: en valencià, el present
d'indicatiu i el present de subjuntiu de la 3a plural es poden escriure
IGUAL ("ells creuen" indicatiu / "que ells creuen" subjuntiu), mentre que
en català sempre es distinguixen ("creuen" / "creuin"). Com l'indicatiu
no canvia, els lexicons diferencials nomes llisten la fila de subjuntiu
-- exactament el mateix mecanisme que el problema de dalt, pero afecta a
**9.220 formes (el 20% de tota la taula)**, no 5 paraules soltes.

`etiqueta()` TAMBE omple `Token.mood` (el tret `Mood` d'spaCy: "Ind",
"Sub"...) per si podia servir ací. **Provat i DESCARTAT el mateix
08/10/2026**: la idea era "si spaCy diu Ind, no apliques la fila de
subjuntiu". Pero spaCy diu "Ind" quasi SEMPRE per a estes formes, siga
quina siga la veritat -- no nomes en els 20 casos on de veres tocava
indicatiu, sino TAMBE en casos on hui la traducció a subjuntiu ja es
CORRECTA i ja funciona ("puguen"→"puguin", "siguen"→"siguin",
"tinguen"→"tinguin", verificat amb el benchmark real i amb doctests ja
existents). És a dir, `Mood` no distingix res ací -- es un valor per
defecte quan la forma no es reconeguda de l'entrenament (`ca_core_news_sm`
es català central), no una classificació real. Fer-ho servir per a
bloquejar hauria introduit regressions noves (trencar "puguen"/"siguen"
que hui van bé) a canvi d'arreglar els 24 casos coneguts -- NO es fa
servir per a res de moment. `Token.mood` es queda calculat (es informació
diagnostica útil, vore `traça_verbs_fallats.py` a pipeline/03_seleccio_de_model/)
pero cap regla el consulta hui. Si en el futur es decidix atacar este
problema, la solució haurà de ser una atra (possiblement estendre
`postprocessat_llm/` a esta persona tambe, amb LLM, no amb spaCy sol).

Tercer us, mateixa capa -- `Token.gender` (afegit 08/10/2026, vore
`concordanca_dos_dues.py`): el tret `Gender` d'spaCy sobre NOUN/ADJ per a
la concordanca "dos"/"dues" sense marcador explicit davant ("dos entitats"
-> "dues entitats"). Provat sobre 5 frases reals del benchmark amb
col·lisio coneguda: 6 de 7 paraules rellevants
(entitats/xifres/llengües/terceres/parts/geminada) be etiquetades Fem; UNA
(`consonants`) mal etiquetada Masc (hauria de ser Fem, "la consonant"). A
diferencia de `Mood`, este tret SI s'usa -- pero nomes com a senyal
POSITIVA (si diu Fem, corregix; si diu Masc/buit/no disponible, no toca
res), mateixa filosofia de "preferix fals negatiu" que la resta del
projecte.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache

from . import Token, separa_prefix_elidit, separa_sufix_elidit

_NLP = None
_CARREGAT = False


# Models en orde de preferència (22/10/2026): `md` encerta més el gènere i
# la morfologia ("gastos" masculí, subjuntius), a la mateixa velocitat que
# `sm` (264 frente a 257 frases/s, cat->val, 1 nucli) pero amb ~190 MB més
# de RAM (696 frente a 503 MB el procés sencer). Si `md` no està
# instal·lat, es fa servir `sm`.
MODELS_SPACY = ("ca_core_news_md", "ca_core_news_sm")


def _carrega_spacy():
    """Carrega el primer model de `MODELS_SPACY` que estiga instal·lat,
    una sola vegada per procés. Si `spacy` no esta instal·lat o no hi ha
    cap model, torna `None` en silenci (vore docstring del modul --
    dependencia opcional)."""
    global _NLP, _CARREGAT
    if _CARREGAT:
        return _NLP
    _CARREGAT = True
    _NLP = None
    try:
        import spacy
    except Exception:
        return None
    for model in MODELS_SPACY:
        try:
            # Sense "parser" ni "ner": cap regla usa dependencies (`.dep_`,
            # `.head`), entitats (`.ents`) ni oracions (`.sents`), nomes
            # POS, morfologia i lema. Mesurat 21/10/2026: 79->147 frases/s
            # en CPU i traduccions identiques a les 4.112 frases de
            # 151+gplsi+BOE.
            _NLP = spacy.load(model, exclude=["parser", "ner"])
            break
        except Exception:
            continue
    return _NLP


def etiqueta(tokens: list[Token]) -> None:
    """Omple `tok.pos` (etiqueta POS universal d'spaCy: "VERB", "NOUN",
    "ADP"...) per a cada token-paraula de `tokens`, mutant-los en lloc.

    Es crida ABANS de qualsevol regla (per aixo fa falta `tok.surface`, no
    `tok.translated` -- en eixe moment son identics). Cerca cada paraula
    pel seu TEXT dins del document d'spaCy (mateix mecanisme ja validat a
    `pipeline/08_traduccio_corpus/postprocessat_llm/benchmark_integrat.py`,
    `pos_de_paraula()`): primera coincidencia insensible a majuscules,
    sense alinear índexs -- la tokenitzacio d'spaCy no coincidix sempre
    amb la nostra (p.ex. "s'oferisca" es UN token nostre pero DOS per a
    spaCy), aixi que s'intenta primer amb la paraula sencera i, si no es
    troba, amb la part DESPRES d'un prefix elidit ("s'oferisca" ->
    "oferisca").

    Si spaCy no esta disponible, no fa res -- tots els tokens es queden
    amb `pos == ""` (el valor per defecte de `Token`).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Hi havia moltes persones al carrer.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.pos) for t in toks if t.surface == "persones"]
    [('persones', 'NOUN')]

    >>> toks = tokenize("Vull que els oferisca ajuda encara que tinguen pressa.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.pos) for t in toks if t.surface in ("oferisca", "tinguen")]
    [('oferisca', 'VERB'), ('tinguen', 'VERB')]

    Prefix elidit -- s'etiqueta la PARAULA, no el token sencer amb l'apostrof:

    >>> toks = tokenize("Vull que s'oferisca ajuda.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.pos) for t in toks if t.surface == "s'oferisca"]
    [("s'oferisca", 'VERB')]

    `mood` (afegit 08/10/2026, vore docstring del mòdul -- col·lisió
    d'indicatiu/subjuntiu en 3a plural): "creuen" ací es present
    d'indicatiu de "creure" ("creure" -- Mood=Ind), encara que
    `conjugacions_dialectals.json` nomes té la conjugació de subjuntiu
    d'un verb DISTINT ("creuar"):

    >>> toks = tokenize("Les dues terceres parts creuen que cal fer-ho.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.mood) for t in toks if t.surface == "creuen"]
    [('creuen', 'Ind')]

    `gender` (afegit 08/10/2026, vore docstring del mòdul i
    `concordanca_dos_dues.py`): el tret `Gender` d'spaCy per a NOUN/ADJ:

    >>> toks = tokenize("Hem creat dos entitats noves.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.gender) for t in toks if t.surface == "entitats"]
    [('entitats', 'Fem')]

    `lemma` (afegit 20/10/2026, vore `cat_val/incoatius.py`):

    >>> toks = tokenize("Aquest servei serveix per a tot.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.lemma) for t in toks if t.surface == "serveix"]
    [('serveix', 'servir')]

    `verb_form` (afegit 21/10/2026, vore `cat_val/per_a_infinitiu.py`), i
    verb amb pronom enclític enganxat: spaCy el partix en dos ("fer", "-ho")
    i abans no es trobava; ara es busca la part sense el pronom:

    >>> toks = tokenize("Cal temps per fer-ho bé.")
    >>> marca_noms_propis(toks)
    >>> etiqueta(toks)
    >>> [(t.surface, t.pos, t.verb_form) for t in toks if t.surface == "fer-ho"]
    [('fer-ho', 'VERB', 'Inf')]
    """
    nlp = _carrega_spacy()
    if nlp is None:
        return
    text = "".join(t.surface for t in tokens)
    doc = nlp(text)
    for tok in tokens:
        if not tok.surface[:1].isalpha():
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        buscada = prefix_resta[1] if prefix_resta else tok.surface
        candidates = [buscada.lower()]
        sufix_resta = separa_sufix_elidit(buscada)
        if sufix_resta is not None:
            candidates.append(sufix_resta[0].lower())
        dt = next(
            (d for buscada_min in candidates for d in doc if d.text.lower() == buscada_min),
            None,
        )
        if dt is None:
            continue
        tok.pos = dt.pos_
        mood = dt.morph.get("Mood")
        tok.mood = mood[0] if mood else ""
        gender = dt.morph.get("Gender")
        tok.gender = gender[0] if gender else ""
        verb_form = dt.morph.get("VerbForm")
        tok.verb_form = verb_form[0] if verb_form else ""
        tok.lemma = dt.lemma_.lower()


_GENERE_CURT = {"Masc": "m", "Fem": "f"}


@lru_cache(maxsize=4096)
def genere_de(paraula: str) -> str:
    """Gènere ("m"/"f") d'un nom segons spaCy, o "" si no és segur.
    Substituïx `canvi_genere_lexic_avl.json` (22/10/2026, llista feta a mà
    amb una sola paraula): ni el lèxic del proveïdor ni cap altra font
    porta gènere.

    La paraula soltada sola no val (mesurat sobre els noms del lèxic:
    "xiquet" eixia femení), així que s'etiqueta dins de dos frases, una
    amb article masculí i una amb femení ("Veig el X ara." / "Veig la X
    ara.", o "els"/"les" si acaba en -s), i només es dona per bo si spaCy
    diu el mateix gènere a les dos: si es deixa portar per l'article, no
    en sap prou.

    >>> genere_de("vivenda"), genere_de("gastos"), genere_de("granera")
    ('f', 'm', 'f')

    Límits mesurats (22/10/2026, `ca_core_news_md`): de 27 noms de control,
    15 encerts, 2 errors (variants gràfiques, que no es consulten mai: vore
    `_es_variant_grafica`) i 10 sense resposta. Sense resposta, el
    determinant no es toca ("dacsa", "gasto", "bresquilla"). Amb `sm`
    eren 12 encerts i 7 errors ("dacsa" eixia masculí):

    >>> genere_de("dacsa"), genere_de("gasto"), genere_de("bresquilla")
    ('', '', '')
    """
    nlp = _carrega_spacy()
    if nlp is None or not paraula:
        return ""
    articles = ("els", "les") if paraula.lower().endswith("s") else ("el", "la")
    generes = set()
    for article in articles:
        doc = nlp(f"Veig {article} {paraula} ara.")
        trobat = next((t for t in doc if t.text.lower() == paraula.lower()), None)
        if trobat is None:
            return ""
        gender = trobat.morph.get("Gender")
        generes.add(gender[0] if gender else "")
    if len(generes) != 1:
        return ""
    return _GENERE_CURT.get(generes.pop(), "")


def _es_variant_grafica(a: str, b: str) -> bool:
    """Dos formes quasi iguals ("ametlla"/"ametla", "dipòsit"/"depòsit")
    són la mateixa paraula escrita diferent: mai canvien de gènere.
    Mesurat 22/10/2026 sobre els noms del lèxic: entre estos parells
    (ràtio >= 0,8) spaCy veia 11 canvis de gènere i només un era real
    ("joguines"/"joguets", que es perd)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.8


def genere_tras_substitucio(tok: Token, forma: str, original: str = "") -> tuple[str, bool]:
    """Per a un nom `tok` que es tradueix per `forma`: torna `(gènere de
    la forma nova, si ha canviat respecte de l'original)`. El gènere
    original és el que spaCy dona a `tok` dins de la frase (etiquetat
    abans de les regles); el nou, `genere_de(forma)`. Sense dades segures
    de les dos bandes, no hi ha canvi. `original` és la paraula sense
    prefix elidit, si en portava ("l'escombra" -> "escombra").

    >>> t = Token("despeses", "despeses", pos="NOUN", gender="Fem")
    >>> genere_tras_substitucio(t, "gastos")
    ('m', True)
    >>> t = Token("dipòsit", "dipòsit", pos="NOUN", gender="Masc")
    >>> genere_tras_substitucio(t, "depòsit")
    ('m', False)
    """
    if tok.pos not in ("NOUN", "PROPN"):
        return "", False
    genere_original = _GENERE_CURT.get(tok.gender, "")
    if _es_variant_grafica(original or tok.surface, forma):
        return genere_original, False
    nou = genere_de(forma.lower().split()[0])  # "blat de moro" -> "blat"
    if not nou:
        return genere_original, False
    return nou, bool(genere_original) and nou != genere_original


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
