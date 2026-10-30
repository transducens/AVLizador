# AVLizador: metodología y resultados completos

Este documento resume todo el proceso del proyecto, de principio a fin:
de dónde sale el texto fuente, cómo se decidieron las reglas dialectales,
qué modelos se usaron y por qué, cómo se construyó el motor de
traducción determinista y su dirección inversa, la capa de postprocesado
con modelo de lenguaje, la métrica propia de grado dialectal (GD), la
validación contra corpus reales, y la reorganización final del
repositorio — qué problemas se encontraron por el camino y cómo se
corrigieron. Pensado para quien reciba este repositorio sin más contexto
que el propio código.

**Secciones 1-10** (hasta el 22/09/2026): construcción del corpus
sintético a partir del scraping de la AVL — etapas 1-4 del proyecto.
**Secciones 11 en adelante** (a partir del 02/10/2026): el motor de
reglas deterministas (`traductor/`), que ha sido el foco real de trabajo
desde entonces, en las dos direcciones, más su validación. Desde el
20/10/2026 el trabajo se centra solo en **catalán → valenciano**, una de
las dos herramientas que se entregan a la Conselleria (la otra es el GD,
sección 14), para equipos con pocos recursos y sin GPU. El estado actual
de esa dirección está en la sección 12 (motor), la 13 (capa opcional con
modelo de lenguaje para los homógrafos) y la 17 (resumen de cifras).

## 1. Origen del texto (el lado "valenciano")

### 1.1 Qué es la AVL y por qué es la fuente

La **AVL (Acadèmia Valenciana de la Llengua)** es la institución oficial
que regula el valenciano — creada en 1998 por las Corts Valencianes, es al
valenciano lo que el IEC es al catalán oriental: fija la normativa (léxico,
gramática, ortografía), resuelve consultas lingüísticas y publica los
materiales de referencia oficiales. Se eligió como fuente precisamente por
eso: al ser la autoridad normativa, su web es la fuente con más garantías
de contener valenciano occidental normativo real (no una mezcla de
registros ni texto de otro origen).

### 1.2 Qué se scrapeó exactamente, página por página

La web de la AVL no es un solo tipo de contenido — combina un WordPress
normal con herramientas de consulta antiguas (JSP) y documentos en PDF. Por
eso hay **5 scripts distintos**, cada uno con la técnica que le hacía falta
a cada tipo de página:

| Script | Técnica | Qué saca | Qué es esa sección |
|---|---|---|---|
| `avl_probe.py` | API REST de WordPress (`/wp-json/wp/v2/...`) | `butlleti`, `glossari`, `post`, `pagina`, y la categoría 9 (`notes-de-premsa`) | El **butlletí** es el boletín/revista periódica de la AVL. El **glossari** son consultas lingüísticas resueltas por la Acadèmia (del tipo "¿cómo se dice X en valenciano?", explicando origen y uso de una palabra) — esto explica por qué el benchmark tiene bastantes frases que hablan *sobre* palabras, no solo frases normales. **Post**/**pàgina** son entradas de blog y páginas estáticas genéricas. **Notes de premsa** son los comunicados de prensa institucionales. |
| `avl_crawler.py` | HTML directo (requests + BeautifulSoup + trafilatura) | `salutacio` (la página de presentación institucional, un único documento) y `escriptors` (biografías) | **Escriptors** son las biografías de los autores reconocidos en "Escriptors de l'Any", un galardón anual de la AVL. |
| `gnv_extractor.py` | Playwright (navegador real automatizado) | La **GNV — Gramàtica Normativa Valenciana** (2006) | La gramática oficial completa y técnica del valenciano. Hace falta Playwright (no basta con `requests`) porque el buscador de la GNV es una herramienta JSP antigua que detecta peticiones automatizadas y devuelve contenido recortado si no ve un navegador real. |
| `gvb_extractor.py` | Playwright, mismo motivo que arriba | La **GVB — Gramàtica Valenciana Bàsica** (2016) | Versión simplificada de la gramática normativa, pensada para público no especializado — secciones más breves, sin terminología lingüística técnica. Es un documento distinto de la GNV, no un duplicado. |
| `pdf_extractor.py` | Descarga + extracción de texto (pymupdf), sin guardar el PDF en disco | PDFs listados en `fonts_pdf.txt` (`legislacio`, `acord-normatiu`) y `fonts_pdf_publicacions.txt` (`publicacions`) | **Legislació**: la ley de creación de la AVL, el reglamento interno, dictámenes del Consell Valencià de Cultura. **Acord normatiu**: los acuerdos normativos oficiales aprobados en pleno por la AVL (decisiones formales sobre normas lingüísticas concretas, p. ej. cuándo usar "dos" o "dues"). **Publicacions**: manuales y colecciones de investigación propias ("Recerca", "Documents", "Plurilingüisme"). |

### 1.3 Cómo se filtra a "solo valenciano occidental puro"

```
avl_probe.py / avl_crawler.py / gnv_extractor.py / gvb_extractor.py / pdf_extractor.py
        ↓
dades/avl/raw/*.jsonl  →  neteja_corpus.py  →  dades/avl/clean/*.jsonl
        ↓ (unificación de todas las fuentes)
dades/avl/final/unified.jsonl          (2.233 documentos, todo unificado)
        ↓ estudi_dialectal.py
dades/avl/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documentos, 821.195 tokens — SOLO texto verificado
         como valenciano occidental puro)
```

`estudi_dialectal.py` clasifica cada documento contando cuántas palabras
del texto coinciden con una lista de marcadores dialectales ya conocidos
(`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`, codificadas directamente en el
script — el mismo tipo de contraste léxico que se documenta en la etapa 2,
pero usado aquí para *clasificar* documentos en vez de para traducir). Para
cada documento se calcula:

```
ratio = (marcadores occidentales) / (marcadores occidentales + orientales)
```

y se clasifica: **≥80% → occidental_clar, 60-80% → occidental_predominant,
40-60% → mixt, 20-40% → oriental_predominant, <20% → oriental_clar.** Si un
documento no tiene ningún marcador (no hay ninguna palabra dialectalmente
marcada en todo el texto), se asume `occidental_assumit` cuando la fuente
ya es institucionalmente valenciana (AVL, GNV, GVB) y no es una página
genérica; si no, queda `no_determinat`.

**Decisión clave**: el corpus final solo se queda con `occidental_clar` +
`occidental_predominant` + `occidental_assumit` — se descarta explícitamente
lo mixto y lo oriental. No se tradujo `unified.jsonl` (el corpus completo)
precisamente para no meter en la mezcla texto que ya estaba en catalán
oriental o en registro mixto, lo que habría generado pares donde el
"original" ya no era realmente valenciano.

### 1.4 Segmentación en frases

Cada documento se segmenta en frases sueltas (no se traduce el párrafo
entero) por dos motivos: el modelo se benchmarkeó sobre frases sueltas, y
traducir párrafos largos aumenta el riesgo de que "explique" en vez de
traducir; y porque mucho texto (glosario, textos legales) se repite entre
documentos y conviene deduplicar. De 48.037 frases candidatas quedaron
**46.315 únicas** tras deduplicar, descartar frases de <5 palabras/20
caracteres (ruido) y de >280 caracteres (riesgo de corte a mitad de
respuesta).

## 2. Cómo se decidieron las reglas dialectales

El punto de partida fue `apertium-cat.cat.dix`, el diccionario morfológico
de Apertium: cada forma marcada `v="val_gva"` (occidental) se comparó con
su equivalente `v="cat"`/`v="val_uni"` (oriental/general) dentro del mismo
diccionario, paradigma por paradigma. Esto dio un primer informe bruto con
la cobertura real de cada patrón — cuántos casos del diccionario lo siguen,
del total de casos con esa combinación gramatical — que hoy vive como el
apéndice final de `reglas_dialectales.md`.

**Principio seguido todo el proyecto**: nunca inventar una traducción. Si
un patrón tenía menos de, aproximadamente, 60-70% de cobertura en el
diccionario, no se convertía en regla general del prompt — se dejaba como
lista cerrada de palabras confirmadas una a una, o como "pendiente de
confirmar" documentado pero no aplicado. Ejemplos de reglas descartadas por
baja fiabilidad pese a parecer razonables: un patrón general "é→è" (roto
por palabras muy frecuentes como *més*/*és*, que NO cambian) o el patrón
"-és/-ès" con solo 4/10 de cobertura en una muestra pequeña (que al
investigarlo a fondo resultó ser en realidad el patrón, mucho más fiable,
de los gentilicis — ver más abajo).

Fuentes de las reglas finales, cada una con su nivel de confianza
documentado en `reglas_dialectales.md`:

- **Morfología verbal** (demostratius, possessius, subjuntiu, participi,
  incoatius): confirmada por comparación directa de paradigmas del
  diccionario.
- **Numerals** (huit→vuit): confirmado como una arrel, no una lista de
  palabras — aplica dentro de cualquier compuesto con guionet.
- **Ordinals** (-é→-è): 113 lemas confirmados en el diccionario.
- **Gentilicis de país/idioma** (-és→-ès): más de 300 lemas confirmados
  (`francés→francès`, `anglés→anglès`...) — un hallazgo que corrigió una
  cifra de fiabilidad antigua (4/10) que en realidad venía de una muestra
  demasiado pequeña.
- **Pretèrit perfet simple → perifràstic** (`passà→va passar`): esta regla
  NO sale del diccionario de palabras — sale de comparar frases completas
  del benchmark (100% de los 4 casos reales encontrados). Es la prueba de
  que hacía falta mirar frases enteras, no solo palabras sueltas.
- **Numeral "dos/dues"** (concordancia de género): tercera fuente distinta
  de las dos anteriores — ni diccionario ni benchmark, sino normativa
  oficial citada directamente (AVL admite "dos" también en femenino como
  forma natural valenciana; el IEC exige "dues" en femenino de forma
  obligatoria). Es la única regla que no es una sustitución de texto fija:
  requiere que el modelo identifique el género del nombre que acompaña a
  "dos" en cada frase.
