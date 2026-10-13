"""
traductor -- Traductor dialectal valencià (occidental, norma AVL) ↔ català
(oriental, norma IEC). No tradueix entre idiomes: convertix morfologia i
lèxic dins de la mateixa llengua.

Ús públic:
    from traductor import translate, translate_cat_val
    translate("Este xiquet és molt bo.")           # -> "Aquest xiquet és molt bo."
    translate_cat_val("Aquest xiquet és molt bo.")  # -> "Este xiquet és molt bo."

Des de la línia de comandes: `python -m traductor.cli "text"` (vore
`cli.py` per al flag `--direccio`).

Este paquet és el "pas 5" del projecte (vore final/05_motor_reglas/README.md):
ve DESPRÉS del corpus sintètic i el benchmark de selecció de model
(03_seleccio_de_model/), i està pensat per a viure com a mòdul independent -- no
depén en temps d'execució de cap altra carpeta del projecte (el lèxic es
copia a traductor/data/, no es llig de "02_regles_dialectals/").

Direcció inversa (`translate_cat_val`, afegida 08/10/2026): vore
`documentacio/hoja_de_ruta_traductor_invers.md` i
`traductor/rules/cat_val/README.md` per a l'abast actual (encara en
construcció -- Fase 0/1 de la hoja de ruta) i les limitacions conegudes.
"""

from .translate import translate
from .translate_invers import translate_cat_val

__all__ = ["translate", "translate_cat_val"]
