*[Llegeix en català](README.md)*

# Motor de reglas determinista — etapa 5

Este paquete (`traductor/`) vive en la raíz del repositorio, sin el prefijo
numérico de las demás etapas (`01_...` a `04_...`), porque es un paquete
Python que se importa por nombre (`import traductor`) desde otras partes
del código — un nombre de módulo no puede empezar por un dígito en Python.
Conceptualmente es la etapa 5 del proyecto.

## Por qué existe esto

Las etapas 1-4 usan un LLM (qwen2.5:14b) con un system prompt de reglas +
glosario dinámico para generar el corpus sintético. Funciona razonablemente
bien (BLEU ~93 en el benchmark de 60 frases), pero la revisión manual
encontró un ~20% de errores reales frente al ~1,5% que detectan las
comprobaciones automáticas — la mayoría, alucinaciones del modelo sin
relación con ninguna regla dialectal (ver `../documentacion/metodologia_y_resultados.md`,
secciones 6 y 9).

La conversión occidental→oriental es, en su mayor parte, un problema
**morfológico y léxico determinista** (demostrativos, posesivos,
numerales...), no de traducción libre. Un motor de reglas no puede
alucinar: si una palabra no está en ninguna tabla, simplemente no la toca.
Este paquete no sustituye al LLM (todavía no cubre ni de lejos todas las
reglas documentadas — ver "Qué falta" más abajo), pero es una base
determinista, auditable y sin dependencias, pensada para:
- comparar directamente contra el LLM en el mismo benchmark (`--model
  traductor` en `03_seleccion_de_modelo/evalua_models.py`, junto al `--model
  regles` ya existente — ver "Relación con el sistema de reglas antiguo"),
- servir de capa de post-procesado/verificación sobre la salida del LLM,
- o, a medida que crezca, sustituir al LLM en los casos que ya cubre con
  garantías, dejando el LLM solo para lo genuinamente ambiguo.

## Arquitectura

Pipeline secuencial de capas sobre una lista de `Token`, no sustituciones
de texto sobre la frase entera:

```
texto ──tokenize()──▶ [Token, Token, ...] ──marca_noms_propis()──▶
    ──▶ LexicRule ──▶ DemostratiusRule ──▶ PossessiusRule ──▶ NumeralsRule
    ──▶ GentilicisRule ──▶ MorfologiaVerbalRule ──▶ LocucionsRule
    ──▶ PerfetRule ──▶ ElisioRule ──▶ detokenize() ──▶ texto convertido
```

### `Token` (`rules/__init__.py`)

```python
@dataclass
class Token:
    surface: str          # forma original, nunca cambia
    translated: str        # se va sobreescribiendo capa a capa
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

Cada capa marca `is_translated = True` en cuanto toca un token, y todas
las capas posteriores respetan ese flag (`if tok.is_translated: continue`).
Sin esto, dos reglas independientes podrían pisarse sin que nadie se diera
cuenta — p.ej. la regla de posesivos "arreglando" por accidente una
palabra que ya había tocado el léxico. Con un flag explícito, el orden de
las capas queda documentado y cada una sabe exactamente qué le toca
todavía.

### Decisión de diseño: apóstrofos y guiones son parte de la palabra

`tokenize()` trata `d'escola`, `l'AVL` o `dir-li` como **un solo token**
cada uno, no como palabra+frontera. Separarlos en el tokenizador obligaría
a decidir el corte sin conocer todavía la regla gramatical que lo
justifica — esa decisión se deja a `elisio.py`, que es quien de verdad
sabe si `d'` debe deshacerse o no. Como contrapartida, `numerals.py` tiene
que buscar la subcadena `"huit"` **dentro** del token en vez de hacer un
lookup de palabra completa, porque compuestos como `cinquanta-huit`
llegan como un único token.

**Consecuencia que costó encontrar (29/09/2026)**: esa misma decisión hace
que un token como `d'este` nunca coincida con la entrada `"este"` de un
diccionario — el lookup exacto de `demostratius.py`, `lexic.py`,
`conjugacions_dict.py`, las tablas de `morfologia_verbal.py` y los
diccionarios de `numerals.py` se quedaban sin traducir cualquier palabra
pegada a un prefijo elidido (`d'este`, `s'oferisca`, `n'hagen`...).
`separa_prefix_elidit()` (`rules/__init__.py`) es el arreglo compartido:
cada regla de lookup exacto lo usa como segundo intento cuando la
búsqueda directa falla, separando el prefijo y buscando solo la parte
real de la palabra. Las reglas basadas en sufijo (`gentilicis.py`,
`perfet.py`) no lo necesitan: ya operaban con `.sub()` sobre todo el
token, que atraviesa cualquier prefijo sin tener que separarlo.

