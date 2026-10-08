#!/usr/bin/env python3
"""Compara 3 vies de postprocessat amb LLM per a l'ambiguitat present
indicatiu/subjuntiu de 1a persona (p.ex. valencia "plantege" -> catala
"plantejo" indicatiu / "plantegi" subjuntiu), sobre la mostra generada
per `identifica_ambigues.py`.

NOMES s'etiqueta este cas concret (decisio explicita 06/10/2026) -- la
resta de formes "problematica" de conjugacions_dialectals.json (locucions
fixes, col·lisions homografes amb substantius...) no es toquen ací.

Les 3 vies (vore conversa per a la comparativa completa):
  A. El LLM tradueix la FRASE SENCERA (generacio oberta, el mes arriscat:
     pot "corregir" parts que el motor de regles ja tenia be).
  B. El LLM dona NOMES la forma catalana de la paraula marcada, amb el
     context de la frase (generacio mes acotada, pero encara oberta --
     pot inventar una forma que no estiga als nostres candidats).
  C. El LLM NOMES classifica si la paraula funciona com a indicatiu o
     subjuntiu en eixe context (classificacio binaria); la substitucio
     final ve d'una taula ja coneguda (candidat_indicatiu/candidat_subjuntiu),
     no del LLM -- el LLM mai "inventa" la forma final.

System prompt: s'usa el contingut de
`02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md` (demanat
explicitament). IMPORTANT -- eixa guia NO cobrix cap regla de mode verbal
(nomes determinants, pronoms, preposicions, adverbis): es dona com a
context general de registre/convencions, pero el criteri real
d'indicatiu/subjuntiu (present en subordinada amb "que", verbs de voluntat/
necessitat/dubte, etc.) s'afig ací explicitament perque la guia no ho
proporciona.

Model: qwen2.5:14b via Ollama local (ja instal·lat i en us en la resta
del projecte, vore 03_seleccio_de_model/evalua_models.py).

Us:
    python compara_postprocessat.py
    python compara_postprocessat.py --model qwen2.5:7b --limit 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
# Copia local de 02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md
# (mateixa carpeta que este script) -- NO es llig del repo complet perque
# este script es pensat per a pujar-se sol a un clúster (p.ex. Abaco, vore
# README) que no té la resta de l'estructura del projecte. Si el .md
# original canvia, cal tornar a copiar-lo a ma (es un fitxer pràcticament
# estàtic, no justifica un mecanisme de sincronització com sync_data.py).
GUIA_PATH = SCRIPT_DIR / "guia_traduccio_dialectal.md"
MOSTRA_PATH = SCRIPT_DIR / "mostra_casos_ambigues.json"
SALIDA_PATH = SCRIPT_DIR / "resultats_comparativa_ABC.json"

OLLAMA_URL = "http://localhost:11434"

# Activat des de benchmark_integrat.py amb --debug (07/10/2026): quan es
# True, crida_ollama() imprimix el prompt EXACTE que es manda a Ollama i
# la resposta crua, sencers, abans de cap parseig -- per a poder traure
# una traça completa al .out de SLURM i vore paraula per paraula com es
# decidix cada cas, sense haver d'adivinar que hi ha "per dins".
VERBOSE = False


def _imprimix_crida(system: str, prompt: str, model: str) -> None:
    print("\n" + "=" * 100)
    print(f"[OLLAMA] model={model!r}")
    print("-" * 100)
    print("SYSTEM PROMPT (el que fixa el comportament, no canvia entre frases):")
    print(system)
    print("-" * 100)
    print("USER PROMPT (la frase + la paraula marcada d'esta crida concreta):")
    print(prompt)
    print("-" * 100, flush=True)


def _imprimix_resposta(resposta: str, segons: float) -> None:
    print(f"RESPOSTA CRUA D'OLLAMA (abans de cap parseig, {segons:.2f}s): {resposta!r}")
    print("=" * 100 + "\n", flush=True)

CRITERI_MODE_VERBAL = """
CRITERI PER A DECIDIR INDICATIU VS. SUBJUNTIU (la guia de dialectologia no
cobrix mode verbal, nomes determinants/pronoms/preposicions -- este criteri
es general, no ve d'eixe document):
- SUBJUNTIU si la paraula va en una oracio subordinada introduïda per "que"
  depenent d'un verb de voluntat, necessitat, dubte, sentiment o valoracio
  ("vull que", "cal que", "és necessari que", "sempre que", "a fi que"), o
  darrere de "perquè" amb valor final, o en frases de relatiu amb valor
  hipotetic/indefinit ("qualsevol que...", "el que siga que...").
- INDICATIU si expressa un fet asseverat (en qualsevol persona, singular
  o plural), normalment en oracio principal o subordinada completiva
  sense eixe matís de voluntat/dubte ("jo declare que...", "per la
  present jo autorize...", "els experts creuen que...", "molts pares
  poden quedar...").
ATENCIO -- NO confongues la paraula marcada en el verb de la SEUA PROPIA
subordinada: en "jo em centre en que el partit isca bé", la paraula
marcada ("centre") es el verb PRINCIPAL, que asseverA un fet ("centrar-se
en" = fixar l'atencio en), encara que vaja seguit de "que" i encara que el
verb DINS d'eixa subordinada ("isca") siga, ell si, subjuntiu de veres.
Verbs assertius/factuals seguits de "en que"/"que" com "centrar-se en
que", "basar-se en que", "fixar-se en que", "constatar que" son INDICATIU
encara que hi haja un "que" immediatament darrere -- NO es el mateix
patro que "vull que" (ahi el verb marcat seria "vull", no el verb de la
subordinada). Mira SEMPRE si la paraula marcada es la que GOVERNA el
"que" (verb principal, asseveratiu -> INDICATIU) o la que ve DESPRES del
"que" depenent d'un verb de voluntat/dubte/valoracio (-> SUBJUNTIU).
ATENCIO -- frases de relatiu REALS (amb antecedent concret, conegut,
existent) son INDICATIU, encara que hi haja un "que" de relatiu: "els
alumnes que opten a estudiar-hi" (uns alumnes reals i concrets que, de
fet, trien aixo -> opten, INDICATIU), "les persones que creuen aixo"
(persones reals que, de fet, ho creuen -> creuen, INDICATIU). Son
SUBJUNTIU NOMES les frases de relatiu HIPOTETIQUES o INDEFINIDES, on
l'antecedent NO es cap persona/cosa concreta coneguda sino "qualsevol
que complisca la condicio" ("qualsevol que vinga", "el primer que
arribe", "no hi ha ningu que ho sapia"). La prova: si pots substituir
"que" per "qui de fet" o afegir "en concret" sense que la frase perda
sentit (p.ex. "els alumnes que, en concret, opten..."), es relatiu REAL
-> INDICATIU; si nomes te sentit amb "siga qui siga" o "qualsevol que",
es relatiu HIPOTETIC -> SUBJUNTIU.
"""


def carrega_guia(path: Path = GUIA_PATH) -> str:
    return path.read_text(encoding="utf-8")


def crida_ollama(system: str, prompt: str, model: str, timeout: int = 120) -> str:
    if VERBOSE:
        _imprimix_crida(system, prompt, model)
    t0 = time.perf_counter()
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 300},
    }
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        # nota: OLLAMA_URL es global i es fixa a main() segons --ollama-url
        r.raise_for_status()
        resposta = r.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        resposta = "ERROR: no es pot connectar amb Ollama"
    except Exception as e:  # noqa: BLE001
        resposta = f"ERROR: {e}"
    if VERBOSE:
        _imprimix_resposta(resposta, time.perf_counter() - t0)
    return resposta


_PARAULA = re.compile(r"[a-zàèéíòóúïüç']+", re.IGNORECASE)


def conte_paraula(text: str, paraula: str) -> bool:
    return paraula.lower() in {p.lower() for p in _PARAULA.findall(text)}


def via_a(cas: dict, guia: str, model: str, timeout: int) -> dict:
    system = (
        f"Ets un expert en dialectologia valenciana/catalana. Guia de referencia:\n\n{guia}\n\n"
        f"{CRITERI_MODE_VERBAL}\n"
        "Tradueix la frase seguent del valencia (norma AVL/GVA) al catala "
        "oriental (norma IEC), aplicant la guia de dalt quan calga. Retorna "
        "NOMES la frase traduida, sense cap nota ni explicacio."
    )
    resposta = crida_ollama(system, cas["texto_valenciano"], model, timeout)
    toca_indicatiu = conte_paraula(resposta, cas["candidat_indicatiu"])
    toca_subjuntiu = conte_paraula(resposta, cas["candidat_subjuntiu"])
    if toca_subjuntiu and not toca_indicatiu:
        tria = "subjuntiu"
    elif toca_indicatiu and not toca_subjuntiu:
        tria = "indicatiu"
    else:
        tria = "cap/ambigu"
    return {"resposta": resposta, "tria": tria, "encert": tria == cas["veritat_per_referencia"]}


def _encert(tria: str, veritat: str | None, indicatiu_es_forma_sense_canviar: bool = False) -> bool:
    """La paraula marcada pot ser de veres un substantiu/preposicio homograf
    (vore 06/10/2026: "base", "entre", "poble"... existixen a les dades com
    a formes "problematica" d'un verb rar, pero en la practica son MOLT mes
    freqüents amb un atra categoria gramatical -- la mateixa paraula es a
    voltes el verb de veres i a voltes no, NO hi ha cap llista que ho
    distingisca). Quan `veritat` es None (la referencia no confirma cap
    dels 2 candidats, senyal de que probablement no era este verb), la
    resposta CORRECTA es "cap" -- no es pot comparar amb cap candidat.

    `indicatiu_es_forma_sense_canviar` (afegit 08/10/2026 -- vore
    "Col·lisio INDICATIU/SUBJUNTIU en 3a plural" a conjugacions_dict.py):
    per a la 3a plural, el candidat indicatiu ES la mateixa forma
    valenciana sense canviar -- exactament el mateix text que produiria
    "cap" (no tocar res). Les dos respostes son INDISTINGIBLES pel text
    final, aixina que quan `veritat == "indicatiu"` i este flag es cert,
    s'accepten LES DOS com a encert (nomes "subjuntiu" seria un error de
    veres ahí). Sense este flag (1a persona, on indicatiu/subjuntiu/cap
    son 3 cadenes distintes), es manté el criteri estricte d'abans.
    """
    if veritat is None:
        return tria == "cap"
    if veritat == "indicatiu" and indicatiu_es_forma_sense_canviar:
        return tria in ("indicatiu", "cap")
    return tria == veritat


def _es_indistingible_de_cap(cas: dict) -> bool:
    """Torna True si `cas["candidat_indicatiu"]` es la mateixa paraula
    valenciana sense canviar (patro de la 3a plural) -- vore docstring
    de `_encert`."""
    return cas["candidat_indicatiu"].lower() == cas["forma_ambigua"].lower()


def via_b(cas: dict, guia: str, model: str, timeout: int) -> dict:
    system = (
        f"Ets un expert en dialectologia valenciana/catalana. Guia de referencia:\n\n{guia}\n\n"
        f"{CRITERI_MODE_VERBAL}\n"
        "Se't dona una frase en valencia i una paraula marcada d'eixa frase "
        "que, segons les dades, POT ser una forma verbal ambigua: en "
        "valencia la mateixa forma escrita pot servir tant per a un mode "
        "d'indicatiu (present o pretèrit perfet simple) com per al "
        "corresponent de subjuntiu (present o imperfet), en qualsevol "
        "persona (singular o plural) d'un verb rar. ATENCIO: la mateixa "
        "forma sovint es en realitat un "
        "substantiu, preposicio o un atra categoria gramatical NO "
        "relacionada amb eixe verb (p.ex. \"base\", \"entre\", \"poble\") --"
        " mira el context amb cura abans de decidir.\n"
        "- Si la paraula marcada SI funciona com este verb en este context, "
        "digues NOMES la forma catalana oriental correcta EN EIXE CONTEXT.\n"
        "- Si la paraula marcada NO funciona com este verb ahi (es un "
        "substantiu, preposicio, etc.), respon EXACTAMENT: CAP\n"
        "Respon amb UNA SOLA PARAULA, sense puntuacio ni explicacions."
    )
    prompt = f'Frase: "{cas["texto_valenciano"]}"\n\nParaula marcada: {cas["forma_ambigua"]}'
    resposta = crida_ollama(system, prompt, model, timeout)
    forma = _PARAULA.findall(resposta.lower())
    forma = forma[0] if forma else resposta.strip().lower()
    if forma == "cap":
        tria = "cap"
        forma = None
    elif forma == cas["candidat_subjuntiu"].lower():
        tria = "subjuntiu"
    elif forma == cas["candidat_indicatiu"].lower():
        tria = "indicatiu"
    else:
        tria = f"altra forma inventada: {forma!r}"
    indistingible = _es_indistingible_de_cap(cas)
    if VERBOSE:
        print(f"[PARSEIG via_b] resposta_crua={resposta!r} -> paraula_extreta={forma!r} "
              f"(candidat_indicatiu={cas['candidat_indicatiu']!r}, candidat_subjuntiu={cas['candidat_subjuntiu']!r}) "
              f"-> tria={tria!r} -> encert={_encert(tria, cas['veritat_per_referencia'], indistingible)}", flush=True)
    return {"resposta": resposta, "forma_triada": forma, "tria": tria,
            "encert": _encert(tria, cas["veritat_per_referencia"], indistingible)}


def via_c(cas: dict, model: str, timeout: int) -> dict:
    # A proposit SENSE la guia sencera (no fa falta per a classificar mode
    # verbal) -- nomes el criteri explicit, perque es una tasca mes acotada.
    system = (
        "Ets un expert en gramatica catalana/valenciana. "
        f"{CRITERI_MODE_VERBAL}\n"
        "Se't dona una frase en valencia i una paraula marcada que, segons "
        "les dades, POT ser una forma verbal ambigua entre un mode "
        "d'indicatiu (present o pretèrit perfet simple) i el corresponent "
        "de subjuntiu (present o imperfet), en qualsevol persona (singular "
        "o plural) d'un verb rar. ATENCIO: la mateixa forma sovint es en realitat un substantiu, "
        "preposicio o un atra categoria gramatical NO relacionada amb eixe "
        "verb (p.ex. \"base\", \"entre\", \"poble\") -- mira el context amb "
        "cura. Classifica EIXA PARAULA EN EIXE CONTEXT concret:\n"
        "- 'indicatiu' si ahi funciona com un mode d'indicatiu del verb "
        "(present o pretèrit perfet simple -- expressa un fet asseverat).\n"
        "- 'subjuntiu' si ahi funciona com el corresponent de subjuntiu "
        "(present o imperfet -- voluntat, dubte, concessio...).\n"
        "- 'cap' si la paraula marcada NO es en absolut este verb ahi (es "
        "un substantiu, preposicio, una atra categoria gramatical sense "
        "relacio -- NO triga 'cap' nomes perque has descartat subjuntiu; "
        "si es este verb pero en mode indicatiu, la resposta es "
        "'indicatiu', mai 'cap').\n"
        "Respon amb UNA SOLA PARAULA: 'indicatiu', 'subjuntiu' o 'cap'. "
        "Sense cap explicacio ni raonament, nomes la paraula."
    )
    prompt = f'Frase: "{cas["texto_valenciano"]}"\n\nParaula marcada: {cas["forma_ambigua"]}'
    resposta = crida_ollama(system, prompt, model, timeout)
    resposta_neta = resposta.strip().lower()
    # Prioritat 1: la PRIMERA paraula de la resposta (cas normal, i cas
    # 08/10/2026 trobat: el model a voltes explica el raonament encara
    # que se li diga que no ho faça -- eixa explicacio pot mencionar les
    # 3 etiquetes alhora, p.ex. "'cap'... no es pot classificar com a
    # subjuntiu...", que confonia el metode antic de "quines etiquetes
    # apareixen a tot el text").
    m = re.match(r"^[^a-zàèéíòóúïüç]*([a-zàèéíòóúïüç]+)", resposta_neta)
    primera = m.group(1) if m else ""
    trobades: set[str] | None = None
    if primera in ("indicatiu", "subjuntiu", "cap"):
        classe = primera
    else:
        trobades = {p for p in ("indicatiu", "subjuntiu", "cap") if p in resposta_neta}
        if trobades == {"subjuntiu"}:
            classe = "subjuntiu"
        elif trobades == {"indicatiu"}:
            classe = "indicatiu"
        elif trobades == {"cap"}:
            classe = "cap"
        else:
            classe = f"resposta ambigua: {resposta_neta!r}"
    forma_final = cas["candidat_subjuntiu"] if classe == "subjuntiu" else (
        cas["candidat_indicatiu"] if classe == "indicatiu" else None
    )
    indistingible = _es_indistingible_de_cap(cas)
    if VERBOSE:
        print(f"[PARSEIG via_c] resposta_crua={resposta!r} -> net={resposta_neta!r} -> "
              f"primera_paraula={primera!r} paraules_clau_trobades={trobades!r} -> classe={classe!r} -> "
              f"forma_final={forma_final!r} (candidat_indicatiu={cas['candidat_indicatiu']!r}, "
              f"candidat_subjuntiu={cas['candidat_subjuntiu']!r}) -> "
              f"encert={_encert(classe, cas['veritat_per_referencia'], indistingible)}", flush=True)
    return {"resposta": resposta, "classe": classe, "forma_final": forma_final,
            "encert": _encert(classe, cas["veritat_per_referencia"], indistingible)}


def main() -> None:
    global OLLAMA_URL
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="qwen2.5:14b")
    parser.add_argument("--limit", type=int, default=None, help="Nomes les primeres N frases de la mostra")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help="Per a instancies remotes (p.ex. node SLURM)")
    parser.add_argument("--ollama-timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, default=SALIDA_PATH)
    parser.add_argument("--mostra-path", type=Path, default=MOSTRA_PATH)
    parser.add_argument("--guia", type=Path, default=GUIA_PATH)
    args = parser.parse_args()
    OLLAMA_URL = args.ollama_url

    if not args.mostra_path.exists():
        raise SystemExit(f"No existeix {args.mostra_path}; executa primer identifica_ambigues.py "
                          f"(en un entorn que tinga el corpus del BOE) i copia el .json ací")

    mostra = json.loads(args.mostra_path.read_text(encoding="utf-8"))
    if args.limit:
        mostra = mostra[: args.limit]
    guia = carrega_guia(args.guia)

    print(f"Provant {len(mostra)} frases amb model '{args.model}' via {OLLAMA_URL} (3 crides Ollama per frase)...\n")
    resultats = []
    encerts = {"A": 0, "B": 0, "C": 0}
    temps = {"A": [], "B": [], "C": []}
    t_inici_total = time.perf_counter()
    for i, cas in enumerate(mostra, 1):
        print(f"[{i}/{len(mostra)}] {cas['forma_ambigua']!r} "
              f"(veritat: {cas['veritat_per_referencia']}) -- {cas['texto_valenciano'][:70]}...")

        t0 = time.perf_counter()
        res_a = via_a(cas, guia, args.model, args.ollama_timeout)
        t1 = time.perf_counter()
        res_b = via_b(cas, guia, args.model, args.ollama_timeout)
        t2 = time.perf_counter()
        res_c = via_c(cas, args.model, args.ollama_timeout)
        t3 = time.perf_counter()
        res_a["segons"] = round(t1 - t0, 2)
        res_b["segons"] = round(t2 - t1, 2)
        res_c["segons"] = round(t3 - t2, 2)
        temps["A"].append(res_a["segons"])
        temps["B"].append(res_b["segons"])
        temps["C"].append(res_c["segons"])

        for clau, res in (("A", res_a), ("B", res_b), ("C", res_c)):
            marca = "OK" if res["encert"] else "FALLA"
            print(f"    {clau}: {marca} ({res.get('tria') or res.get('classe')}) -- {res['segons']}s")
            if res["encert"]:
                encerts[clau] += 1
        resultats.append({**cas, "via_a": res_a, "via_b": res_b, "via_c": res_c})

    t_total = time.perf_counter() - t_inici_total

    print("\n--- RESUM ---")
    for clau in ("A", "B", "C"):
        mitjana = sum(temps[clau]) / len(temps[clau])
        print(f"  Via {clau}: {encerts[clau]}/{len(mostra)} ({100 * encerts[clau] / len(mostra):.1f}%) "
              f"-- {mitjana:.1f}s/frase de mitjana")
    print(f"  Temps total ({len(mostra)} frases x 3 vies = {3 * len(mostra)} crides Ollama): "
          f"{t_total:.1f}s ({t_total / len(mostra):.1f}s/frase)")

    args.output.write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardat: {args.output}")


if __name__ == "__main__":
    main()
