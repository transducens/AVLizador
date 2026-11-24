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

Prompt "valencia" (`--prompt valencia`, 24/11/2026; `jutge_valencia.sh`): el
jutge veu també l'original català (els nostres errors són de sentit: "cop"
-> "vegada", "calces" -> "bragues") i un bloc "Valencian norm" li diu que
tota forma acceptada per l'AVL és correcta (el prompt anterior marcava
"esta", "servicis", "seua", "siga"... com a errors d'ortografia), que les
paraules del DNV que pareixen castellanes també (gasto, exitós), que la
concordança es mira amb el nom valencià ("la despesa" -> "el gasto") i que
una paraula valenciana d'un altre sentit és un error de sentit. Les formes
catalanes que també accepta l'AVL (aquest, servei) tampoc són error: el
jutge mesura qualitat; el dialecte, el GD. Escala de la fase 2 amb
significat (la del WMT amb origen). Eixida en `resultats/valencia/` (no
trepitja la del prompt anterior).

    python jutge_gemba.py puntua --prompt valencia --model qwen3.6:35b-a3b \
        --eixida resultats/valencia/manual ../baseline_llm/resultats/copia.json ...

Sense dependències fora de la biblioteca estàndard (parla amb Ollama per HTTP).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
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
    # Frases dels benchmarks d'homògrafs i del 151 (24/11/2026)
    "GEN": ("The text is general language (news, literature, everyday topics). The translation should be in "
            "Valencian, following the standard norm of the Acadèmia Valenciana de la Llengua (AVL)."),
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

# Prompt "valencia" (24/11/2026): amb l'original i el bloc de la norma valenciana.
NORMA_VAL = """Valencian norm (read carefully before annotating):
- The translation is in Valencian, following the norm of the Acadèmia Valenciana de la Llengua (AVL: Diccionari normatiu valencià and Gramàtica normativa valenciana). Every form accepted by the AVL is correct. Do NOT mark a Valencian form as a spelling, grammar, register or terminology error, and do NOT annotate it because Central Catalan would use another form.
- Examples of correct Valencian forms: demonstratives este, esta, estos, estes, eixe, eixa, eixos, eixes; possessives meua, teua, seua, meues, teues, seues; plurals servicis, edificis (servici, edifici); verbs siga, sigues, siguen, sigut, haja, hagen, tindre, vindre, traure, extraure, tinga, vinga, isca, pense, parle; present subjunctive in -en and -a (parlen, presenten, consideren, permeta, establisca); -ix / -ixen forms (servix, servixen, patix, impedix, referix, compartixen), conéixer, aparéixer; words hui, ací, eixir, xiquet, xicotet, prompte, faena, vesprada, colp, llavadora, bresquilla, dacsa, anou, brollador; per a + infinitive (per a fer); dos with feminine nouns (les dos parts, dos vegades).
- Valencian accentuation is correct: closed é (francés, anglés, cinqué, comprén, conéixer) and participles in -és (atés, entés, emés, comprés, promés, sotmés, admés), and the AVL criteria for diacritic accents.
- Words of the AVL dictionary are correct even if they look like Spanish (gasto, exitós, exitosa, llavadora). Mark a word as a Spanish borrowing only if it is not accepted by the AVL.
- Forms shared with Central Catalan that the AVL also accepts (aquest, servei, -eix, avui) are not errors either.
- Check gender and number agreement with the noun that is actually in the translation, not with the noun of the source: when a noun changes gender (la despesa -> el gasto, el préssec -> la bresquilla), the article, determiners and adjectives must agree with the Valencian noun. A determiner or adjective that does not agree is a grammar error.
- A Valencian word with a different meaning from the source word (for example vegada "time, occasion" for cop "blow", bragues "underwear" for historical calces "hose", exitosa "successful" used as a noun for reeixida "success") is an accuracy/mistranslation error."""

FASE1_VAL = """Catalan source:
```{src}```
Valencian translation:
```{hyp}```
Based on the source segment and the machine translation surrounded by triple backticks, identify error types in the translation and classify them. The categories of errors are: accuracy (addition, mistranslation, omission), fluency (character encoding, grammar, inconsistency, punctuation, spelling), style (awkward), terminology (inappropriate for context, inconsistent use), other, or no-error.
Each error is classified as one of two categories: major or minor. Major errors disrupt the flow, change the meaning of the source or make the understandability of the text difficult or impossible. Minor errors are errors that do not disrupt the flow significantly, and what the text is trying to say is still understandable.
Return only the annotations in this format:
Major:
category/subcategory - "error span"
Minor:
category/subcategory - "error span"
Use one error per line and write no-error when a section is empty. Quote spans from the translation.
Domain requirements: {domini}
""" + NORMA_VAL

