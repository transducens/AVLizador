#!/usr/bin/env python3
"""repara_corpus.py — Corregeix a mà, sense tornar a cridar Ollama, els 3 tipus
de problema trobats en l'auditoria (`sinteticos/generado/analisi_corpus.html`):

  1. Fuita de "Frase a traduir:" (part del prompt) dins de la resposta.
     ~1.165 casos — es soluciona traient el literal, la resta de la resposta
     ja és una traducció vàlida.
  2. Substitucions de lèxic errònies per col·lisió d'homògrafs o per una
     entrada del lèxic mal transcrita:
       "blanca" (=blanc) -> "garsa" (l'ocell)      "pròxim" -> "proïsme"
       "Ramon" -> "Ramó" (nom de persona)           "Manuel" -> "Manel"
       "celebració" -> "cel·lebració" (entrada errònia, ja tret de
       palabras_traducidas.json — "celebració" s'escriu igual en els dos
       dialectes)
     ~300 casos — es reverteixen al valor original (és la traducció correcta:
     cap d'estes paraules canvia entre valencià i català en eixe sentit).
  3. Formes de subjuntiu que el model no converteix de manera fiable
     (siga/siguen/tinga/tinguen/tinguera) — es corregeixen amb les mateixes
     substitucions deterministes que ja hi ha a evalua_models.tradueix_regles().
     NO es toquen "vinga"/"fora" perquè tenen homonímia real (interjecció
     "vinga!" i advervi "fora"=fora de) i una substitució cega hi introduiria
     errors nous.

Després de pedaçar cada parella, es torna a calcular `motius_sospita` amb la
versió ja corregida d'`avalua_qualitat()` (que ara també detecta el cas 1).

No es crida Ollama en cap moment — tot és manipulació de text sobre el fitxer
que ja tens generat.

ÚS:
    python repara_corpus.py
    python repara_corpus.py --input sinteticos/generado/corpus_sintetic_val_cat.jsonl

SORTIDA:
    Sobreescriu l'`--input` (després de fer-ne una còpia de seguretat
    `<nom>.abans_de_reparar.jsonl` al costat) i regenera les exportacions
    netes (`parallel_val_cat.jsonl`, `parallel.val`, `parallel.cat`,
    `informe_generacio.txt`) a partir del corpus ja corregit.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import genera_corpus_sintetico as gcs  # noqa: E402  (reutilitza avalua_qualitat/exporta_nets)
import evalua_models as em  # noqa: E402  (reutilitza _substitueix_conservant_majuscules)

DEFAULT_INPUT = BASE_DIR / "generado" / "corpus_sintetic_val_cat.jsonl"

# (paraula valenciana original, paraula catalana errònia introduïda pel bug)
REVERSIONS_LEXIC = [
    ("ramon", "ramó"),
    ("manuel", "manel"),
    ("blanca", "garsa"),
    ("pròxim", "proïsme"),
    ("celebració", "cel·lebració"),
]

# (forma occidental, forma oriental correcta) — només les que NO tenen
# homonímia coneguda (per això no hi ha "vinga"/"fora" ací).
SUBJUNTIU_SEGUR = [
    ("siguen", "siguin"),
    ("siga", "sigui"),
    ("tinguera", "tingués"),
    ("tinguen", "tinguin"),
    ("tinga", "tingui"),
]


def repara_fuita_prompt(frase_cat: str) -> tuple[str, bool]:
    nova = re.sub(r"(?i)frase a traduir\s*:?\s*", "", frase_cat).strip()
    return nova, nova != frase_cat.strip()


def repara_lexic(frase_val: str, frase_cat: str) -> tuple[str, list[str]]:
    aplicades = []
    for forma_val, forma_erronia in REVERSIONS_LEXIC:
        patro_val = re.compile(rf"\b{forma_val}\b", re.IGNORECASE)
        patro_cat = re.compile(rf"\b{forma_erronia}\b", re.IGNORECASE)
        if patro_val.search(frase_val) and patro_cat.search(frase_cat):
            frase_cat = em._substitueix_conservant_majuscules(patro_cat.pattern, forma_val, frase_cat)
            aplicades.append(f"{forma_val}<-{forma_erronia}")
    return frase_cat, aplicades


def repara_subjuntiu(frase_val: str, frase_cat: str) -> tuple[str, list[str]]:
    aplicades = []
    val_norm = em.normalitza_apostrofa(frase_val.lower())
    for occ, ori in SUBJUNTIU_SEGUR:
        patro_val = re.compile(rf"\b{occ}\b")
        patro_cat = re.compile(rf"\b{occ}\b", re.IGNORECASE)
        if patro_val.search(val_norm) and patro_cat.search(frase_cat):
            frase_cat = em._substitueix_conservant_majuscules(patro_cat.pattern, ori, frase_cat)
            aplicades.append(f"{occ}->{ori}")
    return frase_cat, aplicades


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Fitxer del corpus a reparar")
    parser.add_argument("--incloure-sospitosos", action="store_true", help="Passa-ho a l'exportació neta final")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: no es troba {input_path}", file=sys.stderr)
        sys.exit(1)

    backup_path = input_path.with_suffix(".abans_de_reparar.jsonl")
    if not backup_path.exists():
        shutil.copy2(input_path, backup_path)
        print(f"Còpia de seguretat: {backup_path}")
    else:
        print(f"Ja existia una còpia de seguretat ({backup_path}); no es sobreescriu.")

    comptadors = Counter()
    motius_abans = Counter()
    motius_despres = Counter()
    registres = []

    with open(input_path, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if not linia:
                continue
            reg = json.loads(linia)
            for m in reg["motius_sospita"]:
                motius_abans[m] += 1

            cat = reg["frase_cat"]
            val = reg["frase_val"]

            cat, tocada1 = repara_fuita_prompt(cat)
            if tocada1:
                comptadors["fuita_prompt"] += 1

            cat, aplicades2 = repara_lexic(val, cat)
            for a in aplicades2:
                comptadors[f"lexic:{a}"] += 1

            cat, aplicades3 = repara_subjuntiu(val, cat)
            for a in aplicades3:
                comptadors[f"subjuntiu:{a}"] += 1

            reg["frase_cat"] = cat
            reg["motius_sospita"] = gcs.avalua_qualitat(val, cat)
            for m in reg["motius_sospita"]:
                motius_despres[m] += 1

            registres.append(reg)

    with open(input_path, "w", encoding="utf-8") as f:
        for reg in registres:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    print(f"\n{len(registres)} parelles processades.\n")
    print("Correccions aplicades:")
    for k, n in comptadors.most_common():
        print(f"  {k:<30} {n}")

    print("\nMotius de sospita — abans -> després:")
    claus = sorted(set(motius_abans) | set(motius_despres))
    for m in claus:
        print(f"  {m:<25} {motius_abans.get(m, 0):>6} -> {motius_despres.get(m, 0):>6}")

    sospitoses_despres = sum(1 for r in registres if r["motius_sospita"])
    print(f"\nParelles amb alguna marca de sospita ARA: {sospitoses_despres} de {len(registres)} "
          f"({100 * sospitoses_despres / len(registres):.2f}%)")

    print("\nRegenerant exportacions netes...")
    gcs.exporta_nets(input_path, args.incloure_sospitosos)
    print("Fet.")


if __name__ == "__main__":
    main()
