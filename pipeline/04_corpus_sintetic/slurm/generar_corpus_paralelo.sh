#!/bin/bash
# generar_corpus_paralelo.sh — Igual que generar_corpus.sh, pero reparte el
# corpus entre varias GPUs del clúster a la vez, en vez de traducirlo todo en
# fila con una sola. Cada GPU recibe ~1/N del corpus (repartido por hash del
# id de cada frase, sin solapes) con su propia instancia de Ollama. Al
# terminar, fusiona los N fragmentos en el fichero final.
#
# Por defecto usa 4 de las 8 GPUs de "abaco" (dejando las otras 4 libres para
# otros usuarios del mismo nodo). No hace falta tocar particiones para esto:
# "abaco" es un único nodo con 8 GPUs, así que pedir 4 en vez de 8 es
# simplemente pedir menos recursos dentro de la misma cola — SLURM no exige
# una partición distinta por reducir cuántas GPUs pides.
#
# Lanzarlo (4 GPUs, tal cual viene el fichero):
#   sbatch generar_corpus_paralelo.sh                   # corpus completo, repartido en 4
#   sbatch generar_corpus_paralelo.sh --sample 40000    # una muestra grande, repartida en 4
#
# Para usar OTRO número de GPUs, cambia A LA VEZ el número de
# #SBATCH --gres=gpu:N de aquí abajo (SLURM no admite variables ahí, pero se
# puede sobreescribir desde la línea de comandos) y la variable de entorno
# NUM_GPUS. Por ejemplo, para volver a las 8:
#   NUM_GPUS=8 sbatch --gres=gpu:8 --cpus-per-task=16 --mem=64G generar_corpus_paralelo.sh
#
# (--cpus-per-task/--mem no son obligatorios al cambiar NUM_GPUS, pero no
# tiene sentido reservar recursos para 8 procesos si solo vas a lanzar 4, ni
# al revés.)
#
# Los argumentos que le pases a `sbatch` DESPUÉS del nombre del fichero (no
# los --gres/--cpus-per-task/--mem, que van ANTES) llegan a cada uno de los
# procesos de traducción (nunca uses aquí --num-shards/--shard-id/--output:
# el script ya se encarga de eso).

#SBATCH --job-name=corpus-valcat-x4
#SBATCH --output=%j_corpus_paralelo.out
#SBATCH --error=%j_corpus_paralelo.err
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO si tu clúster lo exige
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si tu clúster lo exige

set -euo pipefail

NUM_GPUS="${NUM_GPUS:-4}"
# Modelo a usar para generar el corpus completo -- antes venía fijo a
# qwen2.5:14b en el pull y en el propio nombre del log; ahora es una
# variable (igual que NUM_GPUS) para poder generar con otro modelo, p.ej.:
#   MODEL=gemma4:12b sbatch generar_corpus_paralelo.sh
MODEL="${MODEL:-gemma4:12b}"
PUERTO_BASE=11434

# El nodo "abaco" tiene 8 GPUs, pero el aislamiento por cgroups de SLURM no
# parece estar activo aqui: con --gres=gpu:4 el job seguia viendo (y usando
# un poco de memoria de) las 8, no solo 4 -- confirmado con nvidia-smi (los
# PID de las 4 instancias de Ollama aparecian en las 8 GPUs a la vez, ninguna
# con el bloque grande de ~9GB del modelo). El CUDA_VISIBLE_DEVICES=$i por
# instancia (mas abajo) NO bastaba por si solo. Arreglo: restringir la
# visibilidad de TODO el job a las primeras $NUM_GPUS GPUs fisicas desde el
# principio, antes de lanzar ningun proceso -- asi ningun hijo puede ver ni
# tocar las demas, sea cual sea el motivo por el que el aislamiento de SLURM
# no se aplicaba.
GPUS_VISIBLES="$(seq -s, 0 $((NUM_GPUS - 1)))"
export CUDA_VISIBLE_DEVICES="$GPUS_VISIBLES"
echo "Restringiendo el job a las GPUs físicas: $CUDA_VISIBLE_DEVICES"

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo, aixi que ${BASH_SOURCE[0]} apunta ahi, NO a on tens el
# projecte de veritat -- calcular la ruta a partir d'eixe camp trenca tot
# ("Permission denied" en escriure als logs, "No such file" en trobar
# genera_corpus_sintetico.py). $SLURM_SUBMIT_DIR es la variable que SLURM
# ompli sempre amb la carpeta des d'on vas llançar `sbatch` -- eixa si es
# fiable. Fora de SLURM (prova manual amb bash generar_corpus_paralelo.sh)
# cau al metode antic com a reserva.
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
SINTETICOS_DIR="$(dirname "$SCRIPT_DIR")"

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: no se encuentra el comando 'ollama' en este nodo. Instálalo primero (ver README.md)." >&2
    exit 1
fi

PIDS_OLLAMA=()
PIDS_PYTHON=()

