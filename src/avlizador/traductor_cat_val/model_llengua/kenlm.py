"""
model_llengua/kenlm.py -- Puntuador KenLM (n-grames, CPU) i classificador
de sentit per a les paraules ambigües. Integrat el 12/11/2026 com a
alternativa a FLOR-760M; és el model PER DEFECTE des del 13/11/2026
(decisió de l'usuari).

Ocupa el MATEIX buit que FLOR: el motor construïx les frases valencianes
de cada candidat i `ModelKenLM.logprob` les puntua. Dos diferències:

- Prior (`Criteri.lam`): log P(candidat sol) = ln((n + 1) / tokens), amb n
  = vegades que la paraula apareix en el text d'entrenament
  (`<model>_freq.json`, de `freq_unigrames.py`). L'unigrama de KenLM no és
  la freqüència (Kneser-Ney) i log P("<s> colp </s>") tampoc.
- Classificador de sentit (camí C1): en les col·lisions ("cop" -> "colp" /
  "vegada"), si KenLM guanya per menys de `Criteri.desempat` punts, decidix
  un classificador que mira tota la frase (`sentit.py`).

El sistema: `kenlm_val_net_dogv` (MaCoCu valencià net + DOGV 2025-2026,
ordre 5, poda de singletons, 77 MB) amb `CRITERI_KENLM` (marge 3, la
catalana per defecte, λ 1,5 en els homògrafs i 0,75 en les col·lisions,
desempat < 2 amb el Naive Bayes de "cop"). Últimes xifres (13/11/2026,
`avalua_sistema_20261113_1308`, KenLM / FLOR): homògrafs v1 227 / 217 de
253, v2 111 / 96 de 160, manual 232 / 231 de 458, 151 144 / 145, BOE
estricte 1.894 / 1.894, gplsi 1.550 / 1.551; en les 257 decisions dels
homògrafs, 193 encerts i 1 error greu. 0,1 ms per frase candidata
(FLOR, 833 ms) i sense torch. Detall en
`documentacio/resultats_model_llengua_kenlm.md`.

Fitxers (fora de git; vore `fitxers_kenlm`), en la carpeta de la variable
d'entorn `AVLIZADOR_KENLM_DIR`:
- `valencia_net_dogv_o5.binary` -- el model KenLM;
- `valencia_net_dogv_freq.json` -- freqüències per al prior;
- `nb.json` (o `sentit_cop/nb.json`) -- el classificador de "cop".
Cal el paquet `kenlm` (extra `[kenlm]`; en Windows necessita compilador,
la imatge Docker és Linux).
"""

from __future__ import annotations

import json
import math
import os
import re
import warnings
from pathlib import Path

LN10 = math.log(10)
VAR_DIRECTORI = "AVLIZADOR_KENLM_DIR"
NOM_MODEL = "valencia_net_dogv"

_APOSTROF = str.maketrans({"’": "'", "ʼ": "'", "´": "'", "`": "'"})
_TOKEN = re.compile(r"[^\W\d_]+(?:[·\-][^\W\d_]+)*'?|\d+(?:[.,]\d+)*|[^\w\s]")
_DIGITS = re.compile(r"\d+(?:[.,]\d+)*")


def normalitza(text: str) -> str:
    """Frase -> tokens separats per espais, com en el text d'entrenament de
    KenLM (la MATEIXA funció per a entrenar i per a puntuar; abans en
    `pipeline/08_traduccio_corpus/macocu/kenlm/exporta_text.py`):
    minúscules, apòstrof tipogràfic -> ', l'apòstrof pegat a la paraula
    d'abans, els números a "0" i la puntuació en tokens a banda.

    >>> normalitza("D’una vegada, l'home va fer-ho el 2022!")
    "d' una vegada , l' home va fer-ho el 0 !"
    """
    toks = _TOKEN.findall(text.translate(_APOSTROF).lower())
    return " ".join("0" if _DIGITS.fullmatch(t) else t for t in toks)


