#!/usr/bin/env python3
"""genera_corpus_sintetico.py — Corpus paral·lel sintètic valencià → català.

Parteix del corpus ja depurat i verificat com a valencià pur
(``dades/avl/final/dialectal/corpus_occidental_net.jsonl``, generat per
``estudi_dialectal.py``) i genera, frase a frase, la seua traducció al
català oriental amb el model que millor va puntuar al benchmark de
``03_seleccio_de_model/evalua_models.py`` (qwen2.5:14b, BLEU 84.52 / chrF 92.34 /
chrF++ 91.84).

Reutilitza D'EVALUA_MODELS.PY, sense duplicar-los, el system prompt, el
glossari dinàmic per frase i la crida a Ollama — és exactament la
configuració que va donar eixos resultats al benchmark.

ÚS:
    # Prova ràpida (10 frases, per comprovar que Ollama respon bé)
    python genera_corpus_sintetico.py --limit 10 --verbose

    # Mostra aleatòria de 500 frases (per avaluar qualitat abans del run llarg)
    python genera_corpus_sintetico.py --sample 500

    # Generació completa (reanudable: Ctrl+C i tornar a llançar continua on ho va deixar)
    python genera_corpus_sintetico.py

    # Només regenerar els fitxers nets d'exportació a partir del que ja hi ha
    python genera_corpus_sintetico.py --nomes-exporta

    # Repartir el corpus en 8 fragments (p.ex. per a 8 GPUs a la vegada) —
    # cada execució tradueix només el seu fragment, a un Ollama diferent:
    python genera_corpus_sintetico.py --num-shards 8 --shard-id 0 --ollama-url http://localhost:11434
    python genera_corpus_sintetico.py --num-shards 8 --shard-id 1 --ollama-url http://localhost:11435
    ...
    # I, quan tots els fragments han acabat, fusionar-los:
    python genera_corpus_sintetico.py --merge-shards 8

SORTIDA (dins de dades/sintetico/):
    corpus_sintetic_val_cat.jsonl   Fitxer principal: totes les parelles amb
                                     metadades i marques de qualitat. Es va
                                     escrivint frase a frase (append + flush),
                                     per això el procés és reanudable.
    parallel_val_cat.jsonl          Exportació neta {"val", "cat"} sense les
                                     parelles marcades com a sospitoses — llest
                                     per a entrenar/afinar un model de traducció.
    parallel.val / parallel.cat     El mateix, en dos fitxers de text alineats
                                     línia a línia (format Moses/OPUS habitual).
    generacio.log                   Log complet amb timestamp.
    informe_generacio.txt           Resum final (docs coberts, frases per
                                     tipus de document, sospitoses, temps...).
    corpus_sintetic_val_cat.shardN.jsonl   Amb --num-shards > 1, cada fragment
                                     escriu ací en lloc del fitxer principal;
                                     --merge-shards els combina en un de sol.

Per a executar-ho amb GPU (local, clúster SLURM o Colab), veure slurm/README.md
i colab/README.md. slurm/generar_corpus_paralelo.sh ja automatitza el
repartiment en fragments per a aprofitar diverses GPUs a la vegada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # sinteticos/
ROOT_DIR = BASE_DIR.parent                          # scrapeo/
EVALUA_DIR = ROOT_DIR / "03_seleccio_de_model"

sys.path.insert(0, str(EVALUA_DIR))
import evalua_models as em  # noqa: E402  (reutilitza system prompt + glossari + Ollama)
import requests  # noqa: E402  (ja instal·lat per evalua_models.instala_si_cal())

# El benchmark d'evalua_models.py es fa amb frases curtes soltes, sense noms
# d'institucions. En aplicar el mateix prompt a text real de l'AVL es va
# detectar que el model "tradueix" sigles d'institucions (AVL -> IEC), un
# error factual, no dialectal. S'afig una regla extra NOMÉS per a aquest
# script, sense tocar el prompt ja validat al benchmark d'evalua_models.py.
SYSTEM_PROMPT_CORPUS = em.SYSTEM_PROMPT_BASE + """

