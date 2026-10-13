"""
cat_val/incoatius.py -- Mirall invers de `rules/val_cat/incoatius.py`:
verbs incoatius -eix (oriental) -> -ix (occidental): estableix->establix,
serveix->servix, requereix->requerix...

**Per què açò és una llista TANCADA d'arrels, no una regla de sufix pura
(a diferència de l'original)**: en català, "estableix" (ha de canviar) i
"apareix" (mai canvia, vore `rules/val_cat/incoatius.py`) acaben
EXACTAMENT igual -- "l"+"eix" i "r"+"eix" respectivament, els dos amb
"eix" precedit de consonant. El truc que funciona en sentit val->cat
(mirar si la lletra abans d'"ix" és "e") NO servix ací: el valencià
distingix les dos classes ortogràficament (ix/eix), pero el català les
fon totes dos en "eix" -- la distinció és LÈXICA (quin verb és en
concret), no detectable per cap patró ortogràfic. Confirmat: cap d'estos
verbs apareix a `conjugacions_dialectals.json` (és un patró PRODUCTIU,
Mauricio no el llista, mateix motiu que l'original és una regla de sufix
i no un diccionari).

**Arrels incloses (13/10/2026), NOMÉS les trobades amb evidència real al
benchmark invertit** (7 verbs, 8 aparicions: RC025 "servix", RC091/092
"establix", RC110 "s'aconseguix", RC124 "requerix", RC127 "oferix",
RC132 "exhaurix", RC134 "coincidix"): `establir`, `servir`,
`aconseguir`, `requerir`, `oferir`, `exhaurir`, `coincidir`. NO és una
llista exhaustiva de verbs incoatius catalans (n'hi ha molts mes:
"admetre"... -- en realitat la classe 3a incoativa és grossa) -- s'amplia
NOMÉS quan apareix evidència real (p.ex. revisant el corpus del BOE),
mai per endevinar, mateix criteri que la resta del projecte.

Gestiona qualsevol persona/forma que continga `arrel + "eix"` seguit de
qualsevol terminació (estableix, estableixen, estableixes, estableixi,
estableixin...) -- substituïx NOMÉS eixe fragment "eix"->"ix", deixant
la resta de la terminació intacta.
"""

from __future__ import annotations

from .. import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

_ARRELS_INCOATIUS = {
    "establ", "serv", "aconsegu", "requer", "ofer", "exhaur", "coincid",
}


def _intenta_incoatiu(paraula: str) -> str | None:
    for arrel in _ARRELS_INCOATIUS:
        prefix_eix = arrel + "eix"
        if paraula.startswith(prefix_eix):
            return arrel + "ix" + paraula[len(prefix_eix):]
    return None


class IncoatiusInversRule:
    """Substitueix "eix" per "ix" nomes per a les arrels verbals de la
    llista tancada (vore docstring del mòdul).

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Això estableix i serveix per a requereixen.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('estableix', 'establix'), ('serveix', 'servix'), ('requereixen', 'requerixen')]

    Verbs NO coneguts (p.ex. "apareix") mai es toquen, encara que
    acaben igual -- evita l'error de l'original invertit:

    >>> toks = tokenize("Açò apareix i desapareix.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Prefix elidit ("s'aconsegueix" -> "s'aconseguix", cas real RC110):

    >>> toks = tokenize("Açò s'aconsegueix fàcilment.")
    >>> marca_noms_propis(toks)
    >>> toks = IncoatiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("s'aconsegueix", "s'aconseguix")]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            nova = _intenta_incoatiu(minuscules)
            if nova is not None:
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            nova = _intenta_incoatiu(resta.lower())
            if nova is not None:
                aplica_amb_prefix_elidit(tokens, i, prefix, resta, nova)
                tok.is_translated = True
        return tokens
