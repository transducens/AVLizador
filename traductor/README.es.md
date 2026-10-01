*[Read it in Catalan](README.md)*

# Motor de diccionario determinista — etapa 5

Este paquete (`traductor/`) vive en la raíz del repositorio, sin el
prefijo numérico de las otras etapas (`01_...` a `04_...`), porque es un
paquete Python que se importa por el nombre (`import traductor`) desde
otras partes del código — un nombre de módulo no puede empezar por un
dígito en Python. Conceptualmente es la etapa 5 del proyecto.

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
de Mauricio.

Ese mismo día, por la tarde, se redujo el traductor a **SOLO lookup exacto
de diccionario, y SOLO con datos de `02_regles_dialectals/lexic/font_mauricio/`**
(equipo AVLizador) — ninguna regla de sufijo, patrón morfológico ni
reconstrucción algorítmica, y ninguna fuente que no sea Mauricio.

**Consecuencia, medida, no asumida**: el benchmark de 150 frases pasó de
**89/150 (59,3%)** con la arquitectura de 10 capas a **27/150 (18,0%)**
con la arquitectura pura de diccionario. La pérdida venía sobre todo de:
demostrativos (`este/eixe→aquest`, la conversión más frecuente del
corpus, sin fuente en Mauricio), posesivos masculinos/tónicos (nunca
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
`font_mauricio/README.md`. Con esto el benchmark subió a **28/150
(18,7%)** -- una mejora pequeña porque la mayoría de los casos de estos 2
patrones ya estaban cubiertos por el diccionario de acentuación.

**Recreado el mismo día, aún más tarde**: `demostratius.py`
(`este/eixe/aqueix→aquest`, `açò→això`) -- la eliminación del 30/09/2026
había sido un error, no un patrón que "no hacía falta" como los demás: es
el paradigma gramatical MÁS FRECUENTE del corpus, y ningún diccionario de
Mauricio lo lista (es una lista cerrada, no léxico abierto). Con esto el
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

## Arquitectura

Pipeline secuencial de capas sobre una lista de `Token`, no sustituciones
de texto sobre la frase entera:

```
texto ──tokenize()──▶ [Token, Token, ...] ──marca_noms_propis()──▶
    ──▶ LexicRule ──▶ ConjugacionsDictRule ──▶ PossessiusRule ──▶ NumeralsRule
    ──▶ DemostratiusRule ──▶ AccentuacioRule ──▶ IncoatiusRule ──▶ detokenize() ──▶ texto convertido
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
tok.is_translated: continue`). Con 6 capas independientes, esto evita que
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
`03_seleccio_de_model/evalua_models.py::glossari_per_frase()`, añadida
allí tras un incidente real con `blanca`/`Blanca` y `roig`/`Roig` (ver
`../documentacio/metodologia_i_resultats.md`, sección 6). Límite
conocido, heredado sin arreglar: un nombre propio que es la **primera**
palabra del texto nunca se detecta.

## Las 7 capas

- **`lexic.py`** — lookup de léxico general + acentuación + género/número.
  Fusiona `flexio_genere_avl.json` (prioridad máxima, ver abajo),
  `lexic_mauricio.json` (copia de `lexico_general_limpio.json`, filtrado:
  excluye `_PENDENT`, topónimos, multi-palabra, resuelve `canonica`) y
  `lexic_acentuacio_mauricio.json` (copia de `acentuacion_limpio.json`,
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
  por ambigüedad en Mauricio sin fuente externa que desempatara).
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
  `possessius_mauricio.json` (copia de `posesivos_cat_val.json`), un
  producto cartesiano sin filtrar del que solo se quedan los 6 pares
  donde el número (singular/plural) casa a ambos lados.
- **`demostratius.py`** — lookup de demostrativos: `este/eixe/aqueix`
  (los tres colapsan hacia `aquest`, misma familia + plurales) y el
  neutro `açò→això`. **Recreado 30/09/2026** (se había quitado del todo
  al pasar a "puro diccionario de Mauricio" y fue un error: ningún
  diccionario puede cubrir un paradigma gramatical cerrado que Mauricio
  no lista). Fuente: `demostratius_avl.json` (paradigma sourced de
  `regles_dialectals_amb_evidencia.md` §1). `aquell`/`allò` son
  idénticos en ambos dialectos y no tienen entrada. La tabla INVERSA
  (`aqueix→eixe`, para un hipotético traductor oriental→occidental) se
  queda documentada en el mismo fichero sin implementarse -- este motor
  solo traduce en un sentido.
- **`numerals.py`** — lookup exacto contra `numerals_mauricio.json`
  (copia de `numerales_limpio.json`, 180 filas): toda la familia
  huit/vuit, "dinou"/"disset" + derivados, y "díhuit"→"divuit" sin ningún
  caso especial (es lookup exacto, no sustitución de subcadena). Excluye
  4 filas de "vuitavat" que parecen una extracción rota en el fichero
  fuente (mismo catalán repetido para 4 valencianos distintos).
- **`accentuacio.py`** — 2 reglas de SUFIJO productivas (añadidas
  30/09/2026, tarde, ver "DECISIÓN DE ARQUITECTURA"): `-és→-ès`
  (`francés→francès`, mismo patrón que 695 palabras literales de
  `lexic_acentuacio_mauricio.json` pero ahora generalizado a CUALQUIER
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

`traductor/rules/*.py` nunca lee `02_regles_dialectals/lexic/` en
tiempo de ejecución -- solo lee copias propias dentro de `traductor/data/`
(para que el paquete funcione de forma autónoma). Si editas un fichero
fuente de `font_mauricio/` directamente, ese cambio no llega al motor
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
   `posesivos_cat_val.json`) directamente en `font_mauricio/`.
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

`03_seleccio_de_model/evalua_models.py` ya tenía un sistema de reglas
(`tradueix_regles`, opción `--model regles`) — sustituciones con regex
sobre la frase completa. Es distinto y **no se ha tocado ni sustituido**:
el paquete `traductor/` se añade como una opción nueva,
`--model traductor`, para poder comparar los dos directamente en el mismo
benchmark:

```bash
cd 03_seleccio_de_model
python evalua_models.py --model traductor                    # motor nuevo (traductor/)
python evalua_models.py --model regles                       # sistema antiguo (regex)
python evalua_models.py --model tots                          # todo a la vez, incluidos ambos
```

El adaptador (`tradueix_traductor_nou` en `evalua_models.py`) añade la
raíz del repositorio a `sys.path` antes de importar `traductor/`, porque
el script siempre se ejecuta desde dentro de `03_seleccio_de_model/` y
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
    'traductor.rules.possessius', 'traductor.rules.numerals', 'traductor.rules.demostratius',
    'traductor.rules.accentuacio', 'traductor.rules.incoatius', 'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
