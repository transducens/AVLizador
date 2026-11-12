"""
termes_ambigus.py -- Freqüència i contextos de les paraules ambigües del
sistema cat->val (les dels punts de `model_llengua`: cop/colp/vegada,
manca/falta, gandula/hamaca...) en cada font de text valencià (11/11/2026).

Per a saber si els errors de KenLM venen de la poca freqüència d'una forma
("colp" 2.380 vegades en el valencià net, "vegada" 84.521) i quines fonts
noves la podrien pujar sense tocar l'avaluació. Fonts:

- `net`: el text del KenLM `valencia_net` (MaCoCu valencià: frases amb ≥ 2
  marcadors o del seu document; com `exporta_text.py --marcadors-doc 2`).
- `dogv`: `dades/dogv_apunt/dogv_net.txt` (ja normalitzat).
- `avl`: `dades/avl/final/unified.jsonl` partit en frases, SENSE res de
  l'avaluació: fora els documents del 151 i del manual AVL, i qualsevol
  frase semblant (Jaccard ≥ 0,6) a una del manual, del 151 o dels homògrafs.
- `ua`: notícies de la Universitat d'Alacant (`ua_noticias_va.jsonl`), amb
  el GD de cada frase (estàndard de la UA: aquest/avui/servei).

Eixida (`dades/macocu/kenlm/termes/`): `termes.json` (comptes, contextos
esquerre/dret i exemples per font) i `termes.md` (taules), i
`avl_net.txt`/`ua_net.txt`: les frases normalitzades de cada font,
preparades per a entrenar (la UA, només les frases de GD ≥ `--gd-ua`).

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/kenlm/termes_ambigus.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
from comu import _SEPARA  # noqa: E402
from exporta_text import normalitza  # noqa: E402

ARREL = AQUI.parents[3]
EIXIDA = ARREL / "dades" / "macocu" / "kenlm" / "termes"
VALENCIA = ARREL / "dades" / "macocu" / "valencia" / "valencia.jsonl"
DOGV = ARREL / "dades" / "dogv_apunt" / "dogv_net.txt"
AVL = ARREL / "dades" / "avl" / "final" / "unified.jsonl"
UA = ARREL / "dades" / "dogv_apunt" / "ua_noticias_va.jsonl"
B151 = ARREL / "pipeline" / "03_seleccio_de_model" / "benchmark_corpus.json"
BENCH = ARREL / "dades" / "benchmarks"
POOL_AVL = ARREL / "dades" / "benchmark_manual" / "pool_avl.jsonl"
MIN_TOKENS = 3
_PARAULA = re.compile(r"[^\W\d_]+", re.UNICODE)


def termes() -> dict[str, list[str]]:
    """{forma catalana: candidats} de tots els punts (+ la forma mateixa)."""
    from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

    return {p: sorted({c.lower() for c in d["candidats"]} | {p.lower()}) for p, d in carrega_punts().items()}


def _conjunt(text: str) -> frozenset:
    return frozenset(w.lower() for w in _PARAULA.findall(text))


class Avaluacio:
    """Tot el que no pot entrar en l'entrenament: frases i documents."""

    def __init__(self) -> None:
        frases = []
        b151 = json.loads(B151.read_text(encoding="utf-8"))
        self.docs = {b["corpus_id"] for b in b151 if b.get("corpus_id")}
        frases += [b[c] for b in b151 for c in ("occidental", "oriental") if b.get(c)]
        for f in BENCH.rglob("*.json"):
            if "boe_dialectal" in f.parts:  # el BOE no és de l'AVL (i són 150.000 frases)
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            files = d["frases"] if isinstance(d, dict) and "frases" in d else d
            if isinstance(files, list):
                frases += [x[c] for x in files if isinstance(x, dict) for c in ("occidental", "oriental") if x.get(c)]
        self.conjunts = [c for c in map(_conjunt, frases) if len(c) >= 4]
        # índex per paraula rara per a no comparar amb totes
        self.index: dict[str, list[int]] = defaultdict(list)
        freq = Counter(w for c in self.conjunts for w in c)
        for i, c in enumerate(self.conjunts):
            for w in sorted(c, key=lambda w: freq[w])[:3]:
                self.index[w].append(i)
        # Documents del manual AVL: els del pool amb una frase semblant a una del manual.
        manual = [_conjunt(x[c]) for x in json.loads(
            (BENCH / "manual" / "benchmark_manual_avl_cat_val.json").read_text(encoding="utf-8"))
            for c in ("occidental", "oriental")]
        for linia in POOL_AVL.read_text(encoding="utf-8").splitlines():
            r = json.loads(linia)
            c = _conjunt(r.get("occidental") or "")
            if any(len(c & m) / max(1, len(c | m)) >= 0.6 for m in manual):
                self.docs.add(r["document"])

    def semblant(self, text: str, llindar: float = 0.6) -> bool:
        c = _conjunt(text)
        if len(c) < 4:
            return False
        for i in {i for w in c for i in self.index.get(w, ())}:
            a = self.conjunts[i]
            if len(c & a) / len(c | a) >= llindar:
                return True
        return False


