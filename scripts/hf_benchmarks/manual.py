"""
manual.py -- Prepara el benchmark manual cat→val d'AVLizador com a dataset
de Hugging Face (09/11/2026): dades en JSONL, fitxa (`README.md`) i bàner,
en `dades/hf_benchmarks/manual/` (fora de git).

Llicència: Apache 2.0 (la del projecte). Les frases del BOE es poden reutilitzar i modificar
citant "Basado en datos de la Agencia Estatal Boletín Oficial del Estado"
amb enllaç, la data i marcant els canvis (avís legal del BOE): per això
cada frase porta la data, l'enllaç al document i, si el text es va
corregir a mà, l'original (`oriental_original`, `occidental_original`);
l'atribució va en la fitxa i en el fitxer NOTICE.

Les frases de l'AVL NO entren per defecte: l'avís legal de l'AVL
(https://www.avl.gva.es/index.php/aviso-legal/) prohibix reproduir i
distribuir els textos de la web sense autorització expressa. Només
s'afigen amb `--amb-avl "<referència de l'autorització>"`.

Ús (des de l'arrel del repositori):
    python scripts/hf_benchmarks/manual.py                      # només BOE (246)
    python scripts/hf_benchmarks/manual.py --amb-avl "Autorització de l'AVL, 20/11/2026"
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comu import (  # noqa: E402
    ARREL, AUTORS, BENCH, BOE_DERIVAT, GITHUB, METRIQUES_NOTA, ORG_PER_DEFECTE, autoria, autors_text, banner,
    capcalera, cita, escriu_jsonl, escriu_notice, prepara_desti, yaml,
)

REVISIO = ARREL / "dades" / "benchmark_manual"
REPO_PER_DEFECTE = f"{ORG_PER_DEFECTE}/avlizador-manual-ca-va"

FENOMENS = {
    "DEM": "demonstratives (aquest → este)",
    "POS": "possessives (seva → seua)",
    "LEX_NOM": "nouns (feina → faena)",
    "LEX_ADJ": "adjectives (petit → xicotet)",
    "LEX_ADV": "adverbs (aquí → ací)",
    "LEX_ALTRES": "other lexicon",
    "NUM": "numerals (vuit → huit)",
    "CONJ_IND": "verbs, indicative",
    "CONJ_SUBJ": "verbs, subjunctive (pugui → puga)",
    "CONJ_IMP": "verbs, imperative",
    "CONJ_INF": "verbs, infinitive (tenir → tindre)",
    "CONJ_PART": "verbs, participle",
    "CONJ_ARREL": "verbs, different root",
    "CONJ_ALTRES": "verbs, other forms",
    "INC": "inchoative verbs (serveix → servix)",
    "PER_A": "per a + infinitive",
    "ACC": "accent (conèixer → conéixer)",
    "DOS_DUES": "dos / dues agreement",
}


def _frases(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d["frases"] if isinstance(d, dict) else d


def _pool() -> dict[str, list[dict]]:
    pool: dict[str, list[dict]] = {}
    for nom in ("pool_boe.jsonl", "pool_avl.jsonl"):
        for linia in (REVISIO / nom).read_text(encoding="utf-8").splitlines():
            r = json.loads(linia)
            pool.setdefault(r["id_origen"], []).append(r)
    return pool


def _data(valor) -> str | None:
    return str(valor)[:10] if valor else None


def files(amb_avl: bool) -> list[dict]:
    """Frases del benchmark amb la procedència i els canvis respecte de
    l'original."""
    bench = _frases(BENCH / "manual" / "benchmark_manual_cat_val.json")
    meta = {x["id"]: x for x in _frases(REVISIO / "revisio_boe_v2.json")}
    for nom in ("revisio_persona1.json", "revisio_persona2.json"):
        meta.update({x["id"]: x for x in _frases(REVISIO / nom) if x["id"].startswith("BM-AVL")})
    pool = _pool()
    eixida = []
    for b in bench:
        boe = b["id"].startswith("BM-BOE")
        if not boe and not amb_avl:
            continue
        m = meta[b["id"]]
        candidats = pool.get(m["id_origen"], [])
        orig = max(candidats, key=lambda c: difflib.SequenceMatcher(None, c["occidental"], b["occidental"]).ratio())
        fila = {
            "id": b["id"],
            "source": "BOE" if boe else "AVL",
            "oriental": b["oriental"],
            "occidental": b["occidental"],
            "oriental_original": None,
            "occidental_original": orig["occidental"] if orig["occidental"] != b["occidental"] else None,
            "oriental_is_draft": not boe,
            "phenomena": [re.sub(r"\s*\[.*\]$", "", f) for f in m.get("fenomens") or []],
            "document": m.get("document"),
            "text_type": m.get("doc_type"),
            "date": _data(m.get("data")),
            "url": m.get("url") or (f"https://www.boe.es/buscar/doc.php?id={m['document']}" if boe else None),
        }
        if boe and orig["oriental"] != b["oriental"]:
            fila["oriental_original"] = orig["oriental"]
        eixida.append(fila)
    return eixida


# --------------------------------------------------------------------------
# Fitxa
# --------------------------------------------------------------------------

