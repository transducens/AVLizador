> **⚠️ FICHERO RECONSTRUIDO el 14/10/2026** tras un borrado accidental
> del original. El fichero nunca estuvo en git (salía como `??` en
> `git status`), así que no hay ningún historial del que recuperarlo, y
> tampoco estaba en la papelera de reciclaje de Windows. A diferencia de
> `hoja_de_ruta_traductor_invers.md`, de este fichero **no se leyó
> ningún fragmento literal durante la sesión del 14/10/2026** — esta
> versión es una reconstrucción basada ENTERAMENTE en los resúmenes de
> `CLAUDE.md`, bastante más corta e incompleta que el original. Trátala
> como un índice de lo que se sabe que contenía, no como el documento en
> sí — el redactado original, los ejemplos concretos y buena parte del
> razonamiento intermedio se han perdido.

# Hoja de ruta: IPD y próxima fase

Plan de 3 pasos, en el orden exacto que pidió el usuario:

1. **Índice de Puresa Dialectal (IPD)** primero — una métrica propia
   (ratio de ocurrencias de formas occidentales sobre el total de
   ocurrencias marcadas), reemplazando el enfoque basado en reglas de
   `estudi_dialectal.py` por uno basado en el índice de palabras del
   traductor, usable sobre cualquier documento o corpus.
2. Después, incorporar una capa de modelo (LLM) para cat→val, solo una
   vez cerrados los huecos arreglables del benchmark.
3. Por último, probar con un dataset distinto del benchmark de 151 (el
   BOE, identificado como candidato).

## Paso 1 — HECHO (13/10/2026)

Implementado como hito propio del proyecto, etapa 9:
`pipeline/09_index_puresa_dialectal/ipd.py` + README.md (valencià) + README.es.md
(castellano) — ver esos ficheros para el detalle técnico completo
(fórmula, fuentes de datos, limitaciones conocidas), que SÍ siguen
existiendo y no se han perdido.

Resumen de lo más importante:
- Reutiliza directamente los `carrega_*`/`carrega_*_invers` de
  `traductor/rules/val_cat/` y `cat_val/` (lexic, demostratius,
  numerals, possessius) más un loader propio y más estricto para las
  conjugaciones (`_carrega_conjugacions_pures`), en vez de mantener
  listas de palabras curadas a mano como hacía `estudi_dialectal.py`.
- **Dos bugs reales encontrados y corregidos la misma tarde** (a raíz de
  que el usuario desconfiara del número viendo el informe `--html`,
  concretamente con "aquestes"): (1) sin filtro de categoría gramatical,
  formas verbales raras colisionaban con palabras comunes ("entre",
  "poden", "base"...); (2) el prefijo elidido ("d'aquestes" nunca casaba
  con la entrada "aquestes" porque el tokenizador trata el apóstrofo
  como parte de la palabra).
- Validado contra el benchmark de 151 frases: IPD 0,9339 en el lado
  valenciano, 0,0153 en el catalán.
- Confirmado a mayor escala con el corpus del BOE y, más tarde
  (14/10/2026), con el dataset `gplsi/CA-VA_alignment_test` (1.958
  frases): mismo patrón en los tres corpus independientes.
- Se dejó como módulo/CLI independiente, sin tocar `estudi_dialectal.py`
  directamente, para no arriesgar la etapa 1 ya estable.

> **Nota 14/10/2026**: el Paso 1 se siguió ampliando después de escrito
> este resumen — validación contra el dataset gplsi, un filtrado del
> corpus por IPD para separar sinonimia de fallos reales del motor, y 4
> bugs reales nuevos encontrados en el propio diccionario del traductor
> (no en el IPD) gracias a esa validación. Todo esto está documentado
> con mucho más detalle y de primera mano en `CLAUDE.md` — es la fuente
> más completa y fiable a partir de esa fecha, más que este documento
> reconstruido.

## Paso 2 — pendiente

