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
catalanes DINS del mateix fitxer font de Mauricio (aixo es el que marca
`problematica: true`, p.ex. "base"/"entre"/"centre"). Els 5 casos de dalt
NOMES tenen UNA entrada cadascun al seu fitxer font (el verb rar nomes es
conjuga una vegada per a eixa persona), aixi que mai es marquen
`problematica` -- la col·lisio es amb una paraula d'un fitxer QUE NI TAN
SOLS EXISTIX, perque els lexicons de Mauricio son DIFERENCIALS (nomes
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
diagnostica útil, vore `traça_verbs_fallats.py` a 03_seleccio_de_model/)
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

from . import Token, separa_prefix_elidit

_NLP = None
_CARREGAT = False


def _carrega_spacy():
    """Carrega `ca_core_news_sm` una sola vegada per procés. Si `spacy` no
    esta instal·lat o el model no esta descarregat, torna `None` en
    silenci (vore docstring del modul -- dependencia opcional)."""
    global _NLP, _CARREGAT
    if _CARREGAT:
        return _NLP
    _CARREGAT = True
    try:
        import spacy

        _NLP = spacy.load("ca_core_news_sm")
    except Exception:
        _NLP = None
    return _NLP


def etiqueta(tokens: list[Token]) -> None:
    """Omple `tok.pos` (etiqueta POS universal d'spaCy: "VERB", "NOUN",
    "ADP"...) per a cada token-paraula de `tokens`, mutant-los en lloc.

    Es crida ABANS de qualsevol regla (per aixo fa falta `tok.surface`, no
    `tok.translated` -- en eixe moment son identics). Cerca cada paraula
    pel seu TEXT dins del document d'spaCy (mateix mecanisme ja validat a
    `08_traduccio_corpus/postprocessat_llm/benchmark_integrat.py`,
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
        buscada_min = buscada.lower()
        for dt in doc:
            if dt.text.lower() == buscada_min:
                tok.pos = dt.pos_
                mood = dt.morph.get("Mood")
                tok.mood = mood[0] if mood else ""
                gender = dt.morph.get("Gender")
                tok.gender = gender[0] if gender else ""
                break


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
