"""
desglossa_frases.py -- XCOMET-XL sense referència i el jutge LLM (Qwen 3.6,
GEMBA-ESA només amb la traducció) frase a frase, en el manual mescla (458),
per a vore on difereixen (19/11/2026).

No puntua res: llig els JSON que ja hi ha (`../comet/resultats/*_qe.json` i
`../jutge_llm/resultats/qwen3.6-35b-a3b/*.json`) i hi afig, per a cada
frase i sistema, les nostres mesures: igual a la referència, chrF i TER
contra la referència, GD de l'eixida amb els marcadors, i quants trossos
marcats com a error cauen en una forma valenciana o catalana del lèxic.

Sistemes per defecte: la referència (el valencià del manual com a
traducció), "sense traduir" (el català tal qual), AVLizador 2.0.0 i el
millor LLM del baseline (gemma3:12b, el de TER més baix i GD més alt).

    python desglossa_frases.py
    python desglossa_frases.py --sistemes referencia copia avlizador_1.1.0 ollama_gemma3-12b

Eixides (`resultats/`):
- `frases_sistemes.csv`: una fila per frase i sistema.
- `frases.csv`: una fila per frase, els sistemes en columnes i les
  diferències de cada parell (A − B) en cada mètrica.
- `resum.md`: mitjanes, parells (quantes frases guanya cada un segons cada
  mètrica), acord amb el GD, frases on més es prefereix el català, on
  XCOMET i el jutge discrepen més, i paraules més marcades com a error.
- `visor.html`: visor sense dependències (filtres, ordre, trossos d'error
  pintats).
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DIR_COMET = AQUI.parent / "comet" / "resultats"
DIR_JUTGE = AQUI.parent / "jutge_llm" / "resultats" / "qwen3.6-35b-a3b"

SISTEMES_PER_DEFECTE = ["referencia", "copia", "avlizador_2.0.0", "ollama_gemma3-12b"]
NOMS = {
    "referencia": "Referència",
    "copia": "Sense traduir",
    "avlizador_2.0.0": "AVLizador 2.0.0",
    "avlizador_1.1.0": "AVLizador 1.1.0",
    "avlizador": "AVLizador 1.0.1",
    "motor": "Motor sol",
    "ollama_gemma3-12b": "gemma3:12b",
}
# Parells (A, B): A − B en cada mètrica; > 0 = la mètrica prefereix A.
PARELLS_PER_DEFECTE = [
    ("referencia", "copia"),
    ("avlizador_2.0.0", "copia"),
    ("avlizador_2.0.0", "ollama_gemma3-12b"),
    ("avlizador_2.0.0", "referencia"),
]
METRIQUES = ["xcomet", "jutge", "gd", "chrf"]
NOM_METRICA = {"xcomet": "XCOMET-XL qe", "jutge": "Jutge Qwen 3.6", "gd": "GD", "chrf": "chrF (ref.)"}
PARAULA_RE = re.compile(r"[\w·]+", re.UNICODE)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def norm(text: str) -> str:
    return " ".join(text.replace("’", "'").replace("ʼ", "'").split())


def subconjunt(id_: str) -> str:
    return "BOE" if id_.startswith("BM-BOE-") else "AVL" if id_.startswith("BM-AVL-") else "?"


def nom(sistema: str) -> str:
    return NOMS.get(sistema, sistema)


def llig(sistema: str, dir_jutge: Path) -> dict[str, dict] | None:
    f_comet = DIR_COMET / f"{sistema}__XCOMET-XL_qe.json"
    f_jutge = dir_jutge / f"{sistema}.json"
    falten = [str(f) for f in (f_comet, f_jutge) if not f.exists()]
    if falten:
        print(f"AVÍS: {nom(sistema)} fora, falten: {', '.join(falten)}", file=sys.stderr)
        return None
    comet = {x["id"]: x for x in json.loads(f_comet.read_text(encoding="utf-8"))["resultats"]}
    jutge = {x["id"]: x for x in json.loads(f_jutge.read_text(encoding="utf-8"))["resultats"]}
    if set(comet) != set(jutge):
        print(f"AVÍS: {nom(sistema)}: XCOMET i el jutge no tenen les mateixes frases "
              f"({len(comet)} / {len(jutge)}); només les comunes.", file=sys.stderr)
    files = {}
    for id_ in comet.keys() & jutge.keys():
        c, j = comet[id_], jutge[id_]
        if norm(c["hipotesi"]) != norm(j["hipotesi"]):
            print(f"AVÍS: {nom(sistema)} {id_}: la traducció no és la mateixa en XCOMET i el jutge.",
                  file=sys.stderr)
        files[id_] = {
            "entrada": c["entrada"], "referencia": c["referencia"], "hipotesi": c["hipotesi"],
            "xcomet": c["comet"], "xcomet_trossos": c.get("error_spans") or [],
            "jutge": j.get("nota"), "jutge_des_errors": j.get("nota_spans"),
            "jutge_trossos": j.get("error_spans") or [],
        }
    return files


LLETRA_RE = re.compile(r"[\w·]", re.UNICODE)


def amplia_tros(text: str, hipotesi: str) -> str | None:
    """El tros tal com és en la traducció, ampliat fins a paraules senceres.

    XCOMET treballa amb subparaules i de vegades marca un tros de paraula
    («bra» de «brama»): es busca primer com a paraula sencera i, si no, com a
    tros, i s'estén fins als límits de paraula. None si no és en la traducció.

    >>> amplia_tros("bra", "La brama dels llauradors")
    'brama'
    >>> amplia_tros("ció influenciar", "per derivació influenciar.")
    'derivació influenciar'
    >>> amplia_tros("d", "Així, d'oferir")
    'd'
    >>> amplia_tros("res", "Així, d'oferir") is None
    True
    """
    q = text.strip().lower()
    if not q:
        return None
    low = hipotesi.lower()
    m = re.search(rf"(?<![\w·]){re.escape(q)}(?![\w·])", low)
    if m:
        return hipotesi[m.start():m.end()]
    i = low.find(q)
    if i < 0:
        return None
    j = i + len(q)
    while i > 0 and LLETRA_RE.match(hipotesi[i - 1]):
        i -= 1
    while j < len(hipotesi) and LLETRA_RE.match(hipotesi[j]):
        j += 1
    return hipotesi[i:j]


def classifica_tros(text: str, hipotesi: str, val: set[str], cat: set[str]) -> str:
    """'val' / 'cat' si el tros (ampliat a paraules senceres) té un marcador
    del GD de l'eixida, 'neutra' si no, 'no_trobat' si el text no és en la
    traducció (el jutge de vegades hi posa raonament)."""
    ampliat = amplia_tros(text, hipotesi)
    if ampliat is None:
        return "no_trobat"
    paraules = set(PARAULA_RE.findall(ampliat.lower()))
    if paraules & val:
        return "val"
    if paraules & cat:
        return "cat"
    return "neutra"


def canvis(a: str, b: str) -> list[str]:
    """Paraules que canvien de B a A ("aquest→este")."""
    ta, tb = norm(a).split(), norm(b).split()
    eix = []
    for tag, b1, b2, a1, a2 in difflib.SequenceMatcher(None, tb, ta, autojunk=False).get_opcodes():
        if tag != "equal":
            eix.append(f"{' '.join(tb[b1:b2]) or '∅'}→{' '.join(ta[a1:a2]) or '∅'}")
    return eix


def mesura(dades: dict[str, dict[str, dict]]) -> None:
    import sacrebleu
    from avlizador.grau_dialectal.gd import calcula_gd

    total = sum(len(v) for v in dades.values())
    fet = 0
    for sistema, files in dades.items():
        for x in files.values():
            ref, hip = norm(x["referencia"]), norm(x["hipotesi"])
            x["igual_referencia"] = hip == ref
            x["chrf"] = round(sacrebleu.sentence_chrf(hip, [ref]).score, 2)
            x["ter"] = round(sacrebleu.sentence_ter(hip, [ref]).score, 2)
            g = calcula_gd(x["hipotesi"])
            x["gd"] = g["gd"]
            x["marcadors_val"] = g["marcadors_occidentals"]
            x["marcadors_cat"] = g["marcadors_orientals"]
            val, cat = set(g["marcadors_occidentals"]), set(g["marcadors_orientals"])
            for clau in ("xcomet_trossos", "jutge_trossos"):
                for t in x[clau]:
                    t["classe"] = classifica_tros(t.get("text", ""), x["hipotesi"], val, cat)
                    t["ampliat"] = amplia_tros(t.get("text", ""), x["hipotesi"])
            fet += 1
            if fet % 200 == 0:
                print(f"  {fet}/{total}", file=sys.stderr)


def compta(trossos: list[dict]) -> collections.Counter:
    return collections.Counter(t["classe"] for t in trossos)


def text_trossos(trossos: list[dict]) -> str:
    return " | ".join(f"{t.get('text', '')[:80]} [{t.get('severity', '?')}, {t['classe']}]" for t in trossos)


def fmt(v, dec=2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{dec}f}".replace(".", ",")
    return str(v)


def diferencia(a, b):
    return None if a is None or b is None else round(a - b, 4)


def inversions(x: dict[str, dict], sistemes: list[str], m1: str, m2: str) -> int:
    """Parells de sistemes que les dues mètriques ordenen al revés (sense empats)."""
    n = 0
    for i, a in enumerate(sistemes):
        for b in sistemes[i + 1:]:
            d1 = diferencia(x[a][m1], x[b][m1])
            d2 = diferencia(x[a][m2], x[b][m2])
            if d1 and d2 and (d1 > 0) != (d2 > 0):
                n += 1
    return n


def escriu_csv(dades, ids, sistemes, parells, eixida: Path) -> None:
    with open(eixida / "frases_sistemes.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "subconjunt", "sistema", "entrada", "referencia", "hipotesi",
                    "igual_referencia", "chrf", "ter", "gd", "marcadors_val", "marcadors_cat",
                    "xcomet", "xcomet_errors", "xcomet_errors_val", "xcomet_errors_cat",
                    "xcomet_trossos", "jutge", "jutge_des_errors", "jutge_errors",
                    "jutge_errors_val", "jutge_errors_cat", "jutge_trossos"])
        for id_ in ids:
            for s in sistemes:
                x = dades[s][id_]
                cx, cj = compta(x["xcomet_trossos"]), compta(x["jutge_trossos"])
                w.writerow([id_, subconjunt(id_), nom(s), x["entrada"], x["referencia"], x["hipotesi"],
                            int(x["igual_referencia"]), x["chrf"], x["ter"], x["gd"],
                            " ".join(x["marcadors_val"]), " ".join(x["marcadors_cat"]),
                            x["xcomet"], len(x["xcomet_trossos"]), cx["val"], cx["cat"],
                            text_trossos(x["xcomet_trossos"]), x["jutge"], x["jutge_des_errors"],
                            len(x["jutge_trossos"]), cj["val"], cj["cat"],
                            text_trossos(x["jutge_trossos"])])
    with open(eixida / "frases.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        cap = ["id", "subconjunt", "entrada", "referencia"]
        for s in sistemes:
            cap += [f"{nom(s)}: traducció"] + [f"{nom(s)}: {NOM_METRICA[m]}" for m in METRIQUES]
        for a, b in parells:
            cap += [f"{NOM_METRICA[m]}: {nom(a)} − {nom(b)}" for m in METRIQUES]
            cap += [f"canvis {nom(b)} → {nom(a)}"]
        cap += ["inversions XCOMET / jutge"]
        w.writerow(cap)
        for id_ in ids:
            x = {s: dades[s][id_] for s in sistemes}
            fila = [id_, subconjunt(id_), x[sistemes[0]]["entrada"], x[sistemes[0]]["referencia"]]
            for s in sistemes:
                fila += [x[s]["hipotesi"]] + [x[s][m] for m in METRIQUES]
            for a, b in parells:
                fila += [diferencia(x[a][m], x[b][m]) for m in METRIQUES]
                fila += [" ; ".join(canvis(x[a]["hipotesi"], x[b]["hipotesi"]))]
            fila += [inversions(x, sistemes, "xcomet", "jutge")]
            w.writerow(fila)


def mitjana(vs):
    vs = [v for v in vs if v is not None]
    return sum(vs) / len(vs) if vs else None


def escriu_resum(dades, ids, sistemes, parells, eixida: Path, top: int) -> None:
    L = ["# Desglossament per frase: XCOMET-XL sense referència i jutge Qwen 3.6", "",
         f"Manual mescla, {len(ids)} frases. Generat per `desglossa_frases.py`. "
         "XCOMET-XL en mode `qe` (català + traducció); jutge Qwen 3.6 35B-A3B amb "
         "GEMBA-ESA només amb la traducció (nota de la fase 2). GD i chrF de "
         "l'eixida com a regla de mesura (el chrF, contra la referència).", ""]

    # 1. Mitjanes
    L += ["## 1. Mitjanes", "",
          "| Sistema | XCOMET qe | Jutge | GD | chrF | Iguals a la ref. | Trossos XCOMET (val / cat / total) | Trossos jutge (val / cat / total) |",
          "|---|---|---|---|---|---|---|---|"]
    for s in sistemes:
        xs = [dades[s][i] for i in ids]
        cx = sum((compta(x["xcomet_trossos"]) for x in xs), collections.Counter())
        cj = sum((compta(x["jutge_trossos"]) for x in xs), collections.Counter())
        L.append(f"| {nom(s)} | {fmt(mitjana([x['xcomet'] for x in xs]))} | "
                 f"{fmt(mitjana([x['jutge'] for x in xs]))} | {fmt(mitjana([x['gd'] for x in xs]), 3)} | "
                 f"{fmt(mitjana([x['chrf'] for x in xs]))} | {sum(x['igual_referencia'] for x in xs)} | "
                 f"{cx['val']} / {cx['cat']} / {sum(cx.values())} | {cj['val']} / {cj['cat']} / {sum(cj.values())} |")
    L += ["", "Trossos «val» / «cat»: el tros marcat com a error conté una forma "
          "valenciana / catalana del lèxic (marcadors del GD de l'eixida).", ""]

    # 2. Parells
    L += ["## 2. Parells, frase a frase", "",
          "Per a cada parell A / B: en quantes frases cada mètrica puntua més A, "
          "empata o puntua més B, i la diferència mitjana (A − B).", ""]
    for a, b in parells:
        L += [f"### {nom(a)} / {nom(b)}", "",
              f"| Mètrica | Guanya {nom(a)} | Empat | Guanya {nom(b)} | Diferència mitjana |",
              "|---|---|---|---|---|"]
        for m in METRIQUES:
            ds = [diferencia(dades[a][i][m], dades[b][i][m]) for i in ids]
            ds = [d for d in ds if d is not None]
            L.append(f"| {NOM_METRICA[m]} | {sum(d > 0 for d in ds)} | {sum(d == 0 for d in ds)} | "
                     f"{sum(d < 0 for d in ds)} | {fmt(mitjana(ds), 3)} |")
        # Acord amb el GD quan el GD diu clarament qui és més valencià.
        gd_a = [i for i in ids if (diferencia(dades[a][i]["gd"], dades[b][i]["gd"]) or 0) > 0]
        if gd_a:
            L += ["", f"Frases on el GD diu que {nom(a)} és més valencià: {len(gd_a)}. D'elles, "
                  + ", ".join(f"{NOM_METRICA[m]} puntua més {nom(a)} en "
                              f"{sum((diferencia(dades[a][i][m], dades[b][i][m]) or 0) > 0 for i in gd_a)}"
                              for m in ("xcomet", "jutge")) + "."]
        iguals = [i for i in ids if dades[a][i]["igual_referencia"] and not dades[b][i]["igual_referencia"]]
        if a != "referencia" and iguals:
            L += ["", f"Frases on {nom(a)} és idèntic a la referència i {nom(b)} no: {len(iguals)}. "
                  "Hi puntua més " + nom(b) + ": "
                  + ", ".join(f"{NOM_METRICA[m]} {sum((diferencia(dades[a][i][m], dades[b][i][m]) or 0) < 0 for i in iguals)}"
                              for m in ("xcomet", "jutge")) + "."]
        L.append("")
        for m in ("xcomet", "jutge"):
            pitjors = sorted((i for i in ids if diferencia(dades[a][i][m], dades[b][i][m]) is not None),
                             key=lambda i: diferencia(dades[a][i][m], dades[b][i][m]))[:top]
            pitjors = [i for i in pitjors if diferencia(dades[a][i][m], dades[b][i][m]) < 0]
            if not pitjors:
                continue
            L += [f"#### {NOM_METRICA[m]}: on més prefereix {nom(b)} ({len(pitjors)})", "",
                  f"| id | {nom(a)} − {nom(b)} | {nom(a)} | {nom(b)} | GD A / B | Canvis {nom(b)} → {nom(a)} | Trossos d'error en {nom(a)} |",
                  "|---|---|---|---|---|---|---|"]
            for i in pitjors:
                xa, xb = dades[a][i], dades[b][i]
                tr = "; ".join(f"«{t.get('text', '')[:40]}» ({t['classe']})" for t in xa[f"{m}_trossos"])
                L.append(f"| {i} | {fmt(diferencia(xa[m], xb[m]))} | {fmt(xa[m])} | {fmt(xb[m])} | "
                         f"{fmt(xa['gd'], 2)} / {fmt(xb['gd'], 2)} | "
                         f"{'; '.join(canvis(xa['hipotesi'], xb['hipotesi']))[:160].replace('|', '/')} | "
                         f"{tr[:200].replace('|', '/')} |")
            L.append("")

    # 3. Discrepància XCOMET / jutge
    L += ["## 3. On XCOMET i el jutge discrepen més", "",
          f"Parells de sistemes que les dues mètriques ordenen al revés (de {len(sistemes) * (len(sistemes) - 1) // 2}).", ""]
    disc = sorted(ids, key=lambda i: -inversions({s: dades[s][i] for s in sistemes}, sistemes, "xcomet", "jutge"))
    distrib = collections.Counter(inversions({s: dades[s][i] for s in sistemes}, sistemes, "xcomet", "jutge") for i in ids)
    L += ["Distribució: " + ", ".join(f"{k} inversions: {v} frases" for k, v in sorted(distrib.items())), "",
          "| id | Inversions | " + " | ".join(f"{nom(s)} (XCOMET / jutge / GD)" for s in sistemes) + " |",
          "|---|---|" + "---|" * len(sistemes)]
    for i in disc[:top]:
        x = {s: dades[s][i] for s in sistemes}
        L.append(f"| {i} | {inversions(x, sistemes, 'xcomet', 'jutge')} | "
                 + " | ".join(f"{fmt(x[s]['xcomet'])} / {fmt(x[s]['jutge'], 0)} / {fmt(x[s]['gd'], 2)}" for s in sistemes) + " |")
    L.append("")

    # 4. Paraules marcades
    L += ["## 4. Paraules més marcades com a error", "",
          "Paraules dels trossos d'error (els trobats en la traducció), per sistema i mètrica: "
          "primer les formes del lèxic (val / cat = marcador del GD de l'eixida), amb quantes "
          "vegades cauen dins d'un tros d'error; després la resta. XCOMET marca sovint trossos "
          "de paraula («bra» de «brama»): es compta la paraula sencera on cau.", ""]
    for m in ("xcomet", "jutge"):
        L += [f"### {NOM_METRICA[m]}", ""]
        for s in sistemes:
            c = collections.Counter()
            for i in ids:
                x = dades[s][i]
                val, cat = set(x["marcadors_val"]), set(x["marcadors_cat"])
                for t in x[f"{m}_trossos"]:
                    if t["classe"] == "no_trobat":
                        continue
                    for p in set(PARAULA_RE.findall((t.get("ampliat") or "").lower())):
                        c[(p, "val" if p in val else "cat" if p in cat else "")] += 1
            lexic = ", ".join(f"{p} ({k}) {n}" for (p, k), n in c.most_common() if k)
            altres = ", ".join(f"{p} {n}" for (p, k), n in c.most_common() if not k and len(p) >= 4)
            L += [f"- **{nom(s)}**: formes del lèxic: {lexic[:600] or '—'}",
                  f"  - altres (≥ 4 lletres): {altres[:400] or '—'}"]
        L.append("")

    (eixida / "resum.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def escriu_visor(dades, ids, sistemes, parells, eixida: Path) -> None:
    frases = []
    for i in ids:
        frases.append({
            "id": i, "sub": subconjunt(i),
            "entrada": dades[sistemes[0]][i]["entrada"], "referencia": dades[sistemes[0]][i]["referencia"],
            "inv": inversions({s: dades[s][i] for s in sistemes}, sistemes, "xcomet", "jutge"),
            "sis": {s: {k: dades[s][i][k] for k in ("hipotesi", "xcomet", "jutge", "gd", "chrf",
                                                     "igual_referencia", "marcadors_val", "marcadors_cat",
                                                     "xcomet_trossos", "jutge_trossos")} for s in sistemes},
        })
    dades_js = json.dumps({"sistemes": [[s, nom(s)] for s in sistemes], "parells": parells,
                           "metriques": [[m, NOM_METRICA[m]] for m in METRIQUES], "frases": frases},
                          ensure_ascii=False).replace("</", "<\\/")
    plantilla = (AQUI / "visor_plantilla.html").read_text(encoding="utf-8")
    (eixida / "visor.html").write_text(plantilla.replace("/*DADES*/null", dades_js), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sistemes", nargs="+", default=SISTEMES_PER_DEFECTE,
                    help="Noms dels fitxers (sense sufix): referencia, copia, avlizador_2.0.0, ollama_gemma3-12b...")
    ap.add_argument("--parells", nargs="+", metavar="A:B",
                    help="Parells A:B (per defecte, la referència i AVLizador contra la resta).")
    ap.add_argument("--jutge", type=Path, default=DIR_JUTGE, help="Carpeta de resultats del jutge.")
    ap.add_argument("--eixida", type=Path, default=AQUI / "resultats")
    ap.add_argument("--top", type=int, default=20, help="Frases per llista en el resum.")
    args = ap.parse_args(argv)

    dades = {}
    for s in args.sistemes:
        d = llig(s, args.jutge)
        if d is not None:
            dades[s] = d
    sistemes = list(dades)
    if len(sistemes) < 2:
        print("ERROR: calen almenys dos sistemes amb XCOMET qe i jutge.", file=sys.stderr)
        return 1
    ids = sorted(set.intersection(*(set(v) for v in dades.values())))
    if args.parells:
        parells = [tuple(p.split(":", 1)) for p in args.parells]
    else:
        parells = [p for p in PARELLS_PER_DEFECTE if p[0] in dades and p[1] in dades]
        if not parells:
            parells = [(sistemes[0], s) for s in sistemes[1:]]
    for a, b in parells:
        if a not in dades or b not in dades:
            print(f"ERROR: el parell {a}:{b} té un sistema que no s'ha carregat.", file=sys.stderr)
            return 1

    print(f"Sistemes: {', '.join(nom(s) for s in sistemes)}; {len(ids)} frases. Mesurant GD, chrF i TER...",
          file=sys.stderr)
    mesura(dades)
    args.eixida.mkdir(parents=True, exist_ok=True)
    escriu_csv(dades, ids, sistemes, parells, args.eixida)
    escriu_resum(dades, ids, sistemes, parells, args.eixida, args.top)
    escriu_visor(dades, ids, sistemes, parells, args.eixida)
    print(f"Fet: {args.eixida}/frases_sistemes.csv, frases.csv, resum.md, visor.html", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
