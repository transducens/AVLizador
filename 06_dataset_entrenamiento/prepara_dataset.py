"""
prepara_dataset.py -- Prepara los datos para el finetuning: SOLO el corpus
sintetico (AVL) se parte en train/dev/test. El corpus real (BOE) se
normaliza al MISMO esquema de campos pero se deja como fichero aparte,
sin mezclar -- sirve para evaluar despues si el modelo generaliza a un
dominio real (legal) que nunca ha visto en entrenamiento.

El split del sintetico se agrupa por documento (doc_id), nunca por frase
suelta, para que ninguna frase de un mismo documento acabe a la vez en
train y en dev/test (fuga de datos).

El benchmark_corpus.json (60 frases con referencia humana) NO se toca
aqui -- queda reservado aparte como test final "de verdad".

Uso:
    python prepara_dataset.py
    python prepara_dataset.py --sintetic ruta/al/corpus_v2.jsonl  # cuando termine la v2
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def carrega_boe(path: Path) -> list[dict]:
    registres = []
    with open(path, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if not linia:
                continue
            r = json.loads(linia)
            registres.append({
                "val": r["texto_valenciano"],
                "cat": r["texto_catalan"],
                "origen": "boe",
                "doc_id": r["documento_id"],
                "similitud": r.get("similitud"),
            })
    return registres


def carrega_sintetic(path: Path) -> list[dict]:
    registres = []
    descartades = 0
    with open(path, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if not linia:
                continue
            r = json.loads(linia)
            if r.get("motius_sospita"):
                descartades += 1
                continue
            registres.append({
                "val": r["frase_val"],
                "cat": r["frase_cat"],
                "origen": "avl_sintetic",
                "doc_id": r["doc_id"],
                "similitud": None,
            })
    print(f"  (sintetic: {descartades} frases sospitoses descartades)")
    return registres


def normalitza_clau(val: str, cat: str) -> tuple[str, str]:
    return (val.strip().lower(), cat.strip().lower())


def deduplica(registres: list[dict]) -> list[dict]:
    vistos = set()
    out = []
    for r in registres:
        clau = normalitza_clau(r["val"], r["cat"])
        if clau in vistos:
            continue
        vistos.add(clau)
        out.append(r)
    return out


def split_per_document(registres: list[dict], seed: int, prop_dev: float, prop_test: float):
    """Barreja documents (no frases) i reparteix per document fins arribar
    aproximadament a la proporcio objectiu de FRASES en dev/test -- mai
    parteix un document entre dos splits."""
    per_doc: dict[str, list] = {}
    for r in registres:
        per_doc.setdefault(r["doc_id"], []).append(r)

    claus = list(per_doc.items())
    rng = random.Random(seed)
    rng.shuffle(claus)

    total = len(registres)
    objectiu_test = total * prop_test
    objectiu_dev = total * prop_dev

    train, dev, test = [], [], []
    n_test = n_dev = 0
    for _, frases in claus:
        if n_test < objectiu_test:
            test.extend(frases)
            n_test += len(frases)
        elif n_dev < objectiu_dev:
            dev.extend(frases)
            n_dev += len(frases)
        else:
            train.extend(frases)
    return train, dev, test


def escriu_jsonl(registres: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in registres:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def resum(nom: str, regs: list[dict]) -> None:
    print(f"  {nom:<6} {len(regs):>7} pares")


def main():
    parser = argparse.ArgumentParser(
        description="Prepara train/dev/test SOLO del sintetico; normaliza BOE aparte como eval fuera de dominio"
    )
    parser.add_argument("--boe", default=str(ROOT / "data" / "boe" / "corpus_entrenamiento.jsonl"))
    parser.add_argument("--sintetic", default=str(ROOT / "data" / "sintetico" / "corpus_sintetic_val_cat.jsonl"))
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "dataset_entrenamiento"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prop-dev", type=float, default=0.05, help="Proporcio de frases del sintetic per a dev (per defecte 5%%)")
    parser.add_argument("--prop-test", type=float, default=0.05, help="Proporcio de frases del sintetic per a test (per defecte 5%%)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Sintetic: el UNICO que se parte en train/dev/test ───────────────
    print("Carregant sintetic AVL (el que s'entrena)...")
    sintetic = carrega_sintetic(Path(args.sintetic))
    abans = len(sintetic)
    sintetic = deduplica(sintetic)
    print(f"  {abans} -> {len(sintetic)} tras dedup interna ({abans - len(sintetic)} duplicats)")

    train, dev, test = split_per_document(sintetic, args.seed, args.prop_dev, args.prop_test)
    escriu_jsonl(train, out_dir / "train.jsonl")
    escriu_jsonl(dev, out_dir / "dev.jsonl")
    escriu_jsonl(test, out_dir / "test.jsonl")

    print("\nSplit del sintetic (esto es lo que se entrena/valida):")
    resum("train", train)
    resum("dev", dev)
    resum("test", test)

    # ── 2. BOE: normalizado al MISMO esquema, pero NUNCA mezclado con lo de
    # arriba -- fichero aparte, pensado para evaluar generalizacion fuera de
    # dominio (legal/real) una vez el modelo ya este entrenado solo con el
    # sintetico. Se le quita cualquier frase que coincida EXACTAMENTE con
    # alguna del train del sintetico, para que de verdad sea "no vista".
    print("\nCarregant BOE (queda APART, no s'entrena amb ell)...")
    boe = carrega_boe(Path(args.boe))
    abans = len(boe)
    boe = deduplica(boe)
    print(f"  {abans} -> {len(boe)} tras dedup interna ({abans - len(boe)} duplicats)")

    claus_train = {normalitza_clau(r["val"], r["cat"]) for r in train}
    abans = len(boe)
    boe = [r for r in boe if normalitza_clau(r["val"], r["cat"]) not in claus_train]
    if abans != len(boe):
        print(f"  {abans - len(boe)} frases de BOE coincidian exactamente con el train sintetico -- eliminadas del eval")

    escriu_jsonl(boe, out_dir / "boe_eval.jsonl")
    print(f"\nBOE normalizado (mismo esquema, fichero aparte): {len(boe)} pares -> {out_dir / 'boe_eval.jsonl'}")

    print(f"\nGuardat tot a {out_dir}/")
    print("train.jsonl / dev.jsonl / test.jsonl  -> entrenar y validar (solo sintetico)")
    print("boe_eval.jsonl                        -> evaluar generalizacion fuera de dominio (NO entrenar con esto)")
    print("benchmark_corpus.json (03_seleccion_de_modelo/) -> test final humano, aparte de todo lo anterior")


if __name__ == "__main__":
    main()
