# `avlizador.traductor_cat_val.model_llengua` — homògrafs cat→val amb un model de llengua

Postprocessat (23/10/2026) per a les paraules catalanes ambigües que el
motor de regles no pot resoldre a soles. Des del 29/10/2026 forma part
del **sistema principal** (`translate_cat_val`).

## Model per defecte: KenLM + classificador de sentit (des del 13/11/2026)

**Decisió de l'usuari (13/11/2026)**: KenLM + el classificador de sentit
substituïx FLOR-760M com a model per defecte. FLOR continua
disponible com a opció (`model="flor"`, extra `[ml]`).

| | KenLM + classificador | FLOR-760M |
|---|---|---|
| Homògrafs v1 (253) | **227** | 217 |
| Homògrafs v2 (160) | **111** | 96 |
| Manual mescla BOE + AVL (458) | **232** | 231 |
| 151 (154) | 144 | **145** |
| BOE estricte (2.000) | 1.894 | 1.894 |
| gplsi (1.958) | 1.550 | **1.551** |
| Temps per frase candidata | **0,1 ms** | 833 ms |
| Memòria | **~74 MB** | ~1,5 GB |
| Dependències | `kenlm` | `torch` + `transformers` |

Exactes, `avalua_sistema_20261113_1308` (KenLM) i `_1016` (FLOR). En les 257 decisions dels
homògrafs, KenLM + classificador fa 193 encerts i 1 error greu (que
canvien el sentit). Per què, com s'hi va arribar i què es va descartar
(KenLM català, fastText, KenLM sense poda, en dos sentits, de lemes,
híbrid amb FLOR): `documentacio/resultats_model_llengua_kenlm.md`.

Ús:

- `translate_cat_val(text)`: KenLM si hi ha el paquet `kenlm` i els
  fitxers; si falta alguna cosa, el motor sol i un avís
  (`AvisSenseModelLlengua`).
