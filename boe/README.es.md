*[Llegeix en català](README.md)*

# Scraper del BOE en català i valencià

Descarga de forma ética y respetuosa el corpus lingüístico de documentos del
BOE (Boletín Oficial del Estado) que tienen **traducción oficial** al catalán
o al valenciano, publicados como "suplement en llengua catalana/valenciana"
en boe.es.

## Resumen del proceso (3 fases, ya completadas)

El scraping terminó el 2026-09-10 (log: "Finalizado") y el corpus ya no
crece más: 521 PDF en cada idioma, 2009-2015. A partir de ahí, tres fases:

**1. Scraping** (`scraper_boe.py`) — descarga solo los PDF con traducción
oficial real (clase `puntoPDFsup`), respetando `robots.txt` y con ritmo de
cortesía (8s-2min de espera entre peticiones). Detalles y cifras de tiempo
en ["Hallazgos importantes"](#hallazgos-importantes-léelo-antes-de-ejecutar)
y ["Cortesía con el servidor"](#cortesía-con-el-servidor-por-qué-tardará-varios-días)
más abajo. Salida: `../dades/boe/{catalan,valenciano}/<año>/BOE-*.pdf`.

**2. Extracción** (`construir_corpus.py`) — texto de cada PDF a nivel de
**párrafo real** (bloque de PyMuPDF, con info de fuente para fusionar
correctamente párrafos cortados por saltos de página sin confundir títulos
en cursiva con cuerpo de texto — ver
["Construcción del corpus"](#construcción-del-corpus-para-estudio) más
abajo para el porqué exacto). Salida: `../dades/boe/corpus.json`, 45,5M/45,4M
caracteres, 6,83M/6,80M palabras (català/valencià).

**3. Alineación** (`alinear_corpus_bleualign.py`, con `texto_comun.py`) —
por similitud de texto con [Bleualign](https://github.com/rsennrich/Bleualign)
en vez de por coincidencia exacta de conteo (eso descartaba documentos
enteros por una sola discrepancia). Antes se excluyen los párrafos
tabulares (presupuestos/aranceles/formularios, `texto_comun.es_tabla`) para
no ensuciar la alineación. Salida: `../dades/boe/corpus_bleualign.jsonl`,
**302.977 pares de frase** (94,0% de cobertura sobre las frases en català
tras excluir tablas, similitud media 0,71).
Detalle completo en
["corpus_bleualign.jsonl"](#corpus_bleualignjsonl-alineación-por-similitud-no-por-posición)
más abajo.

Sobre esto, dos herramientas más: `analizar_corpus.py` genera un informe
HTML de análisis/QA del corpus (vocabulario dialectal, morfología, diff
textual, y la propia alineación de Bleualign — ver más abajo, sección
"Analítica del corpus"); y
`exportar_entrenamiento.py` filtra `corpus_bleualign.jsonl` a un
subconjunto limpio para entrenar (`corpus_entrenamiento.jsonl`, 268.735
pares, 88,7%) — ver su docstring para la regla de dos niveles usada (un
único umbral de similitud no basta: hay pares dialectales correctos de
similitud muy baja que no hay que perder).

## Hallazgos importantes (léelo antes de ejecutar)

Antes de escribir el scraper se inspeccionó `robots.txt` y la estructura real
de las páginas de boe.es. Dos cosas cambian lo que es posible/razonable
descargar:

1. **`robots.txt` prohíbe explícitamente** `/diario_boe/txt.php?*lang=ca`,
   `?lang=va`, y `/diario_boe/xml.php?` (el texto plano/XML del documento en
   lengua cooficial). El scraper respeta esto y **nunca** solicita esas
   rutas. Por tanto, el corpus solo puede construirse a partir de los
   **PDF** enlazados en el sumario diario — no hay atajo de texto plano.

2. En el sumario de cada día, cada documento tiene un enlace a PDF con dos
   variantes posibles:
   - `<li class="puntoPDF">` → el PDF **en castellano** (el documento no
     tiene traducción; el sumario lo enlaza igualmente a modo de
     referencia).
   - `<li class="puntoPDFsup">` → el PDF **realmente traducido**, con
     nombre de fichero `BOE-X-YYYY-NNNNN-C.pdf` (català) o `...-V.pdf`
     (valencià).

   El scraper **descarga únicamente el segundo tipo**. Esto es intencional:
   solo una parte de los documentos publicados cada día (sobre todo Leyes,
   Reales Decretos Legislativos y Reales Decretos-ley) reciben traducción
   oficial; la mayoría de Órdenes/Resoluciones nunca la tienen. El corpus
   resultante será mucho más pequeño que "todo el BOE de ese año" — es
   normal que muchos días no aporten ningún documento.

3. `robots.txt` también bloquea, uno a uno, varios cientos de PDF
   concretos (por causas legales/de privacidad ajenas a este proyecto). El
   scraper carga `robots.txt` una vez al inicio y comprueba **cada URL**
   (calendario, día y documento) contra esas reglas antes de solicitarla,
   con un matcher propio que sí interpreta los comodines `*`/`$` (se
   comprobó que `urllib.robotparser` de la librería estándar de Python
   **no** los interpreta bien y habría dejado pasar peticiones que
   `robots.txt` pide bloquear).

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

Ejecución completa (catalán 2001–2025, valenciano 2001–2015):

```bash
python scraper_boe.py
```

Solo un idioma y/o rango de años:

```bash
python scraper_boe.py --idiomas catalan --anio-desde 2010 --anio-hasta 2015
```

Prueba rápida (se detiene tras N documentos descargados, sin esperar días):

```bash
python scraper_boe.py --max-documentos 3 --verbose
```

El scraper es **reanudable**: puede interrumpirse (Ctrl+C) y volver a
lanzarse con el mismo comando; retomará justo donde se quedó gracias a
`../dades/boe/progreso.json` (días ya procesados y documentos ya descargados
no se vuelven a pedir). Un día solo se marca como completado si **todos**
sus documentos se descargaron correctamente; si alguno falla o se corta la
ejecución a medias, ese día se reintenta en la siguiente ejecución.

## Salida

```
../dades/boe/
├── progreso.json          # registro de reanudación
├── scraper.log             # log completo con timestamp, URL y status code
├── catala/
│   ├── 2001/
│   │   └── BOE-A-2001-XXXXX-C.pdf
│   └── ...
└── valencia/
    ├── 2001/
    │   └── BOE-A-2001-XXXXX-V.pdf
    └── ...
```

`progreso.json` guarda también metadatos por documento (título en el idioma
correspondiente, fecha, URL origen) — útil para catalogar el corpus después.

## Cortesía con el servidor (por qué tardará varios días)

Todo el tráfico es secuencial (una sola petición a la vez, sin hilos ni
async), con sesión persistente, User-Agent realista rotado entre 5
navegadores, cabeceras completas (Accept, Accept-Language, Referer),
reintentos con backoff exponencial (30s/60s/120s) ante 429/503/timeout, y
una pausa de 10 minutos si el servidor sigue devolviendo error tras agotar
los reintentos. Los tiempos de espera aplicados son:

| Entre...      | Espera aleatoria |
|---------------|-------------------|
| documentos    | 8–20 s            |
| días          | 15–30 s           |
| meses         | 30–60 s           |
| años          | 60–120 s          |

**Estimación de tiempo total**: el calendario anual del catalán enlaza del
orden de ~290 días con "suplemento" (la mayoría sin ningún documento
traducido, pero cada uno exige igualmente una petición de cortesía). Con
~23 años de catalán y ~15 de valenciano, eso son del orden de **11.000
peticiones a nivel de día**, que a ~22 s de media entre cada una suman por
sí solas **unas 68–70 horas**. Sumando las esperas entre meses/años y las
descargas de los documentos realmente traducidos (probablemente unos
cientos a lo largo de todo el rango), la ejecución completa de ambos
idiomas requiere aproximadamente **3–4 días de ejecución continua** (o
varias sesiones más cortas, gracias a que es reanudable). Esto es
deliberado: prioriza no saturar un servicio público sobre la velocidad.

## Construcción del corpus para estudio

Una vez descargados los PDF, `construir_corpus.py` construye un corpus en
JSON listo para analizar, sin volver a tocar la red. Se puede relanzar en
cualquier momento (p.ej. según el scraper vaya descargando más parejas):
recorre lo que haya en disco y regenera la salida entera cada vez.

```bash
python construir_corpus.py   # PDF -> ../dades/boe/corpus.json
```

### `corpus.json` (nivel documento)

Un array con un objeto por cada pareja català/valencià (mismo ID base
`BOE-X-YYYY-NNNNN`, ya garantizado por el scraper). Extrae el texto de
ambos PDF con PyMuPDF **a nivel de bloque** (`page.get_text("dict")`, con
la info de fuente de cada tramo de texto), que en el BOE corresponde a
párrafos reales — no a nivel de línea renderizada. Esto importa: català y
valencià envuelven cada párrafo en un número de líneas de PDF distinto (la
traducción no ocupa el mismo espacio), así que segmentar por línea en vez
de por párrafo desalineaba las frases entre los dos idiomas más adelante.
Cada `texto` guarda sus párrafos separados por una línea en blanco
(`"\n\n"`); dentro de un párrafo, los saltos de línea del PDF ya se han
unido en una sola frase continua.

Un párrafo cortado a media frase (típicamente por un salto de página) se
fusiona con el siguiente si no termina en puntuación de cierre — pero solo
si además **coincide la fuente** en el punto de unión (misma tipografía,
p.ej. cursiva/redonda) y el siguiente **no** es un encabezado estructural
reconocido ("Article N.", "Disposició final/addicional...", "CAPÍTOL...").
Hicieron falta las dos condiciones porque, mirando casos reales: los
títulos de artículo van en cursiva y el cuerpo en redonda, así que
comparar solo la puntuación fusionaba a veces el título con el párrafo
siguiente en un idioma sí y en el otro no (el catalán y el valencià no
siempre coinciden en si el título lleva punto final — una inconsistencia
real de los PDF oficiales, no un error de extracción); y en un caso
concreto ("...article 149.1.25a" seguido de "Disposició final segona.")
ni siquiera había diferencia de tipografía, solo de puntuación, así que
hizo falta además reconocer el patrón del encabezado en sí. También limpia
las cabeceras/pies de página que el BOE repite en cada página (encabezado
"BOLETÍN OFICIAL DEL ESTADO", línea de suplemento, fecha, "Secc. X. Pàg.
N", pie con ISSN...).

```json
{
  "id": "BOE-A-2009-3022",
  "fecha": "2009-02-24",
  "anio": 2009,
  "catalan":    {"id": "BOE-A-2009-3022-C", "titulo": "...", "url": "...", "archivo": "...", "num_paginas": 5, "num_caracteres": 16000, "texto": "..."},
  "valenciano": {"id": "BOE-A-2009-3022-V", "titulo": "...", "url": "...", "archivo": "...", "num_paginas": 5, "num_caracteres": 16280, "texto": "..."}
}
```

Esquema de IDs (decisión: sí se diferencia el idioma, pero como sufijo, no
en el ID base): `id` es el identificador BOE compartido por la pareja, sin
idioma; `catalan.id`/`valenciano.id` añaden el sufijo `-C`/`-V` (el mismo
que ya usa el nombre de fichero del PDF). Así se puede agrupar por
documento o filtrar por idioma indistintamente.

`segmentar_parrafo`/`segmentar_parrafos` (partir `texto` en párrafos reales
por `"\n\n"`, y cada párrafo en frases por puntuación) viven en
`texto_comun.py`, compartidas por `analizar_corpus.py` y
`alinear_corpus_bleualign.py`. Ahí mismo vive `es_tabla()` (ver más abajo,
sección de Bleualign). Hubo una versión anterior de este corpus a nivel de
frase con alineación por conteo exacto de posición (`corpus_frases.jsonl`,
generado por un `construir_frases.py` ya retirado) — se abandonó en favor
de `alinear_corpus_bleualign.py`, que alinea por similitud de texto en vez
de por conteo y cubre muchos más casos (ver más abajo).

### `corpus_bleualign.jsonl` (alineación por similitud, no por posición)

Exigir coincidencia exacta de conteo (mismo nº de párrafos, luego mismo nº
de frases dentro de cada uno) descarta documentos enteros por una sola
discrepancia, aunque el 95% del documento sea perfectamente paralelo — fue
el primer enfoque de este proyecto y se abandonó por eso. Investigando esos
casos se vio que la causa no siempre es un fallo de extracción — a veces
el preámbulo de una versión trae párrafos explicativos que la otra
sencillamente no tiene (contenido real distinto, no una frase mal
cortada; p.ej. una sección entera, «TÍTOL I bis», que solo existe en la
versión valenciana de un documento). `alinear_corpus_bleualign.py`
resuelve esto alineando por **similitud de texto** en vez de por conteo,
usando [Bleualign](https://github.com/rsennrich/Bleualign) (Sennrich &
Volk, 2010):

```bash
pip install -r requirements.txt   # instala pymupdf y bleualign
python alinear_corpus_bleualign.py   # corpus.json -> ../dades/boe/corpus_bleualign.jsonl
```

Bleualign está pensado para pares de idiomas *distintos*: necesita una
traducción automática de un lado hacia el idioma del otro para poder
comparar por solapamiento de n-gramas (BLEU). Aquí no hace falta traducir
nada de verdad — se le pasa **el propio texto en català como si fuera ya
su traducción al valencià** (identidad), razonable únicamente porque
comparten la inmensa mayoría del vocabulario. Por dentro, Bleualign
combina dos fases: una alineación por BLEU con programación dinámica
(camino monótono que maximiza similitud, permitiendo saltar frases sin
pareja), y un relleno de huecos que prueba agrupar varias frases seguidas
de un lado contra una del otro, y como último recurso, para huecos
pequeños, aplica el algoritmo Gale-Church clásico de 1993 (basado en
longitud, no en texto).

```json
{"id": "BOE-A-2009-3022-0003", "documento_id": "BOE-A-2009-3022", "fecha": "2009-02-24", "texto_catalan": "Les principals economies desenvolupades...", "texto_valenciano": "Les principals economies desenrotllades...", "similitud": 0.77}
```

`similitud` no la da Bleualign directamente (no expone su puntuación BLEU
interna por par vía su API sencilla) — se recalcula con solapamiento de
palabras normalizadas (Jaccard) sobre el par que Bleualign decide, para
poder filtrar por calidad al usarlo como datos de entrenamiento. Ojo: un
par con `similitud: 0.0` no siempre es un error — frases cortas como
`"1."` o alternancias dialectales sin raíz común (`Vuit.`/`Huit.`,
`Cinquanta-cinquè.`/`Cinquanta-cinc.`) dan Jaccard 0 aunque el
emparejamiento sea correcto; comprobado a mano que la inmensa mayoría de
los pares con similitud 0 son de este tipo, no errores reales.

**Filtro de párrafos tabulares:** antes de segmentar en frases y pasárselas
a Bleualign, se descartan los párrafos que `texto_comun.es_tabla()`
identifica como presupuestos/aranceles/formularios — no son prosa, y
dejarlos entrar solo daba a Bleualign contenido casi todo numérico donde no
tiene con qué emparejar bien (mirando los pares de similitud más baja, la
mayoría de los errores genuinos de verdad — no las alternancias
dialectales sin raíz común, que son correctas aunque den similitud 0 — se
concentraban ahí: filas de tablas de sueldos/coeficientes/códigos
arancelarios emparejadas con la fila equivocada). Se detecta con dos
señales: puntos-guía (`". . . . . . ."`, el BOE los usa para alinear
visualmente una etiqueta con un número) o menos de 55% de letras sobre
caracteres no-espacio. Calibrado sobre el corpus real: marca ~1,1% de los
párrafos (concentrados en documentos de presupuestos/aranceles/
formularios), cero falsos positivos en una muestra de revisión de 20 al
azar.

Resultados sobre el corpus de 521 documentos (tras excluir párrafos
tabulares): 520 con al menos una frase alineada (el único sin ninguna,
`BOE-A-2010-11419`, es un caso aparte: la extracción del PDF valencià da 0
párrafos, probablemente un PDF escaneado sin texto, no un problema de
alineación), **94,0% de todas las frases en català emparejadas** (322.300
frases totales, 302.977 pares; frente al ~32% que pasa la exigencia de
conteo exacto de párrafo), similitud media 0,71-0,72 (mediana 0,79). Ni el
documento peor alineado baja de 0,62 de similitud media.

### `corpus_entrenamiento.jsonl` (subconjunto limpio para entrenar)

```bash
python exportar_entrenamiento.py   # corpus_bleualign.jsonl -> ../dades/boe/corpus_entrenamiento.jsonl
```

Un único umbral de similitud no separa bien "par correcto de similitud
baja" de "par mal emparejado": comprobado con casos reales, los pares
dialectales legítimos sin raíz común (`Vuit.`/`Huit.`, `Dinovena.`/`Dènou.`)
tienen las dos frases de **longitud casi idéntica** (ratio 1,0-1,5) aunque
compartan cero palabras; el caso de error real que conocíamos
(`FERRALLA` emparejado con una lista de códigos arancelarios) tiene un
ratio de longitud de **21x**. Regla de dos niveles en vez de un corte
único:

1. `similitud >= 0.3`: se queda siempre (266.393 pares).
2. Si no, se rescata solo si las dos frases tienen palabras reales (no son
   solo números/marcas de lista) **y** su longitud es parecida
   (ratio ≤ 2) — 2.342 pares rescatados. Se descartan 352 por longitud
   dispar (aquí cae el caso `FERRALLA`) y 33.890 por no tener ninguna
   palabra real en algún lado (pares técnicamente correctos pero sin
   contenido que aprender, tipo `"1."`/`"1."`).

Total: **268.735 pares (88,7%)**. Los umbrales (`UMBRAL_SEGURO`,
`RATIO_LONGITUD_MAXIMO`) son constantes al principio del script — cambiar
de criterio es tocar un número y relanzar.

## Analítica del corpus (`analizar_corpus.py`)

Genera un informe HTML autónomo (sin dependencias externas, se abre en
cualquier navegador sin internet) para estudiar el corpus y, en concreto,
cuánto se sostiene en la práctica la separación dialectal català/valencià:

```bash
python analizar_corpus.py   # corpus.json + 02_regles_dialectals -> ../dades/boe/analitica_corpus.html
```

Requiere `corpus.json` ya generado (`construir_corpus.py`), opcionalmente
`corpus_bleualign.jsonl` (`alinear_corpus_bleualign.py`, si no existe esa
pestaña simplemente no aparece), y la carpeta `../02_regles_dialectals`
con estos ficheros — `cargar_materiales()` los busca primero en la raíz de
esa carpeta y si no están ahí, en `lexic/` y `fonts/` (la carpeta se
reorganizó en subcarpetas para un pipeline distinto que también la usa; ver
su propio `README.md` si quieres el detalle de esa reorganización):

- `apertium-cat.cat.dix` (diccionario Apertium, fuente de `palabras_val.json`; en `fonts/`).
- `palabras_traducidas.json`: glosario curado valencià/català/castellà (en `lexic/`).
- `palabras_val.json`: formas marcadas exclusivamente `v="val_gva"` en el
  diccionario Apertium, sin equivalente `cat` en la misma entrada (en `fonts/`).
- `regles_cat_val.md`: 108 reglas de terminación morfológica (verbos,
  pronombres, adjectius...), demostratius (est-/aquest-) i locucions (en `fonts/`).

El informe tiene pestañas: Resumen (documentos/año, tamaño del corpus,
% de documentos con parrafos alineables), Léxico dialectal, Formas
exclusivas de valencià, Morfología, Demostratius (con evolución por año),
Locucions, Diff textual y Bleualign (esta última solo si existe
`corpus_bleualign.jsonl`); todas las tablas grandes son interactivas
(filtro de texto + orden por columna). Para cada marcador se calcula una
"fidelidad": qué %
de sus apariciones en todo el corpus caen en el lado dialectal donde se
esperarían (100% = separación limpia; valores bajos indican que el texto
etiquetado como valencià usa en realidad la forma catalana, o al revés).
La pestaña "Metodología" del propio informe explica las limitaciones
(tokenización heurística, falsos positivos por sufijos cortos, etc.).

### Diff textual: qué cambia palabra a palabra entre las dos versiones

Alineación en dos niveles, no una única posición global de frase (la
alineación por frase a secas resultó demasiado fragil — ver más abajo):
primero por **párrafo** (`indice.pares_parrafos_alineados`: documentos con
el mismo número de párrafos reales en los dos idiomas, la unidad de
traducción natural del BOE — cada articulo/párrafo es 1 a 1). Dentro de
cada párrafo ya emparejado, si también tiene el mismo número de frases en
los dos idiomas se comparan frase a frase; si no, se compara el párrafo
entero como una sola unidad, para no perder ese párrafo del análisis. En
todos los casos, la comparación es `difflib` palabra a palabra, en vez de
partir de un glosario cerrado.

Con el corpus parcial ya probado esto encontró automáticamente, sin tocar
el glosario, pares como `estableix`/`establix` o `refereix`/`referix`
(terminación verbal -eix/-ix, un patrón sistemático que no estaba entre
las 108 reglas), lexemas nuevos como `perjudici`/`perjuí`, diferencias de
tiempo verbal como `pot`/`podrà` o `és`/`serà`, y hasta un caso donde la
versión "valenciana" de un documento usa la palabra castellana `estado` en
vez de `estat` — justo el tipo de hallazgo que un glosario cerrado no
puede sacar por sí solo.

Cada par de sustitución encontrado se marca como conocido (coincide con el
glosario o con una regla morfológica) o "novedad"; la tabla por documento
permite ver en qué documentos cambia más vocabulario. Importante: que dos
versiones tengan el mismo número total de párrafos no garantiza que el
párrafo `i` de una corresponda al párrafo `i` de la otra en todo el
documento — la columna "similitud media" de esa tabla sirve para detectar
cuándo la correspondencia es en realidad mala pese a cuadrar el total (en
la práctica, la mayoría de documentos alineados por párrafo salen con
90%+ de similitud media; los que bajan de ahí suelen ser leyes de
presupuestos con tablas numéricas muy densas).

**Por qué por párrafo y no por frase a secas:** la primera versión de esto
segmentaba el texto por línea de PDF renderizada antes de buscar el punto
y seguido; como català y valencià envuelven la misma frase en un número de
líneas distinto (la traducción no ocupa el mismo espacio), la mayoría de
"frases" resultantes eran en realidad fragmentos de línea que no se
correspondían entre idiomas, aunque el número total coincidiera por
casualidad. Al extraer el texto por bloque de PyMuPDF (párrafo real, ver
`corpus.json` más arriba) y alinear primero por párrafo, la cobertura
subió de 57 a 168 documentos comparables sobre el mismo corpus de 521
parejas, y los ejemplos que salen ahora son frases completas y coherentes
en vez de fragmentos cortados.

Ojo, esto no fue un arreglo de una sola vez: la primera versión con
bloques de PyMuPDF seguía fusionando mal en casos concretos — el título de
un artículo (en cursiva, sin punto final en una de las dos versiones) se
fusionaba con el párrafo siguiente en un idioma sí y en el otro no,
desplazando la correspondencia párrafo a párrafo del resto del documento
aunque el número total de párrafos siguiera coincidiendo por casualidad
("BOE-A-2009-3022", el documento de ejemplo del 24 de febrero de 2009,
tenía justo este problema). Se corrigió comparando también la tipografía
en el punto de unión y reconociendo los encabezados estructurales del BOE
("Article N.", "Disposició final/addicional...") para que nunca se
fusionen con el párrafo anterior — ver `construir_corpus.py`.

### Visor frase a frase (leer las diferencias, no solo contarlas)

Dentro de la pestaña "Diff textual" hay un visor: eliges un documento en un
desplegable y lees sus frases una a una, con las palabras que cambian
resaltadas en color directamente sobre el texto real —

> Correcció d'errors i **errades** de la Llei 2/2008... (català)
> Correcció d'errors i **errates** de la Llei 2/2008... (valencià)

— en vez de solo ver la pareja `errades`/`errates` suelta en una tabla.
Ámbar = palabra sustituida, verde = palabra que solo está en el valencià,
rojo tachado = palabra que solo está en el català. Tiene casilla para
mostrar solo las frases con diferencias, buscador de texto, y cambia de
documento sin recargar la página (cada documento se pinta en lotes de 300
frases con un botón "Cargar más", asi que documentos con miles de frases
no bloquean el navegador). Es la forma de valorar a ojo la calidad de una
traducción concreta del BOE, más allá de las cifras agregadas.

Con 168 documentos comparables el HTML pesa unas cuantas decenas de MB (el
visor guarda el texto resaltado de cada frase de cada documento
comparable); un navegador normal lo abre sin problema, solo puede tardar
uno o dos segundos en cargar.

(Nota técnica interna: al implementar esto se detectó y corrigió un fallo
real en el HTML generado por versiones anteriores del script — las
funciones JavaScript de las tablas se definían al final de la página pero
se llamaban antes, así que ninguna tabla llegaba a pintarse en un
navegador real. Ya corregido y verificado con un navegador headless.)

Nota de limpieza: `palabras_traducidas.json` trae, en algunas entradas,
restos de la notación "raíz/desinencia" de género (p.ej. `Bonico/a`)
partidos por `/` como si fueran sinónimos independientes — quedan como
ítems sueltos de 1-2 letras en minúscula ("a", "ja"...) que, contados en
el corpus, no significan nada (son preposición/adverbio muy frecuentes).
El script los descarta automáticamente (ver `_limpiar_entradas_vocabulario`
en `analizar_corpus.py`); se verificó a mano que todo ítem corto legítimo
del fichero viene capitalizado, así que el filtro no pierde datos reales.

## Notas

- Antes de cada ejecución se descarga y respeta `robots.txt` en tiempo
  real (no hay una copia local que pueda quedar desactualizada).
- No se vuelve a descargar un fichero que ya exista en disco o que ya
  conste en `progreso.json`.
- Si boe.es devuelve 429/503 de forma persistente, el scraper pausa 10
  minutos antes de un último intento; si ese intento también falla, se
  descarta ese elemento (queda registrado en el log) y se continúa con el
  siguiente, sin abortar toda la ejecución.
