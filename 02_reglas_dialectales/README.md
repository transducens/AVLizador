*[Llegeix-ho en castellà](README.es.md)*

# Etapa 2 — Regles dialectals i lèxic

Tot allò relacionat amb les diferències dialectals entre valencià
(occidental, norma AVL/GVA) i català (oriental, norma IEC): d'on ixen,
com es documenten, i les dades estructurades que usa el pipeline de
traducció. Amb el corpus font ja net (etapa 1), esta etapa defineix
**què canvia** entre els dos dialectes — les regles que després usa el
model per a traduir (etapes 3-4).

**[`reglas_dialectales_con_evidencia.md`](reglas_dialectales_con_evidencia.md)**
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

Vore `../documentacion/metodologia_y_resultados.md` seccions 2 i 4 per al
detall complet del procés.

## Estructura

```
02_reglas_dialectales/
├── reglas_prompt/      documentació per a llegir i revisar (comença ací)
├── lexico/             dades estructurades: parells valencià-català en JSON
└── fuentes/             material brut d'origen (no pensat per a llegir directament)
```

### `reglas_prompt/` — comença per ací

El material d'estudi i revisió. Vore el seu propi
[`reglas_prompt/README.md`](reglas_prompt/README.md) per al detall, però
en resum:

- **`guia_dialectal_valencia_catala.md`** — document tipus tema de llibre
  amb totes les regles dialectals explicades (morfologia + lèxic). El
  document de referència principal.
- **`lexic_per_frequencia.md`** — per a revisar el lèxic ràpid: només les
  paraules que de veres s'usen al corpus, ordenades per impacte.
- **`system_prompt.md`** / **`glossari_dinamic.md`** — com està implementat
  açò al codi (el prompt literal, el mecanisme del glossari dinàmic).

### `lexico/` — dades estructurades (JSON)

| Fitxer | Què és |
|---|---|
| `lexico_fiable.json` | **⭐ El que usa de veres el pipeline ara mateix.** 194 parells (31 d'Apertium + 34 de Paula Guerrero + 129 de `fuentes/paralelos.txt`) revisats i en els quals confies. `evalua_models.py` ja no llig `palabras_traducidas.json` — llig este fitxer directament. Els numerals compostos amb guionet (huitanta-cinc, noranta-huit...) estan col·lapsats en les seues formes base (`huit`, `huitanta`) perquè el glossari dinàmic tokenitza per guionet — vore `guia_dialectal_valencia_catala.md` secció 6. Per a afegir paraules noves, edita este JSON directament. |
| `apertium_368_val_cat.json` | Les 368 formes que Apertium marca com a valencianes, separades en confirmades (68) i pendents (3, sense parella trobada, sense inventar res). D'ací ixen les 30 entrades d'origen "apertium" de `lexico_fiable.json` (68 confirmades per Apertium, reduïdes a formes base després de llevar numerals compostos redundants). |
| `contrastius_paula_guerrero.json` | 35 parells valencià-català categoritzats (determinants, verbs incoatius, lèxic...), d'una font externa curada a banda. 34 dels 35 ja estan bolcats en `lexico_fiable.json`. |
| `palabras_traducidas.json` | Còpia de treball del lèxic **antic** (l'original viu en `03_seleccion_de_modelo/palabras_traducidas.json`, ja no usat pel pipeline). Seguix sent útil com a pedrera: si en revisar-lo trobes una paraula de la qual estàs completament segur, afig-la a `lexico_fiable.json` editant-lo directament. |

### `fuentes/` — material brut d'origen

No pensat per a llegir directament (llevat de `reglas_cat_val.md`, que és
més llegible); són els fitxers d'on ixen les dades de `lexico/` i de la
guia.

| Fitxer | Què és |
|---|---|
| `reglas_cat_val.md` | Informe generat automàticament comparant `apertium-cat.cat.dix` (`v="cat"` vs `v="val_gva"`) amb la llista curada — d'ací ix el 90% del contingut de `pares_valenciano_catalan.json` i de la guia dialectal. |
| `apertium-cat.cat.dix` | El diccionari morfològic d'Apertium en brut (format XML/lttoolbox, ~66.500 entrades). |
| `palabras_traducidas.txt` | La llista curada original, en text pla, abans de convertir-se a JSON. |
| `palabras_val.json` | Formes marcades específicament com a valencianes (`v="val_gva"`) en Apertium — sense parella catalana directa, és matèria primera, no parells ja fets. |

## Com afegir una paraula nova al lèxic fiable

Edita `lexico/lexico_fiable.json` directament, afegint una entrada nova a
l'array `entradas` amb el mateix esquema que les altres (`valenciano`,
`catalan`, `castellano`, `categoria`, `origen`). És el fitxer que usa
`evalua_models.py` (i per tant també `genera_corpus_sintetico.py`, que el
reutilitza). No fa falta tocar ni reiniciar res més — la pròxima vegada que
s'execute el pipeline, ja la usa.

## Flux de treball per a revisar el lèxic antic

1. Revisa `reglas_prompt/lexic_per_frequencia.md` (les paraules del lèxic
   antic que de veres s'usen al corpus, prioritzades per impacte) o
   `lexico/palabras_traducidas.json` directament.
2. De les que estigues completament segur, afig-les a `lexico_fiable.json`
   editant-lo directament (o dis-me quines i les afig jo).
3. Si vols que una correcció també s'aplique al corpus ja generat
   (no només a futures generacions), s'amplia
   `04_corpus_sintetico/repara_corpus.py` amb la reversió corresponent.

## Com corregir/ampliar una regla morfològica

Revisa `reglas_prompt/guia_dialectal_valencia_catala.md` (seccions 1-8).
Si cal canviar el prompt que usa el model, dis-m'ho i l'aplique en
`03_seleccion_de_modelo/evalua_models.py` (`SYSTEM_PROMPT_BASE`).

## Mètrica de puresa dialectal (proposta, encara no implementada)

`metrica_puresa_dialectal.md` especifica l'Índex de Puresa Dialectal
(IPD) — un score bidireccional per a detectar contaminació occidental↔oriental
en qualsevol text, reutilitzant les taules de `traductor/rules/` com a
diccionari de marcadors. Pensat per a aplicar-se sobre el corpus AVL, el
BOE i el corpus sintètic per a mesurar la qualitat/puresa de cada font.
