# Imatge Docker d'AVLizador: interfície web + API (traductor català ->
# valencià i Grau Dialectal), només CPU i sense internet en funcionament.
# Pla i decisions: documentacio/hoja_de_ruta_interfaz_docker.md (secció 7).
#
#   docker compose up --build        # http://localhost:8000
#
# LLICÈNCIES: la imatge inclou el model d'spaCy ca_core_news_md (GPL-3.0) i
# FLOR-760M (derivat de BLOOM, llicència RAIL). Vegeu NOTICE abans de
# distribuir-la; la recomanació és construir-la en local (decisió D3).

# --- Fase 1: instal·lació -------------------------------------------------
FROM python:3.12-slim AS construccio

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /src
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
# torch només CPU (~200 MB en compte de més de 2 GB amb CUDA). Primer i a
# soles des de l'índex de CPU: amb --extra-index-url pip podria triar el de
# PyPI (CUDA).
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install ".[ml,web]" \
 && pip freeze > /opt/versions_python.txt

# FLOR-760M dins de la imatge (decisió D2), a una revisió fixa: la mateixa
# amb què s'han mesurat els resultats.
ARG FLOR_REVISIO=d47b56bdc67aa290cf9c4a64a6ee040b01eacdfc
ENV HF_HOME=/opt/hf
COPY docker/descarrega_flor.py /tmp/descarrega_flor.py
RUN python /tmp/descarrega_flor.py "$FLOR_REVISIO"

# --- Fase 2: imatge final, neta i sense root ------------------------------
FROM python:3.12-slim

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin avlizador

COPY --from=construccio /opt/venv /opt/venv
COPY --from=construccio /opt/hf /opt/hf
COPY --from=construccio /opt/versions_python.txt /opt/versions_python.txt

# Valors per defecte (es poden canviar en docker-compose.yml sense
# reconstruir). Taula completa: README, secció "Variables d'entorn".
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    AVLIZADOR_MODE=complet \
    MAX_CARACTERS=20000 \
    MAX_TRADUCCIONS_SIMULTANIES=2 \
    OMP_NUM_THREADS=2 \
    TORCH_NUM_THREADS=2 \
    UVICORN_LOG_LEVEL=warning

USER avlizador
WORKDIR /tmp
EXPOSE 8000

# Carregar spaCy i FLOR tarda uns segons: --start-period els dona temps.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8000/api/salut', timeout=4).read(); sys.exit(0 if b'\"ok\"' in r else 1)"]

CMD ["avlizador", "web", "--host", "0.0.0.0", "--port", "8000"]
