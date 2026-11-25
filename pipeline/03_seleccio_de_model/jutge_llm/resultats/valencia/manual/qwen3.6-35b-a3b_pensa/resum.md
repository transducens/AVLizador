## 25/11/2026 08:12 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Sin traducir (catalán tal cual) | 99.25 | 99.76 | 98.66 | 99.8 | 28/458 |
| Motor + KenLM + sentit | 97.72 | 97.09 | 98.44 | 99.12 | 98/458 |
| Referencia valenciana (manual) | 94.64 | 91.18 | 98.63 | 97.76 | 159/457 |
| gemma3:12b | 94.17 | 94.71 | 93.54 | 97.78 | 171/458 |

### Parells contrastius: valencià (referència) / català (sense traduir)

| Nota | Guanya el valencià | Empat | Guanya el català | Diferència mitjana (val − cat) |
|---|---|---|---|---|
| Fase 2 | 18 | 264 | 175 | -4.61 (n=457) |
| Des dels errors | 18 | 288 | 151 | -2.04 (n=457) |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 225 | 22 | 100 | 103 | -6.24 |
| Sin traducir (catalán tal cual) | 456 | 18 | 263 | 175 | -4.62 |
| gemma3:12b | 446 | 120 | 202 | 124 | 0.5 |
