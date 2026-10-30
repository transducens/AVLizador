# Baseline cat→val: resultados

Generado: 30/10/2026 12:48 (`baseline_cat_val.py resum`). Instrucción de los LLM (la misma para todos, temperatura 0):

> Traduïx el text següent del català al valencià. Respon només amb la traducció. «frase»

Ordenado por TER (más bajo = mejor). GDV = Grau Dialectal Valencià de la salida (1 = ninguna forma catalana). Limpiadas = respuestas tocadas por el postprocesado mínimo.

## Manual mezcla BOE + AVL (458)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GDV | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|
| AVLizador: motor + FLOR-760M | 227/458 (49,6 %) | 90,88 | 96,34 | 95,92 | 5,61 | 6,01 | 0,9995 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 214/458 (46,7 %) | 90,39 | 96,10 | 95,65 | 5,91 | 6,30 | 0,9981 | 0 | 0 | 0,03 |

## Manual BOE (246)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GDV | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|
| AVLizador: motor + FLOR-760M | 32/246 (13,0 %) | 83,82 | 93,59 | 92,82 | 9,26 | 9,94 | 0,9991 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 32/246 (13,0 %) | 83,53 | 93,46 | 92,66 | 9,50 | 10,15 | 0,9984 | 0 | 0 | 0,03 |

## Manual AVL (212)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GDV | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|
| AVLizador: motor + FLOR-760M | 195/212 (92,0 %) | 99,08 | 99,54 | 99,52 | 0,41 | 0,41 | 1,0000 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 182/212 (85,8 %) | 98,35 | 99,16 | 99,12 | 0,80 | 0,80 | 0,9976 | 0 | 0 | 0,03 |

Ficheros: `avlizador.json`, `motor.json`
