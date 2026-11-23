"""
prova_marge_text_real.py -- El sistema 2.0.0 (KenLM + classificador) amb
diversos marges sobre text CATALÀ REAL (20/11/2026, petició de l'usuari).

Els bancs d'homògrafs tenen la meitat de casos de cada sentit; en text real
el sentit que s'ha de deixar en català («calces» d'època, «manca» verb,
«reeixides» èxits, «nou» nou) és molt més freqüent. Abans de baixar el
marge de 3 a 1 cal saber quantes vegades més tradueix el sistema en text
real i si eixes traduccions noves són bones.

1. Recorre `dades/macocu/catala_pur.jsonl` (frases catalanes de MaCoCu, GD
   = 0; no s'ha usat per a entrenar el model, que és valencià) i, per a cada
   forma catalana ambigua del lèxic (`carrega_punts`), compta en quantes
   frases apareix i en tria una mostra a l'atzar (`--per-paraula`, llavor
   fixa).
2. Puntua cada frase UNA vegada amb el sistema (motor + KenLM + classificador
   de sentit, com `tradueix_cat_val_ml`) i aplica el criteri del sistema
   (`CRITERI_KENLM`) canviant només el marge (`--marges`).
3. Eixida (`resultats/prova_marge_text_real_<data>.{json,md}`): per paraula,
   quantes frases tradueix cada marge, i totes les frases on la decisió
   canvia entre el primer i l'últim marge, per a revisar-les a mà.

4. (23/11/2026) Amb `--mescla`, cada frase es puntua també amb la mescla
   formes + lemes parcials amb el context lematitzat una vegada (document viu,
   4.23) i s'hi apliquen els criteris `MARGE:DESEMPAT` donats (per defecte 3:4
   i 1:4); l'informe afig les frases on la mescla no coincidix amb el sistema
   amb l'últim marge. Els models de la mescla es busquen en `--dir-models`.

Ús (en Abaco o on hi haja `kenlm`; el model de la 2.0.0 en `AVLIZADOR_KENLM_DIR`):
    python pipeline/03_seleccio_de_model/model_llengua/prova_marge_text_real.py --per-paraula 200
    python .../prova_marge_text_real.py --limit-linies 20000 --per-paraula 5   # prova
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
RESULTATS = ARREL / "pipeline" / "03_seleccio_de_model" / "resultats"
PARAULA = re.compile(r"\w+(?:·\w+)*")


def mostra(entrada: Path, formes: set[str], per_paraula: int, llavor: int,
           limit: int | None = None) -> tuple[dict, dict, int]:
    """Recompte de frases per forma i mostra a l'atzar de cada una
    (mostreig de reservori: totes les frases tenen la mateixa probabilitat).

    >>> import tempfile
    >>> p = Path(tempfile.mkdtemp()) / "t.jsonl"
    >>> _ = p.write_text("\\n".join(json.dumps({"text": t}) for t in
    ...     ["Un cop més.", "Tres cops.", "Res.", "Un altre cop i un cop."]), encoding="utf-8")
    >>> n, m, total = mostra(p, {"cop", "cops"}, 5, 1)
    >>> n["cop"], n["cops"], total, sorted(m["cop"])
    (2, 1, 4, ['Un altre cop i un cop.', 'Un cop més.'])
    """
    rnd = random.Random(llavor)
    comptes: dict = collections.Counter()
    mostres: dict = {f: [] for f in formes}
    total = 0
    with entrada.open(encoding="utf-8") as fh:
        for linia in fh:
            if limit and total >= limit:
                break
            total += 1
            text = json.loads(linia)["text"]
            presents = formes.intersection(PARAULA.findall(text.lower()))
            for f in sorted(presents):  # 23/11/2026: l'ordre d'un set canvia d'una execució a l'altra
                comptes[f] += 1
                k = comptes[f]
                if len(mostres[f]) < per_paraula:
                    mostres[f].append(text)
                else:
                    j = rnd.randrange(k)
                    if j < per_paraula:
                        mostres[f][j] = text
    return dict(comptes), mostres, total


def clau_mescla(marge: float, desempat: float) -> str:
    """Nom d'un criteri de la mescla en l'eixida.

    >>> clau_mescla(3.0, 4.0)
    'mescla m3 d4'
    """
    return f"mescla m{marge:g} d{desempat:g}"


def mescla_ref(dir_models: Path):
    """23/11/2026: la mescla formes + lemes parcials amb el context lematitzat
    una vegada (`kenlm_mescla_ref_dogv2_c1` del comparador, document viu 4.23)."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from compara_models import Carregador

    return Carregador(dir_models, None).puntuador("kenlm_mescla_ref_dogv2_c1")