- **Léxico diferencial** (`lexico_fiable.json`, 194 parejas): descrito en
  la sección 4.

## 3. Selección del modelo de traducción

Se construyó un benchmark de 60 frases valencià→català con referencia
humana (`pipeline/03_seleccio_de_model/benchmark_corpus.json`) y se probaron varias
opciones:

| Modelo | BLEU | chrF | chrF++ | Notas |
|---|---|---|---|---|
| Sistema de reglas deterministas (sin LLM) | 80,5-85,9 | 91,3-95,5 | 90,3-94,5 | Baseline: solo sustituciones de texto, sin entender contexto |
| NLLB-200-distilled-600M | 53,13 | 76,67 | 75,00 | Traductor genérico, sin prompt dialectal — confirma que la ventaja de los LLM viene del prompt, no solo del tamaño |
| llama3.1:8b | 57,2-73,6 | 69,3-85,7 | 68,2-84,7 | Descartado, muy inconsistente entre ejecuciones |
| qwen2.5:7b | 72,0-77,8 | 85,7-89,0 | 84,8-88,1 | Peor que la versión 14b |
| **qwen2.5:14b** | **75,3-92,90** | **89,3-96,86** | **88,4-96,57** | Elegido — ver evolución abajo |
| salamandra-7b-instruct (BSC) | 75,7-86,7 | 89,2-93,8 | 88,8-93,4 | Probado como alternativa más barata (mitad de parámetros); descartado al final, ver sección 6 |

**Por qué qwen2.5:14b**: mejor combinación de calidad y consistencia entre
ejecuciones, y con un margen de mejora claro a medida que se afinaba el
prompt (ver tabla de evolución). Se ejecuta vía Ollama local, con
`temperature=0` y `num_predict=200` para reproducibilidad.

### Evolución de qwen2.5:14b según se mejoraba el prompt y el léxico

| Fecha | BLEU | chrF | chrF++ | Qué cambió |
|---|---|---|---|---|
| 2026-09-08 | 84,02 | 92,34 | 91,84 | Versión validada inicialmente, prompt con 7 reglas + `palabras_traducidas.json` (1.604 formas, sin revisar a fondo) |
| 2026-09-16 | 83,58 | 92,27 | 91,73 | Cambio a `lexico_fiable.json` (65 entradas revisadas a mano) — bajada mínima esperable al reducir mucho el léxico bruto, ganancia en fiabilidad |
| 2026-09-17 (mañana) | 87,56 | 94,28 | 93,87 | Léxico ampliado a 194 entradas (`paralelos.txt` revisado), reglas de gentilicis/ordinals añadidas |
| 2026-09-17 (mediodía) | 90,87 | 95,86 | 95,55 | Reglas de pretèrit perifràstic, protección de instituciones, elisión automática, aviso anti-alucinación |
| 2026-09-17 (tarde) | **91,08** | **95,34** | **95,06** | Regla de concordancia de género "dos/dues" — exactos sube de 23/60 (38,3%) a **30/60 (50,0%)** |
| 2026-09-18  | **92,2** | **98,86** | **96,57** | Mejora del benchmark y haciendo el system prompt más robust para los apóstrofe |

La lección de esta tabla: **el modelo no cambió en ningún momento** — toda
la mejora (84→92 BLEU) vino de afinar el prompt y el léxico a partir de
analizar los errores reales, no de buscar un modelo más grande o más caro.

## 4. El léxico: de `palabras_traducidas.json` a `lexico_fiable.json`

El léxico original (`pipeline/03_seleccio_de_model/palabras_traducidas.json`, ~1.600
entradas) se descartó del pipeline por no ser una fuente fiable —mezclaba
entradas sin revisar de origen incierto, encontradas solo al auditar el
corpus generado (ver sección 6). Se sustituyó por `lexico_fiable.json`,
construido enteramente con parejas confirmadas:

- 31 parejas de los 368 términos que Apertium marca explícitamente como
  valencianos (`v="val_gva"` exclusivo), con su forma catalana confirmada
  dentro del mismo diccionario.
- 34 parejas de una fuente externa curada (contrastius_paula_guerrero).
- 129 parejas de `paralelos.txt`, revisado a mano por el autor del
  proyecto, tras filtrar sistemáticamente las que ya cubría una regla
  general (posesivos, numerales, "vesprada"...) y reducir las locuciones
  multi-palabra a la única palabra que realmente cambia.

**Total: 194 entradas**, todas con origen documentado (campo `origen` en
cada entrada del JSON).

## 5. Comparativa final qwen vs. salamandra-7b-instruct

Con el léxico y las reglas ya maduros (17/09), se hizo una comparación
limpia entre los dos modelos con mejor resultado, cada uno con su mejor
prompt:

| | qwen2.5:14b | salamandra-7b-instruct |
|---|---|---|
| BLEU | **92,90** | 86,29 |
| chrF | **96,86* | 93,62 |
| chrF++ | **96,57** | 93,17 |
| Exactos | **31/60 (51,7%)** | 19/60 (31,7%) |
| Parámetros | 14,8B | 7,8B (la mitad) |

(qwen2.5:14b con la regla de concordancia "dos/dues" añadida después de
esta comparativa — salamandra no se ha vuelto a probar con ella.)

Salamandra llegó a estar casi empatada en un punto intermedio (86,74 vs.
87,56 BLEU), pero al reforzar el prompt con más reglas explícitas mostró
ser un modelo más frágil: en vez de mejorar de forma fiable como qwen,
a veces empeoraba — se detectaron colapsos parciales a español
("Tirar el cap... por encima de algo") y nuevas fugas de literales del
prompt que no aparecían antes. **Decisión: qwen2.5:14b para la generación
completa del corpus.** Salamandra queda documentada como alternativa válida
y mucho más barata de ejecutar, por si se quiere un segundo corpus de
comparación en el futuro.

## 6. Auditoría de calidad del corpus (primera generación, v1)

Antes de dar por bueno el primer corpus generado (46.315 frases, con el
léxico y prompt de la versión inicial) se hizo una auditoría completa
(`dades/sintetic/analisi_corpus.html`), contrastando cada regla
documentada contra lo que el modelo hizo de verdad en las 46.315 frases
reales, no solo confiando en el benchmark de 60 frases.

### Bugs encontrados y corregidos (sin volver a traducir nada)

Corregidos con `pipeline/04_corpus_sintetic/repara_corpus.py` — manipulación de texto
sobre el corpus ya generado:

| Problema | Casos | Causa raíz | Arreglo |
|---|---|---|---|
| El literal `"Frase a traduir:"` se colaba en la respuesta | 1.165 | Fuga de una etiqueta del prompt | Texto eliminado; el resto de la respuesta ya era válido |
| `"blanca"` (adjetivo) confundida con `"Blanca"` (nombre del pájaro *garsa*) | 28 | Entrada de léxico polisémica sin filtrar | Revertido; la entrada ya no está en `lexico_fiable.json` |
| `"pròxim"` confundido con el sentido religioso `"proïsme"` | 45 | Ídem | Revertido; ídem |
| `"Ramon"`/`"Manuel"` tratados como variantes dialectales | 32 + 51 | Nombres de persona en el léxico | Revertido + arreglado de raíz (`categoria=="nombre"` se excluye en `carrega_lexic()`) |
| Subjuntivos sin convertir (`siga`, `siguen`, `tinga`, `tinguen`) | 289 | El modelo no aplicaba la regla de forma consistente | Corregido con sustitución determinista |
| `Vila-real → Vila-reial` (topónimo alterado) | — | El léxico viejo tenía `real→reial`, y el glosario dinámico se lo sugería aunque fuera un topónimo | ✅ Resuelto de raíz: `real` no está en `lexico_fiable.json` |

**Lo que NO se corrigió a propósito**: `vinga`→`vingui` y `fora`→`fos`
tienen homonimia real (*"vinga!"* interjección, *"fora"* = fuera) — revertir
a ciegas habría introducido errores nuevos. Y `Beneixida → Benedita`
(el modelo "corrige" un topónimo real como si fuera una errata): no hay
ninguna pista de léxico aquí, es un límite del propio modelo, no del
prompt — no se puede arreglar con reglas.

### Estado del corpus v1 (con el léxico y prompt anteriores a esta ronda de mejoras)

| | |
|---|---|
| Frases únicas totales | 46.315 |
| Con alguna marca de sospecha | 663 (1,43%) |
| Limpias | 45.652 (98,57%) |
| Compliance medio de las reglas morfológicas | 96,7% |

**Hallazgo importante de la revisión manual** (200 frases seguidas
revisadas a mano, no aleatorias): de esas 200, un 21,2% tenía algún
problema — muy por encima del 1,43% que marcaban las comprobaciones
automáticas. La mayoría de esos errores no eran incumplimientos de una
regla conocida, sino alucinaciones puntuales del modelo (sustituciones
léxicas sin relación con ninguna regla dialectal) — un tipo de error que
ninguna comprobación automática basada en reglas puede detectar. Esto es
la razón principal por la que se ha invertido tanto esfuerzo en afinar el
prompt (sección 3) antes de dar el corpus por definitivo.

## 7. Estado actual y siguiente paso

Con el léxico, el prompt y las reglas ya maduros (qwen2.5:14b, BLEU 91,08
en el benchmark), se está regenerando el corpus completo desde cero
(v2) con esta configuración, en el clúster SLURM. El corpus v1 descrito en
la sección 6 queda en `dades/sintetic/` como referencia
histórica de la auditoría, pero **el fichero a usar es el de la
regeneración v2** una vez termine — ver `pipeline/04_corpus_sintetic/README.md` para
las instrucciones de ejecución y `pipeline/04_corpus_sintetic/slurm/` para los
scripts de SLURM.

## 8. Limitaciones conocidas

- **El corpus es sintético** — lo genera un LLM, no un traductor humano. Un
  modelo entrenado con esto puede acercarse a la calidad de qwen2.5:14b en
  esta tarea, pero no superarla; el techo de calidad es el del modelo que
  lo generó.
