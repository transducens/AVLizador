# Imatge Docker d'AVLizador: interfície web + API (traductor català ->
# valencià i Grau Dialectal), només CPU i sense internet en funcionament.
# Pla i decisions: documentacio/hoja_de_ruta_interfaz_docker.md (secció 7).
#
#   docker compose up --build        # http://localhost:8000
#
# Des del 13/11/2026 el model de llengua és KenLM (en lloc de FLOR-760M i
# PyTorch): la imatge és molt més lleugera. ABANS DE CONSTRUIR-LA cal posar
# en docker/kenlm/ (carpeta ignorada per git) els tres fitxers del model:
#   valencia_net_dogv_o5.binary, valencia_net_dogv_freq.json i el
#   classificador de sentit: sentit.json (el general, des del 13/11/2026)
#   o nb.json (el de "cop")
# (de dades/macocu/kenlm/ en Abaco; més avant es publicaran en Hugging Face).
#
# LLICÈNCIES: la imatge inclou el model d'spaCy ca_core_news_md (GPL-3.0) i
# la biblioteca KenLM (LGPL-2.1). Vegeu NOTICE abans de distribuir-la; la
# recomanació és construir-la en local (decisió D3).

# --- Fase 1: instal·lació -------------------------------------------------
FROM python:3.12-slim AS construccio

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# kenlm es compila en instal·lar-lo: compilador de C++ i zlib només en esta
# fase (la imatge final no els porta).
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /src
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install ".[kenlm,web]" \
 && pip freeze > /opt/versions_python.txt

# Fitxers del model KenLM (vore la capçalera). Si en falta algun, la
# construcció s'atura ací amb un missatge clar.
COPY docker/kenlm/ /opt/kenlm/
RUN for f in valencia_net_dogv_o5.binary valencia_net_dogv_freq.json; do \
      test -s "/opt/kenlm/$f" || { echo "Falta docker/kenlm/$f (vore la capçalera del Dockerfile)" >&2; exit 1; }; \
    done \
 && { test -s /opt/kenlm/sentit.json || test -s /opt/kenlm/nb.json \
      || { echo "Falta docker/kenlm/sentit.json (o nb.json): el classificador de sentit" >&2; exit 1; }; }

# --- Fase 2: imatge final, neta i sense root ------------------------------
FROM python:3.12-slim

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin avlizador

COPY --from=construccio /opt/venv /opt/venv
COPY --from=construccio /opt/kenlm /opt/kenlm
COPY --from=construccio /opt/versions_python.txt /opt/versions_python.txt

# Valors per defecte (es poden canviar en docker-compose.yml sense
# reconstruir). Taula completa: README, secció "Variables d'entorn".
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AVLIZADOR_MODE=complet \
    AVLIZADOR_KENLM_DIR=/opt/kenlm \
    MAX_CARACTERS=20000 \
    MAX_TRADUCCIONS_SIMULTANIES=2 \
    UVICORN_LOG_LEVEL=warning

USER avlizador
WORKDIR /tmp
EXPOSE 8000

# Carregar spaCy i KenLM tarda uns segons: --start-period els dona temps.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8000/api/salut', timeout=4).read(); sys.exit(0 if b'\"ok\"' in r else 1)"]

CMD ["avlizador", "web", "--host", "0.0.0.0", "--port", "8000"]
