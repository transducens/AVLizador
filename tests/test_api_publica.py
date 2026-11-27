"""El contracte de l'API pública (26/11/2026): el que poden usar els que
instal·len el paquet, com la interfície web
(https://github.com/transducens/traductor-transducens-web, que en fa servir
`translate_cat_val`, `translate_cat_val_motor`, `calcula_gd`,
`resalta_html`, `info_model`, `kenlm_disponible` i `__version__`). Si una
d'estes proves falla perquè s'ha llevat o reanomenat alguna cosa, cal una
versió major."""

import pytest

import avlizador
from avlizador import grau_dialectal, traductor_cat_val

API = {
    avlizador: ["__version__", "translate_cat_val", "translate_cat_val_motor", "calcula_gd", "calcula_gdv",
                "calcula_gdc", "resalta_html", "info_model", "descarrega_model", "comprova_model",
                "kenlm_disponible"],
    traductor_cat_val: ["translate_cat_val", "translate_cat_val_motor", "AvisSenseModelLlengua", "info_model",
                        "descarrega_model", "comprova_model", "ErrorModel", "kenlm_disponible"],
    grau_dialectal: ["calcula_gd", "calcula_gdv", "calcula_gdv_corpus", "calcula_gdc", "calcula_gdc_corpus",
                     "resalta_html"],
}


@pytest.mark.parametrize("modul", API, ids=lambda m: m.__name__)
def test_api_publica(modul):
    for nom in API[modul]:
        assert nom in modul.__all__, f"{modul.__name__}.{nom} no és en __all__"
        assert getattr(modul, nom) is not None


def test_el_mateix_objecte_des_de_la_dalt_i_des_del_subpaquet():
    assert avlizador.info_model is traductor_cat_val.info_model
    assert avlizador.resalta_html is grau_dialectal.resalta_html


def test_claus_que_llig_la_web():
    """La web llig estes claus dels resultats: també són part del contracte."""
    r = avlizador.calcula_gd("Este xiquet vol vindre hui.")
    for clau in ("gd", "total_paraules", "total_occidentals", "total_orientals", "total_marcades",
                 "marcadors_occidentals", "marcadors_orientals"):
        assert clau in r, clau
    assert "nom" in avlizador.info_model()
    assert "<" in avlizador.resalta_html("Este xiquet", etiquetes=("val", "cat"))
