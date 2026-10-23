"""
model_llengua/punts.py -- Quines paraules del text català són ambigües i
quines frases valencianes candidates en surten. No necessita cap model:
només el lèxic i el motor.

Tres tipus de punt, tots trets de `traductor/data/lexic_general.json` (cap
paraula escrita ací), sempre amb la forma ambigua al costat CATALÀ:

- `colisio`: entrades `problema: "colision_homonima"` amb la mateixa
  `forma_problematica` i valencians distints ("cop" -> "colp" / "vegada").
  El motor no la tradueix (dos candidats sense canònica).
- `irresoluble`: `homonimia_lexica` on les lectures comparteixen categoria
  i spaCy no pot decidir ("calces", "gandula"). El motor tradueix sempre;
  els candidats són la traducció i deixar la paraula catalana.
- `resoluble`: `homonimia_lexica` que spaCy ja resol dins del motor
  ("nou", "manca"). Només entra si es demana, per a comparar el model de
  llengua amb spaCy.

Cada candidat es construïx sobre una "base neutra" (la frase traduïda pel
motor amb la paraula ambigua sense tocar): es posa el candidat i es fa
concordar el determinant d'abans ("un cop" -> "una vegada"). Límit: el
motor no concorda els altres determinants ni adjectius ("molts cops" ->
"molts vegades", "un altre cop" -> "un altre vegada"); l'opció
experimental `concordanca="variants"` proposa les formes de l'altre
gènere i deixa triar al model de llengua.
"""

from __future__ import annotations

import copy
import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..rules import (
    _CATEGORIES_LEMA_RE,
    _POS_PER_CATEGORIA,
    LEXIC_GENERAL_PATH,
    Token,
    carrega_homografs,
    corregeix_article_abans,
    corregeix_contraccio_al_abans,
    corregeix_determinant_abans,
    corregeix_elisio_de_abans,
    detokenize,
    preserva_majuscula,
    separa_prefix_elidit,
)
from ..rules.pos_tagger import _GENERE_CURT, genere_de

TIPUS = ("colisio", "irresoluble", "resoluble")
TIPUS_PER_DEFECTE = ("colisio", "irresoluble")


def carrega_punts(path: Path = LEXIC_GENERAL_PATH) -> dict[str, dict]:
    """`{forma catalana: {"tipus", "candidats", "categoria", "lectures"}}`.
    `categoria` és la de l'entrada (la lectura dialectal) i `lectures`, les
    categories de cada lectura dels `lemas` (només als homògrafs).

    >>> p = carrega_punts()
    >>> p["cop"]["tipus"], p["cop"]["candidats"], p["cops"]["candidats"]
    ('colisio', ['colp', 'vegada'], ['colps', 'vegades'])
    >>> p["calces"]["tipus"], p["calces"]["candidats"], p["nou"]["tipus"]
    ('irresoluble', ['bragues', 'calces'], 'resoluble')
    >>> p["gandula"]["categoria"], [sorted(l) for l in p["gandula"]["lectures"]]
    ('n', [['adj', 'n'], ['n']])
    """
    resolubles, _ = carrega_homografs(path)
    punts: dict[str, dict] = {}
    for e in json.loads(Path(path).read_text(encoding="utf-8")):
        forma = (e.get("forma_problematica") or "").strip().lower()
        catalan = (e.get("catalan") or "").strip().lower()
        valencia = (e.get("valenciano") or "").strip()
        if not forma or forma != catalan or not valencia or " " in valencia:
            continue
        if e.get("problema") == "colision_homonima":
            p = punts.setdefault(forma, {"tipus": "colisio", "candidats": [], "categoria": e.get("categoria"),
                                         "lectures": []})
            if valencia not in p["candidats"]:
                p["candidats"].append(valencia)
        elif e.get("problema") == "homonimia_lexica":
            tipus = "resoluble" if forma in resolubles else "irresoluble"
            lectures = [{c.strip() for c in m.group(1).split(",")}
                        for lema in e.get("lemas") or [] for m in [_CATEGORIES_LEMA_RE.search(lema)] if m]
            punts[forma] = {"tipus": tipus, "candidats": [valencia, forma], "categoria": e.get("categoria"),
                            "lectures": lectures}
    return {f: p for f, p in punts.items() if len(p["candidats"]) > 1}