### Protección de nombres propios (`marca_noms_propis`)

Se ejecuta una sola vez, antes de la primera regla: marca `is_proper_noun`
en toda palabra capitalizada que **no** sea la primera del texto (la
primera letra de una frase siempre va en mayúscula, sea o no nombre
propio). Es la misma heurística ya probada en
`03_seleccion_de_modelo/evalua_models.py::glossari_per_frase()`, añadida allí tras
un incidente real con `blanca`/`Blanca` y `roig`/`Roig` (ver
`../documentacion/metodologia_y_resultados.md`, sección 6). Límite conocido, heredado sin
arreglo: un nombre propio que es la **primera** palabra del texto nunca se
detecta.

## Orden de las reglas, y por qué

| # | Regla | Por qué en esta posición |
|---|---|---|
| 1 | `lexic` | Lookup directo, la más "seca" — conviene que corra antes de que cualquier regla morfológica toque la misma palabra por otro motivo |
| 2 | `conjugacions_dict` | Ídem, pero de formas verbales (fuente Mauricio/Apertium, 29/09/2026) — misma naturaleza que `lexic`, por eso va justo después |
| 3 | `demostratius` | Patrón cerrado y sin ambigüedad, no interactúa con nada más |
| 4 | `possessius` | Ídem |
| 5 | `numerals` | Ídem (incluye la concordancia "dos/dues") |
| 6 | `gentilicis` | Regla de sufijo general, pero acotada por las excepciones "és"/"més" |
| 7 | `morfologia_verbal` | Fases 1, 2 y 6 (presente indicativo, presente subjuntivo, incoativos); lista cerrada para 1/2, sufijo con excepciones para 6 |
| 8 | `locucions` | Sustituciones de frase fija (`cap a on`, `dalt/baix de`) — no interactúa con nada anterior |
| 9 | `perfet` | Genera una **frase** ("va passar"), no una palabra — mejor después de que todo lo demás ya esté resuelto palabra por palabra |
| 10 | `elisio` | **Deliberadamente la última**: opera sobre el resultado ya transformado (`tok.translated`, no `tok.surface`) de la palabra siguiente. Si fuera antes, una regla posterior podría cambiar esa palabra y dejar la elisión apuntando a una vocal/consonante que ya no está — es exactamente lo que dice la fuente (`../02_reglas_dialectales/reglas_dialectales_con_evidencia.md`, §11.2): "cal aplicar l'elisió cada vegada que una altra regla la dispara" |

**Bug real encontrado al verificar este orden** (no solo revisado a ojo,
con doctest de regresión en `elisio.py`): la primera implementación de
`ElisioRule` miraba `tok.surface` de la palabra siguiente en vez de
`tok.translated`. Con `"de huitanta"`, `numerals.py` ya había convertido
`huitanta→vuitanta` (empieza por consonante, no elide), pero `elisio.py`
miraba la forma original `huitanta` (empieza por h muda + vocal, sí
parece elidir) y producía `"d'vuitanta"`, incorrecto. Arreglado mirando
`tok.translated`; el caso queda como test de regresión permanente.

## Cada regla, en una frase

- **`lexic.py`** — sustitución directa vía `traductor/data/lexico_fiable.json`
  (copia de trabajo de `02_reglas_dialectales/lexico/lexico_fiable.json`,
  347 entradas). El JSON usa arrays paralelos singular/plural
  (`["ametla","ametles"] → ["ametlla","ametlles"]`), no "una palabra,
  varias alternativas" — solo hay una excepción real de longitudes
  distintas (`corder/corders → xai/be/anyell`), resuelta cogiendo siempre
  el primer sinónimo (documentado, no arreglado del todo: da
  `corders→xai` en singular en vez de plural). El 29/09/2026 se
  incorporaron 150 entradas nuevas de un diccionario catalán-valenciano
  aportado por Mauricio (equipo AVLizador, basado en el apertium
  bilingüe), más los 3 pares sueltos que ya estaban documentados en la
  fuente pero aún no implementados (`vindre→venir`, `valdre→valer` §4,
  `vos→us` §3) — ver `02_reglas_dialectales/lexico/font_mauricio/` para
  los datos en bruto y el criterio de filtrado exacto (excluyendo
  entradas `_PENDENT` sin verificar y conflictos con entradas ya
  revisadas a mano, que siempre ganan).
