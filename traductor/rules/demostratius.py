"""
demostratius.py -- Pronoms/adjectius demostratius: este/eixe (occidental)
-> aquest (oriental), tots dos col·lapsats a la mateixa forma. Taula
copiada de final/02_reglas_dialectales/reglas_dialectales_con_evidencia.md,
secció 1 -- NO inventada ací.

És la regla morfològica MÉS freqüent del corpus (apareix en quasi totes les
frases), i una de les que el LLM del benchmark complia amb més
regularitat -- bon candidat per a una regla 100% determinista.

Nota de la font: "L'AVL també admet aquest/aquesta com a forma normativa
pròpia -- per això esta alternança és coneixement general de la variació
dialectal, no una equivalència mecànica derivada directament d'un
diccionari." És a dir: este/esta NO són "incorrectes" en cap dels dos
estàndards, però la substitució cap a aquest/aquesta és la conversió
esperada quan es vol el registre oriental dominant.

DECISIÓ REVISADA (eixe -> aquest, no aqueix): el sistema de 3 graus
este/eixe/aquell -> aquest/aqueix/aquell és el que admeten totes dos
normatives (AVL i IEC) sobre el paper, i és el que este mòdul va
implementar primer. Però l'ús real de l'oriental contemporani (confirmat
en analitzar el benchmark de qwen3:14b i el corpus sintètic generat) ha
col·lapsat pràcticament del tot el 2n grau cap al 1r: "aqueix" es percep
com a forma arcaica/literària, rara fora de registre molt formal, mentre
que "aquest" cobrix en la pràctica els dos usos (proximitat al parlant I
a l'oient). Per això ara "eixe" -> "aquest", igual que "este" -> "aquest"
-- els dos graus es fusionen en un de sol al costat oriental.

"aqueix" NO desapareix del tot: seguix sent la forma normativa i encara
apareix (rar) en textos orientals formals/literaris. Si mai es fa
traducció en sentit invers (oriental -> occidental), "aqueix" trobat en
un text ha de tornar cap a "eixe", no cap a "este" -- és l'equivalència
inversa d'esta mateixa decisió, documentada ací per si mai s'implementa
eixe sentit.
"""

from __future__ import annotations

from . import Token, preserva_majuscula, separa_prefix_elidit

_DEMOSTRATIUS = {
    "este": "aquest",
    "esta": "aquesta",
    "estos": "aquests",
    "estes": "aquestes",
    "eixe": "aquest",
    "eixa": "aquesta",
    "eixos": "aquests",
    "eixes": "aquestes",
}


class DemostratiusRule:
    """Substitueix demostratius occidentals per la seua forma oriental.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Este xiquet i eixes xiquetes.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Este', 'Aquest'), ('eixes', 'aquestes')]

    Nom propi protegit encara que coincidisca amb un demostratiu (exemple
    sintètic -- cap topònim real es diu així, però la protecció ha de
    funcionar igual):

    >>> toks = tokenize("Anem a visitar Estos, un poble menut.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Demostratiu enganxat a un prefix elidit ("d'este", "d'eixe"...): sense
    això es queda sense traduir, perquè el token sencer ("d'este") mai
    casa amb l'entrada del diccionari ("este") -- vore
    `separa_prefix_elidit` a rules/__init__.py. Bug real trobat en
    auditar les proves de 29/09/2026.

    >>> toks = tokenize("Sé que d'este poble és bo.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'este", "d'aquest")]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = _DEMOSTRATIUS.get(tok.surface.lower())
            if forma is not None:
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = _DEMOSTRATIUS.get(resta.lower())
            if forma is not None:
                tok.translated = prefix + preserva_majuscula(resta, forma)
                tok.is_translated = True
        return tokens
