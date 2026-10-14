#!/bin/bash
# generar_corpus.sh — Job de SLURM que genera el corpus sintético completo:
# levanta Ollama y ejecuta genera_corpus_sintetico.py dentro del MISMO job,
# en un nodo con GPU. No necesitas estar conectado mientras corre.
#
# Lanzarlo:
#   sbatch generar_corpus.sh                     # corpus completo (46.315 frases)
#   sbatch generar_corpus.sh --sample 8000       # una muestra (recomendado antes de lanzar todo)
#   sbatch generar_corpus.sh --nomes-exporta      # solo regenerar la exportación limpia
#
# Cualquier argumento que le pases a `sbatch` después del nombre del fichero
# llega tal cual a genera_corpus_sintetico.py (mira el "$@" del final).
#
# Las líneas marcadas CAMBIA-ESTO dependen de la configuración de tu clúster
# concreto — revísalas con tu servicio de informática/HPC antes de lanzarlo.

#SBATCH --job-name=corpus-valcat
#SBATCH --output=%j_corpus.out
#SBATCH --error=%j_corpus.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=24:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO: descomenta y pon el nombre real si tu clúster lo exige (mira `sinfo`)
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO: descomenta si tu clúster exige --account

set -euo pipefail

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo, aixi que ${BASH_SOURCE[0]} apunta ahi, NO al projecte real.
# $SLURM_SUBMIT_DIR es la carpeta des d'on vas llançar `sbatch` -- eixa si
# es fiable. Fora de SLURM cau al metode antic com a reserva.
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
SINTETICOS_DIR="$(dirname "$SCRIPT_DIR")"

# El aislamiento de GPU por cgroups de SLURM no parece activo en "abaco"
# (--gres=gpu:1 no impide ver ni tocar las otras 7) -- se restringe a mano.
# OLLAMA_VULKAN=0 + GGML_VK_VISIBLE_DEVICES=-1: Ollama >=0.30 tambien
# descubre GPUs por Vulkan ademas de CUDA, y esa via NO respeta
# CUDA_VISIBLE_DEVICES (bug conocido: github.com/ollama/ollama/issues/16508).
# Desactivar Vulkan fuerza a usar solo la deteccion CUDA, que si lo respeta.
export CUDA_VISIBLE_DEVICES="0"
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1

OLLAMA_PORT="${OLLAMA_PORT:-11434}"
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"   # CAMBIA-ESTO si tu $HOME tiene poca cuota (usa tu espacio de proyecto/scratch)
mkdir -p "$OLLAMA_MODELS"

if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: no se encuentra el comando 'ollama' en este nodo. Instálalo primero (ver README.md)." >&2
    exit 1
fi

echo "Nodo: $(hostname) — arrancando Ollama en segundo plano (puerto ${OLLAMA_PORT})..."
ollama serve &
OLLAMA_PID=$!
trap 'kill "$OLLAMA_PID" 2>/dev/null || true' EXIT

echo "Esperando a que Ollama responda..."
for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 && break
    sleep 2
done

echo "Comprobando que qwen2.5:14b está descargado (~9-10 GB, solo la primera vez)..."
echo "  Si este nodo no tiene salida a internet, descárgalo antes desde el"
echo "  nodo de acceso/login, usando el mismo \$OLLAMA_MODELS."
ollama pull qwen2.5:14b

echo "Generando el corpus sintético..."
cd "$SINTETICOS_DIR"
python genera_corpus_sintetico.py --ollama-url "http://127.0.0.1:${OLLAMA_PORT}" "$@"

echo "Terminado (o interrumpido por el --time). Para continuar donde se quedó:"
echo "  sbatch slurm/generar_corpus.sh $*"
