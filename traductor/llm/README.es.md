# `traductor/llm/` — capas de postprocesado con LLM (21/10/2026)

*[Llegeix-ho en valencià](README.md)*

Dos capas **opcionales e independientes**, una por dirección. El motor de
reglas traduce y deja unos **puntos ambiguos** donde la decisión depende
del significado. El LLM solo **elige una etiqueta de una lista cerrada**
para cada punto: nunca escribe texto libre. Si no responde o responde
algo que no está en la lista, se queda la salida del motor.

`traductor.translate()` y `traductor.translate_cat_val()` **no usan** esta
capa: sin Ollama todo funciona igual que antes.

## cat→val (`cat_val.py`)

| Tipo | Forma catalana | Opciones | Motor por defecto |
|---|---|---|---|
| `demostratiu` | aquest, aquesta, aquests, aquestes | `este` (1r grado) / `eixe` (2º grado) | `este` |
| `b4` | l'hi, la hi, les hi, els hi, -l'hi, -la-hi, -les-hi, -los-hi | `datiu` (li'l, li la…) / `neutre` (li ho) / `plural` (los el) / `lloc` (igual) | `lloc` (no tocar) |

## val→cat (`val_cat.py`)

| Tipo | Forma valenciana | Opciones | Motor por defecto |
|---|---|---|---|
| `mode_verbal` | 1ª singular y 3ª plural con la misma grafía en indicativo y subjuntivo ("creuen") | `indicatiu` / `subjuntiu` / `cap` | `cap` (no tocar) |

Es la "vía C" de `pipeline/08_traduccio_corpus/postprocessat_llm/` (récord
129/151 con `qwen3:8b`), traída dentro de `traductor/`: las ambigüedades se
calculan solo con `traductor/data/`. La versión antigua leía ficheros de
conjugaciones retirados el 19/10/2026 y ya no funcionaba.

## Uso

```python
from traductor.llm import ClientLLM, tradueix_cat_val, tradueix_val_cat
client = ClientLLM("qwen3:8b", url="http://localhost:11434")
text, punts = tradueix_cat_val("Si l'interessat l'hi presenta...", client)
text, punts = tradueix_val_cat("Vull que creuen el carrer.", client)
```

## Evaluación

`pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py`
(motor solo frente a motor + LLM, y acierto punto a punto contra la
referencia) y, en Abaco, `slurm/avalua_capa_llm.sh`. Con `--sense-llm`
solo cuenta los puntos sin llamar al modelo.

**Antes de activar `demostratiu` por defecto** hay que validarlo contra un
benchmark completo: sin LLM, "este" ya acierta el 100% en el benchmark de
151 y el 94,5% en el BOE, así que el margen es pequeño y el riesgo real (la
Fase 3 de octubre empeoró el resultado).
