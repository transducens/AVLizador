# Hoja de ruta: benchmark manual catalán → valenciano (200 BOE + 200 AVL)

Creada el 23/10/2026. **Actualizada el 26/10/2026 con las decisiones del
usuario del 23/10 (sección 1); las secciones 2, 3 (pasos 5-7) y 6 ya
reflejan lo implementado.**

Estado (26/10/2026):
- Hecho: detector (`benchmark_manual/fenomens.py`), pool de la AVL (760
  frases), pool del BOE (1.049 frases, ~1 min: filtros baratos sobre todo
  el corpus y el GD solo sobre las 28.429 candidatas que quedan).
- Pendiente: `selecciona.py` (250 + 250), revisar la cobertura con el
  usuario y pasar los dos JSON al equipo.

## 0. Objetivo

Construir un banco de prueba de **400 frases revisadas a mano** para medir
el traductor catalán → valenciano que se entrega a la Conselleria:

- **200 frases del BOE**, del corpus alineado catalán/valenciano. La
  referencia valenciana la corrige el usuario cuando el BOE reformula.
- **200 frases de la AVL**, del scraping, de todos los tipos de texto.

Cada frase tiene que **contener al menos un fenómeno que el traductor debe
resolver** (sección 2), y el conjunto tiene que cubrir todos los fenómenos
y todos los registros. Una frase "muy buena":

1. Es una frase completa y natural, de 8 a 40 palabras, sin listas,
   títulos, tablas ni restos de OCR.
2. Contiene uno o más fenómenos del catálogo, preferiblemente 2-3
   distintos.
3. Su valenciano es **valenciano estándar de la AVL**, el que se espera de
   un texto para toda la población de la Comunidad Valenciana: sin formas
   subdialectales ni coloquiales que la norma no recoja, y sin catalanismos.
4. Su GD es el esperado: valenciano claramente occidental y catalán
   claramente oriental (sección 3, paso 3).
5. No está en el banco de 151 ni en otro benchmark ya usado para ajustar el
   motor.
