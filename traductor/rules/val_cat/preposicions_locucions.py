"""
preposicions_locucions.py -- Capa del pipeline que corregix la preposició
"a"/"en" en un grapat de LOCUCIONS CONCRETES on el valencià i el català
difereixen (categoria D de `traductor/README.md`, "ANÀLISI DE FALLADES
RESIDUALS" -- 5 frases del benchmark de 151, cadascuna amb 1 sola
evidència).

NO és una regla general "en"->"a" ni "a"->"en": es va comprovar que la
direcció correcta depén de l'expressió regida pel verb anterior, i fins
i tot DINS DE LA MATEIXA FRASE la mateixa preposició "a" es manté en un
cas i canvia en un altre -- RC137 té "elevar AL Consell" (sense tocar,
"al" és la contracció "a"+"el", no el nostre patró) i "elevar A les Corts
Valencianes" (canvia a "EN les Corts Valencianes") en la mateixa oració,
amb el mateix verb "elevar". No hi ha cap patró fonològic ni gramatical
que ho predigga, només la col·locació concreta. Per això, seguint el
mateix criteri que la resta del projecte (vore CLAUDE.md, "No hi ha
heurístiques automàtiques amplies"), cada cas és una entrada EXACTA en
una llista tancada -- mai una regla per sufix o paraula solta.

Casos coneguts (08/10/2026, cada un amb 1 sola evidència al benchmark de
151 frases -- s'amplia NOMÉS si apareixen més casos reals, p.ex. al
corpus del BOE):
    RC027 "vinculat A esta universitat"    -> "vinculat EN aquesta..."
    RC100 "està EN les seues mans"         -> "està A les seves mans"
    RC115 "seu EN la ciutat de València"   -> "seu A la ciutat de..."
    RC135 "està EN l'interior"             -> "està A l'interior"
    RC137 "elevar... A les Corts Valencianes" -> "...EN les Corts..."

Verificat contra la resta del benchmark abans d'afegir cada entrada
(`03_seleccio_de_model/benchmark_corpus.json`): "Corts Valencianes"
apareix també en RC031 (sense preposició, "de les Corts Valencianes") i
RC087 ("PER les Corts Valencianes") -- cap dels dos casa amb el patró
d'esta regla (que exigix el token EXACTE "a", no "de"/"per"), així que
no hi ha risc de tocar-los. "la ciutat" i "l'interior" només apareixen
una vegada cadascun a tot el benchmark.
"""

from __future__ import annotations

from .. import Token, paraula_anterior_es, paraules_segudents_son, preserva_majuscula

# Cada entrada: (paraula_exacta_abans | None, preposicio_origen,
# [paraules_despres], preposicio_desti). `paraula_abans`, si no es None,
# ha de ser el token real immediatament anterior (minuscules). Les
# paraules "despres" es comparen contra `tok.surface` (no `translated`),
# aixina la regla funciona siga quin siga l'orde d'esta capa respecte a
# `possessius.py`/`demostratius.py` (vore `paraules_segudents_son`).
_LOCUCIONS = [
    ("vinculat", "a", [], "en"),
    (None, "en", ["les", "seues", "mans"], "a"),
    (None, "en", ["la", "ciutat"], "a"),
    (None, "en", ["l'interior"], "a"),
    (None, "a", ["les", "corts", "valencianes"], "en"),
]


class PreposicionsLocucionsRule:
    """Corregix "a"/"en" en les 5 locucions conegudes (vore docstring del
    mòdul). Mai toca un token ja traduït ni un nom propi.

    >>> from .. import tokenize, marca_noms_propis, detokenize
    >>> toks = tokenize("Està vinculat a esta universitat.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('a', 'en')]

    >>> toks = tokenize("El futur està en les seues mans.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('en', 'a')]

    "en mans de" (sense "les"/"seues" davant) no es toca -- no casa amb
    la locució exacta:

    >>> toks = tokenize("Ho tenim en mans de tercers.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    >>> toks = tokenize("Tindrà la seu en la ciutat de València.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('en', 'a')]

    >>> toks = tokenize("El parèntesi està en l'interior de la frase.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('en', 'a')]

    >>> toks = tokenize("Cal elevar a les Corts Valencianes estes propostes.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('a', 'en')]

    La contracció "al" (a+el) no és el token "a" sol -- mai es toca,
    encara que vaja seguida d'una paraula coneguda (RC137, "elevar al
    Consell" es queda igual):

    >>> toks = tokenize("Cal elevar al Consell estes propostes.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Sense cap de les locucions, no toca res:

    >>> toks = tokenize("Vivim en una ciutat gran.")
    >>> marca_noms_propis(toks)
    >>> toks = PreposicionsLocucionsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()
            for paraula_abans, origen, despres, desti in _LOCUCIONS:
                if minuscules != origen:
                    continue
                if paraula_abans is not None and not paraula_anterior_es(tokens, i, paraula_abans):
                    continue
                if despres and not paraules_segudents_son(tokens, i, despres):
                    continue
                tok.translated = preserva_majuscula(tok.surface, desti)
                tok.is_translated = True
                break
        return tokens
