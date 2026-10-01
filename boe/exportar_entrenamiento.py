#!/usr/bin/env python3
"""Filtra ../dades/boe/corpus_bleualign.jsonl a un subconjunto limpio para
entrenamiento: ../dades/boe/corpus_entrenamiento.jsonl.

No se aplica un unico umbral de similitud (Jaccard sobre palabras
normalizadas) porque la zona baja de esa metrica mezcla dos cosas muy
distintas que un solo numero no puede separar:

  - Pares dialectales legitimos donde las dos formas no comparten raiz
    (huit/vuit, dinovena/denou, cinquanta-cinque/cinquanta-cinc): son
    exactamente el tipo de correspondencia "dificil" que interesa para
    entrenar, y dan similitud muy baja o 0 aunque el emparejamiento sea
    perfecto.
  - Emparejamientos realmente equivocados (casi siempre en tablas/
    aranceles que el filtro de texto_comun.es_tabla no pudo distinguir
    por estar fusionados con prosa): la senal que SI los distingue de los
    anteriores no es la similitud, es que las dos frases tienen una
    longitud muy distinta (ratio de longitud >> 1), porque no son en
    realidad la misma unidad de contenido.

Regla de dos niveles, validada a mano sobre casos conocidos:
  1. similitud >= UMBRAL_SEGURO: se queda siempre.
  2. si no, se rescata solo si las dos frases tienen palabras reales (no
     son solo numeros/marcas de lista) Y su longitud es parecida
     (ratio <= RATIO_LONGITUD_MAXIMO). El resto (sin palabras reales en
     algun lado, o con longitud muy dispar) se descarta.

Sobre el corpus completo (302.977 pares): 266.393 pasan el paso 1,
2.342 se rescatan en el paso 2, 352 se descartan por longitud dispar y
33.890 por no tener palabras reales en algun lado — total 268.735 (88,7%).

Uso:
    python exportar_entrenamiento.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOE_DIR = Path(__file__).resolve().parent
# Los datos del BOE ahora viven en dades/boe/ (junto a los del resto de
# fuentes del proyecto), no dentro de boe/ como antes.
CORPUS_DIR = BOE_DIR.parent / "dades" / "boe"
ENTRADA_PATH = CORPUS_DIR / "corpus_bleualign.jsonl"
SALIDA_PATH = CORPUS_DIR / "corpus_entrenamiento.jsonl"

sys.path.insert(0, str(BOE_DIR))
from alinear_corpus_bleualign import PATRON_TOKEN, normalizar  # noqa: E402

UMBRAL_SEGURO = 0.3
RATIO_LONGITUD_MAXIMO = 2.0


def tiene_palabras(texto: str) -> bool:
    return bool(PATRON_TOKEN.findall(normalizar(texto)))


def ratio_longitud(a: str, b: str) -> float:
    la, lb = len(a), len(b)
    if min(la, lb) == 0:
        return float("inf")
    return max(la, lb) / min(la, lb)


def se_conserva(registro: dict) -> tuple[bool, str]:
    if registro["similitud"] >= UMBRAL_SEGURO:
        return True, "seguro"
    a, b = registro["texto_catalan"], registro["texto_valenciano"]
    if not (tiene_palabras(a) and tiene_palabras(b)):
        return False, "sin_palabras_reales"
    if ratio_longitud(a, b) > RATIO_LONGITUD_MAXIMO:
        return False, "longitud_dispar"
    return True, "rescatado"


def main() -> None:
    if not ENTRADA_PATH.exists():
        raise SystemExit(f"No existe {ENTRADA_PATH}; ejecuta primero alinear_corpus_bleualign.py")

    contador = {"seguro": 0, "rescatado": 0, "sin_palabras_reales": 0, "longitud_dispar": 0}
    total = 0

    with open(ENTRADA_PATH, encoding="utf-8") as entrada, open(SALIDA_PATH, "w", encoding="utf-8") as salida:
        for linea in entrada:
            registro = json.loads(linea)
            total += 1
            conservar, motivo = se_conserva(registro)
            contador[motivo] += 1
            if conservar:
                salida.write(json.dumps(registro, ensure_ascii=False) + "\n")

    conservados = contador["seguro"] + contador["rescatado"]
    print(f"Total pares de entrada: {total}")
    print(f"  Seguros (similitud >= {UMBRAL_SEGURO}): {contador['seguro']}")
    print(f"  Rescatados (similitud baja, palabras reales, longitud parecida): {contador['rescatado']}")
    print(f"  Descartados por longitud dispar (ratio > {RATIO_LONGITUD_MAXIMO}): {contador['longitud_dispar']}")
    print(f"  Descartados por no tener palabras reales en algun lado: {contador['sin_palabras_reales']}")
    print(f"Guardado: {SALIDA_PATH} ({conservados} pares, {100*conservados/total:.1f}% del total)")


if __name__ == "__main__":
    main()
