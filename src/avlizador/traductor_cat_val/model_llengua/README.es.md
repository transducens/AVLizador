# `avlizador.traductor_cat_val.model_llengua` — homógrafos cat→val con un modelo de lenguaje

Postprocesado (23/10/2026) para las palabras catalanas ambiguas que el
motor de reglas no puede resolver solo. Desde el 29/10/2026 forma parte
del **sistema principal** (`translate_cat_val`); necesita el extra `[ml]`
(`torch` + `transformers`). Sin él, `translate_cat_val` usa el motor solo
y avisa una vez (`AvisSenseModelLlengua`).

## Qué resuelve

Los puntos salen del léxico (`traductor_cat_val/data/lexic_general.json`), sin
ninguna palabra escrita en el código:

| tipo | de dónde sale | ejemplo | qué hace hoy el motor |
|---|---|---|---|
| `colisio` | `problema: "colision_homonima"` | cop → colp / vegada; cops → colps / vegades | no traduce (dos candidatos, ninguno canónico) |
| `irresoluble` | `homonimia_lexica`, lecturas de la misma categoría | calces → bragues / calces; gandula → hamaca / gandula | traduce siempre |
| `resoluble` | `homonimia_lexica` que spaCy separa | nou → anou / nou; manca → carència / manca | decide spaCy |

**Sistema final (decisión del usuario, 23/10/2026):**

