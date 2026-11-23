"""
prepara_kenlm.py -- Posa els fitxers del model KenLM en /opt/kenlm en construir
la imatge Docker (23/11/2026; abans era una línia de Python dins del
Dockerfile). S'executa dins de la construcció, no fora.

- Opció per defecte (sempre): `valencia_net_dogv_o5.binary`,
  `valencia_net_dogv_freq.json` i `sentit.json` (o `nb.json`).
- Opció amb lemes (`--lemes`, `--build-arg KENLM_LEMES=1`):
  `valencia_net_dogv_lemes_o5.binary` i `valencia_net_dogv_lemes_freq.json`
  (~80 MB més). Sense `--lemes` no s'hi posen, encara que siguen en
  docker/kenlm/.

Cada fitxer es copia de docker/kenlm/ si hi és; els que falten es baixen de
Hugging Face (el mateix repositori, `REPO_HF`, i la revisió del paquet,
`REVISIO_HF`, o la de `--revisio`). Si en falta algun al final, ix amb error
i la construcció s'atura.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from avlizador.traductor_cat_val.model_llengua.kenlm import (FITXERS_HF, FITXERS_HF_LEMES, REPO_HF,
                                                                 REVISIO_HF)

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--origen", type=Path, default=Path("/tmp/docker/kenlm"))
    p.add_argument("--desti", type=Path, default=Path("/opt/kenlm"))
    p.add_argument("--revisio", default="", help="revisió de Hugging Face (per defecte, REVISIO_HF)")
    p.add_argument("--lemes", default="", help="1 = també l'opció amb lemes")
    a = p.parse_args(argv)

    lemes = a.lemes.strip().lower() in ("1", "true", "si", "sí", "yes")
    volguts = list(FITXERS_HF) + ([f for f in FITXERS_HF_LEMES if f not in FITXERS_HF] if lemes else [])
    a.desti.mkdir(parents=True, exist_ok=True)
    for f in volguts + ["nb.json"]:  # nb.json: el classificador antic, si n'hi ha
        if (a.origen / f).is_file() and (a.origen / f).stat().st_size:
            shutil.copy(a.origen / f, a.desti / f)
            print(f"Model KenLM: {f} de docker/kenlm/")
    falten = [f for f in volguts if not (a.desti / f).exists()]
    if falten == ["sentit.json"] and (a.desti / "nb.json").exists():
        falten = []
    if falten:
        from huggingface_hub import snapshot_download

        revisio = a.revisio or REVISIO_HF
        print(f"Model KenLM: {', '.join(falten)} de {REPO_HF} ({revisio})")
        snapshot_download(REPO_HF, revision=revisio, local_dir=str(a.desti), allow_patterns=falten)
        shutil.rmtree(a.desti / ".cache", ignore_errors=True)
    falten = [f for f in volguts if not (a.desti / f).is_file() or not (a.desti / f).stat().st_size]
    if falten == ["sentit.json"] and (a.desti / "nb.json").exists():
        falten = []
    if falten:
        print(f"Falten fitxers del model KenLM: {', '.join(falten)} (vore la capçalera del Dockerfile)",
              file=sys.stderr)
        return 1
    print(f"Model KenLM a {a.desti}: {', '.join(sorted(p.name for p in a.desti.iterdir()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
