#!/usr/bin/env python3
"""Utilidades de texto compartidas por analizar_corpus.py y
alinear_corpus_bleualign.py: segmentacion en parrafo/frase (mismo
esquema que usaba construir_frases.py) y deteccion de contenido tabular
(presupuestos, aranceles, formularios) que no aporta como prosa.
"""

from __future__ import annotations

import re

PATRON_FIN_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀÈÉÍÒÓÚÜÇ«\"(0-9])")


def segmentar_parrafos(texto: str) -> list[str]:
    return [p.strip() for p in texto.split("\n\n") if p.strip()]


def segmentar_parrafo(parrafo: str) -> list[str]:
    trozos = PATRON_FIN_FRASE.split(parrafo.strip())
    return [t.strip() for t in trozos if t.strip()]


PATRON_PUNTOS_LIDER = re.compile(r"\.\s*\.\s*\.\s*\.")
UMBRAL_RATIO_LETRAS = 0.55
LONGITUD_MINIMA_TABLA = 8


def es_tabla(parrafo: str) -> bool:
    """Heuristica de dos senyales, calibrada sobre el corpus real (ver
    README): un parrafo se considera tabla/formulario, no prosa, si tiene
    puntos-guia (".  .  .  .", el BOE los usa para alinear visualmente una
    etiqueta con un numero en presupuestos/aranceles) o si la proporcion de
    letras sobre caracteres no-espacio es baja (filas de tabla — sueldos,
    coeficientes, codigos arancelarios — son casi todo cifras; la prosa
    legal normal se mantiene claramente por encima aunque cite varios
    numeros en la misma frase).

    Comprobado sobre 188.813 parrafos del corpus: marca el 1,1% (2.134),
    concentrados en 126/521 documentos (presupuestos, aranceles,
    formularios); en una muestra de 20 al azar de lo marcado, cero falsos
    positivos (todo tabla real, formularios en blanco tipo "Sexe: ......",
    o ejes de grafica tipo "0 200 400 600 800")."""
    parrafo = parrafo.strip()
    if len(parrafo) < LONGITUD_MINIMA_TABLA:
        return False
    if PATRON_PUNTOS_LIDER.search(parrafo):
        return True
    sin_espacios = parrafo.replace(" ", "")
    if not sin_espacios:
        return False
    letras = sum(c.isalpha() for c in sin_espacios)
    return (letras / len(sin_espacios)) < UMBRAL_RATIO_LETRAS
