# Baseline de modelos de lenguaje para `traductor/model_llengua/`

Medida del 29/10/2026. Pregunta: ¿hay algún modelo de lenguaje pequeño
(que funcione en CPU) que resuelva los homógrafos cat→val mejor que
FLOR-760M, el que usa hoy el sistema final?

**Respuesta: no. FLOR-760M es el mejor, el más rápido y de los más
pequeños. Se queda.** Falta probar FLOR-1.3B (pide aceptar condiciones en
Hugging Face).

## Qué se ha medido

El sistema es el de siempre (`traductor/model_llengua/`, README): el motor
traduce, para cada homógrafo se construyen las frases valencianas
completas de cada candidato y el modelo elige la más probable. Lo único
que cambia es el modelo que puntúa (`--model-llengua`).

- **Benchmark combinado**
  (`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json`,
  253 frases: las 151 + 98 homógrafos + 1 frase real de gplsi), con el
  criterio por defecto (λ = 0,5, margen 5).
- **Rejilla de criterios** sobre los 98 homógrafos (λ 0 / 0,5 / 1 ×
  margen 0 / 5), porque el criterio por defecto se ajustó para FLOR el
  23/10 y podría favorecerlo.

Ejecutado en Abaco, solo CPU, un modelo por tarea
(`pipeline/08_traduccio_corpus/postprocessat_llm/slurm/baseline_models_llengua.sh`).
FLOR-760M se midió también en local: el mismo resultado exacto (227/253).
Ningún log tiene líneas `ERROR:`.

Modelos: los abiertos de hasta ~2B parámetros con catalán en el
entrenamiento o multilingües. FLOR-1.3B, Llama-3.2-1B y Gemma-3-1B no
entraron porque piden aceptar condiciones en Hugging Face.

## Resultados del benchmark combinado (criterio por defecto)

| Modelo | Tamaño | Exactas /253 | BLEU | Colisión /33 | Irresoluble /24 | s/frase* |
|---|---|---|---|---|---|---|
| **projecte-aina/FLOR-760M** | 1,5 GB | **227** | **96,47** | **31** | 18 | **1,09** |
| BSC-LT/salamandra-2b | 4,5 GB | 222 | 95,97 | 30 | 14 | 3,15 |
| utter-project/EuroLLM-1.7B | 3,3 GB | 218 | 95,06 | 25 | 15 | 2,13 |
| bigscience/bloom-560m | 1,1 GB | 217 | 95,01 | 20 | **19** | 1,35 |
| bigscience/bloom-1b7 | 3,4 GB | 213 | 94,66 | 22 | 13 | 3,37 |
| Qwen/Qwen3-1.7B-Base | 3,4 GB | 210 | 94,00 | 18 | 14 | 4,07 |
| Qwen/Qwen3-0.6B-Base | 1,2 GB | 209 | 93,94 | 16 | 15 | 1,61 |
| Qwen/Qwen2.5-1.5B | 3,1 GB | 208 | 93,76 | 16 | 14 | 3,04 |
| Qwen/Qwen2.5-0.5B | 1,0 GB | 204 | 93,12 | 14 | 12 | 1,37 |

\* Segundos por frase de la rejilla en Abaco, con las 9 tareas a la vez.
Solo sirven para comparar modelos entre sí.

Las 151 (146/154), los homógrafos resolubles (30/40) y las frases de
control (2/2) dan lo mismo con todos los modelos: ahí no interviene el
modelo de lenguaje. Toda la diferencia sale de las colisiones ("cop",
"cops") y de los irresolubles ("calces", "gandula", "gandules").

Referencias: elegir siempre "vegada" da 16/32 en colisión; el motor solo
(traducir siempre) da 12/24 en irresoluble.

## Rejilla de criterios (homógrafos, 56 puntos de colisión + irresoluble)

| Modelo | Criterio por defecto | Su mejor criterio | Cuál |
|---|---|---|---|
| FLOR-760M | **49** | **49** | λ 0,5, margen 5 |
| salamandra-2b | 44 | 46 | λ 0, margen 0 |
| bloom-560m | 39 | 45 | λ 0, margen 5 |
| EuroLLM-1.7B | 40 | 41 | λ 0, margen 5 |
| bloom-1b7 | 36 | 41 | λ 0, margen 5 |
| Qwen3-1.7B-Base | 34 | 36 | λ 0, margen 5 |
| Qwen3-0.6B-Base | 32 | 34 | λ 0, margen 0 |
| Qwen2.5-1.5B | 31 | 31 | λ 0, margen 0 |
| Qwen2.5-0.5B | 29 | 30 | λ 0,5, margen 0 |

