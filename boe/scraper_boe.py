#!/usr/bin/env python3
"""Scraper ético del BOE (suplements en català i valencià) - boe.es.

Descarga únicamente los documentos que tienen traducción oficial real
(clase HTML "puntoPDFsup", nombre de fichero acabado en -C.pdf / -V.pdf),
no el PDF castellano de referencia que el sumario muestra para el resto
de documentos (clase "puntoPDF"). Ver README.md para más contexto.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.boe.es"
CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "boe"
PROGRESS_PATH = CORPUS_DIR / "progreso.json"
LOG_PATH = CORPUS_DIR / "scraper.log"

# lang_key -> (código usado en boe.es, sufijo del PDF traducido)
IDIOMAS = {
    "catalan": {"codigo": "c", "sufijo": "-C"},
    "valenciano": {"codigo": "v", "sufijo": "-V"},
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

DELAY_DOCUMENTO = (8, 20)
DELAY_DIA = (15, 30)
DELAY_MES = (30, 60)
DELAY_ANIO = (60, 120)

TIMEOUT = 30
MAX_REINTENTOS = 3
BACKOFF_BASE = 30
PAUSA_LARGA = 600  # 10 minutos, tras agotar reintentos con 429/503
CODIGOS_REINTENTABLES = {429, 503}

logger = logging.getLogger("boe_scraper")


def configurar_logging(verbose: bool) -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    nivel = logging.DEBUG if verbose else logging.INFO
    formato = "%(asctime)s [%(levelname)s] %(message)s"
    logger.setLevel(nivel)
    logger.handlers.clear()

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter(formato))
    logger.addHandler(consola)

    fichero = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fichero.setFormatter(logging.Formatter(formato))
    logger.addHandler(fichero)


def espera(rango: tuple[float, float], motivo: str) -> None:
    segundos = random.uniform(*rango)
    logger.debug(f"Esperando {segundos:.1f}s ({motivo})")
    time.sleep(segundos)


class RobotsChecker:
    """Matcher de robots.txt compatible con comodines '*' y '$'.

    urllib.robotparser (stdlib) NO interpreta '*'/'$' correctamente: deja
    pasar patrones como '/diario_boe/txt.php?*lang=ca' que boe.es SÍ quiere
    bloquear. Se comprobó explícitamente antes de escribir este scraper.
    Se implementa el algoritmo estándar (regla más larga que aplica gana;
    en empate, Allow gana sobre Disallow).
    """

    def __init__(self, session: requests.Session):
        self._reglas: list[tuple[int, str, re.Pattern]] = []
        self._cargar(session)

    def _cargar(self, session: requests.Session) -> None:
        url = urljoin(BASE_URL, "/robots.txt")
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        en_grupo_general = False
        for linea in resp.text.splitlines():
            linea = linea.split("#", 1)[0].strip()
            if not linea or ":" not in linea:
                continue
            campo, _, valor = linea.partition(":")
            campo, valor = campo.strip().lower(), valor.strip()
            if campo == "user-agent":
                en_grupo_general = valor == "*"
                continue
            if not en_grupo_general or not valor:
                continue
            if campo in ("disallow", "allow"):
                self._reglas.append((len(valor), campo, re.compile(self._a_regex(valor))))
        logger.info(f"robots.txt cargado: {len(self._reglas)} reglas para User-agent: *")

    @staticmethod
    def _a_regex(patron: str) -> str:
        ancla_final = patron.endswith("$")
        cuerpo = patron[:-1] if ancla_final else patron
        partes = [".*" if c == "*" else re.escape(c) for c in cuerpo]
        return "^" + "".join(partes) + ("$" if ancla_final else "")

    def puede_acceder(self, url: str) -> bool:
        partes = urlsplit(url)
        ruta = partes.path + (("?" + partes.query) if partes.query else "")
        mejor: tuple[int, str] | None = None
        for longitud, tipo, regex in self._reglas:
            if regex.match(ruta) and (mejor is None or longitud > mejor[0]):
                mejor = (longitud, tipo)
        return mejor is None or mejor[1] == "allow"


class Progreso:
    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            self.datos = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.datos = {"dias_completados": {}, "documentos": {}}

    def guardar(self) -> None:
        self.path.write_text(json.dumps(self.datos, ensure_ascii=False, indent=2), encoding="utf-8")

    def dia_completado(self, idioma: str, anio: int, fecha: str) -> bool:
        clave = f"{idioma}/{anio}"
        return fecha in self.datos["dias_completados"].get(clave, [])

    def marcar_dia_completado(self, idioma: str, anio: int, fecha: str) -> None:
        clave = f"{idioma}/{anio}"
        lista = self.datos["dias_completados"].setdefault(clave, [])
        if fecha not in lista:
            lista.append(fecha)
        self.guardar()

    def documento_descargado(self, doc_id: str) -> bool:
        return doc_id in self.datos["documentos"]

    def marcar_documento(self, doc_id: str, meta: dict) -> None:
        self.datos["documentos"][doc_id] = meta
        self.guardar()


@dataclass
class Documento:
    id: str
    url: str
    titulo: str


def construir_sesion() -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ca,es-ES;q=0.9,es;q=0.8,en;q=0.5",
            "Connection": "keep-alive",
        }
    )
    return sesion


def peticion_con_reintentos(
    sesion: requests.Session,
    robots: RobotsChecker,
    url: str,
    referer: str | None = None,
    stream: bool = False,
) -> requests.Response | None:
    if not robots.puede_acceder(url):
        logger.warning(f"BLOQUEADO por robots.txt, no se solicita: {url}")
        return None

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    if referer:
        headers["Referer"] = referer

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = sesion.get(url, headers=headers, timeout=TIMEOUT, stream=stream)
            logger.info(f"GET {url} -> {resp.status_code} (intento {intento})")
            if resp.status_code == 200:
                return resp
            if resp.status_code in CODIGOS_REINTENTABLES:
                if intento < MAX_REINTENTOS:
                    espera_s = BACKOFF_BASE * (2 ** (intento - 1))
                    logger.warning(f"HTTP {resp.status_code}, backoff {espera_s}s antes de reintentar")
                    time.sleep(espera_s)
                    continue
                logger.warning(
                    f"HTTP {resp.status_code} tras {MAX_REINTENTOS} intentos, "
                    f"pausa larga de {PAUSA_LARGA}s"
                )
                time.sleep(PAUSA_LARGA)
                try:
                    resp2 = sesion.get(url, headers=headers, timeout=TIMEOUT, stream=stream)
                    logger.info(f"GET {url} -> {resp2.status_code} (tras pausa larga)")
                    if resp2.status_code == 200:
                        return resp2
                except requests.RequestException as exc:
                    logger.error(f"Fallo tras pausa larga en {url}: {exc}")
                logger.error(f"Descartando {url} tras agotar todos los reintentos")
                return None
            logger.error(f"HTTP {resp.status_code} no recuperable en {url}, se descarta")
            return None
        except requests.RequestException as exc:
            logger.warning(f"Excepción de red en intento {intento} para {url}: {exc}")
            if intento < MAX_REINTENTOS:
                espera_s = BACKOFF_BASE * (2 ** (intento - 1))
                time.sleep(espera_s)
                continue
            logger.error(f"Descartando {url} tras excepciones repetidas")
            return None
    return None


def obtener_anios_disponibles(sesion, robots, codigo: str) -> list[int]:
    url = f"{BASE_URL}/diario_boe/calendarios.php?c={codigo}&a=2015"
    resp = peticion_con_reintentos(sesion, robots, url, referer=BASE_URL)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    select = soup.find("select", id="p_selecc")
    if not select:
        return []
    anios = []
    for opcion in select.find_all("option"):
        texto = opcion.get_text(strip=True)
        if texto.isdigit():
            anios.append(int(texto))
    return sorted(anios)


def obtener_dias_del_anio(sesion, robots, idioma_dir: str, codigo: str, anio: int, referer: str) -> list[str]:
    url = f"{BASE_URL}/diario_boe/calendarios.php?c={codigo}&a={anio}"
    resp = peticion_con_reintentos(sesion, robots, url, referer=referer)
    if resp is None:
        return []
    patron = re.compile(rf'/boe_{idioma_dir}/dias/({anio}/\d{{2}}/\d{{2}})/')
    fechas = sorted({m.group(1).replace("/", "-") for m in patron.finditer(resp.text)})
    return fechas


def obtener_documentos_del_dia(sesion, robots, idioma_dir: str, fecha: str, sufijo: str, referer: str):
    anio, mes, dia = fecha.split("-")
    url = f"{BASE_URL}/boe_{idioma_dir}/dias/{anio}/{mes}/{dia}/index.php"
    resp = peticion_con_reintentos(sesion, robots, url, referer=referer)
    if resp is None:
        return url, []

    soup = BeautifulSoup(resp.text, "lxml")
    documentos = []
    for li in soup.select("li.puntoPDFsup"):
        enlace = li.find("a", href=True)
        if not enlace:
            continue
        doc_url = urljoin(url, enlace["href"])
        nombre = Path(urlsplit(doc_url).path).name  # p.ej. BOE-A-2015-10565-C.pdf
        if not nombre.endswith(sufijo + ".pdf"):
            continue
        doc_id = nombre[: -len(".pdf")]
        titulo = ""
        dispo = li.find_parent("li", class_="dispo")
        if dispo:
            p = dispo.find("p")
            if p:
                titulo = p.get_text(strip=True)
        documentos.append(Documento(id=doc_id, url=doc_url, titulo=titulo))
    return url, documentos


def descargar_documento(sesion, robots, doc: Documento, destino: Path, referer: str) -> bool:
    resp = peticion_con_reintentos(sesion, robots, doc.url, referer=referer, stream=True)
    if resp is None:
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(destino, "wb") as f:
            for trozo in resp.iter_content(chunk_size=8192):
                f.write(trozo)
    except requests.exceptions.RequestException as exc:
        # La conexión se cortó a mitad de la descarga (tras el 200 inicial,
        # que sí pasó por los reintentos). No debe tumbar todo el script:
        # se descarta el fichero parcial y se deja para el próximo intento.
        logger.error(f"Conexión interrumpida descargando {doc.url}: {exc}")
        destino.unlink(missing_ok=True)
        return False
    finally:
        resp.close()
    return True


def reconciliar_anio(anio: int, progreso: Progreso) -> None:
    """Elimina, para un año ya completado, cualquier documento sin pareja en el otro idioma.

    Necesario porque un año puede tener ficheros de catalán descargados en una
    ejecución anterior (antes de exigir emparejamiento) que ahora, al comprobar
    contra valencià, resultan huérfanos. Se compara lo que hay en disco, nunca
    se asume nada por progreso.json.
    """
    dir_c = CORPUS_DIR / "catalan" / str(anio)
    dir_v = CORPUS_DIR / "valenciano" / str(anio)
    ids_c = {p.stem[:-2]: p for p in dir_c.glob("*-C.pdf")} if dir_c.exists() else {}
    ids_v = {p.stem[:-2]: p for p in dir_v.glob("*-V.pdf")} if dir_v.exists() else {}

    huerfanos_c = set(ids_c) - set(ids_v)
    huerfanos_v = set(ids_v) - set(ids_c)

    for base in huerfanos_c:
        ruta = ids_c[base]
        logger.warning(f"{anio}: sin pareja en valencià, se elimina {ruta.name}")
        ruta.unlink(missing_ok=True)
        progreso.datos["documentos"].pop(f"{base}-C", None)
    for base in huerfanos_v:
        ruta = ids_v[base]
        logger.warning(f"{anio}: sin pareja en català, se elimina {ruta.name}")
        ruta.unlink(missing_ok=True)
        progreso.datos["documentos"].pop(f"{base}-V", None)

    if huerfanos_c or huerfanos_v:
        progreso.guardar()


def procesar_pares(sesion, robots, progreso: Progreso, anio_desde: int, anio_hasta: int, max_documentos: int | None, contador: dict) -> None:
    """Recorre valencià (menos años, menos ruido) y solo baja català cuando hay pareja.

    Para cada día con documentos en valencià, se pide la página del mismo día
    en català y se cruzan por ID base. Si valencià no tiene nada ese día, NO
    se pide la página de català: es justo el ahorro de peticiones que importa.
    """
    cfg_v = IDIOMAS["valenciano"]
    cfg_c = IDIOMAS["catalan"]

    logger.info("=== Modo emparejado: valencià primero, català solo si hay pareja ===")
    anios_disponibles = obtener_anios_disponibles(sesion, robots, cfg_v["codigo"])
    anios = [a for a in anios_disponibles if anio_desde <= a <= anio_hasta]
    if not anios:
        anios = list(range(anio_desde, anio_hasta + 1))
    logger.info(f"Años a procesar: {anios}")

    referer_calendario = BASE_URL
    for indice_anio, anio in enumerate(anios):
        if max_documentos is not None and contador["total"] >= max_documentos:
            logger.info("Límite de documentos alcanzado, deteniendo.")
            return

        logger.info(f"--- {anio} ---")
        fechas = obtener_dias_del_anio(sesion, robots, "valenciano", cfg_v["codigo"], anio, referer_calendario)
        referer_calendario = f"{BASE_URL}/diario_boe/calendarios.php?c={cfg_v['codigo']}&a={anio}"
        logger.info(f"{len(fechas)} días con suplemento en valencià/{anio}")

        anio_completo = True
        mes_anterior = None
        for indice_dia, fecha in enumerate(fechas):
            if max_documentos is not None and contador["total"] >= max_documentos:
                logger.info("Límite de documentos alcanzado, deteniendo.")
                anio_completo = False
                break

            if progreso.dia_completado("pares", anio, fecha):
                logger.debug(f"Día ya procesado, se omite: {fecha}")
                continue

            mes_actual = fecha[:7]
            if mes_anterior is not None and mes_actual != mes_anterior:
                espera(DELAY_MES, "cambio de mes")
            mes_anterior = mes_actual

            url_v, docs_v = obtener_documentos_del_dia(sesion, robots, "valenciano", fecha, cfg_v["sufijo"], referer_calendario)

            docs_c_por_base: dict[str, Documento] = {}
            url_c = None
            if docs_v:
                logger.info(f"{fecha}: {len(docs_v)} documento(s) en valencià, comprobando català")
                espera(DELAY_DOCUMENTO, "consultar página de català del mismo día")
                url_c, docs_c = obtener_documentos_del_dia(sesion, robots, "catalan", fecha, cfg_c["sufijo"], url_v)
                docs_c_por_base = {d.id[:-2]: d for d in docs_c}
            else:
                logger.debug(f"{fecha}: sin documentos en valencià")

            dia_incompleto = False
            for doc_v in docs_v:
                if max_documentos is not None and contador["total"] >= max_documentos:
                    dia_incompleto = True
                    break

                base = doc_v.id[:-2]
                doc_c = docs_c_por_base.get(base)
                if doc_c is None:
                    logger.info(f"{fecha}: {doc_v.id} sin pareja en català, se descarta")
                    continue

                for doc, idioma_dir, referer in ((doc_v, "valenciano", url_v), (doc_c, "catalan", url_c)):
                    if max_documentos is not None and contador["total"] >= max_documentos:
                        dia_incompleto = True
                        break
                    destino = CORPUS_DIR / idioma_dir / str(anio) / f"{doc.id}.pdf"
                    if progreso.documento_descargado(doc.id) or destino.exists():
                        logger.debug(f"Ya descargado, se omite: {doc.id}")
                        continue
                    espera(DELAY_DOCUMENTO, "entre documentos")
                    ok = descargar_documento(sesion, robots, doc, destino, referer=referer)
                    if ok:
                        logger.info(f"Descargado: {doc.id} -> {destino}")
                        progreso.marcar_documento(
                            doc.id,
                            {"titulo": doc.titulo, "fecha": fecha, "url": doc.url, "archivo": str(destino)},
                        )
                        contador["total"] += 1
                    else:
                        logger.error(f"No se pudo descargar {doc.id} ({doc.url})")
                        dia_incompleto = True

            if dia_incompleto:
                logger.warning(f"{fecha}: día no marcado como completado (quedan documentos pendientes)")
                anio_completo = False
            else:
                progreso.marcar_dia_completado("pares", anio, fecha)

            if indice_dia < len(fechas) - 1:
                espera(DELAY_DIA, "entre días")

        if anio_completo:
            reconciliar_anio(anio, progreso)
        else:
            logger.info(f"{anio} no se completó del todo en esta ejecución; se pospone la limpieza de huérfanos")

        if indice_anio < len(anios) - 1:
            espera(DELAY_ANIO, "entre años")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anio-desde", type=int, default=2001, help="Año inicial (por defecto 2001)")
    parser.add_argument(
        "--anio-hasta",
        type=int,
        default=2015,
        help="Año final (por defecto 2015: no hay valencià más allá de ese año, así que no hay pareja posible)",
    )
    parser.add_argument(
        "--max-documentos",
        type=int,
        default=None,
        help="Detiene la ejecución tras descargar N documentos en total (útil para pruebas)",
    )
    parser.add_argument("--verbose", action="store_true", help="Logging en modo debug")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configurar_logging(args.verbose)

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    sesion = construir_sesion()

    logger.info("Comprobando robots.txt de boe.es antes de empezar...")
    robots = RobotsChecker(sesion)

    progreso = Progreso(PROGRESS_PATH)
    contador = {"total": 0}

    procesar_pares(sesion, robots, progreso, args.anio_desde, args.anio_hasta, args.max_documentos, contador)

    logger.info(f"Finalizado. Documentos descargados en esta ejecución: {contador['total']}")


if __name__ == "__main__":
    main()
