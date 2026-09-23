"""
gvb_extractor.py — Extractor de la Gramàtica Normativa Valenciana (GVB)
------------------------------------------------------------------------
Usa Playwright per renderitzar la pàgina com un navegador real.

Estructura de classes CSS del DOM renderitzat:
  p.capitol       (42)  — seccions grans: ORTOLOGIA, MORFOLOGIA...
  p.subapartat   (423)  — capítols numerats: 1. La pronunciació...  ← divisió principal
  p.apartat      (323)  — subseccions: 1.1. Introducció...
  p.subsubapartat  (5)  — sub-subseccions
  p.text        (1836)  — text narratiu principal
  p.text_exemple(1979)  — exemples
  p.text_llista   (43)  — llistes
  p.bloc          (10)  — títols de bloc gran: PRESENTACIÓ, INTRODUCCIÓ

INSTAL·LACIÓ:
    pip install playwright beautifulsoup4 lxml
    playwright install chromium

US:
    python gvb_extractor.py

SORTIDA:
    corpus/raw/avl_gvb.jsonl       — un document per subapartat (capítol)
    corpus/raw/avl_gvb_full.jsonl  — un sol document amb tot el text
"""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ─── Configuració ─────────────────────────────────────────────────────────────

URL = "https://www.avl.gva.es/gnv/buscador.jsp?gramatica=GVB&index=GVB_GNV"
# Ancorat a __file__ (no al directori de treball): este fitxer viu a
# 01_scraping_y_limpieza/, i "corpus/" és a l'arrel del repositori.
OUTPUT_DIR = str(Path(__file__).resolve().parent.parent / "corpus" / "raw")

# Classes que contenen text de contingut real
CLASSES_CONTINGUT = {"text", "text_exemple", "text_llista"}

# Classes que actuen com a títols / separadors estructurals
CLASSES_TITOL = {"capitol", "subapartat", "apartat", "subsubapartat", "bloc"}

# ─── Descàrrega amb Playwright ────────────────────────────────────────────────

