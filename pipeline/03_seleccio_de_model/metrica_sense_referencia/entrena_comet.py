"""Llança `comet-train` (unbabel-comet 2.2.7) sense el seu error d'impressió.

`comet.cli.train.initialize_trainer` imprimix els arguments del Trainer amb
`json.dumps(..., default=lambda x: x.__dict__)`. Amb el pytorch-lightning
d'Abaco algun callback guarda una classe, el `__dict__` de la qual és un
`mappingproxy`, i el `print` peta abans d'entrenar (job de prova, 18/11/2026):

    AttributeError: 'mappingproxy' object has no attribute '__dict__'

Ací se substituïx el `json` d'eixe mòdul per un que, si un objecte no es pot
serialitzar, n'escriu el `repr`. L'entrenament és exactament el de
`comet-train` (mateixos arguments de línia d'ordres). Al final escriu el pic
de memòria de la GPU segons PyTorch (el de nvidia-smi inclou la memòria que
PyTorch reserva per avançat):

    python entrena_comet.py --cfg configs/referenceless_complet.yaml --seed_everything 20261118

Treballadors del DataLoader: COMET en posa 2 fixos. En el job del model
complet (18/11/2026) un treballador va morir passades 3,5 hores
(`RuntimeError: could not unlink the shared memory file /torch_...`: algú va
esborrar el fitxer de /dev/shm) i el procés principal es va quedar esperant
el lot per sempre, amb la GPU al 0 %. Per això ací es fan servir 0
treballadors per defecte (el lot es tokenitza en el procés principal, que
costa poc al costat de xlm-roberta-large). Amb `TREBALLADORS=N` se'n poden
posar N, i aleshores un lot que tarda més de 10 minuts fa petar el job en
compte de penjar-lo.
"""
import json
import os

import comet.cli.train as train
import comet.models.base as base
from torch.utils.data import DataLoader

TREBALLADORS = int(os.environ.get("TREBALLADORS", "0"))


class _DataLoaderSegur(DataLoader):
    def __init__(self, *args, **kw):
        kw["num_workers"] = TREBALLADORS
        if TREBALLADORS > 0:
            kw.setdefault("timeout", 600)
        super().__init__(*args, **kw)


base.DataLoader = _DataLoaderSegur


def _per_defecte(x):
    d = getattr(x, "__dict__", None)
    return d if isinstance(d, dict) else repr(x)


class _JsonSegur:
    """`json` amb un `dumps` que no falla mai (només s'usa per a imprimir)."""

    def dumps(self, obj, **kw):
        kw["default"] = _per_defecte
        try:
            return json.dumps(obj, **kw)
        except (TypeError, ValueError):  # referències circulars, etc.
            return repr(obj)

    def __getattr__(self, nom):
        return getattr(json, nom)


train.json = _JsonSegur()

if __name__ == "__main__":
    print(f"Treballadors del DataLoader: {TREBALLADORS}", flush=True)
    train.train_command()
    import torch

    if torch.cuda.is_available():
        mib = 2**20
        print(f"Pic de memòria de la GPU (PyTorch, MiB): assignada {torch.cuda.max_memory_allocated() // mib}, "
              f"reservada {torch.cuda.max_memory_reserved() // mib}, "
              f"total {torch.cuda.get_device_properties(0).total_memory // mib}", flush=True)
