*[Llegeix en català](README.md)*

# Traductor dialectal valencià ↔ català oriental

Proyecto para construir un traductor automático entre valencià occidental
(norma AVL/GVA) y català oriental (norma IEC). El objetivo no es la
traducción en sí: el valenciano es un idioma de recursos escasos, mientras
que el catalán oriental tiene muchos más — un traductor dialectal fiable
actúa como **puente** para aprovechar esos recursos en tareas que en
valenciano serían inviables por falta de datos (p. ej. alinear inglés↔valencià
pasando por el catalán).

## Qué se entrega (estado del 23/10/2026)

Dos herramientas, para la Conselleria, en equipos con pocos recursos y
solo CPU. El resto del repositorio es la infraestructura que las construye
y las valida.

1. **El traductor catalán → valenciano** ([`traductor/`](traductor/), la
   dirección prioritaria):
   - el **motor de reglas** (`translate_cat_val`): diccionarios del
     proveedor + spaCy, determinista, sin GPU ni LLM;
   - una **capa opcional** ([`traductor/model_llengua/`](traductor/model_llengua/),
     `translate_cat_val_ml`): un modelo de lenguaje pequeño (FLOR-760M) que
     solo decide unas pocas palabras ambiguas del léxico ("cop" → colp o
     vegada; "gandula" → hamaca o gandula), eligiendo entre las frases que
     construye el motor.
2. **El Índice de Pureza Dialectal (IPD)**
   ([`pipeline/09_index_puresa_dialectal/`](pipeline/09_index_puresa_dialectal/)),
   con dos índices simétricos hermanos: el IPDV (pureza valenciana) y el
   IPDC (pureza catalana), los dos de 0 a 1.

El estado y la estructura actuales del traductor están al principio de
[`traductor/README.es.md`](traductor/README.es.md). La dirección valenciano
→ catalán existe ([`traductor/rules/val_cat/`](traductor/rules/val_cat/))
pero está aparcada desde el 20/10/2026.

## Empieza por aquí

**[`documentacio/metodologia_i_resultats.md`](documentacio/metodologia_i_resultats.md)**
— la historia completa del proyecto en un solo documento: de dónde sale el
texto, cómo se decidieron las reglas, qué modelos se compararon y con qué
resultados, qué bugs se encontraron y cómo se corrigieron, limitaciones
conocidas. Cada carpeta de etapa tiene además su propio README con el
detalle de uso de esa etapa en concreto.

## Estructura del repositorio

**Reestructurado el 14/10/2026**: las 9 etapas numeradas viven ahora
dentro de [`pipeline/`](pipeline/), separadas del producto real
(`traductor/`) y de los datos (`dades/`). `boe/` (antes suelto en la
raíz, sin número) ahora es `pipeline/05_corpus_boe/` — cierra el hueco
que había en la numeración (antes no existía ningún "05") sin tocar
ninguna de las otras 8 carpetas.

```
traductor/              # el motor real -- el PRODUCTO, no una etapa
  rules/cat_val/          # motor catalán -> valenciano (el que se entrega)
  rules/val_cat/          # motor valenciano -> catalán (aparcado)
  model_llengua/          # capa opcional cat->val: homógrafos con un modelo de lenguaje
  llm/                    # capas de LLM por preguntas (aparcadas)
  data/                   # solo las copias de los dos diccionarios del proveedor
pipeline/
  01_extraccio_i_neteja/
  02_regles_dialectals/
  03_seleccio_de_model/
  04_corpus_sintetic/
  05_corpus_boe/         # antes "boe/" suelto en la raíz, sin número
  06_dades_entrenament/
  07_entrenament_de_models/
  08_traduccio_corpus/
  09_index_puresa_dialectal/
dades/                   # transversal, lo consumen varias etapas
documentacio/            # transversal
```

