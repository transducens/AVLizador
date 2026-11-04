*[Llegeix en català](README.md)*

# Etapa 3 — Selección del modelo de traducción

Con las reglas dialectales ya definidas (etapa 2), esta etapa decide **qué
modelo** traduce el corpus, comparando varias opciones sobre un benchmark
de 150 frases con referencia humana (`pipeline/03_seleccio_de_model/benchmark_corpus.json`,
sacado del mismo corpus limpio de la etapa 1).

## Herramienta

`pipeline/03_seleccio_de_model/evalua_models.py` — benchmarquea el modelo que le indiques
contra las 150 frases, calculando BLEU/chrF/chrF++ y % de traducciones
exactas; desde el 30/10/2026 también **TER y WER** (de corpus: ediciones /
palabras de la referencia, más bajo = mejor; detalle y resultados en
`documentacio/hoja_de_ruta_benchmark_manual.md`, sección 10). Tabla de
consulta rápida con todas las métricas de cada ejecución cat→val:
[`resultats_benchmarks_cat_val.md`](resultats_benchmarks_cat_val.md).
Para evaluar el sistema final (motor + FLOR-760M) en todos los benchmarks
de una vez: `python avalua_sistema_final.py` (ver el fichero anterior). Uso:

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

Ver `../documentacio/metodologia_i_resultats.md` secciones 3, 5 y 6 para la evolución
completa, la comparativa detallada y los problemas encontrados con cada
modelo.

## Uso actual: medir el traductor catalán → valenciano (23/10/2026)

Desde octubre, `evalua_models.py` se usa sobre todo para medir el motor de
`traductor/`. En catalán → valenciano el benchmark se lee al revés: el
campo `oriental` es la entrada y `occidental`, la referencia.

| opción | qué evalúa |
|---|---|
| `--model traductor --direccio cat-val` | el motor solo (`translate_cat_val`) |
| `--model traductor_ml --direccio cat-val` | el sistema final: motor + modelo de lenguaje para los homógrafos (`traductor/model_llengua/`; necesita `torch` y `transformers`) |
| `--sense-model-irresolubles` | con `traductor_ml`: el modelo solo para "cop/cops" (para comparar) |
| `--model-llengua ID` | con `traductor_ml`: otro modelo de Hugging Face (por defecto FLOR-760M) |

Benchmarks:

| fichero | qué mide |
|---|---|
| `benchmark_corpus.json` (el "151", 154 frases; por defecto) | banco curado; referencia editada por el usuario el 21/10/2026 |
| `benchmark_sistema_final_cat_val.json` (253 frases) | el 151 + 98 frases de homógrafos + 1 de gplsi; se reconstruye con `construeix_benchmark_sistema_final.py` |
| `../../dades/boe/benchmarks/benchmark_boe_dialectal_estricte_complet.json` | regresiones (9.453 pares del BOE con solo diferencias dialectales) |
| `../../dades/boe/benchmarks/benchmark_boe_dialectal_ampli.json` | huecos (2.000 pares del BOE) |
| `../../dades/gplsi_ca_va_alignment_test/benchmark_gplsi.json` | 1.958 pares de dos traductores independientes |

```bash
python evalua_models.py --model traductor --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
python evalua_models.py --model traductor_ml --direccio cat-val --benchmark benchmark_sistema_final_cat_val.json
```

Los resultados se guardan en `resultats/`, con el desglose por el campo
`categoria` de cada frase. **Atención**: si el traductor lanza una
excepción en una frase, el script escribe `ERROR:` y cuenta la frase
original sin traducir; hay que mirar siempre si aparece.
