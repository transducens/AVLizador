#!/usr/bin/env python3
"""Identifica dos fenomens d'ambiguitat INDICATIU/SUBJUNTIU en valencia
que el motor de regles deixa a proposit sense traduir, per a que el
postprocessat LLM (vía C) decidisca mirant el context real de la frase:

1. **1a persona singular, present** (06/10/2026): "plantege" -> "plantejo"
   indicatiu / "plantegi" subjuntiu. Calculat a `calcula_ambiguitats_1a_persona()`
   a partir de les 4 fonts crues de Mauricio (dos candidats catalans que
   comparteixen arrel i acaben en "-o"/"-i").
2. **3a plural, present i imperfet** (08/10/2026): "creuen" -> "creuen"
   indicatiu (no canvia, per aixo no hi ha fila a les dades) / "creuin"
   subjuntiu; "quedaren" -> "quedaren" indicatiu / "quedessin" subjuntiu.
   Calculat a `calcula_ambiguitats_3a_plural()` a partir de
   `traductor/data/conjugacions_dialectals.json` ja fusionat, reutilitzant
   `es_risc_mode_3a_plural()` de `conjugacions_dict.py` -- mateixa funcio
   que el motor fa servir per a EXCLOURE estes formes del lookup directe,
   perque este script ha de mirar EXACTAMENT el mateix conjunt.

`calcula_ambiguitats()` combina els dos (vore baix). Este fitxer tambe
localitza frases reals del BOE on apareixen -- mostra de prova per a
comparar les 3 vies de postprocessat amb LLM (A/B/C, vore conversa
06/10/2026).

Per que estos patrons i no uns atres: ConjugacionsDictRule EXCLOU del
lookup qualsevol forma marcada "problematica" o detectada per
`es_risc_mode_3a_plural()` (vore traductor/rules/conjugacions_dict.py).
La resta de formes "problematica" (locucions fixes, col·lisions
homografes amb substantius com "germanes", etc.) NO son estos fenomens i
es gestionen per atres mecanismes (EXCLUSIONS_HOMOGRAF, filtre POS).

Nota important: esta detecció NOMES mira el PARELL de catalans candidats
per forma valenciana -- no consulta el camp "problematica" existent,
perque eixe camp es calcula FITXER A FITXER (vore
_marca_ambigues_dins_del_mateix_fitxer a sync_data.py) i per tant pot
deixar escapar casos on l'indicatiu ve d'un fitxer i el subjuntiu d'un
altre (ambiguitat real que avui NO es detecta -- vore README d'esta
carpeta per als numeros trobats).

Us:
    python identifica_ambigues.py
    python identifica_ambigues.py --mostra 30 --seed 7

    # Sobre un altre corpus (p.ex. el benchmark de 150 frases, camps
    # distints i format JSON -- no JSONL -- i sense "documento_id"):
    python identifica_ambigues.py --corpus ../../03_seleccio_de_model/benchmark_corpus.json \
        --format json --camp-valencia occidental --camp-catala oriental --camp-doc id \
        --salida mostra_casos_ambigues_benchmark.json --mostra 999
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# En local, l'arrel del repo esta 2 nivells amunt. En Abaco este fitxer es
# puja sol dins d'una carpeta plana que ja conte 02_regles_dialectals/
# directament -- per aixo es permet sobreescriure amb AVLIZADOR_ROOT (vore
# benchmark_integrat.py i slurm/benchmark_integrat_multimodel.sh).
ARREL = Path(os.environ.get("AVLIZADOR_ROOT", Path(__file__).resolve().parent.parent.parent))
MAURICIO = ARREL / "02_regles_dialectals" / "lexic" / "font_mauricio"
CORPUS_PATH = ARREL / "dades" / "boe_net" / "corpus_entrenamiento_net.jsonl"
SALIDA_AMBIGUITATS = Path(__file__).resolve().parent / "ambiguitats_indicatiu_subjuntiu.json"
SALIDA_MOSTRA = Path(__file__).resolve().parent / "mostra_casos_ambigues.json"

FONTS = (
    "verbos_no_ambiguos.json",
    "conjugaciones_limpio.json",
    "verbos_todos_anotados.json",
    "conjugaciones_nuevo.json",
)


def calcula_ambiguitats_1a_persona() -> dict[str, dict[str, str]]:
    """Torna {forma_valenciana: {"indicatiu": ..., "subjuntiu": ...}} per a
    totes les formes on, entre les 4 fonts de Mauricio, hi ha EXACTAMENT 2
    traduccions catalanes candidates que comparteixen arrel i difereixen
    només en la vocal final -o (indicatiu) / -i (subjuntiu) -- 1a persona
    singular."""
    per_valencia: dict[str, set[str]] = defaultdict(set)
    for nom_font in FONTS:
        dades = json.loads((MAURICIO / nom_font).read_text(encoding="utf-8"))
        for entrada in dades:
            v = entrada.get("valenciano", "").strip().lower()
            c = entrada.get("catalan", "").strip()
            if v and c:
                per_valencia[v].add(c)

    resultat: dict[str, dict[str, str]] = {}
    for valenciano, catalans in per_valencia.items():
        if len(catalans) != 2:
            continue
        a, b = sorted(catalans)
        if a.endswith("o") and b.endswith("i") and a[:-1] == b[:-1]:
            indicatiu, subjuntiu = a, b
        elif b.endswith("o") and a.endswith("i") and a[:-1] == b[:-1]:
            indicatiu, subjuntiu = b, a
        else:
            continue
        resultat[valenciano] = {"indicatiu": indicatiu, "subjuntiu": subjuntiu}
    return resultat


def calcula_ambiguitats_3a_plural() -> dict[str, dict[str, str]]:
    """Torna {forma_valenciana: {"indicatiu": ..., "subjuntiu": ...}} per a
    la col·lisio INDICATIU/SUBJUNTIU de 3a plural trobada el 08/10/2026
    (present "-en"->"-in", imperfet "-aren"/"-eren"->"-essin"/"-issin" --
    vore `traductor/rules/conjugacions_dict.py::es_risc_mode_3a_plural`,
    la mateixa funcio que `ConjugacionsDictRule` fa servir per a EXCLOURE
    estes formes del lookup directe, perque este script ha de mirar
    EXACTAMENT el mateix conjunt que el motor deixa sense traduir).

    A diferencia de `calcula_ambiguitats_1a_persona()`, ací l'indicatiu NO
    ve de cap fila de dades -- es la mateixa forma valenciana SENSE
    CANVIAR (el present/pretèrit d'indicatiu de 3a plural no canvia mai
    entre dialectes, per aixo cap lexic diferencial el llista; nomes hi
    ha la fila de subjuntiu, que es l'unica que veu `conjugacions_dialectals.json`).
    """
    sys.path.insert(0, str(ARREL))
    from traductor.rules.conjugacions_dict import (  # noqa: E402
        DEFAULT_CONJUGACIONS_PATH,
        EXCLUSIONS_HOMOGRAF,
        SEMPRE_VERB,
        es_risc_mode_3a_plural,
    )

    dades = json.loads(DEFAULT_CONJUGACIONS_PATH.read_text(encoding="utf-8"))
    per_valencia: dict[str, set[str]] = defaultdict(set)
    for entrada in dades.get("entradas", []):
        if entrada.get("problematica"):
            continue
        v = (entrada.get("valenciano") or "").strip().lower()
        c = (entrada.get("catalan") or "").strip()
        if v and c:
            per_valencia[v].add(c)

    resultat: dict[str, dict[str, str]] = {}
    for valenciano, catalans in per_valencia.items():
        if valenciano in EXCLUSIONS_HOMOGRAF or valenciano in SEMPRE_VERB:
            continue
        if len(catalans) != 1:
            continue
        subjuntiu = next(iter(catalans))
        if not es_risc_mode_3a_plural(valenciano, subjuntiu):
            continue
        resultat[valenciano] = {"indicatiu": valenciano, "subjuntiu": subjuntiu}
    return resultat


def calcula_ambiguitats() -> dict[str, dict[str, str]]:
    """Combina 1a persona singular + 3a plural (08/10/2026) -- vore
    `calcula_ambiguitats_1a_persona()` i `calcula_ambiguitats_3a_plural()`.
    Mantinguda com a punt d'entrada unic perque `benchmark_integrat.py`
    i la resta de scripts ja la criden tal qual, sense saber quants
    fenomens distints combina per davall."""
    resultat = calcula_ambiguitats_1a_persona()
    resultat.update(calcula_ambiguitats_3a_plural())
    return resultat


_PARAULA = re.compile(r"[a-zàèéíòóúïüç']+", re.IGNORECASE)


def llig_registres(corpus_path: Path, format_: str) -> list[dict]:
    if format_ == "jsonl":
        with open(corpus_path, encoding="utf-8") as f:
            return [json.loads(linia) for linia in f]
    return json.loads(corpus_path.read_text(encoding="utf-8"))


def troba_frases(
    ambiguitats: dict[str, dict[str, str]],
    mostra: int,
    seed: int,
    corpus_path: Path = CORPUS_PATH,
    format_: str = "jsonl",
    camp_valencia: str = "texto_valenciano",
    camp_catala: str = "texto_catalan",
    camp_id: str = "id",
    camp_doc: str = "documento_id",
) -> list[dict]:
    # Tokenitza CADA frase UNA vegada i consulta per pertinença a un set
    # (O(1)) en compte d'aplicar 3.004 regex per frase (l'enfoc inicial
    # trigava massa: 3.004 patrons x 260.345 frases).
    #
    # Filtre important (trobat 06/10/2026): moltes formes "ambigües" NOMÉS
    # ho son en teoria -- en la pràctica, la mateixa cadena és MOLT més
    # freqüent com a substantiu que com a verb rar ("objecte", "projecte",
    # "contracte", "base", "compte"...), un altre cas de col·lisió
    # homògrafa com la ja documentada a traductor/README.md. Per a esta
    # mostra de prova exigim que el candidat INDICATIU o el SUBJUNTIU
    # aparega literalment (com a paraula) en la traducció catalana de
    # referència del BOE -- això descarta quasi tots els falsos positius
    # nominals (el substantiu es queda igual en la referència) i, de pas,
    # ens dona una etiqueta "correcta" GRATIS per a jutjar les 3 vies
    # A/B/C sense anotar res a mà.
    candidates: list[dict] = []
    for registre in llig_registres(corpus_path, format_):
        text = registre[camp_valencia]
        referencia = registre[camp_catala]
        paraules_val = {p.lower() for p in _PARAULA.findall(text)}
        paraules_ref = {p.lower() for p in _PARAULA.findall(referencia)}
        trobades = paraules_val & ambiguitats.keys()
        for forma in trobades:
            indicatiu = ambiguitats[forma]["indicatiu"]
            subjuntiu = ambiguitats[forma]["subjuntiu"]
            en_ref_indicatiu = indicatiu in paraules_ref
            en_ref_subjuntiu = subjuntiu in paraules_ref
            if en_ref_indicatiu == en_ref_subjuntiu:
                # cap dels dos (probable substantiu, descartem) o
                # tots dos a la vegada (ambigu de veres en la pròpia
                # referència, no útil com a "veritat" automàtica)
                continue
            candidates.append({
                "id": registre[camp_id],
                "documento_id": registre.get(camp_doc, registre[camp_id]),
                "texto_valenciano": text,
                "texto_catalan_boe": referencia,
                "forma_ambigua": forma,
                "candidat_indicatiu": indicatiu,
                "candidat_subjuntiu": subjuntiu,
                "veritat_per_referencia": "indicatiu" if en_ref_indicatiu else "subjuntiu",
            })

    comptador = Counter(c["veritat_per_referencia"] for c in candidates)
    print(f"  {len(candidates)} frases amb forma ambigua I candidat confirmat en la referència (filtrats substantius)")
    print(f"  distribucio real: {dict(comptador)} -- el BOE (registre legal, ple de subordinades 'que') "
          f"esbiaixa fortament cap a subjuntiu, es mostreja ESTRATIFICAT per no amagar els casos indicatiu")

    random.seed(seed)
    # Mostreig ESTRATIFICAT per veritat_per_referencia: sense això, una
    # mostra a l'atzar eixiria quasi tota subjuntiu (97% dels casos reals
    # ho son, vore comentari dalt) i la comparativa A/B/C no detectaria si
    # una via simplement "sempre tria subjuntiu" en compte de mirar el
    # context de veres.
    per_classe: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        per_classe[c["veritat_per_referencia"]].append(c)

    cupo = -(-mostra // len(per_classe))
    triades: list[dict] = []
    for classe, llista in per_classe.items():
        random.shuffle(llista)
        vistes: set[str] = set()
        for c in llista:
            if c["forma_ambigua"] in vistes:
                continue
            vistes.add(c["forma_ambigua"])
            triades.append(c)
            if len(vistes) >= cupo:
                break

    random.shuffle(triades)
    triades = triades[:mostra]
    triades.sort(key=lambda c: (c["documento_id"], c["id"]))
    return triades


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mostra", type=int, default=25, help="Nombre de frases a seleccionar")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH, help="Fitxer font (per defecte, el corpus del BOE)")
    parser.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    parser.add_argument("--camp-valencia", default="texto_valenciano")
    parser.add_argument("--camp-catala", default="texto_catalan")
    parser.add_argument("--camp-id", default="id")
    parser.add_argument("--camp-doc", default="documento_id", help="Si el registre no el te, s'usa --camp-id")
    parser.add_argument("--salida", type=Path, default=SALIDA_MOSTRA)
    args = parser.parse_args()

    print("Calculant ambigüitats indicatiu/subjuntiu (1a persona) des de font_mauricio...")
    ambiguitats = calcula_ambiguitats()
    print(f"  {len(ambiguitats)} formes valencianes ambigües trobades")
    SALIDA_AMBIGUITATS.write_text(json.dumps(ambiguitats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Guardat: {SALIDA_AMBIGUITATS}")

    print(f"\nBuscant frases amb alguna d'estes formes en {args.corpus}...")
    mostra = troba_frases(
        ambiguitats, args.mostra, args.seed,
        corpus_path=args.corpus, format_=args.format,
        camp_valencia=args.camp_valencia, camp_catala=args.camp_catala,
        camp_id=args.camp_id, camp_doc=args.camp_doc,
    )
    args.salida.write_text(json.dumps(mostra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(mostra)} frases seleccionades (una per forma distinta com a molt)")
    print(f"  Guardat: {args.salida}")


if __name__ == "__main__":
    main()
