"""`avlizador model` i `model_llengua/descarrega.py` (26/11/2026), sense xarxa:
Hugging Face se substituïx per unes empremtes i una descàrrega falses."""

import json

import pytest

from avlizador.cli import main
from avlizador.traductor_cat_val.model_llengua import descarrega as d

FITXERS = d.fitxers_model()


def _fitxers_bons(carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    for f in FITXERS:
        (carpeta / f).write_bytes(f"contingut de {f}\n".encode())
    return carpeta


@pytest.fixture
def hf(monkeypatch, tmp_path):
    """Un Hugging Face fals: les empremtes són les dels fitxers de `bons/`, i
    «baixar» és copiar-los d'allí (es guarda què s'ha baixat)."""
    bons = _fitxers_bons(tmp_path / "bons")
    baixats = []

    def empremtes(fitxers, revisio=None):
        return {f: d.Empremta((bons / f).stat().st_size, sha1_git=d._sha1_git(bons / f)) for f in fitxers}

    def baixa(fitxers, revisio, desti):
        baixats.extend(fitxers)
        desti = desti or tmp_path / "cau"
        desti.mkdir(parents=True, exist_ok=True)
        for f in fitxers:
            (desti / f).write_bytes((bons / f).read_bytes())
        return desti

    monkeypatch.setattr(d, "empremtes", empremtes)
    monkeypatch.setattr(d, "_baixa", baixa)
    return baixats


def test_copia_d_origen_si_corresponen(hf, tmp_path):
    origen = _fitxers_bons(tmp_path / "origen")
    desti = d.descarrega_model(tmp_path / "desti", origen=origen, avisa=lambda m: None)
    assert sorted(p.name for p in desti.iterdir()) == sorted(FITXERS)
    assert hf == []


def test_baixa_el_que_no_correspon(hf, tmp_path):
    origen = _fitxers_bons(tmp_path / "origen")
    (origen / FITXERS[1]).write_text("una taula de freqüències d'una altra revisió\n", encoding="utf-8")
    avisos = []
    d.descarrega_model(tmp_path / "desti", origen=origen, avisa=avisos.append)
    assert hf == [FITXERS[1]]
    assert any("no correspon" in a for a in avisos)


def test_no_torna_a_baixar_el_que_ja_hi_es(hf, tmp_path):
    d.descarrega_model(tmp_path / "desti", avisa=lambda m: None)
    assert hf == list(FITXERS)
    d.descarrega_model(tmp_path / "desti", avisa=lambda m: None)
    assert hf == list(FITXERS)


def test_sense_comprovar_no_va_a_la_xarxa(monkeypatch, tmp_path):
    def sense_xarxa(*a, **k):
        raise AssertionError("no hauria d'anar a Hugging Face")

    monkeypatch.setattr(d, "empremtes", sense_xarxa)
    monkeypatch.setattr(d, "_baixa", sense_xarxa)
    origen = _fitxers_bons(tmp_path / "origen")
    desti = d.descarrega_model(tmp_path / "desti", origen=origen, comprova=False, avisa=lambda m: None)
    assert all((desti / f).exists() for f in FITXERS)


def test_error_si_al_final_no_correspon(monkeypatch, hf, tmp_path):
    monkeypatch.setattr(d, "_baixa", lambda fitxers, revisio, desti: desti)  # no baixa res
    with pytest.raises(d.ErrorModel, match="falta o no correspon"):
        d.descarrega_model(tmp_path / "desti", avisa=lambda m: None)


def test_memoria_cau(hf, tmp_path):
    assert d.descarrega_model(avisa=lambda m: None) == tmp_path / "cau"
    with pytest.raises(d.ErrorModel, match="només té sentit amb `desti`"):
        d.descarrega_model(origen=tmp_path, avisa=lambda m: None)


def test_lemes():
    assert set(d.fitxers_model(lemes=True)) == set(FITXERS) | {
        "valencia_net_dogv_lemes_o5.binary", "valencia_net_dogv_lemes_freq.json"}


def test_revisio_de_la_variable(monkeypatch):
    assert d.revisio_model() == d.REVISIO_HF
    monkeypatch.setenv("AVLIZADOR_KENLM_REVISIO", "main")
    assert d.revisio_model() == "main"
    assert d.info_model()["revisio_del_paquet"] is False


def test_empremta_dels_fitxers_grans(tmp_path):
    import hashlib

    p = tmp_path / "model.binary"
    p.write_bytes(b"x" * 3_000_000)
    assert d.Empremta(3_000_000, sha256=hashlib.sha256(b"x" * 3_000_000).hexdigest()).correspon(p)
    assert not d.Empremta(3_000_000, sha256="0" * 64).correspon(p)


def test_info_de_la_carpeta_de_la_variable(monkeypatch, tmp_path):
    carpeta = _fitxers_bons(tmp_path / "kenlm")
    monkeypatch.setenv("AVLIZADOR_KENLM_DIR", str(carpeta))
    info = d.info_model()
    assert info["lloc"] == "AVLIZADOR_KENLM_DIR" and info["directori"] == str(carpeta)
    assert all(info["fitxers"][f] for f in FITXERS)
    assert not info["fitxers"]["valencia_net_dogv_lemes_o5.binary"]


def test_cli_info_json(tmp_path, capsys):
    assert main(["model", "info", "--json", "--dir", str(tmp_path)]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["repo"] == "transducens/avlizador-kenlm-va" and info["lloc"] == "argument"


def test_cli_descarrega_escriu_la_carpeta(hf, tmp_path, capsys):
    assert main(["model", "descarrega", "--desti", str(tmp_path / "desti")]) == 0
    eixida = capsys.readouterr()
    assert eixida.out.strip() == str(tmp_path / "desti")  # només la carpeta: es pot usar en un script
    assert "Model KenLM" in eixida.err


def test_cli_comprova(hf, tmp_path, capsys):
    carpeta = _fitxers_bons(tmp_path / "kenlm")
    assert main(["model", "comprova", "--dir", str(carpeta)]) == 0
    (carpeta / FITXERS[0]).write_text("un altre model\n", encoding="utf-8")
    (carpeta / FITXERS[2]).unlink()
    assert main(["model", "comprova", "--dir", str(carpeta)]) == 1
    linies = capsys.readouterr().out.splitlines()[-3:]
    estat = {l.split()[-1]: l.rsplit(maxsplit=1)[0].strip() for l in linies}
    assert estat == {FITXERS[0]: "no correspon", FITXERS[1]: "bo", FITXERS[2]: "falta"}


def test_cli_errors(monkeypatch, tmp_path, capsys):
    def sense_xarxa(*a, **k):
        raise d.ErrorModel("sense xarxa")

    monkeypatch.setattr(d, "empremtes", sense_xarxa)
    assert main(["model", "descarrega", "--desti", str(tmp_path)]) == 1
    assert "ERROR: sense xarxa" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        main(["model", "descarrega", "--origen", str(tmp_path)])
    assert e.value.code == 2
