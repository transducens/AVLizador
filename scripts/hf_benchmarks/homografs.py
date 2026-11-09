"""
homografs.py -- Prepara els benchmarks d'homògrafs cat→val d'AVLizador com
UN dataset de Hugging Face amb dos configuracions, `v2` (per defecte) i
`v1` (decisió de l'usuari, 09/11/2026), en `dades/hf_benchmarks/homografs/`
(fora de git). El v1 és l'únic amb les col·lisions cop/cops.

Frases escrites per a la prova (no tretes de cap corpus): no hi ha textos
de tercers, només Apache 2.0. Les referències les va generar el motor
d'AVLizador posant el candidat esperat en el punt ambigu
(`pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py`) i es
van revisar a mà.

Ús (des de l'arrel del repositori):
    python scripts/hf_benchmarks/homografs.py --repo ORG/avlizador-homographs-ca-va
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comu import (  # noqa: E402
    AUTORS, BENCH, GITHUB, METRIQUES_NOTA, ORG_PER_DEFECTE, autoria, banner, capcalera, cita, escriu_jsonl,
    escriu_notice, prepara_desti, yaml,
)

FITXERS = {2: "benchmark_homografs_v2_cat_val.json", 1: "benchmark_homografs_cat_val.json"}
TIPUS = {
    "colisio": "collision: the Catalan word is never kept, the choice is between two Valencian words",
    "irresoluble": "same grammatical category for both senses: only the context decides",
    "resoluble": "different grammatical categories: the part-of-speech tag decides",
}

# Resultats (v2: 06/11/2026, AVLizador 1.2.0; v1, sense traduir i motor sol:
# 09/11/2026, mateixes mètriques de `avlizador avalua`).
RESULTATS = {
    2: """| System | Exact match | BLEU | chrF | TER ↓ |
|---|---|---|---|---|
| **AVLizador 1.2.0** (rules + FLOR-760M, margin 2, Catalan by default) | **95 / 160 (59.4 %)** | **84.29** | **92.29** | **5.82** |
| AVLizador, rule engine only | 82 / 160 (51.3 %) | – | – | – |
| Untranslated (Catalan as is) | 59 / 160 (36.9 %) | 74.84 | 87.30 | 10.81 |

The rule engine alone almost always picks the dialectal reading (68/72
right on the Valencian senses, 14/88 on the others). AVLizador 1.2.0 is
deliberately conservative: when the language model is not clearly sure
(margin 2), it keeps the Catalan word, because a wrong replacement changes
the meaning while an untranslated word only leaves a Catalan form. A
less conservative setting of the same system reached 124/160.""",
    1: """| System | Exact match | BLEU | chrF | TER ↓ |
|---|---|---|---|---|
| **AVLizador 1.2.0** (rules + FLOR-760M) | **71 / 98 (72.4 %)** | **88.51** | **94.18** | **4.44** |
| AVLizador, rule engine only | 33 / 98 (33.7 %) | 74.24 | 85.46 | 11.16 |
| Untranslated (Catalan as is) | 23 / 98 (23.5 %) | 68.16 | 82.42 | 15.59 |""",
}


def _files(versio: int) -> list[dict]:
    d = json.loads((BENCH / "homografs" / FITXERS[versio]).read_text(encoding="utf-8"))
    eixida = []
    for x in d["frases"] if isinstance(d, dict) else d:
        fila = {"id": x["id"], "oriental": x["oriental"], "occidental": x["occidental"],
                "word": x.get("paraula"), "sense": x.get("sentit"), "expected": x.get("esperat"),
                "ambiguity_type": x.get("tipus"), "engine_output": x.get("motor_sol")}
        if versio == 1:
            fila.pop("sense")
        eixida.append(fila)
    return eixida


def _taula_paraules(fs: list[dict], versio: int) -> str:
    if versio == 2:
        sentits: dict[str, Counter] = defaultdict(Counter)
        for f in fs:
            sentits[f["word"]][f["sense"]] += 1
        linies = ["| Word | Senses (sentences) |", "|---|---|"]
        for w, c in sentits.items():
            linies.append(f"| *{w}* | " + "; ".join(f"{s} ({n})" for s, n in c.items()) + " |")
        return "\n".join(linies)
    c = Counter(f["word"] or "(control, no ambiguous word)" for f in fs)
    return "| Word | Sentences |\n|---|---|\n" + "\n".join(f"| *{w}* | {n} |" for w, n in c.most_common())


def _tipus(fs: list[dict]) -> str:
    c = Counter(f["ambiguity_type"] for f in fs if f["ambiguity_type"])
    return ", ".join(f"`{t}` {n}" for t, n in c.most_common())


def fitxa(v2: list[dict], v1: list[dict], repo: str) -> str:
    """Una sola fitxa per a les dos versions (dos configuracions)."""
    ex2, ex1 = v2[0], next(f for f in v1 if f["word"] == "cop")
    titol = "AVLizador homograph benchmark"
    configs = """configs:
  - config_name: v2
    default: true
    data_files:
      - split: test
        path: data/v2/test.jsonl
  - config_name: v1
    data_files:
      - split: test
        path: data/v1/test.jsonl"""
    nomes_v1 = sorted({f["word"] for f in v1 if f["word"]} - {f["word"] for f in v2})
    comunes = len({f["oriental"] for f in v1} & {f["oriental"] for f in v2})
    return yaml(f"{titol} (Catalan → Valencian)", "n<1K", configs) + "\n" + capcalera(
        repo, f"{titol}: ambiguous words, Catalan to Valencian", len(v2) + len(v1)) + f"""
