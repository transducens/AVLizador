"""
Construïx `benchmark_sistema_final_cat_val.json` (23/10/2026): el benchmark
per a provar el SISTEMA FINAL de cat->val (motor + model de llengua per als
homògrafs) contra el motor sol. Junta, sense tocar cap fitxer d'origen:

1. `benchmark_corpus.json` (les 154 frases "del 151") -- `categoria: "151"`.
   Cap té paraules dels punts del model: el sistema final hi ha de donar
   EXACTAMENT el mateix que el motor (prova de no regressió).
2. `traductor/model_llengua/benchmark_homografs_cat_val.json` (el revisat a
   mà) -- `categoria: "homografs_<tipus>"` (colisio, irresoluble,
   resoluble) o `"homografs_control"`.
3. Les frases de `frases_homografs.json` que encara no hi són (afegides
   després de generar-lo), amb la referència del motor i el candidat
   esperat -- `revisat: false`, s'han de revisar també.

Es torna a executar cada vegada que canvia el benchmark d'homògrafs (així
recull les teues correccions):

    cd pipeline/03_seleccio_de_model
    python construeix_benchmark_sistema_final.py
    python evalua_models.py --model traductor --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
    python evalua_models.py --model traductor_ml --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parent.parent
sys.path.insert(0, str(ARREL))

BENCHMARK_151 = AQUI / "benchmark_corpus.json"
DIR_ML = ARREL / "traductor" / "model_llengua"
HOMOGRAFS = DIR_ML / "benchmark_homografs_cat_val.json"
FRASES = DIR_ML / "frases_homografs.json"
EIXIDA = AQUI / "benchmark_sistema_final_cat_val.json"


def _frases_noves(ja: set[str]) -> list[dict]:
    """Frases de `frases_homografs.json` que no són al benchmark revisat."""
    pendents = [f for f in json.loads(FRASES.read_text(encoding="utf-8"))["frases"]
                if f["text"] not in ja and f["paraula"]]
    if not pendents:
        return []
    from traductor.model_llengua.punts import TIPUS, aplica_candidat, base_neutra, carrega_punts, detecta
    from traductor.rules import detokenize
    from traductor.rules.cat_val.engine import RuleEngineInvers

    motor, punts = RuleEngineInvers(), carrega_punts()
    noves = []
    for n, f in enumerate(pendents, 1):
        tokens = motor.tradueix_tokens(f["text"])
        trobats = [p for p in detecta(tokens, punts, TIPUS) if p.paraula.lower() == f["paraula"]]
        if not trobats or f["esperat"] not in trobats[0].candidats:
            print(f"AVÍS: no s'ha trobat el punt «{f['paraula']}» -> {f['text']}")
            continue
        p = trobats[0]
        noves.append({
            "id": f"HGN{n:02d}", "oriental": f["text"],
            "occidental": detokenize(aplica_candidat(base_neutra(motor, f["text"], [p]), p, f["esperat"])),
            "categoria": f"homografs_{p.tipus}", "paraula": f["paraula"], "esperat": f["esperat"],
            "font": f.get("font", "a_ma"), "revisat": False,
        })
    return noves


def main() -> None:
    items = []
    for b in json.loads(BENCHMARK_151.read_text(encoding="utf-8")):
        items.append({**b, "categoria": "151"})
    homografs = json.loads(HOMOGRAFS.read_text(encoding="utf-8"))["frases"]
    for h in homografs:
        items.append({
            "id": h["id"], "oriental": h["oriental"], "occidental": h["occidental"],
            "categoria": f"homografs_{h['tipus'] or 'control'}", "paraula": h["paraula"], "esperat": h["esperat"],
            "font": "a_ma", "revisat": True,
        })
    noves = _frases_noves({h["oriental"] for h in homografs})
    items += noves
    EIXIDA.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    per_cat: dict[str, int] = {}
    for it in items:
        per_cat[it["categoria"]] = per_cat.get(it["categoria"], 0) + 1
    print(f"{len(items)} frases -> {EIXIDA}")
    for c, n in sorted(per_cat.items()):
        print(f"  {c}: {n}")
    for it in noves:
        print(f"  NOVA (a revisar) {it['id']}: {it['occidental']}")


if __name__ == "__main__":
    main()