- `translate_cat_val(text, model="kenlm")`: igual, però si falta alguna
  cosa, `FaltaKenLM` (s'ha demanat expressament).
- `translate_cat_val(text, model="flor")`: FLOR-760M (extra `[ml]`; sense
  ell, motor sol i avís).
- Ordres: `avlizador tradueix [--model flor]`, `avlizador avalua [--model
  kenlm flor]`.

Peces:

- `kenlm.py`: `normalitza` (la mateixa de l'entrenament; la importa
  `pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py`) i
  `ModelKenLM` (log P natural de la frase; prior = ln((n + 1) / tokens)
  amb les freqüències del text d'entrenament, `<model>_freq.json`).
- `sentit.py`: classificadors de sentit amb una interfície fixa,
  `candidat(punt) -> str | None`. Des del 13/11/2026, `ClassificadorSentit`
  (`sentit.json`): el classificador GENERAL, part del sistema, sense cap
  cas a mà. Un Naive Bayes (lemes d'spaCy al voltant) per a cada grup de
  paraules ambigües del lèxic (singular i plural junts si tenen els mateixos
  `lemas`), entrenat amb frases valencianes de MaCoCu + DOGV, sense l'AVL
  (`pipeline/03_seleccio_de_model/model_llengua/sentit_general.py`). Un grup
  només entra si acerta com a mínim un 0,7 (equilibrat) amb frases reals
  apartades; hui cop (0,89), deu (0,81) i cops (0,75). La resta (nou,
  manca, calces, gandula, rentadora, reeixida: no arriben; fartanera,
  panotxa, recuita: sense dades) no en tenen i fan com sempre. Quan hi haja
  més dades, una paraula que passe el llindar hi entra sola. L'antic de
  "cop" (`ClassificadorCop`, `nb.json`) encara es carrega si no hi ha
  `sentit.json`.
- `CRITERI_KENLM`: marge 3, la catalana per defecte, λ 1,5 en els homògrafs
  i 0,75 en les col·lisions, desempat < 2 amb el classificador: si KenLM
  guanya per menys de 2, decidix el classificador de la paraula (si en té);
  si no, la regla de sempre.
- `punts.decisio_spacy`: abans del model, spaCy descarta lectures
  impossibles; des del 13/11/2026 també si la paraula d'abans és un pronom
  personal ("Tu manques de paciència": verb, no nom), i un NUM darrere de
  "una" no és el numeral ("una nou": decidix el model). spaCy etiqueta el
  text sense els espais del principi i del final (un espai al final canviava
  l'etiqueta).

Fitxers (fora de git): `valencia_net_dogv_o5.binary` (82 MB; des de la
2.0.0, MaCoCu valencià net + el DOGV 2025-2026 sencer, ordre 5, poda de
singletons: `valencia_net_dogv2` en Abaco), `valencia_net_dogv_freq.json` i
el classificador `sentit.json` (`sentit_dogv2_avl`: el mateix text + l'AVL;
o l'antic de "cop", `nb.json`). Publicats en Hugging Face
([`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va),
CC BY 4.0; `REVISIO_HF` diu quina revisió baixa cada versió del paquet):
sense `AVLIZADOR_KENLM_DIR`, `directori_kenlm` els busca en la memòria cau de
Hugging Face i els baixa la primera vegada. En la imatge Docker van en
`/opt/kenlm` (es baixen en construir-la, o es copien de `docker/kenlm/`).
Per a publicar-ne una versió nova: `scripts/hf_model/kenlm.py`. El paquet `kenlm` es compila en instal·lar-lo (`pip install
"avlizador[kenlm]"`; en Windows cal compilador, la imatge Docker és Linux).

## Manteniment: paraules i corpus nous (16/11/2026)

Què cal fer perquè el sistema KenLM + classificador tinga en compte una
paraula ambigua nova o un corpus nou. Totes les ordres, des de l'arrel del
repositori. En Abaco, amb el venv activat (`source
~/venvs/avlizador/bin/activate`) i la branca al dia (`git pull`).

Els fitxers del model viuen en **tres llocs**, i cada vegada que en canvie
un cal copiar-lo als tres:

| Lloc | Per a què |
|---|---|
| `dades/macocu/kenlm/` en Abaco | avaluar (`avalua_sistema.sh`, `compara_models.sh`) |
| la carpeta d'`AVLIZADOR_KENLM_DIR` en el PC (si s'usa KenLM fora de Docker) | `translate_cat_val`, `avlizador tradueix` |
| `docker/kenlm/` (fora de git) | la imatge Docker (`/opt/kenlm`); cal reconstruir-la |

### 1. Paraula ambigua nova

| # | Pas | On |
|---|---|---|
| 1 | El company afig l'entrada al lèxic: `forma_problematica`, `problema` (`colision_homonima` o `homonimia_lexica`) i, si són homògrafs, `lemas`. Convé que l'`espanol` de cada lectura estiga bé (servirà si s'etiqueten els sentits amb el castellà). | `dades/lexic/lexico_general.json` |
| 2 | Copiar el lèxic dins del paquet. D'ací en avant el sistema **ja tracta la paraula com a ambigua** (`punts.carrega_punts`). Commit i `git pull` en Abaco. | PC |
| 3 | Comprovar que les candidates són en la taula de freqüències. Si en falta alguna, regenerar-la (si no, compta com a 0 aparicions i amb λ guanya avantatge: va passar amb «faltes» el 13/11). | PC / Abaco |
| 4 | **KenLM no es toca**: és un model general del valencià i puntua qualsevol frase. | — |
| 5 | Reentrenar el classificador (secció 3). | PC o Abaco |
| 6 | Copiar als tres llocs el que haja canviat (`valencia_net_dogv_freq.json`, `sentit.json`) i reconstruir la imatge Docker. | — |
| 7 | Mesurar. | Abaco |

Si es vol mesurar la paraula nova, cal afegir frases seues al benchmark
d'homògrafs (només amb permís de l'usuari).

```bash
# 2. Lèxic -> paquet (PC)
python scripts/sync_data.py
python scripts/sync_data.py --check          # "Tot sincronitzat"

# 3. Falten candidates en la taula de freqüències? (sense kenlm: val en Windows)
#    Imprimix [] si hi són totes. Canviar la ruta per la del fitxer que s'use.
python -c "import json; from avlizador.traductor_cat_val.model_llengua.kenlm import ModelKenLM; from avlizador.traductor_cat_val.model_llengua.lemes import formes_candidates; f = json.load(open('docker/kenlm/valencia_net_dogv_freq.json', encoding='utf-8')); print(ModelKenLM(None, f).paraules_sense_freq(formes_candidates()))"
#    (En carregar el sistema també ix l'avís AvisFreqKenLM.)

# 3b. Si en falta alguna: regenerar-la en Abaco (llig el lèxic del paquet: abans, git pull)
cp dades/macocu/kenlm/valencia_net_dogv_freq.json dades/macocu/kenlm/valencia_net_dogv_freq_$(date +%Y%m%d).json
python pipeline/08_traduccio_corpus/macocu/kenlm/freq_unigrames.py dades/macocu/kenlm/valencia_net_dogv.txt
#    -> dades/macocu/kenlm/valencia_net_dogv_freq.json. Al PC:
scp nmartin@abaco:~/scrapeo/AVLizador/dades/macocu/kenlm/valencia_net_dogv_freq.json docker/kenlm/

# 6. Imatge Docker amb els fitxers nous de docker/kenlm/
docker compose up --build

# 7. Mesurar (Abaco, des de pipeline/03_seleccio_de_model/model_llengua)
MODELS="kenlm" BENCHMARKS="homografs homografs_v2 manual" sbatch avalua_sistema.sh
#    -> pipeline/03_seleccio_de_model/resultats/avalua_sistema_<data>/resum_<data>.md
```

### 2. Corpus nou

El corpus servix per a dos coses distintes, i cadascuna té els seus passos.

**A. Per a KenLM** (es reentrena):

1. **Preparar el text**: quedar-se només amb el valencià filtrant per GD
   (com el DOGV en `prepara_dogv.py`) i normalitzar-lo amb la mateixa
   funció de sempre (`kenlm.normalitza`; ho fan els dos scripts). Una
   frase per línia.
2. **Ajuntar els texts**: el text actual, `valencia_net_dogv.txt`, més el
   nou, en un fitxer nou.
3. **Entrenar** en Abaco amb `entrena_kenlm.sh`: genera el `.binary` (ordre
   5, poda de singletons) i la seua taula de freqüències (`<nom>_freq.json`).
4. **Comparar** amb el model actual en el comparador: donar-li una clau en
   `FITXERS_KENLM` i en `MODELS` de `compara_models.py` i llançar-lo en
   homògrafs i manual. Les dos claus sense `_c1` es comparen sense
   classificador: és la comparació dels dos KenLM.
5. **Si millora, passar-lo al sistema**. El paquet busca sempre
   `valencia_net_dogv_o5.binary` i `valencia_net_dogv_freq.json`
   (`NOM_MODEL` en `kenlm.py`): o es renomenen els fitxers nous amb eixos
   noms (guardant els vells), o es canvia `NOM_MODEL`. Després, als tres
   llocs, i l'avaluació completa (`avalua_sistema.sh` amb tots els
   benchmarks). El classificador no depén de KenLM: no cal reentrenar-lo.

```bash
# 1. Preparar el text (Abaco o PC), segons el format del corpus:
#    - documents com el DOGV (mateix format que dogv_documents.tsv): documents de GD >= 0,8
python pipeline/08_traduccio_corpus/dogv_apunt/prepara_dogv.py --entrada <corpus.tsv> --eixida dades/macocu/kenlm/<nou>.txt --min-gd-doc 0.8
#    - frases en JSONL (camp text; gd i occ si es filtra, com valencia.jsonl)
python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py --jsonl <corpus.jsonl> --min-gd 0.5 --eixida dades/macocu/kenlm/<nou>.txt

# 2. Ajuntar
cat dades/macocu/kenlm/valencia_net_dogv.txt dades/macocu/kenlm/<nou>.txt > dades/macocu/kenlm/<nom>.txt

# 3. Entrenar (Abaco, des de pipeline/08_traduccio_corpus/macocu/kenlm; TEXT relatiu a l'arrel del repo)
TEXT=dades/macocu/kenlm/<nom>.txt NOM=<nom> sbatch entrena_kenlm.sh
#    -> dades/macocu/kenlm/<nom>_o5.binary i <nom>_freq.json

# 4. Comparar (Abaco, des de pipeline/03_seleccio_de_model/model_llengua), després d'afegir
#    "kenlm_<nom>": "<nom>" a FITXERS_KENLM i "kenlm_<nom>" a MODELS:
MODELS="kenlm_val_net_dogv kenlm_<nom>" EXTRA="--benchmarks homografs homografs_v2 manual --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --detall" sbatch compara_models.sh

# 5. Passar-lo al sistema (Abaco), guardant els vells
cd dades/macocu/kenlm
mv valencia_net_dogv_o5.binary valencia_net_dogv_o5_$(date +%Y%m%d).binary
mv valencia_net_dogv_freq.json valencia_net_dogv_freq_$(date +%Y%m%d).json
cp <nom>_o5.binary valencia_net_dogv_o5.binary
cp <nom>_freq.json valencia_net_dogv_freq.json
#    i al PC (docker/kenlm/ i AVLIZADOR_KENLM_DIR) amb scp, com en 3b.
```

Altres ordres del KenLM: `ORDRE=<n>` en `entrena_kenlm.sh` (amb
`SENSE_FREQ=1` si el text és el mateix i ja té taula) i
`pipeline/03_seleccio_de_model/model_llengua/prova_ordres.sh` (ordre 5
enfront de 6, 7 i 8; 16/11/2026: donen les mateixes decisions, es queda el
5). Compte: `kenlm` es compila per defecte amb ordre màxim 6; per a més cal
recompilar les eines (`cmake -DKENLM_MAX_ORDER=10 ..`) i el mòdul de Python
(`MAX_ORDER=10 pip install --no-cache-dir --force-reinstall
https://github.com/kpu/kenlm/archive/master.zip`).

**B. Per al classificador**:

1. Les fonts de frases són en
   `pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py`: `FONTS`
   (`net` = `dades/macocu/valencia/valencia.jsonl`, `dogv` =
   `dades/dogv_apunt/dogv_net.txt`, `avl`) i `frases_font`. Afegir un
   corpus és afegir una font més (un nom en `FONTS`, la seua ruta i la
   seua branca en `frases_font`; un text normalitzat, una frase per línia,
   com `dogv_net.txt`). És un canvi de codi xicotet. Compte: el
   classificador va amb el paquet, així que la font s'ha de poder
   redistribuir (per això l'AVL és fora des del 12/11).
2. Reentrenar amb eixa font. Si s'ha d'usar sempre, afegir-la també a
   `FONTS_PER_DEFECTE`.

```bash
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py recompte --fonts net dogv <nova>
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py entrena --fonts net dogv <nova>
```

### 3. Com s'actualitza el classificador

- **Es reentrena sencer**, no per parts. `recompte` diu quantes frases té
  cada sentit de cada paraula; `entrena` escriu
  `dades/macocu/kenlm/sentit/sentit.json` (el classificador) i
  `sentit_entrenament.json` (l'informe). Necessita
  `dades/macocu/valencia/valencia.jsonl` i `dades/dogv_apunt/dogv_net.txt`
  (són en el PC i en Abaco).
- **Les paraules entren i ixen soles**: cada paraula que arriba al 0,7
  d'encert equilibrat en les frases apartades entra en `grups`; les que no
  hi arriben van a `descartats` i les que no tenen dades (menys de 20
  frases d'un sentit), a `sense_dades`. El sistema les tracta com sempre:
  amb dubte, la catalana. No cal tocar res a mà.
- **El sistema agafa el fitxer nou tot sol**: carrega `sentit.json` si
  existix i, si no, l'antic de «cop» (`nb.json`).
- **Protecció si canvia el lèxic**: si el lèxic canvia les candidates
  d'una paraula, el seu classificador antic deixa d'usar-se (`sentit.py`,
  `ClassificadorSentit.candidat`) fins que es reentrene.
- **Compte**: reentrenar no arregla les paraules a què els falten dades.
  Per a això cal més corpus o etiquetar els sentits amb el castellà
  (corpus paral·lel català–castellà i l'`espanol` del lèxic; proposta del
  16/11, sense fer).

```bash
# Entrenar (PC o Abaco)
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py recompte
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py entrena
#    Opcions: --min-dev 0.7 (llindar), --minim 20 (frases mínimes per sentit), --fonts

# Quines paraules han entrat (i amb quin encert)
python -c "import json; d = json.load(open('dades/macocu/kenlm/sentit/sentit_entrenament.json', encoding='utf-8')); [print(s, list(x['punts']), x['frases'], x.get('balancejat')) for s in ('grups', 'descartats', 'sense_dades') for x in d[s].values()]"

# Als tres llocs (des del PC)
cp dades/macocu/kenlm/sentit/sentit.json docker/kenlm/
scp dades/macocu/kenlm/sentit/sentit.json nmartin@abaco:~/scrapeo/AVLizador/dades/macocu/kenlm/sentit.json
#    + la carpeta d'AVLIZADOR_KENLM_DIR, si s'usa; i docker compose up --build
```

El que ve a continuació és sobretot la història de FLOR (23/10-12/11/2026).
Les capes d'spaCy i la tria per tipus de punt són les mateixes per als dos
models.

## Què resol

Els punts ixen del lèxic (`traductor_cat_val/data/lexic_general.json`), sense cap
paraula escrita al codi:

| tipus | d'on ix | exemple | què fa hui el motor |
|---|---|---|---|
| `colisio` | `problema: "colision_homonima"` | cop → colp / vegada; cops → colps / vegades | no tradueix (dos candidats, cap canònic) |
| `irresoluble` | `homonimia_lexica`, lectures de la mateixa categoria | calces → bragues / calces; gandula → hamaca / gandula | tradueix sempre |
| `resoluble` | `homonimia_lexica` que spaCy separa | nou → anou / nou; manca → carència / manca | decidix spaCy |

**Sistema final (decisió de l'usuari, 23/10/2026)**: `colisio` ("cop",
"cops") → model de llengua; `irresoluble` ("calces", "gandula/es") → (1)
spaCy, si dona una categoria que només té l'altra lectura dels `lemas`
("molt gandula": ADJ → no es tradueix), i (2) si no, el model, que només
canvia el motor si guanya per més de 5 (des del 05/11/2026, marge 2 amb la catalana per defecte); `resoluble` → spaCy dins del motor.
El model es va descartar primer als irresolubles, però la causa era un
error de dades (E0592 "hamaces"; el plural és "hamaques", corregit amb
permís de l'usuari). Criteri per defecte: FLOR-760M, PMI 0,5, suma, marge
2 amb la paraula catalana per defecte (`per_defecte="catala"`, des del
05/11/2026: només es tradueix si FLOR veu la traducció més probable per
més de 2 punts; si no, es queda la paraula catalana; abans, marge 5 a
favor del motor; vore la secció "Margen 2 con la catalana por defecto" del
README.es.md), concordança `variants`. Mesurat el 06/11/2026 frente al
marge 5: 151 + homògrafs 233 → 218/253, homògrafs v2 124 → 95/160 (les
frases que deixen la catalana, 42 → 57/59; les que demanen la
valenciana, 82 → 38/101), manual 228/458 sense canvis. Resultats: benchmark combinat motor 190/253 →
sistema 227/253 (151 sense cap canvi, colisio 0 → 31/33, irresoluble 12 →
18/24; "calces" no la separa); BOE ampli 1.206/2.000. La
funció és `translate_cat_val_ml(text)`; `evalua_models.py --model
traductor_ml --direccio cat-val` l'avalua sobre
`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json` (el de
151 + els homògrafs, `construeix_benchmark_sistema_final.py`).

## Com funciona

1. El motor tradueix la frase.
2. Per a cada punt es construïxen les frases valencianes **completes**, una
   per candidat, sobre una "base neutra" (la frase del motor amb la paraula
   ambigua sense tocar) i amb el determinant concordat:
   "**Una vegada** acabada la reunió…" / "**Un colp** acabada la reunió…".
3. El model de llengua puntua cada frase (log-probabilitat) i guanya la
   més probable. El model no genera text ni respon preguntes.

Opcions del criteri (`Criteri`), per a provar amb `avalua.py`: `lam` (PMI,
es resta `lam` × log P(candidat sol)), `norma` (`suma` / `mitjana` per
token), `marge` i `per_defecte` (als homògrafs la forma per defecte,
`catala` o `motor`, només canvia si l'altra guanya per més de `marge`
punts) i `concordanca` (`motor` o `variants`,
experimental: formes de l'altre gènere de les dos paraules d'abans, i el
model tria).

**Des del 29/10/2026 `avlizador.translate_cat_val` és sempre este sistema**
(motor + FLOR-760M); el motor sol és `translate_cat_val_motor`. Eixe
mateix dia els resolubles també passen pel model i "nou", "manca",
"recuita"… són irresolubles (els `lemas` diuen que l'adjectiu també fa de
nom).

**Paràgraf valencià davant (03/11/2026)**: FLOR preferix la forma que ha
vist més vegades, quasi sempre la catalana ("vegada" davant de "colp",
"rentadora" davant de "llavadora"). Des del 03/11 cada frase es puntua
com a continuació d'un paràgraf curt en valencià
(`puntuador.CONTEXT_PER_DEFECTE`; `ModelLlengua(context=None)` el lleva).
El paràgraf passa pel model una sola vegada (`past_key_values`): no costa
temps. 151 + homògrafs 226 → **233/253**, homògrafs v2 111 → **122/160**,
gplsi 1.544 → 1.547; manual, 151 i BOE sense canvis. Perd "manca" verb
(→ "carència") en 2 frases més. Proves (paràgrafs, freqüències, LoRA) en
`pipeline/03_seleccio_de_model/model_llengua/sesgo/README.md`.

**Concordança amb el determinant (03/11/2026)**: si spaCy dona ADJ a la
paraula ambigua i el seu gènere no és el del determinant d'abans ("una
nou", "les nous"), la capa d'spaCy no decidix i passa al model
(`punts.decisio_spacy`). Amb NUM no (un numeral fa de nom amb qualsevol
article: "la nou" = la jugadora del dorsal nou). Homògrafs v2 122 → 124,
manual 227 → 228, homògrafs 233 igual. Detall en
`pipeline/03_seleccio_de_model/traces/README.md`.

Models: `projecte-aina/FLOR-760M` per defecte (1,5 GB, CPU) i
`BSC-LT/salamandra-2b` (4,5 GB).

Baseline del 29/10/2026 amb 9 models xicotets (FLOR, salamandra, EuroLLM,
bloom, Qwen2.5 i Qwen3): **FLOR-760M continua sent el millor** (227/253 al
combinat; el següent, salamandra-2b, 222) i el més ràpid. Els models que
no coneixen el valencià trien "vegada" quasi sempre. Detall a
`documentacio/resultats_baseline_models_llengua.md`; pendent FLOR-1.3B.

## Fitxers

`punts.py` (punts i candidats, sense model), `puntuador.py`
(`ModelLlengua`, FLOR), `kenlm.py` (`ModelKenLM`, `normalitza`), `sentit.py`
(`ClassificadorSentit`, `ClassificadorCop`), `__init__.py` (`tradueix_cat_val_ml`,
`translate_cat_val_ml`, `translate_cat_val_kenlm`); fora del paquet, en
`pipeline/03_seleccio_de_model/model_llengua/`: `frases_homografs.json` (frases catalanes amb el sentit esperat),
`genera_benchmark.py` (crea `benchmark_homografs_cat_val.json` amb el
motor; **les referències s'han de revisar a mà**) i `avalua.py` (prova
tots els criteris amb cada model).

## Executar (des de l'arrel del repo)

```bash
python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py        # no sobreescriu sense --sobreescriu
python pipeline/03_seleccio_de_model/model_llengua/avalua.py
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b
```

Resultats a `pipeline/03_seleccio_de_model/resultats/benchmark_homografs_ml_<model>_<data>.json`.
