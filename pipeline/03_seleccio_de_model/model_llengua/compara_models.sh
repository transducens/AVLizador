#!/bin/bash
# compara_models.sh -- Job de SLURM NOMÉS CPU (10/11/2026): compara FLOR,
# KenLM (català, valencià, valencià net, diferències) i fastText en la
# decisió de les paraules ambigües (vore compara_models.py).
#
# Necessita, en dades/macocu/: kenlm/{macocu_tot,macocu_30pc,valencia,valencia_net}_o5.binary
# i fasttext/autotune.bin; i en el venv, `kenlm` i `fasttext` (pip).
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/model_llengua):
#   sbatch compara_models.sh
#   sbatch --dependency=afterok:<job del KenLM valencià net> compara_models.sh
#   LIMIT=10 sbatch --time=00:30:00 compara_models.sh          # prova
#   MODELS="motor kenlm_val fasttext" sbatch compara_models.sh
# Variables: MODELS (tots), LIMIT (cap), EXTRA (més opcions de compara_models.py).

#SBATCH --job-name=compara-lm
#SBATCH --output=%j_compara_models.out
#SBATCH --error=%j_compara_models.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=16000M
#SBATCH --time=04:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, memòria: ${SLURM_MEM_PER_NODE:-?} MB, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8 HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error
CPUS="${SLURM_CPUS_PER_TASK:-4}"
# Tots els models en un sol fil de càlcul llevat de FLOR (--fils): el temps
# per frase és comparable i no es barallen per les CPU.
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

cd "$ARREL_REPO"
for f in kenlm/macocu_tot_o5.binary kenlm/macocu_30pc_o5.binary kenlm/valencia_o5.binary \
         kenlm/valencia_net_o5.binary fasttext/autotune.bin; do
    [[ -s "dades/macocu/$f" ]] || echo "AVÍS: falta dades/macocu/$f (el model que el necessita fallarà)" >&2
done

OPC=(--fils "$CPUS")
[[ -n "${MODELS:-}" ]] && read -r -a M <<< "$MODELS" && OPC+=(--models "${M[@]}")
[[ -n "${LIMIT:-}" ]] && OPC+=(--limit "$LIMIT")
# shellcheck disable=SC2086
python -u pipeline/03_seleccio_de_model/model_llengua/compara_models.py "${OPC[@]}" ${EXTRA:-}
