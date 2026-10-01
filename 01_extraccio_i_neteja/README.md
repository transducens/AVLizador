*[Llegeix-ho en castellà](README.es.md)*

# Etapa 1 — Scraping i neteja del corpus font

Primera etapa del projecte: aconseguir text real en valencià occidental,
verificat, per a poder generar sobre ell el corpus sintètic. Els scripts
d'esta etapa viuen en `01_extraccio_i_neteja/` (arrel del repositori,
mateix nivell que la resta d'etapes) — esta carpeta només documenta què fa
cada un, d'on trau les dades i en quin ordre s'executen.

## Què és l'AVL i per què és la font

L'**AVL (Acadèmia Valenciana de la Llengua)** és la institució oficial
que regula el valencià — creada el 1998 per les Corts Valencianes. És al
valencià el que l'IEC és al català oriental: fixa la normativa (lèxic,
gramàtica, ortografia), resol consultes lingüístiques i publica els
materials de referència oficials. Es va triar com a font per això
mateix: en ser l'autoritat normativa, la seua web és la font amb més
garanties de contindre valencià occidental normatiu real, no una mescla
de registres.

## Els 5 scripts, tècnica per tècnica

La web de l'AVL no és un sol tipus de contingut — mescla un WordPress
normal, ferramentes de consulta antigues fetes en JSP, i documents en
PDF. Per això fa falta una tècnica distinta per a cada tipus de pàgina:

### `avl_probe.py` — API REST de WordPress

Usa `https://www.avl.gva.es/wp-json/wp/v2/...` directament (no fa falta
analitzar HTML). Trau quatre tipus de contingut:

- **`butlleti`** — el butlletí/revista periòdica de l'AVL.
- **`glossari`** — consultes lingüístiques resoltes per l'Acadèmia (del
  tipus "com es diu X en valencià?", explicant origen i ús d'una
  paraula). Açò explica per què el benchmark de traducció té bastants
  frases que parlen *sobre* paraules en lloc de frases d'ús normal.
- **`post`** / **`pagina`** — entrades de blog i pàgines estàtiques
  genèriques del lloc.
- Categoria de WordPress núm. 9 → **`notes-de-premsa`** — comunicats de
  premsa institucionals.

### `avl_crawler.py` — HTML directe (requests + BeautifulSoup + trafilatura)

- **`salutacio`** — la pàgina de presentació institucional (un únic
  document).
- **`escriptors`** — biografies dels autors reconeguts en "Escriptors
  de l'Any", un guardó anual de l'AVL.

### `gnv_extractor.py` i `gvb_extractor.py` — Playwright (navegador real automatitzat)

Estes dos ferramentes de consulta gramatical de l'AVL estan muntades
sobre un buscador JSP antic que detecta peticions automatitzades i
retorna contingut retallat si no veu un navegador real — per això fa
falta Playwright en lloc de `requests` normal. Són **dos documents
distints**, no un duplicat:

- **GNV — Gramàtica Normativa Valenciana** (2006): la gramàtica oficial
  completa i tècnica.
- **GVB — Gramàtica Valenciana Bàsica** (2016): versió simplificada de la
  mateixa normativa, pensada per a públic no especialitzat — seccions més
  breus, sense terminologia lingüística tècnica.

### `pdf_extractor.py` — descàrrega i extracció de text (pymupdf, sense guardar el PDF en disc)

Llig les URL de `fonts_pdf.txt` i `fonts_pdf_publicacions.txt`:

- **`legislacio`** — la llei de creació de l'AVL, el reglament intern,
  dictàmens del Consell Valencià de Cultura.
- **`acord-normatiu`** — els acords normatius oficials aprovats en
  ple per l'AVL (decisions formals sobre normes lingüístiques
  concretes — p. ex., d'ací ix la norma "dos/dues" documentada en
  l'etapa 2).
- **`publicacions`** — manuals i col·leccions d'investigació pròpies de
  l'AVL ("Recerca", "Documents", "Plurilingüisme").

## Pipeline complet (de raw a net)

```
avl_probe.py / avl_crawler.py / gnv_extractor.py / gvb_extractor.py / pdf_extractor.py
        ↓
dades/avl/raw/*.jsonl
        ↓ neteja_corpus.py
dades/avl/clean/*.jsonl
        ↓ (unificació de totes les fonts)
dades/avl/final/unified.jsonl                    (2.233 documents)
        ↓ estudi_dialectal.py
dades/avl/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documents, 821.195 tokens — el fitxer que de veres
         s'usa com a font per al corpus sintètic)
```

## Com classifica `estudi_dialectal.py`

Compta, en cada document, quantes paraules coincideixen amb una llista de
marcadors dialectals ja coneguts (`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`,
codificades directament en `estudi_dialectal.py` — el mateix tipus de
contrast lèxic que es documenta en l'etapa 2, però usat ací per a
*classificar* documents en lloc de per a traduir). Calcula:

```
ratio = (marcadors occidentals) / (marcadors occidentals + orientals)
```

i classifica: **≥80% → occidental_clar, 60-80% → occidental_predominant,
40-60% → mixt, 20-40% → oriental_predominant, <20% → oriental_clar.** Si un
document no té cap marcador, s'assumeix `occidental_assumit` quan la
font ja és institucionalment valenciana (AVL, GNV, GVB) i no és una
pàgina genèrica; si no, queda `no_determinat`.

## Fitxers clau

| Fitxer | Què fa |
|---|---|
| `avl_probe.py` | Scraping via API REST de WordPress (butlletí, glossari, posts, pàgines, notes de premsa) |
| `avl_crawler.py` | Scraping HTML directe (salutació institucional, biografies d'escriptors) |
| `gnv_extractor.py` | Extrau la Gramàtica Normativa Valenciana (Playwright) |
| `gvb_extractor.py` | Extrau la Gramàtica Valenciana Bàsica (Playwright) |
| `pdf_extractor.py` | Extrau text de PDF (legislació, acords normatius, publicacions) |
| `neteja_corpus.py` | Neteja: normalitza text, lleva soroll del raspat |
| `estudi_dialectal.py` | Classifica cada document per dialecte i filtra el corpus final |

## Decisió clau d'esta etapa

No es va generar el corpus sintètic des de `unified.jsonl` (el corpus
complet sense filtrar), sinó específicament des de `corpus_occidental_net.jsonl`
(només `occidental_clar` + `occidental_predominant` + `occidental_assumit`).
Traduir des del corpus complet hauria ficat en la mescla text que ja
estava en català oriental o en registre mixt, generant parelles on
l'"original" ja no era realment valencià — hauria corromput el corpus
sintètic abans de començar.

Vore `../documentacio/metodologia_i_resultats.md` secció 1 per a més context.
