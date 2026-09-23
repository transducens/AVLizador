# Corpus sintético paralelo valencià ↔ català — proyecto completo

Proyecto para construir un corpus sintético de pares de frases valencià
occidental (norma AVL/GVA) → català oriental (norma IEC), pensado como base
para entrenar/afinar un modelo de traducción entre las dos variantes.
Esta carpeta organiza y documenta las cuatro etapas del proyecto, cada una
en su propia subcarpeta con su README.

## Empieza por aquí

**[`metodologia_y_resultados.md`](metodologia_y_resultados.md)** — la
historia completa del proyecto en un solo documento: de dónde sale el
texto, cómo se decidieron las reglas, qué modelos se compararon y con qué
resultados, qué bugs se encontraron y cómo se corrigieron, limitaciones
conocidas. Cada etapa de abajo tiene su propio README más corto, enlazado
a la sección correspondiente de este documento para el detalle completo.

## Las etapas

| Etapa | Qué hace | Documentación |
|---|---|---|
| 1 | Scraping de la web de la AVL y limpieza/clasificación dialectal del texto | [`01_scraping_y_limpieza/`](01_scraping_y_limpieza/) |
| 2 | Definición de las reglas dialectales y el léxico diferencial | [`02_reglas_dialectales/`](02_reglas_dialectales/) |
| 3 | Benchmark y selección del modelo de traducción | [`03_seleccion_de_modelo/`](03_seleccion_de_modelo/) |
| 4 | Generación del corpus sintético completo | [`04_corpus_sintetico/`](04_corpus_sintetico/) |
| 5 | Motor de reglas determinista (`traductor/`), alternativa/complemento al LLM | [`05_motor_reglas/`](05_motor_reglas/) |

## Cómo se relaciona esto con el código del repositorio

Los ficheros de esta carpeta son en su mayoría **copias** de los originales
(reglas, léxico, prompts), que se siguen editando en `materiales
conversion/`. Si corriges una regla o el léxico, el cambio real se hace
allí y luego se vuelve a copiar aquí para que esta carpeta no quede
desactualizada. El código en sí (scraping, benchmark, generación del
corpus) no se ha duplicado aquí — vive donde siempre:

```
avl_crawler.py, neteja_corpus.py, estudi_dialectal.py...  (raíz)   → etapa 1
materiales conversion/                                            → etapa 2
evalua_modelos/                                                    → etapa 3
corpus_sinteticos/                                                 → etapa 4
traductor/                                                         → etapa 5
```

La etapa 5 es la única excepción a "esta carpeta son copias": `traductor/`
es un paquete de código nuevo, no una copia de nada — vive solo en la raíz
del repositorio, `final/05_motor_reglas/README.md` es su documentación,
no una copia de sus ficheros.

## Resultado actual

qwen2.5:14b, BLEU 91,08 / chrF 95,34 / chrF++ 95,06 / 50% de traducciones
exactas en el benchmark de 60 frases — ver
[`03_seleccion_de_modelo/`](03_seleccion_de_modelo/) para la comparativa
completa contra otros modelos probados.
