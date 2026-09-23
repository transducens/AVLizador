"""
pdf_extractor.py — Extractor de PDFs per al corpus de l'AVL
------------------------------------------------------------
Descarrega PDFs directament en memòria, extreu el text amb pymupdf
i guarda el resultat en JSONL. Cap PDF es guarda al disc.

INSTAL·LACIÓ:
    pip install pymupdf requests

US:
    python pdf_extractor.py --source fonts_pdf.txt
    python pdf_extractor.py --url https://exemple.com/doc.pdf

SORTIDA:
    corpus/pdf/raw/avl_pdfs.jsonl

FORMAT fonts_pdf.txt (una URL per línia, # per comentaris):
    # Legislació
    https://www.avl.gva.es/documents/31595/32337/Llei+de+creació
    # Acords normatius
    https://www.avl.gva.es/documents/...
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import pymupdf
import requests

# ─── Configuració ─────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "CorpusValencia-Research/1.0 (nmm144@alu.ua.es)",
    "Accept": "application/pdf,*/*",
}

DELAY_MIN   = 5
DELAY_MAX   = 10
OUTPUT_DIR  = "corpus/pdf/raw"
OUTPUT_FILE = "avl_pdfs.jsonl"
MIN_TOKENS  = 50

# ─── Funcions base ────────────────────────────────────────────────────────────

def wait():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"  ... esperant {delay:.1f}s")
    time.sleep(delay)


def safe_get_pdf(url: str, reintents: int = 3):
    """Descarrega un PDF en memòria. Retorna els bytes o None."""
    for intent in range(reintents):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
        except requests.exceptions.Timeout:
            print(f"  [TIMEOUT] Intent {intent+1}/{reintents}. Esperant 30s...")
            time.sleep(30)
            continue
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] {e}")
            return None

        if r.status_code == 429:
            print("  [RATE LIMIT] Esperant 120s...")
            time.sleep(120)
            continue
        if r.status_code == 403:
            print("  [BLOQUEJAT 403] Para el script i espera 1 hora.")
            sys.exit(1)
        if r.status_code == 404:
            print(f"  [404] PDF no trobat: {url}")
            return None
        if r.status_code != 200:
            print(f"  [ERROR {r.status_code}] {url}")
            return None

        # Verifica que és realment un PDF
        content_type = r.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not r.content[:4] == b"%PDF":
            print(f"  [AVÍS] La resposta no sembla un PDF (Content-Type: {content_type})")

        return r.content

    print(f"  [FALLAT] {reintents} intents sense èxit.")
    return None


# ─── Diagnosi del PDF ─────────────────────────────────────────────────────────

def diagnostica_pdf(doc: pymupdf.Document) -> dict:
    """Analitza el PDF per detectar el tipus i problemes potencials."""
    n_pages = len(doc)
    chars_total = sum(len(page.get_text()) for page in doc)
    chars_per_page = chars_total / n_pages if n_pages else 0

    # Detecta columnes mirant la distribució horitzontal dels blocs
    te_columnes = False
    if n_pages > 0:
        blocks = doc[0].get_text("blocks")
        if blocks:
            mid_x = doc[0].rect.width / 2
            esq = sum(1 for b in blocks if b[0] < mid_x - 50)
            dre = sum(1 for b in blocks if b[0] > mid_x + 50)
            te_columnes = esq > 2 and dre > 2

    return {
        "n_pages":       n_pages,
        "chars_per_page": round(chars_per_page),
        "tipus":         "digital" if chars_per_page > 100 else "escanejat",
        "te_columnes":   te_columnes,
    }


# ─── Extracció de text ────────────────────────────────────────────────────────

def extreu_pagina_simple(page: pymupdf.Page) -> str:
    """Extreu text d'una pàgina sense columnes."""
    text = page.get_text("text")
    return text


def extreu_pagina_columnes(page: pymupdf.Page) -> str:
    """Extreu text d'una pàgina amb dues columnes."""
    blocks = page.get_text("blocks")
    mid_x  = page.rect.width / 2

    col_esq = sorted(
        [b for b in blocks if b[0] < mid_x],
        key=lambda b: b[1]
    )
    col_dre = sorted(
        [b for b in blocks if b[0] >= mid_x],
        key=lambda b: b[1]
    )

    text_esq = " ".join(b[4] for b in col_esq if b[4].strip())
    text_dre = " ".join(b[4] for b in col_dre if b[4].strip())

    return text_esq + "\n" + text_dre if text_dre else text_esq


def neteja_text_pdf(text: str) -> str:
    """Neteja el text extret d'un PDF."""
    # Paraules partides amb guió al final de línia
    text = re.sub(r'-\n(\w)', r'\1', text)
    # Números de pàgina sols en una línia
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Salts de línia múltiples → paràgraf
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Espais múltiples
    text = re.sub(r'[ \t]+', ' ', text)
    # Neteja línies curtes aïllades (capçaleres/peus de pàgina repetits)
    lines = text.splitlines()
    if len(lines) > 10:
        # Elimina línies que es repeteixen més de 3 vegades (capçaleres)
        from collections import Counter
        freq = Counter(l.strip() for l in lines if l.strip())
        repetides = {l for l, c in freq.items() if c > 3 and len(l) < 80}
        lines = [l for l in lines if l.strip() not in repetides]
        text = "\n".join(lines)

    return text.strip()


