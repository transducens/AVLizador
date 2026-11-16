#!/bin/bash
# prova_corpus.sh -- Llança en Abaco la prova de MÉS TEXT per al KenLM i per al
# classificador de sentit (16/11/2026, petició de l'usuari per a la versió
# 2.0.0). El sistema d'ara: KenLM `valencia_net_dogv` (MaCoCu net + DOGV de
# 10.289 documents) + classificador `sentit.json` (net + DOGV, sense AVL).
#
# KenLM (ordre 5, mateixa poda), cadascun amb la seua taula de freqüències:
#   valencia_net_dogv2          MaCoCu net + el DOGV nou sencer (15.702 documents)
#   valencia_net_dogv2_avl      ídem + la AVL
#   valencia_net_dogv2_avl_ua   ídem + les notícies de la UA (frases de GD >= 0,8)
# Classificador de sentit (`sentit_general.py`, mateixos paràmetres):
#   sentit_dogv2                net + DOGV nou
#   sentit_dogv2_avl            net + DOGV nou + AVL
#
# Res dels benchmarks: `prepara_dogv.py` lleva del DOGV les frases dels
# benchmarks, i `termes_ambigus.py` lleva de la AVL els documents del 151 i del
# manual i qualsevol frase semblant (Jaccard >= 0,6) a una del manual, del 151 o
# dels homògrafs.
#
# NO és un job: s'executa en el node de login i encua:
#   1. entrena_kenlm.sh, un per variant de KenLM.
#   2. sentit_general.py entrena, un per classificador nou (job de CPU).
#   3. compara_models.sh, un per classificador (l'actual i els nous), cadascun
#      amb els quatre KenLM (el del sistema i les tres variants): 3 x 4
#      combinacions. Homògrafs v1 i v2, manual i 151, sense FLOR ni el motor;
#      graella de marges i λ i el detall de cada decisió. L'eixida porta el nom
#      del classificador: compara_models_<data>_<classificador>.{md,json}.
#
# Fitxers que han d'estar en Abaco (es generen en local i es pugen amb scp; vore
# documentacio/resultats_model_llengua_kenlm.md, secció 4.19):
#   dades/macocu/kenlm/valencia_net.txt          (ja hi és)
#   dades/macocu/valencia/valencia.jsonl         (ja hi és; el classificador hi llig el MaCoCu net)
#   dades/dogv_apunt/nova/dogv_net.txt           (prepara_dogv.py sobre el DOGV nou)
#   dades/macocu/kenlm/termes/avl_net.txt        (termes_ambigus.py)
#   dades/macocu/kenlm/termes/ua_net.txt         (termes_ambigus.py)
#
# Ús (des de ~/scrapeo/AVLizador, amb la branca `kenlm-2.0` al dia):
#   bash pipeline/03_seleccio_de_model/model_llengua/prova_corpus.sh
#   VARIANTS="valencia_net_dogv2" CLASSIFICADORS="sentit_dogv2" bash .../prova_corpus.sh
#   NOMES_COMPARA=1 bash .../prova_corpus.sh      # ja està tot entrenat: només el pas 3
#   SENSE_KENLM=1 ESPERA="3129:3130:3131" bash .../prova_corpus.sh
#       # els KenLM ja estan en cua (jobs 3129-3131): només els classificadors i
#       # les comparacions, que esperen també a eixos jobs
# Mirar com van: squeue -u $USER; els .out queden en la carpeta de cada script.
# Disc: cada .arpa fa uns quants GB; quan el .binary funcione, es pot esborrar.

set -euo pipefail

ARREL="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ARREL"
echo "Repo: $ARREL ($(git log -1 --format='%h %s'), branca $(git branch --show-current))"
DIR_LM="dades/macocu/kenlm"
MODEL_LL="pipeline/03_seleccio_de_model/model_llengua"
DIR_KENLM="pipeline/08_traduccio_corpus/macocu/kenlm"
VENV="${VENV:-$HOME/venvs/avlizador}"
NET="${NET:-$DIR_LM/valencia_net.txt}"
DOGV2="${DOGV2:-dades/dogv_apunt/nova/dogv_net.txt}"
AVL="${AVL:-$DIR_LM/termes/avl_net.txt}"
UA="${UA:-$DIR_LM/termes/ua_net.txt}"
read -r -a VAR <<< "${VARIANTS:-valencia_net_dogv2 valencia_net_dogv2_avl valencia_net_dogv2_avl_ua}"
read -r -a CLS <<< "${CLASSIFICADORS:-sentit_dogv2 sentit_dogv2_avl}"

# Els textos de cada variant de KenLM, en ordre.
fonts() {
    case "$1" in
        valencia_net_dogv2) echo "$NET $DOGV2" ;;
        valencia_net_dogv2_avl) echo "$NET $DOGV2 $AVL" ;;
        valencia_net_dogv2_avl_ua) echo "$NET $DOGV2 $AVL $UA" ;;
        *) echo "Variant desconeguda: $1" >&2; exit 1 ;;
    esac
}
# Clau del comparador de cada variant.
clau() {
    case "$1" in
        valencia_net_dogv2) echo kenlm_dogv2_c1 ;;
        valencia_net_dogv2_avl) echo kenlm_dogv2_avl_c1 ;;
        valencia_net_dogv2_avl_ua) echo kenlm_dogv2_avl_ua_c1 ;;
    esac
}
# Fonts de sentit_general.py de cada classificador.
fonts_sentit() {
    case "$1" in
        sentit_dogv2) echo "net dogv2" ;;
        sentit_dogv2_avl) echo "net dogv2 avl" ;;
        *) echo "Classificador desconegut: $1" >&2; exit 1 ;;
    esac
}