def frases_avl(aval: Avaluacio, comptes: Counter):
    for linia in AVL.read_text(encoding="utf-8").splitlines():
        r = json.loads(linia)
        if r.get("corpus_id") in aval.docs:
            comptes["avl_document_avaluacio"] += 1
            continue
        for par in r["text"].split("\n"):
            for frase in _SEPARA.split(par.strip()):
                if not frase:
                    continue
                if aval.semblant(frase):
                    comptes["avl_frase_semblant"] += 1
                    continue
                yield frase, r.get("doc_type")


def frases_ua(comptes: Counter):
    vistes = set()
    for linia in UA.read_text(encoding="utf-8").splitlines():
        if "{" not in linia:
            continue
        if not linia.startswith("{"):  # una línia del fitxer porta una "r" solta davant (no es toca l'original)
            comptes["ua_linia_reparada"] += 1
            linia = linia[linia.index("{"):]
        r = json.loads(linia)
        for par in (r.get("VA") or "").split("\n"):
            for frase in _SEPARA.split(par.strip()):
                if frase and frase not in vistes:
                    vistes.add(frase)
                    yield frase
                elif frase:
                    comptes["ua_repetida"] += 1


def frases_net():
    docs = set()
    with VALENCIA.open(encoding="utf-8") as fh:
        for linia in fh:
            if not linia.strip():
                continue
            r = json.loads(linia)
            if r.get("occ", 0) >= 2:
                docs.add(r["doc"])
    with VALENCIA.open(encoding="utf-8") as fh:
        for linia in fh:
            if not linia.strip():
                continue
            r = json.loads(linia)
            if r.get("occ", 0) >= 2 or r["doc"] in docs:
                yield r["text"]


