*[Llegeix-ho en castellà](README.es.md)*

# Corpus sintètic paral·lel valencià → català (font: AVL)

Corpus de parells de frases valencià (occidental, norma AVL/GVA) → català
(oriental, norma IEC), generat traduint amb un LLM el corpus real
raspat de la web de l'AVL (Acadèmia Valenciana de la Llengua). Pensat
com a base per a entrenar/afinar un model de traducció entre les dos
variants, o com a banc d'avaluació.

## 1. D'on ix el text original (el costat "valencià")

Tot el text valencià ve de raspar la web de l'AVL:

```
avl_crawler.py / avl_probe.py / gnv_extractor.py / gvb_extractor.py / pdf_extractor.py
        ↓ (scraping per seccions: butlletí, glossari, gramàtica normativa,
        ↓  notes de premsa, pàgines, posts, legislació, acords normatius,
        ↓  publicacions, biografies...)
data/avl/raw/*.jsonl  →  neteja_corpus.py  →  data/avl/clean/*.jsonl
        ↓
data/avl/final/unified.jsonl          (2.233 documents, tot unificat)
        ↓ estudi_dialectal.py (classifica cada document com a occidental/
        ↓  oriental/mixt segons marcadors dialectals, i descarta el que
        ↓  no és clarament valencià occidental)
data/avl/final/dialectal/corpus_occidental_net.jsonl
        (1.778 documents, 821.195 tokens — NOMÉS text verificat
         com a valencià occidental pur)
```

**Decisió clau**: no es va traduir `unified.jsonl` (el corpus complet), sinó
específicament `corpus_occidental_net.jsonl`. Traduir des del corpus
complet hauria ficat en la mescla text que ja estava en català oriental
o en registre mixt, generant parells on l'"original" ja no era
realment valencià — hauria corromput el corpus abans de començar.

## 2. Com es va segmentar el text

`corpus_occidental_net.jsonl` té documents complets (paràgrafs sencers, de
vegades centenars de paraules). Es va decidir traduir **frase a frase**, no
document a document, per dos motius:

- El model qwen2.5:14b, amb el prompt/glossari que es valida al punt 3,
  es va fer benchmark sobre frases soltes — traduir paràgrafs llargs d'una
  vegada ix d'eixe règim provat i augmenta el risc que el model
  "explique" en lloc de traduir, o perda coherència.
- Permet deduplicar: molt text (sobretot del glossari i textos legals)
  es repetix paraula per paraula en diversos documents.

Regles de segmentació (`genera_corpus_sintetico.py`):
- Divisió per frases amb heurística de puntuació + llista d'abreviatures
  (per a no tallar en "Sr.", "art.", "núm.", etc.).
- Es descarten frases de menys de 5 paraules o 20 caràcters (soroll,
  numeració, taules) i de més de 280 caràcters (per a no arriscar que la
  resposta del model es talle a la mitat — el límit de generació són 200
  tokens, heretat del benchmark).
- Deduplicació exacta per contingut (normalitzant apòstrofs i
  majúscules): de 48.037 frases candidates van quedar **46.315 úniques**
  (1.722 duplicades, típic del glossari i de textos legals repetits
  entre butlletins).
- Cada frase única guarda quantes vegades apareixia al corpus original
  (`n_ocurrencies`) — informació que no afecta la traducció però és
  útil per a saber com de "central" és cada frase.

## 3. Com es va traduir

**Model**: qwen2.5:14b via Ollama, local (`temperature=0`, `num_predict=200`
per a reproduïbilitat).

**Per què este model i no un altre**: es van fer benchmark de diverses
opcions en `03_seleccion_de_modelo/` (diverses grandàries d'Ollama, regles
deterministes, NLLB-200) sobre 60 frases amb referència humana.
qwen2.5:14b + el prompt/glossari de davall va donar **BLEU 84,52 / chrF
92,34 / chrF++ 91,84**, molt per damunt de la resta (NLLB-200-600M, per
comparació, va donar BLEU 53,13 sense eixe prompt/glossari — confirma que
l'avantatge ve sobretot del prompt afinat, no només de la grandària del
model).

