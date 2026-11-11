#!/bin/bash
# entrena_kenlm.sh -- Job de SLURM NOMÉS CPU (09/11/2026): entrena un model
# de n-grames KenLM amb MaCoCu-ca SENCER sense filtrar (primera prova de
# substituir FLOR; vore README.es.md d'esta carpeta).
#   1. exporta_text.py -> dades/macocu/kenlm/macocu_tot.txt (si no hi és)
#   2. lmplz -> .arpa      3. build_binary -> .binary (trie quantitzat)
#
# Abans (una vegada, al node de login): compilar KenLM (vore el README).
#
# Llançar-ho (des de ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/kenlm):
#   sbatch entrena_kenlm.sh                         # ordre 5, poda de singletons
#   ORDRE=4 sbatch entrena_kenlm.sh
#   LIMIT_MB=500 NOM=prova sbatch entrena_kenlm.sh  # prova xicoteta
#   JSONL=dades/macocu/valencia/valencia.jsonl NOM=valencia sbatch entrena_kenlm.sh  # KenLM valencià
#   JSONL=dades/macocu/valencia/valencia.jsonl MARCADORS_DOC=2 NOM=valencia_net sbatch entrena_kenlm.sh
#   TEXT=dades/macocu/kenlm/valencia_net_dogv.txt NOM=valencia_net_dogv_np PODA="" sbatch entrena_kenlm.sh  # sense poda
# Variables: ORDRE (5), PODA ("0 1 1 1 1": lleva els n-grames d'1 aparició
# des dels bigrames; "" = sense poda), MEM_LMPLZ (70%
# de la memòria del job), NOM (macocu_tot), KENLM (~/kenlm), TMPDIR_LM,
# TEXT (11/11/2026: un text ja normalitzat, relatiu a l'arrel del repo, en
# lloc de dades/macocu/kenlm/<NOM>.txt; no s'exporta res).
# Pas 4 (11/11/2026): <NOM>_freq.json, la freqüència de les paraules
# candidates en el text (el prior de compara_models.py; freq_unigrames.py).

#SBATCH --job-name=kenlm
#SBATCH --output=%j_kenlm.out
#SBATCH --error=%j_kenlm.err
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00

set -euo pipefail

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
ARREL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
echo "Repo: $ARREL_REPO ($(git -C "$ARREL_REPO" log -1 --format='%h %s'))"
echo "CPU: ${SLURM_CPUS_PER_TASK:-?}, memòria: ${SLURM_MEM_PER_NODE:-?} MB, node: $(hostname)"

VENV="${VENV:-$HOME/venvs/avlizador}"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONIOENCODING=utf-8

KENLM="${KENLM:-$HOME/kenlm}"
LMPLZ="$KENLM/build/bin/lmplz"
BUILD_BINARY="$KENLM/build/bin/build_binary"
[[ -x "$LMPLZ" ]] || { echo "No trobe $LMPLZ: compila KenLM abans (vore README)." >&2; exit 1; }

CPUS="${SLURM_CPUS_PER_TASK:-4}"
ORDRE="${ORDRE:-5}"
PODA="${PODA-0$(printf ' 1%.0s' $(seq 2 "$ORDRE"))}"
NOM="${NOM:-macocu_tot}"
LIMIT_MB="${LIMIT_MB:-0}"
# JSONL: frases d'un JSONL (camp text, relatiu a l'arrel del repo) en lloc de MaCoCu sencer.
OPC_JSONL=()
[[ -n "${JSONL:-}" ]] && OPC_JSONL=(--jsonl "$JSONL")
# MARCADORS_DOC: amb JSONL, frases de >= N marcadors o del mateix document que una d'elles.
[[ -n "${MARCADORS_DOC:-}" ]] && OPC_JSONL+=(--marcadors-doc "$MARCADORS_DOC")
DIR_LM="$ARREL_REPO/dades/macocu/kenlm"
TEXT_DONAT="${TEXT:-}"
TEXT="${TEXT:+$(cd "$ARREL_REPO" && realpath "$TEXT")}"
TEXT="${TEXT:-$DIR_LM/$NOM.txt}"
ARPA="$DIR_LM/${NOM}_o${ORDRE}.arpa"
BIN="$DIR_LM/${NOM}_o${ORDRE}.binary"
TMPDIR_LM="${TMPDIR_LM:-$DIR_LM/tmp}"
MEM_MB="${SLURM_MEM_PER_NODE:-16000}"
MEM_LMPLZ="${MEM_LMPLZ:-$(( MEM_MB * 70 / 100 ))M}"
mkdir -p "$DIR_LM" "$TMPDIR_LM"
cd "$ARREL_REPO"

T0=$(date +%s)
# El .json l'escriu exporta_text.py només quan acaba: sense ell, el text
# pot estar a mitges i es torna a exportar.
if [[ -n "$TEXT_DONAT" ]]; then
    [[ -s "$TEXT" ]] || { echo "No trobe el text $TEXT" >&2; exit 1; }
    echo "=== 1. text donat: $TEXT ($(du -h "$TEXT" | cut -f1)) ==="
elif [[ ! -s "$TEXT" || ! -s "${TEXT%.txt}.json" ]]; then
    echo "=== 1. exporta el text ($TEXT) ==="
    python -u pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py \
        --processos "$CPUS" --limit-mb "$LIMIT_MB" --eixida "$TEXT" ${OPC_JSONL[@]+"${OPC_JSONL[@]}"}
else
    echo "=== 1. el text ja hi és: $TEXT ($(du -h "$TEXT" | cut -f1)) ==="
fi
echo "Temps: $(( $(date +%s) - T0 )) s"; df -h "$DIR_LM" | tail -1

echo "=== 2. lmplz (ordre $ORDRE, poda '${PODA}', memòria $MEM_LMPLZ) ==="
OPC_PODA=()
[[ -n "$PODA" ]] && read -r -a OPC_PODA <<< "--prune $PODA"
"$LMPLZ" -o "$ORDRE" -S "$MEM_LMPLZ" -T "$TMPDIR_LM" ${OPC_PODA[@]+"${OPC_PODA[@]}"} \
    --discount_fallback < "$TEXT" > "$ARPA"
ls -lh "$ARPA"
echo "Temps: $(( $(date +%s) - T0 )) s"

echo "=== 3. build_binary (trie, quantitzat 8 bits) ==="
"$BUILD_BINARY" -T "$TMPDIR_LM" trie -q 8 -b 8 "$ARPA" "$BIN"
ls -lh "$BIN"
echo "L'arpa es pot esborrar si el .binary funciona: rm $ARPA"

echo "=== 4. freqüència de les paraules candidates (prior) ==="
python -u pipeline/08_traduccio_corpus/macocu/kenlm/freq_unigrames.py "$TEXT" --eixida "$DIR_LM/${NOM}_freq.json"
echo "Temps total: $(( $(date +%s) - T0 )) s"