| Carpeta | Qué es |
|---|---|
| [`traductor/`](traductor/) | El motor de reglas determinista — el producto del proyecto, por eso vive fuera de `pipeline/`; con una capa opcional de modelo de lenguaje para los homógrafos (`model_llengua/`). Ver `traductor/README.es.md` |
| [`pipeline/01_extraccio_i_neteja/`](pipeline/01_extraccio_i_neteja/) | Etapa 1 — scraping de la web de la AVL y limpieza/clasificación dialectal |
| [`pipeline/02_regles_dialectals/`](pipeline/02_regles_dialectals/) | Etapa 2 — reglas dialectales y léxico diferencial valencià↔català |
| [`pipeline/03_seleccio_de_model/`](pipeline/03_seleccio_de_model/) | Etapa 3 — benchmark y selección del modelo de traducción; hoy, sobre todo, `evalua_models.py`, con el que se miden el motor y el sistema final |
| [`pipeline/04_corpus_sintetic/`](pipeline/04_corpus_sintetic/) | Etapa 4 — generación del corpus sintético completo |
| [`pipeline/05_corpus_boe/`](pipeline/05_corpus_boe/) | Etapa 5 — scripts del corpus real y alineado del BOE (antes `boe/`, sin número) |
| [`pipeline/06_dades_entrenament/`](pipeline/06_dades_entrenament/) | Etapa 6 — prepara el dataset final (train/dev/test) para el finetuning |
| [`pipeline/07_entrenament_de_models/`](pipeline/07_entrenament_de_models/) | Etapa 7 — finetuning, baselines y comparación de modelos |
| [`pipeline/08_traduccio_corpus/`](pipeline/08_traduccio_corpus/) | Etapa 8 — aplica el motor de reglas a un corpus completo (no solo al benchmark); postprocesado con LLM de los casos ambiguos |
| [`pipeline/09_index_puresa_dialectal/`](pipeline/09_index_puresa_dialectal/) | Etapa 9 — Índice de Pureza Dialectal (IPD): métrica reutilizable para medir qué porcentaje de un texto es occidental vs. oriental, basada en el índice de pares de `traductor/` |
| [`documentacio/`](documentacio/) | La metodología completa del proyecto |

**Datos** (todo agrupado en [`dades/`](dades/), separado del código):

| Carpeta | Qué es |
|---|---|
| `dades/avl/` | Salida cruda y limpia del scraping de la AVL (raw/clean/final) — entrada de la etapa 4 |
| `dades/boe/` | Corpus real del BOE: PDFs descargados, extracción y alineación (`corpus_entrenamiento.jsonl`); en `dades/boe/benchmarks/`, los benchmarks "BOE dialectal" estricto y amplio |
| `dades/gplsi_ca_va_alignment_test/` | Dataset público gplsi (1.958 pares catalán/valenciano, CC BY 4.0), usado como benchmark |
| `dades/sintetic/` | El corpus sintético generado (etapa 4): `corpus_sintetic_val_cat.jsonl`, `parallel_val_cat.jsonl`... |
| `dades/dataset_entrenament/` | El dataset final ya partido (etapa 6): `train.jsonl`/`dev.jsonl`/`test.jsonl`/`boe_eval.jsonl` |

## Cómo se relacionan las carpetas

Las etapas 1-4 y 6 son código activo (scraping, reglas, benchmark,
generación del corpus, split final); cada una lee/escribe en su subcarpeta
correspondiente de `dades/`. La etapa 7 consume la salida de la 6 para
entrenar/evaluar modelos. `traductor/` es un paquete Python independiente
que vive en la raíz, fuera de `pipeline/`, porque se importa como módulo
desde otras partes del proyecto y porque no es una etapa de un solo uso
sino el producto que todas las etapas alimentan (además, un módulo
Python no puede empezar por un dígito). `pipeline/05_corpus_boe/` es una
fuente de datos paralela e independiente del pipeline AVL — su código
vive ahí, sus datos en `dades/boe/`, y no se mezcla con el corpus
sintético en el entrenamiento: se usa para evaluar generalización fuera
de dominio (ver `pipeline/06_dades_entrenament/README.md`).

## Nota si trabajas también en un clúster remoto

Esta estructura de carpetas se reorganizó localmente (última vez,
14/10/2026: las etapas numeradas se movieron dentro de `pipeline/` y
`boe/` pasó a ser `pipeline/05_corpus_boe/`) — si tienes una copia en
otro sitio (p. ej. un clúster SLURM) sincronizada a mano con
`scp`/`rsync`, tendrás que replicar ahí los mismos renombrados antes de
tu próxima sincronización, o las rutas no coincidirán. La estructura
plana de Abaco (`~/scrapeo/postprocesado_llm/`) se mantiene a propósito
independiente de este cambio — ver
`pipeline/08_traduccio_corpus/postprocessat_llm/README.md`.
