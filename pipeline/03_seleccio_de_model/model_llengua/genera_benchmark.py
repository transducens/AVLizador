"""
Genera `benchmark_homografs_cat_val.json` a partir de `frases_homografs.json`:
la referència valenciana (`occidental`) és la traducció del MOTOR amb el
candidat esperat posat al punt ambigu (i el determinant concordat). Les
referències s'han de revisar a mà després (p.ex. "un altre vegada" ->
"una altra vegada", que el motor no concorda); per això no sobreescriu un
benchmark existent sense `--sobreescriu`.

`--v2` (02/11/2026): el benchmark d'homògrafs v2, a partir de
`frases_homografs_v2.json` (les 18 formes d'homonimia lèxica, 4 frases per
sentit, amb el camp `sentit`). Escriu `benchmark_homografs_v2_cat_val.json`
ací i una còpia en `dades/benchmarks/homografs/` en el format de
`avlizador avalua` (llista de `{id, oriental, occidental, ...}`).

Ús (des de l'arrel del repo):
    python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py [--sobreescriu]
    python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py --v2 [--sobreescriu]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from avlizador.traductor_cat_val.rules import detokenize
from avlizador.traductor_cat_val.rules.cat_val.engine import RuleEngineInvers
from avlizador.traductor_cat_val.model_llengua.punts import TIPUS, aplica_candidat, base_neutra, carrega_punts, detecta

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[2]
FRASES = AQUI / "frases_homografs.json"
BENCHMARK = AQUI / "benchmark_homografs_cat_val.json"
FRASES_V2 = AQUI / "frases_homografs_v2.json"
BENCHMARK_V2 = AQUI / "benchmark_homografs_v2_cat_val.json"
COPIA_V2 = ARREL / "dades" / "benchmarks" / "homografs" / "benchmark_homografs_v2_cat_val.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sobreescriu", action="store_true")
    ap.add_argument("--v2", action="store_true", help="Benchmark d'homògrafs v2 (frases_homografs_v2.json).")
    args = ap.parse_args()
    frases_path, benchmark, prefix = (FRASES_V2, BENCHMARK_V2, "HG2-") if args.v2 else (FRASES, BENCHMARK, "HG")
    if benchmark.exists() and not args.sobreescriu:
        raise SystemExit(f"{benchmark.name} ja existix (i potser l'has revisat). Usa --sobreescriu.")

    motor, punts = RuleEngineInvers(), carrega_punts()
    frases = json.loads(frases_path.read_text(encoding="utf-8"))["frases"]
    items, avisos = [], []
    for n, f in enumerate(frases, 1):
        tokens = motor.tradueix_tokens(f["text"])
        motor_sol = detokenize(tokens)
        item = {"id": f"{prefix}{n:03d}", "oriental": f["text"], "paraula": f["paraula"],
                "esperat": f["esperat"], "tipus": None, "motor_sol": motor_sol}
        if "sentit" in f:
            item["sentit"] = f["sentit"]
        if f["paraula"] is None:
            item["occidental"] = motor_sol
        else:
            trobats = [p for p in detecta(tokens, punts, TIPUS) if p.paraula.lower() == f["paraula"]]
            if not trobats or f["esperat"] not in trobats[0].candidats:
                avisos.append(f"{item['id']}: no s'ha trobat el punt «{f['paraula']}» -> {f['text']}")
                continue
            punt = trobats[0]
            item["tipus"] = punt.tipus
            base = base_neutra(motor, f["text"], [punt])
            item["occidental"] = detokenize(aplica_candidat(base, punt, f["esperat"]))
        items.append(item)

    benchmark.write_text(json.dumps({
        "descripcio": "Benchmark d'homògrafs cat->val (generat per genera_benchmark.py; referències a revisar a mà). "
                      "`occidental` = referència valenciana; `motor_sol` = el que dona hui el motor sense model.",
        "frases": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} frases -> {benchmark}")
    if args.v2:
        COPIA_V2.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"còpia per a `avlizador avalua` -> {COPIA_V2}")
    for a in avisos:
        print("AVÍS", a)


if __name__ == "__main__":
    main()
