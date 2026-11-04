"""
benchmark_manual/construeix_pool.py -- Passos 2-4 de
documentacio/hoja_de_ruta_benchmark_manual.md: extrau les frases candidates
del BOE i de l'AVL, aplica els filtres de qualitat, el GD i les exclusions,
detecta els fenòmens dels diccionaris i escriu:

    dades/benchmark_manual/pool_boe.jsonl
    dades/benchmark_manual/pool_avl.jsonl
    dades/benchmark_manual/pool_estadistiques.json

Ús (des de l'arrel del repo):
    python pipeline/03_seleccio_de_model/benchmark_manual/construeix_pool.py [--font boe|avl|totes]
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[2]
sys.path.insert(0, str(AQUI))

from avlizador.grau_dialectal import gd  # noqa: E402
from fenomens import (carrega_index, detecta_parell, detecta_regles_parell, detecta_regles_valencia,  # noqa: E402
                      detecta_valencia, paraules)

BOE = ARREL / "dades" / "boe" / "corpus_entrenamiento.jsonl"
AVL = ARREL / "dades" / "avl" / "final" / "dialectal" / "corpus_occidental_net.jsonl"
B151 = ARREL / "pipeline" / "03_seleccio_de_model" / "benchmark_corpus.json"
EIXIDA = ARREL / "dades" / "benchmark_manual"

MIN_PARAULES, MAX_PARAULES = 8, 40
MAX_PER_DOCUMENT_POOL = 3  # només AVL; al BOE no hi ha màxim (decisió de l'usuari, 26/10)

# --- filtres de qualitat ---------------------------------------------------
_INICI_LLISTA = re.compile(r"^\s*(\d+[\.\)º]|[a-zA-Z]\s?\)|[-–—•·*]|[IVXLC]+\.)\s")
_METALINGUISTIC = re.compile(
    r"\b(paraul(?:a|es)|mots?|termes?|vocables?|ètims?|llatí|grec|àrab|castellà|italià|portugu[eé]s|"
    r"franc[eé]s|angl[eé]s|occità|etimologia|prové|provenen|deriva|derivats?|accepcions?|"
    r"sinònims?|significats?|s'escriu|s’escriu|es pronuncia|dígrafs?|lletres?|síl·labes?|"
    r"apòstrof|morfemes?|sufix(?:os)?|prefix(?:os)?|gramàtica|normativ\w*|substantius?|adjectius?|"
    r"oracions?|subjectes?|complements?|verbs?|numerals?|majúscul\w*|minúscul\w*|topònims?|"
    r"denomina|designa|es diu|es deia|es coneix com)\b",
    re.IGNORECASE,
)
_GLOSSA = re.compile(r"[‘'][^‘’']{1,40}[’']|«[^»]{1,25}»|\"[^\"]{1,25}\"")


def frase_valida(text: str) -> bool:
    """Frase completa, de 8 a 40 paraules, sense llistes ni majúscules
    senceres, amb pocs números.

    >>> frase_valida("Aquest servei es prestarà durant tot l'any als ciutadans de la comarca.")
    True
    >>> frase_valida("a) Aquest servei es prestarà durant tot l'any als ciutadans.")
    False
    >>> frase_valida("DISPOSICIONS GENERALS DEL REGLAMENT DE SERVEIS PER A LA COMARCA.")
    False
    """
    t = text.strip()
    n = len(t.split())
    if not (MIN_PARAULES <= n <= MAX_PARAULES):
        return False
    if not t[0].isupper() and t[0] not in "«\"“":
        return False
    if t[-1] not in ".?!" or t.endswith("..."):
        return False
    if _INICI_LLISTA.match(t) or t.upper() == t:
        return False
    amb_digits = sum(any(c.isdigit() for c in p) for p in t.split())
    return amb_digits <= max(2, n // 8)


def es_metalinguistica(text: str) -> bool:
    """Frases que parlen de paraules (no servixen per a mesurar).

    >>> es_metalinguistica("La paraula medalla prové del llatí vulgar medialĭa.")
    True
    >>> es_metalinguistica("El president ha expressat hui el seu suport a l'Acadèmia.")
    False
    """
    return bool(_METALINGUISTIC.search(text) or _GLOSSA.search(text))


def normalitza(text: str) -> str:
    return " ".join(paraules(re.sub(r"\d+", "", text)))


def _conjunt(text: str) -> frozenset:
    return frozenset(p for p in paraules(text) if len(p) > 2)


class Exclusions:
    """El banc de 151 (per document de l'AVL i per semblança de text) i els
    duplicats dins del pool."""

    def __init__(self) -> None:
        b151 = json.loads(B151.read_text(encoding="utf-8"))
        self.docs_avl = {b["corpus_id"] for b in b151 if b.get("corpus_id")}
        self.conjunts = [_conjunt(b[c]) for b in b151 for c in ("occidental", "oriental")]
        self.vistes: set[str] = set()

    def massa_semblant_151(self, text: str, llindar: float = 0.6) -> bool:
        c = _conjunt(text)
        if not c:
            return False
        return any(len(c & d) / len(c | d) >= llindar for d in self.conjunts if d)

    def duplicada(self, text: str) -> bool:
        clau = normalitza(text)
        if clau in self.vistes:
            return True
        self.vistes.add(clau)
        return False


def _resum_gd(r: dict) -> dict:
    return {"gd": r["gd"], "occ": r["marcadors_occidentals"], "ori": r["marcadors_orientals"]}


# --- BOE -------------------------------------------------------------------
MOSTRA_BOE = 50000  # màxim de candidates (després dels filtres barats) que passen al GD; hui hi caben totes (28.429, ~2 min)
LLAVOR_BOE = 23


def pool_boe(index, formes, excl: Exclusions, estad: dict) -> list[dict]:
    """Dos fases: (1) filtres barats sobre tot el BOE; (2) sobre una mostra
    aleatòria fixa de `MOSTRA_BOE` candidates, la semblança amb el 151 i
    el GD amb spaCy a les dues llengües (el pas car)."""
    c = collections.Counter()
    candidates = []
    t0 = time.time()
    with BOE.open(encoding="utf-8") as fh:
        for linia in fh:
            r = json.loads(linia)
            c["total"] += 1
            if c["total"] % 50000 == 0:
                print(f"  BOE fase 1: {c['total']} llegides, {len(candidates)} candidates ({time.time() - t0:.0f}s)", flush=True)
            cat, val = r["texto_catalan"].strip(), r["texto_valenciano"].strip()
            if cat == val:
                c["identiques"] += 1
                continue
            if not frase_valida(cat) or not frase_valida(val):
                c["qualitat"] += 1
                continue
            if not (0.85 <= len(val) / len(cat) <= 1.15) or r.get("similitud", 1) < 0.6:
                c["alineacio"] += 1
                continue
            fen = detecta_parell(cat, val, index)
            fen += detecta_regles_parell(cat, val, fen)
            if not fen:
                c["sense_fenomen"] += 1
                continue
            if excl.duplicada(cat):
                c["duplicada"] += 1
                continue
            candidates.append((r, cat, val, fen))
    c["candidates_fase1"] = len(candidates)
    random.Random(LLAVOR_BOE).shuffle(candidates)
    if len(candidates) > MOSTRA_BOE:
        c["fora_de_mostra"] = len(candidates) - MOSTRA_BOE
        candidates = candidates[:MOSTRA_BOE]
    print(f"  BOE fase 1 acabada: {c['candidates_fase1']} candidates, {len(candidates)} al GD ({time.time() - t0:.0f}s)", flush=True)

    pool = []
    t1 = time.time()
    for i, (r, cat, val, fen) in enumerate(candidates, 1):
        if i % 1000 == 0:
            print(f"  BOE fase 2: {i}/{len(candidates)}, {len(pool)} acceptades ({time.time() - t1:.0f}s)", flush=True)
        if excl.massa_semblant_151(cat) or excl.massa_semblant_151(val):
            c["semblant_151"] += 1
            continue
        i_val = gd.calcula_gd(val, formes)
        if not (i_val["gd"] == 1.0 and i_val["total_occidentals"] >= 2):
            c["gd_valencia"] += 1
            continue
        i_cat = gd.calcula_gd(cat, formes, dialecte="cat")
        if not (i_cat["gd"] == 0.0 and i_cat["total_orientals"] >= 2):
            c["gd_catala"] += 1
            continue
        pool.append({
            "font": "boe", "id_origen": r["id"], "document": r["documento_id"], "data": r.get("fecha"),
            "doc_type": "boe", "oriental": cat, "occidental": val,
            "fenomens": fen, "gd_val": _resum_gd(i_val), "gd_cat": _resum_gd(i_cat),
        })
        c["acceptades"] += 1
    estad["boe"] = dict(c)
    return pool


# --- AVL -------------------------------------------------------------------
_EXEMPLE = re.compile(r"\[Ex:\s*([^\]]+)\]")
_SEPARA = re.compile(r"(?<=[.!?])\s+(?=[«\"“A-ZÀ-Ý])")


def frases_avl(text: str) -> list[tuple[str, str]]:
    """(frase, origen): les frases del text ("text") i les dels exemples de
    la gramàtica ("exemple"). Les línies partides a mitja frase s'unixen.

    >>> frases_avl("El president ha parlat\\nhui amb els acadèmics. Després han dinat junts.")
    [('El president ha parlat hui amb els acadèmics.', 'text'), ('Després han dinat junts.', 'text')]
    """
    eixida = []
    for ex in _EXEMPLE.findall(text):
        eixida += [(f.strip(), "exemple") for f in _SEPARA.split(ex) if f.strip()]
    sense_ex = _EXEMPLE.sub(" ", text)
    unit = re.sub(r"(?<![.!?:])\s*\n\s*", " ", sense_ex)
    for bloc in unit.split("\n"):
        eixida += [(f.strip(), "text") for f in _SEPARA.split(bloc.strip()) if f.strip()]
    return eixida


def pool_avl(index, formes, excl: Exclusions, estad: dict) -> list[dict]:
    c = collections.Counter()
    pool = []
    for linia in AVL.open(encoding="utf-8"):
        d = json.loads(linia)
        if d.get("corpus_id") in excl.docs_avl:
            c["document_del_151"] += 1
            continue
        per_doc = 0
        for frase, origen in frases_avl(d.get("text", "")):
            c["total"] += 1
            if per_doc >= MAX_PER_DOCUMENT_POOL:
                c["max_document"] += 1
                continue
            if not frase_valida(frase):
                c["qualitat"] += 1
                continue
            if es_metalinguistica(frase):
                c["metalinguistica"] += 1
                continue
            if excl.duplicada(frase):
                c["duplicada"] += 1
                continue
            if excl.massa_semblant_151(frase):
                c["semblant_151"] += 1
                continue
            i_val = gd.calcula_gd(frase, formes)
            if not (i_val["gd"] == 1.0 and i_val["total_occidentals"] >= 2):
                c["gd_valencia"] += 1
                continue
            fen = detecta_valencia(i_val["marcadors_occidentals"], index)
            fen += detecta_regles_valencia(frase, fen)
            if not fen:
                c["sense_fenomen"] += 1
                continue
            per_doc += 1
            pool.append({
                "font": "avl", "id_origen": d.get("corpus_id"), "document": d.get("corpus_id"),
                "titol": d.get("title"), "data": d.get("date_published"), "doc_type": d.get("doc_type"),
                "origen_frase": origen, "url": d.get("source_url"),
                "oriental": None, "occidental": frase,
                "fenomens": fen, "gd_val": _resum_gd(i_val),
            })
            c["acceptades"] += 1
    estad["avl"] = dict(c)
    return pool


def _taula(pool: list[dict]) -> dict:
    per_fenomen = collections.Counter(f for p in pool for f in {x["fenomen"] for x in p["fenomens"]})
    per_tipus = collections.Counter(p["doc_type"] for p in pool)
    return {"frases": len(pool), "per_fenomen": dict(per_fenomen.most_common()),
            "per_doc_type": dict(per_tipus.most_common()),
            "amb_homograf": sum(any(x["hom"] for x in p["fenomens"]) for p in pool)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", choices=["boe", "avl", "totes"], default="totes")
    args = ap.parse_args()
    EIXIDA.mkdir(parents=True, exist_ok=True)
    index, formes, excl = carrega_index(), gd.carrega_formes_dialectals(), Exclusions()
    estad: dict = {}
    fonts = ["avl", "boe"] if args.font == "totes" else [args.font]
    for font in fonts:
        t0 = time.time()
        pool = (pool_avl if font == "avl" else pool_boe)(index, formes, excl, estad)
        with (EIXIDA / f"pool_{font}.jsonl").open("w", encoding="utf-8") as fh:
            for p in pool:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
        estad[f"{font}_taula"] = _taula(pool)
        print(f"{font}: {len(pool)} frases en {time.time() - t0:.0f}s")
        print("  filtres:", estad[font])
        print("  taula:", json.dumps(estad[f"{font}_taula"], ensure_ascii=False))
    previ = EIXIDA / "pool_estadistiques.json"
    totes = json.loads(previ.read_text(encoding="utf-8")) if previ.exists() else {}
    totes.update(estad)
    previ.write_text(json.dumps(totes, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
