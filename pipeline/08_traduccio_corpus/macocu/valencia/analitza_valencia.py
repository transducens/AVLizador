"""
analitza_valencia.py -- Característiques de les frases valencianes de
MaCoCu (`dades/macocu/valencia/valencia.jsonl`, eixida de
`filtra_valencia.py`), sense tornar a passar spaCy: cada frase ja porta
el GD i els seus marcadors (10/11/2026).

Què mira:
- quantes frases hi ha per nombre de marcadors occidentals (1, 2, 3...) i
  quantes porten també algun marcador català (GD < 1);
- els marcadors més freqüents, en total i en les frases d'un sol
  marcador (on n'hi ha més de falsos: "vegada", "permet"...);
- dominis i dominis de primer nivell (.cat, .es...) que més aporten, i
  quina part del total fan els 20 primers;
- longitud (paraules) i fluïdesa (`lm_score`);
- exemples a l'atzar (llavor fixa) de cada grup, per a llegir-los.

Eixida: `dades/macocu/valencia/analisi_valencia.md` (informe) i
`analisi_valencia.json` (xifres).

Ús (des de l'arrel del repositori; en Abaco, amb `srun`, uns minuts):
    python pipeline/08_traduccio_corpus/macocu/valencia/analitza_valencia.py
    python pipeline/08_traduccio_corpus/macocu/valencia/analitza_valencia.py --exemples 15
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comu import DIR  # noqa: E402

VALENCIA = DIR / "valencia" / "valencia.jsonl"
EIXIDA = DIR / "valencia"


def grup_marcadors(n: int) -> str:
    """
    >>> [grup_marcadors(n) for n in (1, 2, 3, 4, 9)]
    ['1', '2', '3', '4', '5+']
    """
    return str(n) if n < 5 else "5+"


def tld(domini: str) -> str:
    """
    >>> tld("www.ajuntament.valencia.es"), tld("vilaweb.cat"), tld("")
    ('.es', '.cat', '?')
    """
    return "." + domini.rsplit(".", 1)[-1] if "." in domini else "?"


def format_valencia(text: str) -> str:
    """Xifres com s'escriuen en valencià: punt de milers i coma decimal
    (només en la part de les xifres, no en el text dels exemples).

    >>> format_valencia("15,124 frases (83.5 %), lm 0.894, 1,234,567")
    '15.124 frases (83,5 %), lm 0,894, 1.234.567'
    """
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "\x00", text)
    text = re.sub(r"(?<=\d)\.(?=\d)", ",", text)
    return text.replace("\x00", ".")


def percentil(valors: list[float], p: float) -> float:
    valors = sorted(valors)
    return valors[min(len(valors) - 1, int(p * len(valors)))] if valors else 0.0


def taula(files: list[tuple], capcalera: tuple[str, ...]) -> str:
    linies = ["| " + " | ".join(capcalera) + " |", "|" + "---|" * len(capcalera)]
    linies += ["| " + " | ".join(str(c) for c in f) + " |" for f in files]
    return "\n".join(linies)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--entrada", type=Path, default=VALENCIA)
    p.add_argument("--eixida", type=Path, default=EIXIDA)
    p.add_argument("--exemples", type=int, default=10, help="exemples per grup")
    p.add_argument("--llavor", type=int, default=13)
    args = p.parse_args(argv)

    t0 = time.time()
    rng = random.Random(args.llavor)
    total = 0
    per_grup: Counter = Counter()
    mixtes_per_grup: Counter = Counter()
    marcadors: Counter = Counter()
    marcadors_1: Counter = Counter()
    marcadors_or: Counter = Counter()
    dominis: Counter = Counter()
    dominis_2: Counter = Counter()
    tlds: Counter = Counter()
    docs: set = set()
    longituds: list[int] = []
    lm: list[float] = []
    # Reservori d'exemples per grup (1, 2, 3, 4, 5+, i "mixtes" = GD < 1).
    exemples: dict[str, list] = defaultdict(list)
    vistos: Counter = Counter()

    def guarda(grup: str, r: dict) -> None:
        vistos[grup] += 1
        fila = (r["text"], r.get("domini") or "", r["marcadors_occidentals"], r["marcadors_orientals"])
        if len(exemples[grup]) < args.exemples:
            exemples[grup].append(fila)
        else:
            j = rng.randrange(vistos[grup])
            if j < args.exemples:
                exemples[grup][j] = fila

    with open(args.entrada, encoding="utf-8") as f:
        for linia in f:
            r = json.loads(linia)
            total += 1
            occ, ori = r["occ"], r["ori"]
            g = grup_marcadors(occ)
            per_grup[g] += 1
            if ori:
                mixtes_per_grup[g] += 1
                guarda("mixtes", r)
            guarda(g, r)
            marcadors.update(r["marcadors_occidentals"])
            marcadors_or.update(r["marcadors_orientals"])
            if occ == 1:
                marcadors_1.update(r["marcadors_occidentals"])
            domini = r.get("domini") or ""
            dominis[domini] += 1
            if occ >= 2:
                dominis_2[domini] += 1
            tlds[tld(domini)] += 1
            docs.add(r.get("doc"))
            longituds.append(r.get("total_paraules", len(r["text"].split())))
            lm.append(float(r.get("lm_score", 0)))
            if total % 500_000 == 0:
                print(f"  {total:,} frases ({time.time() - t0:,.0f} s)", flush=True)

    def pct(n: int) -> str:
        return f"{100 * n / total:.1f} %" if total else "0 %"

    grups = ["1", "2", "3", "4", "5+"]
    almenys2 = sum(per_grup[g] for g in grups[1:])
    top20 = sum(n for _, n in dominis.most_common(20))
    resum = {
        "frases": total, "documents": len(docs), "dominis": len(dominis),
        "per_marcadors": {g: per_grup[g] for g in grups},
        "amb_marcador_catala_per_marcadors": {g: mixtes_per_grup[g] for g in grups},
        "almenys_2_marcadors": almenys2,
        "marcadors_mes_frequents": marcadors.most_common(60),
        "marcadors_frases_1_marcador": marcadors_1.most_common(60),
        "marcadors_catalans_mes_frequents": marcadors_or.most_common(30),
        "dominis_mes_frequents": dominis.most_common(40),
        "dominis_mes_frequents_2_marcadors": dominis_2.most_common(40),
        "tld": tlds.most_common(15),
        "part_20_dominis": round(top20 / total, 4) if total else 0,
        "paraules": {"mitjana": round(statistics.mean(longituds), 1) if longituds else 0,
                     "mediana": statistics.median(longituds) if longituds else 0},
        "lm_score": {"mitjana": round(statistics.mean(lm), 3) if lm else 0,
                     "p10": percentil(lm, 0.1), "p50": percentil(lm, 0.5)},
        "segons": round(time.time() - t0),
    }
    args.eixida.mkdir(parents=True, exist_ok=True)
    (args.eixida / "analisi_valencia.json").write_text(json.dumps(resum, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")

    md = [f"# Frases valencianes de MaCoCu-ca ({total:,} frases)", "",
          f"Font: `{args.entrada.name}` (GD > 0,5 amb ≥ 1 marcador occidental). "
          f"{len(docs):,} documents, {len(dominis):,} dominis.", "",
          "## Per nombre de marcadors valencians", "",
          taula([(g, f"{per_grup[g]:,}", pct(per_grup[g]), f"{mixtes_per_grup[g]:,}") for g in grups],
                ("Marcadors", "Frases", "%", "També amb algun marcador català")), "",
          f"Amb ≥ 2 marcadors: **{almenys2:,}** ({pct(almenys2)}).", "",
          "## Marcadors valencians més freqüents", "",
          taula([(m, f"{n:,}") for m, n in marcadors.most_common(30)], ("Marcador", "Vegades")), "",
          "## En les frases d'un sol marcador", "",
          "Ací és on n'hi ha més de falsos (formes que també són català normal).", "",
          taula([(m, f"{n:,}", f"{100 * n / max(per_grup['1'], 1):.1f} %") for m, n in marcadors_1.most_common(30)],
                ("Marcador", "Frases", "% de les d'1 marcador")), "",
          "## Marcadors catalans que hi apareixen (frases mixtes)", "",
          taula([(m, f"{n:,}") for m, n in marcadors_or.most_common(20)], ("Marcador", "Vegades")), "",
          "## Dominis", "",
          f"Els 20 primers fan el {100 * resum['part_20_dominis']:.1f} % de les frases.", "",
          taula([(d or "?", f"{n:,}", pct(n), f"{dominis_2[d]:,}") for d, n in dominis.most_common(30)],
                ("Domini", "Frases", "%", "Amb ≥ 2 marcadors")), "",
          "Domini de primer nivell:", "",
          taula([(t, f"{n:,}", pct(n)) for t, n in tlds.most_common(10)], ("TLD", "Frases", "%")), "",
          "## Longitud i fluïdesa", "",
          f"- Paraules per frase: mitjana {resum['paraules']['mitjana']}, mediana {resum['paraules']['mediana']}.",
          f"- `lm_score` (Monocleaner, 0-1): mitjana {resum['lm_score']['mitjana']}, "
          f"p10 {resum['lm_score']['p10']}, mediana {resum['lm_score']['p50']}.", "",
          "## Exemples a l'atzar", ""]
    for g in grups + ["mixtes"]:
        titol = "frases amb algun marcador català" if g == "mixtes" else f"{g} marcador(s)"
        md += [f"### {titol} ({format_valencia(f'{vistos[g]:,}')})", ""]
        for text, domini, occ, ori in exemples[g]:
            extra = f"; català: {', '.join(ori)}" if ori else ""
            md.append(f"- {text} *({domini}; valencià: {', '.join(occ)}{extra})*")
        md.append("")
    text = "\n".join(md)
    xifres, separador, exemples_md = text.partition("## Exemples a l'atzar")
    (args.eixida / "analisi_valencia.md").write_text(format_valencia(xifres) + separador + exemples_md,
                                                     encoding="utf-8")
    print(f"Fet en {resum['segons']} s: {args.eixida / 'analisi_valencia.md'}")


if __name__ == "__main__":
    main()
