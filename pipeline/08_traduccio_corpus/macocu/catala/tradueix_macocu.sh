#!/bin/bash
# tradueix_macocu.sh -- Job de SLURM NOMÉS CPU (09/11/2026): traduïx a
# valencià les frases de dades/macocu/catala_pur.jsonl amb AVLizador
# (vore tradueix_macocu.py i README.es.md d'esta carpeta).
#   PAS=motor (per defecte): motor + spaCy, un procés per nucli menys un.
#       Les frases sense paraules ambigües -> paralel_motor.jsonl (ja finals);
#       les que en tenen -> pendents_flor.jsonl.
#   PAS=flor: sistema complet amb FLOR-760M per a les pendents ->
#       paralel_flor.jsonl. PROCESSOS x FILS = nuclis (per defecte 4 x 4).
# Els dos són reprenibles: si el job s'acaba pel temps, tornar a llançar-lo
# continua on ho va deixar.
#
# Abans (una vegada, al node de login, des de ~/scrapeo/AVLizador):
#   git fetch && git checkout macocu && git pull
#   (catala_pur.jsonl ja hi és, de filtra_macocu.sh)
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/catala):
#   MAXIM=20000 sbatch tradueix_macocu.sh          # prova: unes 20.000 línies
#   sbatch tradueix_macocu.sh                      # pas 1 sencer
#   PAS=flor MAXIM=2000 sbatch tradueix_macocu.sh  # prova del pas 2
#   PAS=flor sbatch tradueix_macocu.sh             # pas 2 sencer
# Per a començar de zero un pas: REINICIA=1.

#SBATCH --job-name=macocu-trad
#SBATCH --output=%j_macocu_trad.out
#SBATCH --error=%j_macocu_trad.err
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=24:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8
export TOKENIZERS_PARALLELISM=false

CPUS="${SLURM_CPUS_PER_TASK:-8}"
PAS="${PAS:-motor}"
MAXIM="${MAXIM:-0}"
EXTRA=()
[[ -n "${REINICIA:-}" ]] && EXTRA+=(--reinicia)
SCRIPT="$ARREL_REPO/pipeline/08_traduccio_corpus/macocu/catala/tradueix_macocu.py"
cd "$ARREL_REPO"

T0=$(date +%s)
if [[ "$PAS" == "motor" ]]; then
    # Un fil per procés: el paral·lelisme el fan els processos.
    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCH_NUM_THREADS=1
    PROCESSOS=$(( CPUS > 1 ? CPUS - 1 : 1 ))
    echo "=== pas motor ($PROCESSOS processos, maxim $MAXIM) ==="
    python -u "$SCRIPT" motor --processos "$PROCESSOS" --maxim "$MAXIM" ${EXTRA[@]+"${EXTRA[@]}"}
elif [[ "$PAS" == "flor" ]]; then
    FILS="${FILS:-4}"
    PROCESSOS="${PROCESSOS:-$(( CPUS / FILS > 0 ? CPUS / FILS : 1 ))}"
    export OMP_NUM_THREADS="$FILS" MKL_NUM_THREADS="$FILS"
    echo "=== pas flor ($PROCESSOS processos x $FILS fils, maxim $MAXIM) ==="
    python -u "$SCRIPT" flor --processos "$PROCESSOS" --fils "$FILS" --maxim "$MAXIM" ${EXTRA[@]+"${EXTRA[@]}"}
else
    echo "PAS ha de ser motor o flor (és '$PAS')" >&2
    exit 1
fi
echo "Temps: $(( $(date +%s) - T0 )) s"
