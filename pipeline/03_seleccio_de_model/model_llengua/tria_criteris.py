"""
tria_criteris.py -- Tria els millors criteris de cada model a partir de la
graella completa de `compara_models.py --graella-completa` (20/11/2026,
petició de l'usuari: buscar la millor configuració del sistema 2.0.0, del
KenLM amb tot a lema i del de tot a lema + classificador, amb totes les
mètriques menys COMET).

Per a cada model:
- **criteri actual** (`fix`): el del sistema (`CRITERI_KENLM` en els `*_c1`);
- **millor sense més greus**: el que més encerta en les decisions dels
  homògrafs v1 + v2 sense passar dels errors greus del sistema actual
  (desempat: exactes del manual, després exactes dels homògrafs);
- **millor absolut**: el que més encerta, siguen quants siguen els greus;
- **validació creuada**: el criteri es tria amb un benchmark d'homògrafs
  (el millor sense més greus que el sistema en eixe benchmark) i es mesura
  en l'altre. Com que els criteris de les altres files s'ajusten sobre els
  mateixos homògrafs, és la xifra honesta.

Greus = traduïda sense caldre + candidat erroni. Mètriques de cada fila:
exactes, BLEU, chrF, TER i WER de cada benchmark i GD, GDV i GDC de
l'eixida del manual.

Ús (des de l'arrel del repositori):
    python pipeline/03_seleccio_de_model/model_llengua/tria_criteris.py \\
        pipeline/03_seleccio_de_model/resultats/compara_models_<data>_graella.json
Eixida: el mateix nom amb `_tria.md`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SISTEMA = "kenlm_dogv2_c1"
HOMOGRAFS = ("homografs", "homografs_v2")
NOMS = {"kenlm_dogv2_c1": "Sistema 2.0.0 (KenLM de formes + classificador)",
        "kenlm_lemes_tot_dogv2": "Tot a lema",
        "kenlm_lemes_tot_dogv2_c1": "Tot a lema + classificador",
        "kenlm_mescla_tot_dogv2_c1": "Mescla formes + tot a lema + classificador",
        "kenlm_lemes_dogv2": "Lemes parcials",
        "kenlm_lemes_dogv2_c1": "Lemes parcials + classificador",
        "kenlm_mescla_dogv2_c1": "Mescla formes + lemes parcials + classificador"}


def decisions(fila: dict, benchmarks=HOMOGRAFS) -> tuple[int, int, int]:
    """(encerts, greus, sense traduir) en els benchmarks d'homògrafs.

    >>> f = {"homografs": {"classes": {"encert": 5, "candidat_erroni": 1}},
    ...      "homografs_v2": {"classes": {"encert": 3, "traduida_sense_caldre": 2, "sense_traduir": 4}}}
    >>> decisions(f), decisions(f, ["homografs"])
    ((8, 3, 4), (5, 1, 0))
    """
    e = g = s = 0
    for b in benchmarks:
        c = fila.get(b, {}).get("classes", {})
        e += c.get("encert", 0)
        g += c.get("traduida_sense_caldre", 0) + c.get("candidat_erroni", 0)
        s += c.get("sense_traduir", 0)
    return e, g, s


def ordre(fila: dict, benchmarks=HOMOGRAFS) -> tuple:
    """Per a triar: més encerts, després més exactes en el manual i en els
    homògrafs, després menys greus."""
    e, g, _ = decisions(fila, benchmarks)
    return (e, fila.get("manual", {}).get("exactes", 0),
            sum(fila.get(b, {}).get("exactes", 0) for b in benchmarks), -g)


def millor(files: list[dict], max_greus: int | None, benchmarks=HOMOGRAFS) -> dict | None:
    """El millor criteri amb com a molt `max_greus` errors greus (None = sense límit).

    >>> fs = [{"criteri": "a", "homografs": {"classes": {"encert": 9, "candidat_erroni": 3}}},
    ...       {"criteri": "b", "homografs": {"classes": {"encert": 7, "candidat_erroni": 1}}}]
    >>> millor(fs, 1, ["homografs"])["criteri"], millor(fs, None, ["homografs"])["criteri"]
    ('b', 'a')
    """
    candidats = [f for f in files if max_greus is None or decisions(f, benchmarks)[1] <= max_greus]
    return max(candidats, key=lambda f: ordre(f, benchmarks)) if candidats else None


def frontera(files: list[dict]) -> list[dict]:
    """Criteris que no es poden millorar en encerts sense afegir greus
    (frontera de Pareto), de menys a més greus."""
    millors: dict[int, dict] = {}
    for f in files:
        e, g, _ = decisions(f)
        if g not in millors or ordre(f) > ordre(millors[g]):
            millors[g] = f
    eixida, maxim = [], -1
    for g in sorted(millors):
        e = decisions(millors[g])[0]
        if e > maxim:
            eixida.append(millors[g])
            maxim = e
    return eixida


def num(x, dec: int = 2) -> str:
    return "—" if x is None else (f"{x:.{dec}f}".replace(".", ",") if isinstance(x, float) else str(x))


def parametres(f: dict) -> str:
    parts = [f"marge {num(f['marge'], 1)}", f"λ {num(f['lam'], 2)}"]
    if f.get("lam_colisio") is not None:
        parts.append(f"λ col. {num(f['lam_colisio'], 2)}")
    if f.get("lam_irresoluble") is not None:
        parts.append(f"λ irr. {num(f['lam_irresoluble'], 2)}")
    if f.get("desempat") is not None:
        parts.append(f"desempat {num(f['desempat'], 1)}")
    return ", ".join(parts)


def taula_metriques(files: list[tuple[str, str, dict]], benchmarks: list[str]) -> list[str]:
    """Una fila per (model, etiqueta, criteri) amb totes les mètriques."""
    cap = ["Model", "Criteri", "Paràmetres", "Encerts", "Greus", "Sense traduir"]
    for b in benchmarks:
        cap += [f"{b}: exactes", f"{b}: BLEU", f"{b}: chrF", f"{b}: TER", f"{b}: WER"]
    cap += ["manual: GD", "manual: GDV", "manual: GDC"]
    md = ["| " + " | ".join(cap) + " |", "|" + "---|" * len(cap)]
    for model, etiqueta, f in files:
        e, g, s = decisions(f)
        cel = [NOMS.get(model, model), etiqueta, parametres(f), str(e), str(g), str(s)]
        for b in benchmarks:
            v = f.get(b, {})
            cel += [f"{v.get('exactes', '—')}/{v.get('n_frases', '—')}", num(v.get("bleu_mitja")),
                    num(v.get("chrf_mitja")), num(v.get("ter_corpus")), num(v.get("wer_corpus"))]
        m = f.get("manual", {})
        cel += [num(m.get("gd"), 4), num(m.get("gdv"), 4), num(m.get("gdc"), 4)]
        md.append("| " + " | ".join(cel) + " |")
    return md


def informe(graella: dict) -> str:
    models = graella["models"]
    benchmarks = graella["benchmarks"]
    ref = next(f for f in models[SISTEMA] if f["fix"]) if SISTEMA in models else None
    greus_ref = decisions(ref)[1] if ref else None
    n_decisions = (sum(sum(ref.get(b, {}).get("classes", {}).values()) for b in HOMOGRAFS)
                   if ref else "?")  # 23/11/2026: abans posava 257 sempre (ara n'hi ha 237)
    md = ["# Millors criteris de cada model (graella completa)", "",
          f"Graella de `{graella['data']}`. Decisions = homògrafs v1 + v2 ({n_decisions}); greus = traduïda sense "
          "caldre + candidat erroni. "
          + (f"Referència: el sistema 2.0.0 amb el criteri actual, {decisions(ref)[0]} encerts i "
             f"{greus_ref} greus." if ref else ""), ""]

    md += ["## Encerts i greus de cada model", "",
           "| Model | Criteris provats | Criteri actual | Millor sense més greus | Millor absolut |",
           "|---|---|---|---|---|"]
    triats = []
    for model, files in models.items():
        fix = next(f for f in files if f["fix"])
        sense = millor(files, greus_ref)
        abs_ = millor(files, None)
        triats += [(model, "actual", fix)]
        if sense is not None:
            triats.append((model, "millor sense més greus", sense))
        triats.append((model, "millor absolut", abs_))
        fmt = lambda f: "—" if f is None else "{} / {} ({})".format(*decisions(f)[:2], parametres(f))
        md.append(f"| {NOMS.get(model, model)} | {len(files)} | {fmt(fix)} | {fmt(sense)} | {fmt(abs_)} |")
    md += ["", "Cada cel·la: encerts / greus (paràmetres). Triats sobre els mateixos homògrafs: "
           "mireu la validació creuada.", ""]

    md += ["## Validació creuada (triat en un benchmark, mesurat en l'altre)", "",
           "Es tria el criteri amb un benchmark d'homògrafs (el que més encerta sense passar dels greus del "
           "sistema actual en eixe benchmark) i es mesura en l'altre. Entre parèntesis, el sistema actual en "
           "el mateix benchmark.", "",
           "| Model | Triat en | Paràmetres | Mesurat en | Encerts | Greus | Sense traduir | Exactes |",
           "|---|---|---|---|---|---|---|---|"]
    for model, files in models.items():
        for tria, mesura in (("homografs", "homografs_v2"), ("homografs_v2", "homografs")):
            if tria not in benchmarks or mesura not in benchmarks:
                continue
            g_ref = decisions(ref, [tria])[1] if ref else None
            f = millor(files, g_ref, [tria])
            if f is None:
                continue
            e, g, s = decisions(f, [mesura])
            re_, rg, rs = decisions(ref, [mesura]) if ref else (None, None, None)
            md.append(f"| {NOMS.get(model, model)} | {tria} | {parametres(f)} | {mesura} | {e} ({re_}) | "
                      f"{g} ({rg}) | {s} ({rs}) | {f[mesura]['exactes']} ({ref[mesura]['exactes'] if ref else '—'}) |")
    md.append("")

    md += ["## Totes les mètriques (sense COMET)", ""]
    md += taula_metriques(triats, benchmarks)
    md += ["", "## Frontera encerts / greus de cada model", "",
           "Els criteris que no es poden millorar en encerts sense afegir greus.", "",
           "| Model | Greus | Encerts | Sense traduir | Paràmetres |", "|---|---|---|---|---|"]
    for model, files in models.items():
        for f in frontera(files):
            e, g, s = decisions(f)
            md.append(f"| {NOMS.get(model, model)} | {g} | {e} | {s} | {parametres(f)} |")
    return "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("graella", type=Path, help="compara_models_<data>_graella.json")
    a = p.parse_args(argv)
    graella = json.loads(a.graella.read_text(encoding="utf-8"))
    eixida = a.graella.with_name(a.graella.stem.removesuffix("_graella") + "_tria.md")
    eixida.write_text(informe(graella), encoding="utf-8")
    print(f"-> {eixida}")


if __name__ == "__main__":
    main()
