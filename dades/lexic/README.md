# Diccionarios del proyecto (fuente única)

Los diccionarios de los que salen el traductor y el Grado Dialectal. Es
la **única fuente**: desde el 30/10/2026 viven aquí (antes en
`pipeline/02_regles_dialectals/lexic/diccionarios/`).

| Fichero | Qué contiene |
|---|---|
| `lexico_general.json` | Léxico general catalán ↔ valenciano con categoría gramatical, forma canónica, colisiones y homógrafos (`canonica`, `problema`, `id_colision`, `forma_problematica`, `lemas`); incluye numerales, demostrativos y posesivos |
| `conjugaciones_general.json` | Formas verbales catalán ↔ valenciano por persona, tiempo y modo (`morfologia`) |
| `verbos_diferentes_conjugados.json` | Verbos con raíz distinta en cada variedad (conjugados) |
| `Funcionamiento listas de palabras.pdf` | Guía del proveedor: qué significa cada campo |

## Cómo se cambian

1. Se editan **solo** estos ficheros (nunca las copias del paquete).
2. `python scripts/sync_data.py` copia y fusiona los datos en
   `src/avlizador/traductor_cat_val/data/` (`lexic_general.json` y
   `conjugacions_dialectals.json`, lo que lee el paquete instalado);
   `python scripts/sync_data.py --check` tiene que decir "Tot sincronitzat".
3. `pytest` y `avlizador avalua --benchmarks manual` para ver que no hay
   regresiones.

Ningún cambio en estos ficheros sin permiso explícito del responsable
del proyecto, caso a caso.
