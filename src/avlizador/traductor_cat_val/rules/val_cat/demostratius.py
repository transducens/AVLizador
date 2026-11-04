"""
demostratius.py -- Pronoms/adjectius demostratius: este -> aquest,
eixe -> aqueix (i les formes de femení i plural).

**Font: el lèxic del proveïdor (22/10/2026)**, igual que `possessius.py`:
es lligen les entrades de `traductor/data/lexic_general.json` amb
`categoria: "det"` que no són possessius (`fuente: "avl_equip"`, vore
`possessius.py`). Substituïx `demostratius_avl.json`, un paradigma fet a
mà (30/09/2026) que col·lapsava este/eixe/aqueix cap a "aquest" i
convertia el neutre "açò" -> "això". Amb el lèxic, "eixe" passa a
"aqueix" (la forma normativa del 2n grau) i "açò" es queda sense tocar,
perquè el proveïdor no porta cap d'estes dos decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lexic_general.json"


def carrega_demostratius(path: Path = LEXIC_GENERAL_PATH) -> dict[str, str]:
    """`{demostratiu valencià: català}` des del lèxic general.

    >>> lookup = carrega_demostratius()
    >>> lookup["este"], lookup["estes"], lookup["eixa"]
    ('aquest', 'aquestes', 'aqueixa')
    >>> "meua" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades:
        if entrada.get("categoria") != "det" or entrada.get("fuente") == "avl_equip":
            continue
        valenciano = (entrada.get("valenciano") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if valenciano and catalan and valenciano != catalan:
            lookup[valenciano] = catalan
    return lookup


class DemostratiusRule:
    """Substitueix els demostratius valencians per la forma catalana del
    lèxic.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Este xiquet i eixes xiquetes.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Este', 'Aquest'), ('eixes', 'aqueixes')]

    "aquell" i "allò" mai canvien:

    >>> toks = tokenize("Aquell home i allò que vas dir.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Nom propi protegit i prefix elidit:

    >>> toks = tokenize("Anem a visitar Estos, un poble menut.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    >>> toks = tokenize("Sé que d'este poble és bo.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'este", "d'aquest")]
    """

    def __init__(self, path: Path = LEXIC_GENERAL_PATH) -> None:
        self._lookup = carrega_demostratius(path)

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
