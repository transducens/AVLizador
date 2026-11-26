## 25/11/2026 17:42 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia3»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 98.47 | — | — | 99.38 | 39/249 |
| Referencia valenciana (manual) | 98.43 | — | — | 99.68 | 25/249 |
| Motor solo | 95.82 | — | — | 99.01 | 55/249 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 22 | 12 | 8 | 2 | -0.45 |
| Motor solo | 71 | 39 | 24 | 8 | 9.15 |
