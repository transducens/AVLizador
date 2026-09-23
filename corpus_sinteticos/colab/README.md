# Probar la generación del corpus en Google Colab (GPU)

`generar_corpus_colab.ipynb` ejecuta `sinteticos/genera_corpus_sintetico.py`
con GPU gratuita de Colab, usando exactamente el mismo motor (system prompt +
glosario de `evalua_modelos/evalua_models.py`, modelo qwen2.5:14b) que ya
probaste en local.

## Cómo abrirlo

1. Sube el archivo `generar_corpus_colab.ipynb` a tu Google Drive, o ábrelo
   directamente desde [colab.research.google.com](https://colab.research.google.com)
   → "Subir cuaderno" → selecciona este archivo.
2. Sube también tu proyecto (o al menos las carpetas/archivos que el
   notebook necesita — están listados en su primera celda) a tu Google
   Drive, en `MyDrive/AVLizador/scrapeo/` (o edita `PROJECT_DIR` dentro del
   notebook si lo pones en otro sitio).
3. `Entorno de ejecución` → `Cambiar tipo de entorno de ejecución` → GPU.
4. Ejecuta las celdas en orden, de arriba a abajo.

## Qué hace, celda a celda

1. Comprueba la GPU asignada (`nvidia-smi`).
2. Monta tu Google Drive.
3. Verifica que están los archivos imprescindibles del proyecto.
4. Instala Ollama (Colab da acceso root, así que el instalador oficial
   funciona sin más).
5. Arranca `ollama serve` en segundo plano, guardando los modelos en tu
   Drive (`sinteticos/../ollama_models/`) para no tener que volver a
   descargar los ~9-10 GB de qwen2.5:14b en cada sesión nueva.
6. Descarga qwen2.5:14b.
7. Comprueba que de verdad está corriendo en GPU (`ollama ps`, mira
   `size_vram`).
8. Segmenta el corpus fuente y muestra estadísticas (no llama al modelo).
9. Prueba real con 10 frases — compara el tiempo con los ~30-60 s/frase que
   viste en CPU local.
10. Te enseña las 10 traducciones para que las revises tú mismo.
11. Celda para escalar a una muestra más grande (`--sample N`), con notas
    sobre los límites de sesión de Colab y cómo reanudar si se corta.
12. Celda opcional para regenerar solo la exportación limpia.

## Sobre los límites de la sesión gratuita

Colab desconecta por inactividad (~90 min) y tiene un tope de sesión
(~12h); con uso intensivo, Google puede limitarte el acceso a GPU una
temporada, sin avisar cuánto durará. El script ya es reanudable y el
archivo de salida vive en tu Drive, así que si se corta, basta con volver a
ejecutar las celdas de montar Drive + arrancar Ollama y relanzar la
generación con el mismo comando — retoma donde lo dejó.

Para una tanda muy larga (el corpus completo, ~46.315 frases) el clúster
SLURM de la universidad (ver `../slurm/`) es más adecuado, precisamente
porque no tiene ese techo de tiempo. Colab es mejor para probar y para
tandas de varios miles de frases por sesión.
