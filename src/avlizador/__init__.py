"""AVLizador: traductor dialectal català -> valencià (norma AVL) i Grau
Dialectal (GD, GDV, GDC).

    from avlizador import translate_cat_val, calcula_gd, calcula_gdv, calcula_gdc

    translate_cat_val("Aquest noi necessita ajuda.")   # -> "Este xic necessita ajuda."
    calcula_gdv("Este xiquet vol vindre hui.")["gdv"]  # -> 1.0

Subpaquets:
- `avlizador.traductor_cat_val`: el traductor (motor de regles + KenLM).
- `avlizador.grau_dialectal`: GD, GDV i GDC.
- `avlizador.avaluacio`: mètriques i avaluació en els benchmarks
  (extra `[avaluacio]`).

Línia d'ordres: `avlizador tradueix | gd | gdv | gdc | avalua | model` (vore
`avlizador --help`).

API pública (26/11/2026): el que exporta este mòdul (`__all__`) i els
`__all__` de `avlizador.traductor_cat_val` i `avlizador.grau_dialectal`.
Canviar-la o llevar-ne alguna cosa exigix una versió major; afegir-ne, una
menor. La resta de mòduls són interns.
"""

__version__ = "2.0.1"

_API = {
    "translate_cat_val": "traductor_cat_val",
    "translate_cat_val_motor": "traductor_cat_val",
    "calcula_gd": "grau_dialectal",
    "calcula_gdv": "grau_dialectal",
    "calcula_gdc": "grau_dialectal",
    "resalta_html": "grau_dialectal",
    "info_model": "traductor_cat_val",
    "descarrega_model": "traductor_cat_val",
    "comprova_model": "traductor_cat_val",
    "kenlm_disponible": "traductor_cat_val",
}

__all__ = ["__version__", *_API]


def __getattr__(nom: str):
    # Import peresós: `import avlizador` no carrega els diccionaris ni spaCy.
    if nom in _API:
        from importlib import import_module

        return getattr(import_module(f".{_API[nom]}", __name__), nom)
    raise AttributeError(f"module 'avlizador' has no attribute {nom!r}")
