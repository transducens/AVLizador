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
  `avlizador.avaluacio`) y el **grau dialectal de la salida** (GD, GDV y
  GDC; desde el 02/11, antes solo el GDV). Si un sistema devuelve catalán
  o mezcla, lo muestran aunque el BLEU sea alto:
  - **GD** = formas valencianas / (valencianas + catalanas), de 0
    (catalán) a 1 (valenciano). Es el que más separa: solo cuenta las
    palabras con marca dialectal.
  - **GDV** = 1 − formas catalanas / palabras: cuánto catalán **queda**.
  - **GDC** = 1 − formas valencianas / palabras: cuánto valenciano
    **aparece** (más bajo = más formas valencianas).

  El GDV solo no basta: divide entre todas las palabras, casi todas
  neutras, y una salida que reformula con palabras neutras sube sin haber
  puesto ninguna forma valenciana. Se calculan de las traducciones
  guardadas (`resum` los recalcula siempre) y la tabla incluye una fila
  con los valores de la referencia.

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
Las pruebas con `--limit` no entran en el resumen ni en git. `--sistema
copia` devuelve el catalán sin tocar: es el umbral que un sistema tiene
que superar.

## Resultados (02/11/2026; job 2578 en Abaco, 0 errores)

Manual mezcla (458). Tablas completas, también del BOE y de la AVL, en
`resum_baseline.md`.

| Sistema | Exactas | BLEU | chrF | TER ↓ | GD | GDV | GDC |
|---|---|---|---|---|---|---|---|
| *Referencia (valenciano)* | — | — | — | — | *0,9973* | *0,9998* | *0,9182* |
| **AVLizador: motor + FLOR-760M** | **227 (49,6 %)** | **90,88** | **96,34** | **5,61** | **0,9936** | **0,9995** | **0,9189** |
| AVLizador: motor solo | 214 (46,7 %) | 90,39 | 96,10 | 5,91 | 0,9764 | 0,9981 | 0,9194 |
| Sin traducir (catalán tal cual) | 1 (0,2 %) | 69,25 | 87,97 | 15,76 | 0,0264 | 0,9200 | 0,9978 |
| gemma3:12b (el mejor LLM) | 11 (2,4 %) | 70,54 | 87,46 | 16,13 | 0,3889 | 0,9530 | 0,9701 |
| llama3.1:8b | 1 | 68,32 | 87,55 | 16,28 | 0,0601 | 0,9239 | 0,9951 |
| gemma4:12b | 1 | 67,49 | 87,06 | 16,88 | 0,0564 | 0,9273 | 0,9957 |
| qwen3:8b | 1 | 66,86 | 86,88 | 17,23 | 0,0382 | 0,9227 | 0,9969 |
| qwen3:14b | 2 | 66,83 | 86,81 | 17,32 | 0,0435 | 0,9227 | 0,9965 |
| qwen2.5:7b | 1 | 63,57 | 85,36 | 19,50 | 0,0372 | 0,9242 | 0,9971 |
| qwen2.5:14b | 0 | 59,04 | 82,96 | 22,55 | 0,0975 | 0,9325 | 0,9927 |
| mistral-nemo:12b | 1 | 59,35 | 82,89 | 22,86 | 0,1263 | 0,9365 | 0,9908 |
| salamandra-7b-instruct | 4 | 57,77 | 79,50 | 26,06 | 0,1517 | 0,9359 | 0,9885 |

Por partes (GD de la salida; referencia BOE 0,9951 y AVL 1,0000):
AVLizador 0,9886 y 1,0000; sin traducir 0,0000 y 0,0605; el mejor LLM,
gemma3, 0,3538 y 0,4354; el resto, entre 0,003 y 0,10 en el BOE y entre
0,07 y 0,24 en la AVL.

**Lectura**:

1. **Ningún LLM mejora el no traducir nada** en TER (15,76 sin tocar el
   catalán; el mejor LLM, gemma3, 16,13). Solo gemma3 lo supera un poco
   en BLEU (70,54 frente a 69,25) y en la parte del BOE (TER 18,83 frente
   a 20,16). AVLizador queda a un tercio del TER de cualquiera de ellos
   (5,61) y es el único que acierta frases enteras (227 frente a 11).
2. **Su salida sigue siendo catalán**: el GD de los LLM va de 0,04 a 0,15
   (gemma3, 0,39), frente a 0,997 de la referencia y 0,994 de AVLizador;
   la entrada catalana da 0,026. El GDC lo confirma desde el otro lado:
   0,99 en los LLM (casi ninguna forma valenciana), 0,919 en AVLizador y
   0,918 en la referencia. En la mezcla, AVLizador pone 1.085 formas
   valencianas y deja 7 catalanas (la referencia, 1.092 y 3); llama3.1,
   65 y 1.016. El GDV (0,92-0,95, casi el 0,92 de la entrada) dice lo
   mismo, pero muy comprimido. Las formas catalanas que más dejan son
   las mismas en todos: "aquesta/aquest/aquests/aquestes" (unas 250 por
   modelo), "seva/seves" (unas 120) y "serveis". Solo gemma3 cambia algo
   ("seues", "paren").
3. **Muchos devuelven la frase tal cual**: llama3.1:8b 325 de 458, qwen3:8b
   315, qwen3:14b 294, gemma4:12b 240, qwen2.5:7b 189.
4. **Los que sí cambian la frase empeoran**: no hacen cambios dialectales,
   reformulan (salamandra: "reporta"→"genera", "és necessari"→"cal"),
   introducen errores ("interconnected", "siat", "frontales", "las
   aprovés", "los nutrients") o corrigen el catalán de entrada. Por eso
   qwen2.5:14b, mistral-nemo y salamandra quedan por debajo de no
   traducir.
5. **Velocidad** (GPU RTX 2080 Ti): 0,6-1,4 s por frase; AVLizador, 0,5 s
   en CPU con FLOR y 0,03 s el motor solo. qwen2.5:7b sale a 9,7 s por
   frase, una anomalía de esa tarea (probablemente la GPU compartida o
   el modelo en CPU), no del modelo.

**Conclusión**: con una instrucción mínima, los LLM generalistas de 7.000
a 14.000 millones de parámetros no saben pasar de catalán a valenciano
normativo: dejan el catalán casi intacto o lo reformulan. AVLizador sí lo
hace, sin GPU y más rápido.

**Aviso sobre el benchmark** (visto al revisar las salidas): algunas
frases de la AVL tienen erratas en el catalán de entrada que vienen del
borrador automático val→cat y no se corrigieron en la revisión:
BM-AVL-003 ("parin", "permeto"), BM-AVL-016 y BM-AVL-070 ("permeto") y
BM-AVL-004 ("dels l'arbres", también en el valenciano). Afectan igual a
todos los sistemas; no se han tocado (datos del benchmark).
