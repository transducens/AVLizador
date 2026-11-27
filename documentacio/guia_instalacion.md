*[Llegeix-ho en valencià](guia_installacio.md)*

# Instalar y usar AVLizador (Windows, Linux y macOS)

Guía paso a paso para instalar el paquete `avlizador` desde el
repositorio, traducir una frase, medir el Grau Dialectal y evaluar. Cada
paso tiene los comandos de los tres sistemas.

## 0. Requisitos

- **Python 3.10 o posterior** y **Git**.
- Un **compilador de C++** para KenLM, el modelo de lenguaje por defecto
  (se compila al instalarlo). En Windows normalmente no se instala: ver
  el paso 3.
- No hace falta tarjeta gráfica: todo funciona con CPU.
- Conexión a internet en la instalación y la primera vez que se traduce
  (se descargan de Hugging Face los tres ficheros del modelo KenLM, unos
  83 MB; ver el paso 3).

| | Comprobar | Instalar si falta |
|---|---|---|
| **Windows** (PowerShell) | `python --version`, `git --version` | python.org (marcar "Add python.exe to PATH") y git-scm.com |
| **Linux** (Debian/Ubuntu) | `python3 --version`, `git --version` | `sudo apt install python3 python3-venv python3-pip git build-essential zlib1g-dev` |
| **Linux** (Fedora) | ídem | `sudo dnf install python3 python3-pip git gcc-c++ zlib-devel` |
| **macOS** | `python3 --version`, `git --version` | `xcode-select --install` (trae Git y el compilador) y Python de python.org o `brew install python` |

## 1. Descargar el repositorio

Igual en los tres sistemas:

```bash
git clone https://github.com/transducens/AVLizador.git
cd AVLizador
```

Si ya estaba clonado: `git checkout main` y `git pull`.

## 2. Crear y activar un entorno virtual

Deja el paquete aislado del resto de Python. Se crea una vez y se activa
**cada vez que se abre una terminal nueva**.

| | Crear | Activar |
|---|---|---|
| **Windows** (PowerShell) | `python -m venv .venv` | `.\.venv\Scripts\Activate.ps1` |
| **Linux / macOS** | `python3 -m venv .venv` | `source .venv/bin/activate` |

Activado, la línea de la terminal empieza por `(.venv)` y `python` y
`pip` ya son los del entorno (también en Linux y macOS, sin el "3").

- Windows: si PowerShell no deja activarlo ("execution policy"), una
  vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Linux: si falla con "ensurepip is not available", falta el paquete
  `python3-venv` (paso 0).

## 3. Instalar el paquete

Igual en los tres sistemas (con el entorno activado):

```bash
python -m pip install -U pip
pip install -e ".[kenlm,avaluacio,dev]"
avlizador --version        # -> avlizador 2.0.1
```

- `[kenlm]`: la biblioteca KenLM, el modelo de lenguaje de las palabras
  ambiguas ("cop", "nou"...) con un clasificador de sentido, y
  `huggingface_hub` para descargar sus ficheros. Es el sistema por defecto
  desde el 13/11/2026; sin él (o sin los ficheros de abajo), el traductor
  usa solo el motor y avisa.
- `[avaluacio]`: sacrebleu, para `avlizador avalua`. `[dev]`: pytest.
- El modelo catalán de spaCy (`ca_core_news_md`) se instala solo.
- `-e` (editable): el paquete usa los ficheros de la carpeta; si se
  cambia algo (por ejemplo el léxico), no hay que reinstalar.

Instalación mínima, solo el motor de reglas: `pip install -e .`

