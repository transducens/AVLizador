"""
model_llengua/lemes.py -- Text en LEMES per a un KenLM de lemes (12/11/2026,
EXPERIMENT; proposta del supervisor; resultats en
`documentacio/resultats_model_llengua_kenlm.md`).

Idea: KenLM no es decidix en les paraules rares ("panotxes", "fartaneres",
"rentadores", "recuites") perquè les ha vistes poques vegades, i menys en
plural. Si el context es passa a lemes, "va pegar" / "pegà" / "pegaren"
compten com "pegar" i el model té més dades per a cada context.

Què NO es lematitza (es queda la forma):
- les paraules candidates de `model_llengua` (les catalanes i les seues
  traduccions: "cop", "colp", "vegades", "nous", "anous"...): són el que es
  compara i han de quedar distintes (i el prior en compta la freqüència);
- les paraules amb gènere que concorden (DET, NUM, ADJ, PRON amb `Gender`):
  "les nous" (fruit) / "els nous" (adjectiu), "una vegada" / "un colp". Amb
  lemes tot quedaria "el nou" i es perdria la pista;
- la puntuació i els números.

La MATEIXA funció (`LematitzadorLM.linies`) fa el text d'entrenament
(`pipeline/08_traduccio_corpus/macocu/kenlm/lematitza_text.py`) i les frases
que puntua el model (`compara_models.py`, clau `kenlm_lemes*`).
"""

from __future__ import annotations

from .kenlm import normalitza

# Les mateixes categories que s'amaguen en el classificador de "cop" (sentit.py).
CONCORDEN = {"DET", "NUM", "ADJ", "PRON"}


def formes_candidates() -> set[str]:
    """Formes catalanes i candidats valencians de tots els punts ambigus.

    >>> f = formes_candidates()
    >>> {"cop", "colp", "vegada", "nous", "anous", "panotxes"} <= f
    True
    """
    from .punts import carrega_punts

    return {c.lower() for p, d in carrega_punts().items() for c in [p, *d["candidats"]]}


class LematitzadorLM:
    """Frase -> línia de lemes per a KenLM (tokens com `normalitza`).

    >>> lem = LematitzadorLM()
    >>> lem.linia("Les nous que vaig comprar eren boníssimes.").split()[:5]
    ['les', 'nous', 'que', 'anar', 'comprar']
    >>> lem.linia("Li va pegar un cop amb la destral.").split()[:5]
    ['li', 'anar', 'pegar', 'un', 'cop']
    """

    def __init__(self, conserva: set[str] | None = None, nlp=None) -> None:
        if nlp is None:
            from ..rules.pos_tagger import _carrega_spacy

            nlp = _carrega_spacy()
        from spacy.tokens import Doc

        self.nlp, self.Doc = nlp, Doc
        self.conserva = formes_candidates() if conserva is None else conserva

    def forma(self, t) -> str:
        w = t.text
        if w in self.conserva or not any(c.isalpha() for c in w):
            return w
        if t.pos_ in CONCORDEN and t.morph.get("Gender"):
            return w
        lema = "_".join((t.lemma_ or w).lower().split())
        return lema or w

    def linies(self, textos: list[str], lot: int = 256) -> list[str]:
        """Cada text: normalitzat, lematitzat i normalitzat altra vegada
        (així la línia ja és la que veu KenLM: `normalitza` no la canvia)."""
        tokens = [normalitza(t).split() for t in textos]
        docs = (self.Doc(self.nlp.vocab, words=t) for t in tokens)
        return [normalitza(" ".join(self.forma(t) for t in d)) for d in self.nlp.pipe(docs, batch_size=lot)]

    def linia(self, text: str) -> str:
        return self.linies([text])[0]
