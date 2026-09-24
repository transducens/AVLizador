#!/usr/bin/env python3
"""genera_candidatos_benchmark.py -- Selecciona frases candidatas del corpus
real de la AVL para ampliar benchmark_corpus.json de 60 a 150 frases.

NO traduce nada ni escribe en benchmark_corpus.json directamente -- genera
un fichero aparte con las frases en valenciano (occidental) y el campo
"oriental" vacío, listo para que alguien con conocimiento de las dos normas
escriba la traducción a mano. Solo cuando decidas incorporarlas, se copian
al benchmark real.

Criterio de selección (no aleatorio):
1. Reutiliza EXACTAMENTE la misma segmentación de frases que
   genera_corpus_sintetico.py (misma función, mismos filtros de longitud),
   para que las candidatas sean representativas del corpus real que se usa
   para generar el corpus sintético -- no un criterio distinto inventado
   aquí.
2. Descarta las frases que ya están en benchmark_corpus.json (comparación
   exacta, normalizando apóstrofos y mayúsculas).
3. Puntúa cada frase por cuántas categorías DISTINTAS de reglas dialectales
   contiene (demostratius, possessius, numerals, gentilicis, pretèrit
   perifràstic, elisió amb h muda, subjuntiu, locucions) -- una frase que
   toca 3 reglas a la vez es más rentable de traducir a mano que una que no
   toca ninguna.
4. Reparte la selección por tipo de documento con un tope máximo por tipo,
   para no repetir el sesgo ya conocido del corpus (glossari+publicacions
   son casi dos tercios de las frases candidatas totales) -- ver
   documentacion/metodologia_y_resultados.md sección 8, "Registro
   concentrado".

Uso:
    python genera_candidatos_benchmark.py
    python genera_candidatos_benchmark.py --num-candidatos 90 --output benchmark_candidatos.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "04_corpus_sintetico"))
import genera_corpus_sintetico as gcs  # noqa: E402  (reutiliza la segmentacion real)
import evalua_models as em  # noqa: E402  (reutiliza normalitza_apostrofa)

BENCHMARK_PATH = BASE_DIR / "benchmark_corpus.json"
DEFAULT_OUTPUT = BASE_DIR / "benchmark_candidatos_ampliacion.json"

# ─── Marcadores de reglas dialectales (para puntuar candidatas) ────────────
# Cada patrón identifica la PRESENCIA de un tipo de regla en la frase -- no
# pretende ser exhaustivo ni 100% preciso (eso es cosa del prompt/motor de
# reglas reales); aquí solo sirve para priorizar qué merece la pena traducir
# a mano primero.
MARCADORS = {
    "demostratius_este": re.compile(r"\b(este|esta|estos|estes)\b", re.IGNORECASE),
    "demostratius_eixe": re.compile(r"\b(eixe|eixa|eixos|eixes)\b", re.IGNORECASE),
    "possessius": re.compile(r"\b(meua|meues|teua|teues|seua|seues)\b", re.IGNORECASE),
    "numeral_huit": re.compile(r"huit", re.IGNORECASE),
    "numeral_ordinal": re.compile(r"\b\w*(cinqu|sis|set|vuit|nov|des|dotz|vint|trent|quarant|cent)é\b", re.IGNORECASE),
    "numeral_dos_dues": re.compile(r"\bdos\b", re.IGNORECASE),
    "gentilici": re.compile(r"\b\w{4,}és\b", re.IGNORECASE),
    "preterit_simple": re.compile(r"\b\w+(à|aren)\b", re.IGNORECASE),
    "elisio_h_muda": re.compile(r"\b(de|la|el)\s+h(isenda|ivern|ome|ora|istòria|armonia)", re.IGNORECASE),
    "subjuntiu_ga": re.compile(r"\b(puga|tinga|vinga|vaja|siga|haja|puguen|tinguen|siguen|hagen)\b", re.IGNORECASE),
    "locucions": re.compile(r"\b(a on|hui dia|ha sigut|han sigut|havia sigut)\b", re.IGNORECASE),
}

# Tope máximo de candidatas por tipo de documento, para no repetir el sesgo
# ya conocido del corpus (glossari/publicacions dominan el total de frases).
TOPE_POR_TIPO = {
    "glossari": 20,
    "publicacions": 15,
    "acord-normatiu": 15,
    "gramatica_normativa": 15,
    "legislacio": 12,
    "notes-de-premsa": 10,
    "butlleti": 8,
    "pagina": 6,
    "post": 6,
    "escriptors": 4,
    "salutacio": 2,
}


def normalitza_clau(frase: str) -> str:
    return em.normalitza_apostrofa(frase).strip().lower()


def carrega_frases_ja_usades() -> set[str]:
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        actual = json.load(f)
    return {normalitza_clau(r["occidental"]) for r in actual}


def puntua_frase(frase: str) -> tuple[int, list[str]]:
    categories = [nom for nom, patro in MARCADORS.items() if patro.search(frase)]
    return len(categories), categories


def selecciona(registre: dict, ja_usades: set[str], num_candidatos: int) -> list[dict]:
    candidates_per_tipus: dict[str, list[dict]] = defaultdict(list)

    for fu in registre.values():
        clau = normalitza_clau(fu.frase_val)
        if clau in ja_usades:
            continue
        puntuacio, categories = puntua_frase(fu.frase_val)
        if puntuacio == 0:
            continue  # no toca ninguna regla dialectal conocida -- no aporta como test
        candidates_per_tipus[fu.doc_type].append({
            "doc_id": fu.doc_id,
            "doc_type": fu.doc_type,
            "source_url": fu.source_url,
            "occidental": fu.frase_val,
            "puntuacio": puntuacio,
            "categories": categories,
        })

    # dentro de cada tipo, las de mayor puntuacion (mas reglas a la vez) primero
    for tipus in candidates_per_tipus:
        candidates_per_tipus[tipus].sort(key=lambda c: c["puntuacio"], reverse=True)

    seleccio: list[dict] = []
    for tipus, candidates in candidates_per_tipus.items():
        tope = TOPE_POR_TIPO.get(tipus, 5)
        seleccio.extend(candidates[:tope])

    # si con los topes no llegamos al numero pedido, rellena con lo que quede
    # mejor puntuado de cualquier tipo (mejor tener 90 frases utiles que
    # menos por ser demasiado estrictos con el reparto)
    if len(seleccio) < num_candidatos:
        ya_elegidas = {c["doc_id"] + c["occidental"] for c in seleccio}
        resto = [
            c
            for tipus, candidates in candidates_per_tipus.items()
            for c in candidates[TOPE_POR_TIPO.get(tipus, 5):]
            if c["doc_id"] + c["occidental"] not in ya_elegidas
        ]
        resto.sort(key=lambda c: c["puntuacio"], reverse=True)
        seleccio.extend(resto[: num_candidatos - len(seleccio)])

    seleccio.sort(key=lambda c: c["puntuacio"], reverse=True)
    return seleccio[:num_candidatos]


def main():
    parser = argparse.ArgumentParser(description="Selecciona frases candidatas para ampliar el benchmark")
    parser.add_argument("--input", default=str(gcs.DEFAULT_INPUT), help="Corpus fuente en valencià (jsonl)")
    parser.add_argument("--num-candidatos", type=int, default=90, help="Cuantas candidatas generar (60 actuales + esto = objetivo)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--min-paraules", type=int, default=5)
    parser.add_argument("--min-caracters", type=int, default=20)
    parser.add_argument("--max-caracters", type=int, default=280)
    args = parser.parse_args()

    print(f"Cargando corpus fuente: {args.input}")
    registre, docs_per_tipus, _ = gcs.carrega_frases_uniques(
        Path(args.input), args.min_paraules, args.min_caracters, args.max_caracters
    )
    print(f"  {len(registre)} frases únicas candidatas en el corpus completo")

    ja_usades = carrega_frases_ja_usades()
    print(f"  {len(ja_usades)} frases ya están en benchmark_corpus.json (se excluyen)")

    seleccio = selecciona(registre, ja_usades, args.num_candidatos)

    salida = []
    for i, c in enumerate(seleccio, start=61):
        salida.append({
            "id": f"RC{i:03d}",
            "doc_id": c["doc_id"],
            "doc_type": c["doc_type"],
            "source_url": c["source_url"],
            "categories_detectadas": c["categories"],
            "occidental": c["occidental"],
            "oriental": "",
        })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print(f"\n{len(salida)} candidatas escritas en {args.output}")
    print("Campo 'oriental' vacío -- rellénalo a mano antes de incorporarlas a benchmark_corpus.json.")

    print("\nReparto por tipo de documento:")
    resumen = Counter(c["doc_type"] for c in salida)
    for tipus, n in resumen.most_common():
        print(f"  {tipus:<25} {n:>3}")

    print("\nReparto por nº de reglas dialectales detectadas por frase:")
    resumen_puntuacio = Counter(len(c["categories_detectadas"]) for c in salida)
    for puntuacio in sorted(resumen_puntuacio, reverse=True):
        print(f"  {puntuacio} regla(s): {resumen_puntuacio[puntuacio]} frases")


if __name__ == "__main__":
    main()