11. SIGLES D'INSTITUCIONS I NOMS PROPIS
   No tradueixis ni substituïsques MAI sigles d'institucions encara que
   tinguen un equivalent en català oriental: AVL, GVA, GNV, GVB, RACV...
   es queden EXACTAMENT igual (per exemple, "AVL" mai es converteix en
   "IEC"). Tampoc tradueixis noms de persona ni topònims.
   Molt important: fes-ho només quan la sigla JA APAREGA a la frase
   original. Si l'original diu "l'Acadèmia" o "la institució" (sense
   sigla), la traducció ha de mantindre "l'Acadèmia" o "la institució" —
   MAI la substituïsques per "AVL" ni per cap altra sigla que no estiguera
   ja escrita a l'original."""

ENTITATS_PROTEGIDES = ["AVL", "GVA", "GNV", "GVB", "RACV"]


def tradueix(frase: str, model: str, timeout: int) -> str:
    """Com evalua_models.tradueix_ollama(), però amb SYSTEM_PROMPT_CORPUS
    (protegeix sigles d'institucions) en lloc del system prompt del benchmark."""
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT_CORPUS,
        "prompt": em.construeix_prompt_usuari(frase),
        "stream": False,
        # "think": false -- vore evalua_models.tradueix_ollama() per al
        # motiu: sense açò, un model amb "extended thinking" (p.ex. gemma4)
        # gasta tot el "num_predict" raonant i el camp "response" torna buit.
        "think": False,
        "options": {"temperature": 0, "num_predict": 200},
    }
    try:
        r = requests.post(f"{em.OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: no es pot connectar amb Ollama (està engegat 'ollama serve'?)"
    except Exception as e:
        return f"ERROR: {e}"


DEFAULT_INPUT = ROOT_DIR / "dades" / "avl" / "final" / "dialectal" / "corpus_occidental_net.jsonl"

# Bug real trobat en organitzar el projecte: fins ara estes constants
# apuntaven a BASE_DIR (la carpeta del propi script), pero el corpus ja
# generat sempre s'havia guardat/mogut a ma a un subdirectori "generado/"
# (vore repara_corpus.py, que SI ja esperava eixe subdirectori) -- amb la
# reorganitzacio en carpeta dades/, ara totes dos coincidixen de veritat:
# tot el corpus sintetic (input i output) viu a dades/sintetico/.
GENERAT_DIR   = ROOT_DIR / "dades" / "sintetico"
OUTPUT_PATH   = GENERAT_DIR / "corpus_sintetic_val_cat.jsonl"
PARALLEL_JSONL = GENERAT_DIR / "parallel_val_cat.jsonl"
PARALLEL_VAL  = GENERAT_DIR / "parallel.val"
PARALLEL_CAT  = GENERAT_DIR / "parallel.cat"
LOG_PATH      = GENERAT_DIR / "generacio.log"
INFORME_PATH  = GENERAT_DIR / "informe_generacio.txt"

DEFAULT_MODEL = "qwen2.5:14b"
DEFAULT_TIMEOUT = 300  # segons per petició (model gran, recomanat a evalua_models.py)
DEFAULT_DELAY = 0.3

MAX_ERRORS_CONSECUTIUS = 5  # si Ollama falla tantes vegades seguides, s'atura l'execució

logger = logging.getLogger("genera_corpus_sintetic")


def configurar_logging(verbose: bool) -> None:
    GENERAT_DIR.mkdir(parents=True, exist_ok=True)
    nivell = logging.DEBUG if verbose else logging.INFO
    formato = "%(asctime)s [%(levelname)s] %(message)s"
    logger.setLevel(nivell)
    logger.handlers.clear()

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter(formato))
    logger.addHandler(consola)

    fitxer = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fitxer.setFormatter(logging.Formatter(formato))
    logger.addHandler(fitxer)


# ─── Segmentació en frases ────────────────────────────────────────────────────
# Heurística amb regex (sense dependències de NLP): parteix per puntuació
# forta seguida d'espai + majúscula/cometa, i torna a unir si la paraula
# anterior és una abreviatura coneguda (art., núm., Sr., etc.) o una inicial.

ABREVIATURES = {
    "sr", "sra", "sres", "dr", "dra", "d", "dna", "núm", "num", "art",
    "pàg", "pag", "p", "ex", "etc", "aprox", "vol", "ed", "coord", "tel",
    "c", "av", "prof", "cf", "ibid", "op", "cit", "s", "art.",
}

_SENT_END_RE = re.compile(r'(?<=[.!?…])\s+(?=[A-ZÀÈÉÍÒÓÚÜÇ«"\'(‘“])')


