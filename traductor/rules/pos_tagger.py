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
                break


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
