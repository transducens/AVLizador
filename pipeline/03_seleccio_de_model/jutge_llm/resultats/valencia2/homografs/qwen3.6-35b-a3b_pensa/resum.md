## 25/11/2026 11:34 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia2»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Referencia valenciana (manual) | 97.63 | — | — | 99.37 | 37/249 |
| Motor + KenLM + sentit | 97.61 | — | — | 99.24 | 39/249 |
| Motor solo | 94.44 | — | — | 98.57 | 57/249 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 22 | 6 | 11 | 5 | 0.23 |
| Motor solo | 71 | 30 | 32 | 9 | 11.2 |