6. No es metalingüística: frases que hablan de palabras ("la paraula
   *rentar*…"), habituales en el glosario de la AVL, citan a propósito las
   dos variantes y no sirven para medir.

Es una prueba independiente del motor. Las frases se eligen por lo que
dice el texto de referencia, **no por lo que hace hoy el motor**, para que
el banco mida también los huecos y no solo lo que ya se acierta.

## 1. Decisiones

### Lo que decidió el usuario (23/10/2026)

| # | decisión |
|---|---|
| D1 | El catalán de las frases de la AVL es un **borrador del motor valenciano → catalán** (`traductor.translate`) que el equipo **corrige a mano**. El valenciano del BOE también se corrige a mano cuando reformula. |
| D2 | **Sin HTML**: se revisa directamente en JSON. El equipo se reparte el trabajo en dos ficheros, `revisio_persona1.json` y `revisio_persona2.json`. |
| D3 | Cuotas = **los fenómenos de los diccionarios** (por `categoria` del léxico y por `morfologia` de las conjugaciones) **y, desde el 26/10, también los de las reglas del motor**: "per a" + infinitivo, dos/dues, incoativos y acentuación ("que esté representado casi todo"). |
| D4b | (26/10) En el pool del BOE **no hay máximo de frases por documento**; en la selección se mantiene el de 2. |
| D4 | Las muestras del BOE ya usadas (semilla 21) **no se excluyen**. Sí se excluyen el banco de 151 y los duplicados. |
| D5 | **250 candidatas por fuente**; luego el equipo revisa a mano y se quedan 200 + 200. |

### Propuesta original (23/10, sustituida por la tabla de arriba)

| # | decisión | propuesta |
|---|---|---|
| D1 | **El lado catalán de las frases de la AVL.** La AVL solo está en valenciano, y el traductor necesita catalán de entrada. | Generar un **borrador** con el motor valenciano → catalán y que el usuario lo corrija hasta que sea catalán natural de la norma IEC. Riesgo: si el borrador no se corrige bien, la entrada "se parece" a lo que el motor espera. Se marca cada frase con `catala_revisat: true/false` y solo entran las revisadas. Alternativa: que alguien escriba el catalán desde cero (más fiable, más lento). |
| D2 | **Herramienta de revisión.** | Un **HTML local**, un solo fichero que se abre en el navegador y no sube nada: botones Sí / No / Dudosa, campos para corregir los dos lados, guardado automático en el navegador y botón para exportar un JSON. Si la revisión la tienen que hacer o ver otras personas, se puede publicar como página compartida con base de datos. |
| D3 | **Cuotas por fenómeno** (sección 2). | Los mínimos de la tabla; una frase cuenta para todos los fenómenos que contiene. |
| D4 | **Qué se excluye.** | El banco de 151 (los 62 documentos de la AVL de los que sale y, por similitud de texto, el resto); las muestras de 2.000 líneas del BOE ya usadas (`benchmark_boe_mostra_2000.json`, `benchmark_boe_dialectal_*.json`, semilla 21), para que el banco nuevo sea independiente; y los 98 homógrafos inventados. |
| D5 | **Sobremuestreo.** | Proponer **500 candidatas de cada fuente** (2,5 veces lo necesario) para que, tras descartar, queden 200 + 200 con las cuotas cubiertas. |

## 2. Catálogo de fenómenos a cubrir

### Implementado (D3, `benchmark_manual/fenomens.py`)

Un fenómeno es una entrada de `traductor/data/lexic_general.json` o de
`conjugacions_dialectals.json`, clasificada por su propio campo. Un solo
fenómeno por par (si un par sale en varias entradas, gana el más
específico: el subjuntivo gana al imperativo en "puguin"). Se detecta en
la referencia: BOE = la forma catalana en el texto catalán y la valenciana
en el valenciano; AVL = los marcadores valencianos del GD buscados en el
índice valenciano.

| código | qué | mínimo por fuente (de 250) |
|---|---|---|
| LEX_NOM / LEX_ADJ / LEX_ADV / LEX_ALTRES | léxico, por `categoria` (n, adj, adv, resto) | 40 / 20 / 20 / 10 |
| DEM | `categoria: "det"` (demostrativos) | 30 |
| POS | `det` con `fuente: "avl_equip"` (posesivos) | 20 |
| NUM | `fuente: "numerales"` o `categoria: "num"` | 10 |
| CONJ_IND / CONJ_SUBJ / CONJ_IMP / CONJ_INF / CONJ_PART | conjugaciones, por `morfologia` | 20 / 25 / 10 / 10 / 15 |
| CONJ_ARREL | verbos de raíz distinta (`infinitiu_cat`) | 20 |
| HOM | la entrada es `homonimia_lexica` o `colision_homonima` | 10 |
| PER_A | "per" + infinitivo → "per a" | 15 |
| DOS_DUES | "dues" → "dos" | 10 |
| INC | incoativos ("ofereix" → "oferix") | 20 |
| ACC | acentuación ("francès" → "francés") | 15 |

Los cuatro últimos (26/10) no salen del diccionario sino de las **mismas
reglas del motor aplicadas solas**: en el BOE, la regla cat→val propone el
cambio sobre el catalán y cuenta si la referencia valenciana lo trae; en
la AVL, la regla espejo val→cat (dos/dues con el género de spaCy) y, para
"per a", spaCy (`VerbForm=Inf`, sin "per a haver"). Si un par ya lo da el
diccionario, no se cuenta dos veces.

Cuotas por tipo de texto en la AVL (de 250): glossari 85, nota-de-premsa
70, acord-normatiu 30, butlleti 25, gramatica_normativa 15, pagina 10,
publicacions 8, legislacio 5. Máximo 6 frases por par concreto y 2 por
documento.

### Propuesta original (23/10, sustituida por la de arriba)

Son las reglas del motor catalán → valenciano (`traductor/rules/cat_val/`)
más los casos en que **no** debe cambiar nada. Cada fenómeno se detecta en
el **texto de referencia**, no en la salida del motor.

| código | fenómeno | ejemplo cat → val | cómo se detecta | mínimo BOE | mínimo AVL |
|---|---|---|---|---|---|
| LEX | léxico (par del diccionario) | avui → hui, sortida → eixida | palabra del lado catalán cuyo par está en el léxico y aparece en el valenciano | 40 | 40 |
| CONJ | conjugación (forma distinta) | tenir → tindre, sigui → siga | par del diccionario de conjugaciones | 40 | 40 |
| SUBJ | subjuntivo (-i → -a/-e) | que sigui → que siga, puguin → puguen | CONJ con `morfologia` de subjuntivo | 15 | 15 |
| INC | incoativos (-eix → -ix) | serveix → servix, ofereixen → oferixen | forma -eix/-eixen con lema en -ir del diccionario | 20 | 15 |
| DEM | demostrativos | aquest → este, aquesta → esta | entradas `det` del léxico | 25 | 25 |
| DEM2 | "aquest" que el valenciano escribe "eixe" | aquest → eixe | DEM con "eixe" en la referencia (mide el error del valor por defecto) | 5 | 5 |
| POS | posesivos | seva → seua, meves → meues | entradas de posesivos del léxico | 20 | 20 |
| NUM | numerales y ordinales | vuit → huit, dinou → dènou, cinquè → quint | entradas `num` y ordinales | 10 | 10 |
| ACC | acentuación | francès → francés, conèixer → conéixer | -ès/-èixer en catalán con -és/-éixer en la referencia | 20 | 20 |
| PERA | per + infinitivo → per a | per fer → per a fer | "per" + infinitivo (spaCy) con "per a" en la referencia | 15 | 10 |
| ART | artículo, apóstrofo o contracción tras sustituir | la sortida → l'eixida, de la despesa → del gasto | LEX que cambia la inicial o el género de la palabra | 10 | 10 |
| DOS | dos/dues | les dues → les dos | "dues" en catalán y "dos" en la referencia | 10 | 10 |
| HOM+ | homógrafo que sí se traduce | la manca → la carència | `homonimia_lexica` con la lectura dialectal | 5 | 5 |
| HOM− | homógrafo que no se traduce | li manca → li manca, nou cotxe | `homonimia_lexica` u homógrafo de conjugación con la otra lectura | 10 | 10 |
| MAJ | mayúsculas y nombres propios | Servei de Salut → Servici de Salut | palabra en mayúscula con par en el léxico | 10 | 5 |
| CTRL | control: nada cambia | — | frase idéntica en los dos lados, con palabras que podrían confundir | 15 | 15 |

**Para toda la población**: además de los fenómenos, el banco debe
repartirse entre registros y temas.

- **BOE**: registro administrativo y legal, de varios años (2009-2015) y
  tipos de disposición; como máximo 2 frases por documento.
- **AVL**: todos los `doc_type`. El corpus `corpus_occidental_net.jsonl`
  tiene 1.778 documentos: glossari 1.394, nota-de-premsa 168,
  gramatica_normativa 117, butlleti 39, acord-normatiu 25, pagina 23 y
  algunos más. Propuesta de reparto de las 200: glossari 60, nota-de-premsa
  50, gramatica_normativa 30, butlleti 25, acord-normatiu 15, pagina y el
  resto 20. Como máximo 2 frases por documento.

## 3. Pasos

### Paso 1 — Detector de fenómenos y medida de frecuencias

- **Qué**: un script que, para un par catalán/valenciano (o solo valenciano,
  en la AVL), devuelve los fenómenos de la sección 2 que contiene, con las
  palabras concretas. Usa los mismos cargadores que el traductor y el GD,
  sin listas a mano.
- **Medida**: cuántas frases de cada fuente tienen cada fenómeno. Así se
  sabe si las cuotas son realistas (por ejemplo, los posesivos de primera
  persona son raros en el BOE) y se ajustan antes de seleccionar.
- **Entregable**: `pipeline/03_seleccio_de_model/benchmark_manual/detecta_fenomens.py`
  + una tabla de frecuencias.

### Paso 2 — Extracción, segmentación y filtros de calidad

- **BOE**: `dades/boe/corpus_entrenamiento.jsonl` (267.962 pares
  alineados, campo `similitud`). Se quedan los pares con:
  - alineación buena: `similitud` alta y relación de longitudes entre 0,85
    y 1,15 (el mismo criterio que la muestra de 2.000);
  - de 8 a 40 palabras, mayúscula inicial y puntuación final;
  - sin listas, numeraciones, tablas ni cabeceras ("DISPOSICIONS
    GENERALS").
- **AVL**: `dades/avl/final/dialectal/corpus_occidental_net.jsonl`, que ya
  está filtrado como valenciano occidental. Se segmenta en frases con el
  mismo segmentador de la etapa 1 y se aplican los mismos filtros de
  longitud y forma. Además se descartan las frases metalingüísticas:
  comillas o cursiva alrededor de una palabra, "la paraula…", "es diu…",
  "en castellà…".
- **Entregable**: `pool_boe.jsonl` y `pool_avl.jsonl` en
  `dades/benchmark_manual/`, una frase por línea con su procedencia
  (documento, fecha, `doc_type`).

### Paso 3 — Filtro de GD

El GD (`pipeline/09_grau_dialectal/gd.py`, `calcula_gd`) dice
qué parte de las palabras dialectalmente marcadas de un texto son
valencianas. Lo esperado para este banco:

| lado | condición | por qué |
|---|---|---|
| valenciano (BOE y AVL) | GD = 1,0 **y** al menos 2 marcadores valencianos | la referencia tiene que ser valenciano claro, sin formas catalanas |
| catalán (BOE) | GD = 0,0 **y** al menos 2 marcadores catalanes | la entrada tiene que ser catalán claro |
| catalán (AVL, tras el paso 6) | GD = 0,0 | el catalán revisado no puede dejar formas valencianas |

Las frases de control (CTRL) son la excepción: no tienen marcadores.
Límite conocido: el GD usa el mismo diccionario que el traductor; mide
que el texto tenga las formas conocidas, no que sea buen valenciano, y
por eso hace falta además la revisión a mano. El HTML de revisión mostrará
el GD de cada lado y resaltará los marcadores.

### Paso 4 — Exclusiones

- El banco de 151: los 62 documentos de la AVL de los que salen sus frases
  (campo `corpus_id`), fuera enteros. El resto se compara por similitud de
  texto, y se descarta todo lo que se parezca más de un 60%.
- Las muestras del BOE ya usadas (D4).
- Duplicados y casi duplicados dentro del propio pool. El BOE repite
  mucho: "Contra aquesta resolució, que exhaureix la via administrativa…".

> **Lo implementado (26/10)**: D4 cambia el paso 4 (no se excluyen las
> muestras del BOE); por D2 no hay HTML (paso 7): `selecciona.py` escribe
> directamente `revisio_persona1.json` / `revisio_persona2.json` con los
> campos `valida`, `oriental_corregit`, `occidental_corregit` y
> `comentari`, y las frases de la AVL llevan el borrador catalán marcado
> (`oriental_es_esborrany: true`, y en cada fenómeno "[l'esborrany no ho
> ha convertit]" cuando hace falta). Por D5 son 250 + 250, no 500 + 500.
> Pool del BOE: los filtros baratos (calidad, alineación, fenómeno,
> duplicados) sobre las 267.962 líneas; la semejanza con el 151 y el GD
> (spaCy en las dos lenguas) solo sobre las candidatas que quedan (28.429;
> tope `MOSTRA_BOE = 50000` con muestra aleatoria de semilla 23 si se
> supera).

### Paso 5 — Selección estratificada (500 + 500 candidatas)

- Se eligen frases hasta cubrir los mínimos de la sección 2, empezando por
  los fenómenos más raros. A igualdad, gana la frase con más fenómenos
  distintos.
- Se respetan el reparto por tipo de texto y el máximo de 2 frases por
  documento.
- Con semilla fija, para que se pueda repetir.
- **Entregable**: `candidates_boe.jsonl` y `candidates_avl.jsonl`, con
  la tabla de cobertura resultante.

### Paso 6 — Lado catalán de la AVL (borrador)

Según D1: borrador con el motor valenciano → catalán, marcado
`catala_revisat: false`. En el HTML, el usuario lo corrige hasta que sea
catalán natural de la norma IEC. Las frases sin corregir no entran en el
banco final.

### Paso 7 — HTML de revisión

Un fichero `dades/benchmark_manual/revisio.html`, autónomo:

- Una tarjeta por frase: catalán y valenciano, con los marcadores del GD
  resaltados; los fenómenos que contiene; procedencia (documento, fecha,
  tipo de texto) e GD de cada lado.
- Botones **Sí / No / Dudosa**, campos para **corregir** el catalán y el
  valenciano y un comentario.
- Filtros por fuente, fenómeno, tipo de texto y estado. Contador de
  cobertura en vivo: cuántas aceptadas hay de cada fenómeno frente al
  mínimo.
- Se guarda solo en el navegador (`localStorage`), sin perder nada al
  cerrar. Un botón **Exportar** descarga `revisio_<fecha>.json`.

### Paso 8 — Incorporar la revisión y segunda ronda

- Un script lee el JSON exportado, aplica las correcciones y recalcula el
  GD de las frases corregidas, avisando si alguna deja de cumplir el
  paso 3.
- Si algún fenómeno queda por debajo del mínimo, se proponen más
  candidatas de ese fenómeno y se repite el paso 7 solo con ellas.

### Paso 9 — Corrección final de los textos

- **BOE**: donde la referencia oficial reformula (añade, quita o cambia de
  orden), el usuario la deja como una adaptación dialectal fiel del
  catalán: las mismas palabras y estructura, solo con los cambios del
  valenciano.
- **AVL**: catalán revisado (paso 6).
- Cada frase guarda el texto original y el corregido, para poder ver qué se
  cambió.

### Paso 10 — Validación y congelación

- Comprobaciones automáticas: GD final, cobertura por fenómeno y por tipo
  de texto, ningún duplicado ni solapamiento con el 151.
- **Línea base**: ejecutar `evalua_models.py --model traductor` y
  `--model traductor_ml` sobre el banco nuevo, con el desglose por
  fenómeno. Es la primera medida "limpia" del traductor.
- Congelar como `benchmark_manual_cat_val_v1.json`, con un README que
  explique el criterio, las cuotas, quién revisó y cuándo. A partir de ahí
  no se cambia: si hace falta corregir algo, se saca una v2.

## 4. Formato final

Lista de objetos JSON compatible con `evalua_models.py`. El desglose sale
solo del campo `categoria`:

```json
{
  "id": "BM-BOE-001",
  "oriental": "frase catalana (entrada)",
  "occidental": "frase valenciana (referencia)",
  "categoria": "boe",
  "fenomens": ["DEM", "POS", "CONJ"],
  "paraules": {"DEM": ["aquesta→esta"], "POS": ["seva→seua"], "CONJ": ["tinguin→tinguen"]},
  "font": "BOE-A-2012-1234",
  "doc_type": "boe",
  "gd_val": 1.0, "gd_cat": 0.0,
  "original_oriental": "…", "original_occidental": "…",
  "revisat": true, "revisor": "…", "data_revisio": "2026-10-…"
}
```

Para tener el desglose por fenómeno con `evalua_models.py`, se puede
generar también una versión con una fila por fenómeno principal, o
analizar después los resultados con el campo `fenomens`.

## 5. Riesgos y cómo se evitan

| riesgo | cómo se evita |
|---|---|
| Que el banco solo mida lo que el motor ya hace bien | los fenómenos se detectan en la referencia, no en la salida del motor (paso 1) |
| Catalán de la AVL "hecho a medida" del motor | borrador marcado y revisión obligatoria (D1, paso 6) |
| Referencias del BOE reformuladas | filtro de alineación (paso 2) y corrección a mano (paso 9) |
| Frases metalingüísticas del glosario | filtro del paso 2 y la revisión |
| Un registro o un documento dominan el banco | cuotas por tipo de texto y máximo de 2 frases por documento (paso 5) |
| El GD da por bueno un texto que no lo es | el GD solo filtra; la revisión a mano decide |
| Ajustar el motor mirando este banco | se congela (paso 10) y se usa solo para medir |

## 6. Reparto del trabajo

| paso | quién | esfuerzo aproximado |
|---|---|---|
| 1-5 (detector, pool, GD, exclusiones, selección) | Claude | una sesión |
| 6 (borrador del catalán de la AVL) | Claude | parte de la misma sesión |
| 7 (HTML de revisión) | Claude | parte de la misma sesión |
| revisión de 1.000 candidatas | usuario | unas 4-6 horas (unos 15-20 s por frase) |
| 8 (incorporar y segunda ronda) | Claude + usuario | corto |
| 9 (corrección final) | usuario | depende de cuántas reformulaciones del BOE haya |
| 10 (validación, línea base, congelación) | Claude, con la ejecución del usuario | corto |

## 7. Resultado: benchmark generado (28/10/2026)

El equipo terminó la revisión. La corrección se hizo directamente en los
campos `oriental` y `occidental` de `revisio_persona1.json` y
`revisio_persona2.json`. El reparto entre las dos personas se cambió
respecto al del 26/10.

**Fichero**: `dades/benchmark_manual/benchmark_manual_cat_val.json`.

**Para regenerarlo** (después de cualquier cambio en los ficheros de
revisión):

```
python pipeline/03_seleccio_de_model/benchmark_manual/construeix_benchmark.py
python pipeline/09_grau_dialectal/mesura_corpus.py --corpus manual_val manual_cat --reinicia
```

El script aplica los criterios de abajo y lista las frases que quedan
fuera. También avisa (y termina con error) si hay ids o pares
repetidos, frases vacías, espacios sobrantes o frases con el catalán
igual que el valenciano. No corrige nada.

El fichero tiene
el mismo formato que el 151: una lista de `{id, oriental, occidental}`,
así que funciona con `evalua_models.py --benchmark`. El `id` es el de la
revisión (`BM-BOE-…`, `BM-AVL-…`), que es único y dice la fuente. Las
frases van ordenadas por id: primero el BOE y luego la AVL.

Decisiones del usuario:
- solo entran las frases con `valida: true`;
- se usa el texto original revisado;
- en BM-BOE-002 y BM-BOE-006 se usa `occidental_corregit`;
- el ID es el campo `id`.

**Total: 453 frases**

| Fuente | Frases | Palabras (val / cat) |
|---|---|---|
| BOE | 241 | 7.717 / 7.690 |
| AVL | 212 | 5.499 / 5.501 |
| **Total** | **453** | **13.216 / 13.191** |

**Fuera: 16 frases**
- 7 marcadas `false`: BM-BOE-047, 073, 117 y 224, y BM-AVL-009, 126
  y 183;
- 9 marcadas como dudosas (escritas "dubtosa", "dubotosa" o "dubotsa"):
  - persona 1: BM-BOE-115, 121, 123 y 147;
  - persona 2: BM-BOE-082 y BM-AVL-002, 014, 104 y 108.

**Comprobaciones**: no hay ids repetidos, ni pares duplicados, ni
espacios sobrantes, y en ninguna frase el catalán es igual al valenciano.

Hay tres frases válidas con comentarios de duda. Se incluyen porque
están marcadas `true`:
- BM-BOE-011: "si s'escau";
- BM-BOE-187: "-los" / "els haurà de";
- BM-BOE-195: "hi".

El GD, el GDV y el GDC del benchmark están en
`documentacio/resultats_gd_gdv_gdc.md`, sección 6. Allí también salen
las posibles erratas que quedan en el lado catalán.

## 8. Primera evaluación del traductor cat→val (28/10/2026)

```
cd pipeline/03_seleccio_de_model
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_cat_val.json
```

Sistema final: motor + FLOR-760M para los homógrafos, con los datos
sincronizados el 28/10. Resultado en
`resultats/benchmark_Traductor_Invers_ML_FLOR-760M_20261028_1623.json`,
sobre el benchmark regenerado a las 16:21. Hay una ejecución anterior,
la de las 14:10, sobre la primera versión del benchmark: 316/453, BLEU
96,63.

| Fuente | Frases | Exactas | % |
|---|---|---|---|
| BOE | 241 | 120 | 49,8 % |
| AVL | 212 | 193 | 91,0 % |
| **Total** | **453** | **317** | **70,0 %** |

BLEU 96,85, chrF 98,81 y 0 errores (ninguna línea `ERROR:`). De las 136
frases que fallan, 91 tienen una sola diferencia y 45 tienen dos o
tres.

La AVL sale muy alta porque su catalán es un borrador del motor
val→cat, corregido después a mano. El BOE sale bajo sobre todo por la
referencia (ver la tabla A).

Análisis palabra a palabra (`difflib` entre la salida y la referencia).
Cada frase se ha clasificado por su causa principal; algunas tienen más
de una.

### A. Problemas de la referencia: para la revisión manual del equipo

Son diferencias que no son dialectales. El valenciano del BOE conserva
reformulaciones que no están en el catálogo.

| Tipo | Frases (BM-BOE-…) |
|---|---|
| Cambio de tiempo o modo ("pot"→"podrà", "s'aplica"→"s'aplicarà", "Estan"→"Estaran"…) | 016, 019, 069, 072, 077, 083, 094, 095, 096, 101, 105, 109, 110, 122, 127, 144, 149, 158, 163, 164, 174, 175, 178, 184, 198, 214, 233, 247 (28) |
| Solo puntuación (comas, «, ;) | 035, 050, 119, 129, 136, 137, 139, 160, 219, 223, y en parte 006, 024, 043, 045, 070, 091, 170 |
| Solo mayúsculas | 051, 054, 092, 107, 143, 148, 166 |
| Palabras añadidas o quitadas, o sinónimos no dialectales ("mitjançant"→"per mitjà de", "esmentada"→"mencionada", "s'escau"→"és el cas", "alhora"→"al mateix temps", "al"→"en el"…) | 001, 006, 008, 011, 014, 020, 025, 026, 037, 038, 042, 068, 078, 086, 091, 093, 100, 108, 120, 124, 128, 151, 165, 171, 173, 175, 184, 192, 194, 196, 201, 216, 220, 221, 229, 245 |
| Erratas en la referencia | 179 ("han **e** publicar"), 194 ("Sofía", con acento castellano) |
| Forma de la referencia válida en los dos estándares | 065 ("haja estat"), 103 ("defineixen"), 233 ("persisteix"), 059 y 141 ("diferents"/"distints") |

### B. Errores reales del traductor

| Problema | Frases | Causa | Propuesta (no aplicada) |
|---|---|---|---|
| **Subjuntivos sin convertir** ("sol·licitin", "importin", "Afirmin", "iguali") | BOE-024, 178, 207, 212 | Las formas están en `conjugacions_dialectals.json`, pero spaCy `md` las etiqueta como `PROPN`. `cat_val/conjugacions_dict.py::_pos_admet` descarta los `PROPN`, una regla pensada para nombres como "París". | Descartar el `PROPN` solo si la palabra va en mayúscula y no empieza la frase. Hay que medirlo en todos los benchmarks. |
| Subjuntivo que no está en los datos ("coneguin") | BOE-244 | Hueco de datos | Para el compañero |
| **Concordancia tras "despesa"→"gasto"** ("la gasto pública", "gastos associades", "totes els gastos") | BOE-097, 135, 226 | El determinante se corrige, pero el adjetivo y el cuantificador no | Ampliar la concordancia más allá del determinante |
| "El préssec"→"El bresquilla" | AVL-196 | spaCy `md` no conoce el género de "bresquilla" (límite ya conocido) | — |
| "per"+infinitivo → "per a" cuando "per" es causal ("encuriosida per conèixer", "s'opta per prolongar") | AVL-005, 179; BOE-015, 045, 092 | La regla C2 no distingue cuándo "per" lo rige el verbo o el adjetivo | Revisar con el corpus ("optar per", "encuriosit per") |
| "nous"→"anous" no se convierte | AVL-191 | Homógrafo `E0723`: ni spaCy ni FLOR lo resuelven aquí | — |
| "t'haig" no pasa a "t'he" | AVL-057 | `LIMPIO_588` | Dato ya conocido |
| Gerundios, participios e infinitivos que faltan ("rentada", "aixecant", "copejant", "signada", "dipositant", "contenir", "arrodonit", "reportéssim") | AVL-023, 025, 041; BOE-033, 120, 142 | Los verbos nuevos del compañero no tienen todas las formas | Para el compañero |

### C. Decisiones de datos o de registro (las decide el usuario)

| Caso | Frases | Qué pasa |
|---|---|---|
| **"noi/noia"→"xic/xica"** (la canónica es `E0256`-`E0259`); la referencia quiere "xiquet/xiqueta" | AVL-038, 039, 062, 070, 084, 147, 171, 172, 205 (9) | `E0256`-`E0259` "xic" es canónica y `E0260`-`E0263` "xiquet" no. El 151 y la AVL usan "xiquet". |
| **"mentre"→"mentre"**; la referencia escribe "mentres" | BOE-064, 075, 079, 146, 181, 185, 215 (7) | Canónica `E1647` (decisión del 21/10). En el BOE valenciano se usa "mentres". |
| **"aquest"→"este"** cuando la referencia quiere "eixe" | BOE-016, 043, 087, 093, 114, 187, 191, 205, 241, 243 (10) | Límite conocido (deixis); "este" por defecto |
| **"finalitat"→"fi"** (`E1664`/`E1665`) | BOE-087, 089, 103, 167 quieren "finalitat"; BOE-138 y 198 quieren "este fi", pero el motor da "esta fi" | El par nuevo del compañero. Además, el motor no cambia el género del determinante ("fi" en este sentido es masculino). |
| "cadascun"→"cada un" no se convierte | BOE-044, 148, 169 | Coincide con el commit "eliminacion cadascu" del 28/10 |
| "dues"→"dos" (el motor la convierte; la referencia de la AVL deja "dues") | AVL-159 | La AVL admite las dos formas; en cambio BOE-077 sí quiere "dos". |
| "petit"→"xicotet", "sota"→"davall", "forma"→"manera", "fuites"→"fugues", "afer"→"assumpte", "emmagatzematge"→"emmagatzemament", "ullada"→"colp d'ull" | BOE-084, 066, 191, 229, 126, 086, 108; AVL-189 | Pares que faltan o registro |

### Lectura

- **El BOE no se puede leer todavía como medida del traductor.** Más
  de la mitad de sus fallos son de la referencia (tabla A): sobre todo
  cambios de tiempo (28 frases), puntuación y mayúsculas.
- Esto ya se sabía del BOE alineado (de ahí los benchmarks "estricto" y
  "amplio"). La revisión manual debía corregirlo, pero se han quedado
  muchos casos.
- Cuando el equipo revise las frases de la tabla A, el BOE debería subir
  mucho sin cambiar el motor.
- **Lo más útil para el motor** es el fallo de los subjuntivos
  etiquetados `PROPN`. Es un fallo general, no solo de este benchmark, y
  su arreglo es pequeño, pero hay que medirlo antes de aplicarlo.
- La AVL (91 %) está inflada por el origen de su catalán, pero confirma
  los problemas de datos ("xic", "nous", "t'haig") y de concordancia.

**Pendiente (29/10/2026)**:
1. El usuario revisa a mano las frases (tabla A sobre todo) y se
   regenera el benchmark con `construeix_benchmark.py`.
2. Se vuelve a evaluar y a medir el GD.
3. Se deciden con el usuario los casos de la tabla C y la propuesta del
   `PROPN` (tabla B).

## 9. Segunda revisión del BOE y tres benchmarks (29-30/10/2026)

**Por qué.** Al equipo le dijeron que la revisión del BOE (la de las
secciones 7 y 8) no seguía el estilo pedido y que había que partir del
original. **Decisión del usuario**: guardar la revisión anterior y que el
usuario revise él solo el BOE desde el texto original alineado. La
revisión de la AVL se mantiene.

**Qué se hizo:**

1. **Archivo (29/10).** La revisión anterior se guardó sin tocarla en
   `dades/benchmark_manual/archiu/revisio_v1_2026-10-29/`:
   `benchmark_manual_cat_val.json` (453 frases; sistema final 371/453),
   `revisio_persona1.json` y `revisio_persona2.json`.
2. **BOE original (29/10).** `dades/benchmark_manual/revisio_boe_v2.json`
   lleva las frases del BOE tal como salieron del corpus (commit
   `f110b7a`, idénticas a `pool_boe.jsonl`) con la revisión vacía, sin
   las 4 que la revisión anterior marcó `valida: false` (BM-BOE-047, 073,
   117 y 224): 246 frases. Las 5 dudosas de entonces sí están.
3. **Revisión del usuario (29-30/10)**: las 246 `valida: true` (BM-BOE-009,
   que se había quedado en `null`, y los espacios dobles de BM-BOE-201,
   arreglados por el usuario el 30/10).
4. **Tres benchmarks (30/10)**, todos desde
   `construeix_benchmark.py`, que coge la AVL de
   `revisio_persona{1,2}.json` (sus frases del BOE ya no se leen) y el
   BOE de `revisio_boe_v2.json`:

   | Fichero (`dades/benchmark_manual/`) | Frases |
   |---|---|
   | `benchmark_manual_boe_cat_val.json` | 246 (BOE) |
   | `benchmark_manual_avl_cat_val.json` | 212 (AVL) |
   | `benchmark_manual_cat_val.json` | 458 (los dos; mismo nombre de siempre) |

   Mismo formato que el 151 (`id`, `oriental`, `occidental`), así que
   sirven con `evalua_models.py --benchmark`. Están en git (la carpeta no
   está en `.gitignore`).
5. **GD, GDV y GDC de los tres**: `resultats_gd_gdv_gdc.md`, sección 7.
   BOE: val 0,9951 / cat 0,0000. AVL: val 1,0000 / cat 0,0607. Mezcla:
   val 0,9973 / cat 0,0265. Todos los marcadores cruzados que quedan son
   errores conocidos del GD ("finalitat", colisión verbal), no de la
   revisión.

**Aviso del script** (sale con código 1 cuando hay avisos): BM-AVL-057,
el catalán es igual al valenciano ("Mira, si t'he de dir la veritat, no
he pogut fer res.": frase sin ninguna diferencia dialectal). Sin tocar.

**Cómo se regenera y se mide** (desde la raíz del repo):

```bash
python pipeline/03_seleccio_de_model/benchmark_manual/construeix_benchmark.py
python pipeline/09_grau_dialectal/mesura_corpus.py --corpus manual_boe_val manual_boe_cat manual_avl_val manual_avl_cat manual_val manual_cat --reinicia
cd pipeline/03_seleccio_de_model
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_boe_cat_val.json
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_avl_cat_val.json
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_cat_val.json
```

**Pendiente**: ~~decidir BM-AVL-057~~ (se queda tal cual, 30/10);
~~evaluar el traductor con los tres benchmarks~~ (hecho, sección 10).

## 10. Evaluación del traductor en los tres benchmarks + TER y WER (30/10/2026)

**Sistema principal = motor + FLOR-760M** (`traductor.translate_cat_val`,
`evalua_models.py --model traductor_ml`; decisión del usuario, 29/10,
confirmada el 30/10). El motor solo (`--model traductor`) se mide al lado
solo para ver qué aporta el modelo de lenguaje.

### Qué es cada benchmark

| Benchmark | Fichero (`dades/benchmark_manual/`) | Frases | Origen de la referencia valenciana |
|---|---|---|---|
| BOE | `benchmark_manual_boe_cat_val.json` | 246 | Texto oficial del BOE en valenciano, tal cual (revisión v2 del usuario) |
| AVL | `benchmark_manual_avl_cat_val.json` | 212 | Textos de la AVL; el catalán es el borrador val→cat corregido a mano |
| Mezcla | `benchmark_manual_cat_val.json` | 458 | **Las 246 + las 212 juntas**, sin frases nuevas |

La **mezcla** no es un tercer conjunto: es la suma de los otros dos (su
resultado es la media de los dos ponderada por número de frases y
palabras). Sirve como cifra única del benchmark manual, pero queda
dominada por el BOE en TER/WER (tiene más frases y más largas: 32,3
palabras de media frente a 26,4). Para entender qué pasa hay que mirar
el BOE y la AVL por separado.

### Métricas (nuevas en `evalua_models.py` desde el 30/10)

- **Exactas**: frase idéntica a la referencia (sin distinguir mayúsculas,
  apóstrofos normalizados). Muy dura con referencias reformuladas.
- **BLEU / chrF / chrF++** (sacrebleu, media de las frases): coincidencia
  de n-gramas de palabras (BLEU) o de caracteres (chrF; chrF++ añade
  palabras). Más alto = mejor.
- **TER** (nuevo): % de ediciones (insertar, borrar, sustituir palabra o
  **mover un bloque**, que cuenta como 1) para llegar a la referencia.
  `sacrebleu.sentence_ter`. Más bajo = mejor.
- **WER** (nuevo): igual pero sin desplazamientos (Levenshtein por
  palabras; un cambio de orden cuesta una edición por palabra).
  `evalua_models.distancia_paraules`, sin dependencias nuevas. Más bajo =
  mejor. WER ≥ TER siempre; si se separan, hay reordenaciones.
- TER y WER: separación por espacios, distinguen mayúsculas, puntuación
  pegada a la palabra. La cifra del benchmark es **de corpus** (suma de
  ediciones / suma de palabras de la referencia; `ter_corpus`,
  `wer_corpus` en el JSON); cada frase guarda además `ter`, `wer`,
  `ter_edicions`, `wer_edicions` y `ref_paraules`.

### Resultados (30/10/2026, 0 `ERROR:`)

JSON en `pipeline/03_seleccio_de_model/resultats/benchmark_Traductor_Invers{,_ML_FLOR-760M}_20261030_081{4,6,9}.json`
(0814 = BOE, 0816 = AVL, 0819 = mezcla).

| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ |
|---|---|---|---|---|---|---|---|
| BOE 246 | motor solo | 32 (13,0 %) | 83,53 | 93,46 | 92,66 | 9,50 | 10,15 |
| BOE 246 | **motor + FLOR** | 32 (13,0 %) | 83,82 | 93,59 | 92,82 | **9,26** | **9,94** |
| AVL 212 | motor solo | 182 (85,8 %) | 98,35 | 99,16 | 99,12 | 0,80 | 0,80 |
| AVL 212 | **motor + FLOR** | **195 (92,0 %)** | 99,08 | 99,54 | 99,52 | **0,41** | **0,41** |
| Mezcla 458 | motor solo | 214 (46,7 %) | 90,39 | 96,10 | 95,65 | 5,91 | 6,30 |
| Mezcla 458 | **motor + FLOR** | **227 (49,6 %)** | 90,88 | 96,34 | 95,92 | **5,61** | **6,01** |

Ediciones (WER) por frase con motor + FLOR:

| Ediciones | 0 | 1 | 2-3 | 4-6 | 7+ |
|---|---|---|---|---|---|
| BOE (246) | 32 | 36 | 81 | 77 | 20 |
| AVL (212) | 195 | 11 | 6 | 0 | 0 |

### Lectura

1. **FLOR mejora en los tres y no empeora en ninguno.** AVL: +14 / −1
   frases exactas ("cop/cops" → "vegada/vegades/colp", "anou" → "nou";
   pierde BM-AVL-191, "les anous", ya conocido). TER de la AVL a la mitad
   (0,80 → 0,41). En el BOE cambia 12 frases, todas a mejor ("Tot anou
   depòsit" → "Tot nou depòsit", "Un cop" → "Una vegada"), pero ninguna
   llega a exacta porque el resto de la frase ya difiere: por eso las
   exactas no se mueven y el TER sí (9,50 → 9,26).
2. **AVL: casi resuelto.** Los 17 fallos que quedan tienen 1-3
   ediciones y son de tres tipos:
   - "xic/xica/xics/xiques" (canónica del léxico) donde la AVL quiere
     "xiquet/xiqueta" (9 frases): es el "noi"→"xic" de la sección 8, C;
     lo decide el usuario.
   - "reporta/reportar/reportéssim" → "genera/generar/generàrem" (3):
     el catalán corregido a mano dice "reportar" y el léxico no tiene
     este par; es reformulación de la referencia, no dialectal.
   - Sueltos: "dos"→"dues" (BM-AVL-159), "El"→"La" tras un cambio de
     palabra (BM-AVL-196), "ullada"→"colp d'ull" (BM-AVL-189), una "a"
     de más (BM-AVL-005) y BM-AVL-191 ("anous").
3. **BOE: las exactas engañan.** 13 % de exactas, pero TER ≈ 9: una
   palabra de cada diez. Solo 20 frases tienen 7 o más ediciones. La
   referencia es el texto oficial sin retocar, y gran parte de la
   distancia no es dialectal: futuro normativo donde el catalán usa
   presente ("pot"→"podrà" 20, "poden"→"podran" 7, "és"→"serà" 7,
   "ha"→"haurà" 5, "tenen"→"tindran" 3, "correspon"→"correspondrà" 3,
   "S'ha d'imposar"→"S'imposarà"), reformulaciones ("mitjançant"→"per
   mitjà de", "forma"→"manera", "signada"→"firmada", "obtindre"→
   "arreplegar"), artículos añadidos o quitados, este/eixe y orden
   cambiado (por eso WER > TER). En el BOE, **TER/WER y chrF son la
   medida útil**; las exactas, no.
4. **Para comparar sistemas**, la cifra de referencia es el TER/WER del
   BOE y las exactas + TER de la AVL. La mezcla, como resumen.

### Cómo se reproduce

```bash
cd pipeline/03_seleccio_de_model
for b in boe_ avl_ ""; do
  python evalua_models.py --model traductor_ml --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_${b}cat_val.json
  python evalua_models.py --model traductor    --direccio cat-val --benchmark ../../dades/benchmark_manual/benchmark_manual_${b}cat_val.json
done
```

Mirar siempre que no haya líneas `ERROR:` en la salida (la frase se
quedaría sin traducir y contaría como fallo normal).
