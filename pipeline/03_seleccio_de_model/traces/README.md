# Trazas de la traducción catalán → valenciano

Para entender qué hace AVLizador con una frase, paso a paso. Está fuera
del paquete a propósito y **no cambia ninguna traducción**: repite los
mismos pasos que `translate_cat_val` (las mismas capas, en el mismo orden,
con el mismo modelo y el mismo criterio) y comprueba que el resultado
sale idéntico.

## Qué muestra cada traza

1. **spaCy y diccionario**, palabra por palabra:
   - **todos los rasgos de spaCy**: POS, etiqueta, lema y rasgos
     morfológicos. En azul, los que usa el traductor: POS, lema, `Gender`
     y `VerbForm`. `Mood` se guarda, pero ninguna regla de cat→val lo
     mira;
   - **qué hay en el diccionario** de cada capa: léxico, frases del
     léxico, conjugaciones (y si la forma exige que spaCy diga verbo),
     posesivos, numerales y demostrativos; si es una de las 20 palabras
     ambiguas; y las entradas tal cual de los ficheros de datos, también
     las que el motor descarta al cargar;
   - **el resultado**: qué capa la cambia o, si no cambia, **por qué**.
     Por ejemplo: "homógrafo; solo se cambia si spaCy da ADJ", "spaCy la
     etiqueta como nombre propio", "la decide el postprocesado"...
   - un **aviso** cuando el traductor usa la etiqueta de otra aparición
     de la misma palabra y la suya propia sería distinta.
2. **Motor**: las 9 capas en orden y qué cambia cada una, incluidos los
   vecinos (apóstrofo, contracciones).
3. **Postprocesado con FLOR-760M**: si entra y por qué (o por qué no).
   Para cada palabra ambigua muestra:
   - la decisión de spaCy (categoría frente a la lectura dialectal y las
     lecturas de `lemas`);
   - **las frases completas que recibe FLOR**, con las variantes de
     concordancia probadas;
   - `lp`, `prior` y la puntuación (`lp − 0,5 × prior`);
   - la diferencia frente al margen 5 y quién decide (spaCy, FLOR o el
     motor), con la explicación.

## Uso

Desde la raíz del repositorio, con el paquete instalado
(`pip install -e ".[ml]"`):

```bash
# en la terminal
python pipeline/03_seleccio_de_model/traces/traca_traduccio.py "Un cop acabada la reunió, el noi marxarà."
python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --motor "..."      # sin FLOR

# página HTML (y JSON) de un benchmark: solo las frases con palabras ambiguas
python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --benchmark manual --nomes-ambigues \
    --silencios --html pipeline/03_seleccio_de_model/traces/resultats/manual_ambigues.html \
    --json pipeline/03_seleccio_de_model/traces/resultats/manual_ambigues.json

# otras entradas
... --fitxer frases.txt                       # una frase por línea
... --benchmark homografs --ids HG001 HG002   # ids concretos (nombres de `avlizador avalua --llista`)
... --benchmark manual --limit 20             # las 20 primeras
```

