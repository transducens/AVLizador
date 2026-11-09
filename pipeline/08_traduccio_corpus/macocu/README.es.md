*[Llegiu-lo en valencià](README.md)*

# MaCoCu-ca: frases en catalán puro (filtradas por Grau Dialectal)

Saca de **MaCoCu-ca 1.0** las frases en catalán **puro** (GD 0 con al
menos 2 marcadores orientales), para traducirlas después al valenciano
con AVLizador y obtener un corpus paralelo catalán/valenciano con el que
ajustar algún modelo (decisión del usuario, 06/11/2026). **De momento no
se traduce nada**: solo se filtra.

## El corpus

- MaCoCu-ca 1.0, CLARIN.SI, [`hdl 11356/1837`](https://www.clarin.si/repository/xmlui/handle/11356/1837),
  licencia **CC0**. Web de 2022 (dominios .cat, .es, .ad, .fr, .it,
  .eu), 5,9 M documentos, 1.737 M palabras.
- `MaCoCu-ca-1.0.xml.zip` (4,72 GB; md5 `ee39dfa0d626432ae5c44aa9071908bb`),
  15,6 GB descomprimido. El `.dtd` (3 KB) solo describe el esquema.
- Formato "prevert": `<doc>` con título, URL, dominio y fluidez; `<p>` con
  calidad jusText (`good`, `short`, `neargood`...), idioma, fluidez
  (`lm_score` 0-1, Monocleaner), si es título y si tiene datos sensibles.
  Ya vienen sin párrafos casi duplicados.
- Va en `dades/macocu/` (en el `.gitignore`, como las salidas).

**MaCoCu-ca no es solo catalán**: en una muestra de 300 párrafos buenos,
el 51 % era catalán puro, el 6 % valenciano puro (GD 1: Diputació de
Castelló, ayuntamientos...), el 17 % mezcla y el 26 % sin marcadores.

## Cómo se filtra

**Paso 1, `extreu`** (sin spaCy, una pasada; ~1 hora para todo el XML):

1. Párrafos `quality="good"`, `lang="ca"`, no título, no sensibles y
   `lm_score >= 0,7` (deja fuera el ~10 % menos fluido; `--lm-min`).
2. Frases de 8 a 40 palabras, completas, sin listas ni mayúsculas
   enteras y con pocos números (el criterio del benchmark manual,
   `construeix_pool.py`). Sin repetidas.
3. **Prefiltro de GD seguro**. spaCy solo **quita** marcadores en el GD
   (formas verbales que no son verbo, homógrafos con otra categoría),
   nunca los añade. Por tanto, una frase que sin spaCy no llega a 2
   posibles marcadores catalanes, o que tiene un marcador valenciano que
   no depende de spaCy, nunca saldrá como catalana pura, y se descarta
   antes. Primero un corte por palabras sueltas (cota superior, 2,6 M
   palabras/s) y después con el tokenizador del motor, el mismo de
   `calcula_gd` (0,3 M palabras/s).

Salida: `candidates.jsonl` y `estadistiques_extreu.json`.

**Paso 2, `gd`** (spaCy, en paralelo y reanudable): `calcula_gd(text,
dialecte="cat")` de cada candidata; se quedan las de GD 0 con al menos 2
marcadores. `--fraccio 0.2` hace una muestra uniforme y determinista (por
hash del id; la misma frase siempre entra o no) y `--maxim N` para al
llegar a N frases. Si se corta, al volver a lanzarlo sigue donde lo
dejó (`progres_gd.json`; `--reinicia` para empezar de cero).

Salida: `catala_pur.jsonl` y `estadistiques_gd.json`. Cada línea:

```json
{"id": "macocu.ca.2.3.s4", "doc": "macocu.ca.2", "domini": "tempsdeflors.girona.cat",
 "url": "https://...", "lm_score": 0.892,
 "text": "Aquesta xifra alta de visitants s'ha traduït també amb una ocupació gairebé plena...",
 "gd": 0.0, "marcadors_orientals": ["aquesta", "gairebé"], "total_paraules": 37}
```

## Uso

Desde la raíz del repositorio, con `avlizador` instalado (`pip install -e .`):

```bash
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py extreu
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py extreu --limit-mb 200   # prueba
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py gd --processos 6
python pipeline/08_traduccio_corpus/macocu/filtra_macocu.py gd --processos 6 --fraccio 0.2
```

Si no está el XML descomprimido, el script lo lee directamente del
`.zip` (no hacen falta los 15 GB).

### En Abaco

`filtra_macocu.sh` (solo CPU, 16 núcleos, 32 GB, 24 h) hace los dos
pasos; el GD usa un proceso por núcleo menos uno. Si se acaba el tiempo,
relanzarlo continúa donde lo dejó. Instrucciones (descargar el `.zip` con
`wget` en Abaco y lanzar con `sbatch`) en la cabecera del script.

```bash
sbatch filtra_macocu.sh                  # todas las candidatas
FRACCIO=0.2 sbatch filtra_macocu.sh      # muestra del 20 %
```

## Mediciones (06/11/2026, portátil, 8 núcleos)

- **Prefiltro seguro, comprobado**: de 4.000 frases válidas, pasan 521
  (13 %); el GD exacto da 461 catalanas puras (88 % de las que pasan) y
  **ninguna** catalana pura queda fuera por el prefiltro.
- **Paso 1** con los primeros 200 MB: 485.514 párrafos → 226.023 buenos
  → 521.168 frases válidas → **63.031 candidatas**, en 49 s. Para el XML
  entero: ~1 hora y unos 5 M de candidatas.
- **Paso 2** con 6 procesos: ~90-100 candidatas/s (4.000 en 46 s, con el
  arranque de spaCy); el 86 % son catalanas puras. Todas las candidatas:
  ~13-15 h; con `--fraccio 0.2`, ~3 h.

## Traducción al valenciano (`tradueix_macocu.py`, 09/11/2026)

Traduce `catala_pur.jsonl` entero con AVLizador (sin los 4 dominios
excluidos, ver "Decisiones"). Dos pasos, los dos en paralelo y
reanudables. Si el job se corta a mitad de lote, al relanzarlo se recortan
las líneas sin guardar, así que no hay duplicados.

1. **`motor`** (motor + spaCy, sin FLOR): las frases **sin** palabras
   ambiguas ya tienen la traducción final, porque el sistema completo
   daría exactamente lo mismo. Van a `paralel_motor.jsonl`. Las que tienen
   palabras ambiguas (~6,5 %) van a `pendents_flor.jsonl`.
2. **`flor`**: el sistema completo (`translate_cat_val`: motor + spaCy +
   FLOR-760M, catalana por defecto y margen 2) para las pendientes →
   `paralel_flor.jsonl`.

Cada línea:

```json
{"id": "macocu.ca.44.6.s3", "doc": "...", "domini": "...", "url": "...",
 "catala": "Un cop finalitzat el procés, aquest és retornat a la seva ubicació habitual.",
 "valencia": "Una vegada finalitzat el procés, este és retornat a la seua ubicació habitual.",
 "canvis": [["Un cop", "Una vegada"], ["aquest", "este"], ["seva", "seua"]],
 "gd_val": 1.0, "gdv_val": 1.0, "marcadors_orientals_val": [],
 "punts": [{"paraula": "cop", "tipus": "colisio", "candidats": ["colp", "vegada"], "motor": null,
            "tria": "vegada", "decidit": "model", "pos": "NOUN",
            "puntuacions": {"colp": {"lp": -58.916, "prior": -17.149, "n": 16}, "vegada": {...}}}],
 "revisar": true}
```

`revisar` = alguna palabra ambigua no la decidió spaCy (la decidió FLOR,
la catalana por defecto o el motor). `gd_val` con `dialecte="val"`;
`gdv_val` = 1 − orientales / palabras.

```bash
python pipeline/08_traduccio_corpus/macocu/tradueix_macocu.py motor --processos 6 --maxim 10000
python pipeline/08_traduccio_corpus/macocu/tradueix_macocu.py flor --processos 2 --fils 3 --maxim 200
```

En Abaco, `tradueix_macocu.sh` (solo CPU, 16 núcleos, 32 GB, 24 h):

```bash
MAXIM=20000 sbatch tradueix_macocu.sh           # prueba del paso 1
sbatch tradueix_macocu.sh                       # paso 1 entero
PAS=flor MAXIM=2000 sbatch tradueix_macocu.sh   # prueba del paso 2
PAS=flor sbatch tradueix_macocu.sh              # paso 2 entero (4 procesos x 4 hilos)
```

Prueba en el portátil (09/11/2026):

- `motor`, 3 procesos: 6.000 líneas en ~110 s (~55 frases/s con el GD
  de la salida). De ellas, 391 (6,5 %) van a FLOR. Al reanudar continúa
  donde lo dejó, sin duplicados.
- `flor`, 2 procesos × 3 hilos: 200 frases en 1.014 s, **~0,2 frases/s
  (~5 s por frase y proceso)**. Es lento porque FLOR puntúa cada
  candidato y sus variantes de concordancia, y además el prior. 147 de
  200 (73 %) quedan con `revisar`. Elecciones: cop→vegada 56, cop→colp
  11, cops→vegades 10, deu (se queda) 9, manca (catalana por defecto) 5.
- Para el corpus entero, ~287.000 frases van a FLOR. Con este ritmo, en
  CPU serían **días**: hay que medirlo en Abaco (`PAS=flor MAXIM=2000`) y
  decidir si FLOR va en GPU o en varios jobs de CPU en paralelo.

## Calidad de los datos (ejecución completa en Abaco, 09/11/2026)

Sección viva: se completa a medida que se revisan los datos.

### Cifras

| Paso | Frases | Tiempo |
|---|---|---|
| Párrafos | 43.945.726 | |
| Párrafos buenos (`good`, ca, no título, `lm_score` ≥ 0,7) | 22.741.901 (51,7 %) | |
| Frases | 63.726.758 | |
| Frases válidas (8-40 palabras, completas) | 43.798.067 | |
| Pasan el corte por palabras sueltas | 5.998.405 | |
| `extreu` → candidatas (sin las 66.925 repetidas) | 5.224.279 | 4.398 s (73 min) |
| `gd` → catalán puro (GD 0, ≥2 marcadores) | **4.489.982 (85,9 %)** | 3.267 s (54 min), 15 procesos |

- El 85,9 % de candidatas puras coincide con la medida local (86 %): el
  prefiltro se comporta igual en todo el corpus que en los primeros 200 MB.
- El GD fue mucho más rápido de lo previsto (~1.600 candidatas/s con 15
  procesos, frente a las ~13-15 h estimadas con 6 en el portátil): no
  hace falta muestrear con `--fraccio` para filtrar.
- 4,49 M frases de 8-40 palabras son muchas más de las que se pueden
  traducir con FLOR en CPU (decenas de frases/s): para el corpus paralelo
  habrá que muestrear.

### Qué hay en `catala_pur.jsonl`

- **GD 0,0 en las 4.489.982 frases** (es la condición del filtro).
  Marcadores por frase: 2 en el 77,6 %, 3 en el 18,0 %, 4 o más en el
  4,4 %.
- **Longitud** (palabras de `total_paraules`): centrada en 15-39; pico
  en 20-29 (1,8 M).
- **Fluidez** (`lm_score`): el 81 % entre 0,85 y 0,95.
- **Procedencia**: 1.958.137 documentos y 40.554 dominios. TLD `.cat`
  53 %, `.com` 28 %, `.org` 7 %, `.es` 4 %, `.ad` 1,3 %. Los 10 dominios
  que más aportan dan el 9,4 % de las frases, los 100 primeros el 33 % y
  los 1.000 primeros el 66 %. El primero es catalunyadiari.com, con
  90.485 frases (2 %). La mayoría de documentos aportan 1 o 2 frases,
  pero hay documentos con cientos (máximo 902).

### Qué marcadores dan la pureza

Hay 6.727 marcadores distintos, aunque dominan unos pocos:
"aquest/a/s/es" (2,6 M apariciones), "seva/seves" (1,1 M), "estat" (362
mil, casi siempre "ha estat"), "tenir", "us", "sigui", "avui", "cop",
"aquí", "servei/s", "mentre", "feina", "nens"... Las frases solo con
demostrativos y posesivos son las más frecuentes ("aquest" + "aquesta"
73.636; "aquest" + "seva" 70.229). Si se traduce una muestra aleatoria,
el corpus paralelo enseñará sobre todo aquest→este y seva→seua, y poco
léxico. Conviene **muestrear estratificando por marcador**.

**Marcadores dudosos**: el 9,4 % de las frases (423.909) no llegaría a 2
marcadores sin contar los errores conocidos del GD ("estat", "us",
"finalitat", "recull", "rebuda", "deu"). Se revisaron 25 de esas frases
al azar. "estat" es casi siempre el participio "ha estat", que es un
marcador real (val. "ha sigut"). "us" es el pronombre (val. "vos"), también
real. "Estat" como nombre aparece en muy pocas: la detección aproximada
con expresiones regulares da 342 de 344.855. **No hace falta quitarlas.**

### Muestra revisada a mano (60 frases al azar)

Todas son catalán bien formado, y la mayoría proceden de prensa local,
ayuntamientos, blogs y la universidad. Hay algo de balear
(clubdelabonataula, capvermell) y errores de los autores ("alliberàs",
"me donat", "recorre"), que vienen del original. El catalán se queda tal
cual; la traducción los arrastrará.

### Fuentes problemáticas (~67 mil frases, 1,5 %)

| Dominio | Frases | Problema |
|---|---|---|
| pdfslide.tips, dokumen.tips | 17.536 | PDF mal extraído: faltan letras y apóstrofos ("colleccionistes dart", "clssica", "nensbascos") |
| ca.eferrit.com | 33.484 | Traducción automática del inglés ("Vostè pot tenir les meves armes...", "noggues") |
| ca.whattalking.com | 15.368 | Traducción automática del inglés (salud, fitness) |

Hay otros subdominios `ca.*` (93 en total, 61.232 frases). La mayoría
son buenos (Wikipedia y sus proyectos, globalvoices, wikiloc). Hay
algunos comerciales pequeños (slotgamemachine, girlsbcn). wikizero.com
(51.314) es una copia de la Wikipedia: el texto es bueno, pero repite el
de la Wikipedia.

Ejemplos de la traducción automática (de 12 frases vistas, unas 4-5 son
correctas):

- eferrit: "Vostè pot tenir les meves armes **quan les pren** de les mans
  fredes i mortes" (falta el subjuntivo: "quan me les prengui"); "No és
  la llum vermella que…, **però** la llum vermella…" (debe ser "sinó");
  "**noggues**" (palabra inglesa sin traducir); "la càmera CSPAN
  **s'està escapant a les bateries**" (sin sentido).
- whattalking: "**Si ho heu fet mai no vaig tenir orgasme**, aquí
  teniu…" (incoherente); "**treure's cap amunt**" (calco de *pull
  yourself up*); "**espigues de carn**" (sin sentido).

