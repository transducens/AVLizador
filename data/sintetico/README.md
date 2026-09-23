# Corpus sintético paralelo valenciano → catalán (fuente: AVL)

Corpus de pares de frases valenciano (occidental, norma AVL/GVA) → catalán
(oriental, norma IEC), generado traduciendo con un LLM el corpus real
scrapeado de la web de la AVL (Acadèmia Valenciana de la Llengua). Pensado
como base para entrenar/afinar un modelo de traducción entre las dos
variantes, o como banco de evaluación.

## 1. De dónde sale el texto original (el lado "valenciano")

Todo el texto valenciano viene de scrapear la web de la AVL:

```
avl_crawler.py / avl_probe.py / gnv_extractor.py / gvb_extractor.py / pdf_extractor.py
        ↓ (scraping por secciones: butlletí, glossari, gramàtica normativa,
        ↓  notes de premsa, pàgines, posts, legislació, acords normatius,
        ↓  publicacions, biografies...)
data/avl/raw/*.jsonl  →  neteja_corpus.py  →  data/avl/clean/*.jsonl
        ↓
data/avl/final/unified.jsonl          (2.233 documentos, todo unificado)
        ↓ estudi_dialectal.py (clasifica cada documento como occidental/
        ↓  oriental/mixto según marcadores dialectales, y descarta lo que
        ↓  no es claramente valenciano occidental)
data/avl/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documentos, 821.195 tokens — SOLO texto verificado
         como valenciano occidental puro)
```

**Decisión clave**: no se tradujo `unified.jsonl` (el corpus completo), sino
específicamente `corpus_occidental_net.jsonl`. Traducir desde el corpus
completo habría metido en la mezcla texto que ya estaba en catalán oriental
o en registro mixto, generando pares donde el "original" ya no era
realmente valenciano — habría corrompido el corpus antes de empezar.

## 2. Cómo se segmentó el texto

`corpus_occidental_net.jsonl` tiene documentos completos (párrafos enteros,
a veces cientos de palabras). Se decidió traducir **frase a frase**, no
documento a documento, por dos motivos:

- El modelo qwen2.5:14b, con el prompt/glosario que se valida en el punto 3,
  se benchmarkeó sobre frases sueltas — traducir párrafos largos de una vez
  se sale de ese régimen probado y aumenta el riesgo de que el modelo
  "explique" en vez de traducir, o pierda coherencia.
- Permite deduplicar: mucho texto (sobre todo del glosario y textos legales)
  se repite palabra por palabra en varios documentos.

Reglas de segmentación (`genera_corpus_sintetico.py`):
- División por frases con heurística de puntuación + lista de abreviaturas
  (para no cortar en "Sr.", "art.", "núm.", etc.).
- Se descartan frases de menos de 5 palabras o 20 caracteres (ruido,
  numeración, tablas) y de más de 280 caracteres (para no arriesgar que la
  respuesta del modelo se corte a mitad — el límite de generación son 200
  tokens, heredado del benchmark).
- Deduplicación exacta por contenido (normalizando apóstrofos y
  mayúsculas): de 48.037 frases candidatas quedaron **46.315 únicas**
  (1.722 duplicadas, típico del glosario y de textos legales repetidos
  entre boletines).
- Cada frase única guarda cuántas veces aparecía en el corpus original
  (`n_ocurrencies`) — información que no afecta a la traducción pero es
  útil para saber qué tan "central" es cada frase.

## 3. Cómo se tradujo

**Modelo**: qwen2.5:14b vía Ollama, local (`temperature=0`, `num_predict=200`
para reproducibilidad).

**Por qué este modelo y no otro**: se benchmarkearon varias opciones en
`03_seleccion_de_modelo/` (varios tamaños de Ollama, reglas deterministas, NLLB-200)
sobre 60 frases con referencia humana. qwen2.5:14b + el prompt/glosario de
abajo dio **BLEU 84,52 / chrF 92,34 / chrF++ 91,84**, muy por encima del
resto (NLLB-200-600M, por comparación, dio BLEU 53,13 sin ese prompt/glosario
— confirma que la ventaja viene sobre todo del prompt afinado, no solo del
tamaño del modelo).