- **`demostratius.py`** — este/esta/estos/estes→aquest...; eixe/eixa/eixos/eixes→aquest...
  (desde el 28/09/2026 "eixe" se fusiona con "este" hacia la misma forma
  oriental — el oriental real ha colapsado el sistema de 3 grados a 2; ver
  `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` §1 para
  el razonamiento completo).
- **`possessius.py`** — meua/teua/seua (+ plurales) → meva/teva/seva. Solo
  formas átonas femeninas; masculinas y tónicas no cambian (§2).
- **`conjugacions_dict.py`** — lookup exacto de 904 formas verbales (111
  verbos) del diccionario de Mauricio (equipo AVLizador, apertium
  bilingüe, 29/09/2026): cubre alternancias irregulares que
  `morfologia_verbal.py` no puede generalizar por sufijo
  (`oferisca→ofereixi`, `traure→treure`...). Excluye deliberadamente las
  65 formas marcadas `problematica` en la fuente (el valenciano usa la
  misma forma para indicativo y subjuntivo en esos casos, y sin
  pos-tagging no hay forma fiable de elegir cuál toca) — ver docstring
  del módulo.
- **`numerals.py`** — cuatro mecanismos independientes: raíz `huit→vuit`
  (búsqueda de subcadena, con `díhuit→divuit` como excepción real
  resuelta aparte), ordinales `-é→-è` (tabla cerrada, **no** regla de
  sufijo genérica — hay palabras como préstamos acabados en -é que no son
  ordinales), concordancia `dos/dues` (heurística débil: mira si la
  palabra siguiente acaba en "-a"/"-es"/"-ió"/"-ions" — este último sufijo
  añadido 29/09/2026, fiable porque casi ningún nombre acabado en "-ió" es
  masculino; falso negativo conocido con femeninos que no acaban en
  ninguno de estos, p.ej. "dos mans"), y raíces `dinou/disset` + sus
  derivados en `-ena`/`-é` (tabla cerrada de 10 formas, añadida
  29/09/2026 con datos de Mauricio — no comparten subcadena con el
  oriental como sí hace `huit/vuit`). La concordancia `dos/dues` también
  mira hacia ATRÁS (29/09/2026, caso real RC062) cuando no hay ninguna
  palabra detrás de "dos" (típicamente puntuación: `"...en dos:
  establir..."`) — "dos" ahí se refiere anafóricamente a un nombre ya
  dicho antes en la misma frase.
- **`gentilicis.py`** — sufijo `-és→-ès`, sí como regla general (300+
  lemas confirmados según la fuente), con las dos excepciones explícitas
  de la fuente (`és` verbo, `més` cantidad) que nunca cambian, más una
  tercera encontrada empíricamente al correr el benchmark completo:
  `"després"` (adverbio) se rompía en `"desprès"` — la fuente solo daba 2
  excepciones, no es una lista exhaustiva.
- **`morfologia_verbal.py`** — **fase 1** (presente indicativo, 1ª
  persona, 1ª conjugación: parle→parlo...) y **fase 2** (presente
  subjuntivo, "jo"/"ells": puga→pugui, tinguen→tinguin...), las dos como
  lista cerrada y no regla de sufijo genérica: demasiadas palabras
  catalanas acaban en "-e"/"-a"/"-en" sin ser esas formas verbales
  concretas. **Fase 6** (incoativos -ix→-eix: establix→estableix) sí es
  regla de sufijo, porque la fuente lo documenta como patrón general —
  lleva lista negra (`baix`, `calaix`, `dibuix`, `guix`) para no tocar
  palabras reales que acaban igual sin ser verbos. Fases 3-5 (imperfecto
  de subjuntivo, imperfecto de indicativo, participio de "ser")
  documentadas como TODO explícito dentro del propio fichero, con la
  razón de por qué cada una necesita más cuidado antes de implementarse.