def _taula_fenomens(fs: list[dict]) -> str:
    c = Counter(codi for x in fs for codi in {f.split(":")[0] for f in x["phenomena"]})
    linies = ["| Phenomenon | Sentences |", "|---|---|"]
    for codi, n in c.most_common():
        linies.append(f"| `{codi}`: {FENOMENS.get(codi, codi)} | {n} |")
    return "\n".join(linies)


def fitxa(fs: list[dict], repo: str, autoritzacio: str | None) -> str:
    boe = [f for f in fs if f["source"] == "BOE"]
    avl = [f for f in fs if f["source"] == "AVL"]
    anys = Counter(f["date"][:4] for f in boe if f["date"])
    tipus = Counter(f["text_type"] for f in avl)
    occ_boe = sum(1 for f in boe if f["occidental_original"])
    or_boe = sum(1 for f in boe if f["oriental_original"])
    occ_avl = sum(1 for f in avl if f["occidental_original"])
    autors = autors_text()
    ex = next(f for f in boe if f["id"] == "BM-BOE-001")

    if avl:
        configs_yaml = """configs:
  - config_name: default
    data_files:
      - split: test
        path: data/test.jsonl
      - split: boe
        path: data/boe.jsonl
      - split: avl
        path: data/avl.jsonl"""
        splits = (f"| `test` | {len(fs)} | BOE + AVL: **the evaluation set** |\n"
                  f"| `boe` | {len(boe)} | Official texts from the Spanish State Gazette (BOE) |\n"
                  f"| `avl` | {len(avl)} | Texts from the website of the Acadèmia Valenciana de la Llengua (AVL) |")
        llicencia_avl = (f"- **AVL sentences**: texts © Acadèmia Valenciana de la Llengua "
                         f"([avl.gva.es](https://www.avl.gva.es)), reproduced with its authorization "
                         f"({autoritzacio}). The Catalan side of these sentences was written by the authors.")
        avl_build = f"""### AVL ({len(avl)} sentences)

- **Source**: public texts from the website of the
  [Acadèmia Valenciana de la Llengua](https://www.avl.gva.es) (the
  official body that sets the Valencian standard), collected with a
  crawler of the AVLizador project: {", ".join(f"{t} ({n})" for t, n in tipus.most_common())}.
  Only documents identified as Valencian were used.
- **Valencian side**: the original AVL text ({occ_avl} sentences slightly
  corrected; the original is kept in `occidental_original`).
- **Catalan side**: a **draft** produced automatically by AVLizador's
  Valencian → Catalan engine, then **corrected by hand** by the authors
  until it was natural Catalan following the IEC standard
  (`oriental_is_draft = true`).
- Metalinguistic sentences (that talk about words, frequent in the AVL
  glossary) were removed.
"""
    else:
        configs_yaml = """configs:
  - config_name: default
    data_files:
      - split: test
        path: data/test.jsonl"""
        splits = (f"| `test` | {len(fs)} | Official texts from the Spanish State Gazette (BOE) |")
        llicencia_avl = ("- The full benchmark used in AVLizador also has 212 sentences from the website "
                         "of the Acadèmia Valenciana de la Llengua (AVL). They are **not included** here: "
                         "the AVL's legal notice does not allow reproducing its texts without express "
                         "authorization.")
        avl_build = ""

    insignia = '<img alt="Hand reviewed" src="https://img.shields.io/badge/hand-reviewed-2e8b57">\n  '
    return yaml("AVLizador manual benchmark (Catalan → Valencian)", "n<1K", configs_yaml) + "\n" + capcalera(
        repo, "AVLizador manual benchmark: Catalan to Valencian", len(fs), insignia) + f"""
# AVLizador manual benchmark: Catalan → Valencian

A hand-reviewed test set for **dialectal adaptation** from Central/Eastern
Catalan (standard of the Institut d'Estudis Catalans, IEC) to
**Valencian** (standard of the Acadèmia Valenciana de la Llengua, AVL).
Both sides are the same language: only the dialectal features change
(demonstratives, possessives, verb forms, lexicon, accents…).

{autoria()} It is the benchmark used to evaluate AVLizador.

> *Conjunt d'avaluació revisat a mà per a adaptar textos del català
> oriental (norma de l'IEC) al valencià (norma de l'AVL). Fet per a
> AVLizador per {' i '.join(AUTORS)}.*

| Catalan (input) | Valencian (reference) |
|---|---|
| {ex["oriental"]} | {ex["occidental"]} |

## Splits

| Split | Sentences | Content |
|---|---|---|
{splits}

## Fields

| Field | Description |
|---|---|
| `id` | Sentence id (`BM-BOE-…`, `BM-AVL-…`) |
| `source` | `BOE` or `AVL` |
| `oriental` | Catalan sentence (input) |
| `occidental` | Valencian sentence (reference) |
| `oriental_original`, `occidental_original` | The original text when the authors corrected it by hand; `null` if unchanged |
| `oriental_is_draft` | `true` when the Catalan side was drafted automatically and corrected by hand (AVL) |
| `phenomena` | Dialectal phenomena found in the pair, as `CODE: catalan → valencian` |
| `document`, `text_type`, `date`, `url` | Where the sentence comes from |

## Where the data come from

### BOE ({len(boe)} sentences)

- **Source**: the Spanish State Gazette ([BOE](https://www.boe.es))
  publishes laws and regulations in Catalan and in Valencian, as two
  separate official versions of the same Spanish text. The AVLizador
  project downloaded the documents from {min(anys)} to {max(anys)} and
  aligned the two versions sentence by sentence (267,962 aligned pairs).
- **Selection**: aligned pairs with a good alignment (length ratio 0.85-1.15),
  complete sentences of 8 to 40 words, no lists, tables or headings; the
  Valencian side clearly Valencian and the Catalan side clearly Catalan
  according to AVLizador's *Grau Dialectal* (GD = 1 and GD = 0, at least
  two dialectal markers each); chosen to cover the dialectal phenomena
  of the project's dictionaries and rules (table below), at most two
  sentences per document.
- **Review**: every sentence was reviewed by hand from the original
  aligned text by the authors. {occ_boe} Valencian and {or_boe} Catalan
  sentences were corrected by hand; the original is kept in `occidental_original` /
  `oriental_original`. The rest are the official texts unchanged.
- Years: {", ".join(f"{a} ({n})" for a, n in sorted(anys.items()))}.

{avl_build}
### Phenomena covered

{_taula_fenomens(fs)}

## Usage

```python
from datasets import load_dataset

ds = load_dataset("{repo}", split="test")
print(ds[0]["oriental"], "→", ds[0]["occidental"])
```

With [AVLizador]({GITHUB}) installed, the split can be evaluated directly:

```bash
avlizador avalua --fitxer test.jsonl
```

## Results (BOE sentences)

Same run for all systems. AVLizador against leaving the text untranslated
and against the best of 9 general LLMs asked to adapt the text. TER and
WER: lower is better. GD (*Grau Dialectal*, 0 = Catalan, 1 = Valencian)
measures how Valencian the output is; the references score 0.995.

| System | Exact match | BLEU | chrF | TER ↓ | WER ↓ | GD |
|---|---|---|---|---|---|---|
| **AVLizador** (rules + FLOR-760M) | **32 / 246 (13.0 %)** | **83.82** | **93.59** | **9.26** | **9.94** | **0.989** |
| Best LLM (gemma3:12b) | 0 / 246 | 66.57 | 86.46 | 18.83 | 19.73 | 0.354 |
| Untranslated (Catalan as is) | 0 / 246 | 61.79 | 85.71 | 20.16 | 20.70 | 0.000 |

On the full benchmark used in AVLizador (BOE + AVL, 458 sentences),
AVLizador 1.2.0 reaches 228/458 exact matches (BLEU 90.93, TER 5.59). Few
BOE sentences match exactly because the official Valencian version often
rewords the text (future tense, synonyms, articles), not because of the
dialectal features.

{METRIQUES_NOTA}

## Limitations

- Valencian often has more than one valid form (*este/aquest*,
  *servici/servei*); the references follow the AVL standard and the style
  of each source, so an exact-match error is not always a real error.
- BOE sentences are administrative and legal register.
- The selection used AVLizador's dictionaries and GD, so the set is
  focused on the phenomena AVLizador models.

## License and attribution

- This dataset: **Apache 2.0**, {autors}. Keep the `NOTICE` file when
  redistributing it.
- **BOE sentences**: *{BOE_DERIVAT}*
  ([www.boe.es](https://www.boe.es)). Each sentence
  keeps its document, date and link; changes made by the authors are
  marked in `oriental_original` / `occidental_original`. This is not an
  official version of the texts, and the BOE does not endorse this work.
{llicencia_avl}

{cita("avlizador_manual_benchmark_2026", "AVLizador manual benchmark: Catalan to Valencian dialectal adaptation", repo)}"""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", default=REPO_PER_DEFECTE, help="org/nom del dataset en el Hub")
    p.add_argument("--amb-avl", metavar="AUTORITZACIO",
                   help="inclou les frases de l'AVL; cal la referència de l'autorització de l'AVL")
    args = p.parse_args(argv)

    desti = prepara_desti("manual")
    fs = files(bool(args.amb_avl))
    escriu_jsonl(desti / "data" / "test.jsonl", fs)
    if args.amb_avl:
        escriu_jsonl(desti / "data" / "boe.jsonl", [f for f in fs if f["source"] == "BOE"])
        escriu_jsonl(desti / "data" / "avl.jsonl", [f for f in fs if f["source"] == "AVL"])
    (desti / "README.md").write_text(fitxa(fs, args.repo, args.amb_avl), encoding="utf-8")
    escriu_notice(desti, "AVLizador manual benchmark (Catalan -> Valencian)", BOE_DERIVAT)
    banner(desti / "assets" / "banner.png", "AVLizador manual benchmark",
           "Catalan → Valencian dialectal adaptation · hand-reviewed",
           "aquesta  seva  feina", "esta  seua  faena")
    print(f"{len(fs)} frases ({Counter(f['source'] for f in fs)}) -> {desti}")


if __name__ == "__main__":
    main()