**Prompt y glosario**: se reutiliza tal cual el motor de
`03_seleccion_de_modelo/evalua_models.py` (el mismo que se usó en el benchmark, para
no perder esa validación):
- Un system prompt con las reglas morfológicas documentadas (demostrativos,
  posesivos, infinitivos irregulares, subjuntivo presente/imperfecto,
  numerales, léxico base) — el mismo conjunto que hay explicado como guía de
  estudio en `02_reglas_dialectales/reglas_prompt/guia_dialectal_valencia_catala.md`.
- Un glosario dinámico por frase: antes de llamar al modelo se buscan en
  `palabras_traducidas.json` (1.604 formas) las palabras valencianas
  presentes en esa frase concreta, y se le pasan como pista
  `[VOCABULARI: valenciano=catalán, ...]`.

**Una regla añadida solo para este corpus** (no toca el prompt del
benchmark, que queda intacto para no perder esa validación): se detectó que
al aplicar el prompt a texto real (con nombres de instituciones, cosa que no
salía en las frases cortas del benchmark) el modelo a veces "traducía"
siglas reales por otras (`AVL` → `IEC`). Se añadió una regla explícita
diciendo que las siglas de instituciones (AVL, GVA, GNV, GVB, RACV) nunca se
tocan, y solo si ya estaban en el original.

**Dónde se ejecutó**: en el clúster SLURM de la universidad ("abaco", 8x
RTX 2080 Ti), repartiendo el corpus en fragmentos por hash del id de cada
frase para traducir con varias GPUs a la vez (ver `04_corpus_sintetico/slurm/`).

## 4. Auditoría de calidad

Antes de dar el corpus por bueno se hizo una auditoría completa
(`data/sintetico/analisi_corpus.html`, generada a partir de este mismo
corpus), contrastando **cada una de las reglas dialectales documentadas**
contra lo que el modelo hizo de verdad, no solo confiando en que un LLM con
buen BLEU en 60 frases se comportaría igual en 46.315 frases reales de todo
tipo. Metodología:

- Por cada regla morfológica (this→aquest, meua→meva, siga→sigui...): en
  cuántas frases aparecía la forma valenciana, y en cuántas el catalán
  todavía conservaba esa misma forma sin convertir.
- Por cada palabra frecuente del léxico: cobertura real contra
  `palabras_traducidas.json`.
- Revisión manual de una muestra de casos marcados como sospechosos y de
  los "peores" resultados de cada categoría.

Esto sacó a la luz varios problemas reales que las marcas automáticas del
propio generador no habían detectado (ver sección 5) — es la razón por la
que existe `repara_corpus.py`.

## 5. Bugs encontrados y corregidos (sin volver a traducir nada)

Todo esto se corrigió con `04_corpus_sintetico/repara_corpus.py` — manipulación de
texto sobre el corpus ya generado, sin llamar otra vez a Ollama:

| Problema | Casos | Cómo se corrigió |
|---|---|---|
| El literal `"Frase a traduir:"` (parte del prompt) se colaba en la respuesta | 1.165 | Se eliminó el literal; el resto de cada respuesta ya era una traducción válida |
| `"blanca"` (adjetivo) confundida con `"Blanca"` (nombre regional del pájaro *garsa* en el léxico) | 28 | Revertido al valenciano original |
| `"pròxim"` (adjetivo común) confundido con el sentido religioso `"el pròxim"` = `"proïsme"` | 45 | Revertido al original |
| `"Ramon"`/`"Manuel"` (nombres de persona) tratados como variantes dialectales | 32 + 51 | Revertidos al original, y arreglado de raíz en `evalua_models.carrega_lexic()` (excluye entradas de categoría "nombre") |
| Formas de subjuntivo sin convertir (`siga`, `siguen`, `tinga`, `tinguen`) | 241+32+8+8 | Corregidas con las mismas sustituciones deterministas de `evalua_models.tradueix_regles()` |

