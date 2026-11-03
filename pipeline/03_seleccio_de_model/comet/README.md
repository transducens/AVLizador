# XCOMET-XL sobre el benchmark manual (03/11/2026)

[COMET](https://github.com/Unbabel/COMET) es una métrica aprendida de
Unbabel: un modelo que lee la frase de origen, la traducción y la
referencia y da una nota de 0 a 100. **XCOMET-XL** (`Unbabel/XCOMET-XL`,
unos 3.500 millones de parámetros) es la versión grande; además de la
nota, marca los trozos de la traducción que considera errores
(`error_spans`, con gravedad *minor*, *major* o *critical*).

Aquí se puntúan traducciones que **ya existen** del manual mezcla (458
frases), sin volver a traducir:

- `../baseline_llm/resultats/`: AVLizador 1.0.1, el motor solo, **sin
  traducir** (el catalán tal cual) y los 9 LLM del baseline.
- `entrades/avlizador_1.1.0.json`: AVLizador 1.1.0 (`avlizador avalua
  --benchmarks manual` del 03/11/2026).

## Qué queremos saber

COMET mide sobre todo si se conserva el **significado**, y el catalán
sin traducir significa lo mismo que el valenciano. Por eso el "sin
traducir" es la prueba clave: si COMET le da casi la misma nota que a
AVLizador, **no ve el dialecto** y no sirve para evaluar esta tarea (o
solo sirve junto con el GD). Si los separa, es una buena métrica para
presentar. Los `error_spans` dirán si marca como error las formas
catalanas ("aquest", "seva", "serveis"...).

## Ficheros

| Fichero | Qué hace |
|---|---|
| `puntua_comet.py` | Carga el modelo una vez y puntúa los JSON que se le pasan (`entrada`, `hipotesi`, `referencia`); un JSON por sistema con la nota y los errores de cada frase, y `resum__<modelo>.md` con la nota media por sistema (mezcla, BOE, AVL) |
| `comet.sh` | Job de SLURM para Abaco (1 GPU), con su propio venv |
| `entrades/` | Traducciones que no están en el baseline (AVLizador 1.1.0) |
| `resultats/` | Salidas (las de prueba, `*_limit*`, no entran en git) |

## Cómo lanzarlo en Abaco

Una sola vez, en el login:

1. En huggingface.co, entrar en `Unbabel/XCOMET-XL` y aceptar las
   condiciones (el modelo es de acceso restringido).
2. Crear un token de **lectura** (Settings → Access Tokens → Read) y
   guardarlo en Abaco con el venv del paquete:
   `~/venvs/avlizador/bin/hf auth login` (en versiones antiguas,
   `huggingface-cli login`; a "Add token as git credential?", no). Queda
   en `~/.cache/huggingface/token` y el job lo usa solo.

Después:

```bash
cd ~/scrapeo/AVLizador && git pull && git checkout comet
cd pipeline/03_seleccio_de_model/comet
LIMIT=10 sbatch comet.sh     # prueba: 10 frases por sistema
cat logs/<jobid>_xcomet.out  # torch ... cuda True, y una tabla al final
sbatch comet.sh              # todo
```

La primera vez el job crea el venv `~/venvs/comet` (torch de CUDA 12.8 +
`unbabel-comet`) y descarga el modelo (~14 GB): tarda bastante más.
Variables: `PRECISIO=fp32` (si fp16 diera problemas; necesita una GPU de
16 GB), `QE=1` (sin referencia: solo origen y traducción), `LOT=4` (si
falta memoria en la GPU).

Traer los resultados (desde `scrapeo/` en local):

```powershell
scp -r nmartin@abaco:scrapeo/AVLizador/pipeline/03_seleccio_de_model/comet/resultats pipeline/03_seleccio_de_model/comet/
```

## Decisiones

- **fp16 por defecto**: XCOMET-XL en fp32 ocupa ~14 GB y las GPU de
  Abaco tienen 11 GB.
- **Venv propio** (`~/venvs/comet`): `unbabel-comet` fija versiones que
  chocan con el venv del paquete, y el torch de PyPI por defecto no ve
  las GPU de Abaco (driver CUDA 12.9; ver el job 2646 del LoRA en
  `../model_llengua/sesgo/README.md`).
- **Licencia**: XCOMET-XL es CC BY-NC-SA 4.0 (sin uso comercial). Sirve
  para evaluar; no entra en el paquete ni en la entrega.
- **Sin probar en local** (decisión del usuario): solo se comprobó el
  script con un modelo falso.

## Resultados

*Pendiente.*
