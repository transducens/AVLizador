#!/bin/bash
# baseline_llm_cat_val.sh -- Job array de SLURM (31/10/2026): baseline cat->val
# de LLM generalistes TAL QUAL (instrucció mínima, vore baseline_cat_val.py)
# en el benchmark manual mescla (458). Cada tasca de l'array avalua UN model
# amb el seu propi Ollama en UNA GPU; com a molt 2 tasques alhora (%2) per a
# no acaparar Abaco.
#
# Només funciona amb el CLON del repo (~/scrapeo/AVLizador, `git pull`) i amb
# el venv del paquet (per defecte ~/venvs/avlizador, `pip install -e ".[ml,avaluacio]"`).
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/baseline_llm):
#   sbatch baseline_llm_cat_val.sh                # tots els models
#   sbatch --array=0 baseline_llm_cat_val.sh      # només un (índex de MODELS)
#   LIMIT=10 sbatch --array=0 baseline_llm_cat_val.sh   # prova ràpida amb 10 frases
# Resultats: resultats/ (un JSON per model, en git) i logs/ (Ollama i eixida).

#SBATCH --job-name=baseline-llm
#SBATCH --output=logs/%A_%a_baseline_llm.out
#SBATCH --error=logs/%A_%a_baseline_llm.err
#SBATCH --array=0-7%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00

set -euo pipefail

# Tots caben en una GPU de 11 GB en Q4 (els de 14B, justos).
MODELS=(
    llama3.1:8b
    qwen2.5:7b
    qwen2.5:14b
    qwen3:8b
    qwen3:14b
    gemma3:12b
    gemma4:12b
    hdnh2006/salamandra-7b-instruct
)
MODEL="${MODELS[${SLURM_ARRAY_TASK_ID:-0}]}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
LOGS="$SCRIPT_DIR/logs"
mkdir -p "$LOGS"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Model: $MODEL (tasca ${SLURM_ARRAY_TASK_ID:-0}) en $(hostname)"

# La GPU la tria SLURM (--gres=gpu:1); el clúster no aïlla per cgroups, així
# que la fixem explícitament i no seguim si SLURM no n'ha assignada cap.
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU (CUDA_VISIBLE_DEVICES buit)." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8

# Ollama propi d'esta tasca, en un port propi (dos tasques poden caure en el
# mateix node). Vulkan desactivat: no respecta CUDA_VISIBLE_DEVICES.
PORT=$((11500 + ${SLURM_ARRAY_TASK_ID:-0}))
export OLLAMA_HOST="127.0.0.1:$PORT"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
export OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 OLLAMA_SCHED_SPREAD=false
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

ollama pull "$MODEL"

cd "$ARREL_REPO"
python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix \
    --sistema "ollama:$MODEL" --ollama-url "http://$OLLAMA_HOST" ${LIMIT:+--limit "$LIMIT"}
