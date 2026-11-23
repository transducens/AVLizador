# Imatge Docker d'AVLizador: interfície web + API (traductor català ->
# valencià i Grau Dialectal), només CPU i sense internet en funcionament.
# Pla i decisions: documentacio/hoja_de_ruta_interfaz_docker.md (secció 7).
#
#   docker compose up --build        # http://localhost:8000
#
# Des del 13/11/2026 el model de llengua és KenLM (en lloc de FLOR-760M i
# PyTorch): la imatge és molt més lleugera. Els tres fitxers del model
# (valencia_net_dogv_o5.binary, valencia_net_dogv_freq.json i sentit.json)
# es baixen de Hugging Face en construir-la (16/11/2026; transducens/
# avlizador-kenlm-va, la revisió del paquet o --build-arg KENLM_REVISIO=...),
# o es copien de docker/kenlm/ si hi són (vore docker/LLEGIM.md). En
# funcionament la imatge no es connecta a internet.
#
# Opció amb lemes (23/11/2026, `--model kenlm-lemes`): amb
# --build-arg KENLM_LEMES=1 (o KENLM_LEMES: "1" en docker-compose.yml) la
# imatge porta també valencia_net_dogv_lemes_o5.binary i _lemes_freq.json
# (~80 MB més), del mateix repositori de Hugging Face o de docker/kenlm/.
# Sense, no. Ho fa docker/prepara_kenlm.py.
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
# Model d'spaCy: pip el baixa dels "releases" de GitHub (URL directa del
# pyproject). Si eixa descàrrega falla dins de Docker (17/11/2026: la xarxa de
# Docker Desktop tallava la connexió SSL i en Windows sí que baixava), es pot
# deixar el fitxer en docker/ (ca_core_news_md-3.8.0-py3-none-any.whl) i
# s'instal·la d'allí: les altres dependències s'instal·len a banda perquè, amb
# la URL directa, pip el tornaria a baixar encara que ja estiga instal·lat.
COPY docker/LLEGIM.md docker/*.whl /tmp/whl/
RUN if ls /tmp/whl/ca_core_news_md-*.whl >/dev/null 2>&1; then \
      echo "Model d'spaCy: docker/" \
      && pip install /tmp/whl/ca_core_news_md-*.whl \
      && python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; e = p['optional-dependencies']; r = [d for d in p['dependencies'] if not d.replace('-', '_').startswith('ca_core_news_md')] + e['kenlm'] + e['web']; open('/tmp/requisits.txt', 'w').write(chr(10).join(r))" \
      && pip install -r /tmp/requisits.txt \
      && pip install --no-deps . ; \
    else \
      pip install ".[kenlm,web]" ; \
    fi \
 && pip check \
 && rm -rf /tmp/whl /tmp/requisits.txt \
 && pip freeze > /opt/versions_python.txt

# Fitxers del model KenLM (vore la capçalera): cada un de docker/kenlm/ si hi
# és; els que falten, de Hugging Face. Si en falta algun, la construcció
# s'atura ací (docker/prepara_kenlm.py).
ARG KENLM_REVISIO=""
ARG KENLM_LEMES=""
COPY docker/ /tmp/docker/
RUN python /tmp/docker/prepara_kenlm.py --origen /tmp/docker/kenlm --desti /opt/kenlm \
      --revisio "$KENLM_REVISIO" --lemes "$KENLM_LEMES" \
 && rm -rf /tmp/docker /opt/kenlm/.cache

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
