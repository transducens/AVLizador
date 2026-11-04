#!/bin/bash
# baseline_models_llengua.sh -- Job array de SLURM NOMÉS CPU (29/10/2026):
# baseline de models de llengua xicotets per a `traductor/model_llengua/`
# (el sistema final cat->val; vore el seu README). Cada tasca de l'array
# avalua UN model, en paralel:
#   1. el benchmark combinat (151 + homògrafs, 253 frases) amb el criteri
#      per defecte (`evalua_models.py --model traductor_ml --model-llengua M`);
#   2. una graella de criteris sobre els 98 homògrafs
#      (`traductor.model_llengua.avalua`, lam 0/0,5/1 x marge 0/5), perquè
#      el criteri per defecte es va ajustar per a FLOR-760M.
# El model de llengua corre en CPU (`puntuador.py` no usa GPU), com a la
# Conselleria: no es demana GPU.
#
# Només funciona amb el CLON del repo (~/scrapeo/AVLizador, `git pull`):
# els dos benchmarks estan a git.
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/postprocessat_llm/slurm):
#   sbatch baseline_models_llengua.sh             # els 9 models
#   sbatch --array=0,3 baseline_models_llengua.sh # només uns quants (índex de MODELS)
#   sbatch --array=9 baseline_models_llengua.sh   # FLOR-1.3B (abans: huggingface-cli login
#                                                 # i acceptar-ne les condicions a la web)
# Resultats: pipeline/03_seleccio_de_model/resultats/ (JSON de cada model) i
# dades/abaco/baseline_models_llengua/ (logs de cada model).

#SBATCH --job-name=baseline-ml
#SBATCH --output=%A_%a_baseline_ml.out
#SBATCH --error=%A_%a_baseline_ml.err
#SBATCH --array=0-8
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=03:00:00

set -euo pipefail

# Models oberts (sense acceptar condicions a Hugging Face), de menys a més
# paràmetres (índexs 0-8, l'array per defecte). Resultats del 29/10/2026 a
# documentacio/resultats_baseline_models_llengua.md. L'índex 9 (FLOR-1.3B)
# demana accés (gated): `huggingface-cli login` i acceptar-ne les condicions.
# Llama-3.2-1B i Gemma-3-1B també són gated i no s'han afegit.
MODELS=(
    projecte-aina/FLOR-760M
    Qwen/Qwen2.5-0.5B
    Qwen/Qwen3-0.6B-Base
    bigscience/bloom-560m
    Qwen/Qwen2.5-1.5B
    Qwen/Qwen3-1.7B-Base
    utter-project/EuroLLM-1.7B
    bigscience/bloom-1b7
    BSC-LT/salamandra-2b
    projecte-aina/FLOR-1.3B
)
MODEL="${MODELS[${SLURM_ARRAY_TASK_ID:-0}]}"
NOM="${MODEL##*/}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
unset AVLIZADOR_ROOT
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "Model: $MODEL (tasca ${SLURM_ARRAY_TASK_ID:-0}, ${SLURM_CPUS_PER_TASK:-?} CPU)"

export PIP_BREAK_SYSTEM_PACKAGES=1
export PYTHONIOENCODING=utf-8
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
# Nou tasques baixant models alhora: la memòria cau de Hugging Face al HOME
# (canvia HF_HOME si la quota del HOME no dona per a ~16 GB).
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

# Dependències. Millor instal·lar-les UNA vegada al node de login abans de
# llançar l'array (nou `pip install` alhora es poden trepitjar); ací només
# s'instal·la el que falte.
python3 -c "import torch" 2>/dev/null || pip install -q torch --index-url https://download.pytorch.org/whl/cpu
python3 -c "import transformers, sacrebleu, requests" 2>/dev/null || pip install -q "transformers>=4.56" accelerate sacrebleu requests
python3 -c "import spacy" 2>/dev/null || pip install -q spacy
# El mateix model d'spaCy que en local (pos_tagger.MODELS_SPACY prova md i després sm)
python3 -c "import ca_core_news_md" 2>/dev/null || python3 -m spacy download ca_core_news_md -q
# Des del 30/10/2026 el traductor és el paquet `avlizador` (src/): s'instal·la
# en mode editable des del clon, sense tocar les dependències de dalt.
python3 -c "import avlizador" 2>/dev/null || pip install -q --no-deps -e "$ARREL_REPO"

LOGS="$ARREL_REPO/dades/abaco/baseline_models_llengua"
mkdir -p "$LOGS"

echo ""
echo "=== 1. Benchmark combinat (253 frases), criteri per defecte ==="
T0=$(date +%s)
(cd "$ARREL_REPO/pipeline/03_seleccio_de_model" && python3 -u evalua_models.py --model traductor_ml \
    --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json --model-llengua "$MODEL") \
    2>&1 | tee "$LOGS/combinat_$NOM.log"
echo "Temps combinat: $(( $(date +%s) - T0 )) s"
# evalua_models.py torna la frase SENSE TRADUIR si el traductor peta (vore CLAUDE.md)
N_ERRORS=$(grep -c "ERROR:" "$LOGS/combinat_$NOM.log" || true)
echo "Línies ERROR: $N_ERRORS"

echo ""
echo "=== 2. Graella de criteris sobre els homògrafs (98 frases) ==="
T0=$(date +%s)
(cd "$ARREL_REPO" && python3 -u pipeline/03_seleccio_de_model/model_llengua/avalua.py --models "$MODEL" \
    --lams 0 0.5 1 --marges 0 5 --puntuacions frase --spacy-irresolubles si --model-irresolubles si) \
    2>&1 | tee "$LOGS/graella_$NOM.log"
echo "Temps graella: $(( $(date +%s) - T0 )) s"
echo "Fet: $MODEL"
