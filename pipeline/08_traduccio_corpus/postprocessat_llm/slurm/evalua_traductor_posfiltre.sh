#!/bin/bash
# evalua_traductor_posfiltre.sh -- Job de SLURM NOMES CPU (sense GPU): corre
# la suite de doctests + `03_seleccio_de_model/evalua_models.py --model
# traductor` per a validar canvis al motor de `traductor/` abans de fer
# commit. Usat per primera vegada per al filtre POS (07/10/2026, vore
# traductor/README.md "DECISIO D'ARQUITECTURA"); reutilitzat el
# 08/10/2026 per a validar dos/dues capa 2, elisio "de"->"d'" i
# concordança de gènere tras substitució lèxica (vore CLAUDE_HISTORIAL.md).
#
# A diferencia de la resta de scripts d'esta carpeta, este NO necessita
# Ollama ni GPU -- nomes el motor de regles de `traductor/` + spaCy
# (CPU, ~11 ms/frase mesurat en local). Nomes necessita que
# ~/scrapeo/postprocesado_llm/ ja tinga `traductor/` i
# `03_seleccio_de_model/benchmark_corpus.json` (ja hi son, pujats en
# sessions anteriors per als scripts de benchmark_integrat.py).
#
# FITXERS A PUJAR abans de llançar-ho (08/10/2026 -- dos/dues capa 2,
# elisio "de"->"d'", concordança de gènere; vore CLAUDE_HISTORIAL.md):
#   traductor/rules/__init__.py              (modificat: Token.gender,
#                                              corregeix_elisio_de_abans)
#   traductor/rules/pos_tagger.py            (modificat: omple gender)
#   traductor/rules/concordanca_dos_dues.py  (modificat: capa 2 spaCy)
#   traductor/rules/conjugacions_dict.py     (modificat: crida elisio)
#   traductor/rules/lexic.py                 (modificat: concordança genere)
#   traductor/data/canvi_genere_lexic_avl.json (NOU)
#   traductor/data/conjugacions_dialectals.json (resincronitzat abans
#                                              d'avui -- calfar/escalfar,
#                                              vetlar/vetllar -- pujar per
#                                              si Abaco encara te la versio
#                                              vella)
#
#   ssh nmartin@abaco "mkdir -p ~/scrapeo/postprocesado_llm/traductor/rules ~/scrapeo/postprocesado_llm/traductor/data"
#   scp traductor/rules/__init__.py traductor/rules/pos_tagger.py \
#       traductor/rules/concordanca_dos_dues.py traductor/rules/conjugacions_dict.py \
#       traductor/rules/lexic.py \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/traductor/rules/
#   scp traductor/data/canvi_genere_lexic_avl.json \
#       traductor/data/conjugacions_dialectals.json \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/traductor/data/
#   scp 08_traduccio_corpus/postprocessat_llm/slurm/evalua_traductor_posfiltre.sh \
#       nmartin@abaco:~/scrapeo/postprocesado_llm/08_traduccio_corpus/postprocessat_llm/slurm/
#
# Lanzarlo (des del node de login d'Abaco):
#   cd ~/scrapeo/postprocesado_llm/08_traduccio_corpus/postprocessat_llm/slurm
#   # (si eixa carpeta no existix allà, puja este script a qualsevol lloc
#   # dins de ~/scrapeo/postprocesado_llm/ i ajusta POSTPROC_DIR a mà)
#   sbatch evalua_traductor_posfiltre.sh

#SBATCH --job-name=eval-traductor-pos
#SBATCH --output=%j_eval_traductor_pos.out
#SBATCH --error=%j_eval_traductor_pos.err
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
# #SBATCH --partition=cpu            # CAMBIA-ESTO si el teu cluster ho exigix
# #SBATCH --account=TU_CUENTA        # CAMBIA-ESTO si el teu cluster ho exigix

set -euo pipefail

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
# POSTPROC_DIR = carpeta plana d'Abaco que conte traductor/,
# 02_regles_dialectals/ i 03_seleccio_de_model/ -- vore CLAUDE.md,
# seccio "Ejecucion en el cluster SLURM Abaco", per al perque este camí
# es distint de la resta de l'estructura numerada local.
POSTPROC_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
if [ ! -d "$POSTPROC_DIR/traductor" ]; then
    # Fallback si este script s'ha pujat solt en un atre lloc dins de
    # ~/scrapeo/postprocesado_llm/ -- ajusta esta linia a mà si cal.
    POSTPROC_DIR="$HOME/scrapeo/postprocesado_llm"
fi
echo "POSTPROC_DIR=$POSTPROC_DIR"

echo "Instal·lant/comprovant spaCy + model de catala (ca_core_news_sm)..."
# Vore benchmark_integrat_posfiltre.sh per a l'explicacio completa de
# PIP_BREAK_SYSTEM_PACKAGES (PEP 668, "externally-managed-environment").
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q spacy
python3 -m spacy download ca_core_news_sm -q || python3 -m pip install -q \
    https://github.com/explosion/spacy-models/releases/download/ca_core_news_sm-3.8.0/ca_core_news_sm-3.8.0-py3-none-any.whl

echo ""
echo "Corrent la suite de doctests de traductor/ (244 tests esperats en local, 0 fallos)..."
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
    print(f'{m}: {r.attempted} tests, {r.failed} fallos')
print()
print(f'TOTAL: {tt} tests, {tf} fallos')
"

echo ""
echo "Corrent el benchmark complet (evalua_models.py --model traductor)..."
cd "$POSTPROC_DIR/03_seleccio_de_model"
python3 evalua_models.py --model traductor

echo ""
echo "Fet. Compara el 'Exactes: N/151' de dalt amb el baseline conegut: 109/151"
echo "abans dels canvis d'avui, 114/151 (75,5%) BLEU 97,54 esperat amb els 3"
echo "fixes nous (dos/dues capa 2, elisio 'de'->'d'', concordança de genere)"
echo "-- vore CLAUDE.md i CLAUDE_HISTORIAL.md."
