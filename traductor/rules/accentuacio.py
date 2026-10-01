"""
accentuacio.py -- Dos patrons de sufix PRODUCTIUS (no llista tancada, a
diferència de les 4 capes de diccionari que van abans en el pipeline --
vore engine.py): qualsevol paraula valenciana que acabe així es convertix,
encara que no estiga enumerada a cap fitxer de Mauricio. Afegit 30/09/2026
a petició explícita, després de constatar que el pur lookup de diccionari
(decisió del mateix dia, vore traductor/README.md) no pot cobrir mai un
patró obert i productiu -- un diccionari només conté les paraules que algú
ja hi ha ficat.

    1. -és (agut, occidental) -> -ès (obert, oriental): francés->francès,
       interés->interès, comités->comitès... Mateix patró que ja cobria
       `lexic_acentuacio_mauricio.json` per a les 695 paraules literals,
       però ara generalitzat a QUALSEVOL paraula -- inclosos gentilicis i
       noms no enumerats a eixe fitxer.
    2. -éixer (infinitiu, occidental) -> -èixer (oriental): conéixer->
       conèixer, paréixer->parèixer, aparéixer->aparèixer... Mai coincidix
       amb el patró 1 (acaben en "-er", no en "-és"), així que no fa falta
       triar entre els dos.

Excepcions conegudes del patró 1 (mateixes que es van trobar auditant els
benchmarks reals abans de retirar `gentilicis.py` el 30/09/2026, vore
`../../02_regles_dialectals/reglas_dialectales_con_evidencia.md` §6.2):
"és" (verb "ser") i "més" (quantitat) són l'excepció explícita de la font;
"només", "després", "procés", "congrés", "accés", "progrés", "través" es
van trobar empíricament -- són diccionaris DIFERENCIALS (com els de
Mauricio) que mai poden confirmar per si sols que una paraula NO canvia,
així que esta llista es queda com a set de Python, no com a fitxer font.

Cap excepció coneguda per al patró 2 -- "-éixer" és una terminació
d'infinitiu molt específica, no s'ha trobat cap paraula real que hi
acabe sense ser un d'estos verbs.
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

_EXCEPCIONS_ES = {
    "és", "més", "només", "després", "procés", "congrés", "accés", "progrés", "través",
}
_SUFIX_ES_RE = re.compile(r"és$", re.IGNORECASE)
_SUFIX_EIXER_RE = re.compile(r"éixer$", re.IGNORECASE)


class AccentuacioRule:
    """Aplica els dos patrons de sufix documentats al mòdul.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("El meu amic francés parla anglés i és cortés.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('francés', 'francès'), ('anglés', 'anglès'), ('cortés', 'cortès')]

    "és" (verb) i "més" (quantitat) mai es toquen:

    >>> toks = tokenize("Hi ha més interés del que és normal.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('interés', 'interès')]

    "després"/"només"/"procés"/"congrés"/"accés"/"progrés"/"través"
    tampoc -- substantius/adverbis comuns que NO seguixen el patró
    (falsos positius confirmats al benchmark real):

    >>> toks = tokenize("El procés d'accés al congrés continua en progrés a través de tot, però només un poc, i després ja vorem.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Infinitius acabats en "-éixer" (patró 2):

    >>> toks = tokenize("Vull conéixer i paréixer content, no aparéixer trist.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('conéixer', 'conèixer'), ('paréixer', 'parèixer'), ('aparéixer', 'aparèixer')]

    Paraula enganxada a un prefix elidit ("d'", "l'"...): la substitució
    de sufix ja travessa qualsevol prefix sense necessitat de separar-lo
    (mateix motiu que abans a `gentilicis.py`/`perfet.py`). "accés" mai es
    toca encara que porte un prefix elidit davant:

    >>> toks = tokenize("Vaig sentir parlar d'aparéixer i d'accés directe.")
    >>> marca_noms_propis(toks)
    >>> toks = AccentuacioRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'aparéixer", "d'aparèixer")]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            # "d'accés"/"l'interés" arriben com un sol token (l'apòstrof
            # és part de la paraula, vore rules/__init__.py) -- cal
            # comprovar les excepcions sobre la part real de la paraula.
            paraula = re.split(r"['’]", minuscules)[-1]

            if paraula not in _EXCEPCIONS_ES and paraula.endswith("és"):
                nova = _SUFIX_ES_RE.sub("ès", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
                continue

            if paraula.endswith("éixer"):
                nova = _SUFIX_EIXER_RE.sub("èixer", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
        return tokens
