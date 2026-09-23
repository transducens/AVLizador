# Corpus sintético paralelo valencià → català (fuente: AVL) — metodología y resultados

Este documento resume todo el proceso: de dónde sale el texto, cómo se
decidieron las reglas dialectales, qué modelo se usó y por qué, qué
problemas se encontraron por el camino y cómo se corrigieron, y el estado
final del corpus. Pensado para quien reciba este repositorio sin más
contexto que el propio código.

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
corpus/raw/*.jsonl  →  neteja_corpus.py  →  corpus/clean/*.jsonl
        ↓ (unificación de todas las fuentes)
corpus/final/unified.jsonl          (2.233 documentos, todo unificado)
        ↓ estudi_dialectal.py
corpus/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documentos, 821.195 tokens — SOLO texto verificado
         como valenciano occidental puro)
```

`estudi_dialectal.py` clasifica cada documento contando cuántas palabras
del texto coinciden con una lista de marcadores dialectales ya conocidos
(`corpus/final/lexic/marcadors_dialectals.json`, con una lista de
marcadores occidentales y otra de orientales — el mismo tipo de contraste
léxico que se documenta en la etapa 2, pero usado aquí para *clasificar*
documentos en vez de para traducir). Para cada documento se calcula:

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
humana (`evalua_modelos/benchmark_corpus.json`) y se probaron varias
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

El léxico original (`evalua_modelos/palabras_traducidas.json`, ~1.600
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
(`corpus_sinteticos/generado/analisi_corpus.html`), contrastando cada regla
documentada contra lo que el modelo hizo de verdad en las 46.315 frases
reales, no solo confiando en el benchmark de 60 frases.

### Bugs encontrados y corregidos (sin volver a traducir nada)

Corregidos con `corpus_sinteticos/repara_corpus.py` — manipulación de texto
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
la sección 6 queda en `corpus_sinteticos/generado/` como referencia
histórica de la auditoría, pero **el fichero a usar es el de la
regeneración v2** una vez termine — ver `corpus_sinteticos/README.md` para
las instrucciones de ejecución y `corpus_sinteticos/slurm/` para los
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
  contra traducciones de origen humano (ver `boe/boe_corpus/`, traducciones
  oficiales del BOE — explorado en paralelo pero fuera del alcance de este
  documento).

## 9. Auditoría de la fuente (21/09) — el corpus base, no el modelo

Al revisar a mano una muestra generada con qwen2.5:14b + `lexico_fiable.json`
ya maduros, la calidad seguía sin convencer. Antes de tocar el prompt o
probar otro modelo otra vez, se auditó `corpus/final/dialectal/corpus_occidental_net.jsonl`
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
`evalua_modelos/comparativa_salamandraTA_gemma/`):

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
documentados con detalle en `evalua_modelos/comparativa_salamandraTA_gemma/README.md`:

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