### Decisiones

**1. Se quitan los 4 dominios de la tabla** (decisión del usuario,
09/11/2026): pdfslide.tips, dokumen.tips, ca.eferrit.com y
ca.whattalking.com. Quedan **4.423.594 frases** (−66.388, −1,5 %).

Motivo: el valenciano del corpus paralelo saldrá de traducir este
catalán con AVLizador, que solo cambia lo dialectal. Por eso los calcos
y los errores de la traducción automática, igual que las letras perdidas
de los PDF, pasarían tal cual a los dos lados del par, y el modelo
ajustado aprendería a reproducirlos. Además, no es catalán escrito por
personas. Se quitan los dominios enteros, aunque una parte de sus frases
sea correcta, porque no hay forma fiable de separar las buenas de las
malas y el coste es pequeño.

`catala_pur.jsonl` no se toca. La exclusión se aplica al muestrear para
traducir.

**2. Sin tope de frases por documento** (decisión del usuario,
09/11/2026). Se pensó para ganar variedad (hay documentos con cientos de
frases: un blog con 902, la política de privacidad de Microsoft con
238), pero medido no compensa:

| Tope | Quedan | Se pierden |
|---|---|---|
| 3 | 3.330.831 | 24,7 % |
| 5 | 3.796.379 | 14,2 % |
| 10 | 4.158.698 | 6,0 % |
| 20 | 4.321.650 | 2,3 % |