def uneix_talls_de_negreta(text: str) -> str:
    """Reuneix línies que en realitat són una mateixa frase partida per un
    salt de línia que va introduir la neteja del raspat quan al mig de la
    frase hi havia una paraula en negreta o enllaçada (molt habitual als
    articles del glossari de l'AVL: "amb la paraula\\nfurri." es tractava
    com dos "paràgrafs" i la primera meitat colava com a frase completa).
    Senyal fiable: la línia següent comença en minúscula -- cap paràgraf,
    títol o ítem de llista real comença mai en minúscula, així que és
    sempre la continuació de la frase anterior, mai un tros nou."""
    linies = (text or "").split("\n")
    resultat: list[str] = []
    i = 0
    n = len(linies)
    while i < n:
        actual = linies[i].strip()
        while actual and i + 1 < n:
            seguent = linies[i + 1].strip()
            if seguent and seguent[0].islower():
                actual = actual + " " + seguent
                i += 1
            else:
                break
        resultat.append(actual)
        i += 1
    return "\n".join(resultat)


def divideix_frases(paragraf: str) -> list[str]:
    """Parteix un paràgraf en frases. Heurístic, no perfecte — les parelles
    dubtoses queden filtrades després per longitud/ràtio de lletres."""
    paragraf = paragraf.strip()
    if not paragraf:
        return []

    candidats = _SENT_END_RE.split(paragraf)
    frases: list[str] = []
    buffer = ""

    for candidat in candidats:
        candidat = candidat.strip()
        if not candidat:
            continue
        if buffer:
            ultima = re.findall(r"[A-Za-zÀ-ÿ]+\.?$", buffer)
            paraula = ultima[-1].rstrip(".").lower() if ultima else ""
            es_inicial = len(paraula) <= 1 and buffer.rstrip().endswith(".")
            if paraula in ABREVIATURES or es_inicial:
                buffer = buffer + " " + candidat
                continue
            frases.append(buffer)
        buffer = candidat

    if buffer:
        frases.append(buffer)

    return frases


def extreu_frases_document(
    text: str, min_paraules: int, min_caracters: int, max_caracters: int
) -> list[str]:
    """Extrau frases netes d'un document: separa per paràgraf, divideix en
    frases i descarta el que és massa curt, massa llarg (risc de tall a la
    resposta del model) o té massa poques lletres (taules, numeració...)."""
    frases_ok = []
    for paragraf in uneix_talls_de_negreta(text).split("\n"):
        for frase in divideix_frases(paragraf):
            frase = re.sub(r"\s+", " ", frase).strip()
            if not frase:
                continue
            if len(frase.split()) < min_paraules:
                continue
            if not (min_caracters <= len(frase) <= max_caracters):
                continue
            lletres = sum(c.isalpha() for c in frase)
            if lletres / len(frase) < 0.55:
                continue
            frases_ok.append(frase)
    return frases_ok


# ─── Registre de frases úniques ───────────────────────────────────────────────

@dataclass
class FraseUnica:
    id: str
    frase_val: str
    doc_id: str
    doc_type: str
    source_name: str
    source_url: str
    n_ocurrencies: int = 1


def id_frase(frase: str) -> str:
    clau = em.normalitza_apostrofa(frase).strip().lower()
    return hashlib.sha1(clau.encode("utf-8")).hexdigest()[:16]


