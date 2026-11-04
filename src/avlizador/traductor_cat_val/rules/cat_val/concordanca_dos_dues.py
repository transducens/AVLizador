"""
cat_val/concordanca_dos_dues.py -- Mirall invers de
`rules/val_cat/concordanca_dos_dues.py`, pero MOLT mes simple: el valencià fa
servir "dos" invariable sempre (masculí i femení), així que la regla
inversa és un reemplaç INCONDICIONAL "dues"->"dos", sense cap de les dos
capes (marcador explícit, gènere amb spaCy) que calien en l'altra
direcció -- ací no hi ha cap ambigüitat que resoldre, el català d'entrada
ja distingix "dos"/"dues" perfectament, i el valencià simplement no fa
eixa distinció mai.
"""

from __future__ import annotations

from .. import Token, preserva_majuscula


class ConcordancaDosDuesInversRule:
    """Substitueix "dues" per "dos" sempre, siga quin siga el context.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Les dues institucions i dues xifres mes.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dues', 'dos'), ('dues', 'dos')]

    "dos" (ja masculí) no es toca:

    >>> toks = tokenize("Els dos verbs eren irregulars.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            if tok.surface.lower() != "dues":
                continue
            tok.translated = preserva_majuscula(tok.surface, "dos")
            tok.is_translated = True
        return tokens
