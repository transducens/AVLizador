*[Llegir en valencià](README.md)*

# KenLM con MaCoCu-ca entero (primera prueba, 09/11/2026)

Primera prueba para sustituir a FLOR en la decisión de las palabras
ambiguas (cop/colp/vegada, nou/anou...): un modelo de n-gramas
[KenLM](https://github.com/kpu/kenlm) entrenado con **todo MaCoCu-ca sin
filtrar** (decisión del usuario), para ver por dónde tirar. Como MaCoCu
es sobre todo catalán, se espera que prefiera las formas catalanas (como
FLOR); la prueba sirve para medirlo y tener una base.

| Fichero | Qué hace |
|---|---|
| `exporta_text.py` | XML de MaCoCu → texto, una frase por línea, normalizado (`normalitza`) |
| `entrena_kenlm.sh` | job de SLURM: exporta (si hace falta) → `lmplz` → `build_binary` |
| `prova_kenlm.py` | puntúa frases y compara variantes ("vegada \| colp \| cop") |

**Qué texto entra**: todos los párrafos, de cualquier calidad jusText y
títulos incluidos; solo se quitan los de otro idioma (`lang` distinto de
`ca` y de `?`) y las frases de menos de 3 tokens. `--nomes-bons` deja
solo los párrafos `good` en catalán, para una segunda prueba.

**Normalización** (la misma al entrenar y al puntuar: por eso
`prova_kenlm.py` importa `normalitza`): minúsculas, apóstrofo pegado a la
palabra anterior ("d' una"), números a "0" y puntuación separada.

Tamaño medido con 50 MB del XML: 6,3 M de tokens y 33 MB de texto en 12
s (3 procesos). Para el corpus entero (16,8 GB): **~2.100 M de tokens,
~11 GB de texto**.

## Pasos en Abaco

### 1. Compilar KenLM (una vez, en el nodo de login)

Necesita `cmake`, un compilador de C++ y Boost (`program_options`,
`system`, `thread`), más zlib/bzip2/xz para leer comprimidos.

```bash
cmake --version; g++ --version; ls /usr/include/boost/version.hpp
cd ~ && git clone https://github.com/kpu/kenlm.git
cd kenlm && mkdir -p build && cd build
cmake .. -DKENLM_MAX_ORDER=6 && make -j 4
ls bin/lmplz bin/build_binary bin/query
```

Si falta Boost o `cmake` y no hay permisos de administrador, con conda
(sin tocar el venv):

```bash
conda create -y -n kenlm -c conda-forge cmake boost-cpp eigen zlib bzip2 xz cxx-compiler make
conda activate kenlm
cd ~/kenlm/build && cmake .. -DKENLM_MAX_ORDER=6 && make -j 4
```

Módulo de Python para puntuar (en el venv del paquete; compila lo suyo):

```bash
source ~/venvs/avlizador/bin/activate
pip install https://github.com/kpu/kenlm/archive/master.zip
python -c "import kenlm; print('ok')"
```

### 2. Prueba pequeña (500 MB del XML, ~65 M de tokens)

```bash
cd ~/scrapeo/AVLizador && git pull
cd pipeline/08_traduccio_corpus/macocu/kenlm
LIMIT_MB=500 NOM=prova sbatch --cpus-per-task=4 --mem=12G entrena_kenlm.sh
```

Mirar `<jobid>_kenlm.out` y probar el modelo:

```bash
cd ~/scrapeo/AVLizador
python pipeline/08_traduccio_corpus/macocu/kenlm/prova_kenlm.py dades/macocu/kenlm/prova_o5.binary \
  "Una altra vegada hem guanyat. | Un altre colp hem guanyat. | Un altre cop hem guanyat." \
  "Hem comprat nous i ametlles. | Hem comprat anous i ametlles."
```

### 3. Modelo entero

Antes, espacio en disco: el texto (~11 GB), los temporales de `lmplz`
(varias veces el texto) y el ARPA (decenas de GB) van en
`dades/macocu/kenlm/`.

```bash
df -h ~/scrapeo/AVLizador/dades
sinfo -o "%n %C %m %e"            # CPU libres (A/I/O/T) y memoria libre
sbatch entrena_kenlm.sh            # orden 5, poda de singletons, 8 CPU, 32 GB
# si no hay tanta memoria libre:
sbatch --mem=20G entrena_kenlm.sh
```

`lmplz` usa el 70 % de la memoria del job (`-S`) y lo que no cabe lo
ordena en disco (`-T`): con menos memoria va más lento, pero acaba. La
**poda** (`--prune 0 1 1 1 1`) quita los n-gramas de 2 a 5 palabras que
salen una sola vez: sin ella el modelo de 2.000 M de tokens no cabría.
`build_binary trie -q 8 -b 8` lo deja en un fichero mucho más pequeño que
el ARPA, que se puede borrar al final.

Opciones: `ORDRE=4` (más pequeño y rápido), `PODA=""` (sin poda; solo
para la prueba pequeña), `MEM_LMPLZ=16G`.

### 4. Traer el modelo

```powershell
scp nmartin@abaco:scrapeo/AVLizador/dades/macocu/kenlm/macocu_tot_o5.binary dades/macocu/kenlm/
```

## Siguiente (cuando esté el modelo)

Medirlo como a FLOR: las frases candidatas de los homógrafos v1 (253) y
v2 (160) y del manual (458), con el mismo `Criteri` (margen, catalana por
defecto), más tiempo y memoria en CPU (FLOR: 1,4 GB). Si prefiere el
catalán como se espera, la segunda prueba es añadir valenciano (frases de
GD alto de MaCoCu, AVL, BOE val, la traducción de `catala_pur.jsonl`).
