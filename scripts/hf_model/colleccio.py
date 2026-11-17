"""
colleccio.py -- Crea (o completa) la col·lecció "AVLizador" de Hugging Face
(16/11/2026) amb el model KenLM i els datasets de benchmarks. Sense
`--crea` només diu què faria. Cal haver iniciat la sessió amb un token
d'escriptura de l'organització (`hf auth login`).

Ús (des de l'arrel del repositori):
    python scripts/hf_model/colleccio.py            # què faria
    python scripts/hf_model/colleccio.py --crea     # ho fa
Si un repositori encara no existix en el Hub, s'avisa i se salta (es pot tornar
a executar després: el que ja hi és no es duplica).
"""

from __future__ import annotations

import argparse

ORG = "transducens"
TITOL = "AVLizador"
DESCRIPCIO = ("Catalan → Valencian dialectal adaptation: the KenLM model used by AVLizador "
              "and its evaluation benchmarks.")
ELEMENTS = [
    ("model", f"{ORG}/avlizador-kenlm-va", "Valencian 5-gram KenLM model used by AVLizador for ambiguous words"),
    ("dataset", f"{ORG}/avlizador-manual-ca-va", "Manual benchmark: 458 sentences (BOE + AVL), the evaluation set"),
    ("dataset", f"{ORG}/avlizador-homographs-ca-va", "Homographs: sentences with ambiguous words (configs v2 and v1)"),
    ("dataset", f"{ORG}/avlizador-boe-strict-ca-va", "BOE strict: aligned sentences whose differences are all dialectal"),
    ("dataset", f"{ORG}/avlizador-boe-broad-ca-va", "BOE broad: aligned sentences with only one-to-one substitutions"),
]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--crea", action="store_true", help="crear-la de veres (sense: només ho mostra)")
    args = p.parse_args(argv)

    from huggingface_hub import HfApi

    api = HfApi()
    existix = {}
    for tipus, repo, _ in ELEMENTS:
        existix[repo] = api.repo_exists(repo, repo_type=tipus)
        print(f"{'  ' if existix[repo] else '! '}{tipus:8} {repo}{'' if existix[repo] else '  (encara no existix)'}")
    if not args.crea:
        print(f"\nAmb --crea: col·lecció '{TITOL}' en {ORG} amb els que existixen.")
        return
    col = api.create_collection(title=TITOL, namespace=ORG, description=DESCRIPCIO, exists_ok=True)
    for tipus, repo, nota in ELEMENTS:
        if existix[repo]:
            api.add_collection_item(col.slug, item_id=repo, item_type=tipus, note=nota, exists_ok=True)
    print(f"\n-> https://huggingface.co/collections/{col.slug}")


if __name__ == "__main__":
    main()