def _decisions(forma, punt, punts, text_motor, criteris: dict) -> dict:
    from avlizador.traductor_cat_val.model_llengua import aplica_tries, tria

    eixida = {}
    for nom, c in criteris.items():
        t = tria(punt, c)
        eixida[nom] = {"tria": t, "decidit": punt.decidit, "traduix": t is not None and t.lower() != forma,
                       "eixida": aplica_tries(text_motor, punts, c)}
    return eixida


def avalua(mostres: dict, marges: list[float], dir_kenlm: str | None, mescla=None,
           criteris_mescla: list[tuple[float, float]] = ()) -> list[dict]:
    from avlizador.avaluacio.metriques import normalitza_apostrofa
    from avlizador.traductor_cat_val.model_llengua import (CONCORDANCA_PER_DEFECTE, CRITERI_KENLM, _motor,
                                                           puntua_punts, sistema_kenlm)
    from avlizador.traductor_cat_val.rules import detokenize

    model, sentit = sistema_kenlm(dir_kenlm)
    c0 = CRITERI_KENLM
    tipus_model = tuple(t for t in c0.tipus if t != "irresoluble" or c0.model_irresolubles)
    criteris = {str(m): replace(c0, marge=m) for m in marges}
    criteris_m = {clau_mescla(m, d): replace(c0, marge=m, desempat=d) for m, d in criteris_mescla}

    def puntua(text, puntuador):
        text_motor, punts = puntua_punts(text, puntuador, c0.tipus, CONCORDANCA_PER_DEFECTE, tipus_model)
        for p in punts:
            if p.puntuacions:
                p.sentit = sentit.candidat(p)
        return text_motor, punts

    files = []
    for forma, frases in sorted(mostres.items()):
        for text in frases:
            text = normalitza_apostrofa(text)
            text_motor, punts = puntua(text, model)
            punt = next((p for p in punts if p.paraula.lower() == forma), None)
            fila = {"forma": forma, "text": text, "detectat": punt is not None,
                    "tipus": punt.tipus if punt else None, "decisions": {}}
            if punt is not None:
                fila["puntuacions"] = {c: {k: round(v[k], 3) for k in ("lp", "prior", "n")}
                                       for c, v in punt.puntuacions.items()}
                fila["sentit"] = punt.sentit
                fila["decisions"] = _decisions(forma, punt, punts, text_motor, criteris)
                if mescla is not None:
                    mescla.fixa_referencia(detokenize(_motor()[0].tradueix_tokens(text)))
                    text_m, punts_m = puntua(text, mescla)
                    punt_m = next((p for p in punts_m if p.paraula.lower() == forma), None)
                    if punt_m is not None:
                        fila["puntuacions_mescla"] = {c: {k: round(v[k], 3) for k in ("lp", "prior", "n")}
                                                      for c, v in punt_m.puntuacions.items()}
                        fila["decisions"].update(_decisions(forma, punt_m, punts_m, text_m, criteris_m))
            files.append(fila)
    return files


def _canvis(files: list[dict], a: str, b: str) -> list[str]:
    md = ["", f"## Frases on la decisió canvia ({a} → {b})", "",
          f"| Paraula | {a} | {b} | Frase (catalana) |", "|---|---|---|---|"]
    for f in files:
        da, db = f["decisions"].get(a), f["decisions"].get(b)
        if da and db and da["tria"] != db["tria"]:
            md.append(f"| {f['forma']} | {da['tria']} ({da['decidit']}) | {db['tria']} ({db['decidit']}) | "
                      f"{f['text'].replace('|', '/')} |")
    return md


