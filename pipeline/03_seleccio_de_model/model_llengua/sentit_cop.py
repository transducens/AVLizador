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
"cop" es siempre masculino, así que la concordancia no puede ser una pista;
como spaCy no lematiza "una"/"dues", las palabras con género (rasgo
`Gender`) se sustituyen por su categoría (`<DET>`, `<NUM>`, `<ADJ>`...).
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

El núcleo (rasgos, Naive Bayes, lematizador, `ClassificadorCop`) está en el
paquete desde el 12/11/2026 (`avlizador.traductor_cat_val.model_llengua.sentit`);
aquí quedan el entrenamiento y la evaluación.

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


# --------------------------------------------------------------------------
# Rasgos y modelo: en el paquete (12/11/2026), una sola fuente para entrenar
# aquí y para traducir con `translate_cat_val(text, model="kenlm")`.
# --------------------------------------------------------------------------

from avlizador.traductor_cat_val.model_llengua import sentit as _sentit  # noqa: E402
from avlizador.traductor_cat_val.model_llengua.sentit import (  # noqa: E402,F401
    CLASSES,
    CONCORDEN,
    NaiveBayes,
    trets as rasgos,
)

HUECO = _sentit.BUIT
SENTIT = _sentit.SENTIT_COP


class Lematitzador(_sentit.Lematitzador):
    """El del paquete; `genere=True` deja las palabras con género."""

    def __init__(self, genere: bool = False) -> None:
        super().__init__(genere=genere)


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
    lem = Lematitzador(args.genere)
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
    nb.desa(EIXIDA / f"{args.nom}.json")
    # Dev: frases reales apartadas
    resultat = {"args": vars(args), "dev": avalua_dev(nb, dev), "informatius": nb.mes_informatius()}
    (EIXIDA / f"{args.nom}_entrenament.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
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
    return _sentit.trets_de_frases({c: d["frase"] for c, d in punt["puntuacions"].items()}, lem, finestra)


def avalua(args) -> None:
    nb = NaiveBayes.carrega(EIXIDA / f"{args.nom}.json")
    lem = Lematitzador(args.genere)
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
    (EIXIDA / f"{args.nom}_avaluacio.json").write_text(json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8")
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
    for x in (e, a := sub.add_parser("avalua")):
        x.add_argument("--nom", default="nb", help="nombre del modelo (dades/macocu/kenlm/sentit_cop/<nom>.json)")
        x.add_argument("--genere", action="store_true", help="no ocultar las palabras con género")
    a.add_argument("--traces", required=True, help="prefijo de los JSON de trazas (…_traces_)")
    a.add_argument("--kenlm", default="kenlm_val_net_dogv")
    a.add_argument("--lam-col", type=float, default=0.75)
    a.add_argument("--finestra", type=int, default=8)
    args = p.parse_args(argv)
    entrena(args) if args.ordre == "entrena" else avalua(args)


if __name__ == "__main__":
    main()
