# Hoja de ruta: reestructuración del repositorio

Documento vivo, lo vamos marcando a medida que se ejecuta cada paso.
Todo esto se hace en la rama `reorganitzacio-repo` (creada desde `main`
el 14/10/2026), nunca directamente en `main` — se hace merge cuando el
usuario esté conforme con el resultado completo.

## Por qué

El repo tiene 9 carpetas numeradas + `traductor/` + `boe/` + `dades/` +
`documentacio/` todas al mismo nivel en la raíz, más un hueco real en la
numeración (no hay "05") y varios ficheros/carpetas sueltos de
exploración puntual acumulados sesión tras sesión. Si esto se hace
público algún día, hoy sería difícil de entender para alguien que llega
sin contexto.

## Decisión de fondo: todo bajo `pipeline/`, con `boe/` cerrando el hueco de numeración

```
traductor/              # el motor real — el PRODUCTO, no una etapa,
                         # se queda fuera de pipeline/ a propósito
pipeline/
  01_extraccio_i_neteja/
  02_regles_dialectals/
  03_seleccio_de_model/
  04_corpus_sintetic/
  05_corpus_boe/         # antes "boe/" suelto en la raíz, sin número
  06_dades_entrenament/
  07_entrenament_de_models/
  08_traduccio_corpus/
  09_index_puresa_dialectal/
dades/                   # transversal, lo consumen varias etapas
documentacio/            # transversal
README.md / README.es.md
```

**Por qué `boe/`→`05_corpus_boe`**: conceptualmente ya es una etapa más
(fuente de datos paralela a `01_extraccio_i_neteja`, justo antes de
`06_dades_entrenament`, que es donde se junta con el resto). Con este
único movimiento, las 7 carpetas que YA tienen número (01,02,03,04,06,
07,08,09) no se tocan ni se renombran — cero riesgo ahí, la secuencia
01-09 queda completa sin huecos.

**Por qué `traductor/` se queda fuera**: no es una etapa de un solo uso,
es el producto final que todas las etapas alimentan. Forzarlo a un "05"
dentro de `pipeline/` sería cosmético y tocaría imports por todo el
código (`from traductor...` en decenas de ficheros) sin ganar nada real.

- [x] Confirmar esta decisión con el usuario antes de mover nada.
- [x] **Ejecutado 14/10/2026**: `boe/` → `pipeline/05_corpus_boe/` y las
      8 carpetas numeradas → `pipeline/` (vía `git mv`/`Move-Item`,
      historial conservado). Todas las rutas hardcodeadas corregidas:
      scripts que subían `parent.parent` para llegar a la raíz (ahora
      necesitan un nivel más, por la carpeta `pipeline/` de por medio),
      `traductor/sync_data.py` (la única ruta funcional real que
      apuntaba a `02_regles_dialectals/`), y las menciones en prosa de
      todos los README (general + los 9 de cada etapa, valencià/català y
      castellano) y en los docstrings de `traductor/`. De paso se
      arregló un import roto en `postprocessat_llm/benchmark_integrat.py`
      que todavía usaba `PreposicionsLocucionsRule` (el módulo que se
      eliminó del motor más temprano hoy). **Verificado**: 536/536
      doctests, val→cat 115/151 y cat→val 116/151 (idénticos a antes del
      movimiento) ejecutados desde las nuevas rutas.

## Limpieza de `02_regles_dialectals/lexic/` (a petición explícita del usuario)

**Verificado antes de proponerlo**: de todo el repo, SOLO
`traductor/sync_data.py` referencia estas rutas (`LEXICO = ARREL /
"02_regles_dialectals" / "lexic"`) — es el único fichero a tocar si se
reestructura esta carpeta.

**Se queda, es la fuente real** (confirmado por `traductor/rules/val_cat/lexic.py`,
docstring "DECISIÓ 30/09/2026": el motor ya es sobre todo diccionario de
Mauricio):
```
lexic/font_mauricio/
  README.md
  acentuacion_limpio.json      -> copiado a traductor/data/lexic_acentuacio_mauricio.json
  conjugaciones_nuevo.json     -> copiado a traductor/data/conjugacions_dialectals.json
  lexico_general_limpio.json   -> copiado a traductor/data/lexic_mauricio.json (via unificado.json)
  numerales_limpio.json        -> copiado a traductor/data/numerals_mauricio.json
  posesivos_cat_val.json       -> copiado a traductor/data/possessius_mauricio.json
  unificado.json
  conjugaciones_limpio.json
  verbos_no_ambiguos.json
  verbos_todos_anotados.json
```

**Candidatos a quitar** (confirmado que el motor real ya NO los usa,
retirados el 30/09/2026 según `val_cat/lexic.py`):
- `lexic/apertium_368_val_cat.json`
- `lexic/contrastius_paula_guerrero.json`
- `lexic/lexico_fiable.json` (el "revisado a mano" que fusionaba todo,
  sustituido por Mauricio puro)
- `lexic/palabras_traducidas.json`
- `fonts/apertium-cat.cat.dix`, `fonts/palabras_traducidas.txt`,
  `fonts/paralelos.txt` (extracciones crudas/intermedias, ya
  superadas por las versiones JSON de `font_mauricio/`)
