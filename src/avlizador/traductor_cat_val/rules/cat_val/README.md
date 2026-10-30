*[Read it in Spanish](README.es.md)*

# `cat_val/` — direcció inversa (català → valencià)

Direcció inversa del motor de regles: català oriental (norma IEC) →
valencià occidental (norma AVL/GVA). Companya de `traductor_cat_val/rules/val_cat/*.py`
(la direcció original, val→cat), que es queda exactament igual, sense
tocar. Vore `documentacio/hoja_de_ruta_traductor_invers.md` (arrel del
repositori) per al raonament complet, les xifres reals que justifiquen
cada decisió, i l'estat de cada fase.

## Capes actuals (23/10/2026)

`engine.py` (`RuleEngineInvers`) etiqueta la frase amb spaCy una vegada i
aplica estes 9 capes en este ordre; cada una salta els tokens que ja ha
traduït una altra:

| capa | fitxer | què fa | usa spaCy |
|---|---|---|---|
| 1 | `lexic.py` | parells del lèxic (una paraula i frases de 2-3); `canonica` en cas de dubte; homògrafs resolubles; article, contracció i apòstrof | homògrafs i gènere |
| 2 | `conjugacions_dict.py` | formes verbals; les que tenen lectura no verbal, només si spaCy diu verb | sí |
| 3 | `possessius.py` | meva → meua | no |
| 4 | `numerals.py` | cardinals (vuitanta → huitanta); els ordinals van pel lèxic | no |
| 5 | `concordanca_dos_dues.py` | les dues → les dos | no |
| 6 | `demostratius.py` | aquest → este, aqueix → eixe (entrades `det` del lèxic) | no |
| 7 | `incoatius.py` | serveix → servix (sense llista: lema en -ir validat contra el diccionari) | sí |
| 8 | `accentuacio.py` | francès → francés | no |
| 9 | `per_a_infinitiu.py` | per + infinitiu → per a (llevat de "per haver") | sí |

Dades: només `traductor_cat_val/data/lexic_general.json` i
`conjugacions_dialectals.json` (còpies de `dades/lexic/`). Cap llista de
paraules a mà.

**Homògrafs de la mateixa categoria** ("calces", "gandula", "gandules") i
**col·lisions** ("cop", "cops", dos traduccions sense canònica): els
resol la capa opcional `traductor_cat_val/model_llengua/` (spaCy per categoria dels
`lemas` + model de llengua FLOR-760M). El motor sol, sense eixa capa,
tradueix sempre els irresolubles i deixa "cop/cops" sense traduir. Vore
`traductor_cat_val/model_llengua/README.md`.

Les seccions de baix són l'historial de com s'hi va arribar.

## Per què existix com a paquet a banda, no com un flag

Invertir la direcció NO és "la mateixa regla cap arrere" en la majoria
dels casos — la lògica concreta canvia de veres (vore la hoja de ruta
per als casos exactes: la col·lisió indicatiu/subjuntiu de 3a plural
desapareix en esta direcció, pero apareixen altres noves com "aquest"->
"este"/"eixe"). Mesclar les dos direccions al mateix fitxer amb
condicionals hauria fet el codi menys llegible, no mes — cada regla
d'ací és un fitxer propi, auditable de forma independent.

## Què es reutilitza i què es copia

**Reutilitzat directament, sense duplicar**:
- `Token`, `tokenize`/`detokenize` i tots els helpers de
  `rules/__init__.py` (`separa_prefix_elidit`, `aplica_amb_prefix_elidit`,
  `corregeix_determinant_abans`...).
- `pos_tagger.py` (spaCy) — sense cap canvi, i amb MES fiabilitat ací que
  en val->cat, perquè l'entrada ja és català real (l'idioma en què
  `ca_core_news_sm` està entrenat).
- Els mateixos fitxers de dades de `traductor_cat_val/data/*.json` — cada
  entrada ja porta els dos camps (`valenciano`/`catalan`), així que no
  cal cap fitxer nou, nomes carregadors nous que indexen per l'atre camp.

