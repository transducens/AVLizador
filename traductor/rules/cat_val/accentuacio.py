"""
cat_val/accentuacio.py -- Mirall invers de `rules/val_cat/accentuacio.py`: dos
patrons de sufix productius, -ès (oriental) -> -és (occidental) i -èixer
(oriental) -> -éixer (occidental): francès->francés, conèixer->conéixer...

**Per què esta direcció NO necessita cap llista d'excepcions** (a
diferència de `rules/val_cat/accentuacio.py`, que en té 9: "només", "després",
"procés"...): eixes excepcions són paraules que en CATALÀ es queden amb
l'accent TANCAT (é), exactament com en valencià -- mai arriben a escriure's
amb accent OBERT (è). Com el patró d'esta regla NOMÉS dispara sobre "-ès"
(obert), eixes paraules invariables NI TAN SOLS CASEN amb el patró
d'entrada -- verificat comptant totes les paraules acabades en -ès/-é s
del costat català del benchmark de 151 frases (vore
`documentacio/hoja_de_ruta_traductor_invers.md`): "només", "després",
"procés", "accés", "congrés", "progrés", "través", "més" hi apareixen,
tots amb accent TANCAT (é), mai amb obert (è) -- cap manté cap risc de
col·lisió.

Trobat de pas: el mateix benchmark té "aprés" escrit amb accent OBERT en
un lloc (RC010) i TANCAT en un altre (RC015) per a la MATEIXA paraula
("ha aprés" = "ha après/aprés") -- inconsistència del propi corpus de
referència, no d'esta regla (mateix tipus de soroll ja documentat en
altres llocs del projecte, p.ex. "o siga"/RC067).
"""

from __future__ import annotations

import re

from .. import Token, preserva_majuscula

_SUFIX_ES_RE = re.compile(r"ès$", re.IGNORECASE)
_SUFIX_EIXER_RE = re.compile(r"èixer$", re.IGNORECASE)


class AccentuacioInversRule:
    """Aplica els dos patrons de sufix en sentit invers.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("El meu amic francès parla anglès i és cortès.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('francès', 'francés'), ('anglès', 'anglés'), ('cortès', 'cortés')]

    "només"/"després"/"procés"... mai es toquen -- no acaben en "-ès"
    (accent obert), vore docstring del mòdul:

    >>> toks = tokenize("El procés d'accés al congrés continua en progrés a través de tot, però només un poc, i després ja vorem.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Infinitius acabats en "-èixer" (patró 2):

    >>> toks = tokenize("Vull conèixer i parèixer content, no aparèixer trist.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('conèixer', 'conéixer'), ('parèixer', 'paréixer'), ('aparèixer', 'aparéixer')]

    Paraula enganxada a un prefix elidit:

    >>> toks = tokenize("Vaig sentir parlar d'aparèixer i d'anglès.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'aparèixer", "d'aparéixer"), ("d'anglès", "d'anglés")]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            paraula = re.split(r"['’]", minuscules)[-1]

            if paraula.endswith("èixer"):
                nova = _SUFIX_EIXER_RE.sub("éixer", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
                continue

            if paraula.endswith("ès"):
                nova = _SUFIX_ES_RE.sub("és", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
        return tokens
