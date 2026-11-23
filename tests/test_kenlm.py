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
from avlizador.traductor_cat_val.model_llengua import kenlm

# La funció real (conftest.py la substituïx en tots els tests).
_DIRECTORI_HF = kenlm._directori_hf


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


def test_kenlm_es_el_model_per_defecte(sistema, monkeypatch):
    """Sense `model` (13/11/2026): KenLM si hi és."""
    from avlizador.traductor_cat_val.model_llengua import kenlm

    sistema(bones=("una vegada",))
    monkeypatch.setattr(kenlm, "kenlm_disponible", lambda directori=None: True)
    assert translate_cat_val("Un cop acabada la reunió, marxem.") == "Una vegada acabada la reunió, marxem."


class PrefereixAbsoluta(KenLMFals):
    def score(self, frase, bos=True, eos=True):
        return super().score(frase) + (3.0 if "absoluta" in frase else 0.0)


def test_el_model_no_tria_el_genere_de_paraules_que_no_depenen_del_nom(monkeypatch):
    """FLORES+ devtest 461 (19/11/2026): amb `concordanca="variants"` el model
    triava "absoluta una vegada". Ara la concordança la fa la regla i eixa
    frase ni es proposa, encara que el model la preferira."""
    monkeypatch.setattr(ml, "_SISTEMA_KENLM", (ModelKenLM(PrefereixAbsoluta(("una vegada",)), FREQ),
                                               ClassificadorCop(nb_cop())))
    text = "L'aïllament és absolut un cop arribes dins de la cova."
    assert translate_cat_val(text, model="kenlm") == \
        "L'aïllament és absolut una vegada arribes dins de la cova."


def test_participi_enganxat_al_nom_concorda():
    """FLORES+ devtest 782 (19/11/2026): spaCy fa "xocolata" `amod` de
    "desfeta", i els participis no es tocaven."""
    assert translate_cat_val_motor("La xocolata desfeta arriba als estàndards belgues.") == \
        "El xocolate desfet arriba als estàndards belgues."


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
            CRITERI_KENLM.lam_colisio, CRITERI_KENLM.desempat) == (1.0, "catala", 1.5, 0.75, 2.0)


def test_classificador_desat_i_carregat(tmp_path):
    nb_cop().desa(tmp_path / "nb.json", minim=1)
    c = ClassificadorCop.carrega(tmp_path / "nb.json")
    assert c.nb.logodds(["W=destral"]) > 0 > c.nb.logodds(["W=dir"])


def test_falta_directori(monkeypatch):
    monkeypatch.delenv("AVLIZADOR_KENLM_DIR", raising=False)
    with pytest.raises(FaltaKenLM):
        fitxers_kenlm()


def _hf_fals(monkeypatch, tmp_path, en_cau: bool):
    """`snapshot_download` fals: apunta les crides i torna `tmp_path`."""
    import huggingface_hub

    monkeypatch.setattr(kenlm, "_directori_hf", _DIRECTORI_HF)
    crides = []

    def snapshot_download(repo_id, revision=None, local_files_only=False, **kw):
        crides.append((repo_id, revision, local_files_only))
        if local_files_only and not en_cau:
            raise FileNotFoundError(repo_id)
        return str(tmp_path)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", snapshot_download)
    return crides


def test_la_carpeta_de_la_variable_mana(monkeypatch, tmp_path):
    pytest.importorskip("huggingface_hub")
    crides = _hf_fals(monkeypatch, tmp_path / "hf", en_cau=True)
    monkeypatch.setenv("AVLIZADOR_KENLM_DIR", str(tmp_path))
    assert kenlm.directori_kenlm() == tmp_path and crides == []


def test_sense_variable_es_baixa_de_hugging_face(monkeypatch, tmp_path):
    pytest.importorskip("huggingface_hub")
    for var in ("AVLIZADOR_KENLM_DIR", "AVLIZADOR_KENLM_DESCARREGA", "AVLIZADOR_KENLM_REVISIO", "HF_HUB_OFFLINE"):
        monkeypatch.delenv(var, raising=False)
    crides = _hf_fals(monkeypatch, tmp_path, en_cau=False)
    assert kenlm.directori_kenlm() == tmp_path
    assert crides == [(kenlm.REPO_HF, kenlm.REVISIO_HF, True), (kenlm.REPO_HF, kenlm.REVISIO_HF, False)]


