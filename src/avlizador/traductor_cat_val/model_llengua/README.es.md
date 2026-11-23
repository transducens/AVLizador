# `avlizador.traductor_cat_val.model_llengua` — homógrafos cat→val con un modelo de lenguaje

Postprocesado (23/10/2026) para las palabras catalanas ambiguas que el
motor de reglas no puede resolver solo. Desde el 29/10/2026 forma parte
del **sistema principal** (`translate_cat_val`).

## Modelo por defecto: KenLM + clasificador de sentido (desde el 13/11/2026)

**Decisión del usuario (13/11/2026)**: KenLM + el clasificador de sentido
sustituye a FLOR-760M como modelo por defecto. Desde la versión 2.0.0
(17/11/2026, decisión del usuario) FLOR ya no está en el paquete, ni como
opción; su puntuador está en `pipeline/03_seleccio_de_model/model_llengua/flor.py`
para repetir los experimentos.

| | KenLM + clasificador | FLOR-760M |
|---|---|---|
| Homógrafos v1 (253) | **227** | 217 |
| Homógrafos v2 (160) | **111** | 96 |
| Manual mezcla BOE + AVL (458) | **232** | 231 |
| 151 (154) | 144 | **145** |
| BOE estricto (2.000) | 1.894 | 1.894 |
| gplsi (1.958) | 1.550 | **1.551** |
| Tiempo por frase candidata | **0,1 ms** | 833 ms |
| Memoria | **~74 MB** | ~1,5 GB |
| Dependencias | `kenlm` | `torch` + `transformers` |

Exactas, `avalua_sistema_20261113_1308` (KenLM) y `_1016` (FLOR). En las 257 decisiones de los
homógrafos, KenLM + clasificador da 193 aciertos y 1 error grave (que
cambian el sentido). Por qué, cómo se llegó y qué se descartó (KenLM
catalán, fastText, KenLM sin poda, en dos sentidos, de lemas, híbrido con
FLOR): `documentacio/resultats_model_llengua_kenlm.md`.

Uso:

- `translate_cat_val(text)`: KenLM si está el paquete `kenlm` y los
  ficheros; si falta algo, el motor solo y un aviso
  (`AvisSenseModelLlengua`).
- `translate_cat_val(text, model="kenlm")`: igual, pero si falta algo,
  `FaltaKenLM` (se ha pedido expresamente).
- Órdenes: `avlizador tradueix [--motor]`, `avlizador avalua [--motor]`.

Piezas:

- `kenlm.py`: `normalitza` (la misma del entrenamiento; la importa
  `pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py`) y
  `ModelKenLM`: log P natural de la frase con `<s>` y `</s>`; prior =
  ln((n + 1) / tokens) con las frecuencias del texto de entrenamiento
  (`<modelo>_freq.json`).
- `sentit.py`: clasificadores de sentido con una interfaz fija,
  `candidat(punt) -> str | None` (frase con hueco → candidato). Desde el
  13/11/2026, `ClassificadorSentit` (`sentit.json`): el clasificador
  GENERAL, parte del sistema, sin ningún caso a mano. Un Naive Bayes (lemas
  de spaCy alrededor) por cada grupo de palabras ambiguas del léxico
  (singular y plural juntos si tienen los mismos `lemas`), entrenado con
  frases valencianas de MaCoCu + DOGV, sin la AVL
  (`pipeline/03_seleccio_de_model/model_llengua/sentit_general.py`). Un
  grupo solo entra si acierta al menos un 0,7 (equilibrado) con frases
  reales apartadas; hoy cop (0,89), deu (0,81) y cops (0,75). El resto (nou,
  manca, calces, gandula, rentadora, reeixida: no llegan; fartanera,
  panotxa, recuita: sin datos) no tienen y hacen lo de siempre. Cuando haya
  más datos, una palabra que pase el umbral entra sola. El antiguo de "cop"
  (`ClassificadorCop`, `nb.json`) se sigue cargando si no hay `sentit.json`.
- `CRITERI_KENLM`: margen 1 (desde la 2.0.1; hasta la 2.0.0, margen 3), la
  catalana por defecto, λ 1,5 en homógrafos resolubles, 1,25 en irresolubles
  y 0,75 en colisiones, y desempate < 2 con el clasificador (`Criteri.desempat`):
  si KenLM gana por menos de 2, decide el clasificador de la palabra (si
  tiene); si no, la regla de siempre.
- `punts.decisio_spacy`: antes del modelo, spaCy descarta lecturas
  imposibles; desde el 13/11/2026 también si la palabra anterior es un
  pronombre personal ("Tu manques de paciència": verbo, no nombre), y un
  NUM detrás de "una" no es el numeral ("una nou": decide el modelo). spaCy
  etiqueta el texto sin los espacios del principio y del final (un espacio
  al final cambiaba la etiqueta).

