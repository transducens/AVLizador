"""
gentilicis.py -- Gentilicis de país/idioma amb sufix -és (occidental) ->
-ès (oriental): francés -> francès, anglés -> anglès... El mateix patró
també cobrix una vintena de noms comuns que no són gentilicis
(interés -> interès, imprés -> imprès...). Font:
final/02_reglas_dialectales/reglas_dialectales.md, secció 6.2 -- patró
MOLT productiu (300+ lemes confirmats a Apertium), per això s'implementa
com a regla de SUFIX general (qualsevol paraula acabada en "-és"), no com
a llista tancada -- a diferència dels ordinals (numerals.py), on la font
NO dona prou garantia per a generalitzar.

Excepció EXPLÍCITA i obligatòria (donada per la mateixa font): "és" (el
verb ser, 3a persona singular) i "més" (quantitat) mai canvien -- són
paraules gramaticals curtes que casualment acaben en la mateixa seqüència
de lletres, no formen part del patró.

Excepció trobada EMPÍRICAMENT (no ve de la font, que només en dona dos):
en córrer el motor sencer contra el benchmark real de 60 frases, "després"
(adverbi de temps) es convertia incorrectament en "desprès" -- ni
l'occidental ni l'oriental del benchmark canvien mai esta paraula (les
dos diuen "després"). La llista de dos excepcions de la font no és
exhaustiva; esta se n'ha afegit una tercera amb evidència directa, i és
esperable que n'aparega alguna més en ampliar les proves.
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

_EXCEPCIONS = {"és", "més", "després"}
_SUFIX_ES_RE = re.compile(r"és$", re.IGNORECASE)


class GentilicisRule:
    """Substitueix el sufix -és per -ès, excepte "és"/"més".

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("El meu amic francés parla anglés i és cortés.")
    >>> marca_noms_propis(toks)
    >>> toks = GentilicisRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('francés', 'francès'), ('anglés', 'anglès'), ('cortés', 'cortès')]

    "és" (verb) i "més" (quantitat) mai es toquen:

    >>> toks = tokenize("Hi ha més interés del que és normal.")
    >>> marca_noms_propis(toks)
    >>> toks = GentilicisRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('interés', 'interès')]

    "després" tampoc (fals positiu confirmat al benchmark real, vore
    docstring del mòdul):

    >>> toks = tokenize("Ho vam saber després de tot.")
    >>> marca_noms_propis(toks)
    >>> toks = GentilicisRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Plural en -és (com "comités", que NO és un gentilici però seguix el
    mateix patró de sufix -- vore lexic.py per a "comité" en singular,
    que no acaba en "-és" i per tant no el toca esta regla):

    >>> toks = tokenize("Els comités es van reunir.")
    >>> marca_noms_propis(toks)
    >>> toks = GentilicisRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('comités', 'comitès')]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            if minuscules in _EXCEPCIONS or not minuscules.endswith("és"):
                continue
            nova = _SUFIX_ES_RE.sub("ès", minuscules)
            tok.translated = preserva_majuscula(tok.surface, nova)
            tok.is_translated = True
        return tokens
