*[Llegeix-ho en castellà](README.es.md)*

# Etapa 7 — Finetuning, baselines i comparació de models

Última etapa: amb el dataset ja preparat (etapa 6:
`data/dataset_entrenamiento/{train,dev,test,boe_eval}.jsonl`), esta carpeta
entrena i avalua distints candidats a model de traducció dialectal, i
deixa constància comparable dels resultats de cada un.

**Estat: bastida inicial.** Els fitxers de `scripts/` estan buits
encara — esta carpeta definix l'estructura abans d'escriure el codi,
perquè cada experiment nou siga un fitxer de config, no un script nou.

## Estructura

```
07_entrenamiento_modelos/
├── configs/       un fitxer per experiment (model, hiperparàmetres, quin split usa)
├── scripts/       codi genèric, reutilitzat per tots els experiments
├── checkpoints/   pesos dels models entrenats (no versionat en git)
├── runs/          logs de cada execució (no versionat en git)
└── resultados/    taules comparatives entre experiments (sí versionat)
```

### `configs/` — un experiment, un fitxer

| Fitxer | Què prova |
|---|---|
| `baseline_qwen_zeroshot.yaml` | qwen2.5:14b sense finetuning, amb el prompt de regles actual — la referència a batre (BLEU 93,11, però **compte**: es va calcular contra el benchmark vell de 60 frases, vore nota davall) |
| `baseline_gemma4_zeroshot.yaml` | gemma4:12b sense finetuning, mateix prompt |
| `nllb_600m_finetune.yaml` | Finetuning de NLLB-200-distilled-600M sobre `train.jsonl`/`dev.jsonl` |
| `salamandraTA_lora.yaml` | LoRA sobre SalamandraTA-7b-instruct — el candidat amb més recorregut esperat, ja especialitzat en variants catalanes |

**El BLEU 93,11 de qwen2.5:14b (`../documentacion/metodologia_y_resultados.md`
secció 10) està desactualitzat com a referència**: es va calcular contra el
benchmark de 60 frases, que des de llavors es va ampliar a 150 (90 frases
noves, deliberadament triades per a cobrir regles dialectals que les 60
originals no cobrien bé — les 90 ja estan fusionades en `03_seleccion_de_modelo/benchmark_corpus.json`, l'script que les va generar ja va complir la seua funció i es va retirar).
Abans de fixar "la referència a batre" de veres, cal recalcular el
zero-shot de qwen2.5:14b contra les 150 frases actuals — és d'esperar que
el número baixe una mica, ja que les noves es van triar precisament per ser
més exigents (diverses regles dialectals a la vegada), no a l'atzar.

Afegir un experiment nou és copiar un config i canviar els paràmetres —
mai duplicar `scripts/train.py`.

### `scripts/` — codi genèric, no per experiment

| Fitxer | Què fa |
|---|---|
| `baseline.py` | Avalua un model SENSE entrenar (zero-shot via API/Ollama) contra `test.jsonl`, `boe_eval.jsonl` i `03_seleccion_de_modelo/benchmark_corpus.json` |
| `train.py` | Entrena/fa finetuning segons un config de `configs/` |
| `evaluate.py` | Avalua qualsevol checkpoint ja entrenat amb el mateix criteri que `baseline.py`, perquè els números siguen comparables entre si |

Reutilitza la lògica de puntuació (BLEU/chrF/chrF++) ja existent en
`03_seleccion_de_modelo/evalua_models.py::calcula_metriques()`, en lloc de
reimplementar-la.

### Per què s'avalua contra tres conjunts, no només un

- **`test.jsonl`** — mateix domini que l'entrenament (corpus sintètic
  AVL). Mesura si el model ha aprés bé el que se li ha ensenyat.
- **`boe_eval.jsonl`** — domini real distint (legal/BOE), mai vist en
  entrenament. Mesura generalització — si un model només rendix bé en
  `test.jsonl` però s'enfonsa ací, està sobreajustat al registre
  institucional de l'AVL.
- **`03_seleccion_de_modelo/benchmark_corpus.json`** — les 150 frases amb
  traducció de referència humana. L'únic test genuïnament humà, mai
  s'usa per a entrenar ni ajustar res.

### `checkpoints/` i `runs/` — per què no van a git

Els pesos d'un model entrenat pesen de centenars de MB a diversos GB — mai
han d'anar a control de versions. `.gitignore` ja exclou el contingut
d'estes dos carpetes (mantenint només un `.gitkeep` perquè la carpeta
existisca al repo). `resultados/` sí es versiona perquè són taules de text
xicotetes, no els pesos en si.

## Pròxim pas

Triar amb quin experiment començar (recomanat: `nllb_600m_finetune`,
ràpid i barat de provar primer) i escriure `scripts/train.py` i
`scripts/evaluate.py` per a eixe cas concret.
