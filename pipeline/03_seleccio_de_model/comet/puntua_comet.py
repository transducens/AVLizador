"""
puntua_comet.py -- Puntua amb XCOMET-XL (o un altre model COMET) traduccions
cat->val que ja existixen, sense tornar a traduir (03/11/2026).

Llig JSON amb una llista `resultats` de frases amb `entrada` (català),
`hipotesi` (traducció) i `referencia` (valencià): els de `avlizador avalua`
i els de `baseline_llm/resultats/`. Carrega el model una sola vegada i, per
a cada fitxer, guarda la nota de cada frase i, amb XCOMET, els trossos que
el model marca com a error (`error_spans`). Al final escriu una taula amb
la nota de cada sistema: mescla, BOE i AVL (pel prefix de l'id).

Pensat per a Abaco amb GPU (vore `comet.sh`). XCOMET-XL té uns 3.500
milions de paràmetres: en fp32 ocupa ~14 GB, i les GPU d'Abaco en tenen
11, per això per defecte es carrega en fp16 (~7 GB).

    python puntua_comet.py ../baseline_llm/resultats/*.json entrades/*.json
    python puntua_comet.py --limit 10 entrades/avlizador_1.1.0.json      # prova
    python puntua_comet.py --sense-referencia ...                        # QE: només entrada + traducció

Necessita `unbabel-comet` i torch amb CUDA (no el paquet avlizador), i
haver acceptat les condicions de `Unbabel/XCOMET-XL` a Hugging Face amb
`huggingface-cli login` fet (el model és d'accés restringit; llicència
CC BY-NC-SA 4.0: per a avaluar, no per a distribuir).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MODEL_PER_DEFECTE = "Unbabel/XCOMET-XL"
SUBCONJUNTS = {"BOE": "BM-BOE-", "AVL": "BM-AVL-"}

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def carrega_model(nom: str, precisio: str):
    import torch
    from comet import download_model, load_from_checkpoint

    model = load_from_checkpoint(download_model(nom))
    if precisio == "fp16":
        model = model.half()
    elif precisio == "bf16":
        model = model.to(torch.bfloat16)
    return model


def llig(fitxer: Path, limit: int | None) -> tuple[str, list[dict]]:
    d = json.loads(fitxer.read_text(encoding="utf-8"))
    frases = d["resultats"] if isinstance(d, dict) else d
    nom = d.get("sistema", fitxer.stem) if isinstance(d, dict) else fitxer.stem
    return nom, frases[:limit] if limit else frases


def mitjana(valors: list[float]) -> float | None:
    return round(sum(valors) / len(valors), 2) if valors else None


def puntua(model, frases: list[dict], amb_referencia: bool, lot: int, gpus: int) -> list[dict]:
    mostres = [{"src": f["entrada"], "mt": f["hipotesi"], **({"ref": f["referencia"]} if amb_referencia else {})}
               for f in frases]
    eixida = model.predict(mostres, batch_size=lot, gpus=gpus, progress_bar=False)
    # `Prediction` és un dict; només XCOMET hi posa `metadata.error_spans`
    spans = (eixida.get("metadata") or {}).get("error_spans")
    puntuades = []
    for i, (f, nota) in enumerate(zip(frases, eixida["scores"])):
        fila = {"id": f["id"], "entrada": f["entrada"], "referencia": f["referencia"], "hipotesi": f["hipotesi"],
                "comet": round(nota * 100, 2)}
        if spans is not None:
            fila["error_spans"] = [{"text": s.get("text"), "severity": s.get("severity"),
                                    "confidence": round(float(s.get("confidence", 0)), 3)} for s in spans[i]]
        puntuades.append(fila)
    return puntuades


def resum(puntuades: list[dict]) -> dict:
    r = {"total": mitjana([p["comet"] for p in puntuades]), "n": len(puntuades)}
    for nom, prefix in SUBCONJUNTS.items():
        r[nom] = mitjana([p["comet"] for p in puntuades if p["id"].startswith(prefix)])
    if any("error_spans" in p for p in puntuades):
        r["frases_amb_error"] = sum(1 for p in puntuades if p.get("error_spans"))
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fitxers", nargs="+", type=Path, help="JSON amb `resultats` (entrada, hipotesi, referencia).")
    ap.add_argument("--model", default=MODEL_PER_DEFECTE)
    ap.add_argument("--precisio", choices=["fp32", "fp16", "bf16"], default="fp16")
    ap.add_argument("--lot", type=int, default=8, help="Frases per lot en la GPU.")
    ap.add_argument("--gpus", type=int, default=1, help="0 = CPU (molt lent amb XCOMET-XL).")
    ap.add_argument("--sense-referencia", action="store_true", help="Mode QE: només entrada i traducció.")
    ap.add_argument("--limit", type=int, help="Només les N primeres frases de cada fitxer (prova).")
    ap.add_argument("--eixida", type=Path, default=AQUI / "resultats")
    args = ap.parse_args(argv)

    fitxers = [f for f in args.fitxers if "_limit" not in f.stem]
    curt = args.model.split("/")[-1] + ("_qe" if args.sense_referencia else "") + (f"_limit{args.limit}" if args.limit else "")
    args.eixida.mkdir(parents=True, exist_ok=True)
    inici = time.time()
    print(f"Carregant {args.model} ({args.precisio})...", flush=True)
    model = carrega_model(args.model, args.precisio)
    print(f"  carregat en {time.time() - inici:.0f} s", flush=True)

    files = []
    for fitxer in fitxers:
        nom, frases = llig(fitxer, args.limit)
        t0 = time.time()
        puntuades = puntua(model, frases, not args.sense_referencia, args.lot, args.gpus)
        r = resum(puntuades)
        (args.eixida / f"{fitxer.stem}__{curt}.json").write_text(json.dumps({
            "sistema": nom, "fitxer": fitxer.name, "model": args.model, "precisio": args.precisio,
            "amb_referencia": not args.sense_referencia, "timestamp": datetime.now().isoformat(timespec="seconds"),
            "segons": round(time.time() - t0, 1), "resum": r, "resultats": puntuades,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        files.append((nom, r))
        print(f"  {nom}: {r['total']} (BOE {r['BOE']}, AVL {r['AVL']}) en {time.time() - t0:.0f} s", flush=True)

    files.sort(key=lambda x: -(x[1]["total"] or 0))
    linies = [f"## {datetime.now():%d/%m/%Y %H:%M} — {args.model} ({args.precisio}"
              f"{', sense referència' if args.sense_referencia else ''})", "",
              "| Sistema | Mescla | BOE | AVL | Frases amb error |", "|---|---|---|---|---|"]
    def n(x):
        return "—" if x is None else x

    for nom, r in files:
        linies.append(f"| {nom} | {n(r['total'])} | {n(r['BOE'])} | {n(r['AVL'])} | "
                      f"{r.get('frases_amb_error', '—')}/{r['n']} |")
    taula = "\n".join(linies) + "\n"
    (args.eixida / f"resum__{curt}.md").write_text(taula, encoding="utf-8")
    print("\n" + taula)
    return 0


if __name__ == "__main__":
    sys.exit(main())
