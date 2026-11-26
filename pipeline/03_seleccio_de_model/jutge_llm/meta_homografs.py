"""Meta-avaluació del jutge en els homògrafs: ¿marca la paraula quan és un error
de sentit i la deixa en pau quan és correcta (sobretot, la forma valenciana)?

Veritat: el benchmark diu, per a cada frase, la paraula catalana (`paraula`) i la
correcta (`esperat`). Per a cada eixida (referència, AVLizador, motor) es busca
quina paraula hi ha en eixe lloc (alineant amb l'original català) i es classifica:
  correcta_val  esperat ≠ paraula i l'eixida diu esperat (p. ex. «anou» fruit)
  correcta_cat  esperat = paraula i l'eixida la deixa (p. ex. «nou» adjectiu)
  deixa_cat     esperat ≠ paraula i l'eixida deixa la catalana (error lleu)
  error_sentit  l'eixida posa una altra paraula (error greu)
El jutge «marca» el lloc si algun tros amb error conté la paraula de l'eixida.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # consola de Windows (cp1252): «≠», «…»
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ARREL = Path(__file__).resolve().parents[3]  # arrel del repositori (en jutge_llm/)
BENCH = {
    "homografs": ["benchmark_homografs_cat_val.json"],
    "homografs_v2": ["benchmark_homografs_v2_cat_val.json"],
}
SISTEMES = {"referencia": "Referència", "avlizador": "AVLizador 2.0.1", "motor": "Motor sol"}
CLASSES = ["correcta_val", "correcta_cat", "deixa_cat", "error_sentit"]
NOM_CLASSE = {
    "correcta_val": "Correcta, forma valenciana (anou fruit, colp, llavadora…)",
    "correcta_cat": "Correcta, paraula catalana mantinguda (nou adjectiu, calces de vestir…)",
    "deixa_cat": "Deixa el català on calia traduir (lleu)",
    "error_sentit": "Error de sentit (cotxe anou, bragues per calces…)",
}


def paraules(text: str) -> list[str]:
    """
    >>> paraules("Afig d’anous a l'ensalada.")
    ['afig', 'd', 'anous', 'a', 'l', 'ensalada']
    """
    return re.findall(r"[\w·]+", text.replace("’", "'").lower())


def paraula_al_lloc(origen: str, eixida: str, p: str) -> str | None:
    """Paraula de l'eixida alineada amb la primera aparició de `p` en l'origen.

    >>> paraula_al_lloc("Ha comprat un cotxe nou.", "Ha comprat un cotxe anou.", "nou")
    'anou'
    >>> paraula_al_lloc("Ha comprat un cotxe nou.", "Ha comprat un cotxe nou.", "nou")
    'nou'
    """
    o, e = paraules(origen), paraules(eixida)
    if p not in o:
        return None
    i = o.index(p)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, o, e, autojunk=False).get_opcodes():
        if i1 <= i < i2:
            if op == "equal":
                return e[j1 + i - i1]
            if op == "replace":
                return " ".join(e[j1:j2])
            return None  # esborrada
    return None


def classifica(p: str, esperat: str, w: str | None) -> str | None:
    if w is None:
        return None
    ws = w.split()
    if esperat in ws:
        return "correcta_val" if esperat != p else "correcta_cat"
    if p in ws:
        return "deixa_cat"
    return "error_sentit"


def carrega_bench() -> dict[str, dict]:
    b = {}
    for fitxers in BENCH.values():
        for f in fitxers:
            d = json.loads((ARREL / "dades/benchmarks/homografs" / f).read_text(encoding="utf-8"))
            for x in (d if isinstance(d, list) else d["frases"]):
                if x.get("paraula"):
                    b[x["id"]] = x
    return b


def recull(dir_prompt: Path, bench: dict) -> list[dict]:
    files = []
    for conjunt in BENCH:
        for clau in SISTEMES:
            fs = list((dir_prompt / conjunt).glob(f"*_pensa/{clau}.json"))
            if not fs:
                continue
            for r in json.loads(fs[0].read_text(encoding="utf-8"))["resultats"]:
                x = bench.get(r["id"])
                if not x:
                    continue
                w = paraula_al_lloc(r["entrada"], r["hipotesi"], x["paraula"])
                c = classifica(x["paraula"], x["esperat"], w)
                if c is None:
                    continue
                trossos = [set(paraules(s["text"])) for s in r["error_spans"]]
                marca = any(set(w.split()) & t for t in trossos)
                files.append(dict(conjunt=conjunt, sistema=clau, id=r["id"], paraula=x["paraula"],
                                  esperat=x["esperat"], w=w, classe=c, marca=marca, nota=r["nota"],
                                  text=r["hipotesi"],
                                  trossos=[(s["severity"], s["text"]) for s in r["error_spans"]]))
    return files


def singular(p: str, totes: set[str]) -> str:
    """Agrupa el plural amb el singular, si el singular també és en el benchmark.

    >>> [singular(p, {"manca", "manques", "nou", "nous", "calces", "panotxa", "panotxes"})
    ...  for p in ["manques", "nous", "calces", "panotxes"]]
    ['manca', 'nou', 'calces', 'panotxa']
    """
    if p.endswith("s"):
        for c in (p[:-1], p[:-2] + "a", p[:-4] + "ca"):
            if c in totes:
                return c
    return p


def auc(pos: list[float], neg: list[float]) -> float:
    """Probabilitat que una frase amb error tinga menys nota que una correcta (empats = 0,5)."""
    if not pos or not neg:
        return float("nan")
    s = sum((a < b) + 0.5 * (a == b) for a in pos for b in neg)
    return s / (len(pos) * len(neg))


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "—"


def informe(files: list[dict], titol: str) -> list[str]:
    L = [f"## {titol}", ""]
    L += ["| Classe | Llocs | El jutge marca la paraula | Nota mitjana | Frases amb nota < 100 |",
          "|---|---|---|---|---|"]
    per = collections.defaultdict(list)
    for f in files:
        per[f["classe"]].append(f)
    for c in CLASSES:
        fs = per[c]
        if not fs:
            continue
        L.append(f"| {NOM_CLASSE[c]} | {len(fs)} | {pct(sum(f['marca'] for f in fs), len(fs))} | "
                 f"{sum(f['nota'] for f in fs) / len(fs):.1f} | {pct(sum(f['nota'] < 100 for f in fs), len(fs))} |")
    greus = per["error_sentit"]
    bons = per["correcta_val"] + per["correcta_cat"]
    tp = sum(f["marca"] for f in greus)
    fp = sum(f["marca"] for f in bons)
    fp_val = sum(f["marca"] for f in per["correcta_val"])
    L += ["",
          f"- **Exhaustivitat** (errors de sentit que marca): {pct(tp, len(greus))}",
          f"- **Precisió** (de les paraules correctes o errònies que marca, quantes són errors): "
          f"{pct(tp, tp + fp)}",
          f"- **Falsos positius en formes valencianes correctes**: {pct(fp_val, len(per['correcta_val']))}",
          f"- **AUC de la nota** (error de sentit vs. correcta; 0,5 = a l'atzar, 1 = perfecte): "
          f"{auc([f['nota'] for f in greus], [f['nota'] for f in bons]):.2f}",
          ""]
    # per paraula: errors marcats i formes valencianes correctes marcades
    L += ["Per paraula (paraula catalana → esperada; marca / total):", "",
          "| Paraula | Error de sentit marcat | Forma valenciana correcta marcada | Catalana correcta marcada |",
          "|---|---|---|---|"]
    pp = collections.defaultdict(lambda: collections.defaultdict(list))
    totes = {f["paraula"] for f in files}
    for f in files:
        pp[singular(f["paraula"], totes)][f["classe"]].append(f["marca"])
    for k in sorted(pp):
        d = pp[k]
        cel = lambda c: pct(sum(d[c]), len(d[c])) if d[c] else "—"
        L.append(f"| {k} | {cel('error_sentit')} | {cel('correcta_val')} | {cel('correcta_cat')} |")
    return L + [""]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resultats", type=Path, required=True, help="carpeta resultats/ del jutge")
    ap.add_argument("--prompts", nargs="+", default=["valencia", "valencia2"])
    ap.add_argument("--eixida", type=Path, required=True)
    args = ap.parse_args()
    bench = carrega_bench()
    L = ["# Meta-avaluació del jutge en els homògrafs", "", __doc__.split("\n\n", 1)[1].strip(), ""]
    detall = []
    for pr in args.prompts:
        files = recull(args.resultats / pr, bench)
        L += informe(files, f"Prompt «{pr}» (v1 + v2, referència + AVLizador + motor)")
        for s, nom in SISTEMES.items():
            fs = [f for f in files if f["sistema"] == s]
            c = collections.Counter(f["classe"] for f in fs)
            L.append(f"- {nom}: " + ", ".join(f"{k} {c[k]}" for k in CLASSES))
        L.append("")
        for f in files:
            if (f["classe"] == "error_sentit") != f["marca"]:
                detall.append(f"| {pr} | {f['sistema']} | {f['id']} | {f['classe']} | {f['w']} | "
                              f"{f['nota']} | {f['text']} | {'; '.join(t for _, t in f['trossos'])} |")
    L += ["## Casos on el jutge s'equivoca (error no marcat o paraula correcta marcada)", "",
          "| Prompt | Sistema | Id | Classe | Paraula | Nota | Frase | Trossos |", "|---|---|---|---|---|---|---|---|"]
    args.eixida.write_text("\n".join(L + detall) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
