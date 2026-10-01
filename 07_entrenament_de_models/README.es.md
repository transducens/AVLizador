*[Llegeix en català](README.md)*

# Etapa 7 — Finetuning, baselines y comparación de modelos

Última etapa: con el dataset ya preparado (etapa 6:
`dades/dataset_entrenamiento/{train,dev,test,boe_eval}.jsonl`), esta carpeta
entrena y evalúa distintos candidatos a modelo de traducción dialectal, y
deja constancia comparable de los resultados de cada uno.

**Estado: andamiaje inicial.** Los ficheros de `scripts/` están vacíos
todavía — esta carpeta define la estructura antes de escribir el código,
para que cada experimento nuevo sea un fichero de config, no un script
nuevo.

## Estructura

```
07_entrenament_de_models/
├── configs/       un fichero por experimento (modelo, hiperparámetros, qué split usa)
├── scripts/       código genérico, reutilizado por todos los experimentos
├── checkpoints/   pesos de los modelos entrenados (no versionado en git)
├── runs/          logs de cada ejecución (no versionado en git)
└── resultados/    tablas comparativas entre experimentos (sí versionado)
```

### `configs/` — un experimento, un fichero

| Fichero | Qué prueba |
|---|---|
| `baseline_qwen_zeroshot.yaml` | qwen2.5:14b sin finetuning, con el prompt de reglas actual — la referencia a batir (BLEU 93,11, pero **ojo**: se calculó contra el benchmark viejo de 60 frases, ver nota abajo) |
| `baseline_gemma4_zeroshot.yaml` | gemma4:12b sin finetuning, mismo prompt |
| `nllb_600m_finetune.yaml` | Finetuning de NLLB-200-distilled-600M sobre `train.jsonl`/`dev.jsonl` |
| `salamandraTA_lora.yaml` | LoRA sobre SalamandraTA-7b-instruct — el candidato con más recorrido esperado, ya especializado en variantes catalanas |

**El BLEU 93,11 de qwen2.5:14b (`../documentacio/metodologia_y_resultados.md`
sección 10) está desactualizado como referencia**: se calculó contra el
benchmark de 60 frases, que desde entonces se amplió a 150 (90 frases
nuevas, deliberadamente elegidas para cubrir reglas dialectales que las 60
originales no cubrían bien — las 90 ya están fusionadas en `03_seleccio_de_model/benchmark_corpus.json`, el script que las generó ya cumplió su función y se retiró).
Antes de fijar "la referencia a batir" de verdad, hay que recalcular el
zero-shot de qwen2.5:14b contra las 150 frases actuales — es de esperar que
el número baje algo, ya que las nuevas se eligieron precisamente por ser
más exigentes (varias reglas dialectales a la vez), no al azar.

Añadir un experimento nuevo es copiar un config y cambiar los parámetros —
nunca duplicar `scripts/train.py`.

### `scripts/` — código genérico, no por experimento

| Fichero | Qué hace |
|---|---|
| `baseline.py` | Evalúa un modelo SIN entrenar (zero-shot vía API/Ollama) contra `test.jsonl`, `boe_eval.jsonl` y `03_seleccio_de_model/benchmark_corpus.json` |
| `train.py` | Entrena/hace finetuning según un config de `configs/` |
| `evaluate.py` | Evalúa cualquier checkpoint ya entrenado con el mismo criterio que `baseline.py`, para que los números sean comparables entre sí |

Reutiliza la lógica de puntuación (BLEU/chrF/chrF++) ya existente en
`03_seleccio_de_model/evalua_models.py::calcula_metriques()`, en vez de
reimplementarla.

### Por qué se evalúa contra tres conjuntos, no solo uno

- **`test.jsonl`** — mismo dominio que el entrenamiento (corpus sintético
  AVL). Mide si el modelo aprendió bien lo que se le enseñó.
- **`boe_eval.jsonl`** — dominio real distinto (legal/BOE), nunca visto en
  entrenamiento. Mide generalización — si un modelo solo rinde bien en
  `test.jsonl` pero se hunde aquí, está sobreajustado al registro
  institucional de la AVL.
- **`03_seleccio_de_model/benchmark_corpus.json`** — las 150 frases con
  traducción de referencia humana. El único test genuinamente humano, nunca
  se usa para entrenar ni ajustar nada.

### `checkpoints/` y `runs/` — por qué no van a git

Los pesos de un modelo entrenado pesan de cientos de MB a varios GB — nunca
deben ir a control de versiones. `.gitignore` ya excluye el contenido de
estas dos carpetas (manteniendo solo un `.gitkeep` para que la carpeta
exista en el repo). `resultados/` sí se versiona porque son tablas de texto
pequeñas, no los pesos en sí.

## Siguiente paso

Elegir con qué experimento empezar (recomendado: `nllb_600m_finetune`,
rápido y barato de probar primero) y escribir `scripts/train.py` y
`scripts/evaluate.py` para ese caso concreto.
