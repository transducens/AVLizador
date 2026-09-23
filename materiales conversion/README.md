# Materiales de conversión valencià ↔ català

Todo lo relacionado con las diferencias dialectales entre valenciano
(occidental, norma AVL/GVA) y catalán (oriental, norma IEC): de dónde salen,
cómo se documentan, y los datos estructurados que usa el pipeline de
traducción.

## Estructura

```
materiales conversion/
├── reglas_prompt/      documentación para leer y revisar (empieza aquí)
├── lexico/             datos estructurados: pares valenciano-catalán en JSON
└── fuentes/             material bruto de origen (no pensado para leer directo)
```

### `reglas_prompt/` — empieza por aquí

El material de estudio y revisión. Ver su propio
[`reglas_prompt/README.md`](reglas_prompt/README.md) para el detalle, pero
en resumen:

- **`guia_dialectal_valencia_catala.md`** — documento tipo tema de libro con
  todas las reglas dialectales explicadas (morfología + léxico). El
  documento de referencia principal.
- **`lexic_per_frequencia.md`** — para revisar el léxico rápido: solo las
  palabras que de verdad se usan en el corpus, ordenadas por impacto.
- **`system_prompt.md`** / **`glossari_dinamic.md`** — cómo está implementado
  esto en el código (el prompt literal, el mecanismo del glosario dinámico).

### `lexico/` — datos estructurados (JSON)

| Fichero | Qué es |
|---|---|
| `lexico_fiable.json` | **⭐ El que usa de verdad el pipeline ahora mismo.** 194 pares (31 de Apertium + 34 de Paula Guerrero + 129 de `fuentes/paralelos.txt`) revisados y en los que confías. `evalua_models.py` ya no lee `palabras_traducidas.json` — lee este fichero directamente. Los numerales compuestos con guionet (huitanta-cinc, noranta-huit...) están colapsados en sus formas base (`huit`, `huitanta`) porque el glosario dinámico tokeniza por guionet — ver `guia_dialectal_valencia_catala.md` sección 6. |
| `anyade_paraula.py` | Script para añadir palabras nuevas a `lexico_fiable.json` sin editar el JSON a mano: `python anyade_paraula.py --val xxx --cat yyy`. |
| `apertium_368_val_cat.json` | Las 368 formas que Apertium marca como valencianas, separadas en confirmadas (68) y pendientes (3, sin pareja encontrada, sin inventar nada). De aquí salen las 30 entradas de origen "apertium" de `lexico_fiable.json` (68 confirmadas por Apertium, reducidas a formas base tras quitar numerales compuestos redundantes). |
| `contrastius_paula_guerrero.json` | 35 pares valenciano-catalán categorizados (determinantes, verbos incoativos, léxico...), de una fuente externa curada aparte. 34 de los 35 ya están volcados en `lexico_fiable.json`. |
| `pares_valenciano_catalan.json` | El listado más amplio: 1.601 pares valenciano→catalán (Apertium + la lista curada completa). Ya no lo usa el pipeline ni la guía — se queda como referencia si algún día hace falta más cobertura. |
| `palabras_traducidas.json` | Copia de trabajo del léxico **antiguo** (el original vive en `evalua_modelos/palabras_traducidas.json`, ya no usado por el pipeline). Sigue siendo útil como cantera: si al revisarlo encuentras una palabra de la que estás completamente seguro, añádela a `lexico_fiable.json` con `anyade_paraula.py`. |

### `fuentes/` — material bruto de origen

No pensado para leer directamente (salvo `reglas_cat_val.md`, que es más
legible); son los ficheros de los que salen los datos de `lexico/` y de la
guía.

| Fichero | Qué es |
|---|---|
| `reglas_cat_val.md` | Informe generado automáticamente comparando `apertium-cat.cat.dix` (`v="cat"` vs `v="val_gva"`) con la lista curada — de aquí sale el 90% del contenido de `pares_valenciano_catalan.json` y de la guía dialectal. |
| `apertium-cat.cat.dix` | El diccionario morfológico de Apertium en bruto (formato XML/lttoolbox, ~66.500 entradas). |
| `palabras_traducidas.txt` | La lista curada original, en texto plano, antes de convertirse a JSON. |
| `palabras_val.json` | Formas marcadas específicamente como valencianas (`v="val_gva"`) en Apertium — sin pareja catalana directa, es materia prima, no pares ya hechos. |

## Cómo añadir una palabra nueva al léxico fiable

```bash
cd lexico
python anyade_paraula.py --val xiquet --val xiquets --cat nen --cat nens
```

Eso la añade directamente a `lexico_fiable.json`, que es el que usa
`evalua_models.py` (y por tanto también `genera_corpus_sintetico.py`, que lo
reutiliza). No hace falta tocar ni reiniciar nada más — la próxima vez que
se ejecute el pipeline, ya la usa.

## Flujo de trabajo para revisar el léxico antiguo

1. Revisa `reglas_prompt/lexic_per_frequencia.md` (las palabras del léxico
   antiguo que de verdad se usan en el corpus, priorizadas por impacto) o
   `lexico/palabras_traducidas.json` directamente.
2. De las que estés completamente seguro, añádelas a `lexico_fiable.json`
   con `anyade_paraula.py` (o dime cuáles y las añado yo).
3. Si quieres que una corrección también se aplique al corpus ya generado
   (no solo a futuras generaciones), se amplía
   `corpus_sinteticos/repara_corpus.py` con la reversión correspondiente.

## Cómo corregir/ampliar una regla morfológica

Revisa `reglas_prompt/guia_dialectal_valencia_catala.md` (secciones 1-8).
Si hay que cambiar el prompt que usa el modelo, dímelo y lo aplico en
`evalua_modelos/evalua_models.py` (`SYSTEM_PROMPT_BASE`).
