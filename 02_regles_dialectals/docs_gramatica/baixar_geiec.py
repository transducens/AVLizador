#!/usr/bin/env python3
"""
Scraper GEIEC v4 — Playwright (executa JavaScript)
https://geiec.iec.cat

El contingut es carrega via JavaScript, per tant usem Playwright
per renderitzar la pàgina completament abans d'extreure el text.

Instal·lació (una sola vegada):
    pip install playwright
    playwright install chromium

Ús:
    python3 baixar_geiec.py
"""

import time, random, re, logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ─────────────────────────────────────────────
# CONFIGURACIÓ
# ─────────────────────────────────────────────

OUTPUT_DIR        = "geiec_txt"
CONSOLIDATED_FILE = "geiec_complet.txt"
LOG_FILE          = "geiec_scraper.log"

WAIT_MIN       = 3.0
WAIT_MAX       = 7.0
PAUSE_EVERY_N  = 20
PAUSE_LONG_MIN = 25.0
PAUSE_LONG_MAX = 45.0
PAGE_TIMEOUT   = 15000   # ms per esperar que carregui la pàgina

BASE_URL = "https://geiec.iec.cat"

# ─────────────────────────────────────────────
# ÍNDEX REAL DEL GEIEC
# ─────────────────────────────────────────────

SECCIONS = [
    # CAP 1 — Les vocals i la síl·laba
    "1.1", "1.2", "1.2.1", "1.2.2",
    "1.3", "1.3.1", "1.3.2", "1.3.3",
    "1.4", "1.4.1", "1.4.2", "1.4.3",
    "1.5",
    # CAP 2 — Les consonants
    "2.1", "2.2", "2.2.1", "2.2.2", "2.2.3", "2.2.4",
    "2.3", "2.3.1", "2.3.2", "2.3.3", "2.3.4",
    "2.4", "2.4.1", "2.4.2",
    "2.5",
    # CAP 3 — L'accent i l'entonació
    "3.1", "3.2", "3.2.1", "3.2.2", "3.2.3",
    "3.3", "3.3.1", "3.3.2",
    "3.4",
    # CAP 4 — L'ortografia
    "4.1", "4.2", "4.3", "4.4", "4.5",
    "4.6", "4.6.1", "4.6.2",
    "4.7", "4.8",
    # CAP 5 — La formació de mots
    "5.1", "5.2", "5.2.1", "5.2.2", "5.2.3",
    "5.3", "5.3.1", "5.3.2", "5.3.3",
    "5.4", "5.4.1", "5.4.2",
    "5.5",
    # CAP 6 — El nom
    "6.1", "6.2", "6.2.1", "6.2.2",
    "6.3", "6.3.1", "6.3.2",
    "6.4", "6.5",
    # CAP 7 — El gènere
    "7.1", "7.2", "7.3", "7.4", "7.5",
    # CAP 8 — El nombre
    "8.1", "8.2", "8.3", "8.4",
    # CAP 9 — L'adjectiu
    "9.1", "9.2", "9.3", "9.4", "9.5",
    # CAP 10 — Els determinants
    "10.1", "10.2", "10.3", "10.4", "10.5", "10.6",
    # CAP 11 — Els quantificadors
    "11.1", "11.2", "11.3", "11.4", "11.5",
    # CAP 12 — Els pronoms personals
    "12.1", "12.2", "12.3", "12.4",
    # CAP 13 — Els pronoms relatius, interrogatius i exclamatius
    "13.1", "13.2", "13.3", "13.4",
    # CAP 14 — Les preposicions àtones i les compostes
    "14.1", "14.2", "14.3", "14.4",
    "14.4.1", "14.4.2", "14.4.3", "14.4.4",
    "14.5",
    # CAP 15 — Les preposicions tòniques
    "15.1", "15.2", "15.3", "15.4", "15.5",
    # CAP 16 — Els pronoms febles
    "16.1", "16.2", "16.3", "16.4", "16.5",
    # CAP 17 — L'adverbi
    "17.1", "17.2", "17.3", "17.4",
    # CAP 18 — Les conjuncions
    "18.1", "18.2", "18.3", "18.4",
    # CAP 19 — El verb: formes no personals
    "19.1", "19.2", "19.3",
    "19.3.1", "19.3.2", "19.3.3", "19.3.4", "19.3.5",
    "19.3.5.1", "19.3.5.2", "19.3.5.3", "19.3.5.4", "19.3.5.5",
    # CAP 20 — El verb: formes personals
    "20.1", "20.2", "20.3", "20.4", "20.5",
    # CAP 21 — La flexió verbal
    "21.1", "21.2", "21.3", "21.4",
    # CAP 22 — Les perífrasis verbals
    "22.1", "22.2", "22.3", "22.4",
    # CAP 23 — El sintagma nominal
    "23.1", "23.2", "23.3", "23.4",
    # CAP 24 — El sintagma verbal
    "24.1", "24.2", "24.3",
    # CAP 25 — El sintagma adjectival i l'adverbial
    "25.1", "25.2",
    # CAP 26 — El sintagma preposicional
    "26.1", "26.2",
    # CAP 27 — Les oracions de relatiu
    "27.1", "27.2", "27.3", "27.4",
    "27.4.1", "27.4.2", "27.4.3", "27.4.4",
    "27.5", "27.6", "27.6.1", "27.6.2",
    # CAP 28 — Les oracions completives
    "28.1", "28.2", "28.3",
    # CAP 29 — Les oracions adverbials
    "29.1", "29.2", "29.3", "29.4",
    # CAP 30 — La modalitat oracional
    "30.1", "30.2", "30.3", "30.4",
    # CAP 31 — La negació
    "31.1", "31.2", "31.3",
    # CAP 32 — La veu passiva i les construccions impersonals
    "32.1", "32.2", "32.3",
    # CAP 33 — La concordança
    "33.1", "33.2", "33.3",
    # CAP 34 — L'ordre dels constituents
    "34.1", "34.2", "34.3",
    # CAP 35 — La cohesió textual
    "35.1", "35.2", "35.3",
]