Con el mejor criterio de cada uno, FLOR sigue delante. El "mejor
criterio" se elige sobre las mismas frases con las que se mide: es una
cifra optimista para todos.

## Análisis

**1. Los modelos flojos tienen sesgo hacia "vegada", no hacia el primer
candidato.** En las colisiones hay 16 frases de cada sentido:

| Modelo | Elige "colp" | Elige "vegada" | Aciertos cuando es "colp" |
|---|---|---|---|
| FLOR-760M | 15 | 17 | 15/16 |
| salamandra-2b | 14 | 18 | 14/16 |
| EuroLLM-1.7B | 9 | 23 | 9/16 |
| bloom-1b7 | 7 | 25 | 7/16 |
| bloom-560m / Qwen3-1.7B | 4 | 28 | 4/16 |
| Qwen2.5-0.5B / 1.5B / Qwen3-0.6B | 1 | 31 | 1/16 |

Los Qwen eligen "vegada" casi siempre (su 16/32 es azar) aunque el PMI
compense la frecuencia: "colp" es una forma valenciana que no han visto
y la ven improbable en cualquier contexto. Es la misma lección que el
dato "hamaces" del 23/10. Solo los modelos entrenados con mucho catalán y
valenciano (FLOR, salamandra) reparten según el contexto. Que el orden de
los candidatos no influye ya se comprobó el 29/10: invirtiéndolo, 0
cambios.

**2. Comparación frase a frase con FLOR** (56 puntos, test exacto de McNemar):

| Frente a | Solo FLOR acierta | Solo el otro acierta | p |
|---|---|---|---|
| salamandra-2b | 7 | 2 | 0,18 |
| bloom-560m | 13 | 3 | 0,02 |
| EuroLLM-1.7B | 10 | 1 | 0,01 |

Frente a salamandra la diferencia no es significativa con tan pocas
frases, pero salamandra pesa el triple y es unas 3 veces más lento por
frase: no compensa.

**3. "calces" sigue sin resolverse.** Aciertos por sentido (combinado):

| Modelo | calces (no traducir) | calces (→ bragues) | gandula (no) | gandula (→ hamaca) | gandules (no) | gandules (→ hamaques) |
|---|---|---|---|---|---|---|
| FLOR-760M | 0/5 | 5/5 | 3/4 | 4/4 | 3/3 | 3/3 |
| bloom-560m | 3/5 | 4/5 | 3/4 | 4/4 | 2/3 | 3/3 |
| salamandra-2b | 1/5 | 1/5 | 2/4 | 4/4 | 3/3 | 3/3 |
| EuroLLM-1.7B | 0/5 | 5/5 | 3/4 | 4/4 | 0/3 | 3/3 |

FLOR no separa "calces": su 5/10 es traducir siempre. bloom-560m es el
único que separa algo (7/10) y por eso gana a FLOR en los irresolubles
(19 frente a 18), pero pierde de lejos en las colisiones. Son 10 frases:
no basta para fiarse.

**4. Combinar dos modelos no compensa.** Sumando las puntuaciones de FLOR
y salamandra-2b (λ 0, margen 5) salen 50/56, una más que FLOR solo, con
el criterio elegido sobre las mismas frases y el doble de coste en CPU.
FLOR + bloom-560m: 49; FLOR + EuroLLM: 44.

## Decisión y pendiente

- **Se mantiene `projecte-aina/FLOR-760M`** como modelo por defecto
  (`puntuador.MODEL_PER_DEFECTE`). No cambia nada en el código.
- **Pendiente: FLOR-1.3B** (`projecte-aina/FLOR-1.3B`, 2,6 GB, CPU). Es
  el índice 9 del array de Abaco (`sbatch --array=9
  baseline_models_llengua.sh`) o se ejecuta en local; en los dos casos hay
  que iniciar sesión en Hugging Face y aceptar sus condiciones.
- El benchmark de homógrafos tiene frases inventadas con el sentido muy
  marcado y pocas frases por palabra (10 de "calces"). Las diferencias de
  1-3 frases no son concluyentes.

## Ficheros

- Resultados del combinado:
  `pipeline/03_seleccio_de_model/resultats/benchmark_Traductor_Invers_ML_<modelo>_20261029_*.json`.
- Rejilla: `pipeline/03_seleccio_de_model/resultats/benchmark_homografs_ml_<modelo>_20261029.json`
  (`detall_millor` guarda las puntuaciones brutas de cada candidato: se
  puede recalcular cualquier criterio sin volver a llamar al modelo).
- Logs de Abaco: `dades/abaco/baseline_models_llengua/`.
