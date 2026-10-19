"""
cat_val/demostratius.py -- Pronoms/adjectius demostratius en sentit
invers (vore docstring del mòdul principal, `rules/val_cat/demostratius.py`,
i la hoja de ruta). Reutilitza el MATEIX fitxer
`traductor/data/demostratius_avl.json`.

**"aqueix" (forma normativa oriental del 2n grau)** trobat en text català
real NOMÉS pot tornar cap a "eixe" -- mai cap a "este", perquè si l'autor
volia dir "este" ja hauria escrit "aquest" directament. És l'entrada del
paradigma sense ambigüitat real -- ve del camp `invers_pendent_no_implementat`
del fitxer de dades, ja dibuixada el 30/09/2026 quan es va construir la
direcció val->cat, sense implementar-se fins el 08/10/2026.

**"aquest" -- DEFAULT "este" (canviat el 13/10/2026, decisió mesurada,
no un oblit)**: "aquest" és AMBIGU DE VERITAT -- pot vindre d'"este" (1r
grau) o d'"eixe" (2n grau col·lapsat cap a "aquest" en l'ús real oriental,
vore `rules/val_cat/demostratius.py`). Cap senyal del text per si sol (ni
POS ni gènere) ho resol -- és una distinció de proximitat discursiva, no
gramatical.

Es va provar primer deixar "aquest" SENSE TOCAR (preferir fals negatiu,
mateixa filosofia que la resta del projecte). Mesurat contra el benchmark
de 151 frases: **el benchmark SENCER va baixar de 92/151 a 44/151** --
deixar-ho sense tocar no és un "fals negatiu" barat ací, és perdre TOTS
els casos (107 aparicions de "aquest*" al benchmark, bastants mes que
els altres fenòmens d'esta direcció junts). Abans de descartar l'opció
de triar un valor per defecte, es va comptar la proporció real alineant
paraula a paraula les 151 frases (`difflib` sobre `oriental`/`occidental`):
de 52 casos on "aquest*" canvia de veres, **40 van a "este" i només 12 a
"eixe"** (~77%/23%) -- el mateix patró que ja vam confirmar fa dies en
sentit contrari (l'ús real oriental col·lapsa "eixe" cap a "aquest", així
que la majoria dels "aquest" reals VENIEN d'"este" per començar).

Per això ara SÍ es tradueix "aquest"->"este" (i el seu paradigma) per
defecte -- un valor per defecte MESURAT, amb un 23% d'error conegut i
acceptat, no una suposició. La Fase 3 de la hoja de ruta (desambiguació
assistida per LLM, mateix patró que `pipeline/08_traduccio_corpus/postprocessat_llm/`
ja fa per a indicatiu/subjuntiu) és l'única manera de pujar per damunt
d'eixe 77% -- pendent, no implementada encara.

El neutre "això" es queda SENSE TOCAR: 0 aparicions amb canvi real al
benchmark de 151 (ni a favor d'"açò" ni en contra) -- sense evidència no
es tria cap valor per defecte, mateix criteri que la resta del projecte.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import Token, aplica_amb_prefix_elidit, preserva_majuscula, separa_prefix_elidit

AVL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "demostratius_avl.json"


# "aquest"->"este" (i el seu paradigma): DEFAULT mesurat, no una
# suposició -- vore docstring del mòdul per a la proporció real (40/52,
# ~77%, mesurada alineant les 151 frases del benchmark paraula a
# paraula). NOMÉS el grau "este" es dona per defecte -- "eixe"/"aqueix"
# com a resposta per defecte seria pitjor (són la minoria real, ~23%).
_DEFAULT_AQUEST = {"aquest": "este", "aquesta": "esta", "aquests": "estos", "aquestes": "estes"}

# Els dos candidats reals per a cada forma ambigua -- exposat en públic
# perquè `pipeline/08_traduccio_corpus/postprocessat_llm/` (Fase 3, desambiguació
# per LLM) necessita saber quins SON els dos candidats, no nomes quin
# s'aplica per defecte.
CANDIDATS_AQUEST = {
    "aquest": ("este", "eixe"),
    "aquesta": ("esta", "eixa"),
    "aquests": ("estos", "eixos"),
    "aquestes": ("estes", "eixes"),
}


def carrega_demostratius_invers(path: Path = AVL_PATH) -> dict[str, str]:
    """Llig `demostratius_avl.json`, camp `invers_pendent_no_implementat`
    (el grup "aqueix", segur de veres) + el default mesurat "aquest"->
    "este" (vore `_DEFAULT_AQUEST` i docstring del mòdul). Exclou
    `aixo_neutre`, que es queda sense evidència de cap valor per defecte.

    >>> lookup = carrega_demostratius_invers()
    >>> lookup["aqueix"]
    'eixe'
    >>> lookup["aqueixes"]
    'eixes'
    >>> lookup["aquest"]
    'este'
    >>> lookup["aquestes"]
    'estes'
    >>> "aixo_neutre" in lookup
    False
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    invers = dades["invers_pendent_no_implementat"]
    lookup = {
        cat: val
        for cat, val in invers.items()
        if cat != "descripcio" and cat != "aixo_neutre"
    }
    lookup.update(_DEFAULT_AQUEST)
    return lookup


