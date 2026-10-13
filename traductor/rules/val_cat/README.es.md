*[Llegeix en català](README.md)*

# `val_cat/` — dirección original (valenciano → catalán)

Dirección original del motor de reglas, movida aquí el 08/10/2026 desde
`traductor/rules/*.py` por simetría con la nueva dirección inversa
(`traductor/rules/cat_val/`) — ningún cambio de comportamiento, solo de
ubicación. Para la explicación completa de la arquitectura (las 9+1
capas, las decisiones tomadas sesión a sesión, el catálogo de fallos
residuales), ver `traductor/README.es.md` (raíz del paquete), que se
queda como la documentación de referencia de esta dirección.

Comparte con `cat_val/` todo lo que vive en `rules/__init__.py`
(`Token`, `tokenize`/`detokenize`, helpers) y `rules/pos_tagger.py`.
