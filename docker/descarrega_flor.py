"""Descarrega FLOR-760M dins de la imatge Docker (opció A de la secció 7.2
de `documentacio/hoja_de_ruta_interfaz_docker.md`: la imatge funciona
sense internet). S'executa en construir la imatge, no en arrancar-la.

    python descarrega_flor.py <revisió>

Fixa la revisió (el *commit* de Hugging Face) perquè la imatge siga
reproduïble i la versió de NOTICE coincidisca amb la de dins. Com que
`translate_cat_val` carrega el model sense dir cap revisió (és a dir,
`main`), s'escriu `refs/main` apuntant a eixa revisió: així, amb
`HF_HUB_OFFLINE=1`, transformers el troba en la memòria cau sense eixir a
internet.
"""

import sys
from pathlib import Path

from huggingface_hub import snapshot_download

MODEL = "projecte-aina/FLOR-760M"
revisio = sys.argv[1]
cami = Path(snapshot_download(MODEL, revision=revisio,
                              allow_patterns=["*.json", "*.txt", "*.safetensors"]))
commit = cami.name
refs = cami.parent.parent / "refs"
refs.mkdir(parents=True, exist_ok=True)
(refs / "main").write_text(commit, encoding="utf-8")
print(f"{MODEL} @ {commit}: {', '.join(sorted(f.name for f in cami.iterdir()))}")
