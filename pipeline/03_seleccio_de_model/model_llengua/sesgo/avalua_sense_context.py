"""
avalua_sense_context.py -- El mateix que `avalua_sistema_final.py` (totes
els benchmarks, totes les mètriques), però amb FLOR SENSE el paràgraf de
context (`ModelLlengua(context=None)`, el sistema d'abans del 03/11/2026).
Servix de referència per a comparar amb el sistema amb P1 en el mateix
equip i el mateix dia. Mateixes opcions que `avlizador avalua`:

    python avalua_sense_context.py --eixida resultats/sense_context
"""

import sys

from avlizador.avaluacio.avalua import main
from avlizador.traductor_cat_val import model_llengua
from avlizador.traductor_cat_val.model_llengua.puntuador import ModelLlengua

if __name__ == "__main__":
    model_llengua._MODEL_PER_DEFECTE = ModelLlengua(context=None)
    sys.exit(main(sys.argv[1:]))
