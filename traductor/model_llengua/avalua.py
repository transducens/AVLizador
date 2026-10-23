"""
Avalua el postprocessat amb model de llengua sobre
`benchmark_homografs_cat_val.json`, provant molts criteris alhora (el
model es crida una sola vegada per frase i candidat; les variants es
calculen després).

Mètriques per tipus de punt (colisio / irresoluble / resoluble):
- `sentit`: el candidat triat és l'esperat.
- `exactes`: la frase sencera és igual que la referència revisada.
La fila "motor sol" és el que fa hui el motor: a les col·lisions no tria
res (compta com a error) i als homògrafs resolubles decidix spaCy. La
columna `resoluble` de les files del model és NOMÉS informativa (el
sistema final hi deixa spaCy); el millor criteri es tria per colisio +
irresoluble.

Ús (des de l'arrel del repo; la primera vegada baixa el model):
    python -m traductor.model_llengua.avalua --per-defecte      # només el sistema final
    python -m traductor.model_llengua.avalua                    # graella per defecte
    python -m traductor.model_llengua.avalua --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b
    python -m traductor.model_llengua.avalua --lams 0 0.5 1 --normes suma mitjana --marges 0 2 5 \\
        --concordances motor variants --puntuacions frase dreta --spacy-irresolubles si no
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import time
from datetime import date
from pathlib import Path

from . import CONCORDANCA_PER_DEFECTE, Criteri, aplica_tries, puntua_punts
from .genera_benchmark import BENCHMARK
from .punts import TIPUS
from .puntuador import MODEL_PER_DEFECTE, ModelLlengua

RESULTATS = Path(__file__).resolve().parents[2] / "pipeline" / "03_seleccio_de_model" / "resultats"
TIPUS_SISTEMA = ("colisio", "irresoluble")


def _norm(s: str) -> str:
    return s.replace("’", "'").replace("ʼ", "'").strip()


def _resum(files: list[dict], clau_tria: str, clau_text: str) -> dict:
    res = {}
    for t in TIPUS + ("control",):
        sel = [f for f in files if (f["tipus"] or "control") == t]
        if sel:
            res[t] = {
                "n": len(sel),
                "sentit": sum(f[clau_tria] == f["esperat"] for f in sel),
                "exactes": sum(_norm(f[clau_text]) == _norm(f["occidental"]) for f in sel),
            }
    return res


def _fila(nom: str, r: dict) -> str:
    cel = []
    for t, v in r.items():
        if t == "control":
            continue
        etiqueta = f"{t} (info)" if t == "resoluble" and nom != "motor sol" else t
        cel.append(f"{etiqueta}: {v['sentit']}/{v['n']} sentit, {v['exactes']} exactes")
    if "control" in r:
        cel.append(f"control {r['control']['exactes']}/{r['control']['n']}")
    return f"{nom}\n    " + " | ".join(cel)


def main() -> None:
    d = Criteri()
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[MODEL_PER_DEFECTE])
    ap.add_argument("--per-defecte", action="store_true", help="només el criteri per defecte (el sistema final)")
    ap.add_argument("--lams", nargs="+", type=float, default=[0.0, 0.5, 1.0])
    ap.add_argument("--normes", nargs="+", default=["suma"], choices=["suma", "mitjana"])
    ap.add_argument("--marges", nargs="+", type=float, default=[0.0, 5.0])
    ap.add_argument("--concordances", nargs="+", default=[CONCORDANCA_PER_DEFECTE], choices=["motor", "variants"])
    ap.add_argument("--puntuacions", nargs="+", default=["frase", "dreta"], choices=["frase", "dreta"])
    ap.add_argument("--spacy-irresolubles", nargs="+", default=["si", "no"], choices=["si", "no"])
    ap.add_argument("--model-irresolubles", nargs="+", default=["si", "no"], choices=["si", "no"])
    ap.add_argument("--fils", type=int, default=None, help="fils de CPU per a torch")
    ap.add_argument("--benchmark", type=Path, default=BENCHMARK)
    args = ap.parse_args()
    if args.per_defecte:
        args.lams, args.normes, args.marges = [d.lam], [d.norma], [d.marge]
        args.concordances, args.puntuacions = [CONCORDANCA_PER_DEFECTE], [d.puntuacio]
        args.spacy_irresolubles = ["si" if d.spacy_irresolubles else "no"]
        args.model_irresolubles = ["si", "no"]

    items = json.loads(args.benchmark.read_text(encoding="utf-8"))["frases"]
    RESULTATS.mkdir(parents=True, exist_ok=True)

    for model_id in args.models:
        print(f"\n=== {model_id} ===")
        t0 = time.time()
        model = ModelLlengua(model_id, fils=args.fils)
        print(f"carregat en {time.time() - t0:.1f}s")

        millor, taula, primer = None, [], True
        for concordanca in args.concordances:
            t0 = time.time()
            puntuats = []
            for it in items:
                text_motor, punts = puntua_punts(it["oriental"], model, TIPUS, concordanca)
                # només el punt que avalua la frase
                punts = [p for p in punts if it["paraula"] and p.paraula.lower() == it["paraula"]][:1]
                puntuats.append((it, text_motor, punts))
            segons = (time.time() - t0) / len(items)
            print(f"\n-- concordança: {concordanca} ({segons:.2f} s/frase, CPU; menys si reaprofita la memòria cau)")

            files = [{**it, "tria_motor": punts[0].motor if punts else None} for it, _, punts in puntuats]
            if primer:
                print(_fila("motor sol", _resum(files, "tria_motor", "motor_sol")))
                primer = False

            for lam, norma, marge, punt_, sp, mi in itertools.product(
                    args.lams, args.normes, args.marges, args.puntuacions, args.spacy_irresolubles,
                    args.model_irresolubles):
                criteri = Criteri(lam=lam, norma=norma, marge=marge, tipus=TIPUS, puntuacio=punt_,
                                  spacy_irresolubles=sp == "si", model_irresolubles=mi == "si")
                for f, (it, text_motor, punts) in zip(files, puntuats):
                    f["text_ml"] = aplica_tries(text_motor, punts, criteri)
                    f["tria_ml"] = punts[0].tria if punts else None
                    f["decidit"] = punts[0].decidit if punts else ""
                    f["puntuacions"] = punts[0].puntuacions if punts else {}
                r = _resum(files, "tria_ml", "text_ml")
                nom = (f"conc={concordanca} punt={punt_} lam={lam} norma={norma} marge={marge} "
                       f"spacy_irres={sp} model_irres={mi}")
                print(_fila(nom, r))
                total = sum(r[t]["sentit"] for t in TIPUS_SISTEMA if t in r)
                exactes = sum(r[t]["exactes"] for t in TIPUS_SISTEMA if t in r)
                taula.append({"criteri": nom, "resum": r, "sentit_sistema": total, "exactes_sistema": exactes,
                              "s_per_frase": segons})
                if millor is None or (total, exactes) > millor[0]:
                    millor = ((total, exactes), nom, [dict(f) for f in files])

        claus = ("id", "tipus", "paraula", "esperat", "tria_motor", "tria_ml", "decidit", "oriental",
                 "occidental", "motor_sol", "text_ml", "puntuacions")
        detall = [{k: f.get(k) for k in claus} for f in millor[2]]
        eixida = RESULTATS / f"benchmark_homografs_ml_{model_id.split('/')[-1]}_{date.today():%Y%m%d}.json"
        eixida.write_text(json.dumps({"model": model_id, "taula": taula,
                                      "millor_criteri": millor[1], "detall_millor": detall},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nmillor (colisio + irresoluble): {millor[1]}\n    {millor[0][0]} sentits, "
              f"{millor[0][1]} frases exactes -> {eixida}")
        quants = collections.Counter((f["tipus"], f["decidit"]) for f in millor[2] if f["tipus"] in TIPUS_SISTEMA)
        print("    qui decidix:", ", ".join(f"{t}/{q}: {n}" for (t, q), n in sorted(quants.items())))
        for f in millor[2]:
            if f["tipus"] in TIPUS_SISTEMA and f["tria_ml"] != f["esperat"]:
                print(f"  ERROR {f['id']} {f['paraula']} ({f['decidit']}): esperat {f['esperat']}, "
                      f"triat {f['tria_ml']} | {f['oriental']}")


if __name__ == "__main__":
    main()
