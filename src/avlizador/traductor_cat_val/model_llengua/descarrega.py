"""
model_llengua/descarrega.py -- Informació, descàrrega i comprovació dels
fitxers del model KenLM (26/11/2026). És el que fa l'ordre `avlizador
model` i el que ha d'usar qualsevol instal·lació que vulga deixar el model
a punt abans de traduir (per exemple, en construir una imatge Docker),
sense tocar les constants internes de `kenlm.py`.

Cada versió del paquet porta fixada la revisió del model en Hugging Face
(`kenlm.REVISIO_HF`; `AVLIZADOR_KENLM_REVISIO` la canvia). Sempre es baixa
eixa revisió, i la comprovació compara cada fitxer amb el que Hugging Face
diu que hi ha en eixa revisió: la mida i l'empremta (sha256 dels fitxers
grans, guardats amb LFS; sha1 de git dels menuts). Així es detecta, abans
d'usar-la, una còpia local d'una altra revisió (com la taula de
freqüències vella del 13/11 i del 23/11/2026).

On es poden deixar els fitxers:
- sense `desti`: en la memòria cau de Hugging Face, que és on els busca el
  paquet si no hi ha `AVLIZADOR_KENLM_DIR` (per a tindre'ls abans del
  primer ús o per a treballar després sense internet);
- amb `desti`: en una carpeta, per a usar-la amb `AVLIZADOR_KENLM_DIR`
  (com `/opt/kenlm` en la imatge Docker). Cada fitxer s'agafa, per orde, de
  `desti` si ja hi és i és bo, d'`origen` (una carpeta amb còpies locals)
  si és bo, o es baixa de Hugging Face.

Cal `huggingface_hub` (extra `[kenlm]`) per a baixar i per a comprovar;
per a `info_model`, no.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import kenlm as _kenlm
from .kenlm import (FITXERS_HF, FITXERS_HF_LEMES, NOM_MODEL, NOM_MODEL_LEMES, REPO_HF, REVISIO_HF,
                    VAR_DIRECTORI, VAR_REVISIO)

_BLOC = 1 << 20  # es llig d'1 MB en 1 MB: el model en fa 86


class ErrorModel(RuntimeError):
    """No s'ha pogut deixar el model a punt: no es pot baixar ni comprovar,
    o algun fitxer falta o no correspon a la revisió."""


@dataclass(frozen=True)
class Empremta:
    """El que diu Hugging Face d'un fitxer en una revisió: la mida i el
    sha256 (fitxers LFS) o el sha1 de git (la resta)."""

    mida: int
    sha256: str | None = None
    sha1_git: str | None = None

    def correspon(self, cami: Path) -> bool:
        """True si `cami` és este fitxer: mateixa mida i mateixa empremta.

        >>> import tempfile
        >>> p = Path(tempfile.mkdtemp()) / "f.json"
        >>> _ = p.write_bytes(b"hola\\n")
        >>> Empremta(5, sha1_git="5c1b14949828006ed75a3e8858957f86a2f7e2eb").correspon(p)
        True
        >>> Empremta(5, sha256="0" * 64).correspon(p), Empremta(6, sha1_git="x").correspon(p)
        (False, False)
        """
        if not cami.is_file() or cami.stat().st_size != self.mida:
            return False
        if self.sha256:
            return _sha256(cami) == self.sha256
        return _sha1_git(cami) == self.sha1_git


def _sha256(cami: Path) -> str:
    h = hashlib.sha256()
    with cami.open("rb") as f:
        while bloc := f.read(_BLOC):
            h.update(bloc)
    return h.hexdigest()


def _sha1_git(cami: Path) -> str:
    """El sha1 que git dona al contingut del fitxer (`git hash-object`)."""
    h = hashlib.sha1(b"blob %d\0" % cami.stat().st_size)
    with cami.open("rb") as f:
        while bloc := f.read(_BLOC):
            h.update(bloc)
    return h.hexdigest()


def fitxers_model(lemes: bool = False) -> tuple[str, ...]:
    """Els fitxers de l'opció per defecte i, amb `lemes`, també els de
    l'opció amb lemes (`sentit.json` és comú).

    >>> fitxers_model()
    ('valencia_net_dogv_o5.binary', 'valencia_net_dogv_freq.json', 'sentit.json')
    >>> fitxers_model(lemes=True)[3:]
    ('valencia_net_dogv_lemes_o5.binary', 'valencia_net_dogv_lemes_freq.json')
    """
    if not lemes:
        return FITXERS_HF
    return FITXERS_HF + tuple(f for f in FITXERS_HF_LEMES if f not in FITXERS_HF)


def revisio_model() -> str:
    """La revisió del model que usa el paquet: `AVLIZADOR_KENLM_REVISIO` o
    la fixada en esta versió (`REVISIO_HF`)."""
    return os.environ.get(VAR_REVISIO) or REVISIO_HF


def empremtes(fitxers: tuple[str, ...] | list[str], revisio: str | None = None) -> dict[str, Empremta]:
    """La mida i l'empremta de cada fitxer en la revisió, segons Hugging
    Face (cal xarxa). `ErrorModel` si no es pot consultar o hi falta algun."""
    revisio = revisio or revisio_model()
    try:
        from huggingface_hub import HfApi
    except ImportError as e:
        raise ErrorModel('Falta huggingface_hub: pip install "avlizador[kenlm]"') from e
    try:
        info = HfApi().get_paths_info(REPO_HF, list(fitxers), revision=revisio)
    except Exception as e:  # sense xarxa, revisió inexistent...
        raise ErrorModel(f"No s'ha pogut consultar {REPO_HF} (revisió {revisio}) per a comprovar els "
                         f"fitxers: {e}. Sense xarxa: còpies locals sense comprovar (comprova=False, "
                         f"--sense-comprovar amb --origen).") from e
    resultat = {}
    for f in info:
        lfs = getattr(f, "lfs", None)
        resultat[f.path] = Empremta(f.size, sha256=lfs.sha256 if lfs else None,
                                    sha1_git=None if lfs else f.blob_id)
    falten = [f for f in fitxers if f not in resultat]
    if falten:
        raise ErrorModel(f"{REPO_HF} (revisió {revisio}) no té {', '.join(falten)}")
    return resultat


def _baixa(fitxers: list[str], revisio: str, desti: Path | None) -> Path:
    """Baixa els `fitxers` de la revisió: a `desti` o, sense, a la memòria
    cau. Torna la carpeta on són."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise ErrorModel('Falta huggingface_hub: pip install "avlizador[kenlm]"') from e
    try:
        if desti is None:
            return Path(snapshot_download(REPO_HF, revision=revisio, allow_patterns=list(fitxers)))
        snapshot_download(REPO_HF, revision=revisio, allow_patterns=list(fitxers), local_dir=str(desti))
    except Exception as e:
        raise ErrorModel(f"No s'ha pogut baixar {', '.join(fitxers)} de {REPO_HF} (revisió {revisio}): "
                         f"{e}") from e
    shutil.rmtree(desti / ".cache", ignore_errors=True)  # metadades de la descàrrega
    return desti


