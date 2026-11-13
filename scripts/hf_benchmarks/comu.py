"""
comu.py -- Peces compartides pels scripts que preparen cada benchmark
d'AVLizador com a dataset de Hugging Face (un dataset per benchmark):
rutes, autors, llicència, escriptura de JSONL, NOTICE del BOE, parts
comunes de la fitxa i el bàner.

Llicència (decisió de l'usuari, 09/11/2026): Apache 2.0, la del projecte.
Les frases del BOE porten, a més, l'atribució que demana l'avís legal del
BOE (https://www.boe.es/informacion/aviso_legal/), en la fitxa i en un
fitxer NOTICE (Apache 2.0 obliga a conservar el NOTICE en les obres
derivades).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ARREL = Path(__file__).resolve().parents[2]
BENCH = ARREL / "dades" / "benchmarks"
EIXIDA = ARREL / "dades" / "hf_benchmarks"

AUTORS = ("Mauricio González Arcas", "Nicolás Martín Morcillo")
GITHUB = "https://github.com/transducens/AVLizador"
LLICENCIA = "apache-2.0"
ORG_PER_DEFECTE = "transducens"

BOE_COPIA = "Fuente de los datos: Agencia Estatal Boletín Oficial del Estado"
BOE_DERIVAT = "Basado en datos de la Agencia Estatal Boletín Oficial del Estado"


def autors_text() -> str:
    return " and ".join(AUTORS)


def prepara_desti(nom: str) -> Path:
    desti = EIXIDA / nom
    if desti.exists():
        shutil.rmtree(desti)
    desti.mkdir(parents=True)
    return desti


def escriu_jsonl(path: Path, files: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in files), encoding="utf-8")


def escriu_notice(desti: Path, titol: str, boe: str | None, altres: list[str] | None = None) -> None:
    """NOTICE del dataset: autors, llicència i, si hi ha frases del BOE,
    l'atribució que demana l'avís legal del BOE (`boe` = BOE_COPIA si el
    text es reproduïx sense canvis, BOE_DERIVAT si s'ha modificat).
    `altres`: més línies d'atribució (p. ex. les frases de l'AVL)."""
    linies = [titol, f"Copyright 2026 {autors_text()}.",
              "Made for AVLizador (" + GITHUB + ").",
              "Licensed under the Apache License, Version 2.0.", ""]
    if boe:
        linies += [
            "This dataset contains sentences from the Spanish State Gazette (BOE).",
            f"{boe} (https://www.boe.es).",
            "This is not an official version of the texts, and the Agencia Estatal",
            "Boletín Oficial del Estado does not sponsor or endorse this work.",
            "",
        ]
    if altres:
        linies += [*altres, ""]
    (desti / "NOTICE").write_text("\n".join(linies), encoding="utf-8")
    shutil.copy(ARREL / "LICENSE", desti / "LICENSE")


def yaml(pretty: str, mida: str, configs: str) -> str:
    return f"""---
pretty_name: {pretty}
language:
  - ca
license: {LLICENCIA}
task_categories:
  - translation
  - text2text-generation
tags:
  - catalan
  - valencian
  - dialect
  - dialectal-adaptation
  - benchmark
  - evaluation
size_categories:
  - {mida}
{configs}
---
"""


def capcalera(repo: str, alt: str, n: int, extra_insignia: str = "") -> str:
    """Bàner + insígnies."""
    return f"""<p align="center">
  <img src="https://huggingface.co/datasets/{repo}/resolve/main/assets/banner.png" alt="{alt}" width="100%">
</p>

<p align="center">
  <a href="{GITHUB}"><img alt="Made for AVLizador" src="https://img.shields.io/badge/made%20for-AVLizador-1f6f8b?logo=github"></a>
  <img alt="Language" src="https://img.shields.io/badge/ca%20%E2%86%92%20ca--valencia-e8a33d">
  <img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-13294b">
  {extra_insignia}<img alt="Sentences" src="https://img.shields.io/badge/sentences-{n:,}-555">
</p>
"""


def autoria() -> str:
    return (f"Made for [**AVLizador**]({GITHUB}), a Catalan → Valencian adapter (rule engine + "
            f"spaCy + a small language model for ambiguous words, CPU only). **Authors: {autors_text()}.**")


def cita(clau: str, titol: str, repo: str) -> str:
    bib = " and ".join(f"{a.split(' ', 1)[1]}, {a.split(' ', 1)[0]}" for a in AUTORS)
    return f"""## Citation

```bibtex
@misc{{{clau},
  title        = {{{titol}}},
  author       = {{{bib}}},
  year         = {{2026}},
  howpublished = {{\\url{{https://huggingface.co/datasets/{repo}}}}},
  note         = {{Made for AVLizador, {GITHUB}}}
}}
```
"""


METRIQUES_NOTA = """Learned metrics such as xCOMET-XL and LLM judges **do not see the
dialect**: in our tests they scored the untranslated Catalan as high as,
or higher than, the Valencian reference. For this task we recommend
surface metrics together with a dialect measure such as the *Grau
Dialectal* (GD) included in AVLizador (`avlizador gd`)."""


def banner(path: Path, titol: str, subtitol: str, catala: str, valencia: str) -> None:
    """Bàner de 1800x480 px: degradat blau → ambre, títol i un exemple."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 3.2), dpi=150)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    colors = matplotlib.colors.LinearSegmentedColormap.from_list("g", ["#13294b", "#1f6f8b", "#e8a33d"])
    ax.imshow(np.linspace(0, 1, 512)[None, :], extent=(0, 1, 0, 1), aspect="auto", cmap=colors)
    ax.text(0.04, 0.70, titol, color="white", fontsize=32, fontweight="bold", va="center")
    ax.text(0.04, 0.47, subtitol, color="#f3f6fa", fontsize=15, va="center")
    t = ax.text(0.04, 0.22, catala, color="#ffd9a0", fontsize=17, family="monospace", va="center")
    fig.canvas.draw()
    x = ax.transAxes.inverted().transform(t.get_window_extent())[1][0]
    ax.text(x + 0.02, 0.22, "→", color="white", fontsize=19, va="center")
    ax.text(x + 0.06, 0.22, valencia, color="white", fontsize=17, family="monospace", fontweight="bold",
            va="center")
    fig.savefig(path)
    plt.close(fig)