def carrega_frases_uniques(
    input_path: Path, min_paraules: int, min_caracters: int, max_caracters: int
) -> "tuple[dict[str, FraseUnica], Counter, int]":
    """Llig el corpus, segmenta cada document i deduplica frases idèntiques
    (molt habitual al glossari i als textos legals repetits d'un butlletí a
    l'altre). Retorna el registre, el recompte de docs per tipus i el total
    de frases candidates descartades pels filtres de longitud."""
    registre: dict[str, FraseUnica] = {}
    docs_per_tipus: Counter = Counter()
    total_docs = 0
    total_frases_brutes = 0

    with open(input_path, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if not linia:
                continue
            doc = json.loads(linia)
            total_docs += 1
            docs_per_tipus[doc.get("doc_type", "desconegut")] += 1

            frases = extreu_frases_document(
                doc.get("text", ""), min_paraules, min_caracters, max_caracters
            )
            total_frases_brutes += len(frases)

            for frase in frases:
                fid = id_frase(frase)
                if fid in registre:
                    registre[fid].n_ocurrencies += 1
                    continue
                registre[fid] = FraseUnica(
                    id=fid,
                    frase_val=frase,
                    doc_id=doc.get("id", ""),
                    doc_type=doc.get("doc_type", "desconegut"),
                    source_name=doc.get("source_name", ""),
                    source_url=doc.get("source_url", ""),
                )

    logger.info(f"Documents llegits: {total_docs} ({dict(docs_per_tipus)})")
    logger.info(
        f"Frases candidates: {total_frases_brutes} → {len(registre)} úniques "
        f"({total_frases_brutes - len(registre)} duplicades descartades)"
    )
    return registre, docs_per_tipus, total_frases_brutes


# ─── Control de qualitat de la traducció ─────────────────────────────────────

def avalua_qualitat(frase_val: str, frase_cat: str) -> list[str]:
    """Retorna una llista de motius de sospita (buida si la traducció sembla
    correcta). No es descarta res automàticament: es marca perquè l'usuari
    puga revisar-ho, i l'exportació neta ho filtra."""
    motius = []
    if not frase_cat.strip():
        motius.append("buit")
        return motius

    if "[VOCABULARI" in frase_cat.upper():
        motius.append("fuga_prompt")

    # El prompt d'usuari comença amb "Frase a traduir: ..."; de vegades el model
    # copia eixe encapçalament dins de la resposta en lloc de només traduir.
    if "frase a traduir" in frase_cat.lower():
        motius.append("instruccio_filtrada")

    for sigla in ENTITATS_PROTEGIDES:
        apareix_val = re.search(rf"\b{sigla}\b", frase_val)
        apareix_cat = re.search(rf"\b{sigla}\b", frase_cat)
        if apareix_val and not apareix_cat:
            motius.append("entitat_alterada")
        elif apareix_cat and not apareix_val:
            # El model s'ha inventat una sigla que no hi era (p.ex. "l'Acadèmia" -> "l'AVL")
            motius.append("sigla_introduida")

    # Fragment de paraula duplicat just després d'una elisió (p.ex. "M'm-interessa"):
    # un tipus de glitch de generació que s'ha vist en textos llargs.
    if re.search(r"(?i)\b(\w)'\1-", frase_cat):
        motius.append("possible_glitch")

    if re.search(r"\b(traducció|traduccion|nota:|resposta:)\b", frase_cat, re.IGNORECASE):
        motius.append("possible_explicacio")

    ratio = len(frase_cat) / max(len(frase_val), 1)
    if ratio < 0.5 or ratio > 1.8:
        motius.append("longitud_anormal")

    marcadors_occ = {
        "este", "esta", "estos", "estes", "hui", "meua", "teua", "seua",
        "traure", "tindre", "vindre", "vore", "eixir", "huit", "xiquet",
        "xiqueta", "faena",
    }
    val_norm = em.normalitza_apostrofa(frase_val.lower())
    cat_norm = em.normalitza_apostrofa(frase_cat.lower())
    conte_marcador = any(re.search(rf"\b{m}\b", val_norm) for m in marcadors_occ)
    if conte_marcador and val_norm.strip() == cat_norm.strip():
        motius.append("no_traduit")

    return motius


# ─── Lectura/escriptura del corpus sintètic ───────────────────────────────────

def carrega_fets(output_path: Path) -> set[str]:
    """Llig el fitxer de sortida existent i retorna el conjunt d'ids ja
    traduïts, per poder reanudar. Si troba una línia corrupta al final (procés
    tallat a mig escriure), la descarta i reescriu el fitxer net."""
    if not output_path.exists():
        return set()

    linies_valides = []
    corruptes = 0
    with open(output_path, encoding="utf-8") as f:
        for linia in f:
            linia_neta = linia.strip()
            if not linia_neta:
                continue
            try:
                json.loads(linia_neta)
                linies_valides.append(linia_neta)
            except json.JSONDecodeError:
                corruptes += 1

    if corruptes:
        logger.warning(f"{corruptes} línia(es) corruptes al final de {output_path.name}; es netegen.")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(linies_valides) + ("\n" if linies_valides else ""))

    return {json.loads(linia)["id"] for linia in linies_valides}


