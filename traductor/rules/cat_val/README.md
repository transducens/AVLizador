*[Read it in Spanish](README.es.md)*

# `cat_val/` — direcció inversa (català → valencià)

Direcció inversa del motor de regles: català oriental (norma IEC) →
valencià occidental (norma AVL/GVA). Companya de `traductor/rules/val_cat/*.py`
(la direcció original, val→cat), que es queda exactament igual, sense
tocar. Vore `documentacio/hoja_de_ruta_traductor_invers.md` (arrel del
repositori) per al raonament complet, les xifres reals que justifiquen
cada decisió, i l'estat de cada fase.

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
- Els mateixos fitxers de dades de `traductor/data/*.json` — cada
  entrada ja porta els dos camps (`valenciano`/`catalan`), així que no
  cal cap fitxer nou, nomes carregadors nous que indexen per l'atre camp.

**Nou, amb estructura semblant pero lògica pròpia** (cada fitxer explica
al seu docstring si "copia" el patró de l'equivalent val->cat o si la
lògica és genuïnament distinta): `engine.py`, `lexic.py`,
`conjugacions_dict.py`, `possessius.py`, `numerals.py`, `demostratius.py`,
`accentuacio.py`, `concordanca_dos_dues.py`, `preposicions_locucions.py`.

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
