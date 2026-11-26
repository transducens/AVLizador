## 26/11/2026 08:50 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia_va»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 95.25 | — | — | 99.25 | 5/20 |
| Referencia valenciana (manual) | 87.5 | — | — | 98.12 | 8/20 |
| Motor solo | 78.5 | — | — | 96.38 | 10/20 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 5 | 0 | 2 | 3 | -31.0 |
| Motor solo | 10 | 4 | 5 | 1 | 18.0 |