@dataclass
class Punt:
    index: int
    paraula: str           # la forma catalana, sense prefix elidit
    prefix: str            # "l'", "d'"... o ""
    tipus: str
    candidats: list[str]
    motor: str | None      # el candidat que ha triat el motor (None: cap)
    puntuacions: dict = field(default_factory=dict)  # candidat -> dades del model
    frases: dict = field(default_factory=dict)  # candidat -> frase valenciana completa (sense model)
    tria: str | None = None
    pos: str = ""          # etiqueta d'spaCy de la paraula dins de la frase
    categoria: str | None = None   # categoria de la lectura dialectal (la de l'entrada)
    lectures: list = field(default_factory=list)  # categories de cada lectura (`lemas`)
    decidit: str = ""      # "spacy", "model" o "motor": qui ha fet la tria


_CATEGORIA_PER_POS = {pos: cat for cat, poss in _POS_PER_CATEGORIA.items() for pos in poss}


def decisio_spacy(punt: Punt) -> str | None:
    """Primera capa per als homògrafs irresolubles. Si spaCy dona a la
    paraula una categoria que NOMÉS té l'altra lectura, es deixa la paraula
    catalana ("molt gandula": ADJ, i la lectura "hamaca" només és nom).
    Si la categoria és la compartida, o no és de cap lectura, no decidix
    (`None`) i passa al model de llengua.

    >>> p = Punt(0, "gandula", "", "irresoluble", ["hamaca", "gandula"], "hamaca",
    ...          categoria="n", lectures=[{"adj", "n"}, {"n"}])
    >>> p.pos = "ADJ"; decisio_spacy(p)
    'gandula'
    >>> p.pos = "NOUN"; decisio_spacy(p) is None
    True
    >>> p.pos = "VERB"; decisio_spacy(p) is None
    True
    """
    cat = _CATEGORIA_PER_POS.get(punt.pos)
    if not cat or cat == punt.categoria or not any(cat in l for l in punt.lectures):
        return None
    return next(c for c in punt.candidats if c.lower() == punt.paraula.lower())


def detecta(tokens: list[Token], punts: dict[str, dict], tipus=TIPUS_PER_DEFECTE) -> list[Punt]:
    """Punts ambigus dels tokens que ha deixat el motor. Una paraula que ja
    ha consumit una altra regla ("cop de puny" -> "punyada") no compta.

    >>> from ..rules.cat_val.engine import RuleEngineInvers
    >>> motor, punts = RuleEngineInvers(), carrega_punts()
    >>> [(p.paraula, p.motor) for p in detecta(motor.tradueix_tokens("Un cop més, les calces."), punts)]
    [('cop', None), ('calces', 'bragues')]
    >>> detecta(motor.tradueix_tokens("Va rebre un cop de puny."), punts)
    []
    """
    trobats = []
    for i, tok in enumerate(tokens):
        if tok.surface.isspace():
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        prefix, paraula = prefix_resta if prefix_resta else ("", tok.surface)
        info = punts.get(paraula.lower())
        if info is None or info["tipus"] not in tipus:
            continue
        # el motor pot haver apostrofat dins del token ("la gandula" -> "" + "l'hamaca")
        traduida = separa_prefix_elidit(tok.translated)
        actual = (traduida[1] if traduida else tok.translated).lower()
        if info["tipus"] == "colisio":
            if tok.is_translated and actual not in info["candidats"]:
                continue
            motor = actual if tok.is_translated else None
        else:
            if actual not in {c.lower() for c in info["candidats"]}:
                continue
            motor = actual
        trobats.append(Punt(i, paraula, prefix, info["tipus"], list(info["candidats"]), motor,
                            pos=tok.pos, categoria=info["categoria"], lectures=info["lectures"]))
    return trobats


