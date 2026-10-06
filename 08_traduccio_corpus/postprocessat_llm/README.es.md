*[Read it in Catalan](README.md)*

# Post-procesado con LLM de los casos marcados

**Estado (06/10/2026): un caso concreto ya probado y documentado (ver
abajo), el resto todavía PENDIENTE.** El mecanismo general de marcado en
`Token` (ver "Lo que falta decidir" más abajo) todavía no existe -- las
pruebas hechas hasta ahora son scripts autónomos fuera de `traductor/`,
nada integrado en producción. No integrar nada en `traductor/` hasta que
el usuario lo diga explícitamente.

Esta carpeta documenta la decisión de
arquitectura tomada el 02/10/2026: en vez de forzar al motor de reglas a
resolverlo TODO (arriesgado -- cada vez que se ha probado una heurística
automática demasiado amplia en este proyecto, desde el escaneo de género
en `flexio_genere_avl.json` hasta la distinción "per"/"per a", el
resultado ha sido peor que no tocarlo), el plan es dividir el problema en
dos:

1. **El motor de reglas (`traductor/`) traduce y, de paso, marca** los
   puntos donde no tiene suficiente confianza -- sin intentar
   adivinarlos.
2. **Un LLM revisa SOLO esos puntos marcados**, con el contexto de la
   frase y las guías de `../../02_regles_dialectals/docs_gramatica/`
   (GEIEC/GNV completas + las comparativas dialectales derivadas) como
   referencia normativa -- no toda la frase desde cero, como hacen las
   etapas 3-4 con el corpus sintético actual.

## Por qué así y no de otra manera

La alternativa (un LLM que revisa/corrige la frase entera) ya existe en
este proyecto: es exactamente lo que hacen las etapas 3-4
(`03_seleccio_de_model/`, `04_corpus_sintetic/`) con qwen2.5:14b. Ese
enfoque funciona razonablemente bien (BLEU ~93) pero **alucina** -- la
revisión manual encontró ~20% de errores reales sin relación con ninguna
regla dialectal (ver `../../documentacio/metodologia_i_resultats.md`,
secciones 6 y 9). El interés de un motor de reglas es precisamente que no
puede alucinar: si no sabe una palabra, no la toca. Mantener esa
propiedad implica que el LLM solo debe intervenir donde el motor lo pida
explícitamente, no sobre el texto entero.

## Caso probado (06/10/2026): ambigüedad presente indicativo/subjuntivo de 1ª persona

### Por qué este caso y no otro

Decisión explícita del usuario de acotar el primer experimento a UN SOLO
fenómeno, dejando el resto de casos "problematica" de
`conjugacions_dialectals.json` (locuciones fijas, colisiones homógrafas
con sustantivos...) fuera: en valenciano, la misma forma escrita sirve
para el presente de indicativo Y el de subjuntivo en 1ª persona singular
(p.ej. "plantege" -> "plantejo" indicativo / "plantegi" subjuntivo).
`ConjugacionsDictRule` ya excluye estas formas del lookup (ver su
docstring), así que hoy no se traducen nunca -- el objetivo es ver si un
LLM puede decidir el modo correcto mirando el contexto de la frase.

### Datos: 3.004 formas ambiguas, filtrado de falsos positivos nominales

`identifica_ambigues.py` calcula, desde las 4 fuentes de Mauricio, todas
las formas valencianas con EXACTAMENTE 2 traducciones catalanas
candidatas que comparten raíz y difieren solo en la vocal final (-o
indicativo / -i subjuntivo): **3.004 formas**. Buscarlas tal cual en un
corpus real da MUCHOS falsos positivos: muchas de esas formas son MUCHO
más frecuentes como sustantivo ("compte", "objecte", "projecte",
"base"...) que como conjugación de un verbo raro -- el mismo patrón de
colisión homógrafa ya documentado en `traductor/README.md`. Filtro
aplicado: exigir que uno de los dos candidatos aparezca literalmente
como palabra en la traducción catalana de referencia -- esto descarta
casi todos los sustantivos (que se quedan igual en la referencia) y, de
paso, da una "verdad" automática sin anotar nada a mano.

Resultado sobre el corpus del BOE (`dades/boe_net/`, 260.345 frases):
**17.785 frases con forma ambigua y candidato confirmado**, 96%
subjuntivo / 4% indicativo (el BOE es registro legal, lleno de
subordinadas "que"). Sobre el benchmark curado de 150 frases
(`03_seleccio_de_model/benchmark_corpus.json`): solo **2 frases** con el
patrón confirmado -- ese benchmark no es un buen corpus para este
fenómeno concreto (cada frase está elegida para ilustrar OTRO fenómeno
dialectal distinto). El script ya acepta cualquier corpus con
`--corpus --format --camp-valencia --camp-catala --camp-doc` por si hay
que repetir esto sobre otro conjunto.