def extreu_text_pdf(pdf_bytes: bytes, url: str) -> tuple[str, dict]:
    """
    Extreu tot el text d'un PDF en memòria.
    Retorna (text_net, info_diagnosi).
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"  [ERROR pymupdf] No s'ha pogut obrir el PDF: {e}")
        return "", {}

    info = diagnostica_pdf(doc)
    print(f"  → {info['n_pages']} pàgines, "
          f"{info['chars_per_page']} chars/pàg, "
          f"tipus={info['tipus']}, "
          f"columnes={info['te_columnes']}")

    if info["tipus"] == "escanejat":
        print("  [AVÍS] PDF escanejat — OCR no implementat, saltant.")
        doc.close()
        return "", info

    pagines_text = []
    for page in doc:
        if info["te_columnes"]:
            text = extreu_pagina_columnes(page)
        else:
            text = extreu_pagina_simple(page)
        pagines_text.append(text)

    doc.close()

    text_complet = "\n\n".join(pagines_text)
    text_net = neteja_text_pdf(text_complet)
    return text_net, info


# ─── Creació del document JSONL ───────────────────────────────────────────────

def nom_des_url(url: str) -> str:
    """Extreu un nom llegible de la URL del PDF."""
    path = urlparse(url).path
    nom  = path.split("/")[-1]
    nom  = unquote(nom).replace("+", " ")
    return nom or "document"


def crea_document(url: str, text: str, info: dict, doc_type: str) -> dict:
    return {
        "id":             hashlib.md5(url.encode()).hexdigest()[:12],
        "title":          nom_des_url(url),
        "text":           text,
        "source_url":     url,
        "source_name":    "AVL",
        "doc_type":       doc_type,
        "dialect":        None,
        "date_scraped":   datetime.now(timezone.utc).isoformat(),
        "date_published": None,
        "language":       "val",
        "tokens_approx":  len(text.split()),
        "n_pages":        info.get("n_pages", 0),
        "source_format":  "pdf",
    }


# ─── Processament d'una URL ───────────────────────────────────────────────────

def processa_url(url: str, doc_type: str) -> dict | None:
    """Descarrega, extreu i neteja el text d'un PDF. Retorna el document o None."""
    print(f"  Descarregant: {url[:80]}")
    pdf_bytes = safe_get_pdf(url)
    if not pdf_bytes:
        return None

    print(f"  Mida: {len(pdf_bytes)/1024:.0f} KB")
    text, info = extreu_text_pdf(pdf_bytes, url)

    if not text or len(text.split()) < MIN_TOKENS:
        print(f"  → Descartat (massa poc text: {len(text.split())} tokens)")
        return None

    doc = crea_document(url, text, info, doc_type)
    print(f"  → '{doc['title'][:55]}' ({doc['tokens_approx']} tokens, "
          f"{doc['n_pages']} pàg)")
    return doc


# ─── Lectura del fitxer de fonts ─────────────────────────────────────────────

def llegeix_fonts(path: str) -> list[tuple[str, str]]:
    """
    Llegeix el fitxer de fonts PDF.
    Format:
        # Comentari (doc_type per defecte: document-oficial)
        # doc_type: legislacio
        https://url1.com/doc.pdf
        https://url2.com/doc.pdf
        # doc_type: acord-normatiu
        https://url3.com/doc.pdf
    """
    urls = []
    doc_type_actual = "document-oficial"

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                # Detecta canvi de doc_type
                if "doc_type:" in line:
                    doc_type_actual = line.split("doc_type:")[-1].strip()
                continue
            if line.startswith("http"):
                urls.append((line, doc_type_actual))

    return urls


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extractor de PDFs per al corpus de l'AVL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--source",
        help="Fitxer .txt amb una URL de PDF per línia"
    )
    group.add_argument(
        "--url",
        help="URL directa d'un sol PDF (per a proves)"
    )
    parser.add_argument(
        "--doc-type",
        default="document-oficial",
        help="Tipus de document (legislacio, acord-normatiu, etc.)"
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    # Recull les URLs a processar
    if args.url:
        urls = [(args.url, args.doc_type)]
    else:
        if not os.path.exists(args.source):
            print(f"Fitxer no trobat: {args.source}")
            sys.exit(1)
        urls = llegeix_fonts(args.source)

    print(f"\n=== PDF EXTRACTOR ===")
    print(f"URLs a processar: {len(urls)}")
    print(f"Fitxer sortida:   {out_path}\n")

    docs_guardats  = 0
    docs_descartats = 0
    docs_error     = 0

    with open(out_path, "a", encoding="utf-8") as f:
        for i, (url, doc_type) in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {doc_type}")
            doc = processa_url(url, doc_type)

            if doc:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                docs_guardats += 1
            else:
                docs_descartats += 1

            if i < len(urls):
                wait()

    print(f"\n=== FINALITZAT ===")
    print(f"Guardats:   {docs_guardats}")
    print(f"Descartats: {docs_descartats}")
    print(f"Fitxer:     {out_path}")


if __name__ == "__main__":
    main()