def mergeja_shards(num_shards: int, output_path: Path) -> None:
    """Combina corpus_sintetic_val_cat.shard0.jsonl..shard(N-1).jsonl en el
    fitxer final. Com el repartiment és per hash de l'id, cada frase pertany
    a un únic fragment — no hi pot haver duplicats entre fragments, però es
    deduplica igualment per seguretat (p.ex. si es re-executa un fragment
    amb --num-shards diferent per error)."""
    vistos: set[str] = set()
    total = 0
    with open(output_path, "w", encoding="utf-8") as f_out:
        for i in range(num_shards):
            shard_path = output_path.with_suffix(f".shard{i}.jsonl")
            if not shard_path.exists():
                logger.warning(f"No trobat: {shard_path} (eixe fragment no ha produït res encara)")
                continue
            n = 0
            with open(shard_path, encoding="utf-8") as f_in:
                for linia in f_in:
                    linia = linia.strip()
                    if not linia:
                        continue
                    reg = json.loads(linia)
                    if reg["id"] in vistos:
                        continue
                    vistos.add(reg["id"])
                    f_out.write(linia + "\n")
                    n += 1
            logger.info(f"{shard_path.name}: {n} frases fusionades")
            total += n
    logger.info(f"Fusió completa: {total} frases úniques -> {output_path}")


def exporta_nets(output_path: Path, incloure_sospitosos: bool) -> int:
    """Regenera els fitxers d'exportació neta (jsonl + parallel.val/.cat) a
    partir del corpus sintètic complet."""
    if not output_path.exists():
        logger.warning("No hi ha res a exportar encara: no existeix %s", output_path)
        return 0

    n = 0
    with open(output_path, encoding="utf-8") as f_in, \
         open(PARALLEL_JSONL, "w", encoding="utf-8") as f_jsonl, \
         open(PARALLEL_VAL, "w", encoding="utf-8") as f_val, \
         open(PARALLEL_CAT, "w", encoding="utf-8") as f_cat:
        for linia in f_in:
            linia = linia.strip()
            if not linia:
                continue
            reg = json.loads(linia)
            if reg["motius_sospita"] and not incloure_sospitosos:
                continue
            f_jsonl.write(json.dumps(
                {"val": reg["frase_val"], "cat": reg["frase_cat"]}, ensure_ascii=False
            ) + "\n")
            f_val.write(reg["frase_val"] + "\n")
            f_cat.write(reg["frase_cat"] + "\n")
            n += 1

    logger.info(f"Exportades {n} parelles netes → {PARALLEL_JSONL.name}, {PARALLEL_VAL.name}, {PARALLEL_CAT.name}")
    return n


