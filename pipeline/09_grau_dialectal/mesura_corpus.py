#!/usr/bin/env python3
"""
mesura_corpus.py -- GD, GDV i GDC de cada document dels corpus de
referència, amb un sol comandament i reprenent si es para.

Corpus (en este orde, els xicotets primer):

    151_val    benchmark de 151, costat valencià (camp `occidental`)
    151_cat    benchmark de 151, costat català (camp `oriental`)
    manual_val benchmark manual (453 frases BOE + AVL), costat valencià
    manual_cat benchmark manual, costat català
    gnv        Gramàtica Normativa Valenciana (txt, un document per línia)
    geiec      Gramàtica essencial de l'IEC (txt, un document per línia)
    boe_val    BOE complet, costat valencià (~268.000 línies)
    boe_cat    BOE complet, costat català (~268.000 línies)

Per a cada document (registre del JSON/JSONL o línia del txt) calcula
les tres mètriques amb UNA sola crida a `gd.py::calcula_gd` (mateixos
marcadors que `gd.py`, `gdv.py` i `gdc.py`):

    GD  = occ / (occ + or)          None si no hi ha cap marcador
    GDV = 1 - or  / paraules        1.0 si no hi ha paraules
    GDC = 1 - occ / paraules        1.0 si no hi ha paraules

Al BOE, a més, agrupa les línies per `documento_id` (el document
sencer del BOE) i dona les tres mètriques de cada un.

CÒPIA DE SEGURETAT / REPRENDRE: cada document s'escriu a
`<eixida>/<corpus>.jsonl` tan prompte com es calcula (es buida al disc
cada 200). Si es para (Ctrl+C, tancar la finestra, apagar), en tornar a
llançar el MATEIX comandament compta els documents ja escrits i
continua des d'ací; una última línia a mitges es descarta. El resum
(`resum.json` i `resum.md`) es calcula al final a partir dels .jsonl,
així que és el mateix es pare o no. `--reinicia` esborra els resultats
dels corpus triats i torna a començar.

Nota: els txt es mesuren línia a línia, així que els totals de les
gramàtiques canvien un poc respecte a `gdv.py --fitxer` (spaCy veu
menys context: GNV 755/115 en compte de 760/114).

ÚS:

    python pipeline/09_grau_dialectal/mesura_corpus.py
    python pipeline/09_grau_dialectal/mesura_corpus.py --corpus 151_val gnv
    python pipeline/09_grau_dialectal/mesura_corpus.py --corpus boe_val --limit 2000
    python pipeline/09_grau_dialectal/mesura_corpus.py --nomes-resum
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterator

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from gd import _llig_jsonl, calcula_gd, carrega_formes_dialectals  # noqa: E402

ARREL = _DIR.parents[1]
EIXIDA_PER_DEFECTE = ARREL / "dades" / "grau_dialectal"
BENCHMARK_151 = ARREL / "pipeline" / "03_seleccio_de_model" / "benchmark_corpus.json"
BENCHMARK_MANUAL = ARREL / "dades" / "benchmark_manual" / "benchmark_manual_cat_val.json"
GRAMATIQUES = ARREL / "pipeline" / "02_regles_dialectals" / "docs_gramatica"

# nom -> (fitxer, camp de text o None per a txt, dialecte esperat)
CORPUS = {
    "151_val": (BENCHMARK_151, "occidental", "val"),
    "151_cat": (BENCHMARK_151, "oriental", "cat"),
    "manual_val": (BENCHMARK_MANUAL, "occidental", "val"),
    "manual_cat": (BENCHMARK_MANUAL, "oriental", "cat"),
    "gnv": (GRAMATIQUES / "gnv_complet.txt", None, "val"),
    "geiec": (GRAMATIQUES / "geiec_complet.txt", None, "cat"),
    "boe_val": (ARREL / "dades" / "boe" / "valencia" / "boe_corpus_entrenamiento_val.jsonl", "texto", "val"),
    "boe_cat": (ARREL / "dades" / "boe" / "catala" / "boe_corpus_entrenamiento_cat.jsonl", "texto", "cat"),
}

CADA_FLUSH = 200
CADA_INFORME = 2000


def _documents(path: Path, camp: str | None) -> Iterator[tuple[str, str | None, str]]:
    """(id, documento_id, text) de cada document, sempre en el mateix
    orde (necessari per a reprendre)."""
    if camp is None:
        n = 0
        with path.open(encoding="utf-8") as f:
            for linia in f:
                linia = linia.strip()
                if linia:
                    n += 1
                    yield f"L{n}", None, linia
        return
    for i, doc in enumerate(_llig_jsonl(path), start=1):
        ident = doc.get("id") or doc.get("corpus_id") or f"D{i}"
        yield str(ident), doc.get("documento_id"), doc.get(camp) or ""


def metriques(occ: int, orr: int, paraules: int) -> dict:
    """Les tres mètriques a partir dels recomptes.

    >>> metriques(1, 1, 8)
    {'gd': 0.5, 'gdv': 0.875, 'gdc': 0.875}
    >>> metriques(0, 0, 8)
    {'gd': None, 'gdv': 1.0, 'gdc': 1.0}
    >>> metriques(0, 0, 0)
    {'gd': None, 'gdv': 1.0, 'gdc': 1.0}
    """
    marcades = occ + orr
    return {
        "gd": round(occ / marcades, 4) if marcades else None,
        "gdv": round(1 - orr / paraules, 4) if paraules else 1.0,
        "gdc": round(1 - occ / paraules, 4) if paraules else 1.0,
    }


def _ja_fets(path: Path) -> int:
    """Documents complets ja escrits a `path`. Si l'última línia està a
    mitges (parada a meitat d'escriptura), la lleva del fitxer."""
    if not path.exists():
        return 0
    linies = path.read_text(encoding="utf-8").splitlines(keepends=True)
    bones = []
    for linia in linies:
        try:
            json.loads(linia)
        except json.JSONDecodeError:
            break
        bones.append(linia if linia.endswith("\n") else linia + "\n")
    if len(bones) != len(linies) or (linies and not linies[-1].endswith("\n")):
        path.write_text("".join(bones), encoding="utf-8")
    return len(bones)


def mesura(nom: str, eixida: Path, limit: int | None) -> None:
    fitxer, camp, _ = CORPUS[nom]
    if not fitxer.exists():
        print(f"[{nom}] NO EXISTIX {fitxer} -- me'l salte")
        return
    desti = eixida / f"{nom}.jsonl"
    fets = _ja_fets(desti)
    if fets:
        print(f"[{nom}] reprenc: {fets} documents ja fets")
    else:
        print(f"[{nom}] comence")

    formes = carrega_formes_dialectals()
    nous = 0
    inici = time.time()
    with desti.open("a", encoding="utf-8") as f:
        try:
            for i, (ident, doc_id, text) in enumerate(_documents(fitxer, camp)):
                if limit is not None and i >= limit:
                    break
                if i < fets:
                    continue
                r = calcula_gd(text, formes)
                registre = {
                    "id": ident,
                    "documento_id": doc_id,
                    "paraules": r["total_paraules"],
                    "occ": r["total_occidentals"],
                    "or": r["total_orientals"],
                    **metriques(r["total_occidentals"], r["total_orientals"], r["total_paraules"]),
                    "marcadors_occ": r["marcadors_occidentals"],
                    "marcadors_or": r["marcadors_orientals"],
                }
                f.write(json.dumps(registre, ensure_ascii=False) + "\n")
                nous += 1
                if nous % CADA_FLUSH == 0:
                    f.flush()
                if nous % CADA_INFORME == 0:
                    vel = nous / (time.time() - inici)
                    print(f"[{nom}] {fets + nous} documents ({vel:.0f}/s)", flush=True)
        except KeyboardInterrupt:
            f.flush()
            print(f"\n[{nom}] PARAT a {fets + nous} documents. Torna a llançar el mateix "
                  f"comandament per a continuar.")
            raise
    print(f"[{nom}] acabat: {fets + nous} documents ({nous} nous, {time.time() - inici:.0f} s)")


def _resum_registres(registres: list[dict]) -> dict:
    """Global (sumant recomptes) i mitjana per registre de les tres
    mètriques. La mitjana del GD només compta els registres amb marcadors."""
    occ = sum(r["occ"] for r in registres)
    orr = sum(r["or"] for r in registres)
    paraules = sum(r["paraules"] for r in registres)
    amb_gd = [r["gd"] for r in registres if r["gd"] is not None]
    n = len(registres)
    return {
        "documents": n,
        "sense_marcadors": n - len(amb_gd),
        "paraules": paraules,
        "occ": occ,
        "or": orr,
        "neutres": paraules - occ - orr,
        "global": metriques(occ, orr, paraules),
        "mitjana": {
            "gd": round(sum(amb_gd) / len(amb_gd), 4) if amb_gd else None,
            "gdv": round(sum(r["gdv"] for r in registres) / n, 4) if n else None,
            "gdc": round(sum(r["gdc"] for r in registres) / n, 4) if n else None,
        },
    }


def _per_document_boe(registres: list[dict], desti: Path) -> list[dict]:
    """Agrupa les línies del BOE per `documento_id` i escriu les tres
    mètriques de cada document sencer."""
    grups: dict[str, dict] = defaultdict(lambda: {"linies": 0, "paraules": 0, "occ": 0, "or": 0})
    for r in registres:
        g = grups[r["documento_id"]]
        g["linies"] += 1
        g["paraules"] += r["paraules"]
        g["occ"] += r["occ"]
        g["or"] += r["or"]
    documents = [
        {"documento_id": doc_id, **g, **metriques(g["occ"], g["or"], g["paraules"])}
        for doc_id, g in grups.items()
    ]
    with desti.open("w", encoding="utf-8") as f:
        for d in documents:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return documents


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.4f}".replace(".", ",")


