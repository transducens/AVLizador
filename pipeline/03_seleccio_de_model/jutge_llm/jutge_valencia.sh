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
#   PROMPT=valencia2 sbatch jutge_valencia.sh   # sense les formes candidates d'un
#                                               # homògraf (25/11/2026); en resultats/valencia2/
#   PROMPT=valencia3 sbatch jutge_valencia.sh   # valencia2 + glossari de la frase tret
#                                               # del lèxic (25/11/2026); en resultats/valencia3/
#   PROMPT=valencia_va sbatch jutge_valencia.sh # "valencia" traduït al valencià (26/11/2026)
#   IDS="HG2-004,HG2-010" CONJUNTS=homografs_v2 sbatch jutge_valencia.sh
#                                               # només eixes frases (carpeta ..._mostraN)
# Si s'acaba per temps, es torna a llançar igual: continua des de la memòria
# cau (resultats/<prompt>/<conjunt>/<model>/cache.jsonl).
#
# En dos màquines (24/11/2026): les traduccions en Abaco, només CPU
#   sbatch --mem=8G --cpus-per-task=4 --time=01:00:00 -o logs/%j_entrades.out \
#       --wrap "NOMES_ENTRADES=1 bash jutge_valencia.sh"
# i el jutge en una màquina amb GPU sense SLURM (p. ex. nevis, A100 40 GB),
# amb entrades_valencia/ copiada i Ollama al PATH (no cal el venv):
#   OLLAMA_VULKAN=1 bash jutge_valencia.sh      # nevis: la GPU només per Vulkan
#
# En caiman (25/11/2026): CONJUNTS=... PENSA=1 sbatch --partition=gpu --gres=gpu:1 jutge_valencia.sh
# Sense baixar les CPU: amb --cpus-per-task=4 el llama-server (36 fils, 410 %
# de CPU, GPU al 17 %) generava a ~110 tokens/s, i amb les 8 per defecte
# (job 2455) a ~240 (manual: 30 s/text en compte de 12). Probablement és la
# CPU; no s'ha comprovat a banda.

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
PROMPT="${PROMPT:-valencia}"
VENV="${AVLIZADOR_VENV:-$HOME/venvs/avlizador}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
LOGS="$SCRIPT_DIR/logs"
ENTRADES="$SCRIPT_DIR/entrades_valencia"
BASELINE="$SCRIPT_DIR/../baseline_llm/resultats"
mkdir -p "$LOGS" "$ENTRADES"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Model: $MODEL; prompt: $PROMPT; conjunts: $CONJUNTS; en $(hostname)"

export PYTHONIOENCODING=utf-8
PYTHON=python3

# 1. Traduccions d'AVLizador i del motor sol (CPU; uns minuts). Només cal
#    el venv si falten.
cd "$ARREL_REPO"
if [[ ! -f "$ENTRADES/manual/avlizador.json" || ! -f "$ENTRADES/homografs_v2/motor.json" ]]; then
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    PYTHON=python
fi
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
if [[ -n "${NOMES_ENTRADES:-}" ]]; then
    echo "Traduccions en $ENTRADES:"; ls -l "$ENTRADES"/*/
    exit 0
fi

# 2. Ollama propi (en Abaco, en les 2 GPU de SLURM; fora de SLURM, les de la màquina)
if [[ -n "${SLURM_JOB_ID:-}" && -z "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    echo "ERROR: SLURM no ha assignat cap GPU (CUDA_VISIBLE_DEVICES buit)." >&2
    exit 1
fi
echo "GPU: ${CUDA_VISIBLE_DEVICES:-totes}"
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader || true
PORT=$((11700 + ${SLURM_JOB_ID:-0} % 100))
export OLLAMA_HOST="127.0.0.1:$PORT"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
if [[ "${OLLAMA_VULKAN:-0}" == 1 ]]; then
    # nevis (24/11/2026): driver NVIDIA 535 i Ollama demana el 550 per a CUDA;
    # per Vulkan sí que veu la A100. El carregador libvulkan.so.1 no està al
    # sistema: `apt download libvulkan1` + `dpkg -x` en ~/vulkan.
    export OLLAMA_VULKAN=1
    unset GGML_VK_VISIBLE_DEVICES
    if [[ -d "$HOME/vulkan/usr/lib/x86_64-linux-gnu" ]]; then
        export LD_LIBRARY_PATH="$HOME/vulkan/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
else
    # Abaco: Vulkan fora (no respecta CUDA_VISIBLE_DEVICES)
    export OLLAMA_VULKAN=0 GGML_VK_VISIBLE_DEVICES=-1
fi
export OLLAMA_SCHED_SPREAD=true
# CUDA numera les GPU per velocitat i SLURM (i nvidia-smi) pel bus PCI: sense
# açò, CUDA_VISIBLE_DEVICES=0 de SLURM pot ser una altra GPU física. En caiman
# (job 2527, 25/11/2026) SLURM va donar la 0 i Ollama va carregar en la 3.
export CUDA_DEVICE_ORDER=PCI_BUS_ID
# Ollama instal·lat en ~/ollama sense root (Abaco, nevis): sbatch hereta el
# PATH de la sessió, que pot no tindre'l.
command -v ollama > /dev/null || export PATH="$HOME/ollama/bin:$PATH"
command -v ollama > /dev/null || { echo "ERROR: no trobe ollama (ni en ~/ollama/bin)" >&2; exit 1; }
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
        manual3)  # 26/11/2026: només el català sense traduir, AVLizador i la referència (s'hi afig sola)
            FITXERS=("$BASELINE/copia.json" "$ENTRADES/manual/avlizador.json") ;;
        homografs|homografs_v2) FITXERS=("$ENTRADES/$c/avlizador.json" "$ENTRADES/$c/motor.json") ;;
        sintetic)  # benchmark_sintetic.json (26/11/2026): versió correcta i amb error de cada frase
            "$PYTHON" "$SCRIPT_DIR/sintetic.py" prepara --eixida "$ENTRADES/sintetic"
            FITXERS=("$ENTRADES/sintetic/original.json" "$ENTRADES/sintetic/correcta.json" "$ENTRADES/sintetic/erronia.json") ;;
        manual_errors)  # benchmark_errors_manual.json (26/11/2026): 20 frases de l'AVL amb un error posat a mà
            "$PYTHON" "$SCRIPT_DIR/sintetic.py" prepara --bench "$SCRIPT_DIR/benchmark_errors_manual.json"                 --eixida "$ENTRADES/manual_errors"
            FITXERS=("$ENTRADES/manual_errors/original.json" "$ENTRADES/manual_errors/correcta.json"
                     "$ENTRADES/manual_errors/erronia.json") ;;
        *) echo "ERROR: conjunt desconegut: $c" >&2; exit 1 ;;
    esac
    echo "== $c =="
    "$PYTHON" jutge_gemba.py puntua --prompt "$PROMPT" --model "$MODEL" --ollama-url "http://$OLLAMA_HOST" \
        --eixida "resultats/$PROMPT/$c" ${LIMIT:+--limit "$LIMIT"} ${IDS:+--ids "$IDS"} ${PENSA:+--pensa} \
        "${FITXERS[@]}"
done
grep -iE "offload|layers|VRAM" "$LOGS/ollama_valencia_${NOM_LOG}_${SLURM_JOB_ID:-local}.log" | tail -5 || true