FASE2_VAL = """Given the Catalan source, the Valencian machine translation and the annotated error spans, assign a score on a continuous scale from 0 to 100. The scale has the following reference points: 0="No meaning preserved", 33="Some meaning preserved", 66="Most meaning preserved and few grammar mistakes", up to 100="Perfect meaning and grammar".
Domain requirements: {domini}
Valencian forms accepted by the AVL are correct and must not lower the score.
Score the following translation:
Catalan source:
```{src}```
Valencian translation:
```{hyp}```
Annotated error spans:
```{spans}```
Respond with ONLY a valid JSON object and nothing else: {{"score": N}}
where N is an integer from 0 to 100."""


# Empremta del prompt "valencia": entra en la clau de la memòria cau, i així
# qualsevol canvi del prompt torna a puntuar-ho tot (24/11/2026).
EMPREMTA_VAL = hashlib.sha1((SISTEMA + FASE1_VAL + FASE2_VAL).encode("utf-8")).hexdigest()[:8]


def domini_de(id_frase: str) -> str:
    """
    >>> domini_de("BM-BOE-001"), domini_de("BM-AVL-010"), domini_de("HG2-028"), domini_de("RC070")
    ('BOE', 'AVL', 'GEN', 'GEN')
    """
    if id_frase.startswith("BM-BOE-"):
        return "BOE"
    return "AVL" if id_frase.startswith("BM-AVL-") else "GEN"


def clau(text: str, domini: str, src: str = "") -> str:
    """Clau de la memòria cau. Amb el prompt "valencia" hi entra l'original
    (la mateixa traducció pot vindre de dos frases distintes); sense, la
    clau és la d'abans (les memòries cau antigues seguixen valent)."""
    return hashlib.sha1((f"{domini}\n{src}\n{text}" if src else f"{domini}\n{text}").encode("utf-8")).hexdigest()


def prompts(prompt: str, text: str, src: str, dom: str, spans: str | None = None) -> str:
    """La fase 1 (`spans` None) o la 2 del prompt triat."""
    if prompt == "valencia":
        if spans is None:
            return FASE1_VAL.format(src=src, hyp=text, domini=DOMINI[dom])
        return FASE2_VAL.format(src=src, hyp=text, domini=DOMINI[dom], spans=spans)
    if spans is None:
        return FASE1.format(tgt="Valencian", hyp=text, domini=DOMINI[dom])
    return FASE2.format(tgt="Valencian", hyp=text, domini=DOMINI[dom], spans=spans)


PENSAMENTS: dict[str, str] = {}  # últim raonament de cada crida amb `pensa` (24/11/2026)


