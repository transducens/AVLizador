*[Read it in Catalan](README.md)*

# BOE net — corpus depurado de ruido de estilo (02-05/10/2026)

Versiones DERIVADAS del corpus BOE (`../boe/`), pensadas para separar
diferencias **dialectales reales** de diferencias de **estilo del
traductor** (mismo texto oficial, traducido dos veces por equipos
distintos). Los ficheros originales de `../boe/` **no se tocan nunca** --
todo lo que hay aquí se obtiene ejecutando los scripts de `boe/`
indicados abajo, y se puede regenerar siempre que haga falta.

## Ficheros

| Fichero | Qué es |
|---|---|
| `corpus_entrenamiento_net.jsonl` | `../boe/corpus_entrenamiento.jsonl` (260.345 de 267.962 filas) menos las dos categorías de ruido de abajo. |
| `descartados_estilo.jsonl` | Las 7.617 filas quitadas, con el motivo (`motivo_descarte`) -- nunca se pierden en silencio. |
| `visor_diferencias.html` + `visor_diferencias_chunks/` | Visor de las 178.416 frases con diferencia real, ordenadas de MÁS a MENOS diferencia -- ver abajo. |

## `depurar_ruido_estilistico.py` -- las dos categorías de ruido

```bash
cd ../../boe
python depurar_ruido_estilistico.py
```

Dos categorías detectadas con seguridad del 100% (no hacen falta reglas
difusas, solo comparar tokens normalizados):

- **`solo_mayusculas`** (7.260 filas, 2,7%): las dos frases tienen
  exactamente las mismas palabras en el mismo orden, solo difieren en
  mayúsculas/minúsculas -- el valenciano capitaliza cada palabra del
  título de una ley ("Llei Orgànica", "Mesures Urgents"), el catalán no.
  Convención tipográfica de uno de los dos equipos, no tiene nada que
  ver con dialecto.
- **`reordenament_pur`** (357 filas, 0,1%): mismo multiconjunto de
  palabras, orden distinto -- típicamente anteposición/posposición del
  adjetivo ("eixos següents" / "següents eixos"). Preferencia de estilo
  sistemática, no gramática dialectal.

**Reanálisis hecho después de depurar** (sobre los 520 documentos
completos, no solo los 169 con párrafos alineados que mira
`analizar_corpus.py`): 83.602 pares de sustitución distintos, con el top
por frecuencia dominado por pares dialectales ya confirmados
(`aquesta/esta` 18.784 veces, `seva/seua` 13.727, `sigui/siga` 7.413...).
Dos hallazgos nuevos a seguir investigando:

- **`pot`→`podrà`, `és`→`serà`, `poden`→`podran`, `ha`→`haurà`** (27.000+
  instancias juntas): NO es dialecto, es una diferencia de TIEMPO verbal
  (presente vs. futuro) -- probablemente convención de redacción legal
  de un equipo concreto, no gramática valenciana/catalana. Candidato a
  una tercera categoría de ruido a filtrar.
- **`s'escau`→`és el cas`** (5.574 veces): parece elección léxica/
  idiomática real, candidata a añadir al glosario si se confirma.
- Sospechosos por palabras demasiado cortas/genéricas (`a`→`en`,
  `preveu`→`en`, `s'ha`→`es`): probablemente mezclan casos reales con
  ruido puro del algoritmo de diff, revisar antes de fiarse.

## `generar_visor_diferencias.py` -- visor frase a frase, dos órdenes

```bash
cd ../../boe
python generar_visor_diferencias.py
# despues, para abrirlo:
cd ../dades/boe_net
python -m http.server 8000
# -> http://localhost:8000/visor_diferencias.html
```

A diferencia de `analizar_corpus.py` (solo 169 documentos) y de
`depurar_ruido_estilistico.py` (agrupa por PAREJA de palabras, no por
frase), este visor trabaja a nivel de **frase completa**, sobre los
**520 documentos** de `corpus_entrenamiento_net.jsonl`, con dos pestañas
independientes (filtro y carga por separado en cada una):

- **"Mayor diferencia primero"** (similitud ascendente): para encontrar
  errores de alineamiento reales, empezando por las más sospechosas.
- **"Mayor similitud primero"** (similitud descendente, añadida
  05/10/2026): las frases casi idénticas salvo un detalle -- suele ser
  el caso más limpio de sustitución dialectal puntual (misma idea que
  `ratio_medio_frase` en `depurar_ruido_estilistico.py`, ahora a nivel
  de frase entera en vez de par de palabras).

El diff resaltado de cada frase se calcula UNA sola vez y se reutiliza
para las dos pestañas (solo cambia el orden en que se escriben los
chunks).

**Arquitectura (misma lección que el visor de `analizar_corpus.py`,
ver `../../boe/README.es.md`)**: con ~178.000 frases, embeberlas todas
en el HTML volvería a disparar el peso del fichero -- aquí se parten en
trozos ("chunks") de 1.000 frases, cargados con `fetch()` a medida que
se hace scroll o se pulsa "Cargar más" (un directorio de chunks por
pestaña). Por eso **hace falta un servidor local** para usarlo (no vale
abrirlo haciendo doble clic) -- la propia página lo explica si `fetch()`
falla.

## Pendiente (acordado, no implementado todavía)

- Filtrar la 3ª categoría de ruido (presente/futuro: `pot/podrà`...).
- Confirmar `s'escau/és el cas` y añadirlo al glosario si procede.
- Revisar los pares de palabras demasiado cortas/genéricas.
- Investigar por qué `es_tabla()` no coge las tablas de tarifas de
  `BOE-A-2013-13616`/`BOE-A-2012-8745` (ver `../../boe/README.es.md`).
- Llevar las señales de confianza dialectal a un filtro real dentro de
  `exportar_entrenamiento.py`, no solo a tablas de inspección visual.
