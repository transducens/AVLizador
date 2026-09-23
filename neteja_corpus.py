# neteja_corpus.py
import json
import re

def neteja_text(text: str) -> str:
    if not text:
        return ""

    # Elimina dates del glossari tipus [13/07/2020]
    text = re.sub(r'^\[\d{2}/\d{2}/\d{4}\]\s*', '', text)

    lines = text.splitlines()
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            if result and result[-1] != "":
                result.append("")
            i += 1
            continue

        # Màxim 5 fusions per línia per evitar bucles infinits
        fusions = 0
        while i + 1 < len(lines) and fusions < 5:
            next_line = lines[i + 1].strip()
            if not next_line:
                break

            current_ends_mid = (
                len(line) < 45
                and line[-1] not in ".?!:;\"»"
            )
            next_starts_punct = bool(next_line) and next_line[0] in ",:;.!?)»"

            if current_ends_mid or next_starts_punct:
                if next_starts_punct:
                    line = line + next_line
                else:
                    line = line + " " + next_line
                i += 1
                fusions += 1
            else:
                break

        result.append(line)
        i += 1

    text = "\n".join(result)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' ([,:;.!?])', r'\1', text)
    return text.strip()

def processa_fitxer(input_path: str, output_path: str, min_tokens: int = 50):
    docs_ok = 0
    docs_descartats = 0

    with open(input_path, encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in fin:
            doc = json.loads(line)
            doc["text"] = neteja_text(doc["text"])
            doc["tokens_approx"] = len(doc["text"].split())

            if doc["tokens_approx"] < min_tokens:
                docs_descartats += 1
                continue

            fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
            docs_ok += 1

    print(f"{input_path}")
    print(f"  Guardats:   {docs_ok}")
    print(f"  Descartats: {docs_descartats}")
    print()


if __name__ == "__main__":
    fitxers = [
        ("corpus/raw/avl_butlleti.jsonl",       "corpus/clean/avl_butlleti.jsonl",       100),
        ("corpus/raw/avl_glossary.jsonl",        "corpus/clean/avl_glossary.jsonl",        100),
        ("corpus/raw/avl_posts.jsonl",           "corpus/clean/avl_posts.jsonl",           200),
        ("corpus/raw/avl_gnv.jsonl",             "corpus/clean/avl_gnv.jsonl",             100),
        ("corpus/raw/avl_gvb.jsonl",             "corpus/clean/avl_gvb.jsonl",              50),
        ("corpus/raw/avl_pages.jsonl",           "corpus/clean/avl_pages.jsonl",           200),
        ("corpus/raw/avl_notes-de-premsa.jsonl", "corpus/clean/avl_notes-de-premsa.jsonl", 100),
        ("corpus/raw/avl_salutacio.jsonl",       "corpus/clean/avl_salutacio.jsonl",        50),
        ("corpus/raw/avl_legislacio.jsonl",      "corpus/clean/avl_legislacio.jsonl",      200),
        ("corpus/raw/avl_escriptors.jsonl",      "corpus/clean/avl_escriptors.jsonl",      100),
        ("corpus/raw/avl_seu.jsonl",             "corpus/clean/avl_seu.jsonl",             100),
        ("corpus/pdf/raw/avl_pdfs.jsonl", "corpus/pdf/clean/avl_pdfs.jsonl", 100),
    ]

    import os
    os.makedirs("corpus/clean", exist_ok=True)

    for inp, out, min_tok in fitxers:
        if os.path.exists(inp):
            processa_fitxer(inp, out, min_tok)
        else:
            print(f"No trobat: {inp}")