Lo que se pierde son sobre todo documentos normales de 6 a 20 frases
(noticias, artículos). Además, al muestrear al azar el peso de los
documentos largos se diluye solo: en una muestra de 200.000 frases, el
documento de 902 aportaría unas 40. Si algún día se traduce el corpus
entero, se puede reconsiderar un tope alto (20).

**3. Objetivo del corpus paralelo** (decisión del usuario, 09/11/2026):
de momento solo se construye el conjunto de datos. Su primer uso será
entrenar un KenLM o un fastText que haga lo que hace hoy FLOR (decidir
las palabras ambiguas) **sin el sesgo hacia el catalán**, gracias a
entrenarlo con valenciano.

**4. Se traduce todo**: las 4.423.594 frases, sin muestreo, sin tope por
dominio. La estratificación por marcador se deja para otro conjunto de
datos.

**5. Formato de salida**: JSONL con `id`, `catala`, `valencia`, `gd_val`,
`gdv_val`, `domini` y los cambios/puntos ambiguos de AVLizador.

### Medida previa de la traducción (5.023 frases, portátil, 1 núcleo)

- Motor (con spaCy, sin FLOR): **176 frases/s**. Todo el corpus son
  ~7 h en un núcleo y ~30 min con 15 procesos.
- **El 6,0 % de las frases tiene palabras ambiguas** (cop 165, nou 79,
  nous 28, deu 18, cops 17, manca 9...). spaCy decide parte de ellas;
  **solo el 3,8 % llega a FLOR**, casi todas por "cop/cops". Eso son unas
  170.000 frases en todo el corpus.
