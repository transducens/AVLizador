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

### `visor_ipd.html` — revisar resultats sense tornar a executar res (14/10/2026)

En compte de generar un informe HTML nou per a cada corpus que es prova
(que s'acumulava com a fitxers solts al repo, regenerables però pesats —
vore `CLAUDE_HISTORIAL.md`), `--sortida` (el JSON, no el `--html`) ara és
l'eixida recomanada per a revisar resultats: inclou el mateix detall per
document (text, IPD, marcadors) i, si es dona `--camp-alt`, també les
dades de la segona columna (`text_alt`, `ipd_alt`, `marcadors_*_alt`) —
tot el que fa falta per a reconstruir la comparativa de dos columnes
sense tornar a executar `ipd.py`.

`visor_ipd.html` és un visor genèric i reutilitzable (sense dependències,
tot el processament al navegador, cap dada ix d'ahí) que carrega eixe
JSON i el mostra amb el text ressaltat i un cercador, igual que l'informe
`--html` pero sense generar un fitxer nou per cada corpus:

```bash
python ipd.py --corpus ../03_seleccio_de_model/benchmark_corpus.json \
    --camp occidental --camp-alt oriental --sortida resultat.json
# despres, obri visor_ipd.html al navegador i arrossega resultat.json
```

Admet carregar diversos JSON alhora (en pestanyes), per a comparar p.ex.
el benchmark i gplsi un al costat de l'altre sense generar res nou.

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

## Validació addicional (14/10/2026): text propi de l'usuari i el corpus gplsi

**Sobre dos notícies reals de l'usuari** (`proves/noticia_val.txt`
valencià, `proves/noticia_cat.txt` català): IPD 0,7308 / 0,1111 —
patró correcte, pero revisant els marcadors paraula a paraula van eixir
3 casos reals a investigar (un 4t, "estes"/"estès", el va descartar el
mateix usuari -- és una errata real del text català d'origen, sense
tilde, no un bug de l'IPD):

1. **"petit"/"menut" mal emparellat** a `lexic_general.json` -- despres
   confirmat també com a bug real del traductor (no nomes de l'IPD) amb
   el corpus gplsi de baix.
2. **"què" es cola com a marcador oriental en text valencià** perquè
   l'exclusió `_BUG_DADES_CONEGUTS_CAT` (que ja exclou "què"/"tard"/
   "ensenyament") només existix a `cat_val/lexic.py`, i `val_cat/lexic.py`
   té la seua pròpia `_BUG_DADES_CONEGUTS = {"després"}` sense espellar
   les altres 3 -- pendent d'arreglar (no trenca cap traducció hui,
   només contamina l'IPD, que fusiona les dos direccions).
3. **"acull" per col·lisió de persona** (1a "jo acull" vs. 3a persona
   compartida) -- confirmat que NO afecta cap traducció real (la clau de
   lookup sempre és la forma exacta d'una sola persona), nomes contamina
   l'IPD per ser un recompte agregat sense context.

**Amb el dataset `gplsi/CA-VA_alignment_test`** (Hugging Face, CC BY 4.0,
1.958 frases catalán/valencià traduïdes independentment): IPD global
0,9039 valencià / 0,0533 català -- confirma el mateix patró que el
benchmark de 151 i el BOE, a una escala i domini distints, tercera
confirmació independent.

**Filtrat per IPD per a separar sinonímia de fallos reals del motor**:
de les 1.958, 1.139 (58,2%) tenen IPD occidental=1,0 I oriental=0,0 a la
vegada -- sobre eixe subconjunt "net", el motor de traducció puja de
65,4%/61,9% a 88,9%/87,9% (val→cat/cat→val), molt a prop del benchmark
de 151. Confirma que gran part de la caiguda a escala era sinonímia
entre dos traductors independents, no el motor fallant més.

**L'anàlisi de fallos del motor sobre gplsi** (no de l'IPD, pero trobat
gràcies a esta validació) va destapar 4 bugs reals al traductor --
"xicotet"/"menut"/"petit" mal etiquetat `canonica`, els parells
AVL-only "tindre/vore/obtindre/mantindre" i "últim/darrer" retirats el
30/09/2026 (~25% dels fallos val→cat), `incoatius.py` sense cobrir el
plural "-ixen", i el plural "servicis"/"serveis" sense derivar -- vore
`CLAUDE.md` per al detall i l'estat de cada un.

## Homògrafs: spaCy només decidix els que declaren les dades (21/10/2026)

spaCy es consulta NOMÉS per a les formes que el proveïdor declara com a
homògrafes (entrades `problema: "homonimia_lexica"`, camps
`forma_problematica`, `lemas`, `categoria`). Si la lectura dialectal té
una categoria que cap altra lectura comparteix ("manca": n vs. adj), la
forma compta només quan spaCy li dona eixa categoria; si la comparteix
("bes", "blanca", "calces"), no compta mai. La resta de paraules no passa
per spaCy: es va provar un filtre general per categoria (amb i sense
llindar de seguretat) i es va descartar perquè spaCy no coneix moltes
formes valencianes ("hui", "faena") i n'inventa l'etiqueta.

| Corpus | Costat valencià | Costat català |
|---|---|---|
| Benchmark 151 | 0,9647 → 0,9749 | 0,1135 → 0,1115 |
| gplsi | 0,9341 → 0,9387 | 0,0685 → 0,0632 |

"després" (E0977, adjectiu "desprès"/"després" vs. l'adverbi compartit) i
"tancat" seguixen comptant com a marcador fals perquè les dades no els
declaren com a homògrafs: es resol marcant-los a l'origen. Detall al
docstring d'`ipd.py` ("HOMÒGRAFS ENTRE CATEGORIES").

## Relació amb la resta del projecte

Pendent documentat a `CLAUDE.md` (secció "Pendiente") i detallat a
`documentacio/hoja_de_ruta_ipd_y_proxima_fase.md`: este era el primer
pas a fer abans de seguir ampliant el motor de regles amb mes casos del
benchmark, i abans d'intentar una capa de model (LLM) nova per a
cat→val o de provar amb un corpus distint (el BOE, ja començat ací).
