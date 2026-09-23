"""
combina_resultats.py -- Genera un informe comparatiu combinant els fitxers
benchmark_<model>_<timestamp>.json que deixa cada procés evalua_models.py
llançat per separat (un per GPU) a comparar_salamandraTA_gemma.sh.

evalua_models.py ja sap fer un informe comparatiu quan avalua diversos
models en UNA sola execució -- este script fa el mateix però llegint els
resultats de VARIES execucions independents en paral·lel.

US:
    # Combina tot el que s'haja generat en les últimes 4 hores (per defecte)
    python combina_resultats.py --resultats-dir ../resultats

    # Finestra de temps diferent
    python combina_resultats.py --resultats-dir ../resultats --minuts 60

    # Fitxers concrets, sense dependre de l'hora
    python combina_resultats.py --fitxers ../resultats/benchmark_A.json ../resultats/benchmark_B.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evalua_models import genera_informe_comparatiu  # reutilitza la mateixa taula/format


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resultats-dir", default=str(Path(__file__).resolve().parent.parent / "resultats"),
        help="Carpeta amb els benchmark_*.json (per defecte evalua_modelos/resultats)"
    )
    parser.add_argument(
        "--minuts", type=float, default=240,
        help="Inclou només fitxers modificats en els darrers N minuts (per defecte 240)"
    )
    parser.add_argument(
        "--fitxers", nargs="*", default=None,
        help="Si es dona, ignora --resultats-dir/--minuts i usa exactament estos fitxers"
    )
    parser.add_argument(
        "--salida", default=None,
        help="Fitxer on guardar l'informe, a més d'imprimir-lo per pantalla"
    )
    args = parser.parse_args()

    if args.fitxers:
        rutes = [Path(f) for f in args.fitxers]
    else:
        resultats_dir = Path(args.resultats_dir)
        llindar = time.time() - args.minuts * 60
        rutes = sorted(
            p for p in resultats_dir.glob("benchmark_*.json")
            if p.stat().st_mtime >= llindar
        )

    if not rutes:
        print("No s'ha trobat cap fitxer de resultats recent. "
              "Puja --minuts o passa --fitxers explícitament.")
        sys.exit(1)

    resultats = []
    for ruta in rutes:
        with open(ruta, encoding="utf-8") as f:
            resultats.append(json.load(f))
        print(f"Carregat: {ruta.name}")

    informe = genera_informe_comparatiu(resultats)
    print("\n" + informe)

    if args.salida:
        Path(args.salida).write_text(informe, encoding="utf-8")
        print(f"\nInforme guardat a {args.salida}")


if __name__ == "__main__":
    main()
