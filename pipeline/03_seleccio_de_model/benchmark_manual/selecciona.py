"""
benchmark_manual/selecciona.py -- Passos 5-6 de
documentacio/hoja_de_ruta_benchmark_manual.md: tria 250 candidates del BOE i
250 de l'AVL dels pools (`construeix_pool.py`) i escriu els fitxers de
revisió, un per persona:

    dades/benchmark_manual/revisio_persona1.json
    dades/benchmark_manual/revisio_persona2.json
    dades/benchmark_manual/seleccio_cobertura.json

Criteris (decisions de l'usuari, 23/10/2026):
- fenòmens = els dels diccionaris (vore `fenomens.py`), amb un mínim per
  fenomen (`QUOTES`); una frase compta per a tots els que conté;
- varietat: una frase entra només si algun dels seus parells concrets
  ("aquesta->esta") té menys de `MAX_PER_PARELL` frases
  i a igualtat guanya la frase que afig parells nous;
- AVL: quotes per tipus de text (`QUOTES_DOC_TYPE_AVL`);
- màxim 2 frases per document;
- el català de les frases de l'AVL és un ESBORRANY del motor valencià->català
  (`traductor.translate`), que l'equip corregix a mà.

Ús (des de l'arrel del repo):
    python pipeline/03_seleccio_de_model/benchmark_manual/selecciona.py [--n 250] [--llavor 23]
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[2]
sys.path.insert(0, str(ARREL))
sys.path.insert(0, str(AQUI))

from fenomens import carrega_index, detecta_parell, detecta_regles_parell  # noqa: E402

DIR = ARREL / "dades" / "benchmark_manual"

# Mínims per fenomen en cada font (de 250 frases). Si el pool no en té
# prou, es prenen totes les que hi haja.
QUOTES = {
    "LEX_NOM": 40, "LEX_ADJ": 20, "LEX_ADV": 20, "LEX_ALTRES": 10,
    "DEM": 30, "POS": 20, "NUM": 10,
    "CONJ_IND": 20, "CONJ_SUBJ": 25, "CONJ_IMP": 10, "CONJ_INF": 10,
    "CONJ_PART": 15, "CONJ_ARREL": 20,
    "HOM": 10,
    # Regles del motor (usuari, 26/10: que estiga representat quasi tot)
    "PER_A": 15, "DOS_DUES": 10, "INC": 20, "ACC": 15,
}
QUOTES_DOC_TYPE_AVL = {
    "nota-de-premsa": 70, "glossari": 85, "acord-normatiu": 30, "butlleti": 25,
    "gramatica_normativa": 15, "pagina": 10, "publicacions": 8, "legislacio": 5,
}
MAX_PER_PARELL = 6
MAX_PER_DOCUMENT = 2


def _fenomens_frase(p: dict) -> set[str]:
    f = {x["fenomen"] for x in p["fenomens"]}
    if any(x["hom"] for x in p["fenomens"]):
        f.add("HOM")
    return f


def _parells(p: dict) -> set[str]:
    return {f"{x['cat']}→{x['val']}" for x in p["fenomens"]}


def selecciona(pool: list[dict], n: int, llavor: int, quotes_doc: dict | None = None) -> list[dict]:
    """Tria voraç: cada pas pren la frase que més ajuda a cobrir els mínims
    (els fenòmens rars pesen més) i que afig més parells nous, respectant
    els màxims per parell, per document i per tipus de text."""
    rnd = random.Random(llavor)
    pool = list(pool)
    rnd.shuffle(pool)
    disponibles = collections.Counter(f for p in pool for f in _fenomens_frase(p))
    pes = {f: 1 / max(disponibles.get(f, 1), 1) ** 0.5 for f in QUOTES}
    falten = {f: min(q, disponibles.get(f, 0)) for f, q in QUOTES.items()}
    per_parell, per_doc, per_tipus = collections.Counter(), collections.Counter(), collections.Counter()
    triades: list[dict] = []
    restants = pool
    while len(triades) < n and restants:
        millor, millor_puntuacio, nous_restants = None, -1.0, []
        for p in restants:
            if per_doc[p["document"]] >= MAX_PER_DOCUMENT:
                continue
            if quotes_doc and per_tipus[p["doc_type"]] >= quotes_doc.get(p["doc_type"], 0):
                continue
            parells = _parells(p)
            # Només es descarta si no afig res: tots els seus parells ja
            # tenen el màxim ("aquest->este" ix a quasi totes les frases).
            if all(per_parell[x] >= MAX_PER_PARELL for x in parells):
                continue
            nous_restants.append(p)
            puntuacio = sum(pes[f] * 10 for f in _fenomens_frase(p) if falten.get(f, 0) > 0)
            puntuacio += sum(1 for x in parells if per_parell[x] == 0)
            if puntuacio > millor_puntuacio:
                millor, millor_puntuacio = p, puntuacio
        if millor is None:
            break
        triades.append(millor)
        for f in _fenomens_frase(millor):
            if f in falten:
                falten[f] = max(0, falten[f] - 1)
        per_parell.update(_parells(millor))
        per_doc[millor["document"]] += 1
        per_tipus[millor["doc_type"]] += 1
        restants = [p for p in nous_restants if p is not millor]
    return triades


def _registre(p: dict, num: int, index) -> dict:
    font = p["font"]
    esborrany = False
    oriental = p["oriental"]
    fenomens = p["fenomens"]
    if font == "avl":
        from traductor import translate

        oriental = translate(p["occidental"])
        esborrany = True
        # Fenòmens que l'esborrany ja ha convertit (els altres, a corregir a mà)
        trobats = detecta_parell(oriental, p["occidental"], index)
        trobats += detecta_regles_parell(oriental, p["occidental"], trobats)
        convertits = {(x["fenomen"], x["val"]) for x in trobats}
    else:
        convertits = None
    return {
        # --- camps que omplin els revisors ---
        "valida": None,              # true (servix) / false (no servix) / "dubtosa"
        "oriental_corregit": None,   # el català corregit (si cal); null = es queda com està
        "occidental_corregit": None, # el valencià corregit (si cal); null = es queda com està
        "comentari": "",
        # --- dades de la frase ---
        "id": f"BM-{font.upper()}-{num:03d}",
        "font": font,
        "oriental": oriental,
        "oriental_es_esborrany": esborrany,
        "occidental": p["occidental"],
        "fenomens": [
            f"{x['fenomen']}: {x['cat']} → {x['val']}"
            + (" (homògraf)" if x["hom"] else "")
            + ("" if convertits is None or (x["fenomen"], x["val"]) in convertits else " [l'esborrany no ho ha convertit]")
            for x in fenomens
        ],
        "gd_valencia": p["gd_val"]["gd"], "marcadors_valencians": p["gd_val"]["occ"],
        "gd_catala": p.get("gd_cat", {}).get("gd"), "marcadors_catalans": p.get("gd_cat", {}).get("ori"),
        "doc_type": p["doc_type"], "document": p["document"], "titol": p.get("titol"),
        "url": p.get("url"), "data": p.get("data"), "id_origen": p["id_origen"],
    }


def _cobertura(triades: list[dict]) -> dict:
    return {
        "frases": len(triades),
        "per_fenomen": {f: sum(f in _fenomens_frase(p) for p in triades) for f in QUOTES},
        "quotes": QUOTES,
        "parells_distints": len({x for p in triades for x in _parells(p)}),
        "per_doc_type": dict(collections.Counter(p["doc_type"] for p in triades).most_common()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--llavor", type=int, default=23)
    args = ap.parse_args()
    index = carrega_index()
    cobertura, persones = {}, {1: [], 2: []}
    for font in ("boe", "avl"):
        pool = [json.loads(l) for l in (DIR / f"pool_{font}.jsonl").open(encoding="utf-8")]
        triades = selecciona(pool, args.n, args.llavor, QUOTES_DOC_TYPE_AVL if font == "avl" else None)
        cobertura[font] = _cobertura(triades)
        print(font, json.dumps(cobertura[font], ensure_ascii=False))
        # Repartiment equilibrat: s'ordena per fenomen principal i s'alterna.
        triades.sort(key=lambda p: (sorted(_fenomens_frase(p)), p["doc_type"]))
        for i, p in enumerate(triades):
            persones[1 + i % 2].append(_registre(p, i + 1, index))
    for num, frases in persones.items():
        (DIR / f"revisio_persona{num}.json").write_text(json.dumps({
            "instruccions": (
                "Per a cada frase: 'valida' = true (servix), false (no servix) o \"dubtosa\". "
                "Si cal corregir el català o el valencià, escriu la frase sencera corregida a "
                "'oriental_corregit' / 'occidental_corregit' (null = es queda com està). "
                "AVL: el català és un esborrany del motor i S'HA DE REVISAR SEMPRE. "
                "BOE: el valencià ha de ser una adaptació dialectal fidel del català "
                "(si el BOE reformula, corregix-lo). Criteris complets: "
                "documentacio/hoja_de_ruta_benchmark_manual.md."
            ),
            "frases": frases,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"revisio_persona{num}.json: {len(frases)} frases")
    (DIR / "seleccio_cobertura.json").write_text(json.dumps(cobertura, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
