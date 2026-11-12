#!/bin/bash
# filtra_macocu.sh -- Job de SLURM NOMÉS CPU (06/11/2026): els dos passos de
# filtra_macocu.py sobre MaCoCu-ca (vore README.es.md d'esta carpeta).
#   1. `extreu` (un nucli, ~1 h): si ja hi ha candidates.jsonl, se salta.
#   2. `gd` (spaCy, un procés per nucli menys un): reprenible; si el job
#      s'acaba pel temps, tornar a llançar-lo continua on ho va deixar.
#
# Abans (una vegada, al node de login, des de ~/scrapeo/AVLizador):
#   git fetch && git checkout macocu && git pull
#   mkdir -p dades/macocu && cd dades/macocu
#   wget https://www.clarin.si/repository/xmlui/bitstream/handle/11356/1837/MaCoCu-ca-1.0.xml.zip
#   md5sum MaCoCu-ca-1.0.xml.zip    # ee39dfa0d626432ae5c44aa9071908bb
# No cal descomprimir-lo: el script el llig directament del .zip.
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/catala):
#   sbatch filtra_macocu.sh                      # totes les candidates
#   FRACCIO=0.2 sbatch filtra_macocu.sh          # mostra del 20 %
# Resultats: ~/scrapeo/AVLizador/dades/macocu/catala_pur.jsonl (+ estadistiques_*.json)

#SBATCH --job-name=macocu-gd
#SBATCH --output=%j_macocu.out
#SBATCH --error=%j_macocu.err
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=24:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8
# Un fil per procés: el paral·lelisme el fan els processos de `gd`.
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCH_NUM_THREADS=1

CPUS="${SLURM_CPUS_PER_TASK:-8}"
PROCESSOS=$(( CPUS > 1 ? CPUS - 1 : 1 ))
FRACCIO="${FRACCIO:-1.0}"
SCRIPT="$ARREL_REPO/pipeline/08_traduccio_corpus/macocu/catala/filtra_macocu.py"
cd "$ARREL_REPO"

if [[ ! -s dades/macocu/candidates.jsonl ]]; then
    echo "=== 1. extreu ==="
    T0=$(date +%s)
    python -u "$SCRIPT" extreu
    echo "Temps extreu: $(( $(date +%s) - T0 )) s"
else
    echo "=== 1. extreu: ja fet ($(wc -l < dades/macocu/candidates.jsonl) candidates) ==="
fi

echo "=== 2. gd ($PROCESSOS processos, fraccio $FRACCIO) ==="
T0=$(date +%s)
python -u "$SCRIPT" gd --processos "$PROCESSOS" --fraccio "$FRACCIO"
echo "Temps gd: $(( $(date +%s) - T0 )) s"
