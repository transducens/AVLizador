*[Llig-ho en castellà](README.es.md)*

# `pipeline/09_index_puresa_dialectal/` — Índex de Puresa Dialectal (IPD)

Novena etapa del projecte AVLizador (vore `README.es.md` de l'arrel):
mètrica per a saber, de qualsevol text, quin percentatge de les seues
paraules dialectalment marcades són formes **occidentals** (valencianes)
en compte de **orientals** (catalanes).

```
IPD = total_paraules_occidentals / (total_occidentals + total_orientals)
```

Un IPD d'1,0 vol dir que cap paraula catalana marcada apareix al text;
0,0 vol dir el contrari; i `None` (cap resultat) vol dir que el text no
conté cap paraula dialectalment marcada de les que coneix l'índex — no
es pot calcular un percentatge sobre zero.

## Per què un mòdul nou, si ja hi havia una mètrica pareguda

`pipeline/01_extraccio_i_neteja/estudi_dialectal.py` ja calculava una cosa molt
pareguda (`ratio_occ`, a la seua tasca 1), pero contra dos llistes
curades a mà d'una huitantena de paraules cadascuna
(`OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS`, dins del mateix fitxer).
Este mòdul calcula el mateix índex, pero contra l'índex de parells
dialectals que `traductor/` ja manté per a traduir de veres:

| | Llistes antigues (`estudi_dialectal.py`) | Índex de l'IPD (`traductor/data/*.json`) |
|---|---|---|
| Grandària | ~70 paraules per dialecte | ~53.000 parells (1.471 de lèxic general + ~52.000 formes verbals conjugades + demostratius/possessius/numerals) |
| Font de veritat | Llista a banda, mantinguda a mà | La MATEIXA que fa servir el traductor per a traduir |
| Abast | Només documents ya carregats a `unified.jsonl` | Qualsevol text — una frase solta, un fitxer, un corpus JSONL |

No es reinventa cap dada nova: es reutilitzen directament els
carregadors (`carrega_lexic`, `carrega_conjugacions`,
`carrega_demostratius`, `carrega_numerals`, `carrega_possessius`...) de
`traductor/rules/val_cat/` i `traductor/rules/cat_val/`, en les dos
direccions (cada direcció resol l'ambigüitat pel seu costat, aixina que
fusionar-les dona mes cobertura que qualsevol de les dos soles).

## Limitació coneguda, acceptada de moment

Només compta paraules que apareixen LITERALMENT a algun diccionari de
lookup exacte. Els patrons PRODUCTIUS de sufix del motor (p.ex.
`-és`(occ)/`-ès`(or) d'`accentuacio.py`, o l'alternança incoativa
d'`incoatius.py`) encara no hi estan inclosos — cobrixen un patró obert
(qualsevol paraula que acabe aixina), no una llista tancada, i
barrejar-ho amb el lookup exacte en esta primera versió complicava el
disseny sense evidència encara de quant canviaria el resultat. Es queda
documentat com a ampliació pendent, no com un oblit.

## Ús

Com a script:

```bash
python ipd.py --text "Este xiquet vol vindre hui."
python ipd.py --fitxer un_document.txt
python ipd.py --corpus ../../dades/avl/final/unified.jsonl --camp text --sortida resultat.json

# Informe HTML per a vore i depurar frase a frase (paraules ressaltades
# en verd=occidental/taronja=oriental), amb les dos columnes del
# benchmark del projecte una al costat de l'atra:
python ipd.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
    --camp occidental --camp-alt oriental --html informe.html

# Corpus grans (p.ex. el del BOE, ~268.000 linies): --limit per a provar
# amb una mostra abans de llançar-ho sencer (cada frase es tokenitza amb
# spaCy, aixina que tot el fitxer pot tardar ~30 minuts):
python ipd.py --corpus ../../dades/boe/corpus_entrenamiento.jsonl \
    --camp texto_catalan --limit 5000
```

Accepta tant un fitxer JSONL (un document per linia) com un JSON normal
amb un array d'objectes (com `benchmark_corpus.json`) — es detecta sol.

Com a mòdul, des d'un atre script del projecte:

```python
from ipd import calcula_ipd

calcula_ipd("Este xiquet vol vindre hui.")["ipd"]  # -> 1.0
```

## Dos bugs reals trobats i corregits (13/10/2026, a petició de l'usuari)

La primera versió feia un lookup ingenu amb un regex simple. Revisant el
propi benchmark de l'usuari ("aquestes" quasi no es detectava com a
marcador oriental) van aparéixer dos problemes reals:

1. **Sense filtre de categoria gramatical**: formes verbals RARES de
   `conjugacions_dialectals.json` (p.ex. "entre" = "jo entre" d'"entrar")
   coincidien amb paraules COMUNS ("entre" preposició, "poden", "sobre",
   "base", "pobles"...), inflant el recompte dins de text que no tenia
   res de dialectal. Corregit aplicant el mateix filtre de POS (spaCy)
   que ja fa servir `ConjugacionsDictRule` per a traduir.
2. **Prefix elidit**: el tokenitzador tracta l'apòstrof com a part de la
   paraula, aixina que "d'aquestes" és UN SOL token i mai casava amb
   l'entrada "aquestes". Corregit reutilitzant `separa_prefix_elidit`.

## Validació feta (13/10/2026)

Contra el benchmark de 151 frases de `pipeline/03_seleccio_de_model/benchmark_corpus.json`
(despres dels dos fixes): el costat valencià dona **IPD 0,9339** (240
marcadors occidentals, 17 orientals) i el costat català **IPD 0,0153** (4
occidentals, 258 orientals).

**Confirmat a mes escala amb el corpus del BOE** (`dades/boe/`,
`dades/boe_net/`): el costat català es queda igual de pur en mostres molt
mes grans i d'un domini distint (5.000 frases de
`corpus_entrenamiento.jsonl`: IPD 0,0181; 200 frases de
`muestra_test_dialectal.json`: IPD 0,0127) — el mateix patró es repetix
en tres corpus independents. La mostra del BOE també va aportar evidència
molt mes forta sobre "què" (29 aparicions reals sense tocar en valencià,
front a només 4 al benchmark menut) i dos candidats nous al mateix tipus
de problema que "nou" (entrades de lèxic sense filtre de categoria
gramatical): "afecte" (confós amb "carinyo" quan en realitat vol dir
"subjecte a" en text legal) i "estat" (spaCy a vegades l'etiqueta verb
quan és el substantiu "l'Estat").

## Relació amb la resta del projecte

Pendent documentat a `CLAUDE.md` (secció "Pendiente") i detallat a
`documentacio/hoja_de_ruta_ipd_y_proxima_fase.md`: este era el primer
pas a fer abans de seguir ampliant el motor de regles amb mes casos del
benchmark, i abans d'intentar una capa de model (LLM) nova per a
cat→val o de provar amb un corpus distint (el BOE, ja començat ací).
