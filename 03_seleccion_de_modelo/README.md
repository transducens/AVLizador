# Etapa 3 — Selección del modelo de traducción

Con las reglas dialectales ya definidas (etapa 2), esta etapa decide **qué
modelo** traduce el corpus, comparando varias opciones sobre un benchmark
de 150 frases con referencia humana (`03_seleccion_de_modelo/benchmark_corpus.json`,
sacado del mismo corpus limpio de la etapa 1).

## Herramienta

`03_seleccion_de_modelo/evalua_models.py` — benchmarquea el modelo que le indiques
contra las 150 frases, calculando BLEU/chrF/chrF++ y % de traducciones
exactas. Uso:

```bash
python evalua_models.py --model ollama --ollama-model qwen2.5:14b
```

## Resultado final (con las reglas y el léxico ya maduros)

| Modelo | BLEU | chrF | chrF++ | Exactos |
|---|---|---|---|---|
| **qwen2.5:14b** (elegido) | **91,08** | **95,34** | **95,06** | **30/60 (50,0%)** |
| salamandra-7b-instruct (BSC) | 86,29 | 93,62 | 93,17 | 19/60 (31,7%) |
| Sistema de reglas deterministas (sin LLM) | 80,5-85,9 | 91,3-95,5 | 90,3-94,5 | — |
| NLLB-200-distilled-600M | 53,13 | 76,67 | 75,00 | 0/60 |
| llama3.1:8b | 57,2-73,6 | 69,3-85,7 | 68,2-84,7 | — |
| qwen2.5:7b | 72,0-77,8 | 85,7-89,0 | 84,8-88,1 | — |

**Por qué qwen2.5:14b**: mejor calidad y más consistente entre ejecuciones,
con margen de mejora claro según se afinaba el prompt (subió de 84,02 a
91,08 BLEU sin cambiar nunca de modelo — toda la ganancia vino de mejorar
el prompt y el léxico a partir de analizar los errores reales). Se probó
también salamandra-7b-instruct por ser la mitad de parámetros (más barato
de ejecutar); llegó a estar casi empatada en un punto intermedio, pero
resultó ser un modelo más frágil ante cambios de prompt — a veces empeoraba
en vez de mejorar al añadirle más reglas explícitas.

Ver `../metodologia_y_resultados.md` secciones 3, 5 y 6 para la evolución
completa, la comparativa detallada y los problemas encontrados con cada
modelo.
