*[Llegeix en català](README.md)*

# Dataset de entrenamiento — preparación final antes del finetuning

Esta carpeta prepara los datos que de verdad se le dan a un modelo para
hacerle finetuning: parte el corpus sintético (AVL) en train/dev/test, y
normaliza el corpus real del BOE a un fichero aparte para poder evaluar
generalización fuera de dominio. No entrena nada — solo deja los ficheros
listos.

## Ficheros fuente necesarios (antes de ejecutar nada)

| Fichero | De dónde sale | Qué es |
|---|---|---|
| `dades/sintetic/corpus_sintetic_val_cat.jsonl` | `04_corpus_sintetic/genera_corpus_sintetico.py` (ver `04_corpus_sintetic/README.md`) | El corpus sintético **con metadatos** (`doc_id`, `motius_sospita`...) — **NO** uses `parallel_val_cat.jsonl` para esto, ese export ya no tiene `doc_id` y no se puede agrupar por documento. |
| `dades/boe/corpus_entrenamiento.jsonl` | `boe/exportar_entrenamiento.py` (ver `boe/README.md`) | El corpus real del BOE ya filtrado (268.735 pares en la versión actual). |
| `03_seleccio_de_model/benchmark_corpus.json` | Ya existe, no se toca | Las 150 frases con traducción de referencia humana — el test final "de verdad", fuera de todo lo de aquí. |

Si alguno de los dos primeros no existe todavía, genera antes ese corpus —
este script no descarga ni traduce nada, solo reorganiza lo que ya está
generado.

## Cómo ejecutarlo

```bash
cd 06_dades_entrenament
python prepara_dataset.py
```

Con las rutas por defecto asume la estructura de arriba (relativa a la raíz
del repositorio). Para usar otro fichero (p. ej. cuando termine la
regeneración v2 del corpus sintético, o si tiene otro nombre):

```bash
python prepara_dataset.py --sintetic ../dades/sintetic/corpus_sintetic_val_cat_v2.jsonl
```

Otros argumentos:

| Argumento | Por defecto | Qué controla |
|---|---|---|
| `--boe` | `dades/boe/corpus_entrenamiento.jsonl` | Ruta al corpus BOE |
| `--sintetic` | `dades/sintetic/corpus_sintetic_val_cat.jsonl` | Ruta al corpus sintético (con metadatos) |
| `--output-dir` | `dades/dataset_entrenament/` | Dónde se escriben los ficheros de salida |
| `--seed` | `42` | Semilla del barajado — mismo seed, mismo split siempre (reproducible) |
| `--prop-dev` | `0.05` (5%) | Proporción aproximada de frases del sintético para `dev.jsonl` |
| `--prop-test` | `0.05` (5%) | Proporción aproximada de frases del sintético para `test.jsonl` |

Es determinista: relanzarlo con los mismos ficheros de entrada y el mismo
`--seed` reproduce exactamente el mismo split.

## Estado actual del split (última ejecución)

Corpus sintético: **28.576 frases, 100% traducidas con gemma4:12b**
(confirmado contando el campo `model` de cada registro — no es una mezcla
de modelos). 341 sospechosas descartadas → 28.235 frases limpias.

| Fichero | Frases |
|---|---|
| `train.jsonl` | 25.407 |
| `dev.jsonl` | 1.414 |
| `test.jsonl` | 1.414 |
| `boe_eval.jsonl` | 199.575 |

## Qué genera, y para qué sirve cada fichero

```
dades/dataset_entrenament/
├── train.jsonl       # entrenar el modelo — SOLO corpus sintético
├── dev.jsonl         # validar durante el entrenamiento (early stopping, elegir checkpoint) — SOLO sintético
├── test.jsonl        # evaluación final dentro del mismo dominio (AVL) — SOLO sintético
└── boe_eval.jsonl    # evaluación de generalización FUERA de dominio (legal/BOE) — nunca se entrena con esto
```

### Nomenclatura: por qué `dev` y no `val`

