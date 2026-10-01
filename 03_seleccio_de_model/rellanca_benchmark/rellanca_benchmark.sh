#!/bin/bash
# rellanca_benchmark.sh — Relanza el benchmark de 150 frases sobre 5 modelos de
# Ollama en paralelo (uno por GPU): los 3 ya conocidos + los 2 candidatos
# nuevos de la familia Qwen3.
#
# Modelos:
#   GPU 0: qwen2.5:14b   (referencia actual, campeona hasta ahora — BLEU 93,11)
#   GPU 1: gemma3:12b    (segunda mejor conocida)
#   GPU 2: gemma4:12b    (publicado abril 2026, ya confirmado funcionando
#                          tras el fix de "think: false")
#   GPU 3: qwen3:8b      (nuevo — generación más reciente que qwen2.5, más
#                          pequeño; ~4,6-5 GB en Q4, cabe de sobra)
#   GPU 4: qwen3:14b     (nuevo — mismo tamaño que la referencia actual mejor
#                          probada; ~8,3-9 GB en Q4, misma liga que
#                          qwen2.5:14b)
#
# NO se prueba qwen3.8 (27B, publicado 14/08/2026) en esta tanda: solo existe
# en un tamaño grande (~18 GB en Q4, necesitaría repartirse en 2 GPUs) y no
# hay variante pequeña todavía con la que probar barato antes de comprometer
# recursos — mejor esperar a ver si compensa antes de montar esa
# infraestructura.
#
# Mismo patrón de aislamiento de GPU + Ollama que el resto de scripts del
# proyecto (generar_muestra_comparativa.sh, comparar_salamandraTA_gemma.sh):
# SLURM en este nodo ("abaco") no aísla GPUs por cgroups, así que se hace a
# mano con CUDA_VISIBLE_DEVICES por instancia, y se desactiva Vulkan en
# Ollama (bug conocido: github.com/ollama/ollama/issues/16508 -- Vulkan no
# respeta CUDA_VISIBLE_DEVICES).
#
# Lanzarlo:
#   cd 03_seleccio_de_model/rellanca_benchmark
#   sbatch rellanca_benchmark.sh

#SBATCH --job-name=relanza-benchmark
#SBATCH --output=%j_relanza.out
#SBATCH --error=%j_relanza.err
#SBATCH --gres=gpu:5
#SBATCH --cpus-per-task=20
#SBATCH --mem=80G
#SBATCH --time=01:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si tu clúster lo exige
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si tu clúster lo exige

set -euo pipefail

QWEN="qwen2.5:14b"
GEMMA3="gemma3:12b"
GEMMA4="gemma4:12b"
QWEN3_8B="qwen3:8b"
QWEN3_14B="qwen3:14b"

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo -- ${BASH_SOURCE[0]} apuntaria ahí, no al projecte real.
# $SLURM_SUBMIT_DIR sí és fiable (mateix arreglo ja usat a la resta
# d'scripts d'este projecte).
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
EVALUA_DIR="$(dirname "$SCRIPT_DIR")"           # 03_seleccio_de_model/
BENCHMARK="$EVALUA_DIR/benchmark_corpus.json"
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

export CUDA_VISIBLE_DEVICES="0,1,2,3,4"
echo "Restringiendo el job a las GPUs físicas: $CUDA_VISIBLE_DEVICES"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

PIDS_SERVIDORS=()
PIDS_BENCHMARK=()
limpiar() {
    echo "Deteniendo procesos..."
    for pid in "${PIDS_BENCHMARK[@]:-}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS_SERVIDORS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap limpiar EXIT

echo "[GPU0] Arrancando Ollama para $QWEN (puerto 11434)..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11434" ollama serve > "$LOGS_DIR/ollama_gpu0.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU1] Arrancando Ollama para $GEMMA3 (puerto 11435)..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11435" ollama serve > "$LOGS_DIR/ollama_gpu1.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU2] Arrancando Ollama para $GEMMA4 (puerto 11436)..."
CUDA_VISIBLE_DEVICES=2 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11436" ollama serve > "$LOGS_DIR/ollama_gpu2.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU3] Arrancando Ollama para $QWEN3_8B (puerto 11437)..."
CUDA_VISIBLE_DEVICES=3 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11437" ollama serve > "$LOGS_DIR/ollama_gpu3.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU4] Arrancando Ollama para $QWEN3_14B (puerto 11438)..."
CUDA_VISIBLE_DEVICES=4 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11438" ollama serve > "$LOGS_DIR/ollama_gpu4.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "Esperando a que las 5 instancias de Ollama respondan..."
for PUERTO in 11434 11435 11436 11437 11438; do
    for _ in $(seq 1 30); do
        curl -s "http://127.0.0.1:${PUERTO}/api/tags" >/dev/null 2>&1 && break
        sleep 2
    done
