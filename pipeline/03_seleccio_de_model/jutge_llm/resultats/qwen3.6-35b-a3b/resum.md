## 04/11/2026 15:12 — qwen3.6:35b-a3b, només la traducció (GEMBA-ESA adaptat)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| hdnh2006/salamandra-7b-instruct | 81.28 | 79.45 | 83.41 | 92.69 | 319/458 |
| llama3.1:8b | 80.25 | 78.09 | 82.75 | 91.78 | 333/458 |
| qwen3:14b | 79.57 | 77.83 | 81.59 | 91.92 | 333/458 |
| Sin traducir (catalán tal cual) | 79.22 | 78.17 | 80.44 | 91.8 | 335/458 |
| qwen3:8b | 79.07 | 77.56 | 80.83 | 91.34 | 339/458 |
| gemma4:12b | 78.89 | 76.58 | 81.57 | 91.61 | 333/458 |
| gemma3:12b | 78.83 | 77.61 | 80.24 | 91.36 | 374/458 |
| Referencia valenciana (manual) | 77.0 | 75.16 | 79.14 | 88.89 | 402/458 |
| AVLizador 1.1.0: motor + FLOR-760M (P1) | 76.62 | 74.45 | 79.14 | 87.97 | 405/458 |
| AVLizador: motor + FLOR-760M | 76.61 | 74.43 | 79.14 | 88.0 | 404/458 |
| AVLizador: motor solo | 76.2 | 74.15 | 78.58 | 87.97 | 406/458 |
| qwen2.5:7b | 75.59 | 74.33 | 77.05 | 90.38 | 362/458 |
| qwen2.5:14b | 70.61 | 69.21 | 72.23 | 87.53 | 400/458 |
| mistral-nemo:12b | 70.29 | 68.09 | 72.85 | 83.59 | 392/458 |

### Parells contrastius: valencià (referència) / català (sense traduir)

| Nota | Guanya el valencià | Empat | Guanya el català | Diferència mitjana (val − cat) |
|---|---|---|---|---|
| Fase 2 | 132 | 151 | 175 | -2.22 (n=458) |
| Des dels errors | 89 | 155 | 214 | -2.91 (n=458) |