def _avisa_stderr(missatge: str) -> None:
    print(missatge, file=sys.stderr)


def descarrega_model(desti: Path | str | None = None, *, lemes: bool = False, revisio: str | None = None,
                     origen: Path | str | None = None, comprova: bool = True,
                     avisa: Callable[[str], None] = _avisa_stderr) -> Path:
    """Deixa a punt els fitxers del model i torna la carpeta on són.

    - `desti`: la carpeta on deixar-los (per a `AVLIZADOR_KENLM_DIR`); sense,
      la memòria cau de Hugging Face, on els busca el paquet per defecte.
    - `lemes`: també els de l'opció amb lemes (`--model kenlm-lemes`).
    - `revisio`: per defecte, la del paquet (`revisio_model()`).
    - `origen`: carpeta amb còpies locals que s'usen en lloc de baixar-les,
      si corresponen a la revisió (només amb `desti`).
    - `comprova`: comparar cada fitxer amb la mida i l'empremta de Hugging
      Face (cal xarxa). Sense comprovar, un fitxer que ja és en `desti` o
      en `origen` s'accepta tal com està.

    `ErrorModel` si al final falta algun fitxer o no correspon a la revisió.
    `avisa` rep un missatge per cada pas (per defecte, a l'eixida d'errors).
    """
    fitxers = fitxers_model(lemes)
    revisio = revisio or revisio_model()
    refs = empremtes(fitxers, revisio) if comprova else None

    def bo(cami: Path) -> bool:
        if not cami.is_file() or not cami.stat().st_size:
            return False
        return refs is None or refs[cami.name].correspon(cami)

    if desti is None:
        if origen is not None:
            raise ErrorModel("`origen` només té sentit amb `desti`: la memòria cau la gestiona Hugging Face.")
        avisa(f"Model KenLM: {', '.join(fitxers)} de {REPO_HF} (revisió {revisio[:12]}) a la memòria cau")
        carpeta = _baixa(list(fitxers), revisio, None)
    else:
        carpeta = Path(desti)
        carpeta.mkdir(parents=True, exist_ok=True)
        origen = Path(origen) if origen else None
        falten = []
        for f in fitxers:
            if bo(carpeta / f):
                avisa(f"Model KenLM: {f} ja és en {carpeta}")
                continue
            if origen is not None and (origen / f).is_file():
                if bo(origen / f):
                    shutil.copy2(origen / f, carpeta / f)
                    avisa(f"Model KenLM: {f} copiat de {origen}")
                    continue
                avisa(f"Model KenLM: el {f} de {origen} no correspon a la revisió {revisio[:12]}; es baixa")
            (carpeta / f).unlink(missing_ok=True)  # si n'hi havia un de dolent, que no el reaprofite
            falten.append(f)
        if falten:
            avisa(f"Model KenLM: {', '.join(falten)} de {REPO_HF} (revisió {revisio[:12]})")
            _baixa(falten, revisio, carpeta)

    dolents = [f for f in fitxers if not bo(carpeta / f)]
    if dolents:
        raise ErrorModel(f"Després de la descàrrega, {', '.join(dolents)} falta o no correspon a la revisió "
                         f"{revisio} en {carpeta}")
    return carpeta


