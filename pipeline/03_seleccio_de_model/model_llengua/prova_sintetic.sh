#!/bin/bash
# prova_sintetic.sh -- Llança en Abaco la prova del KenLM amb el corpus
# sintètic d'homògrafs (25/11/2026, petició de l'usuari). Prova a banda: el
# model del sistema (2.0.1) no es toca.
#
# KenLM (ordre 5, mateixa poda que el del sistema), cadascun amb la seua taula
# de freqüències:
#   valencia_net_dogv2_sint    el text del sistema (valencia_net_dogv2.txt) + les frases sintètiques x1
#   valencia_net_dogv2_sint3   ídem, amb les frases sintètiques x3 (la poda lleva els n-grames únics)
# Comparació (compara_models.sh): el sistema (kenlm_dogv2_c1) i les dues
# variants, amb el classificador del sistema (sentit_dogv2_avl.json) i el
# criteri del sistema (CRITERI_KENLM: marge 1); homògrafs v1 i v2, manual i
# 151; detall de cada decisió.
#
# Fitxers que han d'estar en Abaco (els sintètics es generen en local amb
# prepara_sintetic.py i es pugen amb scp):
#   dades/macocu/kenlm/valencia_net_dogv2.txt          (ja hi és)
#   dades/macocu/kenlm/sentit/sentit_dogv2_avl.json    (ja hi és)
#   dades/sintetic_homografs/sintetic_net.txt
#   dades/sintetic_homografs/sintetic_net_x3.txt
#
# NO és un job: s'executa en el node de login i encua.
# Ús (des de ~/scrapeo/AVLizador, en la branca kenlm-sintetic):
#   bash pipeline/03_seleccio_de_model/model_llengua/prova_sintetic.sh
#   NOMES_COMPARA=1 bash .../prova_sintetic.sh     # ja estan entrenats
# Resultats: pipeline/03_seleccio_de_model/resultats/compara_models_<data>_sintetic{,_detall}.{md,json}

set -euo pipefail

ARREL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ARREL"
echo "Repo: $ARREL ($(git log -1 --format='%h %s'), branca $(git branch --show-current))"
DIR_LM="dades/macocu/kenlm"
MODEL_LL="pipeline/03_seleccio_de_model/model_llengua"
DIR_KENLM="pipeline/08_traduccio_corpus/macocu/kenlm"
BASE="$DIR_LM/valencia_net_dogv2.txt"
SENTIT="$ARREL/$DIR_LM/sentit/sentit_dogv2_avl.json"
declare -A SINT=([valencia_net_dogv2_sint]=dades/sintetic_homografs/sintetic_net.txt
                 [valencia_net_dogv2_sint3]=dades/sintetic_homografs/sintetic_net_x3.txt)

for f in "$DIR_LM/valencia_net_dogv2_o5.binary" "$DIR_LM/valencia_net_dogv2_freq.json" "$SENTIT"; do
    [[ -s "$f" ]] || { echo "Falta $f (el sistema, per a comparar)" >&2; exit 1; }
done

JOBS=()
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -s "$BASE" ]] || { echo "Falta $BASE" >&2; exit 1; }
    for v in "${!SINT[@]}"; do
        [[ -s "${SINT[$v]}" ]] || { echo "Falta ${SINT[$v]} (prepara_sintetic.py + scp)" >&2; exit 1; }
        cat "$BASE" "${SINT[$v]}" > "$DIR_LM/$v.txt"
        echo "   $v.txt: $(wc -l < "$DIR_LM/$v.txt") frases (+$(wc -l < "${SINT[$v]}") sintètiques)"
        J=$(cd "$DIR_KENLM" && TEXT="$DIR_LM/$v.txt" NOM="$v" \
            sbatch --parsable --job-name="kenlm-$v" entrena_kenlm.sh)
        echo "1. KenLM $v:   job $J"
        JOBS+=("$J")
    done
fi
DEP=()
[[ ${#JOBS[@]} -gt 0 ]] && DEP=(--dependency=afterok:"$(IFS=:; echo "${JOBS[*]}")")

MODELS="kenlm_dogv2_c1 kenlm_dogv2_sint_c1 kenlm_dogv2_sint3_c1"
J3=$(cd "$MODEL_LL" && \
     MODELS="$MODELS" \
     EXTRA="--benchmarks homografs homografs_v2 manual 151 --model-sentit $SENTIT --etiqueta sintetic --marges 1 --per-defecte catala --lams 1.5 --lams-colisio 0.75 --lams-irresoluble 1.25 --desempats 2 --detall" \
     sbatch --parsable --time=06:00:00 --job-name="compara-sintetic" ${DEP[@]+"${DEP[@]}"} compara_models.sh)
echo "2. compara: $MODELS   job $J3${DEP:+ (després dels entrenaments)}"
