"""
prepara_dades.py -- Dades per a les proves del biaix de FLOR (02/11/2026).

FLOR prefereix la forma més freqüent ("rentadora" davant "llavadora",
"nou" davant "anou") perquè s'ha entrenat amb molt més català que
valencià. Este script prepara el que necessiten les tres opcions que es
proven (vore README.md):

1. `paragrafs.json` -- paràgrafs en valencià normatiu per a posar davant
   de cada frase candidata (opció 1): un d'escrit a mà i quatre trets
   automàticament del corpus de l'AVL (llavor fixa), sense cap de les
   paraules ambigües ni dels seus candidats.
2. `freq.json` -- freqüència de les paraules ambigües i dels seus
   candidats en textos valencians (AVL + BOE en valencià) i catalans (BOE
   en català), per a corregir la freqüència de FLOR (opció 2). Les
   paraules ixen del lèxic (`carrega_punts`), no d'una llista a mà.
3. `entrenament_valencia.txt` -- frases valencianes per a continuar
   l'entrenament de FLOR (opció 3), sense cap frase que aparega en els
   benchmarks.

Ús (des de l'arrel del repo; necessita `dades/avl/final/unified.jsonl` i
`dades/boe/{valencia,catala}/*.jsonl`, que no estan en git):
    python pipeline/03_seleccio_de_model/model_llengua/sesgo/prepara_dades.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from avlizador.avaluacio.avalua import BENCHMARKS, troba_dir_benchmarks
from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[3]
AVL = ARREL / "dades" / "avl" / "final" / "unified.jsonl"
BOE_VAL = ARREL / "dades" / "boe" / "valencia" / "boe_corpus_entrenamiento_val.jsonl"
BOE_CAT = ARREL / "dades" / "boe" / "catala" / "boe_corpus_entrenamiento_cat.jsonl"
PARAULA = re.compile(r"[a-zàáèéíïòóúüç·]+", re.IGNORECASE)
LLAVOR = 21
N_ENTRENAMENT = 40_000

PARAGRAF_A_MA = ("Este és un text escrit en valencià. Hui els xiquets han eixit prompte de l'escola "
                 "i se n'han anat a casa per a vore la seua família.")


def normalitza(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("´", "'").strip().lower())


def frases_benchmarks() -> set[str]:
    dir_b = troba_dir_benchmarks()
    vistes = set()
    for _, ruta in BENCHMARKS.values():
        p = dir_b / ruta
        if p.exists() and "complet" not in ruta:
            for x in json.loads(p.read_text(encoding="utf-8")):
                vistes.add(normalitza(x["oriental"]))
                vistes.add(normalitza(x["occidental"]))
    return vistes


def frases_de(text: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if f.strip()]


def main() -> int:
    for f in (AVL, BOE_VAL, BOE_CAT):
        if not f.exists():
            print(f"ERROR: falta {f}", file=sys.stderr)
            return 1
    punts = carrega_punts()
    objectiu = set(punts) | {c.lower() for p in punts.values() for c in p["candidats"]}
    vistes = frases_benchmarks()
    rng = random.Random(LLAVOR)

    avl = [json.loads(l) for l in AVL.open(encoding="utf-8")]
    boe_val = [json.loads(l)["texto"] for l in BOE_VAL.open(encoding="utf-8")]

    # 1. paràgrafs (opció 1)
    candidats = []
    for d in avl:
        frases = [f for f in frases_de(d["text"]) if 6 <= len(f.split()) <= 30 and normalitza(f) not in vistes]
        bloc = " ".join(frases[:3])
        paraules = {w.lower() for w in PARAULA.findall(bloc)}
        if 30 <= len(bloc.split()) <= 60 and not (paraules & objectiu):
            candidats.append(bloc)
    rng.shuffle(candidats)
    paragrafs = [{"id": "P1", "origen": "escrit a mà", "text": PARAGRAF_A_MA}] + [
        {"id": f"P{n + 2}", "origen": "corpus AVL", "text": t} for n, t in enumerate(candidats[:4])]
    (AQUI / "paragrafs.json").write_text(json.dumps(paragrafs, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2. freqüències (opció 2)
    def compta(textos) -> tuple[Counter, int]:
        c, total = Counter(), 0
        for t in textos:
            for w in PARAULA.findall(t.lower()):
                total += 1
                if w in objectiu:
                    c[w] += 1
        return c, total
    val, n_val = compta([d["text"] for d in avl] + boe_val)
    cat, n_cat = compta(json.loads(l)["texto"] for l in BOE_CAT.open(encoding="utf-8"))
    (AQUI / "freq.json").write_text(json.dumps({
        "valencia": {"total": n_val, "paraules": dict(val)},
        "catala": {"total": n_cat, "paraules": dict(cat)},
        "fonts": {"valencia": "AVL (unified.jsonl) + BOE en valencià", "catala": "BOE en català"},
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # 3. frases d'entrenament (opció 3): AVL + BOE val, sense les dels benchmarks
    frases = []
    for d in avl:
        frases += [f for f in frases_de(d["text"]) if 5 <= len(f.split()) <= 60]
    frases += [t for t in boe_val if 5 <= len(t.split()) <= 60]
    frases = [f for f in dict.fromkeys(frases) if normalitza(f) not in vistes]
    rng.shuffle(frases)
    (AQUI / "entrenament_valencia.txt").write_text("\n".join(frases[:N_ENTRENAMENT]) + "\n", encoding="utf-8")

    print(f"paràgrafs: {len(paragrafs)} | freq val: {n_val} paraules, cat: {n_cat} | "
          f"frases d'entrenament: {min(len(frases), N_ENTRENAMENT)} de {len(frases)}")
    for w in sorted(objectiu):
        print(f"  {w:<12} val {val[w]:>6}  cat {cat[w]:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
