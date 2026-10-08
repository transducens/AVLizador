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

FILTRE POS AMB SPACY (07/10/2026, activat per defecte): abans de cridar
el LLM, es comprova amb `ca_core_news_sm` si la paraula marcada funciona
com a VERB en eixa frase. Si NO ho es (NOUN/ADP/ADJ...), es decideix
"cap" SENSE cridar el LLM -- provat sobre els 28 casos reals del
benchmark: 27/28 correctes nomes amb este filtre, 0 falsos positius
sobre substantius (vore conversa 07/10/2026). Nomes els casos que spaCy
confirma com a VERB arriben a la via B/C -- aço estalvia la majoria de
crides Ollama i reduix el risc, encara que no l'elimina del tot (si
spaCy diu VERB per error, la via C encara pot dir "cap" com a segona
xarxa de seguretat). Desactiva amb --no-pos-filter per a comparar.

Us:
    python benchmark_integrat.py --via c --model qwen2.5:14b
    python benchmark_integrat.py --via b --model qwen3:8b --limit 20
    python benchmark_integrat.py --via c --model qwen3:8b --no-pos-filter   # sense filtre, per comparar
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
from traductor.rules import pos_tagger as _pos_tagger_motor  # noqa: E402
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

_NLP_CA = None  # carregat de manera peresosa -- vore carrega_spacy()


def carrega_spacy():
    """Carrega el pipeline de spaCy en catala (ca_core_news_sm) una sola
    vegada. Torna None si spaCy o el model no estan instal·lats -- en eixe
    cas el filtre POS simplement es desactiva (tot va a la via B/C, mateix
    comportament que abans del 07/10/2026)."""
    global _NLP_CA
    if _NLP_CA is not None:
        return _NLP_CA
    try:
        import spacy
        _NLP_CA = spacy.load("ca_core_news_sm")
    except Exception as e:  # noqa: BLE001
        print(f"AVIS: no s'ha pogut carregar spaCy/ca_core_news_sm ({e}) -- filtre POS desactivat.")
        _NLP_CA = False
    return _NLP_CA


def pos_de_paraula(doc, forma: str) -> str | None:
    """Cerca `forma` (comparacio insensible a majuscules) entre els tokens
    del document de spaCy i torna la seua etiqueta POS universal, o None
    si no s'ha trobat (p.ex. diferencies de tokenitzacio)."""
    for tok in doc:
        if tok.text.lower() == forma.lower():
            return tok.pos_
    return None