- **Registro concentrado**: el texto fuente es institucional/normativo
  (glosario, gramática, textos legales, notas de prensa de la AVL). Un
  modelo entrenado solo con esto traducirá bien ese registro y
  probablemente peor cualquier otro (conversación, prensa informal,
  literatura).
- **El benchmark de 60 frases tiene poca potencia estadística** para
  patrones raros (algunos patrones solo se han visto 2-4 veces en total) y
  está algo sesgado hacia frases metalingüísticas (que hablan del
  significado de palabras, típico del glosario de la AVL) — no
  necesariamente representativo de todo el corpus.
- **Validación contra texto humano pendiente**: para saber si un futuro
  modelo generaliza más allá de este corpus sintético, convendría validar
  contra traducciones de origen humano (ver `dades/boe/`, traducciones
  oficiales del BOE — explorado en paralelo pero fuera del alcance de este
  documento).

## 9. Auditoría de la fuente (21/09) — el corpus base, no el modelo

Al revisar a mano una muestra generada con qwen2.5:14b + `lexico_fiable.json`
ya maduros, la calidad seguía sin convencer. Antes de tocar el prompt o
probar otro modelo otra vez, se auditó `dades/avl/final/dialectal/corpus_occidental_net.jsonl`
(1.778 documentos) reproduciendo exactamente la segmentación de
`genera_corpus_sintetico.py::extreu_frases_document()` sobre las 48.037
frases candidatas reales. Conclusión: **el cuello de botella está en la
fuente, no en el modelo ni en el prompt.**

### Lo que NO es el problema

Contaminación de idioma (miedo inicial: castellano/inglés colándose):
mucho más baja de lo esperado.

| | frases | % del total |
|---|---|---|
| Con marcadores claros de castellano (`ñ` o ≥2 palabras solo-castellanas) | 194 | 0,4% |
| Con marcadores claros de inglés (≥3 palabras solo-inglesas) | 31 | 0,1% |

Casi todos los casos de castellano son citas literales dentro de textos
*sobre* filología (el `Diccionario de la lengua española de la RAE`
citado en un artículo en valenciano, sentencias del TS citadas en
`legislacio`) — ruido real pero minúsculo en volumen.

### Lo que SÍ es el problema

**(a) La segmentación corta frases por la mitad en un tipo de documento
concreto.** `extreu_frases_document()` separa primero por párrafo
(`text.split("\n")`) y solo luego busca el punto final. Cuando el HTML
origen tenía una palabra en negrita/enlazada en medio de una frase (muy
habitual en la columna de vocabulario `glossari` de la AVL, donde la
palabra del día aparece resaltada), la limpieza previa del scraping
convierte eso en un salto de línea, así que la frase se trocea en dos
"documentos" separados y cada mitad pasa los filtros como si fuera una
frase completa e independiente:

```
"Això fa que, a voltes, una paraula puga despertar reaccions diferents
en els parlants ... segons el contacte més o menys habitual amb al"
"És el que passa quan ens trobem amb la paraula"          <- corte real, aquí iba "furri"
```

`glossari` es **el 34% de todas las frases candidatas del corpus**
(16.334 de 48.037, desde 1.394 documentos) — es el tipo de documento
más grande con diferencia, así que este corte afecta a una fracción
importante del total, no a un puñado de casos sueltos.

**(b) Concentración extrema en 5 documentos.** `publicacions` es el
**29,3% de todas las frases** (14.087 de 48.037) pero viene de solo
**5 PDFs** (los manuales `MANUALS_01/02/03`, `Recerca_02`,
`Documents_05`, extraídos con `pdf_extractor.py`, 100-370K caracteres
cada uno). Casi un tercio del corpus repite el registro y los posibles
artefactos de extracción PDF (saltos de página, notas al pie, guionado)
de un puñado de libros, no de una muestra diversa de fuentes.

**(c) Fragmentos que no son frases** (títulos de ley, tablas de
encuestas con porcentajes, listados de autores/créditos, formularios):
al menos 1.715 casos (3,6%) detectados por heurística simple de
"demasiadas mayúsculas seguidas" — probablemente más si se afinara la
detección, ya que la heurística no captura frases gramaticalmente
incompletas que sí pasan el filtro de longitud (ver ejemplo del
`gramatica_normativa`: `"millor que les de en + infinitiu."` o
`"Però, en el cas concret del participi"`, fragmentos de una
explicación con viñetas, no oraciones).

### Plan de limpieza propuesto (por orden de impacto, no de esfuerzo)

1. **Arreglar el corte por salto de línea en `glossari`** — antes de
   dividir por párrafo, reunir líneas que no terminan en puntuación
   fuerte con la siguiente (o revisar la limpieza HTML→texto en el
   scraping para que no inserte el salto en mitad de frase). Máximo
   impacto: toca al 34% del corpus con un cambio acotado.
2. **Filtrar fragmentos no-frase**: exigir que la frase empiece por
   mayúscula y acabe en `.!?…` (ahora mismo no se comprueba), y
   descartar líneas con ratio de mayúsculas o de dígitos alto — cubre
   el problema (c).
3. **Reponderar o auditar aparte los 5 PDFs de `publicacions`** —
   revisar una muestra manual de esos documentos en concreto para ver
   si el texto extraído tiene artefactos propios de PDF, y considerar
   limitar cuántas frases se toman de un mismo documento para que no
   domine el corpus.
4. Solo después de (1)-(3): repetir el benchmark de 60 frases y decidir
   si de verdad hace falta tocar el prompt o el modelo otra vez —
   ahora mismo no se puede saber cuánta de la mala impresión al revisar
   la muestra viene del modelo y cuánta viene de pedirle que traduzca
   frases ya rotas de origen.

### Sobre probar otros modelos ahora

Salamandra-7b-instruct ya se probó a fondo (sección 5) y perdió
claramente contra qwen2.5:14b (BLEU 86,29 vs 92,90; colapsos parciales a
español bajo prompts más exigentes) — no es que no se haya intentado.
Merece la pena reconsiderarlo, u otros modelos, **después** de limpiar
la fuente, no antes: si la entrada tiene frases rotas, ningún modelo va
a dar buen resultado con ellas, y una comparación de modelos sobre
datos rotos no es fiable.

### Arreglo aplicado (21/09): reunió de talls de negreta

Implementado en `genera_corpus_sintetico.py` (`uneix_talls_de_negreta()`,
llamado al principio de `extreu_frases_document()`): cuando una línia no
acaba en puntuació forta i la línia següent comença en minúscula, es
tracten com una sola frase partida pel raspat, no com dos paràgrafs
independents. Impacte real, mesurat sobre el mateix corpus font:

| | Abans | Després |
|---|---|---|
| Frases candidates totals | 48.037 | 29.585 (-38%) |

