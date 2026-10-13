"""
val_cat -- Direcció ORIGINAL del motor de regles: valencià (occidental,
norma AVL/GVA) -> català (oriental, norma IEC). Companya de
`traductor/rules/cat_val/` (la direcció inversa). Moguda ací el
08/10/2026 des de `traductor/rules/*.py` per simetria amb `cat_val/`
(abans eren els únics mòduls plans dins de `rules/`) -- cap canvi de
comportament, nomes de ubicació; vore
`documentacio/hoja_de_ruta_traductor_invers.md` per al perquè.

El que es queda COMPARTIT a `rules/__init__.py`/`rules/pos_tagger.py`
(un nivell amunt), no ací: `Token`, `tokenize`/`detokenize`, tots els
helpers (`separa_prefix_elidit`, `aplica_amb_prefix_elidit`,
`corregeix_determinant_abans`...) i el POS-tagger d'spaCy.
"""