El muestreo es ESTRATIFICADO por clase de verdad (no al azar), porque
con 96%/4% una muestra al azar saldría casi toda subjuntivo y escondería
cómo se comporta cada vía en la clase minoritaria -- justo donde más se
ve la diferencia real entre vías.

### Las 3 vías comparadas

| Vía | Qué hace el LLM | Riesgo principal |
|---|---|---|
| **A** -- frase entera | Traduce toda la frase de cero | Puede alterar o recortar partes que ya estaban bien (generación abierta sin restricción) |
| **B** -- solo la palabra | Traduce SOLO la palabra marcada, con el contexto de la frase | Puede "inventar" una forma que no es ninguno de los dos candidatos conocidos |
| **C** -- clasificación | SOLO clasifica indicativo/subjuntivo; la forma final sale de una tabla ya conocida | Ninguno -- nunca genera texto nuevo, solo elige entre 2 opciones |

Prompt: `compara_postprocessat.py` usa `guia_traduccio_dialectal.md` como
contexto (pedido explícitamente), con un aviso honesto: esa guía NO
cubre modo verbal (solo determinantes/pronombres/preposiciones/
adverbios), así que el criterio real de indicativo/subjuntivo
(subordinada con "que" dependiente de voluntad/necesidad/duda, etc.) se
añade aparte, en el prompt.

### Resultados (17 frases reales del BOE, misma muestra, 2 modelos vía Ollama/Abaco)

| Vía | qwen2.5:14b | qwen3:8b |
|---|---|---|
| A -- frase entera | 5/17 (29%) | 6/17 (35%) |
| B -- solo la palabra | 11/17 (65%) | 10/17 (59%) |
| C -- clasificación | **14/17 (82%)** | **13/17 (76%)** |

Desglose por clase (importante: solo 4 de las 17 frases eran indicativo,
la clase difícil y minoritaria):

| Vía | subjuntivo (n=13) qwen2.5 | indicativo (n=4) qwen2.5 | subjuntivo (n=13) qwen3:8b | indicativo (n=4) qwen3:8b |
|---|---|---|---|---|
| A | 5/13 | 0/4 | 6/13 | 0/4 |
| B | 10/13 | 1/4 | 10/13 | 0/4 |
| C | 12/13 | 2/4 | 10/13 | **3/4** |

**Conclusiones principales**:
1. **La vía C gana con margen en los dos modelos** -- es la única que
   nunca puede "alucinar" una forma inexistente, porque la sustitución
   final siempre viene de una tabla cerrada de 2 opciones, nunca del LLM.
2. **Cada modelo falla de manera distinta** en las vías A/B: qwen2.5:14b
   inventa palabras sin sentido ("oposiussenpt", "determineix",
   "maneu"); qwen3:8b a menudo simplemente deja la palabra original sin
   traducir ("enquadre", "dispose", "licite", "mane") -- un fallo "más
   honesto" pero fallo igualmente.
3. **Los casos de indicativo (la clase minoritaria) son los más
   difíciles en general, pero NO igual en los dos modelos**: qwen2.5:14b
   solo lo acierta 2/4 (se deja llevar por los verbos subjuntivos vecinos
   en fórmulas solemnes como "jo la sancione" o "Mane a tots..."),
   mientras que qwen3:8b lo acierta 3/4 -- a cambio de perder algo de
   precisión en subjuntivo (10/13 frente a 12/13). Con solo 4 ejemplos de
   indicativo, hace falta más muestra antes de elegir un modelo
   definitivo solo por este criterio.
4. **Bug encontrado, no corregido todavía**: en un caso, qwen2.5:14b
   respondió "subjuntivo" (castellano) en vez de "subjuntiu" (catalán) en
   la vía C -- el parser actual no lo reconoce y lo cuenta como fallo.
   Pendiente ampliar el parser para aceptar variantes.

### Tiempo por frase (datos reales, 06/10/2026, GPU de Abaco)

Desde que `compara_postprocessat.py` mide los segundos de cada llamada
(campo `segons` dentro de cada `via_a`/`via_b`/`via_c`, y un resumen al
final de la ejecución), ya hay datos reales de 3 modelos sobre GPU (no
solo el test trivial por CPU local de 65s de antes, que no era
representativo):

| Modelo | Vía A (frase entera) | Vía B (solo palabra) | Vía C (clasificación) |
|---|---|---|---|
| qwen2.5:14b | 5,7s | 2,0s | **0,6s** |
| qwen3:8b | 4,1s | 1,2s | **0,4s** |
| qwen3:14b | 18,6s (un caso subió a 34s) | 1,9s | **0,6s** |