limpiar() {
    echo "Deteniendo procesos..."
    for pid in "${PIDS_PYTHON[@]:-}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${PIDS_OLLAMA[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap limpiar EXIT

# ── 1. Arranca la instancia 0 sola y descarga el modelo antes que nada ──────
# (evita que las N instancias intenten descargar el modelo a la vez sobre el
# mismo $OLLAMA_MODELS compartido la primera vez que se ejecuta esto)
#
# OLLAMA_SCHED_SPREAD=false: sin esto, Ollama puede repartir un mismo modelo
# entre varias GPUs visibles en vez de quedarse en la que le toca.
#
# OLLAMA_VULKAN=0 + GGML_VK_VISIBLE_DEVICES=-1: el motivo REAL por el que
# CUDA_VISIBLE_DEVICES no bastaba (confirmado con nvidia-smi: las 4 instancias
# aparecian repartidas por las 8 GPUs). Ollama >=0.30 detecta las GPUs tambien
# por Vulkan ademas de CUDA, y esa via de deteccion NO respeta
# CUDA_VISIBLE_DEVICES (bug conocido: github.com/ollama/ollama/issues/16508).
# Desactivar Vulkan del todo fuerza a usar solo la deteccion CUDA, que si
# respeta CUDA_VISIBLE_DEVICES.
echo "Arrancando Ollama en la GPU 0 para descargar el modelo primero..."
CUDA_VISIBLE_DEVICES=0 OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
    OLLAMA_HOST="127.0.0.1:${PUERTO_BASE}" ollama serve > "ollama_gpu0.log" 2>&1 &
PIDS_OLLAMA+=($!)

for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:${PUERTO_BASE}/api/tags" >/dev/null 2>&1 && break
    sleep 2
done

echo "Descargando $MODEL (solo la primera vez; las otras GPUs lo reusarán del disco)..."
echo "  Si este nodo no tiene salida a internet, descárgalo antes desde el nodo de acceso."
OLLAMA_HOST="127.0.0.1:${PUERTO_BASE}" ollama pull "$MODEL"

# ── 2. Arranca las GPUs restantes ────────────────────────────────────────────
echo "Arrancando las $((NUM_GPUS - 1)) GPUs restantes..."
for i in $(seq 1 $((NUM_GPUS - 1))); do
    PUERTO=$((PUERTO_BASE + i))
    CUDA_VISIBLE_DEVICES=$i OLLAMA_SCHED_SPREAD=false OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1 \
        OLLAMA_HOST="127.0.0.1:${PUERTO}" ollama serve > "ollama_gpu${i}.log" 2>&1 &
    PIDS_OLLAMA+=($!)
done

echo "Esperando a que las $NUM_GPUS instancias de Ollama respondan..."
for i in $(seq 0 $((NUM_GPUS - 1))); do
    PUERTO=$((PUERTO_BASE + i))
    for _ in $(seq 1 30); do
        curl -s "http://127.0.0.1:${PUERTO}/api/tags" >/dev/null 2>&1 && break
        sleep 2
    done
done

# Comprobación rápida de que cada instancia ve su propia GPU (no varias a la vez)
echo "Comprobando asignación de GPU por instancia (size_vram=0 en TODAS es señal de que algo va mal):"
for i in $(seq 0 $((NUM_GPUS - 1))); do
    PUERTO=$((PUERTO_BASE + i))
    echo "  GPU $i (puerto $PUERTO):"
    curl -s "http://127.0.0.1:${PUERTO}/api/ps" || true
done

# Comprobació extra amb nvidia-smi: confirma que NOMES es toquen les
# $NUM_GPUS GPU restringides ($CUDA_VISIBLE_DEVICES), no la resta del node.
# Queda al .out del job, no cal que ho revises tu a ma cada vegada.
echo ""
echo "Comprovació nvidia-smi (nomes hauria d'eixir activitat a GPU 0-$((NUM_GPUS - 1))):"
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv || true

# ── 3. Lanza los procesos de traducción en paralelo, uno por fragmento ─────
echo "Lanzando $NUM_GPUS procesos de traducción en paralelo..."
cd "$SINTETICOS_DIR"
for i in $(seq 0 $((NUM_GPUS - 1))); do
    PUERTO=$((PUERTO_BASE + i))
    python3 genera_corpus_sintetico.py \
        --model "$MODEL" \
        --ollama-url "http://127.0.0.1:${PUERTO}" \
        --num-shards "$NUM_GPUS" --shard-id "$i" \
        "$@" > "$SINTETICOS_DIR/traduccion_fragmento${i}.log" 2>&1 &
    PIDS_PYTHON+=($!)
done

echo "Esperando a que terminen los $NUM_GPUS fragmentos (mira traduccion_fragmentoN.log para ver el progreso de cada uno)..."
estado=0
for pid in "${PIDS_PYTHON[@]}"; do
    wait "$pid" || estado=1
done

# ── 4. Fusiona los fragmentos en el fichero final ───────────────────────────
echo "Fusionando los $NUM_GPUS fragmentos y regenerando la exportación limpia..."
python3 genera_corpus_sintetico.py --model "$MODEL" --merge-shards "$NUM_GPUS"

if [ "$estado" -ne 0 ]; then
    echo "AVISO: al menos un fragmento terminó con error — revisa traduccion_fragmentoN.log."
    echo "Puedes relanzar 'sbatch generar_corpus_paralelo.sh $*' tal cual: es reanudable, no repite nada ya hecho."
fi

echo "Hecho."
