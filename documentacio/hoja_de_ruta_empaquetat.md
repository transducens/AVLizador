# Empaquetado de AVLizador (rama `empaquetat`, 30/10/2026)

Registro de las decisiones y de los cambios para convertir el traductor y
el Grado Dialectal en un paquete instalable. Sirve para pasarlo a
CLAUDE.md al fusionar la rama en `main`. Plan general en
`hoja_de_ruta_entrega_baseline_trazas.md` (sección B).

## Decisiones del usuario (30/10/2026)

1. **Nombre**: distribución e import `avlizador`, con los subpaquetes
   `avlizador.traductor_cat_val` (el traductor; antes `traductor`) y
   `avlizador.grau_dialectal` (GD, GDV y GDC; antes
   `pipeline/09_grau_dialectal/`). El usuario propuso "traductorcatval o
   algo así"; se eligió `traductor_cat_val` (con guiones bajos, norma de
   nombres de Python).
2. **Léxico**: las fuentes se mueven de
   `pipeline/02_regles_dialectals/lexic/diccionarios/` a `dades/lexic/`,
   **fuente única**. Ojo: el compañero que edita el léxico tiene que
   saberlo (antes trabajaba en la ruta vieja; rama `lista-lexico`).
3. **Dirección val→cat fuera del paquete**, de momento: no está en la
   API pública ni en las órdenes. El código (`rules/val_cat/`,
   `translate.py`) sigue dentro porque el GD necesita sus cargadores de
   datos (marcadores valencianos); `pipeline/` lo usa importándolo
   explícitamente (`avlizador.traductor_cat_val.translate`).
4. **Sin FLOR** (sin el extra `[ml]`): `translate_cat_val` usa el motor
   solo y avisa una vez (`AvisSenseModelLlengua`, un `UserWarning`).
5. **Una orden con subórdenes** (lo decidió Claude, el usuario lo dejó a
   su criterio): `avlizador tradueix | gd | gdv | gdc | avalua`.
6. **Licencia**: previsiblemente CC BY 4.0, **por confirmar** (no está en
   `pyproject.toml` ni hay `LICENSE` todavía). Nota: Creative Commons no
   recomienda sus licencias para código; se puede usar CC BY 4.0 para los
   datos y benchmarks y una licencia de software (MIT, Apache-2.0) para
   el código. A decidir.
7. **Benchmarks**: todos en git, también los completos del BOE
   (`dades/benchmarks/`, 28 MB en total).
8. **Benchmark de evaluación**: el manual mezcla (458).

## Estructura

```
pyproject.toml            avlizador 1.0.0, Python >= 3.10, setuptools, diseño src/
src/avlizador/
  __init__.py               API (import perezoso): translate_cat_val, translate_cat_val_motor,
                            calcula_gd, calcula_gdv, calcula_gdc, __version__
  __main__.py, cli.py       orden `avlizador` (también `python -m avlizador`)
  traductor_cat_val/        = traductor/ (rules/, model_llengua/ solo __init__/punts/puntuador, data/)
  grau_dialectal/           gd.py, gdv.py, gdc.py (imports relativos, main(argv))
  avaluacio/                metriques.py (BLEU, chrF, chrF++, TER, WER) + avalua.py
dades/lexic/              fuentes del léxico (git mv desde pipeline/02/.../diccionarios/)
dades/benchmarks/         copias de todos los benchmarks + README
scripts/sync_data.py      (git mv desde traductor/sync_data.py), rutas nuevas
tests/                    test_doctests.py (todos los módulos) + test_api_cli.py
```

### Qué se ha movido fuera del paquete

| Antes | Ahora | Por qué |
|---|---|---|
| `traductor/llm/` | `pipeline/08_traduccio_corpus/postprocessat_llm/capa_llm/` | Necesita Ollama; capa de val→cat congelada y de cat→val retirada |
| `traductor/cli.py` | `.../capa_llm/cli_antic.py` | Sustituida por `avlizador tradueix` (la vieja tenía `--direccio`) |
| `traductor/model_llengua/avalua.py`, `genera_benchmark.py`, `benchmark_homografs_cat_val.json`, `frases_homografs.json` | `pipeline/03_seleccio_de_model/model_llengua/` | Herramientas de evaluación del modelo, no del producto |
| `traductor/sync_data.py` | `scripts/sync_data.py` | Lee las fuentes del repo; no sirve instalado |

### Dependencias (`pyproject.toml`)

- Base: `spacy>=3.8,<3.9` y `ca_core_news_md` 3.8.0 por URL (la wheel
  oficial de spaCy en GitHub). Vale para instalar desde el repo o una
  wheel propia; **PyPI no acepta dependencias por URL** (si algún día se
  publica allí, hará falta otro mecanismo).
- `[ml]`: `torch>=2.2`, `transformers>=4.45`, `huggingface_hub>=0.24,<2.0`.
  Para torch solo CPU: `--extra-index-url https://download.pytorch.org/whl/cpu`.
- `[avaluacio]`: `sacrebleu>=2.4`. `[dev]`: `pytest`, `sacrebleu`.

## Cambios en `pipeline/` (para que siga funcionando)

