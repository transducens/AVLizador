*[Llegeix en català](README.md)*

# Corpus sintético paralelo valenciano → catalán

Genera un corpus de pares de frases (valenciano original / catalán sintético)
para entrenar o afinar un modelo de traducción occidental↔oriental.

## Fuente y modelo

- **Fuente**: `dades/avl/final/dialectal/corpus_occidental_net.jsonl` — no el
  `unified.jsonl` general, sino el subconjunto que `estudi_dialectal.py` ya
  filtró y verificó como valenciano puro (1.778 documentos, 821K tokens, sin
  contaminación de textos orientales). Traducir desde aquí en vez del corpus
  completo evita enseñarle al modelo pares donde el "original" ya estaba en
  catalán.
- **Modelo**: `qwen2.5:14b` vía Ollama local, con el mismo system prompt y el
  mismo glosario dinámico por frase que `03_seleccio_de_model/evalua_models.py`
  (BLEU 90,87 / chrF 95,86 / chrF++ 95,55 en el benchmark del 17/09/2026, con
  el léxico de 194 entradas y las reglas de pretérito perifrástico/instituciones/
  elisión ya añadidas) — la mejor configuración probada hasta ahora. Comparado
  también con salamandra-7b-instruct (BSC) — ver
  `../documentacio/metodologia_y_resultados.md` sección 5 para la comparativa completa.
- **Diferencia respecto al benchmark**: el benchmark traduce frases sueltas
  sin nombres de instituciones. Al aplicarlo a texto real de la AVL se
  detectó que el modelo "traducía" siglas (`AVL` → `IEC`), un error factual,
  no dialectal. Este script añade una regla extra al system prompt (solo
  aquí, sin tocar `evalua_models.py`) para que `AVL`, `GVA`, `GNV`, `GVB` y
  `RACV` se queden siempre intactas, y marca como sospechoso cualquier par
  donde esto falle igualmente.

## Uso

```bash
# Prueba rápida (10 frases, para comprobar que Ollama responde bien)
python genera_corpus_sintetico.py --limit 10 --verbose

# Muestra aleatoria de N frases (para evaluar calidad antes del run largo)
python genera_corpus_sintetico.py --sample 500

# Generación completa — reanudable con Ctrl+C y volver a lanzar el mismo comando
python genera_corpus_sintetico.py

# Regenerar solo los ficheros limpios de exportación (sin volver a traducir nada)
python genera_corpus_sintetico.py --nomes-exporta
```

Parámetros más relevantes (`--help` para la lista completa):

| Parámetro | Por defecto | Para qué sirve |
|---|---|---|
| `--model` | `qwen2.5:14b` | Modelo de Ollama |
| `--ollama-url` | `http://localhost:11434` | URL del servidor Ollama (cámbiala para apuntar a un Ollama remoto, p.ej. un nodo GPU — ver `slurm/README.md`) |
| `--ollama-timeout` | 300 | Segundos de espera por petición |
| `--max-caracters` | 280 | Frases más largas se descartan (evita cortes en la respuesta) |
| `--sample N` / `--limit N` | — | Muestra aleatoria / las N primeras, mutuamente excluyentes |
| `--incloure-sospitosos` | no | Incluye en la exportación limpia también los pares marcados |
| `--num-shards N` / `--shard-id I` | 1 / 0 | Reparte el corpus en N fragmentos (para N GPUs a la vez) — ver `slurm/generar_corpus_paralelo.sh` |
| `--merge-shards N` | — | Fusiona los N fragmentos en el fichero final (no traduce nada) |

## ⚠️ Tiempo de ejecución (lee esto antes de lanzarlo todo)

Esta máquina **no tiene GPU** (Ollama carga qwen2.5:14b entero en CPU).
Con una prueba real de 5 frases, el ritmo estable es **~30-60 s/frase**.

El corpus fuente contiene **46.315 frases únicas**. A los ritmos medidos:

| Alcance | Tiempo estimado |
|---|---|
| 200 frases (prueba) | ~2-3 horas |
| 8.000 frases (muestra grande) | ~3-6 días continuos |
| 46.315 frases (corpus completo) | **~16-32 días continuos** |

