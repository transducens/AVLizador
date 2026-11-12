"""
boe_dialectal.py -- Prepara els benchmarks BOE estricte i BOE ampli
d'AVLizador com a datasets de Hugging Face (09/11/2026), en
`dades/hf_benchmarks/boe_estricte/` i `dades/hf_benchmarks/boe_ampli/`
(fora de git). Splits: `test` (la mostra de 2.000, llavor 21) i `full`.

Les frases són del BOE alineat (`dades/boe/corpus_entrenamiento.jsonl`,
d'on es trauen el document i la data de cada parell: l'id `boe_<n>` és el
número de línia). Respecte de l'original només canvien els apòstrofs i
cometes simples tipogràfics (’ ‘ → '), comprovat en els 73.705 parells de
l'ampli. Atribució del BOE en la fitxa i en el NOTICE.

Ús (des de l'arrel del repositori):
    python scripts/hf_benchmarks/boe_dialectal.py
    python scripts/hf_benchmarks/boe_dialectal.py --nom estricte
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comu import (  # noqa: E402
    ARREL, AUTORS, BENCH, BOE_DERIVAT, METRIQUES_NOTA, ORG_PER_DEFECTE, autoria, banner, capcalera, cita,
    escriu_jsonl, escriu_notice, prepara_desti, yaml,
)

CORPUS = ARREL / "dades" / "boe" / "corpus_entrenamiento.jsonl"

# Resultats (06/11/2026, AVLizador 1.2.0; sense traduir, 09/11/2026; mateixes
# mètriques de `avlizador avalua`) sobre el split `test`.
DADES = {
    "estricte": {
        "titol": "AVLizador BOE strict benchmark",
        "curt": "strict",
        "mida": "1K<n<10K",
        "que": ("BOE sentence pairs whose differences are **only safe dialectal ones**. "
                "It measures **regressions**: everything here is something AVLizador's dictionaries "
                "and rules should already handle."),
        "criteri": """From the structural filter above, the pairs with at least one
  difference where **every** difference is a safe dialectal one:
  (a) the pair of words is in AVLizador's dictionaries (lexicon,
  conjugations, demonstratives); (b) spaCy gives the same lemma and the
  same features (tense, mood, person, number, verb form) on both sides,
  with the same elided prefix and clitic; (c) only the open/closed accent
  changes (*entès / entés*); (d) the *a* of *per a* + infinitive; (e) an
  inchoative verb (*estableix / establix*). Any other difference
  (capitalization, tense, an unclassified word) leaves the pair out.
  Result: 7,906 pairs explained by the dictionaries and 1,547 by (b)-(e).""",
        "resultats": """| System | Exact match | BLEU | chrF | TER ↓ | WER ↓ |
|---|---|---|---|---|---|
| **AVLizador 1.2.0** | **1,887 / 2,000 (94.3 %)** | **99.03** | **99.65** | **0.30** | **0.57** |
| Untranslated (Catalan as is) | 0 / 2,000 | 79.37 | 92.98 | 7.34 | 7.60 |""",
        "limit": ("The selection uses AVLizador's own dictionaries (criterion a), so this set is good to "
                  "detect regressions, **not** to compare AVLizador with other systems on equal terms."),
    },
    "ampli": {
        "titol": "AVLizador BOE broad benchmark",
        "curt": "broad",
        "mida": "10K<n<100K",
        "que": ("BOE sentence pairs **without rewording**: identical, or differing only in one-to-one "
                "word substitutions. It measures **coverage gaps**: the differences AVLizador does not "
                "know yet show up here."),
        "criteri": """Only the structural filter above, **without any dictionary**: 32,079
  identical pairs and 41,626 pairs with only word-for-word substitutions.
  Many substitutions are dialectal; others are style choices of the
  official translation (*és → serà*, synonyms).""",
        "resultats": """| System | Exact match | BLEU | chrF | TER ↓ | WER ↓ |
|---|---|---|---|---|---|
| **AVLizador 1.2.0** | **1,212 / 2,000 (60.6 %)** | **88.35** | **95.57** | **3.66** | **5.92** |
| Untranslated (Catalan as is) | 872 / 2,000 (43.6 %) | 82.96 | 93.68 | 6.82 | 9.06 |

About 44 % of the pairs are identical in both versions, so leaving the
text untranslated already matches many of them.""",
        "limit": ("Not reviewed by hand: some substitutions are style choices of the official Valencian "
                  "version, not dialectal differences, so a system can be right and still not match."),
    },
}


def _metadades(ids: set[int]) -> dict[int, dict]:
    meta = {}
    with open(CORPUS, encoding="utf-8") as f:
        for i, linia in enumerate(f):
            if i in ids:
                r = json.loads(linia)
                meta[i] = {"document": r["documento_id"], "date": r["fecha"], "line_id": r["id"]}
    return meta


def _files(nom: str) -> dict[str, list[dict]]:
    splits = {"test": f"benchmark_boe_dialectal_{nom}.json", "full": f"benchmark_boe_dialectal_{nom}_complet.json"}
    dades = {s: json.loads((BENCH / "boe_dialectal" / f).read_text(encoding="utf-8")) for s, f in splits.items()}
    meta = _metadades({int(x["id"][4:]) for x in dades["full"]})
    eixida = {}
    for s, fs in dades.items():
        eixida[s] = []
        for x in fs:
            m = meta[int(x["id"][4:])]
            eixida[s].append({"id": x["id"], "oriental": x["oriental"], "occidental": x["occidental"], **m,
                              "url": f"https://www.boe.es/buscar/doc.php?id={m['document']}"})
    return eixida


def fitxa(nom: str, fs: dict[str, list[dict]], repo: str) -> str:
    d = DADES[nom]
    test, full = fs["test"], fs["full"]
    anys = Counter(f["date"][:4] for f in full)
    ex = next(f for f in test if f["oriental"] != f["occidental"] and 60 < len(f["oriental"]) < 160 and f["oriental"][0].isupper() and f["oriental"].endswith("."))
    configs = """configs:
  - config_name: default
    data_files:
      - split: test
        path: data/test.jsonl
      - split: full
        path: data/full.jsonl"""
    altre = "ampli" if nom == "estricte" else "estricte"
    repo_altre = repo.replace(f"-{d['curt']}-", f"-{DADES[altre]['curt']}-")
    return yaml(f"{d['titol']} (Catalan → Valencian)", d["mida"], configs) + "\n" + capcalera(
        repo, f"{d['titol']}: Catalan to Valencian", len(full)) + f"""
