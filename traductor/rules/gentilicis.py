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

Excepcions trobades EMPÍRICAMENT (no vénen de la font, que només en dona
dos): en córrer el motor sencer contra els benchmarks reals:
  - "després" (adverbi de temps, benchmark de 60 frases): es convertia
    incorrectament en "desprès" -- ni l'occidental ni l'oriental canvien
    mai esta paraula.
  - "només", "procés", "congrés", "accés", "progrés", "través" (benchmark
    de 150 frases, 28/09/2026): la font només confirma el patró -és->-ès per als
    gentilicis/idiomes (secció 6.2, general, 300+ lemes) i per "una
    vintena" de noms comuns EXPLÍCITAMENT enumerats (interés, imprés,
    entremés, malentés, sobrepés, desinterés, contrapés) -- NO per a
    qualsevol substantiu acabat en -és. Estos 5 són substantius comuns
    fora d'eixa llista que el benchmark confirma que es queden EXACTAMENT
    igual als dos dialectes.
La llista de dos excepcions de la font no és exhaustiva per als noms
comuns; esta se n'ha ampliat amb evidència directa, i és esperable que
n'aparega alguna més en ampliar les proves (els gentilicis/idiomes en si
mateixos, en canvi, sí semblen seguir el patró de manera fiable).
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

_EXCEPCIONS = {"és", "més", "només", "després", "procés", "congrés", "accés", "progrés", "través"}
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

    "procés"/"congrés"/"accés"/"progrés"/"través" tampoc -- són substantius
    comuns que NO segueixen el patró (fals positiu confirmat al benchmark
    de 150 frases, vore docstring del mòdul):

    >>> toks = tokenize("El procés d'accés al congrés continua en progrés a través de tot, però només un poc.")
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
            # "d'accés"/"l'interés" arriben com un sol token (l'apòstrof és
            # part de la paraula, vore rules/__init__.py) -- cal comprovar
            # les excepcions sobre la part real de la paraula, no sobre el
            # token sencer amb el prefix elidit davant. El tokenitzador
            # accepta tant l'apòstrof recte (') com el tipogràfic (’, com
            # el que fa servir de veres el corpus real) -- cal partir per
            # qualsevol dels dos.
            paraula = re.split(r"['’]", minuscules)[-1]
            if paraula in _EXCEPCIONS or not paraula.endswith("és"):
                continue
            nova = _SUFIX_ES_RE.sub("ès", minuscules)
            tok.translated = preserva_majuscula(tok.surface, nova)
            tok.is_translated = True
        return tokens