def tradueix_amb_tokens(text: str) -> list:
    tokens = tokenize(text)
    marca_noms_propis(tokens)
    # Mateixa capa 0 que `RuleEngine.translate()` (vore engine.py,
    # 07/10/2026) -- sense esta crida, `ConjugacionsDictRule` mai veu
    # `tok.pos` omplit ací (encara que reutilitze la mateixa classe real),
    # i el filtre homograf nou (persones/pobles/projectes/plomes/pares/
    # visites...) es queda silenciosament inactiu en este benchmark, tot
    # i estar actiu de veres en `traductor.translate()`.
    _pos_tagger_motor.etiqueta(tokens)
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
    Si apareixen els dos o cap, no se sap (probablement substantiu).

    Bug real trobat i corregit (08/10/2026): la paraula de referència
    sovint du un prefix elidit pegat ("s'hagin", "s'emmarquen"), i
    `_PARAULA` tracta l'apòstrof com a part del token -- "s'hagin" mai
    coincidia amb el candidat solt "hagin", aixina que `veritat_coneguda`
    tornava `None` (semblava "cap") encara que el candidat SI aparega,
    nomes que amb un prefix davant. Això disparava `REGRESSIO` falsos al
    informe per a casos que en realitat ja eren correctes (p.ex.
    "hagen"->"hagin" en RC094, "esforcen" en RC069, "emmarquen" en RC086
    -- els 3 duien prefix elidit a la referència). Ara es busca TAMBÉ la
    forma sense el prefix.
    """
    paraules_ref: set[str] = set()
    for p in _PARAULA.findall(referencia):
        pl = p.lower()
        paraules_ref.add(pl)
        prefix_resta = separa_prefix_elidit(pl)
        if prefix_resta is not None:
            paraules_ref.add(prefix_resta[1])
    ind = ambiguitats[forma]["indicatiu"].lower() in paraules_ref
    sub = ambiguitats[forma]["subjuntiu"].lower() in paraules_ref
    if ind == sub:
        return None
    return "indicatiu" if ind else "subjuntiu"


def processa_frase(
    reg: dict, ambiguitats: dict, guia: str, via: str, model: str, timeout: int,
    pos_filter: bool = True,
) -> dict:
    text = reg["occidental"]
    referencia = reg["oriental"]

    tokens = tradueix_amb_tokens(text)
    hipotesi_base = detokenize(tokens)
    metriques_base = calcula_metriques(hipotesi_base, referencia)

    candidats = troba_candidats_ambigus(tokens, ambiguitats)

    # El pipeline de spaCy es relativament car -- NOMES es crida si de
    # veres hi ha candidats en esta frase, i UNA vegada per frase (no per
    # candidat), reutilitzant el mateix `doc` per a tots.
    doc_spacy = None
    nlp = carrega_spacy() if (pos_filter and candidats) else None
    if nlp:
        doc_spacy = nlp(text)

    info_paraules = []
    for (i, forma, prefix, resta_original) in candidats:
        veritat = veritat_coneguda(forma, ambiguitats, referencia)
        pos = pos_de_paraula(doc_spacy, forma) if doc_spacy is not None else None

        if cp.VERBOSE:
            print(f"\n### FRASE {reg.get('id', '?')!r} -- paraula ambigua {forma!r} "
                  f"(indicatiu={ambiguitats[forma]['indicatiu']!r}, subjuntiu={ambiguitats[forma]['subjuntiu']!r}, "
                  f"veritat_per_referencia={veritat!r}) ###")
            print(f"[FILTRE POS] spaCy etiqueta {forma!r} com a: {pos!r} "
                  f"({'NO es VERB/AUX -> es decidix cap SENSE cridar el LLM' if pos is not None and pos not in ('VERB', 'AUX') else 'es VERB/AUX (o spaCy no disponible/no trobat) -> es crida la via ' + via.upper()})",
                  flush=True)

        if pos is not None and pos not in ("VERB", "AUX"):
            # Filtre POS: spaCy diu que ací NO funciona com el verb ambigu
            # (NOUN/ADP/ADJ...) -- es decidix "cap" SENSE cridar el LLM.
            # "AUX" compta com a verb (mateix criteri que ConjugacionsDictRule
            # al motor -- "poden"/"puguen" sovint s'etiqueten AUX quan van
            # davant d'un infinitiu, "puguen fer", i son el verb ambigu de
            # veres, 08/10/2026).
            tria = "cap"
            forma_final = None
            resposta_llm = None
            segons = 0.0
            indistingible = ambiguitats[forma]["indicatiu"].lower() == forma.lower()
            encert = cp._encert(tria, veritat, indistingible)
        else:
            # O no hi ha filtre POS, o spaCy diu que SI es VERB (o no l'ha
            # trobat al document) -- es crida la via B/C com fins ara.
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
            resposta_llm = res.get("resposta")
            segons = res.get("segons")
            encert = res["encert"]

        # "encert" ja te en compte el cas "cap" (vore _encert en
        # compara_postprocessat.py): si veritat es None (probable
        # substantiu homograf) i la via ha triat "cap", es considera
        # ENCERT -- no una resposta "sense veritat coneguda".
        info_paraules.append({
            "forma": forma, "prefix": prefix, "veritat": veritat,
            "tria": tria, "forma_final": forma_final, "encert": encert,
            "resposta_llm": resposta_llm, "segons": segons,
            "pos_spacy": pos, "filtrat_per_pos": pos is not None and pos not in ("VERB", "AUX"),
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
    parser.add_argument("--ids", default=None,
                         help="Nomes proba estos id's concrets del benchmark, separats per comes "
                              "(p.ex. --ids RC151 o --ids RC106,RC110,RC151) -- ignora --limit si es dona")
    parser.add_argument("--pos-filter", dest="pos_filter", action="store_true", default=True,
                         help="Filtra amb spaCy abans de cridar el LLM (per defecte activat)")
    parser.add_argument("--no-pos-filter", dest="pos_filter", action="store_false",
                         help="Desactiva el filtre POS -- tot va a la via B/C, com abans del 07/10/2026")
    parser.add_argument("--debug", action="store_true",
                         help="Log super complet: imprimix el prompt EXACTE enviat a Ollama, la "
                              "resposta crua i com es parseja cada crida (compara_postprocessat.VERBOSE)")
    args = parser.parse_args()
    cp.OLLAMA_URL = args.ollama_url
    cp.VERBOSE = args.debug

    print(f"Calculant formes ambigües des de font_mauricio...")
    ambiguitats = calcula_ambiguitats()
    guia = cp.carrega_guia(args.guia)
    if args.pos_filter:
        if carrega_spacy():
            print("Filtre POS amb spaCy (ca_core_news_sm): ACTIVAT")
        else:
            print("Filtre POS demanat pero spaCy no disponible -- continua sense filtre")
    else:
        print("Filtre POS: DESACTIVAT (--no-pos-filter)")

    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    if args.ids:
        ids_triats = {i.strip() for i in args.ids.split(",") if i.strip()}
        benchmark = [r for r in benchmark if r.get("id") in ids_triats]
        trobats = {r["id"] for r in benchmark}
        faltants = ids_triats - trobats
        if faltants:
            print(f"AVIS: no s'han trobat estos id's en {args.benchmark.name}: {sorted(faltants)}")
    elif args.limit:
        benchmark = benchmark[: args.limit]

    print(f"Processant {len(benchmark)} frases -- via {args.via.upper()}, model '{args.model}'...\n")

    t0 = time.perf_counter()
    resultats = []
    for i, reg in enumerate(benchmark, 1):
        r = processa_frase(reg, ambiguitats, guia, args.via, args.model, args.ollama_timeout, args.pos_filter)
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
    encerts_paraula = sum(1 for p in tots_paraules if p["encert"])
    encerts_amb_veritat = sum(1 for p in amb_veritat if p["encert"])
    encerts_sense_veritat = sum(1 for p in sense_veritat if p["encert"])

    print("\n--- RESUM (comparable amb evalua_models.py --model traductor) ---")
    print(f"NOMES REGLES (base):     exacte {exactes_base}/{len(resultats)} "
          f"({100 * exactes_base / len(resultats):.1f}%)  "
          f"BLEU {mitjana('metriques_base', 'bleu'):.2f}  "
          f"chrF {mitjana('metriques_base', 'chrf'):.2f}")
    print(f"REGLES + POSTPROC {args.via.upper()}: exacte {exactes_final}/{len(resultats)} "
          f"({100 * exactes_final / len(resultats):.1f}%)  "
          f"BLEU {mitjana('metriques_final', 'bleu'):.2f}  "
          f"chrF {mitjana('metriques_final', 'chrf'):.2f}")
    print(f"\nParaules ambigües trobades: {len(tots_paraules)} en {sum(1 for r in resultats if r['paraules_ambigues'])} frases"
          f" -- encert global: {encerts_paraula}/{len(tots_paraules)}")
    print(f"  Verb de veres (confirmable per la referència): {len(amb_veritat)} "
          f"-- encerts: {encerts_amb_veritat}/{len(amb_veritat)}")
    print(f"  Probable substantiu/preposició homògraf (la resposta correcta es 'cap'): "
          f"{len(sense_veritat)} -- encerts: {encerts_sense_veritat}/{len(sense_veritat)}")
    for p in sense_veritat:
        if not p["encert"]:
            print(f"    REGRESSIO: {p['forma']!r} -> {p['tria']} -> {p['forma_final'] or '(sense tocar)'}")

    filtrades = sum(1 for p in tots_paraules if p["filtrat_per_pos"])
    if args.pos_filter:
        print(f"\nFiltre POS: {filtrades}/{len(tots_paraules)} paraules resoltes SENSE cridar el LLM "
              f"(spaCy ha dit que no eren el verb) -- {len(tots_paraules) - filtrades} crides Ollama reals fetes.")
    print(f"\nTemps total: {t_total:.1f}s ({t_total / len(resultats):.2f}s/frase de mitjana, "
          f"incloent frases sense cap paraula ambigua -- eixes no criden Ollama)")

    args.output.write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardat: {args.output}")


if __name__ == "__main__":
    main()
