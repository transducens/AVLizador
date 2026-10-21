#!/usr/bin/env python3
"""Avalua les capes de LLM de `traductor/llm/` (21/10/2026) contra un
benchmark (`id`/`occidental`/`oriental`): motor sol vs. motor + LLM, amb
les mateixes mètriques que `evalua_models.py`, i l'encert del LLM punt a
punt comparat amb el valor per defecte del motor.

Per a cada punt ambigu es mira quina opció apareix a la referència
("veritat"); si n'apareix exactament una (o, en el mode verbal de 3a
plural, "indicatiu" i "cap", que donen el mateix text), es compta si
l'encerta el LLM i si l'encertava el motor.

Ús (des de l'arrel del repo; en Abaco, exporta AVLIZADOR_ROOT):

    python pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py \\
        --direccio cat-val --benchmark dades/boe/benchmark_boe_mostra_2000.json \\
        --model qwen3:8b --tipus demostratiu,b4

    # Només comptar punts, sense cridar cap model:
    python .../avalua_capa_llm.py --direccio val-cat --sense-llm
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ENV = os.environ.get("AVLIZADOR_ROOT")
ARREL = Path(_ENV) if _ENV else Path(__file__).resolve().parents[3]
DIR_03 = ARREL / "03_seleccio_de_model" if _ENV else ARREL / "pipeline" / "03_seleccio_de_model"
sys.path.insert(0, str(ARREL))
sys.path.insert(0, str(DIR_03))

from traductor.llm import ClientLLM, tradueix_cat_val, tradueix_val_cat  # noqa: E402
from evalua_models import calcula_metriques  # noqa: E402


def _apareix(text: str, referencia: str) -> bool:
    text = text.strip()
    return bool(text) and re.search(rf"(?<![\w'’-]){re.escape(text)}(?![\w'’-])", referencia.replace("’", "'"), re.I) is not None


def veritat(punt, referencia: str) -> set[str]:
    """Etiquetes la forma de les quals apareix a la referència."""
    return {e for e, textos in punt.opcions.items() if _apareix("".join(textos), referencia)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--direccio", choices=["cat-val", "val-cat"], required=True)
    ap.add_argument("--benchmark", type=Path, default=DIR_03 / "benchmark_corpus.json")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--tipus", default=None, help="cat-val: 'demostratiu', 'b4' o tots dos separats per coma")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sense-llm", action="store_true", help="només detecta i compta punts")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--sortida", type=Path, default=None)
    args = ap.parse_args()

    dades = json.loads(args.benchmark.read_text(encoding="utf-8"))[: args.limit]
    entrada, ref_camp = ("oriental", "occidental") if args.direccio == "cat-val" else ("occidental", "oriental")
    client = None if args.sense_llm else ClientLLM(args.model, args.ollama_url, args.timeout, args.verbose)
    tipus = set(args.tipus.split(",")) if args.tipus else None

    resultats = []
    estad = collections.defaultdict(collections.Counter)
    exactes_base = exactes_llm = 0
    t0 = time.perf_counter()
    for n, reg in enumerate(dades, 1):
        text, ref = reg[entrada], reg[ref_camp]
        if args.direccio == "cat-val":
            base, _ = tradueix_cat_val(text, None, tipus)
            final, punts = tradueix_cat_val(text, client, tipus)
        else:
            base, _ = tradueix_val_cat(text, None)
            final, punts = tradueix_val_cat(text, client)
        mb, mf = calcula_metriques(base, ref), calcula_metriques(final, ref)
        exactes_base += mb["exacte"]
        exactes_llm += mf["exacte"]
        info = []
        for p in punts:
            v = veritat(p, ref)
            if p.tipus == "mode_verbal" and v == {"indicatiu", "cap"}:
                v = {"indicatiu", "cap"}  # mateix text: les dos són correctes
            elif len(v) != 1:
                v = set()
            e = estad[p.tipus]
            e["punts"] += 1
            e["canviats pel LLM"] += p.decisio != p.per_defecte
            e["sense resposta vàlida"] += client is not None and not p.resposta_llm.strip()
            if v:
                e["amb veritat a la referència"] += 1
                e["encert motor (per defecte)"] += p.per_defecte in v
                e["encert LLM"] += p.decisio in v
            info.append({"tipus": p.tipus, "marcada": p.marcada, "opcions": {k: "".join(t) for k, t in p.opcions.items()},
                         "per_defecte": p.per_defecte, "decisio": p.decisio, "veritat": sorted(v), "resposta_llm": p.resposta_llm})
        resultats.append({"id": reg.get("id"), "entrada": text, "referencia": ref, "motor": base, "motor_llm": final,
                          "metriques_motor": mb, "metriques_llm": mf, "punts": info})
        if n % 50 == 0:
            print(f"  {n}/{len(dades)} frases ({time.perf_counter() - t0:.0f}s)", flush=True)

    print(f"\n{args.direccio} -- {args.benchmark.name} ({len(dades)} frases) -- "
          f"{'sense LLM' if client is None else args.model}")
    print(f"  Frases exactes: motor {exactes_base} -> motor + LLM {exactes_llm}")
    for t, e in estad.items():
        print(f"  [{t}] " + ", ".join(f"{k}: {v}" for k, v in e.items()))
    if args.sortida:
        args.sortida.write_text(json.dumps({"args": {k: str(v) for k, v in vars(args).items()},
                                            "exactes_motor": exactes_base, "exactes_llm": exactes_llm,
                                            "estadistiques": {t: dict(e) for t, e in estad.items()},
                                            "resultats": resultats}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  Detall a {args.sortida}")


if __name__ == "__main__":
    main()
