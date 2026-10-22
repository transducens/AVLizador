*[Read it in Catalan](README.md)*

# Motor de diccionario determinista — etapa 5

Este paquete (`traductor/`) vive en la raíz del repositorio, sin el
prefijo numérico de las otras etapas (`01_...` a `04_...`), porque es un
paquete Python que se importa por el nombre (`import traductor`) desde
otras partes del código — un nombre de módulo no puede empezar por un
dígito en Python. Conceptualmente es la etapa 5 del proyecto.

**Dirección inversa (catalán→valenciano, en construcción desde el
08/10/2026)**: `from traductor import translate_cat_val` — ver
`traductor/rules/cat_val/README.es.md` y
`documentacio/hoja_de_ruta_traductor_invers.md` (raíz del repositorio)
para el estado, el alcance actual y el razonamiento completo. Esta
dirección original (`translate`, val→cat) se queda exactamente igual,
sin ningún cambio.

**22/10/2026 — `data/` solo tiene ya los dos ficheros del proveedor**
(`lexic_general.json` y `conjugacions_dialectals.json`, copias de
`diccionarios/` vía `sync_data.py`). Se retiraron los ficheros hechos a
mano, y lo que dice este README sobre ellos es histórico:
- `flexio_genere_avl.json` → nada: el léxico ya trae las formas de
  femenino y plural (y el fichero tapaba "xiques" con "xices").
- `canvi_genere_lexic_avl.json` → spaCy da el género de la palabra nueva
  y se corrige el determinante y el apóstrofo
  (`rules/pos_tagger.py::genere_tras_substitucio`).
- `categoria_gramatical_lexic.json` → los homógrafos los decide el propio
  léxico (`problema: "homonimia_lexica"`, `categoria`, `lemas`) con spaCy
  (`rules/__init__.py::carrega_homografs`, el mismo mecanismo que el IPD).
- `demostratius_avl.json` → `demostratius.py` lee las entradas
  `categoria: "det"` del léxico, igual que `possessius.py`.
Además, las entradas `_PENDENT` del léxico se usan como las demás (la
etiqueta es metadato del proveedor) y en `cat_val/lexic.py` ya no queda
ninguna lista a mano (ordinales, rentar/empentar); en `val_cat/lexic.py`
tampoco (`_LEXIC_PERDUT_RESTAURAT`, `_ORDINALS_PERDUTS`,
`_CANONICA_OVERRIDES`).

**Modelo de spaCy (22/10/2026)**: `ca_core_news_md` (`python -m spacy
download ca_core_news_md`); si no está, se usa `ca_core_news_sm`. Misma
velocidad, ~190 MB más de RAM, mejor género y morfología.

## Por qué existe esto

Las etapas 1-4 usan un LLM (qwen2.5:14b) con un system prompt de reglas +
glosario dinámico para generar el corpus sintético. Funciona
razonablemente bien (BLEU ~93 en el benchmark de 60 frases), pero la
revisión manual encontró un ~20% de errores reales frente al ~1,5% que
detectan las comprobaciones automáticas — la mayoría, alucinaciones del
modelo sin relación con ninguna regla dialectal (ver
`../documentacio/metodologia_i_resultats.md`, secciones 6 y 9).

Un motor de diccionario no puede alucinar: si una palabra no está en
ninguna tabla, sencillamente no la toca. Este paquete no sustituye al
LLM, pero es una base determinista, auditable y sin dependencias.

## DECISIÓN DE ARQUITECTURA (30/09/2026): puro lookup de diccionario + 2 sufijos productivos

Hasta el 29/09/2026 este paquete tenía 10 capas: lookup de diccionario
(léxico, conjugaciones) + reglas morfológicas y de sufijo generalizadas
(demostrativos, gentilicios, incoativos, pretérito perfecto, locuciones,
elisión). Esas reglas cubrían más casos, pero mezclaban datos de varias
fuentes (Apertium, Paula Guerrero, tablas escritas a mano) con la fuente
del proveedor de datos.

Ese mismo día, por la tarde, se redujo el traductor a **SOLO lookup exacto
de diccionario, y SOLO con datos de `pipeline/02_regles_dialectals/lexic/`**
(equipo AVLizador) — ninguna regla de sufijo, patrón morfológico ni
reconstrucción algorítmica, y ninguna fuente que no sea el proveedor de datos.

**Consecuencia, medida, no asumida**: el benchmark de 150 frases pasó de
**89/150 (59,3%)** con la arquitectura de 10 capas a **27/150 (18,0%)**
con la arquitectura pura de diccionario. La pérdida venía sobre todo de:
demostrativos (`este/eixe→aquest`, la conversión más frecuente del
corpus, sin fuente en el proveedor de datos), posesivos masculinos/tónicos (nunca
tuvieron regla, no cambian), el patrón general de gentilicios `-és→-ès`
(solo cubría las 695 palabras literales de acentuación, no cualquier
gentilicio), los incoativos `-ix→-eix` (solo los verbos concretos que ya
estaban en `conjugacions_dialectals.json`), y el pretérito perfecto
simple → perifrástico (`celebrà→va celebrar`, ningún diccionario da
formas perifrásticas).

