*[Léelo en valenciano](README.md)*

# `pipeline/09_grau_dialectal/` — Grado Dialectal (GD)

> **30/10/2026: `gd.py`, `gdv.py` y `gdc.py` se han movido al paquete**
> [`src/avlizador/grau_dialectal/`](../../src/avlizador/grau_dialectal/)
> (`pip install -e .` en la raíz). Se usan con `avlizador gd|gdv|gdc ...`
> o `from avlizador.grau_dialectal import calcula_gd`; donde abajo pone
> `python gd.py ...`, léase `avlizador gd ...`. Aquí se quedan
> `mesura_corpus.py`, el visor y las pruebas.

Novena etapa del proyecto AVLizador (ver `README.es.md` de la raíz):
métrica para saber, de cualquier texto, qué porcentaje de sus palabras
dialectalmente marcadas son formas **occidentales** (valencianas) en vez
de **orientales** (catalanas).

```
GD = total_palabras_occidentales / (total_occidentales + total_orientales)
```

Hasta el 26/10/2026 esta métrica se llamaba **Índice de Pureza
Dialectal (IPD)**, y sus hermanas IPDV/IPDC. Los documentos antiguos
(informes semanales, historial) conservan ese nombre.

Un GD de 1,0 significa que ninguna palabra catalana marcada aparece en
el texto; 0,0 significa lo contrario.

**Texto sin ninguna palabra marcada (decisión del 26/10/2026)**: un
texto sin ninguna palabra dialectalmente marcada de las que conoce el
índice no dice nada sobre su dialecto, y el valor que conviene darle
depende de la tarea. Por eso hay tres modos, elegidos con el parámetro
`dialecte` (`--dialecte` para `--text`/`--fitxer`/`--camp`,
`--dialecte-alt` para `--camp-alt` en la CLI):

| `dialecte` | GD sin marcadores | para qué |
|---|---|---|
| sin poner (por defecto) | `None` (vacío) | medida neutra: el texto no entra en las medias y no favorece a ningún dialecto |
| `"val"` | **1,0** | comprobar que un texto (o una traducción cat→val) es valenciano puro: lo que no tiene nada que lo desmienta cuenta como puro |
| `"cat"` | **0,0** | lo mismo para un texto que debe ser catalán |

Con `"val"`/`"cat"` el resultado queda condicionado por la tarea (los
textos sin marcadores favorecen al lado que se evalúa), así que
no sirve para comparar dialectos. Se probó 0,5 y se descartó: se
confunde con un texto mezclado a partes iguales. En cualquier modo,
`total_marcades == 0` dice que el GD no viene de ningún marcador, y en
el informe HTML esos textos salen en gris. El GD global de un corpus
se calcula con la suma de marcadores, así que solo cambia si el corpus
entero no tiene ninguno.

## GDV e GDC: dos índices simétricos con las palabras neutras (26-27/10/2026)

Además del GD, hay dos medidas hermanas, cada una en su fichero, que
van las dos de **0 a 1** (1 = todas las palabras son válidas en ese
dialecto):

| fichero | medida | fórmula | 1,0 significa |
|---|---|---|---|
| `gdv.py` | **GDV**, Grado Dialectal Valenciano | (occidentales + neutras) / palabras = 1 − orientales / palabras | ninguna forma catalana |
| `gdc.py` | **GDC**, Grado Dialectal Catalán | (orientales + neutras) / palabras = 1 − occidentales / palabras | ninguna forma valenciana |

**Diferencia con el GD (decisión del usuario, 27/10/2026)**: el GD solo
mira los marcadores e ignora las palabras neutras (las que no son
marcador de ningún dialecto: "casa", "amb", "el"...). El GDV y el GDC
las cuentan como válidas en los dos dialectos, porque siguen los dos
estándares. Motivo: poder usarlos como recompensa para entrenar
modelos, donde una frase sin marcadores también es correcta. Por eso
GDV + GDC ya no suma 1, y los dos quedan cerca de 1 (el 95-99 % de las
palabras de un texto son neutras). Un texto sin palabras da 1. Límite:
"neutra" significa "no está en el diccionario de pares", no "es
correcta" (un castellanismo cuenta como válido). No reimplementan nada:
llaman a `gd.py::calcula_gd`, que se queda tal cual.

(Versión del 26/10/2026, ya sustituida: GDV = occidentales / marcadas,
sin las neutras; con marcadores, GDC = 1 − GDV.)

