#!/usr/bin/env python3
"""Alinea ../dades/boe/corpus.json por similitud de texto usando Bleualign,
en vez de por coincidencia exacta de conteo de parrafos/frases (eso
descarta documentos enteros por una sola discrepancia, aunque el 95% del
documento sea perfectamente paralelo: a veces el preambulo de una version
tiene parrafos explicativos que la otra simplemente no tiene, contenido
realmente distinto, no un fallo de extraccion).

Antes de generar las frases de cada documento se descartan los parrafos
tabulares (presupuestos, aranceles, formularios: ver
texto_comun.es_tabla) — no son prosa, y colarlos solo da a Bleualign
contenido casi todo numerico donde no tiene con que emparejar bien.

Bleualign (Sennrich & Volk, 2010: "MT-based Sentence Alignment for
OCR-generated Parallel Texts") esta pensado para pares de idiomas
DISTINTOS: necesita una traduccion automatica de un lado al idioma del
otro para poder comparar por solapamiento de n-gramas (BLEU). Aqui no
hace falta traducir nada de verdad: catala y valencia comparten la
inmensa mayoria del vocabulario, asi que se usa **el propio texto catala
como si fuera su traduccion al valencia** (identidad).

Algoritmo de Bleualign (visto en su codigo, bleualign/align.py):
  1. Puntua cada frase candidata por BLEU (solapamiento de n-gramas) y
     busca, con programacion dinamica, el camino monotono (nunca hacia
     atras) que maximiza la similitud total, saltando una frase sin
     pareja cuando no compensa quedarsela.
  2. Relleno de huecos: para lo que la fase 1 deja sin emparejar, prueba
     agrupar N frases seguidas de un lado contra 1 del otro si eso mejora
     el BLEU (heuristica "bleu1to1"/N-a-1), y como ultimo recurso, para
     huecos pequenyos, aplica el algoritmo Gale-Church CLASICO (basado en
     longitud, no en texto) tal cual se publico en 1993.

Requiere el paquete `bleualign` (ver requirements.txt):
    pip install git+https://github.com/rsennrich/Bleualign.git

Salida: ../dades/boe/corpus_bleualign.jsonl. Bleualign no expone
directamente su puntuacion BLEU interna por par via su API sencilla, asi
que el campo "similitud" de cada registro se recalcula con solapamiento
de palabras normalizadas (Jaccard) sobre el par que Bleualign decide —
sirve para filtrar por calidad al usarlo como datos de entrenamiento, con
un matiz importante: un par con similitud 0.0 no siempre es un error (ver
metodologia en README.md).

Uso:
    python alinear_corpus_bleualign.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOE_DIR = Path(__file__).resolve().parent
# Los datos del BOE ahora viven en dades/boe/ (junto a los del resto de
# fuentes del proyecto), no dentro de boe/ como antes.
CORPUS_DIR = BOE_DIR.parent / "dades" / "boe"
ENTRADA_PATH = CORPUS_DIR / "corpus.json"
SALIDA_PATH = CORPUS_DIR / "corpus_bleualign.jsonl"

sys.path.insert(0, str(BOE_DIR))
from texto_comun import es_tabla, segmentar_parrafo, segmentar_parrafos  # noqa: E402

try:
    from bleualign.align import Aligner
except ImportError as exc:
    raise SystemExit(
        "Falta el paquete 'bleualign'. Instala con:\n"
        "  pip install git+https://github.com/rsennrich/Bleualign.git"
    ) from exc

PATRON_TOKEN = re.compile(r"[^\W\d_]+(?:[-'·][^\W\d_]+)*", re.UNICODE)


def normalizar(texto: str) -> str:
    return texto.replace("’", "'").replace("‘", "'").lower()


def similitud_jaccard(a: str, b: str) -> float:
    ta = frozenset(PATRON_TOKEN.findall(normalizar(a)))
    tb = frozenset(PATRON_TOKEN.findall(normalizar(b)))
    if not ta or not tb:
        return 0.0
    interseccion = len(ta & tb)
    if interseccion == 0:
        return 0.0
    return interseccion / len(ta | tb)


def frases_documento(texto: str) -> list[str]:
    """Frases del documento, excluyendo los parrafos tabulares (presupuestos,
    aranceles, formularios: ver texto_comun.es_tabla) antes de segmentar en
    frases — asi ni siquiera llegan a Bleualign, en vez de colar
    alineaciones de baja calidad sobre contenido que no es prosa."""
    return [
        f
        for parrafo in segmentar_parrafos(texto)
        if not es_tabla(parrafo)
        for f in segmentar_parrafo(parrafo)
    ]


def alinear_con_bleualign(frases_cat: list[str], frases_val: list[str]) -> list[tuple[str, str]]:
    if not frases_cat or not frases_val:
        return []
    opciones = {
        "srcfile": frases_cat,
        "targetfile": frases_val,
        # el propio catala como "traduccion" al valencia (ver docstring del modulo)
        "srctotarget": [frases_cat],
        "verbosity": 0,
    }
    aligner = Aligner(opciones)
    aligner.mainloop()
    salida_cat, salida_val = aligner.results()
    lineas_cat = salida_cat.getvalue().splitlines()
    lineas_val = salida_val.getvalue().splitlines()
    return list(zip(lineas_cat, lineas_val))


def main() -> None:
    if not ENTRADA_PATH.exists():
        raise SystemExit(f"No existe {ENTRADA_PATH}; ejecuta primero construir_corpus.py")

    corpus = json.loads(ENTRADA_PATH.read_text(encoding="utf-8"))
    print(f"Alineando {len(corpus)} documentos con Bleualign...")

    total_pares = 0
    total_frases_cat = 0
    total_parrafos_tabla = 0
    documentos_con_pareja = 0
    documentos_con_error = []

    with open(SALIDA_PATH, "w", encoding="utf-8") as salida:
        for indice_doc, doc in enumerate(corpus):
            parrafos_cat = segmentar_parrafos(doc["catalan"]["texto"])
            total_parrafos_tabla += sum(1 for p in parrafos_cat if es_tabla(p))

            frases_cat = frases_documento(doc["catalan"]["texto"])
            frases_val = frases_documento(doc["valenciano"]["texto"])
            total_frases_cat += len(frases_cat)

            try:
                pares = alinear_con_bleualign(frases_cat, frases_val)
            except Exception as exc:  # bleualign puede fallar en casos limite (documento vacio, etc.)
                documentos_con_error.append((doc["id"], str(exc)))
                continue

            if pares:
                documentos_con_pareja += 1

            for indice_par, (fc, fv) in enumerate(pares, start=1):
                registro = {
                    "id": f"{doc['id']}-{indice_par:04d}",
                    "documento_id": doc["id"],
                    "fecha": doc["fecha"],
                    "texto_catalan": fc,
                    "texto_valenciano": fv,
                    "similitud": round(similitud_jaccard(fc, fv), 3),
                }
                salida.write(json.dumps(registro, ensure_ascii=False) + "\n")
                total_pares += 1

            if (indice_doc + 1) % 50 == 0:
                print(f"  {indice_doc + 1}/{len(corpus)} documentos procesados...")

    print(f"Parrafos tabulares excluidos antes de segmentar en frases (catalan): {total_parrafos_tabla}")
    print(f"Documentos con al menos un par alineado: {documentos_con_pareja} / {len(corpus)}")
    if documentos_con_error:
        print(f"Documentos con error (omitidos): {len(documentos_con_error)}")
        for doc_id, error in documentos_con_error[:10]:
            print(f"  {doc_id}: {error}")
    print(f"Guardado: {SALIDA_PATH} ({total_pares} pares de frase)")


if __name__ == "__main__":
    main()