def test_sense_permis_per_a_baixar(monkeypatch, tmp_path):
    pytest.importorskip("huggingface_hub")
    monkeypatch.delenv("AVLIZADOR_KENLM_DIR", raising=False)
    monkeypatch.setenv("AVLIZADOR_KENLM_DESCARREGA", "0")
    crides = _hf_fals(monkeypatch, tmp_path, en_cau=False)
    with pytest.raises(FaltaKenLM, match="Hugging Face"):
        kenlm.directori_kenlm()
    assert [c[2] for c in crides] == [True]  # només ha mirat la memòria cau


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


def test_avisa_si_la_taula_de_frequencies_no_te_una_candidata(tmp_path, monkeypatch):
    """13/11/2026: «faltes» no era en la taula i comptava com a 0 aparicions."""
    import importlib.util
    import json

    from avlizador.traductor_cat_val.model_llengua import kenlm as mk

    class KenLMModul:
        Model = staticmethod(lambda ruta: KenLMFals())

    for nom in ("valencia_net_dogv_o5.binary", "nb.json"):
        (tmp_path / nom).write_text("{}", encoding="utf-8")
    (tmp_path / "valencia_net_dogv_freq.json").write_text(
        json.dumps({"tokens": 1000, "freq": {"colp": 10, "vegada": 300}}), encoding="utf-8")
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a: object() if n == "kenlm" else real(n, *a))
    monkeypatch.setitem(__import__("sys").modules, "kenlm", KenLMModul)
    monkeypatch.setattr("avlizador.traductor_cat_val.model_llengua.sentit.carrega_classificador",
                        lambda ruta: None)
    with pytest.warns(mk.AvisFreqKenLM, match="paraules candidates no són"):
        model, _ = carrega_sistema_kenlm(tmp_path)
    assert "faltes" in model.paraules_sense_freq(["faltes", "colp"])


def test_desempat_tambe_en_els_homografs():
    """13/11/2026: el classificador desempata en totes les paraules ambigües."""
    from avlizador.traductor_cat_val.model_llengua import tria
    from avlizador.traductor_cat_val.model_llengua.punts import Punt

    p = Punt(0, "rentadora", "", "irresoluble", ["llavadora", "rentadora"], "llavadora",
             pos="NOUN", categoria="n")
    p.puntuacions = {"llavadora": {"lp": -20.0, "n": 6, "prior": -10.0},
                     "rentadora": {"lp": -20.5, "n": 6, "prior": -10.0}}
    p.sentit = "llavadora"
    assert tria(p, CRITERI_KENLM) == "llavadora" and p.decidit == "sentit"
    p.sentit = None  # sense classificador: la regla de sempre (dins del marge, la catalana)
    assert tria(p, CRITERI_KENLM) == "rentadora" and p.decidit == "catala"


def test_carrega_els_dos_formats_de_classificador(tmp_path):
    import json

    from avlizador.traductor_cat_val.model_llengua.sentit import (
        ClassificadorSentit, carrega_classificador)


    nb_cop().desa(tmp_path / "nb.json")
    assert isinstance(carrega_classificador(tmp_path / "nb.json"), ClassificadorCop)
    nb = NaiveBayes(alpha=1.0, classes=("0", "1"))
    nb.afig(["W=roba"], "0"); nb.afig(["W=sabó"], "1")
    (tmp_path / "sentit.json").write_text(json.dumps(
        {"versio": 2, "finestra": 8, "grups": {"g": {"punts": {"rentadora": ["llavadora", "rentadora"]},
                                                      "nb": nb.a_dict(0)}}}), encoding="utf-8")
    c = carrega_classificador(tmp_path / "sentit.json")
    assert isinstance(c, ClassificadorSentit) and c.index == {"rentadora": "g"}


# --- Opció amb lemes (23/11/2026) -------------------------------------------