Para un corpus dan dos cifras: `gdv_global`/`gdc_global` (por palabra,
sobre todo el corpus) y `gdv_mitjana`/`gdc_mitjana` (media por frase).
Benchmark de 151 (27/10/2026): GDV del lado valenciano 0,9991 global /
0,9989 media; GDC del lado catalán 0,9914 / 0,9909.

```bash
python gdv.py --text "Este xiquet vol vindre hui."
python gdc.py --text "Aquest nen vol venir avui."
python gdv.py --corpus ../03_seleccio_de_model/benchmark_corpus.json --camp occidental --sortida gdv.json
python gdc.py --corpus ../03_seleccio_de_model/benchmark_corpus.json --camp oriental --sortida gdc.json
```

**Todo de una vez (27/10/2026)**: `mesura_corpus.py` calcula GD, GDV y
GDC de cada documento del 151 (los dos lados), la GNV, la GEIEC (línea a
línea) y el BOE completo (cada lado, por línea y por `documento_id`).
Escribe cada documento en `dades/grau_dialectal/<corpus>.jsonl` en
cuanto lo calcula; si se para, el mismo comando continúa donde se quedó.
Al final deja `resum.json` y `resum.md`.

```bash
python pipeline/09_grau_dialectal/mesura_corpus.py
```

## Por qué un módulo nuevo, si ya existía una métrica parecida

`pipeline/01_extraccio_i_neteja/estudi_dialectal.py` ya calculaba algo muy
parecido (`ratio_occ`, en su tarea 1), pero contra dos listas curadas a
mano de unas setenta palabras cada una
(`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`, dentro del mismo fichero). Este
módulo calcula el mismo índice, pero contra el índice de pares
dialectales que `traductor/` ya mantiene para traducir de verdad:

| | Listas antiguas (`estudi_dialectal.py`) | Índice del GD (`traductor/data/*.json`) |
|---|---|---|
| Tamaño | ~70 palabras por dialecto | ~53.000 pares (1.471 de léxico general + ~52.000 formas verbales conjugadas + demostrativos/posesivos/numerales) |
| Fuente de verdad | Lista aparte, mantenida a mano | La MISMA que usa el traductor para traducir |
| Alcance | Solo documentos ya cargados en `unified.jsonl` | Cualquier texto — una frase suelta, un fichero, un corpus JSONL |

No se reinventa ningún dato nuevo: se reutilizan directamente los
cargadores (`carrega_lexic`, `carrega_conjugacions`,
`carrega_demostratius`, `carrega_numerals`, `carrega_possessius`...) de
`traductor/rules/val_cat/` y `traductor/rules/cat_val/`, en las dos
direcciones (cada dirección resuelve la ambigüedad por su lado, así que
fusionarlas da más cobertura que cualquiera de las dos por separado).

## Limitación conocida, aceptada por ahora

Solo cuenta palabras que aparecen LITERALMENTE en algún diccionario de
lookup exacto. Los patrones PRODUCTIVOS de sufijo del motor (p.ej.
`-és`(occ)/`-ès`(or) de `accentuacio.py`, o la alternancia incoativa de
`incoatius.py`) todavía no están incluidos — cubren un patrón abierto
(cualquier palabra que acabe así), no una lista cerrada, y mezclarlo con
el lookup exacto en esta primera versión complicaba el diseño sin
evidencia todavía de cuánto cambiaría el resultado. Queda documentado
como ampliación pendiente, no como un descuido.

## Uso

Como script:

```bash
python gd.py --text "Este xiquet vol vindre hui."
python gd.py --text "Aquest nen vol venir avui." --dialecte cat
python gd.py --fitxer un_document.txt
python gd.py --corpus ../../dades/avl/final/unified.jsonl --camp text --sortida resultat.json

# Informe HTML para ver y depurar frase a frase (palabras resaltadas en
# verde=occidental/naranja=oriental), con las dos columnas del benchmark
# del proyecto una al lado de la otra (añadid --dialecte val
# --dialecte-alt cat para contar como puros los textos sin marcadores):
python gd.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
    --camp occidental --camp-alt oriental --html informe.html

# Corpus grandes (p.ej. el del BOE, ~268.000 líneas): --limit para
# probar con una muestra antes de lanzarlo entero (cada frase se
# tokeniza con spaCy, así que el fichero completo puede tardar ~30 min):
python gd.py --corpus ../../dades/boe/corpus_entrenamiento.jsonl \
    --camp texto_catalan --limit 5000
```