def escriu_resum(eixida: Path) -> None:
    resum = {}
    for nom, (fitxer, camp, dialecte) in CORPUS.items():
        path = eixida / f"{nom}.jsonl"
        if not path.exists():
            continue
        registres = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not registres:
            continue
        resum[nom] = {"fitxer": str(fitxer.relative_to(ARREL)), "dialecte": dialecte,
                      **_resum_registres(registres)}
        if any(r["documento_id"] for r in registres):
            docs = _per_document_boe(registres, eixida / f"{nom}_per_document.jsonl")
            resum[nom]["per_document"] = _resum_registres(
                [{**d, "gd": d["gd"], "gdv": d["gdv"], "gdc": d["gdc"]} for d in docs]
            )

    (eixida / "resum.json").write_text(json.dumps(resum, ensure_ascii=False, indent=2), encoding="utf-8")

    files = [
        "| Corpus | Dialecte | Documents | Sense marcadors | Paraules | occ | or "
        "| GD global | GDV global | GDC global | GD mitjana | GDV mitjana | GDC mitjana |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for nom, r in resum.items():
        files.append(
            f"| {nom} | {r['dialecte']} | {r['documents']} | {r['sense_marcadors']} | {r['paraules']} "
            f"| {r['occ']} | {r['or']} | {_fmt(r['global']['gd'])} | {_fmt(r['global']['gdv'])} "
            f"| {_fmt(r['global']['gdc'])} | {_fmt(r['mitjana']['gd'])} | {_fmt(r['mitjana']['gdv'])} "
            f"| {_fmt(r['mitjana']['gdc'])} |"
        )
        if "per_document" in r:
            p = r["per_document"]
            files.append(
                f"| {nom} (per `documento_id`) | {r['dialecte']} | {p['documents']} | {p['sense_marcadors']} "
                f"| {p['paraules']} | {p['occ']} | {p['or']} | {_fmt(p['global']['gd'])} "
                f"| {_fmt(p['global']['gdv'])} | {_fmt(p['global']['gdc'])} | {_fmt(p['mitjana']['gd'])} "
                f"| {_fmt(p['mitjana']['gdv'])} | {_fmt(p['mitjana']['gdc'])} |"
            )
    (eixida / "resum.md").write_text("\n".join(files) + "\n", encoding="utf-8")
    print("\n".join(files))
    print(f"\nResum guardat a {eixida / 'resum.json'} i {eixida / 'resum.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GD, GDV i GDC de cada document del 151, la GNV, la GEIEC i el BOE "
                    "(cada costat), reprenent si es para."
    )
    parser.add_argument("--corpus", nargs="+", choices=list(CORPUS), default=list(CORPUS),
                        help="Quins corpus mesurar (per defecte: tots, en este orde).")
    parser.add_argument("--eixida", type=Path, default=EIXIDA_PER_DEFECTE,
                        help=f"Carpeta de resultats (per defecte: {EIXIDA_PER_DEFECTE.relative_to(ARREL)}).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Només els primers N documents de cada corpus (per a provar).")
    parser.add_argument("--reinicia", action="store_true",
                        help="Esborra els resultats dels corpus triats i comença de zero.")
    parser.add_argument("--nomes-resum", action="store_true",
                        help="No mesura res: només refà el resum amb el que ja hi ha.")
    args = parser.parse_args()

    args.eixida.mkdir(parents=True, exist_ok=True)
    if not args.nomes_resum:
        if args.reinicia:
            for nom in args.corpus:
                for path in (args.eixida / f"{nom}.jsonl", args.eixida / f"{nom}_per_document.jsonl"):
                    path.unlink(missing_ok=True)
        try:
            for nom in args.corpus:
                mesura(nom, args.eixida, args.limit)
        except KeyboardInterrupt:
            print("Faig el resum parcial amb el que hi ha fins ara.")
    escriu_resum(args.eixida)


if __name__ == "__main__":
    main()