**Lo que NO se corrigió automáticamente, a propósito**:
- `vinga`→`vingui` y `fora`→`fos`: tienen homonimia real (`"vinga!"` es
  también una interjección, `"fora"` también significa "fuera") — una
  corrección ciega habría introducido errores nuevos.
- 65 casos de `sigla_introduida` (el modelo inventa una sigla que no estaba
  en el original, p.ej. "l'Acadèmia" → "l'AVL"): no es una simple reversión
  de texto, requeriría volver a traducir esas frases con el prompt ya
  reforzado. Quedan excluidas de la exportación limpia, pero sin corregir.

## 6. Estado final

| | |
|---|---|
| Frases únicas totales | 46.315 |
| Con alguna marca de sospecha | 663 (1,43%) |
| Limpias | 45.652 (98,57%) |
| Compliance medio de las 38 reglas morfológicas fiables | 96,7% (30 de 38 reglas ≥95%) |
| Cobertura del léxico (excluyendo entradas polisémicas conocidas) | 97,2% |

Distribución por tipo de documento: glossari 35% (16.240), publicacions 29%
(13.599), acord-normatiu 13% (6.163), gramatica_normativa 11% (5.038),
pagina 3% (1.563), nota-de-premsa 3% (1.554), legislacio 3% (1.208),
butlleti 2% (934), biografia/post <0,1%.

**Limitación importante a tener en cuenta**: el corpus es **sintético** — lo
generó un LLM, no un traductor humano. Un modelo entrenado con esto puede
llegar a acercarse a la calidad de qwen2.5:14b en esta tarea (y ser mucho
más barato/rápido de ejecutar), pero no la va a superar; el techo de calidad
es el del modelo que lo generó. Para saber si un futuro modelo generaliza
más allá de este corpus, conviene validar contra texto de origen humano
(ver `data/boe/` — traducciones oficiales reales, pendiente de
extraer y alinear; se deja aparte por ahora).

**Otra limitación**: el corpus está concentrado en registro institucional/
normativo (glosario, gramática, textos legales). Un modelo entrenado solo
con esto traducirá muy bien ese registro y probablemente peor cualquier
otro (conversación, prensa informal, literatura).

## 7. Qué fichero usar

```
data/sintetico/
├── corpus_sintetic_val_cat.jsonl            ← el corpus completo, con metadatos
├── corpus_sintetic_val_cat.abans_de_reparar.jsonl  ← copia de seguridad pre-reparación
├── parallel_val_cat.jsonl                   ← ⭐ EL BUENO para entrenar/usar
├── parallel.val / parallel.cat              ← lo mismo, en 2 ficheros alineados línea a línea
└── analisi_corpus.html                      ← el informe de auditoría completo
```

- **`parallel_val_cat.jsonl`** — usa este. Son las 45.652 parejas limpias
  (sin ninguna marca de sospecha), formato `{"val": "...", "cat": "..."}`,
  una por línea. Listo para casi cualquier framework de fine-tuning.
- **`parallel.val` / `parallel.cat`** — el mismo contenido en formato
  Moses/OPUS (dos ficheros de texto plano, línea N de uno se corresponde con
  línea N del otro) — útil si la herramienta que uses espera ese formato en
  vez de JSONL.
- **`corpus_sintetic_val_cat.jsonl`** — solo si necesitas los metadatos
  (`doc_type`, `source_url`, `n_ocurrencies`, `motius_sospita`) para filtrar
  tú mismo de otra manera (p.ej. si quisieras incluir algunas frases
  sospechosas a propósito, o pesar el entrenamiento por tipo de documento).

## 8. Cómo se generó / cómo reproducirlo o ampliarlo

Ver `04_corpus_sintetico/README.md` (uso del script principal) y
`04_corpus_sintetico/slurm/README.md` (ejecución en el clúster con GPU). Resumen:

```bash
python genera_corpus_sintetico.py                 # generación completa (reanudable)
python repara_corpus.py                           # aplica las correcciones de la sección 5
```