def formes_cobertes_per_demostratius_invers(path: Path = AVL_PATH) -> set[str]:
    """Formes catalanes (minúscules) que esta capa ja gestiona amb
    autoritat pròpia -- `cat_val/lexic.py` les ha d'ignorar encara que
    aparega una entrada accidental per a elles en el lèxic general
    (mateix criteri que `_formes_demostratius_conegudes` del costat
    val->cat, vore `rules/val_cat/lexic.py`).

    Bug real trobat i corregit (13/10/2026, mesurant contra el benchmark
    invertit -- RC021/RC047/RC066/RC079/RC086/RC087/RC088/RC090/RC093/
    RC114/RC121/RC125/RC130/RC138/RC139, ~15 frases): esta funció nomes
    tornava les formes de `invers_pendent_no_implementat` (el grup
    "aqueix", segur). Pero `lexic_general.json` te 4 entrades directes
    {"valenciano": "este", "catalan": "aquest"} (i esta/estos/estes) que
    `rules/val_cat/lexic.py` ja excloïa pel costat valencia (son el
    costat actiu del paradigma, gestionat per `demostratius.py` amb
    autoritat), pero que `cat_val/lexic.py` NO excloïa pel costat catala
    -- "aquest" (que DemostratiusInversRule deixa expressament sense
    tocar, ambigu de veres) es resolia igualment, i mal, a traves del
    lexic general ("aquest"->"este" sempre, mai "eixe"). Ara s'inclouen
    tambe les formes ACTIVES ("aquest"/"aquesta"/"aquests"/"aquestes"/
    "això"), perque la decisio de deixar-les sense tocar es de
    `cat_val/demostratius.py`, no del lexic general.

    >>> formes = formes_cobertes_per_demostratius_invers()
    >>> "aqueix" in formes
    True
    >>> "aquest" in formes
    True
    >>> "això" in formes
    True
    """
    actives = json.loads(Path(path).read_text(encoding="utf-8"))["entrades_actives_occidental_a_oriental"]
    return set(carrega_demostratius_invers(path).keys()) | {v.lower() for v in actives.values()}


class DemostratiusInversRule:
    """Substitueix "aqueix"/"aqueixa"/"aqueixos"/"aqueixes" per la seua
    forma occidental segura ("eixe"/"eixa"/"eixos"/"eixes"), i "aquest"/
    "aquesta"/"aquests"/"aquestes" pel seu DEFAULT mesurat ("este"/
    "esta"/"estos"/"estes", ~77% d'encert real, vore docstring del
    mòdul). "això" es queda sense tocar -- sense evidència de cap valor
    per defecte.

    >>> from .. import tokenize, marca_noms_propis
    >>> toks = tokenize("Aqueixa dona i aqueixos xiquets.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Aqueixa', 'Eixa'), ('aqueixos', 'eixos')]

    "aquest" -> "este" per defecte (majoria real, NO certesa -- vore
    docstring del mòdul per al ~23% d'error conegut i acceptat):

    >>> toks = tokenize("Aquest xiquet és bo.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Aquest', 'Este')]

    "això" es queda SENSE TOCAR -- sense evidència, vore docstring:

    >>> toks = tokenize("Això és molt important.")
    >>> marca_noms_propis(toks)
    >>> toks = DemostratiusInversRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    "aquell"/"allò" mai canvien -- idèntics als dos dialectes:

    >>> toks = tokenize("Aquell home i allò que vas dir.")
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

    def __init__(self, path: Path = AVL_PATH) -> None:
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
