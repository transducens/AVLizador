"""AVLizador: traductor dialectal català -> valencià (norma AVL) i Grau
Dialectal (GD, GDV, GDC).

    from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

    translate_cat_val("Aquest noi necessita ajuda.")   # -> "Este xic necessita ajuda."
    calcula_gdv("Este xiquet vol vindre hui.")["gdv"]  # -> 1.0

Subpaquets:
- `avlizador.traductor_cat_val`: el traductor (motor de regles + FLOR-760M).
- `avlizador.grau_dialectal`: GD, GDV i GDC.
- `avlizador.avaluacio`: mètriques i avaluació en els benchmarks
  (extra `[avaluacio]`).

Línia d'ordres: `avlizador tradueix | gd | gdv | gdc | avalua` (vore
`avlizador --help`).
"""

__version__ = "1.0.0"

_API = {
    "translate_cat_val": "traductor_cat_val",
    "translate_cat_val_motor": "traductor_cat_val",
    "calcula_gd": "grau_dialectal",
    "calcula_gdv": "grau_dialectal",
    "calcula_gdc": "grau_dialectal",
}

__all__ = ["__version__", *_API]


def __getattr__(nom: str):
    # Import peresós: `import avlizador` no carrega els diccionaris ni spaCy.
    if nom in _API:
        from importlib import import_module

        return getattr(import_module(f".{_API[nom]}", __name__), nom)
    raise AttributeError(f"module 'avlizador' has no attribute {nom!r}")