def _on_es(directori: Path | str | None) -> tuple[Path | None, str | None]:
    """On busca el paquet els fitxers, sense baixar res: `directori`,
    `AVLIZADOR_KENLM_DIR` o la memòria cau de Hugging Face."""
    if directori:
        return Path(directori), "argument"
    if os.environ.get(VAR_DIRECTORI):
        return Path(os.environ[VAR_DIRECTORI]), VAR_DIRECTORI
    cau = _kenlm._directori_hf(descarrega=False, fitxers=FITXERS_HF)
    return (cau, "memoria_cau") if cau else (None, None)


def comprova_model(directori: Path | str | None = None, *, lemes: bool = False,
                   revisio: str | None = None) -> dict[str, str]:
    """L'estat de cada fitxer de la carpeta que usaria el paquet (o de
    `directori`): `"bo"`, `"falta"` o `"no correspon"` a la revisió. Cal
    xarxa (`ErrorModel` si no es pot consultar Hugging Face)."""
    fitxers = fitxers_model(lemes)
    refs = empremtes(fitxers, revisio)
    carpeta, _ = _on_es(directori)
    estat = {}
    for f in fitxers:
        cami = carpeta / f if carpeta else None
        if cami is None or not cami.is_file():
            estat[f] = "falta"
        else:
            estat[f] = "bo" if refs[f].correspon(cami) else "no correspon"
    return estat


def info_model(directori: Path | str | None = None) -> dict:
    """Quin model usa esta versió del paquet, on el trobaria i si està a
    punt. No baixa res ni va a la xarxa.

    Claus: `versio_paquet`, `repo`, `revisio`, `revisio_del_paquet` (True
    si no l'ha canviada `AVLIZADOR_KENLM_REVISIO`), `nom`, `nom_lemes`,
    `directori` (o None si no hi ha cap carpeta amb el model), `lloc`
    (`"argument"`, `"AVLIZADOR_KENLM_DIR"`, `"memoria_cau"` o None),
    `fitxers` ({nom: hi és}), `kenlm_installat`, `huggingface_hub_installat`,
    `disponible` (es pot traduir amb el model per defecte) i
    `lemes_disponible` (també amb l'opció amb lemes).

    >>> import tempfile
    >>> d = Path(tempfile.mkdtemp())
    >>> i = info_model(d)
    >>> i["nom"], i["lloc"], i["disponible"], sum(i["fitxers"].values())
    ('valencia_net_dogv', 'argument', False, 0)
    """
    from importlib.util import find_spec

    from ... import __version__

    carpeta, lloc = _on_es(directori)
    fitxers = {f: bool(carpeta and (carpeta / f).is_file() and (carpeta / f).stat().st_size)
               for f in fitxers_model(lemes=True)}
    kenlm_installat = find_spec("kenlm") is not None
    revisio = revisio_model()
    return {
        "versio_paquet": __version__,
        "repo": REPO_HF,
        "revisio": revisio,
        "revisio_del_paquet": revisio == REVISIO_HF,
        "nom": NOM_MODEL,
        "nom_lemes": NOM_MODEL_LEMES,
        "directori": str(carpeta) if carpeta else None,
        "lloc": lloc,
        "fitxers": fitxers,
        "kenlm_installat": kenlm_installat,
        "huggingface_hub_installat": find_spec("huggingface_hub") is not None,
        "disponible": kenlm_installat and all(fitxers[f] for f in FITXERS_HF),
        "lemes_disponible": kenlm_installat and all(fitxers[f] for f in FITXERS_HF_LEMES),
    }