**Prompt i glossari**: es reutilitza tal qual el motor de
`03_seleccion_de_modelo/evalua_models.py` (el mateix que es va usar al
benchmark, per a no perdre eixa validació):
- Un system prompt amb les regles morfològiques documentades (demostratius,
  possessius, infinitius irregulars, subjuntiu present/imperfet,
  numerals, lèxic base) — el mateix conjunt que hi ha explicat com a guia
  d'estudi en `02_reglas_dialectales/reglas_prompt/guia_dialectal_valencia_catala.md`.
- Un glossari dinàmic per frase: abans de cridar el model es busquen en
  `palabras_traducidas.json` (1.604 formes) les paraules valencianes
  presents en eixa frase concreta, i se li passen com a pista
  `[VOCABULARI: valencià=català, ...]`.

**Una regla afegida només per a este corpus** (no toca el prompt del
benchmark, que queda intacte per a no perdre eixa validació): es va
detectar que en aplicar el prompt a text real (amb noms d'institucions,
cosa que no eixia a les frases curtes del benchmark) el model de vegades
"traduïa" sigles reals per unes altres (`AVL` → `IEC`). Es va afegir una
regla explícita dient que les sigles d'institucions (AVL, GVA, GNV, GVB,
RACV) mai es toquen, i només si ja estaven a l'original.

**On es va executar**: al clúster SLURM de la universitat ("abaco", 8x
RTX 2080 Ti), repartint el corpus en fragments per hash de l'id de cada
frase per a traduir amb diverses GPU a la vegada (vore `04_corpus_sintetico/slurm/`).

## 4. Auditoria de qualitat

Abans de donar el corpus per bo es va fer una auditoria completa
(`data/sintetico/analisi_corpus.html`, generada a partir d'este mateix
corpus), contrastant **cada una de les regles dialectals documentades**
contra el que el model va fer de veres, no només confiant que un LLM amb
bon BLEU en 60 frases es comportaria igual en 46.315 frases reals de tot
tipus. Metodologia:

- Per cada regla morfològica (este→aquest, meua→meva, siga→sigui...): en
  quantes frases apareixia la forma valenciana, i en quantes el català
  encara conservava eixa mateixa forma sense convertir.
- Per cada paraula freqüent del lèxic: cobertura real contra
  `palabras_traducidas.json`.
- Revisió manual d'una mostra de casos marcats com a sospitosos i dels
  "pitjors" resultats de cada categoria.

Açò va traure a la llum diversos problemes reals que les marques
automàtiques del propi generador no havien detectat (vore secció 5) — és
la raó per la qual existix `repara_corpus.py`.

## 5. Bugs trobats i corregits (sense tornar a traduir res)

Tot açò es va corregir amb `04_corpus_sintetico/repara_corpus.py` —
manipulació de text sobre el corpus ja generat, sense cridar altra vegada
Ollama:

