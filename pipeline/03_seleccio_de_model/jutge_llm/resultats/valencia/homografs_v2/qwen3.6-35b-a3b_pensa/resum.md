## 24/11/2026 17:47 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 97.78 | — | — | 99.48 | 10/144 |
| Referencia valenciana (manual) | 96.46 | — | — | 99.24 | 15/144 |
| Motor solo | 87.29 | — | — | 97.08 | 45/144 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 31 | 2 | 22 | 7 | -6.13 |
| Motor solo | 69 | 38 | 29 | 2 | 19.13 |
