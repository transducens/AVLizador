"""Comprovació d'accessibilitat de la pàgina de traduir (fase 2 de
`documentacio/hoja_de_ruta_interfaz_docker.md`): axe-core (WCAG 2.0-2.2
A/AA + bones pràctiques) en valencià i castellà, mode clar i fosc;
recorregut amb teclat, focus visible, anuncis, botó "Copiar", 320 px
d'amplària sense desplaçament horitzontal i el formulari sense JavaScript.
NO substituïx la prova manual amb lector de pantalla (NVDA/VoiceOver).

Necessita Playwright amb Chrome i axe-core (fora del repo):

    pip install playwright
    npm pack axe-core@4.10.2 && tar -xzf axe-core-4.10.2.tgz   # en una carpeta a part
    AVLIZADOR_MODE=motor avlizador web --port 8766 &
    python scripts/comprova_accessibilitat.py http://127.0.0.1:8766 package/axe.min.js captures/

Ix amb 1 si hi ha cap problema. Les captures queden en la carpeta indicada.
El navegador s'obri amb `bypass_csp` només per a poder injectar axe (la
pàgina no permet JavaScript en línia).
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL, AXE, OUT = sys.argv[1], Path(sys.argv[2]).read_text(encoding="utf-8"), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]
problemes = 0


def axe(page, nom):
    global problemes
    page.add_script_tag(content=AXE)
    r = page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
    v = r["violations"]
    print(f"[{nom}] axe: {len(v)} infraccions, {len(r['passes'])} regles superades, "
          f"{len(r['incomplete'])} per revisar a mà")
    for x in v:
        problemes += 1
        print(f"   ✗ {x['id']} ({x['impact']}): {x['help']}")
        for n in x["nodes"][:3]:
            print("       ", n["target"], n.get("failureSummary", "").replace("\n", " | ")[:200])
    for x in r["incomplete"]:
        print(f"   ? {x['id']}: {x['help']} ({len(x['nodes'])} elements)")


def comprova(condicio, missatge):
    global problemes
    print(("   ✓ " if condicio else "   ✗ ") + missatge)
    problemes += 0 if condicio else 1


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome")
    for esquema in ("light", "dark"):
        for idioma in ("ca-valencia", "es"):
            ctx = nav.new_context(bypass_csp=True, color_scheme=esquema, viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto(f"{URL}/?idioma={idioma}")
            axe(page, f"{idioma}, {esquema}")
            page.screenshot(path=str(OUT / f"inici_{idioma}_{esquema}.png"), full_page=True)
            ctx.close()

    # Recorregut amb teclat i traducció amb JavaScript
    ctx = nav.new_context(bypass_csp=True, viewport={"width": 1280, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(URL + "/?idioma=ca-valencia")
    ordre = []
    for _ in range(12):
        page.keyboard.press("Tab")
        ordre.append(page.evaluate("() => { const e = document.activeElement; "
                                   "return e.id || e.textContent.trim().slice(0, 20) || e.tagName; }"))
    print("Ordre de tabulació:", ordre)
    comprova(ordre[0] == "Salta al contingut", "el primer enfocable és «Salta al contingut»")
    comprova(ordre.index("origen") < ordre.index("desti") < ordre.index("text") < ordre.index("boto-traduir")
             < ordre.index("traduccio") < ordre.index("copiar"), "ordre lògic dels camps")
    estil_focus = page.evaluate("() => { document.getElementById('text').focus(); "
                                "const s = getComputedStyle(document.getElementById('text')); "
                                "return [s.outlineStyle, s.outlineWidth]; }")
    comprova(estil_focus[0] != "none" and float(estil_focus[1].rstrip("px")) >= 2, f"focus visible {estil_focus}")
    page.fill("#text", "Aquest noi necessita ajuda.\nLa seva feina és important.")
    comprova("55 de 20.000" in page.inner_text("#comptador"), "comptador: " + page.inner_text("#comptador"))
    page.focus("#boto-traduir")
    page.keyboard.press("Enter")
    page.wait_for_function("() => document.getElementById('traduccio').value.length > 0", timeout=60000)
    page.wait_for_timeout(200)
    comprova(page.input_value("#traduccio") == "Este xic necessita ajuda.\nLa seua faena és important.",
             "traducció: " + repr(page.input_value("#traduccio")))
    comprova(page.inner_text("#estat") == "Traducció feta.", "anunci: " + page.inner_text("#estat"))
    comprova(page.evaluate("() => document.activeElement.id") == "boto-traduir", "el focus no salta")
    page.click("#copiar")
    page.wait_for_timeout(200)
    comprova(page.inner_text("#estat") == "Traducció copiada.", "copiar: " + page.inner_text("#estat"))
    comprova(page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n") == page.input_value("#traduccio"),
             "el porta-retalls té la traducció")
    axe(page, "després de traduir")
    page.fill("#text", "")
    page.click("#boto-traduir")
    comprova(page.get_attribute("#text", "aria-invalid") == "true" and page.is_visible("#error-text"),
             "text buit: error junt al camp")
    page.screenshot(path=str(OUT / "error_buit.png"), full_page=True)
    ctx.close()

    # Grau Dialectal i "Sobre" (fase 3)
    TEXT_GD = "El xiquet jugava amb el nen del veí. Hui els xiquets han eixit prompte."
    for esquema in ("light", "dark"):
        for idioma in ("ca-valencia", "es"):
            ctx = nav.new_context(bypass_csp=True, color_scheme=esquema, viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto(f"{URL}/gd?idioma={idioma}")
            axe(page, f"GD buida, {idioma}, {esquema}")
            page.fill("#text", TEXT_GD)
            page.click("button[type=submit]")
            page.wait_for_selector("#resultat")
            axe(page, f"GD amb resultat, {idioma}, {esquema}")
            page.screenshot(path=str(OUT / f"gd_{idioma}_{esquema}.png"), full_page=True)
            page.goto(f"{URL}/sobre?idioma={idioma}")
            axe(page, f"Sobre, {idioma}, {esquema}")
            ctx.close()
    ctx = nav.new_context(bypass_csp=True)
    page = ctx.new_page()
    page.goto(URL + "/gd?idioma=ca-valencia")
    page.fill("#text", TEXT_GD)
    page.click("button[type=submit]")
    page.wait_for_selector("#resultat")
    comprova(page.evaluate("() => document.activeElement.id") == "resultat"
             or page.evaluate("() => location.hash") == "#resultat", "després de calcular es va al resultat")
    estils = page.evaluate("""() => ['.text-marcat .paraula-valenciana', '.text-marcat .paraula-catalana'].map(
        s => { const e = document.querySelector(s); const c = getComputedStyle(e);
               return [c.textDecorationLine, c.textDecorationStyle, e.textContent]; })""")
    comprova(estils[0][:2] == ["underline", "solid"] and estils[1][:2] == ["underline", "dotted"],
             f"sense color també es distingixen: {estils}")
    comprova(estils[0][2].endswith("(valencià)") and estils[1][2].endswith("(català)"),
             "text ocult per al lector de pantalla")
    page.emulate_media(forced_colors="active")
    page.screenshot(path=str(OUT / "gd_alt_contrast.png"), full_page=True)
    ctx.close()

    # 320 px d'amplària (equivalent al 400 % de zoom en 1280 px): sense desplaçament horitzontal
    for amplaria in (320, 640):
        for ruta in ("/", "/gd", "/sobre"):
            ctx = nav.new_context(bypass_csp=True, viewport={"width": amplaria, "height": 800})
            page = ctx.new_page()
            page.goto(URL + ruta)
            if ruta == "/gd":
                page.fill("#text", TEXT_GD)
                page.click("button[type=submit]")
                page.wait_for_selector("#resultat")
            sw = page.evaluate("() => document.documentElement.scrollWidth")
            comprova(sw <= amplaria, f"{ruta} a {amplaria} px: scrollWidth {sw}")
            nom = ruta.strip("/") or "inici"
            page.screenshot(path=str(OUT / f"estreta_{nom}_{amplaria}.png"), full_page=True)
            ctx.close()

    # Sense JavaScript: el formulari funciona igualment
    ctx = nav.new_context(bypass_csp=True, java_script_enabled=False)
    page = ctx.new_page()
    page.goto(URL + "/")
    comprova(not page.is_visible("#copiar"), "sense JS, el botó «Copiar» no es mostra")
    page.fill("#text", "Aquest noi necessita ajuda.")
    page.click("#boto-traduir")
    page.wait_for_load_state()
    comprova(page.input_value("#traduccio").strip() == "Este xic necessita ajuda.",
             "sense JS: " + repr(page.input_value("#traduccio")))
    ctx.close()
    nav.close()

print(f"\nTOTAL problemes: {problemes}")
sys.exit(1 if problemes else 0)
