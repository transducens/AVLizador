#!/bin/bash
# benchmark_integrat_multimodel.sh — Job de SLURM que executa
# `benchmark_integrat.py` (motor de regles + postprocessat LLM, mesurat
# amb BLEU/chrF/exacte sobre el benchmark REAL de 150 frases) amb 3
# models en paral·lel (un per GPU), cadascun amb les 2 vies B i C.
# Pruebes puntuals, 06/10/2026 -- vore ../README.md per al contexte.
#
# Models (triats per l'usuari per a este baseline):
#   GPU 0: gemma4:12b
#   GPU 1: qwen3:8b
#   GPU 2: qwen3:14b
#
# Mateix patró d'aïllament de GPU + Ollama que la resta del projecte
# (generar_muestra_comparativa.sh, rellanca_benchmark.sh): SLURM en
# "abaco" no aïlla GPUs per cgroups, es restringix a mà amb
# CUDA_VISIBLE_DEVICES, i es desactiva Vulkan en Ollama (bug conegut:
# github.com/ollama/ollama/issues/16508 -- Vulkan no respecta
# CUDA_VISIBLE_DEVICES).
#
# IMPORTANT -- a diferència de compara_postprocessat.sh, este script SI
# necessita l'estructura completa del projecte (`traductor/`,
# `02_regles_dialectals/`, `03_seleccio_de_model/benchmark_corpus.json`)
# perque `benchmark_integrat.py` aplica el motor de regles de veres, no
# nomes llig un .json de mostra ja feta. Per aixo este script assumix que
# ~/scrapeo/ ja te una copia COMPLETA del repo (no nomes la carpeta
# postprocesado_llm com l'altre script) -- revisa els camins de dalt si
# la teua copia d'Abaco esta organitzada diferent.
#
# Lanzarlo (des del node de login d'Abaco, dins del repo complet):
#   cd 08_traduccio_corpus/postprocessat_llm/slurm
#   sbatch benchmark_integrat_multimodel.sh            # benchmark complet (150 frases)
#   sbatch benchmark_integrat_multimodel.sh 30         # nomes les primeres 30 (prova rapida)
#
# Les línies marcadas CAMBIA-ESTO depenen de la configuracio del teu
# cluster concret -- revisa-les abans de llançar-lo.

#SBATCH --job-name=bench-integrat
#SBATCH --output=%j_bench_integrat.out
#SBATCH --error=%j_bench_integrat.err
#SBATCH --gres=gpu:3
#SBATCH --cpus-per-task=12
#SBATCH --mem=48G
#SBATCH --time=04:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si el teu cluster ho exigix
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si el teu cluster ho exigix

set -euo pipefail

LIMIT="${1:-}"   # si es dona, nomes les primeres N frases del benchmark (per a proves rapides)

GEMMA4="gemma4:12b"
QWEN3_8B="qwen3:8b"
QWEN3_14B="qwen3:14b"

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
POSTPROC_DIR="$(dirname "$SCRIPT_DIR")"

export CUDA_VISIBLE_DEVICES="0,1,2"
echo "Restringint el job a les GPUs fisiques: $CUDA_VISIBLE_DEVICES"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

echo "Instal·lant/comprovant spaCy + model de catala (ca_core_news_sm) -- filtre POS, 07/10/2026..."
# Vore benchmark_integrat_posfiltre.sh per a l'explicacio completa de
# PIP_BREAK_SYSTEM_PACKAGES (PEP 668, "externally-managed-environment" en
# Linux moderns -- cal la variable, no nomes el flag, perque spacy
# download crida pip per dins sense exposar eixe flag).
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q spacy
python3 -m spacy download ca_core_news_sm -q || python3 -m pip install -q \
    https://github.com/explosion/spacy-models/releases/download/ca_core_news_sm-3.8.0/ca_core_news_sm-3.8.0-py3-none-any.whl

OUT_DIR="$POSTPROC_DIR/resultats_benchmark_integrat_$(date +%Y%m%d_%H%M)"
LOGS_DIR="$OUT_DIR/logs"
mkdir -p "$LOGS_DIR"
echo "Eixida en: $OUT_DIR"

