*[Léelo en castellano](guia_instalacion.md)*

# Instal·lar i usar AVLizador (Windows, Linux i macOS)

Guia pas a pas per a instal·lar el paquet `avlizador` des del
repositori, traduir una frase, mesurar el Grau Dialectal i avaluar. Cada
pas té les ordres dels tres sistemes.

## 0. Requisits

- **Python 3.10 o posterior** i **Git**.
- Un **compilador de C++** per a KenLM, el model de llengua per defecte
  (es compila en instal·lar-lo). En Windows normalment no s'instal·la:
  vegeu el pas 3.
- No cal targeta gràfica: tot funciona amb CPU.
- Connexió a internet en la instal·lació i la primera vegada que es
  tradueix (es baixen de Hugging Face els tres fitxers del model KenLM,
  uns 83 MB; vegeu el pas 3).

| | Comprovar | Instal·lar si falta |
|---|---|---|
| **Windows** (PowerShell) | `python --version`, `git --version` | python.org (marcar "Add python.exe to PATH") i git-scm.com |
| **Linux** (Debian/Ubuntu) | `python3 --version`, `git --version` | `sudo apt install python3 python3-venv python3-pip git build-essential zlib1g-dev` |
| **Linux** (Fedora) | ídem | `sudo dnf install python3 python3-pip git gcc-c++ zlib-devel` |
| **macOS** | `python3 --version`, `git --version` | `xcode-select --install` (porta Git i el compilador) i Python de python.org o `brew install python` |

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
pip install -e ".[kenlm,avaluacio,dev]"
avlizador --version        # -> avlizador 2.0.1
```

- `[kenlm]`: la biblioteca KenLM, el model de llengua de les paraules
  ambigües ("cop", "nou"...) amb un classificador de sentit, i
  `huggingface_hub` per a baixar-ne els fitxers. És el sistema per defecte
  des del 13/11/2026; sense ell (o sense els fitxers de baix), el
  traductor usa només el motor i avisa.
- `[avaluacio]`: sacrebleu, per a `avlizador avalua`. `[dev]`: pytest.
- El model català d'spaCy (`ca_core_news_md`) s'instal·la sol.
- `-e` (editable): el paquet usa els fitxers de la carpeta; si es canvia
  alguna cosa (per exemple, el lèxic), no cal reinstal·lar.

Instal·lació mínima, només el motor de regles: `pip install -e .`

**Fitxers del model KenLM.** No són en git ni en el paquet: estan
publicats en Hugging Face,
[`transducens/avlizador-kenlm-va`](https://huggingface.co/transducens/avlizador-kenlm-va)
(CC BY 4.0), i el paquet els baixa sol la primera vegada que es tradueix:
`valencia_net_dogv_o5.binary` (el model, 82 MB),
`valencia_net_dogv_freq.json` (freqüències) i `sentit.json` (el
classificador de sentit). Es guarden en la memòria cau de Hugging Face
(`~/.cache/huggingface` en Linux i macOS, `C:\Users\<usuari>\.cache\huggingface`
en Windows) i després no cal internet. Per a provar que es baixen:

```bash
avlizador tradueix "Un cop acabada la reunió, marxem."   # -> Una vegada acabada la reunió, marxem.
```

Per a usar una còpia local dels tres fitxers (per exemple, en una
màquina sense internet), la variable `AVLIZADOR_KENLM_DIR` diu on és la
carpeta (cal tornar-la a posar en cada terminal nova, o afegir-la al
perfil); amb `AVLIZADOR_KENLM_DESCARREGA=0` no es baixa res:

| | Ordre |
|---|---|
| **Windows** (PowerShell) | `$env:AVLIZADOR_KENLM_DIR = "C:\ruta\a\kenlm"` |
| **Linux / macOS** | `export AVLIZADOR_KENLM_DIR=/ruta/a/kenlm` |

**Windows.** KenLM normalment no s'instal·la (no hi ha compilador de
C++). Dos opcions: (1) la imatge Docker (README de l'arrel), que porta
KenLM; (2) el motor sol (`pip install -e ".[avaluacio,dev]"`): el traductor
funciona, però no resol les paraules ambigües i avisa. FLOR-760M, el model
fins a la versió 1.2.0, ja no és en el paquet.

## 4. Traduir

Igual en els tres sistemes:

```bash
avlizador tradueix "Un cop acabada la reunió, marxarem."
# -> Una vegada acabada la reunió, marxarem.

avlizador tradueix "Aquest noi necessita ajuda per fer els deures."
# -> Este xic necessita ajuda per a fer els deures.

avlizador tradueix --motor "Un cop acabada la reunió, marxarem."
# només el motor de regles, sense model de llengua: deixa "Un cop" igual

avlizador tradueix --fitxer entrada.txt > eixida.txt   # una frase o paràgraf per línia
```

Amb `--motor`, unes 250 frases per segon; KenLM hi afig molt poc (~0,1
ms per frase candidata). La **primera** traducció tarda uns segons més:
es baixen els fitxers del model (uns 83 MB, una sola vegada) en la memòria
cau de Hugging Face (es canvia amb la variable `HF_HOME`).

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

translate_cat_val("Aquest noi necessita ajuda.")        # 'Este xic necessita ajuda.' (motor + KenLM)
translate_cat_val_motor("Aquest noi necessita ajuda.")  # només el motor
calcula_gd("Este xiquet vol vindre hui.")["gd"]         # 1.0
```

## 7. Avaluar i provar

```bash
avlizador avalua --llista                 # benchmarks disponibles (dades/benchmarks/)
avlizador avalua --benchmarks manual      # el d'avaluació: 458 frases, uns 4 minuts
pytest                                    # proves: totes han de passar
```

Si tot està ben instal·lat, `avalua --benchmarks manual` dona **232/458,
TER 5,58** (versió 2.0.0, 17/11/2026, en les màquines del projecte).
Els resultats es guarden en
`resultats_avaluacio/`.

## 8. Canviar el lèxic

S'editen **només** els fitxers de `dades/lexic/`. Després:

```bash
python scripts/sync_data.py            # copia el lèxic al paquet
python scripts/sync_data.py --check    # ha de dir "Tot sincronitzat"
pytest
avlizador avalua --benchmarks manual   # comparar amb 232/458
```

## Problemes habituals

| Símptoma | Causa i solució |
|---|---|
| `avlizador: command not found` / no es reconeix | L'entorn no està activat: pas 2 |
| Avís `AvisSenseModelLlengua` | Falta l'extra `[kenlm]`, o no s'han pogut baixar els fitxers del model (sense internet la primera vegada) i no hi ha `AVLIZADOR_KENLM_DIR`: pas 3 |
| Error `FaltaKenLM` (amb `model="kenlm"` o `--model kenlm`) | La mateixa causa; el missatge diu què falta |
| `pip` falla en compilar `kenlm` | Falta el compilador de C++ (pas 0); en Windows, Docker o el motor sol (pas 3) |
| Linux: "ensurepip is not available" | `sudo apt install python3-venv` |
| Windows: no deixa executar `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Sense internet en la màquina de treball | Baixar abans el model KenLM amb connexió: `python -c "from huggingface_hub import snapshot_download; print(snapshot_download('transducens/avlizador-kenlm-va', revision='db4a1f10d55bbc30ad54728e1639d17d32526ef7'))"` i copiar la carpeta que diu a la màquina de treball, amb `AVLIZADOR_KENLM_DIR` apuntant-hi. |
