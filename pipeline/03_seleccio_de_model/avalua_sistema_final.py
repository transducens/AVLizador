"""Avalua el SISTEMA FINAL cat->val (motor + FLOR-760M) en tots els
benchmarks d'una vegada, amb totes les mètriques (exactes, BLEU, chrF,
chrF++, TER i WER), i escriu una taula resum.

Reutilitza `evalua_models.py` (mateixes mètriques, mateix JSON per
benchmark), però en un sol procés: FLOR es carrega una sola vegada.

Ús (des d'esta carpeta):

    python avalua_sistema_final.py                    # tots els benchmarks
    python avalua_sistema_final.py --benchmarks manual_boe manual_avl
    python avalua_sistema_final.py --amb-motor        # també el motor sol, per a comparar
    python avalua_sistema_final.py --limit 5          # prova ràpida (5 frases per benchmark)
    python avalua_sistema_final.py --llista           # mostra els benchmarks disponibles

Eixida en `resultats/`:
- `benchmark_sistema_final_<benchmark>_<data>.json` per benchmark (i
  `benchmark_motor_<benchmark>_<data>.json` amb `--amb-motor`);
- `resum_sistema_final_<data>.md`: la taula de tots, per a copiar-la a
  `resultats_benchmarks_cat_val.md`.

Mirar la columna "Errors" de la taula: si no és 0, alguna frase ha donat
una excepció i s'ha quedat sense traduir (compta com a fallada normal).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import evalua_models as em

AQUI = Path(__file__).resolve().parent
DADES = AQUI.parent.parent / "dades"

# nom curt -> (descripció, fitxer). L'orde és el de la taula resum.
BENCHMARKS = {
    "manual_boe":   ("Manual BOE (246)", DADES / "benchmark_manual" / "benchmark_manual_boe_cat_val.json"),
    "manual_avl":   ("Manual AVL (212)", DADES / "benchmark_manual" / "benchmark_manual_avl_cat_val.json"),
    "manual":       ("Manual mezcla BOE + AVL (458)", DADES / "benchmark_manual" / "benchmark_manual_cat_val.json"),
    "151":          ("151 (banco curado)", AQUI / "benchmark_corpus.json"),
    "homografs":    ("151 + homógrafos (253)", AQUI / "benchmark_sistema_final_cat_val.json"),
    "boe_estricte": ("BOE estricto, muestra (2.000)", DADES / "boe" / "benchmarks" / "benchmark_boe_dialectal_estricte.json"),
    "boe_ampli":    ("BOE amplio, muestra (2.000)", DADES / "boe" / "benchmarks" / "benchmark_boe_dialectal_ampli.json"),
    "gplsi":        ("gplsi (1.958)", DADES / "gplsi_ca_va_alignment_test" / "benchmark_gplsi.json"),
    "boe_estricte_complet": ("BOE estricto completo (9.453)", DADES / "boe" / "benchmarks" / "benchmark_boe_dialectal_estricte_complet.json"),
}
# El complet tarda molt i el seu mostreig ja està en `boe_estricte`: només si es demana.
PER_DEFECTE = [b for b in BENCHMARKS if b != "boe_estricte_complet"]

SISTEMES = {
    "sistema_final": ("Motor + FLOR-760M", em.tradueix_traductor_ml),
    "motor":         ("Motor solo", em.tradueix_traductor_invers),
}


def fila_markdown(descripcio: str, sistema: str, r: dict) -> str:
    """Una fila de la taula resum a partir del resum d'`avalua_model`.

    >>> r = {"exactes": 3, "n_frases": 4, "exactes_pct": 75.0, "bleu_mitja": 90.0,
    ...      "chrf_mitja": 95.0, "chrf_pp_mitja": 94.5, "ter_corpus": 2.5,
    ...      "wer_corpus": 3.0, "errors": 0}
    >>> fila_markdown("X", "Motor solo", r)
    '| X | Motor solo | 3/4 (75,0 %) | 90,00 | 95,00 | 94,50 | 2,50 | 3,00 | 0 |'
    """
    def n(x):
        return f"{x:.2f}".replace(".", ",")
    exactes = f"{r['exactes']}/{r['n_frases']} ({r['exactes_pct']:.1f} %)".replace(".", ",")
    return (f"| {descripcio} | {sistema} | {exactes} | {n(r['bleu_mitja'])} | "
            f"{n(r['chrf_mitja'])} | {n(r['chrf_pp_mitja'])} | {n(r['ter_corpus'])} | "
            f"{n(r['wer_corpus'])} | {r['errors']} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--benchmarks", nargs="+", choices=list(BENCHMARKS),
                        default=PER_DEFECTE, metavar="NOM",
                        help="Benchmarks a avaluar (per defecte, tots menys "
                             "boe_estricte_complet). --llista per a vore'ls.")
    parser.add_argument("--amb-motor", action="store_true",
                        help="Avalua també el motor sol (per a comparar).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Només les N primeres frases de cada benchmark (prova ràpida).")
    parser.add_argument("--llista", action="store_true",
                        help="Mostra els benchmarks disponibles i ix.")
    args = parser.parse_args()

    if args.llista:
        for nom, (descripcio, fitxer) in BENCHMARKS.items():
            estat = "" if fitxer.exists() else "  [NO EXISTIX]"
            marca = "" if nom in PER_DEFECTE else "  (només si es demana)"
            print(f"{nom:<22} {descripcio:<32} {fitxer}{estat}{marca}")
        return

    falten = [n for n in args.benchmarks if not BENCHMARKS[n][1].exists()]
    if falten:
        for n in falten:
            print(f"ERROR: no es troba el benchmark {n}: {BENCHMARKS[n][1]}")
        sys.exit(1)

    sistemes = ["sistema_final"] + (["motor"] if args.amb_motor else [])
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    files = []

    for nom in args.benchmarks:
        descripcio, fitxer = BENCHMARKS[nom]
        with open(fitxer, encoding="utf-8") as f:
            benchmark = json.load(f)
        if args.limit:
            benchmark = benchmark[:args.limit]
            descripcio += f" [limit {args.limit}]"

        for clau in sistemes:
            nom_sistema, funcio = SISTEMES[clau]
            resum = em.avalua_model(f"{nom_sistema} - {nom}", funcio, benchmark,
                                    delay=0.0, direccio="cat-val")
            resum["benchmark"] = str(fitxer)
            eixida = em.OUTPUT_DIR / f"benchmark_{clau}_{nom}_{ts}.json"
            with open(eixida, "w", encoding="utf-8") as f:
                json.dump(resum, f, ensure_ascii=False, indent=2)
            print(f"\nResultats guardats: {eixida}")
            files.append((fila_markdown(descripcio, nom_sistema, resum), eixida.name))

    capcalera = [
        f"## {datetime.now().strftime('%d/%m/%Y %H:%M')} — `avalua_sistema_final.py`",
        "",
        "| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | Errors |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    taula = capcalera + [f for f, _ in files] + ["", "Ficheros (`resultats/`):", ""]
    taula += [f"- `{nom_fitxer}`" for _, nom_fitxer in files]
    text = "\n".join(taula) + "\n"

    resum_path = em.OUTPUT_DIR / f"resum_sistema_final_{ts}.md"
    resum_path.write_text(text, encoding="utf-8")
    print("\n" + "=" * 70 + "\n" + text)
    print(f"Resum guardat: {resum_path}")


if __name__ == "__main__":
    main()