**Ampliación (mismo día, más tarde)**: se confirmó que un puro diccionario
nunca puede cubrir un patrón ABIERTO y PRODUCTIVO -- por definición, un
diccionario solo contiene palabras que alguien ya ha metido ahí. Se
volvieron a añadir 2 reglas de sufijo (no listas cerradas) para los 3
patrones más productivos y mejor evidenciados: `accentuacio.py`
(`-és→-ès`, `-éixer→-èixer`) e `incoatius.py` (`-ix→-eix`). No se dio
marcha atrás en el resto todavía (pretérito perfecto, locuciones, elisión
automática general) -- ver "Cosas que ya no se cubren" en
`lexic/README.md`. Con esto el benchmark subió a **28/150
(18,7%)** -- una mejora pequeña porque la mayoría de los casos de estos 2
patrones ya estaban cubiertos por el diccionario de acentuación.

**Recreado el mismo día, aún más tarde**: `demostratius.py`
(`este/eixe/aqueix→aquest`, `açò→això`) -- la eliminación del 30/09/2026
había sido un error, no un patrón que "no hacía falta" como los demás: es
el paradigma gramatical MÁS FRECUENTE del corpus, y ningún diccionario
del proveedor de datos lo lista (es una lista cerrada, no léxico abierto). Con esto el
benchmark subió de golpe a **83/150 (55,3%)** -- el salto más grande de
todos los cambios de esta sesión, confirmando que los demostrativos eran
la pieza que más faltaba.

**Ampliación final del mismo día**: `flexio_genere_avl.json` (dentro de
`lexic.py`) añade derivación de género/número para un puñado curado de
palabras con variación real (`xiquet/xiqueta/xiquets/xiquetes→nen/nena/nens/nenes`).
Probado también el enfoque "escanear todo el léxico por patrón de
sufijo" -- descartado enseguida: la mayoría de palabras acabadas en
consonante "segura" son verbos/adverbios sin género, dando formas
absurdas ("cercar"→"cercara"). Con la lista curada, el benchmark subió a
**92/150 (61,3%)**.

Esta cifra se deja aquí a propósito, sin suavizarla: es la consecuencia
directa y conocida de la decisión, no un bug.

## DECISIÓN DE ARQUITECTURA (01/10/2026): concordancia `dos→dues`, primera capa (artículo/demostrativo)

Pérdida ya documentada desde el 30/09/2026 (ver docstring de
`numerals.py`): la concordancia de género `dos/dues` se había quitado al
pasar a puro lookup de diccionario, porque "dos"/"dues" se escriben igual
en ambos dialectos (no es una sustitución léxica del proveedor de datos) -- el motor
simplemente no corregía el desacuerdo cuando el valenciano coloquial usa
"dos" invariable delante de un nombre femenino ("tinc dos germanes" en
vez de "dues germanes").

