"""
cat_val/preposicions_locucions.py -- Mirall invers de
`rules/val_cat/preposicions_locucions.py`: les 5 MATEIXES locucions, cadascuna
revertida a mà (NO amb un flip automàtic "a"<->"en" -- ja es va comprovar
en construir la direcció original que la mateixa preposició pot canviar
de sentit distint fins i tot dins de la mateixa frase, RC137: "elevar AL
Consell" es queda igual pero "elevar A les Corts Valencianes" ve d'"EN
les Corts Valencianes"). Les paraules de "lookahead" es comparen contra
`tok.surface` EN CATALÀ ara (abans en valencià), per això "seves" ací, no
"seues".

**6a locució, afegida 13/10/2026, trobada mesurant el benchmark
invertit**: "per a acabar" (català) -> "per acabar" (valencià), 2 casos
reals (RC112, RC118), cap excepció. A diferència de les altres 5, esta
no substituïx "a" per una altra preposició -- l'ELIMINA sencera (marcada
amb `desti = None`), fonent l'espai sobrant perquè no quede doble espai.
"""

from __future__ import annotations

from .. import Token, paraula_anterior_es, paraules_segudents_son, preserva_majuscula

# (paraula_abans | None, preposicio_origen_catalana, [paraules_despres_catalanes], preposicio_desti_valenciana | None)
# `desti = None` vol dir "elimina la preposicio" (vore docstring del modul).
_LOCUCIONS_INVERSES = [
    ("vinculat", "en", [], "a"),
    (None, "a", ["les", "seves", "mans"], "en"),
    (None, "a", ["la", "ciutat"], "en"),
    (None, "a", ["l'interior"], "en"),
    (None, "en", ["les", "corts", "valencianes"], "a"),
    ("per", "a", ["acabar"], None),
]


class PreposicionsLocucionsInversRule:
    """Corregix "a"/"en" en sentit invers per a les 5 locucions conegudes.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Està vinculat en aquesta universitat.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('en', 'a')]

    >>> toks = tokenize("El futur està a les seves mans.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('a', 'en')]

    >>> toks = tokenize("Tindrà la seu a la ciutat de València.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('a', 'en')]

    >>> toks = tokenize("El parèntesi està a l'interior de la frase.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('a', 'en')]

    >>> toks = tokenize("Cal elevar en les Corts Valencianes estes propostes.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('en', 'a')]

    La contracció "al" mai es toca:

    >>> toks = tokenize("Cal elevar al Consell estes propostes.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    "per a acabar" -> "per acabar" (elimina "a", sense doble espai):

    >>> from .. import detokenize
    >>> toks = tokenize("Per a acabar: tenim dos llengües.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsInversRule().apply(toks)
    >>> detokenize(toks)
    'Per acabar: tenim dos llengües.'
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            for paraula_abans, origen, despres, desti in _LOCUCIONS_INVERSES:
                if minuscules != origen:
                    continue
                if paraula_abans is not None and not paraula_anterior_es(tokens, i, paraula_abans):
                    continue
                if despres and not paraules_segudents_son(tokens, i, despres):
                    continue
                if desti is None:
                    tok.translated = ""
                    tok.is_translated = True
                    if i > 0 and tokens[i - 1].surface.isspace():
                        tokens[i - 1].translated = ""
                        tokens[i - 1].is_translated = True
                else:
                    tok.translated = preserva_majuscula(tok.surface, desti)
                    tok.is_translated = True
                break
        return tokens
