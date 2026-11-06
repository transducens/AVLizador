*[Léelo en castellano](guia_instalacion.md)*

# Instal·lar i usar AVLizador (Windows, Linux i macOS)

Guia pas a pas per a instal·lar el paquet `avlizador` des del
repositori, traduir una frase, mesurar el Grau Dialectal i avaluar. Cada
pas té les ordres dels tres sistemes.

## 0. Requisits

- **Python 3.10 o posterior** i **Git**.
- Uns **3 GB lliures**: FLOR-760M ocupa 1,5 GB i torch i spaCy, uns altres
  tants. No cal targeta gràfica: tot funciona amb CPU.
- Connexió a internet en la instal·lació i la primera vegada que es
  tradueix (es baixa FLOR).

| | Comprovar | Instal·lar si falta |
|---|---|---|
| **Windows** (PowerShell) | `python --version`, `git --version` | python.org (marcar "Add python.exe to PATH") i git-scm.com |
| **Linux** (Debian/Ubuntu) | `python3 --version`, `git --version` | `sudo apt install python3 python3-venv python3-pip git` |
| **Linux** (Fedora) | ídem | `sudo dnf install python3 python3-pip git` |
| **macOS** | `python3 --version`, `git --version` | `xcode-select --install` (porta Git) i Python de python.org o `brew install python` |

## 1. Baixar el repositori

Igual en els tres sistemes:

```bash
git clone https://github.com/transducens/AVLizador.git
cd AVLizador
```

Si ja estava clonat: `git checkout main` i `git pull`.

## 2. Crear i activar un entorn virtual

Deixa el paquet aïllat de la resta de Python. Es crea una vegada i
s'activa **cada vegada que s'obri una terminal nova**.

| | Crear | Activar |
|---|---|---|
| **Windows** (PowerShell) | `python -m venv .venv` | `.\.venv\Scripts\Activate.ps1` |
| **Linux / macOS** | `python3 -m venv .venv` | `source .venv/bin/activate` |

Quan està activat, la línia de la terminal comença per `(.venv)`, i
`python` i `pip` ja són els de l'entorn (també en Linux i macOS, sense
el "3").

- Windows: si PowerShell no deixa activar-lo ("execution policy"), una
  vegada: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Linux: si falla amb "ensurepip is not available", falta el paquet
  `python3-venv` (pas 0).

## 3. Instal·lar el paquet

Igual en els tres sistemes (amb l'entorn activat):

```bash
python -m pip install -U pip
pip install -e ".[ml,avaluacio,dev]" --extra-index-url https://download.pytorch.org/whl/cpu
avlizador --version        # -> avlizador 1.2.0
```

- `[ml]`: torch (versió CPU), transformers i FLOR-760M, el model de
  llengua de les paraules ambigües ("cop", "nou"...). És el sistema
  principal; sense ell, el traductor usa només el motor i avisa.
- `[avaluacio]`: sacrebleu, per a `avlizador avalua`. `[dev]`: pytest.
- El model català d'spaCy (`ca_core_news_md`) s'instal·la sol.
- `-e` (editable): el paquet usa els fitxers de la carpeta; si es canvia
  alguna cosa (per exemple, el lèxic), no cal reinstal·lar.
- `--extra-index-url ...whl/cpu` evita baixar torch amb CUDA (uns quants
  GB que no calen). En macOS no canvia res i es pot deixar igual.

Instal·lació mínima, sense FLOR ni avaluació: `pip install -e .`

## 4. Traduir

Igual en els tres sistemes:

```bash
avlizador tradueix "Un cop acabada la reunió, marxarem."
# -> Una vegada acabada la reunió, marxarem.

avlizador tradueix "Aquest noi necessita ajuda per fer els deures."
# -> Este xic necessita ajuda per a fer els deures.

avlizador tradueix --motor "Un cop acabada la reunió, marxarem."
# només el motor de regles, sense FLOR: deixa "Un cop" igual

avlizador tradueix --fitxer entrada.txt > eixida.txt   # una frase o paràgraf per línia
```

La **primera** traducció tarda: es baixa FLOR (1,5 GB, una sola vegada)
en la memòria cau de Hugging Face (`~/.cache/huggingface` en Linux i
macOS, `%USERPROFILE%\.cache\huggingface` en Windows; es canvia amb la
variable `HF_HOME`). Després, uns 0,5 s per frase amb FLOR i unes 250
frases per segon amb `--motor`.

## 5. Grau Dialectal

```bash
avlizador gd  --text "Este xiquet vol vindre hui."   # GD 1,0: valencià
avlizador gd  --text "Aquest nen vol venir avui."    # GD 0,0: català
avlizador gdv --text "Aquest nen vol venir avui."    # GDV: quant de català queda
avlizador gdc --text "Este xiquet vol vindre hui."   # GDC: quant de valencià apareix
```

També `--fitxer text.txt` (un text sencer) i `--corpus corpus.jsonl
--camp text` (un document per línia; amb `--html informe.html`, informe
frase a frase).

## 6. Des de Python

```python
from avlizador import translate_cat_val, translate_cat_val_motor, calcula_gd, calcula_gdv, calcula_gdc

translate_cat_val("Aquest noi necessita ajuda.")        # 'Este xic necessita ajuda.'
translate_cat_val_motor("Aquest noi necessita ajuda.")  # només el motor
calcula_gd("Este xiquet vol vindre hui.")["gd"]         # 1.0
```

## 7. Avaluar i provar

```bash
avlizador avalua --llista                 # benchmarks disponibles (dades/benchmarks/)
avlizador avalua --benchmarks manual      # el d'avaluació: 458 frases, uns 4 minuts
pytest                                    # proves: 48 passed
```

Si tot està ben instal·lat, `avalua --benchmarks manual` dona **227/458,
TER 5,61**, igual que en les màquines del projecte (comprovat en Windows
i en Linux). Els resultats es guarden en `resultats_avaluacio/`.

## 8. Canviar el lèxic

S'editen **només** els fitxers de `dades/lexic/`. Després:

```bash
python scripts/sync_data.py            # copia el lèxic al paquet
python scripts/sync_data.py --check    # ha de dir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar amb 227/458
```

## Problemes habituals

| Símptoma | Causa i solució |
|---|---|
| `avlizador: command not found` / no es reconeix | L'entorn no està activat: pas 2 |
| Avís `AvisSenseModelLlengua` | Falta l'extra `[ml]`: repetir el pas 3 |
| La primera traducció tarda minuts | Descàrrega de FLOR (només la primera vegada) |
| `pip` baixa uns quants GB de torch amb CUDA | Falta `--extra-index-url https://download.pytorch.org/whl/cpu` |
| Linux: "ensurepip is not available" | `sudo apt install python3-venv` |
| Windows: no deixa executar `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Sense internet en la màquina de treball | Baixar FLOR abans amb connexió: `python -c "from huggingface_hub import snapshot_download; snapshot_download('projecte-aina/FLOR-760M')"`, o usar `--motor` |
