"""
model_llengua/kenlm.py -- Puntuador KenLM (n-grames, CPU) i classificador
de sentit per a les paraules ambigües. Integrat el 12/11/2026 com a
alternativa a FLOR-760M; és el model per defecte des del 13/11/2026 i
l'únic des de la versió 2.0.0 (decisions de l'usuari; FLOR ja no és en el
paquet).

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
ordre 5, poda de singletons, 77 MB) amb `CRITERI_KENLM` (marge 1 des de la
2.0.1, abans 3; la catalana per defecte, λ 1,5 en els homògrafs i 0,75 en
les col·lisions, desempat < 2 amb el Naive Bayes de "cop"). Últimes xifres (13/11/2026,
`avalua_sistema_20261113_1308`, KenLM / FLOR): homògrafs v1 227 / 217 de
253, v2 111 / 96 de 160, manual 232 / 231 de 458, 151 144 / 145, BOE
estricte 1.894 / 1.894, gplsi 1.550 / 1.551; en les 257 decisions dels
homògrafs, 193 encerts i 1 error greu. 0,1 ms per frase candidata
(FLOR, 833 ms) i sense torch. Detall en
`documentacio/resultats_model_llengua_kenlm.md`.

Fitxers (fora de git; vore `fitxers_kenlm`):
- `valencia_net_dogv_o5.binary` -- el model KenLM;
- `valencia_net_dogv_freq.json` -- freqüències per al prior;
- `sentit.json` (o el de "cop", `nb.json`) -- el classificador de sentit.
On es busquen (`directori_kenlm`, 16/11/2026): en la carpeta de la variable
d'entorn `AVLIZADOR_KENLM_DIR` si està definida; si no, en el model de
Hugging Face `transducens/avlizador-kenlm-va` (`REPO_HF`), que es baixa a la
memòria cau de Hugging Face la primera vegada, com FLOR. Per a no baixar res:
`AVLIZADOR_KENLM_DESCARREGA=0` o `HF_HUB_OFFLINE=1`. La revisió:
`AVLIZADOR_KENLM_REVISIO` (per defecte, `REVISIO_HF`).
Cal el paquet `kenlm` (extra `[kenlm]`, que també porta `huggingface_hub`;
en Windows necessita compilador, la imatge Docker és Linux).

Opció amb LEMES (`ModelKenLMLemes`, 23/11/2026, decisió de l'usuari; NO és
el per defecte): el mateix sistema amb el KenLM de lemes parcials
(`valencia_net_dogv_lemes_o5.binary` i `_lemes_freq.json`). Els fitxers són
en el MATEIX repositori de Hugging Face i es busquen igual (la carpeta
d'`AVLIZADOR_KENLM_DIR` o la memòria cau / la descàrrega), però només quan
es demana l'opció: qui usa el sistema per defecte no els baixa. Vore
`ModelKenLMLemes` i `documentacio/resultats_model_llengua_kenlm.md`, 4.23-4.26.
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
NOM_MODEL_LEMES = "valencia_net_dogv_lemes"  # 23/11/2026: l'opció amb lemes
# Els fitxers de Hugging Face que necessita cada opció (no la fitxa ni el bàner).
FITXERS_HF = (f"{NOM_MODEL}_o5.binary", f"{NOM_MODEL}_freq.json", "sentit.json")
FITXERS_HF_LEMES = (f"{NOM_MODEL_LEMES}_o5.binary", f"{NOM_MODEL_LEMES}_freq.json", "sentit.json")
# 16/11/2026: els fitxers també es poden baixar de Hugging Face.
REPO_HF = "transducens/avlizador-kenlm-va"
# Revisió del model que correspon a cada versió del paquet: el commit de Hugging Face
# (no es pot crear una etiqueta des de la web). 2.0.0: commit db4a1f1, 17/11/2026.
# 2.0.1: commit 684993c, 23/11/2026 (la taula de freqüències nova, amb «brolladors»,
# del commit ea87f3f, i els dos fitxers de l'opció amb lemes).
REVISIO_HF = "684993c83721bb000d424bbeb7286247c40e9154"
VAR_REVISIO = "AVLIZADOR_KENLM_REVISIO"
VAR_DESCARREGA = "AVLIZADOR_KENLM_DESCARREGA"

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


def _directori_hf(descarrega: bool = True, fitxers=FITXERS_HF) -> Path | None:
    """La carpeta del model de Hugging Face (`REPO_HF`) amb els `fitxers`: de
    la memòria cau si ja hi són tots; si no, els baixa (si `descarrega` i no
    ho impedixen `AVLIZADOR_KENLM_DESCARREGA=0` ni `HF_HUB_OFFLINE`). `None`
    si no es pot (sense `huggingface_hub`, sense xarxa, sense permís). Només
    es baixen els `fitxers` (els de l'opció per defecte, `FITXERS_HF`, o els
    de l'opció amb lemes, `FITXERS_HF_LEMES`), no tot el repositori."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return None
    revisio = os.environ.get(VAR_REVISIO) or REVISIO_HF
    fitxers = list(fitxers)
    try:
        cau = Path(snapshot_download(REPO_HF, revision=revisio, allow_patterns=fitxers, local_files_only=True))
        # La memòria cau té la carpeta de la revisió encara que només s'hi haja baixat
        # l'altra opció: si falta algun fitxer, cal baixar-lo.
        if all((cau / f).exists() for f in fitxers):
            return cau
    except Exception:  # no és en la memòria cau
        pass
    sense_xarxa = os.environ.get("HF_HUB_OFFLINE", "").lower() in ("1", "true", "yes")
    if not descarrega or os.environ.get(VAR_DESCARREGA) == "0" or sense_xarxa:
        return None
    try:
        return Path(snapshot_download(REPO_HF, revision=revisio, allow_patterns=fitxers))
    except Exception:
        return None


def directori_kenlm(directori: Path | str | None = None, descarrega: bool = True,
                    fitxers=FITXERS_HF) -> Path:
    """La carpeta dels fitxers: `directori`, `AVLIZADOR_KENLM_DIR` o, si no
    n'hi ha cap, el model de Hugging Face amb els `fitxers` (vore
    `_directori_hf`)."""
    directori = directori or os.environ.get(VAR_DIRECTORI)
    if directori:
        return Path(directori)
    hf = _directori_hf(descarrega, fitxers)
    if hf is None:
        raise FaltaKenLM(
            f"Falta el model KenLM: no s'ha pogut baixar de Hugging Face ({REPO_HF}) ni hi ha "
            f"{VAR_DIRECTORI} (una carpeta amb {', '.join(fitxers)}).")
    return hf


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


class ModelKenLMLemes(ModelKenLM):
    """KenLM de LEMES parcials (opció, 23/11/2026; decisió de l'usuari): la
    frase es passa a lemes amb `lemes.LematitzadorLM` (la mateixa funció del
    text d'entrenament) abans de puntuar-la; les paraules candidates i les
    que hi concorden en gènere es queden en la seua forma, així que el prior
    (freqüència del candidat, de la taula del text de lemes) és el de sempre.

    El context es lematitza UNA vegada, sobre la traducció del motor
    (`fixa_referencia`, que crida `puntua_punts` quan la frase té alguna
    paraula ambigua): spaCy lematitzava el context de manera distinta segons
    el candidat ("el sastre cosia bragues" -> "cosir"; "el sastre cosia
    calces" -> "cosia") i les frases candidates ja no es podien comparar. En
    cada frase candidata, les paraules iguals que en la referència prenen el
    lema de la referència i només les que canvien es lematitzen dins de la
    frase candidata.

    >>> class M:
    ...     def score(self, frase, bos=True, eos=True): return -float(len(frase.split()))
    >>> class Lem:
    ...     def tokens_formes(self, text):
    ...         t = normalitza(text).split()
    ...         return t, [{"cosia": "cosir" if "bragues" in t else "cosia"}.get(w, w) for w in t]
    ...     def linia(self, text): return " ".join(self.tokens_formes(text)[1])
    >>> k = ModelKenLMLemes(M(), Lem())
    >>> k.linia("El sastre cosia calces.")
    'el sastre cosia calces .'
    >>> k.fixa_referencia("El sastre cosia bragues.")
    >>> k.linia("El sastre cosia calces."), k.logprob("El sastre cosia calces.")[1]
    ('el sastre cosir calces .', 6)
    """

    def __init__(self, model, lematitzador, freq: dict | None = None) -> None:
        super().__init__(model, freq)
        self.lem = lematitzador
        self._ref = None  # (tokens normalitzats, formes) de la traducció del motor

    def fixa_referencia(self, text: str) -> None:
        self._ref = self.lem.tokens_formes(text)

    def linia(self, text: str) -> str:
        if self._ref is None:
            return self.lem.linia(text)
        import difflib

        toks, formes = self.lem.tokens_formes(text)
        ref_toks, ref_formes = self._ref
        eixida = list(formes)
        for a, b, n in difflib.SequenceMatcher(None, ref_toks, toks, autojunk=False).get_matching_blocks():
            eixida[b:b + n] = ref_formes[a:a + n]
        return normalitza(" ".join(eixida))

    def logprob(self, text: str) -> tuple[float, int]:
        return super().logprob(self.linia(text))


def fitxers_kenlm_lemes(directori: Path | str | None = None) -> dict[str, Path]:
    """`{"model", "freq", "sentit"}` de l'opció amb lemes: en `directori`, en
    `AVLIZADOR_KENLM_DIR` o, si no n'hi ha cap, de Hugging Face (el mateix
    repositori i la mateixa revisió que el sistema; només `FITXERS_HF_LEMES`).
    El classificador, el mateix que el del sistema.

    >>> import tempfile
    >>> d = Path(tempfile.mkdtemp())
    >>> {k: v.name for k, v in fitxers_kenlm_lemes(d).items()}
    {'model': 'valencia_net_dogv_lemes_o5.binary', 'freq': 'valencia_net_dogv_lemes_freq.json', 'sentit': 'nb.json'}
    """
    d = directori_kenlm(directori, fitxers=FITXERS_HF_LEMES)
    fitxers = fitxers_kenlm(d)
    return {"model": d / f"{NOM_MODEL_LEMES}_o5.binary", "freq": d / f"{NOM_MODEL_LEMES}_freq.json",
            "sentit": fitxers["sentit"]}


def carrega_sistema_kenlm_lemes(directori: Path | str | None = None):
    """`(ModelKenLMLemes, classificador)` de l'opció amb lemes, o
    `FaltaKenLM` amb el que falta. Necessita spaCy (com el motor)."""
    from importlib.util import find_spec

    if find_spec("kenlm") is None:
        raise FaltaKenLM('Falta el paquet kenlm: pip install "avlizador[kenlm]" (en Linux o Docker).')
    fitxers = fitxers_kenlm_lemes(directori)
    falten = [str(p) for p in fitxers.values() if not p.exists()]
    if falten:
        raise FaltaKenLM(
            "Falten fitxers del model KenLM de lemes: " + ", ".join(falten) + ". Són en el repositori "
            f"de Hugging Face ({REPO_HF}) i es baixen la primera vegada si no hi ha {VAR_DIRECTORI}; amb "
            f"{VAR_DIRECTORI}, posa'ls en eixa carpeta. En Docker, la imatge els porta si es construïx "
            'amb KENLM_LEMES: "1" (docker-compose.yml) o --build-arg KENLM_LEMES=1.')
    import kenlm

    from .lemes import LematitzadorLM, formes_candidates
    from .sentit import carrega_classificador

    freq = json.loads(fitxers["freq"].read_text(encoding="utf-8"))
    model = ModelKenLMLemes(kenlm.Model(str(fitxers["model"])), LematitzadorLM(), freq)
    falten = model.paraules_sense_freq(formes_candidates())
    if falten:
        warnings.warn(f"{len(falten)} paraules candidates no són en {fitxers['freq'].name} ("
                      f"{', '.join(falten[:10])}{'...' if len(falten) > 10 else ''}): regenera-la amb "
                      "freq_unigrames.py.", AvisFreqKenLM, stacklevel=2)
        model._avisades.update(falten)
    return model, carrega_classificador(fitxers["sentit"])
