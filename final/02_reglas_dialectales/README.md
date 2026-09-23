# Etapa 2 — Reglas dialectales y léxico

Con el corpus fuente ya limpio (etapa 1), esta etapa define **qué cambia**
entre el valencià occidental (norma AVL/GVA) y el català oriental (norma
IEC): las reglas morfológicas/sintácticas y el léxico diferencial que luego
usa el modelo para traducir (etapa 3-4).

| Fichero | Qué contiene |
|---|---|
| [`reglas_dialectales.md`](reglas_dialectales.md) | **Empieza por aquí.** Las reglas explicadas como un tema de estudio (demostrativos, posesivos, morfología verbal, numerales, gentilicios, sintaxis, léxico diferencial), más un apéndice con la evidencia numérica de cada una. |
| [`lexico_fiable.json`](lexico_fiable.json) | Las 194 parejas de palabras valencià→català confirmadas y revisadas a mano, con su origen documentado. |
| [`system_prompt.md`](system_prompt.md) | El texto **literal** que se le pasa al modelo (prompt base + el añadido solo para el corpus), con la razón e historial de cada regla. |

## Metodología (resumen)

Las reglas se derivaron comparando, dentro del diccionario morfológico de
Apertium (`apertium-cat.cat.dix`), las formas marcadas `v="val_gva"`
(occidental) con sus equivalentes `v="cat"`/`v="val_uni"` (oriental).
Cada patrón se documenta con su **cobertura** (cuántos casos reales lo
siguen) — un patrón con cobertura baja no se convierte en regla general,
se deja como lista cerrada de palabras confirmadas una a una. Dos reglas
salen de fuentes distintas al diccionario, documentadas explícitamente
donde corresponde: el pretèrit perifràstic (de analizar frases completas
del benchmark) y la concordancia de género de "dos/dues" (de normativa
AVL/IEC citada directamente).

Ver `../metodologia_y_resultados.md` sección 2 y 4 para el detalle completo
del proceso.
