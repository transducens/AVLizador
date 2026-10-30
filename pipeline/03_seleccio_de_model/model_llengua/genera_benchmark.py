"""
Genera `benchmark_homografs_cat_val.json` a partir de `frases_homografs.json`:
la referència valenciana (`occidental`) és la traducció del MOTOR amb el
candidat esperat posat al punt ambigu (i el determinant concordat). Les
referències s'han de revisar a mà després (p.ex. "un altre vegada" ->
"una altra vegada", que el motor no concorda); per això no sobreescriu un
benchmark existent sense `--sobreescriu`.

Ús (des de l'arrel del repo):
    python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py [--sobreescriu]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from avlizador.traductor_cat_val.rules import detokenize
from avlizador.traductor_cat_val.rules.cat_val.engine import RuleEngineInvers
from avlizador.traductor_cat_val.model_llengua.punts import TIPUS, aplica_candidat, base_neutra, carrega_punts, detecta

AQUI = Path(__file__).resolve().parent
FRASES = AQUI / "frases_homografs.json"
BENCHMARK = AQUI / "benchmark_homografs_cat_val.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sobreescriu", action="store_true")
    args = ap.parse_args()
    if BENCHMARK.exists() and not args.sobreescriu:
        raise SystemExit(f"{BENCHMARK.name} ja existix (i potser l'has revisat). Usa --sobreescriu.")

    motor, punts = RuleEngineInvers(), carrega_punts()
    frases = json.loads(FRASES.read_text(encoding="utf-8"))["frases"]
    items, avisos = [], []
    for n, f in enumerate(frases, 1):
        tokens = motor.tradueix_tokens(f["text"])
        motor_sol = detokenize(tokens)
        item = {"id": f"HG{n:03d}", "oriental": f["text"], "paraula": f["paraula"],
                "esperat": f["esperat"], "tipus": None, "motor_sol": motor_sol}
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

    BENCHMARK.write_text(json.dumps({
        "descripcio": "Benchmark d'homògrafs cat->val (generat per genera_benchmark.py; referències a revisar a mà). "
                      "`occidental` = referència valenciana; `motor_sol` = el que dona hui el motor sense model.",
        "frases": items,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} frases -> {BENCHMARK}")
    for a in avisos:
        print("AVÍS", a)


if __name__ == "__main__":
    main()