def base_neutra(motor, text: str, punts: list[Punt]) -> list[Token]:
    """La frase traduïda pel motor amb les paraules dels punts SENSE tocar
    (ni elles ni el seu article): la base sobre la qual es posa cada
    candidat. Cal perquè el motor, quan apostrofa, posa l'"l'" dins de la
    paraula ("la gandula" -> "" + "l'hamaca")."""
    return motor.tradueix_tokens(text, protegits=frozenset(p.index for p in punts))


def _genere_original(tok: Token, paraula: str) -> str:
    return _GENERE_CURT.get(tok.gender, "") or genere_de(paraula.lower())


def aplica_candidat(base: list[Token], punt: Punt, candidat: str) -> list[Token]:
    """Còpia de `base` (vore `base_neutra`) amb `candidat` al lloc del punt.
    Si és la paraula catalana mateixa, no es toca res més. Si no, i el
    gènere canvia (o no se sap el de l'original), el determinant d'abans
    concorda amb el del candidat, i després apòstrof i contraccions.

    >>> from ..rules.cat_val.engine import RuleEngineInvers
    >>> motor = RuleEngineInvers()
    >>> def prova(text, candidat):
    ...     p = detecta(motor.tradueix_tokens(text), carrega_punts(), TIPUS)[0]
    ...     return detokenize(aplica_candidat(base_neutra(motor, text, [p]), p, candidat))
    >>> prova("Un cop acabada la reunió, marxem.", "vegada"), prova("Un cop acabada la reunió.", "colp")
    ('Una vegada acabada la reunió, marxem.', 'Un colp acabada la reunió.')
    >>> prova("Es va estirar a la gandula.", "hamaca"), prova("Es va estirar a la gandula.", "gandula")
    ("Es va estirar a l'hamaca.", 'Es va estirar a la gandula.')
    >>> prova("Arribarem a les nou del matí.", "nou")
    'Arribarem a les nou del matí.'
    """
    tt = copy.deepcopy(base)
    tok = tt[punt.index]
    tok.translated = punt.prefix + preserva_majuscula(punt.paraula, candidat)
    tok.is_translated = True
    if punt.prefix or candidat.lower() == punt.paraula.lower():
        return tt
    nou, original = genere_de(candidat.lower()), _genere_original(tok, punt.paraula)
    if nou and nou != original:
        corregeix_determinant_abans(tt, punt.index, nou)
    corregeix_contraccio_al_abans(tt, punt.index)
    corregeix_article_abans(tt, punt.index)
    corregeix_elisio_de_abans(tt, punt.index)
    return tt


# --- Variants de concordança (opció experimental `concordanca="variants"`) ---
# El motor només corregix el determinant immediatament anterior i només el
# que coneix ("un"/"una", "el"/"la"...). "Molts cops" -> "molts vegades",
# "un altre cop" -> "un altre vegada". Ací es proposen formes de l'altre
# gènere per a les (fins a) dos paraules d'abans que spaCy etiqueta com a
# determinant, adjectiu, numeral o pronom, amb les terminacions regulars
# del femení/masculí; el model de llengua tria quina frase és bona (si una
# forma no existix, la veurà improbable). Cap paraula escrita a mà.
_CAT_CONCORDA = {"DET", "ADJ", "NUM", "PRON"}


