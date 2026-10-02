*[Llegeix-ho en castellà](README.es.md)*

# Etapa 2 — Regles dialectals i lèxic

Tot allò relacionat amb les diferències dialectals entre valencià
(occidental, norma AVL/GVA) i català (oriental, norma IEC): d'on ixen,
com es documenten, i les dades estructurades que usa el pipeline de
traducció. Amb el corpus font ja net (etapa 1), esta etapa defineix
**què canvia** entre els dos dialectes — les regles que després usa el
model per a traduir (etapes 3-4).

**[`regles_dialectals_amb_evidencia.md`](regles_dialectals_amb_evidencia.md)**
— comença per ací si vols les regles explicades com un tema d'estudi
(demostratius, possessius, morfologia verbal, numerals, gentilicis,
sintaxi, lèxic diferencial), amb un apèndix d'evidència numèrica de
cada una.

## Metodologia: com es van derivar les regles

Es van derivar comparant, dins del diccionari morfològic d'Apertium
(`apertium-cat.cat.dix`), les formes marcades `v="val_gva"` (occidental) amb
els seus equivalents `v="cat"`/`v="val_uni"` (oriental). Cada patró es
documenta amb la seua **cobertura** (quants casos reals el seguixen) — un
patró amb cobertura baixa no es convertix en regla general, es deixa com a
llista tancada de paraules confirmades una a una. Dos regles ixen de fonts
distintes al diccionari, documentades explícitament on correspon: el
pretèrit perifràstic (d'analitzar frases completes del benchmark) i la
concordança de gènere de "dos/dues" (de normativa AVL/IEC citada
directament).

Vore `../documentacio/metodologia_i_resultats.md` seccions 2 i 4 per al
detall complet del procés.

## Estructura

```
02_regles_dialectals/
├── regles_prompt/      documentació per a llegir i revisar (comença ací)
├── lexic/             dades estructurades: parells valencià-català en JSON
├── fonts/             material brut d'origen (no pensat per a llegir directament)
└── docs_gramatica/    GEIEC (IEC) i GNV (AVL) completes + guies dialectals derivades
```

### `regles_prompt/` — comença per ací

El material d'estudi i revisió. Vore el seu propi
[`regles_prompt/README.md`](regles_prompt/README.md) per al detall, però
en resum:

- **`guia_dialectal_valencia_catala.md`** — document tipus tema de llibre
  amb totes les regles dialectals explicades (morfologia + lèxic). El
  document de referència principal.
- **`lexic_per_frequencia.md`** — per a revisar el lèxic ràpid: només les
  paraules que de veres s'usen al corpus, ordenades per impacte.
- **`system_prompt.md`** / **`glossari_dinamic.md`** — com està implementat
  açò al codi (el prompt literal, el mecanisme del glossari dinàmic).

### `lexic/` — dades estructurades (JSON)

| Fitxer | Què és |
|---|---|
| `lexico_fiable.json` | **Usat per `evalua_models.py --model regles` i `genera_corpus_sintetico.py` (sistema antic de regex, no el motor `traductor/`).** 347 parells (194 originals: 31 d'Apertium + 34 de Paula Guerrero + 129 de `fonts/paralelos.txt`; +150 de Mauricio i +3 de l'evidència AVL afegits 29/09/2026). **Retirat de `traductor/rules/lexic.py` el 30/09/2026** (junt amb `apertium_368_val_cat.json` i `contrastius_paula_guerrero.json`, vore baix): eixe paquet ara és pur lookup de diccionari de Mauricio, sense cap font externa -- vore `traductor/README.md`, secció "DECISIÓ D'ARQUITECTURA". Este fitxer es queda com a còpia de seguretat i com la font que seguixen usant els altres dos scripts. |
| `apertium_368_val_cat.json` | Les 368 formes que Apertium marca com a valencianes, separades en confirmades (65 amb parella, 6 sense) i pendents. Es va fer servir a `traductor/rules/lexic.py` del 30/09/2026 (matí) fins que eixa vesprada es va retirar en reduir el traductor a pur Mauricio -- ja no l'usa cap script actiu. |
| `contrastius_paula_guerrero.json` | 35 parells valencià-català categoritzats (determinants, verbs incoatius, lèxic...), d'una font externa curada a banda, amb un camp `category` real. Mateix cas que l'anterior: es va fer servir un temps a `lexic.py`/`demostratius.py`/`possessius.py`, retirat el 30/09/2026 en passar el traductor a pur Mauricio. |
| `posesivos_cat_val.json` (dins de `font_mauricio/`) | 12 files de Mauricio (30/09/2026), un producte cartesià sense filtrar dels possessius febles. `traductor/rules/possessius.py` es queda només amb els 6 parells on el número casa. |
| `palabras_traducidas.json` | Còpia de treball del lèxic **antic** (l'original viu en `03_seleccio_de_model/palabras_traducidas.json`, ja no usat pel pipeline). |

### `fonts/` — material brut d'origen

No pensat per a llegir directament (llevat de `regles_cat_val.md`, que és
més llegible); són els fitxers d'on ixen les dades de `lexic/` i de la
guia.

| Fitxer | Què és |
|---|---|
| `regles_cat_val.md` | Informe generat automàticament comparant `apertium-cat.cat.dix` (`v="cat"` vs `v="val_gva"`) amb la llista curada — d'ací ix el 90% del contingut de `pares_valenciano_catalan.json` i de la guia dialectal. |
| `apertium-cat.cat.dix` | El diccionari morfològic d'Apertium en brut (format XML/lttoolbox, ~66.500 entrades). |
| `palabras_traducidas.txt` | La llista curada original, en text pla, abans de convertir-se a JSON. |
| `palabras_val.json` | Formes marcades específicament com a valencianes (`v="val_gva"`) en Apertium — sense parella catalana directa, és matèria primera, no parells ja fets. |

### `docs_gramatica/` — gramàtiques oficials completes

Mentre `lexic/` i `fonts/` cobrixen diferències **lèxiques**, esta carpeta
cobrix diferències **gramaticals** (articles, demostratius, pronoms
febles, preposicions...), amb les dos normatives completes en text pla
com a font d'autoritat:

- **GEIEC** (IEC, 2018) — escrapejada en directe amb `baixar_geiec.py`
  (Playwright, 204 seccions).
- **GNV** (AVL, 2016) — reformatada a partir de
  `../dades/avl/clean/avl_gnv.jsonl` (ja escrapejada per l'etapa 1), no
  un scraping nou.
- **`guia_dialectal_morfologia.md`** i **`guia_traduccio_dialectal.md`**
  — anàlisi de les divergències entre totes dos, per tema i per regla
  pràctica respectivament.

Vore el seu propi [`docs_gramatica/README.md`](docs_gramatica/README.md)
per al detall complet i com regenerar cada fitxer.

## Com afegir una paraula nova al lèxic fiable

**Nota (30/09/2026)**: açò només afecta `evalua_models.py --model regles`
i `genera_corpus_sintetico.py` (sistema antic de regex). El motor
`traductor/` (opció `--model traductor`) ja no llig `lexico_fiable.json`
-- per a afegir-li paraules, edita el fitxer font de la categoria
corresponent a `traductor/data/` (vore `traductor/README.md`, secció
"Com afegir una regla nova").

Edita `lexic/lexico_fiable.json` directament, afegint una entrada nova a
l'array `entradas` amb el mateix esquema que les altres (`valenciano`,
`catalan`, `castellano`, `categoria`, `origen`). No fa falta tocar ni
reiniciar res més — la pròxima vegada que s'execute el pipeline, ja la usa.

## Flux de treball per a revisar el lèxic antic

1. Revisa `regles_prompt/lexic_per_frequencia.md` (les paraules del lèxic
   antic que de veres s'usen al corpus, prioritzades per impacte) o
   `lexic/palabras_traducidas.json` directament.
2. De les que estigues completament segur, afig-les a `lexico_fiable.json`
   editant-lo directament (o dis-me quines i les afig jo).
3. Si vols que una correcció també s'aplique al corpus ja generat
   (no només a futures generacions), s'amplia
   `04_corpus_sintetic/repara_corpus.py` amb la reversió corresponent.

## Com corregir/ampliar una regla morfològica

Revisa `regles_prompt/guia_dialectal_valencia_catala.md` (seccions 1-8).
Si cal canviar el prompt que usa el model, dis-m'ho i l'aplique en
`03_seleccio_de_model/evalua_models.py` (`SYSTEM_PROMPT_BASE`).

## Mètrica de puresa dialectal (proposta, encara no implementada)

`metrica_puresa_dialectal.md` especifica l'Índex de Puresa Dialectal
(IPD) — un score bidireccional per a detectar contaminació occidental↔oriental
en qualsevol text, reutilitzant les taules de `traductor/rules/` com a
diccionari de marcadors. Pensat per a aplicar-se sobre el corpus AVL, el
BOE i el corpus sintètic per a mesurar la qualitat/puresa de cada font.
