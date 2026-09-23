# Reglas pasadas al modelo — documentación para revisión

Esta carpeta reúne, en texto plano fácil de leer, **todo lo que de verdad
se le dice al modelo** al generar el corpus sintético — para poder
revisarlo y detectar errores sin tener que ir a buscar strings de Python
dentro de dos ficheros distintos.

| Fichero | Qué contiene |
|---|---|
| [`guia_dialectal_valencia_catala.md`](guia_dialectal_valencia_catala.md) | **Empieza por aquí.** Documento puramente lingüístico: las diferencias dialectales entre valenciano y catalán explicadas con ejemplos (como un tema de libro), sin nada de código ni de análisis del corpus. La sección 9 (léxico) tiene como base las 368 formas que Apertium marca explícitamente como valencianas (no la lista curada de ~1.600) — de ellas, 68 tienen pareja catalana confirmada dentro del propio diccionario y 3 quedan pendientes de determinar, sin traducción inventada. |
| [`lexic_per_frequencia.md`](lexic_per_frequencia.md) | **Para revisar rápido, usa esto en vez del JSON crudo.** Las 472 palabras del léxico que de verdad se usan en el corpus, ordenadas por cuántas veces aparecen — de más a menos impacto real. Las 1.020 palabras restantes (68% del léxico) no aparecen ni una vez en el corpus actual. |
| [`system_prompt.md`](system_prompt.md) | El system prompt literal (reglas de demostrativos, posesivos, subjuntivo, numerales, léxico base...) tal como se le pasa al modelo, más la regla 8 (siglas/nombres propios) añadida solo para el corpus. |
| [`glossari_dinamic.md`](glossari_dinamic.md) | Cómo se construye la pista `[VOCABULARI: ...]` que se añade a cada frase, las listas de exclusión completas, y la lista de entradas del léxico que colisionan con palabras comunes (con cuáles ya están arregladas y cuáles no). |

## Flujo de trabajo

1. Manda a revisar (o revisa tú mismo) `guia_dialectal_valencia_catala.md`
   — es el documento lingüístico puro, sin referencias a código ni al
   corpus generado.
2. Con las correcciones/confirmaciones en mano, dime qué cambios aplicar
   — se llevan a `evalua_models.carrega_lexic()` (código) y/o a
   `palabras_traducidas.json` (datos), y luego se actualiza también
   `system_prompt.md`/`glossari_dinamic.md` para que esta carpeta no quede
   desactualizada.
3. Si quieres que las correcciones también se apliquen al corpus ya
   generado (no solo a futuras generaciones), se amplía
   `corpus_sinteticos/repara_corpus.py` con las nuevas reversiones. El
   análisis de qué falla en el corpus vive aparte, en
   `corpus_sinteticos/generado/analisi_corpus.html` y en las revisiones
   manuales — no en esta carpeta.

## Relación con el resto del proyecto

- El texto de estos documentos **no se edita aquí** — están copiados de
  `evalua_modelos/evalua_models.py` y `corpus_sinteticos/genera_corpus_sintetico.py`.
  Si decides cambiar una regla, el cambio real se hace en esos ficheros de
  código; vuelve a copiar el texto actualizado aquí después para que esta
  carpeta no quede desactualizada.
- El léxico que usa de verdad el pipeline es
  `../lexico/lexico_fiable.json` (194 entradas revisadas a mano) — ya no
  `palabras_traducidas.json`, que se retiró por tener entradas sin revisar
  de origen poco fiable. Añadir palabras nuevas: `../lexico/anyade_paraula.py`.
- El léxico antiguo (para seguir sacando palabras confirmadas de ahí) y el
  listado combinado más amplio (Apertium + lista curada + léxico del
  corpus) están en `../lexico/` (ver el README general de
  `materiales conversion/`).
- Las reglas morfológicas "de fondo" (de dónde salió el número exacto de
  casos de cada regla) están en `../fuentes/reglas_cat_val.md` — este
  documento nuevo se centra en el prompt y el glosario, no en repetir esa
  tabla.
- La auditoría completa de cuánto se cumple cada regla en el corpus real
  está en `corpus_sinteticos/generado/analisi_corpus.html`.
