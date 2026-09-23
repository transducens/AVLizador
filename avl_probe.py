"""
avl_probe.py — Script de reconeixement i extracció de la API REST de la AVL
----------------------------------------------------------------------------
OBJECTIU: Extreure corpus de text en valenciano de la API de la AVL
          amb el mínim de peticions i sense risc de bloqueig.

US:
    python avl_probe.py --mode volume
    python avl_probe.py --mode sample
    python avl_probe.py --mode inspect EP
    python avl_probe.py --mode fetch EP
    python avl_probe.py --mode fetch-cat CATEGORIA_ID NOM

EXEMPLES:
    python avl_probe.py --mode fetch butlleti
    python avl_probe.py --mode fetch-cat 9 notes-de-premsa

ORDRE RECOMANAT D'EXTRACCIÓ:
    1. butlleti
    2. glossary
    3. posts
    4. pages
    5. notes-de-premsa  → python avl_probe.py --mode fetch-cat 9 notes-de-premsa

NO extreure ara:
    - col_leccio:          contingut buit via API (Elementor/JS)
    - les_nostres_revistes: apunta a PDFs externs
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ─── Configuració ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.avl.gva.es/wp-json/wp/v2"

HEADERS = {
    "User-Agent": "CorpusValencia-Research/1.0 (nmm144@alu.ua.es)",
    "Accept": "application/json",
}

ENDPOINTS = {
    "butlleti": "butlleti",
    "glossary": "glossari",
    "posts":    "post",
    "pages":    "pagina",
}

ENDPOINTS_DESCARTATS = {
    "col_leccio":           "contingut buit via API (Elementor/JS)",
    "les_nostres_revistes": "apunta a PDFs externs",
}

# Categories de WordPress (id → nom)
CATEGORIES = {
    9: "notes-de-premsa",
}

DELAY_MIN = 4
DELAY_MAX = 8

MIN_TOKENS = {
    "butlleti":         100,
    "glossary":         100,
    "posts":            200,
    "pages":            200,
    "notes-de-premsa":  100,
}

OUTPUT_DIR = "corpus/raw"

# ─── Funcions base ────────────────────────────────────────────────────────────

def wait():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"  ... esperant {delay:.1f}s")
    time.sleep(delay)


def safe_get(url: str, params: dict = None, reintents: int = 3) -> requests.Response | None:
    for intent in range(reintents):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        except requests.exceptions.Timeout:
            print(f"  [TIMEOUT] Intent {intent+1}/{reintents}. Esperant 30s...")
            time.sleep(30)
            continue
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR de connexió] {e}")
            return None

        if r.status_code == 429:
            print("  [RATE LIMIT 429] Esperant 120s...")
            time.sleep(120)
            continue
        if r.status_code == 403:
            print("  [BLOQUEJAT 403] Para el script i espera almenys 1 hora.")
            sys.exit(1)
        if r.status_code != 200:
            print(f"  [ERROR {r.status_code}] {url}")
            return None

        return r

    print(f"  [FALLAT] {reintents} intents sense èxit.")
    return None


def extract_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(["a", "em", "strong", "span", "b", "i"]):
        tag.replace_with(" " + tag.get_text() + " ")
    text = soup.get_text(separator="\n")
    lines = [" ".join(l.split()) for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def parse_item(item: dict, doc_type: str) -> dict:
    raw_html   = item.get("content", {}).get("rendered", "")
    text       = extract_text(raw_html)
    title_html = item.get("title", {}).get("rendered", "")
    title      = BeautifulSoup(title_html, "html.parser").get_text().strip()
    return {
        "id":             hashlib.md5(str(item["id"]).encode()).hexdigest()[:12],
        "wp_id":          item["id"],
        "title":          title,
        "text":           text,
        "source_url":     item.get("link", ""),
        "source_name":    "AVL",
        "doc_type":       doc_type,
        "dialect":        None,
        "date_scraped":   datetime.now(timezone.utc).isoformat(),
        "date_published": item.get("date", None),
        "language":       "val",
        "tokens_approx":  len(text.split()),
    }


def fetch_pagines(url: str, params_base: dict, n_pages: int,
                  doc_type: str, min_tok: int, out_path: str):
    """
    Funció compartida per mode_fetch i mode_fetch_cat.
    Descarrega totes les pàgines i guarda el JSONL.
    """
    docs_saved = docs_skipped = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for page in range(1, n_pages + 1):
            if page > 1:
                wait()
                print(f"Pàgina {page}/{n_pages}...")

            r = safe_get(url, params={**params_base, "page": page})
            if not r:
                print(f"  Error a la pàgina {page}. Saltant.")
                continue

            for item in r.json():
                doc = parse_item(item, doc_type)
                if doc["tokens_approx"] < min_tok:
                    docs_skipped += 1
                    continue
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                docs_saved += 1

    print(f"\n=== FINALITZAT ===")
    print(f"Documents guardats:   {docs_saved}")
    print(f"Documents descartats: {docs_skipped} (menys de {min_tok} tokens)")
    print(f"Fitxer:               {out_path}")


# ─── Modes d'execució ─────────────────────────────────────────────────────────

def mode_volume():
    print("\n=== MODE VOLUME: comptant documents per endpoint ===\n")
    results = {}
    endpoint_list = list(ENDPOINTS.keys())

    for i, endpoint in enumerate(endpoint_list):
        url = f"{BASE_URL}/{endpoint}"
        print(f"Consultant: {endpoint}")
        r = safe_get(url, params={"per_page": 100, "page": 1})
        if r:
            total   = r.headers.get("X-WP-Total", "?")
            n_pages = r.headers.get("X-WP-TotalPages", "?")
            results[endpoint] = {"total": total, "pages": n_pages}
            print(f"  → {total} documents, {n_pages} pàgines de 100\n")
        else:
            results[endpoint] = {"total": "ERROR", "pages": "ERROR"}
            print("  → ERROR\n")
        if i < len(endpoint_list) - 1:
            wait()

    # Categories
    print("Consultant categories...")
    for cat_id, cat_nom in CATEGORIES.items():
        r = safe_get(f"{BASE_URL}/posts",
                     params={"per_page": 100, "page": 1, "categories": cat_id})
        if r:
            total   = r.headers.get("X-WP-Total", "?")
            n_pages = r.headers.get("X-WP-TotalPages", "?")
            results[f"cat:{cat_nom}"] = {"total": total, "pages": n_pages}
            print(f"  → categoria '{cat_nom}': {total} docs, {n_pages} pàgines\n")
        wait()

    print("\n=== RESUM ===")
    print(f"{'Endpoint':<28} {'Documents':>10} {'Pàgines':>10} {'Temps est.':>12}")
    print("-" * 64)
    for ep, data in results.items():
        try:
            pages = int(data["pages"])
            mins  = round(pages * ((DELAY_MIN + DELAY_MAX) / 2) / 60, 1)
            temps = f"~{mins} min"
        except (ValueError, TypeError):
            temps = "?"
        print(f"{ep:<28} {data['total']:>10} {data['pages']:>10} {temps:>12}")

    print("\nEndpoints descartats:")
    for ep, motiu in ENDPOINTS_DESCARTATS.items():
        print(f"  {ep}: {motiu}")
    print()


def mode_sample():
    print("\n=== MODE SAMPLE: mostrant 2 docs per endpoint ===\n")
    endpoint_list = list(ENDPOINTS.items())
    for i, (endpoint, doc_type) in enumerate(endpoint_list):
        url = f"{BASE_URL}/{endpoint}"
        print(f"\n{'='*60}\nENDPOINT: {endpoint}\n{'='*60}")
        r = safe_get(url, params={"per_page": 2, "page": 1})
        if not r:
            continue
        total = r.headers.get("X-WP-Total", "?")
        print(f"Total disponibles: {total}\n")
        for item in r.json():
            doc = parse_item(item, doc_type)
            qualitat = "✓ BON" if doc["tokens_approx"] >= MIN_TOKENS.get(endpoint, 100) else "✗ CURT"
            print(f"  Títol:    {doc['title'][:70]}")
            print(f"  Tokens:   {doc['tokens_approx']} {qualitat}")
            print(f"  Text:     {doc['text'][:200]!r}")
            print()
        if i < len(endpoint_list) - 1:
            wait()


def mode_inspect(endpoint: str):
    all_ep = {**ENDPOINTS, **{k: k for k in ENDPOINTS_DESCARTATS}}
    if endpoint not in all_ep:
        print(f"Endpoint desconegut: {endpoint}")
        sys.exit(1)
    print(f"\n=== MODE INSPECT: endpoint={endpoint} ===\n")
    r = safe_get(f"{BASE_URL}/{endpoint}", params={"per_page": 1, "page": 1})
    if not r:
        return
    items = r.json()
    if not items:
        print("Cap document trobat.")
        return
    item = items[0]
    print(f"Total documents: {r.headers.get('X-WP-Total', '?')}\n")
    for key, val in item.items():
        if isinstance(val, dict):
            print(f"  {key}: {{claus: {list(val.keys())}}}")
        elif isinstance(val, str) and len(val) > 120:
            print(f"  {key}: '{val[:120]}...' [{len(val)} chars]")
        else:
            print(f"  {key}: {val!r}")
    print("\nJSON complet (màx 3000 chars):")
    print(json.dumps(item, ensure_ascii=False, indent=2)[:3000])


def mode_fetch(endpoint: str):
    if endpoint not in ENDPOINTS:
        print(f"Endpoint desconegut: {endpoint}")
        print(f"Disponibles: {', '.join(ENDPOINTS.keys())}")
        sys.exit(1)

    doc_type = ENDPOINTS[endpoint]
    min_tok  = MIN_TOKENS.get(endpoint, 100)
    out_path = os.path.join(OUTPUT_DIR, f"avl_{endpoint}.jsonl")
    url      = f"{BASE_URL}/{endpoint}"

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    r = safe_get(url, params={"per_page": 100, "page": 1})
    if not r:
        return

    total   = int(r.headers.get("X-WP-Total", 0))
    n_pages = int(r.headers.get("X-WP-TotalPages", 1))
    secs    = n_pages * ((DELAY_MIN + DELAY_MAX) / 2)

    print(f"\n=== MODE FETCH: {endpoint} → {out_path} ===\n")
    print(f"Documents:         {total}")
    print(f"Pàgines:           {n_pages}")
    print(f"Tokens mínims:     {min_tok}")
    print(f"Temps estimat:     ~{secs/60:.0f} minuts\n")

    if os.path.exists(out_path):
        print(f"AVÍS: {out_path} ja existeix i serà sobreescrit.")

    input("Prem Enter per continuar (Ctrl+C per cancel·lar)...\n")

    fetch_pagines(url, {"per_page": 100}, n_pages, doc_type, min_tok, out_path)


def mode_fetch_cat(cat_id: int, nom: str):
    """
    Extreu tots els posts d'una categoria WordPress per ID.
    Us: python avl_probe.py --mode fetch-cat 9 notes-de-premsa
    """
    doc_type = "nota-de-premsa"
    min_tok  = MIN_TOKENS.get(nom, 100)
    out_path = os.path.join(OUTPUT_DIR, f"avl_{nom}.jsonl")
    url      = f"{BASE_URL}/posts"
    params   = {"per_page": 100, "categories": cat_id}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n=== MODE FETCH-CAT: categoria {cat_id} ({nom}) → {out_path} ===\n")

    r = safe_get(url, params={**params, "page": 1})
    if not r:
        return

    total   = int(r.headers.get("X-WP-Total", 0))
    n_pages = int(r.headers.get("X-WP-TotalPages", 1))
    secs    = n_pages * ((DELAY_MIN + DELAY_MAX) / 2)

    print(f"Documents:     {total}")
    print(f"Pàgines:       {n_pages}")
    print(f"Tokens mínims: {min_tok}")
    print(f"Temps estimat: ~{secs/60:.0f} minuts\n")

    if os.path.exists(out_path):
        print(f"AVÍS: {out_path} ja existeix i serà sobreescrit.")

    input("Prem Enter per continuar (Ctrl+C per cancel·lar)...\n")

    fetch_pagines(url, params, n_pages, doc_type, min_tok, out_path)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extracció de corpus de la API REST de la AVL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  volume      → quants documents per endpoint
  sample      → 2 docs per endpoint per verificar qualitat
  inspect EP  → JSON brut d'un document
  fetch EP    → extreu TOTS els docs d'un endpoint
  fetch-cat ID NOM → extreu tots els posts d'una categoria WordPress

Exemples:
  python avl_probe.py --mode fetch butlleti
  python avl_probe.py --mode fetch-cat 9 notes-de-premsa
        """
    )
    parser.add_argument(
        "--mode",
        choices=["volume", "sample", "inspect", "fetch", "fetch-cat"],
        required=True,
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="endpoint, o ID i NOM per a fetch-cat"
    )
    parsed = parser.parse_args()

    if parsed.mode == "volume":
        mode_volume()

    elif parsed.mode == "sample":
        mode_sample()

    elif parsed.mode == "inspect":
        if not parsed.args:
            print("inspect requereix un endpoint.")
            sys.exit(1)
        mode_inspect(parsed.args[0])

    elif parsed.mode == "fetch":
        if not parsed.args:
            print("fetch requereix un endpoint.")
            sys.exit(1)
        mode_fetch(parsed.args[0])

    elif parsed.mode == "fetch-cat":
        if len(parsed.args) < 2:
            print("fetch-cat requereix ID i NOM.")
            print("Exemple: python avl_probe.py --mode fetch-cat 9 notes-de-premsa")
            sys.exit(1)
        try:
            cat_id = int(parsed.args[0])
        except ValueError:
            print(f"L'ID ha de ser un número enter. Rebut: '{parsed.args[0]}'")
            sys.exit(1)
        mode_fetch_cat(cat_id, parsed.args[1])


if __name__ == "__main__":
    main()