# Traductor dialectal valencià ↔ català oriental

Proyecto para construir un traductor automático entre valencià occidental
(norma AVL/GVA) y català oriental (norma IEC). El objetivo no es la
traducción en sí: el valenciano es un idioma de recursos escasos, mientras
que el catalán oriental tiene muchos más — un traductor dialectal fiable
actúa como **puente** para aprovechar esos recursos en tareas que en
valenciano serían inviables por falta de datos (p. ej. alinear inglés↔valencià
pasando por el catalán).

## Empieza por aquí

**[`final/README.md`](final/README.md)** — punto de entrada a toda la
documentación del proyecto: las 5 etapas, la metodología completa
(`final/metodologia_y_resultados.md`) y los resultados actuales.

## Estructura del repositorio

| Carpeta | Qué es |
|---|---|
| [`01_scraping_y_limpieza/`](01_scraping_y_limpieza/) | Etapa 1 — scraping de la web de la AVL y limpieza/clasificación dialectal |
| `corpus/` | Datos: salida cruda y limpia del scraping (entrada del resto del pipeline) |
| [`02_reglas_dialectales/`](02_reglas_dialectales/) | Etapa 2 — reglas dialectales y léxico diferencial valencià↔català |
| [`03_seleccion_de_modelo/`](03_seleccion_de_modelo/) | Etapa 3 — benchmark y selección del modelo de traducción |
| [`04_corpus_sintetico/`](04_corpus_sintetico/) | Etapa 4 — generación del corpus sintético completo |
| [`traductor/`](traductor/) | Etapa 5 — motor de reglas determinista (sin LLM), documentado en `final/05_motor_reglas/` |
| [`boe/`](boe/) | Corpus real y alineado del BOE (traducciones oficiales català/valencià) — pilar complementario al sintético |
| [`dataset_entrenamiento/`](dataset_entrenamiento/) | Prepara el dataset final (train/dev/test) para el finetuning del modelo |
| [`final/`](final/) | Toda la documentación del proyecto: metodología, resultados, decisiones |

## Cómo se relacionan las carpetas

Las etapas 1-4 son código activo (scraping, reglas, benchmark, generación
del corpus). `traductor/` (etapa 5) es un paquete Python independiente que
vive en la raíz porque se importa como módulo desde otras partes del
proyecto. `boe/` es una fuente de datos paralela e independiente del
pipeline AVL — no se mezcla con el corpus sintético en el entrenamiento,
se usa para evaluar generalización fuera de dominio (ver
`dataset_entrenamiento/README.md`).

## Nota si trabajas también en un clúster remoto

Esta estructura de carpetas se reorganizó localmente — si tienes una copia
en otro sitio (p. ej. un clúster SLURM) sincronizada a mano con `scp`/`rsync`,
tendrás que replicar ahí los mismos renombrados antes de tu próxima
sincronización, o las rutas no coincidirán.
