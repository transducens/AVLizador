"""Interfície web d'AVLizador (FastAPI): `avlizador web` o
`uvicorn avlizador.web.main:app --no-access-log`. Necessita l'extra `[web]`.

API (fase 1 de `documentacio/hoja_de_ruta_interfaz_docker.md`):
`GET /api/idiomes`, `POST /api/tradueix`, `POST /api/gd`, `GET /api/salut`
i `GET /api/versio`.
"""

from .main import Configuracio, create_app

__all__ = ["Configuracio", "create_app"]
