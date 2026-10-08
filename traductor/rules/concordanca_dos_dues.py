"""
concordanca_dos_dues.py -- Corregix "dos" -> "dues" quan el token
immediatament anterior és un article o demostratiu que ja marca per si
mateix femení plural ("les", "estes", "eixes", "aqueixes", "aquelles",
"unes"). "dos"/"dues" s'escriuen igual als dos dialectes (no és una
substitució lèxica Mauricio), però el valencià col·loquial sovint fa
servir "dos" invariable també davant de femení -- este mòdul corregix
eixe desacord de gènere, NO traduïx cap paraula nova.

SENYAL TRIADA (primera capa, la més segura -- vore conversa 01/10/2026):
el token anterior ja és gramaticalment inequívoc per si mateix (ningú diu
"els estes" ni "el les"), així que comprovar-lo és precisió ~100% sense
necessitar cap diccionari ni heurística de sufix. Verificat contra els 150
casos del benchmark: de ~28 frases amb "dos"->"dues" real, 13 anaven
precedides directament per un d'estos marcadors ("les dos institucions",
"estes dos circumstàncies", "estes dos veus"...). La resta (casos "pelats"
sense article/demostratiu davant, com "dos entitats" o "dos xifres")
necessiten mirar el SUFIX de la paraula següent -- eixa és la segona capa
pendent, NO implementada ací a propòsit (vore nota baix).

SEGONA CAPA (afegida 08/10/2026): quan no hi ha marcador explícit davant,
es consulta `Token.gender` (spaCy, capa 0 opcional, vore `pos_tagger.py`)
de la primera paraula NOUN/ADJ després de "dos" -- cobrix "dos entitats"
(entitats=NOUN Fem) i "dos terceres parts" (terceres=ADJ Fem, ja resol
sense arribar al nom). NOMÉS s'actua quan spaCy diu Fem explícitament; si
diu Masc, buit, o spaCy no està instal·lat, no es toca res -- preferix fals
negatiu (vore `pos_tagger.py`: provat amb 5 frases reals, 6/7 paraules
rellevants be etiquetades, pero "consonants" ix Masc per error, així que
"dos consonants" es queda SENSE corregir amb esta capa -- acceptat, no
s'afig cap llista curada mentre no es trobe evidencia real que calga).

RISC CONEGUT (acceptat): el corpus benchmark mateix és inconsistent en 2
casos (RC112, RC120) on "dos" + nom femení ("dos llengües") es deixa
SENSE corregir a la referència, perquè és una cita literal de registre
antic/dialectal. Esta regla la corregiria igualment (gramaticalment és
correcte fer-ho), encara que no casara amb eixes 2 referències concretes.
Acceptat conscientment: preferix corregir bé la immensa majoria a canvi de
2 falsos "desacords" en cites literals, en compte de no corregir res.
"""

from __future__ import annotations

from . import Token, preserva_majuscula

# Articles/demostratius valencians que ja marquen femení plural per si
# mateixos -- mai ambigus, mai coincidixen amb la forma masculina.
_MARCADORS_FEMENI_PLURAL = {"les", "estes", "eixes", "aqueixes", "aquelles", "unes"}


class ConcordancaDosDuesRule:
    """Corregix "dos" -> "dues" quan el precedix un marcador de femení
    plural (vore docstring del mòdul per a la llista i el raonament).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Les dos institucions han firmat un conveni.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dos', 'dues')]

    >>> toks = tokenize("Estes dos circumstàncies s'han destacat.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dos', 'dues')]

    Sense marcador davant, la segona capa (spaCy, `Token.gender`) detecta
    el femení del nom/adjectiu següent -- nomes funciona si s'ha cridat
    `pos_tagger.etiqueta()` abans (com fa `RuleEngine`; en estos doctests
    es crida a mà):

    >>> from . import pos_tagger
    >>> toks = tokenize("Hem creat dos entitats noves.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dos', 'dues')]

    Sense spaCy disponible (`gender` buit per a tots els tokens), esta
    capa no fa res -- es queda igual que abans:

    >>> toks = tokenize("Hem creat dos entitats noves.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Davant de masculí no toca res, encara que hi haja un marcador plural
    just abans (els és masculí, mai activa la regla):

    >>> toks = tokenize("Els dos verbs eren irregulars.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Primer token de la frase: no hi ha anterior que comprovar, no peta:

    >>> toks = tokenize("Dos dies després va tornar.")
    >>> marca_noms_propis(toks)
    >>> toks = ConcordancaDosDuesRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            if tok.surface.lower() != "dos":
                continue
            if not (_marcador_femeni_abans(tokens, i) or _femeni_despres(tokens, i)):
                continue
            tok.translated = preserva_majuscula(tok.surface, "dues")
            tok.is_translated = True
        return tokens


def _marcador_femeni_abans(tokens: list[Token], index: int) -> bool:
    """Com `paraula_anterior_es` de `rules/__init__.py` (salta espais en
    blanc), però comprova pertinença a `_MARCADORS_FEMENI_PLURAL` en
    compte d'una sola paraula exacta."""
    for tok in reversed(tokens[:index]):
        if tok.surface.isspace():
            continue
        return tok.surface.lower() in _MARCADORS_FEMENI_PLURAL
    return False


def _femeni_despres(tokens: list[Token], index: int) -> bool:
    """Segona capa (vore docstring del mòdul): mira la primera paraula
    NOUN/ADJ després de "dos" i comprova `Token.gender` (spaCy, capa 0
    opcional). Nomes torna `True` quan diu "Fem" explícitament -- buit
    (spaCy no disponible o paraula no reconeguda) o "Masc" no activen la
    regla, mateixa filosofia de preferir fals negatiu que la resta del
    projecte."""
    for tok in tokens[index + 1 :]:
        if tok.surface.isspace():
            continue
        if tok.pos not in ("NOUN", "ADJ"):
            return False
        return tok.gender == "Fem"
    return False
