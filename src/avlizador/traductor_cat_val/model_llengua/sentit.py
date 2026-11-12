"""
model_llengua/sentit.py -- Classificadors de sentit per a les col·lisions
(11/11/2026, camí C1; al paquet des del 12/11/2026).

Interfície fixa: `candidat(punt) -> str | None`. Rep un `Punt` ja puntuat
(amb les frases valencianes de cada candidat) i torna el candidat del
sentit que veu en la frase, o `None` si no en sap res. `tria` l'usa com a
desempat (`Criteri.desempat`): només quan el model de llengua guanya per
poc. Canviar de classificador = un altre `nb.json` (reentrenat amb
`pipeline/03_seleccio_de_model/model_llengua/sentit_cop.py`) o una altra
classe amb el mateix mètode (p. ex. fastText).

`ClassificadorCop`: Naive Bayes multinomial per a "cop/cops" (colp = golp,
vegada = vez). Pren la frase d'un candidat, hi posa un buit en lloc de la
paraula i en trau els lemes del voltant (spaCy). Les paraules que
concorden amb el nom ("una/dues/última") es queden només amb la categoria:
en valencià delaten el candidat ("una vegada" / "un colp"), però en
l'entrada catalana "cop" sempre és masculí. Entrenat amb frases valencianes
reals (MaCoCu net, DOGV, AVL; fora el que s'assembla als benchmarks):
"destral", "cara", "estat" -> colp; "tres", "cada", "a" -> vegada.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from .kenlm import normalitza

SENTIT_COP = {"colp": "colp", "colps": "colp", "vegada": "vegada", "vegades": "vegada"}
CLASSES = ("colp", "vegada")
BUIT = "__X__"
# Categories que concorden amb el nom ("una/dues/última vegada"): només
# estes s'amaguen. Els noms ("banc", "cara") tenen gènere propi i són pistes.
CONCORDEN = {"DET", "NUM", "ADJ", "PRON"}
FINESTRA = 8


class Lematitzador:
    """Lemes d'spaCy sobre tokens ja separats (un per token, alineats). Per
    defecte, el mateix model d'spaCy que el motor (no se'n carrega un altre)."""

    def __init__(self, nlp=None, genere: bool = False) -> None:
        if nlp is None:
            from ..rules.pos_tagger import _carrega_spacy

            nlp = _carrega_spacy()
        from spacy.tokens import Doc

        self.nlp, self.Doc = nlp, Doc
        self.genere = genere  # True: deixa les paraules amb gènere (sense amagar-les)

    def lemes(self, llistes: list[list[str]], lot: int = 256) -> list[list[str]]:
        docs = (self.Doc(self.nlp.vocab, words=t) for t in llistes)
        return [[self.forma(t) for t in d] for d in self.nlp.pipe(docs, batch_size=lot)]

    def forma(self, t) -> str:
        """Lema; si la paraula té gènere i concorda (un/una, dos/dues,
        últim/última), només la categoria (`<DET>`...): spaCy no passa "una"
        ni "dues" a "un"/"dos", així que el lema no basta."""
        if not self.genere and t.text != BUIT and t.morph.get("Gender") and t.pos_ in CONCORDEN:
            return f"<{t.pos_}>"
        return (t.lemma_ or t.text).lower()


def trets(lemes: list[str], i: int, finestra: int = FINESTRA) -> list[str]:
    """Trets del buit en la posició `i`: els lemes de les 2 paraules de cada
    costat (amb la posició), els bigrames del costat i la bossa de lemes a
    ±`finestra`.

    >>> trets(["a", "un", "x", "de", "destral", "."], 2, 3)
    ['L1=un', 'L2=a', 'R1=de', 'R2=destral', 'L21=a_un', 'R12=de_destral', 'W=a', 'W=un', 'W=de', 'W=destral']
    """
    def at(j):
        return lemes[j] if 0 <= j < len(lemes) else ("<s>" if j < 0 else "</s>")

    f = [f"L1={at(i - 1)}", f"L2={at(i - 2)}", f"R1={at(i + 1)}", f"R2={at(i + 2)}",
         f"L21={at(i - 2)}_{at(i - 1)}", f"R12={at(i + 1)}_{at(i + 2)}"]
    for j in range(max(0, i - finestra), min(len(lemes), i + finestra + 1)):
        if j != i and any(c.isalpha() for c in lemes[j]):
            f.append(f"W={lemes[j]}")
    return f


class NaiveBayes:
    """Naive Bayes multinomial de dues classes (recomptes en JSON), amb
    priors iguals.

    >>> nb = NaiveBayes(alpha=1.0)
    >>> nb.afig(["W=destral"], "colp"); nb.afig(["W=tres"], "vegada")
    >>> nb.logodds(["W=destral"]) > 0 > nb.logodds(["W=tres"])
    True
    >>> nb.logodds(["W=desconeguda"])
    0.0
    """

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self.n = {c: Counter() for c in CLASSES}
        self.total = Counter()
        self._v = None

    def afig(self, f: list[str], classe: str) -> None:
        self.n[classe].update(f)
        self.total[classe] += len(f)
        self._v = None

    def logodds(self, f: list[str]) -> float:
        """Suma de log P(x|colp) − log P(x|vegada). Els trets que no ixen en
        l'entrenament s'ignoren: amb el suavitzat i "colp" amb 13 vegades
        menys dades, un tret desconegut empentava +2,5 cap a "colp"."""
        if self._v is None:
            self._v = len(set(self.n["colp"]) | set(self.n["vegada"])) or 1
        v, s = self._v, 0.0
        for x in f:
            if not self.n["colp"][x] and not self.n["vegada"][x]:
                continue
            pc = (self.n["colp"][x] + self.alpha) / (self.total["colp"] + self.alpha * v)
            pv = (self.n["vegada"][x] + self.alpha) / (self.total["vegada"] + self.alpha * v)
            s += math.log(pc) - math.log(pv)
        return s

    def desa(self, path: Path, minim: int = 2) -> None:
        tots = self.n["colp"] + self.n["vegada"]
        json.dump({"alpha": self.alpha, "total": dict(self.total),
                   "n": {c: {k: v for k, v in self.n[c].items() if tots[k] >= minim} for c in CLASSES}},
                  Path(path).open("w", encoding="utf-8"), ensure_ascii=False)

    @classmethod
    def carrega(cls, path: Path) -> NaiveBayes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        nb = cls(d["alpha"])
        nb.n = {c: Counter(d["n"][c]) for c in CLASSES}
        nb.total = Counter(d["total"])
        return nb

    def mes_informatius(self, k: int = 25) -> dict:
        tots = self.n["colp"] + self.n["vegada"]
        punt = {x: self.logodds([x]) for x, c in tots.items() if c >= 20}
        ordre = sorted(punt.items(), key=lambda x: x[1])
        return {"vegada": ordre[:k], "colp": ordre[::-1][:k]}


def trets_de_frases(frases: dict[str, str], lem: Lematitzador, finestra: int = FINESTRA) -> list[str] | None:
    """Trets a partir de la primera frase candidata (valenciana) on es troba
    el seu candidat; el candidat es canvia pel buit. `frases`: `{candidat:
    frase}` (com `Punt.frases`)."""
    for c, frase in frases.items():
        toks = normalitza(frase).split()
        if c.lower() in toks:
            i = toks.index(c.lower())
            toks[i] = BUIT
            l = lem.lemes([toks])[0]
            l[i] = BUIT
            return trets(l, i, finestra)
    return None


class ClassificadorCop:
    """Classificador de sentit de "cop/cops" (Naive Bayes + lemes d'spaCy).

    >>> nb = NaiveBayes(alpha=1.0)
    >>> nb.afig(["W=destral"], "colp"); nb.afig(["L1=<NUM>"], "vegada")
    >>> c = ClassificadorCop(nb)
    >>> from .punts import Punt
    >>> p = Punt(0, "cop", "", "colisio", ["colp", "vegada"], None)
    >>> p.frases = {"colp": "Li va pegar un colp amb la destral.", "vegada": "Li va pegar una vegada amb la destral."}
    >>> c.candidat(p)
    'colp'
    >>> p.frases = {"colp": "Ho he dit dos colps.", "vegada": "Ho he dit dues vegades."}
    >>> p.candidats = ["colps", "vegades"]
    >>> p.frases = {"colps": p.frases["colp"], "vegades": p.frases["vegada"]}
    >>> c.candidat(p)
    'vegades'

    Fora de les col·lisions, o amb candidats que no coneix, no diu res:

    >>> c.candidat(Punt(0, "calces", "", "irresoluble", ["bragues", "calces"], "bragues")) is None
    True
    """

    def __init__(self, nb: NaiveBayes, lematitzador: Lematitzador | None = None, finestra: int = FINESTRA) -> None:
        self.nb, self._lem, self.finestra = nb, lematitzador, finestra

    @classmethod
    def carrega(cls, path: Path) -> ClassificadorCop:
        return cls(NaiveBayes.carrega(path))

    @property
    def lem(self) -> Lematitzador:
        if self._lem is None:
            self._lem = Lematitzador()
        return self._lem

    def candidat(self, punt) -> str | None:
        if punt.tipus != "colisio" or not any(c.lower() in SENTIT_COP for c in punt.candidats):
            return None
        frases = punt.frases or {c: d["frase"] for c, d in punt.puntuacions.items()}
        f = trets_de_frases(frases, self.lem, self.finestra)
        if f is None:
            return None
        sentit = "colp" if self.nb.logodds(f) > 0 else "vegada"
        return next((c for c in punt.candidats if SENTIT_COP.get(c.lower()) == sentit), None)
