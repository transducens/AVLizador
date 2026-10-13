*[Read it in Spanish](README.es.md)*

# `val_cat/` — direcció original (valencià → català)

Direcció original del motor de regles, moguda ací el 08/10/2026 des de
`traductor/rules/*.py` per simetria amb la nova direcció inversa
(`traductor/rules/cat_val/`) — cap canvi de comportament, nomes
d'ubicació. Per a l'explicació completa de l'arquitectura (les 9+1
capes, les decisions preses sessió a sessió, el catàleg de fallades
residuals), vore `traductor/README.md` (arrel del paquet), que es queda
com la documentació de referència d'esta direcció.

Compartix amb `cat_val/` tot el que viu a `rules/__init__.py`
(`Token`, `tokenize`/`detokenize`, helpers) i `rules/pos_tagger.py`.
