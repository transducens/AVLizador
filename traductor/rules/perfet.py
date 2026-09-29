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

BUG GREU trobat en auditar el benchmark de 150 frases (28/09/2026): la
terminació "-à" també casa amb el FUTUR de qualsevol verb de 1a conjugació
("celebrarà", futur, casava igual que "celebrà", pretèrit simple), perquè
el futur s'assumix afegint "à" a l'INFINITIU sencer (celebrar+à), mentre
el pretèrit simple l'afig a l'arrel (celebr+à). El resultat era un doble
sufix absurd: "celebrarà" -> "va celebrarar". Corregit exigint que la
terminació "-à" NO estiga precedida de "ar" (eixe patró és exclusiu del
futur: infinitiu(-ar) + à). Coneguda limitació d'esta correcció: un verb
rar el radical del qual ja acabara en "ar" abans de llevar la terminació
d'infinitiu (p.ex. "declarar" -> arrel "declar", pretèrit "declarà") es
quedaria sense convertir -- fals negatiu acceptat davant l'alternativa
(el fals positiu, molt més freqüent: 7 casos trobats en 150 frases només
amb verbs regulars en futur).

PENDENT, NO RESOLT: verbs IRREGULARS en futur (radical futur no derivat de
l'infinitiu sencer) seguixen col·lidint, perquè no acaben en "-arà" sinó
en "-rà" a soles: "tindrà" (tindre), "podrà" (poder), "veurà" (veure),
"resoldrà" (resoldre), "entendrà" (entendre), "caldrà" (caldre), "permetrà"
(permetre) -- tots trobats produint garbage ("va tindrar", "va podrar"...)
en auditar el benchmark de 150 frases. No s'ha construït encara una llista
negra d'arrels irregulars de futur (calen ~15-20 verbs catalans d'ús molt
freqüent); queda com a treball pendent, documentat ací per a no oblidar-ho.
"""

from __future__ import annotations

import re

from . import Token

_TERMINACIONS_PERFET = [
    ("àrem", "vam"),
    ("àreu", "vau"),
    ("aren", "van"),
    ("à", "va"),
]

# El futur d'1a conjugació s'afig sobre l'INFINITIU sencer (celebrar+à ->
# "celebrarà"), mentre el pretèrit simple s'afig sobre l'arrel (celebr+à
# -> "celebrà") -- per això, si la terminació "-à" ve precedida de "ar",
# és futur, no pretèrit, i no s'ha de tocar (vore BUG GREU al docstring).
_FUTUR_RE = re.compile(r"arà$", re.IGNORECASE)

# Falsos positius CONFIRMATS de la terminació "-à" (vore taula de dades
# dalt): "està" (present d'indicatiu d'"estar", irregular -- no pretèrit
# simple; produïa l'incorrecte "va estar", canviant el TEMPS de la frase),
# "valencià"/"castellà"/"català"/"italià"/"romà" (gentilicis/adjectius, no
# verbs; produïen "va valenciar"/"va castellar"/"va italiar"/"va romar"),
# "mitjà" (substantiu "mitjà de comunicació", no verb; "va mitjar"),
# "endemà" (substantiu "l'endemà", no verb; "va endemar"), "enllà" (adverbi
# "més enllà", no verb; "va enllar"). `is_proper_noun` no cobrix estos
# casos -- només protegix noms propis, no gentilicis, adjectius,
# substantius o verbs irregulars.
_FALSOS_POSITIUS_CONEGUTS = {
    "està", "valencià", "català", "castellà", "italià", "romà",
    "mitjà", "endemà", "enllà",
}


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

    El futur ("celebrarà", "reservarà"...) mai es confon amb el pretèrit
    simple ("celebrà"), encara que abans d'esta correcció "celebrarà"
    produïa l'absurd "va celebrarar" (vore BUG GREU al docstring del mòdul):

    >>> _reconstrueix_perifrastic("celebrarà") is None
    True
    >>> _reconstrueix_perifrastic("celebrà")
    'va celebrar'

    Adjectius/substantius que casualment acaben en "-à" sense ser verbs,
    trobats auditant el benchmark de 150 frases:

    >>> _reconstrueix_perifrastic("italià") is None
    True
    >>> _reconstrueix_perifrastic("romà") is None
    True
    >>> _reconstrueix_perifrastic("mitjà") is None
    True
    >>> _reconstrueix_perifrastic("endemà") is None
    True

    La llista negra protegix igual si la paraula arriba amb un prefix
    elidit enganxat (mateix problema ja trobat a gentilicis.py):

    >>> _reconstrueix_perifrastic("l'endemà") is None
    True

    ...i igual amb l'apòstrof tipogràfic (’), el que fa servir de veres el
    corpus real:

    >>> _reconstrueix_perifrastic("l’endemà") is None
    True
    """
    minuscules = paraula.lower()
    # "l'endemà"/"s'assemblà" arriben com un sol token (l'apòstrof és part
    # de la paraula, vore rules/__init__.py) -- la llista negra ha de
    # comprovar-se sobre la part real de la paraula, no sobre el token
    # sencer amb el prefix elidit davant (mateix problema ja trobat i
    # arreglat a gentilicis.py). El tokenitzador accepta tant l'apòstrof
    # recte (') com el tipogràfic (’, el que fa servir de veres el corpus).
    paraula_real = re.split(r"['’]", minuscules)[-1]
    if paraula_real in _FALSOS_POSITIUS_CONEGUTS or _FUTUR_RE.search(paraula_real):
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
