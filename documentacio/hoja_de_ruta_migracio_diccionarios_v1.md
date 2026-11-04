# Hoja de ruta: migración a `diccionarios_v1/` (proveedor de datos, 16/10/2026)

Documento vivo. Objetivo final (pedido explícito del usuario): sustituir
todos los JSON de `pipeline/02_regles_dialectals/lexic/` por los 3
ficheros de `pipeline/02_regles_dialectals/lexic/diccionarios_v1/`, y
cuando esté todo migrado y verificado, borrar los JSON viejos, mover los
3 nuevos directamente a `lexic/` y borrar la carpeta `diccionarios_v1/`.

**No es un reemplazo ciego de fichero por fichero** — hay al menos un caso
confirmado (ver sección 4) donde el motor ya tiene una decisión validada
con evidencia que CONTRADICE lo que dice el diccionario nuevo. Cada
módulo se migra comprobando contra el benchmark, nunca asumiendo que "lo
nuevo gana siempre".

## 1. Qué hay en `diccionarios_v1/` (verificado 16/10/2026, bytes/encoding limpios en los 3)

| Fichero | Filas | Qué es |
|---|---|---|
| `lexico_general.json` | 1.629 | Léxico general + numerales + demostrativos/pronombres, todo en un fichero, con campo nuevo `categoria`. |
| `conjugaciones_general.json` | 43.242 (4.752 verbos) | Conjugaciones con raíz igual en los dos dialectos. Campo `morfologia`: **lista de listas cuando la forma es ambigua** (ver sección 5). |
| `verbos_diferentes_conjugados.json` | 912 | Verbos con raíz DISTINTA en cada dialecto (p.ej. "telefonar"/"trucar per telèfon"). Ya trae `ambigu`/`repetida`/`cat_traduccions_val` calculados. |

## 2. Correspondencia con los ficheros actuales de `traductor/data/`

| Fichero/mecanismo actual | Origen actual (`sync_data.py`) | Sustituto en `diccionarios_v1/` |
|---|---|---|
| `lexic_general.json` | `unificado.json` | `lexico_general.json` (categorías n/adj/adv/cnjadv/pr/ij) |
| `numerals_general.json` | `numerales_limpio.json` | `lexico_general.json`, `categoria: "num"` (77 entradas, más completo: compuestos hasta decenas de miles) |
| `possessius_general.json` | `posesivos_cat_val.json` | probablemente `lexico_general.json`, `categoria: "prn"` — **pendiente confirmar cobertura completa**, solo 6 entradas en `prn` vistas, parece insuficiente para posesivos completos (meu/meua/meus/meues...) |
| `demostratius_avl.json` (val_cat, hardcoded "aquest" default) | curado a mano | `lexico_general.json`, `categoria: "det"` (8 entradas: este/esta/estos/estes/eixe/eixa/eixos/eixes) — **⚠️ ver sección 4, conflicto real** |
| `conjugacions_dialectals.json` | 4 fuentes fusionadas (`verbos_no_ambiguos.json` + `conjugaciones_limpio.json` + `verbos_todos_anotados.json` + `conjugaciones_nuevo.json`, con lógica de orden/colisión en `sync_data.py`) | `conjugaciones_general.json` — **posible simplificación grande**: si este fichero ya es el consolidado del proveedor, buena parte de la lógica de fusión/orden actual de `sync_data.py` podría quedar obsoleta. Falta confirmar que es un superconjunto real antes de borrar esa lógica. |
| Verbos de raíz distinta (ya integrados dentro de `conjugacions_dialectals.json` hoy, causaban el bug de locuciones "digues adéu" en el GD) | mezclados en las mismas 4 fuentes de arriba | `verbos_diferentes_conjugados.json`, ahora SEPARADO — esto probablemente arregla solo, de raíz, el bug de locuciones multi-palabra que encontramos ayer en el GD (ya no estarán mezcladas con las conjugaciones de raíz única). |
| `categoria_gramatical_lexic.json` (hoy solo `"anou": "NOUN"`, a mano) | curado a mano, 1 sola entrada | el campo `categoria` de `lexico_general.json` ya lo da para TODO el léxico (no solo "anou") — esto es lo que más impacto puede tener: resolvería de raíz el hueco que encontramos el 16/10 con "nou" en el GD. |
| `canvi_genere_lexic_avl.json`, `flexio_genere_avl.json` | curados a mano | sin equivalente visto todavía en los 3 ficheros nuevos — **pendiente de confirmar si el proveedor los cubre en otra entrega o si se quedan como están** |