class Comptador:
    def __init__(self, formes: set[str]) -> None:
        self.formes = formes
        self.n = Counter()
        self.esq = defaultdict(Counter)   # forma -> 2 paraules d'abans
        self.dre = defaultdict(Counter)   # forma -> 2 paraules de després
        self.exemples = defaultdict(list)
        self.tokens = 0
        self.frases = 0

    def afig(self, toks: list[str], original: str | None = None) -> None:
        self.tokens += len(toks) + 1
        self.frases += 1
        for i, t in enumerate(toks):
            if t in self.formes:
                self.n[t] += 1
                self.esq[t][" ".join(toks[max(0, i - 2):i])] += 1
                self.dre[t][" ".join(toks[i + 1:i + 3])] += 1
                if len(self.exemples[t]) < 8:
                    self.exemples[t].append(original or " ".join(toks))

    def resum(self) -> dict:
        return {"tokens": self.tokens, "frases": self.frases, "n": dict(self.n),
                "esquerra": {f: c.most_common(12) for f, c in self.esq.items()},
                "dreta": {f: c.most_common(12) for f, c in self.dre.items()},
                "exemples": dict(self.exemples)}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--gd-ua", type=float, default=0.8,
                   help="GD mínim d'una frase de la UA per a ua_net.txt (amb ≥ 1 marcador)")
    p.add_argument("--sense-net", action="store_true", help="no llegir el MaCoCu (lent: ~3 min)")
    args = p.parse_args(argv)
    from avlizador.grau_dialectal import calcula_gd

    grups = termes()
    formes = {f for fs in grups.values() for f in fs}
    EIXIDA.mkdir(parents=True, exist_ok=True)
    comptes: Counter = Counter()
    fonts: dict[str, Comptador] = {}

    aval = Avaluacio()
    print(f"avaluació: {len(aval.conjunts)} frases, {len(aval.docs)} documents de l'AVL exclosos", flush=True)
    c = fonts["avl"] = Comptador(formes)
    with (EIXIDA / "avl_net.txt").open("w", encoding="utf-8") as fh:
        for frase, _tipus in frases_avl(aval, comptes):
            n = normalitza(frase)
            if n.count(" ") + 1 < MIN_TOKENS:
                continue
            c.afig(n.split(), frase)
            fh.write(n + "\n")
    print(f"avl: {c.frases} frases, {c.tokens} tokens", flush=True)

    c = fonts["ua"] = Comptador(formes)
    c_tot = fonts["ua_tota"] = Comptador(formes)
    gd_termes = defaultdict(list)
    cau_path = EIXIDA / "ua_gd_cau.json"  # el GD de cada frase de la UA (spaCy: ~10 min)
    cau = json.loads(cau_path.read_text(encoding="utf-8")) if cau_path.exists() else {}
    with (EIXIDA / "ua_net.txt").open("w", encoding="utf-8") as fh:
        for frase in frases_ua(comptes):
            n = normalitza(frase)
            if n.count(" ") + 1 < MIN_TOKENS:
                continue
            toks = n.split()
            c_tot.afig(toks, frase)
            if frase not in cau:
                g = calcula_gd(frase)
                cau[frase] = {"gd": g["gd"], "total_occidentals": g["total_occidentals"]}
            gd = cau[frase]
            for t in set(toks) & formes:
                gd_termes[t].append(gd["gd"])
            if gd["gd"] is not None and gd["gd"] >= args.gd_ua and gd["total_occidentals"] >= 1:
                c.afig(toks, frase)
                fh.write(n + "\n")
            else:
                comptes["ua_gd_baix_o_sense_marcadors"] += 1
    cau_path.write_text(json.dumps(cau, ensure_ascii=False), encoding="utf-8")
    print(f"ua: {c_tot.frases} frases ({c.frases} amb GD ≥ {args.gd_ua})", flush=True)

    c = fonts["dogv"] = Comptador(formes)
    for linia in DOGV.read_text(encoding="utf-8").splitlines():
        c.afig(linia.split())
    if not args.sense_net:
        c = fonts["net"] = Comptador(formes)
        for text in frases_net():
            c.afig(normalitza(text).split(), text)
        print(f"net: {c.frases} frases, {c.tokens} tokens", flush=True)

    resultat = {"grups": grups, "comptes": dict(comptes), "gd_ua": args.gd_ua,
                "gd_ua_per_terme": {t: {"n": len(v), "mitjana": round(sum(x for x in v if x is not None) /
                                                                        max(1, sum(x is not None for x in v)), 3)}
                                    for t, v in gd_termes.items()},
                "fonts": {k: v.resum() for k, v in fonts.items()}}
    (EIXIDA / "termes.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    (EIXIDA / "termes.md").write_text(informe(resultat), encoding="utf-8")
    print(f"-> {EIXIDA / 'termes.md'}")


def informe(r: dict) -> str:
    fonts = [f for f in ("net", "dogv", "avl", "ua", "ua_tota") if f in r["fonts"]]
    md = ["# Paraules ambigües en les fonts de text valencià", "",
          "Comptes de cada forma (text normalitzat, minúscules). `ua` = frases de la UA amb GD ≥ "
          f"{r['gd_ua']}; `ua_tota` = totes. La AVL, sense res de l'avaluació.", "",
          "| Font | Frases | Tokens |", "|---|---|---|"]
    for f in fonts:
        md.append(f"| {f} | {r['fonts'][f]['frases']:,} | {r['fonts'][f]['tokens']:,} |".replace(",", "."))
    md += ["", "| Punt | Forma | " + " | ".join(fonts) + " | GD mitjà UA |", "|---|---|" + "---|" * (len(fonts) + 1)]
    for punt, formes in r["grups"].items():
        for forma in formes:
            fila = [str(r["fonts"][f]["n"].get(forma, 0)) for f in fonts]
            gd = r["gd_ua_per_terme"].get(forma, {}).get("mitjana", "—")
            md.append(f"| {punt} | {forma} | " + " | ".join(fila) + f" | {gd} |")
    md += ["", "## Contextos (2 paraules a esquerra i dreta) en avl + ua", ""]
    for punt, formes in r["grups"].items():
        for forma in formes:
            for f in ("avl", "ua"):
                d = r["fonts"][f]
                if d["n"].get(forma):
                    esq = ", ".join(f"«{k}» {v}" for k, v in d["esquerra"][forma][:6])
                    dre = ", ".join(f"«{k}» {v}" for k, v in d["dreta"][forma][:6])
                    md.append(f"- **{forma}** ({f}, {d['n'][forma]}): ← {esq} · → {dre}")
    md += ["", "Exclusions: " + ", ".join(f"{k} {v}" for k, v in r["comptes"].items())]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