És a dir: més d'un terç del que es comptava com a "frase" abans eren
trossos trencats (típicament a `glossari`, on la paraula destacada de
l'article quedava en una línia a part). Pendent encara: filtrar
fragments que no són frase (títols, taules, llistes de noms — punts (b)
i (c) de dalt), que no arregla este canvi.

## 10. Comparativa definitiva (22/09): qwen vs. gemma3 vs. salamandra vs. SalamandraTA

Comparativa completa en el mismo benchmark de 60 frases, 4 candidatos en
paralelo sobre el clúster SLURM (script y detalle completo en
`pipeline/03_seleccio_de_model/comparativa_salamandraTA_gemma/`):

| Modelo | BLEU | chrF | chrF++ | Exactas |
|---|---|---|---|---|
| **qwen2.5:14b** | **93,11** | **96,90** | **96,64** | **32/60 (53,3%)** |
| gemma3:12b | 91,01 | 95,71 | 95,45 | 32/60 (53,3%) |
| salamandra-7b-instruct (hdnh2006) | 85,67 | 93,20 | 92,83 | 22/60 (36,7%) |
| SalamandraTA-7b-instruct (plantilla oficial) | 83,54 | 91,27 | 90,69 | 13/60 (21,7%) |
| SalamandraTA-7b-instruct (plantilla + glosario corto) | 83,46 | 91,22 | 90,72 | 13/60 (21,7%) |
| SalamandraTA-7b-instruct (con reglas dialectales completas) | 1,75 | 13,31 | 11,74 | 0/60 (0,0%) |

**Conclusión: qwen2.5:14b se mantiene como mejor opción.** Dato interesante:
gemma3:12b (más pequeño, sin especializar en catalán) queda prácticamente
empatado en exactas y muy cerca en BLEU/chrF — alternativa real si algún
día se necesita un modelo más barato de correr.

### SalamandraTA: por qué no compensa, ni siquiera siendo "el especializado"

Se probó de tres formas, la tercera pensada específicamente para descartar
que el problema de la segunda fuera solo "el prompt es demasiado largo":

1. **Plantilla oficial de traducción** (`"Translate the following text from
   Catalan (Valencian variety) into Catalan..."`) — funciona, pero por
   debajo de los demás (83,54 BLEU). SalamandraTA trata valencià y català
   como una sola entrada de idioma; no hay garantía de que distinga bien
   la dirección dialectal, y el resultado lo confirma.
2. **La misma plantilla + un glosario dinámico corto** (formato
   `[VOCABULARI: este=aquest, roig=vermell]`, el mismo formato compacto —
   pensado explícitamente para no ser repetido — que ya usan qwen/gemma sin
   problema). Resultado: 83,46 BLEU, prácticamente idéntico al anterior
   (diferencia dentro del ruido). Conclusión: el modelo no aprovecha
   pistas adicionales de ningún tamaño, no es una cuestión de longitud de
   prompt que se pudiera seguir afinando — simplemente no incorpora nada
   más allá de su plantilla exacta de traducción.
3. **El mismo system prompt de reglas dialectales completas que usamos con
   qwen/gemma** — inutilizable: en vez de aplicar las reglas, el modelo
   repite fragmentos literales de las propias instrucciones como si fueran
   la traducción (p. ej. devuelve `"ELISION (només 'de', 'la', 'el')..."`
   en lugar de traducir la frase). Confirma lo que ya advertía el propio
   model card de BSC-LT: es un modelo *de traducción*, no un instructor de
   propósito general — no sabe qué hacer con una instrucción compleja en
   el system prompt.

### El camino hasta llegar a estos números (infraestructura, no el modelo)

Antes de tener este resultado se encontraron y resolvieron, en orden,
cuatro problemas reales de infraestructura del clúster (nodo "abaco", 8
GPUs RTX 2080 Ti de 11 GB, arquitectura Turing/compute capability 7.5) —
documentados con detalle en `pipeline/03_seleccio_de_model/comparativa_salamandraTA_gemma/README.md`:

1. `pip install` directo rechazado (`externally-managed-environment`,
   PEP 668) → entorno virtual dedicado en `~/venv_vllm`.
2. `vllm` sin fijar versión trae la última (0.29.0), que ya no soporta
   `bitsandbytes` como método de cuantización.
3. Esa misma última versión de vLLM exige PyTorch compilado para CUDA
   13.0, más nuevo que el driver del nodo (12.9) → vLLM fijado a la
   versión `0.9.2`, confirmada compatible con CUDA 12.4.
4. vLLM 0.9.2 choca con versiones recientes de `transformers` (conflicto
   de registro `'aimv2'`) → `transformers` fijado a `<4.54.0`.
5. `fp8` (pensado para cuantizar y caber en 1 GPU) no lo soporta el
   hardware Turing (exige compute capability ≥80, este nodo tiene 75) —
   límite real de hardware, no de configuración.
6. `bfloat16` (el dtype por defecto) TAMPOCO lo soporta Turing en cómputo
   — solución: repartir el modelo sin cuantizar en `float16` entre 2 GPUs
   con `--tensor-parallel-size 2`.
7. El prompt largo de reglas dialectales (~2200 tokens) no cabía en el
   `--max-model-len` recortado que se había fijado pensando en ahorrar
   memoria para una cuantización que al final no hizo falta.

Ninguno de estos problemas era del modelo en sí — todos eran de encaje
entre versiones de software y las GPUs concretas de este clúster. Vale la
pena dejarlo anotado por si se repite el ejercicio con otro modelo servido
por vLLM en el mismo nodo.

## 11. El motor de reglas deterministas (`traductor/`)

Las secciones 1-10 cubren las etapas 1-4 (scraping, reglas, selección de
modelo, corpus sintético), cerradas a finales de septiembre. Desde
entonces el foco real del proyecto, durante semanas, ha sido `traductor/`
— un paquete Python independiente, sin prefijo numérico porque no es una
etapa de un solo uso sino el producto que las demás etapas alimentan.

### Por qué un motor de reglas, no solo un LLM

La sección 6 ya documentó el problema: un LLM que reescribe la frase
entera "alucina" — introduce errores léxicos sin relación con ninguna
regla dialectal, indetectables por verificación automática. Un motor de
reglas deterministas no tiene ese problema por diseño: si no reconoce una
palabra o construcción, la deja exactamente igual en vez de arriesgarse a
inventar algo. El coste es que no resuelve nada que no esté en sus datos
ni en sus reglas — de ahí que, más adelante (sección 13), se añada un LLM
otra vez, pero solo para los puntos muy concretos donde el motor decide
expresamente no actuar, nunca para reescribir la frase.

### Arquitectura

El motor tokeniza el texto y etiqueta cada token con spaCy
(`ca_core_news_md`, o `ca_core_news_sm` si no está): categoría, género,
lema y forma verbal. Después encadena capas fijas, cada una `.apply()`
sobre los tokens, saltando cualquiera ya marcado por una capa anterior.
Cada dirección tiene su propio paquete y su propio orden de capas
(estado del 23/10/2026):

| | valenciano → catalán (`rules/val_cat/`, aparcado) | catalán → valenciano (`rules/cat_val/`) |
|---|---|---|
| 1 | `lexic` — léxico general | `lexic` — léxico general, frases de 2-3 palabras, homógrafos resolubles con spaCy, artículo y apóstrofo |
| 2 | `conjugacions_dict` — formas verbales | `conjugacions_dict` — formas verbales, con spaCy en las que tienen lectura no verbal |
| 3 | `possessius` | `possessius` |
| 4 | `numerals` | `numerals` |
| 5 | `concordanca_dos_dues` | `concordanca_dos_dues` |
| 6 | `relatiu_on` — "a on" → "on" | `demostratius` — aquest → este, aqueix → eixe |
| 7 | `demostratius` | `incoatius` — -eix → -ix, propuesto por spaCy y validado por el diccionario |
| 8 | `accentuacio` | `accentuacio` — -ès → -és |
| 9 | `incoatius` | `per_a_infinitiu` — per + infinitivo → per a |
| 10 | `combinacio_li` — li'l → l'hi | — |

En valenciano → catalán, además, se protegen las palabras en mayúscula
que no inician la frase (posibles nombres propios); en catalán →
valenciano ya no (22/10/2026, ver sección 12).

Todos los datos vienen de **dos ficheros**, `traductor/data/lexic_general.json`
y `conjugacions_dialectals.json`, copias sincronizadas con
`traductor/sync_data.py` desde las fuentes del proveedor
(`pipeline/02_regles_dialectals/lexic/diccionarios/`). `traductor/` nunca
lee esa carpeta en tiempo de ejecución, solo sus propias copias, para poder
funcionar como módulo autónomo. Desde el 22/10/2026 no queda ningún fichero
de datos hecho a mano, y en catalán → valenciano tampoco ninguna lista de
palabras en el código (sección 12); en valenciano → catalán quedan tres
listas de excepciones gramaticales (`SEMPRE_VERB` en `conjugacions_dict`,
`_EXCEPCIONS` en `incoatius` y `_EXCEPCIONS_ES` en `accentuacio`).

### Evolución y hallazgos reales, valenciano → catalán

El motor se redujo el 30/09/2026 a puro lookup de diccionario (sin
reconstrucción morfológica propia), basado casi enteramente en un
diccionario diferencial de ~53.000 pares aportado por un colaborador del
equipo (el proveedor de datos): 1.471 de léxico general más ~52.000 formas verbales
conjugadas, además de demostrativos/posesivos/numerales. A partir de ahí,
cada mejora se midió contra un benchmark curado de 151 frases
(`pipeline/03_seleccio_de_model/benchmark_corpus.json`), nunca solo con
los tests automáticos (`doctests`) — el proyecto ha tenido regresiones
reales que pasaban con los doctests en verde.

Progreso medido: 92/151 → 119/151 (cuatro confirmaciones independientes,
local y en el clúster) → 120/151 al corregir un bug real ("o siga" se
trataba como locución congelada idéntica en los dos dialectos; medido
contra el único caso real del benchmark, es falso — es un par dialectal
normal) → **115/151 hoy**, tras retirar una regla que solo acertaba en
las frases exactas del benchmark sin generalizar a ninguna frase nueva
(detalle en la sección 16).

**Motor + postprocesado con LLM (sección 13): récord de 129/151 (85,4%),
BLEU 98,64, chrF 99,55**, confirmado en el clúster de la universidad.

### Catálogo de los fallos que quedan

El catálogo completo y categorizado de los fallos residuales de
val→cat vive en `traductor/README.md`, sección "ANÀLISI DE FALLADES
RESIDUALS" — la mayoría son casos donde una misma grafía valenciana
cubre dos formas catalanas distintas (indicativo/subjuntivo en 3ª
plural, 9.220 de las ~53.000 formas del diccionario) y el motor,
siguiendo la misma disciplina de "no generalizar sin evidencia", prefiere
dejarlos sin tocar antes que arriesgarse a acertar por casualidad.

## 12. La dirección inversa: catalán → valenciano

A partir del 08/10/2026 se construyó desde cero una segunda dirección,
`traductor/rules/cat_val/`, simétrica a la original en estructura (11
ficheros, mismo nombre de módulo con sufijo `Invers`) pero no en
contenido — cada regla se midió contra el benchmark invertido
(catalán como entrada, valenciano como referencia) desde evidencia
propia, nunca asumiendo que lo que valía para una dirección valía para la
otra.

### El hallazgo estructural más importante

Los dos problemas más grandes de val→cat (homógrafos verbales raros
colisionando con sustantivos comunes, y la colisión indicativo/subjuntivo
de 3ª plural) son **estructuralmente asimétricos**: de 50.526 formas
catalanas únicas en el diccionario de conjugaciones, solo 346 (0,68%)
tienen más de un candidato valenciano real — frente al 20% de formas
valencianas problemáticas en la dirección original. La razón es simple:
el catalán de entrada siempre distingue por escrito lo que el valenciano
funde en una sola grafía (p. ej. "creuen" indicativo / "creuin"
subjuntiu), así que el modo verbal "ya viene resuelto" por cómo está
escrito el catalán — no hace falta ningún mecanismo equivalente a la
protección que sí hace falta en val→cat.

### "aquest", la ambigüedad real que sí existe en esta dirección

El catalán oriental contemporáneo ha colapsado un sistema demostrativo de
tres grados a dos: "aquest" cubre tanto el valenciano "este" (1r grado)
como "eixe" (2n grado). Esto es una ambigüedad genuina de proximidad
discursiva, no gramatical — ninguna señal del texto (ni categoría
gramatical, ni género) la resuelve por sí sola. Medido alineando las 151
frases palabra a palabra: de 52 apariciones reales donde "aquest*"
cambia de verdad, 40 van a "este" y 12 a "eixe" (~77%/23%). El motor
aplica "este" por defecto — un valor medido, no una suposición — con
ese 23% de error conocido y aceptado. Es, con diferencia, el bucket más
grande de fallos residuales de esta dirección.

### Progreso medido (histórico, hasta el 14/10/2026)

Las cifras actuales están al final de esta sección y en la sección 17.

92/151 → 118/151 (Fase 2: reconstrucción del paradigma demostrativo,
`relatiu_on`/`incoatius` invertidos, léxico multi-palabra catalán,
exclusión de "ensenyament" del léxico general por registro) → 123/151
(con dos ediciones del benchmark fuente que tunearon la referencia para
coincidir con la salida del motor en ese momento — ver nota de
transparencia en la sección 16) → **116/151 hoy**, tras la misma
retirada de reglas sin generalizar que afectó a val→cat.

### Verbos incoativos: spaCy propone, los diccionarios validan (20/10/2026)

Los verbos incoativos de la tercera conjugación (servir, oferir,
produir…) intercalan un incremento entre la raíz y la terminación del
presente: "-eix-" en catalán central (serveix, serveixes, serveixen) y
"-ix-" en valenciano (servix, servixes, servixen). Es el patrón de fallo
más frecuente de esta dirección: en las 2.109 frases de los dos corpus,
el valenciano de referencia usa "-ix" en 198 de 198 casos reales.

El fallo tiene dos causas que se suman. La primera está en los datos: la
AVL admite las dos formas en valenciano, así que el proveedor no las
trata como par dialectal. Su diccionario de conjugaciones trae de
"servir" la primera persona ("serveixo"→"servisc") y todo el subjuntivo,
pero no "serveix"/"serveixes"/"serveixen", que son justo las formas más
usadas. Ningún lookup puede encontrarlas. La segunda es lingüística: en
catalán la terminación "-eix" no identifica un incoativo. Acaban igual
los incoativos en "-ir" (serveix, que sí cambia), los verbos en "-èixer"
(apareix, coneix, creix, que nunca cambian) y palabras que ni siquiera
son verbos (mateix, peix). El valenciano distingue las dos clases de
verbos por escrito; el catalán las funde. La diferencia es léxica, y por
eso la primera versión de la regla dependía de una lista cerrada de
siete raíces escrita a mano, con la cobertura limitada que eso implica.

La solución actual no tiene ninguna lista. Un verbo terminado en "-eix",
"-eixes" o "-eixen" pasa a "-ix" solo si se cumplen tres condiciones:
(1) spaCy lo etiqueta como verbo, lo que descarta "mateix" o "peix";
(2) el lema que propone spaCy acaba en "-ir", lo que descarta "créixer"
o "conèixer"; y (3) ese lema existe como infinitivo en el diccionario de
conjugaciones del proveedor. La tercera condición es la decisiva. spaCy,
entrenado en catalán central, se inventa lemas para los verbos que no
reconoce ("apareix"→*aparir*, "coneix"→*conir*, "neix"→*nir*); como esos
infinitivos no existen en nuestros datos, se descartan solos. Además, la
palabra debe ser exactamente raíz del lema + "eix" + terminación, y la
diéresis se aplica cuando la raíz acaba en vocal sonora ("produïx",
"posseïx", pero "aconseguix"). Es el mismo principio que guía el resto
del motor: **el modelo estadístico propone y los diccionarios validan**,
de modo que un error de spaCy nunca llega por sí solo a la traducción.

Resultado: el banco de 151 frases se mantiene en 136/154 (recupera los
mismos ocho casos que cubría la lista) y gplsi pasa de 1.337 a 1.505
frases exactas de 1.958 (BLEU 90,14→93,05). Frente a no tener la regla,
gana 185 frases y pierde una ("conquereix", que la referencia deja
igual). Quedan fuera, por diseño, los casos en que spaCy no da una
etiqueta fiable: un verbo a principio de frase etiquetado como nombre
propio ("Floreix…") o con un pronombre enclítico pegado ("Serveix-li").

En la misma jornada se fijaron otras dos piezas de esta dirección:

- **Regla de la forma canónica.** Cuando una palabra catalana tiene
  varios candidatos valencianos en el léxico (batlle→alcalde/batle,
  noi→xic/xiquet, llimona→llima/llimó), se elige el marcado
  `canonica: true` por el proveedor, en lugar de dejar la palabra sin
  traducir. La única excepción son los ordinales básicos, donde la
  canónica es la forma culta (quint, sext) y el uso real prefiere la
  popular (cinqué, sisé). Las conjugaciones no traen este campo, así que
  sus 49 formas ambiguas siguen sin traducirse.
- **Artículo apostrofado tras una sustitución.** Si la palabra
  traducida pasa a empezar por vocal, el artículo se apostrofa ("el
  darrer"→"l'últim", "el batlle"→"l'alcalde", "la sortida"→"l'eixida"),
  respetando que "la" no se apostrofa ante *i/u* átonas.

También se comprobó si spaCy podía resolver la otra ambigüedad verbal de
esta dirección: formas como "busqueu" o "sortim", que en catalán se
escriben igual en indicativo, subjuntivo e imperativo mientras el
valenciano las distingue ("cercau"/"cerqueu"). La respuesta es no. El
rasgo `Mood` de spaCy devuelve "indicativo" casi siempre (10 de 35
aciertos con el modelo pequeño, 8 de 35 con el mediano), y decidir el
modo exige entender el verbo principal ("vull que sortim" frente a
"diuen que sortim"). Esos casos, unos 19 en 2.112 frases, se reservan
para la capa de LLM.

### La guía de traducción contrastada con los corpus oficiales (21/10/2026)

Antes de construir una capa de postprocesado con LLM a partir de la guía
de traducción dialectal (pronombres débiles, preposiciones, adverbios de
lugar), se midió cada regla en los dos corpus oficiales: la AVL (2.233
documentos en valenciano) y el BOE (268.000 líneas alineadas catalán y
valenciano). La medida es un porcentaje: cuántas veces el texto oficial
usa la forma que dice la guía cuando aparece el contexto de la regla.

Solo tres reglas tienen evidencia clara, y las tres se pueden aplicar
sin modelo: "per" + infinitivo → "per a" (92% en la AVL, 95% en el BOE;
salvo "per haver", que es causal), "aquí" → "ací" (83% y 100%) y el
relativo "on" sin "a" (80% y 99,6%), lo que obliga a retirar el "a on"
que el motor añadía siguiendo el estilo del banco curado. En cambio, el
valenciano oficial no sigue la guía en los pronombres débiles: escribe
"el", "els" y "en" igual que el catalán ("lo", "los" y "ne" aparecen
entre el 0% y el 2%), y tampoco sustituye "quan" por "en" + infinitivo
(1-11%). Las dos reglas que dependen del significado, "a" → "en" de lugar
(13,9% en el BOE) y "l'hi" → "li'l" (muy rara), son las únicas candidatas
a LLM, con poco volumen. La lección es la misma que con el bloque de
preposiciones del 14/10/2026: una guía normativa describe la lengua en
general, y el registro escrito oficial solo manifiesta una parte; se
mide antes de implementar.

Las tres reglas con evidencia se implementaron el mismo día: "aquí" →
"ací" como un par más del diccionario (sin código), "per a" + infinitivo
como regla nueva que reconoce el infinitivo con spaCy, y la retirada del
"a on". En una muestra de 2.000 líneas del BOE, las frases idénticas a la
referencia oficial pasan de 360 a 368. Los dos bancos no oficiales bajan
(151: 137 → 130; gplsi: 1.524 → 1.486) porque sus traductores siguen otro
estilo en estos puntos ("a on", "per" + infinitivo). Se optó por la norma
oficial. La combinación "l'hi" → "li'l" se descartó como regla: leídos
uno a uno, los casos del BOE muestran cuatro lecturas distintas del
catalán "l'hi" (con "li" + acusativo, con "ho", con "hi" de lugar, con
dativo plural) que solo distingue el significado.

### Todo desde los diccionarios, sin listas a mano (22/10/2026)

El 22/10/2026 se retiraron, por decisión del usuario, todos los ficheros y
listas de palabras hechos a mano. Había dos motivos: algunas listas tapaban
errores de datos en lugar de arreglarlos, y otras tapaban el propio léxico
(el fichero de flexión de género convertía "noies" en "xices" en lugar de
"xiques"). Desde entonces `traductor/data/` solo contiene los dos ficheros
del proveedor, y cada pieza que hacían las listas sale del propio dato:

- **Homógrafos del léxico**: las entradas `problema: "homonimia_lexica"`
  dicen qué forma es ambigua y qué lecturas tiene (`lemas`, con su
  categoría). Si la lectura dialectal tiene una categoría que no comparte
  ninguna otra, el motor solo traduce cuando spaCy le da esa categoría
  ("manca" nombre → "carència"; "manca" verbo, no). Es el mismo mecanismo
  que usa el GD.
- **Homógrafos de las conjugaciones**: el diccionario de conjugaciones ya
  marca en `morfologia` las formas que también son nombre o adjetivo
  ("estat", "través", "obres"); esas solo se traducen si spaCy dice verbo.
  Las de raíz distinta (signar → firmar), que el fichero no marca, siempre
  exigen verbo.
- **Género tras una sustitución**: spaCy da el género de la palabra nueva,
  etiquetándola en dos frases de prueba ("Veig el X ara." / "Veig la X
  ara.") y aceptándolo solo si coinciden. Con él se corrigen el
  determinante, las contracciones y el apóstrofo ("les despeses" → "els
  gastos", "l'habitatge" → "la vivenda").
- **Demostrativos y posesivos**: salen de las entradas `det` del léxico.
- **Regla fija de la forma canónica**: si hay varios candidatos, manda
  `canonica: true`, también en los ordinales (cinquè → quint). Las entradas
  marcadas `_PENDENT` se usan como las demás: es un metadato del proveedor.

El mismo día se cambió a `ca_core_news_md` (misma velocidad, unos 190 MB
más de memoria, mejor género y morfología) y se dejó de proteger las
palabras en mayúscula en esta dirección: el BOE escribe en mayúscula
muchos nombres comunes ("Servei de Salut", "Despeses de personal"), y el
valenciano oficial los traduce. Proteger la mayúscula dejaba mal 439
frases del BOE estricto. El límite aceptado son los topónimos que
coinciden con palabras comunes ("les Garrigues", "la Noguera", "Maó"),
pendientes de que el proveedor los marque.

### Estado del motor catalán → valenciano (22-23/10/2026)

| benchmark | qué mide | frases exactas |
|---|---|---|
| 151 (banco curado; referencia editada por el usuario el 21/10 para seguir la norma) | estilo de un texto concreto | 146/154 |
| BOE estricto completo (9.453 pares con solo diferencias dialectales seguras) | regresiones | 8.857 |
| BOE amplio (muestra de 2.000) | huecos de cobertura | 1.200 |
| gplsi (1.958 frases, dos traductores independientes) | variación real | 1.479 |

Los dos benchmarks "BOE dialectal" se construyeron el 21/10/2026 a partir
del BOE completo alineado (`dades/boe/benchmarks/`, con su README). Desde
entonces son la referencia principal de esta dirección: el estricto
detecta regresiones y el amplio, huecos. Rendimiento en un solo núcleo de
CPU: unas 250 frases por segundo, con unos 700 MB de memoria.

## 13. Postprocesado con modelo de lenguaje ("vía C")

### El problema que el motor deja sin resolver a propósito

Cada vez que se ha intentado una heurística automática amplia en este
proyecto (escaneo automático de género, la distinción "per"/"per a" por
sufijo) el resultado ha sido peor que no tocar nada. En vez de forzar al
motor a adivinar, la decisión de arquitectura (02/10/2026) fue dividir
el problema en dos: el motor traduce y, de paso, deja sin tocar
expresamente los puntos donde no tiene confianza suficiente; un LLM
revisa *solo* esos puntos, con el contexto de la frase — nunca la frase
entera, que es exactamente lo que ya hacen (y por lo que alucinan) las
etapas 3-4 con el corpus sintético.

### El primer caso probado, y las tres formas de usar el LLM comparadas

El caso elegido para el primer experimento (06/10/2026): la ambigüedad
de presente indicativo/subjuntivo de 1ª persona singular en valenciano
("plantege" → "plantejo" indicativo / "plantegi" subjuntiu), 3.004 formas
candidatas identificadas automáticamente desde el diccionario de origen.
Se compararon tres formas de usar el LLM sobre el mismo caso:

| Vía | Qué hace el LLM | Riesgo principal |
|---|---|---|
| A — frase entera | Traduce toda la frase desde cero | Puede alterar partes que ya estaban bien |
| B — solo la palabra | Traduce solo la palabra marcada, con contexto | Puede "inventar" una forma que no es ninguno de los dos candidatos conocidos |
| C — clasificación | Solo clasifica indicativo/subjuntivo; la forma final sale de una tabla ya conocida | Ninguno — nunca genera texto nuevo |

Resultado sobre 17 frases reales del BOE, dos modelos:

| Vía | qwen2.5:14b | qwen3:8b |
|---|---|---|
| A | 5/17 (29%) | 6/17 (35%) |
| B | 11/17 (65%) | 10/17 (59%) |
| **C** | **14/17 (82%)** | **13/17 (76%)** |

La vía C gana con margen en los dos modelos, y además es la más rápida
con diferencia (entre 7 y 50 veces más rápida que la A, porque solo
genera una palabra de salida en vez de regenerar la frase o la forma
catalana completa) — la decisión de arquitectura queda reforzada desde
dos ángulos independientes, precisión y coste, no solo uno.

### Integración real sobre el benchmark completo

Un primer intento de integrar la detección sin ningún filtro adicional
**empeoró** el benchmark (89/150 → 78/150): de 28 palabras detectadas
como candidatas, solo 2 eran verbos ambiguos de verdad; las otras 26 eran
sustantivos/preposiciones homógrafas que el motor ya dejaba
correctamente sin tocar, y que el LLM, obligado a elegir entre
indicativo/subjuntivo, convertía en verbos inventados. Corregido
añadiendo una tercera respuesta explícita ("ninguno de los dos") cuando
la palabra marcada no funciona como el verbo ambiguo en ese contexto
concreto — verificado sin excepción en 6 combinaciones de modelo × vía
sobre el benchmark completo tras la corrección.

### Estado en producción (14/10/2026)

La integración final (`pipeline/08_traduccio_corpus/postprocessat_llm/benchmark_integrat.py`)
es un script envoltorio que replica las 9 reglas por fuera de
`traductor/`, no un cambio dentro de la clase `Token` del motor como se
planteaba originalmente — un camino más sencillo y de menos riesgo que
se acabó eligiendo en la práctica. **Récord actual: `qwen3:8b` + vía C,
129/151 (85,4%)** en val→cat, confirmado en el clúster
(`slurm/genera_resultats_complet.sh` es el flujo normal para lanzarlo).

Un intento análogo para cat→val (desambiguar "aquest"→"este"/"eixe" con
el mismo patrón de vía C) se probó y **empeoró** el resultado (113→98/151
con `qwen2.5:14b`) por dos fallos metodológicos identificados — el
criterio se calibró con una muestra de solo 6 casos sesgada al caso
minoritario, y se validó contra esa misma muestra en vez del benchmark
completo. Queda aparcado, a retomar con `qwen3` y un criterio más
exigente, no descartado por imposibilidad de fondo.

### La capa de LLM tras la evaluación completa (21/10/2026)

Se construyeron dos capas de LLM, una por dirección, dentro de
`traductor/llm/`: el motor marca los puntos ambiguos con opciones
cerradas y el modelo solo elige una etiqueta, así que no puede inventar
texto. Evaluadas en el clúster con qwen3:8b sobre el banco curado y 2.000
líneas del BOE, el resultado fue muy distinto en cada dirección.

En catalán a valenciano la capa no cambió ninguna frase. El demostrativo
"aquest" se desactivó porque el modelo empeoraba el valor por defecto
("este" acierta el 94,5% en el BOE y el 100% en el banco curado: en los
textos oficiales "este" y "eixe" anafóricos alternan por estilo, sin una
señal en la frase), y la combinación "l'hi" no aparece en esas muestras.
La capa se retiró: la herramienta de catalán a valenciano funciona sin
modelo de lenguaje, lo que encaja con su destino, equipos solo con CPU.
(Para los homógrafos se añadió después una capa opcional distinta, con un
modelo de lenguaje pequeño que solo puntúa frases: ver el último apartado
de esta sección.)

En valenciano a catalán la capa sí aporta. En el BOE, el modo verbal que
el valenciano escribe igual en indicativo y subjuntivo pasa de acertarse
un 20% de las veces (motor solo) a un 71%; en el banco curado, las frases
exactas suben de 100 a 109. La capa se queda congelada, con sus errores
catalogados: sobre todo, distinguir el relativo normativo de los textos
legales ("trabajadores que tengan…") del relativo real, y dos fallos que
no necesitarían modelo (la primera persona sin sujeto "jo" y el
subjuntivo detrás de "si").

### Homógrafos de catalán a valenciano: de las preguntas a la perplejidad (22-23/10/2026)

Retirada la capa de catalán a valenciano, quedaban dos tipos de palabra
que el motor no puede resolver con reglas ni con spaCy:

- **Colisiones** (`problema: "colision_homonima"`): una palabra catalana
  con dos traducciones valencianas igual de válidas y ninguna canónica.
  Hoy son "cop" (colp / vegada) y su plural "cops" (colps / vegades). El
  motor no las traduce.
- **Homógrafos irresolubles** (`homonimia_lexica` cuyas lecturas comparten
  categoría): "calces" (bragues / la prenda histórica), "gandula" y
  "gandules" (tumbona / persona vaga). El motor las traduce siempre.

**Primer intento, 22/10/2026: preguntar a un LLM.** Se le preguntaba si la
palabra tenía tal sentido (sí/no) o se le pedía traducirla al castellano.
Con qwen2.5:7b, qwen3:8b y qwen3:4b el resultado fue el mismo que sin
modelo (7/14): los modelos no conocían estas palabras, y la pregunta de
sí/no los sesgaba hacia el "no". qwen2.5:14b acertaba, pero tardaba unos
12 segundos por respuesta en CPU. La capa (`traductor/llm/cat_val.py`)
quedó aparcada.

**Método adoptado, 23/10/2026: perplejidad con un modelo de lenguaje
pequeño.** En lugar de preguntar, el motor construye la frase valenciana
**completa** de cada candidato, con el artículo y la concordancia ya
corregidos ("Una vegada acabada la reunió…" / "Un colp acabada la
reunió…"), y un modelo de lenguaje calcula la probabilidad de cada frase:
la suma de los logaritmos de la probabilidad de cada trozo dado lo
anterior. Gana la más probable. El modelo no genera texto ni recibe
instrucciones: solo puede elegir entre candidatos del diccionario, y con
la misma entrada da siempre el mismo resultado. Es la diferencia con un
LLM usado como asistente: la tecnología es la misma, pero aquí solo se
aprovecha lo que sabe hacer cualquier modelo de lenguaje, notar qué frase
suena natural.

Piezas del método (`traductor/model_llengua/`):

- **Base neutra**: el motor vuelve a traducir la frase con la palabra
  ambigua protegida (`RuleEngineInvers.tradueix_tokens(protegits=…)`), y
  cada candidato se coloca encima; si no, el apóstrofo que el motor mete
  dentro de la palabra ("la gandula" → "l'hamaca") impedía construir bien
  las alternativas.
- **Concordancia por variantes**: el motor solo corrige el determinante
  inmediatamente anterior. Para "molts cops", "un altre cop" o "per primer
  cop" se generan, con las terminaciones regulares del femenino, las
  variantes de las dos palabras anteriores ("moltes", "altra", "primera"),
  y el modelo elige también entre ellas.
- **PMI (λ = 0,5)**: a la puntuación de cada frase se le resta la mitad de
  la log-probabilidad de la palabra sola, para que la frecuencia general
  de una palabra no se imponga al contexto. Decide un caso real casi
  empatado ("Li van donar cops amb un pal").
- **Margen (5 puntos)**: cuando el motor ya ha traducido (irresolubles),
  el modelo solo cambia esa decisión si gana por más de 5 puntos.
- **Capa de spaCy para los irresolubles**: los `lemas` dicen qué
  categorías tiene cada lectura. Si spaCy da una categoría que solo tiene
  la otra lectura ("molt gandula": adjetivo, y la lectura "hamaca" solo
  es nombre), se deja la palabra catalana sin consultar al modelo.

**Modelos comparados**, en CPU: FLOR-760M (projecte-aina, 1,5 GB) y
Salamandra-2B (BSC, 4,5 GB). FLOR fue mejor en todo y el doble de rápido
(1,5 s frente a 3,3 s por frase con palabra ambigua), y es el que se usa.
También se probó puntuar solo el contexto que sigue a la palabra, que
empeoró las colisiones (28/32), y se descartó.

**Un error de datos disfrazado de límite del modelo.** En la primera
medida, el modelo parecía incapaz de separar "gandules" tumbona de
"gandules" persona: elegía siempre dejar la palabra catalana. La causa
era la entrada E0592 del léxico, que daba "hamaces" en lugar de la forma
correcta "hamaques" (como vaca → vaques). El modelo castigaba esa palabra
mal escrita fuera cual fuera el sentido. Corregido el dato, con permiso
del usuario, los dos sentidos quedan separados: diferencia traducir − dejar
de −2,9 a +4,8 en las tumbonas y de −7,1 a −11,7 en las personas, con el
margen de 5 en medio. El modelo sirve así también para encontrar formas
sospechosas del léxico. "calces" sigue sin separarse: el modelo no conoce
el sentido histórico, y queda como el motor ("bragues").

**Resultados** (benchmark de homógrafos: 98 frases escritas para la
prueba con los dos sentidos de cada palabra, más una frase real de gplsi;
referencias = motor + candidato correcto, revisadas a mano):

| tipo | motor solo | con la capa |
|---|---|---|
| colisión (cop, cops) | 0/33 | 31/33 |
| irresoluble (calces, gandula, gandules) | 12/24 | 18/24 |
| resoluble (nou, manca…; decide spaCy en los dos) | 30/40 | 30/40 |

Errores que quedan en las colisiones: "un últim cop al banc" (golpe en
el sentido de robo) y "intent de cop" (golpe de estado sin "d'estat").
En el BOE "cop" aparece en 428 líneas y la referencia valenciana nunca
usa "colp": 117 veces "vegada" y el resto reformula la frase.

**Decisión** (usuario, 23/10/2026): el modelo actúa en las colisiones y en
los irresolubles (con la capa de spaCy delante y el margen); los
homógrafos resolubles siguen con spaCy dentro del motor, aunque con
margen 5 el modelo los mejoraba en la prueba (35/40 frente a 31/40). La
capa es opcional: `translate_cat_val_ml(text)` frente a
`translate_cat_val(text)`, y se evalúa con `evalua_models.py --model
traductor_ml --direccio cat-val`.

## 14. Grado Dialectal (GD)

El 13/10/2026 se implementó una métrica propia, reutilizable sobre
cualquier texto: qué porcentaje de sus palabras dialectalmente marcadas
son formas occidentales (valencianas) frente a orientales (catalanas).

```
GD = total_palabras_occidentales / (total_occidentales + total_orientales)
```

Una métrica parecida (`ratio_occ`) ya existía en `estudi_dialectal.py`
(sección 1), pero contra dos listas curadas a mano de ~70 palabras cada
una. El GD reutiliza en cambio el índice de ~53.000 pares que
`traductor/` ya mantiene para traducir de verdad — mismos datos, sin
inventar nada nuevo, y aplicable a cualquier corpus, no solo a los
documentos ya cargados del scraping de la AVL.

**Dos bugs reales encontrados y corregidos la misma tarde**, a raíz de
que el usuario desconfiara de un resultado concreto viendo el informe
visual: (1) formas verbales raras del diccionario colisionaban con
palabras comunes ("entre" preposición vs. "jo entre" de "entrar"),
inflando el recuento — corregido con el mismo filtro de categoría
gramatical (spaCy) que ya usa el motor para traducir; (2) el tokenizador
trata el apóstrofo como parte de la palabra, así que "d'aquestes" nunca
coincidía con la entrada "aquestes" del diccionario — corregido
reutilizando la misma función que ya resuelve esto en el motor.

Validado de forma consistente contra tres corpus independientes (ver
tabla en la sección 15): el lado valenciano puntúa siempre entre 0,87 y
0,93 de GD, el catalán entre 0,01 y 0,05.

### Homógrafos: spaCy solo decide los que declara el diccionario (21/10/2026)

Al retirar las listas de exclusión del traductor (19/10/2026), algunos
pares reales empezaron a colarse como marcadores falsos porque la forma
tiene un homógrafo común a los dos dialectos. El caso tipo es "després":
el diccionario empareja correctamente el adjetivo catalán "desprès" (que
se desprende de lo que tiene) con el adjetivo valenciano "després", pero
el adverbio "després" (más tarde) se escribe igual y es compartido.

La primera idea fue un filtro general: que ningún marcador contara si
spaCy le daba una categoría distinta de la del diccionario. Se descartó
tras medirlo, incluso con un umbral de seguridad: spaCy, entrenado en
catalán central, no conoce muchas formas valencianas ("hui", "faena",
"seua") y les inventa la etiqueta, a veces con mucha seguridad, así que
el filtro eliminaba marcadores buenos.

La solución final consulta a spaCy **solo para los homógrafos que el
propio diccionario declara**. Las entradas `homonimia_lexica` del
proveedor traen la forma homógrafa (`forma_problematica`), la categoría
de cada lectura (`lemas`, por ejemplo "manc [adj]" y "manca [n]") y la
de la lectura dialectal (`categoria`). Si ninguna otra lectura comparte
esa categoría, la forma cuenta como marcador solo cuando spaCy se la da
("manca" nombre sí, "manca" adjetivo no). Si otra lectura la comparte
("bes": be [n] / bes [n]), spaCy no puede decidir y la forma no cuenta
nunca. El resto de palabras no pasa por spaCy.

| Corpus | Lado valenciano | Lado catalán |
|---|---|---|
| Banco curado (151) | 0,9647 → **0,9749** | 0,1135 → **0,1115** |
| gplsi (1.958) | 0,9341 → **0,9387** | 0,0685 → **0,0632** |

El lado catalán apenas mejora porque "després" (17 casos en cada corpus)
y "tancat" no están declarados como homógrafos en el diccionario; el
mecanismo los filtrará en cuanto se marquen en origen, sin tocar código.
Con "després" declarado, el lado catalán bajaría a alrededor de 0,05 en
los dos corpus. Tampoco se resuelven las palabras compartidas por
registro ("estat", "avui", "últim", "alcalde") ni el par "petit"/"menut",
mal emparejado en los datos.

### Textos sin marcadores, GDV e GDC (26/10/2026)

Un texto sin ninguna palabra marcada no dice nada sobre su dialecto, y
el valor que conviene darle depende de la tarea. Se probó 0,5 y se
descartó, porque se confunde con un texto mezclado a partes iguales.
Por decisión del usuario quedan dos soluciones:

- **`gd.py`** (GD único, 1 = valenciano, 0 = catalán) tiene tres
  modos con el parámetro `dialecte`. Sin él, el GD de esos textos es
  `None` (medida neutra, que no entra en las medias). Con `"val"` vale
  1,0 y con `"cat"` vale 0,0: el texto cuenta como puro en el dialecto
  que se evalúa.
- **`gdv.py` e `gdc.py`** son dos índices simétricos que van los dos
  de 0 (nada puro) a 1 (puro): el GDV es la proporción de marcadores
  valencianos y el GDC la de catalanes. Un texto sin marcadores cuenta
  como puro en los dos (1 y 1). Reutilizan `calcula_gd`. Para un corpus
  dan la cifra global (suma de marcadores) y la media por frase, que es
  donde pesan los textos sin marcadores. En el benchmark de 151: GDV
  del lado valenciano 0,9863 global / 0,9930 media (14 frases sin
  marcadores); GDC del lado catalán 0,8733 / 0,8937 (15).

## 15. Validación contra corpus reales, más allá del banco curado

El banco de 151 frases está diseñado para ilustrar un fenómeno dialectal
cada una — es una buena prueba de que cada regla es correcta, pero no
dice cómo se comporta el motor sobre miles de frases reales sin
seleccionar. Dos validaciones a mayor escala, ambas con el GD y con el
propio motor:

### Corpus del Boletín Oficial del Estado (BOE)

Textos legales reales con traducción oficial a los dos idiomas.
Confirmó el mismo patrón del GD a escala mucho mayor (5.000 frases:
GD catalán 0,0181; muestra de 200 frases: 0,0127 catalán / 0,8661
valenciano) y aportó la evidencia más fuerte hasta ahora de un patrón ya
sospechado: el diccionario aplica sinónimos valencianos "populares"
(cerquen, arreplega, desenrotllament, mentres) en un registro
formal/institucional que en realidad prefiere la palabra compartida con
el catalán — el mismo patrón, pero con mucho más volumen de evidencia
(p. ej. 29 apariciones reales de "qué" sin tocar, frente a solo 4 en el
benchmark pequeño).

### Dataset público `gplsi/CA-VA_alignment_test`

1.958 frases catalán/valenciano (Universidad de Alicante, licencia CC
BY 4.0), traducidas independientemente por un filólogo desde el mismo
castellano de origen (Common Voice) — a diferencia del benchmark propio
(una traducción adaptada de la otra), aquí hay dos traducciones humanas
independientes, con más variabilidad de sinónimos válidos que no es un
fallo del motor.

| | val→cat | cat→val |
|---|---|---|
| GD | 0,9039 valenciano | 0,0533 catalán |
| Traducción, 1.958 frases completas | 65,4% (BLEU 89,20) | 61,9% (BLEU 88,08) |
| Traducción, filtrado por GD (1.139 frases, 58,2%) | **88,9%** (BLEU 97,00) | **87,9%** (BLEU 96,67) |

El filtro se queda solo con las frases donde el GD confirma 1,0 en
el lado valenciano y 0,0 en el catalán a la vez — sobre ese
subconjunto, la precisión sube a niveles muy cercanos al benchmark de
151, confirmando que gran parte de la caída inicial es sinonimia entre
los dos traductores independientes, no el motor fallando más.

### Cuatro bugs reales encontrados en el diccionario

El análisis de fallos sobre gplsi (agregado por frecuencia, no caso a
caso) destapó, con causa raíz confirmada en cada caso:

1. **"xicotet"→"menut" mal marcado como forma canónica** en el
   diccionario de origen (había dos candidatos, "menut" y "petitet"; el
   marcado como canónico es el que casi nunca aparece en 1.958 frases
   reales, donde la traducción real es siempre "petit") — ~75 fallos
   combinados en las dos direcciones, y la causa raíz exacta de un falso
   positivo que el propio GD ya había señalado sobre texto real del
   equipo.
2. **Pares léxicos retirados el 30/09/2026** ("tindre/vore/obtindre/
   mantindre", "últim/darrer") al centralizar el diccionario en una
   única fuente, aceptando entonces la pérdida sin saber cuánto costaría
   — ahora cuantificado por primera vez: **~25% de los fallos val→cat**
   vienen solo de esta decisión.
3. El patrón de sufijo incoativo (-ix→-eix) no cubre el plural
   (-ixen→-eixen), solo el singular — nunca evidenciado hasta ahora por
   falta de volumen suficiente.
4. El plural de "servici"/"servei" no está derivado del singular, que sí
   figura en el diccionario.

### Benchmark manual revisado a mano: BOE y AVL (28-30/10/2026)

Los benchmarks anteriores tienen dos límites: el de 151 frases es pequeño
y el BOE "estricto" se construyó con el propio diccionario (mide
regresiones, no huecos). Por eso se montó un benchmark nuevo, revisado
frase a frase por personas (proceso completo en
`documentacio/hoja_de_ruta_benchmark_manual.md`):

- **BOE, 246 frases**: catalán y valenciano oficiales del BOE, elegidas
  para cubrir los fenómenos de los diccionarios y de las reglas (léxico,
  conjugaciones, demostrativos, posesivos, "per a", incoativos...) y
  revisadas a mano desde el original.
- **AVL, 212 frases**: valenciano de los textos de la AVL; el catalán se
  generó con el traductor val→cat y se corrigió a mano.
- **Mezcla, 458**: las dos juntas, como cifra única.

Además de las exactas, BLEU y chrF, desde el 30/10/2026 se mide **TER**
(porcentaje de ediciones de palabra, contando un bloque movido como una
sola) y **WER** (lo mismo sin desplazamientos), los dos de corpus y
cuanto más bajos, mejor. Resultados del sistema que se entrega (motor +
FLOR-760M) frente al motor solo:

| Benchmark | Sistema | Exactas | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|---|
| BOE 246 | motor solo | 32 (13,0 %) | 83,53 | 93,46 | 9,50 | 10,15 |
| BOE 246 | **motor + FLOR** | 32 (13,0 %) | 83,82 | 93,59 | **9,26** | **9,94** |
| AVL 212 | motor solo | 182 (85,8 %) | 98,35 | 99,16 | 0,80 | 0,80 |
| AVL 212 | **motor + FLOR** | **195 (92,0 %)** | 99,08 | 99,54 | **0,41** | **0,41** |
| Mezcla 458 | motor solo | 214 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |
| Mezcla 458 | **motor + FLOR** | **227 (49,6 %)** | 90,88 | 96,34 | **5,61** | **6,01** |

Lectura:

- **El modelo de lenguaje mejora los tres y no empeora ninguno.** En la
  AVL resuelve 14 frases ("cop"→"vegada", "anou"→"nou") y pierde una
  ("les anous").
- **AVL, casi resuelta**: las 17 frases que fallan están a 1-3 palabras
  de la referencia. La mitad es una decisión de registro pendiente
  ("xic" frente a "xiquet").
- **BOE: las exactas engañan.** Solo el 13 % de frases salen idénticas,
  pero el TER es 9, es decir, una palabra de cada diez. La referencia es
  el texto oficial tal cual y se separa del catalán por motivos que no
  son dialectales: futuro donde el catalán usa presente ("pot"→"podrà",
  "és"→"serà"), reformulaciones ("mitjançant"→"per mitjà de"), artículos
  y orden. En este benchmark, TER, WER y chrF son la medida útil.

Todas las cifras, con chrF++ y las rutas de los resultados, en
`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`.

## 16. Reestructuración del repositorio (14/10/2026)

Tras varias semanas de trabajo acumulado, el repositorio tenía una
organización poco clara para alguien que lo recibiera sin más contexto:
9 carpetas numeradas con un hueco real en la numeración, ficheros de
exploración puntual sin limpiar, y documentación desactualizada en
varios puntos tras los avances más recientes. Se hizo una revisión
completa, carpeta por carpeta:

- Las 9 etapas se agruparon bajo `pipeline/`, separadas del producto
  final (`traductor/`, fuera de `pipeline/` por ser el producto y no una
  etapa) y de los datos (`dades/`). La antigua carpeta `boe/` (sin
  número) pasó a ser `pipeline/05_corpus_boe/`, cerrando el hueco de
  numeración sin tocar las otras 8 carpetas.
- Se depuraron las fuentes de léxico que el motor real ya no usa desde
  el 30/09/2026 (Apertium, un glosario de contrastes de otro
  colaborador, un fichero de fusión manual superado), un prompt de LLM
  sin ningún uso real detectado, y varios informes/resultados generados
  automáticamente y por tanto regenerables en cualquier momento.
- Se encontró y corrigió, de paso, un bug real en `.gitignore`: dos
  reglas que excluían pesos de modelos y traducciones generadas habían
  dejado de funcionar en silencio tras mover las carpetas, por una
  particularidad de cómo se ancla un patrón de `.gitignore` con barras
  en medio.
- **Advertencia de transparencia**: durante este trabajo se encontró que
  dos ficheros reales del proyecto, nunca comiteados a git
  (`documentacio/hoja_de_ruta_traductor_invers.md`,
  `documentacio/hoja_de_ruta_gd_y_proxima_fase.md`) se habían borrado
  por accidente, y un tercero (`documentacio/informes/`, el informe
  semanal anterior) se perdió del todo sin dejar ningún rastro
  recuperable. Los dos primeros se reconstruyeron con fidelidad parcial
  a partir del propio historial de la conversación; el tercero no se
  pudo recuperar en absoluto — el informe de la sección "Próximos pasos"
  más abajo es nuevo, no una reconstrucción.
- Cada paso se verificó contra la suite completa de pruebas automáticas
  (536 casos) y los dos benchmarks de traducción, sin ningún cambio de
  comportamiento salvo el ya documentado en las secciones 11-12 (la
  retirada de una regla que no generalizaba más allá del propio
  benchmark).

## 17. Estado actual (30/10/2026) y próximos pasos

**Catalán → valenciano** (la dirección que se entrega). Desde el
29-30/10/2026 el **sistema principal es motor + FLOR-760M**; el motor
solo se mide únicamente para ver qué aporta el modelo de lenguaje.

Sistema final en todos los benchmarks, misma versión y mismas métricas
(30/10/2026; el de evaluación principal es el **manual mezcla**):

| Benchmark | Exactas | BLEU | chrF | TER ↓ | WER ↓ |
|---|---|---|---|---|---|
| **Manual mezcla BOE + AVL (458)** | **227 (49,6 %)** | 90,88 | 96,34 | 5,61 | 6,01 |
| Manual BOE (246) | 32 (13,0 %) | 83,82 | 93,59 | 9,26 | 9,94 |
| Manual AVL (212) | 195 (92,0 %) | 99,08 | 99,54 | 0,41 | 0,41 |
| 151 (154) | 146 (94,8 %) | 99,32 | 99,66 | 0,27 | 0,27 |
| 151 + homógrafos (253) | 226 (89,3 %) | 96,38 | 98,21 | 0,74 | 0,74 |
| BOE estricto, muestra (2.000) | 1.880 (94,0 %) | 98,95 | 99,64 | 0,32 | 0,59 |
| BOE amplio, muestra (2.000) | 1.203 (60,2 %) | 88,24 | 95,54 | 3,73 | 6,00 |
| gplsi (1.958) | 1.544 (78,9 %) | 93,52 | 97,00 | 2,77 | 2,79 |

En los manuales, el motor solo da 214/458 en la mezcla (TER 5,91), 32/246
en el BOE (TER 9,50) y 182/212 en la AVL (TER 0,80): el modelo de
lenguaje mejora los tres. Frente a las medidas anteriores (22-23/10), el
BOE estricto sube de 1.778 a 1.880 y gplsi de 1.486 a 1.544 por el
trabajo de datos de la última semana; el BOE amplio baja 3 frases
("finalitat"→"fi", dato nuevo del léxico). Detalle, ganancias y pérdidas
en `pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`.

Cómo se entrega:

- **Traductor** (`translate_cat_val`): reglas + diccionarios + spaCy +
  FLOR-760M (`torch`, `transformers`, 1,5 GB). Solo CPU. El modelo solo
  se activa en las frases con homógrafos que el diccionario declara
  ("cop", "cops", "nou", "manca", "calces", "gandula"...) y solo elige
  entre candidatos del diccionario: no inventa texto. El motor sin modelo
  sigue disponible como `translate_cat_val_motor` (unos 700 MB de memoria
  y unas 250 frases por segundo en un núcleo).
- **GD** (sección 14): la segunda herramienta.

**Valenciano → catalán**: aparcado desde el 20/10/2026. Última medida: 151
95/154 y gplsi 1.403/1.958 con el motor (22/10); con la capa de LLM
congelada (sección 13, medida del 21/10), 151 109 y BOE 406/2.000.

Pendiente, por orden sugerido:
1. Commit del trabajo del 22-23/10/2026.
2. Homógrafos que el léxico no marca: la entrada E0251 ("afecta" →
   "carinya", correcta como adjetivo) se aplica también al verbo
   "afectar", igual que el caso conocido de "escombra". Propuesta para el
   proveedor: marcarlas `homonimia_lexica`.
3. Revisar con el modelo de lenguaje las formas valencianas del léxico que
   le resulten muy improbables, para encontrar errores como "hamaces".
4. Numerales: el BOE usa "octava", "dèsset", "dènou" y "díhuit" donde el
   léxico pone "huitena", "dessetena", "denovena" y "dihuitena".
5. Empaquetado para la Conselleria (instalación, línea de órdenes o
   servicio).
