"""
elisio.py -- Elisió de "de"/"la"/"el" -> d'/l' davant paraula que comença
per vocal (o "h" muda + vocal). Font:
final/02_reglas_dialectales/reglas_dialectales.md, secció 11.2: "No és una
regla dialectal en si mateixa -- és ortografia catalana general que cal
aplicar cada vegada que una altra regla la dispara" (p.ex. si una altra
regla convertix "calfar" en "escalfar", "de calfar-nos" ha de passar a
"d'escalfar-nos", no quedar-se "de escalfar-nos"). Per això esta regla va
DARRERA de totes les altres al pipeline (vore engine.py): necessita vore
el resultat final de qualsevol substitució prèvia, no el text original.

Relació amb el tokenitzador (rules/__init__.py): "d'escola" ja arriba com
UN sol token des de tokenize() (l'apòstrof es tracta com a part de la
paraula, no com a frontera) -- per tant un token com eixe MAI casa amb
"de"/"la"/"el" exactes, i esta regla no el toca ni el duplica. Només actua
sobre "de"/"la"/"el" que apareixen com a PARAULA SOLTA (el seu propi
token), seguits d'un altre token que comença en vocal real.

A diferència de la resta de regles d'este paquet, `apply()` necessita
mirar el token SEGÜENT per a decidir, no només `tok` a soles -- per això
itera per índex en compte de per valor, encara que la firma pública
(`apply(tokens) -> tokens`) siga idèntica a la de totes les altres.

EXCEPCIÓ real (29/09/2026, no teoria): "la" (mai "el" ni "de") NO elideix
davant de cap paraula que comença per la LLETRA "i" o "u" (tònica o
àtona, s'escriga com s'escriga la síl·laba) -- "la intenció", "la idea",
"la universitat", mai "l'intenció"/"l'idea"/"l'universitat". No és un
fenomen fonètic (no depén de si eixa i/u sona com a vocal plena o com a
semiconsonant, a diferència del que es pensava abans -- vore baix), és
una convenció ortogràfica per a no perdre la distinció de gènere en la
lectura: si "la" també elidira, "l'univers" seria ambigu entre masculí i
femení; en no elidir mai "la" ahí, qualsevol "l'" + i/u es llig sense
ambigüitat com a masculí, i "la" + i/u sense elidir es llig sense
ambigüitat com a femení. "el"/"de" seguixen elidint amb normalitat davant
eixes mateixes paraules ("l'univers", "d'idea").

Este mateix mecanisme resol, com a efecte lateral, el cas "la iaia" que
abans es documentava ací com a AMBIGÚ sense arreglar (paraules que
comencen per "i"/"u" que sonen com a semiconsonant, p.ex. "iaia"): ara
"iaia" també cau dins de la regla general (comença per "i"), sense
necessitat de saber si eixa "i" sona com a vocal o com a consonant.

AMBIGÚ (documentat, no arreglat):
  - "h" muda: "home"/"hivern" SÍ eliden ("l'home", no "el home") perquè la
    h és muda en català/valencià -- este mòdul ho detecta (mira si comença
    per vocal O per h+vocal).
  - Dos elidibles seguits ("de" + "el"/"la"): en català/valencià real això
    mai apareix escrit així (seria una contracció, "del", ja una sola
    paraula) -- però si algun dia arribara un text amb eixa seqüència
    literal, esta regla els encadenaria malament (el primer "de" elidiria
    pensant que "el"/"la" comença en vocal). No s'ha protegit a propòsit:
    afegir eixa comprovació per un cas que no hauria d'aparéixer mai en
    text ben escrit no compensa la complexitat que afig.
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

_ELIDIBLES = {"de": "d'", "la": "l'", "el": "l'"}

# Vocal real, o "h" muda seguida de vocal (home, hivern...).
_COMENCA_EN_VOCAL_RE = re.compile(
    r"^(?:[aeiouàèéíòóúAEIOUÀÈÉÍÒÓÚ]|[hH][aeiouàèéíòóúAEIOUÀÈÉÍÒÓÚ])"
)

# Només per a "la" (vore docstring del mòdul): mai elideix davant de
# paraula que comence per la lletra i/u, en qualsevol accentuació.
_COMENCA_EN_I_U_RE = re.compile(r"^[iuíúIUÍÚ]")


def _seguent_token_no_buit(tokens: list[Token], index: int) -> int | None:
    """Índex del següent token que no és un espai en blanc, o None si
    s'acaba la llista abans de trobar-ne cap."""
    for j in range(index + 1, len(tokens)):
        if not tokens[j].surface.isspace():
            return j
    return None