- **`locucions.py`** — dos patrones: `cap a on→cap on` (sustitución
  literal) y `dalt de/baix de→a dalt de/a baix de` (prefijo, con mayúscula
  gestionada a mano como en `perfet.py`). "per a→per" delante de
  infinitivo se probó y se **retiró**: la auditoría del benchmark real
  (28/09/2026) encontró que de 17 apariciones de "per a + infinitivo",
  ninguna lo reduce a "per" — siempre se mantiene "per a" (ver
  `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` §7.1).
  Pendientes, documentados pero NO implementados aquí (§7.2 de la
  fuente): "a on"/"on" según ubicación estática o dirección, y "en"→"a"
  en construcciones locativas (esta última, además, contradice una
  protección ya existente en el system prompt del LLM — pendiente de
  confirmar el alcance exacto antes de tocarla).
- **`perfet.py`** — pretérito perfecto simple → perifrástico, solo 1ª
  conjugación (`-ar`). Reconstruye el infinitivo quitando la terminación
  y añadiendo "-ar". Alcance recortado con datos reales, no solo teoría:
  al correr el benchmark completo, las terminaciones cortas `-í` y
  `-ares` dieron **0 aciertos y 7 falsos positivos** (`llatí`, `així`,
  `pares`, `clares`...) — se quitaron del todo. `-à` y `-aren` sí tienen
  aciertos reales confirmados (`celebrà`, `passà`, `quedaren`) y se
  quedan, con una lista negra para sus propios falsos positivos
  confirmados (`està`, `valencià`, `castellà`, `català`).
- **`elisio.py`** — `de/la/el → d'/l'` ante vocal real o *h* muda. Nunca
  duplica una elisión que ya viniera hecha en el original (esas llegan
  como un único token desde `tokenize()`, nunca casan con "de"/"la"/"el"
  sueltos). Excepción confirmada (29/09/2026): `la` (nunca `el`/`de`) no
  elide nunca ante palabra que empieza por `i`/`u` (`la intenció`, `la
  universitat`, nunca `l'intenció`/`l'universitat`) — convención
  ortográfica para no perder la distinción de género en la lectura, no un
  fenómeno fonético; de paso resuelve como efecto lateral el caso `la
  iaia` que antes se documentaba aquí como diptongo semiconsonántico sin
  arreglar.

## Qué falta (gaps conocidos, no una promesa de qué se hará)

Reglas que **sí están documentadas** en `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` pero que
**ningún** fichero de `traductor/` cubre todavía:

| Sección de la fuente | Contenido | Dónde encajaría |
|---|---|---|
| §5.3-§5.5 | Imperfecto de subjuntivo, imperfecto de indicativo, participio de "ser" | Documentado fase a fase dentro de `morfologia_verbal.py`, ver el fichero (fases 1/2/6 ya implementadas) |
| §7.2 | `hui→avui`, `vesprada→tarda`... (pares léxicos sueltos, no los de `locucions.py`) | Candidatos a `lexico_fiable.json`, mismo criterio que §3/§4 (ya resueltos, ver abajo) |
| §7.1 | `per a`→`per` delante de infinitivo | **Probado y retirado**: contradicho por 17/17 casos del benchmark real, siempre se mantiene "per a" |
| §7.2 | `a on`→`on`/`a on` (estático/dirección), `en`→`a` (locativo) | Pendientes de confirmar — ver `locucions.py`, ya cubre el resto de patrones de esta sección |
| §11.3 | `al + infinitiu → en + infinitiu` | La propia fuente lo marca como "pendiente de confirmar" (2/2 pero muestra insuficiente) — no implementar sin más evidencia |
| — | Topónimos (`Ademuz→Ademús`, `Alcublas→les Alcubles`...) | 73 pares en el diccionario de Mauricio (`tipo: "v:top_gva"`), NO incorporados: el motor protege todos los nombres propios de traducción (`is_proper_noun`, ver §"Protección de nombres propios" arriba), así que aunque se añadieran a `lexico_fiable.json` nunca se aplicarían. Hay que decidir primero si los topónimos deben traducirse en absoluto y, si sí, cómo distinguirlos de otros nombres propios que nunca deben tocarse — ver los datos en bruto en `02_reglas_dialectales/lexico/font_mauricio/lexico_general_limpio.json` |

**Resuelto el 29/09/2026** (documentado aquí antes, ya implementado): §3
Pronombres personales (`vos→us`) y §4 Infinitivos irregulares
(`traure→treure` y `sigut→estat` §5.5 vienen del diccionario de
conjugaciones de Mauricio, vía `conjugacions_dict.py`; `tindre→tenir`,
`vindre→venir`, `vore→veure`, `eixir→sortir`, `valdre→valer` y `vos→us`
están en `lexico_fiable.json`) — todos eran pares sueltos, no patrones
productivos, tal como ya preveía este mismo README.