# --- Comprovacions -----------------------------------------------------------
for f in "$DIR_LM/valencia_net_dogv_o5.binary" "$DIR_LM/valencia_net_dogv_freq.json"; do
    [[ -s "$f" ]] || { echo "Falta $f (el sistema, per a comparar)" >&2; exit 1; }
done
SENTIT=""
for f in "$DIR_LM/sentit.json" "$DIR_LM/sentit/sentit.json"; do
    [[ -s "$f" ]] && { SENTIT="$f"; break; }
done
[[ -n "$SENTIT" ]] || { echo "Falta el classificador del sistema ($DIR_LM/sentit.json)" >&2; exit 1; }
echo "Classificador del sistema: $SENTIT"
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -n "${SENSE_KENLM:-}" ]] || for v in "${VAR[@]}"; do
        for f in $(fonts "$v"); do
            [[ -s "$f" ]] || { echo "Falta $f (per a $v)" >&2; exit 1; }
        done
    done
    for c in "${CLS[@]}"; do fonts_sentit "$c" > /dev/null; done
    [[ ${#CLS[@]} -eq 0 || -s dades/macocu/valencia/valencia.jsonl ]] || {
        echo "Falta dades/macocu/valencia/valencia.jsonl (per als classificadors)" >&2; exit 1; }
    [[ -n "${SENSE_KENLM:-}" || -x "$HOME/kenlm/build/bin/lmplz" ]] || { echo "Falta KenLM compilat en ~/kenlm" >&2; exit 1; }
else
    for v in "${VAR[@]}"; do
        for f in "$DIR_LM/${v}_o5.binary" "$DIR_LM/${v}_freq.json"; do
            [[ -s "$f" ]] || { echo "NOMES_COMPARA: falta $f" >&2; exit 1; }
        done
    done
    for c in "${CLS[@]}"; do
        [[ -s "$DIR_LM/sentit/$c.json" ]] || { echo "NOMES_COMPARA: falta $DIR_LM/sentit/$c.json" >&2; exit 1; }
    done
fi

# --- 1. KenLM: textos i entrenaments --------------------------------------------
JOBS=()
if [[ -z "${NOMES_COMPARA:-}" ]]; then
    [[ -n "${SENSE_KENLM:-}" ]] || for v in "${VAR[@]}"; do
        # shellcheck disable=SC2046
        cat $(fonts "$v") > "$DIR_LM/$v.txt"
        echo "   $v.txt: $(wc -l < "$DIR_LM/$v.txt") frases ($(fonts "$v"))"
        J=$(cd "$DIR_KENLM" && TEXT="$DIR_LM/$v.txt" NOM="$v" \
            sbatch --parsable --job-name="kenlm-$v" entrena_kenlm.sh)
        echo "1. KenLM $v:   job $J"
        JOBS+=("$J")
    done

# --- 2. Classificadors de sentit ------------------------------------------------
    for c in "${CLS[@]}"; do
        J=$(sbatch --parsable --job-name="$c" --cpus-per-task=2 --mem=16G --time=03:00:00 \
            --output="$MODEL_LL/%j_$c.out" \
            --wrap="cd $ARREL && PYTHONIOENCODING=utf-8 $VENV/bin/python -u $MODEL_LL/sentit_general.py entrena --fonts $(fonts_sentit "$c") --nom $c")
        echo "2. Classificador $c ($(fonts_sentit "$c")):   job $J"
        JOBS+=("$J")
    done
fi
# Jobs d'abans que també cal esperar (p. ex. els KenLM ja en cua: ESPERA="3129:3130:3131").
[[ -n "${ESPERA:-}" ]] && JOBS+=("$ESPERA")
DEP=()
if [[ ${#JOBS[@]} -gt 0 ]]; then
    DEP=(--dependency=afterok:"$(IFS=:; echo "${JOBS[*]}")")
fi

# --- 3. Comparació: un job per classificador ------------------------------------
MODELS="kenlm_val_net_dogv_c1"
for v in "${VAR[@]}"; do MODELS+=" $(clau "$v")"; done
for c in sentit "${CLS[@]}"; do
    if [[ "$c" == sentit ]]; then FITXER="$ARREL/$SENTIT"; else FITXER="$ARREL/$DIR_LM/sentit/$c.json"; fi
    J3=$(cd "$MODEL_LL" && \
         MODELS="$MODELS" \
         EXTRA="--benchmarks homografs homografs_v2 manual 151 --model-sentit $FITXER --etiqueta $c --marges 1 2 3 5 --per-defecte catala --lams 0.5 1 1.5 2 --lams-colisio 0.5 0.75 1 --desempats 2 --detall" \
         sbatch --parsable --time=06:00:00 --job-name="compara-$c" ${DEP[@]+"${DEP[@]}"} compara_models.sh)
    echo "3. compara ($c): $MODELS   job $J3${DEP:+ (després dels entrenaments)}"
done
echo
echo "Resultats: pipeline/03_seleccio_de_model/resultats/compara_models_<data>_<classificador>{,_detall}.{md,json}"
