"""
gnv_extractor.py — Extractor de la Gramàtica Normativa Valenciana (GNV)
------------------------------------------------------------------------
Usa Playwright per renderitzar la pàgina com un navegador real.
El servidor JSP detecta si és un bot i retorna contingut reduït —
Playwright evita això simulant un navegador complet.

INSTAL·LACIÓ:
    pip install playwright
    playwright install chromium

US:
    python gnv_extractor.py

SORTIDA:
    corpus/raw/avl_gnv.jsonl       — un document per capítol
    corpus/raw/avl_gnv_full.jsonl  — un sol document amb tot el text
"""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ─── Configuració ─────────────────────────────────────────────────────────────

URL = "https://www.avl.gva.es/gnv/buscador.jsp?gramatica=GNV&index=GNV"
OUTPUT_DIR = "corpus/raw"

# ─── Descàrrega amb Playwright ────────────────────────────────────────────────

async def descarrega_amb_playwright() -> str:
    """
    Obre la pàgina amb un navegador real (Chromium headless),
    espera que el JS carregui tot el contingut, i retorna el HTML complet.
    """
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

        # Espera que els elements de contingut estiguin al DOM
        print("Esperant que carregui el contingut...")
        try:
            await page.wait_for_selector("p.text", timeout=10000)
        except Exception:
            print("  AVÍS: timeout esperant p.text — continuant igualment")

        # Espera addicional per assegurar que tot el JS ha acabat
        await page.wait_for_timeout(2000)

        # Comprova quants elements hi ha
        n_text = await page.eval_on_selector_all("p.text", "els => els.length")
        n_capitol = await page.eval_on_selector_all("p.capitol", "els => els.length")
        print(f"  → p.text trobats: {n_text}")
        print(f"  → p.capitol trobats: {n_capitol}")

        # Extreu el HTML complet del DOM renderitzat
        html = await page.content()
        print(f"  → HTML renderitzat: {len(html):,} caràcters")

        await browser.close()
        return html


# ─── Extracció ────────────────────────────────────────────────────────────────

def neteja_text(element) -> str:
    """Extreu text net d'un element BeautifulSoup."""
    for tag in element.find_all(["em", "strong", "b", "i", "a", "span"]):
        tag.replace_with(" " + tag.get_text() + " ")
    text = element.get_text(separator="\n")
    lines = [" ".join(l.split()) for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def extreu_capitols(html: str) -> list[dict]:
    """
    Extreu els capítols de la GNV des del HTML renderitzat.
    Agrupa el contingut per p.capitol i acumula els p.text.
    """
    soup = BeautifulSoup(html, "lxml")

    classes_interes = ["bloc", "capitol", "apartat", "subapartat", "text", "exemple"]
    elements = soup.find_all(
        "p",
        class_=lambda c: c and any(ci in c for ci in classes_interes)
    )

    print(f"\nElements trobats al DOM renderitzat: {len(elements)}")

    capitols = []
    data_scraped = datetime.now(timezone.utc).isoformat()

    titol_actual = "Introducció"
    text_acumulat = []
    num_capitol = 0

    for elem in elements:
        classes = elem.get("class", [])

        if "capitol" in classes:
            # Guarda el capítol anterior
            if text_acumulat:
                text_complet = "\n\n".join(text_acumulat)
                capitols.append(crea_document(
                    num_capitol, titol_actual, text_complet, data_scraped
                ))
            num_capitol += 1
            titol_actual = neteja_text(elem)
            text_acumulat = []

        elif "bloc" in classes:
            bloc_text = neteja_text(elem)
            if bloc_text:
                if not text_acumulat and num_capitol == 0:
                    titol_actual = bloc_text
                else:
                    text_acumulat.append(f"\n# {bloc_text}")

        elif "apartat" in classes or "subapartat" in classes:
            apartat_text = neteja_text(elem)
            if apartat_text:
                text_acumulat.append(f"\n## {apartat_text}")

        elif "text" in classes:
            paragraf = neteja_text(elem)
            if paragraf and len(paragraf) > 10:
                text_acumulat.append(paragraf)

        elif "exemple" in classes:
            exemple = neteja_text(elem)
            if exemple:
                text_acumulat.append(f"[Ex: {exemple}]")

    # Guarda l'últim capítol
    if text_acumulat:
        text_complet = "\n\n".join(text_acumulat)
        capitols.append(crea_document(
            num_capitol, titol_actual, text_complet, data_scraped
        ))

    return capitols


def crea_document(num: int, titol: str, text: str, data_scraped: str) -> dict:
    doc_id = hashlib.md5(f"gnv_{num}_{titol}".encode()).hexdigest()[:12]
    return {
        "id":             doc_id,
        "wp_id":          None,
        "title":          titol,
        "text":           text,
        "source_url":     f"{URL}#capitol_{num}",
        "source_name":    "AVL-GNV",
        "doc_type":       "gramatica_normativa",
        "dialect":        None,
        "date_scraped":   data_scraped,
        "date_published": "2006-01-01T00:00:00",
        "language":       "val",
        "tokens_approx":  len(text.split()),
        "capitol_num":    num,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Descàrrega amb navegador real
    html = await descarrega_amb_playwright()

    # 2. Extracció per capítols
    print("\nExtreient capítols...")
    capitols = extreu_capitols(html)

    if not capitols:
        print("ERROR: No s'han extret capítols. Guardant HTML per revisar.")
        with open("gnv_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    # 3. Estadístiques
    total_tokens = sum(c["tokens_approx"] for c in capitols)
    print(f"\n=== RESUM ===")
    print(f"Capítols extrets:  {len(capitols)}")
    print(f"Tokens totals:     {total_tokens:,}")
    print(f"Mitjana tokens:    {total_tokens // len(capitols) if capitols else 0}")
    print()
    for c in capitols:
        bar = "█" * min(c["tokens_approx"] // 100, 30)
        print(f"  [{c['capitol_num']:2d}] {c['title'][:45]:<45} {c['tokens_approx']:>5}t {bar}")

    # 4. Guarda JSONL per capítols
    out_caps = os.path.join(OUTPUT_DIR, "avl_gnv.jsonl")
    guardats = 0
    with open(out_caps, "w", encoding="utf-8") as f:
        for c in capitols:
            if c["tokens_approx"] >= 30:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                guardats += 1
    print(f"\nFitxer per capítols ({guardats} docs): {out_caps}")

    # 5. Guarda document únic complet
    text_complet = "\n\n".join(c["text"] for c in capitols)
    doc_complet = crea_document(
        0, "Gramàtica Normativa Valenciana (completa)",
        text_complet, datetime.now(timezone.utc).isoformat()
    )
    out_complet = os.path.join(OUTPUT_DIR, "avl_gnv_full.jsonl")
    with open(out_complet, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc_complet, ensure_ascii=False) + "\n")
    print(f"Fitxer complet:        {out_complet}")

    # 6. Mostra del primer capítol
    if capitols:
        print(f"\n--- Mostra del capítol 1 ---")
        print(f"Títol: {capitols[0]['title']}")
        print(f"Text:\n{capitols[0]['text'][:400]}")


if __name__ == "__main__":
    asyncio.run(main())