#!/bin/bash
# prova_ordres.sh -- Llança en Abaco la prova de l'ORDRE del KenLM (16/11/2026,
# petició de l'usuari): el KenLM del sistema (`valencia_net_dogv`, ordre 5)
# enfront del mateix text i la mateixa poda amb ordre 6, 7 i 8 (el candidat es
# puntua amb 5, 6 o 7 paraules d'abans en lloc de 4). NO és un job: s'executa
# en el node de login i encua els jobs amb dependències:
#
#   1. entrena_kenlm.sh, un per ordre -- valencia_net_dogv_o<N>.binary, amb
#      SENSE_FREQ=1 (la taula de freqüències és la del text, la mateixa per
#      a tots els ordres: no es toca).
#   2. compara_models.sh -- kenlm_val_net_dogv_c1 (el sistema, ordre 5) i
#      kenlm_o6_c1 / kenlm_o7_c1 / kenlm_o8_c1, tots amb el classificador de
#      sentit general; NOMÉS els homògrafs v1 i v2 i el manual, sense FLOR ni
#      el motor (decisió de l'usuari). Graella de marges i λ (un ordre més
#      alt canvia l'escala de les puntuacions) i el detall de cada decisió;
#      després de tots els entrenaments.
#
# Ús (des de ~/scrapeo/AVLizador, amb la branca `kenlm-ordres` al dia):
#   bash pipeline/03_seleccio_de_model/model_llengua/prova_ordres.sh
#   ORDRES="6 7" bash .../prova_ordres.sh          # només uns ordres
#   NOMES_COMPARA=1 bash .../prova_ordres.sh       # ja estan entrenats: només el pas 2
# Mirar com van: squeue -u $USER; els .out queden en la carpeta de cada script.
# Disc: cada .arpa pot fer uns quants GB; quan el .binary funcione, es pot
# esborrar (rm dades/macocu/kenlm/valencia_net_dogv_o[678].arpa).

set -euo pipefail

ARREL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ARREL"
echo "Repo: $ARREL ($(git log -1 --format='%h %s'), branca $(git branch --show-current))"
DIR_LM="dades/macocu/kenlm"
MODEL_LL="pipeline/03_seleccio_de_model/model_llengua"
DIR_KENLM="pipeline/08_traduccio_corpus/macocu/kenlm"
NOM="valencia_net_dogv"
read -r -a ORD <<< "${ORDRES:-6 7 8}"

# --- Comprovacions -----------------------------------------------------------
for f in "$DIR_LM/${NOM}_o5.binary" "$DIR_LM/${NOM}_freq.json"; do
    [[ -s "$f" ]] || { echo "Falta $f" >&2; exit 1; }
done
# El classificador del sistema: el general (sentit.json), on estiga.
SENTIT=""
for f in "$DIR_LM/sentit.json" "$DIR_LM/sentit/sentit.json"; do
    [[ -s "$f" ]] && { SENTIT="$f"; break; }
done
[[ -n "$SENTIT" ]] || { echo "Falta el classificador general ($DIR_LM/sentit.json)" >&2; exit 1; }
echo "Classificador: $SENTIT"
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -s "$DIR_LM/$NOM.txt" ]] || { echo "Falta $DIR_LM/$NOM.txt" >&2; exit 1; }
    [[ -x "$HOME/kenlm/build/bin/lmplz" ]] || { echo "Falta KenLM compilat en ~/kenlm" >&2; exit 1; }
else
    for o in "${ORD[@]}"; do
        [[ -s "$DIR_LM/${NOM}_o$o.binary" ]] || { echo "NOMES_COMPARA: falta $DIR_LM/${NOM}_o$o.binary" >&2; exit 1; }
    done
fi

# --- 1. Entrenaments ---------------------------------------------------------
JOBS=()
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    for o in "${ORD[@]}"; do
        J=$(cd "$DIR_KENLM" && TEXT="$DIR_LM/$NOM.txt" NOM="$NOM" ORDRE="$o" SENSE_FREQ=1 \
            sbatch --parsable --job-name="kenlm-o$o" entrena_kenlm.sh)
        echo "1. KenLM d'ordre $o:                       job $J"
        JOBS+=("$J")
    done
fi
DEP=()
if [[ ${#JOBS[@]} -gt 0 ]]; then
    DEP=(--dependency=afterok:"$(IFS=:; echo "${JOBS[*]}")")
fi

# --- 2. Comparació ------------------------------------------------------------
MODELS="kenlm_val_net_dogv_c1"
for o in "${ORD[@]}"; do MODELS+=" kenlm_o${o}_c1"; done
J2=$(cd "$MODEL_LL" && \
     MODELS="$MODELS" \
     EXTRA="--benchmarks homografs homografs_v2 manual --model-sentit $ARREL/$SENTIT --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --desempats 2 --detall" \
     sbatch --parsable --time=06:00:00 ${DEP[@]+"${DEP[@]}"} compara_models.sh)
echo "2. compara $MODELS:  job $J2${DEP:+ (després dels entrenaments)}"
echo
echo "Resultats: pipeline/03_seleccio_de_model/resultats/compara_models_*"
echo "Per a portar-los al PC (des de l'arrel del repo en el PC):"
echo "  scp \"nmartin@abaco:~/scrapeo/AVLizador/pipeline/03_seleccio_de_model/resultats/compara_models_*\" pipeline/03_seleccio_de_model/resultats/"
