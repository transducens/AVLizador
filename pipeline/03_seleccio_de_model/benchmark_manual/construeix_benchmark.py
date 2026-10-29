"""
benchmark_manual/construeix_benchmark.py -- Pas final de
documentacio/hoja_de_ruta_benchmark_manual.md (secció 7): construïx el
benchmark cat->val a partir de la revisió a mà de l'equip.

Entrada:
    dades/benchmark_manual/revisio_persona1.json
    dades/benchmark_manual/revisio_persona2.json
Eixida:
    dades/benchmark_manual/benchmark_manual_cat_val.json

Criteris (decisions de l'usuari, 28/10/2026):
- només entren les frases amb `valida: true` (fora les `false` i les
  dubtoses, s'escriguen com s'escriguen);
- el text és el de `oriental`/`occidental` (l'equip ha corregit
  directament ací); si `oriental_corregit`/`occidental_corregit` no és
  buit, mana la correcció (BM-BOE-002 i BM-BOE-006);
- només tres camps: `id` (el de la revisió, BM-BOE-…/BM-AVL-…, únic i diu
  la font), `oriental` (català, entrada del traductor) i `occidental`
  (valencià, referència) -- mateix format que el 151, així que funciona
  amb `evalua_models.py --benchmark`;
- orde per id: primer el BOE i després l'AVL.

Comprovacions (avisa, no corregix res): ids repetits, pars repetits,
frases buides o amb espais sobrants i frases on el català és igual que el
valencià.

Ús (des de l'arrel del repo):
    python pipeline/03_seleccio_de_model/benchmark_manual/construeix_benchmark.py

Després, per a tornar a mesurar el GD:
    python pipeline/09_grau_dialectal/mesura_corpus.py --corpus manual_val manual_cat --reinicia
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARREL = AQUI.parents[2]

DIR = ARREL / "dades" / "benchmark_manual"
REVISIONS = [DIR / "revisio_persona1.json", DIR / "revisio_persona2.json"]
EIXIDA = DIR / "benchmark_manual_cat_val.json"


def _clau_orde(ident: str) -> tuple[int, int]:
    """BM-BOE-… abans que BM-AVL-…, i dins de cada font per número.

    >>> sorted(["BM-AVL-002", "BM-BOE-010", "BM-BOE-002"], key=_clau_orde)
    ['BM-BOE-002', 'BM-BOE-010', 'BM-AVL-002']
    """
    _, font, num = ident.split("-")
    return (0 if font == "BOE" else 1, int(num))


def frase_benchmark(f: dict) -> dict:
    """La frase del benchmark a partir d'una frase de la revisió: manen
    les correccions si n'hi ha.

    >>> frase_benchmark({"id": "BM-BOE-001", "oriental": "aquesta", "occidental": "esta",
    ...                  "oriental_corregit": None, "occidental_corregit": "eixa"})
    {'id': 'BM-BOE-001', 'oriental': 'aquesta', 'occidental': 'eixa'}
    """
    return {
        "id": f["id"],
        "oriental": f.get("oriental_corregit") or f["oriental"],
        "occidental": f.get("occidental_corregit") or f["occidental"],
    }


def comprova(frases: list[dict]) -> list[str]:
    """Avisos sobre el benchmark (no en canvia res).

    >>> comprova([{"id": "A", "oriental": "x ", "occidental": "x "}])
    ['A: espais sobrants', 'A: el català és igual que el valencià']
    """
    avisos = []
    for ident, n in collections.Counter(f["id"] for f in frases).items():
        if n > 1:
            avisos.append(f"{ident}: id repetit {n} vegades")
    for par, n in collections.Counter((f["oriental"], f["occidental"]) for f in frases).items():
        if n > 1:
            avisos.append(f"par repetit {n} vegades: {par[0][:60]}")
    for f in frases:
        textos = (f["oriental"], f["occidental"])
        if not all(t and t.strip() for t in textos):
            avisos.append(f"{f['id']}: frase buida")
        elif any(t != t.strip() or "  " in t for t in textos):
            avisos.append(f"{f['id']}: espais sobrants")
        if f["oriental"] == f["occidental"]:
            avisos.append(f"{f['id']}: el català és igual que el valencià")
    return avisos


def main() -> None:
    frases = []
    fora = []
    for path in REVISIONS:
        for f in json.loads(path.read_text(encoding="utf-8"))["frases"]:
            if f["valida"] is True:
                frases.append(frase_benchmark(f))
            else:
                fora.append((path.stem, f["id"], f["valida"]))
    frases.sort(key=lambda f: _clau_orde(f["id"]))

    EIXIDA.write_text(json.dumps(frases, ensure_ascii=False, indent=1), encoding="utf-8")

    per_font = collections.Counter(f["id"].split("-")[1] for f in frases)
    print(f"{len(frases)} frases ({', '.join(f'{k} {v}' for k, v in sorted(per_font.items(), reverse=True))})"
          f" -> {EIXIDA.relative_to(ARREL)}")
    print(f"\nFora: {len(fora)}")
    for persona, ident, valida in fora:
        print(f"  {persona}  {ident}  valida={valida!r}")

    avisos = comprova(frases)
    print(f"\nAvisos: {len(avisos)}")
    for a in avisos:
        print(f"  {a}")
    if avisos:
        sys.exit(1)


if __name__ == "__main__":
    main()
