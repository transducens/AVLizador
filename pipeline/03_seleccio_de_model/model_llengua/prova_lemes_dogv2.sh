#!/bin/bash
# prova_lemes_dogv2.sh -- Llança en Abaco la prova del KenLM de LEMES amb el
# text del sistema 2.0.0 (20/11/2026, petició de l'usuari). La del 12/11
# (`prova_lemes.sh`) es va fer amb el text vell (`valencia_net_dogv`); ara el
# sistema és `valencia_net_dogv2` (MaCoCu net + el DOGV nou sencer) amb el
# classificador `sentit_dogv2_avl`. Mateix lematitzador que el 12/11
# (`LematitzadorLM`: tot a lema llevat de les paraules candidates i de les que
# concorden en gènere). NO és un job: s'executa en el node de login i encua:
#
#   1. lematitza_text.sh  -- valencia_net_dogv2.txt -> valencia_net_dogv2_lemes.txt
#   2. entrena_kenlm.sh   -- KenLM de lemes (ordre 5, poda de singletons) i la
#      seua taula de freqüències; després de 1.
#   3. compara_models.sh  -- el sistema 2.0.0 (`kenlm_dogv2_c1`), el KenLM de
#      lemes sol i + classificador, i la mescla formes + lemes + classificador,
#      en homògrafs v1 i v2, manual i 151, amb la graella de marges i λ i el
#      detall de cada decisió; després de 2.
#
# Ús (des de ~/scrapeo/AVLizador, amb la branca `kenlm-lemes-2.0` al dia):
#   bash pipeline/03_seleccio_de_model/model_llengua/prova_lemes_dogv2.sh
#   NOMES_COMPARA=1 bash .../prova_lemes_dogv2.sh   # el KenLM de lemes ja està entrenat
#   BENCH="homografs homografs_v2 manual 151 boe_estricte gplsi" bash .../prova_lemes_dogv2.sh
# Mirar com van: squeue -u $USER; els .out queden en la carpeta de cada script.

set -euo pipefail

ARREL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ARREL"
echo "Repo: $ARREL ($(git log -1 --format='%h %s'), branca $(git branch --show-current))"
DIR_LM="dades/macocu/kenlm"
MODEL_LL="pipeline/03_seleccio_de_model/model_llengua"
DIR_KENLM="pipeline/08_traduccio_corpus/macocu/kenlm"
BASE="valencia_net_dogv2"
NOM="${BASE}_lemes"
SENTIT="$ARREL/$DIR_LM/sentit/sentit_dogv2_avl.json"
BENCH="${BENCH:-homografs homografs_v2 manual 151}"

# --- Comprovacions -----------------------------------------------------------
for f in "$DIR_LM/${BASE}_o5.binary" "$DIR_LM/${BASE}_freq.json" "$SENTIT"; do
    [[ -s "$f" ]] || { echo "Falta $f (el sistema 2.0.0)" >&2; exit 1; }
done
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -s "$DIR_LM/$BASE.txt" ]] || { echo "Falta $DIR_LM/$BASE.txt" >&2; exit 1; }
    [[ -x "$HOME/kenlm/build/bin/lmplz" ]] || { echo "Falta KenLM compilat en ~/kenlm" >&2; exit 1; }
else
    for f in "$DIR_LM/${NOM}_o5.binary" "$DIR_LM/${NOM}_freq.json"; do
        [[ -s "$f" ]] || { echo "NOMES_COMPARA: falta $f" >&2; exit 1; }
    done
fi

# --- 1 i 2. KenLM de lemes ----------------------------------------------------
DEP=()
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    J1=$(cd "$DIR_KENLM" && ENTRADA="$DIR_LM/$BASE.txt" EIXIDA="$DIR_LM/$NOM.txt" \
         sbatch --parsable --job-name="lemes-dogv2" lematitza_text.sh)
    echo "1. lematitza el text:          job $J1"
    J2=$(cd "$DIR_KENLM" && TEXT="$DIR_LM/$NOM.txt" NOM="$NOM" \
         sbatch --parsable --job-name="kenlm-lemes-dogv2" --dependency=afterok:"$J1" entrena_kenlm.sh)
    echo "2. entrena el KenLM de lemes:  job $J2 (després de $J1)"
    DEP=(--dependency=afterok:"$J2")
fi

# --- 3. Comparació ------------------------------------------------------------
J3=$(cd "$MODEL_LL" && \
     MODELS="kenlm_dogv2_c1 kenlm_lemes_dogv2 kenlm_lemes_dogv2_c1 kenlm_mescla_dogv2_c1" \
     EXTRA="--benchmarks $BENCH --model-sentit $SENTIT --etiqueta lemes_dogv2 --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --desempats 2 --detall" \
     sbatch --parsable --time=08:00:00 --job-name="compara-lemes-dogv2" ${DEP[@]+"${DEP[@]}"} compara_models.sh)
echo "3. compara els models:         job $J3${DEP:+ (després de ${J2:-})}"
echo
echo "Resultats: pipeline/03_seleccio_de_model/resultats/compara_models_<data>_lemes_dogv2{,_detall}.{md,json}"
