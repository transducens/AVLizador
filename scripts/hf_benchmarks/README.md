# Benchmarks d'AVLizador en Hugging Face

Prepara cada benchmark com un dataset de Hugging Face (dades en JSONL,
fitxa `README.md`, `LICENSE`, `NOTICE` i bàner) en `dades/hf_benchmarks/<nom>/`
(fora de git). No publica res: la pujada la fa l'usuari.

| Script | Dataset (repo per defecte) | Frases |
|---|---|---|
| `manual.py` | `transducens/avlizador-manual-ca-va` | 458: 246 del BOE + 212 de l'AVL (`--sense-avl`: només el BOE) |
| `homografs.py` | `transducens/avlizador-homographs-ca-va`, un dataset amb dos configuracions: `v2` (per defecte) i `v1` (l'únic amb cop/cops) | 160 / 98 |
| `boe_dialectal.py` | `transducens/avlizador-boe-strict-ca-va`, `…-boe-broad-ca-va` | 2.000 + 9.453 / 2.000 + 73.705 |

```bash
python scripts/hf_benchmarks/manual.py --repo ORG/avlizador-manual-ca-va
python scripts/hf_benchmarks/homografs.py --repo ORG/avlizador-homographs-ca-va
python scripts/hf_benchmarks/boe_dialectal.py --org ORG
```

- **Llicència**: Apache 2.0 (decisió de l'usuari, 09/11/2026), autors
  Mauricio González Arcas i Nicolás Martín Morcillo.
- **BOE**: l'avís legal del BOE permet reutilitzar i modificar citant
  "Basado en datos de la Agencia Estatal Boletín Oficial del Estado" amb
  enllaç, la data i marcant els canvis: va en la fitxa, en el `NOTICE` i
  en cada frase (document, data, enllaç i, en el manual, l'original quan
  es va corregir a mà).
- **AVL**: des del 12/11/2026 el manual porta també les 212 frases de
  l'AVL, citant-ne l'origen en la fitxa i en el `NOTICE`.
- `boe_dialectal.py` necessita `dades/boe/corpus_entrenamiento.jsonl`
  (document i data de cada parell).