**Nou, amb estructura semblant pero lògica pròpia** (cada fitxer explica
al seu docstring si "copia" el patró de l'equivalent val->cat o si la
lògica és genuïnament distinta): `engine.py`, `lexic.py`,
`conjugacions_dict.py`, `possessius.py`, `numerals.py`, `demostratius.py`,
`accentuacio.py`, `concordanca_dos_dues.py`, `incoatius.py`,
`per_a_infinitiu.py` (`preposicions_locucions.py` i `relatiu_on.py` es van
retirar el 14/10 i el 21/10/2026).

## Estat actual (13/10/2026) — Fase 2 de la hoja de ruta

**113/151 (74,8%) frases exactes, BLEU 97,72, chrF 99,17**, mesurant
contra el mateix benchmark de 151 frases (camp `oriental` com a entrada,
`occidental` com a referència; `evalua_models.py --model traductor
--direccio cat-val`). 485/485 doctests en verd.

**Una troballa important va corregir la hoja de ruta sobre la marxa**:
es pensava que el filtre POS (spaCy) gairebé no faria falta en esta
direcció, perquè el problema "persones"/"personis" és asimètric. Cert
per a EIXE cas concret, pero mesurant contra el benchmark van aparéixer
atres col·lisions amb verbs normals (no rars): "moro" (català, "jo moro"
de "morir") col·lidia amb "moro" dins "blat de moro"; "través" amb una
forma de "travar"; "signes" amb "tu signes" de "signar". El filtre POS SI
fa falta — implementat a `conjugacions_dict.py`.

