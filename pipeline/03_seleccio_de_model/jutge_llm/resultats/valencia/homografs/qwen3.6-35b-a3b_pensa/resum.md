## 25/11/2026 08:12 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Referencia valenciana (manual) | 97.97 | — | — | 99.54 | 27/249 |
| Motor + KenLM + sentit | 97.75 | — | — | 99.24 | 30/249 |
| Motor solo | 94.8 | — | — | 98.59 | 46/249 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 22 | 5 | 12 | 5 | 2.5 |
| Motor solo | 71 | 24 | 45 | 2 | 11.13 |
