"""
avl_crawler.py — Crawler per a seccions específiques de la AVL
---------------------------------------------------------------
US:
    python avl_crawler.py --section escriptors
    python avl_crawler.py --section salutacio

SORTIDA:
    corpus/raw/avl_<section>.jsonl
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
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

# ─── Configuració ─────────────────────────────────────────────────────────────

BASE = "https://www.avl.gva.es"

HEADERS = {
    "User-Agent": "CorpusValencia-Research/1.0 (nmm144@alu.ua.es)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ca-ES,ca;q=0.9",
}

DELAY_MIN = 4
DELAY_MAX = 8
OUTPUT_DIR = "corpus/raw"

SECCIONS = {
    # Pàgina única — extreu directament
    "salutacio": {
        "mode":      "pagina-unica",
        "seeds":     ["https://www.avl.gva.es/salutacio-institucional/"],
        "doc_type":  "presentacio",
        "min_tokens": 50,
    },
    # Escriptors — articles a /escriptors-de-lany/
    "escriptors": {
        "mode":      "crawl",
        "seeds":     ["https://www.avl.gva.es/escriptors/"],
        "article_pat": r"avl\.gva\.es/escriptors-de-lany/[^/]+/?$",
        "doc_type":  "biografia",
        "min_tokens": 100,
    },
}

# ─── Funcions base ────────────────────────────────────────────────────────────

def wait():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"  ... esperant {delay:.1f}s")
    time.sleep(delay)


def safe_get(url: str, reintents: int = 3) -> requests.Response | None:
    for intent in range(reintents):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
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
            print(f"  [404] {url}")
            return None
        if r.status_code != 200:
            print(f"  [ERROR {r.status_code}] {url}")
            return None

        r.encoding = "utf-8"
        return r

    print(f"  [FALLAT] {reintents} intents sense èxit.")
    return None


def extreu_text(html: str, url: str) -> str:
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_precision=False,  # False = menys estricte, agafa més text
    )
    if not text:
        return ""
    lines = [" ".join(l.split()) for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def extreu_titol(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for sel in ["h1.entry-title", "h1.page-title", "h1", "title"]:
        el = soup.select_one(sel)
        if el:
            return el.get_text().strip()
    return ""


def extreu_data(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    time_el = soup.find("time")
    if time_el:
        return time_el.get("datetime") or time_el.get_text().strip()
    meta = soup.find("meta", {"property": "article:published_time"})
    if meta:
        return meta.get("content")
    return None


def crea_document(url: str, titol: str, text: str,
                  doc_type: str, data_pub) -> dict:
    return {
        "id":             hashlib.md5(url.encode()).hexdigest()[:12],
        "title":          titol,
        "text":           text,
        "source_url":     url,
        "source_name":    "AVL",
        "doc_type":       doc_type,
        "dialect":        None,
        "date_scraped":   datetime.now(timezone.utc).isoformat(),
        "date_published": data_pub,
        "language":       "val",
        "tokens_approx":  len(text.split()),
    }


def extreu_links(html: str, base_url: str, article_pat: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    pat  = re.compile(article_pat)
    links = []
    for a in soup.find_all("a", href=True):
        href  = urljoin(base_url, a["href"])
        clean = urlparse(href)
        url   = f"{clean.scheme}://{clean.netloc}{clean.path}"
        if pat.search(url) and url not in links:
            links.append(url)
    return links


# ─── Modes de crawling ────────────────────────────────────────────────────────

def mode_pagina_unica(nom: str, config: dict) -> list[dict]:
    """Extreu el text directament de les URLs seed sense seguir links."""
    docs = []
    min_tok = config.get("min_tokens", 100)

    for url in config["seeds"]:
        print(f"Extraient: {url}")
        r = safe_get(url)
        if not r:
            wait()
            continue

        text  = extreu_text(r.text, url)
        titol = extreu_titol(r.text)
        data  = extreu_data(r.text)
        tokens = len(text.split())

        if tokens < min_tok:
            print(f"  → Descartat ({tokens} tokens < {min_tok})")
        else:
            docs.append(crea_document(url, titol, text, config["doc_type"], data))
            print(f"  → '{titol[:60]}' ({tokens} tokens)")

        wait()

    return docs


def mode_crawl(nom: str, config: dict) -> list[dict]:
    """Segueix links des de les seeds i extreu cada article."""
    docs      = []
    visitades = set()
    min_tok   = config.get("min_tokens", 100)

    # 1. Recull URLs d'articles des de les seeds
    article_urls = []
    for seed in config["seeds"]:
        print(f"Explorant seed: {seed}")
        r = safe_get(seed)
        if not r:
            wait()
            continue
        links = extreu_links(r.text, seed, config["article_pat"])
        article_urls.extend(links)
        print(f"  → {len(links)} articles trobats")
        wait()

    article_urls = list(dict.fromkeys(article_urls))
    print(f"\nTotal URLs a visitar: {len(article_urls)}")

    if not article_urls:
        print("  Cap URL trobada. Comprova el patró article_pat.")
        return docs

    # 2. Visita cada article
    for i, url in enumerate(article_urls, 1):
        if url in visitades:
            continue
        visitades.add(url)

        print(f"[{i}/{len(article_urls)}] {url}")
        r = safe_get(url)
        if not r:
            wait()
            continue

        text  = extreu_text(r.text, url)
        titol = extreu_titol(r.text)
        data  = extreu_data(r.text)
        tokens = len(text.split())

        if tokens < min_tok:
            print(f"  → Descartat ({tokens} tokens)")
        else:
            docs.append(crea_document(url, titol, text, config["doc_type"], data))
            print(f"  → '{titol[:55]}' ({tokens} tokens)")

        wait()

    return docs


def crawl_seccio(nom: str, config: dict) -> list[dict]:
    print(f"\n{'='*60}")
    print(f"SECCIÓ: {nom}")
    print(f"{'='*60}")

    mode = config.get("mode", "crawl")
    if mode == "pagina-unica":
        return mode_pagina_unica(nom, config)
    else:
        return mode_crawl(nom, config)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Crawler de seccions específiques de la AVL"
    )
    parser.add_argument(
        "--section",
        choices=list(SECCIONS.keys()) + ["all"],
        required=True,
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.section == "all":
        seccions_a_crawlejar = list(SECCIONS.items())
    else:
        seccions_a_crawlejar = [(args.section, SECCIONS[args.section])]

    resum = []

    for nom, config in seccions_a_crawlejar:
        docs = crawl_seccio(nom, config)

        if not docs:
            print(f"\n  Cap document extret per a '{nom}'")
            continue

        out_path = os.path.join(OUTPUT_DIR, f"avl_{nom}.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

        total_tokens = sum(d["tokens_approx"] for d in docs)
        print(f"\n=== RESUM {nom} ===")
        print(f"Documents: {len(docs)}")
        print(f"Tokens:    {total_tokens:,}")
        print(f"Fitxer:    {out_path}")
        resum.append({"seccio": nom, "docs": len(docs), "tokens": total_tokens})

        if args.section == "all" and nom != seccions_a_crawlejar[-1][0]:
            print("\nPausa de 60s entre seccions...")
            time.sleep(60)

    if len(resum) > 1:
        print(f"\n{'='*60}\nRESUM GLOBAL\n{'='*60}")
        for r in resum:
            print(f"  {r['seccio']:<20} {r['docs']:>5} docs  {r['tokens']:>8,} tokens")
        print(f"  {'TOTAL':<20} {sum(r['docs'] for r in resum):>5} docs  "
              f"{sum(r['tokens'] for r in resum):>8,} tokens")


if __name__ == "__main__":
    main()