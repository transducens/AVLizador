#!/bin/bash
# lematitza_text.sh -- Job de SLURM NOMÉS CPU (12/11/2026): passa a lemes el
# text d'entrenament del KenLM valencià (vore lematitza_text.py) per a
# entrenar després un KenLM de lemes amb entrena_kenlm.sh.
#
# Llançar-ho (des d'esta carpeta; normalment ho fa
# pipeline/03_seleccio_de_model/model_llengua/prova_lemes.sh):
#   sbatch lematitza_text.sh
#   ENTRADA=dades/macocu/kenlm/valencia_net_dogv.txt EIXIDA=dades/macocu/kenlm/valencia_net_dogv_lemes.txt sbatch lematitza_text.sh
#   LIMIT=20000 sbatch --time=00:30:00 lematitza_text.sh     # prova
# Variables: ENTRADA, EIXIDA (relatius a l'arrel del repo), LIMIT.

#SBATCH --job-name=lemes
#SBATCH --output=%j_lematitza.out
#SBATCH --error=%j_lematitza.err
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=06:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, memòria: ${SLURM_MEM_PER_NODE:-?} MB, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

cd "$ARREL_REPO"
ENTRADA="${ENTRADA:-dades/macocu/kenlm/valencia_net_dogv.txt}"
EIXIDA="${EIXIDA:-dades/macocu/kenlm/valencia_net_dogv_lemes.txt}"
[[ -s "$ENTRADA" ]] || { echo "No trobe $ENTRADA" >&2; exit 1; }
OPC=()
[[ -n "${LIMIT:-}" ]] && OPC+=(--limit "$LIMIT")
python -u pipeline/08_traduccio_corpus/macocu/kenlm/lematitza_text.py "$ENTRADA" --eixida "$EIXIDA" \
    --processos "${SLURM_CPUS_PER_TASK:-4}" ${OPC[@]+"${OPC[@]}"}
wc -l "$ENTRADA" "$EIXIDA"