# {titol}: Catalan → Valencian

A test set of **ambiguous words** for dialectal adaptation from
Central/Eastern Catalan (IEC standard) to **Valencian** (AVL standard).
Some Catalan words have a Valencian equivalent only in one of their
senses: *nou* is "nut" (Valencian *anou*), but also "new" and "nine"
(*nou* in Valencian too); *cop* is "blow" (*colp*) or "time" (*vegada*).
A good adapter has to replace the word only in the right sense.

{autoria()}

> *Conjunt d'avaluació de paraules ambigües per a adaptar textos del
> català oriental al valencià. Fet per a AVLizador per {" i ".join(AUTORS)}.*

## Configurations

| Config | Sentences | What it is |
|---|---|---|
| **`v2`** (default) | {len(v2)} | **18 ambiguous forms, 4 sentences for each of their senses.** The same number of sentences per sense, so a system that always picks one reading cannot score well. Use this one to evaluate. |
| `v1` | {len(v1)} | The first set, **not balanced by sense**. It is the only one with the **collisions** {", ".join(f"*{w}*" for w in nomes_v1)} (the Catalan word is never kept: *colp* or *vegada*), plus {sum(1 for f in v1 if not f["word"])} control sentences without any ambiguous word. |

The two configurations are separate test sets: report their results
separately. They share {comunes} sentences.

```python
from datasets import load_dataset

v2 = load_dataset("{repo}", "v2", split="test")
v1 = load_dataset("{repo}", "v1", split="test")
print(v2[0]["oriental"], "→", v2[0]["occidental"], "|", v2[0]["word"], "→", v2[0]["expected"])
```

| Config | Catalan (input) | Valencian (reference) | Word / sense |
|---|---|---|---|
| `v2` | {ex2["oriental"]} | {ex2["occidental"]} | *{ex2["word"]}* / {ex2["sense"]} |
| `v1` | {ex1["oriental"]} | {ex1["occidental"]} | *{ex1["word"]}* → *{ex1["expected"]}* |

## Fields

| Field | Description |
|---|---|
| `id` | Sentence id (`HG2-…` in v2, `HG…` in v1) |
| `oriental` | Catalan sentence (input) |
| `occidental` | Valencian sentence (reference) |
| `word` | The ambiguous Catalan word (`null` in the control sentences) |
| `sense` | `v2` only: the sense in this sentence, category and meaning (*n: fruit (nuez)*) |
| `expected` | The right form in this sentence: the Valencian word, or the same Catalan word when it must not change |
| `ambiguity_type` | {"; ".join(f"`{t}`: {d}" for t, d in TIPUS.items())} |
| `engine_output` | What AVLizador's rule engine alone produces, for reference |

Ambiguity types: v2 {_tipus(v2)}; v1 {_tipus(v1)}.

## Words covered

### `v2`

{_taula_paraules(v2, 2)}

The senses come from the readings listed in AVLizador's lexicon, plus the
verb readings of *manca/manques* (*mancar*) and *deu* (*deure*).

### `v1`

{_taula_paraules(v1, 1)}

## How it was built

- **Sentences**: written for this test set, not taken from any corpus,
  each one with a single ambiguous word used in a known sense.
- **References**: AVLizador's rule engine adapted each sentence with the
  expected form placed at the ambiguous word (and the article or
  adjective agreeing with it); then every reference was **reviewed by
  hand** (for example, *un altre vegada* → *una altra vegada*).
- The rest of each sentence is ordinary Catalan, so the references also
  contain the usual dialectal changes (*aquest → este*, *seva → seua*…).

## Results

### `v2`

{RESULTATS[2]}

### `v1`

{RESULTATS[1]}

{METRIQUES_NOTA}

## Limitations

- Small and synthetic: the sentences are short and written to make one
  sense clear; real texts are harder.
- The references follow AVLizador's lexicon for the dialectal
  equivalents (*anou*, *colp*, *bragues*, *hamaca*…).

## License

**Apache 2.0**, {" and ".join(AUTORS)}. Keep the `NOTICE` file when
redistributing it.

{cita("avlizador_homographs_2026", f"{titol}: ambiguous words in Catalan to Valencian adaptation", repo)}"""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", default=f"{ORG_PER_DEFECTE}/avlizador-homographs-ca-va", help="org/nom del dataset")
    args = p.parse_args(argv)
    desti = prepara_desti("homografs")
    v2, v1 = _files(2), _files(1)
    escriu_jsonl(desti / "data" / "v2" / "test.jsonl", v2)
    escriu_jsonl(desti / "data" / "v1" / "test.jsonl", v1)
    (desti / "README.md").write_text(fitxa(v2, v1, args.repo), encoding="utf-8")
    escriu_notice(desti, "AVLizador homograph benchmark (Catalan -> Valencian)", None)
    banner(desti / "assets" / "banner.png", "AVLizador homographs",
           "Ambiguous words · Catalan → Valencian dialectal adaptation",
           "una  nou  ·  un  cop", "una  anou  ·  un  colp")
    print(f"homografs: v2 {len(v2)} + v1 {len(v1)} -> {desti} ({args.repo})")


if __name__ == "__main__":
    main()
