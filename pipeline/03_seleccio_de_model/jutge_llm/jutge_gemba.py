"""
jutge_gemba.py -- Jutge LLM obert, NOMÉS AMB LA TRADUCCIÓ (sense origen ni
referència), sobre les traduccions cat->val del manual mescla (04/11/2026).

Per què: XCOMET-XL no veu el dialecte (vore `../comet/README.md`). En el
WMT26 (tasca d'avaluació de la qualitat, Lavie et al. 2026) els millors
avaluadors són LLM sense ajust amb el prompt GEMBA-ESA, i els oberts
(Gemma 4 31B, Qwen 3.6 35B-A3B) estan prop dels tancats. Ací es fa servir
eixe protocol en dues fases (1: trossos amb error, major/minor; 2: nota
0-100), adaptat a "només la traducció": si el jutge veu l'original català,
el "sense traduir" té avantatge per ser idèntic.

Canvis respecte del prompt del WMT26 (apèndix E), els mínims:
- No hi ha bloc d'origen ni de referència.
- Fora les categories d'"accuracy" (sense origen no es poden jutjar).
- Escala de la fase 2: punts de referència de fluïdesa en compte de
  significat (no hi ha origen amb què comparar).
- "Domain requirements" diu que el text ha de ser valencià segons la
  norma de l'AVL, igual que el WMT hi posa el registre de cada domini.

Pares contrastius: el pseudo-sistema "referencia" (el valencià revisat del
manual) i "copia" (el català tal qual) són les dues versions de cada frase;
`resum` diu en quantes el jutge prefereix el valencià.

    python jutge_gemba.py puntua --model gemma4:31b ../baseline_llm/resultats/*.json ../comet/entrades/*.json
    python jutge_gemba.py puntua --model qwen3.6:35b-a3b --limit 10 ...      # prova
    python jutge_gemba.py resum resultats/qwen3.6-35b-a3b/

Els textos repetits (mateixa traducció en diversos sistemes) es puntuen
una sola vegada: hi ha una memòria cau (`cache.jsonl`) per a poder
reprendre si el job s'acaba per temps. Primer es puntuen referència,
"sense traduir", AVLizador i motor; després la resta.

Sense dependències fora de la biblioteca estàndard (parla amb Ollama per HTTP).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SUBCONJUNTS = {"BOE": "BM-BOE-", "AVL": "BM-AVL-"}
# Ordre: primer el que fa falta per a la pregunta principal (parell contrastiu
# referència / sense traduir, i els nostres sistemes).
PRIORITAT = ["referencia", "copia", "avlizador_1.1.0", "avlizador", "motor"]
NOM_REFERENCIA = "Referencia valenciana (manual)"

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

SISTEMA = "Your task is to identify machine translation errors and assess the quality of the translation."

DOMINI = {
    "BOE": ("The text is from an official bulletin (legal and administrative language). The translation should "
            "be in Valencian, following the standard norm of the Acadèmia Valenciana de la Llengua (AVL), "
            "with a formal register."),
    "AVL": ("The text is from publications of the Acadèmia Valenciana de la Llengua (glossaries, grammar, "
            "press releases, normative agreements). The translation should be in Valencian, following the "
            "standard norm of the Acadèmia Valenciana de la Llengua (AVL)."),
}

FASE1 = """{tgt} translation:
```{hyp}```
Based on the machine translation surrounded by triple backticks (the source text is not available), identify error types in the translation and classify them. The categories of errors are: fluency (character encoding, grammar, inconsistency, punctuation, register, spelling), style (awkward), terminology (inappropriate for context, inconsistent use), non-translation, other, or no-error.
Each error is classified as one of two categories: major or minor. Major errors disrupt the flow and make the understandability of the text difficult or impossible. Minor errors are errors that do not disrupt the flow significantly, and what the text is trying to say is still understandable.
Return only the annotations in this format:
Major:
category/subcategory - "error span"
Minor:
category/subcategory - "error span"
Use one error per line and write no-error when a section is empty. Quote spans from the translation.
Domain requirements: {domini}"""

FASE2 = """Given the {tgt} machine translation and the annotated error spans, assign a score on a continuous scale from 0 to 100. The scale has the following reference points: 0="Incomprehensible", 33="Some parts understandable", 66="Mostly understandable and few grammar mistakes", up to 100="Perfect grammar and fluency".
Domain requirements: {domini}
Score the following translation:
{tgt} translation:
```{hyp}```
Annotated error spans:
```{spans}```
Respond with ONLY a valid JSON object and nothing else: {{"score": N}}
where N is an integer from 0 to 100."""


def domini_de(id_frase: str) -> str:
    return "BOE" if id_frase.startswith("BM-BOE-") else "AVL"


def clau(text: str, domini: str) -> str:
    return hashlib.sha1(f"{domini}\n{text}".encode("utf-8")).hexdigest()


def xat(url: str, model: str, usuari: str, max_tokens: int, pensa: bool) -> str:
    cos = {"model": model, "stream": False, "think": pensa,
           "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": usuari}],
           "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": 4096}}
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(cos).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]


_LINIA = re.compile(r'^\s*[-*]?\s*([\w ]+(?:/[\w -]+)?)\s*-\s*["“”\'`]?(.*?)["“”\'`]?\s*$')


def llig_spans(text: str) -> list[dict]:
    """Llig l'eixida de la fase 1.

    >>> llig_spans('Major:\\nno-error\\nMinor:\\nfluency/spelling - "aquest"\\nstyle/awkward - "fer-ho"')
    [{'severity': 'minor', 'category': 'fluency/spelling', 'text': 'aquest'}, {'severity': 'minor', 'category': 'style/awkward', 'text': 'fer-ho'}]
    """
    spans, gravetat = [], None
    for linia in text.splitlines():
        neta = linia.strip().strip("*").strip()
        baix = neta.lower().rstrip(":")
        if baix in ("major", "minor"):
            gravetat = baix
            continue
        if not neta or gravetat is None or "no-error" in baix:
            continue
        m = _LINIA.match(neta)
        if m and m.group(2):
            spans.append({"severity": gravetat, "category": m.group(1).strip().lower(), "text": m.group(2)})
    return spans


def llig_nota(text: str) -> float | None:
    """
    >>> llig_nota('{"score": 87}'), llig_nota('```json\\n{"score": 40.5}\\n```'), llig_nota('cap')
    (87.0, 40.5, None)
    """
    m = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', text)
    return float(m.group(1)) if m else None


def nota_des_de_spans(spans: list[dict]) -> float:
    """Conversió de la tasca 1 a la 2 del WMT26: 100 − 10 per major − 2,5 per minor (mínim 0)."""
    return max(0.0, 100 - sum(10 if s["severity"] == "major" else 2.5 for s in spans))


def carrega_sistemes(fitxers: list[Path], limit: int | None) -> dict[str, dict]:
    sistemes: dict[str, dict] = {}
    for f in fitxers:
        if "_limit" in f.stem:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        frases = d["resultats"][:limit] if limit else d["resultats"]
        sistemes[f.stem] = {"nom": d.get("sistema", f.stem), "frases": frases}
        if "referencia" not in sistemes:
            sistemes["referencia"] = {"nom": NOM_REFERENCIA, "frases": [
                {**fr, "hipotesi": fr["referencia"]} for fr in frases]}
    return dict(sorted(sistemes.items(), key=lambda kv: (
        PRIORITAT.index(kv[0]) if kv[0] in PRIORITAT else len(PRIORITAT), kv[0])))


def puntua(args) -> int:
    curt = args.model.replace(":", "-").replace("/", "-") + ("_pensa" if args.pensa else "")
    eixida = args.eixida / (curt + (f"_limit{args.limit}" if args.limit else ""))
    eixida.mkdir(parents=True, exist_ok=True)
    cau_f = eixida / "cache.jsonl"
    cau = {}
    if cau_f.exists():
        for linia in cau_f.read_text(encoding="utf-8").splitlines():
            if linia.strip():
                r = json.loads(linia)
                cau[r["clau"]] = r
    sistemes = carrega_sistemes(args.fitxers, args.limit)
    pendents = {}
    for s in sistemes.values():
        for fr in s["frases"]:
            k = clau(fr["hipotesi"], domini_de(fr["id"]))
            if k not in cau and k not in pendents:
                pendents[k] = (fr["hipotesi"], domini_de(fr["id"]))
    print(f"{args.model}: {len(sistemes)} sistemes, {len(cau)} textos ja puntuats, {len(pendents)} pendents",
          flush=True)

    t0 = time.time()
    with cau_f.open("a", encoding="utf-8") as fc:
        for i, (k, (text, dom)) in enumerate(pendents.items(), 1):
            try:
                crua1 = xat(args.ollama_url, args.model, FASE1.format(tgt="Valencian", hyp=text, domini=DOMINI[dom]),
                            8192 if args.pensa else 512, args.pensa)
                spans = llig_spans(crua1)
                crua2 = xat(args.ollama_url, args.model, FASE2.format(tgt="Valencian", hyp=text, domini=DOMINI[dom],
                                                                      spans=crua1.strip()), 64, False)
                fila = {"clau": k, "text": text, "domini": dom, "fase1": crua1, "spans": spans,
                        "nota": llig_nota(crua2), "fase2": crua2}
            except Exception as e:  # noqa: BLE001 -- es registra i es continua
                print(f"  ERROR en {k[:8]}: {e}", flush=True)
                continue
            fc.write(json.dumps(fila, ensure_ascii=False) + "\n")
            fc.flush()
            cau[k] = fila
            if i % 25 == 0 or i == len(pendents):
                seg = (time.time() - t0) / i
                print(f"  {i}/{len(pendents)} ({seg:.1f} s/text, queden ~{seg * (len(pendents) - i) / 60:.0f} min)",
                      flush=True)

    for clau_s, s in sistemes.items():
        files = []
        for fr in s["frases"]:
            r = cau.get(clau(fr["hipotesi"], domini_de(fr["id"])))
            if r is None:
                continue
            files.append({"id": fr["id"], "hipotesi": fr["hipotesi"], "referencia": fr["referencia"],
                          "nota": r["nota"], "nota_spans": nota_des_de_spans(r["spans"]), "error_spans": r["spans"]})
        (eixida / f"{clau_s}.json").write_text(json.dumps({
            "sistema": s["nom"], "clau": clau_s, "model": args.model, "pensa": args.pensa,
            "mode": "nomes_traduccio", "timestamp": datetime.now().isoformat(timespec="seconds"),
            "resultats": files}, ensure_ascii=False, indent=1), encoding="utf-8")
    return resum_carpeta(eixida)


def mitjana(v):
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), 2) if v else None


def resum_carpeta(carpeta: Path) -> int:
    sistemes = {}
    for f in sorted(carpeta.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sistemes[d["clau"]] = d
    if not sistemes:
        print("Cap resultat.")
        return 1
    model = next(iter(sistemes.values()))["model"]
    files = []
    for k, d in sistemes.items():
        r = d["resultats"]
        fila = {"nom": d["sistema"], "n": len(r), "nota": mitjana([x["nota"] for x in r]),
                "spans": mitjana([x["nota_spans"] for x in r]),
                "amb_error": sum(1 for x in r if x["error_spans"])}
        for sub, pref in SUBCONJUNTS.items():
            fila[sub] = mitjana([x["nota"] for x in r if x["id"].startswith(pref)])
        files.append(fila)
    files.sort(key=lambda f: -(f["nota"] or 0))
    L = [f"## {datetime.now():%d/%m/%Y %H:%M} — {model}, només la traducció (GEMBA-ESA adaptat)", "",
         "| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |",
         "|---|---|---|---|---|---|"]
    def n(x):
        return "—" if x is None else x

    for f in files:
        L.append(f"| {f['nom']} | {n(f['nota'])} | {n(f['BOE'])} | {n(f['AVL'])} | {n(f['spans'])} | "
                 f"{f['amb_error']}/{f['n']} |")
    if "referencia" in sistemes and "copia" in sistemes:
        L += ["", contrastiu(sistemes["referencia"]["resultats"], sistemes["copia"]["resultats"])]
    taula = "\n".join(L) + "\n"
    (carpeta / "resum.md").write_text(taula, encoding="utf-8")
    print("\n" + taula)
    return 0


def contrastiu(val: list[dict], cat: list[dict]) -> str:
    """Parells contrastius: la mateixa frase en valencià (referència) i en català."""
    c = {x["id"]: x for x in cat}
    L = ["### Parells contrastius: valencià (referència) / català (sense traduir)", "",
         "| Nota | Guanya el valencià | Empat | Guanya el català | Diferència mitjana (val − cat) |",
         "|---|---|---|---|---|"]
    for camp, nom in (("nota", "Fase 2"), ("nota_spans", "Des dels errors")):
        dif = [v[camp] - c[v["id"]][camp] for v in val
               if v["id"] in c and v[camp] is not None and c[v["id"]][camp] is not None]
        if dif:
            L.append(f"| {nom} | {sum(d > 0 for d in dif)} | {sum(d == 0 for d in dif)} | {sum(d < 0 for d in dif)} | "
                     f"{round(sum(dif) / len(dif), 2)} (n={len(dif)}) |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="ordre", required=True)
    p = sub.add_parser("puntua")
    p.add_argument("fitxers", nargs="+", type=Path)
    p.add_argument("--model", required=True, help="Model d'Ollama (p. ex. gemma4:31b, qwen3.6:35b-a3b).")
    p.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    p.add_argument("--pensa", action="store_true", help="Raonament activat en la fase 1 (més lent).")
    p.add_argument("--limit", type=int)
    p.add_argument("--eixida", type=Path, default=AQUI / "resultats")
    r = sub.add_parser("resum")
    r.add_argument("carpeta", type=Path)
    args = ap.parse_args(argv)
    return puntua(args) if args.ordre == "puntua" else resum_carpeta(args.carpeta)


if __name__ == "__main__":
    sys.exit(main())
