"""Simula criteris (marge, per defecte i lam, amb un lam per a les
col·lisions i un altre per als homògrafs) a partir de les puntuacions en
brut guardades en el detall de `compara_models.py --detall` (camp `brut`:
`lp`, `prior`, `n` per candidat; puntuació = lp − lam · prior).

Reprodueix `model_llengua.tria`: spaCy no canvia (les decisions `spacy` es
queden); sense puntuacions decidix el motor; en les col·lisions ("cop") la
catalana no és candidata i el motor no tria (`motor = None`), així que
decidix sempre el model i el marge no influïx.

Ús:
    python simula_marges.py <detall.json> [--models M ...] [--marges ...]
        [--lams-colisio ...] [--lams-homograf ...] [--defecte catala motor]
        [--max-greus N] [--top K]

Primer comprova que, amb el criteri guardat en el detall, ix el mateix que
el sistema (decisió a decisió).
"""
import argparse
import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compara_models import classifica  # noqa: E402

GREUS = ("traduida_sense_caldre", "candidat_erroni")


def llig_criteri(text):
    """'marge=2 defecte=catala lam=0.5 [lam_col=1]' -> (2.0, 'catala', 0.5, 1.0 o 0.5).
    "fix" = el criteri del sistema (`Criteri()`)."""
    if text == "fix":
        return 2.0, "catala", 0.5, 0.5
    camps = dict(p.split("=") for p in text.split())
    lam = float(camps["lam"])
    return float(camps["marge"]), camps["defecte"], lam, float(camps.get("lam_col", lam))


def decidix(f, marge, defecte, lam_col, lam_hom):
    if f["decidit"] == "spacy" or not f.get("brut"):
        return f["tria"]
    lam = lam_col if f["tipus"] == "colisio" else lam_hom
    valors = {c: d["lp"] - lam * d["prior"] for c, d in f["brut"].items()}
    millor = max(valors, key=valors.get)
    per_defecte = f["motor"]
    if defecte == "catala" and f["motor"] is not None:
        catala = next((c for c in f["candidats"] if c.lower() == f["paraula"].lower()), None)
        if catala is not None:
            per_defecte = catala
    if per_defecte in valors and millor != per_defecte and valors[millor] - valors[per_defecte] <= marge:
        return per_defecte
    return millor


