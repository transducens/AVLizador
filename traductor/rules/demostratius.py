"""
demostratius.py -- Pronoms/adjectius demostratius: este/eixe (occidental)
-> aquest/aqueix (oriental). Taula copiada literalment de
final/02_reglas_dialectales/reglas_dialectales.md, secció 1 -- NO inventada
ací.

És la regla morfològica MÉS freqüent del corpus (apareix en quasi totes les
frases), i una de les que el LLM del benchmark complia amb més
regularitat -- bon candidat per a una regla 100% determinista.

Nota de la font: "L'AVL també admet aquest/aquesta com a forma normativa
pròpia -- per això esta alternança és coneixement general de la variació
dialectal, no una equivalència mecànica derivada directament d'un
diccionari." És a dir: este/esta NO són "incorrectes" en cap dels dos
estàndards, però la substitució cap a aquest/aquesta és la conversió
esperada quan es vol el registre oriental dominant.

AMBIGÚ: la taula de la font no dona formes neutres (açò/això/allò) ni
aclarix si "eixe" ha de convertir-se sempre en "aqueix" o si en la parla
oriental real és més freqüent col·lapsar-lo cap a "aquell" -- s'implementa
ací EXACTAMENT el que diu la font (eixe -> aqueix), sense inventar cap
alternativa, perquè és l'única confirmada per escrit.
"""

from __future__ import annotations

from . import Token, preserva_majuscula

_DEMOSTRATIUS = {
    "este": "aquest",
    "esta": "aquesta",
    "estos": "aquests",
    "estes": "aquestes",
    "eixe": "aqueix",
    "eixa": "aqueixa",
    "eixos": "aqueixos",
    "eixes": "aqueixes",
}


class DemostratiusRule:
    """Substitueix demostratius occidentals per la seua forma oriental.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Este xiquet i eixes xiquetes.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Este', 'Aquest'), ('eixes', 'aqueixes')]

    Nom propi protegit encara que coincidisca amb un demostratiu (exemple
    sintètic -- cap topònim real es diu així, però la protecció ha de
    funcionar igual):

    >>> toks = tokenize("Anem a visitar Estos, un poble menut.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = _DEMOSTRATIUS.get(tok.surface.lower())
            if forma is None:
                continue
            tok.translated = preserva_majuscula(tok.surface, forma)
            tok.is_translated = True
        return tokens
