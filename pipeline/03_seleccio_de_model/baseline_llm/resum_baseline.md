# Baseline cat→val: resultados

Generado: 02/11/2026 09:04 (`baseline_cat_val.py resum`). Instrucción de los LLM (la misma para todos, temperatura 0):

> Traduïx el text següent del català al valencià. Respon només amb la traducció. «frase»

Ordenado por TER (más bajo = mejor). Grau dialectal de la salida, calculado sobre todas las frases del conjunto:

- **GD** = formas valencianas / (valencianas + catalanas): de 0 (catalán) a 1 (valenciano). Es la medida que más separa: solo cuenta las palabras con marca dialectal.
- **GDV** = 1 − formas catalanas / palabras: 1 = no queda ninguna forma catalana.
- **GDC** = 1 − formas valencianas / palabras: cuanto más bajo, más formas valencianas (1 = ninguna).

La fila *Referencia* da los valores del valenciano de referencia, el objetivo. Limpiadas = respuestas tocadas por el postprocesado mínimo.

## Manual mezcla BOE + AVL (458)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GD | GDV | GDC | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *Referencia (valenciano)* | — | — | — | — | — | — | *0,9973* | *0,9998* | *0,9182* | — | — | — |
| AVLizador: motor + FLOR-760M | 227/458 (49,6 %) | 90,88 | 96,34 | 95,92 | 5,61 | 6,01 | 0,9936 | 0,9995 | 0,9189 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 214/458 (46,7 %) | 90,39 | 96,10 | 95,65 | 5,91 | 6,30 | 0,9764 | 0,9981 | 0,9194 | 0 | 0 | 0,03 |
| Sin traducir (catalán tal cual) | 1/458 (0,2 %) | 69,25 | 87,97 | 86,21 | 15,76 | 16,08 | 0,0264 | 0,9200 | 0,9978 | 0 | 0 | 0,00 |
| gemma3:12b | 11/458 (2,4 %) | 70,54 | 87,46 | 85,93 | 16,13 | 16,72 | 0,3889 | 0,9530 | 0,9701 | 0 | 0 | 1,27 |
| llama3.1:8b | 1/458 (0,2 %) | 68,32 | 87,55 | 85,73 | 16,28 | 16,69 | 0,0601 | 0,9239 | 0,9951 | 0 | 1 | 0,75 |
| gemma4:12b | 1/458 (0,2 %) | 67,49 | 87,06 | 85,23 | 16,88 | 17,22 | 0,0564 | 0,9273 | 0,9957 | 0 | 1 | 1,03 |
| qwen3:8b | 1/458 (0,2 %) | 66,86 | 86,88 | 84,97 | 17,23 | 17,57 | 0,0382 | 0,9227 | 0,9969 | 0 | 4 | 0,89 |
| qwen3:14b | 2/458 (0,4 %) | 66,83 | 86,81 | 84,89 | 17,32 | 17,83 | 0,0435 | 0,9227 | 0,9965 | 0 | 3 | 1,40 |
| qwen2.5:7b | 1/458 (0,2 %) | 63,57 | 85,36 | 83,23 | 19,50 | 19,85 | 0,0372 | 0,9242 | 0,9971 | 0 | 4 | 9,74 |
| qwen2.5:14b | 0/458 (0,0 %) | 59,04 | 82,96 | 80,57 | 22,55 | 22,93 | 0,0975 | 0,9325 | 0,9927 | 0 | 17 | 1,44 |
| mistral-nemo:12b | 1/458 (0,2 %) | 59,35 | 82,89 | 80,52 | 22,86 | 23,40 | 0,1263 | 0,9365 | 0,9908 | 0 | 3 | 0,85 |
| hdnh2006/salamandra-7b-instruct | 4/458 (0,9 %) | 57,77 | 79,50 | 77,61 | 26,06 | 27,14 | 0,1517 | 0,9359 | 0,9885 | 0 | 0 | 0,62 |

