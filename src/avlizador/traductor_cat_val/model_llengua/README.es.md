# `avlizador.traductor_cat_val.model_llengua` — homógrafos cat→val con un modelo de lenguaje

Postprocesado (23/10/2026) para las palabras catalanas ambiguas que el
motor de reglas no puede resolver solo. Desde el 29/10/2026 forma parte
del **sistema principal** (`translate_cat_val`); necesita el extra `[ml]`
(`torch` + `transformers`). Sin él, `translate_cat_val` usa el motor solo
y avisa una vez (`AvisSenseModelLlengua`).

## Alternativa a FLOR: KenLM + clasificador de sentido (12/11/2026)

Opción complementaria (decisión del usuario; **FLOR sigue por defecto**):
`translate_cat_val(text, model="kenlm")`, `avlizador tradueix --model kenlm`
y `avlizador avalua --model kenlm` (o `--model flor kenlm`). KenLM ocupa el
mismo hueco que FLOR (puntúa las frases candidatas), sin `torch`:

- `kenlm.py`: `normalitza` (la misma del entrenamiento, antes en
  `pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py`, que ahora la
  importa de aquí) y `ModelKenLM`: log P natural de la frase con `<s>` y
  `</s>`; prior = ln((n + 1) / tokens) con las frecuencias del texto de
  entrenamiento (`<modelo>_freq.json`).
- `sentit.py`: clasificadores de sentido con una interfaz fija,
  `candidat(punt) -> str | None` (frase con hueco → candidato). Hoy
  `ClassificadorCop` (Naive Bayes de "cop/cops" + lemas de spaCy, el mismo
  spaCy del motor). Cambiarlo = otro `nb.json` (se entrena con
  `pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py`, que importa
  el núcleo de aquí) u otra clase con el mismo método.
- `CRITERI_KENLM`: margen 3, la catalana por defecto, λ 1,5 en homógrafos y
  0,75 en colisiones, y desempate < 2 con el clasificador (`Criteri.desempat`).

Ficheros (fuera de git) en la carpeta de `AVLIZADOR_KENLM_DIR`:
`valencia_net_dogv_o5.binary` (77 MB), `valencia_net_dogv_freq.json` y
`nb.json` (o `sentit_cop/nb.json`). Hace falta el paquete `kenlm`
(`pip install "avlizador[kenlm]"`; se compila: en Windows hace falta
compilador, la imagen Docker es Linux). Si falta algo, `FaltaKenLM` (no
vuelve al motor solo en silencio: se ha pedido expresamente).

Resultados (`compara_models_20261111_1430`, mismo criterio): en las 257
decisiones de los homógrafos, 191 aciertos y 2 errores graves (FLOR 168 y
3); exactas homógrafos v1 227/253 (FLOR 219), v2 110/160 (95), manual
229/458 (228), 151 145 (146), BOE estricto 1.887 (=), gplsi 1.553 (1.554).
Unas 13.000 veces más rápido que FLOR por llamada y 59 MB de memoria frente
a 1,5 GB. Detalle en `documentacio/resultats_model_llengua_kenlm.md`.

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
  solo cambia lo que hizo el motor si gana por más de `marge` (5; desde el
  05/11/2026, margen 2 con la catalana por defecto, ver más abajo).
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

Criterio por defecto (`Criteri()`): FLOR-760M, PMI 0,5, suma, **margen 2
con la palabra catalana por defecto** (`per_defecte="catala"`, desde el
05/11/2026), concordancia `variants`, puntuación de la frase entera.

### Margen 2 con la catalana por defecto (05/11/2026, decisión del usuario)

En los homógrafos que llegan a FLOR (irresolubles y resolubles con NOUN;
"cop/cops" y lo que decide spaCy no cambian), **solo se traduce si FLOR ve
la traducción más probable que la palabra catalana por más de 2 puntos**
de log-probabilidad (unas 7 veces más probable, e² ≈ 7,4). Si no, se deja
la palabra catalana. Antes era al revés (`per_defecte="motor"`, margen 5):
se quedaba la traducción del motor salvo que FLOR prefiriera la catalana
por más de 5. Para volver: `Criteri(per_defecte="motor", marge=5.0)`.

**Por qué la catalana por defecto**: los dos fallos no pesan igual.
Traducir cuando no toca cambia el sentido ("calces" de época → "bragues",
"gandules" vagas → "hamaques", "manca" verbo → "falta"). No traducir deja
la palabra catalana ("rentadora", "manca", "reeixida"), menos dialectal
pero con el mismo sentido y a menudo válida también en valenciano. El
usuario prefiere no traducir a traducir mal.

**Por qué 2 y no 0**: diferencia de FLOR (traducción − catalana) en las
trazas con P1 de homógrafos v1 + v2, 159 palabras que decide el modelo:

| Diferencia | La referencia quiere la valenciana | Quiere la catalana |
|---|---|---|
| ≤ −4 | 11 | 32 |
| −4 a 0 | 52 | 22 |
| 0 a 2 | 10 | 7 |
| > 2 | 23 | 2 |

