"""
prepara_dades.py -- Fitxers d'entrenament d'un classificador fastText
valencià/català amb frases de MaCoCu-ca (10/11/2026; vore README.es.md
d'esta carpeta).

- Català: `dades/macocu/catala_pur.jsonl` (GD 0 amb >= 2 marcadors,
  `../catala/filtra_macocu.py`).
- Valencià: `dades/macocu/valencia/valencia.jsonl` (`../valencia/`), però
  només les de GD >= `--gd-val` (1,0) amb >= `--min-marcadors` (2)
  marcadors occidentals: el mateix criteri que el català, a l'inrevés.
  Amb 1 sol marcador la majoria són català normal amb un fals marcador
  ("vegada", "permet", "alcalde").
- Fora les frases dels benchmarks (manual, homògrafs v1/v2, 151), per
  si n'hi ha alguna en MaCoCu.
- Mateixa quantitat de frases de cada classe (el català, mostrejat a
  l'atzar amb llavor fixa) i 10.000 de cada per a validar.
- Text normalitzat com el de KenLM (`../kenlm/exporta_text.normalitza`):
  la mateixa funció s'ha d'aplicar a les frases que es classifiquen.

Eixida (`dades/macocu/fasttext/`): `train.txt` i `valid.txt` (una frase
per línia: `__label__val ...` / `__label__cat ...`), `prova.txt` (parells
de prova per a `predict-prob`) i `estadistiques.json`.

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/fasttext/prepara_dades.py
    python pipeline/08_traduccio_corpus/macocu/fasttext/prepara_dades.py --min-marcadors 1 --gd-val 0.75
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

DIR_MACOCU = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_MACOCU))
sys.path.insert(0, str(DIR_MACOCU / "kenlm"))
from comu import ARREL, DIR, clau_repetida  # noqa: E402
from exporta_text import normalitza  # noqa: E402

CAT = DIR / "catala_pur.jsonl"
VAL = DIR / "valencia" / "valencia.jsonl"
EIXIDA = DIR / "fasttext"
BENCHMARKS = [
    "manual/benchmark_manual_cat_val.json",
    "homografs/benchmark_homografs_cat_val.json",
    "homografs/benchmark_homografs_v2_cat_val.json",
    "curat_151/benchmark_corpus.json",
]

# Parells de prova: la mateixa frase amb la forma catalana i la valenciana.
PROVA = [
    "Una altra vegada hem guanyat el partit.",
    "Un altre colp hem guanyat el partit.",
    "Aquest servei és nou i funciona molt bé.",
    "Este servici és nou i funciona molt bé.",
    "Aquesta tarda els nens han sortit a jugar al carrer.",
    "Esta vesprada els xiquets han eixit a jugar al carrer.",
    "Cal que tinguin en compte les seves necessitats.",
    "Cal que tinguen en compte les seues necessitats.",
]


def claus_benchmarks() -> set[bytes]:
    """Claus (`clau_repetida`) de les dos bandes de cada benchmark."""
    claus: set[bytes] = set()
    for rel in BENCHMARKS:
        path = ARREL / "dades" / "benchmarks" / rel
        if not path.exists():
            print(f"  (no trobe {path}, no s'exclou)")
            continue
        dades = json.loads(path.read_text(encoding="utf-8"))
        files = dades if isinstance(dades, list) else next(v for v in dades.values() if isinstance(v, list))
        for f in files:
            for camp in ("oriental", "occidental"):
                if f.get(camp):
                    claus.add(clau_repetida(f[camp]))
    return claus


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cat", type=Path, default=CAT)
    p.add_argument("--val", type=Path, default=VAL)
    p.add_argument("--eixida", type=Path, default=EIXIDA)
    p.add_argument("--gd-val", type=float, default=1.0, help="GD mínim de les valencianes (1,0 = pures)")
    p.add_argument("--min-marcadors", type=int, default=2, help="marcadors occidentals mínims (2)")
    p.add_argument("--max-per-classe", type=int, default=0, help="0 = totes les valencianes que passen")
    p.add_argument("--valid", type=int, default=10_000, help="frases de validació per classe")
    p.add_argument("--llavor", type=int, default=13)
    args = p.parse_args(argv)

    t0 = time.time()
    est: Counter = Counter()
    excloses = claus_benchmarks()
    print(f"Frases de benchmarks excloses: {len(excloses):,}")
    vistes: set[bytes] = set()

    def fora_benchmark(text: str, classe: str) -> bool:
        if clau_repetida(text) in excloses:
            est[f"{classe}_benchmark"] += 1
            return True
        return False

    # 1. Valencià: totes les que passen el criteri (sense repetides).
    val: list[str] = []
    with open(args.val, encoding="utf-8") as f:
        for linia in f:
            est["val_llegides"] += 1
            r = json.loads(linia)
            if r["gd"] < args.gd_val or r["occ"] < args.min_marcadors:
                continue
            clau = clau_repetida(r["text"])
            if clau in excloses:
                est["val_benchmark"] += 1
                continue
            if clau in vistes:
                est["val_repetides"] += 1
                continue
            vistes.add(clau)
            val.append(normalitza(r["text"]))
    rng = random.Random(args.llavor)
    rng.shuffle(val)
    if args.max_per_classe:
        val = val[: args.max_per_classe]
    objectiu = len(val)
    print(f"Valencianes: {objectiu:,} de {est['val_llegides']:,} ({time.time() - t0:,.0f} s)", flush=True)

    # 2. Català: mostra a l'atzar de la mateixa grandària (reservori). Les
    # repetides ja les ha llevades el filtre català; només es normalitzen
    # les que queden en la mostra.
    cat: list[str] = []
    vistes_cat = 0
    with open(args.cat, encoding="utf-8") as f:
        for linia in f:
            est["cat_llegides"] += 1
            if est["cat_llegides"] % 1_000_000 == 0:
                print(f"  {est['cat_llegides']:,} catalanes llegides ({time.time() - t0:,.0f} s)", flush=True)
            vistes_cat += 1
            if len(cat) < objectiu:
                cat.append(linia)
            else:
                j = rng.randrange(vistes_cat)
                if j < objectiu:
                    cat[j] = linia
    cat = [json.loads(l)["text"] for l in cat]
    cat = [normalitza(t) for t in cat if not fora_benchmark(t, "cat")]
    rng.shuffle(cat)
    print(f"Catalanes: {len(cat):,} de {vistes_cat:,} ({time.time() - t0:,.0f} s)", flush=True)
    n = min(len(val), len(cat))
    if n <= 2 * args.valid:
        sys.exit(f"Massa poques frases ({n:,} per classe) per a {args.valid:,} de validació.")

    # 3. Validació (les primeres `--valid` de cada classe) i entrenament.
    def escriu(path: Path, parells: list[tuple[str, str]]) -> None:
        rng.shuffle(parells)
        path.write_text("".join(f"__label__{c} {t}\n" for c, t in parells), encoding="utf-8")

    args.eixida.mkdir(parents=True, exist_ok=True)
    v = args.valid
    escriu(args.eixida / "valid.txt", [("val", t) for t in val[:v]] + [("cat", t) for t in cat[:v]])
    escriu(args.eixida / "train.txt", [("val", t) for t in val[v:n]] + [("cat", t) for t in cat[v:n]])
    (args.eixida / "prova.txt").write_text("".join(normalitza(t) + "\n" for t in PROVA), encoding="utf-8")

    resum = {
        "gd_val": args.gd_val, "min_marcadors": args.min_marcadors, "llavor": args.llavor,
        "per_classe": n, "train_per_classe": n - v, "valid_per_classe": v,
        "cat_valides": vistes_cat, **est, "segons": round(time.time() - t0),
    }
    (args.eixida / "estadistiques.json").write_text(json.dumps(resum, indent=2), encoding="utf-8")
    print(json.dumps(resum, indent=2))


if __name__ == "__main__":
    main()
