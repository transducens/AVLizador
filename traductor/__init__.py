"""
traductor -- Traductor dialectal valencià (occidental, norma AVL) → català
(oriental, norma IEC). No tradueix entre idiomes: convertix morfologia i
lèxic dins de la mateixa llengua.

Ús públic:
    from traductor import translate
    translate("Este xiquet és molt bo.")  # -> "Aquest xiquet és molt bo."

Des de la línia de comandes: `python -m traductor.cli "text"`.

Este paquet és el "pas 5" del projecte (vore final/05_motor_reglas/README.md):
ve DESPRÉS del corpus sintètic i el benchmark de selecció de model
(03_seleccion_de_modelo/), i està pensat per a viure com a mòdul independent -- no
depén en temps d'execució de cap altra carpeta del projecte (el lèxic es
copia a traductor/data/, no es llig de "02_reglas_dialectales/").

Estat (21/09): pas 1-2 fets (estructura + rules/__init__.py). La resta de
mòduls són placeholders documentats -- vore el TODO de cada fitxer per a
saber en quin pas s'implementen.
"""

from .translate import translate

__all__ = ["translate"]
