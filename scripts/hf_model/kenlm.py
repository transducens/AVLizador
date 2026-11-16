"""
kenlm.py -- Prepara el model KenLM d'AVLizador per a Hugging Face (16/11/2026):
els tres fitxers que fa servir el paquet, la fitxa (`README.md`), el NOTICE i el
bàner, en `dades/hf_model/kenlm/` (fora de git). El puja l'usuari:

    hf upload transducens/avlizador-kenlm-va dades/hf_model/kenlm . --repo-type model

Fitxers (els noms que busca `avlizador.traductor_cat_val.model_llengua.kenlm`):
- `<NOM_MODEL>_o5.binary` -- el model KenLM (ordre 5, trie quantitzat);
- `<NOM_MODEL>_freq.json` -- freqüències de les paraules candidates (el prior);
- `sentit.json` -- el classificador de sentit (Naive Bayes per grup de lectures).

Llicència (decisió de l'usuari, 16/11/2026): CC0 1.0. Per això el model NO pot
portar textos de l'AVL (el seu avís legal no ho permet): si `--fonts` inclou
`avl`, el script s'atura. L'avís de retirada només va en el dataset manual.

Ús (des de l'arrel del repositori):
    python scripts/hf_model/kenlm.py --dir docker/kenlm --fonts net dogv
    python scripts/hf_model/kenlm.py --dir dades/macocu/kenlm --nom valencia_net_dogv2 --fonts net dogv2
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hf_benchmarks"))
from comu import ARREL, AUTORS, GITHUB, autors_text, banner  # noqa: E402

from avlizador.traductor_cat_val.model_llengua.kenlm import NOM_MODEL, REPO_HF  # noqa: E402

EIXIDA = ARREL / "dades" / "hf_model" / "kenlm"

# Cada font del text d'entrenament: (descripció per a la fitxa, atribució per al NOTICE).
FONTS = {
    "net": ("**MaCoCu-ca 1.0** ([CLARIN.SI, hdl 11356/1837](http://hdl.handle.net/11356/1837), CC0 1.0): "
            "the Valencian part of this Catalan web corpus, selected with AVLizador's *Grau Dialectal* (GD): "
            "sentences with at least two Valencian markers, or from a document that has one "
            "(1,211,204 sentences).",
            "MaCoCu-ca 1.0 (CLARIN.SI, http://hdl.handle.net/11356/1837), CC0 1.0."),
    "dogv": ("**Diari Oficial de la Generalitat Valenciana (DOGV)**, 2025-2026 ([dogv.gva.es](https://dogv.gva.es)): "
             "10,289 documents; only documents with GD ≥ 0.8, without repeated sentences "
             "(163,558 sentences, 9.5 M words).",
             "Diari Oficial de la Generalitat Valenciana (DOGV, https://dogv.gva.es), 2025-2026."),
    "dogv2": ("**Diari Oficial de la Generalitat Valenciana (DOGV)**, 2025-2026 ([dogv.gva.es](https://dogv.gva.es)): "
              "15,702 documents; only documents with GD ≥ 0.8, without repeated sentences "
              "(233,946 sentences, 13.7 M words).",
              "Diari Oficial de la Generalitat Valenciana (DOGV, https://dogv.gva.es), 2025-2026."),
    "ua": ("**News of the University of Alicante** in Valencian (sentences with GD ≥ 0.8; 31,212 sentences).",
           "News of the University of Alicante (https://web.ua.es)."),
}

# Xifres del sistema amb este model (vore pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md).
# 16/11/2026: les del 13/11 (valencia_net_dogv); s'actualitzen amb l'avaluació de la versió 2.0.0.
RESULTATS = {
    "data": "2026-11-13",
    "files": [
        ("Homographs v1 (253)", "227", "217", "176"),
        ("Homographs v2 (160)", "111", "96", "74"),
        ("Manual benchmark (458)", "232", "231", "218"),
        ("151 sentences (154)", "144", "145", "142"),
    ],
    "decisions": "193 correct and 1 serious error (a wrong meaning) out of 257 decisions in the homograph sets",
}


def fitxa(nom: str, fonts: list[str], freq: dict, n_grups: int, mida_mb: int) -> str:
    fonts_md = "\n".join(f"- {FONTS[f][0]}" for f in fonts)
    taula = "\n".join(f"| {b} | **{k}** | {fl} | {m} |" for b, k, fl, m in RESULTATS["files"])
    tokens = f"{freq.get('tokens', 0):,}" if freq.get("tokens") else "—"
    return f"""---
language:
  - ca
license: cc0-1.0
library_name: kenlm
pipeline_tag: text-generation
tags:
  - kenlm
  - n-gram
  - language-model
  - catalan
  - valencian
  - dialect
  - dialectal-adaptation
---