PIDS_SERVIDORS=()
PIDS_BENCHMARK=()
limpiar() {
    echo "Aturant processos..."
    for pid in "${PIDS_BENCHMARK[@]:-}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS_SERVIDORS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap limpiar EXIT

echo "[GPU0] Engegant Ollama per a $GEMMA4 (port 11434)..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11434" ollama serve > "$LOGS_DIR/ollama_gpu0.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU1] Engegant Ollama per a $QWEN3_8B (port 11435)..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11435" ollama serve > "$LOGS_DIR/ollama_gpu1.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU2] Engegant Ollama per a $QWEN3_14B (port 11436)..."
CUDA_VISIBLE_DEVICES=2 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11436" ollama serve > "$LOGS_DIR/ollama_gpu2.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "Esperant que les 3 instancies d'Ollama responguen..."
for PUERTO in 11434 11435 11436; do
    for _ in $(seq 1 30); do
        curl -s "http://127.0.0.1:${PUERTO}/api/tags" >/dev/null 2>&1 && break
        sleep 2
    done
done

echo "Descarregant models en paral·lel (si no estaven ja en $OLLAMA_MODELS)..."
OLLAMA_HOST="127.0.0.1:11434" ollama pull "$GEMMA4" > "$LOGS_DIR/pull_gemma4.log" 2>&1 &
pid_pull_gemma4=$!
OLLAMA_HOST="127.0.0.1:11435" ollama pull "$QWEN3_8B" > "$LOGS_DIR/pull_qwen3_8b.log" 2>&1 &
pid_pull_qwen3_8b=$!
OLLAMA_HOST="127.0.0.1:11436" ollama pull "$QWEN3_14B" > "$LOGS_DIR/pull_qwen3_14b.log" 2>&1 &
pid_pull_qwen3_14b=$!

fallo_pull=0
wait "$pid_pull_gemma4" || { echo "AVISO: fallo la descarrega de $GEMMA4"; fallo_pull=1; }
wait "$pid_pull_qwen3_8b" || { echo "AVISO: fallo la descarrega de $QWEN3_8B"; fallo_pull=1; }
wait "$pid_pull_qwen3_14b" || { echo "AVISO: fallo la descarrega de $QWEN3_14B"; fallo_pull=1; }
if [ "$fallo_pull" -ne 0 ]; then
    echo "Alguna descarrega ha fallat -- revisa els logs de dalt abans de seguir."
fi

cd "$POSTPROC_DIR"
# benchmark_integrat.py i identifica_ambigues.py esperen, per defecte, que
# l'arrel del repo estiga 2 nivells amunt (estructura local amb carpetes
# numerades) -- en Abaco este fitxer viu dins d'una carpeta PLANA que ja
# conte traductor/, 02_regles_dialectals/ i 03_seleccio_de_model/
# directament, aixi que l'arrel real ES esta mateixa carpeta.
export AVLIZADOR_ROOT="$POSTPROC_DIR"
LIMIT_ARGS=()
if [ -n "$LIMIT" ]; then
    LIMIT_ARGS=(--limit "$LIMIT")
fi

# Per cada model: via B i via C SEQÜENCIALS (mateixa instancia d'Ollama,
# dos passades) pero els 3 MODELS en paral·lel entre ells (3 GPUs).
executa_model() {
    local model="$1" port="$2" slug="$3"
    for via in b c; do
        echo "[$slug] via $via..."
        python3 benchmark_integrat.py \
            --via "$via" --model "$model" --ollama-url "http://127.0.0.1:${port}" --ollama-timeout 300 \
            --output "$OUT_DIR/resultats_${slug}_via${via}.json" "${LIMIT_ARGS[@]}" \
            > "$LOGS_DIR/${slug}_via${via}.log" 2>&1
    done
}

executa_model "$GEMMA4" 11434 "gemma4-12b" &
PIDS_BENCHMARK+=($!)
executa_model "$QWEN3_8B" 11435 "qwen3-8b" &
PIDS_BENCHMARK+=($!)
executa_model "$QWEN3_14B" 11436 "qwen3-14b" &
PIDS_BENCHMARK+=($!)

echo "Esperant que acaben els 3 models (mira $LOGS_DIR/*_via*.log per a veure el progrés en viu)..."
estado=0
for pid in "${PIDS_BENCHMARK[@]}"; do
    wait "$pid" || estado=1
done
if [ "$estado" -ne 0 ]; then
    echo "AVISO: algun benchmark ha acabat amb error -- revisa $LOGS_DIR/."
fi

echo ""
echo "Fet. Resum de cada combinacio (ultimes linies de cada log):"
for log in "$LOGS_DIR"/*_via*.log; do
    echo ""
    echo "=== $(basename "$log") ==="
    grep -A 2 "^NOMES REGLES" "$log" || true
    grep -A 2 "^REGLES + POSTPROC" "$log" || true
done

echo ""
echo "Resultats complets (JSON per frase) en $OUT_DIR/resultats_*.json"
echo "Logs en $LOGS_DIR/"
