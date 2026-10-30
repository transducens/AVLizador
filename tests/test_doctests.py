"""Tots els doctests del paquet `avlizador` (regles, model de llengua, GD,
mètriques...). Abans del paquet (fins al 30/10/2026) eren 648 entre
`traductor/` i el GD."""

import doctest
import importlib
import pkgutil

import pytest

import avlizador

MODULS = sorted(
    nom for _, nom, _ in pkgutil.walk_packages(avlizador.__path__, "avlizador.")
    if not nom.endswith("__main__")
)


@pytest.mark.parametrize("nom", MODULS)
def test_doctests(nom):
    modul = importlib.import_module(nom)
    resultat = doctest.testmod(modul, optionflags=doctest.ELLIPSIS)
    assert resultat.failed == 0, f"{resultat.failed} doctests fallats en {nom}"
