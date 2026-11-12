"""Proves del sistema KenLM (`translate_cat_val(text, model="kenlm")`,
12/11/2026) amb un model fals: en Windows no s'instal·la `kenlm`. Les xifres
reals es comproven en Abaco amb `avlizador avalua --model kenlm`."""

import json

import pytest

from avlizador import cli
from avlizador.traductor_cat_val import translate_cat_val, translate_cat_val_motor
from avlizador.traductor_cat_val import model_llengua as ml
from avlizador.traductor_cat_val.model_llengua import CRITERI_KENLM, Criteri, tradueix_cat_val_ml
from avlizador.traductor_cat_val.model_llengua.kenlm import FaltaKenLM, ModelKenLM, carrega_sistema_kenlm, fitxers_kenlm
from avlizador.traductor_cat_val.model_llengua.sentit import ClassificadorCop, NaiveBayes


class KenLMFals:
    """`score` com `kenlm.Model`: log10. Premia les frases amb `bones`."""

    def __init__(self, bones=(), premi=3.0):
        self.bones, self.premi = bones, premi

    def score(self, frase, bos=True, eos=True):
        return -1.0 * len(frase.split()) + (self.premi if any(b in frase for b in self.bones) else 0.0)


FREQ = {"tokens": 1000, "freq": {"colp": 10, "vegada": 300, "colps": 5, "vegades": 200}}


def nb_cop():
    nb = NaiveBayes(alpha=1.0)
    nb.afig(["W=destral", "W=pegar"], "colp")
    nb.afig(["L1=<NUM>", "W=dir"], "vegada")
    return nb


@pytest.fixture
def sistema(monkeypatch):
    """Injecta un sistema KenLM fals en la memòria cau del paquet."""
    def posa(bones=(), nb=None):
        monkeypatch.setattr(ml, "_SISTEMA_KENLM", (ModelKenLM(KenLMFals(bones), FREQ), ClassificadorCop(nb or nb_cop())))
    yield posa
    ml._SISTEMA_KENLM = None


def test_kenlm_tria_la_frase_mes_probable(sistema):
    sistema(bones=("una vegada",))
    assert translate_cat_val("Un cop acabada la reunió, marxem.", model="kenlm") == \
        "Una vegada acabada la reunió, marxem."


def test_kenlm_sense_punts_es_el_motor(sistema):
    sistema()
    text = "Tinc vuitanta anys i la meva obra és francesa."
    assert translate_cat_val(text, model="kenlm") == translate_cat_val_motor(text)


def test_desempat_amb_el_classificador():
    """KenLM premia "una vegada" en 1,5 (log10) = 3,45 punts; el prior de
    freqüència (λ 0,75) en torna 2,48 a "colp": "vegada" guanya per 0,97 < 2 i
    decidix el classificador, que veu "destral" -> "colp"."""
    model = ModelKenLM(KenLMFals(bones=("una vegada",), premi=1.5), FREQ)
    frase = "Li va pegar un cop amb la destral."
    sense, _ = tradueix_cat_val_ml(frase, model, CRITERI_KENLM)
    amb, punts = tradueix_cat_val_ml(frase, model, CRITERI_KENLM, sentit=ClassificadorCop(nb_cop()))
    (punt,) = [p for p in punts if p.tipus == "colisio"]
    assert punt.sentit == "colp" and punt.decidit == "sentit"
    assert "una vegada" in sense and "un colp" in amb
    # sense `desempat` el classificador no es consulta
    _, punts = tradueix_cat_val_ml(frase, model, Criteri(lam=1.5, lam_colisio=0.75),
                                   sentit=ClassificadorCop(nb_cop()))
    assert all(p.sentit is None for p in punts)


def test_criteri_kenlm():
    assert (CRITERI_KENLM.marge, CRITERI_KENLM.per_defecte, CRITERI_KENLM.lam,
            CRITERI_KENLM.lam_colisio, CRITERI_KENLM.desempat) == (3.0, "catala", 1.5, 0.75, 2.0)


def test_classificador_desat_i_carregat(tmp_path):
    nb_cop().desa(tmp_path / "nb.json", minim=1)
    c = ClassificadorCop.carrega(tmp_path / "nb.json")
    assert c.nb.logodds(["W=destral"]) > 0 > c.nb.logodds(["W=dir"])


def test_falta_directori(monkeypatch):
    monkeypatch.delenv("AVLIZADOR_KENLM_DIR", raising=False)
    with pytest.raises(FaltaKenLM):
        fitxers_kenlm()


def test_falten_fitxers(monkeypatch, tmp_path):
    import importlib.util

    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a: object() if n == "kenlm" else real(n, *a))
    with pytest.raises(FaltaKenLM, match="valencia_net_dogv_o5.binary"):
        carrega_sistema_kenlm(tmp_path)


def test_model_desconegut():
    with pytest.raises(ValueError):
        translate_cat_val("Hola.", model="gpt")


def test_cli_tradueix_kenlm(sistema, capsys):
    sistema(bones=("una vegada",))
    assert cli.main(["tradueix", "--model", "kenlm", "Un cop acabada la reunió, marxem."]) == 0
    assert capsys.readouterr().out.strip() == "Una vegada acabada la reunió, marxem."


def test_cli_tradueix_kenlm_sense_fitxers(monkeypatch, capsys):
    monkeypatch.setattr(ml, "_SISTEMA_KENLM", None)
    monkeypatch.delenv("AVLIZADOR_KENLM_DIR", raising=False)
    assert cli.main(["tradueix", "--model", "kenlm", "Hola."]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_cli_avalua_kenlm(sistema, tmp_path, capsys):
    pytest.importorskip("sacrebleu")
    sistema(bones=("una vegada",))
    bench = tmp_path / "b.json"
    bench.write_text(json.dumps([{"id": "x", "oriental": "Un cop acabada la reunió, marxem.",
                                  "occidental": "Una vegada acabada la reunió, marxem."}]), encoding="utf-8")
    assert cli.main(["avalua", "--model", "kenlm", "--fitxer", str(bench), "--eixida", str(tmp_path / "r")]) == 0
    out = capsys.readouterr().out
    assert "Motor + KenLM + sentit" in out and "| 1/1 (100,0 %) |" in out
    assert (tmp_path / "r").glob("kenlm_b_*.json")
