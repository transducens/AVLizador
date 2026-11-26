## 25/11/2026 16:52 — qwen3.6:35b-a3b, amb l'original i la norma valenciana (prompt «valencia3»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Referencia valenciana (manual) | 93.37 | — | — | 98.94 | 43/144 |
| Motor + KenLM + sentit | 92.4 | — | — | 98.19 | 71/144 |
| Motor solo | 89.27 | — | — | 98.39 | 37/144 |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 31 | 27 | 3 | 1 | 4.52 |
| Motor solo | 69 | 30 | 12 | 27 | 8.55 |
