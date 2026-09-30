"""
demostratius.py -- Pronoms/adjectius demostratius: este/eixe/aqueix
(occidental) -> aquest (oriental), tots tres col·lapsats a la mateixa
forma, més el neutre açò->això. Recreat 30/09/2026 (s'havia llevat del
tot en passar a "pur diccionari de Mauricio" el mateix dia, però cap
diccionari pot cobrir un paradigma gramatical tancat que Mauricio
senzillament no llista -- vore `traductor/README.md`, secció "DECISIÓ
D'ARQUITECTURA").

Font de dades: `traductor/data/demostratius_avl.json`, sourced de
`reglas_dialectales_con_evidencia.md` §1 + coneixement dialectològic
general (cap fitxer de Mauricio llista estes formes -- són paraules
gramaticals tancades, no lèxic obert).

DECISIÓ (heretada, confirmada): el sistema de 3 graus este/eixe/aquell ->
aquest/aqueix/aquell és el que admeten totes dos normatives (AVL i IEC)
sobre el paper, però l'ús real de l'oriental contemporani ha col·lapsat el
2n grau cap al 1r: "aqueix" es percep com a forma arcaica/literària, rara
fora de registre molt formal, mentre que "aquest" cobrix en la pràctica
els dos usos. Per coherència, si "aqueix" mateix apareix en un text
occidental (l'AVL també l'admet com a forma culta), es tradueix igual cap
a "aquest" -- no té sentit tractar-lo distint d'"eixe" si el resultat
oriental real és el mateix.

"aqueix" NO desapareix del tot: seguix sent la forma normativa i encara
apareix (rar) en textos orientals formals/literaris. Si mai es fa
traducció en sentit invers (oriental -> occidental), la taula inversa
("aqueix"->"eixe", no ->"este") ja es queda documentada al fitxer de
dades, sense implementar-se -- este motor només tradueix occidental ->
oriental.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

AVL_PATH = Path(__file__).resolve().parent.parent / "data" / "demostratius_avl.json"


def carrega_demostratius(path: Path = AVL_PATH) -> dict[str, str]:
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(dades["entrades_actives_occidental_a_oriental"])


class DemostratiusRule:
    """Substitueix demostratius occidentals (este/eixe/aqueix + el
    neutre açò) per la seua forma oriental.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Este xiquet i eixes xiquetes i aqueixa dona.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Este', 'Aquest'), ('eixes', 'aquestes'), ('aqueixa', 'aquesta')]

    El neutre "açò" -> "això":

    >>> toks = tokenize("Açò és molt important.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Açò', 'Això')]

    "aquell" (i el neutre "allò") mai canvien -- són idèntics als dos
    dialectes, per això no tenen entrada a la taula:

    >>> toks = tokenize("Aquell home i allò que vas dir.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

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
    `separa_prefix_elidit` a rules/__init__.py. Bug real ja trobat una
    vegada (29/09/2026), recreat ací junt amb la resta del mòdul:

    >>> toks = tokenize("Sé que d'este poble és bo.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("d'este", "d'aquest")]
    """

    def __init__(self, path: Path = AVL_PATH) -> None:
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
