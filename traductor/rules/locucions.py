"""
locucions.py -- Preposicions/locucions on l'occidental fa servir sempre la
mateixa forma i l'oriental distingix segons context. Font:
final/02_reglas_dialectales/reglas_dialectales_con_evidencia.md, secció 7.

Dos patrons implementats, de fiabilitat alta:

  1. "cap a on" -> "cap on": substitució literal de 3 paraules, sense
     ambigüitat -- l'occidental sempre diu "cap a on", l'oriental sempre
     "cap on" (mai "cap a on"). Implementat com a lookup exacte.

  2. "dalt de"/"baix de" -> "a dalt de"/"a baix de": l'occidental no porta
     "a" davant, l'oriental normatiu sí. Implementat com a lookup exacte,
     prefixant "a " (amb gestió manual de majúscula igual que perfet.py,
     perquè la majúscula "salta" a la paraula nova del davant).
     NOTA: "baix de" també es pot dir "sota" en oriental (alternativa més
     idiomàtica) -- no s'implementa eixa alternativa perquè no hi ha
     manera de triar entre "a baix de" i "sota" sense mirar el registre de
     la frase; "a baix de" és sempre gramaticalment vàlida, així que és
     l'opció seleccionada per defecte.

PENDENT, NO IMPLEMENTAT (documentat a la font, secció 7, com a candidats
sense regla automàtica encara):
  - "per a" -> "per" davant d'infinitiu: proposat inicialment, però
    CONTRADIT per evidència directa en auditar el benchmark de 150 frases
    (28/09/2026): les 17 aparicions de "per a + infinitiu" que hi ha al
    benchmark mantenen "per a" en la referència oriental, cap la reduïx a
    "per" (p.ex. "per a traure'n" -> "per a treure'n", mai "per treure'n").
    El registre institucional/normatiu d'este corpus sembla no aplicar
    mai eixa reducció, encara que és una distinció que sí existix en
    certes tradicions prescriptives del català. NO implementat fins que
    es confirme en quin registre/context aplicaria de veres.
  - "a on" -> "on" (ubicació estàtica) / "a on" es manté (direcció): la
    font documenta la distinció, però decidir si una frase és estàtica o
    direccional exigiria detectar un verb de moviment en la clàusula, una
    heurística molt més fràgil que les de dalt -- es deixa pendent fins
    que hi haja evidència real de com de sovint falla no fer-ho.
  - "en" (occidental) -> "a" (oriental) en construccions locatives: NO
    implementat a propòsit -- CONTRADIU la instrucció explícita que ja
    porta el system prompt ("no canvies mai 'en' per 'a'", amb l'exemple
    real "en la costa" que es queda "en la costa"), afegida després de
    trobar eixe error concret en un benchmark anterior. Pendent de
    confirmar l'abast exacte (probablement només topònims tipus "en
    Xàtiva" -> "a Xàtiva", no qualsevol "en") abans de tocar cap regla.
"""

from __future__ import annotations

from . import Token, preserva_majuscula

_PREFIX_A = {
    "dalt": "dalt",
    "baix": "baix",
}


def _index_seguent_paraula_real(tokens: list[Token], index: int) -> int | None:
    """Índex del següent token que és una paraula real (no espai), o None
    si troba puntuació abans o s'acaba la llista."""
    for j in range(index + 1, len(tokens)):
        tok = tokens[j]
        if tok.surface.isspace():
            continue
        if tok.surface[:1].isalpha():
            return j
        return None
    return None


def _seguent_paraula_real(tokens: list[Token], index: int) -> Token | None:
    j = _index_seguent_paraula_real(tokens, index)
    return tokens[j] if j is not None else None


def _tokens_paraula(tokens: list[Token], index: int) -> list[int]:
    """Índexs dels següents N tokens de paraula real (sense espais),
    començant JUSTAMENT a `index` (inclusiu), o llista curta si s'acaba
    abans."""
    resultat = []
    i = index
    while i < len(tokens) and len(resultat) < 3:
        if not tokens[i].surface.isspace():
            resultat.append(i)
        i += 1
    return resultat


class LocucionsRule:
    """Aplica els dos patrons documentats al mòdul, en este orde.

    "cap a on" -> "cap on" (substitució literal):

    >>> from . import tokenize, detokenize, marca_noms_propis
    >>> toks = tokenize("No sé cap a on anem.")
    >>> marca_noms_propis(toks)
    >>> detokenize(LocucionsRule().apply(toks))
    'No sé cap on anem.'

    "dalt de"/"baix de" -> "a dalt de"/"a baix de", amb majúscula gestionada
    a mà (la majúscula "salta" a la paraula nova del davant):

    >>> toks = tokenize("Dalt de la muntanya fa fred.")
    >>> marca_noms_propis(toks)
    >>> detokenize(LocucionsRule().apply(toks))
    'A dalt de la muntanya fa fred.'

    >>> toks = tokenize("Ix per baix de la porta.")
    >>> marca_noms_propis(toks)
    >>> detokenize(LocucionsRule().apply(toks))
    'Ix per a baix de la porta.'

    "per a" NO es toca mai (vore docstring del mòdul -- contradit per
    evidència directa del benchmark, encara que fóra davant d'infinitiu):

    >>> toks = tokenize("Estudie per a aprovar l'examen.")
    >>> marca_noms_propis(toks)
    >>> detokenize(LocucionsRule().apply(toks))
    "Estudie per a aprovar l'examen."
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok.is_translated or tok.is_proper_noun or tok.surface.isspace():
                i += 1
                continue
            minuscules = tok.surface.lower()

            # 1. "cap a on" -> "cap on"
            if minuscules == "cap":
                idxs = _tokens_paraula(tokens, i)
                paraules = tuple(tokens[j].surface.lower() for j in idxs)
                if paraules == ("cap", "a", "on"):
                    tokens[idxs[0]].translated = preserva_majuscula(tokens[idxs[0]].surface, "cap")
                    tokens[idxs[0]].is_translated = True
                    # Es buiden l'espai i "a" (fins idxs[1] inclòs), deixant
                    # l'espai entre "a" i "on" com a únic separador restant.
                    for k in range(idxs[0] + 1, idxs[1] + 1):
                        tokens[k].translated = ""
                        tokens[k].is_translated = True
                    tokens[idxs[2]].translated = tokens[idxs[2]].surface
                    tokens[idxs[2]].is_translated = True
                    i = idxs[2] + 1
                    continue

            # 2. "dalt de" / "baix de" -> "a dalt de" / "a baix de"
            arrel = _PREFIX_A.get(minuscules)
            if arrel is not None:
                seguent = _seguent_paraula_real(tokens, i)
                if seguent is not None and seguent.surface.lower() == "de":
                    prefixat = f"a {minuscules}"
                    if tok.surface[:1].isupper():
                        prefixat = "A " + minuscules
                    tok.translated = prefixat
                    tok.is_translated = True
                    i += 1
                    continue

            i += 1
        return tokens
