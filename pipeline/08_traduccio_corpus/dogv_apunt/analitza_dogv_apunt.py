"""
analitza_dogv_apunt.py -- Primera mirada als textos valencians que han baixat
els companys (`dades/dogv_apunt/`, 10/11/2026), per a decidir si servixen
per a entrenar el KenLM valencià (substitut de FLOR) millor que MaCoCu:

- `dogv_documents.tsv`: DOGV 2025-2026 (`signatura`, `title`, `text`; els
  salts de línia vénen com a "\\n" literal).
- `ua_noticias_va.jsonl`: notícies de la Universitat d'Alacant en valencià
  (`VA`, `url`, `url_es`: la versió castellana, útil més avant per a es-va).

Per a cada font:
- documents, paraules, documents i frases repetides, línies trencades;
- frases aprofitables com les de MaCoCu (`comu.frase_valida`: 8-40
  paraules, completes) i quantes passarien el criteri del KenLM valencià
  net (GD > 0,5 amb >= 2 marcadors), sobre una mostra;
- GD i GDV (`calcula_gd`) per document i global, sobre una mostra, i els
  marcadors més freqüents de cada costat;
- formes que diuen quina norma seguix (este/aquest, seua/seva, -ix/-eix,
  servici/servei...) i les paraules que fallen al KenLM ("colp", "vegada",
  "reeixida"), sobre TOT el text.

Eixida: `dades/dogv_apunt/analisi_dogv_apunt.{md,json}`.

Ús (des de l'arrel del repositori; uns minuts):
    python pipeline/08_traduccio_corpus/dogv_apunt/analitza_dogv_apunt.py
    python pipeline/08_traduccio_corpus/dogv_apunt/analitza_dogv_apunt.py --mostra-docs 300 --mostra-frases 2000
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ARREL / "pipeline" / "08_traduccio_corpus" / "macocu"))
from comu import _SEPARA, clau_repetida, frase_valida  # noqa: E402

DIR = ARREL / "dades" / "dogv_apunt"
_PARAULA = re.compile(r"[^\W\d_]+(?:[·\-'’][^\W\d_]+)*")

# Parells de formes que diuen quina norma seguix el text (la primera, la
# valenciana de l'AVL; la segona, la catalana de l'IEC), i les paraules
# que fallen al KenLM. Només es compten (no és cap regla del traductor).
PARELLS = [
    ("este/esta/estos/estes", r"\b(este|esta|estos|estes)\b", "aquest/a/s/es", r"\b(aquest|aquesta|aquests|aquestes)\b"),
    ("seua/seues", r"\bseu(a|es)\b", "seva/seves", r"\bsev(a|es)\b"),
    ("servici(s)", r"\bservicis?\b", "servei(s)", r"\bserveis?\b"),
    ("-ix/-ixen (incoatius)", r"\b\w+(?<!e)ix(en)?\b", "-eix/-eixen", r"\b\w+eix(en)?\b"),
    ("hui", r"\bhui\b", "avui", r"\bavui\b"),
    ("xiquet(s)", r"\bxiquet(s|a|es)?\b", "nen(s)", r"\bnen(s|a|es)?\b"),
    ("colp/colps", r"\bcolps?\b", "cop/cops", r"\bcops?\b"),
    ("vegada/vegades", r"\bvegad(a|es)\b", "—", None),
    ("reeixida/es", r"\breeixid(a|es)\b", "èxit(s)", r"\bèxits?\b"),
]


def llig_dogv(path: Path):
    csv.field_size_limit(10**9)
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            text = (r.get("text") or "").replace("\\n", "\n")
            yield r.get("signatura") or "", text


def llig_ua(path: Path, est: Counter):
    with open(path, encoding="utf-8") as f:
        for linia in f:
            if not linia.strip():
                continue
            try:
                r = json.loads(linia)
            except json.JSONDecodeError:
                est["linies_trencades"] += 1
                # p. ex. una "r" solta davant del JSON
                i = linia.find("{")
                if i < 0:
                    continue
                try:
                    r = json.loads(linia[i:])
                except json.JSONDecodeError:
                    continue
            yield r.get("url") or "", r.get("VA") or ""


def frases(text: str):
    for paragraf in text.split("\n"):
        for frase in _SEPARA.split(paragraf.strip()):
            if frase.strip():
                yield frase.strip()


def analitza(nom: str, docs: list[tuple[str, str]], args, rng) -> dict:
    from avlizador.grau_dialectal import calcula_gd

    t0 = time.time()
    est: Counter = Counter()
    hash_docs: Counter = Counter()
    claus: Counter = Counter()
    valides: list[str] = []
    comptes = Counter()
    text_minuscula_parts = []
    for _, text in docs:
        est["documents"] += 1
        est["paraules"] += len(_PARAULA.findall(text))
        hash_docs[hashlib.blake2b(text.strip().encode(), digest_size=8).digest()] += 1
        for f in frases(text):
            est["frases"] += 1
            if frase_valida(f):
                est["frases_valides"] += 1
                c = clau_repetida(f)
                claus[c] += 1
                if claus[c] == 1:
                    valides.append(f)
        text_minuscula_parts.append(text.lower())
    est["documents_repetits"] = sum(n - 1 for n in hash_docs.values() if n > 1)
    est["frases_valides_repetides"] = sum(n - 1 for n in claus.values() if n > 1)
    est["frases_valides_uniques"] = len(valides)

    tot = "\n".join(text_minuscula_parts)
    for val, rv, cat, rc in PARELLS:
        comptes[val] = len(re.findall(rv, tot))
        if rc:
            comptes[cat] = len(re.findall(rc, tot))
    del tot

    # GD per document (mostra)
    mostra_docs = rng.sample(docs, min(args.mostra_docs, len(docs)))
    occ = ori = paraules = 0
    gd_docs = []
    marc_occ: Counter = Counter()
    marc_ori: Counter = Counter()
    for _, text in mostra_docs:
        r = calcula_gd(text)
        occ, ori, paraules = occ + r["total_occidentals"], ori + r["total_orientals"], paraules + r["total_paraules"]
        marc_occ.update(r["marcadors_occidentals"])
        marc_ori.update(r["marcadors_orientals"])
        if r["gd"] is not None:
            gd_docs.append(r["gd"])
    trams = Counter()
    for g in gd_docs:
        trams["≥ 0,95" if g >= 0.95 else "0,8-0,95" if g >= 0.8 else "0,5-0,8" if g > 0.5 else "≤ 0,5"] += 1

    # Criteri del KenLM valencià net (mostra de frases)
    mostra_frases = rng.sample(valides, min(args.mostra_frases, len(valides)))
    passen = un_sol = 0
    exemples_passen, exemples_no = [], []
    for f in mostra_frases:
        r = calcula_gd(f)
        if r["gd"] is not None and r["gd"] > 0.5 and r["total_occidentals"] >= 2:
            passen += 1
            if len(exemples_passen) < args.exemples:
                exemples_passen.append(f)
        else:
            if r["total_occidentals"] == 1 and r["gd"] and r["gd"] > 0.5:
                un_sol += 1
            if len(exemples_no) < args.exemples:
                exemples_no.append((f, r["marcadors_occidentals"], r["marcadors_orientals"]))

    return {
        "font": nom, **est, "comptes": dict(comptes),
        "gd_global_mostra": round(occ / (occ + ori), 4) if occ + ori else None,
        "gdv_global_mostra": round(1 - ori / paraules, 4) if paraules else None,
        "docs_mostra": len(mostra_docs), "trams_gd_docs": dict(trams),
        "marcadors_occidentals": marc_occ.most_common(30), "marcadors_orientals": marc_ori.most_common(30),
        "frases_mostra": len(mostra_frases), "passen_criteri_net": passen, "un_sol_marcador": un_sol,
        "exemples_passen": exemples_passen, "exemples_no_passen": exemples_no,
        "segons": round(time.time() - t0),
    }


def nombre(x) -> str:
    return f"{x:,}".replace(",", ".") if isinstance(x, int) else str(x)


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f} %".replace(".", ",") if b else "—"


def informe(resultats: list[dict]) -> str:
    md = ["# DOGV i notícies de la UA: primera anàlisi", ""]
    noms = [r["font"] for r in resultats]
    md += ["## Mida", "", "| | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms)]
    for clau, etiqueta in (("documents", "Documents"), ("documents_repetits", "Documents repetits"),
                           ("paraules", "Paraules"), ("frases", "Frases"),
                           ("frases_valides", "Frases aprofitables (8-40 paraules, completes)"),
                           ("frases_valides_repetides", "… repetides"),
                           ("frases_valides_uniques", "… úniques"), ("linies_trencades", "Línies trencades")):
        md.append(f"| {etiqueta} | " + " | ".join(nombre(r.get(clau, 0)) for r in resultats) + " |")
    md += ["", "## Grau Dialectal (mostra de documents)", "",
           "| | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms),
           "| Documents de la mostra | " + " | ".join(nombre(r["docs_mostra"]) for r in resultats) + " |",
           "| GD global | " + " | ".join(str(r["gd_global_mostra"]).replace(".", ",") for r in resultats) + " |",
           "| GDV global | " + " | ".join(str(r["gdv_global_mostra"]).replace(".", ",") for r in resultats) + " |"]
    for tram in ("≥ 0,95", "0,8-0,95", "0,5-0,8", "≤ 0,5"):
        md.append(f"| Documents amb GD {tram} | " + " | ".join(
            f"{nombre(r['trams_gd_docs'].get(tram, 0))} ({pct(r['trams_gd_docs'].get(tram, 0), r['docs_mostra'])})"
            for r in resultats) + " |")
    md += ["", "## Criteri del KenLM valencià net (mostra de frases aprofitables)", "",
           "| | " + " | ".join(noms) + " |", "|---|" + "---|" * len(noms),
           "| Frases de la mostra | " + " | ".join(nombre(r["frases_mostra"]) for r in resultats) + " |",
           "| GD > 0,5 amb ≥ 2 marcadors | " + " | ".join(
               f"{nombre(r['passen_criteri_net'])} ({pct(r['passen_criteri_net'], r['frases_mostra'])})"
               for r in resultats) + " |",
           "| GD > 0,5 amb 1 sol marcador | " + " | ".join(
               f"{nombre(r['un_sol_marcador'])} ({pct(r['un_sol_marcador'], r['frases_mostra'])})"
               for r in resultats) + " |",
           "", "Les frases sense cap marcador (la majoria) no són catalanes: són neutres. Totes les d'un "
           "document valencià servixen igualment per a entrenar.", ""]
    md += ["## Quina norma seguix (tot el text)", "", "| Forma | " + " | ".join(noms) + " |",
           "|---|" + "---|" * len(noms)]
    for val, _, cat, rc in PARELLS:
        fila_v = [nombre(r["comptes"].get(val, 0)) for r in resultats]
        md.append(f"| {val} | " + " | ".join(fila_v) + " |")
        if rc:
            md.append(f"| {cat} | " + " | ".join(nombre(r["comptes"].get(cat, 0)) for r in resultats) + " |")
    for r in resultats:
        md += ["", f"## {r['font']}: marcadors més freqüents (mostra)", "",
               "Valencians: " + ", ".join(f"{m} ({n})" for m, n in r["marcadors_occidentals"][:25]), "",
               "Catalans: " + ", ".join(f"{m} ({n})" for m, n in r["marcadors_orientals"][:25]) or "—", "",
               "Exemples que passen el criteri net:", ""]
        md += [f"- {f}" for f in r["exemples_passen"]]
        md += ["", "Exemples que no el passen (marcadors valencians; catalans):", ""]
        md += [f"- {f} *({', '.join(o) or '—'}; {', '.join(c) or '—'})*" for f, o, c in r["exemples_no_passen"]]
    return "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dir", type=Path, default=DIR)
    p.add_argument("--mostra-docs", type=int, default=600)
    p.add_argument("--mostra-frases", type=int, default=4000)
    p.add_argument("--exemples", type=int, default=8)
    p.add_argument("--llavor", type=int, default=13)
    args = p.parse_args(argv)
    rng = random.Random(args.llavor)

    resultats = []
    ua_est: Counter = Counter()
    fonts = (("DOGV", list(llig_dogv(args.dir / "dogv_documents.tsv")), Counter()),
             ("Notícies UA", list(llig_ua(args.dir / "ua_noticias_va.jsonl", ua_est)), ua_est))
    for nom, docs, est in fonts:
        print(f"{nom}: {len(docs):,} documents", flush=True)
        r = analitza(nom, docs, args, rng)
        r["linies_trencades"] = est.get("linies_trencades", 0)
        resultats.append(r)
        print(f"  fet en {r['segons']} s", flush=True)
    (args.dir / "analisi_dogv_apunt.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    (args.dir / "analisi_dogv_apunt.md").write_text(informe(resultats), encoding="utf-8")
    print(f"-> {args.dir / 'analisi_dogv_apunt.md'}")


if __name__ == "__main__":
    main()