**Análisis previo a implementar nada** (evidencia, no teoría): se
revisaron los 150 casos del benchmark buscando todas las frases con
"dos"/"dues" para ver qué señal distingue los casos reales. De ~28 frases
con "dos→dues" real, **13 iban precedidas directamente por un artículo o
demostrativo que ya marca femenino plural por sí mismo** (`les`, `estes`,
`eixes`, `aqueixes`): "**les** dos institucions"→dues, "**estes** dos
circumstàncies"→dues. El resto eran casos "pelados" sin marcador delante
("dos entitats", "dos terceres parts"), donde solo el sufijo de la
palabra siguiente (-tat, -ció, -a) delata el género -- y un caso ("dos
consonants") no tiene ninguna marca formal, solo se puede saber de
memoria.

**Decisión**: implementar SOLO la primera capa (marcador delante), en un
fichero aparte (`concordanca_dos_dues.py`) para tenerla controlada por
separado, y dejar la capa de sufijo pendiente a propósito hasta medir el
impacto de esta primera -- mismo criterio que `flexio_genere_avl.json`:
preferir una señal segura y acotada antes que una heurística más amplia
con más riesgo de falsos positivos. Los casos puramente léxicos
("consonants") se dejan fuera a propósito, para una futura lista curada a
mano si algún día dan problemas reales -- nunca con una regla general de
género sobre todo el léxico (mismo motivo por el que se descartó el
escaneo automático en `flexio_genere_avl.json`).

**Riesgo aceptado conscientemente**: el propio benchmark es inconsistente
en 2 casos (citas de registro antiguo/dialectal) donde la referencia deja
"dos" sin corregir a propósito. La regla lo corrige igualmente -- se
prioriza la corrección gramatical real sobre esas 2 coincidencias
concretas.

**Resultado, medido**: el benchmark subió de **99/150 (66,0%)** a
**111/150 (74,0%)** -- el cambio individual más grande desde la
recreación de los demostrativos.

## DECISIÓN DE ARQUITECTURA (02/10/2026): relativo locativo "a on"→"on", y 3 reglas descartadas por falta de evidencia

Mismo método que la decisión anterior, aplicado ahora a partir de
`docs_gramatica/` (las gramáticas GEIEC/GNV completas y sus guías
derivadas, ver `pipeline/02_regles_dialectals/docs_gramatica/README.md`): cada
diferencia que documentan las guías se contrasta contra el benchmark de
150 frases ANTES de escribir ninguna regla, porque una diferencia real
sobre el papel no siempre aparece lo bastante a menudo -- ni con
suficiente seguridad -- como para merecer una regla.

**4 candidatos evaluados, 1 implementado:**

- ✅ **"a on" → "on"** (relativo/interrogativo locativo): 9 apariciones
  reales en el benchmark, **las 9 el mismo patrón, cero excepciones**.
  Implementado en `relatiu_on.py`. Incluye el caso especial "d'a on" →
  "d'on" (prefijo elidido pegado a la "a"), encontrado en 1 de los 9
  casos durante la revisión.
- ❌ **"lo/los" como pronombre débil proclítico**: 2 apariciones, ambas
  falsos positivos (enclíticos detrás de verbo, `saber-lo`/
  `segmentant-los`, idénticos en ambos dialectos -- no tiene nada que ver
  con el "lo" que documentan las gramáticas). Cero evidencia real, no
  implementado.
- ❌ **"per" → "per a"** (finalidad): solo 2 casos reales de 28
  apariciones de "per"/"per a" en el benchmark, y el resto de la
  diferencia depende de si "per" tiene valor de causa o de finalidad --
  distinción sintáctica real, no un patrón de superficie seguro de
  automatizar. Mismo tipo de riesgo que se descartó con el escaneo
  automático de género. No implementado.
- ❌ **"ací" → "aquí"**: solo 1 aparición en el benchmark, y en ese caso
  concreto la referencia deja "ací" **sin cambiar** -- contradice la
  teoría de la gramática con el único dato real disponible. No
  implementado hasta que haya más evidencia real.

**Resultado, medido**: el benchmark subió de **111/150 (74,0%)** a
**119/150 (79,3%)**.

## DECISIÓN DE ARQUITECTURA (05/10/2026): nuevo léxico unificado, y conjugaciones masivas probadas y revertidas

El proveedor de datos compartió 3 ficheros nuevos en `lexic/`. Cada uno se
evaluó por separado antes de integrarlo (mismo método de siempre:
comparar contra los datos existentes y el benchmark, no confiar a ciegas
en un volumen grande de datos nuevos).

**`unificado.json` → sustituye a `lexico_general_limpio.json` (integrado)**:
casi un superconjunto (610 de las 611 entradas antiguas están, +860
nuevas). Introdujo 2 regresiones puntuales al integrarlo, las dos
corregidas:
- `eixa→aqueixa`: la entrada nueva es técnicamente válida pero ignora la
  decisión ya tomada de colapsar este/eixe/aqueix hacia "aquest" --
  `lexic.py` ahora excluye de `lexic_general.json` cualquier forma que
  ya cubra `demostratius.py` con autoridad propia.
- `"después"` reaparecía (bug de datos ya conocido, ver `lexic.py`) por
  una vía distinta a la original -- la exclusión `_BUG_DADES_CONEGUTS`
  ahora se aplica a los dos loaders (léxico general y acentuación), no
  solo uno.

**`conjugaciones_nuevo.json` (5.465 verbos, 49.443 formas, generadas
sistemáticamente) → PROBADO Y REVERTIDO**: no es un problema de
ambigüedad puntual como las 65 formas ya conocidas (indicativo/subjuntivo
que colapsan) -- es **colisión homógrafa masiva**. Con tantos verbos,
muchas conjugaciones regulares coinciden con sustantivos plurales mucho
más frecuentes que el verbo raro que las origina: `persones→personis`
(del verbo "personar"), `projectes→projectis` ("projectar"),
`pobles→poblis` ("poblar"). Medido con el benchmark: **119/150 (79,3%)**
antes, **89/150 (59,3%)** con esta fuente integrada -- 30 regresiones
reales, palabras comunes convertidas en no-palabras. Una lista de
exclusiones curada no lo arregla (harían falta miles); es un problema
estructural de no tener pos-tagging a esa escala. Se probó también
`verbos_todos_anotados.json` (1.229 formas, análisis de ambigüedad en 50
verbos con formas repetidas) -- demasiado acotado para resolver el
problema general, se deja pendiente para un análisis puntual futuro.

De paso, un tercer bug encontrado por la misma vía (homógrafo, no de las
fuentes nuevas): `conjugacions_dict.py` tenía `germanes` (sustantivo,
"hermanas") colisionando con la 2ª persona subjuntivo del verbo
"germanar" -- ahora excluido explícitamente (`EXCLUSIONS_HOMOGRAF`).

**Resultado neto**: léxico ampliado (+860 entradas), 2 regresiones nuevas
corregidas, y una fuente grande descartada con evidencia clara en vez de
integrarla a ciegas porque "son más datos".

## DECISIÓN DE ARQUITECTURA (06/10/2026): `conjugaciones_nuevo.json` re-integrado a propósito, aceptando la bajada del benchmark

Decisión explícita del usuario: volver a añadir `conjugaciones_nuevo.json`
(los 5.465 verbos revertidos un día antes) aunque se sepa que vuelve a
introducir la colisión homógrafa documentada arriba. Razonamiento: ahora
no preocupa tanto la cifra del benchmark porque **el plan es añadir más
adelante un paso de postprocesado con un LLM**
(`pipeline/08_traduccio_corpus/postprocessat_llm/`, todavía NO implementado) que
pueda resolver estos casos ambiguos mirando el contexto real de la frase
-- algo que un lookup plano nunca puede hacer. Mientras no exista ese
paso, se prefiere tener más cobertura (5.465 verbos más) aunque salga más
ruido, en vez de esperar con el motor limitado a 156 verbos.

**Cambio concreto**: `sync_data.py` vuelve a incluir
`conjugaciones_nuevo.json` en la tupla de fuentes de
`conjugacions_dialectals.json`, ahora en ÚLTIMO lugar (antes de
`verbos_no_ambiguos.json` y `conjugaciones_limpio.json`, que ganan en
caso de conflicto por ser más fiables y cubrir verbos más comunes).

**Resultado, medido de nuevo**: el benchmark vuelve a bajar de **119/150
(79,3%)** a **89/150 (59,3%)**, BLEU 95,31 -- exactamente la misma cifra
que la prueba descartada el día anterior, confirmando que el problema es
reproducible y no depende del orden de integración. Esta bajada queda
documentada y aceptada a propósito, no es una regresión sin detectar.

**Pendiente, NO hecho en esta decisión** (a propósito, por alcance): no
se ha implementado ningún postprocesado LLM todavía -- eso se irá
haciendo poco a poco en próximas sesiones. Tampoco se ha integrado
`verbos_todos_anotados.json` -- ver nota importante abajo, tiene un
problema DISTINTO (no de colisión, sino de datos corruptos) que había
que detectar y reportar antes de añadirlo.

### `verbos_todos_anotados.json` -- integrado sin filtrar (06/10/2026, corrección de una alarma previa)

Al revisar si convenía añadir `verbos_todos_anotados.json` (1.229 formas,
análisis detallado de 50 verbos con formas repetidas) se detectó un caso
que parecía preocupante: 8 de los 50 verbos tienen un infinitivo de MÁS
DE UNA PALABRA ("fer una ullada", "telefonar"→"trucar per telèfon"...), y
uno de ellos ("fer una ullada" / "donar un cop d'ull") aparecía con la
forma catalana concatenada sin espacios: la forma limpia y común
**"faria"** (condicional de "fer") asociada a la no-palabra
**"uncopd'ulldonaria"**. Primera alarma: como parecía no tener ambigüedad
interna detectable, se pensó que nada lo protegería y rompería "faria"
siempre.

**Verificado después (y corregido aquí)**: esa alarma estaba mal
calculada. Dentro de este mismo fichero, "faria" aparece DOS veces con
catalanes distintos ("faria" limpio, del idioma "fer una besada"/"fer un
petó"; y "uncopd'ulldonaria" roto, de "fer una ullada"/"donar un cop
d'ull") -- exactamente el patrón que `_marca_ambigues_dins_del_mateix_fitxer`
ya detecta y marca `problematica: true` (verificado: ambas entradas
quedan excluidas del lookup). Revisando el resto de las 227 formas
afectadas por los 8 verbos multi-palabra: la mayoría (telefonar→trucar,
pegar un bac→clavar una patacada, parar atenció→parar esment, armar un
canyaret→armar un sidral, caure com una punyada→caure com un cop de
puny) son formas LIMPIAS y correctas -- el verbo núcleo del idioma se
conjuga bien en los dos lados, y solo la parte no-verbal de "fer una
ullada"/"donar un cop d'ull" produce concatenaciones, que ya quedan
excluidas por el mecanismo existente. **Decisión: integrado sin ningún
filtro adicional** (475 de las 1.229 formas acaban marcadas
`problematica` por el mecanismo ya existente; el resto se añade al
lookup tal cual). No ha cambiado el resultado del benchmark (sigue en
89/150) porque ninguno de estos 50 verbos aparece ahí, pero quedan
disponibles para el corpus real.

## DECISIÓN DE ARQUITECTURA (07/10/2026): filtro POS opcional (spaCy) dentro de `ConjugacionsDictRule`

Se pensaba innecesario por intuición (el motor funciona sin spaCy desde
el principio), pero medido contra el benchmark resultó SÍ hacer falta:
formas verbales raras de `conjugacions_dialectals.json` coincidían con
palabras MUY frecuentes de otra categoría gramatical ("persones" →
"personis" del verbo "personar", "pares" → "paris" de "parar",
"projectes" → "projectis" de "projectar", "pobles" → "poblis" de
"poblar"). Ninguno de estos casos lo detecta
`_marca_ambigues_dins_del_mateix_fitxer` porque cada uno solo tiene una
entrada en su fichero fuente — la colisión es con una palabra de OTRA
categoría que ningún diccionario diferencial lista (los diccionarios
del proveedor de datos son diferenciales: solo listan pares que cambian, nunca
palabras que se quedan igual). Confirmado con spaCy (`ca_core_news_sm`):
etiqueta correctamente estos 5 casos como NOUN en su frase real, sin
romper ningún caso ya conocido. **Resultado, medido**: 89/151 (58,9%) →
**99/151 (65,6%)**, BLEU 95,97, chrF 98,61.

## Análisis de fallos residuales (07/10/2026) — resumen

Con el filtro POS ya aplicado, el benchmark subió a 100/151 (66,2%)
tras una corrección adicional. Categorización completa de los 51 fallos
restantes (detalle caso por caso, con cada identificador RC, en la
versión catalana de este documento):

- **Colisión de modo/tiempo verbal en personas distintas de 1ª
  singular** (24 de 51, la categoría más grande): mismo mecanismo que
  arriba, pero en 3ª persona plural — aquí el filtro POS no sirve porque
  las dos candidatas ya son VERBO para spaCy. Aparcado explícitamente:
  haría falta una lista evidenciada caso a caso, como ya existe para 1ª
  persona.
- **Ambigüedad 1ª persona singular indicativo/subjuntivo** (4 frases,
  residual esperado, no es un bug): es exactamente el fenómeno que
  `pipeline/08_traduccio_corpus/postprocessat_llm/` ataca con
  postprocesado LLM — el motor, por diseño, deja estas formas sin tocar.
- **Concordancia "dos"/"dues" incompleta** (resuelta en gran parte,
  08/10/2026): añadida una segunda capa con `Token.gender` (spaCy) sobre
  el sustantivo/adjetivo siguiente cuando no hay marcador explícito
  delante. +3 frases exactas.
- **Preposición "en"/"a"** (resuelta el 08/10/2026, **retirada del todo
  el 14/10/2026** — ver "Actualización 13-14/10/2026" más abajo): 5
  entradas exactas en una lista cerrada que, medido después con más
  rigor, no generalizaba a ninguna frase nueva.
- **Concordancia de género tras sustitución léxica** (resuelta,
  08/10/2026): +1 frase exacta.
- **Huecos léxicos/morfológicos puntuales sin patrón común**: aparcados
  explícitamente, incluye artefactos puros del corpus (doble espacio,
  ortografía arcaica citada literalmente).
- **Hallazgo nuevo**: "o siga" (RC067) se protegía a propósito como
  locución fija, pero la referencia SÍ la traduce a "o sigui" en ese
  caso concreto — contradicción entre el criterio conservador aplicado
  y el corpus real. **Arreglado el 13/10/2026** (ver abajo): la
  protección asumía que era una locución CONGELADA idéntica en los dos
  dialectos — falso, medido contra el único caso real. Protección
  retirada, 119→120/151.

## Actualización (13-14/10/2026): "o siga" arreglado, `preposicions_locucions.py` retirada, vía C en producción

Resumen de lo ocurrido desde el análisis de fallos de arriba
(07/10/2026) hasta hoy — detalle completo de cada punto en
`documentacio/metodologia_i_resultats.md`, secciones 11-17.

**14/10/2026, `preposicions_locucions.py` retirada del todo**: a
petición del usuario ("eso no es un traductor, solo hace que funcione
nuestro benchmark"), se investigó si la regla C1 de
`pipeline/02_regles_dialectals/docs_gramatica/guia_traduccio_dialectal.md`
("en"+artículo definido en valenciano ↔ "a"+artículo definido en catalán,
fuente normativa GEIEC/GNV) podía sustituir las 5 entradas exactas por
una regla de verdad general. Implementada sin excepciones y medida
contra los dos benchmarks disponibles (el de 151 y el dataset público
`gplsi`, 1.958 frases): **regresión grave en las dos direcciones**
(120→76/151, 123→107/151) — en registro formal, "en + artículo" se usa
sobre todo en sentido ABSTRACTO ("en el Congrés", "en el model
lingüístic"), no de lugar físico, y la regla no puede distinguir los dos
sentidos sin entender el significado. Revertido, y medido limpio antes
de descartarlo del todo: de 136 frases reales con "en + artículo" en
valenciano (53 del benchmark + 83 de gplsi), solo 2 (1,5%) convierten de
verdad a "a" en el catalán de referencia — el fenómeno normativo es real
pero casi no se manifiesta en este registro. Se retira el módulo entero,
sin dejar ninguna regla de reemplazo: **120→115/151**, 536/536 doctests.

**La dirección inversa (`cat_val/`) y la vía C (postprocesado LLM) ya
existen y están maduras**, pero no se documentan en detalle en este
fichero porque tienen su propio README (`rules/cat_val/README.md`) y su
propia carpeta
(`pipeline/08_traduccio_corpus/postprocessat_llm/`) respectivamente. En
resumen: `cat_val/` es una estructura simétrica completa (116/151 hoy), y
la vía C (clasificar entre 2 candidatos ya conocidos, nunca generar
texto nuevo) es el mecanismo que da el récord **129/151 (85,4%)
motor+LLM con `qwen3:8b`**, confirmado en Abaco — cifra anterior a la
limpieza de hoy, pendiente de reconfirmar.

**Índice de Pureza Dialectal**: métrica nueva e independiente
(`pipeline/09_index_puresa_dialectal/ipd.py`) que reutiliza el mismo
índice de diccionario que este motor, pero para medir pureza dialectal
de cualquier texto, no para traducir. No toca ni depende de ningún
fichero de esta carpeta.

**Reestructuración del repositorio (14/10/2026)**: las carpetas
numeradas mencionadas en esta documentación (`02_regles_dialectals/`,
`03_seleccio_de_model/`, etc.) viven ahora dentro de `pipeline/` — las
rutas de este README ya están actualizadas, pero cualquier ruta vista en
capturas o logs antiguos sin ese prefijo es de antes de esta fecha.

## Arquitectura

Pipeline secuencial de capas sobre una lista de `Token`, no sustituciones
de texto sobre la frase entera:

```
texto ──tokenize()──▶ [Token, Token, ...] ──marca_noms_propis()──▶
    ──▶ LexicRule ──▶ ConjugacionsDictRule ──▶ PossessiusRule ──▶ NumeralsRule
    ──▶ ConcordancaDosDuesRule ──▶ RelatiuOnRule ──▶ DemostratiusRule
    ──▶ AccentuacioRule ──▶ IncoatiusRule ──▶ detokenize() ──▶ texto convertido
```

### `Token` (`rules/__init__.py`)

```python
@dataclass
class Token:
    surface: str          # forma original, nunca cambia
    translated: str        # se va sobrescribiendo capa a capa
    pos: str = ""           # etiqueta gramatical; "" si no hay spaCy (opcional, no instalado)
    is_translated: bool = False
    is_proper_noun: bool = False
    start: int = 0
```

`detokenize()` simplemente concatena `translated` de todos los tokens en
orden — como los espacios y la puntuación también son tokens (con
`translated == surface` mientras ninguna regla los toque), el texto se
reconstruye exacto sin lógica de reinserción de espacios.

### Por qué un flag por token y no regex sobre el texto entero

Cada capa marca `is_translated = True` en el momento en que toca un
token, y todas las capas posteriores respetan ese flag (`if
tok.is_translated: continue`). Con 9 capas independientes, esto evita que
dos fuentes se pisen sin que nadie se dé cuenta — la primera capa que
reconoce una palabra se queda el mérito, el resto la salta.

### Decisión de diseño: apóstrofos y guiones son parte de la palabra

`tokenize()` trata `d'escola`, `l'AVL` o `dir-li` como **un solo token**
cada uno, no como palabra+frontera. Consecuencia: un token como `d'este`
nunca coincide con la entrada `"este"` de un diccionario.
`separa_prefix_elidit()` (`rules/__init__.py`) es el arreglo -- `lexic.py`
y `conjugacions_dict.py` (las únicas 2 capas donde el prefijo puede
cambiar de sentido según la palabra encontrada) lo usan como segundo
intento cuando la búsqueda directa falla: separa el prefijo elidido
(`d'`, `l'`, `s'`, `m'`, `t'`, `n'`) y vuelve a buscar solo la parte real
de la palabra.

**Bug real encontrado y arreglado (30/09/2026)**: reconstruir siempre
`prefijo + forma_encontrada` no basta -- si la palabra encontrada cambia
de vocal inicial a consonante inicial (p.ej. "eixir"→"sortir"), la
elisión original ya no tiene sentido: "a l'eixir" daba el incorrecto "a
l'sortir" en vez de "al sortir". `aplica_amb_prefix_elidit()`
(`rules/__init__.py`) lo gestiona: si la forma encontrada ya no empieza
en vocal/h muda, DESHACE la elisión (vuelve el prefijo a su forma
completa: "l'"→"el", "d'"→"de"...) y, si el resultado es "el" y el token
anterior es la preposición "a"/"de", los contrae ("a"+"el"→"al",
"de"+"el"→"del") en vez de dejar "a el".

### Protección de nombres propios (`marca_noms_propis`)

Se ejecuta una sola vez, antes de la primera regla: marca
`is_proper_noun` en toda palabra capitalizada que **no** sea la primera
del texto (la primera letra de una frase siempre va en mayúscula, sea o
no nombre propio). Es la misma heurística ya probada en
`pipeline/03_seleccio_de_model/evalua_models.py::glossari_per_frase()`, añadida
allí tras un incidente real con `blanca`/`Blanca` y `roig`/`Roig` (ver
`../documentacio/metodologia_i_resultats.md`, sección 6). Límite
conocido, heredado sin arreglar: un nombre propio que es la **primera**
palabra del texto nunca se detecta.

## Las 9 capas

- **`lexic.py`** — lookup de léxico general + acentuación + género/número.
  Fusiona `flexio_genere_avl.json` (prioridad máxima, ver abajo),
  `lexic_general.json` (copia de `lexico_general_limpio.json`, filtrado:
  excluye `_PENDENT`, topónimos, multi-palabra, resuelve `canonica`) y
  `lexic_acentuacio_general.json` (copia de `acentuacion_limpio.json`,
  695 parejas). Excluye a mano "después" (bug de datos confirmado en el
  fichero fuente: lo lista como si siguiera el patrón de acentuación,
  pero no cambia nunca en ninguno de los dos dialectos).
  **Género/número (`flexio_genere_avl.json`, añadido 30/09/2026)**: lista
  CURADA a mano (no escaneo automático de todo el léxico -- se probó y la
  mayoría de palabras acabadas en consonante "segura" eran verbos/adverbios
  sin género, dando formas absurdas como "cercara"). Dos categorías:
  `regulars` (deriva fem/plural automáticamente: `xiquet→nen` da también
  `xiqueta→nena`, `xiquets→nens`, `xiquetes→nenes`) e `irregulars`
  (formas exactas para cuando el patrón "+a" no vale, como `menut→menuda`
  -- irregularidad participial que no se puede generalizar con seguridad,
  ya que "petit" acaba igual pero es regular: "petita", no "petida"). De
  paso resuelve la regresión que había con "xiquet" (antes ganaba "noi"
  por ambigüedad en el proveedor de datos sin fuente externa que desempatara).
- **`conjugacions_dict.py`** — lookup de formas verbales. Fusiona
  `conjugaciones_limpio.json` (969 formas, 111 verbos) y
  `verbos_no_ambiguos.json` (261 formas más, 45 verbos, añadido
  30/09/2026, todas marcadas `ambigu: false`) en
  `conjugacions_dialectals.json`. Excluye las formas `problematica: true`
  (ambiguas indicativo/subjuntivo sin pos-tagging) -- solo "haja"/"hagen"
  se quedan sin traducir por esto (toda la conjugación de "haver" es
  `problematica`). Protege "o siga" (locución fija "és a dir") para que
  no se confunda con el verbo "ser" en subjuntivo.
- **`possessius.py`** — lookup de posesivos débiles femeninos
  (`meua/teua/seua` + plurales → `meva/teva/seva`). Fuente:
  `possessius_general.json` (copia de `posesivos_cat_val.json`), un
  producto cartesiano sin filtrar del que solo se quedan los 6 pares
  donde el número (singular/plural) casa a ambos lados.
- **`demostratius.py`** — lookup de demostrativos: `este/eixe/aqueix`
  (los tres colapsan hacia `aquest`, misma familia + plurales) y el
  neutro `açò→això`. **Recreado 30/09/2026** (se había quitado del todo
  al pasar a "puro diccionario del proveedor de datos" y fue un error: ningún
  diccionario puede cubrir un paradigma gramatical cerrado que el proveedor
  de datos no lista). Fuente: `demostratius_avl.json` (paradigma sourced de
  `regles_dialectals_amb_evidencia.md` §1). `aquell`/`allò` son
  idénticos en ambos dialectos y no tienen entrada. La tabla INVERSA
  (`aqueix→eixe`, para un hipotético traductor oriental→occidental) se
  queda documentada en el mismo fichero sin implementarse -- este motor
  solo traduce en un sentido.
- **`numerals.py`** — lookup exacto contra `numerals_general.json`
  (copia de `numerales_limpio.json`, 180 filas): toda la familia
  huit/vuit, "dinou"/"disset" + derivados, y "díhuit"→"divuit" sin ningún
  caso especial (es lookup exacto, no sustitución de subcadena). Excluye
  4 filas de "vuitavat" que parecen una extracción rota en el fichero
  fuente (mismo catalán repetido para 4 valencianos distintos).
- **`concordanca_dos_dues.py`** — regla de CONCORDANCIA (añadida
  01/10/2026, ver "DECISIÓN DE ARQUITECTURA"): corrige `dos→dues` cuando
  el token inmediatamente anterior es `les`/`estes`/`eixes`/`aqueixes`/
  `aquelles`/`unes` (marcador de femenino plural inequívoco, nunca un
  diccionario). No lee ningún fichero de datos -- la lista de marcadores
  es una constante pequeña y cerrada en el mismo módulo. NO cubre casos
  "pelados" sin marcador delante (`dos entitats`) ni casos puramente
  léxicos (`dos consonants`) -- ver la decisión para el porqué.
- **`relatiu_on.py`** — regla de PATRÓN (añadida 02/10/2026, ver
  "DECISIÓN DE ARQUITECTURA"): corrige `a on→on` como relativo/
  interrogativo locativo. Gestiona el caso del prefijo elidido pegado
  (`d'a on→d'on`). Fuente de la evidencia: `docs_gramatica/` (GEIEC/GNV
  completas), contrastado contra el benchmark antes de implementar -- 3
  otras diferencias de estas gramáticas se descartaron por falta de
  evidencia real, ver la decisión.
- **`accentuacio.py`** — 2 reglas de SUFIJO productivas (añadidas
  30/09/2026, tarde, ver "DECISIÓN DE ARQUITECTURA"): `-és→-ès`
  (`francés→francès`, mismo patrón que 695 palabras literales de
  `lexic_acentuacio_general.json` pero ahora generalizado a CUALQUIER
  palabra) y `-éixer→-èixer` (`conéixer→conèixer`). Excepciones del
  primer patrón (`és`/`més`, y 7 más encontradas empíricamente: `només`,
  `després`, `procés`, `congrés`, `accés`, `progrés`, `través`): set de
  Python, no fichero -- ningún diccionario diferencial puede confirmar
  que una palabra NO cambia.
- **`incoatius.py`** — regla de SUFIJO productiva `-ix→-eix`
  (`establix→estableix`, añadida 30/09/2026), con dos protecciones: nunca
  toca palabras que ya acaban en "-eix" (`aparéixer`, `mateix`...) y lista
  negra de palabras reales acabadas en consonante+ix que no son verbos
  (`baix`, `calaix`, `dibuix`, `guix`, `fix`, `prefix`, `sufix`).

## Mantener `traductor/data/` sincronizado con las fuentes

`traductor/rules/*.py` nunca lee `pipeline/02_regles_dialectals/lexic/` en
tiempo de ejecución -- solo lee copias propias dentro de `traductor/data/`
(para que el paquete funcione de forma autónoma). Si editas un fichero
fuente de `lexic/` directamente, ese cambio no llega al motor
hasta que sincronizas:

```bash
python -m traductor.sync_data --check   # solo muestra qué ha cambiado, no escribe nada
python -m traductor.sync_data           # sincroniza de verdad y muestra el mismo resumen
```

El resumen dice exactamente qué entradas se han añadido/quitado por
fichero (no sobrescribe en silencio). Los filtros de negocio (descartar
`_PENDENT`, topónimos, la excepción de "después"...) NO viven aquí --
viven en los loaders de cada regla (`lexic.py`, `numerals.py`...) y se
aplican solos la próxima vez que se instancie `RuleEngine`, así que
después de sincronizar solo hace falta volver a correr el benchmark
(sección siguiente) para confirmar que no hay regresión.

## Cómo añadir datos nuevos

**Caso 1 -- una palabra o forma concreta (la mayoría de los casos)**: no
hace falta tocar ningún `.py`, es lookup de diccionario.

1. Edita el fichero fuente que toque (`lexico_general_limpio.json`,
   `conjugaciones_limpio.json`, `verbos_no_ambiguos.json`,
   `numerales_limpio.json`, `acentuacion_limpio.json`,
   `posesivos_cat_val.json`) directamente en `lexic/`.
2. Corre `python -m traductor.sync_data` (ver arriba).
3. Corre el benchmark (sección siguiente) para confirmar que no hay
   regresión.
4. Si una palabra concreta resulta ser un error del fichero fuente (como
   "después", ver `lexic.py`), documenta la exclusión en el loader
   correspondiente con un comentario claro -- no la "arregles" editando
   el fichero fuente a mano sin dejar rastro.

**Caso 2 -- un patrón de sufijo genuinamente PRODUCTIVO** (como
`accentuacio.py`/`incoatius.py`, ver "DECISIÓN DE ARQUITECTURA"): esto sí
es una regla nueva, no una entrada de diccionario -- pero solo cuando un
diccionario no puede cubrirlo por definición (el patrón aplica a palabras
que NUNCA estarán todas enumeradas). Confirma primero con evidencia real
(benchmark, no teoría) qué excepciones hacen falta, y crea
`traductor/rules/nombre_regla.py` con la misma interfaz que el resto
(`apply(tokens) -> tokens`, saltando `is_translated`/`is_proper_noun`).
Regístrala en `RuleEngine.__init__` DESPUÉS de las 4 capas de diccionario
(ver `engine.py`), porque una forma ya conocida con exactitud no debe
dejarse reprocesar por una regla más débil.

## Relación con el sistema de reglas antiguo

`pipeline/03_seleccio_de_model/evalua_models.py` ya tenía un sistema de reglas
(`tradueix_regles`, opción `--model regles`) — sustituciones con regex
sobre la frase completa. Es distinto y **no se ha tocado ni sustituido**:
el paquete `traductor/` se añade como una opción nueva,
`--model traductor`, para poder comparar los dos directamente en el mismo
benchmark:

```bash
cd pipeline/03_seleccio_de_model
python evalua_models.py --model traductor                    # motor nuevo (traductor/)
python evalua_models.py --model regles                       # sistema antiguo (regex)
python evalua_models.py --model tots                          # todo a la vez, incluidos ambos
```

El adaptador (`tradueix_traductor_nou` en `evalua_models.py`) añade la
raíz del repositorio a `sys.path` antes de importar `traductor/`, porque
el script siempre se ejecuta desde dentro de `pipeline/03_seleccio_de_model/` y
Python no encuentra ahí un paquete que vive en la carpeta de al lado.

## Uso directo

```bash
python -m traductor.cli "Tinc huitanta anys i el meu amic francés parla."
# -> Tinc vuitanta anys i el meu amic francès parla.
```

```python
from traductor import translate
translate("Tinc huitanta anys.")  # -> "Tinc vuitanta anys."
```

## Testing

No hay una carpeta `tests/` — cada regla lleva sus propios doctests
reales (no solo ejemplos ilustrativos) en el docstring de su clase, y se
verifican con `doctest.testmod()`, no a ojo. Para correr los de todo el
paquete de una vez:

```bash
python -c "
import doctest, importlib
modulos = [
    'traductor.rules', 'traductor.rules.lexic', 'traductor.rules.conjugacions_dict',
    'traductor.rules.possessius', 'traductor.rules.numerals', 'traductor.rules.concordanca_dos_dues',
    'traductor.rules.relatiu_on', 'traductor.rules.demostratius', 'traductor.rules.accentuacio',
    'traductor.rules.incoatius', 'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