done

echo "Descargando modelos en paralelo (si no estaban ya en $OLLAMA_MODELS)..."
OLLAMA_HOST="127.0.0.1:11434" ollama pull "$QWEN" > "$LOGS_DIR/pull_qwen.log" 2>&1 &
pid_pull_qwen=$!
OLLAMA_HOST="127.0.0.1:11435" ollama pull "$GEMMA3" > "$LOGS_DIR/pull_gemma3.log" 2>&1 &
pid_pull_gemma3=$!
OLLAMA_HOST="127.0.0.1:11436" ollama pull "$GEMMA4" > "$LOGS_DIR/pull_gemma4.log" 2>&1 &
pid_pull_gemma4=$!
OLLAMA_HOST="127.0.0.1:11437" ollama pull "$QWEN3_8B" > "$LOGS_DIR/pull_qwen3_8b.log" 2>&1 &
pid_pull_qwen3_8b=$!
OLLAMA_HOST="127.0.0.1:11438" ollama pull "$QWEN3_14B" > "$LOGS_DIR/pull_qwen3_14b.log" 2>&1 &
pid_pull_qwen3_14b=$!

fallo_pull=0
wait "$pid_pull_qwen" || { echo "AVISO: falló la descarga de $QWEN (ver $LOGS_DIR/pull_qwen.log)"; fallo_pull=1; }
wait "$pid_pull_gemma3" || { echo "AVISO: falló la descarga de $GEMMA3 (ver $LOGS_DIR/pull_gemma3.log)"; fallo_pull=1; }
wait "$pid_pull_gemma4" || { echo "AVISO: falló la descarga de $GEMMA4 (ver $LOGS_DIR/pull_gemma4.log)"; fallo_pull=1; }
wait "$pid_pull_qwen3_8b" || { echo "AVISO: falló la descarga de $QWEN3_8B (ver $LOGS_DIR/pull_qwen3_8b.log)"; fallo_pull=1; }
wait "$pid_pull_qwen3_14b" || { echo "AVISO: falló la descarga de $QWEN3_14B (ver $LOGS_DIR/pull_qwen3_14b.log)"; fallo_pull=1; }
if [ "$fallo_pull" -ne 0 ]; then
    echo "Alguna descarga falló -- revisa los logs de arriba antes de seguir."
fi
echo "Descargas terminadas."

cd "$EVALUA_DIR"
echo "Lanzando los 5 benchmarks (150 frases cada uno, prompt ya corregido)..."

python3 evalua_models.py --model ollama --ollama-model "$QWEN" \
    --ollama-url "http://127.0.0.1:11434" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_qwen.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$GEMMA3" \
    --ollama-url "http://127.0.0.1:11435" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_gemma3.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$GEMMA4" \
    --ollama-url "http://127.0.0.1:11436" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_gemma4.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$QWEN3_8B" \
    --ollama-url "http://127.0.0.1:11437" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_qwen3_8b.log" 2>&1 &
PIDS_BENCHMARK+=($!)

python3 evalua_models.py --model ollama --ollama-model "$QWEN3_14B" \
    --ollama-url "http://127.0.0.1:11438" --ollama-timeout 300 \
    --benchmark "$BENCHMARK" > "$LOGS_DIR/resultado_qwen3_14b.log" 2>&1 &
PIDS_BENCHMARK+=($!)

echo "Esperando a que terminen los 5..."
estado=0
for pid in "${PIDS_BENCHMARK[@]}"; do
    wait "$pid" || estado=1
done

if [ "$estado" -ne 0 ]; then
    echo "AVISO: algún benchmark terminó con error — revisa $LOGS_DIR/resultado_*.log."
fi

echo "Generando el informe comparativo final..."
python3 "$EVALUA_DIR/comparativa_salamandraTA_gemma/combina_resultats.py" \
    --resultats-dir "$EVALUA_DIR/resultats" \
    --minuts 60 \
    --salida "$SCRIPT_DIR/informe_comparatiu.txt" || true

if [ -f "$SCRIPT_DIR/informe_comparatiu.txt" ]; then
    echo ""
    cat "$SCRIPT_DIR/informe_comparatiu.txt"
fi

echo ""
echo "Hecho. Resultados individuales (JSON) en $EVALUA_DIR/resultats/,"
echo "logs en $LOGS_DIR/, informe combinado en $SCRIPT_DIR/informe_comparatiu.txt"
