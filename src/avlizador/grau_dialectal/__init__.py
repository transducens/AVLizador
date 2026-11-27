"""Grau Dialectal (GD) i els seus dos índexs simètrics, GDV i GDC.

- GD (`gd.py`): de 0 (català oriental) a 1 (valencià occidental), comptant
  només les paraules marcades dialectalment.
- GDV (`gdv.py`): 1 - orientals / paraules; de 0 a 1 (valencià pur).
- GDC (`gdc.py`): 1 - occidentals / paraules; de 0 a 1 (català pur).

Els marcadors ixen dels mateixos diccionaris que el traductor
(`avlizador.traductor_cat_val`). Ús:

    from avlizador.grau_dialectal import calcula_gd, calcula_gdv, calcula_gdc
    calcula_gd("Este xiquet vol vindre hui.")["gd"]  # -> 1.0

`resalta_html(text)` torna el text en HTML amb els marcadors resaltats
(accessible: el dialecte de cada marcador també va en text per al lector
de pantalla).

Des de la línia d'ordres: `avlizador gd|gdv|gdc --text "..."`.
"""

from .gd import calcula_gd, resalta_html
from .gdc import calcula_gdc, calcula_gdc_corpus
from .gdv import calcula_gdv, calcula_gdv_corpus

__all__ = ["calcula_gd", "calcula_gdv", "calcula_gdv_corpus", "calcula_gdc", "calcula_gdc_corpus", "resalta_html"]
