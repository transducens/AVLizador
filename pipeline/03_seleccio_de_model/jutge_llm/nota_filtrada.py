"""
nota_filtrada.py -- nota del jutge sense els trossos que són paraules
valencianes vàlides (26/11/2026).

Per què: amb el prompt «valencia» el jutge ja quasi no castiga el valencià,
però encara marca paraules valencianes que no coneix (perjuí, panolla,
hamaca, fartades, anou...). Tres prompts més (valencia2, valencia3,
valencia_va) no ho han arreglat: el model no sap què volen dir. En compte de
demanar-li-ho, es corregix després amb els nostres diccionaris:

1. Parells dels nostres diccionaris: costat valencià d'una paraula →
   formes catalanes (`lexic_general.json` i `conjugacions_dialectals.json`,
   forma i infinitiu; el català pot ser de més d'una paraula: «blat de
   moro» → «dacsa»).
2. Un tros marcat no compta si cada paraula seua (sense les partícules
   d'una lletra: l', d', a, i...) és l'equivalent valencià d'una paraula que
   hi ha en l'original català: és l'adaptació dialectal. «l'hamaca» per
   «gandula» o «este» per «aquest» no compten; «la gasto» sí (la no és en
   cap parell), «després» on l'original diu «abans» també, i el tros que el
   jutge copia mal (no és en la frase), també.
3. Nota = 100 − 10 per error greu − 2,5 per error lleu amb els trossos que
   queden (la conversió del WMT26 que ja fa `jutge_gemba.nota_des_de_spans`).

El que perd: una paraula valenciana que existix però que va en un altre
sentit («bragues» per calces d'època, «vegada» per cop) tampoc no compta.
Això ho mesura el comparador d'homògrafs.

    python nota_filtrada.py resultats/valencia/manual/qwen3.6-35b-a3b_pensa
    python nota_filtrada.py <carpeta> --json eixida.json --md eixida.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DADES = AQUI.parents[2] / "src" / "avlizador" / "traductor_cat_val" / "data"
PARAULA_RE = re.compile(r"[\w·]+", re.UNICODE)
NOMS = {"referencia": "Referència", "copia": "Sense traduir (català)", "avlizador": "AVLizador 2.0.1",
        "ollama_gemma3-12b": "gemma3:12b", "motor": "Motor sol", "correcta": "Versió correcta",
        "erronia": "Versió amb error"}

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

_FORMES: dict[str, frozenset[str]] | None = None


def formes_valencianes() -> dict[str, frozenset[str]]:
    """Paraula valenciana (minúscules) → formes catalanes dels nostres diccionaris.

    >>> f = formes_valencianes()
    >>> all(p in f for p in ["hamaca", "panolla", "bragues", "anou", "este", "seua", "tindre", "servicis"])
    True
    >>> "gandula" in f["hamaca"], "la" in f
    (True, False)
    """
    global _FORMES
    if _FORMES is None:
        f: dict[str, set[str]] = {}

        def afig(val, cat):
            v, c = (val or "").strip().lower(), (cat or "").strip().lower()
            if v and c and " " not in v:
                f.setdefault(v, set()).add(c)

        for e in json.loads((DADES / "lexic_general.json").read_text(encoding="utf-8")):
            afig(e.get("valenciano"), e.get("catalan"))
        conj = json.loads((DADES / "conjugacions_dialectals.json").read_text(encoding="utf-8"))["entradas"]
        for e in conj:
            afig(e.get("valenciano"), e.get("catalan"))
            afig(e.get("infinitiu_val"), e.get("infinitiu_cat"))
        _FORMES = {v: frozenset(c) for v, c in f.items()}
    return _FORMES


def _en_original(cat: str, original: str) -> bool:
    """
    >>> _en_original("blat de moro", "Hem collit el blat de moro."), _en_original("nou", "Una nouvinguda")
    (True, False)
    """
    return re.search(rf"(?<![\w·]){re.escape(cat)}(?![\w·])", norm(original).lower()) is not None


def norm(text: str) -> str:
    return " ".join(text.replace("’", "'").replace("ʼ", "'").split())


def amplia_tros(text: str, hipotesi: str) -> str | None:
    """El tros tal com és en la traducció, a paraules senceres; None si no hi
    és (igual que en `analitza_valencia.py`).

    >>> amplia_tros("hamac", "S'ha estirat a l'hamaca.")
    'hamaca'
    """
    q = norm(text).strip().lower()
    if not q:
        return None
    hipotesi = norm(hipotesi)
    low = hipotesi.lower()
    m = re.search(rf"(?<![\w·]){re.escape(q)}(?![\w·])", low)
    if m:
        return hipotesi[m.start():m.end()]
    i = low.find(q)
    if i < 0:
        return None
    j = i + len(q)
    while i > 0 and re.match(r"[\w·]", hipotesi[i - 1]):
        i -= 1
    while j < len(hipotesi) and re.match(r"[\w·]", hipotesi[j]):
        j += 1
    return hipotesi[i:j]


def es_forma_valenciana(tros: str, hipotesi: str, original: str, formes: dict | None = None) -> bool:
    """Cada paraula del tros és l'equivalent valencià d'una paraula de l'original.

    >>> o = "La meva germana ha posat la gandula al costat de la rentadora i de la despesa."
    >>> h = "La meua germana ha posat l'hamaca al costat de la llavadora i del gasto."
    >>> [es_forma_valenciana(t, h, o) for t in ["l'hamaca", "llavadora", "meua", "la gasto", "costat", "xyz"]]
    [True, True, True, False, False, False]
    >>> es_forma_valenciana("després", "Cal presentar-la després del 15.", "Cal presentar-la abans del 15.")
    False
    """
    formes = formes_valencianes() if formes is None else formes
    a = amplia_tros(tros, hipotesi)
    if a is None:
        return False
    ps = [p for p in PARAULA_RE.findall(a.lower()) if len(p) > 1]
    return bool(ps) and all(any(_en_original(c, original) for c in formes.get(p, ())) for p in ps)


def nota(spans: list[dict]) -> float:
    return max(0.0, 100 - sum(10 if s["severity"] == "major" else 2.5 for s in spans))


def filtra(x: dict) -> dict:
    """Afig a un resultat del jutge els trossos que queden i les notes."""
    queden, fora = [], []
    for s in x["error_spans"]:
        (fora if es_forma_valenciana(s.get("text", ""), x["hipotesi"], x.get("entrada") or "") else queden).append(s)
    return {**x, "spans_queden": queden, "spans_fora": fora,
            "nota_spans": nota(x["error_spans"]), "nota_filtrada": nota(queden)}


def llig(carpeta: Path) -> dict[str, dict]:
    eix = {}
    for f in sorted(carpeta.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        eix[f.stem] = {"nom": NOMS.get(f.stem, d.get("sistema", f.stem)),
                       "frases": {x["id"]: filtra(x) for x in d["resultats"]}}
    return eix


def part(id_: str) -> str:
    return "BOE" if id_.startswith("BM-BOE-") else "AVL" if id_.startswith("BM-AVL-") else "Tot"


def mitjana(v: list[float]) -> float:
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), 2) if v else float("nan")


def parells(a: dict, b: dict, camp: str, ids: list[str]) -> tuple[int, int, int]:
    """Guanya a / empat / guanya b."""
    g = e = p = 0
    for i in ids:
        va, vb = a["frases"][i][camp], b["frases"][i][camp]
        if va is None or vb is None:
            continue
        g += va > vb
        e += va == vb
        p += va < vb
    return g, e, p


def informe(sis: dict[str, dict], titol: str) -> list[str]:
    camps = [("nota", "Nota del jutge (fase 2)"), ("nota_spans", "Nota dels trossos"),
             ("nota_filtrada", "Nota dels trossos, filtrada")]
    parts = sorted({part(i) for s in sis.values() for i in s["frases"]})
    L = [f"## {titol}", "", "| Sistema | Part | Frases | " + " | ".join(n for _, n in camps)
         + " | Trossos | Fora (formes valencianes) |", "|---|---|---|" + "---|" * (len(camps) + 2)]
    for k, s in sis.items():
        for pt in parts + (["Tot"] if len(parts) > 1 else []):
            fs = [x for i, x in s["frases"].items() if pt == "Tot" or part(i) == pt]
            tros = sum(len(x["error_spans"]) for x in fs)
            fora = sum(len(x["spans_fora"]) for x in fs)
            L.append(f"| {s['nom']} | {pt} | {len(fs)} | " + " | ".join(str(mitjana([x[c] for x in fs])) for c, _ in camps)
                     + f" | {tros} | {fora} |")
    L.append("")
    if "referencia" in sis and "copia" in sis:
        L += ["### Referència (valencià) contra la mateixa frase en català", "",
              "| Part | Nota | Guanya el valencià | Empat | Guanya el català |", "|---|---|---|---|---|"]
        for pt in parts + ["Tot"]:
            ids = [i for i in sis["referencia"]["frases"] if i in sis["copia"]["frases"] and (pt == "Tot" or part(i) == pt)]
            for c, n in camps:
                g, e, p = parells(sis["referencia"], sis["copia"], c, ids)
                L.append(f"| {pt} | {n} | {g} | {e} | {p} |")
        L.append("")
    fora = {}
    for s in sis.values():
        for x in s["frases"].values():
            for sp in x["spans_fora"]:
                t = (amplia_tros(sp["text"], x["hipotesi"]) or sp["text"]).lower()
                fora[t] = fora.get(t, 0) + 1
    L += ["Trossos descomptats més freqüents: "
          + ", ".join(f"{t} {n}" for t, n in sorted(fora.items(), key=lambda kv: -kv[1])[:40]), ""]
    return L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("carpeta", type=Path, help="Carpeta amb els JSON d'un conjunt (referencia.json, copia.json...)")
    ap.add_argument("--json", type=Path, help="Resultats frase a frase amb les notes filtrades")
    ap.add_argument("--md", type=Path, help="Informe en Markdown")
    args = ap.parse_args(argv)
    sis = llig(args.carpeta)
    L = informe(sis, f"Nota filtrada — {args.carpeta}")
    print("\n".join(L))
    if args.md:
        args.md.write_text("\n".join(L) + "\n", encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(sis, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
