## 09/11/2026 13:02 — Unbabel/XCOMET-XL (fp16, mode qe)

| Sistema | Mescla | BOE | AVL | Frases amb error |
|---|---|---|---|---|
| qwen3:14b | 97.12 | 97.75 | 96.39 | 196/458 |
| hdnh2006/salamandra-7b-instruct | 97.11 | 97.98 | 96.09 | 185/458 |
| llama3.1:8b | 97.09 | 97.7 | 96.37 | 193/458 |
| Sin traducir (catalán tal cual) | 97.04 | 97.66 | 96.32 | 184/458 |
| AVLizador: motor + FLOR-760M | 97.0 | 97.49 | 96.43 | 284/458 |
| gemma4:12b | 96.98 | 97.51 | 96.38 | 238/458 |
| AVLizador 1.1.0: motor + FLOR-760M (P1) | 96.98 | 97.49 | 96.4 | 285/458 |
| qwen3:8b | 96.95 | 97.43 | 96.39 | 209/458 |
| AVLizador: motor solo | 96.91 | 97.42 | 96.32 | 291/458 |
| gemma3:12b | 96.87 | 97.49 | 96.14 | 259/458 |
| Referencia valenciana (manual) | 96.82 | 97.07 | 96.52 | 280/458 |
| qwen2.5:7b | 95.72 | 96.31 | 95.03 | 274/458 |
| mistral-nemo:12b | 95.39 | 96.11 | 94.55 | 319/458 |
| qwen2.5:14b | 93.56 | 94.04 | 93.0 | 356/458 |

Parells contrastius, referència valenciana − català sense traduir: guanya el valencià en 91, empat (±0,5) en 175, guanya el català en 192; diferència mitjana -0.22 (n=458).
