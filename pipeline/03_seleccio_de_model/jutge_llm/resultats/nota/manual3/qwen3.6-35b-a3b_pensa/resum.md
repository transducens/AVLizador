## 26/11/2026 12:19 — qwen3.6:35b-a3b, només la nota, una petició per text (prompt «nota»)

| Sistema | Nota (fase 2) | BOE | AVL | Nota des dels errors | Frases amb error |
|---|---|---|---|---|---|
| Sin traducir (catalán tal cual) | 99.85 | 100.0 | 99.67 | — | 0/458 |
| Motor + KenLM + sentit | 99.53 | 99.29 | 99.8 | — | 0/458 |
| Referencia valenciana (manual) | 98.29 | 96.92 | 99.87 | — | 0/458 |

### Parells contrastius: valencià (referència) / català (sense traduir)

| Nota | Guanya el valencià | Empat | Guanya el català | Diferència mitjana (val − cat) |
|---|---|---|---|---|
| Fase 2 | 4 | 388 | 66 | -1.56 (n=458) |

### Cada sistema contra la referència (frases on la traducció és distinta, nota de la fase 2)

| Sistema | Frases distintes | Guanya la referència | Empat | Guanya el sistema | Diferència mitjana (ref − sistema) |
|---|---|---|---|---|---|
| Motor + KenLM + sentit | 226 | 9 | 160 | 57 | -2.51 |
| Sin traducir (catalán tal cual) | 457 | 4 | 387 | 66 | -1.56 |
