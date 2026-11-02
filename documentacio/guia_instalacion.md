*[Llegeix-ho en valencià](guia_installacio.md)*

# Instalar y usar AVLizador (Windows, Linux y macOS)

Guía paso a paso para instalar el paquete `avlizador` desde el
repositorio, traducir una frase, medir el Grau Dialectal y evaluar. Cada
paso tiene los comandos de los tres sistemas.

## 0. Requisitos

- **Python 3.10 o posterior** y **Git**.
- Unos **3 GB libres**: FLOR-760M ocupa 1,5 GB y torch y spaCy, otro
  tanto. No hace falta tarjeta gráfica: todo funciona con CPU.
- Conexión a internet en la instalación y la primera vez que se traduce
  (descarga FLOR).

| | Comprobar | Instalar si falta |
|---|---|---|
| **Windows** (PowerShell) | `python --version`, `git --version` | python.org (marcar "Add python.exe to PATH") y git-scm.com |
| **Linux** (Debian/Ubuntu) | `python3 --version`, `git --version` | `sudo apt install python3 python3-venv python3-pip git` |
| **Linux** (Fedora) | ídem | `sudo dnf install python3 python3-pip git` |
| **macOS** | `python3 --version`, `git --version` | `xcode-select --install` (trae Git) y Python de python.org o `brew install python` |

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
pip install -e ".[ml,avaluacio,dev]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador --version        # -> avlizador 1.0.1
```

- `[ml]`: torch (versión CPU), transformers y FLOR-760M, el modelo de
  lenguaje de las palabras ambiguas ("cop", "nou"...). Es el sistema
  principal; sin él, el traductor usa solo el motor y avisa.
- `[avaluacio]`: sacrebleu, para `avlizador avalua`. `[dev]`: pytest.
- El modelo catalán de spaCy (`ca_core_news_md`) se instala solo.
- `-e` (editable): el paquete usa los ficheros de la carpeta; si se
  cambia algo (por ejemplo el léxico), no hay que reinstalar.
- `--extra-index-url ...whl/cpu` evita descargar torch con CUDA (varios
  GB que no hacen falta). En macOS no cambia nada y se puede dejar igual.

Instalación mínima, sin FLOR ni evaluación: `pip install -e .`

## 4. Traducir

Igual en los tres sistemas:

```bash
avlizador tradueix "Un cop acabada la reunió, marxarem."
# -> Una vegada acabada la reunió, marxarem.

avlizador tradueix "Aquest noi necessita ajuda per fer els deures."
# -> Este xic necessita ajuda per a fer els deures.

avlizador tradueix --motor "Un cop acabada la reunió, marxarem."
# solo el motor de reglas, sin FLOR: deja "Un cop" igual

avlizador tradueix --fitxer entrada.txt > salida.txt   # una frase o párrafo por línea
```

La **primera** traducción tarda: descarga FLOR (1,5 GB, una sola vez) en
la caché de Hugging Face (`~/.cache/huggingface` en Linux y macOS,
`%USERPROFILE%\.cache\huggingface` en Windows; se cambia con la variable
`HF_HOME`). Después, unos 0,5 s por frase con FLOR y unas 250 frases por
segundo con `--motor`.

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

translate_cat_val("Aquest noi necessita ajuda.")        # 'Este xic necessita ajuda.'
translate_cat_val_motor("Aquest noi necessita ajuda.")  # solo el motor
calcula_gd("Este xiquet vol vindre hui.")["gd"]         # 1.0
```

## 7. Evaluar y probar

```bash
avlizador avalua --llista                 # benchmarks disponibles (dades/benchmarks/)
avlizador avalua --benchmarks manual      # el de evaluación: 458 frases, unos 4 minutos
pytest                                    # pruebas: 48 passed
```

Si todo está bien instalado, `avalua --benchmarks manual` da **227/458,
TER 5,61**, igual que en las máquinas del proyecto (comprobado en Windows
y en Linux). Los resultados se guardan en `resultats_avaluacio/`.

## 8. Cambiar el léxico

Se editan **solo** los ficheros de `dades/lexic/`. Después:

```bash
python scripts/sync_data.py            # copia el léxico al paquete
python scripts/sync_data.py --check    # tiene que decir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar con 227/458
```

## Problemas habituales

| Síntoma | Causa y solución |
|---|---|
| `avlizador: command not found` / no se reconoce | El entorno no está activado: paso 2 |
| Aviso `AvisSenseModelLlengua` | Falta el extra `[ml]`: repetir el paso 3 |
| La primera traducción tarda minutos | Descarga de FLOR (solo la primera vez) |
| `pip` descarga varios GB de torch con CUDA | Falta `--extra-index-url https://download.pytorch.org/whl/cpu` |
| Linux: "ensurepip is not available" | `sudo apt install python3-venv` |
| Windows: no deja ejecutar `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Sin internet en la máquina de trabajo | Descargar FLOR antes con conexión: `python -c "from huggingface_hub import snapshot_download; snapshot_download('projecte-aina/FLOR-760M')"`, o usar `--motor` |
