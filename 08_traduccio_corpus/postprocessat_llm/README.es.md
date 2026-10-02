*[Read it in Catalan](README.md)*

# Post-procesado con LLM de los casos marcados (PENDIENTE -- no implementado)

Esta carpeta todavía no contiene código. Documenta la decisión de
arquitectura tomada el 02/10/2026: en vez de forzar al motor de reglas a
resolverlo TODO (arriesgado -- cada vez que se ha probado una heurística
automática demasiado amplia en este proyecto, desde el escaneo de género
en `flexio_genere_avl.json` hasta la distinción "per"/"per a", el
resultado ha sido peor que no tocarlo), el plan es dividir el problema en
dos:

1. **El motor de reglas (`traductor/`) traduce y, de paso, marca** los
   puntos donde no tiene suficiente confianza -- sin intentar
   adivinarlos.
2. **Un LLM revisa SOLO esos puntos marcados**, con el contexto de la
   frase y las guías de `../../02_regles_dialectals/docs_gramatica/`
   (GEIEC/GNV completas + las comparativas dialectales derivadas) como
   referencia normativa -- no toda la frase desde cero, como hacen las
   etapas 3-4 con el corpus sintético actual.

## Por qué así y no de otra manera

La alternativa (un LLM que revisa/corrige la frase entera) ya existe en
este proyecto: es exactamente lo que hacen las etapas 3-4
(`03_seleccio_de_model/`, `04_corpus_sintetic/`) con qwen2.5:14b. Ese
enfoque funciona razonablemente bien (BLEU ~93) pero **alucina** -- la
revisión manual encontró ~20% de errores reales sin relación con ninguna
regla dialectal (ver `../../documentacio/metodologia_i_resultats.md`,
secciones 6 y 9). El interés de un motor de reglas es precisamente que no
puede alucinar: si no sabe una palabra, no la toca. Mantener esa
propiedad implica que el LLM solo debe intervenir donde el motor lo pida
explícitamente, no sobre el texto entero.

## Lo que falta decidir antes de escribir ningún código

- **Formato de la marca**: a nivel de `Token` (añadir un campo como
  `necessita_revisio: bool` o `candidat_regla: str | None` a la clase
  `Token` de `traductor/rules/__init__.py`), a nivel de frase entera, o
  ambos. Todavía no decidido -- no tocar `Token` hasta que se decida.
- **Qué reglas etiquetan y cuándo**: por ejemplo, una futura regla para
  "per"/"per a" podría NO decidir, y en vez de eso marcar el token "per"
  como candidato cuando detecte el patrón ambiguo (ver
  `traductor/README.es.md`, sección "DECISIÓN DE ARQUITECTURA" 02/10/2026,
  para los 3 casos ya identificados como demasiado arriesgados para una
  regla directa).
- **Qué modelo**: local vía Ollama (coherente con el resto del proyecto,
  qwen2.5:14b ya en uso) u otro -- pendiente de probar coste/calidad
  sobre una muestra pequeña de casos marcados antes de elegir.
- **El LLM propone o solo señala**: si la salida del LLM sustituye
  directamente el texto marcado, o si solo genera un informe para
  revisión humana (más lento, pero sin riesgo de alucinación silenciosa
  sobre datos ya marcados como dudosos).

## Cómo continuar cuando se retome

1. Decidir el formato de marca y añadirlo a `Token` + a, al menos, una
   regla real (candidato natural: la distinción "per"/"per a" documentada
   en `docs_gramatica/guia_traduccio_dialectal.md`, bloque C2).
2. Ejecutar `../traduccio_massiva.py` sobre un corpus real y contar
   cuántos puntos quedan marcados -- eso da una primera idea del volumen
   real antes de elegir modelo ni diseñar el prompt.
3. Probar el LLM elegido sobre una muestra pequeña de los puntos
   marcados, mismo método que el resto del proyecto: evidencia antes que
   implementación completa.
