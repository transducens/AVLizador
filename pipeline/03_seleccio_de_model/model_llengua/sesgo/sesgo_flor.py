"""
sesgo_flor.py -- Proves per a reduir el biaix de FLOR cap a la forma més
freqüent (02/11/2026). Tres opcions (vore README.md):

1. **Paràgraf valencià davant**: cada frase candidata es puntua com a
   continuació d'un paràgraf en valencià normatiu (`--paragraf P1..P5`,
   de `paragrafs.json`).
2. **Freqüència valenciana**: a la puntuació s'afig
   `mu × (log f_val(paraula) − log f_cat(paraula))`, amb les freqüències de
   `freq.json` (AVL + BOE valencià davant BOE català).
3. **FLOR adaptat al valencià**: el mateix FLOR amb un adaptador LoRA
   entrenat amb `entrena_lora.py` (`--adaptador carpeta`).

Dos passos, perquè FLOR només es crida una vegada per model i paràgraf:

    # 1) puntuacions de cada paraula ambigua (crida FLOR)
    python .../sesgo/sesgo_flor.py puntua --eixida resultats/base.json
    python .../sesgo/sesgo_flor.py puntua --paragraf P1 --eixida resultats/P1.json
    python .../sesgo/sesgo_flor.py puntua --adaptador lora_valencia --eixida resultats/lora.json
    # 2) totes les combinacions de paràmetres, sense FLOR
    python .../sesgo/sesgo_flor.py compara resultats/*.json

Benchmarks: `homografs` (v1: 151 + homògrafs) per a TRIAR els paràmetres,
i `homografs_v2` i `manual` per a COMPROVAR-los (no s'usen per a triar).
Una paraula ambigua compta si la referència usa un sol dels candidats.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

from avlizador.avaluacio.avalua import BENCHMARKS, troba_dir_benchmarks
from avlizador.traductor_cat_val.model_llengua import CONCORDANCA_PER_DEFECTE, Criteri, puntua_punts
from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts, decisio_spacy, detecta
from avlizador.traductor_cat_val.rules import separa_prefix_elidit
from avlizador.traductor_cat_val.rules.cat_val.engine import RuleEngineInvers

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

AQUI = Path(__file__).resolve().parent
BENCH_TRIA = "homografs"
BENCH_PROVA = ("homografs_v2", "manual")


class ModelAmbParagraf:
    """Un `ModelLlengua` que puntua cada text com a continuació de `paragraf`:
    log P(text | paràgraf) = log P(paràgraf + text) − log P(paràgraf).

    El paràgraf passa per FLOR una sola vegada: se'n guarden els
    `past_key_values` i, per a cada text, només es calculen els tokens del
    text. Si el tokenitzador no talla el paràgraf igual dins de
    "paràgraf + text", es calcula tot sencer (el resultat és el mateix)."""

    def __init__(self, base, paragraf: str | None):
        self.base, self.paragraf = base, paragraf
        self.model_id = base.model_id
        self._cache: dict[str, tuple[float, int]] = {}
        self.sense_kv = 0  # textos calculats sencers (tall diferent)
        if paragraf:
            torch = base._torch
            self._ids_p = [base.bos] + base.tok(paragraf, add_special_tokens=False)["input_ids"]
            with torch.no_grad():
                eix = base.lm(torch.tensor([self._ids_p]), use_cache=True)
            self._kv = eix.past_key_values
            self._ultim = eix.logits[0, -1].float()

    def logprob(self, text: str) -> tuple[float, int]:
        if not self.paragraf:
            return self.base.logprob(text)
        if text in self._cache:
            return self._cache[text]
        base, torch = self.base, self.base._torch
        ids = [base.bos] + base.tok(self.paragraf + " " + text, add_special_tokens=False)["input_ids"]
        n_p = len(self._ids_p)
        if ids[:n_p] != self._ids_p:
            self.sense_kv += 1
            lp_p, np_ = base.logprob(self.paragraf)
            lp, n = base.logprob(self.paragraf + " " + text)
            self._cache[text] = (lp - lp_p, n - np_)
            return self._cache[text]
        nous = ids[n_p:]
        with torch.no_grad():
            eix = base.lm(torch.tensor([nous]), past_key_values=self._kv, use_cache=True,
                          attention_mask=torch.ones(1, len(ids), dtype=torch.long))
        # la caché creix amb els tokens nous: es retalla al paràgraf
        self._kv.crop(-len(nous))
        logits = torch.cat([self._ultim[None], eix.logits[0, :-1].float()])
        lp = torch.log_softmax(logits, -1)[torch.arange(len(nous)), torch.tensor(nous)].sum().item()
        self._cache[text] = (lp, len(nous))
        return self._cache[text]


def carrega_model(model_id: str | None, adaptador: str | None):
    from avlizador.traductor_cat_val.model_llengua.puntuador import MODEL_PER_DEFECTE, ModelLlengua

    m = ModelLlengua(model_id or MODEL_PER_DEFECTE)
    if adaptador:
        from peft import PeftModel

        m.lm = PeftModel.from_pretrained(m.lm, adaptador).merge_and_unload()
        m.lm.eval()
        m.model_id += f" + {adaptador}"
    return m


def apostrofs(text: str) -> str:
    for v in ("´", "‘", "’", "ʼ", "`"):
        text = text.replace(v, "'")
    return text


def paraules_de(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[\w·'-]+", text.lower()):
        pr = separa_prefix_elidit(w)
        out.add(pr[1] if pr else w)
    return out


# ─── 1) puntua ───────────────────────────────────────────────────────────────

def ordre_puntua(args) -> int:
    paragraf = None
    if args.paragraf:
        paragrafs = {p["id"]: p["text"] for p in json.loads((AQUI / "paragrafs.json").read_text(encoding="utf-8"))}
        paragraf = paragrafs[args.paragraf]
    model = ModelAmbParagraf(carrega_model(args.model, args.adaptador), paragraf)
    motor, punts_lexic = RuleEngineInvers(), carrega_punts()
    criteri = Criteri()
    dir_b = troba_dir_benchmarks()
    files, inici = [], time.time()
    for bench in (BENCH_TRIA, *BENCH_PROVA):
        items = json.loads((dir_b / BENCHMARKS[bench][1]).read_text(encoding="utf-8"))
        for x in items[: args.limit] if args.limit else items:
            text, ref = apostrofs(x["oriental"]), apostrofs(x["occidental"])
            if not detecta(motor.tradueix_tokens(text), punts_lexic, criteri.tipus):
                continue
            _, trobats = puntua_punts(text, model, criteri.tipus, CONCORDANCA_PER_DEFECTE, criteri.tipus)
            ref_w = paraules_de(ref)
            for p in trobats:
                en_ref = [c for c in p.candidats if c.lower() in ref_w]
                files.append({
                    "bench": bench, "id": x["id"], "paraula": p.paraula, "tipus": p.tipus,
                    "candidats": p.candidats, "motor": p.motor, "pos": p.pos,
                    "spacy": decisio_spacy(p) if p.tipus == "irresoluble" else None,
                    "esperat": en_ref[0] if len(en_ref) == 1 else None,
                    "punts": {c: {"lp": d["lp"], "prior": d["prior"], "n": d["n"]} for c, d in p.puntuacions.items()},
                })
        print(f"  {bench}: {sum(f['bench'] == bench for f in files)} paraules ambigües "
              f"({time.time() - inici:.0f} s)", file=sys.stderr)
    Path(args.eixida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.eixida).write_text(json.dumps({
        "model": model.model_id, "paragraf": args.paragraf, "text_paragraf": paragraf,
        "segons": round(time.time() - inici), "punts": files,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(files)} paraules -> {args.eixida}", file=sys.stderr)
    return 0


# ─── 2) compara ──────────────────────────────────────────────────────────────

def contrast(freq: dict, paraula: str) -> float:
    """log f_val − log f_cat (relatives, suavitzat +1)."""
    v, c = freq["valencia"], freq["catala"]
    fv = (v["paraules"].get(paraula.lower(), 0) + 1) / v["total"]
    fc = (c["paraules"].get(paraula.lower(), 0) + 1) / c["total"]
    return math.log(fv) - math.log(fc)


def tria(p: dict, lam: float, mu: float, marge: float, freq: dict | None) -> str | None:
    """La mateixa decisió que `model_llengua.tria`, amb el terme de freqüència."""
    if p["spacy"] is not None:
        return p["spacy"]
    if not p["punts"]:
        return p["motor"]
    sc = {c: d["lp"] - lam * d["prior"] + (mu * contrast(freq, c) if mu and freq else 0.0)
          for c, d in p["punts"].items()}
    millor = max(sc, key=sc.get)
    if p["motor"] in sc and millor != p["motor"] and sc[millor] - sc[p["motor"]] <= marge:
        return p["motor"]
    return millor


def encerts(punts: list[dict], bench: str, lam, mu, marge, freq) -> tuple[int, int]:
    sel = [p for p in punts if p["bench"] == bench and p["esperat"] is not None]
    return sum(tria(p, lam, mu, marge, freq) == p["esperat"] for p in sel), len(sel)


def ordre_compara(args) -> int:
    freq = json.loads((AQUI / "freq.json").read_text(encoding="utf-8"))
    lams, mus, marges = (0, 0.25, 0.5, 0.75, 1.0), (0, 0.5, 1, 2), (0, 1, 2, 3, 4, 5, 6, 8, 10)
    print("Paràmetres triats NOMÉS amb la v1; la v2 i el manual no s'usen per a triar.\n")
    print(f"{'configuració':<34} {'λ':>4} {'μ':>4} {'marge':>5} | {'v1 (tria)':>10} {'v2':>9} {'manual':>8}")
    for fitxer in args.fitxers:
        d = json.loads(Path(fitxer).read_text(encoding="utf-8"))
        nom = Path(fitxer).stem
        punts = d["punts"]

        def fila(etiqueta, lam, mu, marge):
            r = [encerts(punts, b, lam, mu, marge, freq) for b in (BENCH_TRIA, *BENCH_PROVA)]
            print(f"{etiqueta:<34} {lam:>4} {mu:>4} {marge:>5} | " + " ".join(
                f"{a:>4}/{n:<4}" for a, n in r))
        fila(f"{nom}: criteri actual", 0.5, 0, 5)
        for amb_freq in (False, True):
            millor = max(((lam, mu, m) for lam in lams for mu in (mus if amb_freq else (0,)) for m in marges),
                         key=lambda t: (encerts(punts, BENCH_TRIA, *t, freq)[0], -abs(t[2] - 5)))
            fila(f"{nom}: millor en v1{' + freq' if amb_freq else ''}", *millor)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="ordre", required=True)
    p = sub.add_parser("puntua")
    p.add_argument("--model", help="Model de Hugging Face (per defecte, FLOR-760M).")
    p.add_argument("--adaptador", help="Carpeta d'un adaptador LoRA (opció 3).")
    p.add_argument("--paragraf", help="P1..P5 de paragrafs.json (opció 1).")
    p.add_argument("--limit", type=int)
    p.add_argument("--eixida", required=True)
    c = sub.add_parser("compara")
    c.add_argument("fitxers", nargs="+")
    args = ap.parse_args(argv)
    return ordre_puntua(args) if args.ordre == "puntua" else ordre_compara(args)


if __name__ == "__main__":
    sys.exit(main())
