#!/bin/bash
# compara_postprocessat.sh — Job de SLURM que compara les 3 vies de
# postprocessat amb LLM (A: tradueix la frase sencera, B: tradueix nomes
# la paraula ambigua amb context, C: classifica indicatiu/subjuntiu i
# aplica una taula ja coneguda) per a l'ambiguitat present indicatiu/
# subjuntiu de 1a persona (p.ex. valencia "plantege" -> catala "plantejo"
# indicatiu / "plantegi" subjuntiu). Vore ../README.md per al contexte
# complet de la decisio (06/10/2026).
#
# Prova local (sense GPU) confirmada massa lenta per a ser util: una sola
# crida trivial a qwen2.5:14b per CPU ha trigat 65s -- per aixo este job
# es llança en un node amb GPU d'"abaco", igual que la resta d'scripts
# d'este projecte.
#
# IMPORTANT -- este script NOMÉS fa el pas 2 (comparar A/B/C): el pas 1
# (`identifica_ambigues.py`, que necessita el corpus COMPLET del BOE,
# ~126 MB, i els 4 fitxers font de Mauricio) s'executa en LOCAL/repo
# complet, NO en Abaco -- Abaco (vore `~/scrapeo/` al servidor) no té la
# resta de l'estructura del projecte (`traductor/`, `02_regles_dialectals/`,
# `dades/boe_net/`), nomes els scripts de generació de corpus sintètic i
# el benchmark. El fitxer de mostra (`mostra_casos_ambigues.json` del BOE,
# o `mostra_casos_ambigues_benchmark.json` dels 150 de benchmark_corpus.json,
# o qualsevol altre generat amb `identifica_ambigues.py --corpus ...`) es
# puja tal qual junt amb els scripts -- vore el README d'esta carpeta per
# al comandament `scp` exacte.
#
# Lanzarlo (des del node de login d'Abaco, dins de ~/scrapeo/postprocesado_llm/):
#   cd slurm
#   sbatch compara_postprocessat.sh                                       # mostra del BOE, qwen2.5:14b (per defecte)
#   sbatch compara_postprocessat.sh qwen3:8b                              # mateixa mostra, un altre model
#   sbatch compara_postprocessat.sh qwen3:8b 10                          # + nomes les primeres 10 (prova rapida)
#   sbatch compara_postprocessat.sh qwen2.5:14b "" mostra_casos_ambigues_benchmark.json
#                                                                          # mostra del benchmark de 150 (nomes 2 casos reals -- vore README)
#
# Les línies marcadas CAMBIA-ESTO depenen de la configuracio del teu
# cluster concret -- revisa-les abans de llançar-lo.

#SBATCH --job-name=postproc-subjuntiu
#SBATCH --output=%j_postproc.out
#SBATCH --error=%j_postproc.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
# #SBATCH --partition=gpu            # CAMBIA-ESTO: descomenta si el teu cluster ho exigix
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO: descomenta si el teu cluster ho exigix

set -euo pipefail

MODEL="${1:-qwen2.5:14b}"                         # model d'Ollama a provar en les 3 vies (A/B/C)
LIMIT="${2:-}"                                     # si es dona, nomes prova les primeres N frases de la mostra
MOSTRA_FILE="${3:-mostra_casos_ambigues.json}"    # quin fitxer de mostra (BOE per defecte, o el del benchmark)

# IMPORTANT: SLURM copia este script a /var/spool/slurmd/jobXXXXX/ abans
# d'executar-lo, aixi que ${BASH_SOURCE[0]} apunta ahi, NO al projecte
# real. $SLURM_SUBMIT_DIR es la carpeta des d'on vas llançar `sbatch` --
# eixa si es fiable (mateix arreglo que la resta d'scripts del projecte).
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
POSTPROC_DIR="$(dirname "$SCRIPT_DIR")"

# El aislamiento de GPU por cgroups de SLURM no esta actiu en "abaco"
# (--gres=gpu:1 no impedix vore ni tocar les altres GPUs) -- es restringix
# a ma. OLLAMA_VULKAN=0 + GGML_VK_VISIBLE_DEVICES=-1: Ollama tambe
# descobrix GPUs per Vulkan a mes de CUDA, i eixa via NO respecta
# CUDA_VISIBLE_DEVICES (bug conegut: github.com/ollama/ollama/issues/16508).
export CUDA_VISIBLE_DEVICES="0"
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1

OLLAMA_PORT="${OLLAMA_PORT:-11434}"
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"   # CAMBIA-ESTO si el teu $HOME te poca quota
mkdir -p "$OLLAMA_MODELS"

if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: no es troba la comanda 'ollama' en este node. Instal·la'l primer." >&2
    exit 1
fi

echo "Node: $(hostname) -- engegant Ollama en segon pla (port ${OLLAMA_PORT})..."
ollama serve &
OLLAMA_PID=$!
trap 'kill "$OLLAMA_PID" 2>/dev/null || true' EXIT

echo "Esperant que Ollama responga..."
for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 && break
    sleep 2
done

echo "Comprovant que $MODEL esta descarregat (nomes la primera vegada)..."
ollama pull "$MODEL"

cd "$POSTPROC_DIR"
if [ ! -f "$MOSTRA_FILE" ]; then
    echo "ERROR: no es troba $MOSTRA_FILE en $POSTPROC_DIR." >&2
    echo "  Genera'l en local (python identifica_ambigues.py, o amb --corpus per a" >&2
    echo "  un altre corpus com el benchmark de 150) i puja'l amb scp/rsync junt" >&2
    echo "  amb la resta d'esta carpeta -- vore README.md." >&2
    exit 1
fi

# El nom del model pot portar ":" (p.ex. "qwen3:8b"), es substituïx per
# "-" al nom de carpeta/fitxer perque ":" dona problemes en alguns FS.
MODEL_SLUG="${MODEL//:/-}"
MOSTRA_SLUG="$(basename "$MOSTRA_FILE" .json)"
OUT_DIR="$POSTPROC_DIR/resultats_${MODEL_SLUG}_${MOSTRA_SLUG}_$(date +%Y%m%d_%H%M)"
mkdir -p "$OUT_DIR"
echo "Eixida en: $OUT_DIR"

LIMIT_ARGS=()
if [ -n "$LIMIT" ]; then
    LIMIT_ARGS=(--limit "$LIMIT")
fi

echo ""
echo "Comparant les 3 vies (A/B/C) amb $MODEL sobre $MOSTRA_FILE..."
python3 compara_postprocessat.py \
    --model "$MODEL" --ollama-url "http://127.0.0.1:${OLLAMA_PORT}" --ollama-timeout 300 \
    --mostra-path "$MOSTRA_FILE" \
    --output "$OUT_DIR/resultats_comparativa_ABC_${MODEL_SLUG}.json" "${LIMIT_ARGS[@]}"

echo ""
echo "Fet. Resultats en $OUT_DIR/resultats_comparativa_ABC_${MODEL_SLUG}.json"
