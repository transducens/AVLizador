# Hoja de ruta: migración a `diccionarios_v1/` (Mauricio, 16/10/2026)

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
| `lexic_mauricio.json` | `unificado.json` | `lexico_general.json` (categorías n/adj/adv/cnjadv/pr/ij) |
| `numerals_mauricio.json` | `numerales_limpio.json` | `lexico_general.json`, `categoria: "num"` (77 entradas, más completo: compuestos hasta decenas de miles) |
| `possessius_mauricio.json` | `posesivos_cat_val.json` | probablemente `lexico_general.json`, `categoria: "prn"` — **pendiente confirmar cobertura completa**, solo 6 entradas en `prn` vistas, parece insuficiente para posesivos completos (meu/meua/meus/meues...) |
| `demostratius_avl.json` (val_cat, hardcoded "aquest" default) | curado a mano | `lexico_general.json`, `categoria: "det"` (8 entradas: este/esta/estos/estes/eixe/eixa/eixos/eixes) — **⚠️ ver sección 4, conflicto real** |
| `conjugacions_dialectals.json` | 4 fuentes fusionadas (`verbos_no_ambiguos.json` + `conjugaciones_limpio.json` + `verbos_todos_anotados.json` + `conjugaciones_nuevo.json`, con lógica de orden/colisión en `sync_data.py`) | `conjugaciones_general.json` — **posible simplificación grande**: si este fichero ya es el consolidado de Mauricio, buena parte de la lógica de fusión/orden actual de `sync_data.py` podría quedar obsoleta. Falta confirmar que es un superconjunto real antes de borrar esa lógica. |
| Verbos de raíz distinta (ya integrados dentro de `conjugacions_dialectals.json` hoy, causaban el bug de locuciones "digues adéu" en el IPD) | mezclados en las mismas 4 fuentes de arriba | `verbos_diferentes_conjugados.json`, ahora SEPARADO — esto probablemente arregla solo, de raíz, el bug de locuciones multi-palabra que encontramos ayer en el IPD (ya no estarán mezcladas con las conjugaciones de raíz única). |
| `categoria_gramatical_lexic.json` (hoy solo `"anou": "NOUN"`, a mano) | curado a mano, 1 sola entrada | el campo `categoria` de `lexico_general.json` ya lo da para TODO el léxico (no solo "anou") — esto es lo que más impacto puede tener: resolvería de raíz el hueco que encontramos el 16/10 con "nou" en el IPD. |
| `canvi_genere_lexic_avl.json`, `flexio_genere_avl.json` | curados a mano | sin equivalente visto todavía en los 3 ficheros nuevos — **pendiente de confirmar si Mauricio los cubre en otra entrega o si se quedan como están** |

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
`numerals_mauricio.json` actual (176 entradas): **0 entradas ganadas, 99
perdidas** — todas formas ORDINALES ("cinquanta-huitena"→"cinquanta-vuitena",
"denovena"→"dinovena", "dessetena"→"dissetena"...). Donde coinciden, dicen
lo mismo (0 conflictos). El fichero nuevo solo cubre cardinales.

**Decisión del usuario (16/10/2026): dejarlo como pendiente, no bloquear
el resto de la migración por esto.** Se extrajeron las 99 entradas
faltantes a un fichero aparte, `pipeline/02_regles_dialectals/lexic/numerals_ordinals_pendent.json`
(mismo esquema que `numerals_mauricio.json`: `valenciano`/`catalan`/`revision`),
para no perder el dato mientras se decide qué hacer (¿Mauricio lo añade
en una próxima entrega? ¿se fusiona a mano con `lexico_general.json`?).
**No incorporado todavía a ningún loader** — es solo la pieza guardada,
la decisión de cómo encajarla queda abierta.

## 4ter. Fase 3 — léxico general: revisado a fondo, resultado positivo, 3 huecos documentados

