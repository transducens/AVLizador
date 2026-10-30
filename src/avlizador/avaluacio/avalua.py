"""Avalua el traductor cat->val en els benchmarks de `dades/benchmarks/`
amb totes les mètriques (exactes, BLEU, chrF, chrF++, TER i WER) i escriu
una taula resum.

Per defecte avalua el sistema final (motor + FLOR-760M,
`translate_cat_val`); `--motor` hi afig el motor sol per a comparar.

    avlizador avalua                               # tots els benchmarks
    avlizador avalua --benchmarks manual           # el d'avaluació (mescla, 458)
    avlizador avalua --motor --limit 5             # prova ràpida
    avlizador avalua --llista                      # benchmarks disponibles
    avlizador avalua --fitxer un_benchmark.json    # un benchmark qualsevol

Els benchmarks no s'instal·len amb el paquet: es busquen en
`dades/benchmarks/` del repositori (des del directori actual cap amunt, o
en la variable d'entorn `AVLIZADOR_BENCHMARKS`). Format de cada benchmark:
llista de `{"id", "oriental", "occidental"}` (`oriental` = català,
l'entrada; `occidental` = valencià, la referència).

Eixida (en `--eixida`, per defecte `resultats_avaluacio/`): un JSON per
benchmark i sistema (`<sistema>_<benchmark>_<data>.json`, amb la traducció
i les mètriques de cada frase) i `resum_<data>.md` amb la taula. Si la
columna "Errors" no és 0, alguna frase ha donat una excepció i s'ha quedat
sense traduir (compta com a fallada).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .metriques import calcula_metriques, normalitza_apostrofa, ter_wer_corpus

# nom curt -> (descripció, ruta dins de dades/benchmarks/). L'orde és el de la taula.
BENCHMARKS = {
    "manual":       ("Manual mezcla BOE + AVL (458)", "manual/benchmark_manual_cat_val.json"),
    "manual_boe":   ("Manual BOE (246)", "manual/benchmark_manual_boe_cat_val.json"),
    "manual_avl":   ("Manual AVL (212)", "manual/benchmark_manual_avl_cat_val.json"),
    "151":          ("151 (banco curado)", "curat_151/benchmark_corpus.json"),
    "homografs":    ("151 + homógrafos (253)", "homografs/benchmark_sistema_final_cat_val.json"),
    "boe_estricte": ("BOE estricto, muestra (2.000)", "boe_dialectal/benchmark_boe_dialectal_estricte.json"),
    "boe_ampli":    ("BOE amplio, muestra (2.000)", "boe_dialectal/benchmark_boe_dialectal_ampli.json"),
    "gplsi":        ("gplsi (1.958)", "gplsi/benchmark_gplsi.json"),
    "boe_estricte_complet": ("BOE estricto completo (9.453)", "boe_dialectal/benchmark_boe_dialectal_estricte_complet.json"),
    "boe_ampli_complet":    ("BOE amplio completo (73.705)", "boe_dialectal/benchmark_boe_dialectal_ampli_complet.json"),
}
# Els complets tarden molt i el seu mostreig ja hi és: només si es demanen.
PER_DEFECTE = [b for b in BENCHMARKS if not b.endswith("_complet")]


def troba_dir_benchmarks() -> Path | None:
    """`AVLIZADOR_BENCHMARKS`, o el primer `dades/benchmarks/` des del
    directori actual cap amunt, o el del repositori si el paquet s'ha
    instal·lat en mode editable (`pip install -e .`)."""
    if os.environ.get("AVLIZADOR_BENCHMARKS"):
        return Path(os.environ["AVLIZADOR_BENCHMARKS"])
    for dir_ in (Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents):
        candidat = dir_ / "dades" / "benchmarks"
        if candidat.is_dir():
            return candidat
    return None


def sistemes(amb_motor: bool) -> list[tuple[str, str, callable]]:
    """(clau, nom, funció) de cada sistema a avaluar."""
    from ..traductor_cat_val import translate_cat_val, translate_cat_val_motor

    llista = [("sistema_final", "Motor + FLOR-760M", translate_cat_val)]
    if amb_motor:
        llista.append(("motor", "Motor solo", translate_cat_val_motor))
    return llista


def avalua_benchmark(funcio, benchmark: list[dict], verbose: bool = True) -> dict:
    """Traduïx cada frase (`oriental` -> `occidental`) i en calcula les
    mètriques; torna el resum i les frases.

    >>> r = avalua_benchmark(str.upper, [{"id": "a", "oriental": "x y", "occidental": "X Y"}],
    ...                      verbose=False)
    >>> r["exactes"], r["ter_corpus"], r["errors"]
    (1, 0.0, 0)
    """
    resultats, errors = [], 0
    for i, item in enumerate(benchmark, 1):
        entrada = normalitza_apostrofa(item["oriental"])
        referencia = normalitza_apostrofa(item["occidental"])
        try:
            hipotesi = funcio(entrada)
        except Exception as exc:  # la frase compta com a fallada, no para l'avaluació
            print(f"  ERROR en {item['id']}: {exc}", file=sys.stderr)
            hipotesi, errors = entrada, errors + 1
        metriques = calcula_metriques(hipotesi, referencia)
        resultats.append({"id": item["id"], "entrada": entrada, "referencia": referencia,
                          "hipotesi": hipotesi, **metriques})
        if verbose and (i % 100 == 0 or i == len(benchmark)):
            print(f"  {i}/{len(benchmark)}", file=sys.stderr)

    n = len(resultats)
    exactes = sum(r["exacte"] for r in resultats)
    return {
        "n_frases":      n,
        "errors":        errors,
        "exactes":       exactes,
        "exactes_pct":   round(exactes / n * 100, 1) if n else 0.0,
        "bleu_mitja":    round(sum(r["bleu"] for r in resultats) / n, 2) if n else 0.0,
        "chrf_mitja":    round(sum(r["chrf"] for r in resultats) / n, 2) if n else 0.0,
        "chrf_pp_mitja": round(sum(r["chrf_pp"] for r in resultats) / n, 2) if n else 0.0,
        "ter_corpus":    ter_wer_corpus(resultats, "ter_edicions"),
        "wer_corpus":    ter_wer_corpus(resultats, "wer_edicions"),
        "resultats":     resultats,
    }


def fila_markdown(descripcio: str, sistema: str, r: dict) -> str:
    """Una fila de la taula resum.

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="avlizador avalua",
        description="Avalua el traductor cat->val en els benchmarks de dades/benchmarks/.",
    )
    parser.add_argument("--benchmarks", nargs="+", choices=list(BENCHMARKS), metavar="NOM",
                        help="Benchmarks a avaluar (per defecte, tots menys els *_complet). "
                             "--llista per a vore'ls.")
    parser.add_argument("--fitxer", type=Path, action="append", default=[],
                        help="Un benchmark JSON qualsevol (es pot repetir).")
    parser.add_argument("--motor", action="store_true", help="Avalua també el motor sol.")
    parser.add_argument("--limit", type=int, help="Només les N primeres frases de cada benchmark.")
    parser.add_argument("--eixida", type=Path, default=Path("resultats_avaluacio"),
                        help="Carpeta dels resultats (per defecte, resultats_avaluacio/).")
    parser.add_argument("--llista", action="store_true", help="Mostra els benchmarks i ix.")
    args = parser.parse_args(argv)

    dir_bench = troba_dir_benchmarks()
    if args.llista:
        print(f"Carpeta: {dir_bench or '(no trobada: AVLIZADOR_BENCHMARKS)'}")
        for nom, (descripcio, ruta) in BENCHMARKS.items():
            existix = dir_bench is not None and (dir_bench / ruta).exists()
            marca = "" if nom in PER_DEFECTE else "  (només si es demana)"
            print(f"{nom:<22} {descripcio:<32} {ruta}{'' if existix else '  [NO EXISTIX]'}{marca}")
        return 0

    tasques = []  # (nom curt, descripció, fitxer)
    noms = args.benchmarks or ([] if args.fitxer else PER_DEFECTE)
    if noms and dir_bench is None:
        print("ERROR: no es troba dades/benchmarks/ (executa des del repositori o "
              "defineix AVLIZADOR_BENCHMARKS).", file=sys.stderr)
        return 1
    for nom in noms:
        descripcio, ruta = BENCHMARKS[nom]
        tasques.append((nom, descripcio, dir_bench / ruta))
    for fitxer in args.fitxer:
        tasques.append((fitxer.stem, fitxer.name, fitxer))
    falten = [str(f) for _, _, f in tasques if not f.exists()]
    if falten:
        print("ERROR: no es troben: " + ", ".join(falten), file=sys.stderr)
        return 1

    args.eixida.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    files = []
    for nom, descripcio, fitxer in tasques:
        benchmark = json.loads(fitxer.read_text(encoding="utf-8"))
        if args.limit:
            benchmark = benchmark[:args.limit]
            descripcio += f" [limit {args.limit}]"
        for clau, nom_sistema, funcio in sistemes(args.motor):
            print(f"\n{nom_sistema} - {descripcio}", file=sys.stderr)
            resum = avalua_benchmark(funcio, benchmark)
            resum = {"sistema": nom_sistema, "benchmark": str(fitxer),
                     "timestamp": datetime.now().isoformat(), **resum}
            eixida = args.eixida / f"{clau}_{nom}_{ts}.json"
            eixida.write_text(json.dumps(resum, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append((fila_markdown(descripcio, nom_sistema, resum), eixida.name))

    text = "\n".join([
        f"## {datetime.now().strftime('%d/%m/%Y %H:%M')} — `avlizador avalua`",
        "",
        "| Benchmark | Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | Errors |",
        "|---|---|---|---|---|---|---|---|---|",
        *[f for f, _ in files],
        "",
        f"Ficheros (`{args.eixida}`):",
        "",
        *[f"- `{nom_fitxer}`" for _, nom_fitxer in files],
    ]) + "\n"
    resum_path = args.eixida / f"resum_{ts}.md"
    resum_path.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"Resum guardat: {resum_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