- **Apóstrofos**: la entrada y la referencia se normalizan como en
  `avlizador avalua` (´ ‘ ’ ʼ ` → '), así que lo que se traza es lo que
  se evalúa y las exactas cuadran con la evaluación oficial (homógrafos
  226/253). Las referencias de los benchmarks usan sobre todo ’ y antes
  salían como diferencias. El diff de la página también compara con los
  apóstrofos normalizados y alinea por palabras (subsecuencia común más
  larga), no por posición.
- **`visor_traces.html`** es la plantilla: `--html` crea una página con
  los datos dentro, que se abre con doble clic, sin servidor. La
  plantilla sola también abre un JSON de `--json` con el botón "Abrir
  JSON".
- La página tiene filtros: buscar, solo las frases con postprocesado,
  solo las distintas de la referencia y solo las que tienen avisos.
- Las salidas van a `resultats/`, que no entra en git.

## Análisis de los homógrafos con el banco curado (02/11/2026)

Benchmark `homografs`: las 151 frases del banco curado, más 98 de
homógrafos y 1 de gplsi (253 frases). Página: `resultats/homografs_151.html`;
empieza en la vista "Resumen". Las 253 trazas coinciden con
`translate_cat_val`. La palabra ambigua acierta si el candidato elegido
es el único de los dos que usa la referencia.

- 101 frases tienen alguna palabra ambigua, con **101 apariciones: 83
  aciertos y 18 fallos**. Decide FLOR en 59, el motor (por el margen) en
  22 y spaCy en 20.
- **Bien**: cop (19/21), cops (12/12), gandula y gandules (13/14), manca y
  manques (10/10), reeixida (4/4), fartanera (4/4).
- **Mal**:
  - **calces** 5/10: FLOR no separa los dos sentidos, y en 4 fallos
    prefería "calces" pero por menos del margen;
  - **deu** 3/6: spaCy da NUM a "deu" fuente, y el margen mantiene "deu";
  - **nou/nous** 10/15: spaCy da ADJ o NUM a "nou" fruto, y FLOR prefiere
    la forma frecuente;
  - **recuita** 2/4.
- **El margen 5 está bien elegido**: simulando con las mismas
  puntuaciones, 0 → 77, 2 → 79, 4 → 81, **5 → 83**, 6 → 84, 8-15 → 80.
  Por debajo de 5 se pierde (FLOR cambia aciertos del motor) y por encima
  también. Ojo: el margen se ajustó con este mismo benchmark, así que no
  es una prueba independiente.
- **Origen de los 18 fallos**:
  - **spaCy decide mal (3)**: "nou"/"nous" fruto etiquetados ADJ o NUM
    (HG058, HG059, HG066);
  - **FLOR elige mal (7)**: "vegada" en lugar de "colp" (HG009, HGN01),
    "nou"/"nous" en lugar de "anou(s)" (HG057, HG065: aquí spaCy dio
    PROPN), y coincide con la elección equivocada del motor en "calces"
    (HG038), "gandula" (HG048, spaCy PROPN) y "recuita" (HG092);
  - **el margen mantiene la elección equivocada del motor (8)**: FLOR
    prefería la correcta, pero por menos de 5: calces (HG039-HG042), deu
    (HG079-HG081, con spaCy NUM) y recuita (HG091).
- Avisos de emparejamiento con spaCy: 65, en 44 de las 253 frases.

## Homógrafos v2: equilibrado por sentido (02/11/2026)

`homografs_v2` (160 frases): las 18 formas de homonimia léxica que
llegan al postprocesado, cada una con **4 frases por sentido**. Los
sentidos salen de los `lemas` del léxico, más el verbo en "manca",
"manques" (mancar) y "deu" (deure). Las frases son
`model_llengua/frases_homografs_v2.json`; el benchmark se genera con
`genera_benchmark.py --v2`. Como en la v1, la referencia es el motor con
el candidato correcto, y conviene revisarla a mano. Página:
`resultats/homografs_v2.html`; las 160 trazas coinciden con
`translate_cat_val`.

| Sistema | Total | Sentido dialectal (72) | Sentido no dialectal (88) |
|---|---|---|---|
| Motor solo (siempre traduce) | 82/160 | 68 | 14 |
| **Motor + spaCy + FLOR** | **112/160 (70 %)** | **45** | **67** |

- El postprocesado arregla 53 frases de sentido no dialectal ("nou"
  nuevo y nueve, "deu" diez y deber, "manca" verbo...), pero estropea 23
  del sentido dialectal. Con el benchmark equilibrado se ve que **tira a
  dejar la palabra catalana**.
- **Sentidos que fallan**:
  - **"nou"/"nous" fruto (1/4 y 0/4)**: spaCy da ADJ o NUM, y con NOUN
    FLOR prefiere "nou(s)";
  - **"deu" manantial (1/4)** y **"rentadora(es)" lavadora (1/4 y
    1/4)**: FLOR prefiere la forma catalana;
  - **"calces" calzas (0/4)**: los dos sentidos son nombres, spaCy no
    puede separarlos y FLOR elige "bragues";
  - **"gandula/es" vaga (1/4 y 1/4)** y **"recuita" recocida (1/4)**:
    spaCy da NOUN y FLOR elige el sentido dialectal.
- **Sentidos que van bien** (4/4 o 3/4): los números, los verbos,
  "nou/nous" nuevo, "gandula/es" tumbona, "recuita" requesón,
  "fartanera" en los dos sentidos, "reeixida" en los dos.
- Etiquetas de spaCy en la palabra ambigua: aciertan la categoría del
  sentido en la mayoría de casos, pero los nombres del sentido dialectal
  salen ADJ (10), NUM (4) o PROPN (4) en 18 de 72.

### Concordancia con el artículo (APLICADA en parte el 03/11/2026)

**Lo aplicado** (`model_llengua/punts.py::decisio_spacy`): si spaCy dice
ADJ y el género del adjetivo no es el del determinante de delante ("una
nou", "les nous": "nou" adjetivo es masculino), spaCy se ha equivocado:
no decide y pasa a FLOR (con el margen 5, así que suele quedar lo del
motor, "anou"). Resultado con P1: v2 122 → **124** (HG2-004 "una nou",
HG2-016 "les nous"), manual 227 → **228** (BM-AVL-191 "les nous"),
homógrafos 233 igual; 0 pérdidas. En los benchmarks reales (manual,
151, BOE, gplsi) spaCy decide 157 veces en irresolubles y la regla solo
salta en BM-AVL-191.

**Lo que NO se aplica, y por qué** (usuario, 03/11): si spaCy dice NUM
("una nou", "la nou"), el determinante no descarta nada: un numeral hace
de nombre con cualquier artículo ("la nou" = la jugadora del dorsal
nueve, "la nou" = la carretera). Tampoco se mira el número ("les nou" =
las nueve). Por eso HG059, HG2-001 y HG2-003 siguen fallando. Probado de
paso: **FLOR no distingue "nou"/"anou"**: con la nuez prefiere "nou"
(8-11 puntos, es lo que ve en catalán) y con la jugadora casi no separa;
el singular "nou" necesita otra señal.

Planteamiento original (02/11):

spaCy se equivoca con "nou", pero acierta con el artículo de delante:
"una/la nou" (femenino singular) solo puede ser nuez; "el/un nou",
nuevo; "les nou" (plural con la palabra en singular), nueve; "les/unes
nous", nueces; "els nous", nuevos. La regla general sería descartar las
lecturas cuyo género o número no concuerdan con el determinante, como
paso entre la decisión de spaCy por categoría y FLOR. FLOR se sigue
usando en todo lo que la gramática no decide: cop, calces, gandula,
rentadora, recuita, panotxa, fartanera, y "nou(s)" sin artículo.
Arreglaría unas 5 de las 8 frases de "nou/nous" fruto de la v2 (y quizá
"una deu"). Necesita el género de cada lectura: añadido a los `lemas`
del léxico ("nou [n, f]") o calculado con spaCy a partir de la palabra
valenciana. Antes de aplicarlo, medirlo en la v1, la v2 y el manual.

### Posibles arreglos (sin implementar): el sesgo de FLOR hacia la palabra frecuente

FLOR prefiere la forma que ha visto más veces ("rentadora" frente a
"llavadora", "deu" frente a "brollador", "nou" frente a "anou"), porque
se entrenó con mucho más catalán que valenciano. Medido con las
puntuaciones de las trazas, en la v1 (101 palabras ambiguas) y la v2
(160) a la vez; ahora mismo hay 83 + 112 = 195 aciertos:

| Prueba | v1 | v2 | Total |
|---|---|---|---|
| Ahora (λ 0,5, margen 5) | 83 | 112 | 195 |
| Otro λ u otro margen (mejor combinación) | 81 | 120 | 201 |
| A. Margen más alto para **quitar** la palabra valenciana (10) | 80 | 119 | 199 |
| **B. Párrafo en valenciano delante de cada frase**, margen 5 | **87** | **115** | **202** |
| B con margen 8 | 84 | 120 | 204 |

- A y los cambios de λ o margen solo pasan aciertos de un benchmark al
  otro.
- **B mejora los dos a la vez** (+4 y +3) sin entrenar nada: antes de
  cada frase candidata se le pasa a FLOR un párrafo fijo en valenciano
  normativo ("Este és un text escrit en valencià. Hui els xiquets han
  eixit prompte de l'escola...") y se puntúa la frase condicionada a ese
  párrafo. Coste: unas 30 palabras más por llamada. Solo se ha probado
  un párrafo y en estos dos benchmarks: hay que probar otros párrafos y
  medirlo en el manual.
- Arreglos de fondo, más caros:
  - **adaptar FLOR al valenciano**, continuando su entrenamiento con
    texto valenciano (AVL, BOE en valenciano), en Abaco con GPU una sola
    vez; luego se sigue usando en CPU igual;
  - **corregir la frecuencia de cada palabra con un corpus valenciano**
    en lugar de con la de FLOR (el `prior` de la fórmula), sacada de los
    datos, sin listas;
  - probar **FLOR-1.3B** (pendiente desde el 29/10).
- Ninguno de estos arregla los fallos de spaCy ("nou" ADJ: ver la
  concordancia, arriba) ni "calces" (dos nombres con el mismo género:
  es cuestión de significado).

## Lo que se ha visto con las trazas (02/11/2026)

En las 31 frases del manual mezcla que pasan por FLOR, la traza coincide
con `translate_cat_val` en las 31. Además salieron tres problemas del
traductor (1 y 3 **arreglados el 03/11/2026**; 2 sigue abierto):

1. **"Necessito" a principio de frase** sale PROPN (nombre propio) y la
   capa de conjugaciones no la traduce. Es el error conocido del 28/10.
   **Arreglado (03/11)**: en `cat_val/conjugacions_dict.py::_pos_admet`
   el PROPN solo bloquea si la palabra va en mayúscula y no es la primera
   de la frase (`_inici_de_frase`: antes solo hay espacios, comillas o
   paréntesis y luego el inicio del texto o ". ! ? …"). Un PROPN en
   minúscula es un error de spaCy ("sanciono", "sol·licitin"). Motor, en
   todos los benchmarks: 17 frases cambian, **+10 exactas / −1**
   ("Necessito", "Estudio", "Afirmin", "Transmetin", "Sapigueu… sanciono"
   ×6; pierde "E. coli", que va en minúscula y ahora se traduce como
   verbo).
2. **Emparejamiento con spaCy**: `pos_tagger.etiqueta` da a cada palabra
   la etiqueta de la **primera** aparición de esa palabra en la frase,
   no la de su posición. En 8 de las 31 frases la etiqueta cambia: un
   "el" pronombre recibe la de artículo (BM-BOE-233), "que" relativo la
   de conjunción, o "capacitat" la de PROPN de un "Capacitat" anterior
   (BM-AVL-168).
3. **Dos palabras ambiguas en la misma frase**: si la segunda cambia el
   apóstrofo ("d'anous" → "de nous"), `aplica_tries` (`_fusiona`) pierde
   ese cambio porque cambia el número de palabras. Ejemplo: "Hem comprat
   un cotxe nou i un sac de nous." → "...un sac d'anous", aunque spaCy
   decide "nous". Aquí, por casualidad, el resultado es el correcto: en
   "un sac de nous" son nueces, pero spaCy las etiqueta ADJ.
   **Arreglado (03/11)**: `_fusiona` alinea el texto del motor con el
   actual y coloca cada cambio, sea del tamaño que sea, sobre las palabras
   que ningún punto anterior ha tocado (si las ha tocado, no lo aplica).
   En todos los benchmarks hay 8 frases con 2+ palabras ambiguas; cambian
   2 (BOE amplio: "d'anou a setze mesos" → "de nou", "de l'anou model" →
   "del nou model"), las dos a la palabra de la referencia; 0 pérdidas.