El script es totalmente **reanudable**: cada frase se guarda (append + flush)
justo después de traducirse, así que se puede interrumpir con Ctrl+C en
cualquier momento y volver a lanzar el mismo comando — no repite ninguna
frase ya hecha.

### Ejecutarlo en GPU (recomendado para el corpus completo)

Con GPU, el mismo qwen2.5:14b suele ir de 10 a 30 veces más rápido que en
CPU (unos 9-10 GB de VRAM), lo que convertiría las ~3 semanas estimadas
arriba en el orden de 1-2 días. `--ollama-url` permite apuntar a un Ollama
que corre en otro sitio. Ya hay un script preparado:

- `slurm/` — scripts `sbatch` para el clúster GPU de la universidad: túnel
  SSH para probarlo, un job autónomo con 1 GPU, y otro que reparte el
  corpus entre **todas las GPU libres a la vez** (`--num-shards`) si el
  clúster tiene varias en la misma máquina — con 8 GPU libres, esto
  puede convertir 1-2 días en unas pocas horas. Detalles completos en su
  README.

## Salida

```
dades/sintetico/
├── corpus_sintetic_val_cat.jsonl   # Fichero principal: todos los pares + metadatos + calidad
├── parallel_val_cat.jsonl          # Exportación limpia {"val", "cat"} (sin sospechosos)
├── parallel.val / parallel.cat     # Lo mismo, en 2 ficheros alineados línea a línea (formato Moses/OPUS)
├── generacio.log                   # Log completo con timestamp
└── informe_generacio.txt           # Resumen: pares por tipo de documento, sospechosos, tiempo
```

## Estado del corpus generado

- **v1** (léxico y prompt anteriores a esta ronda de mejoras): 46.315
  frases, auditada por completo — ver `dades/sintetico/` y
  `../documentacio/metodologia_y_resultados.md` sección 6 para los bugs
  encontrados y corregidos.
- **v2**: regeneración con el léxico de 194 entradas y todas las reglas
  maduras — es la versión que hay que usar una vez esté lista. Fichero
  final: `dades/sintetico/parallel_val_cat.jsonl` (formato
  `{"val": "...", "cat": "..."}`, una pareja por línea, listo para
  entrenar).

`corpus_sintetic_val_cat.jsonl` guarda, por cada frase única: el texto
valenciano, la traducción, el documento de origen (`doc_id`, `source_url`,
`doc_type`), cuántas veces aparecía la frase en el corpus original
(`n_ocurrencies`) y una lista `motius_sospita` (vacía si todo parece
correcto). Motivos posibles:

- `buit` — el modelo no ha devuelto nada
- `fuga_prompt` — el bloque `[VOCABULARI: ...]` ha aparecido en la respuesta
- `possible_explicacio` — parece que ha añadido una nota en vez de traducir
- `longitud_anormal` — la traducción es mucho más corta o larga que el original
- `no_traduit` — el original tenía marcadores occidentales claros y la traducción es idéntica
- `entitat_alterada` — una sigla de institución (AVL, GVA...) ha desaparecido
- `instruccio_filtrada` — el literal «Frase a traduir:» (parte del prompt) ha aparecido filtrado en la respuesta
- `sigla_introduida` — el modelo se ha inventado una sigla que no estaba en el original (p.ej. "l'Acadèmia" → "l'AVL")
- `possible_glitch` — fragmento de palabra duplicado justo después de una elisión (p.ej. "M'm-interessa"), un tipo de ruido de generación visto en texto largo

Los pares sospechosos **no se descartan** del fichero principal (por si quieres
revisarlos tú mismo); simplemente quedan fuera de `parallel_val_cat.jsonl` y
de los ficheros `.val`/`.cat`, que son los pensados para entrenamiento.

**Estos filtros no lo atrapan todo.** Son heurísticos baratos (regex, longitud,
palabras clave) pensados para detectar los errores más frecuentes y evidentes —
no sustituyen una revisión humana. En una prueba con 10 frases reales se
detectaron errores ortográficos sutiles (p.ej. pérdida de un acento: "àmbit" →
"ambit") que ningún heurístico actual capta. Para un corpus que quieras usar
para entrenar, es recomendable revisar a mano una muestra antes de
confiar en él ciegamente, sobre todo si has subido mucho `--max-caracters`.
