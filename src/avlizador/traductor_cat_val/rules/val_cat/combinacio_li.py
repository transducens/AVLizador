"""
val_cat/combinacio_li.py -- Regla B4 de la guia de traducció dialectal
(`pipeline/02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md`):
combinació de datiu singular + acusatiu de 3a persona. Afegida el
21/10/2026.

En valencià el datiu "li" va DAVANT de l'acusatiu ("li'l", "li la", "li
les", "li'ls"); en català central el datiu pren la forma "hi" i va DARRERE
("l'hi", "la hi", "les hi", "els hi"). GNV §22.4.2 ho explica amb els
mateixos exemples ("L'hi he donat (per Li l'he donat)", "Ja la hi donaré
(per Ja li la donaré)"); GEIEC §16.4.

PER QUÈ ÉS DETERMINISTA EN ESTA DIRECCIÓ I NO EN L'ALTRA (vore
`documentacio/hoja_de_ruta_traductor_invers.md`, "B4 -- análisis"): el
català "l'hi" té quatre lectures (li + acusatiu, li + ho, acusatiu + hi
locatiu, datiu plural), i només el significat les distingix -- per això
en cat->val va a la capa de LLM. En canvi, les formes valencianes són
inequívoques: "li'l" sempre és li + el. L'única trampa és "li la"/"li les",
que pot ser el pronom "li" seguit d'un ARTICLE ("donar-li la resposta",
"facilitar-li les coses" -- la majoria dels casos reals de la AVL).

Es va pensar a demanar a spaCy si "la" és PRON, pero NO funciona: provat
el 21/10/2026, spaCy etiqueta "la" com a DET (article) en "Ja li la
donaré" i fins i tot "donaré" com a NOUN -- no coneix esta construcció
valenciana. La gramàtica ho resol sense spaCy: l'article només pot vindre
darrere d'un "li" ENCLÍTIC ("exposar-li la meua queixa"), que el
tokenitzador ja tracta com UN sol token amb el verb, i esta regla no el
toca. Un "li" SOLT sempre és proclític, i darrere d'un proclític només hi
pot haver un altre pronom o el verb, mai un article. Per tant "li" solt +
"la"/"les" és sempre pronom + pronom. Les formes enclítiques amb guionet
("dona-li-la") també són pronom per escriptura.

| Valencià | Català central |
|---|---|
| li'l porte | l'hi porto |
| li'ls porte | els hi porto |
| li l'he portat | l'hi he portat |
| li la done | la hi dono |
| li les done | les hi dono |
| porta-li'l | porta-l'hi |
| dona-li-la | dona-la-hi |
| dona-li-les | dona-les-hi |
| porta-li'ls | porta'ls-hi (darrere vocal) / fer-los-hi (darrere consonant) |

"li ho" i "li'n" són iguals als dos estàndards i no es toquen.
"""

from __future__ import annotations

from .. import Token, preserva_majuscula

_VOCALS = "aeiouàèéíòóú"

_PROCLITICS = {"li'l": "l'hi", "li'ls": "els hi"}


def _seguent(tokens: list[Token], index: int) -> int | None:
    for j in range(index + 1, len(tokens)):
        if not tokens[j].surface.isspace():
            return j
    return None


def _enclitic(surface: str) -> str | None:
    """Forma catalana d'un verb amb enclític valencià li+acusatiu, o None.

    >>> _enclitic("porta-li'l"), _enclitic("dona-li-la"), _enclitic("dona-li-les")
    ("porta-l'hi", 'dona-la-hi', 'dona-les-hi')
    >>> _enclitic("porta-li'ls"), _enclitic("fer-li'ls")
    ("porta'ls-hi", 'fer-los-hi')
    >>> _enclitic("dona-li-ho") is None
    True
    """
    baix = surface.lower()
    for sufix, cat in (("-li'l", "-l'hi"), ("-li-la", "-la-hi"), ("-li-les", "-les-hi")):
        if baix.endswith(sufix):
            return surface[: -len(sufix)] + cat
    if baix.endswith("-li'ls"):
        arrel = surface[: -len("-li'ls")]
        return arrel + ("'ls-hi" if arrel[-1:].lower() in _VOCALS else "-los-hi")
    return None


class CombinacioLiRule:
    """Reordena li + acusatiu a la forma del català central (vore
    docstring del mòdul).

    >>> from .. import tokenize, marca_noms_propis, detokenize, pos_tagger
    >>> def prova(text):
    ...     toks = tokenize(text)
    ...     marca_noms_propis(toks)
    ...     pos_tagger.etiqueta(toks)
    ...     return detokenize(CombinacioLiRule().apply(toks))
    >>> prova("Li'l compraré demà.")
    "L'hi compraré demà."
    >>> prova("Li l'he portat.")
    "L'hi he portat."
    >>> prova("Ja li la donaré.")
    'Ja la hi donaré.'
    >>> prova("Porta-li'l tu.")
    "Porta-l'hi tu."

    "-li" enclític seguit d'un ARTICLE no es toca (és un sol token amb el
    verb; vore docstring del mòdul):

    >>> prova("Vull exposar-li la meua queixa.")
    'Vull exposar-li la meua queixa.'
    >>> prova("Li ho diré demà.")
    'Li ho diré demà.'
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun or tok.surface.isspace():
                continue
            baix = tok.surface.lower()
            if baix in _PROCLITICS:
                tok.translated = preserva_majuscula(tok.surface, _PROCLITICS[baix])
                tok.is_translated = True
                continue
            enclitic = _enclitic(tok.surface)
            if enclitic is not None:
                tok.translated = enclitic
                tok.is_translated = True
                continue
            if baix != "li":
                continue
            j = _seguent(tokens, i)
            if j is None or tokens[j].is_translated:
                continue
            seguent = tokens[j]
            seg_baix = seguent.surface.lower()
            if seg_baix.startswith("l'") and len(seg_baix) > 2:
                # "li l'he portat" -> "l'hi he portat"
                tok.translated = preserva_majuscula(tok.surface, "l'hi")
                seguent.translated = seguent.surface[2:]
            elif seg_baix in ("la", "les"):
                # "li la done" -> "la hi done": "li" solt és proclític, així
                # que "la" ha de ser pronom (vore docstring del mòdul)
                tok.translated = preserva_majuscula(tok.surface, seg_baix)
                seguent.translated = "hi"
            else:
                continue
            tok.is_translated = True
            seguent.is_translated = True
        return tokens