**La vía C no solo es la más fiable -- también es, de lejos, la más
rápida**: entre 7 y 50 veces más rápida que la vía A, y 2-4 veces más
rápida que la B. Tiene sentido: la vía C solo genera una palabra de
salida ("indicatiu"/"subjuntiu"), mientras que la A tiene que regenerar
la frase entera y la B al menos la forma catalana completa. Esto refuerza
la decisión de la arquitectura C desde dos ángulos independientes
(precisión Y coste), no solo uno.

### Prueba cruzada con 3 modelos sobre el benchmark (06/10/2026)

Mismas 2 frases del benchmark (`base`/"quan el tractament es base..." y
`recupere`) probadas con qwen2.5:14b, qwen3:8b y qwen3:14b:

| Modelo | A | B | C |
|---|---|---|---|
| qwen2.5:14b | 0/2 | 0/2 | 1/2 |
| qwen3:8b | 0/2 | 0/2 | 1/2 |
| qwen3:14b | 0/2 | 1/2 | 0/2 |

Muestra demasiado pequeña (n=2) para sacar conclusiones de precisión,
pero revela un hallazgo interesante: **los 3 modelos, sin excepción,
fallan la vía C en el caso "quan el tractament es base en el seu
consentiment"** (lo eligen como indicativo cuando la referencia dice
"es basi", subjuntivo). Puede ser un patrón sistemático no cubierto por
el criterio actual del prompt: "quan" + presente puede exigir subjuntivo
en catalán formal según el tipo de cláusula (condicional/genérica), y el
criterio explícito que se le da hoy al LLM (ver `CRITERI_MODE_VERBAL` en
`compara_postprocessat.py`) no lo menciona explícitamente -- candidato
claro para ampliar el prompt cuando haya más ejemplos de este patrón.

### Herramientas y dónde están los resultados

- `identifica_ambigues.py` -- calcula las 3.004 formas y la muestra
  estratificada (ahora reutilizable sobre cualquier corpus, ver arriba).
- `compara_postprocessat.py` -- ejecuta las 3 vías con el modelo elegido.
- `slurm/compara_postprocessat.sh` -- job de SLURM para Abaco (modelo y
  límite de frases como argumentos, ver cabecera del script).
- `resultats_comparativa_ABC_<modelo>.json` -- salida de cada ejecución
  (no versionado todavía en git, generado por sesión).
- Visualización: artifact HTML en Claude con pestañas por modelo y
  comparativa cabeza a cabeza -- pide el enlace si lo necesitas, o pega
  un JSON de resultados nuevo para regenerarlo.

## Lo que falta decidir antes de escribir ningún código

- **Formato de la marca**: a nivel de `Token` (añadir un campo como
  `necessita_revisio: bool` o `candidat_regla: str | None` a la clase
  `Token` de `traductor/rules/__init__.py`), a nivel de frase entera, o
  ambos. Todavía no decidido -- no tocar `Token` hasta que se decida.
- **Qué reglas etiquetan y cuándo**: por ejemplo, una futura regla para
  "per"/"per a" podría NO decidir, y en vez de eso marcar el token "per"
  como candidato cuando detecte el patrón ambiguo (ver
  `traductor/README.es.md`, sección "DECISIÓN DE ARQUITECTURA" 02/10/2026,
  para los 3 casos ya identificados como demasiado arriesgados para una
  regla directa).
- **Qué modelo**: local vía Ollama (coherente con el resto del proyecto,
  qwen2.5:14b ya en uso) u otro -- pendiente de probar coste/calidad
  sobre una muestra pequeña de casos marcados antes de elegir.
- **El LLM propone o solo señala**: si la salida del LLM sustituye
  directamente el texto marcado, o si solo genera un informe para
  revisión humana (más lento, pero sin riesgo de alucinación silenciosa
  sobre datos ya marcados como dudosos).

## Cómo continuar cuando se retome

1. Decidir el formato de marca y añadirlo a `Token` + a, al menos, una
   regla real (candidato natural: la distinción "per"/"per a" documentada
   en `docs_gramatica/guia_traduccio_dialectal.md`, bloque C2).
2. Ejecutar `../traduccio_massiva.py` sobre un corpus real y contar
   cuántos puntos quedan marcados -- eso da una primera idea del volumen
   real antes de elegir modelo ni diseñar el prompt.
3. Probar el LLM elegido sobre una muestra pequeña de los puntos
   marcados, mismo método que el resto del proyecto: evidencia antes que
   implementación completa.