# {d["titol"]}: Catalan → Valencian

Sentence pairs from the two official versions, **Catalan and Valencian**,
of the Spanish State Gazette (BOE), filtered automatically for
**dialectal adaptation** from Central/Eastern Catalan (IEC standard) to
**Valencian** (AVL standard). {d["que"]}

{autoria()} Companion set: [{DADES[altre]["titol"]}](https://huggingface.co/datasets/{repo_altre}).

> *Parells de frases del BOE en català i en valencià per a avaluar
> l'adaptació del català oriental al valencià. Fet per a AVLizador per
> {" i ".join(AUTORS)}.*

| Catalan (input) | Valencian (reference) |
|---|---|
| {ex["oriental"]} | {ex["occidental"]} |

## Splits

| Split | Pairs | Content |
|---|---|---|
| `test` | {len(test):,} | Fixed random sample (seed 21): use this one to evaluate |
| `full` | {len(full):,} | All the pairs that pass the filter |

## Fields

| Field | Description |
|---|---|
| `id` | Pair id (`boe_<n>`, line of the aligned corpus) |
| `oriental` | Catalan sentence (input) |
| `occidental` | Valencian sentence (reference) |
| `document`, `date`, `url` | BOE document, publication date and link |
| `line_id` | Sentence id inside the document |

## Where the data come from

- **Source**: the Spanish State Gazette ([BOE](https://www.boe.es))
  publishes laws and regulations in Catalan and in Valencian, as two
  separate official versions of the same Spanish text. The AVLizador
  project downloaded the documents from {min(anys)} to {max(anys)} and
  aligned the two versions sentence by sentence (267,963 aligned pairs).
- **Structural filter**: lines of 30 to 300 characters, Valencian/Catalan
  length ratio 0.85-1.15; the words of both sides are aligned and only
  pairs that are **identical** or differ only in **one-to-one
  substitutions** (blocks of up to 2 words; no insertions, deletions or
  reordering, except the *a* of *per a*) are kept. This drops the
  official translation's rewordings (84,695 pairs).
- **This set**: {d["criteri"]}
- **No manual review.** The texts are the official ones; only
  typographic apostrophes and single quotes were normalized (’ ‘ → ').
- Years ({len(full):,} pairs): {", ".join(f"{a} ({n:,})" for a, n in sorted(anys.items()))}.

## Usage

```python
from datasets import load_dataset

ds = load_dataset("{repo}", split="test")
print(ds[0]["oriental"], "→", ds[0]["occidental"])
```

## Results (`test` split)

{d["resultats"]}

{METRIQUES_NOTA}

## Limitations

- {d["limit"]}
- Administrative and legal register only.

## License and attribution

- This dataset: **Apache 2.0**, {" and ".join(AUTORS)}. Keep the
  `NOTICE` file when redistributing it.
- **BOE sentences**: *{BOE_DERIVAT}* ([www.boe.es](https://www.boe.es)).
  Each pair keeps its document, date and link. This is not an official
  version of the texts, and the BOE does not endorse this work.

{cita(f"avlizador_boe_{d['curt']}_2026", f"{d['titol']}: Catalan to Valencian dialectal adaptation", repo)}"""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--nom", choices=tuple(DADES), help="només un (per defecte, els dos)")
    p.add_argument("--org", default=ORG_PER_DEFECTE, help="usuari o organització del Hub")
    args = p.parse_args(argv)
    for nom in [args.nom] if args.nom else list(DADES):
        d = DADES[nom]
        repo = f"{args.org}/avlizador-boe-{d['curt']}-ca-va"
        desti = prepara_desti(f"boe_{nom}")
        fs = _files(nom)
        for s, files in fs.items():
            escriu_jsonl(desti / "data" / f"{s}.jsonl", files)
        (desti / "README.md").write_text(fitxa(nom, fs, repo), encoding="utf-8")
        escriu_notice(desti, f"{d['titol']} (Catalan -> Valencian)", BOE_DERIVAT)
        banner(desti / "assets" / "banner.png", f"AVLizador BOE {d['curt']}",
               "Official Catalan and Valencian versions of the BOE",
               "aquesta  resolució", "esta  resolució")
        print(f"boe_{nom}: {len(fs['test'])} + {len(fs['full'])} -> {desti} ({repo})")


if __name__ == "__main__":
    main()
