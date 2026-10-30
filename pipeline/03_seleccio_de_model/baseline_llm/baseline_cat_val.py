"""
baseline_cat_val.py -- Baseline cat->val (30/10/2026): el nostre sistema
(motor + FLOR-760M) davant de LLM generalistes TAL QUAL i d'Apertium, en el
benchmark manual mescla (458 frases; BOE 246 + AVL 212).

Apertium no té cap parell català -> valencià: va via castellà (cat-spa i
spa-cat_valencia, decisió de l'usuari del 30/10/2026), amb dos traduccions
senceres, així que no és una comparació directa amb un conversor dialectal.

Decisió de l'usuari (30/10/2026): els LLM s'usen sense ajustar-los res,
amb una instrucció mínima i igual per a tots (INSTRUCCIO, sense exemples,
sense regles, sense glossari; temperatura 0). Cada sistema traduïx la
mescla UNA vegada; les taules del BOE i de l'AVL ixen de les mateixes
traduccions, separant per l'id (BM-BOE-*, BM-AVL-*).

Postprocessat mínim, igual per a tots els LLM (`neteja_resposta`): es lleven
els espais, les línies de presentació que acaben en ":" ("Ací tens la
traducció:"), una etiqueta "Traducció:" al principi, les cometes o els
asteriscos que emboliquen tota la resposta, i es queda la primera línia no
buida (l'entrada és sempre una sola frase). La resposta crua es guarda en
`hipotesi_crua`, i `netejada` diu si s'ha tocat.

A més de les mètriques de sempre (exactes, BLEU, chrF, chrF++, TER, WER),
el GDV de l'eixida (`avlizador.grau_dialectal`): si un sistema torna català
o una mescla, el GDV ho mostra encara que el BLEU siga alt.

Ús (des de l'arrel del repo, amb el paquet instal·lat: `pip install -e ".[ml,avaluacio]"`):
    python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema avlizador
    python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema motor
    python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema ollama:qwen2.5:7b --limit 10
    python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema apertium --apertium-mode apy
    python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py resum

En Abaco, els LLM es llancen amb `slurm/baseline_llm_cat_val.sh` (1 GPU per
model, com a molt 2 alhora). Resultats (en git): `resultats/` al costat
d'este script; `resum` escriu `resum_baseline.md` amb les tres taules.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from avlizador.avaluacio.avalua import avalua_benchmark, resumeix, troba_dir_benchmarks
from avlizador.grau_dialectal.gd import carrega_formes_dialectals
from avlizador.grau_dialectal.gdv import calcula_gdv

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

DIR = Path(__file__).resolve().parent
RESULTATS = DIR / "resultats"
BENCHMARK = "manual/benchmark_manual_cat_val.json"
SUBCONJUNTS = {  # clau -> (descripció, prefix de l'id; None = totes)
    "manual":     ("Manual mezcla BOE + AVL (458)", None),
    "manual_boe": ("Manual BOE (246)", "BM-BOE-"),
    "manual_avl": ("Manual AVL (212)", "BM-AVL-"),
}

INSTRUCCIO = ("Traduïx el text següent del català al valencià. "
              "Respon només amb la traducció.\n\n{text}")

OLLAMA_URL = "http://127.0.0.1:11434"
APERTIUM_PARELLS = "cat-spa,spa-cat_valencia"  # no hi ha cat-cat_valencia: via castellà
APERTIUM_APY = "https://www.apertium.org/apy/translate"
MAX_FALLADES_SEGUIDES = 5

_ETIQUETA = re.compile(r"^\s*(\*\*)?\s*(traducci[oó]|traduccio|resposta)\s*(\*\*)?\s*:\s*", re.IGNORECASE)
_EMBOLCALL = [('"', '"'), ("«", "»"), ("“", "”"), ("'", "'"), ("**", "**"), ("*", "*")]


def neteja_resposta(text: str) -> str:
    """Postprocessat mínim d'una resposta de LLM (igual per a tots).

    >>> neteja_resposta("  Este xic.  ")
    'Este xic.'
    >>> neteja_resposta("Ací tens la traducció:\\n\\n«Este xic.»\\n\\nHe canviat aquest per este.")
    'Este xic.'
    >>> neteja_resposta("Traducció: Este xic.")
    'Este xic.'
    >>> neteja_resposta("")
    ''
    """
    linies = [l.strip() for l in text.strip().splitlines() if l.strip()]
    while len(linies) > 1 and linies[0].endswith(":"):
        linies.pop(0)
    if not linies:
        return ""
    frase = _ETIQUETA.sub("", linies[0]).strip()
    for obri, tanca in _EMBOLCALL:
        if len(frase) > len(obri) + len(tanca) and frase.startswith(obri) and frase.endswith(tanca):
            frase = frase[len(obri):-len(tanca)].strip()
            break
    return frase


def traductor_ollama(model: str, url: str, timeout: int):
    """Funció de traducció amb un model d'Ollama i la INSTRUCCIO mínima.
    Torna (hipotesi_neta, hipotesi_crua); llança una excepció si Ollama
    no respon després de 3 intents (la frase compta com a error)."""
    def tradueix(text: str) -> tuple[str, str]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": INSTRUCCIO.format(text=text)}],
            "stream": False,
            "think": False,  # sense açò, gemma4/qwen3 gasten els tokens raonant i tornen buit
            "options": {"temperature": 0, "num_predict": 512},
        }
        for intent in range(3):
            try:
                r = requests.post(f"{url}/api/chat", json=payload, timeout=timeout)
                r.raise_for_status()
                crua = r.json()["message"]["content"]
                return neteja_resposta(crua), crua
            except requests.exceptions.RequestException:
                if intent == 2:
                    raise
                time.sleep(5)
    return tradueix


def traductor_apertium(mode: str, parells: list[str]):
    """Apertium encadenant `parells` (per defecte cat-spa i spa-cat_valencia:
    Apertium no té cap parell català -> valencià, 30/10/2026): `local`
    (ordre `apertium`, sense marcar les desconegudes) o `apy` (l'API
    pública d'apertium.org: envia les frases a un servei extern)."""
    if mode == "local":
        if not shutil.which("apertium"):
            raise SystemExit("ERROR: no es troba l'ordre `apertium` (o usa --apertium-mode apy).")

        def un_pas(text: str, parell: str) -> str:
            r = subprocess.run(["apertium", "-u", parell], input=text, capture_output=True,
                               text=True, encoding="utf-8", check=True)
            return r.stdout.strip()
    else:
        def un_pas(text: str, parell: str) -> str:
            for intent in range(3):
                try:
                    r = requests.get(APERTIUM_APY, timeout=60, params={
                        "langpair": parell.replace("-", "|", 1), "q": text, "markUnknown": "no"})
                    r.raise_for_status()
                    time.sleep(0.2)  # sense saturar el servei públic
                    return r.json()["responseData"]["translatedText"].strip()
                except requests.exceptions.RequestException:
                    if intent == 2:
                        raise
                    time.sleep(5)

    fallades_seguides = [0]

    def tradueix(text: str) -> tuple[str, str]:
        passos = []
        try:
            for parell in parells:
                text = un_pas(text, parell)
                passos.append(text)
        except Exception:
            fallades_seguides[0] += 1
            if fallades_seguides[0] >= MAX_FALLADES_SEGUIDES:  # el servei no va: no seguim
                raise SystemExit(f"ERROR: {MAX_FALLADES_SEGUIDES} frases seguides sense resposta "
                                 "d'Apertium; s'atura sense guardar resultats.")
            raise
        fallades_seguides[0] = 0
        return text, " ||| ".join(passos)  # crua = cada pas (el castellà intermedi inclòs)
    return tradueix


def sistema(nom: str, args) -> tuple[str, str, callable, dict]:
    """(clau per al fitxer, nom per a la taula, funció -> (neta, crua), paràmetres)."""
    if nom == "avlizador":
        from avlizador.traductor_cat_val import translate_cat_val
        return "avlizador", "AVLizador: motor + FLOR-760M", lambda t: (translate_cat_val(t),) * 2, {}
    if nom == "motor":
        from avlizador.traductor_cat_val import translate_cat_val_motor
        return "motor", "AVLizador: motor solo", lambda t: (translate_cat_val_motor(t),) * 2, {}
    if nom == "apertium":
        parells = args.apertium_parells.split(",")
        cadena = " → ".join([parells[0].split("-")[0]] + [p.split("-", 1)[1] for p in parells])
        return ("apertium", f"Apertium vía castellano ({cadena})",
                traductor_apertium(args.apertium_mode, parells),
                {"mode": args.apertium_mode, "parells": parells})
    if nom.startswith("ollama:"):
        model = nom.split(":", 1)[1]
        clau = "ollama_" + re.sub(r"[^A-Za-z0-9.]+", "-", model)
        return (clau, model, traductor_ollama(model, args.ollama_url, args.ollama_timeout),
                {"instruccio": INSTRUCCIO, "temperature": 0, "num_predict": 512, "think": False})
    raise SystemExit(f"ERROR: sistema desconegut: {nom} (avlizador, motor, apertium, ollama:MODEL)")


def afig_gdv(resultats: list[dict], formes) -> None:
    for r in resultats:
        g = calcula_gdv(r["hipotesi"], formes)
        r["gdv"] = g["gdv"]
        r["gdv_orientals"], r["gdv_paraules"] = g["total_orientals"], g["total_paraules"]


def gdv_global(resultats: list[dict]) -> float:
    paraules = sum(r["gdv_paraules"] for r in resultats)
    return round(1 - sum(r["gdv_orientals"] for r in resultats) / paraules, 4) if paraules else 1.0


def ordre_tradueix(args) -> int:
    dir_bench = troba_dir_benchmarks()
    if dir_bench is None:
        print("ERROR: no es troba dades/benchmarks/.", file=sys.stderr)
        return 1
    benchmark = json.loads((dir_bench / BENCHMARK).read_text(encoding="utf-8"))
    if args.limit:
        benchmark = benchmark[:args.limit]
    clau, nom, funcio, params = sistema(args.sistema, args)

    crues = {}
    def nomes_neta(text: str) -> str:
        neta, crua = funcio(text)
        crues[text] = crua
        return neta

    print(f"{nom}: {len(benchmark)} frases", file=sys.stderr)
    inici = time.time()
    r = avalua_benchmark(nomes_neta, benchmark)
    segons = round(time.time() - inici, 1)
    resultats = r["resultats"]
    for x in resultats:
        x["hipotesi_crua"] = crues.get(x["entrada"], x["hipotesi"])
        x["netejada"] = x["hipotesi_crua"].strip() != x["hipotesi"]
    afig_gdv(resultats, carrega_formes_dialectals())

    subconjunts = {}
    for sub, (descripcio, prefix) in SUBCONJUNTS.items():
        tria = [x for x in resultats if prefix is None or x["id"].startswith(prefix)]
        subconjunts[sub] = {"descripcio": descripcio, **resumeix(tria), "gdv_global": gdv_global(tria),
                            "netejades": sum(x["netejada"] for x in tria)}

    RESULTATS.mkdir(parents=True, exist_ok=True)
    sufix = f"_limit{args.limit}" if args.limit else ""
    eixida = RESULTATS / f"{clau}{sufix}.json"
    eixida.write_text(json.dumps({
        "sistema": nom, "clau": clau, "parametres": params, "benchmark": BENCHMARK,
        "limit": args.limit, "timestamp": datetime.now().isoformat(timespec="seconds"),
        "segons": segons, "segons_per_frase": round(segons / len(resultats), 2),
        "subconjunts": subconjunts, "resultats": resultats,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    s = subconjunts["manual"]
    print(f"\n{nom}: {s['exactes']}/{s['n_frases']} exactes, BLEU {s['bleu_mitja']}, "
          f"TER {s['ter_corpus']}, GDV {s['gdv_global']}, errors {s['errors']}, "
          f"netejades {s['netejades']}, {segons} s\nGuardat: {eixida}")
    return 0


def _n(x, dec=2) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def ordre_resum(args) -> int:
    fitxers = sorted(p for p in RESULTATS.glob("*.json") if "_limit" not in p.stem)
    if not fitxers:
        print(f"No hi ha resultats en {RESULTATS}", file=sys.stderr)
        return 1
    dades = [json.loads(p.read_text(encoding="utf-8")) for p in fitxers]
    linies = [
        "# Baseline cat→val: resultados",
        "",
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} (`baseline_cat_val.py resum`). "
        "Instrucción de los LLM (la misma para todos, temperatura 0):",
        "",
        "> " + INSTRUCCIO.replace("\n\n", " ").replace("{text}", "«frase»"),
        "",
        "Ordenado por TER (más bajo = mejor). GDV = Grau Dialectal Valencià de la salida "
        "(1 = ninguna forma catalana). Limpiadas = respuestas tocadas por el postprocesado mínimo.",
    ]
    for sub, (descripcio, _) in SUBCONJUNTS.items():
        files = sorted(dades, key=lambda d: d["subconjunts"][sub]["ter_corpus"])
        linies += ["", f"## {descripcio}", "",
                   "| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GDV | Errores | Limpiadas | s/frase |",
                   "|---|---|---|---|---|---|---|---|---|---|---|"]
        for d in files:
            s = d["subconjunts"][sub]
            exactes = f"{s['exactes']}/{s['n_frases']} ({_n(s['exactes_pct'], 1)} %)"
            linies.append(
                f"| {d['sistema']} | {exactes} | {_n(s['bleu_mitja'])} | {_n(s['chrf_mitja'])} | "
                f"{_n(s['chrf_pp_mitja'])} | {_n(s['ter_corpus'])} | {_n(s['wer_corpus'])} | "
                f"{_n(s['gdv_global'], 4)} | {s['errors']} | {s['netejades']} | {_n(d['segons_per_frase'])} |")
    linies += ["", "Ficheros: " + ", ".join(f"`{p.name}`" for p in fitxers)]
    eixida = DIR / "resum_baseline.md"
    eixida.write_text("\n".join(linies) + "\n", encoding="utf-8")
    print("\n".join(linies))
    print(f"\nGuardat: {eixida}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="ordre", required=True)
    t = sub.add_parser("tradueix", help="Traduïx la mescla amb un sistema i en guarda les mètriques.")
    t.add_argument("--sistema", required=True, help="avlizador, motor, apertium o ollama:MODEL")
    t.add_argument("--limit", type=int, help="Només les N primeres frases (prova; no entra al resum).")
    t.add_argument("--ollama-url", default=OLLAMA_URL)
    t.add_argument("--ollama-timeout", type=int, default=300)
    t.add_argument("--apertium-mode", choices=["local", "apy"], default="local")
    t.add_argument("--apertium-parells", default=APERTIUM_PARELLS,
                   help="Parells d'Apertium encadenats, separats per comes.")
    sub.add_parser("resum", help="Combina els resultats en resum_baseline.md.")
    args = parser.parse_args(argv)
    return ordre_tradueix(args) if args.ordre == "tradueix" else ordre_resum(args)


if __name__ == "__main__":
    sys.exit(main())
