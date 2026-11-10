"""Proves de l'API web (`avlizador.web`), en mode motor perquè siguen
ràpides. Inclouen les dues proves fixes dels requisits de `main.py`: els
textos no apareixen en els logs (tampoc quan la traducció falla) i, amb el
semàfor ple, la petició següent rep un 429."""

import logging
import threading

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from avlizador.grau_dialectal import calcula_gdc, calcula_gdv  # noqa: E402
from avlizador.web.idiomes import Parell, parells_per_defecte  # noqa: E402
from avlizador.web.main import Configuracio, create_app  # noqa: E402

MARCA = "Frase-secreta-XYZ123 aquest noi"


def client(**kw):
    config = Configuracio(mode="motor", **{"precarrega": False, **kw})
    return TestClient(create_app(config))


def client_amb(tradueix, **kw):
    """Un client amb una funció de traduir de prova en el parell ca -> ca-valencia."""
    base = parells_per_defecte("motor")[("ca", "ca-valencia")]
    parell = Parell(base.origen, base.desti, base.nom_origen, base.nom_desti, tradueix, "dialecte")
    config = Configuracio(mode="motor", precarrega=False, **kw)
    return TestClient(create_app(config, {("ca", "ca-valencia"): parell}))


def test_parells_en_les_dues_llengues():
    esperat = [{"origen": "ca", "desti": "ca-valencia", "nom_origen": "Català", "nom_desti": "Valencià",
                "tipus": "dialecte"}]
    with client() as c:
        assert c.get("/api/parells").json() == esperat
        # El nom de la 1.2.0 es manté
        assert c.get("/api/idiomes").json() == esperat
        es = c.get("/api/parells", headers={"Accept-Language": "es-ES"}).json()
        assert es[0]["nom_origen"] == "Catalán" and es[0]["nom_desti"] == "Valenciano"


def test_parells_per_tipus():
    with client() as c:
        assert [p["desti"] for p in c.get("/api/parells?tipus=dialecte").json()] == ["ca-valencia"]
        # Català -> valencià és un dialecte, no un parell d'idiomes
        assert c.get("/api/parells?tipus=idioma").json() == []
        assert c.get("/api/parells?tipus=altre").status_code == 422


def test_tipus_de_parell_valid():
    with pytest.raises(ValueError):
        Parell("a", "b", {"ca-valencia": "A"}, {"ca-valencia": "B"}, str, "llengua")


def test_tradueix_nomes_torna_la_traduccio():
    with client() as c:
        r = c.post("/api/tradueix", json={"text": "Aquest noi necessita ajuda."})
    assert r.status_code == 200
    assert r.json() == {"traduccio": "Este xic necessita ajuda."}


def test_tradueix_conserva_les_linies():
    with client() as c:
        r = c.post("/api/tradueix", json={"text": "Aquest noi.\n\nAquesta noia."})
    assert r.json()["traduccio"] == "Este xic.\n\nEsta xica."


def test_parell_desconegut_400():
    with client() as c:
        r = c.post("/api/tradueix", json={"text": "Hola", "origen": "ca-valencia", "desti": "ca"})
    assert r.status_code == 400
    assert r.json() == {"error": "Este parell no està disponible."}


def test_text_massa_llarg_413_en_castella():
    with client(max_caracters=10) as c:
        r = c.post("/api/tradueix?idioma=es", json={"text": "x" * 11})
    assert r.status_code == 413
    assert r.json()["error"].startswith("El texto es demasiado largo")


def test_peticio_no_valida_no_repetix_el_text():
    with client() as c:
        r = c.post("/api/tradueix", json={"text": MARCA, "origen": 5})
    assert r.status_code == 422
    assert MARCA not in r.text


def test_cos_que_no_es_json_400_amb_el_nostre_missatge():
    with client() as c:
        r = c.post("/api/tradueix", content=b"{no es json", headers={"Content-Type": "application/json"})
        assert r.status_code in (400, 422)
        assert r.json() == {"error": "La petició no és vàlida. Comprova el text i el parell triat."}
        assert c.get("/no-existix").json() == {"error": "Not Found"}


def test_gd_coincidix_amb_gdv_i_gdc():
    text = "El xiquet jugava amb el nen del veí."
    with client() as c:
        r = c.post("/api/gd", json={"text": text}).json()
    assert r["gdv"] == calcula_gdv(text)["gdv"]
    assert r["gdc"] == calcula_gdc(text)["gdc"]
    assert r["marcadors_occidentals"] == ["xiquet"] and r["marcadors_orientals"] == ["nen"]


def test_salut_i_versio():
    with client(precarrega=True) as c:
        assert c.get("/api/salut").json() == {"estat": "ok", "models_carregats": True, "mode": "motor"}
        v = c.get("/api/versio").json()
    assert v["avlizador"] and v["model_llengua"] is None


def test_capcaleres_de_seguretat_i_sense_docs():
    with client() as c:
        r = c.get("/api/salut")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert c.get("/docs").status_code == 404


def test_el_text_no_apareix_en_els_logs(caplog):
    caplog.set_level(logging.DEBUG)
    with client() as c:
        assert c.post("/api/tradueix", json={"text": MARCA}).status_code == 200
        assert c.post("/api/gd", json={"text": MARCA}).status_code == 200
    assert "XYZ123" not in caplog.text


def test_el_text_no_apareix_en_els_logs_quan_falla(caplog):
    def falla(text):
        raise ValueError(f"no puc amb {text}")

    caplog.set_level(logging.DEBUG)
    with client_amb(falla) as c:
        r = c.post("/api/tradueix", json={"text": MARCA})
    assert r.status_code == 500
    assert r.json() == {"error": "No s'ha pogut processar el text. Torna-ho a intentar."}
    assert "XYZ123" not in caplog.text
    assert "ValueError" in caplog.text and f"{len(MARCA)} caràcters" in caplog.text


def test_semafor_ple_429_sense_esperar():
    dins, solta = threading.Event(), threading.Event()

    def lenta(text):
        dins.set()
        solta.wait(10)
        return text

    with client_amb(lenta, max_simultanies=1) as c:
        primera = {}
        fil = threading.Thread(target=lambda: primera.update(
            r=c.post("/api/tradueix", json={"text": "u"})))
        fil.start()
        assert dins.wait(10)
        r = c.post("/api/tradueix", json={"text": "dos"})
        solta.set()
        fil.join(10)
    assert r.status_code == 429
    assert r.json() == {"error": "El servei està ocupat. Torna-ho a intentar en uns segons."}
    assert primera["r"].status_code == 200