- Imports `from traductor...` → `from avlizador.traductor_cat_val...` en
  12 scripts (03, 05, 08); `from traductor.llm` → `from capa_llm`
  (`avalua_capa_llm.py` añade su carpeta a `sys.path`).
- GD: `construeix_pool.py` y `mesura_corpus.py` importan
  `avlizador.grau_dialectal.gd`.
- Rutas: `ARREL / "traductor" / "data"` → `src/avlizador/traductor_cat_val/data`
  (`fenomens.py`, `construeix_boe_dialectal.py`); `DIR_ML` de
  `construeix_benchmark_sistema_final.py` → `pipeline/03_seleccio_de_model/model_llengua/`;
  `regenera_palabras_traducidas.py` → `dades/lexic/`.
- `evalua_models.py` importa las métricas de `avlizador.avaluacio.metriques`
  (ya no las define).
- `avalua_sistema_final.py` es ahora una llamada a `avlizador avalua` con
  `--eixida resultats/` (las opciones cambian: `--motor` en vez de
  `--amb-motor`; ficheros `sistema_final_<benchmark>_<fecha>.json` y
  `resum_<fecha>.md`).
- `slurm/baseline_models_llengua.sh`: instala el paquete en editable
  (`pip install --no-deps -e`) y llama a `model_llengua/avalua.py` por su
  ruta nueva.
- **Para trabajar con `pipeline/` hace falta `pip install -e .`** en el
  entorno (hecho el 30/10 en el miniconda del usuario, con `--no-deps`).
- `slurm/evalua_traductor_posfiltre.sh` ya estaba roto antes (usa la
  estructura de `traductor/rules/` anterior al 08/10): no se ha tocado.

## Hallazgos durante el empaquetado

- **Doctest del GD roto en `main` desde el 29/10** (no lo causa el
  empaquetado; comprobado con un worktree de `main`): "Hi ha una manca de
  recursos." ya no da `['manca']`, porque los `lemas` de "manca" dicen
  ahora "manc [adj, n]" y el GD no cuenta nunca un homógrafo cuya
  categoría dialectal comparte otra lectura. Se actualiza el doctest a
  `[]` con la explicación (comportamiento real, no se oculta nada). Los
  648 doctests de antes no incluían el GD.
- `mesura_guia_corpus_oficials_resultats_20261021.txt`
  (`pipeline/02_regles_dialectals/docs_gramatica/`), que el usuario
  quería dejar sin commitear, ya no existía al crear la rama (nunca
  estuvo en git; no lo borró ninguna orden de esta sesión).

## Verificación

- [x] `pytest`: 48 tests, que incluyen **701 doctests** sin fallos.
- [x] **Mismas traducciones que antes**: `avlizador avalua` (10:13)
      frente a `avalua_sistema_final.py` (08:41), frase a frase: **0
      traducciones distintas** en los 8 benchmarks (8.329 frases) y las
      mismas cifras (mezcla 227/458, TER 5,61...). 0 errores.
- [x] **Instalación limpia** en un venv nuevo (Windows, Python 3.13):
      `pip install ".[ml,avaluacio,dev]" --extra-index-url .../whl/cpu`
      instala torch 2.15 CPU, transformers 5.22, huggingface_hub 1.33,
      spaCy 3.8.18 + `ca_core_news_md` 3.8.0 y el paquete; `pytest` contra
      el paquete INSTALADO (no la carpeta `src/`): 48/48; `avlizador
      tradueix`/`gdv` funcionan fuera del repo y `avalua --llista` encuentra
      `dades/benchmarks/` desde la raíz.
- [ ] Abaco (Linux, solo CPU): instalar desde el clon y probar.
- [ ] Revisión del usuario y fusión en `main` (el usuario hace los
      commits).

## Pendiente después de la fusión

- Licencia (`LICENSE` y campo `license` de `pyproject.toml`): **en
  espera** (30/10, decisión del usuario): no se pone ninguna hasta que lo
  decida el grupo. Opciones explicadas: Apache-2.0 o MIT para el código +
  CC BY 4.0 para `dades/` (recomendada), o CC BY 4.0 para todo.
- CLAUDE.md: pasar este registro (rutas nuevas, órdenes nuevas).
- Avisar al compañero del léxico de la ruta nueva (`dades/lexic/`).
- [x] Documentos vivos que citaban `traductor/` (hecho el 30/10, antes de
  fusionar): el README del traductor tiene reescritas las secciones de
  hoy (estructura, uso, resultados del 30/10, sincronizar, añadir datos,
  evaluar, pruebas) y una nota de rutas para la parte histórica; los de
  `rules/` y `model_llengua/` con las rutas y órdenes nuevas;
  `metodologia_i_resultats.md` con una nota de rutas al principio, la
  sección 11 y la subsección "Empaquetado" en la 16. Los históricos
  (informes, CLAUDE_HISTORIAL) se dejan como están, y también
  `dades/benchmarks/boe_dialectal/README_construccio*.md` (copias que no
  se editan a mano; dicen "`traductor/`" en dos sitios).
- Opcional: GitHub Actions con `pytest` en CPU.
