"""
sentit_cop.py -- Clasificador de sentido para la colisión "cop/cops"
(golpe → "colp/colps"; vez → "vegada/vegades") a partir del contexto de
TODA la frase (11/11/2026, camino C1 de
`documentacio/resultats_model_llengua_kenlm.md`).

KenLM decide "cop" por la frecuencia de la palabra y su vecina de la
izquierda: no sabe de qué trata la frase. Aquí se aprende, con texto
valenciano real, qué palabras acompañan a cada sentido ("destral", "cara",
"estat" → colp; "tres", "cada", "a" → vegada).

Datos: frases valencianas (MaCoCu limpio = `valencia_net`, DOGV y AVL sin la
evaluación) con "colp(s)" o "vegada(es)". La palabra se sustituye por un
hueco y la etiqueta es el sentido. Las palabras de alrededor se pasan a
LEMA con spaCy (una→un, dues→dos, última→últim): en valenciano concuerdan
con el sentido ("una vegada" / "un colp"), pero en la entrada catalana
"cop" es siempre masculino, así que la concordancia no puede ser una pista.
Se excluye lo parecido a cualquier benchmark (como `termes_ambigus.py`).

Modelo: Naive Bayes multinomial (Python puro; recuentos en JSON), con
priors iguales. Rasgos: los lemas de las 2 palabras de cada lado (con su
posición), los bigramas de al lado y la bolsa de lemas a ±`--finestra`.
Devuelve log-odds(colp − vegada).

Evaluación:
- `dev`: 10 % de las frases del corpus, apartadas (usos reales).
- benchmarks: las colisiones de las trazas de `compara_models.py`
  (homógrafos v1/v2, manual, 151, BOE), con la etiqueta del candidato
  esperado o, si no hay, la de la referencia. Se compara con FLOR, con la
  base KenLM (margen 3, λ 0,75 en colisiones, prior de frecuencia) y con
  combinaciones KenLM + w · log-odds.
- gplsi: frases con "cop/cops" (candidatas con el motor; solo el
  clasificador y, si se pide, FLOR).

Uso (desde la raíz del repositorio):
    python pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py entrena
    python pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py avalua --traces pipeline/03_seleccio_de_model/resultats/compara_models_20261111_1232_traces_
Salidas en `dades/macocu/kenlm/sentit_cop/` (fuera de git).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[2]
KENLM_DIR = ARREL / "pipeline" / "08_traduccio_corpus" / "macocu" / "kenlm"
sys.path.insert(0, str(KENLM_DIR))
sys.path.insert(0, str(KENLM_DIR.parent))
from exporta_text import normalitza  # noqa: E402

EIXIDA = ARREL / "dades" / "macocu" / "kenlm" / "sentit_cop"
DOGV = ARREL / "dades" / "dogv_apunt" / "dogv_net.txt"
AVL = ARREL / "dades" / "macocu" / "kenlm" / "termes" / "avl_net.txt"
FREQ = ARREL / "dades" / "macocu" / "kenlm" / "termes" / "termes.json"
SENTIT = {"colp": "colp", "colps": "colp", "vegada": "vegada", "vegades": "vegada"}
CLASSES = ("colp", "vegada")
HUECO = "__X__"


# --------------------------------------------------------------------------
# Rasgos
# --------------------------------------------------------------------------

class Lematitzador:
    """Lemas de spaCy sobre tokens ya separados (uno por token, alineados)."""

    def __init__(self) -> None:
        import spacy
        from spacy.tokens import Doc

        from avlizador.traductor_cat_val.rules.pos_tagger import MODELS_SPACY

        for nom in MODELS_SPACY:
            try:
                self.nlp = spacy.load(nom, exclude=["parser", "ner"])
                break
            except OSError:
                continue
        self.Doc = Doc

    def lemes(self, llistes: list[list[str]], lot: int = 256) -> list[list[str]]:
        docs = (self.Doc(self.nlp.vocab, words=t) for t in llistes)
        return [[(t.lemma_ or t.text).lower() for t in d] for d in self.nlp.pipe(docs, batch_size=lot)]


def rasgos(lemes: list[str], i: int, finestra: int) -> list[str]:
    """Rasgos del hueco en la posición `i`.

    >>> rasgos(["a", "un", "x", "de", "destral", "."], 2, 3)
    ['L1=un', 'L2=a', 'R1=de', 'R2=destral', 'L21=a_un', 'R12=de_destral', 'W=a', 'W=un', 'W=de', 'W=destral']
    """
    def at(j):
        return lemes[j] if 0 <= j < len(lemes) else ("<s>" if j < 0 else "</s>")

    f = [f"L1={at(i - 1)}", f"L2={at(i - 2)}", f"R1={at(i + 1)}", f"R2={at(i + 2)}",
         f"L21={at(i - 2)}_{at(i - 1)}", f"R12={at(i + 1)}_{at(i + 2)}"]
    for j in range(max(0, i - finestra), min(len(lemes), i + finestra + 1)):
        if j != i and any(c.isalpha() for c in lemes[j]):
            f.append(f"W={lemes[j]}")
    return f


class NaiveBayes:
    """
    >>> nb = NaiveBayes(alpha=1.0)
    >>> nb.afig(["W=destral"], "colp"); nb.afig(["W=tres"], "vegada")
    >>> nb.logodds(["W=destral"]) > 0 > nb.logodds(["W=tres"])
    True
    """

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self.n = {c: Counter() for c in CLASSES}
        self.total = Counter()

    def afig(self, f: list[str], classe: str) -> None:
        self.n[classe].update(f)
        self.total[classe] += len(f)

    def logodds(self, f: list[str]) -> float:
        v = len(set(self.n["colp"]) | set(self.n["vegada"])) or 1
        s = 0.0
        for x in f:
            pc = (self.n["colp"][x] + self.alpha) / (self.total["colp"] + self.alpha * v)
            pv = (self.n["vegada"][x] + self.alpha) / (self.total["vegada"] + self.alpha * v)
            s += math.log(pc) - math.log(pv)
        return s

    def desa(self, path: Path, minim: int = 2) -> None:
        tots = self.n["colp"] + self.n["vegada"]
        json.dump({"alpha": self.alpha, "total": dict(self.total),
                   "n": {c: {k: v for k, v in self.n[c].items() if tots[k] >= minim} for c in CLASSES}},
                  path.open("w", encoding="utf-8"), ensure_ascii=False)

    @classmethod
    def carrega(cls, path: Path) -> NaiveBayes:
        d = json.loads(path.read_text(encoding="utf-8"))
        nb = cls(d["alpha"])
        nb.n = {c: Counter(d["n"][c]) for c in CLASSES}
        nb.total = Counter(d["total"])
        return nb

    def mes_informatius(self, k: int = 25) -> dict:
        tots = self.n["colp"] + self.n["vegada"]
        punt = {x: self.logodds([x]) for x, c in tots.items() if c >= 20}
        ordre = sorted(punt.items(), key=lambda x: x[1])
        return {"vegada": ordre[:k], "colp": ordre[::-1][:k]}


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------

def frases_font():
    """(font, tokens normalizados) de net, DOGV y AVL."""
    from termes_ambigus import frases_net

    for text in frases_net():
        yield "net", normalitza(text).split()
    for font, path in (("dogv", DOGV), ("avl", AVL)):
        with path.open(encoding="utf-8") as fh:
            for linia in fh:
                yield font, linia.split()


def recull(max_vegada: int, llavor: int) -> list[dict]:
    from termes_ambigus import Avaluacio

    aval = Avaluacio()
    colp, vegada, comptes = [], [], Counter()
    for font, toks in frases_font():
        pos = [i for i, t in enumerate(toks) if t in SENTIT]
        if not pos:
            continue
        sentits = {SENTIT[toks[i]] for i in pos}
        if len(sentits) > 1:  # les dues paraules en la mateixa frase: fora
            comptes["les_dues"] += 1
            continue
        if aval.semblant(" ".join(toks)):
            comptes["semblant_avaluacio"] += 1
            continue
        ex = {"font": font, "toks": toks, "pos": pos, "classe": sentits.pop()}
        (colp if ex["classe"] == "colp" else vegada).append(ex)
    random.Random(llavor).shuffle(vegada)
    comptes.update({"colp": len(colp), "vegada_total": len(vegada)})
    vegada = vegada[:max_vegada]
    comptes["vegada_mostra"] = len(vegada)
    print("dades:", dict(comptes), flush=True)
    return colp + vegada


def es_dev(toks: list[str]) -> bool:
    return int(hashlib.md5(" ".join(toks).encode()).hexdigest(), 16) % 10 == 0


def entrena(args) -> None:
    EIXIDA.mkdir(parents=True, exist_ok=True)
    exemples = recull(args.max_vegada, args.llavor)
    lem = Lematitzador()
    lemes = lem.lemes([[HUECO if i in e["pos"] else t for i, t in enumerate(e["toks"])] for e in exemples])
    nb = NaiveBayes(args.alpha)
    dev = []
    for e, l in zip(exemples, lemes):
        for i in e["pos"]:
            l2 = list(l)
            l2[i] = HUECO
            f = rasgos(l2, i, args.finestra)
            if es_dev(e["toks"]):
                dev.append((f, e["classe"], e["font"], " ".join(e["toks"])))
            else:
                nb.afig(f, e["classe"])
    nb.desa(EIXIDA / "nb.json")
    # Dev: frases reales apartadas
    resultat = {"args": vars(args), "dev": avalua_dev(nb, dev), "informatius": nb.mes_informatius()}
    (EIXIDA / "entrenament.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    d = resultat["dev"]
    print(f"dev: {d['n']} usos; acierto colp {d['colp']['acerts']}/{d['colp']['n']}, "
          f"vegada {d['vegada']['acerts']}/{d['vegada']['n']} (balanceado {d['balancejat']:.3f})")
    print("colp  ←", ", ".join(f"{k}" for k, _ in resultat["informatius"]["colp"][:15]))
    print("vegada←", ", ".join(f"{k}" for k, _ in resultat["informatius"]["vegada"][:15]))


def avalua_dev(nb: NaiveBayes, dev: list) -> dict:
    r = {c: {"n": 0, "acerts": 0} for c in CLASSES}
    errors = []
    for f, classe, font, text in dev:
        lo = nb.logodds(f)
        pred = "colp" if lo > 0 else "vegada"
        r[classe]["n"] += 1
        r[classe]["acerts"] += pred == classe
        if pred != classe and len(errors) < 40:
            errors.append({"classe": classe, "logodds": round(lo, 2), "font": font, "text": text})
    bal = sum(r[c]["acerts"] / max(1, r[c]["n"]) for c in CLASSES) / 2
    return {"n": len(dev), **r, "balancejat": bal, "errors": errors}


# --------------------------------------------------------------------------
# Evaluación en los benchmarks
# --------------------------------------------------------------------------

def prior_freq() -> callable:
    t = json.loads(FREQ.read_text(encoding="utf-8"))["fonts"]
    tot = t["net"]["tokens"] + t["dogv"]["tokens"]

    def prior(c: str) -> float:
        c = c.lower()
        return math.log((t["net"]["n"].get(c, 0) + t["dogv"]["n"].get(c, 0) + 1) / tot)
    return prior


def etiqueta(punt: dict, referencia: str | None) -> str | None:
    """Sentido esperado: el candidato esperado o el que sale en la referencia."""
    if punt.get("esperat"):
        return SENTIT.get(punt["esperat"].lower())
    if referencia:
        toks = set(normalitza(referencia).split())
        trobats = {SENTIT[c.lower()] for c in punt["candidats"] if c.lower() in toks}
        if len(trobats) == 1:
            return trobats.pop()
    return None


def entrada(punt: dict, lem: Lematitzador, finestra: int) -> list[str] | None:
    """Rasgos a partir de una frase candidata (valenciana) con el hueco."""
    for c, d in punt["puntuacions"].items():
        toks = normalitza(d["frase"]).split()
        if c.lower() in toks:
            i = toks.index(c.lower())
            toks[i] = HUECO
            l = lem.lemes([toks])[0]
            l[i] = HUECO
            return rasgos(l, i, finestra)
    return None


def avalua(args) -> None:
    nb = NaiveBayes.carrega(EIXIDA / "nb.json")
    lem = Lematitzador()
    prior = prior_freq()
    carrega = lambda m: {(f["benchmark"], f["id"]): f for f in json.loads(
        Path(f"{args.traces}{m}.json").read_text(encoding="utf-8"))["frases"]}
    flor, ken = carrega("flor"), carrega(args.kenlm)
    casos = []
    for k, f in ken.items():
        for n, p in enumerate(f["punts"]):
            if p["tipus"] != "colisio" or not p["puntuacions"]:
                continue
            gold = etiqueta(p, f.get("referencia"))
            if gold is None:
                continue
            feats = entrada(p, lem, args.finestra)
            lo = nb.logodds(feats) if feats else 0.0
            # KenLM base: lp − λ · prior(freq); diferència colp − vegada
            v = {SENTIT[c.lower()]: d["lp"] - args.lam_col * prior(c) for c, d in p["puntuacions"].items()}
            casos.append({"bench": k[0], "id": k[1], "gold": gold, "flor": SENTIT.get((flor[k]["punts"][n]["tria"] or "").lower()),
                          "dk": v["colp"] - v["vegada"], "lo": lo, "text": f["oriental"]})
    print(f"{len(casos)} colisiones con etiqueta: " + ", ".join(f"{b} {n}" for b, n in Counter(c['bench'] for c in casos).items()))

    def puntua(nom, pred):
        per = Counter()
        for c in casos:
            ok = pred(c) == c["gold"]
            per[(c["bench"].startswith("homografs"), ok)] += 1
        hom = per[(True, True)], per[(True, True)] + per[(True, False)]
        real = per[(False, True)], per[(False, True)] + per[(False, False)]
        errors = [c["id"] for c in casos if pred(c) != c["gold"]]
        print(f"  {nom:38s} homògrafs {hom[0]}/{hom[1]}   text real {real[0]}/{real[1]}   errors: {', '.join(errors)}")

    sentit = lambda x: "colp" if x > 0 else "vegada"
    puntua("FLOR (sistema)", lambda c: c["flor"])
    puntua(f"KenLM base (λ col {args.lam_col})", lambda c: sentit(c["dk"]))
    puntua("Clasificador solo", lambda c: sentit(c["lo"]))
    for w in (0.25, 0.5, 1.0, 2.0):
        puntua(f"KenLM + {w} · clasificador", lambda c, w=w: sentit(c["dk"] + w * c["lo"]))
    for t in (1.0, 2.0, 3.0):
        puntua(f"KenLM; si |Δ| < {t}, clasificador", lambda c, t=t: sentit(c["lo"] if abs(c["dk"]) < t else c["dk"]))
    (EIXIDA / "avaluacio.json").write_text(json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  detalle (gold, flor, Δ KenLM, log-odds):")
    for c in casos:
        print(f"    {c['bench']:13s} {c['id']:11s} {c['gold']:6s} flor={c['flor'] or '-':6s} Δk={c['dk']:6.2f} lo={c['lo']:6.2f}  {c['text'][:70]}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="ordre", required=True)
    e = sub.add_parser("entrena")
    e.add_argument("--max-vegada", type=int, default=40000, help="muestra de frases con vegada(es)")
    e.add_argument("--finestra", type=int, default=8)
    e.add_argument("--alpha", type=float, default=0.5)
    e.add_argument("--llavor", type=int, default=11)
    a = sub.add_parser("avalua")
    a.add_argument("--traces", required=True, help="prefijo de los JSON de trazas (…_traces_)")
    a.add_argument("--kenlm", default="kenlm_val_net_dogv")
    a.add_argument("--lam-col", type=float, default=0.75)
    a.add_argument("--finestra", type=int, default=8)
    args = p.parse_args(argv)
    entrena(args) if args.ordre == "entrena" else avalua(args)


if __name__ == "__main__":
    main()