<p align="center">
  <img src="https://huggingface.co/{REPO_HF}/resolve/main/assets/banner.png" alt="AVLizador KenLM: Valencian n-gram language model" width="100%">
</p>

<p align="center">
  <a href="{GITHUB}"><img alt="Made for AVLizador" src="https://img.shields.io/badge/made%20for-AVLizador-1f6f8b?logo=github"></a>
  <img alt="Language" src="https://img.shields.io/badge/language-ca--valencia-e8a33d">
  <img alt="License" src="https://img.shields.io/badge/license-CC0%201.0-13294b">
  <img alt="CPU only" src="https://img.shields.io/badge/CPU-only-555">
</p>

# AVLizador KenLM: Valencian n-gram language model

A 5-gram [KenLM](https://github.com/kpu/kenlm) language model of **Valencian**
(standard of the Acadèmia Valenciana de la Llengua), with the small files that
[**AVLizador**]({GITHUB}) needs to decide the **ambiguous words** when it adapts
a Catalan text to Valencian. **Authors: {autors_text()}.**

> *Model de llengua de n-grames del valencià, per a decidir les paraules
> ambigües de l'adaptador català → valencià AVLizador. Fet per
> {' i '.join(AUTORS)}.*

## What it is for

AVLizador adapts Catalan (IEC standard) to Valencian (AVL standard) with rules
and dictionaries. A few words have more than one possible Valencian form, and
only the context tells which one is right:

- *cop* → **colp** (a blow) or **vegada** (a time: *un cop acabada la reunió* →
  *una vegada acabada la reunió*);
- *nou* → **anou** (a walnut) or **nou** (new, nine);
- *manca* → **falta** or the verb *mancar*.

AVLizador builds the full Valencian sentence for each candidate and asks this
model which one is more likely. It only translates when the model clearly
prefers it (margin 3); otherwise it keeps the Catalan word. When the model
hesitates in a collision such as *cop*, the sense classifier (`sentit.json`)
decides from the whole sentence.

It replaces FLOR-760M (a neural model, 1.5 GB of memory and ~0.8 s per
candidate sentence on CPU) with **~0.1 ms per sentence, ~80 MB and no GPU or
PyTorch**, and makes fewer mistakes.

## Files

| File | What it is |
|---|---|
| `{nom}_o5.binary` | KenLM model, order 5, trie with 8-bit quantization ({mida_mb} MB) |
| `{nom}_freq.json` | Frequency of the candidate words in the training text ({tokens} tokens), used to correct the advantage of frequent words |
| `sentit.json` | Sense classifier: one Naive Bayes per group of readings of an ambiguous word ({n_grups} groups), trained on the same kind of text |

## Usage

With AVLizador (the files are downloaded automatically the first time):

```bash
pip install "avlizador[kenlm] @ git+{GITHUB}"
avlizador tradueix "Un cop acabada la reunió, marxem."
# Una vegada acabada la reunió, marxem.
```

```python
from avlizador import translate_cat_val
translate_cat_val("Un cop acabada la reunió, marxem.")
```

To use a local copy instead, point `AVLIZADOR_KENLM_DIR` to a folder with the
three files. With `AVLIZADOR_KENLM_DESCARREGA=0` or `HF_HUB_OFFLINE=1` nothing is
downloaded.

The model on its own (the text must be normalized as in training: lower case,
tokens separated by spaces; use `avlizador.traductor_cat_val.model_llengua.kenlm.normalitza`):

```python
import kenlm
from huggingface_hub import hf_hub_download
from avlizador.traductor_cat_val.model_llengua.kenlm import normalitza

model = kenlm.Model(hf_hub_download("{REPO_HF}", "{nom}_o5.binary"))
for frase in ("Una vegada acabada la reunió, marxem.", "Un colp acabada la reunió, marxem."):
    print(model.score(normalitza(frase), bos=True, eos=True), frase)  # log10 P
```

## Training data

{fonts_md}

No sentence of AVLizador's evaluation sets is in the training text (the
benchmark sentences were removed from the DOGV text).

## Training

- `lmplz -o 5 --prune 0 1 1 1 1` (singletons pruned from order 2 on), then
  `build_binary trie -q 8 -b 8`.
- Text normalized as described above; one sentence per line.
- Scripts: `pipeline/08_traduccio_corpus/macocu/` in the [AVLizador repository]({GITHUB})
  (`kenlm/entrena_kenlm.sh`, `kenlm/freq_unigrames.py`) and
  `pipeline/03_seleccio_de_model/model_llengua/sentit_general.py` for the classifier.

## Results

AVLizador with this model against AVLizador with FLOR-760M and with the rules
alone (exact matches; {RESULTATS["data"]}):

| Benchmark | KenLM | FLOR-760M | Rules only |
|---|---|---|---|
{taula}

