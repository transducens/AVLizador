#!/bin/bash
# generar_muestra_comparativa.sh — Genera la MISMA muestra de N frases (mismo
# --seed) con los 3 modelos viables en paralelo, uno por GPU, para comparar
# cuál traduce mejor en un caso de uso REAL (frases completas del corpus,
# no solo las 60 del benchmark) antes de decidir con cuál lanzar la
# generación completa.
#
# Modelos comparados -- los 3 que salieron viables en
# 03_seleccion_de_modelo/comparativa_salamandraTA_gemma/ (SalamandraTA descartado
# del todo, ver final/metodologia_y_resultados.md sección 10):
#   GPU 0: qwen2.5:14b                      (el actual, mejor en el benchmark)
#   GPU 1: gemma3:12b                       (casi empatado en el benchmark, más barato)
#   GPU 2: hdnh2006/salamandra-7b-instruct  (el más flojo de los 3, para confirmarlo aquí también)
#
# El MISMO --seed en los 3 (por defecto 42, el de genera_corpus_sintetico.py)
# asegura que --sample coge exactamente las mismas frases en los 3 --
# si no, estarías comparando peras con manzanas.
#
# Lanzarlo (500 frases por defecto):
#   cd 04_corpus_sintetico/slurm
#   sbatch generar_muestra_comparativa.sh
#
# Con otro tamaño de muestra (p.ej. 100 para algo más rápido):
#   sbatch generar_muestra_comparativa.sh 100

#SBATCH --job-name=muestra-comparativa
#SBATCH --output=%j_muestra.out
#SBATCH --error=%j_muestra.err
#SBATCH --gres=gpu:3
#SBATCH --cpus-per-task=12
#SBATCH --mem=48G
#SBATCH --time=04:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si tu clúster lo exige
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si tu clúster lo exige

set -euo pipefail

QWEN="qwen2.5:14b"
GEMMA="gemma3:12b"
SALAMANDRA="hdnh2006/salamandra-7b-instruct"
MUESTRA="${1:-500}"   # tamaño de la muestra; pásalo como argumento a sbatch si quieres otro
SEED=42                # el mismo para los 3 -- misma muestra aleatoria exacta

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo -- ${BASH_SOURCE[0]} apuntaria ahí, no al projecte real.
# $SLURM_SUBMIT_DIR sí és fiable (mateix arreglo ja usat a generar_corpus_paralelo.sh).
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
SINTETICOS_DIR="$(dirname "$SCRIPT_DIR")"

# El aislamiento de GPU por cgroups de SLURM no está activo en "abaco" --
# se restringe a mano a las 3 GPUs físicas 0-2, y se desactiva Vulkan en
# Ollama (bug conocido: github.com/ollama/ollama/issues/16508 -- Vulkan no
# respeta CUDA_VISIBLE_DEVICES) para que cada instancia se quede en su GPU.
export CUDA_VISIBLE_DEVICES="0,1,2"
echo "Restringiendo el job a las GPUs físicas: $CUDA_VISIBLE_DEVICES"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

OUT_DIR="$SINTETICOS_DIR/generado/muestra_comparativa_$(date +%Y%m%d_%H%M)"
LOGS_DIR="$OUT_DIR/logs"
mkdir -p "$LOGS_DIR"
echo "Salida en: $OUT_DIR"

PIDS_SERVIDORS=()
PIDS_GENERACION=()
limpiar() {
    echo "Deteniendo procesos..."
    for pid in "${PIDS_GENERACION[@]:-}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS_SERVIDORS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap limpiar EXIT

echo "[GPU0] Arrancando Ollama para $QWEN (puerto 11434)..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11434" ollama serve > "$LOGS_DIR/ollama_gpu0.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU1] Arrancando Ollama para $GEMMA (puerto 11435)..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:11435" ollama serve > "$LOGS_DIR/ollama_gpu1.log" 2>&1 &
PIDS_SERVIDORS+=($!)

echo "[GPU2] Arrancando Ollama para $SALAMANDRA (puerto 11436)..."
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
OLLAMA_HOST="127.0.0.1:11435" ollama pull "$GEMMA" > "$LOGS_DIR/pull_gemma.log" 2>&1 &
pid_pull_gemma=$!
OLLAMA_HOST="127.0.0.1:11436" ollama pull "$SALAMANDRA" > "$LOGS_DIR/pull_salamandra.log" 2>&1 &
pid_pull_salamandra=$!

fallo_pull=0
wait "$pid_pull_qwen" || { echo "AVISO: falló la descarga de $QWEN"; fallo_pull=1; }
wait "$pid_pull_gemma" || { echo "AVISO: falló la descarga de $GEMMA"; fallo_pull=1; }
wait "$pid_pull_salamandra" || { echo "AVISO: falló la descarga de $SALAMANDRA"; fallo_pull=1; }
if [ "$fallo_pull" -ne 0 ]; then
    echo "Alguna descarga falló -- revisa los logs de arriba antes de seguir."
fi

echo ""
echo "Generando muestra de $MUESTRA frases (seed=$SEED, misma muestra para los 3) en paralelo..."
cd "$SINTETICOS_DIR"

# --output distinto para cada uno: si no, los 3 escribirían al mismo
# fichero por defecto (corpus_sintetic_val_cat.jsonl) y se pisarían entre
# sí al correr en paralelo.
python3 genera_corpus_sintetico.py \
    --model "$QWEN" --ollama-url "http://127.0.0.1:11434" --ollama-timeout 300 \
    --sample "$MUESTRA" --seed "$SEED" \
    --output "$OUT_DIR/corpus_qwen.jsonl" \
    > "$LOGS_DIR/generar_qwen.log" 2>&1 &
PIDS_GENERACION+=($!)

python3 genera_corpus_sintetico.py \
    --model "$GEMMA" --ollama-url "http://127.0.0.1:11435" --ollama-timeout 300 \
    --sample "$MUESTRA" --seed "$SEED" \
    --output "$OUT_DIR/corpus_gemma.jsonl" \
    > "$LOGS_DIR/generar_gemma.log" 2>&1 &
PIDS_GENERACION+=($!)

python3 genera_corpus_sintetico.py \
    --model "$SALAMANDRA" --ollama-url "http://127.0.0.1:11436" --ollama-timeout 300 \
    --sample "$MUESTRA" --seed "$SEED" \
    --output "$OUT_DIR/corpus_salamandra.jsonl" \
    > "$LOGS_DIR/generar_salamandra.log" 2>&1 &
PIDS_GENERACION+=($!)

echo "Esperando a que terminen los 3 (mira $LOGS_DIR/generar_*.log para ver el progreso en vivo)..."
estado=0
for pid in "${PIDS_GENERACION[@]}"; do
    wait "$pid" || estado=1
done

if [ "$estado" -ne 0 ]; then
    echo "AVISO: al menos una generación terminó con error -- revisa los logs de $LOGS_DIR/."
fi

echo ""
echo "Hecho. Salida en $OUT_DIR/:"
echo "  corpus_qwen.jsonl, corpus_gemma.jsonl, corpus_salamandra.jsonl"
echo ""
echo "NOTA: informe_generacio.txt y generacio.log dentro de 04_corpus_sintetico/"
echo "son ficheros COMPARTIDOS por los 3 procesos (limitación ya existente del"
echo "script, la misma que afecta a --num-shards) -- se pisan entre sí, no te"
echo "fíes de ellos para comparar. Usa los logs de $LOGS_DIR/generar_*.log"
echo "(cada uno con su propio resumen final) o compara directamente los .jsonl."