**Ficheros del modelo KenLM.** No están en git ni en el paquete: están
publicados en Hugging Face,
[`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va)
(CC BY 4.0), y el paquete los descarga solo la primera vez que se
traduce: `valencia_net_dogv_o5.binary` (el modelo, 82 MB),
`valencia_net_dogv_freq.json` (frecuencias) y `sentit.json` (el
clasificador de sentido). Se guardan en la caché de Hugging Face
(`~/.cache/huggingface` en Linux y macOS, `C:\Users\<usuario>\.cache\huggingface`
en Windows) y después no hace falta internet. Para probar que se
descargan:

```bash
avlizador tradueix "Un cop acabada la reunió, marxem."   # -> Una vegada acabada la reunió, marxem.
```

Para usar una copia local de los tres ficheros (por ejemplo, en una
máquina sin internet), la variable `AVLIZADOR_KENLM_DIR` dice dónde está
la carpeta (hay que volver a ponerla en cada terminal nueva, o añadirla
al perfil); con `AVLIZADOR_KENLM_DESCARREGA=0` no se descarga nada:

| | Comando |
|---|---|
| **Windows** (PowerShell) | `$env:AVLIZADOR_KENLM_DIR = "C:\ruta\a\kenlm"` |
| **Linux / macOS** | `export AVLIZADOR_KENLM_DIR=/ruta/a/kenlm` |

**Windows.** KenLM normalmente no se instala (no hay compilador de C++).
Dos opciones: (1) la imagen Docker de la interfaz web
(https://github.com/transducens/traductor-transducens-web), que lleva KenLM;
(2) el motor solo (`pip install -e ".[avaluacio,dev]"`): el traductor
funciona, pero no resuelve las palabras ambiguas y avisa. FLOR-760M, el
modelo hasta la versión 1.2.0, ya no está en el paquete.

## 4. Traducir

Igual en los tres sistemas:

```bash
avlizador tradueix "Un cop acabada la reunió, marxarem."
# -> Una vegada acabada la reunió, marxarem.

avlizador tradueix "Aquest noi necessita ajuda per fer els deures."
# -> Este xic necessita ajuda per a fer els deures.

avlizador tradueix --motor "Un cop acabada la reunió, marxarem."
# solo el motor de reglas, sin modelo de lenguaje: deja "Un cop" igual

avlizador tradueix --fitxer entrada.txt > salida.txt   # una frase o párrafo por línea
```

Con `--motor`, unas 250 frases por segundo; KenLM añade muy poco (~0,1
ms por frase candidata). La **primera** traducción tarda unos segundos
más: se descargan los ficheros del modelo (unos 83 MB, una sola vez) en la
caché de Hugging Face (se cambia con la variable `HF_HOME`).

## 5. Grau Dialectal

```bash
avlizador gd  --text "Este xiquet vol vindre hui."   # GD 1,0: valenciano
avlizador gd  --text "Aquest nen vol venir avui."    # GD 0,0: catalán
avlizador gdv --text "Aquest nen vol venir avui."    # GDV: cuánto catalán queda
avlizador gdc --text "Este xiquet vol vindre hui."   # GDC: cuánto valenciano aparece
```

También `--fitxer texto.txt` (un texto entero) y `--corpus corpus.jsonl
--camp text` (un documento por línea; con `--html informe.html`, informe
frase a frase).

## 6. Desde Python

```python
from avlizador import translate_cat_val, translate_cat_val_motor, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda.")        # 'Este xic necessita ajuda.' (motor + KenLM)
translate_cat_val_motor("Aquest noi necessita ajuda.")  # solo el motor
calcula_gd("Este xiquet vol vindre hui.")["gd"]         # 1.0
```

## 7. Evaluar y probar

```bash
avlizador avalua --llista                 # benchmarks disponibles (dades/benchmarks/)
avlizador avalua --benchmarks manual      # el de evaluación: 458 frases, unos 4 minutos
pytest                                    # pruebas: tienen que pasar todas
```

Si todo está bien instalado, `avalua --benchmarks manual` da **232/458,
TER 5,58** (versión 2.0.1, 23/11/2026, en las máquinas del proyecto).
Los resultados se guardan en
`resultats_avaluacio/`.

## 8. Cambiar el léxico

Se editan **solo** los ficheros de `dades/lexic/`. Después:

```bash
python scripts/sync_data.py            # copia el léxico al paquete
python scripts/sync_data.py --check    # tiene que decir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar con 232/458
```

## Problemas habituales

| Síntoma | Causa y solución |
|---|---|
| `avlizador: command not found` / no se reconoce | El entorno no está activado: paso 2 |
| Aviso `AvisSenseModelLlengua` | Falta el extra `[kenlm]`, o no se han podido descargar los ficheros del modelo (sin internet la primera vez) y no hay `AVLIZADOR_KENLM_DIR`: paso 3 |
| Error `FaltaKenLM` (con `model="kenlm"` o `--model kenlm`) | La misma causa; el mensaje dice qué falta |
| `pip` falla al compilar `kenlm` | Falta el compilador de C++ (paso 0); en Windows, Docker o el motor solo (paso 3) |
| Linux: "ensurepip is not available" | `sudo apt install python3-venv` |
| Windows: no deja ejecutar `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Sin internet en la máquina de trabajo | Descargar antes el modelo KenLM con conexión: `python -c "from huggingface_hub import snapshot_download; print(snapshot_download('transducens/avlizador-kenlm-va', revision='684993c83721bb000d424bbeb7286247c40e9154'))"` y copiar la carpeta que indica a la máquina de trabajo, con `AVLIZADOR_KENLM_DIR` apuntando a ella. |