Comparado `lexico_general.json` (categorías n/adj/adv/cnjadv/pr/ij) contra
`lexic_mauricio.json` actual, replicando la MISMA lógica de resolución
`canonica` que usa hoy `_resol_mauricio()` (no una comparación ingenua):

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
tancat)/"francès"(cat, obert), hoy en `lexic_acentuacio_mauricio.json`)
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
- `sync_data.py`: `lexic_mauricio.json` ahora sincroniza desde
  `diccionarios_v1/lexico_general.json` (antes `unificado.json`).
- `val_cat/lexic.py::_carrega_mauricio_lexic()`: filtra por
  `categoria in {n,adj,adv,cnjadv,pr,ij,prn}` (deja `num`/`det` a sus
  propios módulos).
- `_CANONICA_OVERRIDES = {"xicotet": "petit"}`: el bug de "xicotet"→"menut"
  (debería ser "petit", confirmado contra gplsi) sigue sin corregirse en
  la fuente — override explícito encima.
- `_BUG_DADES_CONEGUTS`: quitado "vesprada" (ya viene bien, "tarda"),
  añadidos **"alcalde"** (→"batlle", regresión real RC136, mismo patrón
  de registro que "qué"/"ensenyament") y **"tancada"** (→"closa",
  regresión real RC144 — Mauricio mismo lo marca `problema:
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

- Mismo filtro `categoria` en `_carrega_mauricio_lexic_invers()` y
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

## Resumen del estado tras hoy (16/10/2026)

Léxico general migrado y verificado en las dos direcciones:

| | val→cat (151) | val→cat (gplsi) | cat→val (151) | cat→val (gplsi) |
|---|---|---|---|---|
| Antes de migrar | 115/151 | 1281/1958 | 116/151 | 1212/1958 |
| Después de migrar | 115/151 | **1330/1958 (+49)** | 116/151 | **1267/1958 (+55)** |

Numerales (ordinales), posesivos y acentuación siguen con la fuente
vieja (huecos reales en la entrega nueva, documentados arriba).
Conjugaciones (`conjugaciones_general.json`/`verbos_diferentes_conjugados.json`)
sin empezar, bloqueadas hasta tener la explicación de `morfologia`.

## 5. Pendiente de la explicación prometida (NO adivinar mientras tanto)

`conjugaciones_general.json` trae 150 combinaciones distintas de
`morfologia`. Cuando es una lista simple (p.ej. `['pis','p2','pl']`) es
una forma sin ambigüedad; cuando es una LISTA DE LISTAS (p.ej.
`[['imp','p3','pl'], ['prs','p3','pl']]` o `[['n','m','sg'], ['prs','p1','sg']]`)
la forma tiene más de una lectura posible — potencialmente la misma
información que hoy calculamos nosotros mismos con
`es_risc_mode_3a_plural()` y el filtro de POS de spaCy (incluyendo el
caso "estat"/"recull" que dejamos aparcado ayer). **No descifrar los
códigos (`pis`, `pri`, `prs`, `imp`, `pp`, `inf`, `n`...) por prueba y
error** — el riesgo de interpretar mal justo la distinción indicativo/
subjuntivo es demasiado alto para adivinar; esperar la explicación
prometida antes de tocar `conjugacions_dict.py` o `es_risc_mode_3a_plural`.

## 6. Próximos pasos (fases ya acordadas con el usuario, sin empezar todavía)

1. ~~Fase 0 (parte estructural, sin depender de la explicación de morfologia)~~ — este documento.
2. Fase 1: construir loaders nuevos en paralelo, sin tocar los actuales.
3. Fase 2: comprobar una por una las decisiones ya validadas con evidencia (empezando por la de la sección 4) contra los datos nuevos.
4. Fase 3: migrar módulo a módulo (numerals primero, demostratius el último), doctests + benchmark 151 + gplsi en cada paso.
5. Fase 4: evaluar si `morfologia` sustituye `es_risc_mode_3a_plural`/filtro spaCy — **bloqueada hasta tener la explicación de los códigos**.
6. Fase 5: repuntar `sync_data.py` e `ipd.py`.
7. Fase 6: verificación final completa y limpieza (borrar JSON viejos, mover los 3 nuevos a `lexic/`, borrar `diccionarios_v1/`).
