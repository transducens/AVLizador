*[Llegeix en català](README.md)*

# Comparativa: qwen2.5:14b vs. gemma3 vs. salamandra vs. SalamandraTA

Prueba de si hay una alternativa mejor a qwen2.5:14b para la conversión
occidental→oriental, usando el mismo benchmark de 60 frases
(`03_seleccion_de_modelo/benchmark_corpus.json`) sobre 5 GPUs en paralelo (4
candidatos, uno de ellos — SalamandraTA — repartido en 2 GPUs).

**Ajustado a las GPUs reales del clúster** (nodo "abaco": 8×11264 MiB = 11 GB
por GPU, arquitectura Turing/compute capability 7.5, confirmado con
`nvidia-smi`). Con 11 GB, `gemma3:27b` no cabe, y SalamandraTA no cabe en
UNA sola GPU ni en bf16 ni cuantizado — ver detalle abajo.

## Candidatos

| | Cómo se sirve | VRAM aprox. | Por qué |
|---|---|---|---|
| `qwen2.5:14b` | Ollama | ~9,2 GB (ya confirmado en este nodo) | El modelo actual — se recalcula en esta misma pasada para tener una referencia limpia, en igualdad de condiciones |
| `gemma3:12b` | Ollama | ~8 GB | Multilingüe amplio (140+ idiomas), tamaño similar a qwen2.5:14b |
| `hdnh2006/salamandra-7b-instruct` | Ollama | ~4-5 GB | El Salamandra genérico (no el TA) — ya se probó antes y perdió contra qwen, pero fue **antes** de arreglar el corte de frases del corpus; merece un número fresco. El nombre lleva el prefijo `hdnh2006/` porque así está publicado en el registro de Ollama, no como "salamandra-7b-instruct" a secas |
| `BSC-LT/salamandraTA-7b-instruct` | **vLLM, bf16 en 2 GPUs** — no Ollama | ~8 GB por GPU (16 GB repartidos entre 2, `--tensor-parallel-size 2`) | Modelo de traducción especializado del BSC, soporta explícitamente "Catalan (and Catalan-Valencian variety)" |

`gemma3:27b` queda descartado para esta ronda: a 4 bits pesa ~15-17 GB, no
cabe en 11 GB. Si algún día lo pruebas en GPUs de 24 GB+, solo hay que
cambiar la variable correspondiente en el script.

## Por qué SalamandraTA no va por Ollama

