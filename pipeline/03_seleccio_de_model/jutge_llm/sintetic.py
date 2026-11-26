"""
sintetic.py -- benchmark sintètic del jutge (26/11/2026): `benchmark_sintetic.json`.

Parells de la mateixa frase en valencià correcte i amb un error posat a
propòsit. Mesura, abans i després del filtre de diccionari
(`nota_filtrada.py`):
- si el jutge marca l'error (algun tros toca `tros_error`);
- si deixa passar la versió correcta (cap tros);
- si la correcta trau més nota que l'errònia.

    python sintetic.py prepara                 # entrades_valencia/sintetic/{correcta,erronia}.json
    python sintetic.py analitza resultats/valencia/sintetic/qwen3.6-35b-a3b_pensa [--md f.md] [--json f.json]

`jutge_valencia.sh` amb `CONJUNTS=sintetic` fa el `prepara` i jutja les dos versions.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import nota_filtrada as nf  # noqa: E402

BENCH = AQUI / "benchmark_sintetic.json"


def frases() -> list[dict]:
    return json.loads(BENCH.read_text(encoding="utf-8"))["frases"]


def prepara(eixida: Path) -> None:
    eixida.mkdir(parents=True, exist_ok=True)
    for versio in ("correcta", "erronia"):
        res = [{"id": f["id"], "entrada": f["original"], "hipotesi": f[versio], "referencia": f["correcta"]}
               for f in frases()]
        (eixida / f"{versio}.json").write_text(json.dumps({"sistema": nf.NOMS[versio], "resultats": res},
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(res)} parells en {eixida}")


def paraules(t: str) -> set[str]:
    """
    >>> sorted(paraules("perquè arribes tard"))
    ['arribes', 'perquè', 'tard']
    """
    return {p for p in re.findall(r"[\w·-]+", t.lower().replace("’", "'")) if len(p) > 1}


def toca(spans: list[dict], hipotesi: str, tros_error: str) -> bool:
    """Algun tros marcat comparteix paraula amb el tros erroni.

    >>> toca([{"text": "La gasto"}], "La gasto total.", "La gasto")
    True
    >>> toca([{"text": "total"}], "La gasto total.", "La gasto")
    False
    >>> toca([{"text": "no"}], "L'ajuntament aprovarà el pressupost.", "aprovarà|no")
    True
    """
    for alt in tros_error.split("|"):  # omissions: també la paraula que falta
        obj = paraules(alt)
        for s in spans:
            a = nf.amplia_tros(s.get("text", ""), hipotesi) or s.get("text", "")
            if paraules(a) & obj:
                return True
    return False


def analitza(carpeta: Path) -> tuple[list[str], list[dict]]:
    c = {x["id"]: nf.filtra(x) for x in json.loads((carpeta / "correcta.json").read_text(encoding="utf-8"))["resultats"]}
    e = {x["id"]: nf.filtra(x) for x in json.loads((carpeta / "erronia.json").read_text(encoding="utf-8"))["resultats"]}
    files = []
    for f in frases():
        i = f["id"]
        if i not in c or i not in e:
            continue
        files.append({**f,
                      "c": c[i], "e": e[i],
                      "detecta": toca(e[i]["error_spans"], f["erronia"], f["tros_error"]),
                      "detecta_filtrat": toca(e[i]["spans_queden"], f["erronia"], f["tros_error"]),
                      "neta": not c[i]["error_spans"], "neta_filtrat": not c[i]["spans_queden"]})
    per = collections.defaultdict(list)
    for x in files:
        per[x["tipus"]].append(x)
    per["TOTAL"] = files
    L = ["| Tipus | Parells | Error marcat | Error marcat (filtre) | Correcta sense marques | Correcta sense marques (filtre) "
         "| Nota correcta / errònia (fase 2) | Correcta > errònia (fase 2) | Nota correcta / errònia (filtrada) | Correcta > errònia (filtrada) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for t, xs in per.items():
        n = len(xs)

        def m(k):
            return nf.mitjana([x[k[0]][k[1]] for x in xs])

        L.append(f"| {t} | {n} | {sum(x['detecta'] for x in xs)} | {sum(x['detecta_filtrat'] for x in xs)} | "
                 f"{sum(x['neta'] for x in xs)} | {sum(x['neta_filtrat'] for x in xs)} | "
                 f"{m(('c', 'nota'))} / {m(('e', 'nota'))} | {sum(x['c']['nota'] > x['e']['nota'] for x in xs)} | "
                 f"{m(('c', 'nota_filtrada'))} / {m(('e', 'nota_filtrada'))} | "
                 f"{sum(x['c']['nota_filtrada'] > x['e']['nota_filtrada'] for x in xs)} |")
    return L, files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="ordre", required=True)
    p = sub.add_parser("prepara")
    p.add_argument("--eixida", type=Path, default=AQUI / "entrades_valencia" / "sintetic")
    a = sub.add_parser("analitza")
    a.add_argument("carpeta", type=Path)
    a.add_argument("--md", type=Path)
    a.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    if args.ordre == "prepara":
        prepara(args.eixida)
        return 0
    L, files = analitza(args.carpeta)
    print("\n".join(L))
    if args.md:
        args.md.write_text("\n".join(L) + "\n", encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(files, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