Acepta tanto un fichero JSONL (un documento por línea) como un JSON
normal con un array de objetos (como `benchmark_corpus.json`) — se
detecta solo.

### `visor_gd.html` — revisar resultados sin volver a ejecutar nada (14/10/2026)

En vez de generar un informe HTML nuevo para cada corpus que se prueba
(que se iba acumulando como ficheros sueltos en el repo, regenerables
pero pesados — ver `CLAUDE_HISTORIAL.md`), `--sortida` (el JSON, no el
`--html`) es ahora la salida recomendada para revisar resultados:
incluye el mismo detalle por documento (texto, GD, marcadores) y, si se
da `--camp-alt`, también los datos de la segunda columna (`text_alt`,
`gd_alt`, `marcadors_*_alt`) — todo lo que hace falta para reconstruir
la comparativa de dos columnas sin volver a ejecutar `gd.py`.

`visor_gd.html` es un visor genérico y reutilizable (sin dependencias,
todo el procesamiento en el navegador, ningún dato sale de ahí) que
carga ese JSON y lo muestra con el texto resaltado y un buscador, igual
que el informe `--html` pero sin generar un fichero nuevo por cada
corpus:

```bash
python gd.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
    --camp occidental --camp-alt oriental --sortida resultat.json
# despues, abre visor_gd.html en el navegador y arrastra resultat.json
```

Admite cargar varios JSON a la vez (en pestañas), para comparar p.ej.
el benchmark y gplsi uno al lado del otro sin generar nada nuevo.

Como módulo, desde otro script del proyecto:

```python
from gd import calcula_gd

calcula_gd("Este xiquet vol vindre hui.")["gd"]  # -> 1.0
```

## Dos bugs reales encontrados y corregidos (13/10/2026, a petición del usuario)

La primera versión hacía un lookup ingenuo con un regex simple.
Revisando el propio benchmark del usuario ("aquestes" casi nunca se
detectaba como marcador oriental) aparecieron dos problemas reales:

1. **Sin filtro de categoría gramatical**: formas verbales RARAS de
   `conjugacions_dialectals.json` (p.ej. "entre" = "jo entre" de
   "entrar") coincidían con palabras COMUNES ("entre" preposición,
   "poden", "sobre", "base", "pobles"...), inflando el recuento dentro
   de texto que no tenía nada de dialectal. Corregido aplicando el mismo
   filtro de POS (spaCy) que ya usa `ConjugacionsDictRule` para traducir.
2. **Prefijo elidido**: el tokenizador trata el apóstrofo como parte de
   la palabra, así que "d'aquestes" es UN SOLO token y nunca casaba con
   la entrada "aquestes". Corregido reutilizando `separa_prefix_elidit`.

## Validación hecha (13/10/2026)

Contra el benchmark de 151 frases de `pipeline/03_seleccio_de_model/benchmark_corpus.json`
(después de los dos fixes): el lado valenciano da **GD 0,9339** (240
marcadores occidentales, 17 orientales) y el lado catalán **GD 0,0153**
(4 occidentales, 258 orientales).

**Confirmado a mayor escala con el corpus del BOE** (`dades/boe/`,
`dades/boe_net/`): el lado catalán se mantiene igual de puro en muestras
mucho más grandes y de un dominio distinto (5.000 frases de
`corpus_entrenamiento.jsonl`: GD 0,0181; 200 frases de
`muestra_test_dialectal.json`: GD 0,0127) — el mismo patrón se repite en
tres corpus independientes. La muestra del BOE también aportó evidencia
mucho más fuerte sobre "qué" (29 apariciones reales sin tocar en
valenciano, frente a solo 4 en el benchmark pequeño) y dos candidatos
nuevos al mismo tipo de problema que "nou" (entradas de léxico sin filtro
de categoría gramatical): "afecte" (confundido con "cariño" cuando en
realidad significa "sujeto a" en texto legal) y "estat" (spaCy a veces lo
etiqueta como verbo cuando es el sustantivo "el Estado").

## Validación adicional (14/10/2026): texto propio del usuario y el corpus gplsi

