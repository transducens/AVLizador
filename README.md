*[Llegeix-ho en castellà](README.es.md)*

# Traductor dialectal valencià ↔ català oriental

Projecte per a construir un traductor automàtic entre valencià occidental
(norma AVL/GVA) i català oriental (norma IEC). L'objectiu no és la
traducció en si: el valencià és una llengua de recursos escassos, mentre
que el català oriental en té molts més — un traductor dialectal fiable
actua com a **pont** per a aprofitar eixos recursos en tasques que en
valencià serien inviables per falta de dades (p. ex. alinear anglés↔valencià
passant pel català).

## Comença per ací

**[`documentacion/metodologia_y_resultados.md`](documentacion/metodologia_y_resultados.md)**
— la història completa del projecte en un sol document: d'on ix el text,
com es van decidir les regles, quins models es van comparar i amb quins
resultats, quins bugs es van trobar i com es van corregir, limitacions
conegudes. Cada carpeta d'etapa té a més el seu propi README amb el detall
d'ús d'eixa etapa en concret.

## Estructura del repositori

**Codi** (cada carpeta és una etapa o un pilar del projecte):

| Carpeta | Què és |
|---|---|
| [`01_scraping_y_limpieza/`](01_scraping_y_limpieza/) | Etapa 1 — scraping de la web de l'AVL i neteja/classificació dialectal |
| [`02_reglas_dialectales/`](02_reglas_dialectales/) | Etapa 2 — regles dialectals i lèxic diferencial valencià↔català |
| [`03_seleccion_de_modelo/`](03_seleccion_de_modelo/) | Etapa 3 — benchmark i selecció del model de traducció |
| [`04_corpus_sintetico/`](04_corpus_sintetico/) | Etapa 4 — generació del corpus sintètic complet |
| [`traductor/`](traductor/) | Etapa 5 — motor de regles determinista (sense LLM); veure `traductor/README.md` |
| [`06_dataset_entrenamiento/`](06_dataset_entrenamiento/) | Etapa 6 — prepara el dataset final (train/dev/test) per al finetuning |
| [`07_entrenamiento_modelos/`](07_entrenamiento_modelos/) | Etapa 7 — finetuning, baselines i comparació de models |
| [`boe/`](boe/) | Scripts del corpus real i alineat del BOE — pilar independent, sense numerar (no és seqüencial amb 1-7) |
| [`documentacion/`](documentacion/) | La metodologia completa del projecte |

**Dades** (tot agrupat en [`data/`](data/), separat del codi):

| Carpeta | Què és |
|---|---|
| `data/avl/` | Eixida crua i neta del scraping de l'AVL (raw/clean/final) — entrada de l'etapa 4 |
| `data/boe/` | Corpus real del BOE: PDFs descarregats, extracció i alineació (`corpus_entrenamiento.jsonl`) |
| `data/sintetico/` | El corpus sintètic generat (etapa 4): `corpus_sintetic_val_cat.jsonl`, `parallel_val_cat.jsonl`... |
| `data/dataset_entrenamiento/` | El dataset final ja partit (etapa 6): `train.jsonl`/`dev.jsonl`/`test.jsonl`/`boe_eval.jsonl` |

## Com es relacionen les carpetes

Les etapes 1-4 i 6 són codi actiu (scraping, regles, benchmark, generació
del corpus, split final); cada una llig/escriu en la seua subcarpeta
corresponent de `data/`. L'etapa 7 consumeix l'eixida de la 6 per a
entrenar/avaluar models. `traductor/` (etapa 5) és un paquet Python
independent que viu en l'arrel perquè s'importa com a mòdul des d'altres
parts del projecte — no porta prefix numèric perquè un mòdul Python no pot
començar per un dígit. `boe/` és una font de dades paral·lela i
independent del pipeline AVL — el seu codi viu en `boe/`, les seues dades
en `data/boe/`, i no es mescla amb el corpus sintètic en l'entrenament: 
s'usa per a avaluar generalització fora de domini (veure
`06_dataset_entrenamiento/README.md`).

## Nota si treballes també en un clúster remot

Esta estructura de carpetes es va reorganitzar localment — si tens una
còpia en un altre lloc (p. ex. un clúster SLURM) sincronitzada a mà amb
`scp`/`rsync`, hauràs de replicar ahí els mateixos renombraments abans de
la teua pròxima sincronització, o les rutes no coincidiran.