**22/10/2026 — el filtre POS ja no s'aplica a totes les formes**: ho
decidix el propi diccionari. Les formes de `conjugaciones_general.json`
que porten una lectura no verbal a `morfologia` ("estat" nom, "través",
"obres", "moro"...) només es tradueixen si spaCy diu verb; la resta,
sempre llevat que spaCy diga nom propi ("París", "Mano"). Les 900 formes
de `verbos_diferentes_conjugados.json` (arrel distinta: signar->firmar,
prémer->polsar) sempre exigixen verb, perquè eixe fitxer no marca
homògrafs i un error canvia la paraula sencera ("els premis" -> "les
polses"). Substituïx la llista a mà `SEMPRE_VERB_INVERS = {"sigui"}`.
Benchmarks: 151 146, gplsi 1479, BOE estricte 8857/9453, ampli 1200
(amb la llista: 147 / 1479 / 8844 / 1199; l'única frase perduda és una
cita llatina, "confinis"/"finis").

**22/10/2026 — Majúscules i noms propis (decisió de l'usuari)**: en
cat->val es tradueixen TOTES les paraules, també les que van en
majúscula. No cal protegir-les: el diccionari no conté traduccions de
noms propis (els topònims `v:top_gva` no s'apliquen mai), així que un nom
només canvia si coincidix per casualitat amb una paraula comuna del
lèxic. Revisat contra el BOE català sencer, gplsi i el 151, i contra una
llista de noms, cognoms i topònims catalans freqüents, els únics casos
trobats són:
- topònims: "les Garrigues" -> "coscollars" (15 vegades al BOE, sempre en
  majúscula), "la Noguera" -> "anouer" (7), "Maó" -> "rajola", "la Riba"
  -> "vora", "Toro" -> "bou";
- noms de persona: "Estrella" -> "Estrela", "Nen" -> "Xiquet";
- noms d'institucions i títols que contenen paraules comunes ("Cementiri
  Britànic", "Llei d'Ús i Ensenyament").
Cap nom coincidix amb una forma verbal que es traduïsca sense spaCy (les
formes verbals que no són homògrafes es frenen si spaCy diu PROPN:
"París", "Mano"). Si es vol arreglar, el net és que el proveïdor marque
eixos topònims al lèxic, com ja fa amb els valencians.

**22/10/2026 — Homògrafs de cat->val**: de les entrades
`homonimia_lexica` del lèxic, les que afecten esta direcció són les que
tenen la forma ambigua al costat català. Les resol spaCy (les lectures
tenen categories distintes): deu, nou/nous, manca/manques, panotxa(es),
recuita(es), reeixida(es), fartanera(es), rentadora(es) ("sota" no
s'aplica: el valencià té dos paraules). Només tres tenen lectures de la
mateixa categoria i necessitarien un LLM: "calces" (bragues o calces de
pantaló), "gandula" i "gandules" (hamaca o dona gandula). Als tres corpus
apareixen 3 vegades ("calces", en llistes d'aranzels del BOE) i
"gandula(es)" cap: el motor les tradueix sempre. **23/10/2026**: resoltes
a `traductor_cat_val/model_llengua/` sense LLM per preguntes (spaCy per categoria
dels `lemas` + model de llengua): irresolubles 12 → 18/24 al benchmark
d'homògrafs. De passada es va corregir E0592 ("hamaces" → "hamaques").

**"aquest"->"este"/"eixe" (resolt parcialment, 13/10/2026)**: es va
provar primer deixar-ho sense tocar (preferir fals negatiu) — el
benchmark es va ENFONSAR de 92 a 44/151 (107 aparicions, la majoria del
corpus). Mesurat amb `difflib` paraula a paraula sobre les 151 frases:
40/52 casos reals volen "este", 12/52 "eixe" (~77%/23%). Es va
implementar "aquest"->"este" com a DEFAULT MESURAT, no una suposició —
queda un 23% d'error conegut i acceptat, pendent de la Fase 3 (LLM) per
a superar-ho.

**Implementat el 13/10/2026** (abans "deliberadament sense implementar",
vore la hoja de ruta per al detall complet d'evidència de cada un):
`incoatius.py` invers (llista tancada de 7 arrels verbals evidenciades:
establir/servir/aconseguir/requerir/oferir/exhaurir/coincidir),
`relatiu_on.py` invers (8/8 casos reals volen "on"->"a on", 2 excepcions
de construccions d'èmfasi temporal acceptades), lèxic multi-paraula
català ("blat de moro"->"dacsa" i 6 parells mes, amb concordança de
gènere invertida), exclusió d'"ensenyament" (5/6 casos reals el volien
sense tocar), i la locució "per a acabar"->"per acabar".

**20/10/2026**: `incoatius.py` invers REESCRIT sense llista d'arrels a mà:
decidix spaCy (VERB + lema en "-ir") validat contra els infinitius de
`conjugacions_dialectals.json` (vore el docstring del mòdul per al problema
complet). gplsi 1337->1505/1958. Col·lisions del lèxic
resoltes amb el camp `canonica` del proveïdor (regla fixa: en cas de dubte,
la canònica; els ordinals de l'usuari mantenen prioritat). Nova
`corregeix_article_abans()` (`rules/__init__.py`): "el darrer"->"l'últim",
"el batlle"->"l'alcalde".

**Deliberadament sense implementar encara**:
- Fase 3 de veres: desambiguació assistida per LLM d'"aquest" per damunt
  del 77% (candidats tancats "este"/"eixe", mateix patró que
  `pipeline/08_traduccio_corpus/postprocessat_llm/` ja fa servir per a indicatiu/
  subjuntiu).
- Homògraf "nou"/"anou" (nou/nou en català, 3 casos) — sense senyal de
  context comprovada encara.

**21/10/2026 — regles de la guia de traducció dialectal** (mesurades als
corpus oficials AVL + BOE, vore `documentacio/hoja_de_ruta_traductor_invers.md`):
nou `per_a_infinitiu.py` (C2, "per" + infinitiu -> "per a", excepte "per
haver"); "aquí" -> "ací" (D1) és un parell nou del diccionari (E1648, sense
codi); `relatiu_on.py` RETIRAT (C3: el valencià oficial usa "on" sense "a").
BOE (mostra de 2.000 línies) 360 -> 368 frases exactes.
