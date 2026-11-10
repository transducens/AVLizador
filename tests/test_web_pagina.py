"""Proves de les pàgines web: l'adaptador (fase 2), el GD i "Sobre" (fase 3)
i l'estructura "Traductor Transducens" (fase 7: portada, idiomes,
dialectes i redireccions de la 1.2.0)."""

import re

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from avlizador.web.idiomes import Parell, parells_per_defecte  # noqa: E402
from avlizador.web.main import Configuracio, create_app  # noqa: E402
from avlizador.web.missatges import IDIOMES_INTERFICIE, textos  # noqa: E402


def client(**kw):
    return TestClient(create_app(Configuracio(mode="motor", precarrega=False, **kw)))


def test_textos_de_les_dues_llengues_tenen_les_mateixes_claus():
    ca, es = textos("ca-valencia"), textos("es")
    assert sorted(ca) == sorted(es) and sorted(ca["api"]) == sorted(es["api"])


def test_estructura_accessible():
    with client() as c:
        html = c.get("/dialectes/adaptador").text
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
        html = c.get("/dialectes/adaptador").text
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
        r = c.get("/dialectes/adaptador?idioma=es")
        assert '<html lang="es">' in r.text and "Adaptador dialectal del catalán al valenciano" in r.text
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
        r = c.post("/dialectes/adaptador", data={"text": "Aquest noi necessita ajuda.", "origen": "ca", "desti": "ca-valencia"})
    assert r.status_code == 200
    assert "Este xic necessita ajuda.</textarea>" in r.text
    assert "Adaptació feta." in r.text


def test_formulari_text_buit_marca_el_camp():
    with client() as c:
        html = c.post("/dialectes/adaptador", data={"text": "  "}).text
    assert 'aria-invalid="true"' in html and "Escriu un text per a adaptar." in html
    assert 'aria-describedby="ajuda-text comptador error-text"' in html


def test_formulari_massa_llarg_413():
    with client(max_caracters=5) as c:
        r = c.post("/dialectes/adaptador?idioma=es", data={"text": "abcdefgh", "origen": "ca", "desti": "ca-valencia"})
    assert r.status_code == 413
    assert "El texto es demasiado largo: el máximo es de 5 caracteres y tiene 8." in r.text


def test_el_text_s_escapa():
    with client() as c:
        html = c.post("/dialectes/adaptador", data={"text": "<script>alert(1)</script>", "origen": "ca", "desti": "ca-valencia"}).text
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


@pytest.mark.parametrize("idioma", IDIOMES_INTERFICIE)
def test_comptador_amb_milers(idioma):
    with client() as c:
        html = c.get(f"/dialectes/adaptador?idioma={idioma}").text
    assert "0 de 20.000 car" in html


# --- Fase 3: Grau Dialectal i "Sobre" ----------------------------------------

def test_menu_de_dos_nivells():
    with client() as c:
        html = c.get("/dialectes/gd").text
    # Secció activa en el menú principal i pàgina activa en la segona fila
    assert 'href="/dialectes/adaptador" aria-current="true"' in html
    assert 'href="/dialectes/gd" aria-current="page"' in html
    assert '<nav class="subnav" aria-label="Seccions de l&#39;adaptador dialectal">' in html
    assert 'href="/idiomes"' in html and 'href="/sobre"' in html and 'href="/"' in html


def test_gd_calcula_i_marca_sense_dependre_del_color():
    with client() as c:
        html = c.post("/dialectes/gd", data={"text": "El xiquet jugava amb el nen. El nen del veí."}).text
    assert 'id="resultat"' in html and 'tabindex="-1"' in html
    # GD = 1 occidental / 3 marcades; GDV i GDC amb coma decimal
    assert ">0,3333<" in html
    assert 'class="mk-occ paraula-valenciana">xiquet<span class="visualment-amagat"> (valencià)</span>' in html
    assert 'class="mk-or paraula-catalana">nen<span class="visualment-amagat"> (català)</span>' in html
    assert "subratllat continu" in html and "subratllat de punts" in html
    assert "Paraules catalanes (2)" in html and "(2 vegades)" in html


def test_gd_en_castella():
    with client() as c:
        html = c.post("/dialectes/gd?idioma=es", data={"text": "El xiquet i el nen."}).text
    assert '<span class="visualment-amagat"> (valenciano)</span>' in html
    assert "Grado Dialectal Valenciano (GDV)" in html


def test_gd_sense_paraules_marcades():
    with client() as c:
        html = c.post("/dialectes/gd", data={"text": "La casa és gran."}).text
    assert "No es pot calcular: el text no té cap paraula marcada." in html
    assert "Cap." in html


def test_gd_errors_del_camp():
    with client(max_caracters=5) as c:
        buit = c.post("/dialectes/gd", data={"text": " "})
        llarg = c.post("/dialectes/gd", data={"text": "abcdefgh"})
    assert 'aria-invalid="true"' in buit.text and "Escriu un text per a analitzar." in buit.text
    assert llarg.status_code == 413 and "el màxim és de 5 caràcters" in llarg.text


