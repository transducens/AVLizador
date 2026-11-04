#!/bin/bash
# jutge_llm.sh -- Jutge LLM obert (GEMBA-ESA, només la traducció) sobre les
# traduccions cat->val del manual mescla, amb el seu propi Ollama (04/11/2026).
# Vore README.md i jutge_gemba.py.
#
# Els models fan 20-23 GB en Q4 i les GPU d'Abaco en tenen 11: es demanen 2
# GPU i Ollama hi reparteix les capes (el que no càpia, a CPU).
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm):
#   LIMIT=10 sbatch --array=0 jutge_llm.sh   # prova: 10 frases per sistema
#   sbatch --array=0 jutge_llm.sh            # Qwen 3.6 35B-A3B (català a la llista oficial de Qwen3)
#   sbatch --array=1 jutge_llm.sh            # Gemma 4 31B (el millor obert del WMT26)
#   PENSA=1 sbatch --array=0 jutge_llm.sh    # amb raonament en la fase 1 (molt més lent)
# Si el job s'acaba per temps, es torna a llançar igual: continua des de la
# memòria cau (resultats/<model>/cache.jsonl).

#SBATCH --job-name=jutge-llm
#SBATCH --output=logs/%A_%a_jutge_llm.out
#SBATCH --error=logs/%A_%a_jutge_llm.err
#SBATCH --array=0
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=12:00:00

set -euo pipefail

MODELS=(
    qwen3.6:35b-a3b
    gemma4:31b
)
MODEL="${MODELS[${SLURM_ARRAY_TASK_ID:-0}]}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
LOGS="$SCRIPT_DIR/logs"
mkdir -p "$LOGS"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Model: $MODEL (tasca ${SLURM_ARRAY_TASK_ID:-0}) en $(hostname)"

if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU (CUDA_VISIBLE_DEVICES buit)." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader || true

export PYTHONIOENCODING=utf-8
PORT=$((11600 + ${SLURM_ARRAY_TASK_ID:-0}))
export OLLAMA_HOST="127.0.0.1:$PORT"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
# Vulkan fora (no respecta CUDA_VISIBLE_DEVICES); SPREAD per a repartir el
# model entre les 2 GPU.
export OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 OLLAMA_SCHED_SPREAD=true
mkdir -p "$OLLAMA_MODELS"
NOM_LOG="${MODEL//[\/:]/-}"
ollama serve > "$LOGS/ollama_${NOM_LOG}_${SLURM_JOB_ID:-local}.log" 2>&1 &
PID_OLLAMA=$!
trap 'kill "$PID_OLLAMA" 2>/dev/null || true' EXIT

for _ in $(seq 60); do
    curl -s "http://$OLLAMA_HOST/api/tags" > /dev/null && break
    sleep 2
done
curl -s "http://$OLLAMA_HOST/api/tags" > /dev/null || { echo "ERROR: Ollama no arranca" >&2; exit 1; }
ollama --version
ollama pull "$MODEL"

cd "$SCRIPT_DIR"
python3 jutge_gemba.py puntua --model "$MODEL" --ollama-url "http://$OLLAMA_HOST" \
    ${LIMIT:+--limit "$LIMIT"} ${PENSA:+--pensa} \
    ../baseline_llm/resultats/*.json ../comet/entrades/*.json
# Quant ha ocupat cada GPU (per a saber si cal demanar-ne 3)
grep -iE "offload|layers|VRAM" "$LOGS/ollama_${NOM_LOG}_${SLURM_JOB_ID:-local}.log" | tail -5 || true
