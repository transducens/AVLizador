#!/usr/bin/env python3
"""Benchmark INTEGRAT: motor de regles (`traductor/`, preprocessat) +
postprocessat LLM (via B o C) sobre el benchmark REAL de 150 frases
(`03_seleccio_de_model/benchmark_corpus.json`), mesurat amb les MATEIXES
mètriques que `evalua_models.py` (BLEU/chrF/chrF++/exacte) -- no l'encert
aïllat per paraula que mesurava `compara_postprocessat.py`, sinó l'efecte
real sobre la traducció completa.

Pipeline per frase:
  1. Tokenitza i aplica les 9 regles de `RuleEngine`, EN EL MATEIX ORDE
     (replicat ací perque RuleEngine.translate() no exposa els tokens
     abans de detokenize() -- mateix patró ja usat a
     `08_traduccio_corpus/genera_muestra_test_dialectal.py`).
  2. Localitza tokens que casen amb el patro d'ambigüitat indicatiu/
     subjuntiu de 1a persona (vore identifica_ambigues.py) i que el motor
     ha deixat SENSE traduir (`is_translated=False`) -- inclou prefixos
     elidits ("s'oferisca"...).
  3. Per cada un, crida el LLM (via B o C, reutilitzant
     `compara_postprocessat.py`) i aplica la forma triada DIRECTAMENT al
     token -- NOMES si la via ha triat un dels 2 candidats coneguts; si
     B "inventa" una altra cosa, es deixa el token tal com estava (mateixa
     política conservadora de tot el projecte: fals negatiu abans que
     fals positiu).
  4. Detokenitza i calcula BLEU/chrF/chrF++/exacte contra la referència,
     IGUAL que `evalua_models.py` -- resultats comparables directament
     amb el 89/150 (59,3%) ja conegut del motor pur.

AVÍS DE RISC (pruebas puntuals, 06/10/2026, encara no en producció):
el detector del pas 2 NO distingix un verb ambigu de veres d'un
substantiu homògraf ("base", "compte"...) que l'engine ha deixat igual
PERQUE JA ERA CORRECTE -- el mateix problema de col·lisió ja documentat.
Este script force la via B/C a decidir igualment sobre eixos casos, que
podria introduir regressions noves en paraules que ja estaven bé. Es
mesura i es reporta això explícitament (vore "paraules sense veritat
coneguda" en l'eixida).

Us:
    python benchmark_integrat.py --via c --model qwen2.5:14b
    python benchmark_integrat.py --via b --model qwen3:8b --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

POSTPROC_DIR = Path(__file__).resolve().parent
# En local, l'arrel del repo esta 2 nivells amunt
# (08_traduccio_corpus/postprocessat_llm/ -> arrel). En Abaco este fitxer
# es puja sol dins d'una carpeta plana (p.ex. ~/scrapeo/postprocesado_llm/)
# que ja conte directament traductor/, 02_regles_dialectals/ i
# 03_seleccio_de_model/ -- per aixo es permet sobreescriure amb la
# variable d'entorn AVLIZADOR_ROOT (vore slurm/benchmark_integrat_multimodel.sh).
ARREL = Path(os.environ.get("AVLIZADOR_ROOT", POSTPROC_DIR.parent.parent))
sys.path.insert(0, str(ARREL))
sys.path.insert(0, str(ARREL / "03_seleccio_de_model"))
sys.path.insert(0, str(POSTPROC_DIR))

from traductor.rules import (  # noqa: E402
    aplica_amb_prefix_elidit,
    detokenize,
    marca_noms_propis,
    preserva_majuscula,
    separa_prefix_elidit,
    tokenize,
)
from traductor.rules.accentuacio import AccentuacioRule  # noqa: E402
from traductor.rules.concordanca_dos_dues import ConcordancaDosDuesRule  # noqa: E402
from traductor.rules.conjugacions_dict import ConjugacionsDictRule  # noqa: E402
from traductor.rules.demostratius import DemostratiusRule  # noqa: E402
from traductor.rules.incoatius import IncoatiusRule  # noqa: E402
from traductor.rules.lexic import LexicRule  # noqa: E402
from traductor.rules.numerals import NumeralsRule  # noqa: E402
from traductor.rules.possessius import PossessiusRule  # noqa: E402
from traductor.rules.relatiu_on import RelatiuOnRule  # noqa: E402

import compara_postprocessat as cp  # noqa: E402
from identifica_ambigues import calcula_ambiguitats  # noqa: E402

sys.path.insert(0, str(ARREL / "03_seleccio_de_model"))
from evalua_models import calcula_metriques  # noqa: E402

# Mateix orde que traductor/rules/engine.py -- NO el toquis sense tocar
# també engine.py.
REGLES = [
    LexicRule(), ConjugacionsDictRule(), PossessiusRule(), NumeralsRule(),
    ConcordancaDosDuesRule(), RelatiuOnRule(), DemostratiusRule(),
    AccentuacioRule(), IncoatiusRule(),
]

_PARAULA = re.compile(r"[a-zàèéíòóúïüç']+", re.IGNORECASE)

DEFAULT_BENCHMARK = ARREL / "03_seleccio_de_model" / "benchmark_corpus.json"
DEFAULT_OUTPUT = POSTPROC_DIR / "resultats_benchmark_integrat.json"


def tradueix_amb_tokens(text: str) -> list:
    tokens = tokenize(text)
    marca_noms_propis(tokens)
    for regla in REGLES:
        tokens = regla.apply(tokens)
    return tokens


def troba_candidats_ambigus(tokens: list, ambiguitats: dict) -> list[tuple[int, str, str | None, str | None]]:
    """Torna (index, forma, prefix, resta_original) per a tokens no
    traduïts que casen amb el patro ambigu, directament o darrere d'un
    prefix elidit."""
    candidats = []
    for i, tok in enumerate(tokens):
        if tok.is_translated or tok.is_proper_noun:
            continue
        minuscules = tok.surface.lower()
        if minuscules in ambiguitats:
            candidats.append((i, minuscules, None, None))
            continue
        pr = separa_prefix_elidit(tok.surface)
        if pr:
            prefix, resta = pr
            if resta.lower() in ambiguitats:
                candidats.append((i, resta.lower(), prefix, resta))
    return candidats


def veritat_coneguda(forma: str, ambiguitats: dict, referencia: str) -> str | None:
    """Mateixa tècnica que identifica_ambigues.py: si nomes un dels dos
    candidats apareix literalment en la referència, eixa és la "veritat".
    Si apareixen els dos o cap, no se sap (probablement substantiu)."""
    paraules_ref = {p.lower() for p in _PARAULA.findall(referencia)}
    ind = ambiguitats[forma]["indicatiu"] in paraules_ref
    sub = ambiguitats[forma]["subjuntiu"] in paraules_ref
    if ind == sub:
        return None
    return "indicatiu" if ind else "subjuntiu"


def processa_frase(reg: dict, ambiguitats: dict, guia: str, via: str, model: str, timeout: int) -> dict:
    text = reg["occidental"]
    referencia = reg["oriental"]

    tokens = tradueix_amb_tokens(text)
    hipotesi_base = detokenize(tokens)
    metriques_base = calcula_metriques(hipotesi_base, referencia)

    candidats = troba_candidats_ambigus(tokens, ambiguitats)
    info_paraules = []
    for (i, forma, prefix, resta_original) in candidats:
        veritat = veritat_coneguda(forma, ambiguitats, referencia)
        cas = {
            "texto_valenciano": text,
            "forma_ambigua": forma,
            "candidat_indicatiu": ambiguitats[forma]["indicatiu"],
            "candidat_subjuntiu": ambiguitats[forma]["subjuntiu"],
            "veritat_per_referencia": veritat,
        }
        if via == "b":
            res = cp.via_b(cas, guia, model, timeout)
            tria = res["tria"]
            forma_final = res["forma_triada"] if tria in ("indicatiu", "subjuntiu") else None
        else:
            res = cp.via_c(cas, model, timeout)
            tria = res["classe"]
            forma_final = res["forma_final"]

        encert = None if veritat is None else (tria == veritat)
        info_paraules.append({
            "forma": forma, "prefix": prefix, "veritat": veritat,
            "tria": tria, "forma_final": forma_final, "encert": encert,
            "resposta_llm": res.get("resposta"), "segons": res.get("segons"),
        })

        if forma_final is not None:
            tok = tokens[i]
            if prefix is None:
                tok.translated = preserva_majuscula(tok.surface, forma_final)
            else:
                aplica_amb_prefix_elidit(tokens, i, prefix, resta_original, forma_final)
            tok.is_translated = True
        # si forma_final es None (la via no ha triat cap dels 2 candidats
        # coneguts), el token es deixa tal qual -- fals negatiu preferible
        # a injectar una forma inventada en la traduccio final.

    hipotesi_final = detokenize(tokens)
    metriques_final = calcula_metriques(hipotesi_final, referencia)

    return {
        "id": reg.get("id"), "corpus_id": reg.get("corpus_id"),
        "texto_valenciano": text, "texto_catalan_ref": referencia,
        "hipotesis_base": hipotesi_base, "hipotesis_final": hipotesi_final,
        "metriques_base": metriques_base, "metriques_final": metriques_final,
        "paraules_ambigues": info_paraules,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--via", choices=["b", "c"], required=True)
    parser.add_argument("--model", default="qwen2.5:14b")
    parser.add_argument("--ollama-url", default=cp.OLLAMA_URL)
    parser.add_argument("--ollama-timeout", type=int, default=120)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--guia", type=Path, default=cp.GUIA_PATH)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    cp.OLLAMA_URL = args.ollama_url

    print(f"Calculant formes ambigües des de font_mauricio...")
    ambiguitats = calcula_ambiguitats()
    guia = cp.carrega_guia(args.guia)

    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    if args.limit:
        benchmark = benchmark[: args.limit]

    print(f"Processant {len(benchmark)} frases -- via {args.via.upper()}, model '{args.model}'...\n")

    t0 = time.perf_counter()
    resultats = []
    for i, reg in enumerate(benchmark, 1):
        r = processa_frase(reg, ambiguitats, guia, args.via, args.model, args.ollama_timeout)
        if r["paraules_ambigues"]:
            marques = ", ".join(
                f"{p['forma']}->{p['forma_final'] or '(sense tocar)'} "
                f"({'OK' if p['encert'] else ('FALLA' if p['encert'] is False else '?')})"
                for p in r["paraules_ambigues"]
            )
            print(f"[{i}/{len(benchmark)}] {r['id']}: {marques}")
        resultats.append(r)
    t_total = time.perf_counter() - t0

    def mitjana(clau_grup: str, clau_metrica: str) -> float:
        return sum(r[clau_grup][clau_metrica] for r in resultats) / len(resultats)

    exactes_base = sum(1 for r in resultats if r["metriques_base"]["exacte"])
    exactes_final = sum(1 for r in resultats if r["metriques_final"]["exacte"])

    tots_paraules = [p for r in resultats for p in r["paraules_ambigues"]]
    amb_veritat = [p for p in tots_paraules if p["veritat"] is not None]
    sense_veritat = [p for p in tots_paraules if p["veritat"] is None]
    encerts_paraula = sum(1 for p in amb_veritat if p["encert"])

    print("\n--- RESUM (comparable amb evalua_models.py --model traductor) ---")
    print(f"NOMES REGLES (base):     exacte {exactes_base}/{len(resultats)} "
          f"({100 * exactes_base / len(resultats):.1f}%)  "
          f"BLEU {mitjana('metriques_base', 'bleu'):.2f}  "
          f"chrF {mitjana('metriques_base', 'chrf'):.2f}")
    print(f"REGLES + POSTPROC {args.via.upper()}: exacte {exactes_final}/{len(resultats)} "
          f"({100 * exactes_final / len(resultats):.1f}%)  "
          f"BLEU {mitjana('metriques_final', 'bleu'):.2f}  "
          f"chrF {mitjana('metriques_final', 'chrf'):.2f}")
    print(f"\nParaules ambigües trobades: {len(tots_paraules)} en {sum(1 for r in resultats if r['paraules_ambigues'])} frases")
    print(f"  Amb veritat coneguda (confirmable per la referència): {len(amb_veritat)} "
          f"-- encerts: {encerts_paraula}/{len(amb_veritat)}")
    print(f"  SENSE veritat coneguda (probable substantiu homògraf, risc de fals positiu): {len(sense_veritat)}")
    for p in sense_veritat:
        print(f"    {p['forma']!r} -> {p['tria']} -> {p['forma_final'] or '(sense tocar)'}")
    print(f"\nTemps total: {t_total:.1f}s ({t_total / len(resultats):.2f}s/frase de mitjana, "
          f"incloent frases sense cap paraula ambigua -- eixes no criden Ollama)")

    args.output.write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardat: {args.output}")


if __name__ == "__main__":
    main()
