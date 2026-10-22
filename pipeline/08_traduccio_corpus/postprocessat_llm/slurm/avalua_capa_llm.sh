#!/bin/bash
# avalua_capa_llm.sh -- Job de SLURM (GPU) per a avaluar la capa de
# LLM de `traductor/llm/` (val->cat, mode verbal; 21/10/2026) sobre el
# benchmark de 151 i la mostra del BOE. La capa de cat->val es va retirar
# el mateix dia (avaluada aci: no canviava cap frase).
#
# FITXERS A PUJAR (estructura plana d'Abaco, vore CLAUDE.md):
#   scp -r traductor nmartin@abaco:~/scrapeo/postprocesado_llm/
#   scp pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/
#   scp pipeline/08_traduccio_corpus/postprocessat_llm/slurm/avalua_capa_llm.sh \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/slurm/
#   ssh nmartin@abaco "mkdir -p ~/scrapeo/postprocesado_llm/dades/boe/benchmarks"
#   scp dades/boe/benchmarks/benchmark_boe_mostra_2000.json \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/dades/boe/benchmarks/
#   (03_seleccio_de_model/evalua_models.py i benchmark_corpus.json ja hi són)
#
# Llançar-ho (des de ~/scrapeo/postprocesado_llm/slurm):
#   sbatch avalua_capa_llm.sh                 # qwen3:8b, totes dues direccions
#   sbatch avalua_capa_llm.sh qwen3:8b 50     # només les 50 primeres frases

#SBATCH --job-name=capa-llm
#SBATCH --output=%j_capa_llm.out
#SBATCH --error=%j_capa_llm.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00

set -euo pipefail

MODEL="${1:-qwen3:8b}"
LIMIT="${2:-}"

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
# Dos maneres de tindre el codi a Abaco:
#  - CLON DEL REPO (recomanat des del 21/10/2026): `git clone` + `git pull`;
#    este script viu a pipeline/08_traduccio_corpus/postprocessat_llm/slurm/
#    i les rutes són les del repo.
#  - ESTRUCTURA PLANA antiga (~/scrapeo/postprocesado_llm/, pujada a mà).
if ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
    unset AVLIZADOR_ROOT
    BASE_DIR="$ARREL_REPO"
    AVALUADOR="pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py"
    BENCH_151="pipeline/03_seleccio_de_model/benchmark_corpus.json"
    OUT_BASE="$ARREL_REPO/dades/abaco"
    echo "Mode repo git: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
else
    BASE_DIR="$(dirname "$SCRIPT_DIR")"
    export AVLIZADOR_ROOT="$BASE_DIR"
    AVALUADOR="avalua_capa_llm.py"
    BENCH_151="03_seleccio_de_model/benchmark_corpus.json"
    OUT_BASE="$BASE_DIR"
    echo "Mode estructura plana: $BASE_DIR"
fi
# El benchmark del BOE no està a git (dades/ s'ignora): cal pujar-lo a mà a
# dades/boe/benchmarks/ dins de BASE_DIR (o regenerar-lo amb
# pipeline/05_corpus_boe/construeix_boe_dialectal.py).
BENCH_BOE="dades/boe/benchmarks/benchmark_boe_mostra_2000.json"

export CUDA_VISIBLE_DEVICES="0"
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q spacy
python3 -m spacy download ca_core_news_sm -q || python3 -m pip install -q \
    https://github.com/explosion/spacy-models/releases/download/ca_core_news_sm-3.8.0/ca_core_news_sm-3.8.0-py3-none-any.whl

ollama serve &
OLLAMA_PID=$!
trap 'kill "$OLLAMA_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 && break
    sleep 2
done
ollama pull "$MODEL"

cd "$BASE_DIR"
OUT_DIR="$OUT_BASE/resultats_capa_llm_${MODEL//:/-}_$(date +%Y%m%d_%H%M)"
mkdir -p "$OUT_DIR"
LIMIT_ARGS=()
[ -n "$LIMIT" ] && LIMIT_ARGS=(--limit "$LIMIT")

for DIRECCIO in val-cat; do   # la capa cat-val es va retirar el 21/10/2026
    for BENCH in "$BENCH_151" "$BENCH_BOE"; do
        if [ ! -f "$BENCH" ]; then
            echo "AVÍS: no existix $BENCH en $BASE_DIR -- se salta"
            continue
        fi
        NOM="$(basename "$BENCH" .json)"
        echo ""
        echo "=== $DIRECCIO -- $NOM -- $MODEL ==="
        python3 "$AVALUADOR" --direccio "$DIRECCIO" --benchmark "$BENCH" \
            --model "$MODEL" --ollama-url "http://127.0.0.1:${OLLAMA_PORT}" --timeout 300 \
            --sortida "$OUT_DIR/${DIRECCIO}_${NOM}.json" "${LIMIT_ARGS[@]}"
    done
done
echo ""
echo "Fet. Resultats en $OUT_DIR"
