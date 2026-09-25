*[Llegeix en català](README.md)*

# Traductor dialectal valencià ↔ català oriental

Proyecto para construir un traductor automático entre valencià occidental
(norma AVL/GVA) y català oriental (norma IEC). El objetivo no es la
traducción en sí: el valenciano es un idioma de recursos escasos, mientras
que el catalán oriental tiene muchos más — un traductor dialectal fiable
actúa como **puente** para aprovechar esos recursos en tareas que en
valenciano serían inviables por falta de datos (p. ej. alinear inglés↔valencià
pasando por el catalán).

## Empieza por aquí

**[`documentacion/metodologia_y_resultados.md`](documentacion/metodologia_y_resultados.md)**
— la historia completa del proyecto en un solo documento: de dónde sale el
texto, cómo se decidieron las reglas, qué modelos se compararon y con qué
resultados, qué bugs se encontraron y cómo se corrigieron, limitaciones
conocidas. Cada carpeta de etapa tiene además su propio README con el
detalle de uso de esa etapa en concreto.

## Estructura del repositorio

**Código** (cada carpeta es una etapa o un pilar del proyecto):

| Carpeta | Qué es |
|---|---|
| [`01_scraping_y_limpieza/`](01_scraping_y_limpieza/) | Etapa 1 — scraping de la web de la AVL y limpieza/clasificación dialectal |
| [`02_reglas_dialectales/`](02_reglas_dialectales/) | Etapa 2 — reglas dialectales y léxico diferencial valencià↔català |
| [`03_seleccion_de_modelo/`](03_seleccion_de_modelo/) | Etapa 3 — benchmark y selección del modelo de traducción |
| [`04_corpus_sintetico/`](04_corpus_sintetico/) | Etapa 4 — generación del corpus sintético completo |
| [`traductor/`](traductor/) | Etapa 5 — motor de reglas determinista (sin LLM); ver `traductor/README.md` |
| [`06_dataset_entrenamiento/`](06_dataset_entrenamiento/) | Etapa 6 — prepara el dataset final (train/dev/test) para el finetuning |
| [`07_entrenamiento_modelos/`](07_entrenamiento_modelos/) | Etapa 7 — finetuning, baselines y comparación de modelos |
| [`boe/`](boe/) | Scripts del corpus real y alineado del BOE — pilar independiente, no numerado (no es secuencial con 1-7) |
| [`documentacion/`](documentacion/) | La metodología completa del proyecto |

**Datos** (todo agrupado en [`data/`](data/), separado del código):

| Carpeta | Qué es |
|---|---|
| `data/avl/` | Salida cruda y limpia del scraping de la AVL (raw/clean/final) — entrada de la etapa 4 |
| `data/boe/` | Corpus real del BOE: PDFs descargados, extracción y alineación (`corpus_entrenamiento.jsonl`) |
| `data/sintetico/` | El corpus sintético generado (etapa 4): `corpus_sintetic_val_cat.jsonl`, `parallel_val_cat.jsonl`... |
| `data/dataset_entrenamiento/` | El dataset final ya partido (etapa 6): `train.jsonl`/`dev.jsonl`/`test.jsonl`/`boe_eval.jsonl` |

## Cómo se relacionan las carpetas

Las etapas 1-4 y 6 son código activo (scraping, reglas, benchmark,
generación del corpus, split final); cada una lee/escribe en su subcarpeta
correspondiente de `data/`. La etapa 7 consume la salida de la 6 para
entrenar/evaluar modelos. `traductor/` (etapa 5) es un paquete Python
independiente que vive en la raíz porque se importa como módulo desde otras
partes del proyecto — no lleva prefijo numérico porque un módulo Python no
puede empezar por un dígito. `boe/` es una fuente de datos paralela e
independiente del pipeline AVL — su código vive en `boe/`, sus datos en
`data/boe/`, y no se mezcla con el corpus sintético en el entrenamiento: se
usa para evaluar generalización fuera de dominio (ver
`06_dataset_entrenamiento/README.md`).

## Nota si trabajas también en un clúster remoto

Esta estructura de carpetas se reorganizó localmente — si tienes una copia
en otro sitio (p. ej. un clúster SLURM) sincronizada a mano con `scp`/`rsync`,
tendrás que replicar ahí los mismos renombrados antes de tu próxima
sincronización, o las rutas no coincidirán.