Incorporar una capa de modelo (LLM) para cat→val, una vez cerrados los
huecos arreglables del benchmark de reglas. Ver el estado real de esto
(aparcado a petición del usuario el 14/10/2026, con la decisión de usar
`qwen3` en vez de `qwen2.5:14b` al retomarlo) en `CLAUDE.md`, sección
"Pendiente".

## Paso 3 — hecho (gplsi 14/10/2026, BOE completo 15/10/2026)

Probar con un dataset distinto del benchmark de 151: se hizo el
14/10/2026 con `gplsi/CA-VA_alignment_test` (Hugging Face, CC BY 4.0,
1.958 frases) en vez de con el BOE que se había identificado como
candidato original — ver `CLAUDE.md` para los resultados completos
(IPD, benchmark de traducción completo y filtrado, análisis de fallos).
El BOE a gran escala (el corpus `corpus_entrenamiento.jsonl` completo,
~268.000 líneas) se probó después, el 15/10/2026: ver la sección
siguiente.

## Estado del IPD a 21/10/2026

Resumen de todo lo hecho en el IPD desde el 14/10/2026. El detalle
técnico vive en el docstring de `pipeline/09_index_puresa_dialectal/ipd.py`
y en sus dos README.

### 15/10/2026 — BOE completo y marcadores no fiables por registro

Primer cálculo sobre el BOE completo (267.962 documentos, lado
valenciano): 0,8071, bastante por debajo del benchmark y de gplsi. Medido
contra frecuencias reales, "qué" aparece 1 vez por cada 17.584 "què" y
"açò" 65 veces por cada 5.708 "això": son pares reales (el traductor los
convierte bien), pero no son señal de dialecto en registro formal. Se
excluyen solo del IPD (`_MARCADORS_NO_FIABLES_REGISTRE`), sin tocar el
traductor. BOE completo: **0,8071 → 0,9219**.

### 16/10/2026 — Tres mejoras identificadas y aparcadas

1. "nou" (adjetivo/numeral compartido) contaba como marcador catalán por
   el par "anou"/"nou" (nuez). **Resuelto el 21/10/2026** con el
   mecanismo de homógrafos (ver abajo).
2. "estat" y "recull": formas verbales que spaCy etiqueta como verbo con
   frecuencia suficiente para colarse (582 y 246 veces en el BOE).
   **Sigue abierto.**
3. Formas con espacio (126, locuciones y numerales compuestos) que nunca
   pueden casar con un token suelto. Impacto nulo; **sigue sin limpiar**.

### 21/10/2026 — Revisión tras la migración a los diccionarios del proveedor

**Sincronización: correcta.** El IPD no lee los JSON por su cuenta:
reutiliza los cargadores del traductor, así que cualquier cambio de datos
le llega solo. `python -m traductor.sync_data --check` confirma que
`traductor/data/` coincide con `diccionarios/`. La regla de la forma
canónica del 20/10/2026 no cambia el índice. El doctest de "Este xiquet
vol vindre hui." pasó de 3 a 4 marcadores: "vindre" llega con los
infinitivos de `conjugaciones_general.json`, y es correcto.

**Problema encontrado: homógrafos.** Al retirar las listas de exclusión
del traductor (19/10/2026), algunas formas empezaron a contar como
marcador falso porque tienen un homógrafo común a los dos dialectos. Caso
tipo: `E0977` empareja correctamente el adjetivo catalán "desprès" (que
se desprende de lo que tiene) con el adjetivo valenciano "després"; pero
el adverbio "després" (más tarde) se escribe igual y es compartido, así
que cualquier texto catalán con "després" sumaba marcadores valencianos.
El lado catalán del benchmark de 151 llegó a 0,1135.

**Alternativas probadas y descartadas, todas medidas sobre 151 + gplsi:**