Cuando la buena es la catalana, FLOR suele decirlo claro (mediana −4,3);
cuando es la valenciana, casi nunca (mediana −1,1: el sesgo hacia la forma
frecuente). Entre 0 y 2 FLOR ya prefiere la traducción pero acierta 10 de
17 (cara o cruz); por encima de 2, 23 de 25. Con margen 0 se traduciría en
esa zona de duda. Simulación del margen con la catalana por defecto:

| Margen | Traduce sin tocar (error de sentido) | Deja la catalana cuando tocaba traducir | Aciertos |
|---|---|---|---|
| antes (motor, 5) | 28/63 | 9/96 | 122/159 |
| 0 | 9/63 | 63/96 | 87/159 |
| 1 | 5/63 | 71/96 | 83/159 |
| **2** | **2/63** | 73/96 | 84/159 |
| 5 | 1/63 | 85/96 | 73/159 |

Depende de la palabra: FLOR separa bien "deu" (mediana +8,3 si toca
traducir frente a −18,8 si no), "gandula", "manques" y "nou"; no separa
"calces", "reeixida(es)", "panotxa(es)" ni "recuita", que casi nunca se
traducirán. Límites: el 2 sale de estos mismos benchmarks (equilibrados
50/50 por sentido, no del uso real) y la simulación usa las trazas del
03/11. Benchmark manual (ejecutado, no simulado): 229 → **228/458**
(BLEU 90,93 → 90,91, TER 5,58 → 5,59). Cambian dos frases: BM-AVL-191 "les
anous" → "les nous" (la pierde: FLOR prefería "anous" por menos de 2) y
BM-BOE-219 "falta" → "manca" (falla igual: la referencia pone "carència").
Con margen 0 o 1 el manual quedaba en 229.

**Homógrafos, ejecutado (06/11/2026)**, frente al margen 5 a favor del
motor (03/11): 151 + homógrafos 233 → **218/253**, homógrafos v2 124 →
**95/160**; manual 228/458 y BOE estricto/amplio sin cambios por el
margen. Es lo que anunciaba la simulación: en el v2 (equilibrado por
sentido) las frases cuya referencia **deja la palabra catalana** pasan de
42 a **57 de 59** (+16, −1), y las que **piden la valenciana** caen de 82
a **38 de 101** (+5, −49). Casi todos los errores de sentido desaparecen;
a cambio, muchas palabras valencianas quedan sin traducir ("anou",
"llavadora", "brulla", "panolla", "exitosa"...). Es el precio aceptado
de la decisión. Cifras con el léxico del 05/11 (género, "mencionar",
"contindre") y el arreglo de `te_problema` del 06/11: el léxico nuevo
trae `problema` como lista en 10 entradas (`["homonimia_lexica",
"cambio_genero"]`), y sin ese arreglo "nou", "deu" y "cop" dejaban de
pasar por spaCy y FLOR (v2 82/160, igual que el motor solo).

**Párrafo valenciano delante (03/11/2026)**: FLOR prefiere la forma que ha
visto más veces, casi siempre la catalana ("vegada" frente a "colp",
"rentadora" frente a "llavadora"). Desde el 03/11 cada frase se puntúa
como continuación de un párrafo corto en valenciano
(`puntuador.CONTEXT_PER_DEFECTE`; `ModelLlengua(context=None)` lo quita).
El párrafo pasa por el modelo una sola vez (`past_key_values`): no cuesta
tiempo. 151 + homógrafos 226 → **233/253**, homógrafos v2 111 → **122/160**,
gplsi 1.544 → 1.547; manual, 151 y BOE sin cambios. Pierde "manca" verbo
(→ "carència") en 2 frases más. Pruebas (párrafos, frecuencias, LoRA) en
`pipeline/03_seleccio_de_model/model_llengua/sesgo/README.md`.

**Concordancia con el determinante (03/11/2026)**: si spaCy da ADJ a la
palabra ambigua y su género no es el del determinante de delante ("una
nou", "les nous"), la capa de spaCy no decide y pasa al modelo
(`punts.decisio_spacy`). Con NUM no (un numeral hace de nombre con
cualquier artículo: "la nou" = la jugadora del dorsal nueve). Homógrafos
v2 122 → 124, manual 227 → 228, homógrafos 233 igual. Detalle en
`pipeline/03_seleccio_de_model/traces/README.md`.

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
- `marge` y `per_defecte`: en los homógrafos, la forma por defecto
  (`catala`: la palabra catalana; `motor`: la traducción del motor) solo
  cambia si la otra gana por más de `marge` puntos.
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
- `kenlm.py`: `ModelKenLM` y `normalitza` (alternativa a FLOR, sin torch; 12/11/2026).
- `sentit.py`: clasificadores de sentido de las colisiones (`ClassificadorCop`).
- `__init__.py`: `tradueix_cat_val_ml(text, model, criteri, sentit=None)`, elección
  del candidato; `translate_cat_val_ml` (FLOR) y `translate_cat_val_kenlm` (KenLM).

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
