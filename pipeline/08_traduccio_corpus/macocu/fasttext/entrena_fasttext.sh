#!/bin/bash
# entrena_fasttext.sh -- Job de SLURM NOMÉS CPU (10/11/2026): classificador
# fastText valencià/català amb MaCoCu-ca (vore README.es.md d'esta carpeta).
#   1. prepara_dades.py -> dades/macocu/fasttext/{train,valid,prova}.txt
#   2. fasttext supervised -> classificador.bin
#   3. test en valid.txt (precisió/cobertura per classe)
#   4. quantize -> classificador.ftz (pocs MB) + test
#   5. predict-prob dels parells de prova
#
# Abans (una vegada, al node de login): compilar fastText (vore el README):
#   cd ~ && git clone https://github.com/facebookresearch/fastText.git && cd fastText && make
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/fasttext):
#   sbatch entrena_fasttext.sh
#   AUTOTUNE=600 sbatch entrena_fasttext.sh      # busca hiperparàmetres 10 min en valid.txt
#   PREPARA="--min-marcadors 1 --gd-val 0.75" NOM=fluix sbatch entrena_fasttext.sh
# Variables: FASTTEXT (~/fastText/fasttext), NOM (classificador), PREPARA
# (opcions de prepara_dades.py), REINICIA (torna a preparar les dades),
# AUTOTUNE (segons; buit = hiperparàmetres fixos), DIM (50), EPOCH (10),
# LR (0.5), NGRAMS (2), MINN/MAXN (3/5: subparaules de 3 a 5 lletres).

#SBATCH --job-name=fasttext
#SBATCH --output=%j_fasttext.out
#SBATCH --error=%j_fasttext.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=8000M
#SBATCH --time=03:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, memòria: ${SLURM_MEM_PER_NODE:-?} MB, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8

FT="${FASTTEXT:-$HOME/fastText/fasttext}"
[[ -x "$FT" ]] || { echo "No trobe $FT: compila fastText abans (vore README)." >&2; exit 1; }

CPUS="${SLURM_CPUS_PER_TASK:-4}"
NOM="${NOM:-classificador}"
DIR_FT="$ARREL_REPO/dades/macocu/fasttext"
MODEL="$DIR_FT/$NOM"
cd "$ARREL_REPO"
T0=$(date +%s)

if [[ -n "${REINICIA:-}" || ! -s "$DIR_FT/train.txt" || ! -s "$DIR_FT/estadistiques.json" ]]; then
    echo "=== 1. prepara les dades ==="
    # shellcheck disable=SC2086
    python -u pipeline/08_traduccio_corpus/macocu/fasttext/prepara_dades.py ${PREPARA:-}
else
    echo "=== 1. dades ja preparades ($(wc -l < "$DIR_FT/train.txt") frases d'entrenament) ==="
fi
echo "Temps: $(( $(date +%s) - T0 )) s"

echo "=== 2. entrena ==="
if [[ -n "${AUTOTUNE:-}" ]]; then
    "$FT" supervised -input "$DIR_FT/train.txt" -output "$MODEL" -thread "$CPUS" \
        -autotune-validation "$DIR_FT/valid.txt" -autotune-duration "$AUTOTUNE" -verbose 2
else
    "$FT" supervised -input "$DIR_FT/train.txt" -output "$MODEL" -thread "$CPUS" \
        -dim "${DIM:-50}" -epoch "${EPOCH:-10}" -lr "${LR:-0.5}" -wordNgrams "${NGRAMS:-2}" \
        -minn "${MINN:-3}" -maxn "${MAXN:-5}" -minCount 2 -bucket 2000000 -loss softmax -verbose 2
fi
ls -lh "$MODEL.bin"
echo "Temps: $(( $(date +%s) - T0 )) s"

echo "=== 3. test (valid.txt) ==="
"$FT" test "$MODEL.bin" "$DIR_FT/valid.txt"
"$FT" test-label "$MODEL.bin" "$DIR_FT/valid.txt"

echo "=== 4. quantize (.ftz) ==="
"$FT" quantize -input "$DIR_FT/train.txt" -output "$MODEL" -qnorm -retrain -cutoff 300000 -thread "$CPUS"
ls -lh "$MODEL.ftz"
"$FT" test "$MODEL.ftz" "$DIR_FT/valid.txt"

echo "=== 5. parells de prova (probabilitat de cada classe) ==="
paste <("$FT" predict-prob "$MODEL.ftz" "$DIR_FT/prova.txt" 2) "$DIR_FT/prova.txt"

echo "Temps total: $(( $(date +%s) - T0 )) s"