| Alternativa | Por qué se descartó |
|---|---|
| Filtro general: el marcador no cuenta si spaCy da una categoría distinta de la del diccionario | spaCy (catalán central) no conoce "seua", "este", "hui", "xicoteta" y les inventa la etiqueta: perdía ~1.100 marcadores buenos en gplsi |
| El mismo filtro, solo en categorías abiertas y con clases amplias | Seguía perdiendo "hui", "anglés", "francés" |
| El mismo filtro, solo cuando spaCy está seguro (probabilidad ≥ 0,95) | Mucho mejor, pero spaCy se equivoca con seguridad alta en algunas formas que no conoce ("faena", "vosté" como VERB) y en participios ("firmat", "signat") |
| Ignorar todas las entradas `colision` | Una colisión significa "varias traducciones posibles", no "palabra no dialectal": perdía "xiquet", "nen", "xicotet" |
| Usar la tabla de lemas de spaCy o los vectores de `ca_core_news_md` para saber qué palabras conoce spaCy | Ninguna de las dos lo distingue: la tabla incluye formas valencianas y le faltan catalanas básicas; los vectores conocen todas las formas |

**Diseño final (decisión del usuario: que spaCy solo clasifique los
homógrafos).** spaCy se consulta únicamente para las formas que el
proveedor declara como homógrafas: entradas `problema:
"homonimia_lexica"`, con `forma_problematica`, `lemas` (categoría de
cada lectura) y `categoria` (la de la lectura dialectal).

- Si ninguna otra lectura comparte la categoría dialectal (14 formas
  activas, como "manca": adj/n), el marcador cuenta solo cuando spaCy le
  da esa categoría.
- Si otra lectura la comparte ("bes", "blanca", "calces", "gandula",
  "gandules"), spaCy no puede decidir y la forma no cuenta nunca.
- El resto de palabras no pasa por spaCy.

Implementado en `ipd.py::_carrega_homografs` y `_classifica_token`. Sin
listas a mano: todo sale de campos del diccionario.

**Resultados:**

| Corpus | Lado valenciano (ideal 1) | Lado catalán (ideal 0) |
|---|---|---|
| Benchmark 151 | 0,9647 → **0,9749** | 0,1135 → **0,1115** |
| gplsi (1.958) | 0,9341 → **0,9387** | 0,0685 → **0,0632** |

32/32 doctests de `ipd.py`. La traducción no cambia (cat→val 137/154).

### Lo que queda abierto

- **"després" y "tancat" no están declarados como homógrafos** en los
  datos, así que siguen contando como marcador falso (17 "després" en
  cada corpus). El mecanismo los filtrará en cuanto se marquen como
  `homonimia_lexica` en origen, sin tocar código. Con "després" marcado,
  el lado catalán bajaría a unos 0,05 en los dos corpus. **Decisión del
  usuario (21/10/2026): dejarlo así de momento.**
- **`E0537`/`E0538` (tancada/tancades)** tienen `categoria: "adj"`, pero la
  lectura dialectal es el nombre ("vallado"); con el dato así, el IPD
  cuenta "tancada" adjetivo, que es compartido.
- **"nou" (nuez) no cuenta nunca**: spaCy etiqueta "nou" como NUM incluso
  cuando es nombre ("la nou és dura"). Falso negativo aceptado.
- **Palabras compartidas por registro**: "estat" (29 en gplsi), "avui"
  (12), "últim" (11), "mentre", "ordre", "desenvolupament", "alcalde".
  Son pares reales pero malos marcadores en textos formales; es la misma
  decisión de registro pendiente en el traductor.
- **"petit"/"menut" mal emparejado** en los datos (36 marcadores falsos
  en gplsi). Solo se arregla en origen.
- **Incoativos**: el IPD no los cuenta. Medido con el mecanismo de
  `cat_val/incoatius.py` (spaCy + infinitivos de los JSON): +215
  marcadores catalanes y +55 valencianos en gplsi, con un solo error
  ("conquereix"). Preparado, no aplicado.
