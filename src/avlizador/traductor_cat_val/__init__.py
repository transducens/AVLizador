"""
traductor_cat_val -- Traductor dialectal de català oriental (norma IEC) a
valencià occidental (norma AVL). No tradueix entre idiomes: convertix
morfologia i lèxic dins de la mateixa llengua.

Ús públic:
    from avlizador.traductor_cat_val import translate_cat_val
    translate_cat_val("Aquest xiquet és molt bo.")  # -> "Este xiquet és molt bo."

Des de la línia d'ordres: `avlizador tradueix "text"`.

`translate_cat_val` és el sistema final: motor de regles + postprocessat
amb model de llengua (`model_llengua/`, CPU) per als homògrafs. Des del
13/11/2026 el model és KenLM + un classificador de sentit: extra
`[kenlm]`; els fitxers del model es baixen de Hugging Face la primera
vegada (o es llegixen d'`AVLIZADOR_KENLM_DIR`); si falten,
`translate_cat_val` usa el motor sol i avisa (`AvisSenseModelLlengua`).
Fins al 12/11/2026 el model era FLOR-760M; des de la versió 2.0.0 ja no és
en el paquet.
`translate_cat_val_motor` és el motor sol.

Els diccionaris es lligen de `data/` (còpies de `dades/lexic/`, la font
única; `scripts/sync_data.py` les regenera). El paquet no depén en temps
d'execució de cap altra carpeta del repositori.

La direcció valencià -> català (`translate.py`, `rules/val_cat/`) es queda
dins del codi però FORA de l'API pública (decisió del 30/10/2026): el Grau
Dialectal (`avlizador.grau_dialectal`) en necessita els carregadors de
dades.
"""

from .translate_invers import AvisSenseModelLlengua, translate_cat_val, translate_cat_val_motor

__all__ = ["translate_cat_val", "translate_cat_val_motor", "AvisSenseModelLlengua"]
