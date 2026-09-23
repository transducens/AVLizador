"""
lexic.py -- Capa 1 del pipeline: substitució directa per lèxic diferencial
(traductor/data/lexico_fiable.json, ~194 entrades revisades a mà, còpia de
02_reglas_dialectales/lexico/lexico_fiable.json -- fitxer de treball
provisional, vore nota de l'esquema baix).

Esta és la ÚNICA capa que fa lookup en un diccionari en compte d'aplicar una
regla morfològica -- cobrix paraules que canvien de forma per motius
purament lèxics, sense cap patró gramatical que ho prediga (p.ex. "roig" ->
"vermell" en el sentit de color). Justament per això és la MÉS perillosa de
les capes si no es filtren bé els noms propis i els homògrafs: "roig"
també és un cognom/nom (en eixe cas mai s'ha de traduir), i el projecte ja
es va trobar el mateix problema abans amb "blanca" (adjectiu) vs. "Blanca"
(nom de dona) -- vore final/metodologia_y_resultados.md, secció 6, per
l'incident real. Per això LexicRule mai toca un token amb
`is_proper_noun = True` (fixat per `marca_noms_propis()` abans de córrer
cap regla).

Esquema real del JSON (NO és "una paraula -> diverses alternatives"):
    {"valenciano": ["ametla", "ametles"], "catalan": ["ametlla", "ametlles"], ...}
Són DOS ARRAYS PARAL·LELS alineats per índex (singular/plural), no una
paraula amb diverses traduccions possibles -- comprovat sobre les 194
entrades reals: 193 tenen la mateixa longitud als dos arrays. La ÚNICA
excepció real és "corder/corders" -> "xai/be/anyell" (2 formes valencianes
per a 3 sinònims catalans): en eixe cas no hi ha manera de saber quina
forma catalana correspon a quina valenciana, així que totes dos agafen la
PRIMERA («xai») -- no és necessàriament la millor tria, però mai és
incorrecta gramaticalment. # AMBIGÚ: si el lèxic complet (encara pendent,
l'usuari ha dit que este és només un fitxer de treball provisional) te més
casos així, esta mateixa regla de "primera forma" els cobrix, però convé
revisar-los un a un si n'apareixen molts.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Token, preserva_majuscula

DEFAULT_LEXIC_PATH = Path(__file__).resolve().parent.parent / "data" / "lexico_fiable.json"


def carrega_lexic(path: Path = DEFAULT_LEXIC_PATH) -> dict[str, str]:
    """Llig el JSON del lèxic i el converteix en un diccionari pla
    `{forma_valenciana_en_minuscules: forma_catalana}`, a partir dels
    arrays paral·lels "valenciano"/"catalan" de cada entrada (vore
    docstring del mòdul). Entrades sense alguna de les dos llistes, o amb
    `categoria == "nombre"`, es descarten (esta última categoria no
    apareix mai al fitxer actual, però es filtra per si el lèxic complet
    futur en du -- mateix criteri que `03_seleccion_de_modelo/evalua_models.py`).

    >>> lookup = carrega_lexic()
    >>> lookup["abellir"]
    'plaure'
    >>> lookup["ametla"], lookup["ametles"]
    ('ametlla', 'ametlles')
    >>> lookup["corder"], lookup["corders"]
    ('xai', 'xai')
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    lookup: dict[str, str] = {}
    for entrada in dades.get("entradas", []):
        if entrada.get("categoria") == "nombre":
            continue
        valenciano = entrada.get("valenciano") or []
        catalan = entrada.get("catalan") or []
        if not valenciano or not catalan:
            continue
        if len(valenciano) == len(catalan):
            parells = zip(valenciano, catalan)
        else:
            parells = ((v, catalan[0]) for v in valenciano)
        for val, cat in parells:
            val_norm = val.strip().lower()
            if val_norm and val_norm not in lookup:
                lookup[val_norm] = cat.strip()
    return lookup


class LexicRule:
    """Substitueix paraules valencianes conegudes per la seua forma
    catalana, segons `lexico_fiable.json`. Mai toca un token ja traduït
    per una capa anterior (`is_translated`) ni un possible nom propi
    (`is_proper_noun`, fixat per `marca_noms_propis()` abans de córrer
    cap regla -- vore rules/__init__.py).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Hui vull unes ametles.")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('ametles', 'ametlles')]

    Nom propi protegit encara que casualment coincidisca amb una entrada
    del lèxic (exemple sintètic -- ara mateix cap entrada real del fitxer
    comença en majúscula, però la protecció ha de funcionar igualment si
    el lèxic complet futur n'afig alguna, o si un nom propi coincidix per
    casualitat amb una paraula normal del lèxic):

    >>> toks = tokenize("Coneixes a Ametles, el meu gos?")
    >>> marca_noms_propis(toks)
    >>> toks = LexicRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []
    """

    def __init__(self, lexic_path: Path = DEFAULT_LEXIC_PATH) -> None:
        self._lookup = carrega_lexic(lexic_path)

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = self._lookup.get(tok.surface.lower())
            if forma is None:
                continue
            tok.translated = preserva_majuscula(tok.surface, forma)
            tok.is_translated = True
        return tokens
