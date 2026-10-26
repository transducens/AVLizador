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
- només valencià (AVL): cada marcador occidental del GD (que ja filtra
  homògrafs amb spaCy) es busca a l'índex valencià.
"""

from __future__ import annotations

import json
import re
import sys
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
    occidentals del GD."""
    _, per_val = index
    trobats = {}
    for forma in marcadors:
        for fenomen, altra, hom in per_val.get(forma.lower(), ()):
            trobats[(fenomen, forma)] = {"fenomen": fenomen, "cat": altra, "val": forma, "hom": hom}
    return list(trobats.values())


# --- Fenòmens de les regles del motor (no del diccionari) -------------------
# PER_A ("per" + infinitiu -> "per a"), DOS_DUES, INC (incoatius) i ACC
# (accentuació). Es fan servir les MATEIXES regles del traductor, aplicades
# soles: proposen el canvi i el text de referència el confirma.
# - parell (BOE): regles cat->val sobre el català; compta si la forma
#   proposada és al valencià (i no al català).
# - només valencià (AVL): regles val->cat sobre el valencià (incoatius,
#   dos/dues amb el gènere d'spaCy, accentuació); "per a" + infinitiu
#   segons spaCy (val->cat no té eixa regla: el català admet les dues).
_PISTES_REGLES = re.compile(r"\bper\b|\bdues\b|\bdos\b|i[xs]|[èéò]", re.IGNORECASE)
_regles_cache: dict = {}


def _regles():
    if not _regles_cache:
        sys.path.insert(0, str(ARREL))
        from traductor.rules import detokenize, marca_noms_propis, pos_tagger, tokenize
        from traductor.rules.cat_val.accentuacio import AccentuacioInversRule
        from traductor.rules.cat_val.concordanca_dos_dues import ConcordancaDosDuesInversRule
        from traductor.rules.cat_val.incoatius import IncoatiusInversRule
        from traductor.rules.cat_val.per_a_infinitiu import PerAInfinitiuInversRule
        from traductor.rules.val_cat.accentuacio import AccentuacioRule
        from traductor.rules.val_cat.concordanca_dos_dues import ConcordancaDosDuesRule
        from traductor.rules.val_cat.incoatius import IncoatiusRule

        _regles_cache.update(
            tokenize=tokenize, detokenize=detokenize, marca=marca_noms_propis, pos=pos_tagger,
            cat_val=[("PER_A", PerAInfinitiuInversRule()), ("DOS_DUES", ConcordancaDosDuesInversRule()),
                     ("INC", IncoatiusInversRule()), ("ACC", AccentuacioInversRule())],
            val_cat=[("DOS_DUES", ConcordancaDosDuesRule()), ("INC", IncoatiusRule()),
                     ("ACC", AccentuacioRule())],
        )
    return _regles_cache


def _aplica(regla, text: str, noms_propis: bool) -> list[tuple[str, str]]:
    """(forma original, forma proposada) de cada token que canvia la regla."""
    r = _regles()
    toks = r["tokenize"](text)
    if noms_propis:
        r["marca"](toks)
    r["pos"].etiqueta(toks)
    regla.apply(toks)
    return [(t.surface, t.translated) for t in toks if t.is_translated and t.translated != t.surface]


def detecta_regles_parell(cat: str, val: str, ja: list[dict] | None = None) -> list[dict]:
    """Fenòmens de les regles amb el canvi confirmat al valencià.

    >>> sorted((f["fenomen"], f["cat"], f["val"]) for f in detecta_regles_parell(
    ...     "Les dues entitats tenen competència per subscriure el conveni que ofereix.",
    ...     "Les dos entitats tenen competència per a subscriure el conveni que oferix."))
    [('DOS_DUES', 'dues', 'dos'), ('INC', 'ofereix', 'oferix'), ('PER_A', 'per', 'per a')]
    """
    if not _PISTES_REGLES.search(cat):
        return []
    previs = {(x["cat"], x["val"]) for x in ja or ()}
    g_cat, g_val = _ngrames(paraules(cat)), _ngrames(paraules(val))
    t_cat, t_val = f" {' '.join(paraules(cat))} ", f" {' '.join(paraules(val))} "
    trobats = {}
    for fenomen, regla in _regles()["cat_val"]:
        for orig, nova in _aplica(regla, cat, noms_propis=False):
            if fenomen == "PER_A":
                o, n = "per", "per a"
                # El valencià ha de tindre més "per a" que el català.
                confirmat = t_val.count(" per a ") > t_cat.count(" per a ")
            else:
                o, n = paraules(orig)[-1], paraules(nova)[-1]
                confirmat = n in g_val and n not in g_cat
            if (o, n) in previs:
                continue
            if confirmat:
                trobats[(fenomen, o, n)] = {"fenomen": fenomen, "cat": o, "val": n, "hom": False}
    return list(trobats.values())


def detecta_regles_valencia(val: str, ja: list[dict] | None = None) -> list[dict]:
    """Fenòmens de les regles en un text només valencià.

    >>> sorted((f["fenomen"], f["cat"], f["val"]) for f in detecta_regles_valencia(
    ...     "Les dos entitats tenen competència per a subscriure el conveni que oferix."))
    [('DOS_DUES', 'dues', 'dos'), ('INC', 'ofereix', 'oferix'), ('PER_A', 'per', 'per a')]
    """
    if not _PISTES_REGLES.search(val):
        return []
    previs = {(x["cat"], x["val"]) for x in ja or ()}
    r = _regles()
    trobats = {}
    for fenomen, regla in r["val_cat"]:
        for orig, nova in _aplica(regla, val, noms_propis=True):
            o, n = paraules(orig)[-1], paraules(nova)[-1]
            if (n, o) not in previs:
                trobats[(fenomen, o)] = {"fenomen": fenomen, "cat": n, "val": o, "hom": False}
    if re.search(r"\bper a\b", val, re.IGNORECASE):
        toks = r["tokenize"](val)
        r["pos"].etiqueta(toks)
        paraules_toks = [t for t in toks if t.surface[:1].isalpha()]
        for a, b, c in zip(paraules_toks, paraules_toks[1:], paraules_toks[2:]):
            if a.surface.lower() == "per" and b.surface.lower() == "a" and c.verb_form == "Inf" \
                    and not c.surface.lower().startswith("haver"):
                trobats[("PER_A", "per a")] = {"fenomen": "PER_A", "cat": "per", "val": "per a", "hom": False}
    return list(trobats.values())
