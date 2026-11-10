*[Léelo en castellano](README.es.md)*

# AVLizador: traductor dialectal català → valencià i Grau Dialectal

AVLizador convertix text en **català oriental** (norma de l'IEC) a
**valencià occidental** (norma de l'AVL) i mesura quant de valencià o de
català té un text. No tradueix entre llengües: canvia només el que és
dialectal (lèxic, conjugacions, demostratius, possessius, numerals...).

S'instal·la com un paquet de Python, `avlizador`, amb dues eines:

| Eina | Què fa | Importació |
|---|---|---|
| **Traductor català → valencià** | Motor de regles amb els diccionaris del projecte i spaCy, més un model de llengua menut (FLOR-760M) que resol les paraules ambigües ("cop" → *colp* o *vegada*, "nou" → *nou* o *anou*) | `avlizador.traductor_cat_val` |
| **Grau Dialectal** (GD, GDV, GDC) | Índexs de 0 a 1 que diuen si un text és valencià o català | `avlizador.grau_dialectal` |

Funciona **només amb CPU**, sense GPU ni serveis externs: està pensat per
a equips amb pocs recursos.

## Instal·lació

Guia pas a pas per a Windows, Linux i macOS (entorn virtual, instal·lació,
proves i problemes habituals): [`documentacio/guia_installacio.md`](documentacio/guia_installacio.md).
En resum, cal Python 3.10 o posterior i, des d'una còpia del repositori:

```bash
pip install ".[ml]" --extra-index-url https://download.pytorch.org/whl/cpu
```

- `[ml]` instal·la `torch` (versió CPU) i `transformers` per al model de
  llengua FLOR-760M, que es baixa de Hugging Face la primera vegada que
  s'usa (1,5 GB; es guarda en la carpeta de `HF_HOME`). És la instal·lació
  recomanada.
- Sense `[ml]` (`pip install .`) funciona només el motor de regles: el
  traductor l'usa i avisa una vegada que falta el model
  (`AvisSenseModelLlengua`).
- El model català de spaCy (`ca_core_news_md`) s'instal·la sol.
- `[avaluacio]` afig `sacrebleu` per a avaluar amb els benchmarks; `[dev]`,
  `pytest`.

## Ús

En Python:

```python
from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda. Un cop acabada la reunió, marxem.")
# 'Este xic necessita ajuda. Una vegada acabada la reunió, marxem.'

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
pip install ".[ml,web]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador web          # http://127.0.0.1:8000
```

Amb Docker (la imatge porta spaCy i FLOR-760M dins i funciona **sense
internet**; la primera construcció baixa uns 2 GB):

```bash
docker compose up --build     # http://localhost:8000
```

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
| `AVLIZADOR_MODE` | `complet` | `complet` = motor + FLOR; `motor` = només regles (sense carregar FLOR: ~1,5 GB menys de RAM i arrancada més ràpida) | `motor` en equips amb menys de 4 GB de RAM o si cal rapidesa abans que encertar els homògrafs |
| `MAX_CARACTERS` | 20000 | longitud màxima del text per petició; si es passa, HTTP 413 amb un missatge | pujar-la si es traduïxen documents llargs i l'equip ho aguanta; baixar-la si les peticions tarden massa |
| `MAX_TRADUCCIONS_SIMULTANIES` | 2 | traduccions a la vegada; si ja n'hi ha tantes, HTTP 429 ("El servei està ocupat") | segons els nuclis (regla de baix); 1 en equips de 2 nuclis |
| `OMP_NUM_THREADS` | 2 | fils de càlcul de PyTorch (i d'altres llibreries numèriques) | segons els nuclis (regla de baix) |
| `TORCH_NUM_THREADS` | 2 | fils que usa FLOR: la llig AVLizador (`torch.set_num_threads`); PyTorch no la llig per si sol | igual que `OMP_NUM_THREADS`; normalment el mateix valor |
| `HF_HUB_OFFLINE` | `1` | no intentar connectar amb Hugging Face (els models ja són dins de la imatge) | no cal canviar-la en Docker |
| `UVICORN_LOG_LEVEL` | `warning` | nivell dels missatges del servidor (arrancada, avisos, errors). No torna a activar les línies per petició: no es registren mai (privacitat) | `info` o `debug` només per a investigar un problema d'arrancada |
| `AVLIZADOR_DOCS` | `0` | `1` = documentació interactiva de l'API en `/docs` (carrega JavaScript d'un CDN) | només en desenvolupament, mai en producció |

**Regla dels nuclis**: `MAX_TRADUCCIONS_SIMULTANIES` × `TORCH_NUM_THREADS`
≤ nuclis de l'equip (amb els valors per defecte, 4 nuclis). Si es passa,
les traduccions competixen pels mateixos nuclis i totes van més lentes.

## Resultats

Benchmark d'avaluació: **manual mescla** (458 frases del BOE i de l'AVL,
revisades a mà). TER i WER: percentatge de paraules que cal editar per a
arribar a la referència (com més baixos, millor).

| Sistema | Exactes | BLEU | chrF | TER | WER |
|---|---|---|---|---|---|
| Motor + FLOR-760M (sistema principal) | **227/458 (49,6 %)** | **90,88** | **96,34** | **5,61** | **6,01** |
| Motor sol | 214/458 (46,7 %) | 90,39 | 96,10 | 5,91 | 6,30 |

En les frases de l'AVL encerta exactament el 92 %. En les del BOE les
frases exactes baixen (13 %) perquè la traducció oficial reformula molt
(futur on el català usa present, sinònims no dialectals...), però el TER
es queda en 9: una paraula de cada deu. Tots els benchmarks i mètriques,
en
[`pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`](pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).

## Benchmarks

Tots són en [`dades/benchmarks/`](dades/benchmarks/) (vegeu-ne el README):
el manual (mescla, BOE i AVL), el banc curat de 151 frases, el
d'homògrafs, els del BOE (estricte i ampli, mostres i complets) i el
dataset públic gplsi (CC BY 4.0). Format: llista de
`{"id", "oriental", "occidental"}` (català i valencià).

```bash
pip install ".[ml,avaluacio]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador avalua                      # tots (sense els complets del BOE)
avlizador avalua --benchmarks manual  # només el d'avaluació
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
pip install -e ".[ml,avaluacio,dev]" --extra-index-url https://download.pytorch.org/whl/cpu
pytest                                  # doctests + proves de l'API i les ordres
```

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
- FLOR-760M és Apache 2.0 (adaptació de BLOOM-1.1B);
- el dataset gplsi de `dades/benchmarks/gplsi/` és CC BY 4.0 dels seus
  autors;
- els textos del BOE i de l'AVL es reutilitzen citant-ne la font.

**Imatge Docker.** El codi d'AVLizador és Apache 2.0, però la imatge
Docker inclou components de tercers amb altres llicències (vegeu
[`NOTICE`](NOTICE)), entre els quals el model d'spaCy
`ca_core_news_md`, amb llicència GPL-3.0, i FLOR-760M, amb les
restriccions d'ús de la llicència RAIL de BLOOM. Qui distribuïsca una
imatge amb estos models dins ha de complir eixes llicències. Per això
recomanem construir la imatge en local (`docker compose build`) en
compte de distribuir-la.