## 3. Qué hay que seguir filtrando (igual disciplina que siempre)

- `lexico_general.json`: 251/1.629 (15%) siguen marcadas `v:lexic_val_PENDENT` — excluir igual que hoy. 125/1.629 son multi-palabra (algún lado con espacio) — necesitan el mismo tratamiento que ya existe para léxico multi-paraula (`carrega_frases_invers`), no el lookup de una sola palabra.
- `conjugaciones_general.json`: muy limpio — solo 2/43.242 multi-palabra, 0 con `catalan==valenciano`, 0 campos vacíos.
- `verbos_diferentes_conjugados.json`: 17/912 multi-palabra, 589/912 (65%) marcadas `ambigu: true`, 798/912 `repetida: true` — hace falta la misma lógica de desduplicación que ya usan los loaders actuales (`candidats_val`/`candidats_cat`, unicidad).
- No se ha visto ningún topónimo (`v:top_gva`) en `lexico_general.json` — a confirmar si ya vienen excluidos de origen o si hace falta seguir protegiendo nombres propios de todas formas (sí, vía `marca_noms_propis()`, eso no depende del fichero).

## 4. ⚠️ Conflicto real encontrado: demostrativos

`lexico_general.json` (`categoria: "det"`) da la traducción literal
"eixe"→"aqueix". El motor actual, medido contra el benchmark real,
decidió deliberadamente que "este" Y "eixe" colapsan los dos a
**"aquest"** (el catalán oriental contemporáneo ha fusionado el sistema
de 3 graus en 2; "aqueix" apenas se usa en registro real) — aceptar el
dato nuevo tal cual **rompería esa decisión ya validada con evidencia**
(ver `CLAUDE_HISTORIAL.md`/`cat_val/demostratius.py` para el detalle
completo de esa medición). Antes de tocar `demostratius.py`: volver a
medir con el benchmark + gplsi si "aqueix" aparece de verdad en el
catalán de referencia o si sigue siendo ~0% real. No asumir en ningún
sentido sin remedir.

**Dato positivo relacionado**: "vos"→"us" reaparece en `categoria: "prn"`
(`fuente: unificado`) — es uno de los pares AVL-only retirados el
30/09/2026 que causaba ~25% de los fallos de gplsi (ver "Pendiente" en
`CLAUDE.md`). Si se confirma que viene con el mismo respaldo que el resto
del fichero, podría resolver ese pendiente de forma natural al migrar.

## 4bis. Fase 1 hecha (numerales) — hallazgo real: el fichero nuevo pierde cobertura

Comparado `lexico_general.json` (`categoria: "num"`, 77 entradas) contra
`numerals_general.json` actual (176 entradas): **0 entradas ganadas, 99
perdidas** — todas formas ORDINALES ("cinquanta-huitena"→"cinquanta-vuitena",
"denovena"→"dinovena", "dessetena"→"dissetena"...). Donde coinciden, dicen
lo mismo (0 conflictos). El fichero nuevo solo cubre cardinales.

**Decisión del usuario (16/10/2026): dejarlo como pendiente, no bloquear
el resto de la migración por esto.** Se extrajeron las 99 entradas
faltantes a un fichero aparte, `pipeline/02_regles_dialectals/lexic/numerals_ordinals_pendent.json`
(mismo esquema que `numerals_general.json`: `valenciano`/`catalan`/`revision`),
para no perder el dato mientras se decide qué hacer (¿el proveedor lo añade
en una próxima entrega? ¿se fusiona a mano con `lexico_general.json`?).
**No incorporado todavía a ningún loader** — es solo la pieza guardada,
la decisión de cómo encajarla queda abierta.

## 4ter. Fase 3 — léxico general: revisado a fondo, resultado positivo, 3 huecos documentados

Comparado `lexico_general.json` (categorías n/adj/adv/cnjadv/pr/ij) contra
`lexic_general.json` actual, replicando la MISMA lógica de resolución
`canonica` que usa hoy `_resol_polisemia()` (no una comparación ingenua):

- **1.027 → 1.202 entradas (+175 netas)**: 253 ganadas, 78 aparentemente
  perdidas.
