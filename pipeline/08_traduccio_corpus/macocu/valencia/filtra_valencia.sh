#!/bin/bash
# filtra_valencia.sh -- Job de SLURM NOMÉS CPU (09/11/2026): els dos passos de
# filtra_valencia.py sobre MaCoCu-ca (frases amb GD > 0,5; vore README.es.md
# d'esta carpeta).
#   1. `extreu` (un nucli, ~1 h): si ja hi ha candidates.jsonl, se salta.
#   2. `gd` (spaCy, un procés per nucli menys un): reprenible; si el job
#      s'acaba pel temps, tornar a llançar-lo continua on ho va deixar.
#
# Abans (una vegada, al node de login, des de ~/scrapeo/AVLizador):
#   git pull       (el corpus ja és en dades/macocu/, del filtre català)
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/valencia):
#   sbatch filtra_valencia.sh                      # GD > 0,5, almenys 1 marcador
#   MIN_MARCADORS=2 sbatch filtra_valencia.sh      # més exigent (cal REINICIA=1 si ja hi ha extreu)
# Resultats: ~/scrapeo/AVLizador/dades/macocu/valencia/valencia.jsonl (+ estadistiques_*.json)

#SBATCH --job-name=macocu-val
#SBATCH --output=%j_macocu_val.out
#SBATCH --error=%j_macocu_val.err
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
MIN_GD="${MIN_GD:-0.5}"
MIN_MARCADORS="${MIN_MARCADORS:-1}"
SCRIPT="$ARREL_REPO/pipeline/08_traduccio_corpus/macocu/valencia/filtra_valencia.py"
CANDIDATES="dades/macocu/valencia/candidates.jsonl"
OPCIONS=(--min-gd "$MIN_GD" --min-marcadors "$MIN_MARCADORS")
cd "$ARREL_REPO"

if [[ -n "${REINICIA:-}" || ! -s "$CANDIDATES" ]]; then
    echo "=== 1. extreu (GD > $MIN_GD, >= $MIN_MARCADORS marcadors) ==="
    T0=$(date +%s)
    python -u "$SCRIPT" extreu "${OPCIONS[@]}"
    echo "Temps extreu: $(( $(date +%s) - T0 )) s"
else
    echo "=== 1. extreu: ja fet ($(wc -l < "$CANDIDATES") candidates) ==="
fi

echo "=== 2. gd ($PROCESSOS processos) ==="
T0=$(date +%s)
EXTRA=()
[[ -n "${REINICIA:-}" ]] && EXTRA+=(--reinicia)
python -u "$SCRIPT" gd --processos "$PROCESSOS" "${OPCIONS[@]}" ${EXTRA[@]+"${EXTRA[@]}"}
echo "Temps gd: $(( $(date +%s) - T0 )) s"