Patrón general: cualquier cosa que sea "un par de palabras concreto" (no
un sufijo o patrón productivo) encaja mejor en el léxico que en una regla
nueva — es el mismo criterio que ya usó la fuente para `vosté/vostés`.

## Cómo añadir una regla nueva

1. Confirma la tabla/patrón en `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md`
   — **nunca la inventes**; si la fuente no la confirma con evidencia, no
   se implementa (ver cómo se documentaron los huecos de arriba).
2. Decide: ¿es un patrón productivo (sufijo/regla general) o un puñado de
   pares sueltos? Los pares sueltos van a `lexico_fiable.json`, no a un
   fichero nuevo.
3. Si es un patrón nuevo, crea `traductor/rules/nombre_regla.py` con la
   misma interfaz que todas las demás:
   ```python
   class NombreReglaRule:
       def apply(self, tokens: list[Token]) -> list[Token]:
           for tok in tokens:
               if tok.is_translated or tok.is_proper_noun:
                   continue
               # lógica aquí
           return tokens
   ```
4. Si la regla necesita mirar tokens vecinos (como `elisio.py` o la
   concordancia de `numerals.py`), itera por índice, no por valor — pero
   la firma pública sigue siendo `apply(tokens) -> tokens`.
5. Añade doctests reales en el docstring (no solo descripción) — es la
   única suite de tests de este paquete. Ejecuta:
   ```bash
   python -c "import doctest, traductor.rules.nombre_regla as m; print(doctest.testmod(m))"
   ```
   (`python -m doctest fichero.py` **no** funciona aquí por los imports
   relativos del paquete — usa el import de arriba.)
6. Regístrala en `RuleEngine.__init__` (`traductor/rules/engine.py`), en
   el punto del orden que le corresponda, y documenta el porqué en la
   tabla de "Orden de las reglas" de este README.
7. Si algo es lingüísticamente ambiguo (¿es esta forma valenciana o ya
   oriental? ¿aplica siempre o depende de contexto que no podemos ver sin
   spaCy?), coméntalo con `# AMBIGÚ:` explicando el porqué — no lo
   resuelvas adivinando.

## Relación con el sistema de reglas antiguo

`03_seleccion_de_modelo/evalua_models.py` ya tenía un sistema de reglas
(`tradueix_regles`, opción `--model regles`) — sustituciones con regex
sobre la frase completa. Es distinto y **no se ha tocado ni sustituido**:
el paquete `traductor/` se añade como una opción nueva,
`--model traductor`, para poder comparar los dos directamente en el mismo
benchmark:

```bash
cd 03_seleccion_de_modelo
python evalua_models.py --model traductor                    # motor nuevo (traductor/)
python evalua_models.py --model regles                       # sistema antiguo (regex)
python evalua_models.py --model tots                          # todo a la vez, incluidos ambos
```

El adaptador (`tradueix_traductor_nou` en `evalua_models.py`) añade la
raíz del repositorio a `sys.path` antes de importar `traductor/`, porque
el script siempre se ejecuta desde dentro de `03_seleccion_de_modelo/` y Python no
encuentra ahí un paquete que vive en la carpeta de al lado.

## Uso directo

```bash
python -m traductor.cli "Este xiquet mira la meua obra i vaig ser el cinqué de huitanta."
# -> Aquest nen mira la meva obra i vaig ser el cinquè de vuitanta.
```

```python
from traductor import translate
translate("Tinc huitanta anys.")  # -> "Tinc vuitanta anys."
```

## Testing

No hay una carpeta `tests/` — cada regla lleva sus propios doctests reales
(no solo ejemplos ilustrativos) en el docstring de su clase, y se
verifican con `doctest.testmod()`, no a ojo. Para correr los de todo el
paquete de una vez:

```bash
python -c "
import doctest, importlib
modulos = [
    'traductor.rules', 'traductor.rules.lexic', 'traductor.rules.conjugacions_dict',
    'traductor.rules.demostratius', 'traductor.rules.possessius', 'traductor.rules.numerals',
    'traductor.rules.gentilicis', 'traductor.rules.morfologia_verbal', 'traductor.rules.locucions',
    'traductor.rules.perfet', 'traductor.rules.elisio', 'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