class ModelKenLM:
    """log P (natural, com FLOR) d'una frase segons un model KenLM.

    `model`: un `kenlm.Model` (o qualsevol objecte amb `score(frase, bos,
    eos)` en base 10). `freq`: el JSON de `freq_unigrames.py`
    (`{"tokens": N, "freq": {paraula: n}}`) per al prior.

    >>> class Fals:
    ...     def score(self, frase, bos=True, eos=True):
    ...         return -1.0 * (len(frase.split()) + bos + eos)
    >>> m = ModelKenLM(Fals(), {"tokens": 100, "freq": {"colp": 1, "vegada": 39}})
    >>> lp, n = m.logprob("Una vegada més.")
    >>> round(lp, 3), n
    (-13.816, 5)
    >>> import warnings
    >>> with warnings.catch_warnings(record=True) as avisos:
    ...     warnings.simplefilter("always")
    ...     [round(m.prior(w)[0], 3) for w in ("colp", "Vegada", "gandula")]
    [-3.912, -0.916, -4.605]
    >>> [str(a.message)[:40] for a in avisos]
    ['«gandula» no és en la taula de freqüènci']

    Una paraula que no és en la taula compta com a 0 aparicions, i amb `lam`
    això li dona AVANTATGE (el prior es resta): passà el 13/11/2026 amb
    «faltes» (la taula era d'abans del canvi del lèxic). Per això s'avisa
    (una vegada per paraula); `paraules_sense_freq` les llista totes.
    """

    def __init__(self, model, freq: dict | None = None) -> None:
        self.model, self.freq = model, freq
        self._avisades: set[str] = set()

    def paraules_sense_freq(self, paraules) -> list[str]:
        """Les `paraules` (normalitzades, d'una sola paraula) que no són en
        la taula de freqüències.

        >>> ModelKenLM(None, {"tokens": 10, "freq": {"colp": 1}}).paraules_sense_freq(["colp", "faltes"])
        ['faltes']
        """
        if self.freq is None:
            return []
        formes = {normalitza(p) for p in paraules}
        return sorted(f for f in formes if f and " " not in f and f not in self.freq["freq"])

    @classmethod
    def carrega(cls, binari: Path, freq: Path | None = None) -> ModelKenLM:
        import kenlm

        dades = json.loads(Path(freq).read_text(encoding="utf-8")) if freq else None
        return cls(kenlm.Model(str(binari)), dades)

    def logprob(self, text: str) -> tuple[float, int]:
        """`(log P de la frase normalitzada amb <s> i </s>, paraules + 1)`."""
        frase = normalitza(text)
        return self.model.score(frase, bos=True, eos=True) * LN10, len(frase.split()) + 1

    def prior(self, paraula: str) -> tuple[float, int]:
        """log P(paraula sola), per a `Criteri.lam`. Amb `freq`: ln((n + 1) /
        tokens). Sense (o si són diverses paraules): l'n-grama de KenLM
        sense <s> ni </s>, que NO seguix la freqüència (Kneser-Ney: "colp"
        −10,66 i "vegada" −9,89, quan "vegada" és 35 voltes més freqüent)."""
        frase = normalitza(paraula)
        if self.freq is not None and " " not in frase:
            if frase not in self.freq["freq"] and frase not in self._avisades:
                self._avisades.add(frase)
                warnings.warn(f"«{frase}» no és en la taula de freqüències de KenLM: compta com a 0 "
                              "aparicions. Regenera-la amb freq_unigrames.py.", AvisFreqKenLM, stacklevel=2)
            n = self.freq["freq"].get(frase, 0)
            return math.log((n + 1) / self.freq["tokens"]), 1
        return self.model.score(frase, bos=False, eos=False) * LN10, len(frase.split())


class FaltaKenLM(RuntimeError):
    """Falta el paquet `kenlm` o algun fitxer del model."""


class AvisFreqKenLM(UserWarning):
    """Alguna paraula candidata no és en la taula de freqüències (13/11/2026)."""


def directori_kenlm(directori: Path | str | None = None) -> Path:
    """La carpeta dels fitxers: `directori` o `AVLIZADOR_KENLM_DIR`."""
    directori = directori or os.environ.get(VAR_DIRECTORI)
    if not directori:
        raise FaltaKenLM(
            f"Falta la carpeta del model KenLM: defineix {VAR_DIRECTORI} (amb "
            f"{NOM_MODEL}_o5.binary, {NOM_MODEL}_freq.json i nb.json).")
    return Path(directori)


def fitxers_kenlm(directori: Path | str | None = None) -> dict[str, Path]:
    """`{"model", "freq", "sentit"}` dins de la carpeta. El classificador:
    `sentit.json` (el general, des del 13/11/2026) si hi és; si no, el de
    "cop", `nb.json` en la carpeta o en `sentit_cop/`.

    >>> import tempfile
    >>> d = Path(tempfile.mkdtemp())
    >>> (d / "sentit_cop").mkdir()
    >>> _ = (d / "sentit_cop" / "nb.json").write_text("{}")
    >>> {k: v.relative_to(d).as_posix() for k, v in fitxers_kenlm(d).items()}
    {'model': 'valencia_net_dogv_o5.binary', 'freq': 'valencia_net_dogv_freq.json', 'sentit': 'sentit_cop/nb.json'}
    """
    d = directori_kenlm(directori)
    sentit = d / "sentit.json"
    if not sentit.exists():
        sentit = d / "nb.json"
    if not sentit.exists() and (d / "sentit_cop" / "nb.json").exists():
        sentit = d / "sentit_cop" / "nb.json"
    return {"model": d / f"{NOM_MODEL}_o5.binary", "freq": d / f"{NOM_MODEL}_freq.json", "sentit": sentit}


def kenlm_disponible(directori: Path | str | None = None) -> bool:
    """True si està instal·lat `kenlm` i hi ha els tres fitxers (no els carrega)."""
    from importlib.util import find_spec

    if find_spec("kenlm") is None:
        return False
    try:
        return all(p.exists() for p in fitxers_kenlm(directori).values())
    except FaltaKenLM:
        return False


def carrega_sistema_kenlm(directori: Path | str | None = None):
    """`(ModelKenLM, ClassificadorCop)` del sistema KenLM, o `FaltaKenLM`
    amb el que falta."""
    from importlib.util import find_spec

    if find_spec("kenlm") is None:
        raise FaltaKenLM('Falta el paquet kenlm: pip install "avlizador[kenlm]" (en Linux o Docker).')
    fitxers = fitxers_kenlm(directori)
    falten = [str(p) for p in fitxers.values() if not p.exists()]
    if falten:
        raise FaltaKenLM("Falten fitxers del model KenLM: " + ", ".join(falten))
    from .lemes import formes_candidates
    from .sentit import carrega_classificador

    model = ModelKenLM.carrega(fitxers["model"], fitxers["freq"])
    falten = model.paraules_sense_freq(formes_candidates())
    if falten:  # la taula és d'abans d'un canvi del lèxic: avisa en carregar
        warnings.warn(f"{len(falten)} paraules candidates no són en {fitxers['freq'].name} ("
                      f"{', '.join(falten[:10])}{'...' if len(falten) > 10 else ''}): regenera-la amb "
                      "freq_unigrames.py.", AvisFreqKenLM, stacklevel=2)
        model._avisades.update(falten)
    return model, carrega_classificador(fitxers["sentit"])
