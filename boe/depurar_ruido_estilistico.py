#!/usr/bin/env python3
"""Separa de `corpus_entrenamiento.jsonl` dos categorias de "ruido" que NO
son diferencia dialectal ni error de alineamiento, sino convenciones de
estilo/formato de un traductor concreto (conversacion 02-05/10/2026 sobre
"estilo del traductor" vs. variacion dialectal real):

  - "solo_mayusculas": las dos frases tienen EXACTAMENTE las mismas
    palabras en el mismo orden, solo difieren en mayusculas/minusculas
    (ej. "Llei Organica" vs "llei organica" en titulos de ley). Deteccion
    100% segura: normalizar a minusculas y comparar lista de tokens.
  - "reordenament_pur": las dos frases tienen EXACTAMENTE el mismo
    multiconjunto de palabras, pero en orden distinto (ej. "eixos
    seguents" vs "seguents eixos" -- anteposicion/posposicion del
    adjetivo, una preferencia de estilo sistematica, no gramatica
    dialectal). Deteccion 100% segura: normalizar y comparar con
    Counter (ignora orden).

NO se tocan los ficheros originales de `../dades/boe/` -- esto escribe en
`../dades/boe_net/`, aparte, para poder comparar y para no perder nunca
el dato de origen si algun dia se quiere revisar el criterio.

Uso:
    python depurar_ruido_estilistico.py
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BOE_DIR.parent / "dades" / "boe"
NET_DIR = BOE_DIR.parent / "dades" / "boe_net"

ENTRADA_PATH = CORPUS_DIR / "corpus_entrenamiento.jsonl"
SALIDA_NET = NET_DIR / "corpus_entrenamiento_net.jsonl"
SALIDA_DESCARTADOS = NET_DIR / "descartados_estilo.jsonl"

sys.path.insert(0, str(BOE_DIR))
from alinear_corpus_bleualign import PATRON_TOKEN, normalizar  # noqa: E402

MIN_PALABRAS_REORDENAMIENTO = 4  # frases muy cortas dan falsos positivos (ver conversacion)

PATRON_TOKEN_COMPLETO = re.compile(r"[^\W\d_]+(?:[-'·][^\W\d_]+)*|\d+|\s+|.", re.UNICODE | re.DOTALL)
MAX_TOKENS_SUSTITUCION = 4


def _es_palabra(token: str) -> bool:
    return bool(token) and token[0].isalpha()


def clasificar(fc: str, fv: str) -> str:
    """Devuelve 'identica', 'solo_mayusculas', 'reordenament_pur' o 'net'
    (diferencia real, candidata a dialectal o a revisar a mano)."""
    if fc.strip() == fv.strip():
        return "identica"
    tc = PATRON_TOKEN.findall(normalizar(fc))
    tv = PATRON_TOKEN.findall(normalizar(fv))
    if tc == tv:
        return "solo_mayusculas"
    if len(tc) >= MIN_PALABRAS_REORDENAMIENTO and Counter(tc) == Counter(tv):
        return "reordenament_pur"
    return "net"


def extraer_pares(fc: str, fv: str, contador_pares: Counter, ejemplo_por_par: dict) -> None:
    """Mismo mecanismo que `analizar_diff_textual` en analizar_corpus.py,
    simplificado para trabajar sobre un par de frases suelto (no hace
    falta la estructura de parrafos: aqui cada registro YA es una frase
    alineada por Bleualign)."""
    disp_c = PATRON_TOKEN_COMPLETO.findall(fc)
    disp_v = PATRON_TOKEN_COMPLETO.findall(fv)
    norm_c = [normalizar(t) for t in disp_c]
    norm_v = [normalizar(t) for t in disp_v]
    sm = difflib.SequenceMatcher(None, norm_c, norm_v, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace":
            continue
        palabras_c = tuple(t for t in norm_c[i1:i2] if _es_palabra(t))
        palabras_v = tuple(t for t in norm_v[j1:j2] if _es_palabra(t))
        if not (palabras_c and palabras_v):
            continue
        if len(palabras_c) > MAX_TOKENS_SUSTITUCION or len(palabras_v) > MAX_TOKENS_SUSTITUCION:
            continue
        clave = (palabras_c, palabras_v)
        contador_pares[clave] += 1
        ejemplo_por_par.setdefault(clave, (fc, fv))


def main() -> None:
    if not ENTRADA_PATH.exists():
        raise SystemExit(f"No existe {ENTRADA_PATH}; ejecuta primero exportar_entrenamiento.py")
    NET_DIR.mkdir(parents=True, exist_ok=True)

    contador = Counter()
    contador_pares: Counter = Counter()
    ejemplo_por_par: dict = {}

    with open(ENTRADA_PATH, encoding="utf-8") as entrada, \
         open(SALIDA_NET, "w", encoding="utf-8") as salida_net, \
         open(SALIDA_DESCARTADOS, "w", encoding="utf-8") as salida_descartados:
        for linea in entrada:
            registro = json.loads(linea)
            fc, fv = registro["texto_catalan"], registro["texto_valenciano"]
            motivo = clasificar(fc, fv)
            contador[motivo] += 1
            if motivo in ("identica", "net"):
                salida_net.write(json.dumps(registro, ensure_ascii=False) + "\n")
                if motivo == "net":
                    extraer_pares(fc, fv, contador_pares, ejemplo_por_par)
            else:
                salida_descartados.write(
                    json.dumps({**registro, "motivo_descarte": motivo}, ensure_ascii=False) + "\n"
                )

    total = sum(contador.values())
    conservados = contador["identica"] + contador["net"]
    print(f"Total pares de entrada: {total}")
    for motivo in ("identica", "net", "solo_mayusculas", "reordenament_pur"):
        n = contador[motivo]
        print(f"  {motivo}: {n} ({100*n/total:.1f}%)")
    print(f"Guardado neto:       {SALIDA_NET} ({conservados} pares)")
    print(f"Guardado descartados: {SALIDA_DESCARTADOS} ({total - conservados} pares)")

    print()
    print("--- Re-analisis: pares de sustitucion distintos en el corpus neto ---")
    filas = sorted(contador_pares.items(), key=lambda kv: -kv[1])
    total_instancias = sum(n for _, n in filas)
    print(f"Pares distintos: {len(filas)}  (instancias totales: {total_instancias})")
    print("Top 20 por frecuencia:")
    for (cat_tok, val_tok), frecuencia in filas[:20]:
        print(f"  {' '.join(cat_tok)!r:30s} -> {' '.join(val_tok)!r:30s} frec={frecuencia}")


if __name__ == "__main__":
    main()
