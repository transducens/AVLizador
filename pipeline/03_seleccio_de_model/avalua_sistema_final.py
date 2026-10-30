"""Avalua el SISTEMA FINAL cat->val (motor + FLOR-760M) en tots els
benchmarks d'una vegada, amb totes les mètriques (exactes, BLEU, chrF,
chrF++, TER i WER), i escriu una taula resum.

Des del 30/10/2026 és una drecera a `avlizador avalua` (el codi viu al
paquet, `src/avlizador/avaluacio/avalua.py`, i llig els benchmarks de
`dades/benchmarks/`); l'única diferència és que els resultats van a
`resultats/` d'esta carpeta. Mateixes opcions:

    python avalua_sistema_final.py                    # tots els benchmarks
    python avalua_sistema_final.py --benchmarks manual_boe manual_avl
    python avalua_sistema_final.py --motor            # també el motor sol, per a comparar
    python avalua_sistema_final.py --limit 5          # prova ràpida (5 frases per benchmark)
    python avalua_sistema_final.py --llista           # mostra els benchmarks disponibles

Eixida en `resultats/`: `sistema_final_<benchmark>_<data>.json` per
benchmark (i `motor_<benchmark>_<data>.json` amb `--motor`) i
`resum_<data>.md`, la taula per a copiar-la a
`resultats_benchmarks_cat_val.md`. La columna "Errors" ha de ser 0.
"""

import sys
from pathlib import Path

from avlizador.avaluacio.avalua import main

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--eixida" not in argv:
        argv += ["--eixida", str(Path(__file__).resolve().parent / "resultats")]
    sys.exit(main(argv))
