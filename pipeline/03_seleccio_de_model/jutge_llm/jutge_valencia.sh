#!/bin/bash
# jutge_valencia.sh -- Jutge LLM (Qwen 3.6) amb el prompt "valencia": veu
# l'original català i no penalitza les formes valencianes de l'AVL
# (24/11/2026). Vore jutge_gemba.py (docstring) i README.md.
#
# Tres conjunts, cadascun amb la seua referència i la seua carpeta:
#   manual (458)        referència, "sense traduir", gemma3:12b, AVLizador
#   homografs (249)     referència, AVLizador, motor sol
#   homografs_v2 (144)  referència, AVLizador, motor sol
# Les traduccions d'AVLizador (kenlm) i del motor sol es generen ací amb
# `avlizador avalua` (el codi de la branca que hi haja en Abaco), en
# entrades_valencia/; si ja hi són, no es tornen a generar.
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/jutge_llm):
#   LIMIT=10 sbatch jutge_valencia.sh    # prova: 10 frases per sistema i conjunt
#   sbatch jutge_valencia.sh             # tot (~2.200 textos, unes 4-5 h)
#   CONJUNTS="homografs_v2" sbatch jutge_valencia.sh   # només un conjunt
# Si s'acaba per temps, es torna a llançar igual: continua des de la memòria
# cau (resultats/valencia/<conjunt>/<model>/cache.jsonl).

#SBATCH --job-name=jutge-val
#SBATCH --output=logs/%j_jutge_valencia.out
#SBATCH --error=logs/%j_jutge_valencia.err
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=12:00:00

set -euo pipefail

MODEL="${MODEL:-qwen3.6:35b-a3b}"
CONJUNTS="${CONJUNTS:-manual homografs homografs_v2}"
VENV="${AVLIZADOR_VENV:-$HOME/venvs/avlizador}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
LOGS="$SCRIPT_DIR/logs"
ENTRADES="$SCRIPT_DIR/entrades_valencia"
BASELINE="$SCRIPT_DIR/../baseline_llm/resultats"
mkdir -p "$LOGS" "$ENTRADES"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Model: $MODEL; conjunts: $CONJUNTS; en $(hostname)"

# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8

# 1. Traduccions d'AVLizador i del motor sol (CPU; uns minuts)
cd "$ARREL_REPO"
if [[ ! -f "$ENTRADES/manual/avlizador.json" ]]; then
    TMP="$ENTRADES/avalua_manual"
    avlizador avalua --benchmarks manual --eixida "$TMP"
    mkdir -p "$ENTRADES/manual"
    cp "$(ls -t "$TMP"/kenlm_manual_2*.json | head -1)" "$ENTRADES/manual/avlizador.json"
fi
if [[ ! -f "$ENTRADES/homografs_v2/motor.json" ]]; then
    TMP="$ENTRADES/avalua_homografs"
    avlizador avalua --motor --benchmarks homografs homografs_v2 --eixida "$TMP"
    for b in homografs homografs_v2; do
        mkdir -p "$ENTRADES/$b"
        cp "$(ls -t "$TMP"/kenlm_${b}_2*.json | head -1)" "$ENTRADES/$b/avlizador.json"
        cp "$(ls -t "$TMP"/motor_${b}_2*.json | head -1)" "$ENTRADES/$b/motor.json"
    done
fi

# 2. Ollama propi en les 2 GPU (com jutge_llm.sh)
if [[ -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU (CUDA_VISIBLE_DEVICES buit)." >&2
    exit 1
fi
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader || true
PORT=$((11700 + ${SLURM_JOB_ID:-0} % 100))
export OLLAMA_HOST="127.0.0.1:$PORT"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
export OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 OLLAMA_SCHED_SPREAD=true
mkdir -p "$OLLAMA_MODELS"
NOM_LOG="${MODEL//[\/:]/-}"
ollama serve > "$LOGS/ollama_valencia_${NOM_LOG}_${SLURM_JOB_ID:-local}.log" 2>&1 &
PID_OLLAMA=$!
trap 'kill "$PID_OLLAMA" 2>/dev/null || true' EXIT
for _ in $(seq 60); do
    curl -s "http://$OLLAMA_HOST/api/tags" > /dev/null && break
    sleep 2
done
curl -s "http://$OLLAMA_HOST/api/tags" > /dev/null || { echo "ERROR: Ollama no arranca" >&2; exit 1; }
ollama --version
ollama pull "$MODEL"

# 3. El jutge, conjunt per conjunt
cd "$SCRIPT_DIR"
for c in $CONJUNTS; do
    case "$c" in
        manual) FITXERS=("$BASELINE/copia.json" "$BASELINE/ollama_gemma3-12b.json" "$ENTRADES/manual/avlizador.json") ;;
        homografs|homografs_v2) FITXERS=("$ENTRADES/$c/avlizador.json" "$ENTRADES/$c/motor.json") ;;
        *) echo "ERROR: conjunt desconegut: $c" >&2; exit 1 ;;
    esac
    echo "== $c =="
    python jutge_gemba.py puntua --prompt valencia --model "$MODEL" --ollama-url "http://$OLLAMA_HOST" \
        --eixida "resultats/valencia/$c" ${LIMIT:+--limit "$LIMIT"} ${PENSA:+--pensa} "${FITXERS[@]}"
done
grep -iE "offload|layers|VRAM" "$LOGS/ollama_valencia_${NOM_LOG}_${SLURM_JOB_ID:-local}.log" | tail -5 || true
