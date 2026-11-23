"""Configuració comuna dels tests."""

import pytest

from avlizador.traductor_cat_val.model_llengua import kenlm as _kenlm


@pytest.fixture(autouse=True)
def sense_hugging_face(monkeypatch):
    """Cap test baixa el model KenLM de Hugging Face ni el busca en la memòria
    cau (16/11/2026): el resultat no ha de dependre de la xarxa ni del que
    tinga baixat la màquina. Els tests de la descàrrega (test_kenlm.py)
    tornen a posar la funció real."""
    monkeypatch.setattr(_kenlm, "_directori_hf", lambda descarrega=True, fitxers=None: None)