def avalua(files, marge, defecte, lam_col, lam_hom, hibrid=None):
    """`hibrid`: {(benchmark, id): tria} d'un altre model per a les col·lisions."""
    n = Counter()
    greus_per_paraula = Counter()
    for f in files:
        if hibrid is not None and f["tipus"] == "colisio":
            tria = hibrid[(f["_bench"], f["id"])]
        else:
            tria = decidix(f, marge, defecte, lam_col, lam_hom)
        c = classifica(f["paraula"], f["esperat"], tria)
        n[c] += 1
        if c in GREUS:
            greus_per_paraula[f["paraula"].lower()] += 1
    return n, greus_per_paraula


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("detall")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--marges", nargs="*", type=float, default=[0, 0.5, 1, 2, 3, 4, 5, 6, 8, 10])
    ap.add_argument("--lams-colisio", nargs="*", type=float, default=[0, 0.5, 0.75, 1, 1.25, 1.5, 2])
    ap.add_argument("--lams-homograf", nargs="*", type=float, default=[0, 0.5, 0.75, 1, 1.25, 1.5, 2])
    ap.add_argument("--defecte", nargs="*", default=["catala", "motor"])
    ap.add_argument("--max-greus", type=int, default=3)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--prior-traces", action="store_true",
                    help="substituïx el prior dels models KenLM per la suma de `tokens_prior` de "
                         "<detall>_traces_<model>.json (l'unigrama real de KenLM, sense <s> ni </s>)")
    ap.add_argument("--hibrid", metavar="MODEL",
                    help="les col·lisions (cop/cops) les decidix MODEL (p. ex. flor) amb el seu criteri del "
                         "sistema; la resta, el model simulat")
    ap.add_argument("--priors", help="JSON {total: {corpus: n}, corpus: {paraula: freq}}: substituïx el prior "
                    "dels models KenLM per ln((freq + 1) / total) (unigrama, sense <s> ni </s>)")
    a = ap.parse_args()

    d = json.loads(Path(a.detall).read_text(encoding="utf-8"))
    models = a.models or [m for m in d if m != "motor"]

    hibrid = None
    if a.hibrid:
        hibrid = {(b, f["id"]): f["tria"] for b, fs in d[a.hibrid]["fix"][1].items() for f in fs}
        models = [m for m in models if m != a.hibrid]
        print(f"HÍBRID: les col·lisions les decidix {a.hibrid} ({d[a.hibrid]['fix'][0]})\n")

    for model in models:
        criteri, benchmarks = d[model]["fix"]
        files = [dict(f, _bench=b) for b, fs in benchmarks.items() for f in fs]
        marge, defecte, lam, lam_c = llig_criteri(criteri)
        iguals = sum(decidix(f, marge, defecte, lam_c, lam) == f["tria"] for f in files)
        print(f"comprovació {model} ({criteri}): {iguals}/{len(files)} iguals")
        assert iguals == len(files), "el simulador no reprodueix el sistema"
        n, g = avalua(files, marge, defecte, lam_c, lam)
        print(f"  sistema: encerts {n['encert']}, greus {n[GREUS[0]] + n[GREUS[1]]} "
              f"(trad. sense caldre {n[GREUS[0]]}, candidat erroni {n[GREUS[1]]}), "
              f"sense traduir {n['sense_traduir']}  {dict(g)}")

        traces = Path(str(a.detall).removesuffix("_detall.json") + f"_traces_{model}.json")
        if a.prior_traces and model.startswith("kenlm") and traces.exists():
            t = json.loads(traces.read_text(encoding="utf-8"))
            priors = {}
            for fr in t["frases"]:
                for pt in fr["punts"]:
                    for c, v in pt["puntuacions"].items():
                        if v.get("tokens_prior"):
                            priors[c.lower()] = sum(x["lp"] for x in v["tokens_prior"])
            canviats = 0
            for f in files:
                for c, dd in (f.get("brut") or {}).items():
                    if c.lower() in priors:
                        dd["prior"], canviats = priors[c.lower()], canviats + 1
            print(f"  prior substituït per l'unigrama de KenLM ({traces.name}): {canviats} puntuacions")

        if a.priors and model.startswith("kenlm_val"):
            p = json.loads(Path(a.priors).read_text(encoding="utf-8"))
            corpus = ["net", "dogv"] if model.endswith("_dogv") else ["net"]
            total = sum(p["total"][c] for c in corpus)
            for f in files:
                for c, dd in (f.get("brut") or {}).items():
                    freq = sum(p[k].get(c.lower(), 0) for k in corpus)
                    dd["prior"] = math.log((freq + 1) / total)
            print(f"  prior substituït per l'unigrama de {'+'.join(corpus)} ({total} tokens)")

        resultats = []
        for marge, defecte, lc, lh in itertools.product(a.marges, a.defecte, a.lams_colisio, a.lams_homograf):
            n, g = avalua(files, marge, defecte, lc, lh, hibrid)
            greus = n[GREUS[0]] + n[GREUS[1]]
            resultats.append((n["encert"], -greus, marge, defecte, lc, lh, n, g))

        print(f"\n  Millors amb ≤ {a.max_greus} greus (ordenats per encerts):")
        print(f"  {'marge':>5s} {'defecte':7s} {'lam_col':>7s} {'lam_hom':>7s} {'encerts':>7s} {'greus':>5s} "
              f"{'t.s.c.':>6s} {'c.err':>5s} {'s.trad':>6s}  greus per paraula")
        bons = sorted((r for r in resultats if -r[1] <= a.max_greus), key=lambda r: (-r[0], -r[1]))
        for enc, mg, marge, defecte, lc, lh, n, g in bons[:a.top]:
            print(f"  {marge:5g} {defecte:7s} {lc:7g} {lh:7g} {enc:7d} {-mg:5d} {n[GREUS[0]]:6d} "
                  f"{n[GREUS[1]]:5d} {n['sense_traduir']:6d}  {dict(g)}")

        # Col·lisions soles: com canvia "cop/cops" amb lam_col
        col = [f for f in files if f["tipus"] == "colisio"]
        print(f"\n  Col·lisions ({len(col)} decisions) segons lam_col:")
        for lc in a.lams_colisio:
            n, g = avalua(col, 0, "catala", lc, 0)
            print(f"    lam_col {lc:4g}: encerts {n['encert']}, greus {n[GREUS[0]] + n[GREUS[1]]}  {dict(g)}")
        print()


if __name__ == "__main__":
    main()