## Manual BOE (246)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GD | GDV | GDC | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *Referencia (valenciano)* | — | — | — | — | — | — | *0,9951* | *0,9996* | *0,9222* | — | — | — |
| AVLizador: motor + FLOR-760M | 32/246 (13,0 %) | 83,82 | 93,59 | 92,82 | 9,26 | 9,94 | 0,9886 | 0,9991 | 0,9232 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 32/246 (13,0 %) | 83,53 | 93,46 | 92,66 | 9,50 | 10,15 | 0,9790 | 0,9984 | 0,9231 | 0 | 0 | 0,03 |
| gemma3:12b | 0/246 (0,0 %) | 66,57 | 86,46 | 84,56 | 18,83 | 19,73 | 0,3538 | 0,9519 | 0,9737 | 0 | 0 | 1,27 |
| Sin traducir (catalán tal cual) | 0/246 (0,0 %) | 61,79 | 85,71 | 83,30 | 20,16 | 20,70 | 0,0000 | 0,9213 | 1,0000 | 0 | 0 | 0,00 |
| gemma4:12b | 0/246 (0,0 %) | 61,54 | 85,49 | 83,08 | 20,49 | 21,06 | 0,0291 | 0,9278 | 0,9978 | 0 | 0 | 1,03 |
| llama3.1:8b | 0/246 (0,0 %) | 61,21 | 85,38 | 82,95 | 20,59 | 21,26 | 0,0181 | 0,9241 | 0,9986 | 0 | 1 | 0,75 |
| qwen3:8b | 0/246 (0,0 %) | 60,34 | 85,00 | 82,49 | 21,28 | 21,84 | 0,0033 | 0,9226 | 0,9997 | 0 | 2 | 0,89 |
| qwen3:14b | 0/246 (0,0 %) | 60,46 | 85,03 | 82,52 | 21,30 | 22,11 | 0,0065 | 0,9226 | 0,9995 | 0 | 1 | 1,40 |
| qwen2.5:7b | 0/246 (0,0 %) | 57,83 | 83,49 | 80,85 | 23,34 | 23,88 | 0,0135 | 0,9258 | 0,9990 | 0 | 2 | 9,74 |
| qwen2.5:14b | 0/246 (0,0 %) | 54,42 | 81,66 | 78,82 | 25,84 | 26,42 | 0,0766 | 0,9340 | 0,9945 | 0 | 9 | 1,44 |
| mistral-nemo:12b | 0/246 (0,0 %) | 54,02 | 81,68 | 78,70 | 26,43 | 27,17 | 0,0993 | 0,9363 | 0,9930 | 0 | 1 | 0,85 |
| hdnh2006/salamandra-7b-instruct | 0/246 (0,0 %) | 53,61 | 78,75 | 76,35 | 28,55 | 29,90 | 0,0835 | 0,9329 | 0,9939 | 0 | 0 | 0,62 |

## Manual AVL (212)

| Sistema | Exactas | BLEU | chrF | chrF++ | TER ↓ | WER ↓ | GD | GDV | GDC | Errores | Limpiadas | s/frase |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *Referencia (valenciano)* | — | — | — | — | — | — | *1,0000* | *1,0000* | *0,9125* | — | — | — |
| AVLizador: motor + FLOR-760M | 195/212 (92,0 %) | 99,08 | 99,54 | 99,52 | 0,41 | 0,41 | 1,0000 | 1,0000 | 0,9127 | 0 | 0 | 0,53 |
| AVLizador: motor solo | 182/212 (85,8 %) | 98,35 | 99,16 | 99,12 | 0,80 | 0,80 | 0,9732 | 0,9976 | 0,9142 | 0 | 0 | 0,03 |
| Sin traducir (catalán tal cual) | 1/212 (0,5 %) | 77,90 | 90,59 | 89,58 | 9,50 | 9,50 | 0,0605 | 0,9182 | 0,9947 | 0 | 0 | 0,00 |
| llama3.1:8b | 1/212 (0,5 %) | 76,58 | 90,07 | 88,97 | 10,16 | 10,18 | 0,1142 | 0,9238 | 0,9902 | 0 | 0 | 0,75 |
| qwen3:8b | 1/212 (0,5 %) | 74,42 | 89,07 | 87,85 | 11,46 | 11,50 | 0,0842 | 0,9228 | 0,9929 | 0 | 2 | 0,89 |
| qwen3:14b | 2/212 (0,9 %) | 74,22 | 88,86 | 87,63 | 11,66 | 11,73 | 0,0919 | 0,9227 | 0,9922 | 0 | 2 | 1,40 |
| gemma4:12b | 1/212 (0,5 %) | 74,40 | 88,88 | 87,72 | 11,75 | 11,75 | 0,0926 | 0,9265 | 0,9925 | 0 | 1 | 1,03 |
| gemma3:12b | 11/212 (5,2 %) | 75,15 | 88,63 | 87,51 | 12,29 | 12,43 | 0,4354 | 0,9546 | 0,9650 | 0 | 0 | 1,27 |
| qwen2.5:7b | 1/212 (0,5 %) | 70,24 | 87,52 | 85,99 | 14,04 | 14,11 | 0,0677 | 0,9220 | 0,9943 | 0 | 2 | 9,74 |
| mistral-nemo:12b | 1/212 (0,5 %) | 65,53 | 84,29 | 82,62 | 17,78 | 18,03 | 0,1626 | 0,9368 | 0,9877 | 0 | 2 | 0,85 |
| qwen2.5:14b | 0/212 (0,0 %) | 64,40 | 84,46 | 82,59 | 17,87 | 17,98 | 0,1244 | 0,9304 | 0,9901 | 0 | 8 | 1,44 |
| hdnh2006/salamandra-7b-instruct | 4/212 (1,9 %) | 62,60 | 80,37 | 79,08 | 22,50 | 23,22 | 0,2418 | 0,9402 | 0,9809 | 0 | 0 | 0,62 |

Ficheros: `avlizador.json`, `copia.json`, `motor.json`, `ollama_gemma3-12b.json`, `ollama_gemma4-12b.json`, `ollama_hdnh2006-salamandra-7b-instruct.json`, `ollama_llama3.1-8b.json`, `ollama_mistral-nemo-12b.json`, `ollama_qwen2.5-14b.json`, `ollama_qwen2.5-7b.json`, `ollama_qwen3-14b.json`, `ollama_qwen3-8b.json`
