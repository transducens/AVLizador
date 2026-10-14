#!/bin/bash
# benchmark_integrat_posfiltre.sh — Job de SLURM d'1 sola GPU: executa
# `benchmark_integrat.py` amb el filtre POS de spaCy ACTIVAT (per defecte,
# 07/10/2026) sobre el benchmark complet de 150 frases, amb el model que
# li passes (per defecte qwen3:8b, vore conversa 07/10/2026).
#
# A diferencia de compara_postprocessat.sh, este tambe necessita
# l'estructura completa del repo (traductor/, 02_regles_dialectals/,
# 03_seleccio_de_model/) -- mateix avis que benchmark_integrat_multimodel.sh.
#
# Lanzarlo (des del node de login d'Abaco, dins del paquet complet pujat):
#   cd 08_traduccio_corpus/postprocessat_llm/slurm
#   sbatch benchmark_integrat_posfiltre.sh                    # qwen3:8b, via C, benchmark complet
#   sbatch benchmark_integrat_posfiltre.sh qwen3:8b c 30      # nomes 30 frases, prova rapida
#   sbatch benchmark_integrat_posfiltre.sh qwen3:8b c "" --no-pos-filter
#                                                               # sense filtre, per comparar

#SBATCH --job-name=bench-posfiltre
#SBATCH --output=%j_posfiltre.out
#SBATCH --error=%j_posfiltre.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si el teu cluster ho exigix
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si el teu cluster ho exigix

set -euo pipefail

MODEL="${1:-qwen3:8b}"
VIA="${2:-c}"
LIMIT="${3:-}"
shift $(($# < 3 ? $# : 3)) || true
EXTRA_ARGS=("$@")   # p.ex. --no-pos-filter, si cal comparar

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
POSTPROC_DIR="$(dirname "$SCRIPT_DIR")"
export AVLIZADOR_ROOT="$POSTPROC_DIR"

export CUDA_VISIBLE_DEVICES="0"
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1

OLLAMA_PORT="${OLLAMA_PORT:-11434}"
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

echo "Instal·lant/comprovant spaCy + model de catala (ca_core_news_sm)..."
# Molts nodes Linux moderns (Debian/Ubuntu 12+, Python 3.12) bloquegen
# `pip install` fora d'un entorn virtual (PEP 668, "externally-managed-
# environment"). La variable PIP_BREAK_SYSTEM_PACKAGES=1 ho desactiva per
# a QUALSEVOL crida a pip en esta sessio -- calia una variable d'entorn i
# no nomes el flag `--break-system-packages` perque `spacy download`
# crida pip ell mateix per dins, sense exposar eixe flag.
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q spacy
python3 -m spacy download ca_core_news_sm -q || python3 -m pip install -q \
    https://github.com/explosion/spacy-models/releases/download/ca_core_news_sm-3.8.0/ca_core_news_sm-3.8.0-py3-none-any.whl

echo "Node: $(hostname) -- engegant Ollama en segon pla (port ${OLLAMA_PORT})..."
ollama serve &
OLLAMA_PID=$!
trap 'kill "$OLLAMA_PID" 2>/dev/null || true' EXIT

echo "Esperant que Ollama responga..."
for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 && break
    sleep 2
done

echo "Comprovant que $MODEL esta descarregat..."
ollama pull "$MODEL"

cd "$POSTPROC_DIR"
MODEL_SLUG="${MODEL//:/-}"
OUT_DIR="$POSTPROC_DIR/resultats_posfiltre_${MODEL_SLUG}_via${VIA}_$(date +%Y%m%d_%H%M)"
mkdir -p "$OUT_DIR"

LIMIT_ARGS=()
if [ -n "$LIMIT" ]; then
    LIMIT_ARGS=(--limit "$LIMIT")
fi

echo ""
echo "Executant benchmark_integrat.py amb filtre POS -- model=$MODEL via=$VIA..."
python3 benchmark_integrat.py \
    --via "$VIA" --model "$MODEL" --ollama-url "http://127.0.0.1:${OLLAMA_PORT}" --ollama-timeout 300 \
    --output "$OUT_DIR/resultats.json" "${LIMIT_ARGS[@]}" "${EXTRA_ARGS[@]}"

echo ""
echo "Fet. Resultats en $OUT_DIR/resultats.json"
