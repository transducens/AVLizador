"""
cat_val/incoatius.py -- Verbs incoatius "-eix" (català) -> "-ix" (valencià):
serveix->servix, ofereixen->oferixen, produeix->produïx... SENSE cap
llista de verbs a mà (reescrit 20/10/2026, decisió de l'usuari).

EL PROBLEMA
===========
Els verbs incoatius de la 3a conjugació (servir, oferir, produir...)
afigen un increment entre l'arrel i la terminació en el present. Català
central: "-eix-" (serveix, serveixes, serveixen). Valencià: "-ix-"
(servix, servixes, servixen). L'AVL accepta les dos formes en valencià,
i per això el proveïdor NO les llista com a parell dialectal:
`conjugacions_dialectals.json` porta, de "servir", "serveixo"->"servisc"
(1a persona) i tot el subjuntiu ("serveixi"->"servisca"...), pero NO
porta "serveix"/"serveixes"/"serveixen" (2a i 3a persona del singular,
3a del plural i l'imperatiu). Estes formes no estan a cap JSON, així que
cap lookup les pot trobar. I són justament les més freqüents: en els
corpus (151 + gplsi, 2.109 frases) el valencià de referència fa servir
"-ix" en el 100% dels casos reals mesurats (198/198).

PER QUÈ NO SERVIX UNA REGLA DE SUFIX PURA
=========================================
En català "-eix" no identifica un verb incoatiu. Acaben igual:
  - verbs incoatius en "-ir" (ha de canviar): serveix, produeix, requereix
  - verbs en "-èixer" (MAI canvia): apareix, coneix, creix, mereix
    ("neix" canvia d'arrel, "naix", cosa que tampoc és este patró)
  - paraules que no són verbs: mateix, peix, feix, aqueix
El valencià distingix les dos classes de verbs per escrit (servix vs.
apareix); el català les fon totes en "-eix". La diferència és LÈXICA:
depén de quin verb és. Per això l'anterior versió feia servir una llista
tancada de 7 arrels a mà (retirada el mateix 20/10/2026).

LA SOLUCIÓ: spaCy + els nostres JSON
====================================
Es canvia "-eix" per "-ix" NOMÉS si es complixen les tres condicions:
  1. spaCy diu que el token és VERB/AUX (descarta "mateix", "peix"...);
  2. el lema d'spaCy acaba en "-ir" (descarta "créixer", "conèixer"...);
  3. eixe lema existix com a infinitiu a `conjugacions_dialectals.json`
     (camps `verbo`, `infinitiu_cat`, `infinitiu_val`).
La condició 3 fa falta perquè spaCy s'inventa lemes per als verbs que no
coneix: "apareix" -> "aparir", "coneix" -> "conir", "neix" -> "nir". Cap
d'eixos "infinitius" existix als nostres JSON, així que queden fora sense
cap llista d'excepcions. A més, la forma ha de ser exactament arrel del
lema + "eix" + terminació ("serveix" = "serv" + "eix"), per a no fiar-se
d'un lema que no quadre amb la paraula.

Terminacions cobertes: "" (serveix), "es" (serveixes), "en" (serveixen).
La resta ("serveixo", "serveixi"...) ja venen del JSON de conjugacions i
les tradueix `conjugacions_dict.py` abans que corra esta regla. Si l'arrel
acaba en vocal es posa dièresi: "produeix" -> "produïx", "posseeix" ->
"posseïx" -- excepte "gu"/"qu", on la "u" no sona: "aconsegueix" ->
"aconseguix".

Mesurat contra els corpus (20/10/2026, abans d'escriure el codi): 198
conversions correctes, 0 lemes inventats colats, 1 cas dubtós
("conquereix", 1 aparició, la referència el deixa igual). Pèrdua
coneguda i acceptada: quan spaCy etiqueta el verb com a nom propi a
l'inici de frase ("Floreix...", PROPN), no es toca (preferix fals
negatiu). Tampoc es toca el verb amb pronom enclític enganxat
("Serveix-li"): spaCy el partix en dos tokens i `pos_tagger.etiqueta()`
no el troba, així que el token es queda sense `pos`/`lemma`. Sense spaCy
instal·lat la regla no fa res: no hi ha manera de validar el lema.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, preserva_majuscula, separa_prefix_elidit, separa_sufix_elidit

DEFAULT_CONJUGACIONS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "conjugacions_dialectals.json"
)

_TERMINACIONS = ("", "es", "en")
_VOCALS = set("aeiouàèéíòóúïü")


def carrega_infinitius_ir(path: Path = DEFAULT_CONJUGACIONS_PATH) -> set[str]:
    """Tots els infinitius en "-ir" que apareixen a `conjugacions_dialectals.json`.

    >>> infinitius = carrega_infinitius_ir()
    >>> {"servir", "produir", "oferir"} <= infinitius
    True
    >>> "aparir" in infinitius
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    infinitius: set[str] = set()
    for entrada in dades.get("entradas", []):
        for camp in ("verbo", "infinitiu_cat", "infinitiu_val"):
            valor = (entrada.get(camp) or "").strip().lower()
            if valor.endswith("ir") and " " not in valor:
                infinitius.add(valor)
    return infinitius