**Sobre dos noticias reales del usuario** (`proves/noticia_val.txt`
valenciano, `proves/noticia_cat.txt` catalán): GD 0,7308 / 0,1111 —
patrón correcto, pero revisando los marcadores palabra a palabra salieron
3 casos reales a investigar (un 4º, "estes"/"estès", lo descartó el
propio usuario — es una errata real del texto catalán de origen, sin
tilde, no un bug del GD):

1. **"petit"/"menut" mal emparejado** en `lexic_general.json` — después
   confirmado también como bug real del traductor (no solo del GD) con
   el corpus gplsi de abajo.
2. **"què" se cuela como marcador oriental en texto valenciano** porque
   la exclusión `_BUG_DADES_CONEGUTS_CAT` (que ya excluye "què"/"tard"/
   "ensenyament") solo existe en `cat_val/lexic.py`, y `val_cat/lexic.py`
   tiene su propia `_BUG_DADES_CONEGUTS = {"después"}` sin espejar las
   otras 3 — pendiente de arreglar (no rompe ninguna traducción hoy,
   solo contamina el GD, que fusiona las dos direcciones).
3. **"acull" por colisión de persona** (1ª "jo acull" vs. 3ª persona
   compartida) — confirmado que NO afecta a ninguna traducción real (la
   clave de lookup siempre es la forma exacta de una sola persona), solo
   contamina el GD por ser un conteo agregado sin contexto.

**Con el dataset `gplsi/CA-VA_alignment_test`** (Hugging Face, CC BY 4.0,
1.958 frases catalán/valenciano traducidas independientemente): GD
global 0,9039 valenciano / 0,0533 catalán — confirma el mismo patrón que
el benchmark de 151 y el BOE, a una escala y dominio distintos, tercera
confirmación independiente.

**Filtrado por GD para separar sinonimia de fallos reales del motor**:
de las 1.958, 1.139 (58,2%) tienen GD occidental=1,0 Y oriental=0,0 a la
vez — sobre ese subconjunto "limpio", el motor de traducción sube de
65,4%/61,9% a 88,9%/87,9% (val→cat/cat→val), muy cerca del benchmark de
151. Confirma que gran parte de la caída a escala era sinonimia entre
dos traductores independientes, no el motor fallando más.

**El análisis de fallos del motor sobre gplsi** (no del GD, pero
encontrado gracias a esta validación) destapó 4 bugs reales en el
traductor — "xicotet"/"menut"/"petit" mal etiquetado `canonica`, los
pares AVL-only "tindre/vore/obtindre/mantindre" y "últim/darrer"
retirados el 30/09/2026 (~25% de los fallos val→cat), `incoatius.py`
sin cubrir el plural "-ixen", y el plural "servicis"/"serveis" sin
derivar — ver `CLAUDE.md` para el detalle y el estado de cada uno.

## Homógrafos: spaCy solo decide los que declaran los datos (21/10/2026)

spaCy se consulta SOLO para las formas que el proveedor declara como
homógrafas (entradas `problema: "homonimia_lexica"`, campos
`forma_problematica`, `lemas`, `categoria`). Si la lectura dialectal tiene
una categoría que ninguna otra lectura comparte ("manca": n vs. adj), la
forma cuenta solo cuando spaCy le da esa categoría; si la comparte ("bes",
"blanca", "calces"), no cuenta nunca. El resto de palabras no pasa por
spaCy: se probó un filtro general por categoría (con y sin umbral de
seguridad) y se descartó porque spaCy no conoce muchas formas valencianas
("hui", "faena") y les inventa la etiqueta.

| Corpus | Lado valenciano | Lado catalán |
|---|---|---|
| Benchmark 151 | 0,9647 → 0,9749 | 0,1135 → 0,1115 |
| gplsi | 0,9341 → 0,9387 | 0,0685 → 0,0632 |

"després" (E0977, adjetivo "desprès"/"després" frente al adverbio
compartido) y "tancat" siguen contando como marcador falso porque los
datos no los declaran como homógrafos: se resuelve marcándolos en origen.
Detalle en el docstring de `gd.py` ("HOMÒGRAFS ENTRE CATEGORIES").

## Relación con el resto del proyecto

Pendiente documentado en `CLAUDE.md` (sección "Pendiente") y detallado en
`documentacio/hoja_de_ruta_gd_y_proxima_fase.md`: este era el primer
paso a dar antes de seguir ampliando el motor de reglas con más casos del
benchmark, y antes de intentar una capa de modelo (LLM) nueva para
cat→val o de probar con un corpus distinto (el BOE, ya empezado aquí).
