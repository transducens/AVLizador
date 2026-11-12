"""
exporta_text.py -- Passa MaCoCu-ca 1.0 SENCER (sense filtre de GD ni de
qualitat) a text pla per a entrenar KenLM: una frase per línia,
normalitzada amb `normalitza` (09/11/2026, primera prova de substituir
FLOR per KenLM).

Normalització (la MATEIXA s'ha d'aplicar a les frases que puntue el
model després; per això està en una funció a banda, des del 12/11/2026 en el
paquet: `avlizador.traductor_cat_val.model_llengua.kenlm.normalitza`, que
este fitxer reexporta per als scripts que la importen d'ací):
- minúscules; apòstrof tipogràfic (’ ʼ) -> ';
- l'apòstrof queda pegat a la paraula d'abans ("d'una" -> "d' una");
- els números, a "0" (menys vocabulari);
- la puntuació, separada en tokens.

Per defecte entra TOT: qualsevol qualitat jusText, títols inclosos. Només
es lleven els paràgrafs d'un altre idioma (`lang` distint de "ca" i de
"?"; els "short" no tenen idioma) i les frases de menys de 3 tokens.
`--nomes-bons` deixa només els paràgrafs `good` en català.

`--jsonl FITXER` (10/11/2026) llig les frases d'un JSONL (camp `text`) en
lloc del XML: per a entrenar el KenLM valencià amb
`dades/macocu/valencia/valencia.jsonl` (decisió de l'usuari: totes, GD >
0,5 amb >= 1 marcador). `--min-gd` i `--min-marcadors` (camps `gd` i
`occ`) filtren si cal.

`--marcadors-doc N` (10/11/2026, segon KenLM valencià, més net): una frase
entra si té >= N marcadors occidentals o si el seu DOCUMENT té alguna frase
amb >= N (una web que sí que escriu en valencià). Motiu
(`dades/macocu/valencia/analisi_valencia.md`): el 84 % de les frases
d'`valencia.jsonl` només tenen 1 marcador, quasi sempre fals ("vegada",
"permet", "pertany"...). Amb N = 2: 457.963 + 753.241 = 1.211.204 frases.

Ús (des de l'arrel del repositori):
    python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py --processos 8
    python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py --limit-mb 50   # prova
    python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py         --jsonl dades/macocu/valencia/valencia.jsonl --eixida dades/macocu/kenlm/valencia.txt
    python pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py --marcadors-doc 2 \
        --jsonl dades/macocu/valencia/valencia.jsonl --eixida dades/macocu/kenlm/valencia_net.txt
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comu import DIR, XML, _SEPARA, paragrafs  # noqa: E402

EIXIDA = DIR / "kenlm" / "macocu_tot.txt"
MIN_TOKENS = 3

from avlizador.traductor_cat_val.model_llengua.kenlm import normalitza  # noqa: E402,F401  (una sola font)


def _lot(paragrafs_: list[str]) -> tuple[list[str], int]:
    linies, curtes = [], 0
    for text in paragrafs_:
        for frase in _SEPARA.split(text):
            n = normalitza(frase)
            if n.count(" ") + 1 < MIN_TOKENS:
                curtes += 1
                continue
            linies.append(n)
    return linies, curtes


def _frases_jsonl(args, est: Counter):
    """Com `paragrafs`, però des d'un JSONL de frases (`--jsonl`). Amb
    `--marcadors-doc N`, una primera passada apunta els documents amb alguna
    frase de >= N marcadors."""
    docs_bons: set = set()
    if args.marcadors_doc:
        with open(args.jsonl, encoding="utf-8") as f:
            for linia in f:
                r = json.loads(linia)
                if r.get("occ", 0) >= args.marcadors_doc:
                    docs_bons.add(r.get("doc"))
        est["documents_amb_frase_de_n_marcadors"] = len(docs_bons)
    with open(args.jsonl, encoding="utf-8") as f:
        for linia in f:
            r = json.loads(linia)
            if (args.min_gd is not None and r.get("gd", 1.0) < args.min_gd) or r.get("occ", 0) < args.min_marcadors:
                est["jsonl_filtrades"] += 1
                continue
            if args.marcadors_doc:
                if r.get("occ", 0) >= args.marcadors_doc:
                    est["jsonl_per_la_frase"] += 1
                elif r.get("doc") in docs_bons:
                    est["jsonl_pel_document"] += 1
                else:
                    est["jsonl_filtrades"] += 1
                    continue
            yield None, {"lang": "ca"}, r["text"]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--eixida", type=Path, default=EIXIDA)
    p.add_argument("--processos", type=int, default=max(1, mp.cpu_count() - 1))
    p.add_argument("--lot", type=int, default=5000, help="paràgrafs per lot")
    p.add_argument("--nomes-bons", action="store_true", help="només paràgrafs good en català")
    p.add_argument("--limit-mb", type=int, default=0, help="llegir només els primers N MB (proves)")
    p.add_argument("--jsonl", type=Path, help="frases d'un JSONL (camp text) en lloc del XML")
    p.add_argument("--min-gd", type=float, default=None, help="amb --jsonl: GD mínim (camp gd)")
    p.add_argument("--min-marcadors", type=int, default=0, help="amb --jsonl: marcadors mínims (camp occ)")
    p.add_argument("--marcadors-doc", type=int, default=0,
                   help="amb --jsonl: >= N marcadors en la frase o en alguna frase del document")
    args = p.parse_args(argv)

    args.eixida.parent.mkdir(parents=True, exist_ok=True)
    est: Counter = Counter()
    limit = args.limit_mb * 1_000_000 if args.limit_mb else None
    t0 = time.time()

    def escriu(res, out) -> None:
        linies, curtes = res
        est["frases"] += len(linies)
        est["frases_curtes_llevades"] += curtes
        est["tokens"] += sum(l.count(" ") + 1 for l in linies)
        if linies:
            out.write("\n".join(linies) + "\n")

    # S'escriu en un `.part` i només es renomena en acabar: si el job es talla,
    # no queda un text a mitges amb el nom bo (10/11/2026: el job 2943 es va
    # tallar al 30 % i el següent el va donar per bo i va entrenar amb ell).
    part = args.eixida.with_name(args.eixida.name + ".part")
    with mp.Pool(args.processos) as pool, open(part, "w", encoding="utf-8") as out:
        lot: list[str] = []
        pendents = []
        for _, par, text in (_frases_jsonl(args, est) if args.jsonl else paragrafs(XML, limit)):
            est["paragrafs"] += 1
            lang = par.get("lang", "?")
            if args.nomes_bons and not (par.get("quality") == "good" and lang == "ca"):
                continue
            if lang not in ("ca", "?"):
                est["paragrafs_altre_idioma"] += 1
                continue
            lot.append(text)
            if len(lot) >= args.lot:
                pendents.append(pool.apply_async(_lot, (lot,)))
                lot = []
                while len(pendents) > args.processos * 2:
                    escriu(pendents.pop(0).get(), out)
            if est["paragrafs"] % 2_000_000 == 0:
                print(f"  {est['paragrafs']:,} paràgrafs, {est['frases']:,} frases, "
                      f"{est['tokens']:,} tokens, {time.time() - t0:,.0f} s", flush=True)
        if lot:
            pendents.append(pool.apply_async(_lot, (lot,)))
        for r in pendents:
            escriu(r.get(), out)
    part.replace(args.eixida)
    est["segons"] = round(time.time() - t0)
    resum = {"nomes_bons": args.nomes_bons, "limit_mb": args.limit_mb, "jsonl": str(args.jsonl or ""),
             "min_gd": args.min_gd, "min_marcadors": args.min_marcadors,
             "marcadors_doc": args.marcadors_doc, **est}
    args.eixida.with_suffix(".json").write_text(json.dumps(resum, indent=2), encoding="utf-8")
    print(json.dumps(resum, indent=2))


if __name__ == "__main__":
    main()
