"""
entrena_lora.py -- Opció 3 de les proves del biaix (02/11/2026): continua
l'entrenament de FLOR-760M amb text valencià perquè deixe de preferir les
formes catalanes per pura freqüència. No canvia el model original:
entrena un adaptador LoRA (uns pocs MB) que se li suma.

Dades: `entrenament_valencia.txt` (`prepara_dades.py`: frases de l'AVL i
del BOE en valencià, sense cap frase dels benchmarks). El 2 % es guarda
per a mesurar la perplexitat abans i després.

Ús (en Abaco amb GPU, vore `entrena_lora.sh`; en local va, però lent):
    python entrena_lora.py --dades entrenament_valencia.txt --eixida lora_valencia
Necessita torch, transformers i peft (no el paquet avlizador).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer


def blocs(tok, frases: list[str], llargada: int) -> list[list[int]]:
    """Totes les frases seguides (cada una amb el token d'inici) partides en
    blocs de `llargada` tokens."""
    ids = []
    inici = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
    for f in frases:
        ids += [inici] + tok(f, add_special_tokens=False)["input_ids"]
    return [ids[i:i + llargada] for i in range(0, len(ids) - llargada + 1, llargada)]


@torch.no_grad()
def perplexitat(model, dades: list[list[int]], dispositiu, lot: int) -> float:
    model.eval()
    perdua, n = 0.0, 0
    for i in range(0, len(dades), lot):
        x = torch.tensor(dades[i:i + lot], device=dispositiu)
        with torch.autocast(dispositiu.type, dtype=torch.float16, enabled=dispositiu.type == "cuda"):
            perdua += model(input_ids=x, labels=x).loss.item() * len(x)
        n += len(x)
    model.train()
    return math.exp(perdua / max(n, 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dades", required=True)
    ap.add_argument("--eixida", required=True)
    ap.add_argument("--model", default="projecte-aina/FLOR-760M")
    ap.add_argument("--llargada", type=int, default=128)
    ap.add_argument("--lot", type=int, default=16)
    ap.add_argument("--epoques", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rang", type=int, default=16)
    ap.add_argument("--llavor", type=int, default=21)
    args = ap.parse_args()

    random.seed(args.llavor)
    torch.manual_seed(args.llavor)
    dispositiu = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositiu: {dispositiu}", flush=True)

    frases = [l.strip() for l in Path(args.dades).read_text(encoding="utf-8").splitlines() if l.strip()]
    random.shuffle(frases)
    n_val = max(200, len(frases) // 50)
    tok = AutoTokenizer.from_pretrained(args.model)
    entrenament, validacio = blocs(tok, frases[n_val:], args.llargada), blocs(tok, frases[:n_val], args.llargada)
    print(f"{len(frases)} frases -> {len(entrenament)} blocs d'entrenament, {len(validacio)} de validació",
          flush=True)

    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float32).to(dispositiu)
    model = get_peft_model(model, LoraConfig(
        r=args.rang, lora_alpha=2 * args.rang, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["query_key_value", "dense_h_to_4h", "dense_4h_to_h"]))
    model.print_trainable_parameters()

    ppl_abans = perplexitat(model, validacio, dispositiu, args.lot)
    print(f"Perplexitat en valencià (validació) ABANS: {ppl_abans:.2f}", flush=True)

    passos = int(math.ceil(len(entrenament) / args.lot * args.epoques))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
    escalfament = max(1, passos // 20)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / escalfament) * max(0.0, 1 - s / passos))
    escalador = torch.amp.GradScaler(enabled=dispositiu.type == "cuda")
    model.train()
    inici, pas = time.time(), 0
    while pas < passos:
        random.shuffle(entrenament)
        for i in range(0, len(entrenament), args.lot):
            if pas >= passos:
                break
            x = torch.tensor(entrenament[i:i + args.lot], device=dispositiu)
            with torch.autocast(dispositiu.type, dtype=torch.float16, enabled=dispositiu.type == "cuda"):
                perdua = model(input_ids=x, labels=x).loss
            escalador.scale(perdua).backward()
            escalador.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            escalador.step(opt)
            escalador.update()
            opt.zero_grad(set_to_none=True)
            sched.step()
            pas += 1
            if pas % 50 == 0 or pas == passos:
                print(f"  pas {pas}/{passos}  pèrdua {perdua.item():.3f}  ({time.time() - inici:.0f} s)", flush=True)

    ppl_despres = perplexitat(model, validacio, dispositiu, args.lot)
    print(f"Perplexitat en valencià (validació) DESPRÉS: {ppl_despres:.2f}", flush=True)
    model.save_pretrained(args.eixida)
    Path(args.eixida, "entrenament.json").write_text(json.dumps({
        "model": args.model, "frases": len(frases), "blocs": len(entrenament), "passos": passos,
        "llargada": args.llargada, "lot": args.lot, "lr": args.lr, "rang": args.rang, "epoques": args.epoques,
        "perplexitat_abans": round(ppl_abans, 3), "perplexitat_despres": round(ppl_despres, 3),
        "segons": round(time.time() - inici),
    }, indent=1), encoding="utf-8")
    print(f"Adaptador -> {args.eixida}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
