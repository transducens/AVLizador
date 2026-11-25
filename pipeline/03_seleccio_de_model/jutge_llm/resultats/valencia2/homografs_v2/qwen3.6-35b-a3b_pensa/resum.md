## 25/11/2026 09:55 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia2»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 96.91 | — | — | 99.46 | 12/144 |
| Referencia valenciana (manual) | 95.0 | — | — | 99.11 | 20/144 |
| Motor solo | 86.46 | — | — | 97.03 | 61/144 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 31 | 1 | 19 | 11 | -8.87 |
| Motor solo | 69 | 45 | 22 | 2 | 17.83 |
