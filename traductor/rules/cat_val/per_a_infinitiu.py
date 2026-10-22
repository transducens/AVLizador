"""
cat_val/per_a_infinitiu.py -- Regla C2 de la guia de traducció dialectal
(`pipeline/02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md`):
"per" + infinitiu (català) -> "per a" + infinitiu (valencià). Afegida el
21/10/2026.

EVIDÈNCIA (mesurada als corpus oficials, vore
`pipeline/02_regles_dialectals/docs_gramatica/mesura_guia_corpus_oficials.py`
i `documentacio/hoja_de_ruta_traductor_invers.md`):

- AVL: davant d'infinitiu, "per a" el 91,8% de les vegades (n=5.994).
- BOE valencià: 94,7% (n=5.208).
- BOE alineat: quan el català diu "per" + infinitiu, el valencià diu
  "per a" el 96,7% de les vegades (n=5.314, sense reformulacions).
- Excepció: "per haver" + participi (infinitiu compost, valor causal:
  "per haver estat condemnat") es queda "per" el 100% (n=29).

Sense llistes de verbs: l'infinitiu el reconeix spaCy (`Token.verb_form`,
"Inf"), que coneix bé el català d'entrada. Límit conegut (~3%): verbs que
regixen "per" ("optar per mantenir", "caracteritzar-se per ser") o
causals sense "haver" -- distingir-los demana entendre la frase.

Val->cat: la inversa ("per a" -> "per") NO és dialectal sinó d'estil: el
català admet "per" i "per a" davant d'infinitiu (el BOE escriu "per", el
benchmark de 151 "per a"). Si s'activa algun dia, ha de ser una opció de
registre, no una regla per defecte.
"""

from __future__ import annotations

from .. import Token, preserva_majuscula, separa_prefix_elidit, separa_sufix_elidit


def _seguent_paraula(tokens: list[Token], index: int) -> Token | None:
    for tok in tokens[index + 1 :]:
        if tok.surface.isspace():
            continue
        return tok if tok.surface[:1].isalpha() else None
    return None


def _arrel(surface: str) -> str:
    """La paraula sense prefix elidit ni pronom enclític ("haver-hi" -> "haver")."""
    sufix_resta = separa_sufix_elidit(surface)
    paraula = sufix_resta[0] if sufix_resta else surface
    prefix_resta = separa_prefix_elidit(paraula)
    return (prefix_resta[1] if prefix_resta else paraula).lower()


class PerAInfinitiuInversRule:
    """Convertix "per" en "per a" davant d'infinitiu (vore docstring del
    mòdul). Mai toca un "per" ja traduït ni el que ja va seguit de "a".

    >>> from .. import tokenize, marca_noms_propis, detokenize, pos_tagger
    >>> def prova(text):
    ...     toks = tokenize(text)
    ...     marca_noms_propis(toks)
    ...     pos_tagger.etiqueta(toks)
    ...     return detokenize(PerAInfinitiuInversRule().apply(toks))
    >>> prova("Disposen de competència per subscriure acords.")
    'Disposen de competència per a subscriure acords.'
    >>> prova("Per accedir-hi cal una clau.")
    'Per a accedir-hi cal una clau.'

    "per haver" (causal) i "per" davant de nom no es toquen, ni "per a" ja
    present:

    >>> prova("Va ser condemnat per haver mentit.")
    'Va ser condemnat per haver mentit.'
    >>> prova("Ho va fer per la família.")
    'Ho va fer per la família.'
    >>> prova("Serveix per a guardar roba.")
    'Serveix per a guardar roba.'
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            if tok.surface.lower() != "per":
                continue
            seguent = _seguent_paraula(tokens, i)
            if seguent is None or seguent.verb_form != "Inf":
                continue
            if _arrel(seguent.surface) == "haver":
                continue
            tok.translated = preserva_majuscula(tok.surface, "per a")
            tok.is_translated = True
        return tokens
