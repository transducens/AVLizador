"""
regenera_palabras_traducidas.py -- Reconstruye `palabras_traducidas.json`
a partir de la fuente OFICIAL (`diccionarios/lexico_general.json`,
19/10/2026), en vez del glosario viejo basado en Apertium
catala-castella (29/09/2026 i anteriors).

`palabras_traducidas.json` NO lo usa `traductor/` -- es un glosario
trilingue (valenciano/catalan/castellano) que consume directamente
`pipeline/05_corpus_boe/analizar_corpus.py` para contar cuantas veces
aparece cada forma valenciana/catalana en el corpus del BOE (informe de
pureza dialectal del corpus, no traduccion).

Decision explicita del usuario (19/10/2026): `lexico_general.json` NO
trae toponimos ni nombres propios (0 entradas `tipo: "v:top_gva"` en esta
entrega, a diferencia del fichero viejo que tenia 87 toponimos + 28
nombres) -- asi que esas 115 entradas se MANTIENEN tal cual del fichero
viejo (no hay fuente nueva que las sustituya), y solo la categoria
"palabra" (1.261 entradas en el fichero viejo) se reconstruye entera
desde la fuente oficial.

Uso:
    python regenera_palabras_traducidas.py            # reescribe palabras_traducidas.json
    python regenera_palabras_traducidas.py --check     # solo compara, no escribe (exit 1 si hay diferencias)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEXIC = Path(__file__).resolve().parent
LEXICO_GENERAL = LEXIC / "diccionarios" / "lexico_general.json"
DESTINO = LEXIC / "palabras_traducidas.json"


def _es_toponim(entrada: dict) -> bool:
    return entrada.get("tipo") == "v:top_gva"


def _es_pendent(entrada: dict) -> bool:
    return "PENDENT" in (entrada.get("tipo") or "")


def genera_entradas_palabra(path: Path = LEXICO_GENERAL) -> list[dict]:
    """Agrupa `lexico_general.json` por forma valenciana, recogiendo TODAS
    las alternativas catalanas/castellanas reales (a diferencia del motor
    de traduccion, que elige una sola via `canonica` -- aqui interesan
    todas para contar uso real en el corpus, no traducir).

    Excluye: `_PENDENT` (sin verificar), toponimos (0 en esta entrega,
    pero se comprueba por si acaso), entradas sin valenciano/catalan, y
    pares triviales donde valenciano == catalan (sin señal dialectal,
    nada que contar).
    """
    dades = json.loads(path.read_text(encoding="utf-8"))
    por_valenciano: dict[str, dict[str, list[str]]] = {}
    orden: list[str] = []
    for entrada in dades:
        if _es_pendent(entrada) or _es_toponim(entrada):
            continue
        valenciano = (entrada.get("valenciano") or "").strip()
        catalan = (entrada.get("catalan") or "").strip()
        espanol = (entrada.get("espanol") or "").strip()
        if not valenciano or not catalan:
            continue
        if valenciano.lower() == catalan.lower():
            continue
        clave = valenciano.lower()
        if clave not in por_valenciano:
            por_valenciano[clave] = {"valenciano": [], "catalan": [], "castellano": []}
            orden.append(clave)
        grupo = por_valenciano[clave]
        if valenciano not in grupo["valenciano"]:
            grupo["valenciano"].append(valenciano)
        if catalan not in grupo["catalan"]:
            grupo["catalan"].append(catalan)
        if espanol and espanol not in grupo["castellano"]:
            grupo["castellano"].append(espanol)

    entradas = []
    for clave in orden:
        grupo = por_valenciano[clave]
        linea_original = (
            f"{' / '.join(grupo['valenciano'])} - {' / '.join(grupo['catalan'])}"
            + (f" - {' / '.join(grupo['castellano'])}" if grupo["castellano"] else "")
        )
        entradas.append(
            {
                "valenciano": grupo["valenciano"],
                "catalan": grupo["catalan"],
                "castellano": grupo["castellano"],
                "categoria": "palabra",
                "linea_original": linea_original,
            }
        )
    return entradas


def regenera(check_only: bool = False) -> bool:
    actual = json.loads(DESTINO.read_text(encoding="utf-8"))
    conservadas = [e for e in actual["entradas"] if e.get("categoria") in ("toponimo", "nombre")]
    nuevas_palabra = genera_entradas_palabra()
    entradas = conservadas + nuevas_palabra

    nuevo = {
        "total_entradas": len(entradas),
        "total_sin_estructura": actual.get("total_sin_estructura", 0),
        "entradas": entradas,
        "sin_estructura": actual.get("sin_estructura", []),
    }

    antes_palabra = sum(1 for e in actual["entradas"] if e.get("categoria") == "palabra")
    cambia = antes_palabra != len(nuevas_palabra) or json.dumps(
        actual["entradas"], sort_keys=True, ensure_ascii=False
    ) != json.dumps(entradas, sort_keys=True, ensure_ascii=False)

    print(f"Topónimos/nombres conservados tal cual: {len(conservadas)}")
    print(f"Entradas 'palabra' -- antes: {antes_palabra}, ahora (desde lexico_general.json): {len(nuevas_palabra)}")
    print(f"Total entradas -- antes: {actual['total_entradas']}, ahora: {len(entradas)}")

    if not check_only and cambia:
        DESTINO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Escrito {DESTINO}")
    elif not cambia:
        print("Sin cambios.")

    return cambia


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Solo compara, no escribe (exit 1 si hay diferencias).")
    args = parser.parse_args(argv)

    cambia = regenera(check_only=args.check)
    if args.check:
        return 1 if cambia else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
