"""API web d'AVLizador (FastAPI): traducció català -> valencià i Grau
Dialectal. Pla complet: `documentacio/hoja_de_ruta_interfaz_docker.md`.

    avlizador web                                  # http://127.0.0.1:8000
    uvicorn avlizador.web.main:app --no-access-log # el mateix, a mà

Un sol procés: spaCy i FLOR-760M es carreguen una vegada en arrancar
(cada procés en carregaria una còpia). Les traduccions van a un fil a part
perquè no bloquegen el servidor, i un semàfor en limita el nombre a la
vegada.

Variables d'entorn (valors per defecte entre parèntesis):
- `AVLIZADOR_MODE` (`complet`): `complet` = motor + FLOR; `motor` = només regles.
- `MAX_CARACTERS` (20000): longitud màxima del text; si es passa, HTTP 413.
- `MAX_TRADUCCIONS_SIMULTANIES` (2): traduccions a la vegada; si ja n'hi
  ha tantes, HTTP 429 sense esperar.
- `TORCH_NUM_THREADS` (2): fils de càlcul de FLOR (`torch.set_num_threads`).
- `AVLIZADOR_DOCS` (0): 1 = documentació interactiva en `/docs` (carrega
  JavaScript d'un CDN: només en desenvolupament).
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from .idiomes import Parell, parells_per_defecte
from .missatges import IDIOMES_INTERFICIE, missatge, nombre, textos, tria_idioma

CARPETA = Path(__file__).resolve().parent
# Textos que necessita `static/traductor.js` (van en un bloc JSON de la
# pàgina, no en JavaScript en línia).
CLAUS_JS = ("comptador", "traduint", "tardant", "traduccio_feta", "copiada", "no_copiada",
            "res_per_copiar", "text_buit", "error_xarxa")

# PRIVACITAT (requisit fix, 03/11/2026): els textos que es traduïxen poden
# ser documents de l'Administració i NO poden aparéixer mai en els logs.
# - `uvicorn.access` en `warning`: ni una línia per petició (tampoc rutes,
#   IP ni hores d'ús). `avlizador web` a més arranca uvicorn sense log
#   d'accés.
# - Cap middleware registra el cos de les peticions ni cap camp dels models
#   d'entrada (`text`...).
# - Els errors es registren amb el tipus i la longitud del text, mai amb el
#   text ni amb el traceback (pot portar els arguments de la funció).
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
log = logging.getLogger("avlizador.web")

# Windows pren els tipus MIME del registre, i hi pot dir que un .js és
# `text/plain`: amb `X-Content-Type-Options: nosniff` el navegador no
# l'executa (vist el 04/11/2026). Es fixen ací.
for _tipus, _extensio in (("text/javascript", ".js"), ("text/css", ".css"), ("image/svg+xml", ".svg")):
    mimetypes.add_type(_tipus, _extensio)


def _enter(nom: str, per_defecte: int) -> int:
    try:
        return int(os.environ.get(nom, per_defecte))
    except ValueError:
        return per_defecte


@dataclass
class Configuracio:
    mode: str = "complet"
    max_caracters: int = 20000
    max_simultanies: int = 2
    fils: int = 2
    docs: bool = False
    precarrega: bool = True

    @classmethod
    def de_entorn(cls) -> "Configuracio":
        mode = os.environ.get("AVLIZADOR_MODE", "complet").strip().lower()
        return cls(
            mode=mode if mode in ("complet", "motor") else "complet",
            max_caracters=max(1, _enter("MAX_CARACTERS", 20000)),
            max_simultanies=max(1, _enter("MAX_TRADUCCIONS_SIMULTANIES", 2)),
            fils=max(1, _enter("TORCH_NUM_THREADS", 2)),
            docs=os.environ.get("AVLIZADOR_DOCS", "0") == "1",
        )


@dataclass
class Estat:
    config: Configuracio
    parells: dict[tuple[str, str], Parell]
    semafor: asyncio.Semaphore | None = None
    mode_efectiu: str = ""
    models_carregats: bool = False
    versions: dict = field(default_factory=dict)


class ErrorPeticio(Exception):
    """Una petició que no es pot atendre: codi HTTP + clau del missatge."""

    def __init__(self, codi: int, clau: str, **valors):
        super().__init__(clau)
        self.codi, self.clau, self.valors = codi, clau, valors


# --- Peticions i respostes -------------------------------------------------

class PeticioTraduccio(BaseModel):
    text: str
    origen: str = "ca"
    desti: str = "ca-valencia"


class PeticioGD(BaseModel):
    text: str


def tradueix_per_linies(text: str, tradueix) -> str:
    """Traduïx línia a línia (com la CLI) i conserva els salts de línia i
    les línies buides.

    >>> tradueix_per_linies("a\\n\\nb\\r\\nc", str.upper)
    'A\\n\\nB\\r\\nC'
    """
    trossos = re.split(r"(\r\n|\n|\r)", text)
    return "".join(t if (i % 2 or not t.strip()) else tradueix(t) for i, t in enumerate(trossos))


def resum_gd(text: str) -> dict:
    """GD, GDV i GDC d'un text amb UNA sola passada d'spaCy: GDV i GDC ixen
    dels mateixos comptadors que `calcula_gdv`/`calcula_gdc` (ho comprova
    `tests/test_web.py`)."""
    from ..grau_dialectal import calcula_gd

    r = calcula_gd(text)
    total = r["total_paraules"]
    return {
        "gd": r["gd"],
        "gdv": round(1 - r["total_orientals"] / total, 4) if total else 1.0,
        "gdc": round(1 - r["total_occidentals"] / total, 4) if total else 1.0,
        "marcadors_occidentals": r["marcadors_occidentals"],
        "marcadors_orientals": r["marcadors_orientals"],
        "total_paraules": total,
        "total_marcades": r["total_marcades"],
    }


def _versio(paquet: str) -> str | None:
    try:
        return version(paquet)
    except PackageNotFoundError:
        return None


def _precarrega(estat: Estat) -> None:
    """Carrega spaCy, els diccionaris i (en mode complet) FLOR abans de la
    primera petició."""
    from ..traductor_cat_val.translate_invers import model_llengua_disponible

    cfg = estat.config
    mode = cfg.mode
    if mode == "complet" and not model_llengua_disponible():
        log.warning("AVLIZADOR_MODE=complet però falta l'extra [ml] (torch, transformers): s'usa el motor sol.")
        mode = "motor"
    if mode == "complet":
        import torch

        torch.set_num_threads(cfg.fils)
    if cfg.precarrega:
        for parell in estat.parells.values():
            parell.tradueix("Un cop acabada la reunió, marxem.")
        resum_gd("Este xiquet vol vindre hui.")
    estat.mode_efectiu = mode
    estat.versions = {
        "avlizador": __version__,
        "model_llengua": None,
        "spacy": _versio("spacy"),
        "model_spacy": _versio("ca_core_news_md"),
        "torch": _versio("torch") if mode == "complet" else None,
    }
    if mode == "complet":
        from ..traductor_cat_val.model_llengua.puntuador import MODEL_PER_DEFECTE

        estat.versions["model_llengua"] = MODEL_PER_DEFECTE
    estat.models_carregats = True


# --- Aplicació ---------------------------------------------------------------

def create_app(config: Configuracio | None = None,
               parells: dict[tuple[str, str], Parell] | None = None) -> FastAPI:
    config = config or Configuracio.de_entorn()
    estat = Estat(config=config, parells=parells or parells_per_defecte(config.mode))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        estat.semafor = asyncio.Semaphore(config.max_simultanies)
        await run_in_threadpool(_precarrega, estat)
        log.info("AVLizador web preparat (mode %s, %d traduccions a la vegada).",
                 estat.mode_efectiu, config.max_simultanies)
        yield

    app = FastAPI(
        title="AVLizador",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if config.docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.docs else None,
    )
    app.state.avlizador = estat

    plantilles = Environment(loader=FileSystemLoader(CARPETA / "plantilles"),
                             autoescape=select_autoescape(["html"]))
    app.mount("/static", StaticFiles(directory=CARPETA / "static"), name="static")

    def idioma_de(request: Request) -> str:
        return tria_idioma(request.query_params.get("idioma"), request.headers.get("accept-language"),
                           request.cookies.get("idioma"))

    def error(request: Request, codi: int, clau: str, **valors) -> JSONResponse:
        return JSONResponse({"error": missatge(idioma_de(request), clau, **valors)}, status_code=codi)

    def comprova_longitud(text: str) -> None:
        if len(text) > config.max_caracters:
            raise ErrorPeticio(413, "massa_llarg", maxim=nombre(config.max_caracters), n=nombre(len(text)))

    async def tradueix_text(text: str, origen: str, desti: str) -> str:
        """El que fan igual la API i el formulari sense JavaScript: parell,
        longitud, semàfor i traducció en un fil."""
        parell = estat.parells.get((origen, desti))
        if parell is None:
            raise ErrorPeticio(400, "parell_desconegut")
        comprova_longitud(text)
        # Si no queda lloc, es rebutja al moment (no s'espera). Entre
        # `locked()` i l'`async with` no hi ha cap `await`: és atòmic.
        if estat.semafor.locked():
            raise ErrorPeticio(429, "ocupat")
        async with estat.semafor:
            try:
                return await run_in_threadpool(tradueix_per_linies, text, parell.tradueix)
            except Exception as e:  # noqa: BLE001 -- es registra sense el text
                log.error("Error en traduir (%s -> %s): %s, %d caràcters.",
                          origen, desti, type(e).__name__, len(text))
                raise ErrorPeticio(500, "error_traduccio") from None

    @app.exception_handler(ErrorPeticio)
    async def error_peticio(request: Request, exc: ErrorPeticio):
        return error(request, exc.codi, exc.clau, **exc.valors)

    @app.middleware("http")
    async def capcaleres_seguretat(request: Request, call_next):
        resposta = await call_next(request)
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("Referrer-Policy", "no-referrer")
        if not request.url.path.startswith("/docs"):
            resposta.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        return resposta

    @app.exception_handler(RequestValidationError)
    async def peticio_no_valida(request: Request, exc: RequestValidationError):
        # La resposta per defecte de FastAPI torna a enviar el valor rebut
        # (`input`), és a dir, el text: no es repetix.
        return error(request, 422, "peticio_no_valida")

    @app.exception_handler(StarletteHTTPException)
    async def error_http(request: Request, exc: StarletteHTTPException):
        # P. ex., un cos que no és JSON (400): el mateix format {"error": ...}
        # que la resta, en la llengua de la interfície.
        if exc.status_code == 400:
            return error(request, 400, "peticio_no_valida")
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    # --- Pàgines -------------------------------------------------------------

    def pagina_traduir(request: Request, codi: int = 200, text: str = "", traduccio: str = "",
                       origen: str | None = None, desti: str | None = None, error: str | None = None,
                       error_camp: str | None = None, avis_estat: str | None = None) -> HTMLResponse:
        idioma = idioma_de(request)
        t = textos(idioma)
        parells = [p.descriu(idioma) for p in estat.parells.values()]
        origen = origen if any(p["origen"] == origen for p in parells) else parells[0]["origen"]
        destins = [p["desti"] for p in parells if p["origen"] == origen]
        desti = desti if desti in destins else destins[0]
        dades_js = {"textos": {c: t[c] for c in CLAUS_JS} | {"massa_llarg": t["api"]["massa_llarg"]},
                    "maxim": config.max_caracters, "idioma": idioma, "parells": parells}
        html = plantilles.get_template("traduir.html").render(
            t=t, idioma=idioma, pagina="traduir", versio=t["versio"].format(versio=__version__),
            llengues=[(c, textos(c)["nom_llengua"]) for c in IDIOMES_INTERFICIE],
            origens=list({p["origen"]: p for p in parells}.values()), parells=parells,
            origen=origen, desti=desti, text=text, traduccio=traduccio, maxim=config.max_caracters,
            comptador=t["comptador"].format(n=nombre(len(text)), maxim=nombre(config.max_caracters)),
            error=error, error_camp=error_camp, estat=avis_estat, dades_js=dades_js)
        resposta = HTMLResponse(html, status_code=codi)
        if request.query_params.get("idioma") in IDIOMES_INTERFICIE:
            # Galeta tècnica (només la llengua triada): no cal avís de galetes.
            resposta.set_cookie("idioma", idioma, max_age=365 * 24 * 3600, httponly=True, samesite="lax")
        return resposta

    @app.get("/", response_class=HTMLResponse)
    async def inici(request: Request):
        return pagina_traduir(request)

    @app.post("/", response_class=HTMLResponse)
    async def inici_formulari(request: Request):
        # Formulari sense JavaScript (millora progressiva): mateixos límits
        # que la API. Es llig a mà per no dependre de python-multipart.
        camps = parse_qs((await request.body()).decode("utf-8", errors="replace"), keep_blank_values=True)
        text = camps.get("text", [""])[0]
        origen = camps.get("origen", ["ca"])[0]
        desti = camps.get("desti", ["ca-valencia"])[0]
        idioma = idioma_de(request)
        t = textos(idioma)
        if not text.strip():
            return pagina_traduir(request, 200, text, "", origen, desti, error_camp=t["text_buit"])
        try:
            traduccio = await tradueix_text(text, origen, desti)
        except ErrorPeticio as e:
            msg = missatge(idioma, e.clau, **e.valors)
            if e.clau == "massa_llarg":
                return pagina_traduir(request, e.codi, text, "", origen, desti, error_camp=msg)
            return pagina_traduir(request, e.codi, text, "", origen, desti, error=msg)
        return pagina_traduir(request, 200, text, traduccio, origen, desti, avis_estat=t["traduccio_feta"])

    # --- API -----------------------------------------------------------------

    @app.get("/api/salut")
    async def salut():
        return {"estat": "ok" if estat.models_carregats else "carregant",
                "models_carregats": estat.models_carregats, "mode": estat.mode_efectiu or config.mode}

    @app.get("/api/versio")
    async def versio():
        return estat.versions or {"avlizador": __version__}

    @app.get("/api/idiomes")
    async def idiomes(request: Request):
        idioma = idioma_de(request)
        return [p.descriu(idioma) for p in estat.parells.values()]

    @app.post("/api/tradueix")
    async def tradueix(peticio: PeticioTraduccio):
        return {"traduccio": await tradueix_text(peticio.text, peticio.origen, peticio.desti)}

    @app.post("/api/gd")
    async def gd(peticio: PeticioGD, request: Request):
        n = len(peticio.text)
        comprova_longitud(peticio.text)
        try:
            return await run_in_threadpool(resum_gd, peticio.text)
        except Exception as e:  # noqa: BLE001
            log.error("Error en calcular el GD: %s, %d caràcters.", type(e).__name__, n)
            return error(request, 500, "error_gd")

    return app


def __getattr__(nom: str):
    # `uvicorn avlizador.web.main:app`: l'aplicació es crea quan es demana
    # (així importar el mòdul en les proves no llig l'entorn ni carrega res).
    if nom == "app":
        return create_app()
    raise AttributeError(nom)
