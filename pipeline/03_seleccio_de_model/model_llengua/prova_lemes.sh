#!/bin/bash
# prova_lemes.sh -- Llança en Abaco TOTA la prova del KenLM de lemes
# (12/11/2026) i, de pas, la foto del sistema actual. NO és un job: s'executa
# en el node de login i encua els jobs amb dependències:
#
#   1. avalua_sistema.sh  -- `avlizador avalua --motor --model flor kenlm` en
#      homògrafs v1/v2, manual, 151, BOE estricte i gplsi (sense esperar res).
#   2. lematitza_text.sh  -- valencia_net_dogv.txt -> valencia_net_dogv_lemes.txt
#   3. entrena_kenlm.sh   -- KenLM de lemes (ordre 5, poda de singletons) +
#      freqüències (valencia_net_dogv_lemes_o5.binary, _freq.json); després de 2.
#   4. compara_models.sh  -- motor, KenLM actual + C1, KenLM de lemes (sol i
#      + C1) i la mescla formes + lemes (+ C1), en els mateixos benchmarks,
#      amb una graella de marges i λ i el detall de cada decisió; després de 3.
#
# Ús (des de ~/scrapeo/AVLizador, amb la branca `kenlm` al dia):
#   bash pipeline/03_seleccio_de_model/model_llengua/prova_lemes.sh
#   NOMES_COMPARA=1 bash .../prova_lemes.sh   # el KenLM de lemes ja està entrenat: només 1 i 4
#   SENSE_SISTEMA=1 bash .../prova_lemes.sh   # sense el pas 1
# Mirar com van: squeue -u $USER; els .out queden en la carpeta de cada script.

set -euo pipefail

ARREL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ARREL"
echo "Repo: $ARREL ($(git log -1 --format='%h %s'), branca $(git branch --show-current))"
DIR_LM="dades/macocu/kenlm"
MODEL_LL="pipeline/03_seleccio_de_model/model_llengua"
DIR_KENLM="pipeline/08_traduccio_corpus/macocu/kenlm"
NOM="valencia_net_dogv_lemes"

# --- Comprovacions -----------------------------------------------------------
for f in "$DIR_LM/valencia_net_dogv_o5.binary" "$DIR_LM/valencia_net_dogv_freq.json" \
         "$DIR_LM/sentit_cop/nb.json"; do
    [[ -s "$f" ]] || { echo "Falta $f" >&2; exit 1; }
done
# El classificador ha de ser el reentrenat sense l'AVL (12/11/2026).
if [[ -s "$DIR_LM/sentit_cop/nb_sense_avl.json" ]]; then
    cmp -s "$DIR_LM/sentit_cop/nb.json" "$DIR_LM/sentit_cop/nb_sense_avl.json" || {
        echo "nb.json NO és el de sense AVL. Abans:" >&2
        echo "  cd $DIR_LM/sentit_cop && cp nb.json nb_amb_avl.json && cp nb_sense_avl.json nb.json" >&2
        exit 1; }
else
    echo "Falta $DIR_LM/sentit_cop/nb_sense_avl.json (copia'l des del PC amb scp)" >&2; exit 1
fi
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -s "$DIR_LM/valencia_net_dogv.txt" ]] || { echo "Falta $DIR_LM/valencia_net_dogv.txt" >&2; exit 1; }
    [[ -x "$HOME/kenlm/build/bin/lmplz" ]] || { echo "Falta KenLM compilat en ~/kenlm" >&2; exit 1; }
else
    [[ -s "$DIR_LM/${NOM}_o5.binary" ]] || { echo "NOMES_COMPARA: falta $DIR_LM/${NOM}_o5.binary" >&2; exit 1; }
fi

BENCH="homografs homografs_v2 manual 151 boe_estricte gplsi"

# --- 1. Sistema actual --------------------------------------------------------
if [[ -z "${SENSE_SISTEMA:-}" ]]; then
    J1=$(cd "$MODEL_LL" && sbatch --parsable avalua_sistema.sh)
    echo "1. sistema actual (FLOR, KenLM, motor):  job $J1"
fi

# --- 2 i 3. KenLM de lemes ---------------------------------------------------
DEP=()
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    J2=$(cd "$DIR_KENLM" && ENTRADA="$DIR_LM/valencia_net_dogv.txt" EIXIDA="$DIR_LM/$NOM.txt" \
         sbatch --parsable lematitza_text.sh)
    echo "2. lematitza el text:                    job $J2"
    J3=$(cd "$DIR_KENLM" && TEXT="$DIR_LM/$NOM.txt" NOM="$NOM" \
         sbatch --parsable --dependency=afterok:"$J2" entrena_kenlm.sh)
    echo "3. entrena el KenLM de lemes:            job $J3 (després de $J2)"
    DEP=(--dependency=afterok:"$J3")
fi

# --- 4. Comparació ------------------------------------------------------------
J4=$(cd "$MODEL_LL" && \
     MODELS="motor kenlm_val_net_dogv_c1 kenlm_lemes kenlm_lemes_c1 kenlm_mescla_c1" \
     EXTRA="--benchmarks $BENCH --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --desempats 2 --detall" \
     sbatch --parsable --time=10:00:00 ${DEP[@]+"${DEP[@]}"} compara_models.sh)
echo "4. compara els models:                   job $J4${DEP:+ (després de ${J3:-})}"
echo
echo "Resultats: pipeline/03_seleccio_de_model/resultats/{avalua_sistema_*,compara_models_*}"
echo "Per a portar-los al PC (des de l'arrel del repo en el PC):"
echo "  scp -r \"nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/resultats/{avalua_sistema_*,compara_models_*}\" pipeline/03_seleccio_de_model/resultats/"
