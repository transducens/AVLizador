"""
conjugacions_dict.py -- Capa 2 del pipeline (justa despres de lexic.py):
lookup exacte de formes verbals a `traductor/data/conjugacions_dialectals.json`,
969 formes de 111 verbs on almenys una conjugacio difereix entre valencia i
catala, extretes de l'apertium bilingue catala-castella per Mauricio (equip
AVLizador, font externa al projecte, 29/09/2026).

Com lexic.py, esta capa fa un LOOKUP exacte (forma valenciana -> forma
catalana), no una regla morfologica -- i per aixo va MOLT PRIMERENCA al
pipeline (posicio 2, abans de morfologia_verbal.py): quan una forma ja es
coneguda amb precisio (p.ex. "oferisca" -> "ofereixi", una alternanca
irregular que la regla de sufix de fase 6 mai tocaria perque acaba en "-a"
no en "-ix"), no te sentit deixar que una regla de sufix mes feble intente
endevinar-la despres. Les regles de morfologia_verbal.py (fase 1/2/6) ja
salten qualsevol token amb `is_translated = True`, aixi que esta capa i
aquelles no es xoquen mai -- esta capa nomes cobrix EL SUBCONJUNT dels 111
verbs de la font, la resta seguix depenent de les regles de sufix generals.

Exclusio deliberada -- formes "problematica" (65 de les 969): en valencia
hi ha verbs on la mateixa forma escrita servix per al present d'indicatiu
I al de subjuntiu ("abalance" = "jo abalanco" en indicatiu / "que jo
abalanci" en subjuntiu), mentre que en catala son formes diferents
("abalanco" / "abalanci"). Sense pos-tagging no hi ha manera fiable de
saber quin dels dos toca -- Mauricio mateix ho documenta com "hara falta
un mecanisme de desambiguacio". Esta capa, seguint el mateix criteri
conservador que la resta del projecte (preferir un fals negatiu -- deixar
la paraula sense traduir -- abans que un fals positiu), EXCLOU del lookup
qualsevol entrada marcada `problematica: true`. Es queden documentades al
JSON de dades per si en el futur s'afig eixe mecanisme de desambiguacio.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Token, preserva_majuscula, separa_prefix_elidit

DEFAULT_CONJUGACIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "conjugacions_dialectals.json"
)


def carrega_conjugacions(path: Path = DEFAULT_CONJUGACIONS_PATH) -> dict[str, str]:
    """Llig el JSON de conjugacions i el converteix en un diccionari pla
    `{forma_valenciana_en_minuscules: forma_catalana}`, descartant les
    entrades `problematica: true` (vore docstring del modul).

    >>> lookup = carrega_conjugacions()
    >>> lookup["oferisca"]
    'ofereixi'
    >>> lookup["tinguen"]
    'tinguin'
    >>> lookup["traure"]
    'treure'
    >>> "abalance" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades.get("entradas", []):
        if entrada.get("problematica"):
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip()
        if not valenciano or not catalan:
            continue
        lookup.setdefault(valenciano, catalan)
    return lookup


class ConjugacionsDictRule:
    """Substitueix formes verbals valencianes conegudes per la seua forma
    catalana, segons `conjugacions_dialectals.json`. Mai toca un token ja
    traduit per una capa anterior (`is_translated`) ni un possible nom
    propi (`is_proper_noun`).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Els vaig oferisca ajuda encara que tinguen pressa.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('oferisca', 'ofereixi'), ('tinguen', 'tinguin')]

    Formes "problematica" (ambigues entre indicatiu i subjuntiu) no es
    toquen -- vore docstring del modul:

    >>> toks = tokenize("Jo abalance la pilota.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Forma enganxada a un prefix elidit ("s'", "l'"...), mateix mecanisme
    que `lexic.py` (vore `separa_prefix_elidit` a rules/__init__.py):

    >>> toks = tokenize("Vull que s'oferisca ajuda.")
    >>> marca_noms_propis(toks)
    >>> toks = ConjugacionsDictRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("s'oferisca", "s'ofereixi")]
    """

    def __init__(self, path: Path = DEFAULT_CONJUGACIONS_PATH) -> None:
        self._lookup = carrega_conjugacions(path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = self._lookup.get(tok.surface.lower())
            if forma is not None:
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                continue
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            forma = self._lookup.get(resta.lower())
            if forma is not None:
                tok.translated = prefix + preserva_majuscula(resta, forma)
                tok.is_translated = True
        return tokens