`dev` (development set) y `val`/`validation set` son sinónimos exactos en
ML — el conjunto que se usa **durante** el entrenamiento para vigilar
sobreajuste y elegir el mejor checkpoint (nunca para entrenar directamente,
ni para el número final que se reporta — eso es `test.jsonl`). Aquí se usa
deliberadamente **`dev`, nunca `val`**, porque `val` ya significa algo muy
concreto en todo este proyecto: el campo con el texto en **valencià** en
cada registro (`{"val": "...", "cat": "..."}`). Un fichero llamado
`val.jsonl` cuyas líneas tienen un campo también llamado `val` —pero con un
significado totalmente distinto— sería una fuente de confusión real, no
solo teórica. Resumen para no perderse:

| Palabra | Significado en este proyecto |
|---|---|
| `val` (campo dentro de un JSON) | Texto en **valencià** |
| `cat` (campo dentro de un JSON) | Texto en **català** |
| `dev` (nombre de fichero/split) | Conjunto de **validación** durante el entrenamiento |
| `test` (nombre de fichero/split) | Conjunto de evaluación final, mismo dominio que `train` |
| `boe_eval` (nombre de fichero/split) | Evaluación de generalización fuera de dominio |

Cada línea es un JSON con el mismo esquema en los cuatro ficheros:

```json
{"val": "frase en valencià", "cat": "frase en català", "origen": "avl_sintetic", "doc_id": "...", "similitud": null}
```

(`similitud` solo tiene valor real en `boe_eval.jsonl` — viene de la
alineación por Bleualign del corpus BOE, ver `boe/README.md`; en el
sintético siempre es `null`.)

**Por qué el corpus real (BOE) NO se mezcla con el entrenamiento**: la
decisión del proyecto es entrenar solo con el corpus sintético. El BOE
normalizado al mismo esquema sirve, aparte, para comprobar si el modelo
generaliza a un registro real (legal) que nunca ha visto en entrenamiento
— si el modelo solo funciona bien en `test.jsonl` (mismo dominio que
`train.jsonl`) pero se hunde en `boe_eval.jsonl`, es una señal de
sobreajuste al registro institucional de la AVL.

`boe_eval.jsonl` tiene ~200.000 frases — demasiadas para evaluar en cada
época de entrenamiento. Para chequeos rápidos, samplea unas 3.000-5.000 al
azar; guarda la evaluación sobre el fichero completo para el final.

## Decisiones de diseño (por qué está hecho así)

- **Split por documento, no por frase suelta**: todas las frases de un
  mismo `doc_id` caen siempre en el mismo split. Si se partiera frase a
  frase, frases muy parecidas del mismo documento (mismo artículo de ley,
  mismo glosario) podrían caer una en train y otra en test — el modelo
  "vería" en entrenamiento vocabulario/estilo casi idéntico al de test, e
  infla la métrica de forma artificial.
- **Se descartan las frases sospechosas del sintético** (`motius_sospita`
  no vacío) antes de nada — mismo criterio que usa
  `04_corpus_sintetic/genera_corpus_sintetico.py::exporta_nets()` para
  producir `parallel_val_cat.jsonl`, pero aplicado aquí sobre el fichero
  con metadatos para no perder el `doc_id`.
- **Deduplicación exacta dentro de cada corpus** (antes del split): el BOE
  en concreto tiene mucha redundancia real (fórmulas legales fijas
  repetidas entre documentos — en la última ejecución, 268.735 → 199.575
  tras dedup, un 26%). Sin deduplicar antes de partir, un duplicado exacto
  podría acabar a la vez en dos splits distintos.
- **`boe_eval.jsonl` se limpia de cualquier frase idéntica a alguna del
  `train.jsonl` sintético** — si por casualidad coincidiera texto exacto
  entre los dos corpus, esa frase ya no seria una prueba válida de
  "dominio no visto".

## Siguiente paso (fuera del alcance de esta carpeta)

Con `train.jsonl`/`dev.jsonl` listos, el siguiente bloque es el finetuning
en sí — candidatos evaluados: NLLB-200 (distilled-600M/1.3B, primer
experimento recomendado), SalamandraTA-7b-instruct con LoRA (el de más
recorrido esperado, ya "sabe" traducir variantes catalanas de fábrica),
LoRA sobre qwen2.5:7b/gemma3:4b para no depender del prompt largo de
reglas en producción. Ver la conversación/decisión del proyecto para el
detalle de por qué cada uno.