async def descarrega_amb_playwright() -> str:
    async with async_playwright() as p:
        print("Iniciant navegador Chromium...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ca-ES",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print(f"Carregant: {URL}")
        await page.goto(URL, wait_until="networkidle", timeout=30000)

        print("Esperant contingut...")
        try:
            await page.wait_for_selector("p.text", timeout=10000)
        except Exception:
            print("  AVÍS: timeout — continuant igualment")

        await page.wait_for_timeout(2000)

        n_text      = await page.eval_on_selector_all("p.text",       "els => els.length")
        n_subapt    = await page.eval_on_selector_all("p.subapartat", "els => els.length")
        n_capitol   = await page.eval_on_selector_all("p.capitol",    "els => els.length")
        n_exemple   = await page.eval_on_selector_all("p.text_exemple", "els => els.length")
        print(f"  → p.text:        {n_text}")
        print(f"  → p.text_exemple:{n_exemple}")
        print(f"  → p.subapartat:  {n_subapt}")
        print(f"  → p.capitol:     {n_capitol}")

        html = await page.content()
        print(f"  → HTML renderitzat: {len(html):,} caràcters")
        await browser.close()
        return html


# ─── Extracció ────────────────────────────────────────────────────────────────

def neteja_text(element) -> str:
    """Extreu text net d'un element BeautifulSoup."""
    for tag in element.find_all(["em", "strong", "b", "i", "a", "span"]):
        tag.replace_with(" " + tag.get_text() + " ")
    text = element.get_text(separator=" ")
    return " ".join(text.split()).strip()


def extreu_capitols(html: str) -> list[dict]:
    """
    Estratègia d'extracció:
    - p.capitol     → marca una secció gran (ORTOLOGIA, MORFOLOGIA...).
                      S'afegeix com a context però NO divideix el corpus.
    - p.subapartat  → DIVISIÓ PRINCIPAL. Cada subapartat = 1 document del corpus.
    - p.apartat     → subsecció dins del subapartat. S'inclou com a header al text.
    - p.text /
      p.text_exemple /
      p.text_llista → contingut real que s'acumula al document actual.
    """
    soup = BeautifulSoup(html, "lxml")

    totes_classes = CLASSES_CONTINGUT | CLASSES_TITOL
    elements = soup.find_all(
        "p",
        class_=lambda c: c and any(ci in (c if isinstance(c, list) else [c])
                                   for ci in totes_classes)
    )

    print(f"\nElements processats: {len(elements)}")

    capitols      = []
    data_scraped  = datetime.now(timezone.utc).isoformat()

    seccio_actual   = ""   # p.capitol actual (ORTOLOGIA, MORFOLOGIA...)
    titol_actual    = ""   # p.subapartat actual (1. La pronunciació...)
    text_acumulat   = []
    num_subapartat  = 0

    def desa_capitol_actual():
        nonlocal num_subapartat
        if titol_actual and text_acumulat:
            text = "\n\n".join(text_acumulat)
            capitols.append(crea_document(
                num    = num_subapartat,
                titol  = titol_actual,
                seccio = seccio_actual,
                text   = text,
                data   = data_scraped,
            ))

    for elem in elements:
        classes = elem.get("class", [])
        if isinstance(classes, str):
            classes = [classes]

        if "capitol" in classes:
            # Nova secció gran — actualitza el context però no divideix
            seccio_actual = neteja_text(elem)

        elif "subapartat" in classes:
            # NOVA DIVISIÓ — desa l'anterior i inicia nou document
            desa_capitol_actual()
            num_subapartat += 1
            titol_actual  = neteja_text(elem)
            text_acumulat = []

        elif "apartat" in classes or "subsubapartat" in classes:
            # Subsecció — l'afegim com a header dins del text
            apartat = neteja_text(elem)
            if apartat:
                text_acumulat.append(f"## {apartat}")

        elif any(c in classes for c in CLASSES_CONTINGUT):
            # Text real — acumula
            paragraf = neteja_text(elem)
            if paragraf and len(paragraf) > 5:
                # Marca els exemples per distingir-los del text narratiu
                if "text_exemple" in classes:
                    text_acumulat.append(f"[Ex: {paragraf}]")
                else:
                    text_acumulat.append(paragraf)

    # Desa l'últim subapartat
    desa_capitol_actual()

    return capitols


def crea_document(num: int, titol: str, seccio: str,
                  text: str, data: str) -> dict:
    doc_id = hashlib.md5(f"gvb_{num}_{titol}".encode()).hexdigest()[:12]
    return {
        "id":             doc_id,
        "wp_id":          None,
        "title":          titol,
        "seccio":         seccio,   # ORTOLOGIA / MORFOLOGIA / SINTAXI...
        "text":           text,
        "source_url":     f"{URL}#subapartat_{num}",
        "source_name":    "AVL-GVB",
        "doc_type":       "gramatica_normativa",
        "dialect":        None,
        "date_scraped":   data,
        "date_published": "2006-01-01T00:00:00",
        "language":       "val",
        "tokens_approx":  len(text.split()),
        "capitol_num":    num,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Descàrrega
    html = await descarrega_amb_playwright()

    # 2. Extracció
    print("\nExtreient subapartats...")
    capitols = extreu_capitols(html)

    if not capitols:
        print("ERROR: cap capítol extret. Guardant HTML per revisar.")
        with open("gvb_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    # 3. Estadístiques
    total_tokens = sum(c["tokens_approx"] for c in capitols)
    print(f"\n=== RESUM ===")
    print(f"Subapartats extrets: {len(capitols)}")
    print(f"Tokens totals:       {total_tokens:,}")
    print(f"Mitjana tokens:      {total_tokens // len(capitols) if capitols else 0}")
    print()

    seccio_ant = ""
    for c in capitols:
        if c["seccio"] != seccio_ant:
            print(f"\n  ── {c['seccio']} ──")
            seccio_ant = c["seccio"]
        bar = "█" * min(c["tokens_approx"] // 50, 25)
        print(f"  [{c['capitol_num']:3d}] {c['title'][:50]:<50} {c['tokens_approx']:>5}t {bar}")

    # 4. Guarda JSONL per subapartats
    out_caps = os.path.join(OUTPUT_DIR, "avl_gvb.jsonl")
    guardats = 0
    with open(out_caps, "w", encoding="utf-8") as f:
        for c in capitols:
            if c["tokens_approx"] >= 20:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                guardats += 1
    print(f"\nFitxer per subapartats ({guardats} docs): {out_caps}")

    # 5. Guarda document únic complet
    text_complet = "\n\n".join(c["text"] for c in capitols)
    doc_complet  = crea_document(
        0, "Gramàtica Normativa Valenciana (completa)", "GVB",
        text_complet, datetime.now(timezone.utc).isoformat()
    )
    out_complet = os.path.join(OUTPUT_DIR, "avl_gvb_full.jsonl")
    with open(out_complet, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc_complet, ensure_ascii=False) + "\n")
    print(f"Fitxer complet:          {out_complet}")

    # 6. Mostra dels primers 3 subapartats
    print(f"\n--- Mostra dels primers 3 subapartats ---")
    for c in capitols[:3]:
        print(f"\nTítol:   {c['title']}")
        print(f"Secció:  {c['seccio']}")
        print(f"Tokens:  {c['tokens_approx']}")
        print(f"Text:    {c['text'][:250]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())