*[Léelo en castellano](README.es.md)*

# AVLizador: traductor dialectal català → valencià i Grau Dialectal

AVLizador convertix text en **català oriental** (norma de l'IEC) a
**valencià occidental** (norma de l'AVL) i mesura quant de valencià o de
català té un text. No tradueix entre llengües: canvia només el que és
dialectal (lèxic, conjugacions, demostratius, possessius, numerals...).

S'instal·la com un paquet de Python, `avlizador`, amb dues eines:

| Eina | Què fa | Importació |
|---|---|---|
| **Traductor català → valencià** | Motor de regles amb els diccionaris del projecte i spaCy, més un model de llengua de n-grames (KenLM) i un classificador de sentit que resolen les paraules ambigües ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*). Quan un nom canvia de gènere ("el préssec" → "la bresquilla"), fa concordar el determinant, els adjectius i l'atribut | `avlizador.traductor_cat_val` |
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

- `[kenlm]` instal·la la biblioteca KenLM, el model de llengua de les
  paraules ambigües. Es compila en instal·lar-la: cal un compilador de C++.
  En Linux i macOS funciona; en Windows normalment no s'instal·la: useu
  Docker (baix) o el motor sol.
- Els fitxers del model KenLM no són en git ni en el paquet: es baixen de
  Hugging Face la primera vegada que s'usen (vegeu
  [Model de llengua](#model-de-llengua)).
- Sense KenLM o sense els seus fitxers funciona només el motor de regles:
  el traductor l'usa i avisa una vegada que falta el model
  (`AvisSenseModelLlengua`).
- El model català de spaCy (`ca_core_news_md`) s'instal·la sol.
- `[avaluacio]` afig `sacrebleu` per a avaluar amb els benchmarks; `[dev]`,
  `pytest`.

### Model de llengua

Les paraules ambigües del lèxic ("cop", "nou", "manca"...) les decidix un
model KenLM d'ordre 5 entrenat amb frases valencianes de MaCoCu-ca i del
DOGV (2025-2026), més un classificador de sentit (Naive Bayes; hui per a
"cop", "cops" i "deu") entrenat amb el mateix text i textos de l'AVL. Són
tres fitxers, publicats en Hugging Face:
[`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va)
(CC BY 4.0).

| Fitxer | Què és |
|---|---|
| `valencia_net_dogv_o5.binary` | el model KenLM (82 MB) |
| `valencia_net_dogv_freq.json` | freqüències de les paraules (per al prior) |
| `sentit.json` (o l'antic `nb.json`) | el classificador de sentit de les paraules ambigües (~730 KB) |

El paquet els baixa sol la primera vegada que s'usen (cal `huggingface_hub`,
que ve amb `[kenlm]`, i internet eixa vegada) i els guarda en la memòria cau
de Hugging Face (`HF_HOME`); després funciona sense internet.

#### Quina versió del model baixa cada versió del paquet

Cada versió del paquet baixa sempre **el mateix commit** del repositori
del model en Hugging Face, fixat en `REVISIO_HF`
([`src/avlizador/traductor_cat_val/model_llengua/kenlm.py`](src/avlizador/traductor_cat_val/model_llengua/kenlm.py)).
Així, si més avant es puja un model nou, les instal·lacions d'una versió
anterior continuen baixant el seu i traduïxen igual. Es fixa per commit, i
no per etiqueta, perquè la web de Hugging Face no permet crear etiquetes.

| Versió del paquet | Commit del model en Hugging Face | Model |
|---|---|---|
| 2.0.0 | [`db4a1f1`](https://huggingface.co/transducens/avlizador-kenlm-va/tree/db4a1f10d55bbc30ad54728e1639d17d32526ef7) (`db4a1f10d55bbc30ad54728e1639d17d32526ef7`, 17/11/2026) | KenLM `valencia_net_dogv2` (MaCoCu + DOGV 2025-2026) + classificador `sentit_dogv2_avl` (+ AVL) |
| 2.0.1 | [`ea87f3f`](https://huggingface.co/transducens/avlizador-kenlm-va/tree/ea87f3f330de365b2fc04f86271f86e692781bb5) (`ea87f3f330de365b2fc04f86271f86e692781bb5`, 23/11/2026) | El mateix KenLM i classificador; la taula de freqüències nova (amb «brolladors», que hi faltava des del lèxic del 18/11) |

Pujar a Hugging Face un altre fitxer (per exemple, la fitxa `README.md`)
crea un commit nou, però no canvia res per a les versions ja publicades.

**Publicar un model nou** (per a una versió nova del paquet):

1. Generar la carpeta: `python scripts/hf_model/kenlm.py --dir ... --nom ...
   --fonts ...` (vore el seu docstring) → `dades/hf_model/kenlm/`.
2. Pujar-la a Hugging Face (*Files and versions* → *Add file* → *Upload
   files*, o `hf upload transducens/avlizador-kenlm-va dades/hf_model/kenlm . --repo-type model`).
3. Copiar l'identificador complet del commit nou: *Files and versions* →
   *History*, o `python -c "from huggingface_hub import HfApi;
   print(HfApi().model_info('transducens/avlizador-kenlm-va').sha)"`.
4. Posar-lo en `REVISIO_HF`, afegir-ne una fila a la taula de dalt (i en
   [`README.es.md`](README.es.md)), passar els tests i traure la versió
   nova del paquet.

| Variable d'entorn | Què fa |
|---|---|
| `AVLIZADOR_KENLM_DIR` | usar una carpeta local amb els tres fitxers en lloc de Hugging Face |
| `AVLIZADOR_KENLM_DESCARREGA=0` o `HF_HUB_OFFLINE=1` | no baixar res (només la memòria cau o la carpeta local) |
| `AVLIZADOR_KENLM_REVISIO` | una altra revisió del model en Hugging Face (commit, branca o etiqueta) en lloc de la de `REVISIO_HF` |

Cost: ~0,1 ms per frase candidata i ~80 MB de memòria, sense GPU ni
PyTorch. Fins al 12/11/2026 el model era FLOR-760M (833 ms i ~1,5 GB); des
de la versió 2.0.0 ja no és en el paquet.

**Opció amb lemes** (des de la 2.0.1, no per defecte): `--model kenlm-lemes`
usa un KenLM de lemes parcials en lloc del de formes (198 encerts i 1 error
greu en les 237 decisions dels homògrafs, davant de 196 i 0; en les frases
amb paraula ambigua, la traducció tarda unes 2 vegades més: spaCy
lematitza el context). Els seus dos fitxers són en el mateix repositori
de Hugging Face i es baixen, com els altres, la primera vegada que s'usa
l'opció (qui no l'usa no els baixa); també es poden posar en la carpeta
d'`AVLIZADOR_KENLM_DIR`. Detall en
[`model_llengua/README.md`](src/avlizador/traductor_cat_val/model_llengua/README.md).

Per què KenLM i totes les xifres:
[`documentacio/resultats_model_llengua_kenlm.md`](documentacio/resultats_model_llengua_kenlm.md).

## Ús

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'
translate_cat_val("El préssec és molt bo. Les despeses previstes són altes.")
# 'La bresquilla és molt bona. Els gastos previstos són alts.'  (canvi de gènere)
# model="kenlm": error (FaltaKenLM) si falta KenLM, en lloc del motor sol amb avís

calcula_gd("Este xiquet vol vindre hui.")["gd"]     # 1.0: valencià
calcula_gdv("Este xiquet vol vindre hui.")["gdv"]   # 1.0: valencià pur
calcula_gdc("Aquest nen vol venir avui.")["gdc"]    # 1.0: català pur
```

Des de la línia d'ordres:

```bash
avlizador tradueix "Aquest noi necessita ajuda."
avlizador tradueix --fitxer entrada.txt > eixida.txt   # una frase o paràgraf per línia
avlizador tradueix --motor "..."                       # només el motor, sense el model
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

Amb Docker (la imatge porta spaCy i KenLM dins, sense torch, i
funciona **sense internet**). En construir-la es baixa de Hugging Face el
[model de llengua](#model-de-llengua) (cal internet només en eixe moment)
i es guarda en `/opt/kenlm`; si els tres fitxers ja són en `docker/kenlm/`
(carpeta ignorada per git), es copien d'allí sense baixar res. Una altra
revisió del model: `docker compose build --build-arg KENLM_REVISIO=...`.
Per a portar també l'opció amb lemes (~80 MB més): `KENLM_LEMES: "1"` en
`docker-compose.yml` o `--build-arg KENLM_LEMES=1`.
Detall: [`docker/LLEGIM.md`](docker/LLEGIM.md).

```bash
docker compose up --build     # http://localhost:8000
```

La imatge necessita ~1 GB de RAM (`mem_limit: 2g` en
`docker-compose.yml`).

Per a un equip sense internet, la imatge es copia com un fitxer:

```bash
docker save avlizador:2.0.1 > avlizador.tar   # en l'equip on s'ha construït
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
| `AVLIZADOR_KENLM_DIR` | `/opt/kenlm` (en la imatge) | carpeta amb els tres fitxers del [model de llengua](#model-de-llengua) | fora de Docker no cal: sense la variable, el model es baixa de Hugging Face |
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
arribar a la referència (com més baixos, millor). Versió 2.0.1, mesura
del 23/11/2026 (`avlizador avalua`; el manual dona el mateix que la 2.0.0); FLOR-760M (el model d'abans, ja no
inclòs) i el motor sol, del 13/11/2026:

| Sistema | Exactes | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + KenLM + classificador (per defecte) | **232/458 (50,7 %)** | **91,00** | **96,34** | **5,58** | **5,96** |
| Motor + FLOR-760M (fins a la 1.2.0) | 231/458 (50,4 %) | 90,98 | 96,33 | 5,59 | 5,97 |
| Motor sol | 218/458 (47,6 %) | 90,49 | 96,08 | 5,90 | 6,27 |

Per parts (2.0.1): BOE 35/246 (BLEU 84,01, TER 9,21) i AVL 197/212 (BLEU
99,10, TER 0,41). La versió 1.2.0 (FLOR) en traia 33 i 195 (228/458).

Frases exactes en la resta de benchmarks (homògrafs, 23/11/2026, versió
2.0.1, amb els homògrafs corregits el mateix dia: sense «recuita», v1 249 i
v2 144 frases, FLOR no s'hi ha mesurat; 151, 16-17/11/2026; BOE i gplsi,
13/11/2026 amb el model KenLM anterior):

| Benchmark | KenLM + classificador | FLOR-760M (d'abans) | Motor sol |
|---|---|---|---|
| homògrafs v1 (151 + homògrafs, 249) | **228** | — | 179 |
| homògrafs v2 (144) | **113** | — | 75 |
| 151 (154) | 144 | **145** | 142 |
| BOE estricte, mostra (2.000) | **1.894** | **1.894** | 1.800 |
| gplsi (1.958) | 1.550 | **1.551** | 1.533 |

En les 237 decisions dels homògrafs, KenLM + classificador encerta 196 i
no comet cap error greu (que canvie el sentit; la 2.0.0, 186 i 0). Detall:
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
avlizador avalua --motor               # també el motor sol, per a comparar
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

FLOR-760M (el model fins a la 1.2.0) ja no és en el paquet; per a repetir
els experiments que el comparen amb KenLM, el seu puntuador és en
`pipeline/03_seleccio_de_model/model_llengua/flor.py` (cal `torch` i
`transformers` a banda).

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
  el model KenLM l'ha entrenat el projecte amb MaCoCu-ca 1.0 (CC0 1.0),
  textos del DOGV i, el classificador, textos de l'AVL, i està publicat en
  Hugging Face amb llicència **CC BY 4.0**
  ([`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va));
- el dataset gplsi de `dades/benchmarks/gplsi/` és CC BY 4.0 dels seus
  autors;
- els textos del BOE i de l'AVL es reutilitzen citant-ne la font.

**Imatge Docker.** El codi d'AVLizador és Apache 2.0, però la imatge
Docker inclou components de tercers amb altres llicències (vegeu
[`NOTICE`](NOTICE)), entre els quals el model d'spaCy
`ca_core_news_md`, amb llicència GPL-3.0, la biblioteca KenLM (LGPL 2.1)
i el model KenLM del projecte. Qui distribuïsca una imatge amb estos components dins ha de
complir eixes llicències. Per això recomanem construir la imatge en
local (`docker compose build`) en compte de distribuir-la.