def genera_informe(output_path: Path, elapsed: float, errors: int, model: str = DEFAULT_MODEL) -> None:
    if not output_path.exists():
        return
    registres = [json.loads(l) for l in open(output_path, encoding="utf-8") if l.strip()]
    if not registres:
        return

    sospitosos = [r for r in registres if r["motius_sospita"]]
    per_tipus = Counter(r["doc_type"] for r in registres)
    motius = Counter(m for r in sospitosos for m in r["motius_sospita"])

    linies = []
    linies.append("=" * 70)
    linies.append("INFORME — CORPUS SINTÈTIC PARAL·LEL VALENCIÀ → CATALÀ")
    linies.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    linies.append(f"Model: {model}")
    linies.append("=" * 70)
    linies.append("")
    linies.append(f"Total de parelles generades: {len(registres)}")
    linies.append(f"  Netes:      {len(registres) - len(sospitosos)}")
    linies.append(f"  Sospitoses: {len(sospitosos)}")
    linies.append(f"Errors de traducció en aquesta execució: {errors}")
    linies.append(f"Temps d'aquesta execució: {elapsed/60:.1f} min")
    linies.append("")
    linies.append("Parelles per tipus de document:")
    for tipus, n in per_tipus.most_common():
        linies.append(f"  {tipus:<25} {n:>6}")
    if motius:
        linies.append("")
        linies.append("Motius de sospita:")
        for motiu, n in motius.most_common():
            linies.append(f"  {motiu:<25} {n:>6}")

    INFORME_PATH.write_text("\n".join(linies), encoding="utf-8")
    logger.info(f"Informe guardat: {INFORME_PATH}")
    print("\n" + "\n".join(linies))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Corpus font en valencià (jsonl)")
    parser.add_argument(
        "--output", default=None,
        help=f"Fitxer de sortida del corpus sintètic (per defecte: {OUTPUT_PATH.name}, o amb sufix "
             "'.shardN.jsonl' si s'usa --num-shards)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model d'Ollama a usar per traduir")
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", em.OLLAMA_URL),
        help=f"URL del servidor Ollama (per defecte: variable d'entorn OLLAMA_URL o {em.OLLAMA_URL}). "
             "Per a un Ollama remot en un node GPU de clúster, obri un túnel SSH "
             "(veure slurm/README.md) i posa ací 'http://localhost:<port_local>'."
    )
    parser.add_argument("--ollama-timeout", type=int, default=DEFAULT_TIMEOUT, help="Segons d'espera per petició")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Pausa entre peticions (segons)")
    parser.add_argument("--min-paraules", type=int, default=5, help="Mínim de paraules per frase")
    parser.add_argument("--min-caracters", type=int, default=20, help="Mínim de caràcters per frase")
    parser.add_argument("--max-caracters", type=int, default=280, help="Màxim de caràcters per frase (evita talls a la resposta)")
    parser.add_argument("--seed", type=int, default=42, help="Llavor per a --sample")
    parser.add_argument("--verbose", action="store_true", help="Log detallat (DEBUG)")
    parser.add_argument("--dry-run", action="store_true", help="Només mostra estadístiques de segmentació, no tradueix res")
    parser.add_argument("--nomes-exporta", action="store_true", help="No tradueix res: regenera només els fitxers nets a partir del que ja hi ha")
    parser.add_argument("--incloure-sospitosos", action="store_true", help="A l'exportació neta, inclou també les parelles marcades com a sospitoses")
    parser.add_argument(
        "--num-shards", type=int, default=1,
        help="Reparteix el corpus en N fragments deterministes (per repartir-los entre N GPUs/processos). "
             "Cada frase pertany a un únic fragment (per hash del seu id), no cal coordinació entre processos."
    )
    parser.add_argument(
        "--shard-id", type=int, default=0,
        help="Quin fragment (0..--num-shards - 1) tradueix aquesta execució."
    )
    parser.add_argument(
        "--merge-shards", type=int, default=None, metavar="N",
        help="No tradueix res: fusiona els N fitxers *.shard0.jsonl..shard(N-1).jsonl "
             "en el fitxer final i regenera l'exportació neta."
    )

    grup = parser.add_mutually_exclusive_group()
    grup.add_argument("--limit", type=int, default=None, help="Tradueix només les N primeres frases (prova ràpida i determinista)")
    grup.add_argument("--sample", type=int, default=None, help="Tradueix una mostra aleatòria de N frases (prova de qualitat representativa)")

    args = parser.parse_args()
    configurar_logging(args.verbose)

    if args.num_shards < 1 or not (0 <= args.shard_id < args.num_shards):
        logger.error("--shard-id ha d'estar entre 0 i --num-shards - 1")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    elif args.num_shards > 1:
        output_path = OUTPUT_PATH.with_suffix(f".shard{args.shard_id}.jsonl")
    else:
        output_path = OUTPUT_PATH

    if args.merge_shards:
        # Bug real corregit ací: abans usava sempre la constant OUTPUT_PATH
        # fixa, ignorant --output encara que ja s'haguera resolt bé a
        # `output_path` unes línies amunt -- generar amb un model diferent
        # (--output personalitzat per fragment) i després fusionar sense
        # passar el mateix --output sobreescriuria SEMPRE
        # corpus_sintetic_val_cat.jsonl, encara que fora d'una generació
        # anterior amb un altre model.
        mergeja_shards(args.merge_shards, output_path)
        exporta_nets(output_path, args.incloure_sospitosos)
        genera_informe(output_path, 0.0, 0, model=args.model)
        return

    em.OLLAMA_URL = args.ollama_url  # redirigeix ollama_disponible()/tradueix() a l'URL indicada
    logger.info(f"Ollama: {em.OLLAMA_URL}")

    if args.nomes_exporta:
        exporta_nets(output_path, args.incloure_sospitosos)
        return

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"No es troba el corpus font: {input_path}")
        sys.exit(1)

    registre, _, _ = carrega_frases_uniques(
        input_path, args.min_paraules, args.min_caracters, args.max_caracters
    )

    ids = list(registre.keys())

    if args.num_shards > 1:
        ids = [i for i in ids if int(i, 16) % args.num_shards == args.shard_id]
        logger.info(f"Fragment {args.shard_id}/{args.num_shards}: {len(ids)} frases assignades")

    if args.sample is not None:
        random.Random(args.seed).shuffle(ids)
        ids = ids[: args.sample]
    elif args.limit is not None:
        ids = ids[: args.limit]

    if args.dry_run:
        logger.info(f"[--dry-run] {len(ids)} frases seleccionades per a traduir (no es crida cap model).")
        return

    if not em.ollama_disponible():
        logger.error("No es pot connectar amb Ollama a http://localhost:11434 (cal 'ollama serve'?).")
        sys.exit(1)

    fets = carrega_fets(output_path)
    pendents = [i for i in ids if i not in fets]
    logger.info(
        f"Frases seleccionades: {len(ids)} | ja traduïdes: {len(ids) - len(pendents)} | "
        f"pendents: {len(pendents)}"
    )
    if not pendents:
        logger.info("Res per fer: totes les frases seleccionades ja estan traduïdes.")
        exporta_nets(output_path, args.incloure_sospitosos)
        return

    inici = time.time()
    errors_consecutius = 0
    errors_totals = 0
    processades = 0

    with open(output_path, "a", encoding="utf-8") as f_out:
        for i, fid in enumerate(pendents, 1):
            item = registre[fid]

            try:
                # em.neteja_preambul(): el benchmark d'evalua_models.py ja
                # netejava esta mateixa fuga ("Resposta correcta: ", "Frase
                # a traduir: "...) abans de puntuar, però este script no ho
                # feia -- per això el problema no s'havia vist mai al
                # benchmark (sempre net) i sí a la generació real del
                # corpus (sense netejar). Confirmat amb salamandra-7b-
                # instruct, que afig "Resposta correcta:" a totes les
                # respostes reals encara que al benchmark curt no ho fera
                # notar (potser per la mida/format diferent del prompt).
                hipotesi = em.neteja_preambul(
                    tradueix(item.frase_val, model=args.model, timeout=args.ollama_timeout)
                )
            except Exception as e:
                hipotesi = f"ERROR: {e}"

            if hipotesi.startswith("ERROR:"):
                errors_totals += 1
                errors_consecutius += 1
                logger.warning(f"[{i}/{len(pendents)}] error traduint '{item.frase_val[:50]}...': {hipotesi}")
                if errors_consecutius >= MAX_ERRORS_CONSECUTIUS:
                    logger.error(
                        f"{MAX_ERRORS_CONSECUTIUS} errors seguits: sembla que Ollama s'ha aturat. "
                        f"S'interromp l'execució (relança el mateix comandament per continuar)."
                    )
                    break
                continue

            errors_consecutius = 0
            motius = avalua_qualitat(item.frase_val, hipotesi)

            registre_sortida = {
                "id": item.id,
                "frase_val": item.frase_val,
                "frase_cat": hipotesi,
                "doc_id": item.doc_id,
                "doc_type": item.doc_type,
                "source_name": item.source_name,
                "source_url": item.source_url,
                "n_ocurrencies": item.n_ocurrencies,
                "model": args.model,
                "timestamp": datetime.now().isoformat(),
                "motius_sospita": motius,
            }
            f_out.write(json.dumps(registre_sortida, ensure_ascii=False) + "\n")
            f_out.flush()
            processades += 1

            marca = f" [SOSPITÓS: {','.join(motius)}]" if motius else ""
            logger.info(f"[{i}/{len(pendents)}] {item.frase_val[:60]}...{marca}")

            if i < len(pendents):
                time.sleep(args.delay)

            if i % 50 == 0:
                transcorregut = time.time() - inici
                ritme = transcorregut / i
                restant = ritme * (len(pendents) - i)
                logger.info(
                    f"--- progrés: {i}/{len(pendents)} | "
                    f"{ritme:.1f}s/frase | ETA {restant/60:.0f} min ---"
                )

    elapsed = time.time() - inici
    logger.info(f"Fet. {processades} frases noves traduïdes en {elapsed/60:.1f} min ({errors_totals} errors).")

    exporta_nets(output_path, args.incloure_sospitosos)
    genera_informe(output_path, elapsed, errors_totals, model=args.model)


if __name__ == "__main__":
    main()
