"""Proves de la pàgina de traduir (fase 2): estructura accessible, les dues
llengües, la galeta tècnica i el formulari sense JavaScript."""

import re

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from avlizador.web.main import Configuracio, create_app  # noqa: E402
from avlizador.web.missatges import IDIOMES_INTERFICIE, textos  # noqa: E402


def client(**kw):
    return TestClient(create_app(Configuracio(mode="motor", precarrega=False, **kw)))


def test_textos_de_les_dues_llengues_tenen_les_mateixes_claus():
    ca, es = textos("ca-valencia"), textos("es")
    assert sorted(ca) == sorted(es) and sorted(ca["api"]) == sorted(es["api"])


def test_estructura_accessible():
    with client() as c:
        html = c.get("/").text
    assert '<html lang="ca-valencia">' in html
    assert html.count("<h1") == 1
    assert '<a class="saltar" href="#contingut">' in html and 'id="contingut"' in html
    for regio in ("<header", "<nav", "<main", "<footer"):
        assert regio in html
    # Cada camp té la seua etiqueta
    for camp in ("origen", "desti", "text", "traduccio"):
        assert f'<label for="{camp}">' in html and f'id="{camp}"' in html
    assert 'lang="ca"' in html and 'id="traduccio" class="eixida" rows="12" lang="ca-valencia"' in html
    assert 'role="status" aria-live="polite"' in html and 'role="alert"' in html
    assert "tabindex=\"1" not in html and "placeholder" not in html


def test_sense_javascript_en_linia():
    with client() as c:
        html = c.get("/").text
    for etiqueta in re.findall(r"<script[^>]*>", html):
        assert 'src="/static/' in etiqueta or 'type="application/json"' in etiqueta


def test_estatics():
    with client() as c:
        assert c.get("/static/estil.css").status_code == 200
        js = c.get("/static/traductor.js")
    assert js.status_code == 200 and "aria-disabled" in js.text
    # Amb `nosniff`, un .js com a text/plain no s'executa (Windows, 04/11/2026)
    assert js.headers["content-type"].startswith("text/javascript")
    assert c.get("/static/estil.css").headers["content-type"].startswith("text/css")


def test_castella_amb_galeta():
    with client() as c:
        r = c.get("/?idioma=es")
        assert '<html lang="es">' in r.text and "Traducir un texto" in r.text
        assert r.cookies.get("idioma") == "es"
        # La galeta es recorda sense el paràmetre
        assert '<html lang="es">' in c.get("/").text
        assert '<html lang="ca-valencia">' in c.get("/?idioma=ca-valencia").text


def test_selector_de_llengua_marca_la_actual():
    with client() as c:
        html = c.get("/?idioma=es").text
    assert re.search(r'href="\?idioma=es"[^>]*aria-current="true"', html)
    assert 'lang="ca-valencia" hreflang="ca-valencia"' in html


def test_formulari_sense_javascript_traduix():
    with client() as c:
        r = c.post("/", data={"text": "Aquest noi necessita ajuda.", "origen": "ca", "desti": "ca-valencia"})
    assert r.status_code == 200
    assert "Este xic necessita ajuda.</textarea>" in r.text
    assert "Traducció feta." in r.text


def test_formulari_text_buit_marca_el_camp():
    with client() as c:
        html = c.post("/", data={"text": "  "}).text
    assert 'aria-invalid="true"' in html and "Escriu un text per a traduir." in html
    assert 'aria-describedby="ajuda-text comptador error-text"' in html


def test_formulari_massa_llarg_413():
    with client(max_caracters=5) as c:
        r = c.post("/?idioma=es", data={"text": "abcdefgh"})
    assert r.status_code == 413
    assert "El texto es demasiado largo: el máximo es de 5 caracteres y tiene 8." in r.text


def test_el_text_s_escapa():
    with client() as c:
        html = c.post("/", data={"text": "<script>alert(1)</script>"}).text
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


@pytest.mark.parametrize("idioma", IDIOMES_INTERFICIE)
def test_comptador_amb_milers(idioma):
    with client() as c:
        html = c.get(f"/?idioma={idioma}").text
    assert "0 de 20.000 car" in html


# --- Fase 3: Grau Dialectal i "Sobre" ----------------------------------------

def test_menu_amb_les_tres_pantalles():
    with client() as c:
        html = c.get("/gd").text
    assert 'href="/gd" aria-current="page"' in html
    assert 'href="/"' in html and 'href="/sobre"' in html


def test_gd_calcula_i_marca_sense_dependre_del_color():
    with client() as c:
        html = c.post("/gd", data={"text": "El xiquet jugava amb el nen. El nen del veí."}).text
    assert 'id="resultat"' in html and 'tabindex="-1"' in html
    # GD = 1 occidental / 3 marcades; GDV i GDC amb coma decimal
    assert ">0,3333<" in html
    assert 'class="mk-occ paraula-valenciana">xiquet<span class="visualment-amagat"> (valencià)</span>' in html
    assert 'class="mk-or paraula-catalana">nen<span class="visualment-amagat"> (català)</span>' in html
    assert "subratllat continu" in html and "subratllat de punts" in html
    assert "Paraules catalanes (2)" in html and "(2 vegades)" in html


def test_gd_en_castella():
    with client() as c:
        html = c.post("/gd?idioma=es", data={"text": "El xiquet i el nen."}).text
    assert '<span class="visualment-amagat"> (valenciano)</span>' in html
    assert "Grado Dialectal Valenciano (GDV)" in html


def test_gd_sense_paraules_marcades():
    with client() as c:
        html = c.post("/gd", data={"text": "La casa és gran."}).text
    assert "No es pot calcular: el text no té cap paraula marcada." in html
    assert "Cap." in html


def test_gd_errors_del_camp():
    with client(max_caracters=5) as c:
        buit = c.post("/gd", data={"text": " "})
        llarg = c.post("/gd", data={"text": "abcdefgh"})
    assert 'aria-invalid="true"' in buit.text and "Escriu un text per a analitzar." in buit.text
    assert llarg.status_code == 413 and "el màxim és de 5 caràcters" in llarg.text


def test_gd_escapa_el_text():
    with client() as c:
        html = c.post("/gd", data={"text": "<b>nen</b>"}).text
    assert "<b>nen" not in html and "&lt;b&gt;" in html


@pytest.mark.parametrize("idioma,titol", [("ca-valencia", "Límits coneguts"), ("es", "Límites conocidos")])
def test_sobre(idioma, titol):
    with client() as c:
        html = c.get(f"/sobre?idioma={idioma}").text
    assert titol in html and "NOTICE" in html and "1.1.0" in html
    assert html.count("<h1") == 1 and 'href="/sobre" aria-current="page"' in html
