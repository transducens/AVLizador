# Etapa 1 — Scraping y limpieza del corpus fuente

Primera etapa del proyecto: conseguir texto real en valencià occidental,
verificado, para poder generar sobre él el corpus sintético. Los scripts
de esta etapa viven en `01_scraping_y_limpieza/` (raíz del repositorio,
mismo nivel que las demás etapas) — esta carpeta solo documenta qué hace
cada uno, de dónde saca los datos y en qué orden se ejecutan.

## Qué es la AVL y por qué es la fuente

La **AVL (Acadèmia Valenciana de la Llengua)** es la institución oficial
que regula el valenciano — creada en 1998 por las Corts Valencianes. Es al
valenciano lo que el IEC es al catalán oriental: fija la normativa (léxico,
gramática, ortografía), resuelve consultas lingüísticas y publica los
materiales de referencia oficiales. Se eligió como fuente por eso: al ser
la autoridad normativa, su web es la fuente con más garantías de contener
valenciano occidental normativo real, no una mezcla de registros.

## Los 5 scripts, técnica por técnica

La web de la AVL no es un solo tipo de contenido — mezcla un WordPress
normal, herramientas de consulta antiguas hechas en JSP, y documentos en
PDF. Por eso hace falta una técnica distinta para cada tipo de página:

### `avl_probe.py` — API REST de WordPress

Usa `https://www.avl.gva.es/wp-json/wp/v2/...` directamente (no hace falta
parsear HTML). Saca cuatro tipos de contenido:

- **`butlleti`** — el boletín/revista periódica de la AVL.
- **`glossari`** — consultas lingüísticas resueltas por la Acadèmia (del
  tipo "¿cómo se dice X en valenciano?", explicando origen y uso de una
  palabra). Esto explica por qué el benchmark de traducción tiene bastantes
  frases que hablan *sobre* palabras en vez de frases de uso normal.
- **`post`** / **`pagina`** — entradas de blog y páginas estáticas
  genéricas del sitio.
- Categoría de WordPress nº 9 → **`notes-de-premsa`** — comunicados de
  prensa institucionales.

### `avl_crawler.py` — HTML directo (requests + BeautifulSoup + trafilatura)

- **`salutacio`** — la página de presentación institucional (un único
  documento).
- **`escriptors`** — biografías de los autores reconocidos en "Escriptors
  de l'Any", un galardón anual de la AVL.

### `gnv_extractor.py` y `gvb_extractor.py` — Playwright (navegador real automatizado)

Estas dos herramientas de consulta gramatical de la AVL están montadas
sobre un buscador JSP antiguo que detecta peticiones automatizadas y
devuelve contenido recortado si no ve un navegador real — por eso hace
falta Playwright en vez de `requests` normal. Son **dos documentos
distintos**, no un duplicado:

- **GNV — Gramàtica Normativa Valenciana** (2006): la gramática oficial
  completa y técnica.
- **GVB — Gramàtica Valenciana Bàsica** (2016): versión simplificada de la
  misma normativa, pensada para público no especializado — secciones más
  breves, sin terminología lingüística técnica.

### `pdf_extractor.py` — descarga y extracción de texto (pymupdf, sin guardar el PDF en disco)

Lee las URLs de `fonts_pdf.txt` y `fonts_pdf_publicacions.txt`:

- **`legislacio`** — la ley de creación de la AVL, el reglamento interno,
  dictámenes del Consell Valencià de Cultura.
- **`acord-normatiu`** — los acuerdos normativos oficiales aprobados en
  pleno por la AVL (decisiones formales sobre normas lingüísticas
  concretas — p. ej., de aquí sale la norma "dos/dues" documentada en la
  etapa 2).
- **`publicacions`** — manuales y colecciones de investigación propias de
  la AVL ("Recerca", "Documents", "Plurilingüisme").

## Pipeline completo (de raw a limpio)

```
avl_probe.py / avl_crawler.py / gnv_extractor.py / gvb_extractor.py / pdf_extractor.py
        ↓
data/avl/raw/*.jsonl
        ↓ neteja_corpus.py
data/avl/clean/*.jsonl
        ↓ (unificación de todas las fuentes)
data/avl/final/unified.jsonl                    (2.233 documentos)
        ↓ estudi_dialectal.py
data/avl/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documentos, 821.195 tokens — el fichero que de verdad
         se usa como fuente para el corpus sintético)
```

## Cómo clasifica `estudi_dialectal.py`

Cuenta, en cada documento, cuántas palabras coinciden con una lista de
marcadores dialectales ya conocidos (`data/avl/final/lexic/marcadors_dialectals.json`
— una lista de marcadores occidentales y otra de orientales, el mismo tipo
de contraste léxico que se documenta en la etapa 2, pero usado aquí para
*clasificar* documentos en vez de para traducir). Calcula:

```
ratio = (marcadores occidentales) / (marcadores occidentales + orientales)
```

y clasifica: **≥80% → occidental_clar, 60-80% → occidental_predominant,
40-60% → mixt, 20-40% → oriental_predominant, <20% → oriental_clar.** Si un
documento no tiene ningún marcador, se asume `occidental_assumit` cuando la
fuente ya es institucionalmente valenciana (AVL, GNV, GVB) y no es una
página genérica; si no, queda `no_determinat`.

## Ficheros clave

| Fichero | Qué hace |
|---|---|
| `avl_probe.py` | Scraping vía API REST de WordPress (butlletí, glossari, posts, páginas, notas de prensa) |
| `avl_crawler.py` | Scraping HTML directo (salutació institucional, biografías de escriptors) |
| `gnv_extractor.py` | Extrae la Gramàtica Normativa Valenciana (Playwright) |
| `gvb_extractor.py` | Extrae la Gramàtica Valenciana Bàsica (Playwright) |
| `pdf_extractor.py` | Extrae texto de PDFs (legislación, acuerdos normativos, publicaciones) |
| `neteja_corpus.py` | Limpieza: normaliza texto, quita ruido de scraping |
| `estudi_dialectal.py` | Clasifica cada documento por dialecto y filtra el corpus final |

## Decisión clave de esta etapa

No se generó el corpus sintético desde `unified.jsonl` (el corpus completo
sin filtrar), sino específicamente desde `corpus_occidental_net.jsonl`
(solo `occidental_clar` + `occidental_predominant` + `occidental_assumit`).
Traducir desde el corpus completo habría metido en la mezcla texto que ya
estaba en catalán oriental o en registro mixto, generando pares donde el
"original" ya no era realmente valenciano — habría corrompido el corpus
sintético antes de empezar.

Ver `../metodologia_y_resultados.md` sección 1 para más contexto.