- `colisio` ("cop", "cops"): el modelo de lenguaje.
- `irresoluble` ("calces", "gandula", "gandules"): dos capas.
  (1) **spaCy por categoría no compartida**: los `lemas` dicen qué
  categorías tiene cada lectura ("gandula": `gandul [adj, n]` y `gandula
  [n]`). Si spaCy da una categoría que solo tiene la otra lectura ("molt
  gandula": ADJ), se deja la palabra catalana. (2) Si no, **el modelo**, que
  solo cambia lo que hizo el motor si gana por más de `marge` (5).
- `resoluble` ("nou", "manca"…): spaCy dentro del motor, como siempre.

Historia de la decisión sobre los irresolubles: primero se quitó el modelo,
porque no separaba "gandules" (tumbona) de "gandules" (personas vagas). La
causa era un **error de datos**: E0592 decía "hamaces", forma incorrecta (el
plural de "hamaca" es "hamaques", como vaca → vaques), y el modelo la
castigaba siempre. Con el dato corregido (permiso del usuario, 23/10/2026)
la diferencia traducir − dejar separa los sentidos: tumbona −2,9 a +4,8,
persona −7,1 a −11,7; el margen 5 cae en medio. "calces" sigue sin
separarse (el modelo no conoce el sentido histórico): queda "bragues".
Irresolubles: 14/24 sin el modelo, **18/24** con él. Se puede quitar con
`Criteri(model_irresolubles=False)` o `evalua_models.py --sense-model-irresolubles`.

**Lección**: una palabra del léxico mal escrita hace que el modelo la vea
improbable sea cual sea el sentido. El modelo sirve también para encontrar
formas sospechosas del léxico.

Criterio por defecto (`Criteri()`): FLOR-760M, PMI 0,5, suma, margen 5,
concordancia `variants`, puntuación de la frase entera.

**Resultados (23/10/2026)**:

| benchmark | motor solo | sistema final |
|---|---|---|
| combinado (151 + homógrafos), exactas | 190/253 (BLEU 91,5) | **227/253** (BLEU 96,5) |
| — 151 | 146/154 | 146/154 (cero cambios) |
| — colisio | 0/33 | 31/33 |
| — irresoluble | 12/24 | 18/24 (calces 5/10, gandula 7/8, gandules 6/6) |
| — resoluble | 30/40 | 30/40 |
| BOE amplio (2.000 líneas reales) | 1.200 (medida del 22/10) | 1.206 (sin irresolubles en el BOE) |

Errores que quedan en colisio: "un últim **cop** al banc" (golpe = robo) y
"intent de **cop**" (golpe de estado sin "d'estat"), los dos salen "vegada".

La función del sistema final es `translate_cat_val_ml(text)`, y
`evalua_models.py --model traductor_ml --direccio cat-val` la evalúa.
**Desde el 29/10/2026 `avlizador.translate_cat_val` es siempre este
sistema** (motor + FLOR-760M); el motor solo queda como
`translate_cat_val_motor` (`evalua_models.py --model traductor --direccio
cat-val`). Ese mismo día los resolubles también pasan por el modelo y
"nou", "manca", "recuita"… se volvieron irresolubles (los `lemas` dicen
que el adjetivo también hace de nombre). El
benchmark para comparar el sistema final con el motor es
`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json`: el de
151 más los homógrafos. Se reconstruye con `construeix_benchmark_sistema_final.py`.

## Cómo funciona

1. El motor traduce la frase.
2. Para cada punto, se construyen las frases valencianas **completas**, una
   por candidato, sobre una "base neutra" (la frase del motor con la palabra
   ambigua sin tocar) y con el determinante concordado:
   "**Una vegada** acabada la reunió…" / "**Un colp** acabada la reunió…".
3. El modelo de lenguaje puntúa cada frase (log-probabilidad) y gana la
   más probable. El modelo no genera texto ni responde preguntas.

Opciones del criterio (`Criteri`), para probar con `avalua.py`:

- `lam` (PMI): resta `lam` × log P(candidato solo), para compensar que una
  palabra sea más frecuente que la otra en general. 0 = sin corrección.
- `norma`: `suma` (toda la frase) o `mitjana` (por token).
- `marge`: en los homógrafos, el motor ya ha elegido; el modelo solo lo
  cambia si gana por más de `marge` puntos.
- `concordanca`: `motor` (solo el determinante inmediatamente anterior,
  como el motor) o `variants` (propone las formas del otro género de las
  dos palabras anteriores, "molts"→"moltes", "altre"→"altra", y el modelo
  elige).
- `puntuacio`: `frase` (toda la frase) o `dreta` (experimental: solo lo que
  viene después de la palabra, condicionado a ella; deja fuera el término
  "qué probable es esta palabra aquí", donde está el sesgo del modelo hacia
  la forma catalana).
- `spacy_irresolubles`: la capa de spaCy para los irresolubles.
- `model_irresolubles`: el modelo también para los irresolubles cuando
  spaCy no decide (por defecto `True`).

Lo medido el 23/10/2026: PMI no hace falta en colisio (32/32 con PMI 0 por
media o 0,5 por suma); `dreta` empeora colisio (28/32) y apenas cambia los
irresolubles; `variants` produce la concordancia correcta ("Moltes
vegades", "Una altra vegada", "Per primera vegada").

Modelos: `projecte-aina/FLOR-760M` por defecto (1,5 GB, CPU, ~1,5 s por
frase con "cop") y `BSC-LT/salamandra-2b` (4,5 GB, ~3,3 s, peor en todo:
descartado). Se descargan solos la primera vez desde Hugging Face.

Baseline del 29/10/2026 con 9 modelos pequeños (FLOR, salamandra, EuroLLM,
bloom, Qwen2.5 y Qwen3): **FLOR-760M sigue siendo el mejor** (227/253 en el
combinado; el siguiente, salamandra-2b, 222) y el más rápido. Los modelos
que no conocen el valenciano eligen "vegada" casi siempre. Detalle en
`documentacio/resultats_baseline_models_llengua.md`; pendiente FLOR-1.3B.

## Ficheros

- `punts.py`: detección de los puntos y construcción de los candidatos (sin modelo).
- `puntuador.py`: `ModelLlengua`, log-probabilidad de un texto (torch + transformers).
- `__init__.py`: `tradueix_cat_val_ml(text, model, criteri)`, elección del candidato.

Fuera del paquete, en `pipeline/03_seleccio_de_model/model_llengua/`:

- `frases_homografs.json`: las frases catalanas del benchmark, con el sentido esperado.
- `genera_benchmark.py`: crea `benchmark_homografs_cat_val.json` con el motor
  (la referencia es el motor con el candidato correcto). **Las referencias
  hay que revisarlas a mano.**
- `avalua.py`: prueba todos los criterios con cada modelo y lo compara con el motor solo.

## Ejecutar (desde la raíz del repo)

```bash
# doctests de todo el paquete (sin modelo, solo spaCy)
pytest tests/test_doctests.py

# regenerar el benchmark (NO sobrescribe uno revisado sin --sobreescriu)
python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py

# evaluar sobre el benchmark de homógrafos
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --per-defecte   # solo el sistema final
python pipeline/03_seleccio_de_model/model_llengua/avalua.py                 # rejilla: PMI x margen x frase/dreta x spaCy sí/no
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b

# sistema final contra el motor solo (151 + homógrafos)
cd pipeline/03_seleccio_de_model
python construeix_benchmark_sistema_final.py
python evalua_models.py --model traductor --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
python evalua_models.py --model traductor_ml --sense-model-irresolubles --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json   # para comparar
```

Los resultados se guardan en
`pipeline/03_seleccio_de_model/resultats/` (`benchmark_homografs_ml_<modelo>_<fecha>.json`
los de `avalua.py`, `benchmark_Traductor_Invers_ML_<modelo>_<fecha>.json` los
de `evalua_models.py`). Si `evalua_models.py` imprime `ERROR:` en una
frase, esa frase se ha devuelto sin traducir: hay que mirarlo.

## Límites conocidos

- Con `concordanca="motor"`, los determinantes que no son el inmediatamente
  anterior y los adjetivos no se conciertan ("un altre vegada"); con
  `variants` (por defecto) sí, hasta dos palabras antes.
- Si la palabra ya la ha consumido otra regla ("cop de puny" → "punyada"),
  no es un punto.
- Homógrafos que el léxico no marca como `homonimia_lexica` no llegan a esta
  capa. Caso visto: E0251 "afecta"→"carinya" (adjetivo, par correcto) se
  aplica también al verbo ("La manca de pluja **afecta** els cultius" →
  "carinya").
