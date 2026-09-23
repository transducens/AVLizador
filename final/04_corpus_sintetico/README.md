# Etapa 4 — Generación del corpus sintético

Última etapa: con el modelo elegido (qwen2.5:14b, etapa 3) y las reglas ya
maduras (etapa 2), se traduce frase a frase todo el corpus fuente limpio
(etapa 1) para producir el corpus paralelo valencià→català final.

Los scripts de esta etapa viven en `corpus_sinteticos/` (no se han copiado
aquí, son el motor activo del proyecto):

| Fichero | Qué hace |
|---|---|
| `corpus_sinteticos/genera_corpus_sintetico.py` | Segmenta el corpus fuente en frases, las traduce reutilizando el motor de `evalua_modelos/evalua_models.py`, y exporta el corpus limpio |
| `corpus_sinteticos/repara_corpus.py` | Corrige bugs conocidos sobre un corpus ya generado, sin volver a traducir nada |
| `corpus_sinteticos/slurm/` | Scripts `sbatch` para generar en el clúster con GPU (mucho más rápido que en CPU local) |
| `corpus_sinteticos/README.md` | Instrucciones de uso completas |

## Cómo se segmenta y filtra el texto

- División por frases con heurística de puntuación (respeta abreviaturas
  como "Sr.", "art.", "núm.").
- Se descartan frases de menos de 5 palabras/20 caracteres (ruido) y de
  más de 280 caracteres (para no arriesgar que la respuesta del modelo se
  corte a mitad).
- Deduplicación exacta por contenido.

## Estado actual

- **v1** (generada con el léxico y prompt anteriores a esta ronda de
  mejoras): 46.315 frases, auditada por completo — ver
  `corpus_sinteticos/generado/` y `../metodologia_y_resultados.md`
  sección 6 para los bugs encontrados y corregidos.
- **v2** (pendiente/en curso): regeneración completa con qwen2.5:14b, el
  léxico de 194 entradas y todas las reglas nuevas (BLEU 91,08 en el
  benchmark de la etapa 3). Es la versión que hay que usar una vez termine
  — actualiza esta sección y `../metodologia_y_resultados.md` sección 7
  cuando esté lista.

## Fichero final a usar (una vez generado)

```
corpus_sinteticos/generado/parallel_val_cat.jsonl
```

Formato `{"val": "...", "cat": "..."}`, una pareja por línea, sin ninguna
marca de sospecha — listo para entrenar/afinar un modelo de traducción.