class LemFals:
    """Com `LematitzadorLM`, sense spaCy: «va» -> «anar» i «cosia» -> «cosir»
    només si la frase porta «bragues» (spaCy lematitzava distint segons el
    candidat: per això el context es lematitza una vegada)."""

    def tokens_formes(self, text):
        t = kenlm.normalitza(text).split()
        canvis = {"va": "anar", "cosia": "cosir" if "bragues" in t else "cosia"}
        return t, [canvis.get(w, w) for w in t]

    def linia(self, text):
        return " ".join(self.tokens_formes(text)[1])


def test_lemes_referencia_es_la_frase_del_motor():
    """`puntua_punts` fixa com a referència la traducció del motor, i les
    frases candidates prenen d'ella el lema de les paraules iguals."""
    vistes = []

    class Registra(kenlm.ModelKenLMLemes):
        def logprob(self, text):
            vistes.append(self.linia(text))
            return super().logprob(text)

    model = Registra(KenLMFals(bones=("colp",)), LemFals(), FREQ)
    text, punts = ml.puntua_punts("Li va pegar un cop.", model)
    assert model._ref is not None and model._ref[0][:3] == ["li", "va", "pegar"]
    assert any(v.startswith("li anar pegar un colp") for v in vistes)
    assert any(v.startswith("li anar pegar una vegada") for v in vistes)


def test_lemes_sense_paraula_ambigua_no_lematitza():
    model = kenlm.ModelKenLMLemes(KenLMFals(), LemFals(), FREQ)
    ml.puntua_punts("Bon dia a tothom.", model)
    assert model._ref is None


def test_lemes_sense_variable_ni_hugging_face(monkeypatch):
    monkeypatch.delenv("AVLIZADOR_KENLM_DIR", raising=False)
    with pytest.raises(FaltaKenLM, match="valencia_net_dogv_lemes_o5.binary"):
        kenlm.fitxers_kenlm_lemes()


def test_lemes_es_baixen_del_mateix_repositori(monkeypatch, tmp_path):
    """Sense variable, l'opció amb lemes demana a Hugging Face (el mateix
    repositori i revisió) només els seus fitxers; si la memòria cau té la
    carpeta de la revisió però no els fitxers de lemes, els baixa."""
    huggingface_hub = pytest.importorskip("huggingface_hub")
    for var in ("AVLIZADOR_KENLM_DIR", "AVLIZADOR_KENLM_DESCARREGA", "AVLIZADOR_KENLM_REVISIO", "HF_HUB_OFFLINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(kenlm, "_directori_hf", _DIRECTORI_HF)
    for f in kenlm.FITXERS_HF:  # en la memòria cau, només els de l'opció per defecte
        (tmp_path / f).write_text("x")
    crides = []

    def snapshot_download(repo_id, revision=None, allow_patterns=None, local_files_only=False, **kw):
        crides.append((repo_id, revision, tuple(allow_patterns), local_files_only))
        if not local_files_only:
            for f in allow_patterns:
                (tmp_path / f).write_text("x")
        return str(tmp_path)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", snapshot_download)
    fitxers = kenlm.fitxers_kenlm_lemes()
    assert fitxers["model"] == tmp_path / "valencia_net_dogv_lemes_o5.binary" and fitxers["model"].exists()
    assert crides == [(kenlm.REPO_HF, kenlm.REVISIO_HF, kenlm.FITXERS_HF_LEMES, True),
                      (kenlm.REPO_HF, kenlm.REVISIO_HF, kenlm.FITXERS_HF_LEMES, False)]
    crides.clear()  # l'opció per defecte ja hi és: no baixa res
    assert kenlm.directori_kenlm() == tmp_path and [c[3] for c in crides] == [True]


def test_translate_cat_val_kenlm_lemes(monkeypatch):
    monkeypatch.setattr(ml, "_SISTEMA_KENLM_LEMES",
                        (kenlm.ModelKenLMLemes(KenLMFals(bones=("una vegada",)), LemFals(), FREQ), None))
    assert translate_cat_val("Un cop acabada la reunió, marxem.", model="kenlm-lemes").startswith("Una vegada")
