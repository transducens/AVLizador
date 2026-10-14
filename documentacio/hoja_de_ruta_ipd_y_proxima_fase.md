> **⚠️ FICHERO RECONSTRUIDO el 14/10/2026** tras un borrado accidental
> del original. El fichero nunca estuvo en git (salía como `??` en
> `git status`), así que no hay ningún historial del que recuperarlo, y
> tampoco estaba en la papelera de reciclaje de Windows. A diferencia de
> `hoja_de_ruta_traductor_invers.md`, de este fichero **no se leyó
> ningún fragmento literal durante la sesión del 14/10/2026** — esta
> versión es una reconstrucción basada ENTERAMENTE en los resúmenes de
> `CLAUDE.md`, bastante más corta e incompleta que el original. Trátala
> como un índice de lo que se sabe que contenía, no como el documento en
> sí — el redactado original, los ejemplos concretos y buena parte del
> razonamiento intermedio se han perdido.

# Hoja de ruta: IPD y próxima fase

Plan de 3 pasos, en el orden exacto que pidió el usuario:

1. **Índice de Puresa Dialectal (IPD)** primero — una métrica propia
   (ratio de ocurrencias de formas occidentales sobre el total de
   ocurrencias marcadas), reemplazando el enfoque basado en reglas de
   `estudi_dialectal.py` por uno basado en el índice de palabras del
   traductor, usable sobre cualquier documento o corpus.
2. Después, incorporar una capa de modelo (LLM) para cat→val, solo una
   vez cerrados los huecos arreglables del benchmark.
3. Por último, probar con un dataset distinto del benchmark de 151 (el
   BOE, identificado como candidato).

## Paso 1 — HECHO (13/10/2026)

Implementado como hito propio del proyecto, etapa 9:
`09_index_puresa_dialectal/ipd.py` + README.md (valencià) + README.es.md
(castellano) — ver esos ficheros para el detalle técnico completo
(fórmula, fuentes de datos, limitaciones conocidas), que SÍ siguen
existiendo y no se han perdido.

Resumen de lo más importante:
- Reutiliza directamente los `carrega_*`/`carrega_*_invers` de
  `traductor/rules/val_cat/` y `cat_val/` (lexic, demostratius,
  numerals, possessius) más un loader propio y más estricto para las
  conjugaciones (`_carrega_conjugacions_pures`), en vez de mantener
  listas de palabras curadas a mano como hacía `estudi_dialectal.py`.
- **Dos bugs reales encontrados y corregidos la misma tarde** (a raíz de
  que el usuario desconfiara del número viendo el informe `--html`,
  concretamente con "aquestes"): (1) sin filtro de categoría gramatical,
  formas verbales raras colisionaban con palabras comunes ("entre",
  "poden", "base"...); (2) el prefijo elidido ("d'aquestes" nunca casaba
  con la entrada "aquestes" porque el tokenizador trata el apóstrofo
  como parte de la palabra).
- Validado contra el benchmark de 151 frases: IPD 0,9339 en el lado
  valenciano, 0,0153 en el catalán.
- Confirmado a mayor escala con el corpus del BOE y, más tarde
  (14/10/2026), con el dataset `gplsi/CA-VA_alignment_test` (1.958
  frases): mismo patrón en los tres corpus independientes.
- Se dejó como módulo/CLI independiente, sin tocar `estudi_dialectal.py`
  directamente, para no arriesgar la etapa 1 ya estable.

> **Nota 14/10/2026**: el Paso 1 se siguió ampliando después de escrito
> este resumen — validación contra el dataset gplsi, un filtrado del
> corpus por IPD para separar sinonimia de fallos reales del motor, y 4
> bugs reales nuevos encontrados en el propio diccionario del traductor
> (no en el IPD) gracias a esa validación. Todo esto está documentado
> con mucho más detalle y de primera mano en `CLAUDE.md` — es la fuente
> más completa y fiable a partir de esa fecha, más que este documento
> reconstruido.

## Paso 2 — pendiente

Incorporar una capa de modelo (LLM) para cat→val, una vez cerrados los
huecos arreglables del benchmark de reglas. Ver el estado real de esto
(aparcado a petición del usuario el 14/10/2026, con la decisión de usar
`qwen3` en vez de `qwen2.5:14b` al retomarlo) en `CLAUDE.md`, sección
"Pendiente".

## Paso 3 — parcialmente hecho

Probar con un dataset distinto del benchmark de 151: se hizo el
14/10/2026 con `gplsi/CA-VA_alignment_test` (Hugging Face, CC BY 4.0,
1.958 frases) en vez de con el BOE que se había identificado como
candidato original — ver `CLAUDE.md` para los resultados completos
(IPD, benchmark de traducción completo y filtrado, análisis de fallos).
El BOE a gran escala (el corpus `corpus_entrenamiento.jsonl` completo,
~268.000 líneas) sigue sin probarse del todo.
