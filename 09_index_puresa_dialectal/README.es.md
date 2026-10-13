*[Léelo en valenciano](README.md)*

# `09_index_puresa_dialectal/` — Índice de Pureza Dialectal (IPD)

Novena etapa del proyecto AVLizador (ver `README.es.md` de la raíz):
métrica para saber, de cualquier texto, qué porcentaje de sus palabras
dialectalmente marcadas son formas **occidentales** (valencianas) en vez
de **orientales** (catalanas).

```
IPD = total_palabras_occidentales / (total_occidentales + total_orientales)
```

Un IPD de 1,0 significa que ninguna palabra catalana marcada aparece en
el texto; 0,0 significa lo contrario; y `None` (sin resultado) significa
que el texto no contiene ninguna palabra dialectalmente marcada de las
que conoce el índice — no se puede calcular un porcentaje sobre cero.

## Por qué un módulo nuevo, si ya existía una métrica parecida

`01_extraccio_i_neteja/estudi_dialectal.py` ya calculaba algo muy
parecido (`ratio_occ`, en su tarea 1), pero contra dos listas curadas a
mano de unas setenta palabras cada una
(`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`, dentro del mismo fichero). Este
módulo calcula el mismo índice, pero contra el índice de pares
dialectales que `traductor/` ya mantiene para traducir de verdad:

| | Listas antiguas (`estudi_dialectal.py`) | Índice del IPD (`traductor/data/*.json`) |
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
python ipd.py --text "Este xiquet vol vindre hui."
python ipd.py --fitxer un_document.txt
python ipd.py --corpus ../dades/avl/final/unified.jsonl --camp text --sortida resultat.json

# Informe HTML para ver y depurar frase a frase (palabras resaltadas en
# verde=occidental/naranja=oriental), con las dos columnas del benchmark
# del proyecto una al lado de la otra:
python ipd.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
    --camp occidental --camp-alt oriental --html informe.html

# Corpus grandes (p.ej. el del BOE, ~268.000 líneas): --limit para
# probar con una muestra antes de lanzarlo entero (cada frase se
# tokeniza con spaCy, así que el fichero completo puede tardar ~30 min):
python ipd.py --corpus ../dades/boe/corpus_entrenamiento.jsonl \
    --camp texto_catalan --limit 5000
```

Acepta tanto un fichero JSONL (un documento por línea) como un JSON
normal con un array de objetos (como `benchmark_corpus.json`) — se
detecta solo.

Como módulo, desde otro script del proyecto:

```python
from ipd import calcula_ipd

calcula_ipd("Este xiquet vol vindre hui.")["ipd"]  # -> 1.0
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

Contra el benchmark de 151 frases de `03_seleccio_de_model/benchmark_corpus.json`
(después de los dos fixes): el lado valenciano da **IPD 0,9339** (240
marcadores occidentales, 17 orientales) y el lado catalán **IPD 0,0153**
(4 occidentales, 258 orientales).

**Confirmado a mayor escala con el corpus del BOE** (`dades/boe/`,
`dades/boe_net/`): el lado catalán se mantiene igual de puro en muestras
mucho más grandes y de un dominio distinto (5.000 frases de
`corpus_entrenamiento.jsonl`: IPD 0,0181; 200 frases de
`muestra_test_dialectal.json`: IPD 0,0127) — el mismo patrón se repite en
tres corpus independientes. La muestra del BOE también aportó evidencia
mucho más fuerte sobre "qué" (29 apariciones reales sin tocar en
valenciano, frente a solo 4 en el benchmark pequeño) y dos candidatos
nuevos al mismo tipo de problema que "nou" (entradas de léxico sin filtro
de categoría gramatical): "afecte" (confundido con "cariño" cuando en
realidad significa "sujeto a" en texto legal) y "estat" (spaCy a veces lo
etiqueta como verbo cuando es el sustantivo "el Estado").

## Relación con el resto del proyecto

Pendiente documentado en `CLAUDE.md` (sección "Pendiente") y detallado en
`documentacio/hoja_de_ruta_ipd_y_proxima_fase.md`: este era el primer
paso a dar antes de seguir ampliando el motor de reglas con más casos del
benchmark, y antes de intentar una capa de modelo (LLM) nueva para
cat→val o de probar con un corpus distinto (el BOE, ya empezado aquí).
