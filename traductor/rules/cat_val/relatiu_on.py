"""
cat_val/relatiu_on.py -- Mirall invers de `rules/val_cat/relatiu_on.py`:
afig "a" davant de "on" quan funciona com a relatiu/interrogatiu locatiu
("la casa on vivia" -> "la casa a on vivia"). El català estàndard sempre
lleva la preposició explícita en este ús; el valencià l'admet (i, segons
l'evidència real, la fa servir sempre).

EVIDÈNCIA (13/10/2026, mateix mètode que la direcció original): es van
revisar els 151 casos del benchmark invertit (`oriental` com a entrada)
buscant "on". **8 casos reals en 7 frases, els 8 volen "a on"** (RC009,
RC026, RC030, RC052, RC072, RC081, RC083 ×2) -- cap excepció, cap cas de
"on" sol que s'haguera de deixar igual. Coherent amb l'evidència ja
registrada a `rules/val_cat/relatiu_on.py` (direcció original: "a on" MAI
es queda igual en el corpus de referència) -- la mateixa relació, mirada
des de l'altre costat, amb el mateix resultat net: sense ambigüitat
coneguda.

CAS ESPECIAL (mirall de l'original): "d'on" (prefix elidit enganxat) ha
de tornar "d'a on", no "d' a on" amb espai doble ni "da on".

LÍMIT CONEGUT, ACCEPTAT (2 excepcions trobades mesurant, RC061/RC140,
cap heurística fiable trobada encara): quan "on" introduïx una referència
TEMPORAL dins d'una construcció d'èmfasi/escissió ("ha sigut
modernament... on l'ús...", "en les relacions amb els amics és on el
predomini... i, després de casa, on el valencià..."), el valencià real
es queda amb "on" SOL, sense "a". No és el mateix patró que "la casa on
vivia" (locatiu espacial) -- és una distinció semàntica (temps vs. lloc
dins d'una escissió), no gramatical ni posicional: a RC140 un "on" ve
immediatament darrere d'"és" i l'altre darrere d'una coma, els dos són
l'excepció. No s'ha trobat cap senyal prou fiable per a distingir-los
amb la resta del benchmark (només 2 casos, massa poca evidència per a
una regla nova) -- es prioritza no trencar els 8 casos reals que SÍ
funcionen bé (preferix fals negatiu en l'agregat: net +6 mantenint esta
regla simple en compte de +8 arriscant una heurística que podria fallar
en casos futurs no vistos). Pendent de revisar amb mes evidència (BOE).

BUG REAL trobat i corregit (13/10/2026, RC076): "per a on" (català, amb
"a" ja present per la preposició "per a", res a vore amb esta regla) es
convertia en "per a a on" (doblant la "a") perquè la regla no comprovava
si "on" ja anava precedida d'un "a" solt. Corregit comprovant la paraula
real immediatament anterior abans d'afegir res.
"""

from __future__ import annotations

from .. import Token, paraula_anterior_es, preserva_majuscula, separa_prefix_elidit


class RelatiuOnInversRule:
    """Afig "a" davant de "on" quan funciona com a relatiu/interrogatiu
    locatiu (vore docstring del mòdul per a l'evidència).

    >>> from .. import tokenize, marca_noms_propis, detokenize
    >>> toks = tokenize("Hem fet bancals on hi havia pendents.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnInversRule().apply(toks)
    >>> detokenize(toks)
    'Hem fet bancals a on hi havia pendents.'

    Cas especial: prefix elidit enganxat a "on" ("d'on" -> "d'a on", no
    "d' a on" amb espai doble):

    >>> toks = tokenize("Es documenta des d'on ja se sap.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnInversRule().apply(toks)
    >>> detokenize(toks)
    "Es documenta des d'a on ja se sap."

    Majúscula a l'inici de frase es trasllada a "a":

    >>> toks = tokenize("On anem ara?")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnInversRule().apply(toks)
    >>> detokenize(toks)
    'A on anem ara?'

    "on" ja precedit d'un "a" solt (p.ex. "per a on") no es toca -- evita
    doblar la preposició (RC076, "per a on" -> "per a a on" abans d'este fix):

    >>> toks = tokenize("Aquell per a on el sol desapareix.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnInversRule().apply(toks)
    >>> detokenize(toks)
    'Aquell per a on el sol desapareix.'
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            if minuscules == "on":
                if paraula_anterior_es(tokens, i, "a"):
                    continue
                tok.translated = preserva_majuscula(tok.surface, "a on")
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            if resta.lower() != "on":
                continue
            tok.translated = prefix + "a " + resta
            tok.is_translated = True
        return tokens