def converteix_incoatiu(paraula: str, lema: str) -> str | None:
    """Si `paraula` és arrel de `lema` + "eix" + terminació coberta, torna
    la forma valenciana; si no, `None`.

    >>> converteix_incoatiu("serveix", "servir")
    'servix'
    >>> converteix_incoatiu("ofereixen", "oferir")
    'oferixen'
    >>> converteix_incoatiu("produeix", "produir")
    'produïx'

    La "u" de "gu"/"qu" no sona, així que no porta dièresi:

    >>> converteix_incoatiu("aconsegueix", "aconseguir")
    'aconseguix'
    >>> converteix_incoatiu("serveixo", "servir") is None
    True
    """
    arrel = lema[:-2]
    for terminacio in _TERMINACIONS:
        if paraula == arrel + "eix" + terminacio:
            vocal_sonora = arrel[-1:] in _VOCALS and not arrel.endswith(("gu", "qu"))
            increment = "ïx" if vocal_sonora else "ix"
            return arrel + increment + terminacio
    return None


class IncoatiusInversRule:
    """Substitueix "-eix" per "-ix" en verbs incoatius validats per spaCy i
    pels JSON de conjugacions (vore docstring del mòdul).

    >>> from .. import tokenize, marca_noms_propis, detokenize, pos_tagger
    >>> toks = tokenize("Això serveix i ells ofereixen el que es produeix.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> detokenize(IncoatiusInversRule().apply(toks))
    'Això servix i ells oferixen el que es produïx.'

    Verbs en "-èixer" mai es toquen (lema inventat per spaCy, no és als JSON),
    ni les paraules que no són verbs:

    >>> toks = tokenize("El problema apareix i el coneix ell mateix.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in IncoatiusInversRule().apply(toks) if t.is_translated]
    []

    Prefix elidit i pronom enclític es conserven:

    >>> toks = tokenize("Açò s'aconsegueix fàcilment.")
    >>> marca_noms_propis(toks)
    >>> pos_tagger.etiqueta(toks)
    >>> [(t.surface, t.translated) for t in IncoatiusInversRule().apply(toks) if t.is_translated]
    [("s'aconsegueix", "s'aconseguix")]
    """

    def __init__(self, path: Path = DEFAULT_CONJUGACIONS_PATH) -> None:
        self._infinitius = carrega_infinitius_ir(path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            if tok.pos not in ("VERB", "AUX"):
                continue
            if tok.lemma not in self._infinitius:
                continue
            paraula = tok.surface
            prefix = ""
            sufix = ""
            sufix_resta = separa_sufix_elidit(paraula)
            if sufix_resta is not None:
                paraula, sufix = sufix_resta
            prefix_resta = separa_prefix_elidit(paraula)
            if prefix_resta is not None:
                prefix, paraula = prefix_resta
            nova = converteix_incoatiu(paraula.lower(), tok.lemma)
            if nova is None:
                continue
            tok.translated = prefix + preserva_majuscula(paraula, nova) + sufix
            tok.is_translated = True
        return tokens
