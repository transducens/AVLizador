"""
capa_llm/prova_cat_val.py (abans traductor/llm/; des de
pipeline/08_traduccio_corpus/postprocessat_llm/) -- Prova en local de la capa de LLM de cat->val
(`cat_val.py`). Necessita Ollama en marxa amb el model baixat, llevat de
`--sense-llm` (només mostra què faria el motor i quins punts detecta).

    python -m capa_llm.prova_cat_val "Es va posar les calces del pantaló."
    python -m capa_llm.prova_cat_val --sense-llm "Dorm en una gandula."
    python -m capa_llm.prova_cat_val --model qwen3:4b --verbose "..."
    python -m capa_llm.prova_cat_val --prompt v3 --verbose "..."

Avaluació amb les frases de `frases_prova_cat_val.json` (encerts per model
i prompt):

    python -m capa_llm.prova_cat_val --avalua --model qwen3:8b --prompt v3
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .cat_val import tradueix_cat_val
from .client import ClientLLM

FRASES_PROVA = Path(__file__).resolve().parent / "frases_prova_cat_val.json"


def _mostra(frase: str, client, prompt: str) -> None:
    motor, _ = tradueix_cat_val(frase)
    text, punts = tradueix_cat_val(frase, client, prompt)
    print(f"\nCatalà:      {frase}")
    print(f"Motor:       {motor}")
    print(f"Amb el LLM:  {text}")
    if not punts:
        print("  (cap homògraf: no s'ha cridat el model)")
    for p in punts:
        print(f"  - «{p.marcada}»: decisió '{p.decisio}' (resposta del model: {p.resposta_llm!r})")


def _avalua(client, prompt: str) -> None:
    frases = json.loads(FRASES_PROVA.read_text(encoding="utf-8"))["frases"]
    encerts = total = 0
    t0 = time.perf_counter()
    for f in frases:
        _, punts = tradueix_cat_val(f["text"], client, prompt)
        if f["esperat"] is None:
            estat = "OK " if not punts else "MAL"
            print(f"{estat} (sense homògraf: {'cap crida' if not punts else 'ha cridat el model!'})  {f['text']}")
            continue
        decisio = punts[0].decisio if punts else None
        ok = decisio == f["esperat"]
        encerts += ok
        total += 1
        resposta = punts[0].resposta_llm.strip().replace("\n", " ")[:40] if punts else ""
        print(f"{'OK ' if ok else 'MAL'} esperat={f['esperat']:2} decisió={decisio!s:4} resposta={resposta!r:44} {f['text']}")
    model = getattr(client, "model", "sense LLM")
    print(f"\n{model}, prompt {prompt}: {encerts}/{total} encerts ({time.perf_counter() - t0:.0f} s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Traducció cat->val amb la capa de LLM per a homògrafs (Ollama)."
    )
    parser.add_argument("frases", nargs="*", help="Frase o frases en català.")
    parser.add_argument("--model", default="qwen3:8b", help="Model d'Ollama (per defecte qwen3:8b).")
    parser.add_argument("--url", default="http://localhost:11434", help="URL d'Ollama.")
    parser.add_argument("--sense-llm", action="store_true", help="Només el motor: mostra els punts sense cridar el model.")
    parser.add_argument("--verbose", action="store_true", help="Mostra el prompt i la resposta del model.")
    parser.add_argument(
        "--prompt", choices=["v1", "v2", "v3"], default="v1",
        help="v1: català, sí/no; v2: castellà, sí/no; v3: el model traduïx la paraula al castellà.",
    )
    parser.add_argument("--avalua", action="store_true", help=f"Avalua amb {FRASES_PROVA.name}.")
    args = parser.parse_args()

    client = None if args.sense_llm else ClientLLM(model=args.model, url=args.url, verbose=args.verbose)
    if args.avalua:
        _avalua(client, args.prompt)
        return
    if not args.frases:
        parser.error("cal almenys una frase (o --avalua)")
    for frase in args.frases:
        _mostra(frase, client, args.prompt)


if __name__ == "__main__":
    main()
