#!/bin/bash
# entrena_lora.sh -- Opció 3 de les proves del biaix de FLOR (02/11/2026):
# entrena un adaptador LoRA de FLOR-760M amb text valencià (1 GPU) i després
# puntua les paraules ambigües dels benchmarks amb el model adaptat (CPU).
#
# Abans (en local): `prepara_dades.py` genera `entrenament_valencia.txt`
# (no està en git: textos de l'AVL i del BOE). Pujar-lo a Abaco:
#   scp pipeline/03_seleccio_de_model/model_llengua/sesgo/entrenament_valencia.txt \
#       nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/model_llengua/sesgo/
# Llançar-ho (des d'esta carpeta del clon):
#   sbatch entrena_lora.sh
# Resultats: lora_valencia/ (l'adaptador) i resultats/lora.json; baixar-los
# amb scp per a `sesgo_flor.py compara` en local.
#
# Entrenar necessita torch amb CUDA: el venv del paquet (~/venvs/avlizador)
# té torch només CPU, així que l'entrenament usa un venv a banda
# (~/venvs/flor-gpu, es crea la primera vegada). La puntuació usa el venv
# del paquet (amb peft).

#SBATCH --job-name=lora-flor
#SBATCH --output=%j_lora_flor.out
#SBATCH --error=%j_lora_flor.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"
[[ -f "$SCRIPT_DIR/entrenament_valencia.txt" ]] || { echo "ERROR: falta entrenament_valencia.txt (scp)" >&2; exit 1; }

export PYTHONIOENCODING=utf-8
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

# 1) entrenament, amb torch CUDA
VENV_GPU="${VENV_GPU:-$HOME/venvs/flor-gpu}"
if [[ ! -x "$VENV_GPU/bin/python" ]]; then
    python3 -m venv "$VENV_GPU"
    "$VENV_GPU/bin/pip" install -q -U pip
    "$VENV_GPU/bin/pip" install -q torch "transformers>=4.45" "huggingface_hub<2.0" peft accelerate
fi
"$VENV_GPU/bin/python" -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
"$VENV_GPU/bin/python" "$SCRIPT_DIR/entrena_lora.py" \
    --dades "$SCRIPT_DIR/entrenament_valencia.txt" --eixida "$SCRIPT_DIR/lora_valencia"

# 2) puntuació amb el model adaptat, amb el venv del paquet (CPU)
VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -c "import peft" 2>/dev/null || pip install -q peft
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
cd "$ARREL_REPO"
python "$SCRIPT_DIR/sesgo_flor.py" puntua --adaptador "$SCRIPT_DIR/lora_valencia" \
    --eixida "$SCRIPT_DIR/resultats/lora.json"
