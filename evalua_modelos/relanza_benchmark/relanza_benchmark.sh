#!/bin/bash
# relanza_benchmark.sh — Relanza el benchmark de 60 frases sobre los 3
# modelos de Ollama en paralelo (uno por GPU), para confirmar el efecto de
# los últimos arreglos al prompt compartido (SYSTEM_PROMPT_BASE en
# evalua_models.py):
#   - demostratius eixe/eixa/eixos/eixes -> aqueix/aqueixa/aqueixos/aqueixes
#     (antes no se convertían en absoluto; el intento inicial los mapeaba
#     mal a aquest/aquesta -- eixe es demostratiu de SEGON grau, aqueix és
#     el seu equivalent oriental, no aquest -- ya corregido también en
#     benchmark_corpus.json RC021/RC047, que tenían el mismo error en el
#     gold)
#   - elisió amb "h" muda (de hisenda -> d'hisenda)
#   - tic "en"->"a" en preposicions no coberto per cap regla
#
# Modelos:
#   GPU 0: qwen2.5:14b   (referencia ya conocida, recalculada con el prompt nuevo)
#   GPU 1: gemma3:12b    (idem)
#   GPU 2: gemma4:12b    (nuevo, publicado abril 2026 -- primera vez que se prueba aquí)
#
# Mismo patrón de aislamiento de GPU + Ollama que el resto de scripts del
# proyecto (generar_muestra_comparativa.sh, comparar_salamandraTA_gemma.sh):
# SLURM en este nodo ("abaco") no aísla GPUs por cgroups, así que se hace a
# mano con CUDA_VISIBLE_DEVICES por instancia, y se desactiva Vulkan en
# Ollama (bug conocido: github.com/ollama/ollama/issues/16508 -- Vulkan no
# respeta CUDA_VISIBLE_DEVICES).
#
# Lanzarlo:
#   cd evalua_modelos/relanza_benchmark
#   sbatch relanza_benchmark.sh

#SBATCH --job-name=relanza-benchmark
#SBATCH --output=%j_relanza.out
#SBATCH --error=%j_relanza.err
#SBATCH --gres=gpu:3
#SBATCH --cpus-per-task=12
#SBATCH --mem=48G
#SBATCH --time=01:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si tu clúster lo exige
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si tu clúster lo exige

set -euo pipefail

QWEN="qwen2.5:14b"
GEMMA3="gemma3:12b"
GEMMA4="gemma4:12b"

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo -- ${BASH_SOURCE[0]} apuntaria ahí, no al projecte real.
# $SLURM_SUBMIT_DIR sí és fiable (mateix arreglo ja usat a la resta
# d'scripts d'este projecte).
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
EVALUA_DIR="$(dirname "$SCRIPT_DIR")"           # evalua_modelos/
BENCHMARK="$EVALUA_DIR/benchmark_corpus.json"
LOGS_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOGS_DIR"

export CUDA_VISIBLE_DEVICES="0,1,2"
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

echo "Esperando a que las 3 instancias de Ollama respondan..."
for PUERTO in 11434 11435 11436; do
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

fallo_pull=0
wait "$pid_pull_qwen" || { echo "AVISO: falló la descarga de $QWEN (ver $LOGS_DIR/pull_qwen.log)"; fallo_pull=1; }
wait "$pid_pull_gemma3" || { echo "AVISO: falló la descarga de $GEMMA3 (ver $LOGS_DIR/pull_gemma3.log)"; fallo_pull=1; }
wait "$pid_pull_gemma4" || { echo "AVISO: falló la descarga de $GEMMA4 (ver $LOGS_DIR/pull_gemma4.log)"; fallo_pull=1; }
if [ "$fallo_pull" -ne 0 ]; then
    echo "Alguna descarga falló -- revisa los logs de arriba antes de seguir."
fi
echo "Descargas terminadas."

cd "$EVALUA_DIR"
echo "Lanzando los 3 benchmarks (60 frases cada uno, prompt ya corregido)..."

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

echo "Esperando a que terminen los 3..."
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