In the ambiguous words of the homograph sets: {RESULTATS["decisions"]}.
Benchmarks: [AVLizador collection](https://huggingface.co/transducens).

## Limitations

- An n-gram model only sees four words of left context; some senses need
  more (the order 6-8 models gave exactly the same decisions).
- Formal register (official journal, web): the frequency of a form in this
  text is not always the frequency in other registers.
- It is meant to rank the candidate sentences of AVLizador, not as a general
  language model.

## License

**CC0 1.0** (public domain dedication), {autors_text()}. The training data are
cited in `NOTICE`. The KenLM library (LGPL 2.1) is not included: install it with
`pip install kenlm`.

## Citation

```bibtex
@misc{{avlizador_kenlm_2026,
  title        = {{AVLizador KenLM: Valencian n-gram language model}},
  author       = {{{" and ".join(f"{a.split(' ', 1)[1]}, {a.split(' ', 1)[0]}" for a in AUTORS)}}},
  year         = {{2026}},
  howpublished = {{\\url{{https://huggingface.co/{REPO_HF}}}}},
  note         = {{Made for AVLizador, {GITHUB}}}
}}

@inproceedings{{heafield-2011-kenlm,
  title     = {{{{K}}en{{LM}}: Faster and Smaller Language Model Queries}},
  author    = {{Heafield, Kenneth}},
  booktitle = {{Proceedings of the Sixth Workshop on Statistical Machine Translation}},
  year      = {{2011}},
  pages     = {{187--197}}
}}
```
"""


def notice(fonts: list[str]) -> str:
    linies = ["AVLizador KenLM: Valencian n-gram language model",
              f"{autors_text()}, 2026. Made for AVLizador ({GITHUB}).",
              "Dedicated to the public domain under CC0 1.0",
              "(https://creativecommons.org/publicdomain/zero/1.0/).", "",
              "Trained on text from:"]
    linies += [f"- {FONTS[f][1]}" for f in fonts]
    linies += ["", "The KenLM library (Kenneth Heafield, GNU LGPL 2.1, https://github.com/kpu/kenlm)",
               "is not included in this repository."]
    return "\n".join(linies) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dir", type=Path, required=True, help="carpeta amb el .binary, el _freq.json i el classificador")
    p.add_argument("--nom", default=NOM_MODEL, help="nom del model en la carpeta (<nom>_o5.binary, <nom>_freq.json)")
    p.add_argument("--sentit", type=Path, default=None, help="classificador (per defecte, <dir>/sentit.json)")
    p.add_argument("--fonts", nargs="+", required=True, choices=[*FONTS, "avl"],
                   help="fonts del text d'entrenament (per a la fitxa i el NOTICE)")
    args = p.parse_args(argv)
    if "avl" in args.fonts:
        sys.exit("El model porta textos de l'AVL: no es pot publicar en CC0 (decisió de l'usuari, 16/11/2026).")
    if "dogv" in args.fonts and "dogv2" in args.fonts:
        sys.exit("dogv2 ja inclou dogv: posa'n només una.")
    if "ua" in args.fonts:
        print("AVÍS: el text porta notícies de la UA; comprova'n les condicions abans de publicar en CC0.")

    binari = args.dir / f"{args.nom}_o5.binary"
    freq = args.dir / f"{args.nom}_freq.json"
    sentit = args.sentit or args.dir / "sentit.json"
    for f in (binari, freq, sentit):
        if not f.exists():
            sys.exit(f"Falta {f}")

    if EIXIDA.exists():
        shutil.rmtree(EIXIDA)
    EIXIDA.mkdir(parents=True)
    # Amb els noms que busca el paquet (NOM_MODEL), siga quin siga el de la variant.
    shutil.copy(binari, EIXIDA / f"{NOM_MODEL}_o5.binary")
    shutil.copy(freq, EIXIDA / f"{NOM_MODEL}_freq.json")
    shutil.copy(sentit, EIXIDA / "sentit.json")
    dades_freq = json.loads(freq.read_text(encoding="utf-8"))
    n_grups = len(json.loads(sentit.read_text(encoding="utf-8")).get("grups", {}))
    (EIXIDA / "README.md").write_text(
        fitxa(NOM_MODEL, args.fonts, dades_freq, n_grups, round(binari.stat().st_size / 2**20)), encoding="utf-8")
    (EIXIDA / "NOTICE").write_text(notice(args.fonts), encoding="utf-8")
    banner(EIXIDA / "assets" / "banner.png", "AVLizador KenLM", "Valencian 5-gram language model",
           "un cop acabada", "una vegada acabada")
    print(f"-> {EIXIDA} (model {args.nom}, fonts {' '.join(args.fonts)})")
    print(f"Per a pujar-lo: hf upload {REPO_HF} {EIXIDA.relative_to(ARREL).as_posix()} . --repo-type model")


if __name__ == "__main__":
    main()
