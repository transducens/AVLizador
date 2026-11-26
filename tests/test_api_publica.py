"""El contracte de l'API pública (26/11/2026): el que poden usar els que
instal·len el paquet, com la interfície web. Si una d'estes proves falla
perquè s'ha llevat o reanomenat alguna cosa, cal una versió major."""

import ast
from pathlib import Path

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


def test_la_web_nomes_usa_l_api_publica():
    """La interfície web s'ha d'endur a un altre repositori: només pot
    importar d'avlizador el que és públic."""
    publics = {m.__name__: set(m.__all__) for m in API}
    web = Path(avlizador.__file__).parent / "web"
    for fitxer in web.glob("*.py"):
        for node in ast.walk(ast.parse(fitxer.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom):
                continue
            assert node.level == 0 or node.module in ("idiomes", "missatges", "main"), (
                f"{fitxer.name}: import relatiu a l'exterior de la web ({'.' * node.level}{node.module})")
            if node.module and node.module.split(".")[0] == "avlizador":
                assert node.module in publics, f"{fitxer.name}: {node.module} no és un mòdul públic"
                for alies in node.names:
                    assert alies.name in publics[node.module], f"{fitxer.name}: {node.module}.{alies.name}"
