"""
analitza_valencia.py -- anàlisi dels resultats del jutge amb el prompt
«valencia» (25/11/2026).

No puntua res: llig els JSON de `resultats/valencia/<conjunt>/<model>/` i,
per comparar, els del prompt del 04/11 (`resultats/qwen3.6-35b-a3b/`).

1. Trossos amb error que cauen en una forma valenciana o catalana (marcadors
   del GD de la frase), per sistema; i el mateix amb el prompt del 04/11.
2. Categories dels errors (accuracy / fluency...), BOE i AVL per separat.
3. Errors de sentit: en les frases on un sistema és distint de la
   referència, si el jutge marca alguna de les paraules que canvien
   («detecta») i qui guanya.
4. Detall frase a frase (`analisi_detall.md`): on guanya la referència i
   on guanya el sistema, amb els trossos marcats.

    python analitza_valencia.py
    python analitza_valencia.py --model qwen3.6-35b-a3b_pensa
    python analitza_valencia.py --prompt valencia2
"""

from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DIR_VAL = AQUI / "resultats" / "valencia"
DIR_VELL = AQUI / "resultats" / "qwen3.6-35b-a3b"
CONJUNTS = ["manual", "homografs", "homografs_v2"]
NOMS = {"referencia": "Referència", "copia": "Sense traduir", "avlizador": "AVLizador 2.0.1",
        "avlizador_2.0.0": "AVLizador 2.0.0", "motor": "Motor sol", "ollama_gemma3-12b": "gemma3:12b"}
PARAULA_RE = re.compile(r"[\w·]+", re.UNICODE)
LLETRA_RE = re.compile(r"[\w·]", re.UNICODE)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def norm(text: str) -> str:
    return " ".join(text.replace("’", "'").replace("ʼ", "'").split())


def paraules(text: str) -> set[str]:
    """
    >>> sorted(paraules("D'esta manera, l'Estat"))
    ['d', 'esta', 'estat', 'l', 'manera']
    """
    return set(PARAULA_RE.findall(norm(text).lower()))