class ElisioRule:
    """Elideix "de"/"la"/"el" davant paraula que comença en vocal (o h
    muda), buidant l'espai en blanc entremig perquè "d'" i la paraula
    següent queden enganxats en reconstruir el text amb detokenize().

    >>> from . import tokenize, detokenize, marca_noms_propis
    >>> toks = tokenize("Vinc de escola i de la altra ciutat.")
    >>> marca_noms_propis(toks)
    >>> toks = ElisioRule().apply(toks)
    >>> detokenize(toks)
    "Vinc d'escola i de l'altra ciutat."

    "h" muda també elideix:

    >>> toks = tokenize("Vinc de hui. Porte el hivern amagat.")
    >>> marca_noms_propis(toks)
    >>> detokenize(ElisioRule().apply(toks))
    "Vinc d'hui. Porte l'hivern amagat."

    Mai davant consonant (no toca "de casa"), i mai duplica una elisió que
    ja ve feta a l'original (com "d'escola" ja arriba com un sol token des
    de tokenize(), mai casa amb l'entrada del diccionari "de"):

    >>> toks = tokenize("Vinc de casa, no d'escola.")
    >>> marca_noms_propis(toks)
    >>> detokenize(ElisioRule().apply(toks)) == "Vinc de casa, no d'escola."
    True

    Decidix mirant `tok.translated`, NO `tok.surface` -- important perquè
    esta regla va DARRERA de totes les altres (vore docstring del mòdul):
    si una regla anterior ja ha canviat la paraula següent, l'elisió s'ha
    de basar en com queda de veritat, no en com estava escrita
    originalment. Regressió real trobada en proves: "huitanta" (h muda +
    vocal, elidiria) es convertix abans en "vuitanta" (consonant, NO
    elidix) -- mirar `surface` donava "d'vuitanta", incorrecte.

    >>> from .numerals import NumeralsRule
    >>> toks = tokenize("Parlem de huitanta persones.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> detokenize(ElisioRule().apply(toks))
    'Parlem de vuitanta persones.'

    "la" mai elideix davant de "i"/"u" (vore docstring del mòdul), encara
    que "el"/"de" sí ho facen amb normalitat davant les mateixes paraules:

    >>> toks = tokenize("La intenció, la idea i la universitat.")
    >>> marca_noms_propis(toks)
    >>> detokenize(ElisioRule().apply(toks))
    'La intenció, la idea i la universitat.'

    >>> toks = tokenize("Parle de idees i el univers.")
    >>> marca_noms_propis(toks)
    >>> detokenize(ElisioRule().apply(toks))
    "Parle d'idees i l'univers."

    Efecte lateral: "la iaia" tampoc elideix, encara que ahí "i" sone com
    a semiconsonant (abans documentat com a AMBIGÚ sense arreglar):

    >>> toks = tokenize("La iaia ha vingut.")
    >>> marca_noms_propis(toks)
    >>> detokenize(ElisioRule().apply(toks))
    'La iaia ha vingut.'
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            forma_elidida = _ELIDIBLES.get(minuscules)
            if forma_elidida is None:
                continue
            j = _seguent_token_no_buit(tokens, i)
            if j is None or not _COMENCA_EN_VOCAL_RE.match(tokens[j].translated):
                continue
            if minuscules == "la" and _COMENCA_EN_I_U_RE.match(tokens[j].translated):
                continue
            tok.translated = preserva_majuscula(tok.surface, forma_elidida)
            tok.is_translated = True
            for k in range(i + 1, j):
                tokens[k].translated = ""
                tokens[k].is_translated = True
        return tokens
