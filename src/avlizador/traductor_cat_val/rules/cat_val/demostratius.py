"""
cat_val/demostratius.py -- Demostratius en sentit invers: aquest -> este,
aqueix -> eixe (i les formes de femení i plural).

**Font: el lèxic del proveïdor (22/10/2026)**, igual que `possessius.py`:
es lligen les entrades de `traductor/data/lexic_general.json` amb
`categoria: "det"` que no són possessius (`fuente: "avl_equip"`, vore
`possessius.py`) -- E1619-E1626 a l'entrega del 21/10/2026. Substituïx
`demostratius_avl.json`, un paradigma fet a mà (30/09/2026).

"aquest" -> "este" és el que diu el lèxic. Coincidix amb el valor per
defecte mesurat el 13/10/2026 (40 de 52 casos reals del benchmark de 151,
~77%; la resta volien "eixe", una distinció de proximitat que ni spaCy ni
cap regla pot vore). "això" no hi és, així que es queda sense tocar;
"aquell"/"allò" són iguals als dos dialectes.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lexic_general.json"


def carrega_demostratius_invers(path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    """`{demostratiu català: valencià}` des del lèxic general.

    >>> lookup = carrega_demostratius_invers()
    >>> lookup["aqueix"], lookup["aqueixes"], lookup["aquest"], lookup["aquestes"]
    ('eixe', 'eixes', 'este', 'estes')
    >>> "això" in lookup, "meva" in lookup
    (False, False)
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        if entrada.get("categoria") != "det" or entrada.get("fuente") == "avl_equip":
            continue
        catalan = (entrada.get("catalan") or "").strip().lower()
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        if catalan and valenciano and catalan != valenciano:
            lookup[catalan] = valenciano
    return lookup


class DemostratiusInversRule:
    """Substitueix els demostratius catalans per la forma valenciana del
    lèxic.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Aqueixa dona i aqueixos xiquets.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Aqueixa', 'Eixa'), ('aqueixos', 'eixos')]

    >>> toks = tokenize("Aquest xiquet és bo.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Aquest', 'Este')]

    "això", "aquell" i "allò" es queden sense tocar:

    >>> toks = tokenize("Això és com aquell home i allò que vas dir.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Prefix elidit ("d'aqueix" -> "d'eixe"):

    >>> toks = tokenize("Vinc d'aqueix poble.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'aqueix", "d'eixe")]
    """

    def __init__(self, path: Path = LEXIC_GENERAL_PATH) -> None:
        self._lookup = carrega_demostratius_invers(path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
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
                aplica_amb_prefix_elidit(tokens, i, prefix, resta, forma)
                tok.is_translated = True
        return tokens
