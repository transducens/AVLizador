"""Proves de l'API pública i de l'ordre `avlizador`."""

import json
import warnings

import pytest

import avlizador
from avlizador import cli
from avlizador.traductor_cat_val import translate_invers


def test_versio():
    assert avlizador.__version__ == "1.0.0"


def test_api_traductor():
    assert avlizador.translate_cat_val_motor("Aquest noi té vuitanta anys.") == "Este xic té huitanta anys."


def test_api_grau_dialectal():
    assert avlizador.calcula_gd("Este xiquet vol vindre hui.")["gd"] == 1.0
    assert avlizador.calcula_gdv("Este xiquet vol vindre hui.")["gdv"] == 1.0
    assert avlizador.calcula_gdc("Aquest nen vol venir avui.")["gdc"] == 1.0


def test_sense_model_llengua_usa_el_motor_i_avisa(monkeypatch):
    monkeypatch.setattr(translate_invers, "model_llengua_disponible", lambda: False)
    monkeypatch.setattr(translate_invers, "_AVISAT", False)
    with pytest.warns(translate_invers.AvisSenseModelLlengua):
        eixida = translate_invers.translate_cat_val("Un cop acabada la reunió, marxem.")
    assert eixida == translate_invers.translate_cat_val_motor("Un cop acabada la reunió, marxem.")
    with warnings.catch_warnings():  # només avisa una vegada
        warnings.simplefilter("error")
        translate_invers.translate_cat_val("Aquest noi.")


def test_cli_tradueix_motor(capsys):
    assert cli.main(["tradueix", "--motor", "Aquest", "noi", "té", "vuitanta", "anys."]) == 0
    assert capsys.readouterr().out.strip() == "Este xic té huitanta anys."


def test_cli_gd(capsys):
    assert cli.main(["gd", "--text", "Este xiquet vol vindre hui."]) == 0
    assert "1" in capsys.readouterr().out


def test_cli_avalua(tmp_path, capsys):
    bench = tmp_path / "b.json"
    bench.write_text(json.dumps([{"id": "x", "oriental": "Aquest noi.", "occidental": "Este xic."}]),
                     encoding="utf-8")
    pytest.importorskip("sacrebleu")
    from avlizador.avaluacio import avalua

    monkey_sistemes = avalua.sistemes
    try:
        avalua.sistemes = lambda amb_motor: [("motor", "Motor solo", avlizador.translate_cat_val_motor)]
        assert cli.main(["avalua", "--fitxer", str(bench), "--eixida", str(tmp_path / "r")]) == 0
    finally:
        avalua.sistemes = monkey_sistemes
    assert "| 1/1 (100,0 %) |" in capsys.readouterr().out


def test_cli_ajuda(capsys):
    assert cli.main([]) == 0
    assert "tradueix" in capsys.readouterr().out


def test_cli_subordre_desconeguda():
    assert cli.main(["res"]) == 2
