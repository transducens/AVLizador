# slurm/ -- qué script usar

Solo quedan 2 scripts activos (08/10/2026, tras limpiar el resto de
herramientas de exploración ya superadas):

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