Ficheros (fuera de git): `valencia_net_dogv_o5.binary` (82 MB; desde la
2.0.0, MaCoCu valenciano limpio + el DOGV 2025-2026 entero, orden 5, poda
de singletons: `valencia_net_dogv2` en Abaco), `valencia_net_dogv_freq.json`
y el clasificador `sentit.json` (`sentit_dogv2_avl`: el mismo texto + la
AVL; o el antiguo de "cop", `nb.json`). Publicados en Hugging Face
([`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va),
CC BY 4.0; `REVISIO_HF` dice qué revisión descarga cada versión del
paquete): sin `AVLIZADOR_KENLM_DIR`, `directori_kenlm` los busca en la caché
de Hugging Face y los descarga la primera vez. En la imagen Docker van en
`/opt/kenlm` (se descargan al construirla, o se copian de `docker/kenlm/`).
Para publicar una versión nueva: `scripts/hf_model/kenlm.py`. El paquete `kenlm` se compila al instalarlo (`pip install
"avlizador[kenlm]"`; en Windows hace falta compilador, la imagen Docker es
Linux).

## Opción: KenLM de lemas (`--model kenlm-lemes`, 23/11/2026)

Decisión del usuario: se deja como **opción**, no por defecto. El mismo
sistema (criterio `CRITERI_KENLM` y el mismo clasificador), pero el KenLM es
el de **lemas parciales** (propuesta del supervisor): el texto de
entrenamiento y las frases candidatas se pasan a lemas con
`lemes.LematitzadorLM` («va pegar» → «anar pegar»), salvo las palabras
candidatas y las que concuerdan en género («una vegada», «les nous»), que se
quedan en su forma. Así el modelo tiene más datos para cada contexto.

El contexto se lematiza **una sola vez**, sobre la traducción del motor
(`kenlm.ModelKenLMLemes.fixa_referencia`, que llama `puntua_punts` cuando la
frase tiene alguna palabra ambigua): spaCy lematizaba el contexto distinto
según el candidato («cosia bragues» → «cosir», «cosia calces» → «cosia») y
eso daba errores graves.

| En los homógrafos corregidos del 23/11 | KenLM (por defecto) | KenLM de lemas |
|---|---|---|
| Decisiones (237): aciertos / graves / sin traducir | 196 / 0 / 41 | 198 / 1 / 38 |
| Exactas homógrafos v1 (249) / v2 (144) | 228 / 113 | 229 / 114 |
| Exactas manual (458) / 151 (154) | 232 / 144 | 232 / 144 |
| Tiempo del modelo por frase con palabra ambigua | ~0,1 ms | ~10-17 ms (spaCy) |

El grave es «calces» → «bragues» en HG2-093. `avlizador avalua --model kenlm
kenlm-lemes` en Abaco da lo mismo que el comparador (job 3383).

Uso: `translate_cat_val(text, model="kenlm-lemes")`, `avlizador tradueix
--model kenlm-lemes` o `avlizador avalua --model kenlm kenlm-lemes`. Ficheros,
en la carpeta de `AVLIZADOR_KENLM_DIR` (**no se descargan de Hugging Face**):
`valencia_net_dogv_lemes_o5.binary` (80 MB; en Abaco,
`dades/macocu/kenlm/valencia_net_dogv2_lemes_o5.binary`),
`valencia_net_dogv_lemes_freq.json` (`_lemes_freq.json`) y el mismo
`sentit.json`. En Abaco, `~/kenlm_2.0.0` ya tiene los enlaces. Si falta
algo, `FaltaKenLM` (no vuelve al motor solo). Detalle:
`documentacio/resultats_model_llengua_kenlm.md`, 4.23-4.25.

## Mantenimiento: palabras y corpus nuevos (16/11/2026)

Qué hay que hacer para que el sistema KenLM + clasificador tenga en cuenta
una palabra ambigua nueva o un corpus nuevo. Todas las órdenes, desde la
raíz del repositorio. En Abaco, con el venv activado (`source
~/venvs/avlizador/bin/activate`) y la rama al día (`git pull`).

Los ficheros del modelo viven en **tres sitios** de trabajo, y cada vez
que cambie uno hay que copiarlo a los tres; el cuarto, Hugging Face, solo
se toca para una versión nueva del paquete:

| Sitio | Para qué |
|---|---|
| `dades/macocu/kenlm/` en Abaco | evaluar (`avalua_sistema.sh`, `compara_models.sh`) |
| la carpeta de `AVLIZADOR_KENLM_DIR` en el PC (si se usa KenLM fuera de Docker) | `translate_cat_val`, `avlizador tradueix` |
| `docker/kenlm/` (fuera de git) | la imagen Docker (`/opt/kenlm`); hay que reconstruirla |
| Hugging Face (`transducens/avlizador-kenlm-va`) | lo que descarga el paquete y la imagen si no hay `docker/kenlm/`. Solo para una versión nueva del paquete: `scripts/hf_model/kenlm.py`, subirlo y poner el commit nuevo en `REVISIO_HF` (README de la raíz, «Qué versión del modelo descarga cada versión del paquete») |

### 1. Palabra ambigua nueva

| # | Paso | Dónde |
|---|---|---|
| 1 | El compañero añade la entrada al léxico: `forma_problematica`, `problema` (`colision_homonima` o `homonimia_lexica`) y, si son homógrafos, `lemas`. Conviene que el `espanol` de cada lectura esté bien (servirá si se etiquetan los sentidos con el castellano). | `dades/lexic/lexico_general.json` |
| 2 | Copiar el léxico dentro del paquete. Desde aquí el sistema **ya trata la palabra como ambigua** (`punts.carrega_punts`). Commit y `git pull` en Abaco. | PC |
| 3 | Comprobar que las candidatas están en la tabla de frecuencias. Si falta alguna, regenerarla (si no, cuenta como 0 apariciones y con λ gana ventaja: pasó con «faltes» el 13/11). | PC / Abaco |
| 4 | **KenLM no se toca**: es un modelo general del valenciano y puntúa cualquier frase. | — |
| 5 | Reentrenar el clasificador (sección 3). | PC o Abaco |
| 6 | Copiar a los tres sitios lo que haya cambiado (`valencia_net_dogv_freq.json`, `sentit.json`) y reconstruir la imagen Docker. | — |
| 7 | Medir. | Abaco |

Si se quiere medir la palabra nueva, hay que añadir frases suyas al
benchmark de homógrafos (solo con permiso del usuario).

```bash
# 2. Léxico -> paquete (PC)
python scripts/sync_data.py
python scripts/sync_data.py --check          # "Tot sincronitzat"

# 3. ¿Faltan candidatas en la tabla de frecuencias? (sin kenlm: vale en Windows)
#    Imprime [] si están todas. Cambiar la ruta por la del fichero que se use.
python -c "import json; from avlizador.traductor_cat_val.model_llengua.kenlm import ModelKenLM; from avlizador.traductor_cat_val.model_llengua.lemes import formes_candidates; f = json.load(open('docker/kenlm/valencia_net_dogv_freq.json', encoding='utf-8')); print(ModelKenLM(None, f).paraules_sense_freq(formes_candidates()))"
#    (Al cargar el sistema también sale el aviso AvisFreqKenLM.)

# 3b. Si falta alguna: regenerarla en Abaco (lee el léxico del paquete: antes, git pull)
cp dades/macocu/kenlm/valencia_net_dogv_freq.json dades/macocu/kenlm/valencia_net_dogv_freq_$(date +%Y%m%d).json
python pipeline/08_traduccio_corpus/macocu/kenlm/freq_unigrames.py dades/macocu/kenlm/valencia_net_dogv.txt
#    -> dades/macocu/kenlm/valencia_net_dogv_freq.json. Al PC:
scp nmartin@abaco:~/scrapeo/AVLizador/dades/macocu/kenlm/valencia_net_dogv_freq.json docker/kenlm/

# 6. Imagen Docker con los ficheros nuevos de docker/kenlm/
docker compose up --build

# 7. Medir (Abaco, desde pipeline/03_seleccio_de_model/model_llengua)
MODELS="kenlm" BENCHMARKS="homografs homografs_v2 manual" sbatch avalua_sistema.sh
#    -> pipeline/03_seleccio_de_model/resultats/avalua_sistema_<fecha>/resum_<fecha>.md
```

### 2. Corpus nuevo

El corpus sirve para dos cosas distintas, y cada una tiene sus pasos.

**A. Para KenLM** (se reentrena):

1. **Preparar el texto**: quedarse solo con el valenciano filtrando por GD
   (como el DOGV en `prepara_dogv.py`) y normalizarlo con la misma función
   de siempre (`kenlm.normalitza`; lo hacen los dos scripts). Una frase
   por línea.
2. **Unir los textos**: el texto actual, `valencia_net_dogv.txt`, más el
   nuevo, en un fichero nuevo.
3. **Entrenar** en Abaco con `entrena_kenlm.sh`: genera el `.binary` (orden
   5, poda de singletons) y su tabla de frecuencias (`<nom>_freq.json`).
4. **Comparar** con el modelo actual en el comparador: darle una clave en
   `FITXERS_KENLM` y en `MODELS` de `compara_models.py` y lanzarlo en
   homógrafos y manual. Las dos claves sin `_c1` se comparan sin
   clasificador: es la comparación de los dos KenLM.
5. **Si mejora, pasarlo al sistema**. El paquete busca siempre
   `valencia_net_dogv_o5.binary` y `valencia_net_dogv_freq.json`
   (`NOM_MODEL` en `kenlm.py`): o se renombran los ficheros nuevos con esos
   nombres (guardando los viejos), o se cambia `NOM_MODEL`. Después, a los
   tres sitios, y la evaluación completa (`avalua_sistema.sh` con todos los
   benchmarks). El clasificador no depende de KenLM: no hace falta
   reentrenarlo.

```bash
# 1. Preparar el texto (Abaco o PC), según el formato del corpus:
#    - documentos como el DOGV (mismo formato que dogv_documents.tsv): documentos de GD >= 0,8
python pipeline/08_traduccio_corpus/dogv_apunt/prepara_dogv.py --entrada <corpus.tsv> --eixida dades/macocu/kenlm/<nuevo>.txt --min-gd-doc 0.8
#    - frases en JSONL (campo text; gd y occ si se filtra, como valencia.jsonl)
python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py --jsonl <corpus.jsonl> --min-gd 0.5 --eixida dades/macocu/kenlm/<nuevo>.txt

# 2. Unir
cat dades/macocu/kenlm/valencia_net_dogv.txt dades/macocu/kenlm/<nuevo>.txt > dades/macocu/kenlm/<nom>.txt

# 3. Entrenar (Abaco, desde pipeline/08_traduccio_corpus/macocu/kenlm; TEXT relativo a la raíz del repo)
TEXT=dades/macocu/kenlm/<nom>.txt NOM=<nom> sbatch entrena_kenlm.sh
#    -> dades/macocu/kenlm/<nom>_o5.binary y <nom>_freq.json

# 4. Comparar (Abaco, desde pipeline/03_seleccio_de_model/model_llengua), tras añadir
#    "kenlm_<nom>": "<nom>" a FITXERS_KENLM y "kenlm_<nom>" a MODELS:
MODELS="kenlm_val_net_dogv kenlm_<nom>" EXTRA="--benchmarks homografs homografs_v2 manual --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --detall" sbatch compara_models.sh

# 5. Pasarlo al sistema (Abaco), guardando los viejos
cd dades/macocu/kenlm
mv valencia_net_dogv_o5.binary valencia_net_dogv_o5_$(date +%Y%m%d).binary
mv valencia_net_dogv_freq.json valencia_net_dogv_freq_$(date +%Y%m%d).json
cp <nom>_o5.binary valencia_net_dogv_o5.binary
cp <nom>_freq.json valencia_net_dogv_freq.json
#    y al PC (docker/kenlm/ y AVLIZADOR_KENLM_DIR) con scp, como en 3b.
```

Otros órdenes del KenLM: `ORDRE=<n>` en `entrena_kenlm.sh` (con
`SENSE_FREQ=1` si el texto es el mismo y ya tiene tabla) y
`pipeline/03_seleccio_de_model/model_llengua/prova_ordres.sh` (orden 5
frente a 6, 7 y 8; 16/11/2026: dan las mismas decisiones, se queda el 5).
Ojo: `kenlm` se compila por defecto con orden máximo 6; para más hay que
recompilar las herramientas (`cmake -DKENLM_MAX_ORDER=10 ..`) y el módulo
de Python (`MAX_ORDER=10 pip install --no-cache-dir --force-reinstall
https://github.com/kpu/kenlm/archive/master.zip`).

**B. Para el clasificador**:

1. Las fuentes de frases están en
   `pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py`: `FONTS`
   (`net` = `dades/macocu/valencia/valencia.jsonl`, `dogv` =
   `dades/dogv_apunt/dogv_net.txt`, `avl`) y `frases_font`. Añadir un
   corpus es añadir una fuente más (un nombre en `FONTS`, su ruta y su
   rama en `frases_font`; un texto normalizado, una frase por línea, como
   `dogv_net.txt`). Es un cambio de código pequeño. Ojo: el clasificador
   va con el paquete, así que la fuente tiene que poder redistribuirse (por
   eso la AVL está fuera desde el 12/11).
2. Reentrenar con esa fuente. Si debe usarse siempre, añadirla también a
   `FONTS_PER_DEFECTE`.

```bash
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py recompte --fonts net dogv <nueva>
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py entrena --fonts net dogv <nueva>
```

### 3. Cómo se actualiza el clasificador

- **Se reentrena entero**, no por partes. `recompte` dice cuántas frases
  tiene cada sentido de cada palabra; `entrena` escribe
  `dades/macocu/kenlm/sentit/sentit.json` (el clasificador) y
  `sentit_entrenament.json` (el informe). Necesita
  `dades/macocu/valencia/valencia.jsonl` y `dades/dogv_apunt/dogv_net.txt`
  (están en el PC y en Abaco).
- **Las palabras entran y salen solas**: cada palabra que llega al 0,7 de
  acierto equilibrado en las frases apartadas entra en `grups`; las que no
  llegan van a `descartats` y las que no tienen datos (menos de 20 frases
  de un sentido), a `sense_dades`. El sistema las trata como siempre: con
  duda, la catalana. No hay que tocar nada a mano.
- **El sistema coge el fichero nuevo solo**: carga `sentit.json` si existe
  y, si no, el antiguo de «cop» (`nb.json`).
- **Protección si cambia el léxico**: si el léxico cambia las candidatas de
  una palabra, su clasificador antiguo deja de usarse (`sentit.py`,
  `ClassificadorSentit.candidat`) hasta que se reentrene.
- **Ojo**: reentrenar no arregla las palabras a las que les faltan datos.
  Para eso hace falta más corpus o etiquetar los sentidos con el castellano
  (corpus paralelo catalán–castellano y el `espanol` del léxico; propuesta
  del 16/11, sin hacer).

```bash
# Entrenar (PC o Abaco)
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py recompte
python pipeline/03_seleccio_de_model/model_llengua/sentit_general.py entrena
#    Opciones: --min-dev 0.7 (umbral), --minim 20 (frases mínimas por sentido), --fonts

# Qué palabras han entrado (y con qué acierto)
python -c "import json; d = json.load(open('dades/macocu/kenlm/sentit/sentit_entrenament.json', encoding='utf-8')); [print(s, list(x['punts']), x['frases'], x.get('balancejat')) for s in ('grups', 'descartats', 'sense_dades') for x in d[s].values()]"

# A los tres sitios (desde el PC)
cp dades/macocu/kenlm/sentit/sentit.json docker/kenlm/
scp dades/macocu/kenlm/sentit/sentit.json nmartin@abaco:~/scrapeo/AVLizador/dades/macocu/kenlm/sentit.json
#    + la carpeta de AVLIZADOR_KENLM_DIR, si se usa; y docker compose up --build
```

Lo que sigue (hasta "Límites conocidos") es sobre todo la historia de
FLOR (23/10-12/11/2026). Las capas de spaCy y la elección por tipo de punto
son las mismas para los dos modelos.

## Qué resuelve

Los puntos salen del léxico (`traductor_cat_val/data/lexic_general.json`), sin
ninguna palabra escrita en el código:

| tipo | de dónde sale | ejemplo | qué hace hoy el motor |
|---|---|---|---|
| `colisio` | `problema: "colision_homonima"` | cop → colp / vegada; cops → colps / vegades | no traduce (dos candidatos, ninguno canónico) |
| `irresoluble` | `homonimia_lexica`, lecturas de la misma categoría | calces → bragues / calces; gandula → hamaca / gandula | traduce siempre |
| `resoluble` | `homonimia_lexica` que spaCy separa | nou → anou / nou; manca → carència / manca | decide spaCy |

**Sistema final (decisión del usuario, 23/10/2026):**

- `colisio` ("cop", "cops"): el modelo de lenguaje.
- `irresoluble` ("calces", "gandula", "gandules"): dos capas.
  (1) **spaCy por categoría no compartida**: los `lemas` dicen qué
  categorías tiene cada lectura ("gandula": `gandul [adj, n]` y `gandula
  [n]`). Si spaCy da una categoría que solo tiene la otra lectura ("molt
  gandula": ADJ), se deja la palabra catalana. (2) Si no, **el modelo**, que
  solo cambia lo que hizo el motor si gana por más de `marge` (5; desde el
  05/11/2026, margen 2 con la catalana por defecto, ver más abajo).
- `resoluble` ("nou", "manca"…): spaCy dentro del motor, como siempre.

Historia de la decisión sobre los irresolubles: primero se quitó el modelo,
porque no separaba "gandules" (tumbona) de "gandules" (personas vagas). La
causa era un **error de datos**: E0592 decía "hamaces", forma incorrecta (el
plural de "hamaca" es "hamaques", como vaca → vaques), y el modelo la
castigaba siempre. Con el dato corregido (permiso del usuario, 23/10/2026)
la diferencia traducir − dejar separa los sentidos: tumbona −2,9 a +4,8,
persona −7,1 a −11,7; el margen 5 cae en medio. "calces" sigue sin
separarse (el modelo no conoce el sentido histórico): queda "bragues".
Irresolubles: 14/24 sin el modelo, **18/24** con él. Se puede quitar con
`Criteri(model_irresolubles=False)` o `evalua_models.py --sense-model-irresolubles`.

**Lección**: una palabra del léxico mal escrita hace que el modelo la vea
improbable sea cual sea el sentido. El modelo sirve también para encontrar
formas sospechosas del léxico.

Criterio por defecto (`Criteri()`): FLOR-760M, PMI 0,5, suma, **margen 2
con la palabra catalana por defecto** (`per_defecte="catala"`, desde el
05/11/2026), concordancia `variants`, puntuación de la frase entera.

### Margen 2 con la catalana por defecto (05/11/2026, decisión del usuario)

En los homógrafos que llegan a FLOR (irresolubles y resolubles con NOUN;
"cop/cops" y lo que decide spaCy no cambian), **solo se traduce si FLOR ve
la traducción más probable que la palabra catalana por más de 2 puntos**
de log-probabilidad (unas 7 veces más probable, e² ≈ 7,4). Si no, se deja
la palabra catalana. Antes era al revés (`per_defecte="motor"`, margen 5):
se quedaba la traducción del motor salvo que FLOR prefiriera la catalana
por más de 5. Para volver: `Criteri(per_defecte="motor", marge=5.0)`.

**Por qué la catalana por defecto**: los dos fallos no pesan igual.
Traducir cuando no toca cambia el sentido ("calces" de época → "bragues",
"gandules" vagas → "hamaques", "manca" verbo → "falta"). No traducir deja
la palabra catalana ("rentadora", "manca", "reeixida"), menos dialectal
pero con el mismo sentido y a menudo válida también en valenciano. El
usuario prefiere no traducir a traducir mal.

**Por qué 2 y no 0**: diferencia de FLOR (traducción − catalana) en las
trazas con P1 de homógrafos v1 + v2, 159 palabras que decide el modelo:

| Diferencia | La referencia quiere la valenciana | Quiere la catalana |
|---|---|---|
| ≤ −4 | 11 | 32 |
| −4 a 0 | 52 | 22 |
| 0 a 2 | 10 | 7 |
| > 2 | 23 | 2 |

Cuando la buena es la catalana, FLOR suele decirlo claro (mediana −4,3);
cuando es la valenciana, casi nunca (mediana −1,1: el sesgo hacia la forma
frecuente). Entre 0 y 2 FLOR ya prefiere la traducción pero acierta 10 de
17 (cara o cruz); por encima de 2, 23 de 25. Con margen 0 se traduciría en
esa zona de duda. Simulación del margen con la catalana por defecto:

| Margen | Traduce sin tocar (error de sentido) | Deja la catalana cuando tocaba traducir | Aciertos |
|---|---|---|---|
| antes (motor, 5) | 28/63 | 9/96 | 122/159 |
| 0 | 9/63 | 63/96 | 87/159 |
| 1 | 5/63 | 71/96 | 83/159 |
| **2** | **2/63** | 73/96 | 84/159 |
| 5 | 1/63 | 85/96 | 73/159 |

Depende de la palabra: FLOR separa bien "deu" (mediana +8,3 si toca
traducir frente a −18,8 si no), "gandula", "manques" y "nou"; no separa
"calces", "reeixida(es)", "panotxa(es)" ni "recuita", que casi nunca se
traducirán. Límites: el 2 sale de estos mismos benchmarks (equilibrados
50/50 por sentido, no del uso real) y la simulación usa las trazas del
03/11. Benchmark manual (ejecutado, no simulado): 229 → **228/458**
(BLEU 90,93 → 90,91, TER 5,58 → 5,59). Cambian dos frases: BM-AVL-191 "les
anous" → "les nous" (la pierde: FLOR prefería "anous" por menos de 2) y
BM-BOE-219 "falta" → "manca" (falla igual: la referencia pone "carència").
Con margen 0 o 1 el manual quedaba en 229.

**Homógrafos, ejecutado (06/11/2026)**, frente al margen 5 a favor del
motor (03/11): 151 + homógrafos 233 → **218/253**, homógrafos v2 124 →
**95/160**; manual 228/458 y BOE estricto/amplio sin cambios por el
margen. Es lo que anunciaba la simulación: en el v2 (equilibrado por
sentido) las frases cuya referencia **deja la palabra catalana** pasan de
42 a **57 de 59** (+16, −1), y las que **piden la valenciana** caen de 82
a **38 de 101** (+5, −49). Casi todos los errores de sentido desaparecen;
a cambio, muchas palabras valencianas quedan sin traducir ("anou",
"llavadora", "brulla", "panolla", "exitosa"...). Es el precio aceptado
de la decisión. Cifras con el léxico del 05/11 (género, "mencionar",
"contindre") y el arreglo de `te_problema` del 06/11: el léxico nuevo
trae `problema` como lista en 10 entradas (`["homonimia_lexica",
"cambio_genero"]`), y sin ese arreglo "nou", "deu" y "cop" dejaban de
pasar por spaCy y FLOR (v2 82/160, igual que el motor solo).

**Párrafo valenciano delante (03/11/2026)**: FLOR prefiere la forma que ha
visto más veces, casi siempre la catalana ("vegada" frente a "colp",
"rentadora" frente a "llavadora"). Desde el 03/11 cada frase se puntúa
como continuación de un párrafo corto en valenciano
(`puntuador.CONTEXT_PER_DEFECTE`; `ModelLlengua(context=None)` lo quita).
El párrafo pasa por el modelo una sola vez (`past_key_values`): no cuesta
tiempo. 151 + homógrafos 226 → **233/253**, homógrafos v2 111 → **122/160**,
gplsi 1.544 → 1.547; manual, 151 y BOE sin cambios. Pierde "manca" verbo
(→ "carència") en 2 frases más. Pruebas (párrafos, frecuencias, LoRA) en
`pipeline/03_seleccio_de_model/model_llengua/sesgo/README.md`.

**Concordancia con el determinante (03/11/2026)**: si spaCy da ADJ a la
palabra ambigua y su género no es el del determinante de delante ("una
nou", "les nous"), la capa de spaCy no decide y pasa al modelo
(`punts.decisio_spacy`). Con NUM no (un numeral hace de nombre con
cualquier artículo: "la nou" = la jugadora del dorsal nueve). Homógrafos
v2 122 → 124, manual 227 → 228, homógrafos 233 igual. Detalle en
`pipeline/03_seleccio_de_model/traces/README.md`.

**Resultados (23/10/2026)**:

| benchmark | motor solo | sistema final |
|---|---|---|
| combinado (151 + homógrafos), exactas | 190/253 (BLEU 91,5) | **227/253** (BLEU 96,5) |
| — 151 | 146/154 | 146/154 (cero cambios) |
| — colisio | 0/33 | 31/33 |
| — irresoluble | 12/24 | 18/24 (calces 5/10, gandula 7/8, gandules 6/6) |
| — resoluble | 30/40 | 30/40 |
| BOE amplio (2.000 líneas reales) | 1.200 (medida del 22/10) | 1.206 (sin irresolubles en el BOE) |

Errores que quedan en colisio: "un últim **cop** al banc" (golpe = robo) y
"intent de **cop**" (golpe de estado sin "d'estat"), los dos salen "vegada".

La función del sistema final era `translate_cat_val_ml(text)` (hoy, fuera
del paquete, `flor.translate_cat_val_flor`), y
`evalua_models.py --model traductor_ml --direccio cat-val` la evalúa.
**Desde el 29/10/2026 `avlizador.translate_cat_val` es siempre este
sistema** (motor + FLOR-760M); el motor solo queda como
`translate_cat_val_motor` (`evalua_models.py --model traductor --direccio
cat-val`). Ese mismo día los resolubles también pasan por el modelo y
"nou", "manca", "recuita"… se volvieron irresolubles (los `lemas` dicen
que el adjetivo también hace de nombre). El
benchmark para comparar el sistema final con el motor es
`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json`: el de
151 más los homógrafos. Se reconstruye con `construeix_benchmark_sistema_final.py`.

## Cómo funciona

1. El motor traduce la frase.
2. Para cada punto, se construyen las frases valencianas **completas**, una
   por candidato, sobre una "base neutra" (la frase del motor con la palabra
   ambigua sin tocar) y con el determinante concordado:
   "**Una vegada** acabada la reunió…" / "**Un colp** acabada la reunió…".
3. El modelo de lenguaje puntúa cada frase (log-probabilidad) y gana la
   más probable. El modelo no genera texto ni responde preguntas.

Opciones del criterio (`Criteri`), para probar con `avalua.py`:

- `lam` (PMI): resta `lam` × log P(candidato solo), para compensar que una
  palabra sea más frecuente que la otra en general. 0 = sin corrección.
- `norma`: `suma` (toda la frase) o `mitjana` (por token).
- `marge` y `per_defecte`: en los homógrafos, la forma por defecto
  (`catala`: la palabra catalana; `motor`: la traducción del motor) solo
  cambia si la otra gana por más de `marge` puntos.
- `concordanca`: `motor` (por defecto desde el 19/11/2026: la frase de cada
  candidato la hace la regla de concordancia, con spaCy y el fichero
  morfológico, "molts cops"→"moltes vegades", y el modelo solo elige la
  palabra) o `variants` (por defecto hasta el 19/11/2026: además propone
  las formas del otro género de las dos palabras anteriores y el modelo
  elige; no mira si dependen del nombre y daba "L'aïllament és absoluta
  una vegada arribes", FLORES+ devtest 461).
- `puntuacio`: `frase` (toda la frase) o `dreta` (experimental: solo lo que
  viene después de la palabra, condicionado a ella; deja fuera el término
  "qué probable es esta palabra aquí", donde está el sesgo del modelo hacia
  la forma catalana).
- `spacy_irresolubles`: la capa de spaCy para los irresolubles.
- `model_irresolubles`: el modelo también para los irresolubles cuando
  spaCy no decide (por defecto `True`).

Lo medido el 23/10/2026: PMI no hace falta en colisio (32/32 con PMI 0 por
media o 0,5 por suma); `dreta` empeora colisio (28/32) y apenas cambia los
irresolubles; `variants` produce la concordancia correcta ("Moltes
vegades", "Una altra vegada", "Per primera vegada").

Modelos: `projecte-aina/FLOR-760M` por defecto (1,5 GB, CPU, ~1,5 s por
frase con "cop") y `BSC-LT/salamandra-2b` (4,5 GB, ~3,3 s, peor en todo:
descartado). Se descargan solos la primera vez desde Hugging Face.

Baseline del 29/10/2026 con 9 modelos pequeños (FLOR, salamandra, EuroLLM,
bloom, Qwen2.5 y Qwen3): **FLOR-760M sigue siendo el mejor** (227/253 en el
combinado; el siguiente, salamandra-2b, 222) y el más rápido. Los modelos
que no conocen el valenciano eligen "vegada" casi siempre. Detalle en
`documentacio/resultats_baseline_models_llengua.md`; pendiente FLOR-1.3B.

## Ficheros

- `punts.py`: detección de los puntos y construcción de los candidatos (sin modelo).
- `kenlm.py`: `ModelKenLM` y `normalitza` (alternativa a FLOR, sin torch; 12/11/2026).
- `sentit.py`: clasificadores de sentido (`ClassificadorSentit`, el general; `ClassificadorCop`, el antiguo).
- `__init__.py`: `tradueix_cat_val_ml(text, model, criteri, sentit=None)`, elección
  del candidato; `translate_cat_val_kenlm` (KenLM).
- FLOR (`ModelLlengua`, torch + transformers) ya no está aquí: desde la 2.0.0,
  `pipeline/03_seleccio_de_model/model_llengua/flor.py`.

Fuera del paquete, en `pipeline/03_seleccio_de_model/model_llengua/`:

- `frases_homografs.json`: las frases catalanas del benchmark, con el sentido esperado.
- `genera_benchmark.py`: crea `benchmark_homografs_cat_val.json` con el motor
  (la referencia es el motor con el candidato correcto). **Las referencias
  hay que revisarlas a mano.**
- `avalua.py`: prueba todos los criterios con cada modelo y lo compara con el motor solo.

## Ejecutar (desde la raíz del repo)

```bash
# doctests de todo el paquete (sin modelo, solo spaCy)
pytest tests/test_doctests.py

# regenerar el benchmark (NO sobrescribe uno revisado sin --sobreescriu)
python pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py

# evaluar sobre el benchmark de homógrafos
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --per-defecte   # solo el sistema final
python pipeline/03_seleccio_de_model/model_llengua/avalua.py                 # rejilla: PMI x margen x frase/dreta x spaCy sí/no
python pipeline/03_seleccio_de_model/model_llengua/avalua.py --models projecte-aina/FLOR-760M BSC-LT/salamandra-2b

# sistema final contra el motor solo (151 + homógrafos)
cd pipeline/03_seleccio_de_model
python construeix_benchmark_sistema_final.py
python evalua_models.py --model traductor --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
python evalua_models.py --model traductor_ml --sense-model-irresolubles --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json   # para comparar
```

Los resultados se guardan en
`pipeline/03_seleccio_de_model/resultats/` (`benchmark_homografs_ml_<modelo>_<fecha>.json`
los de `avalua.py`, `benchmark_Traductor_Invers_ML_<modelo>_<fecha>.json` los
de `evalua_models.py`). Si `evalua_models.py` imprime `ERROR:` en una
frase, esa frase se ha devuelto sin traducir: hay que mirarlo.

## Límites conocidos

- La concordancia depende del análisis de spaCy: si analiza mal la frase,
  alguna palabra se queda en el género de antes ("La xocolata desfeta és
  molt bona" → "El xocolate desfet és molt bona").
- Si la palabra ya la ha consumido otra regla ("cop de puny" → "punyada"),
  no es un punto.
- Homógrafos que el léxico no marca como `homonimia_lexica` no llegan a esta
  capa. Caso visto: E0251 "afecta"→"carinya" (adjetivo, par correcto) se
  aplica también al verbo ("La manca de pluja **afecta** els cultius" →
  "carinya").