- `fonts/palabras_val.json` — pendiente de revisar contenido antes de
  decidir (no se ha inspeccionado todavía)

**Ejecutado 14/10/2026** — respuestas del usuario y resultado:
- [x] Aplanar `lexic/font_mauricio/*` → `lexic/*` (elegido). Hecho con
      `git mv`, carpeta `font_mauricio/` eliminada.
- [x] `fonts/regles_cat_val.md` → **eliminarlo, pero se encontró un
      CONFLICTO REAL antes de hacerlo**: `pipeline/05_corpus_boe/analizar_corpus.py`
      lo lee con ruta fija (`cargar_materiales()`, el núcleo del script
      que genera `analitica_corpus.html`). Igual con
      `lexic/palabras_traducidas.json` (cargado vía `_leer_json_materiales()`).
      Avisado al usuario, decisión final: **mantener los 2 ficheros**, no
      se borran — el resto de la limpieza se ejecuta igual.
- [x] `regles_prompt/` → eliminada entera (confirmado sin uso real: la
      única mención en todo el repo era un comentario, no una carga de
      fichero; los 5 ficheros llevaban desde el 01/10 sin tocarse).
- [x] `metrica_puresa_dialectal.md` → eliminado (superado por
      `pipeline/09_index_puresa_dialectal/README.md`, ya implementado y validado).

**Borrado definitivo**: `lexic/apertium_368_val_cat.json`,
`lexic/contrastius_paula_guerrero.json`, `lexic/lexico_fiable.json`,
`fonts/apertium-cat.cat.dix`, `fonts/palabras_traducidas.txt`,
`fonts/paralelos.txt`, `regles_prompt/` (carpeta entera),
`metrica_puresa_dialectal.md`. **Se mantienen**: `fonts/regles_cat_val.md`,
`fonts/palabras_val.json` (confirmado en uso por `analizar_corpus.py`),
`lexic/palabras_traducidas.json` (ídem).

**Efecto secundario aceptado**: `lexico_fiable.json` también lo carga
`evalua_models.py` a nivel de módulo (`LEXIC_PATH`), pero
`carrega_lexic()` ya maneja el fichero ausente con un aviso y estructuras
vacías (no revienta) — solo degrada el modelo "regles" (baseline antiguo
de solo substituciones, ya no es el que se usa de verdad). Confirmado sin
impacto en `--model traductor`, que es el que importa.

**Actualizado tras aplanar**: `traductor/sync_data.py` (`MAURICIO =
LEXICO`) y `postprocessat_llm/identifica_ambigues.py` (mismo cambio), más
las menciones de `font_mauricio/` en los README de `02_regles_dialectals/`
y de `traductor/` (valencià/català y castellano).

**Verificado después**: 536/536 doctests, val→cat 115/151, cat→val
116/151 — sin cambios frente a antes de la limpieza.

## Resto de carpetas — directrices del usuario (pendiente, folder a folder)

- [ ] `01_extraccio_i_neteja/`
- [ ] `03_seleccio_de_model/` (ya sabemos que tiene `resultats/`
      acumulado y un par de scripts sueltos, ver conversación del
      14/10/2026)
- [ ] `04_corpus_sintetic/`
- [ ] `06_dades_entrenament/`
- [ ] `07_entrenament_de_models/`
- [ ] `08_traduccio_corpus/` (ya sabemos que `postprocessat_llm/` tiene
      bastante acumulado de exploración puntual, ver conversación del
      14/10/2026)
- [ ] `09_index_puresa_dialectal/` (ya movidas las pruebas a `proves/`
      el 14/10/2026; quedan sueltos los `informe_*.html`/`resultado_*.json`
      de hoy, regenerables)
- [ ] `dades/` (revisar solapamiento conceptual con `pipeline/05_corpus_boe/`
      una vez movido)
- [ ] `documentacio/`

## Secuencia de ejecución propuesta

1. [x] Confirmar la decisión de fondo (`pipeline/` + `boe/`→`05_corpus_boe`).
2. [x] Mover `boe/` → `pipeline/05_corpus_boe/`.
3. [x] Mover las 8 carpetas numeradas restantes → `pipeline/`.
4. [x] Actualizar referencias de rutas rotas (código + los ~20 README
   afectados) — hecho en el mismo lote que los pasos 2-3, no en un
   commit aparte como se planeó originalmente (resultó más seguro
   arreglar las rutas inmediatamente después de mover, en vez de dejar
   el repo en un estado roto entre commits).
5. [ ] Limpieza de `02_regles_dialectals/lexic/` (una vez resueltos los
   pendientes de arriba) — commit aparte, con verificación de
   doctests+benchmark después.
6. [ ] Carpeta a carpeta, según las directrices que vaya dando el usuario —
   un commit por carpeta o por tanda pequeña, no todo junto.
7. [ ] Revisión final conjunta en la rama.
8. [ ] Merge a `main`.

- [ ] **Pendiente de decidir**: el movimiento + arreglo de rutas de hoy
      (pasos 1-4) todavía no está comiteado en `reorganitzacio-repo` —
      decidir si entra en uno o varios commits antes de seguir
      acumulando más cambios encima.
