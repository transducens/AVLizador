#!/bin/bash
# comet.sh -- Puntua amb XCOMET-XL (1 GPU) les traduccions cat->val del
# manual mescla (458) que ja estan en git: el baseline (AVLizador 1.0.1,
# motor sol, sense traduir i 9 LLM, `../baseline_llm/resultats/`) i
# AVLizador 1.1.0 (`entrades/`). No tradueix res: només puntua.
#
# Abans, una sola vegada, en el login d'Abaco:
#   1. Acceptar les condicions de Unbabel/XCOMET-XL a huggingface.co.
#   2. ~/venvs/avlizador/bin/hf auth login   (token de lectura; vore README.md)
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/comet):
#   LIMIT=10 sbatch comet.sh     # prova ràpida: 10 frases per sistema
#   sbatch comet.sh              # tot
#   PRECISIO=fp32 sbatch comet.sh   # si fp16 dona problemes (cal GPU de 16 GB)
#   MODE=qe sbatch comet.sh      # sense referència (només entrada + traducció)
#   MODE=ref sbatch comet.sh     # sense origen (només traducció + referència)
# Resultats: resultats/ (un JSON per sistema + resum__*.md); baixar-los amb
# scp (vore README.md). Logs: logs/.
#
# Entorn: un venv a banda (~/venvs/comet). `unbabel-comet` fixa versions de
# llibreries que xoquen amb el venv del paquet, i el torch de PyPI per
# defecte no veu les GPU d'Abaco (driver CUDA 12.9; vore el job 2646 del
# LoRA): s'instal·la torch de l'índex cu128.

#SBATCH --job-name=xcomet
#SBATCH --output=logs/%j_xcomet.out
#SBATCH --error=logs/%j_xcomet.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

export PYTHONIOENCODING=utf-8
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
[[ -f "$HF_HOME/token" ]] || echo "AVÍS: no hi ha token de Hugging Face ($HF_HOME/token); XCOMET-XL és d'accés restringit." >&2

VENV="${VENV:-$HOME/venvs/comet}"
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu128}"
if [[ ! -x "$VENV/bin/python" ]]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -U pip
    "$VENV/bin/pip" install -q torch --index-url "$TORCH_INDEX"
    "$VENV/bin/pip" install -q unbabel-comet
fi
if ! "$VENV/bin/python" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    echo "torch no veu la GPU: es reinstal·la des de $TORCH_INDEX"
    "$VENV/bin/pip" install -q --force-reinstall torch --index-url "$TORCH_INDEX"
fi
"$VENV/bin/python" -c "import torch, comet; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), '| comet', comet.__version__)"
"$VENV/bin/python" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" \
    || { echo "ERROR: torch continua sense CUDA." >&2; exit 1; }

OPCIONS=(--precisio "${PRECISIO:-fp16}" --lot "${LOT:-8}")
[[ -n "${LIMIT:-}" ]] && OPCIONS+=(--limit "$LIMIT")
[[ -n "${QE:-}" ]] && OPCIONS+=(--mode qe)
[[ -n "${MODE:-}" ]] && OPCIONS+=(--mode "$MODE")

cd "$SCRIPT_DIR"
"$VENV/bin/python" puntua_comet.py "${OPCIONS[@]}" \
    ../baseline_llm/resultats/*.json entrades/*.json
