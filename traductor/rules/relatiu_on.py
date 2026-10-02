"""
relatiu_on.py -- Corregix "a on" -> "on" com a relatiu/interrogatiu
locatiu ("la casa a on vivia" -> "la casa on vivia"). El valencià admet
"a on" amb preposició explícita en este ús; el català estàndard la lleva
sempre. Fitxer a banda (mateix criteri que `concordanca_dos_dues.py`):
regla de patró, no lookup de diccionari, es controla per separat.

EVIDÈNCIA (01-02/10/2026, mateix mètode que `dos/dues`): es van revisar
els 150 casos del benchmark buscant "a on"/"on". De 9 casos reals on la
referència lleva la "a", els 9 són exactament este patró -- cap excepció,
cap ambigüitat ("a on" MAI es queda igual en el corpus de referència).
Per contrast, es van comprovar altres 3 diferències que documenten
`guia_dialectal_morfologia.md`/`guia_traduccio_dialectal.md`
(`docs_gramatica/`) i es van DESCARTAR per falta d'evidència real o risc
massa alt:

  - "lo/los" com a pronom feble: 2 aparicions al benchmark, totes dos
    falsos positius ("saber-lo", "segmentant-los" -- enclítics after verb,
    idèntics als dos dialectes, no té res a vore amb el "lo" proclític que
    documenten les gramàtiques).
  - "per" -> "per a" (finalitat): només 2 casos reals de 28 aparicions de
    "per"/"per a", i la distinció depén de si "per" té valor de causa o de
    finalitat -- difícil d'automatitzar amb seguretat sense anàlisi
    sintàctica real, mateix tipus de risc que es va descartar amb
    l'escaneig automàtic de gènere a `lexic.py`.
  - "ací" -> "aquí": només 1 aparició al benchmark, i en eixe cas concret
    la referència es queda "ací" SENSE canviar -- contradiu la teoria de
    la gramàtica amb l'única dada real disponible, així que no s'implementa
    fins que n'hi haja més evidència.

CAS ESPECIAL trobat en la mateixa revisió: un dels 9 casos és "d'a on"
(prefix elidit "d'" + "a on"), que ha de convertir-se en "d'on" (no en
"d' on" amb espai) -- vore el segon doctest baix.
"""

from __future__ import annotations

from . import Token, preserva_majuscula, separa_prefix_elidit


class RelatiuOnRule:
    """Lleva la "a" de "a on" quan funciona com a relatiu/interrogatiu
    locatiu (vore docstring del mòdul per a l'evidència).

    >>> from . import tokenize, marca_noms_propis, detokenize
    >>> toks = tokenize("Hem fet bancals a on hi havia pendents.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnRule().apply(toks)
    >>> detokenize(toks)
    'Hem fet bancals on hi havia pendents.'

    Cas especial: prefix elidit enganxat a la "a" ("d'a on" -> "d'on", no
    "d' on" amb espai):

    >>> toks = tokenize("Vinga d'a on vinga la inspiració.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnRule().apply(toks)
    >>> detokenize(toks)
    "Vinga d'on vinga la inspiració."

    Majúscula a l'inici de frase es trasllada a "on":

    >>> toks = tokenize("A on anem ara?")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnRule().apply(toks)
    >>> detokenize(toks)
    'On anem ara?'

    "on" sol (sense "a" davant) no es toca:

    >>> toks = tokenize("La casa on vivia era menuda.")
    >>> marca_noms_propis(toks)
    >>> toks = RelatiuOnRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            if tok.surface.lower() != "on":
                continue

            j = i - 1
            while j >= 0 and tokens[j].surface.isspace():
                j -= 1
            if j < 0:
                continue
            anterior = tokens[j]

            if anterior.surface.lower() == "a":
                tok.translated = preserva_majuscula(anterior.surface, "on")
                tok.is_translated = True
                anterior.translated = ""
                anterior.is_translated = True
                for k in range(j + 1, i):
                    tokens[k].translated = ""
                    tokens[k].is_translated = True
                continue

            prefix_resta = separa_prefix_elidit(anterior.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            if resta.lower() != "a":
                continue
            tok.translated = prefix + "on"
            tok.is_translated = True
            anterior.translated = ""
            anterior.is_translated = True
            for k in range(j + 1, i):
                tokens[k].translated = ""
                tokens[k].is_translated = True
        return tokens
