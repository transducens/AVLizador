# slurm/ -- qué script usar

3 scripts activos (08/10/2026):

- **`evalua_traductor_posfiltre.sh`** -- SOLO CPU, sin Ollama/GPU,
  ~15 min. Doctests + `evalua_models.py --model traductor` únicamente.
  Usar ANTES DE HACER COMMIT cuando el cambio es solo en `traductor/`
  (no toca `postprocessat_llm/`) y no hace falta medir el postprocesado
  LLM — mucho más rápido que `genera_resultats_complet.sh` para este caso.
  Revisar la cabecera del script para la lista de ficheros a subir (varía
  según qué se haya tocado).
  ```
  sbatch evalua_traductor_posfiltre.sh
  ```

- **`genera_resultats_complet.sh`** -- uso normal, "¿cómo va todo?".
  Doctests + motor solo + motor con postprocessat LLM, en un solo job,
  guardando los resultados con nombre FIJO (`ULTIM_NOMES_MOTOR.json`,
  `ULTIM_MOTOR_MES_LLM.json`) para comparar sesión a sesión.
  ```
  sbatch genera_resultats_complet.sh                  # qwen3:8b, via C, benchmark complet
  sbatch genera_resultats_complet.sh qwen3:14b b 30    # un atre model/via, nomes 30 frases
  ```

- **`benchmark_integrat_posfiltre.sh`** -- uso puntual, "¿por qué falla
  esta frase concreta?". Soporta `--debug` (log completo del prompt y
  la respuesta de Ollama) y `--ids RCxxx` (solo esa frase).
  ```
  sbatch benchmark_integrat_posfiltre.sh qwen3:8b c "" --ids RC151 --debug
  ```

`archivo/` guarda herramientas de exploración ya cerradas (comparativa
de vías A/B/C, baseline de 3 modelos en paralelo) -- se conservan por si
hace falta repetir ese tipo de comparación, pero no son el flujo normal.

`logs/` guarda los `.out`/`.err` de jobs ya lanzados.