- **De las 78, la inmensa mayoría NO son pérdida real**, comprobado
  buscando cada una en los 3 ficheros nuevos (no solo en el léxico
  general): los verbos con raíz distinta ("eixir"→"sortir",
  "cercar"→"buscar", "telefonar"→"trucar per telèfon"...) viven ahora en
  `verbos_diferentes_conjugados.json` con su paradigma completo; varios
  sustantivos multi-palabra ("dacsa"→"blat de moro", "portada"→"cop de
  porta", "avitarda"→"pioc salvatge"...) SÍ están en `lexico_general.json`,
  solo que necesitan el mismo tratamiento de léxico multi-paraula que ya
  existe (como `carrega_frases_invers` en `cat_val`), no un lookup de una
  sola palabra. **Pérdida real confirmada, tras buscar en los 3
  ficheros**: solo ~10 palabras (amprar, bollir, encollir, enllandar,
  invadir, solejar, subdesenrotllar, "i+d", "i+d+i", "despús-demà") —
  menos del 1% del total.
- **Solo 1 discrepancia real entre lo que coincide en los dos**:
  "hereua" pasa de "hereu" (género mal emparejado) a **"hereva"**
  (corregido) — mejora real.
- **"vesprada" aparece corregido** ("tarda", no ya "tard") — ya no haría
  falta seguir excluyéndolo.
- **"ensenyança"→"ensenyament" sigue sin corregir**, igual que
  **"xicotet"→"menut" (`canonica: true`) sigue sin corregir** (debería
  ser "petit", confirmado contra 1.958 frases reales de gplsi) — estos
  dos siguen necesitando nuestra propia corrección encima del dato nuevo,
  migrar no basta.

**Hueco nuevo encontrado, mismo tipo que numerales-ordinales y
posesivos**: la capa de ACENTUACIÓN (695 pares tipo "francés"(val,
tancat)/"francès"(cat, obert), hoy en `lexic_acentuacio_general.json`)
**no parece estar en la entrega nueva** — "francés" y "qué" aparecen con
el MISMO accent als dos costats en `lexico_general.json`, no l'alternança
que fa falta. Pendiente de confirmar si ve en una entrega futura.

**Decisión del usuario (16/10/2026): dejar aparcado, de momento no se
toca ningún loader real.** Documentado para retomar cuando haya más
piezas (posesivos, acentuación) o la explicación de `morfologia`.

## 4quater. Léxico general MIGRADO de verdad (val→cat), 16/10/2026

Tras la revisión de arriba, decisión del usuario: "quitando numerales y
posesivos... nos quedamos con las entradas nuevas". Implementado para
val→cat (cat→val pendiente, siguiente paso natural):

**Cambios aplicados**:
- `sync_data.py`: `lexic_general.json` ahora sincroniza desde
  `diccionarios_v1/lexico_general.json` (antes `unificado.json`).
- `val_cat/lexic.py::_carrega_lexic_general()`: filtra por
  `categoria in {n,adj,adv,cnjadv,pr,ij,prn}` (deja `num`/`det` a sus
  propios módulos).
- `_CANONICA_OVERRIDES = {"xicotet": "petit"}`: el bug de "xicotet"→"menut"
  (debería ser "petit", confirmado contra gplsi) sigue sin corregirse en
  la fuente — override explícito encima.
- `_BUG_DADES_CONEGUTS`: quitado "vesprada" (ya viene bien, "tarda"),
  añadidos **"alcalde"** (→"batlle", regresión real RC136, mismo patrón
  de registro que "qué"/"ensenyament") y **"tancada"** (→"closa",
  regresión real RC144 — el proveedor mismo lo marca `problema:
  "homonimia_lexica"`, nombre "vallado" vs. adjectiu "tancat/da", la
  entrada solo vale para el sentido nombre). Hay **24 entradas con este
  mismo flag `homonimia_lexica`** en total — solo se excluyó la
  confirmada por regresión real, el resto queda pendiente de medir una
  a una (no generalizar sin evidencia), candidatas a resolverse mejor
  con el mecanismo de `categoria_gramatical_lexic.json` más adelante.
- `_LEXIC_PERDUT_RESTAURAT`: 11 palabras confirmadas perdidas de verdad
  (llavar, espentar, encollir, enllandar, bollir, solejar, amprar,
  subdesenrotllar, invadir, i+d, i+d+i) restauradas a mano desde
  `unificado.json` hasta que lleguen en una entrega futura.
- **Bug real encontrado y arreglado, independiente de los datos**:
  `ConjugacionsDictRule` (val_cat) comprobaba `SEMPRE_VERB` contra la
  superficie CON el prefijo elidido pegado ("l'eixir"), antes de separar
  el prefijo — nunca coincidía con "eixir" suelto. Nunca se había visto
  porque ninguna de las 5 formas anteriores de `SEMPRE_VERB` empezaba en
  vocal. Expuesto al perder "eixir"→"sortir" del léxico general (ahora
  solo en `verbos_diferentes_conjugados.json`, sin integrar todavía) —
  se añadió "eixir" a `SEMPRE_VERB` y se corrigió el orden de
  comprobación.

**Verificación final**: 542/542 doctests, benchmark 151 **115/151
(76,2%), BLEU 97,67 — idéntico al número de antes de migrar**, pero con
mejor composición: se arregla RC049 ("galletes"/"galetes", hueco de
diccionario ya documentado) y pasa a fallar RC138 ("últims"/"darrers",
reaparece el par AVL-only retirado el 30/09/2026 -- trade-off aceptado
con el mismo criterio que "qué"/"ensenyament", confirmado con gplsi que
compensa de sobra: ver abajo).

**Confirmado con gplsi completo (1.958 frases)**: **1281/1958 (65,4%) →
1330/1958 (67,9%), +49 frases**, BLEU 89,20→89,97. La migración (incluida
la reincorporación de "últim"/"darrer") es una mejora real a escala,
compensa de sobra el único caso que empeoró en el benchmark de 151
(RC138) -- trade-off confirmado con evidencia, no solo aceptado a ciegas.

## 4quinquies. Léxico general MIGRADO (cat→val), 16/10/2026

Mismo enfoque que val→cat, aplicado a `cat_val/lexic.py`:

- Mismo filtro `categoria` en `_carrega_lexic_general_invers()` y
  `carrega_frases_invers()` (léxico multi-paraula).
- "tard" quitado de `_BUG_DADES_CONEGUTS_CAT` -- confirmado que ninguna
  entrada nueva colisiona ya con "tard" (el bug "vesprada"/"tard" viene
  arreglado en origen, igual que para val→cat).
- `_LEXIC_PERDUT_RESTAURAT_CAT = {"empentar": "espentar", "rentar": "llavar"}`
  -- mismas 2 palabras perdidas que afectaban al benchmark en esta
  dirección también (RC022/RC025).
- **Bug real encontrado y arreglado, mismo tipo que el de `SEMPRE_VERB`
  en val→cat pero distinto mecanismo**: `ConjugacionsDictInversRule`
  nunca llamaba a `corregeix_contraccio_al_abans()` tras traducir (al
  contrario que `LexicInversRule`, que sí lo hace) -- invisible mientras
  "sortir"->"eixir" vivía en el léxico general (vía `LexicInversRule`,
  que sí corrige la contracción); expuesto al migrar ese par a
  `verbos_diferentes_conjugados.json` (sin integrar), dejando
  "sortir"->"eixir" en manos de `ConjugacionsDictInversRule`, que no
  deshacía "al"->"a l'" (RC016: daba "Al eixir" en vez de "A l'eixir").
  Corregido añadiendo la llamada que faltaba.
- **RC038 nuevo, aceptado como trade-off**: "pardals"->"teuladins" es una
  entrada NUEVA real (no existía la forma plural en el fichero viejo),
  técnicamente correcta ("pardal"="gorrión"), pero en esta frase concreta
  (un texto etimológico sobre el Caprimulgus, un ave que NO es un
  gorrión) la referencia prefiere dejarlo sin tocar -- mismo tipo de
  elección estilística ya aceptada para RC064/RC069, no es un bug.

**Verificación final**: 543/543 doctests, benchmark 151 **116/151 (76,8%),
BLEU 98,12 -- igual o mejor que antes de migrar**, con la misma mejora de
composición (RC049 arreglado, RC038 como trade-off defendible).

**Confirmado con gplsi completo**: **1212/1958 (61,9%) → 1267/1958
(64,7%), +55 frases**, BLEU 88,08→88,89. Mejora real a escala en las dos
direcciones.

## 4sexies. CORRECCIÓN (16/10/2026, más tarde): numerales y acentuación SÍ se podían migrar casi del todo

Las secciones 4bis/4ter de arriba (numerales "77/176", acentuación "no
está en la entrega") estaban **mal medidas** — comprobaciones rápidas
sin pasar por la resolución real de `canonica`, y sin mirar la categoría
`"adj"` para los ordinales. El usuario preguntó explícitamente "¿no
deberían bastar los 3 ficheros nuevos?" y al remedir con rigor
(usando los loaders reales, no atajos) resultó que sí, casi del todo:

- **Ordinales**: los masculinos singulares en "-è" están bajo
  `categoria: "adj"` (gramaticalmente correcto, un ordinal es un
  adjetivo), no `"num"` — por eso no aparecían en mi primera
  comprobación. Combinando `categoria: "adj"` (vía `LexicRule`, que ya
  corre antes que `NumeralsRule`) + `categoria: "num"`: **153/176
  cubiertas**, solo 25 huecos reales (un único patrón morfológico: el
  ordinal masculino singular en "-è" — "huitè", "dihuitè"... — ausente
  de la entrega, mientras que el femenino "-ena" y los plurales "-ens"/
  "-enes" sí están).
- **Acentuación**: remedido con el loader real (`carrega_lexic()`, no
  una comparación manual de 2-3 palabras sueltas) — **693 de 705 pares
  reales ya cubiertos** solo con el léxico general migrado. Los 12
  huecos reales: 8 son locuciones multi-paraula que NINGÚN mecanismo
  del proyecto soporta (ni el viejo fichero de acentuación las cubría
  realmente — "vostè mateix" tiene multi-paraula a los DOS lados, fuera
  del alcance de `carrega_frases_invers`), 1 es "després" (exclusión ya
  intencional), 1 es "tèlexs" (ni es una diferencia dialectal real), y
  **4 son un hallazgo real** ("cinquè"/"sisè"/"setè"/"novè" como
  ordinales básicos) — ver más abajo.
- **Posesivos**: confirmado de nuevo, con búsqueda exhaustiva en TODAS
  las categorías — siguen con 0/6 cobertura real, genuinamente ausentes.

**Migración ejecutada**: `numerals.py` (las dos direcciones) ahora lee
directamente `lexic_general.json` filtrando `categoria == "num"` — ya
no existen `numerals_general.json` ni su fuente `numerales_limpio.json`.
La capa de acentuación a banda (`lexic_acentuacio_general.json` /
`acentuacion_limpio.json`) se **retiró por completo** — el patrón
productivo de sufijo en `accentuacio.py` (que no depende de ningún
fichero, cubre CUALQUIER palabra con ese sufijo) sigue intacto como red
de seguridad independiente.

**Bug real encontrado de paso** (RC144, cat→val): "cinquè"→"cinqué" SÍ
existe en `lexico_general.json` con `canonica: true` (colisionando con
otra entrada "cinqué"→"cinqué" de sentido nombre, `canonica: false`) —
`_carrega_lexic_general()` (val→cat) la resuelve bien con `canonica`,
pero `_invertix_sense_ambiguitat` (cat→val, agrupa por catalán) la
excluye por tener más de un candidato valenciano real visto desde ese
lado — mismo criterio conservador de siempre (prefiere falso negativo),
pero aquí costaba una regresión real. Restaurados a mano los 4 casos
("cinquè", "sisè", "setè", "novè") en `_ORDINALS_BASICS_PERDUTS_CAT`.

**Ficheros borrados en esta ronda**: `numerales_limpio.json`,
`acentuacion_limpio.json` (fuentes), sus copias en `traductor/data/`, y
`numerals_ordinals_pendent.json` (el de 99 entradas que se creó con el
análisis incompleto — ya no hace falta, los 25 reales viven embebidos
en `_ORDINALS_PERDUTS`/`_ORDINALS_PERDUTS_CAT` con su evidencia).

**Lección**: la primera vez NO se verificó con el mismo rigor que el
resto del proyecto exige (comprobaciones rápidas en vez de pasar por los
loaders reales) — el usuario tuvo razón en pedir que se revisara otra
vez antes de descartar nada.

## Resumen del estado tras hoy (16/10/2026)

Léxico general, numerales y acentuación migrados y verificados en las
dos direcciones:

| | val→cat (151) | val→cat (gplsi) | cat→val (151) | cat→val (gplsi) |
|---|---|---|---|---|
| Antes de migrar | 115/151 | 1281/1958 | 116/151 | 1212/1958 |
| Después de migrar | 115/151 | **1330/1958 (+49)** | 116/151 | **1267/1958 (+55)** |

Mismos números en el benchmark curado en las dos rondas de migración
(léxico general, y después numerales/acentuación) — cero regresión neta
en ningún punto, verificado con doctests + los 2 benchmarks + gplsi
completo en cada paso.

**Solo posesivos se queda de verdad con la fuente vieja** (0%
cobertura, confirmado dos veces). El resto de `lexic/` que queda:
`posesivos_cat_val.json` (posesivos), las 4 fuentes de conjugaciones
(`verbos_no_ambiguos.json`, `conjugaciones_limpio.json`,
`conjugaciones_nuevo.json`, `verbos_todos_anotados.json` — bloqueadas
hasta la explicación de `morfologia`), y `palabras_traducidas.json`
(dependencia real de `05_corpus_boe/analizar_corpus.py`, sin relación
con el traductor).

## 5. Códigos de `morfologia` — DESCIFRADOS CON EVIDENCIA (19/10/2026, ya no bloquea nada)

**Resuelto sin esperar la explicación prometida.** Al revisar con calma
qué haría falta para integrar `conjugaciones_general.json` de forma
segura, se vio que el riesgo real (interpretar mal indicatiu/subjuntiu)
no dependía de decodificar `morfologia` en absoluto: el lookup de
`conjugacions_dict.py` es un diccionario plano `valenciano->catalan`, y
**nunca ha usado el campo de tiempo/modo para elegir una traducción** —
es puramente informativo. La seguridad real viene de otro sitio, que ya
existía: el proveedor marca las filas peligrosas con los mismos campos que
ya usan los 4 ficheros viejos (`problematica`/`problema: colision` en
`conjugaciones_general.json`; `ambigu`/`ambigu_cat_a_val` en
`verbos_diferentes_conjugados.json`, mismo esquema que
`verbos_no_ambiguos.json`/`verbos_todos_anotados.json`), y las dos
direcciones del motor YA recalculan la ambigüedad real directamente
sobre los datos (nunca confiando en el nombre de un campo) — ver
`conjugacions_dict.py::_marca_ambigues_dins_del_mateix_fitxer` (val→cat)
y `cat_val/conjugacions_dict.py::carrega_conjugacions_invers` (cat→val,
comentario explícito: "no es confia nomes en el camp
ambigu_cat_a_val del proveedor").

Aun así, se descifraron los códigos de tiempo/modo con evidencia real
(cruzando las formas catalanas/valencianas contra la gramática conocida,
y validando contra el caso ya documentado en el propio código,
`es_risc_mode_3a_plural("creuen", "creuin")`):

| Código | Significado | Evidencia |
|---|---|---|
| `pri` | Present d'indicatiu | `abaixar`: cat "abaixo" / val "abaixe" — 1a sg present, forma corriente |
| `prs` | Present de subjuntiu | Colisiona con `imp` en 3a persona (ambigüitat real del català: "abaixin" = imperatiu formal O present subjuntiu) |
| `pii` | Pretèrit imperfet d'indicatiu | Rarísimo (12/43.242) — coherente: el imperfet d'indicatiu casi nunca difiere entre dialectos |
| `pis` | Pretèrit imperfet de subjuntiu | El más frecuente (28.484) — coherente: el imperfet de subjuntiu SIEMPRE difiere (-ra valenciano / -és català) |
| `imp` | Imperatiu | — |
| `pp` | Participi (passat) | `acomplir`: cat "acomplertes" (irregular) / val "acomplides" (regular) |
| `inf` | Infinitiu | Fila sin persona/nombre (`['inf']` solo) |
| `vbmod`/`vbhaver`/`:haver<vaux` | Marca de classe verbal (modal/auxiliar), no de temps | Antepuesto al código de tiempo normal en verbos especiales (`caldre`, `haver`) |
| `n`/`adj`/`adv`/`prn`/`ij` (+ `sup`/`m`/`f`/`mf`) | Col·lisió amb una altra categoria gramatical | Siempre acompañado de `problematica: true`, `problema: "colision"` — ya excluido por el filtro existente |
| `fti` | Sin decodificar con confianza | 1 sola aparición en todo el fichero (<0,01%) — irrelevante en la práctica |

Estos 7 códigos principales cubren el 99,7% de las 43.242 filas. Detalle
completo de la verificación (tally por posición, ejemplos cruzados) en
el historial de la sesión del 19/10/2026.

**Conclusión: `conjugaciones_general.json` y `verbos_diferentes_conjugados.json`
ya NO están bloqueados.** Se integraron el 19/10/2026 como fuentes
OFICIALES (máxima prioridad) en `sync_data.py::FONTS`, delante de los 4
ficheros viejos. Medido con doctests + benchmark 151 + gplsi completo,
las dos direcciones:

| | val→cat 151 | val→cat gplsi | cat→val 151 | cat→val gplsi |
|---|---|---|---|---|
| Antes (solo 4 ficheros viejos) | 115/151 | 1330/1958 | 116/151 | 1267/1958 |
| Después (oficiales + 4 viejos de red de seguridad) | 114/151 | **1408/1958 (+78)** | 116/151 | **1341/1958 (+74)** |
| Solo oficiales, SIN los 4 viejos | 106/151 | 1399/1958 | 107/151 | 1328/1958 |

La única "regresión" del benchmark de 151 (RC021, val→cat) no es un bug:
la referencia catalana mantiene literalmente "tindre" sin traducir
porque la frase ES una cita metalingüística de la propia expresión
valenciana ("l'expressió tindre faena, és a dir..."), no un uso verbal
normal — mismo patrón ya documentado para "rentar" en RC002. El resto es
mejora neta clara, especialmente a escala (gplsi).

**Los 4 ficheros viejos NO se pueden retirar todavía** (fila "Solo
oficiales" de la tabla): sin ellos como red de seguridad se pierden -8/-9
frases del benchmark de 151 y -9/-13 de gplsi — cubren formas/verbos
reales que `diccionarios_v1` aún no trae. Se quedan con prioridad más
baja hasta que una entrega futura los haga innecesarios de veras.

## 5bis. El usuario preguntó por qué los 4 ficheros viejos siguen haciendo falta — investigado a fondo, solo 1 de 4 aporta algo real (19/10/2026)

Pregunta del usuario: "en teoría `conjugaciones_general` debería ser el
`conjugaciones_limpio` y/o `nuevo`". Tenía razón en parte — diferencia
verbo a verbo (no solo contar frases del benchmark) entre
`conjugaciones_general.json` + `verbos_diferentes_conjugados.json`
(combinados) contra cada uno de los 4 ficheros viejos:

- `verbos_no_ambiguos.json` (261 formas/45 verbos): **0 infinitivos de
  una sola palabra sin cubrir** en las fuentes oficiales.
- `verbos_todos_anotados.json` (1.311 formas/50 verbos): **0 infinitivos
  de una sola palabra sin cubrir**.
- `conjugaciones_nuevo.json` (49.443 formas/5.465 verbos): **0
  infinitivos de una sola palabra sin cubrir** — de los 722 "verbos" que
  parecían faltar, todos resultaron ser frases multi-palabra
  ("llençar la brossa", "fer cara de", "estar al corrent"...), no verbos
  reales, y el motor no tiene ningún mecanismo para aplicar una entrada
  de conjugación multi-palabra de todas formas.
- `conjugaciones_limpio.json` (968 formas/111 verbos, el original de
  el proveedor, 29/09/2026): **12 verbos de una sola palabra SÍ ausentes**
  ("pertànyer", "apareixer", "acréixer", "prémer", "sofrir",
  "concórrer", "sobresortir", "revenir", "ajupir", "adeqüar" + 2 que
  parecen ruido del fichero origen). Pero el hallazgo importante no es
  este: es que el verbo **"ser" SÍ está en la lista de verbos de
  `conjugaciones_general.json`, pero con solo 3 formas** (`eres`/`ets`,
  `fóra`/`fos`, `sigut`/`estat`) — **falta TODO el paradigma de present
  de subjuntiu** (siga/sigues/siga/siguem/sigueu/siguen →
  sigui/siguis/sigui/siguem/sigueu/siguin).

Diferenciando qué frases exactas regresaban al quitar los 4 ficheros
viejos (no solo contar cuántas): **8 de las 9 regresiones de cada
dirección eran "siga"/"sigui" sin convertir** (RC033, RC067, RC078,
RC085, RC089, RC095, RC127, RC131, RC136 según dirección); la 9ª era
"pertany"/"pertanyo". Ninguna otra causa.

**Conclusión y acción**: se retiraron a `backup_pendent/`
`verbos_no_ambiguos.json`, `verbos_todos_anotados.json` y
`conjugaciones_nuevo.json` — confirmado con los 4 benchmarks completos
(151 + gplsi, las dos direcciones) que dan EXACTAMENTE los mismos
números que con los 4 ficheros viejos puestos (114/151, 116/151,
1408/1958, 1343/1958).

## 5ter. `conjugaciones_limpio.json` fusionado ENTERO dentro de `conjugaciones_general.json` y retirado también (19/10/2026)

El usuario pidió generar las formas que faltaban en formato
`conjugaciones_general.json` para fusionarlas a mano. Se generaron las 97
formas "nuevas" (vistas desde el lookup val→cat) con `morfologia`
derivada a mano siguiendo el mismo descodificado de la sección 5, se
fusionaron, y se retiró `conjugaciones_limpio.json` del todo.

**Esto rompió un doctest** (`cat_val/conjugacions_dict.py`,
`"sofreixin" in lookup` esperaba `False`, dio `True`). Investigado: el
fichero completo (968 filas, no 97) tenía una entrada
`sofrisquen→sofreixin` que **nunca aparecía como "forma nueva" en la
comparación val→cat** porque el motor la excluye de ese lookup por el
filtro de riesgo de colisión indicatiu/subjuntiu de 3ª plural
(`es_risc_mode_3a_plural`, mismo patrón que protege "creuen"/"siguen").
Pero esa misma fila SÍ hacía falta en bruto para la dirección cat→val:
`carrega_conjugacions_invers()` agrupa por forma catalana y excluye
cualquiera con más de un candidato valenciano real — sin la fila
"sofrisquen", "sofreixin" se quedaba con un solo candidato
("patisquen", de `verbos_diferentes_conjugados.json`) y dejaba de
detectarse como ambigua.

Repitiendo la comparación a nivel de PARES CRUDOS (`(valenciano,
catalan)`, no del lookup ya filtrado de una sola dirección) aparecieron
**55 pares más** en la misma situación — casi todos formas de 3ª plural
que el filtro de riesgo ya protegía del lado val→cat pero que hacían
falta en bruto para el lado cat→val. **Conclusión: la única comparación
realmente segura es a nivel de fila cruda, nunca sobre el resultado ya
filtrado de una sola dirección** — un filtro de una dirección puede
ocultar que una fila todavía hace falta para la otra.

**Acción final**: se fusionaron las 968 filas COMPLETAS de
`conjugaciones_limpio.json` dentro de `conjugaciones_general.json`
(IDs `LIMPIO_1`..`LIMPIO_968`, `morfologia` derivada a mano para 95
formas con evidencia real — ver tabla de códigos de la sección 5 —,
`null` en el resto como ya hace el proveedor con formas sin clasificar,
`problematica` preservado tal cual en 55 filas que ya lo traían). El
fichero original se retiró entero a `backup_pendent/`.
Confirmado con los 4 benchmarks: **resultados idénticos** a cuando
convivían los 2+1 ficheros (114/151, 116/151, 1408/1958, 1343/1958), y
el doctest roto vuelve a pasar. `traductor/data/conjugacions_dialectals.json`
pasó de 96.137 a 45.122 entradas, mismo contenido real.

**Pendiente de acción fuera de este repo**: informar al proveedor de que
`conjugaciones_general.json` parece tener un hueco real de datos en el
paradigma de present de subjuntiu del verbo "ser" (y probablemente de
otros verbos irregulares muy comunes — no se ha comprobado exhaustivamente
cada verbo irregular, solo "ser" porque es el que explicaba las
regresiones reales). No es un problema de filtrado de este lado del
proyecto.

## 6. Próximos pasos (fases ya acordadas con el usuario, sin empezar todavía)

1. ~~Fase 0 (parte estructural, sin depender de la explicación de morfologia)~~ — este documento.
2. Fase 1: construir loaders nuevos en paralelo, sin tocar los actuales.
3. Fase 2: comprobar una por una las decisiones ya validadas con evidencia (empezando por la de la sección 4) contra los datos nuevos.
4. Fase 3: migrar módulo a módulo (numerals primero, demostratius el último), doctests + benchmark 151 + gplsi en cada paso.
5. Fase 4: evaluar si `morfologia` (ya descifrado, ver sección 5) puede sustituir la heurística de sufijo de `es_risc_mode_3a_plural`/el filtro spaCy por un chequeo directo sobre los datos — mejora posible, no urgente, no empezada.
6. Fase 5: repuntar `sync_data.py` e `gd.py`.
7. Fase 6: verificación final completa y limpieza (borrar JSON viejos, mover los 3 nuevos a `lexic/`, borrar `diccionarios_v1/`).