def informe(files: list[dict], comptes: dict, total: int, marges: list[float],
            criteris_mescla: list[tuple[float, float]] = ()) -> str:
    ms = [str(m) for m in marges]
    mes = [clau_mescla(m, d) for m, d in criteris_mescla]
    noms = [f"marge {m}" for m in ms] + mes
    md = ["# Marge del sistema 2.0.0 en text català real (MaCoCu)", "",
          f"{total:,} frases de `catala_pur.jsonl`; mostra a l'atzar per paraula. «Tradueix» = la tria no és "
          "la paraula catalana.".replace(",", "."), "",
          "| Paraula | Frases en el corpus | Mostra | Detectades | "
          + " | ".join(f"Tradueix ({n})" for n in noms) + " |",
          "|---|---|---|---|" + "---|" * len(noms)]
    per = collections.defaultdict(list)
    for f in files:
        per[f["forma"]].append(f)
    for forma in sorted(per, key=lambda x: -comptes.get(x, 0)):
        fs = per[forma]
        det = [f for f in fs if f["detectat"]]
        cel = [str(sum(f["decisions"].get(m, {}).get("traduix", False) for f in det)) for m in ms + mes]
        md.append(f"| {forma} | {comptes.get(forma, 0)} | {len(fs)} | {len(det)} | " + " | ".join(cel) + " |")
    md += _canvis(files, ms[0], ms[-1])
    for m in mes:  # la mescla davant del sistema amb l'últim marge
        md += _canvis(files, ms[-1], m)
    return "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--entrada", type=Path, default=ARREL / "dades" / "macocu" / "catala_pur.jsonl")
    p.add_argument("--per-paraula", type=int, default=200)
    p.add_argument("--marges", nargs="+", type=float, default=[3.0, 2.0, 1.0])
    p.add_argument("--llavor", type=int, default=20261120)
    p.add_argument("--limit-linies", type=int, default=None)
    p.add_argument("--dir-kenlm", default=None, help="per defecte, AVLIZADOR_KENLM_DIR o la caché de HF")
    p.add_argument("--mescla", nargs="*", default=None, metavar="MARGE:DESEMPAT",
                   help="(23/11/2026) puntua també amb la mescla formes + lemes parcials amb referència; "
                        "criteris de la mescla (per defecte 3:4 1:4)")
    p.add_argument("--dir-models", type=Path, default=ARREL / "dades" / "macocu",
                   help="carpeta amb kenlm/ (models de la mescla), com en compara_models.py")
    a = p.parse_args(argv)
    criteris_mescla = []
    if a.mescla is not None:
        criteris_mescla = [tuple(float(x) for x in c.split(":")) for c in (a.mescla or ["3:4", "1:4"])]
    from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

    formes = {f.lower() for f in carrega_punts()}
    t0 = time.time()
    comptes, mostres, total = mostra(a.entrada, formes, a.per_paraula, a.llavor, a.limit_linies)
    print(f"Recompte: {total} frases, {time.time() - t0:.0f} s; {dict(sorted(comptes.items()))}", flush=True)
    t0 = time.time()
    mescla = mescla_ref(a.dir_models) if criteris_mescla else None
    files = avalua(mostres, a.marges, a.dir_kenlm, mescla, criteris_mescla)
    print(f"Avaluació: {len(files)} frases, {time.time() - t0:.0f} s", flush=True)
    sufix = f"{datetime.now():%Y%m%d_%H%M}" + (f"_limit{a.limit_linies}" if a.limit_linies else "")
    RESULTATS.mkdir(parents=True, exist_ok=True)
    (RESULTATS / f"prova_marge_text_real_{sufix}.json").write_text(
        json.dumps({"total": total, "comptes": comptes, "marges": a.marges, "mescla": criteris_mescla,
                    "per_paraula": a.per_paraula, "llavor": a.llavor, "files": files},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTATS / f"prova_marge_text_real_{sufix}.md").write_text(
        informe(files, comptes, total, a.marges, criteris_mescla), encoding="utf-8")
    print(f"-> {RESULTATS / f'prova_marge_text_real_{sufix}.md'}")


if __name__ == "__main__":
    main()