def _formes_genere(paraula: str, genere: str) -> set[str]:
    """Formes regulars de `paraula` en el gènere `genere` ("m"/"f").

    >>> sorted(_formes_genere("molts", "f")), sorted(_formes_genere("altre", "f"))
    (['moltes'], ['altra'])
    >>> sorted(_formes_genere("pocs", "f")), sorted(_formes_genere("primer", "f"))
    (['poques'], ['primera'])
    >>> sorted(_formes_genere("diverses", "m")), sorted(_formes_genere("poques", "m"))
    (['diversos'], ['pocos', 'pocs'])
    >>> sorted(_formes_genere("una", "m")), sorted(_formes_genere("tres", "f"))
    (['un', 'une'], [])
    """
    p = paraula.lower()
    formes = set()
    if genere == "f":
        if p.endswith("es"):  # ja té forma de femení plural ("tres", "altres")
            pass
        elif p.endswith("s"):  # plural: -s / -os -> -es (poc -> poques)
            arrel = p[:-2] if p.endswith("os") else p[:-1]
            if arrel.endswith("c"):
                arrel = arrel[:-1] + "qu"
            elif arrel.endswith("g"):
                arrel = arrel + "u"
            formes.add(arrel + "es")
        elif p.endswith("e"):  # altre -> altra
            formes.add(p[:-1] + "a")
        elif not p.endswith("a"):  # un -> una, primer -> primera
            formes.add(p + "a")
    elif p.endswith("es"):  # moltes -> molts / moltos (el model tria)
        arrel = p[:-2]
        if arrel.endswith("qu"):
            arrel = arrel[:-2] + "c"
        elif arrel.endswith("gu"):
            arrel = arrel[:-1]
        formes |= {arrel + "os"} if arrel.endswith("s") else {arrel + "s", arrel + "os"}
    elif p.endswith("a"):  # una -> un / une, altra -> altr / altre
        formes |= {p[:-1], p[:-1] + "e"}
    formes.discard(p)
    return {f for f in formes if len(f) > 1}


def variants_concordanca(base: list[Token], punt: Punt, candidat: str) -> list[list[Token]]:
    """`aplica_candidat` i, si el candidat té un gènere conegut distint de
    l'original, les combinacions amb les paraules d'abans canviades de
    gènere.

    >>> from ..rules.cat_val.engine import RuleEngineInvers
    >>> motor = RuleEngineInvers()
    >>> text = "Molts cops no sabem què fer."
    >>> p = detecta(motor.tradueix_tokens(text), carrega_punts())[0]
    >>> sorted(detokenize(v) for v in variants_concordanca(base_neutra(motor, text, [p]), p, "vegades"))
    ['Moltes vegades no sabem què fer.', 'Molts vegades no sabem què fer.']
    """
    primera = aplica_candidat(base, punt, candidat)
    variants = [primera]
    nou = genere_de(candidat.lower())
    if not nou or punt.prefix or candidat.lower() == punt.paraula.lower():
        return variants
    if nou == _GENERE_CURT.get(base[punt.index].gender, ""):
        return variants
    anteriors = []
    j = punt.index - 1
    while j >= 0 and len(anteriors) < 2:
        if primera[j].surface.isspace():
            j -= 1
            continue
        if primera[j].pos not in _CAT_CONCORDA or not primera[j].translated.isalpha():
            break
        anteriors.append(j)
        j -= 1
    opcions = [[primera[j].translated] + [preserva_majuscula(primera[j].translated, f)
                                           for f in sorted(_formes_genere(primera[j].translated, nou))]
               for j in anteriors]
    for combinacio in itertools.product(*opcions):
        if all(c == primera[j].translated for c, j in zip(combinacio, anteriors)):
            continue
        v = copy.deepcopy(primera)
        for c, j in zip(combinacio, anteriors):
            v[j].translated = c
        variants.append(v)
    return variants


def frases_candidates(base: list[Token], punt: Punt, concordanca: str = "motor") -> dict[str, list[list[Token]]]:
    """`{candidat: [variants de tokens]}` (una sola variant amb
    `concordanca="motor"`)."""
    if concordanca == "variants":
        return {c: variants_concordanca(base, punt, c) for c in punt.candidats}
    return {c: [aplica_candidat(base, punt, c)] for c in punt.candidats}


__all__ = ["TIPUS", "TIPUS_PER_DEFECTE", "Punt", "carrega_punts", "decisio_spacy", "detecta", "base_neutra",
           "aplica_candidat", "variants_concordanca", "frases_candidates", "detokenize"]
