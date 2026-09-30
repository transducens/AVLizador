*[Llegeix en català](README.md)*

# Etapa 2 — Reglas dialectales y léxico

Todo lo relacionado con las diferencias dialectales entre valenciano
(occidental, norma AVL/GVA) y catalán (oriental, norma IEC): de dónde salen,
cómo se documentan, y los datos estructurados que usa el pipeline de
traducción. Con el corpus fuente ya limpio (etapa 1), esta etapa define
**qué cambia** entre los dos dialectos — las reglas que luego usa el modelo
para traducir (etapas 3-4).

**[`reglas_dialectales_con_evidencia.md`](reglas_dialectales_con_evidencia.md)**
— empieza por aquí si quieres las reglas explicadas como un tema de estudio
(demostrativos, posesivos, morfología verbal, numerales, gentilicios,
sintaxis, léxico diferencial), con un apéndice de evidencia numérica de
cada una.

## Metodología: cómo se derivaron las reglas

Se derivaron comparando, dentro del diccionario morfológico de Apertium
(`apertium-cat.cat.dix`), las formas marcadas `v="val_gva"` (occidental) con
sus equivalentes `v="cat"`/`v="val_uni"` (oriental). Cada patrón se
documenta con su **cobertura** (cuántos casos reales lo siguen) — un patrón
con cobertura baja no se convierte en regla general, se deja como lista
cerrada de palabras confirmadas una a una. Dos reglas salen de fuentes
distintas al diccionario, documentadas explícitamente donde corresponde: el
pretèrit perifràstic (de analizar frases completas del benchmark) y la
concordancia de género de "dos/dues" (de normativa AVL/IEC citada
directamente).

Ver `../documentacion/metodologia_y_resultados.md` secciones 2 y 4 para el
detalle completo del proceso.

## Estructura

```
02_reglas_dialectales/
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
| `lexico_fiable.json` | **Usado por `evalua_models.py --model regles` y `genera_corpus_sintetico.py` (sistema antiguo de regex, no el motor `traductor/`).** 347 pares (194 originales: 31 de Apertium + 34 de Paula Guerrero + 129 de `fuentes/paralelos.txt`; +150 de Mauricio y +3 de la evidencia AVL añadidos 29/09/2026). **Retirado de `traductor/rules/lexic.py` el 30/09/2026** (junto con `apertium_368_val_cat.json` y `contrastius_paula_guerrero.json`, ver abajo): ese paquete ahora es puro lookup de diccionario de Mauricio, sin ninguna fuente externa -- ver `traductor/README.es.md`, sección "DECISIÓN DE ARQUITECTURA". Este fichero se queda como copia de seguridad y como la fuente que siguen usando los otros dos scripts. |
| `apertium_368_val_cat.json` | Las 368 formas que Apertium marca como valencianas, separadas en confirmadas (65 con pareja, 6 sin) y pendientes. Se usó en `traductor/rules/lexic.py` desde la mañana del 30/09/2026 hasta que esa misma tarde se retiró al reducir el traductor a puro Mauricio -- ya no lo usa ningún script activo. |
| `contrastius_paula_guerrero.json` | 35 pares valenciano-catalán categorizados (determinantes, verbos incoativos, léxico...), de una fuente externa curada aparte, con un campo `category` real. Mismo caso que el anterior: se usó un tiempo en `lexic.py`/`demostratius.py`/`possessius.py`, retirado el 30/09/2026 al pasar el traductor a puro Mauricio. |
| `posesivos_cat_val.json` (dentro de `font_mauricio/`) | 12 filas de Mauricio (30/09/2026), un producto cartesiano sin filtrar de los posesivos débiles. `traductor/rules/possessius.py` se queda solo con los 6 pares donde el número casa. |
| `palabras_traducidas.json` | Copia de trabajo del léxico **antiguo** (el original vive en `03_seleccion_de_modelo/palabras_traducidas.json`, ya no usado por el pipeline). |

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

**Nota (30/09/2026)**: esto solo afecta a `evalua_models.py --model
regles` y `genera_corpus_sintetico.py` (sistema antiguo de regex). El
motor `traductor/` (opción `--model traductor`) ya no lee
`lexico_fiable.json` -- para añadirle palabras, edita el fichero fuente
de la categoría correspondiente en `traductor/data/` (ver
`traductor/README.es.md`, sección "Cómo añadir una regla nueva").

Edita `lexico/lexico_fiable.json` directamente, añadiendo una entrada
nueva al array `entradas` con el mismo esquema que las demás (`valenciano`,
`catalan`, `castellano`, `categoria`, `origen`). No hace falta tocar ni
reiniciar nada más — la próxima vez que se ejecute el pipeline, ya la usa.

## Flujo de trabajo para revisar el léxico antiguo

1. Revisa `reglas_prompt/lexic_per_frequencia.md` (las palabras del léxico
   antiguo que de verdad se usan en el corpus, priorizadas por impacto) o
   `lexico/palabras_traducidas.json` directamente.
2. De las que estés completamente seguro, añádelas a `lexico_fiable.json`
   editándolo directamente (o dime cuáles y las añado yo).
3. Si quieres que una corrección también se aplique al corpus ya generado
   (no solo a futuras generaciones), se amplía
   `04_corpus_sintetico/repara_corpus.py` con la reversión correspondiente.

## Cómo corregir/ampliar una regla morfológica

Revisa `reglas_prompt/guia_dialectal_valencia_catala.md` (secciones 1-8).
Si hay que cambiar el prompt que usa el modelo, dímelo y lo aplico en
`03_seleccion_de_modelo/evalua_models.py` (`SYSTEM_PROMPT_BASE`).

## Métrica de pureza dialectal (propuesta, aún no implementada)

`metrica_puresa_dialectal.md` (en catalán) especifica el Índex de Puresa
Dialectal (IPD) — un score bidireccional para detectar contaminación
occidental↔oriental en cualquier texto, reutilizando las tablas de
`traductor/rules/` como diccionario de marcadores. Pensado para aplicarse
sobre el corpus AVL, el BOE y el corpus sintético para medir la
calidad/pureza de cada fuente.
