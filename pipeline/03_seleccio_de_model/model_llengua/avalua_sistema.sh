#!/bin/bash
# avalua_sistema.sh -- Job de SLURM NOMÉS CPU (12/11/2026): el sistema tal
# com el fa servir el paquet (`avlizador avalua`), amb FLOR, amb KenLM + el
# classificador de "cop" i el motor sol, en els benchmarks de referència.
# És la foto de "com va el sistema" (els experiments van per
# compara_models.sh).
#
# Llançar-ho (des d'esta carpeta; normalment ho fa prova_lemes.sh):
#   sbatch avalua_sistema.sh
#   MODELS="kenlm" BENCHMARKS="homografs homografs_v2 manual" sbatch avalua_sistema.sh
# Variables: MODELS ("flor kenlm"), BENCHMARKS (homògrafs v1 i v2, manual,
# 151, BOE estricte, gplsi), EIXIDA (resultats/avalua_sistema_<data>),
# AVLIZADOR_KENLM_DIR (dades/macocu/kenlm).

#SBATCH --job-name=avalua-sis
#SBATCH --output=%j_avalua_sistema.out
#SBATCH --error=%j_avalua_sistema.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=16000M
#SBATCH --time=08:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, memòria: ${SLURM_MEM_PER_NODE:-?} MB, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8 HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error
export TORCH_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"

cd "$ARREL_REPO"
export AVLIZADOR_KENLM_DIR="${AVLIZADOR_KENLM_DIR:-$ARREL_REPO/dades/macocu/kenlm}"
read -r -a M <<< "${MODELS:-flor kenlm}"
read -r -a B <<< "${BENCHMARKS:-homografs homografs_v2 manual 151 boe_estricte gplsi}"
EIXIDA="${EIXIDA:-pipeline/03_seleccio_de_model/resultats/avalua_sistema_$(date +%Y%m%d_%H%M)}"
echo "Models: ${M[*]}; benchmarks: ${B[*]}; KenLM: $AVLIZADOR_KENLM_DIR -> $EIXIDA"
avlizador avalua --motor --model "${M[@]}" --benchmarks "${B[@]}" --eixida "$EIXIDA"