- El motor solo, sin la capa de spaCy/FLOR, no sirve para este corpus:
  traduce "guanyar nous independentistes" → "anous".

**Riesgo de circularidad**: en las frases con palabras ambiguas que
decide FLOR, el KenLM aprendería las elecciones de FLOR, sesgo incluido.
En "cop/cops" FLOR elige entre "colp" y "vegada" (la catalana no es
candidata). En "manca", "nous" o "deu", con la catalana por defecto y
margen 2, se queda a menudo la catalana. Por eso, en la salida se guarda
**quién decidió** cada palabra ambigua (`decidit`: spaCy, model,
catala, motor) y el campo `revisar`. **Decisión del usuario
(09/11/2026): esas frases NO se quitan**; van etiquetadas y se revisarán
a mano o se decidirá después qué hacer con ellas. Para que el KenLM
aprenda bien "vegada"/"colp" probablemente hará falta también valenciano
real (AVL, BOE val, frases de GD 1 de MaCoCu).

## Límites

- El separador de frases no trata abreviaturas ("Sr.", "núm."): la frase
  cortada acaba sin punto o empieza en minúscula y la descarta el filtro.
- Una web puede aportar muchas frases (`estadistiques_extreu.json` lista
  los 30 dominios con más candidatas). Si hace falta, se limita por
  documento o dominio al muestrear para traducir.
- El GD tiene sus errores conocidos ("finalitat", colisiones verbales
  como "permet"): ver `documentacio/resultats_gd_gdv_gdc.md`.
