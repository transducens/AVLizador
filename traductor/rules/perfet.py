"""
perfet.py -- Pretèrit perfet simple ("passà, transformaren, cantí...",
forma llatinitzant pròpia de registre culte/literari) -> perifràstic ("va
passar, van transformar, vaig cantar..."), la forma estàndard en oriental.
Font: final/02_reglas_dialectales/reglas_dialectales.md, secció 11.1.
Evidència directa del benchmark: 4/4 casos, sense excepció.

Abast d'esta implementació: NOMÉS verbs de 1a conjugació (-ar), que són els
únics que la font confirma amb exemples concrets (passà -> va passar,
ve de "passar"; transformaren -> van transformar, ve de "transformar").
La reconstrucció de l'infinitiu és senzilla per a esta conjugació: llevar
la terminació de perfet simple i afegir "-ar" a l'arrel que queda.

# AMBIGÚ: la font no dona exemples de 2a/3a conjugació (-er/-ir), i eixos
# verbs tenen irregularitats pròpies del pretèrit simple que no seguixen
# el mateix patró senzill "llevar terminació + afegir -ar" (p.ex. un verb
# en -er no reconstruiria bé afegint "-ar"). No s'implementen ací per no
# inventar un patró sense evidència -- queden com a TODO fins que hi haja
# exemples confirmats.

Terminacions cobertes (totes de 1a conjugació):
    -à     (3a sg)  -> "va " + infinitiu       passà -> va passar
    -aren  (3a pl)  -> "van " + infinitiu       transformaren -> van transformar
    -àrem  (1a pl)  -> "vam " + infinitiu       cantàrem -> vam cantar
    -àreu  (2a pl)  -> "vau " + infinitiu       cantàreu -> vau cantar

DADES REALS, no teoria: en córrer el motor sencer contra les 60 frases del
benchmark es van comptar els encerts i els errors de cada terminació:
    -à     : 2 encerts (celebrà, passà) -- 4 falsos positius (està,
             valencià, català*, castellà) abans d'excloure'ls
    -aren  : 1 encert (quedaren) -- 0 falsos positius
    -í     : 0 encerts -- 5 falsos positius (llatí×3, així×2)
    -ares  : 0 encerts -- 2 falsos positius (clares, pares)
(*català no ha eixit al benchmark, exclòs per analogia amb valencià/castellà)

Per això -í i -ares s'han TRET del tot (0% de precisió, cap benefici que
compense el risc), mentre que -à i -aren es queden amb una llista negra
de falsos positius confirmats (_FALSOS_POSITIUS_CONEGUTS) perquè sí tenen
encerts reals que compensen. No s'ha ampliat la llista negra indefinidament
com a estratègia general -- eixe camí no acaba mai (sempre apareixerà una
altra paraula catalana acabada en -à que no siga verb); tallar la
terminació sencera quan les dades mostren 0% de precisió és la resposta
correcta, no apedaçar cas a cas.
"""

from __future__ import annotations

from . import Token

_TERMINACIONS_PERFET = [
    ("àrem", "vam"),
    ("àreu", "vau"),
    ("aren", "van"),
    ("à", "va"),
]

# Falsos positius CONFIRMATS de la terminació "-à" (vore taula de dades
# dalt): "està" (present d'indicatiu d'"estar", irregular -- no pretèrit
# simple; produïa l'incorrecte "va estar", canviant el TEMPS de la frase),
# "valencià"/"castellà" (gentilicis, no verbs; produïen "va valenciar"/
# "va castellar"), "català" (mateix patró, exclòs per analogia encara que
# no haja eixit al benchmark). `is_proper_noun` no cobrix estos casos --
# només protegix noms propis, no gentilicis ni verbs irregulars.
_FALSOS_POSITIUS_CONEGUTS = {"està", "valencià", "català", "castellà"}


def _reconstrueix_perifrastic(paraula: str) -> str | None:
    """Torna la forma perifràstica ("vaig cantar", "va passar"...) si
    `paraula` casa amb alguna terminació de pretèrit simple de 1a
    conjugació, o None si no.

    >>> _reconstrueix_perifrastic("passà")
    'va passar'
    >>> _reconstrueix_perifrastic("transformaren")
    'van transformar'
    >>> _reconstrueix_perifrastic("cantàrem")
    'vam cantar'
    >>> _reconstrueix_perifrastic("cantàreu")
    'vau cantar'
    >>> _reconstrueix_perifrastic("casa") is None
    True

    Falsos positius confirmats de "-à" en el benchmark real, ara protegits
    (vore _FALSOS_POSITIUS_CONEGUTS):

    >>> _reconstrueix_perifrastic("està") is None
    True
    >>> _reconstrueix_perifrastic("valencià") is None
    True
    >>> _reconstrueix_perifrastic("castellà") is None
    True

    "-í" i "-ares" es van traure del tot (0% de precisió confirmada al
    benchmark, vore docstring del mòdul) -- ni tan sols casen ja:

    >>> _reconstrueix_perifrastic("cantí") is None
    True
    >>> _reconstrueix_perifrastic("cantares") is None
    True
    """
    minuscules = paraula.lower()
    if minuscules in _FALSOS_POSITIUS_CONEGUTS:
        return None
    for sufix, pronom in _TERMINACIONS_PERFET:
        if minuscules.endswith(sufix) and len(minuscules) > len(sufix):
            arrel = minuscules[: -len(sufix)]
            infinitiu = arrel + "ar"
            return f"{pronom} {infinitiu}"
    return None


class PerfetRule:
    """Convertix pretèrit perfet simple (1a conjugació) a perifràstic.

    La majúscula inicial es gestiona ací a mà (no amb preserva_majuscula
    compartida) perquè el resultat és una FRASE ("Va passar"), no una sola
    paraula -- només la primera lletra del pronom auxiliar ha de rebre la
    majúscula, mai l'infinitiu que va darrere.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Ahir passà una cosa i despres transformaren tot.")
    >>> marca_noms_propis(toks)
    >>> toks = PerfetRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('passà', 'va passar'), ('transformaren', 'van transformar')]

    >>> toks = tokenize("Passà l'examen sense problemes.")
    >>> marca_noms_propis(toks)
    >>> toks = PerfetRule().apply(toks)
    >>> [t.translated for t in toks if t.is_translated]
    ['Va passar']
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            perifrastic = _reconstrueix_perifrastic(tok.surface)
            if perifrastic is None:
                continue
            if tok.surface[:1].isupper():
                perifrastic = perifrastic[:1].upper() + perifrastic[1:]
            tok.translated = perifrastic
            tok.is_translated = True
        return tokens
