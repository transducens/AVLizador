# `traductor/llm/` — capa de postprocesado con LLM (val→cat)

*[Llegeix-ho en valencià](README.md)*

Capa **opcional** solo para valenciano→catalán. Desde el 21/10/2026 está
**congelada**: funciona y mejora al motor, pero no se sigue mejorando. Los
errores que tiene están catalogados abajo para retomarla más adelante.

`traductor.translate()` y `traductor.translate_cat_val()` **no la usan**:
sin Ollama ni GPU todo funciona igual. Las herramientas que se entregan
(traductor cat→val e IPD, para la Conselleria, solo CPU) no la necesitan.

## Qué hace

El motor deja sin traducir las formas verbales que el valenciano escribe
igual en indicativo y subjuntivo (3ª persona del plural, "creuen"; y 1ª
persona del singular, "realitze"). Para cada una, el LLM elige una
etiqueta cerrada: `indicatiu`, `subjuntiu` o `cap` (no tocar). Si no
responde o responde algo no válido, se queda la salida del motor. Antes de
consultar, spaCy descarta las formas que no son verbo en la frase.

- `val_cat.py`: detección de los puntos y prompt. El prompt es una **copia
  literal** de la vía C original (`pipeline/08_traduccio_corpus/postprocessat_llm/compara_postprocessat.py`),
  la que dio 129/151 con `qwen3:8b`; no cambiarlo sin volver a medir.
- `client.py`: cliente de Ollama con etiquetas cerradas.
- `punts.py`: estructura común (`PuntAmbigu`, `resol`).

```python
from traductor.llm import ClientLLM, tradueix_val_cat
text, punts = tradueix_val_cat("Vull que creuen el carrer.", ClientLLM("qwen3:8b"))
```

## Resultados (Abaco, `qwen3:8b`, 21/10/2026)

| Benchmark | Frases exactas | BLEU | Acierto en los puntos de modo verbal |
|---|---|---|---|
| 151 | 100 → **109** (+9, ninguna perdida) | 96,13 → 96,80 | motor 27/44 → **LLM 37/44** |
| BOE, 2.000 líneas | 396 → **406** (+12, −2) | 75,01 → 75,90 | motor 82/416 (20%) → **LLM 294/416 (71%)** |

En el BOE el LLM acierta 229 puntos que el motor fallaba y estropea 17 que
el motor acertaba. El salto en frases exactas es pequeño porque la versión
valenciana del BOE reformula mucho. ~1.000 consultas tardan del orden de
minutos en GPU (~0,14 s por consulta); en CPU, ~8 s por consulta.

## Catálogo de errores (para retomarla)

Los 122 puntos del BOE donde el LLM se equivoca (17 que estropea + 105 en
los que fallan los dos):

| # | Error | Casos BOE | Ejemplo | Tipo de solución posible |
|---|---|---|---|---|
| 1 | **Relativo normativo tratado como real** → elige indicativo donde va subjuntivo | 70 | "realitzades per treballadors **que disposen** de la qualificació" (= cualquier trabajador que la tenga) | Criterio de registro legal en el prompt: en una norma, el relativo con antecedente genérico es hipotético |
| 2 | **Relativo real tratado como normativo** → elige subjuntivo donde va indicativo | 11 | "les societats **que es fusionen**" (sociedades concretas) | El mismo criterio, con contraejemplos |
| 3 | **1ª persona con "indicatiu" sin sujeto "jo"** → genera formas agramaticales ("realitzo", "presento") | 18 (y 0 casos del BOE donde el indicativo fuera correcto) | "Quan la cessió es **realitze**" → "es realitzo" | **Sin LLM**: en las formas de 1ª persona, "indicatiu" solo si el sujeto es "jo"; si no, subjuntivo o no tocar |
| 4 | **"quan" de condición futura** → indicativo donde va subjuntivo | 6 | "quan els béns **tinguen** el seu origen…" | El criterio ya lo cubre; el modelo no lo aplica en frases largas |
| 5 | **"si" + subjuntivo** → subjuntivo donde la gramática exige indicativo | 2 | "si en **disposen**", "Si les causes… **afecten**" | **Sin LLM**: tras "si" condicional, el presente siempre es indicativo |
| 6 | Frases largas sin conjunción cerca del verbo | 17 | "les quals **tinguen** participació majoritària" | Más contexto o un modelo mayor |

En el benchmark de 151 hay 4 pérdidas ("opten", "gustaren": relativos
reales tomados por hipotéticos, el error 2) y 3 fallos de los dos
("gaudisquen vostés", fórmula de cortesía en subjuntivo; "tinguen").

Los errores 3 y 5 son reglas gramaticales, no de significado: se pueden
corregir en el código sin tocar el modelo. El 1 y el 2 (81 de 122) son el
núcleo y dependen de entender el registro legal.

## Por qué ya no hay capa para cat→val

Se construyó (21/10/2026) para "aquest" → "este"/"eixe" y para la
combinación "l'hi" (B4), y se retiró el mismo día tras evaluarla en Abaco:

- "aquest": en la prueba el LLM cambió 4 de 5 a "eixe" y acertó 1, cuando
  el motor ("este" por defecto) acertaba los 5. En el BOE "eixe" también es
  anafórico ("en eixe cas", "dins d'eixe termini") igual que "este" en el
  151: es estilo, sin señal en la frase. "este" por defecto ya acierta el
  94,5% (BOE) y el 100% (151).
- B4: 0 casos en las 2.000 líneas del BOE y en los 151.
- Con los dos tipos activos o con solo B4, el motor + LLM daba exactamente
  la misma salida que el motor en las 2.154 frases (151 + BOE).

El análisis de B4 (cuatro lecturas de "l'hi" en el BOE) sigue documentado
en `documentacio/hoja_de_ruta_traductor_invers.md`.

## Evaluación

`pipeline/08_traduccio_corpus/postprocessat_llm/avalua_capa_llm.py`
(`--sense-llm` solo cuenta puntos) y, en Abaco, `slurm/avalua_capa_llm.sh`.
