# Baseline cat→val: AVLizador frente a LLM y Apertium

Pregunta: ¿mejora nuestro sistema (motor + FLOR-760M) lo que ya existe?
Se compara con LLM generalistas **tal cual** y con Apertium, en el
benchmark de evaluación, el **manual mezcla** (458 frases), y en sus dos
partes, BOE (246) y AVL (212). Cada sistema traduce la mezcla una vez; las
tablas del BOE y de la AVL salen de las mismas traducciones.

## Condiciones (decisión del usuario, 30/10/2026)

- **Sin ajustar nada a los LLM**: la misma instrucción mínima para todos,
  sin ejemplos, reglas ni glosario, temperatura 0:
  > Traduïx el text següent del català al valencià. Respon només amb la traducció. «frase»
- Postprocesado mínimo e igual para todos (`neteja_resposta`): quita
  líneas de presentación ("Ací tens la traducció:"), una etiqueta
  "Traducció:" y las comillas que envuelven toda la respuesta, y se queda
  la primera línea. La respuesta cruda se guarda (`hipotesi_crua`).
- Métricas: exactas, BLEU, chrF, chrF++, TER y WER (las de
  `avlizador.avaluacio`) y el **GDV de la salida**: si un sistema
  devuelve catalán o mezcla, el GDV baja aunque el BLEU sea alto.

## Sistemas

| Sistema | Dónde |
|---|---|
| AVLizador: motor + FLOR-760M (sistema principal) y motor solo | local, CPU |
| llama3.1:8b, qwen2.5:7b, qwen2.5:14b, qwen3:8b, qwen3:14b, gemma3:12b, gemma4:12b, salamandra-7b-instruct (`hdnh2006/salamandra-7b-instruct`), mistral-nemo:12b | Abaco, Ollama, 1 GPU por modelo, como mucho 2 a la vez |
| Apertium **vía castellano** (`cat-spa` + `spa-cat_valencia`) | API pública (`--apertium-mode apy`) o `apertium` local con los dos pares instalados |

Apertium no tiene ningún par catalán → valenciano (comprobado el 30/10 en
la API pública: el valenciano solo es destino desde el castellano y el
inglés; en Abaco está `apertium` pero ningún par del catalán). Se usa
la vía castellano (decisión del usuario): son dos traducciones completas,
no un cambio dialectal, así que **no es una comparación directa** y en la
tabla figura como "vía castellano". La respuesta cruda guarda también el
castellano intermedio.

**Apertium, fuera del baseline de momento (decisión del usuario,
30/10/2026)**: la API pública devolvía error 500 en todas las
traducciones (también en pares sin relación, como inglés → castellano),
y en Abaco no hay ningún par del catalán instalado. El código sigue en el
script (`--sistema apertium`, se para tras 5 frases seguidas sin
respuesta) por si se retoma.

## Cómo se ejecuta

```bash
# nuestros sistemas (local)
python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema avlizador
python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema motor

# LLM (Abaco, desde esta carpeta del clon, con el venv ~/venvs/avlizador)
LIMIT=10 sbatch --array=0 baseline_llm_cat_val.sh   # prueba con 10 frases
sbatch baseline_llm_cat_val.sh                      # los 9 modelos, 2 a la vez

# Apertium vía castellano (apy envía las frases a apertium.org)
python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py tradueix --sistema apertium --apertium-mode apy

# tabla final
python pipeline/03_seleccio_de_model/baseline_llm/baseline_cat_val.py resum
```

Resultados: `resultats/<sistema>.json` (cada frase con la traducción, la
respuesta cruda y las métricas) y `resum_baseline.md` (las tres tablas).
Las pruebas con `--limit` no entran en el resumen ni en git.