def amplia_tros(text: str, hipotesi: str) -> str | None:
    """El tros tal com és en la traducció, estés a paraules senceres; None si
    no hi és (de vegades el jutge hi posa raonament). Com en
    `desglossament_frases/desglossa_frases.py`.

    >>> amplia_tros("bra", "La brama dels llauradors")
    'brama'
    >>> amplia_tros("res", "Així, d'oferir") is None
    True
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
    while i > 0 and LLETRA_RE.match(hipotesi[i - 1]):
        i -= 1
    while j < len(hipotesi) and LLETRA_RE.match(hipotesi[j]):
        j += 1
    return hipotesi[i:j]


def canvis(sistema: str, referencia: str) -> tuple[set[str], list[str]]:
    """Paraules del sistema que no són en la referència (alineades) i els
    canvis «ref→sistema».

    >>> p, c = canvis("Una vegada acabada", "Un colp acabat")
    >>> sorted(p), c
    (['acabada', 'una', 'vegada'], ['Un colp acabat→Una vegada acabada'])
    """
    ts, tr = norm(sistema).split(), norm(referencia).split()
    noves, eix = set(), []
    for tag, r1, r2, s1, s2 in difflib.SequenceMatcher(None, tr, ts, autojunk=False).get_opcodes():
        if tag != "equal":
            noves |= paraules(" ".join(ts[s1:s2]))
            eix.append(f"{' '.join(tr[r1:r2]) or '∅'}→{' '.join(ts[s1:s2]) or '∅'}")
    return noves, eix


def clau_canvi(cv: list[str]) -> str:
    """Canvis sense majúscules, puntuació ni determinants/contraccions, per
    agrupar («Una vegada→Un cop» i «una vegada→un cop» van junts).

    >>> clau_canvi(["Una vegada→Un cop", "d'un brollador→d'una deu"])
    'vegada→cop; brollador→deu'
    """
    buides = {"un", "una", "uns", "unes", "el", "la", "els", "les", "l", "d", "al", "a", "de", "del"}
    eix = []
    for c in cv:
        a, b = c.split("→")
        a = " ".join(p for p in PARAULA_RE.findall(a.lower()) if p not in buides)
        b = " ".join(p for p in PARAULA_RE.findall(b.lower()) if p not in buides)
        eix.append(f"{a or '∅'}→{b or '∅'}")
    return "; ".join(eix)


def llig(carpeta: Path) -> dict[str, dict[str, dict]]:
    eix = {}
    for f in sorted(carpeta.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        eix[f.stem] = {x["id"]: x for x in d["resultats"]}
    return eix


def subconjunt(id_: str) -> str:
    return "BOE" if id_.startswith("BM-BOE-") else "AVL" if id_.startswith("BM-AVL-") else "—"


_GD = {}


def marcadors(text: str) -> tuple[set[str], set[str]]:
    from avlizador.grau_dialectal.gd import calcula_gd
    if text not in _GD:
        g = calcula_gd(text)
        _GD[text] = ({m.lower() for m in g["marcadors_occidentals"]},
                     {m.lower() for m in g["marcadors_orientals"]})
    return _GD[text]


def classifica(spans: list[dict], hipotesi: str) -> list[tuple[str, dict, str | None]]:
    val, cat = marcadors(hipotesi)
    eix = []
    for s in spans:
        a = amplia_tros(s.get("text", ""), hipotesi)
        if a is None:
            c = "no_trobat"
        else:
            p = paraules(a)
            c = "val" if p & val else "cat" if p & cat else "neutra"
        eix.append((c, s, a))
    return eix


def taula_trossos(dades: dict[str, dict[str, dict]], titol: str) -> list[str]:
    L = [f"#### {titol}", "",
         "| Sistema | Trossos | En forma valenciana | En forma catalana | Neutres | No són en la frase | Formes valencianes més marcades |",
         "|---|---|---|---|---|---|---|"]
    for sis, files in dades.items():
        comp = collections.Counter()
        formes = collections.Counter()
        for x in files.values():
            for c, s, a in classifica(x["error_spans"], x["hipotesi"]):
                comp[c] += 1
                if c == "val":
                    val, _ = marcadors(x["hipotesi"])
                    for p in paraules(a) & val:
                        formes[p] += 1
        tot = sum(comp.values())
        pct = (lambda n: f"{n} ({100 * n / tot:.0f} %)") if tot else str
        top = ", ".join(f"{p} {n}" for p, n in formes.most_common(12))
        L.append(f"| {NOMS.get(sis, sis)} | {tot} | {pct(comp['val'])} | {pct(comp['cat'])} | "
                 f"{pct(comp['neutra'])} | {pct(comp['no_trobat'])} | {top} |")
    return L + [""]


def taula_categories(dades: dict[str, dict[str, dict]]) -> list[str]:
    cats = ["accuracy", "fluency", "style", "terminology", "altres"]
    L = ["| Sistema | Part | Frases | " + " | ".join(cats) + " | Majors |",
         "|---|---|---|" + "---|" * (len(cats) + 1)]
    for sis, files in dades.items():
        parts = sorted({subconjunt(i) for i in files})
        for part in parts:
            n, comp, majors = 0, collections.Counter(), 0
            for id_, x in files.items():
                if subconjunt(id_) != part:
                    continue
                n += 1
                for s in x["error_spans"]:
                    c = s["category"].split("/")[0]
                    comp[c if c in cats else "altres"] += 1
                    majors += s["severity"] == "major"
            L.append(f"| {NOMS.get(sis, sis)} | {part} | {n} | " + " | ".join(str(comp[c]) for c in cats)
                     + f" | {majors} |")
    return L + [""]


def sentit(dades: dict[str, dict[str, dict]], conjunt: str, detall: list[str]) -> list[str]:
    ref = dades["referencia"]
    per_canvi: dict[str, collections.Counter] = {}
    L = ["| Sistema | Frases distintes | Marca alguna paraula canviada | Guanya la ref. | Empat | Guanya el sistema |",
         "|---|---|---|---|---|---|"]
    for sis, files in dades.items():
        if sis == "referencia":
            continue
        n = detecta = gr = emp = gs = 0
        exemples = {"ref": [], "sis": [], "emp": []}
        for id_, x in files.items():
            r = ref.get(id_)
            if r is None or norm(x["hipotesi"]) == norm(r["hipotesi"]):
                continue
            n += 1
            noves, cv = canvis(x["hipotesi"], r["hipotesi"])
            trossos = classifica(x["error_spans"], x["hipotesi"])
            toca = [a for _, _, a in trossos if a and paraules(a) & noves]
            detecta += bool(toca)
            d = r["nota"] - x["nota"]
            if d > 0:
                gr += 1
                exemples["ref"].append((d, id_, x, r, cv))
            elif d < 0:
                gs += 1
                exemples["sis"].append((d, id_, x, r, cv))
            else:
                emp += 1
                exemples["emp"].append((d, id_, x, r, cv))
        L.append(f"| {NOMS.get(sis, sis)} | {n} | {detecta} | {gr} | {emp} | {gs} |")
        per_canvi[sis] = collections.Counter()
        for qui, ex in (("ref", exemples["ref"]), ("sis", exemples["sis"]), ("emp", exemples["emp"])):
            for _, _, _, _, cv in ex:
                per_canvi[sis][(clau_canvi(cv), qui)] += 1
        for qui, titol in (("ref", "guanya la referència"), ("sis", "guanya el sistema")):
            ex = sorted(exemples[qui], key=lambda t: -abs(t[0]))
            if not ex:
                continue
            detall += [f"### {conjunt}: {NOMS.get(sis, sis)}, {titol} ({len(ex)})", ""]
            for d, id_, x, r, cv in ex:
                detall.append(f"- **{id_}** ref {r['nota']:g} / sistema {x['nota']:g}; canvis: "
                              + "; ".join(f"`{c}`" for c in cv[:6]))
                for etiqueta, y in (("sistema", x), ("ref.", r)):
                    if y["error_spans"]:
                        detall.append(f"  - errors ({etiqueta}): " + "; ".join(
                            f"{s['severity']} {s['category']} «{s['text']}»" for s in y["error_spans"]))
            detall.append("")
    L.append("")
    if conjunt.startswith("homografs"):
        L += ["Per canvi (referència → sistema; quantes frases guanya la referència / empat / el sistema):", "",
              "| Sistema | Canvi | Guanya la ref. | Empat | Guanya el sistema |", "|---|---|---|---|---|"]
        for sis, comp in per_canvi.items():
            claus = sorted({k for k, _ in comp}, key=lambda k: (-sum(comp[(k, q)] for q in ("ref", "emp", "sis")), k))
            for k in claus:
                L.append(f"| {NOMS.get(sis, sis)} | {k} | {comp[(k, 'ref')]} | {comp[(k, 'emp')]} | {comp[(k, 'sis')]} |")
        L.append("")
    return L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3.6-35b-a3b_pensa")
    ap.add_argument("--prompt", default="valencia", help="valencia o valencia2 (carpeta de resultats/).")
    ap.add_argument("--eixida", type=Path, default=None, help="Per defecte, resultats/<prompt>/.")
    args = ap.parse_args(argv)
    dir_prompt = AQUI / "resultats" / args.prompt
    args.eixida = args.eixida or dir_prompt

    L = [f"# Jutge «{args.prompt}»: anàlisi ({args.model})", ""]
    detall = [f"# Jutge «{args.prompt}»: detall frase a frase ({args.model})", ""]
    for conjunt in CONJUNTS:
        carpeta = dir_prompt / conjunt / args.model
        if not carpeta.exists():
            continue
        dades = llig(carpeta)
        dades = dict(sorted(dades.items(), key=lambda kv: kv[0] != "referencia"))
        print(f"{conjunt}: {', '.join(f'{k} {len(v)}' for k, v in dades.items())}", file=sys.stderr)
        L += [f"## {conjunt}", "", "### Trossos amb error", ""]
        L += taula_trossos(dades, "Prompt «valencia»")
        if conjunt == "manual" and DIR_VELL.exists():
            vell = {k: v for k, v in llig(DIR_VELL).items()
                    if k in ("referencia", "copia", "avlizador_2.0.0", "ollama_gemma3-12b")}
            L += taula_trossos(vell, "Prompt del 04/11 (sense original), mateixes frases")
        L += ["### Categories dels errors", ""] + taula_categories(dades)
        L += ["### Frases distintes de la referència", "",
              "«Marca alguna paraula canviada» = algun tros amb error del sistema toca una paraula que no és "
              "en la referència. Detall en `analisi_detall.md`.", ""]
        L += sentit(dades, conjunt, detall)
    args.eixida.mkdir(parents=True, exist_ok=True)
    (args.eixida / "analisi.md").write_text("\n".join(L), encoding="utf-8")
    (args.eixida / "analisi_detall.md").write_text("\n".join(detall), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
