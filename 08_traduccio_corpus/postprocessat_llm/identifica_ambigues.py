#!/usr/bin/env python3
"""Identifica l'ambiguitat 1a persona present indicatiu/subjuntiu
(p.ex. valencia "plantege" -> catala "plantejo" indicatiu / "plantegi"
subjuntiu) a partir de les 4 fonts crues de Mauricio, i localitza frases
reals del BOE on apareix -- mostra de prova per a comparar les 3 vies de
postprocessat amb LLM (A/B/C, vore conversa 06/10/2026).

Per que este patro i no un altre: ConjugacionsDictRule EXCLOU del lookup
qualsevol forma marcada "problematica" (vore traductor/rules/conjugacions_dict.py),
que inclou este cas entre altres. Este script aïlla NOMÉS el subconjunt
on dos candidats catalans comparteixen arrel i un acaba en "-o" (present
indicatiu, 1a pers. sg.) i l'altre en "-i" (present subjuntiu, 1a pers.
sg.) -- el cas EXACTE que l'usuari ha demanat etiquetar ("jo plantejo" /
"jo plantege"), ignorant la resta de formes "problematica" (locucions
fixes, col·lisions homografes amb substantius, etc.) que no son este
fenomen.

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
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARREL = Path(__file__).resolve().parent.parent.parent
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


def calcula_ambiguitats() -> dict[str, dict[str, str]]:
    """Torna {forma_valenciana: {"indicatiu": ..., "subjuntiu": ...}} per a
    totes les formes on, entre les 4 fonts de Mauricio, hi ha EXACTAMENT 2
    traduccions catalanes candidates que comparteixen arrel i difereixen
    només en la vocal final -o (indicatiu) / -i (subjuntiu)."""
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


_PARAULA = re.compile(r"[a-zàèéíòóúïüç']+", re.IGNORECASE)


def troba_frases(ambiguitats: dict[str, dict[str, str]], mostra: int, seed: int) -> list[dict]:
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
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for linia in f:
            registre = json.loads(linia)
            text = registre["texto_valenciano"]
            referencia = registre["texto_catalan"]
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
                    "id": registre["id"],
                    "documento_id": registre["documento_id"],
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
    args = parser.parse_args()

    print("Calculant ambigüitats indicatiu/subjuntiu (1a persona) des de font_mauricio...")
    ambiguitats = calcula_ambiguitats()
    print(f"  {len(ambiguitats)} formes valencianes ambigües trobades")
    SALIDA_AMBIGUITATS.write_text(json.dumps(ambiguitats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Guardat: {SALIDA_AMBIGUITATS}")

    print("\nBuscant frases reals del BOE amb alguna d'estes formes...")
    mostra = troba_frases(ambiguitats, args.mostra, args.seed)
    SALIDA_MOSTRA.write_text(json.dumps(mostra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(mostra)} frases seleccionades (una per forma distinta com a molt)")
    print(f"  Guardat: {SALIDA_MOSTRA}")


if __name__ == "__main__":
    main()
