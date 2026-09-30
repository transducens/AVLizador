"""
incoatius.py -- Verbs incoatius -ix (occidental) -> -eix (oriental):
establix->estableix, servix->serveix, requerix->requereix... Patró de
SUFIX productiu (no llista tancada): qualsevol verb incoatiu de 3a
conjugació segueix esta alternança, i un diccionari mai pot enumerar-los
tots. Afegit 30/09/2026 a petició explícita -- vore
`traductor/rules/accentuacio.py` per al mateix raonament sobre per què cal
una regla de sufix ademés del lookup de diccionari.

Dos proteccions, totes dos trobades auditant benchmarks reals (les
mateixes que portava `morfologia_verbal.py` abans de retirar-se el
30/09/2026):

    1. Mai toca paraules que ja acaben en "-eix" (no només "-ix"):
       "aparéixer"/"desaparéixer"/"comparéixer" ja tenen l'infix incoatiu
       "-eix-" DINS del propi infinitiu (a diferència d'"establir", un
       verb pur en "-ir" sense eixe infix), així que la seua 3a persona
       ("apareix", "desapareix") és IDÈNTICA en els dos dialectes -- no
       és una alternança dialectal en absolut. Sense esta exclusió, la
       regla trencaria "mateix" (adjectiu "same/molt", no un verb),
       "tanmateix" (adverbi "nevertheless") i "apareix"/"desapareix"
       mateixos.
    2. Llista negra de paraules catalanes reals que acaben en
       consonant+"ix" sense ser verbs incoatius: `baix`, `calaix`,
       `dibuix`, `guix`, `fix`, `prefix`, `sufix` -- sense esta protecció,
       "el calaix" es convertiria incorrectament en "el calaeix".

També ignora tokens completament en majúscules (`XIX`, `AVL`...): sense
esta guarda, un numeral romà com "segle XIX" es tractaria com si acabara
en "-ix" i es convertiria en l'absurd "XEIX".
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

_EXCEPCIONS = {"baix", "calaix", "dibuix", "guix", "fix", "prefix", "sufix"}
# Exigix que la lletra just abans de "ix" NO siga "e" -- així mai toca
# paraules que ja acaben en "-eix" (aparéixer, mateix, tanmateix...), que
# no són alternances dialectals (vore docstring del mòdul).
_SUFIX_IX_RE = re.compile(r"(?<!e)ix$", re.IGNORECASE)


class IncoatiusRule:
    """Substitueix el sufix -ix per -eix, amb les proteccions del
    docstring del mòdul.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Este servix per a establix una nova norma.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('servix', 'serveix'), ('establix', 'estableix')]

    >>> toks = tokenize("Obri el calaix de baix.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Paraules que ja acaben en "-eix" no es toquen mai:

    >>> toks = tokenize("Açò mateix apareix i desapareix, tanmateix.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    "prefix"/"sufix"/"fix" tampoc són verbs (llista negra):

    >>> toks = tokenize("El prefix i el sufix d'esta paraula són fix.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Numerals romans en majúscules mai es toquen:

    >>> toks = tokenize("En el segle XIX ja es documentava esta forma.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            if len(tok.surface) > 1 and tok.surface.isupper():
                continue
            minuscules = tok.surface.lower()
            if minuscules in _EXCEPCIONS:
                continue
            if _SUFIX_IX_RE.search(minuscules) and len(minuscules) > 2:
                nova = _SUFIX_IX_RE.sub("eix", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
        return tokens
