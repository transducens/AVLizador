"""
benchmark_manual/fenomens.py -- Detector de fenòmens "dels diccionaris" per
al benchmark manual cat->val (vore documentacio/hoja_de_ruta_benchmark_manual.md).

Un fenomen és una entrada dels dos fitxers del proveïdor que el traductor fa
servir (traductor/data/lexic_general.json i conjugacions_dialectals.json),
classificada pel seu propi camp:

- lèxic, per `categoria`: LEX_NOM (n), LEX_ADJ (adj), LEX_ADV (adv),
  LEX_ALTRES (prn, cnjadv, pr, ij...), DEM (det), POS (det de
  `fuente: "avl_equip"`), NUM (`fuente: "numerales"` o `categoria: "num"`);
- conjugacions, per `morfologia`: CONJ_IND (pri, pii, fut, cni...),
  CONJ_SUBJ (prs, pis), CONJ_IMP (imp), CONJ_INF (inf), CONJ_PART (pp),
  CONJ_ALTRES (sense morfologia), CONJ_ARREL (verbs d'arrel distinta,
  `infinitiu_cat`).
- HOM s'afegix si l'entrada té `problema: "homonimia_lexica"` o
  `"colision_homonima"`.

Detecció, sempre sobre el text de REFERÈNCIA (no sobre l'eixida del motor):

- parell (BOE): el fenomen hi és si la forma catalana apareix al text català
  I la seua forma valenciana al text valencià;
- només valencià (AVL): cada marcador occidental de l'IPD (que ja filtra
  homògrafs amb spaCy) es busca a l'índex valencià.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
DATA = ARREL / "traductor" / "data"

_CODIS_MODE = {
    "prs": "CONJ_SUBJ", "pis": "CONJ_SUBJ",
    "imp": "CONJ_IMP", "inf": "CONJ_INF", "pp": "CONJ_PART",
}
_PARAULA_RE = re.compile(r"[a-zà-ÿ·]+(?:-[a-zà-ÿ·]+)*")


def _fenomen_lexic(e: dict) -> str:
    cat = e.get("categoria")
    if e.get("fuente") == "numerales" or cat == "num":
        return "NUM"
    if cat == "det":
        return "POS" if e.get("fuente") == "avl_equip" else "DEM"
    return {"n": "LEX_NOM", "adj": "LEX_ADJ", "adv": "LEX_ADV"}.get(cat, "LEX_ALTRES")


def _fenomen_conj(e: dict) -> str:
    if e.get("infinitiu_cat"):
        return "CONJ_ARREL"
    morf = e.get("morfologia")
    if not morf:
        return "CONJ_ALTRES"
    lectures = morf if isinstance(morf[0], list) else [morf]
    codis = {l[0] for l in lectures if l}
    # Una forma pot tindre diverses lectures ("puguin": imperatiu i subjuntiu
    # de 3a persona); mana la més específica.
    for codi, fenomen in (("prs", "CONJ_SUBJ"), ("pis", "CONJ_SUBJ"), ("imp", "CONJ_IMP"),
                          ("inf", "CONJ_INF"), ("pp", "CONJ_PART")):
        if codi in codis:
            return fenomen
    return "CONJ_IND"


# Quan un mateix parell surt en diverses entrades (p.ex. "hagi"->"haja" amb
# morfologies distintes), es queda el fenomen més específic.
_PRIORITAT = ["POS", "DEM", "NUM", "LEX_NOM", "LEX_ADJ", "LEX_ADV", "LEX_ALTRES",
              "CONJ_ARREL", "CONJ_SUBJ", "CONJ_IMP", "CONJ_INF", "CONJ_PART", "CONJ_IND", "CONJ_ALTRES"]


def carrega_index() -> tuple[dict, dict]:
    """(`per_cat`, `per_val`): forma (minúscules, pot ser de 2-3 paraules) ->
    conjunt de (fenomen, forma de l'altre costat, homograf). Un sol fenomen
    per parell."""
    parells: dict[tuple[str, str], list] = {}

    def afig(cat: str, val: str, fenomen: str, hom: bool) -> None:
        cat, val = (cat or "").strip().lower(), (val or "").strip().lower()
        if not cat or not val or cat == val:
            return
        anterior = parells.get((cat, val))
        if anterior is None:
            parells[(cat, val)] = [fenomen, hom]
        else:
            anterior[0] = min(anterior[0], fenomen, key=_PRIORITAT.index)
            anterior[1] = anterior[1] or hom

    for e in json.loads((DATA / "lexic_general.json").read_text(encoding="utf-8")):
        if e.get("tipo") == "v:top_gva":
            continue
        hom = e.get("problema") in ("homonimia_lexica", "colision_homonima")
        afig(e.get("catalan"), e.get("valenciano"), _fenomen_lexic(e), hom)
    conj = json.loads((DATA / "conjugacions_dialectals.json").read_text(encoding="utf-8"))["entradas"]
    for e in conj:
        afig(e.get("catalan"), e.get("valenciano"), _fenomen_conj(e), False)

    per_cat: dict[str, set] = defaultdict(set)
    per_val: dict[str, set] = defaultdict(set)
    for (cat, val), (fenomen, hom) in parells.items():
        per_cat[cat].add((fenomen, val, hom))
        per_val[val].add((fenomen, cat, hom))
    return dict(per_cat), dict(per_val)


def paraules(text: str) -> list[str]:
    """Paraules en minúscules, amb l'apòstrof com a separador ("l'Estat" ->
    "l", "estat") i les formes amb guionet senceres ("vint-i-vuit").

    >>> paraules("L’Estat i vint-i-vuit d'aquestes.")
    ['l', 'estat', 'i', 'vint-i-vuit', 'd', 'aquestes']
    """
    net = text.lower().replace("’", "'").replace("ʼ", "'")
    return _PARAULA_RE.findall(net)


def _ngrames(par: list[str], maxim: int = 3) -> set[str]:
    return {" ".join(par[i:i + n]) for n in range(1, maxim + 1) for i in range(len(par) - n + 1)}


def detecta_parell(cat: str, val: str, index: tuple[dict, dict]) -> list[dict]:
    """Fenòmens amb la forma catalana al text català i la valenciana al
    valencià.

    >>> idx = carrega_index()
    >>> sorted({f["fenomen"] for f in detecta_parell("Aquesta noia té la seva feina avui.",
    ...                                             "Esta xica té la seua faena hui.", idx)})
    ['DEM', 'LEX_ADV', 'LEX_NOM', 'POS']
    """
    per_cat, _ = index
    g_cat, g_val = _ngrames(paraules(cat)), _ngrames(paraules(val))
    trobats = {}
    for forma in g_cat:
        for fenomen, altra, hom in per_cat.get(forma, ()):
            if altra in g_val and forma not in g_val:
                trobats[(fenomen, forma, altra)] = {"fenomen": fenomen, "cat": forma, "val": altra, "hom": hom}
    return list(trobats.values())


def detecta_valencia(marcadors: list[str], index: tuple[dict, dict]) -> list[dict]:
    """Fenòmens d'un text només valencià a partir dels marcadors
    occidentals de l'IPD."""
    _, per_val = index
    trobats = {}
    for forma in marcadors:
        for fenomen, altra, hom in per_val.get(forma.lower(), ()):
            trobats[(fenomen, forma)] = {"fenomen": fenomen, "cat": altra, "val": forma, "hom": hom}
    return list(trobats.values())
