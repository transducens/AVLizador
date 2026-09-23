"""
genera_lexic_mauri.py -- Converteix els fitxers bruts d'este directori
(acentuacion_cat_val.json, apertium-spa-cat.spa-cat_variantes.json) al
mateix esquema que lexico_fiable.json, PER A PROVAR el lexic del company
EN LLOC DEL nostre (no fusionat) amb evalua_models.py --lexic.

Filtres aplicats (nomes els imprescindibles -- este fitxer es per a
PROVAR, no es el lexic definitiu):
  - Noms propis (majuscula inicial): exclosos -- mai s'han de traduir.
  - Parelles identiques (valencia == catala): excloses -- no son una
    diferencia real.
  - NO es filtren els conflictes coneguts (blanca->garsa, roig->vermell,
    la->un quart...) a proposit: l'objectiu es vore com es comporta el
    model amb el lexic tal com l'ha entregat el company, per a decidir
    quines entrades val la pena quedar-se de veritat.

US:
    python genera_lexic_mauri.py
    (genera lexic_mauri.json en este mateix directori)

Despres, per a provar-lo AMB el benchmark real (no ho executa este
script, cal fer-ho a ma):
    cd ../../../03_seleccion_de_modelo
    python evalua_models.py --model ollama --ollama-model qwen2.5:14b ^
        --lexic "../02_reglas_dialectales/lexico/mauri/lexic_mauri.json"
"""

import json
from pathlib import Path

MAURI_DIR = Path(__file__).parent
MAURI_FILES = [
    "acentuacion_cat_val.json",
    "apertium-spa-cat.spa-cat_variantes.json",
]
OUTPUT = MAURI_DIR / "lexic_mauri.json"


def main():
    vist = {}
    per_fitxer = {}
    for nom_fitxer in MAURI_FILES:
        path = MAURI_DIR / nom_fitxer
        if not path.exists():
            print(f"AVIS: no trobat {path}, se salta.")
            continue
        dades = json.loads(path.read_text(encoding="utf-8"))
        comptador = 0
        for entrada in dades:
            val = entrada.get("valenciano", "").strip()
            cat = entrada.get("catalan") or entrada.get("catalán") or ""
            cat = cat.strip()
            if not val or not cat:
                continue
            if val[0].isupper():
                continue  # nom propi -- mai es tradueix (regla 10 del prompt)
            if val.lower() == cat.lower():
                continue  # identic -- no es una diferencia real
            clau = val.lower()
            if clau not in vist:
                vist[clau] = cat.lower()
                comptador += 1
        per_fitxer[nom_fitxer] = comptador

    entrades = [
        {
            "valenciano": [val],
            "catalan": [cat],
            "castellano": [],
            "categoria": "palabra",
            "origen": "mauri_sense_filtrar",
        }
        for val, cat in sorted(vist.items())
    ]

    resultat = {
        "total_entradas": len(entrades),
        "descripcion": (
            "Lexic exhaustiu recopilat per un company, NOMES filtrat de noms "
            "propis i parelles identiques -- NO revisat per conflictes "
            "d'homografs (blanca/roig/la/fem...). Fet per a PROVAR, no es "
            "el lexic fiable del pipeline (eixe es lexico_fiable.json, un "
            "nivell per damunt d'esta carpeta)."
        ),
        "entradas": entrades,
    }

    OUTPUT.write_text(json.dumps(resultat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Generat: {OUTPUT}")
    print(f"Total entrades: {len(entrades)}")
    for nom, n in per_fitxer.items():
        print(f"  {nom}: {n} entrades noves aportades")


if __name__ == "__main__":
    main()