# ─────────────────────────────────────────────
# LOG
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def esperar(min_s=WAIT_MIN, max_s=WAIT_MAX, motiu=""):
    t = random.uniform(min_s, max_s)
    log.info(f"  ⏳ Esperant {t:.1f}s" + (f" ({motiu})" if motiu else "") + "...")
    time.sleep(t)

def extract_text(page):
    """Extreu el text net un cop la pàgina ha carregat el JS."""
    # Espera que aparegui contingut real (un paràgraf o capçalera dins del main)
    try:
        page.wait_for_selector("main p, article p, .text p, p", timeout=PAGE_TIMEOUT)
    except PWTimeout:
        pass

    # Elimina elements de navegació via JS
    page.evaluate("""
        document.querySelectorAll(
            'nav, header, footer, script, style, noscript, ' +
            '[class*="nav"], [class*="menu"], [class*="footer"], ' +
            '[class*="header"], button, [aria-hidden="true"]'
        ).forEach(el => el.remove());
    """)

    # Extreu el text del contingut principal
    content = page.evaluate("""
        () => {
            const main = document.querySelector('main')
                      || document.querySelector('article')
                      || document.querySelector('.text')
                      || document.querySelector('#contingut')
                      || document.body;
            if (!main) return '';

            let lines = [];
            const seen = new Set();

            main.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,tr,blockquote').forEach(el => {
                const tag = el.tagName.toLowerCase();
                const t   = el.innerText.trim().replace(/\\s+/g, ' ');
                if (!t || seen.has(t)) return;
                seen.add(t);

                if (/^h[1-6]$/.test(tag)) {
                    const lvl = '#'.repeat(parseInt(tag[1]));
                    lines.push('\\n' + lvl + ' ' + t + '\\n');
                } else if (tag === 'p' || tag === 'blockquote') {
                    lines.push(t + '\\n');
                } else if (tag === 'li') {
                    lines.push('- ' + t);
                } else if (tag === 'tr') {
                    const cells = Array.from(el.querySelectorAll('td,th'))
                                       .map(c => c.innerText.trim())
                                       .filter(c => c);
                    if (cells.length) lines.push(cells.join(' | '));
                }
            });
            return lines.join('\\n');
        }
    """)

    # Neteja
    content = re.sub(r"\n{3,}", "\n\n", content or "")
    return content.strip()

def extract_title(page, codi):
    try:
        el = page.query_selector("h1, h2, .titol")
        if el:
            t = el.inner_text().strip()
            if t and len(t) < 200:
                return t
    except Exception:
        pass
    return codi

def has_real_content(page):
    try:
        text = page.evaluate("() => document.body.innerText")
        return len(text.strip()) > 300
    except Exception:
        return False