| Problema | Casos | Com es va corregir |
|---|---|---|
| El literal `"Frase a traduir:"` (part del prompt) es colava a la resposta | 1.165 | Es va eliminar el literal; la resta de cada resposta ja era una traducció vàlida |
| `"blanca"` (adjectiu) confosa amb `"Blanca"` (nom regional de l'ocell *garsa* al lèxic) | 28 | Revertit al valencià original |
| `"pròxim"` (adjectiu comú) confós amb el sentit religiós `"el pròxim"` = `"proïsme"` | 45 | Revertit a l'original |
| `"Ramon"`/`"Manuel"` (noms de persona) tractats com a variants dialectals | 32 + 51 | Revertits a l'original, i arreglat de soca-rel en `evalua_models.carrega_lexic()` (exclou entrades de categoria "nom") |
| Formes de subjuntiu sense convertir (`siga`, `siguen`, `tinga`, `tinguen`) | 241+32+8+8 | Corregides amb les mateixes substitucions deterministes de `evalua_models.tradueix_regles()` |

**El que NO es va corregir automàticament, a propòsit**:
- `vinga`→`vingui` i `fora`→`fos`: tenen homonímia real (`"vinga!"` és
  també una interjecció, `"fora"` també significa "fora") — una
  correcció cega hauria introduït errors nous.
- 65 casos de `sigla_introduida` (el model inventa una sigla que no
  estava a l'original, p.ex. "l'Acadèmia" → "l'AVL"): no és una simple
  reversió de text, requeriria tornar a traduir eixes frases amb el
  prompt ja reforçat. Queden excloses de l'exportació neta, però sense
  corregir.

## 6. Estat final

| | |
|---|---|
| Frases úniques totals | 46.315 |
| Amb alguna marca de sospita | 663 (1,43%) |
| Netes | 45.652 (98,57%) |
| Compliment mitjà de les 38 regles morfològiques fiables | 96,7% (30 de 38 regles ≥95%) |
| Cobertura del lèxic (excloent entrades polisèmiques conegudes) | 97,2% |

Distribució per tipus de document: glossari 35% (16.240), publicacions 29%
(13.599), acord-normatiu 13% (6.163), gramatica_normativa 11% (5.038),
pagina 3% (1.563), nota-de-premsa 3% (1.554), legislacio 3% (1.208),
butlleti 2% (934), biografia/post <0,1%.

**Limitació important a tindre en compte**: el corpus és **sintètic** — el
va generar un LLM, no un traductor humà. Un model entrenat amb açò pot
arribar a acostar-se a la qualitat de qwen2.5:14b en esta tasca (i ser
molt més barat/ràpid d'executar), però no la superarà; el sostre de
qualitat és el del model que el va generar. Per a saber si un futur model
generalitza més enllà d'este corpus, convé validar contra text d'origen
humà (vore `data/boe/` — traduccions oficials reals, pendent
d'extraure i alinear; es deixa a banda per ara).

**Una altra limitació**: el corpus està concentrat en registre
institucional/normatiu (glossari, gramàtica, textos legals). Un model
entrenat només amb açò traduirà molt bé eixe registre i probablement
pitjor qualsevol altre (conversa, premsa informal, literatura).

## 7. Quin fitxer usar

```
data/sintetico/
├── corpus_sintetic_val_cat.jsonl            ← el corpus complet, amb metadades
├── corpus_sintetic_val_cat.abans_de_reparar.jsonl  ← còpia de seguretat pre-reparació
├── parallel_val_cat.jsonl                   ← ⭐ EL BO per a entrenar/usar
├── parallel.val / parallel.cat              ← el mateix, en 2 fitxers alineats línia a línia
└── analisi_corpus.html                      ← l'informe d'auditoria complet
```

- **`parallel_val_cat.jsonl`** — usa este. Són les 45.652 parelles netes
  (sense cap marca de sospita), format `{"val": "...", "cat": "..."}`,
  una per línia. Llest per a quasi qualsevol framework de fine-tuning.
- **`parallel.val` / `parallel.cat`** — el mateix contingut en format
  Moses/OPUS (dos fitxers de text pla, línia N d'un es correspon amb
  línia N de l'altre) — útil si la ferramenta que uses espera eixe
  format en lloc de JSONL.
- **`corpus_sintetic_val_cat.jsonl`** — només si necessites les metadades
  (`doc_type`, `source_url`, `n_ocurrencies`, `motius_sospita`) per a
  filtrar tu mateix d'una altra manera (p.ex. si volgueres incloure
  algunes frases sospitoses a propòsit, o ponderar l'entrenament per
  tipus de document).

## 8. Com es va generar / com reproduir-ho o ampliar-ho

Vore `04_corpus_sintetico/README.md` (ús de l'script principal) i
`04_corpus_sintetico/slurm/README.md` (execució al clúster amb GPU). Resum:

```bash
python genera_corpus_sintetico.py                 # generació completa (reprenible)
python repara_corpus.py                           # aplica les correccions de la secció 5
```