El propio [model card de BSC-LT](https://huggingface.co/BSC-LT/salamandraTA-7b-instruct)
lo dice explícitamente:

> "We strongly discourage using ollama as we have encountered compatibility
> issues that may seriously degrade the model's performance."

Recomiendan **vLLM** (sin cuantizar) o **llama.cpp** (versión GGUF, que BSC-LT
no publica oficialmente). Por eso `comparar_salamandraTA_gemma.sh` levanta un
servidor vLLM con la API compatible con OpenAI, y `evalua_models.py` ahora
sabe hablar con ese tipo de servidor (`--model openai`, ver más abajo) —
esto es nuevo en el script, antes solo sabía hablar con Ollama y Claude.

Nota importante: esto es distinto del "salamandra-7b-instruct" genérico que
ya se probó y perdió contra qwen (ver `../../documentacion/metodologia_y_resultados.md`,
sección 5). SalamandraTA es un modelo *de traducción*, no un instructor de
propósito general — otra arquitectura de uso, no una repetición de la prueba
anterior.

## Entorno virtual para vLLM

El nodo usa un Python "externally managed" (PEP 668, normal en Debian/
Ubuntu recientes): `pip install` directo falla con `error:
externally-managed-environment`. El script crea un entorno virtual
dedicado en `$HOME/venv_vllm` (variable `VENV_VLLM`, persistente entre
ejecuciones, igual que `$OLLAMA_MODELS`) e instala `vllm` ahí — nunca con
`--break-system-packages`, que tocaría el Python de todos los usuarios del
nodo compartido. No hace falta hacer nada a mano; si quieres inspeccionarlo
o reinstalar desde cero: `rm -rf ~/venv_vllm` y vuelve a lanzar el script.

**Ni `bitsandbytes` ni `fp8` se usan — se probaron los dos y los dos
fallaron por motivos reales**:
- `bitsandbytes`: la versión de vLLM que hace falta (ver más abajo) ya no
  lo soporta como método (`Unknown quantization method: bitsandbytes`).
- `fp8`: sí lo soporta vLLM, pero exige compute capability ≥80 (GPUs
  Ampere o más nuevas); este nodo es Turing, capability 75 — error real
  confirmado (`The quantization method fp8 is not supported for the
  current GPU. Minimum capability: 80. Current capability: 75.`). Este es
  un límite de **hardware**, no de configuración — ninguna versión de
  ningún paquete lo arregla.

La solución real no es cuantizar más fuerte, es no cuantizar: repartir el
modelo completo en bf16 entre 2 GPUs con `--tensor-parallel-size 2` (cada
una carga solo la mitad, ~8 GB, que sí cabe en 11 GB con margen de sobra).
Por eso el script pide 5 GPUs en vez de 4.

**`vllm` está FIJADO a la versión `0.9.2`, no "la última"** (variable
`VLLM_VERSION` al principio del script). Instalar sin fijar versión trae
vLLM 0.29.0, que exige PyTorch 2.13.0 compilado para CUDA 13.0 — más
nuevo que el driver de este nodo (575.57.08, CUDA 12.9), y falla al
arrancar con `RuntimeError: The NVIDIA driver on your system is too old`.
vLLM 0.9.2 está documentado oficialmente como compatible con PyTorch 2.6.0
+ CUDA 12.4, que sí cabe bajo un driver de 12.9 — no es una suposición, es
una combinación de versiones conocida. El script instala con
`--extra-index-url https://download.pytorch.org/whl/cu124` para ayudar a
`pip` a resolver esa combinación, y comprueba la versión exacta de `vllm`
ya instalada (no solo si existe alguna) para volver a instalar si el
entorno virtual quedó con la versión equivocada de un intento anterior.

**`transformers` está FIJADO a `<4.54.0`** (variable `TRANSFORMERS_VERSION`).
Sin este límite, `pip` instala una versión de `transformers` que ya
registra el modelo de visión "aimv2" de forma nativa, y vLLM 0.9.2 intenta
registrarlo también por compatibilidad con versiones antiguas —
choque confirmado: `ValueError: 'aimv2' is already used by a Transformers
config, pick another name`. Es un problema conocido y documentado en
varios proyectos que dependen de vLLM 0.9.x, con este mismo arreglo.

## Las formas de probar SalamandraTA

**`--openai-mode regles`** (el mismo system prompt largo con las 10
categorías de reglas dialectales + glosario dinámico que usamos con qwen/
gemma) se probó y se **descartó**: resultado real 0,13-1,75 BLEU, 0/60
exactas. En vez de aplicar las reglas, el modelo repite fragmentos
literales de las propias instrucciones como si fueran la traducción (p.ej.
devuelve `"ELISION (només 'de', 'la', 'el')..."` en lugar de traducir la
frase). No es un instructor de propósito general — un system prompt de
~2200 tokens con reglas gramaticales no es su formato de entrenamiento.
Ya no se ejecuta este modo en el script (perder ~2-3 min por repetición sin
ninguna posibilidad de resultado útil).

El script prueba, una detrás de otra contra el mismo servidor:

1. **`--openai-mode traduccio`**: la plantilla oficial de traducción del
   modelo (`"Translate the following text from X into Y..."`), sin ninguna
   pista. **Resultado real**: 83,54 BLEU, 21,7% exactas — funciona, pero
   por debajo de qwen/gemma. SalamandraTA trata valencià y català como una
   sola entrada de idioma ("Catalan (and Catalan-Valencian variety)"), así
   que no hay garantía documentada de que distinga la dirección él solo.
2. **`--openai-mode traduccio_lexic`**: la MISMA plantilla, pero añadiendo
   el glosario dinámico corto en formato `[VOCABULARI: este=aquest,
   roig=vermell]` — el mismo formato compacto que ya usan qwen/gemma,
   diseñado explícitamente para que el modelo no lo repita en la respuesta
   (a diferencia del system prompt entero de `regles`). Hipótesis a
   comprobar: quizás el problema de `regles` no era "el modelo no puede
   seguir ninguna pista", sino "no sabe qué hacer con un bloque de
   instrucciones largo en un rol `system` que no es su formato".

## Cambios en `evalua_models.py`

Se han añadido, de forma retrocompatible (nada de lo anterior cambia de
comportamiento):

- `--ollama-url` — para lanzar varias instancias de Ollama en paralelo, cada
  una en su puerto/GPU (antes la URL estaba fija a `localhost:11434`).
- `--model openai` + `--openai-url` / `--openai-model` / `--openai-mode` /
  `--openai-timeout` — para hablar con cualquier servidor compatible con la
  API de chat de OpenAI (vLLM, etc.), reutilizando exactamente el mismo
  cálculo de BLEU/chrF/chrF++ e informe comparativo que ya existía.

## Aviso de memoria

Ya ajustado para 11 GB por GPU, pero si lo repites en otro clúster, comprueba
primero cuánta VRAM tiene cada GPU:
```
nvidia-smi --query-gpu=index,memory.total --format=csv
```
Con menos de 11 GB por GPU, hasta el reparto en 2 GPUs puede no caber —
baja `GPU_MEMORY_UTILIZATION` o `VLLM_MAX_MODEL_LEN` al principio del
script, o sube `VLLM_TENSOR_PARALLEL` a más GPUs si tienes de sobra. Con
24 GB o más por GPU, puedes permitirte `gemma3:27b` y SalamandraTA en bf16
en **una sola** GPU (`VLLM_TENSOR_PARALLEL="1"` y quita `CUDA_VISIBLE_DEVICES=2,4`
de la llamada a vLLM, dejando solo `CUDA_VISIBLE_DEVICES=2`).

## Cómo lanzarlo

```bash
# sincroniza los cambios al clúster primero (evalua_models.py + esta carpeta)

cd scrapeo/03_seleccion_de_modelo/comparativa_salamandraTA_gemma
sbatch comparar_salamandraTA_gemma.sh

# seguir el progreso
squeue
tail -f <jobid>_compara.out
```

## Dónde salen los resultados

- `03_seleccion_de_modelo/resultats/benchmark_<modelo>_<timestamp>.json` — un
  fichero por candidato (5 en total: gemma3:12b, salamandra-7b-instruct,
  qwen2.5:14b, salamandraTA_traduccio, salamandraTA_traduccio_lexic), igual que
  cualquier ejecución normal de `evalua_models.py`.
- `comparativa_salamandraTA_gemma/logs/` — logs de cada servidor (Ollama x3,
  vLLM) y de cada benchmark, para depurar si algo falla.
- `comparativa_salamandraTA_gemma/informe_comparatiu.txt` — la tabla
  comparativa final (BLEU/chrF/chrF++/Exactas), generada por
  `combina_resultats.py` a partir de los 5 ficheros anteriores. Reutiliza el
  mismo formato de informe que ya usa `evalua_models.py --model tots`.

Si quieres regenerar solo el informe combinado más tarde (sin relanzar nada):

```bash
python combina_resultats.py --resultats-dir ../resultats --minuts 240
```
