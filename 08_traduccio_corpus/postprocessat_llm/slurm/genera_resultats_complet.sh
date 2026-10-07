#!/bin/bash
# genera_resultats_complet.sh -- Job de SLURM (1 GPU) que genera, en una
# sola execucio, els DOS resultats oficials de l'estat actual del
# projecte (07/10/2026), cadascun en un fitxer amb nom FIX (no
# timestampat) perque es puguen comparar sessio rere sessio sense buscar
# entre dotzenes de fitxers amb data:
#
#   1. NOMES el motor de regles (traductor.translate), CPU, sense LLM --
#      246 doctests + evalua_models.py --model traductor sobre les 151
#      frases del benchmark. Mesura l'efecte del filtre POS + la resta
#      de regles, soles.
#   2. Motor + postprocessat LLM (benchmark_integrat.py, Ollama), GPU --
#      a mes, resol l'ambiguitat 1a persona indicatiu/subjuntiu
#      ("centre"/"base"/"recupere"...) que el motor deixa a proposit
#      sense tocar (vore CRITERI_MODE_VERBAL a compara_postprocessat.py).
#
# Fitxers que han de estar ja pujats a
# ~/scrapeo/postprocesado_llm/traductor/rules/ (vore CLAUDE.md, seccio
# "Sesion 07/10/2026", per a l'historial complet de per que cada un):
#   pos_tagger.py (nou), engine.py, conjugacions_dict.py, __init__.py
# i a ~/scrapeo/postprocesado_llm/08_traduccio_corpus/postprocessat_llm/:
#   benchmark_integrat.py, compara_postprocessat.py
#
# Per si de cas hi ha dubte de si tot esta sincronitzat, puja-ho tot de
# colp abans de llançar este script (des de "scrapeo/" en local):
#   scp traductor/rules/pos_tagger.py traductor/rules/engine.py \
#       traductor/rules/conjugacions_dict.py traductor/rules/__init__.py \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/traductor/rules/
#   scp 08_traduccio_corpus/postprocessat_llm/benchmark_integrat.py \
#       08_traduccio_corpus/postprocessat_llm/compara_postprocessat.py \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/
#   scp 08_traduccio_corpus/postprocessat_llm/slurm/genera_resultats_complet.sh \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/
#
# Lanzarlo (des del node de login d'Abaco):
#   cd ~/scrapeo/postprocesado_llm
#   sbatch genera_resultats_complet.sh                  # qwen3:8b, via C, benchmark complet
#   sbatch genera_resultats_complet.sh qwen3:14b b 30    # un atre model/via, nomes 30 frases

#SBATCH --job-name=resultats-complet
#SBATCH --output=%j_resultats_complet.out
#SBATCH --error=%j_resultats_complet.err
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

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
# Este fitxer pot estar a slurm/ (local) o solt a l'arrel pujada (Abaco) --
# detecta quin dels dos conte traductor/ per a fixar POSTPROC_DIR be.
if [ -d "$SCRIPT_DIR/traductor" ]; then
    POSTPROC_DIR="$SCRIPT_DIR"
elif [ -d "$(dirname "$SCRIPT_DIR")/traductor" ]; then
    POSTPROC_DIR="$(dirname "$SCRIPT_DIR")"
else
    POSTPROC_DIR="$HOME/scrapeo/postprocesado_llm"
fi
export AVLIZADOR_ROOT="$POSTPROC_DIR"
echo "POSTPROC_DIR=$POSTPROC_DIR"

export CUDA_VISIBLE_DEVICES="0"
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1
export OLLAMA_HOST="127.0.0.1:11434"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/ollama_models}"
mkdir -p "$OLLAMA_MODELS"

echo "Instal·lant/comprovant spaCy + model de catala (ca_core_news_sm)..."
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q spacy
python3 -m spacy download ca_core_news_sm -q || python3 -m pip install -q \
    https://github.com/explosion/spacy-models/releases/download/ca_core_news_sm-3.8.0/ca_core_news_sm-3.8.0-py3-none-any.whl

echo ""
echo "=== PAS 1/3: doctests de traductor/ (246 tests esperats, 0 fallos) ==="
cd "$POSTPROC_DIR"
python3 -c "
import doctest, importlib
mods = [
    'traductor', 'traductor.translate', 'traductor.rules', 'traductor.rules.engine',
    'traductor.rules.pos_tagger', 'traductor.rules.conjugacions_dict', 'traductor.rules.lexic',
    'traductor.rules.possessius', 'traductor.rules.numerals', 'traductor.rules.concordanca_dos_dues',
    'traductor.rules.relatiu_on', 'traductor.rules.demostratius', 'traductor.rules.accentuacio',
    'traductor.rules.incoatius',
]
tf = 0; tt = 0
for m in mods:
    mod = importlib.import_module(m)
    r = doctest.testmod(mod, verbose=False)
    tf += r.failed; tt += r.attempted
print(f'TOTAL: {tt} tests, {tf} fallos')
"

echo ""
echo "=== PAS 2/3: NOMES el motor de regles (CPU, evalua_models.py --model traductor) ==="
cd "$POSTPROC_DIR/03_seleccio_de_model"
python3 evalua_models.py --model traductor
# evalua_models.py guarda amb timestamp propi -- es copia a un nom FIX
# a soles, aixina sempre se sap quin es "l'ultim resultat oficial" sense
# buscar per data.
ULTIM=$(ls -t resultats/benchmark_Traductor_Nou_*.json | head -1)
cp "$ULTIM" resultats/ULTIM_NOMES_MOTOR.json
echo "Copiat a resultats/ULTIM_NOMES_MOTOR.json (des de $ULTIM)"

echo ""
echo "=== PAS 3/3: motor + postprocessat LLM (GPU, benchmark_integrat.py, model=$MODEL via=$VIA) ==="
cd "$POSTPROC_DIR/08_traduccio_corpus/postprocessat_llm" 2>/dev/null || cd "$POSTPROC_DIR"
echo "Node: $(hostname) -- engegant Ollama en segon pla..."
ollama serve > "$POSTPROC_DIR/ollama_genera_resultats.log" 2>&1 &
OLLAMA_PID=$!
trap 'kill "$OLLAMA_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do
    curl -s "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && break
    sleep 2
done
echo "Comprovant que $MODEL esta descarregat..."
ollama pull "$MODEL"

LIMIT_ARGS=()
if [ -n "$LIMIT" ]; then
    LIMIT_ARGS=(--limit "$LIMIT")
fi
python3 benchmark_integrat.py --via "$VIA" --model "$MODEL" --ollama-timeout 300 \
    --output "ULTIM_MOTOR_MES_LLM.json" "${LIMIT_ARGS[@]}"

echo ""
echo "Fet. Resultats fixos per a comparar entre sessions:"
echo "  $POSTPROC_DIR/03_seleccio_de_model/resultats/ULTIM_NOMES_MOTOR.json"
echo "  $POSTPROC_DIR/08_traduccio_corpus/postprocessat_llm/ULTIM_MOTOR_MES_LLM.json (o a $POSTPROC_DIR/ si no existia eixa subcarpeta)"