def xat(url: str, model: str, usuari: str, max_tokens: int, pensa: bool, num_ctx: int = 4096) -> str:
    # Amb raonament, el context ha de cabre el prompt i el raonament (abans
    # 4096 fix: es tallava). Les dos fases han de dur el mateix `num_ctx`:
    # si canvia, Ollama torna a carregar el model a cada crida.
    cos = {"model": model, "stream": False, "think": pensa,
           "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": usuari}],
           "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": num_ctx}}
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(cos).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    # Reintents (24/11/2026): en caiman (RTX PRO 6000, Ollama 0.33.3) el
    # llama-server cau a vegades ("CUDA error: an illegal memory access",
    # HTTP 500) i Ollama el torna a arrancar sol.
    for intent in range(3):
        try:
            with urllib.request.urlopen(req, timeout=1200) as r:
                missatge = json.loads(r.read())["message"]
            break
        except urllib.error.HTTPError as e:
            if e.code != 500 or intent == 2:
                raise
            print(f"  HTTP 500, reintent {intent + 1} d'ací a 15 s", flush=True)
            time.sleep(15)
    PENSAMENTS["darrer"] = missatge.get("thinking") or ""
    return missatge["content"]


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
    valencia = args.prompt == "valencia"
    if args.eixida is None:
        args.eixida = AQUI / "resultats" / ("valencia" if valencia else "")
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
    def clau_de(fr: dict) -> str:
        return clau(fr["hipotesi"], domini_de(fr["id"]), f"{EMPREMTA_VAL}\n{fr['entrada']}" if valencia else "")

    pendents = {}
    for s in sistemes.values():
        for fr in s["frases"]:
            k = clau_de(fr)
            if k not in cau and k not in pendents:
                pendents[k] = (fr["hipotesi"], domini_de(fr["id"]), fr.get("entrada", ""))
    print(f"{args.model} (prompt {args.prompt}): {len(sistemes)} sistemes, {len(cau)} textos ja puntuats, "
          f"{len(pendents)} pendents", flush=True)

    ctx = 4096 + 8192 if args.pensa else 4096  # el mateix en les dos fases
    t0 = time.time()
    with cau_f.open("a", encoding="utf-8") as fc:
        for i, (k, (text, dom, src)) in enumerate(pendents.items(), 1):
            try:
                crua1 = xat(args.ollama_url, args.model, prompts(args.prompt, text, src, dom),
                            8192 if args.pensa else 512, args.pensa, ctx)
                pensament1 = PENSAMENTS.get("darrer", "") if args.pensa else ""
                spans = llig_spans(crua1)
                crua2 = xat(args.ollama_url, args.model, prompts(args.prompt, text, src, dom, crua1.strip()),
                            64, False, ctx)
                fila = {"clau": k, "text": text, "domini": dom, "fase1": crua1, "spans": spans,
                        "nota": llig_nota(crua2), "fase2": crua2}
                if valencia:
                    fila["entrada"] = src
                if pensament1:
                    fila["pensament1"] = pensament1
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
            r = cau.get(clau_de(fr))
            if r is None:
                continue
            files.append({"id": fr["id"], "entrada": fr.get("entrada"), "hipotesi": fr["hipotesi"],
                          "referencia": fr["referencia"], "nota": r["nota"],
                          "nota_spans": nota_des_de_spans(r["spans"]), "error_spans": r["spans"]})
        (eixida / f"{clau_s}.json").write_text(json.dumps({
            "sistema": s["nom"], "clau": clau_s, "model": args.model, "pensa": args.pensa,
            "mode": "amb_origen_valencia" if valencia else "nomes_traduccio",
            "empremta_prompt": EMPREMTA_VAL if valencia else None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
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
    mode = next(iter(sistemes.values())).get("mode", "nomes_traduccio")
    titol = ("amb l'original i la norma valenciana (prompt «valencia»)" if mode == "amb_origen_valencia"
             else "només la traducció (GEMBA-ESA adaptat)")
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
    L = [f"## {datetime.now():%d/%m/%Y %H:%M} — {model}, {titol}", "",
         "| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |",
         "|---|---|---|---|---|---|"]
    def n(x):
        return "—" if x is None else x

    for f in files:
        L.append(f"| {f['nom']} | {n(f['nota'])} | {n(f['BOE'])} | {n(f['AVL'])} | {n(f['spans'])} | "
                 f"{f['amb_error']}/{f['n']} |")
    if "referencia" in sistemes and "copia" in sistemes:
        L += ["", contrastiu(sistemes["referencia"]["resultats"], sistemes["copia"]["resultats"])]
    if "referencia" in sistemes:
        L += ["", contra_referencia(sistemes)]
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


def contra_referencia(sistemes: dict[str, dict]) -> str:
    """Cada sistema contra la referència, només en les frases on la seua
    traducció és distinta (24/11/2026): en els homògrafs, si el jutge veu
    els errors de sentit, la referència ha de guanyar quasi sempre.

    >>> ref = {"clau": "referencia", "sistema": "Ref", "resultats": [
    ...     {"id": "a", "hipotesi": "x", "nota": 90}, {"id": "b", "hipotesi": "y", "nota": 80}]}
    >>> sis = {"clau": "motor", "sistema": "Motor", "resultats": [
    ...     {"id": "a", "hipotesi": "x", "nota": 90}, {"id": "b", "hipotesi": "z", "nota": 40}]}
    >>> print(contra_referencia({"referencia": ref, "motor": sis}).splitlines()[-1])
    | Motor | 1 | 1 | 0 | 0 | 40.0 |
    """
    ref = {x["id"]: x for x in sistemes["referencia"]["resultats"]}
    L = ["### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)", "",
         "| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | "
         "Diferència mitjana (ref − sistema) |", "|---|---|---|---|---|---|"]
    for k, d in sistemes.items():
        if k == "referencia":
            continue
        dif = [ref[x["id"]]["nota"] - x["nota"] for x in d["resultats"]
               if x["id"] in ref and x["hipotesi"].strip() != ref[x["id"]]["hipotesi"].strip()
               and x["nota"] is not None and ref[x["id"]]["nota"] is not None]
        mitja = round(sum(dif) / len(dif), 2) if dif else "—"
        L.append(f"| {d['sistema']} | {len(dif)} | {sum(x > 0 for x in dif)} | {sum(x == 0 for x in dif)} | "
                 f"{sum(x < 0 for x in dif)} | {mitja} |")
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
    p.add_argument("--prompt", choices=["gemba", "valencia"], default="gemba",
                   help="gemba: només la traducció (04/11/2026); valencia: amb l'original i la norma valenciana.")
    p.add_argument("--eixida", type=Path, default=None,
                   help="Carpeta (per defecte resultats/, o resultats/valencia/ amb --prompt valencia).")
    r = sub.add_parser("resum")
    r.add_argument("carpeta", type=Path)
    args = ap.parse_args(argv)
    return puntua(args) if args.ordre == "puntua" else resum_carpeta(args.carpeta)


if __name__ == "__main__":
    sys.exit(main())
