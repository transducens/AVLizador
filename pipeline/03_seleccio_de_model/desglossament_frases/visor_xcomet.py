"""Visor HTML de XCOMET-XL sense referència (mode qe) per a un sistema, frase a frase.

No cal el jutge: llig `../comet/resultats/<sistema>__XCOMET-XL_qe.json` i, per
comparar, els dels altres sistemes. A cada frase hi afig el GD de l'eixida
(formes valencianes / catalanes del lèxic) i les paraules que la diferencien
de la referència, i classifica cada tros d'error com en `desglossa_frases.py`.

    python visor_xcomet.py
    python visor_xcomet.py --sistema avlizador_1.1.0 --compara copia referencia

Eixida: `resultats/xcomet_<sistema>.html` (sense dependències).
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from desglossa_frases import AQUI, DIR_COMET, amplia_tros, classifica_tros, nom, subconjunt

COMPARA_PER_DEFECTE = ["copia", "referencia", "avlizador_1.1.0", "ollama_gemma3-12b"]


def llig_qe(sistema: str) -> dict[str, dict] | None:
    fitxer = DIR_COMET / f"{sistema}__XCOMET-XL_qe.json"
    if not fitxer.exists():
        print(f"AVÍS: no hi ha {fitxer.name}; el sistema {sistema} es deixa fora.", file=sys.stderr)
        return None
    return {r["id"]: r for r in json.loads(fitxer.read_text(encoding="utf-8"))["resultats"]}


def trossos(r: dict, val: set[str], cat: set[str]) -> list[dict]:
    eix = []
    for t in r.get("error_spans") or []:
        text = t.get("text", "")
        ampliat = amplia_tros(text, r["hipotesi"])
        eix.append({"text": text, "sev": t.get("severity", "?"),
                    "conf": round(t.get("confidence", 0.0), 2),
                    "classe": classifica_tros(text, r["hipotesi"], val, cat),
                    # La paraula sencera, si XCOMET n'ha marcat només un tros.
                    "paraula": ampliat if ampliat and ampliat.lower() != text.strip().lower() else None})
    return eix


def diferencies(ref: str, hip: str) -> list[list]:
    """La referència partida en trossos [text, és_diferent] respecte de la traducció."""
    a, b = ref.split(), hip.split()
    eix = []
    for op, i1, i2, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if i2 > i1:
            eix.append([" ".join(a[i1:i2]), op != "equal"])
    return eix


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sistema", default="avlizador_2.0.0")
    ap.add_argument("--compara", nargs="*", default=COMPARA_PER_DEFECTE)
    ap.add_argument("--eixida", type=Path, default=AQUI / "resultats")
    args = ap.parse_args(argv)

    from avlizador.grau_dialectal.gd import calcula_gd

    principal = llig_qe(args.sistema)
    if principal is None:
        return 1
    compara = {s: d for s in args.compara if s != args.sistema and (d := llig_qe(s)) is not None}

    frases = []
    for i, r in sorted(principal.items()):
        g = calcula_gd(r["hipotesi"])
        val, cat = set(g["marcadors_occidentals"]), set(g["marcadors_orientals"])
        comp = {}
        for s, d in compara.items():
            c = d.get(i)
            if c is None:
                continue
            gc = calcula_gd(c["hipotesi"])
            vc, cc = set(gc["marcadors_occidentals"]), set(gc["marcadors_orientals"])
            comp[s] = {"h": c["hipotesi"], "x": c["comet"], "tr": trossos(c, vc, cc),
                       "mv": sorted(vc), "mc": sorted(cc)}
        frases.append({
            "id": i, "sub": subconjunt(i), "entrada": r["entrada"], "referencia": r["referencia"],
            "hip": r["hipotesi"], "x": r["comet"], "gd": g["gd"],
            "igual": " ".join(r["hipotesi"].split()) == " ".join(r["referencia"].split()),
            "refdif": diferencies(r["referencia"], r["hipotesi"]),
            "tr": trossos(r, val, cat), "mv": sorted(val), "mc": sorted(cat), "comp": comp,
        })

    dades = {"sistema": [args.sistema, nom(args.sistema)],
             "compara": [[s, nom(s)] for s in compara], "frases": frases}
    js = json.dumps(dades, ensure_ascii=False).replace("</", "<\\/")
    plantilla = (AQUI / "visor_xcomet_plantilla.html").read_text(encoding="utf-8")
    args.eixida.mkdir(parents=True, exist_ok=True)
    eixida = args.eixida / f"xcomet_{args.sistema}.html"
    eixida.write_text(plantilla.replace("/*DADES*/null", js), encoding="utf-8")
    print(f"Fet: {eixida} ({len(frases)} frases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
