*[Léelo en castellano](README.es.md)*

# AVLizador: traductor dialectal català → valencià i Grau Dialectal

AVLizador convertix text en **català oriental** (norma de l'IEC) a
**valencià occidental** (norma de l'AVL) i mesura quant de valencià o de
català té un text. No tradueix entre llengües: canvia només el que és
dialectal (lèxic, conjugacions, demostratius, possessius, numerals...).

S'instal·la com un paquet de Python, `avlizador`, amb dues eines:

| Eina | Què fa | Importació |
|---|---|---|
| **Traductor català → valencià** | Motor de regles amb els diccionaris del projecte i spaCy, més un model de llengua de n-grames (KenLM) i un classificador de sentit que resolen les paraules ambigües ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*); FLOR-760M, opcional | `avlizador.traductor_cat_val` |
| **Grau Dialectal** (GD, GDV, GDC) | Índexs de 0 a 1 que diuen si un text és valencià o català | `avlizador.grau_dialectal` |

Funciona **només amb CPU**, sense GPU ni serveis externs: està pensat per
a equips amb pocs recursos.

## Instal·lació

Guia pas a pas per a Windows, Linux i macOS (entorn virtual, instal·lació,
proves i problemes habituals): [`documentacio/guia_installacio.md`](documentacio/guia_installacio.md).
En resum, cal Python 3.10 o posterior i, des d'una còpia del repositori:

```bash
pip install ".[kenlm]"
```

- `[kenlm]` instal·la la biblioteca KenLM, el model de llengua per defecte
  de les paraules ambigües (des del 13/11/2026). Es compila en instal·lar-la:
  cal un compilador de C++. En Linux i macOS funciona; en Windows
  normalment no s'instal·la: useu Docker (baix), FLOR o el motor sol.
- Els fitxers del model KenLM no són en git ni en el paquet: vegeu
  [Model de llengua](#model-de-llengua) (`AVLIZADOR_KENLM_DIR`).
- Sense KenLM o sense els seus fitxers funciona només el motor de regles:
  el traductor l'usa i avisa una vegada que falta el model
  (`AvisSenseModelLlengua`).
- `[ml]` (opcional) instal·la `torch` (versió CPU) i `transformers` per a
  FLOR-760M, el model per defecte fins al 12/11/2026:
  `pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu`.
  Es baixa de Hugging Face la primera vegada que s'usa (1,5 GB; es guarda
  en la carpeta de `HF_HOME`).
- El model català de spaCy (`ca_core_news_md`) s'instal·la sol.
- `[avaluacio]` afig `sacrebleu` per a avaluar amb els benchmarks; `[dev]`,
  `pytest`.

### Model de llengua

Les paraules ambigües del lèxic ("cop", "nou", "manca"...) les decidix un
model KenLM d'ordre 5 entrenat amb frases valencianes de MaCoCu-ca i del
DOGV (2025-2026), més un classificador de sentit (Naive Bayes) per a
"cop" (*colp* o *vegada*). Cal una carpeta, indicada amb la variable
d'entorn `AVLIZADOR_KENLM_DIR`, amb tres fitxers:

| Fitxer | Què és |
|---|---|
| `valencia_net_dogv_o5.binary` | el model KenLM (77 MB) |
| `valencia_net_dogv_freq.json` | freqüències de les paraules (per al prior) |
| `sentit.json` (o l'antic `nb.json`) | el classificador de sentit de les paraules ambigües (~730 KB; hui en tenen cop, cops i deu) |

De moment es demanen a l'equip; més avant es publicaran en Hugging Face.
Cost: ~0,1 ms per frase candidata i ~74 MB de memòria (FLOR: 833 ms i
~1,5 GB). Per què KenLM i totes les xifres:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

## Ús

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'
# model="kenlm": error (FaltaKenLM) si falta KenLM; model="flor": FLOR-760M (cal [ml])

calcula_gd("Este xiquet vol vindre hui.")["gd"]     # 1.0: valencià
calcula_gdv("Este xiquet vol vindre hui.")["gdv"]   # 1.0: valencià pur
calcula_gdc("Aquest nen vol venir avui.")["gdc"]    # 1.0: català pur
```

Des de la línia d'ordres:

```bash
avlizador tradueix "Aquest noi necessita ajuda."
avlizador tradueix --fitxer entrada.txt > eixida.txt   # una frase o paràgraf per línia
avlizador tradueix --motor "..."                       # només el motor, sense el model
avlizador tradueix --model flor "..."                  # FLOR-760M en lloc de KenLM (cal [ml])
avlizador gd --text "Este xiquet vol vindre hui."      # també gdv i gdc
avlizador gd --corpus corpus.jsonl --camp text --html informe.html  # informe HTML frase a frase
avlizador avalua --benchmarks manual                   # avaluació (cal [avaluacio])
avlizador --help
```

## Interfície web i Docker

Una interfície web accessible (WCAG 2.2 AA), en valencià i castellà, amb
el títol **Traductor Transducens**: una portada, "Traducció d'idiomes"
(preparada per a altres traductors; encara cap parell), "Adaptador
dialectal" amb l'adaptació del català al valencià (`/dialectes/adaptador`)
i el Grau Dialectal (`/dialectes/gd`), i "Sobre". El català i el valencià
són la mateixa llengua: la interfície ho presenta com una adaptació entre
dialectes, no com una traducció entre idiomes. Els textos no es guarden
ni es registren.

Sense Docker, des d'una còpia del repositori:

```bash
pip install ".[kenlm,web]"
avlizador web          # http://127.0.0.1:8000
```

Amb Docker (la imatge porta spaCy i KenLM dins, sense torch ni FLOR, i
funciona **sense internet**). Abans de construir-la, poseu els tres
fitxers del [model de llengua](#model-de-llengua) en `docker/kenlm/`
(carpeta ignorada per git): la construcció els copia en `/opt/kenlm` i
s'atura amb un missatge clar si en falta algun.

```bash
docker compose up --build     # http://localhost:8000
```

La imatge necessita ~1 GB de RAM (`mem_limit: 2g` en
`docker-compose.yml`).

Per a un equip sense internet, la imatge es copia com un fitxer:

```bash
docker save avlizador:1.2.0 > avlizador.tar   # en l'equip on s'ha construït
docker load < avlizador.tar                   # en l'equip de destí
docker compose up                             # amb docker-compose.yml al costat
```

Per defecte només s'hi pot entrar des del mateix equip
(`127.0.0.1:8000`); per a obrir-la a la xarxa, canvieu el port en
`docker-compose.yml` (i, fora d'una xarxa interna, poseu-hi un proxy
HTTPS davant). La imatge s'executa sense root i amb el sistema de
fitxers de només lectura. Detall del disseny:
[`documentacio/hoja_de_ruta_interfaz_docker.md`](documentacio/hoja_de_ruta_interfaz_docker.md).

### Variables d'entorn

Es canvien en `docker-compose.yml` (`environment:`) sense reconstruir la
imatge; fora de Docker, com a variables d'entorn abans de `avlizador web`.

| Variable | Per defecte | Què fa | Quan canviar-la |
|---|---|---|---|
| `AVLIZADOR_MODE` | `complet` | `complet` = motor + KenLM; `motor` = només regles. Si en mode `complet` falten els fitxers de KenLM, el servidor ho avisa en el registre i usa `motor` | `motor` si no es tenen els fitxers del model o si cal rapidesa abans que encertar els homògrafs |
| `AVLIZADOR_KENLM_DIR` | `/opt/kenlm` (en la imatge) | carpeta amb els tres fitxers del [model de llengua](#model-de-llengua) | fora de Docker, on hàgeu posat els fitxers |
| `MAX_CARACTERS` | 20000 | longitud màxima del text per petició; si es passa, HTTP 413 amb un missatge | pujar-la si es traduïxen documents llargs i l'equip ho aguanta; baixar-la si les peticions tarden massa |
| `MAX_TRADUCCIONS_SIMULTANIES` | 2 | traduccions a la vegada; si ja n'hi ha tantes, HTTP 429 ("El servei està ocupat") | segons els nuclis (regla de baix); 1 en equips d'1 nucli |
| `UVICORN_LOG_LEVEL` | `warning` | nivell dels missatges del servidor (arrancada, avisos, errors). No torna a activar les línies per petició: no es registren mai (privacitat) | `info` o `debug` només per a investigar un problema d'arrancada |
| `AVLIZADOR_DOCS` | `0` | `1` = documentació interactiva de l'API en `/docs` (carrega JavaScript d'un CDN) | només en desenvolupament, mai en producció |

**Regla dels nuclis**: KenLM usa un nucli per traducció, així que
`MAX_TRADUCCIONS_SIMULTANIES` ≤ nuclis de l'equip. Si es passa, les
traduccions competixen pels mateixos nuclis i totes van més lentes.

## Resultats

Benchmark d'avaluació: **manual mescla** (458 frases del BOE i de l'AVL,
revisades a mà). TER i WER: percentatge de paraules que cal editar per a
arribar a la referència (com més baixos, millor). Mesura del 13/11/2026
(`avlizador avalua`):

| Sistema | Exactes | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + KenLM + classificador (per defecte) | **232/458 (50,7 %)** | **91,00** | **96,34** | **5,58** | **5,96** |
| Motor + FLOR-760M (opcional) | 231/458 (50,4 %) | 90,98 | 96,33 | 5,59 | 5,97 |
| Motor sol | 218/458 (47,6 %) | 90,49 | 96,08 | 5,90 | 6,27 |

Frases exactes en la resta de benchmarks (13/11/2026):

| Benchmark | KenLM + classificador | FLOR-760M | Motor sol |
|---|---|---|---|
| homògrafs v1 (151 + homògrafs, 253) | **227** | 217 | 181 |
| homògrafs v2 (160) | **111** | 96 | 82 |
| 151 (154) | 144 | **145** | 142 |
| BOE estricte, mostra (2.000) | **1.894** | **1.894** | 1.800 |
| gplsi (1.958) | 1.550 | **1.551** | 1.533 |

En les 257 decisions dels homògrafs, KenLM + classificador encerta 193 i
comet 2 errors greus (canvia el sentit). Detall:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

Històric, mesura del 30/10/2026 (versió 1.0.1, amb FLOR-760M com a model
per defecte; el lèxic ha canviat des d'aleshores):

| Sistema | Exactes | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + FLOR-760M (sistema principal aleshores) | 227/458 (49,6 %) | 90,88 | 96,34 | 5,61 | 6,01 |
| Motor sol | 214/458 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |

En eixa mesura, en les frases de l'AVL encertava exactament el 92 %. En
les del BOE les frases exactes baixen (13 %) perquè la traducció oficial
reformula molt (futur on el català usa present, sinònims no
dialectals...), però el TER es queda en 9: una paraula de cada deu. Tots
els benchmarks i mètriques, en
[`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`](pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).

## Benchmarks

Tots són en [`dades/benchmarks/`](dades/benchmarks/) (vegeu-ne el README):
el manual (mescla, BOE i AVL), el banc curat de 151 frases, el
d'homògrafs, els del BOE (estricte i ampli, mostres i complets) i el
dataset públic gplsi (CC BY 4.0). Format: llista de
`{"id", "oriental", "occidental"}` (català i valencià).

```bash
pip install ".[kenlm,avaluacio]"
avlizador avalua                      # tots (sense els complets del BOE), amb KenLM
avlizador avalua --benchmarks manual  # només el d'avaluació
avlizador avalua --model kenlm flor --motor  # KenLM, FLOR (cal [ml]) i el motor sol
avlizador avalua --llista             # els disponibles
```

## Estructura del repositori

```
src/avlizador/            el paquet que s'instal·la
  traductor_cat_val/        traductor: regles (rules/), model de llengua (model_llengua/), data/
  grau_dialectal/           GD, GDV i GDC
  avaluacio/                mètriques i avaluació amb els benchmarks
  cli.py                    ordre `avlizador`
dades/
  lexic/                    diccionaris del projecte (font única)
  benchmarks/               benchmarks d'avaluació
scripts/sync_data.py      copia dades/lexic/ a src/avlizador/traductor_cat_val/data/
tests/                    pytest: doctests, API i ordres
documentacio/             metodologia, resultats i fulls de ruta
pipeline/                 registre del treball que va construir i validar les eines (etapes 01-09)
```

`pipeline/` no s'instal·la: és la infraestructura del projecte (scraping
de l'AVL, regles, corpus del BOE, selecció de models, capes de LLM
descartades...). La història completa, amb les decisions i el que es va
descartar, és en
[`documentacio/metodologia_i_resultats.md`](documentacio/metodologia_i_resultats.md).

## Desenvolupament

```bash
pip install -e ".[kenlm,avaluacio,dev]"
pytest                                  # doctests + proves de l'API i les ordres
```

Per a provar també FLOR, afegiu-hi `ml` i
`--extra-index-url https://download.pytorch.org/whl/cpu`.

Per a canviar el lèxic, s'editen **només** els fitxers de `dades/lexic/`
i després:

```bash
python scripts/sync_data.py            # regenera src/avlizador/traductor_cat_val/data/
python scripts/sync_data.py --check    # ha de dir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar amb la taula de resultats
```

La direcció valencià → català és en el codi
(`traductor_cat_val/rules/val_cat/`, l'usa el GD) però no forma part de
l'API pública.

## Llicència

[Apache 2.0](LICENSE): el codi i les dades pròpies del projecte (el lèxic
de `dades/lexic/`, recopilat a mà per l'equip, i els benchmarks). Les
peces de tercers mantenen la seua llicència i es detallen en
[`NOTICE`](NOTICE):

- el model català d'spaCy (`ca_core_news_md`) és **GPL 3.0**: no s'inclou,
  pip l'instal·la com a dependència, i qui el redistribuïsca ha de
  complir eixa llicència;
- la biblioteca KenLM és **GNU LGPL 2.1** (https://github.com/kpu/kenlm);
  el model KenLM l'ha entrenat el projecte amb MaCoCu-ca 1.0 (CC0 1.0) i
  textos del DOGV, i les condicions de reutilització del DOGV s'han de
  revisar abans de publicar-lo;
- FLOR-760M (opcional, no s'inclou) és Apache 2.0 (adaptació de
  BLOOM-1.1B);
- el dataset gplsi de `dades/benchmarks/gplsi/` és CC BY 4.0 dels seus
  autors;
- els textos del BOE i de l'AVL es reutilitzen citant-ne la font.

**Imatge Docker.** El codi d'AVLizador és Apache 2.0, però la imatge
Docker inclou components de tercers amb altres llicències (vegeu
[`NOTICE`](NOTICE)), entre els quals el model d'spaCy
`ca_core_news_md`, amb llicència GPL-3.0, la biblioteca KenLM (LGPL 2.1)
i el model KenLM del projecte. Des del 13/11/2026 la imatge ja no porta
FLOR-760M. Qui distribuïsca una imatge amb estos components dins ha de
complir eixes llicències. Per això recomanem construir la imatge en
local (`docker compose build`) en compte de distribuir-la.
