# Backup — fuentes retiradas del pipeline en vivo

Ficheros que el traductor usaba antes de pasar a `diccionarios_v1/` como
fuente oficial y que **ya no sincroniza `sync_data.py` ni lee ningún
módulo de `traductor/`**. Se guardan aquí por si hacen falta de vuelta,
nunca se borran directamente.

| Fichero | Qué cubría | Por qué se retiró |
|---|---|---|
| `verbos_no_ambiguos.json` | 261 formas/45 verbos (equipo AVLizador, 30/09/2026) | **19/10/2026**: medido verbo a verbo que ningún infinitivo de una sola palabra falta ya en `diccionarios_v1/conjugaciones_general.json` + `verbos_diferentes_conjugados.json`. Confirmado también con los 4 benchmarks (151 + gplsi, las dos direcciones): cero diferencia al quitarlo. |
| `verbos_todos_anotados.json` | 1.311 formas, análisis detallado de 50 verbos con formas repetidas/ambiguas | Mismo motivo que arriba — su único contenido no cubierto eran frases multi-palabra ("fer una ullada", "donar un cop d'ull"...) que el motor nunca ha podido usar (no hay mecanismo de coincidencia multi-palabra para verbos). |
| `conjugaciones_nuevo.json` | 49.443 formas, 5.465 verbos, generado sistemáticamente | Mismo motivo: 0 infinitivos de una sola palabra sin cubrir ya en las fuentes oficiales; el resto son frases multi-palabra ("llençar la brossa", "fer cara de"...), ruido inservible para el motor actual. |
| `conjugaciones_limpio.json` | 968 formas/111 verbos, el fichero ORIGINAL de Mauricio (29/09/2026) | **19/10/2026**: sus 968 filas, SIN RECORTAR, ya están fusionadas dentro de `diccionarios_v1/conjugaciones_general.json` (IDs `LIMPIO_1`..`LIMPIO_968`) — ver nota de abajo sobre por qué se fusionó el fichero entero y no solo un subconjunto. |
| `posesivos_cat_val.json` | ~~Posesivos febles femenins~~ | **Ya NO está aquí** — se probó retirarlo (19/10/2026) y se revirtió: cuesta -18/-21 frases del benchmark de 151, sigue activo en `lexic/posesivos_cat_val.json`. |

**Por qué `conjugaciones_limpio.json` se fusionó ENTERO (968 filas) y no
solo las 97 que parecían "nuevas"**: la primera comparación (hecha
mirando solo el lookup val→cat) encontró 97 formas reales que faltaban,
sobre todo el paradigma de presente de subjuntivo del verbo "ser"
(`siga/sigui`...) y ~12 verbos enteros (`pertànyer`, `aparèixer`...). Pero
esa comparación tenía un punto ciego: formas de 3ª plural como
`sofrisquen→sofreixin` quedan excluidas del lookup val→cat por el filtro
de riesgo de colisión indicatiu/subjuntiu (`es_risc_mode_3a_plural`), así
que nunca aparecían como "nuevas" desde ese lado — pero sí hacían falta
en bruto para que la dirección cat→val detectara correctamente que
"sofreixin" es ambigua (podría venir de "sofrisquen" o de "patisquen") y
la excluyera. Fusionar solo 97 filas rompió el doctest que comprobaba
justo este caso. La fusión completa de las 968 filas originales evita
este tipo de hueco invisible visto desde una sola dirección. Confirmado
con los 4 benchmarks (151 + gplsi, las dos direcciones): resultados
IDÉNTICOS a cuando el fichero vivía aparte (114/151, 116/151, 1408/1958,
1343/1958).

**Hueco real de datos, pendiente de informar a Mauricio**: el paradigma
completo de presente de subjuntivo del verbo "ser" (`siga/sigues/siga/
siguem/sigueu/siguen`→`sigui/siguis/sigui/siguem/sigueu/siguin`) solo
tenía 3 formas sueltas en `conjugaciones_general.json` antes de esta
fusión (`eres/ets`, `fóra/fos`, `sigut/estat`), ninguna de subjuntivo —
8 de 9 regresiones del benchmark al quitar los 4 ficheros viejos eran
este mismo hueco. Ya está parcheado aquí con las filas fusionadas, pero
sigue siendo un hueco real en la fuente de Mauricio, no un problema de
filtrado de este lado.

Ver `documentacio/hoja_de_ruta_migracio_diccionarios_v1.md` y `CLAUDE.md`
para el detalle completo y la medición exacta.