def test_gd_escapa_el_text():
    with client() as c:
        html = c.post("/dialectes/gd", data={"text": "<b>nen</b>"}).text
    assert "<b>nen" not in html and "&lt;b&gt;" in html


@pytest.mark.parametrize("idioma,titol", [("ca-valencia", "Límits coneguts"), ("es", "Límites conocidos")])
def test_sobre(idioma, titol):
    with client() as c:
        html = c.get(f"/sobre?idioma={idioma}").text
    assert titol in html and "NOTICE" in html and "1.2.0" in html
    assert html.count("<h1") == 1 and 'href="/sobre" aria-current="page"' in html


# --- Fase 7: Traductor Transducens -------------------------------------------

def client_amb_idioma():
    """Un client amb, a més, un parell d'idiomes de prova (es -> ca-valencia)."""
    parells = dict(parells_per_defecte("motor"))
    parells[("es", "ca-valencia")] = Parell("es", "ca-valencia", {"ca-valencia": "Castellà", "es": "Castellano"},
                                            {"ca-valencia": "Valencià", "es": "Valenciano"}, str.upper)
    return TestClient(create_app(Configuracio(mode="motor", precarrega=False), parells))


def sense_entitats(html):
    return html.replace("&#39;", "'")


def test_titol_transducens_i_portada():
    with client() as c:
        html = sense_entitats(c.get("/").text)
    assert "<title>Traductor Transducens</title>" in html and "AVLizador</span>" not in html
    assert html.count("<h1") == 1 and 'class="marca" href="/" aria-current="page"' in html
    # Dos targetes: idiomes (encara cap) i dialectes, amb l'adaptador i el GD
    assert 'href="/idiomes">Traducció d\'idiomes</a></h2>' in html
    assert 'href="/dialectes/adaptador">Adaptador dialectal</a></h2>' in html
    assert "Encara no hi ha cap traductor d'idiomes disponible." in html
    assert "són la mateixa llengua" in html
    assert 'class="subnav"' not in html


def test_idiomes_sense_parells_avisa():
    with client() as c:
        html = sense_entitats(c.get("/idiomes").text)
        assert c.post("/idiomes", data={"text": "Hola"}).status_code == 400
    assert 'href="/idiomes" aria-current="page"' in html and "<form" not in html
    assert "Quan n'hi haja, apareixerà en esta pàgina." in html
    assert 'href="/dialectes/adaptador">Adaptador del català al valencià</a>' in html


def test_idiomes_amb_un_parell_mostra_el_traductor():
    with client_amb_idioma() as c:
        html = sense_entitats(c.get("/idiomes").text)
        r = c.post("/idiomes", data={"text": "hola", "origen": "es", "desti": "ca-valencia"})
        # Un parell de dialecte no es traduïx en la pàgina d'idiomes, ni al revés
        creuat = c.post("/idiomes", data={"text": "Aquest noi.", "origen": "ca", "desti": "ca-valencia"})
        adaptador = c.get("/dialectes/adaptador").text
        portada = sense_entitats(c.get("/").text)
    assert "Parells d'idiomes disponibles: 1." in portada
    assert '<label for="origen">Idioma d\'origen</label>' in html and ">Castellà</option>" in html
    assert ">Català</option>" not in html and 'action="/idiomes?idioma=ca-valencia"' in html
    assert "HOLA</textarea>" in r.text and "Traducció feta." in r.text
    assert creuat.status_code == 400 and "Este parell no està disponible." in creuat.text
    assert ">Castellà</option>" not in adaptador


def test_adaptador_parla_de_varietats_no_d_idiomes():
    with client() as c:
        for idioma, origen, prohibit in (("ca-valencia", "Varietat d'origen", "Idioma d'origen"),
                                          ("es", "Variedad de origen", "Idioma de origen")):
            html = sense_entitats(c.get(f"/dialectes/adaptador?idioma={idioma}").text)
            assert f'<label for="origen">{origen}</label>' in html
            assert prohibit not in html
    assert 'action="/dialectes/adaptador?idioma=es"' in html


def test_dialectes_porta_a_l_adaptador():
    with client() as c:
        r = c.get("/dialectes?idioma=es", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/dialectes/adaptador?idioma=es"


def test_rutes_de_la_1_2_0_redirigixen():
    with client() as c:
        gd = c.get("/gd?idioma=es", follow_redirects=False)
        assert gd.status_code == 301 and gd.headers["location"] == "/dialectes/gd?idioma=es"
        post_gd = c.post("/gd", data={"text": "x"}, follow_redirects=False)
        assert post_gd.status_code == 308 and post_gd.headers["location"] == "/dialectes/gd"
        post = c.post("/", data={"text": "x"}, follow_redirects=False)
        assert post.status_code == 308 and post.headers["location"] == "/dialectes/adaptador"
        # Seguint la redirecció, el formulari antic encara traduïx
        r = c.post("/", data={"text": "Aquest noi.", "origen": "ca", "desti": "ca-valencia"})
    assert r.status_code == 200 and "Este xic.</textarea>" in r.text