def already_done(output_dir, codi):
    f = Path(output_dir) / f"{codi}.txt"
    return f.exists() and f.stat().st_size > 100

def save_section(output_dir, codi, titol, url, text):
    fname = Path(output_dir) / f"{codi}.txt"
    with open(fname, "w", encoding="utf-8") as fh:
        fh.write(f"SECCIÓ: {codi}\n")
        fh.write(f"TÍTOL:  {titol}\n")
        fh.write(f"URL:    {url}\n")
        fh.write(f"DATA:   {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        fh.write("=" * 60 + "\n\n")
        fh.write(text)

def sort_key(codi):
    return [int(x) for x in codi.split(".")]

def consolidate(output_dir, out_file):
    log.info(f"\n📦 Consolidant en {out_file}...")
    files = sorted(Path(output_dir).glob("*.txt"), key=lambda p: sort_key(p.stem))
    with open(out_file, "w", encoding="utf-8") as out:
        out.write("GRAMÀTICA ESSENCIAL DE LA LLENGUA CATALANA (GEIEC)\n")
        out.write("Institut d'Estudis Catalans — https://geiec.iec.cat\n")
        out.write(f"Descarregada el {datetime.now().strftime('%Y-%m-%d')}\n")
        out.write("=" * 70 + "\n\n")
        for f in files:
            out.write(f.read_text(encoding="utf-8"))
            out.write("\n\n" + "─" * 60 + "\n\n")
    kb = Path(out_file).stat().st_size // 1024
    log.info(f"  ✅ {out_file} — {len(files)} seccions, {kb} KB")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  GEIEC Scraper v4 — Playwright")
    log.info("=" * 60)

    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    total = len(SECCIONS)
    downloaded, skipped, empty, errors = 0, 0, [], []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ca-ES",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # Visita primer la pàgina d'inici per establir cookies/sessió
        log.info("🌐 Iniciant sessió al GEIEC...")
        page.goto(f"{BASE_URL}/inici", wait_until="domcontentloaded", timeout=20000)
        esperar(2, 4, "inici")

        log.info(f"📋 {total} seccions a descarregar\n")

        for i, codi in enumerate(SECCIONS, 1):

            if already_done(OUTPUT_DIR, codi):
                log.info(f"[{i:3d}/{total}] ⏭️  Ja existeix: {codi}")
                skipped += 1
                continue

            url = f"{BASE_URL}/text/{codi}"
            log.info(f"[{i:3d}/{total}] 📥 {codi}  →  {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Espera addicional per al JS
                page.wait_for_timeout(1500)
            except PWTimeout:
                log.error(f"  ❌ Timeout carregant {codi}")
                errors.append(codi)
                esperar(WAIT_MIN, WAIT_MAX)
                continue
            except Exception as e:
                log.error(f"  ❌ Error: {e}")
                errors.append(codi)
                esperar(WAIT_MIN, WAIT_MAX)
                continue

            if not has_real_content(page):
                log.warning(f"  ⚠️  Pàgina sense contingut: {codi}")
                empty.append(codi)
                esperar(WAIT_MIN, WAIT_MAX)
                continue

            titol = extract_title(page, codi)
            text  = extract_text(page)
            save_section(OUTPUT_DIR, codi, titol, url, text)
            log.info(f"  ✅ {len(text)} chars — «{titol[:55]}»")
            downloaded += 1

            if downloaded % PAUSE_EVERY_N == 0:
                esperar(PAUSE_LONG_MIN, PAUSE_LONG_MAX, f"pausa llarga ({downloaded} descarregades)")
            else:
                esperar(WAIT_MIN, WAIT_MAX)

        browser.close()

    # Resum
    log.info("\n" + "=" * 60)
    log.info(f"  Descarregades:  {downloaded}")
    log.info(f"  Ja existien:    {skipped}")
    log.info(f"  Sense contingut:{len(empty)}  {empty if empty else ''}")
    log.info(f"  Errors:         {len(errors)}  {errors if errors else ''}")
    log.info("=" * 60)

    if downloaded + skipped > 0:
        consolidate(OUTPUT_DIR, CONSOLIDATED_FILE)

    log.info(f"\n✅ Fet! Carpeta: {OUTPUT_DIR}/  |  Fitxer: {CONSOLIDATED_FILE}")

if __name__ == "__main__":
    main()