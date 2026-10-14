#!/usr/bin/env python3
"""analitza_fallades.py -- Llig un JSON de resultats d'`evalua_models.py`
(el fitxer que guarda a `resultats/benchmark_<model>_<data>.json`) i
imprimix, per cada frase NO exacta, les paraules/tokens concrets que
difereixen entre referencia i hipotesi (diff a nivell de paraula, no de
caracter). Pensat per a repetir rapidament l'analisi de "que sigue
fallando" sense haver de tornar a fer-ho a ma cada vegada -- vore
`traductor/README.md`, seccio "ANALISI DE FALLADES RESIDUALS
(07/10/2026)" per a la categoritzacio feta amb este script el 07/10/2026.

Us:
    python analitza_fallades.py resultats/benchmark_Traductor_Nou_XXXX.json
    python analitza_fallades.py resultats/benchmark_Traductor_Nou_XXXX.json --id RC017
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path


def diff_paraules(referencia: str, hipotesi: str) -> list[tuple[str, str]]:
    ref_w = referencia.split()
    hip_w = hipotesi.split()
    sm = difflib.SequenceMatcher(None, ref_w, hip_w)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            diffs.append((" ".join(ref_w[i1:i2]), " ".join(hip_w[j1:j2])))
    return diffs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resultats_json", type=Path)
    parser.add_argument("--id", default=None, help="Nomes mostra esta frase concreta")
    args = parser.parse_args()

    data = json.loads(args.resultats_json.read_text(encoding="utf-8"))
    resultats = data["resultats"]
    fails = [r for r in resultats if not r["exacte"]]
    if args.id:
        fails = [r for r in fails if r["id"] == args.id]

    print(f"Total frases: {len(resultats)} -- fallos: {len(fails)}\n")
    for r in fails:
        diffs = diff_paraules(r["referencia"], r["hipotesi"])
        print(f"{r['id']}: {diffs}")
        if args.id:
            print("  OCCIDENTAL:", r["occidental"])
            print("  REFERENCIA:", r["referencia"])
            print("  HIPOTESI  :", r["hipotesi"])


if __name__ == "__main__":
    main()
