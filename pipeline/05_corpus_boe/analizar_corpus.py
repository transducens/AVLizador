#!/usr/bin/env python3
"""Analitica del corpus paralelo catala/valencia + informe HTML autonomo.

Lee ../dades/boe/corpus.json (generado por construir_corpus.py) y los
materiales linguisticos de "02_regles_dialectals" (reglas morfologicas,
vocabulario dialectal y formas exclusivas de valencia extraidas del
diccionario Apertium) para:

  1. Sacar estadisticas generales del corpus (documentos, anios, tamanio,
     alineacion de parrafos).
  2. Medir cuanto aparecen realmente en el corpus los marcadores
     dialectales conocidos (vocabulario, morfologia verbal, demostratius,
     locucions), separando textos etiquetados "catalan" de los etiquetados
     "valenciano", para ver si la separacion dialectal se sostiene en la
     practica o hay "fugas" de una variedad a la otra.
  3. Diff palabra a palabra de los parrafos (y, dentro de ellos, frases)
     alineados de un mismo documento (misma norma, traducida dos veces)
     para ver exactamente que palabras cambian entre las dos versiones
     oficiales, catalogadas en los materiales o no.

Genera un unico HTML autonomo (sin CDN, funciona en local sin internet)
con tablas interactivas (filtro + orden) y graficos SVG generados en
Python. Pensado para ejecutarse cuando el corpus este mas completo; se
puede relanzar en cualquier momento, siempre parte de lo que haya en
../dades/boe/corpus.json en ese momento.

Uso:
    python analizar_corpus.py
"""

from __future__ import annotations

import difflib
import itertools
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOE_DIR = Path(__file__).resolve().parent
# Los datos del BOE ahora viven en dades/boe/ (junto a los del resto de
# fuentes del proyecto), no dentro de boe/ como antes.
CORPUS_DIR = BOE_DIR.parent / "dades" / "boe"
CORPUS_JSON = CORPUS_DIR / "corpus.json"
BLEUALIGN_JSONL = CORPUS_DIR / "corpus_bleualign.jsonl"
MATERIALES_DIR = BOE_DIR.parent / "02_regles_dialectals"
SALIDA_HTML = CORPUS_DIR / "analitica_corpus.html"

sys.path.insert(0, str(BOE_DIR))
from texto_comun import es_tabla, segmentar_parrafo, segmentar_parrafos  # noqa: E402


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def cargar_corpus() -> list[dict]:
    if not CORPUS_JSON.exists():
        raise SystemExit(
            f"No existe {CORPUS_JSON}. Ejecuta primero construir_corpus.py sobre el corpus descargado."
        )
    return json.loads(CORPUS_JSON.read_text(encoding="utf-8"))


def cargar_bleualign() -> list[dict] | None:
    """None si el fichero no existe: la pestaña de Bleualign es opcional,
    depende de haber ejecutado aparte alinear_corpus_bleualign.py."""
    if not BLEUALIGN_JSONL.exists():
        return None
    registros = []
    with open(BLEUALIGN_JSONL, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                registros.append(json.loads(linea))
    return registros


def _leer_json_materiales(nombre: str) -> dict:
    # 02_regles_dialectals/ se reorganizó en subcarpetas: lexic/ (JSON de
    # pares de palabras) y fonts/ (material bruto, incl. regles_cat_val.md).
    # Busca primero en la raíz por compatibilidad, luego en esas subcarpetas.
    candidatos = [MATERIALES_DIR / nombre, MATERIALES_DIR / "lexic" / nombre, MATERIALES_DIR / "fonts" / nombre]
    for ruta in candidatos:
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))
    raise SystemExit(f"No existe {nombre} en {MATERIALES_DIR} ni en lexic/ o fonts/.")


def _extraer_tablas_md(texto_md: str) -> dict[str, list[list[str]]]:
    """Devuelve, por cada seccion '## N. Titulo' del markdown, sus filas de tabla
    (celdas ya separadas, sin la fila de cabecera ni la de separadores)."""
    secciones: dict[str, list[list[str]]] = {}
    seccion_actual = None
    filas: list[list[str]] = []
    patron_seccion = re.compile(r"^##\s+\d+\.\s*(.+?)\s*$")
    patron_separador = re.compile(r"^:?-+:?$")

    def cerrar():
        if seccion_actual is not None:
            secciones[seccion_actual] = filas

    for linea in texto_md.splitlines():
        m = patron_seccion.match(linea)
        if m:
            cerrar()
            seccion_actual = m.group(1)
            filas = []
            continue
        if linea.startswith("|"):
            celdas = [c.strip() for c in linea.strip("|").split("|")]
            if all(patron_separador.match(c) for c in celdas):
                continue
            if celdas and celdas[0] in ("Categoria", "Valenciano"):
                continue
            filas.append(celdas)
    cerrar()
    return secciones


def _limpiar_entradas_vocabulario(entradas: list[dict]) -> list[dict]:
    """palabras_traducidas.json trae, en algunas entradas, restos de la
    notacion "raiz/desinencia" de genero (p.ej. "Bonico/a", "Boig/ja")
    partidos por "/" sin distinguir que no son sinonimos independientes:
    quedan como items sueltos "a", "ja"... que, contados en el corpus, no
    significan nada (son preposicion/adverbio y aparecen millones de veces
    sin relacion con la entrada). Comprobado a mano sobre las 29 entradas
    de 1-2 letras del fichero: todo item corto que es una palabra real
    viene capitalizado; los fragmentos de genero siempre quedan en
    minuscula. Se descartan los items de 1-2 letras en minuscula."""

    def es_fragmento(token: str) -> bool:
        return len(token) <= 2 and token[:1].islower()

    limpias = []
    for e in entradas:
        e_limpia = dict(e)
        for campo in ("valenciano", "catalan", "castellano"):
            if campo in e_limpia:
                e_limpia[campo] = [w for w in e_limpia[campo] if w and not es_fragmento(w)]
        limpias.append(e_limpia)
    return limpias


def cargar_materiales() -> dict:
    datos_vocab = _leer_json_materiales("palabras_traducidas.json")
    datos_val = _leer_json_materiales("palabras_val.json")
    texto_md = (MATERIALES_DIR / "fonts" / "regles_cat_val.md").read_text(encoding="utf-8")
    tablas = _extraer_tablas_md(texto_md)

    morfologia = [
        {
            "categoria": f[0],
            "rasgos": f[1],
            "cat": f[2],
            "val": f[3],
            "cobertura": f[4],
            "ejemplo": f[5],
        }
        for f in tablas.get("Verbos y morfologia (terminaciones)", [])
        if len(f) >= 6
    ]
    demostratius = [
        {"valenciano": f[0], "catalan": f[1]}
        for f in tablas.get("Demostratius", [])
        if len(f) >= 2
    ]
    locucions = [
        {"valenciano": f[0], "catalan": f[1], "fuente": f[2] if len(f) > 2 else ""}
        for f in tablas.get("Locucions", [])
        if len(f) >= 2
    ]

    return {
        "vocabulario": _limpiar_entradas_vocabulario(datos_vocab["entradas"]),
        "val_especificas": datos_val["lista_palabras"],
        "val_especificas_meta": {p["palabra"]: p for p in datos_val.get("palabras", [])},
        "morfologia": morfologia,
        "demostratius": demostratius,
        "locucions": locucions,
    }


# ---------------------------------------------------------------------------
# Tokenizacion y frecuencias
# ---------------------------------------------------------------------------

PATRON_TOKEN = re.compile(r"[^\W\d_]+(?:[-'·][^\W\d_]+)*", re.UNICODE)

# Tokenizador "sin perdidas": ademas de palabras, separa numeros, espacios y
# cada signo de puntuacion como su propio token, de forma que "".join(...)
# reconstruye el texto original exacto. Se usa para el diff visual palabra a
# palabra (analizar_diff_textual), donde ademas de detectar que palabra
# cambia hace falta poder repintar la frase completa tal cual.
PATRON_TOKEN_COMPLETO = re.compile(r"[^\W\d_]+(?:[-'·][^\W\d_]+)*|\d+|\s+|.", re.UNICODE | re.DOTALL)


def normalizar(texto: str) -> str:
    return texto.replace("’", "'").replace("‘", "'").lower()


def tokenizar(texto: str) -> list[str]:
    return PATRON_TOKEN.findall(normalizar(texto))


def _es_palabra(token: str) -> bool:
    return bool(token) and token[0].isalpha()


def tokenizar_forma(forma: str) -> tuple[str, ...]:
    return tuple(PATRON_TOKEN.findall(normalizar(forma)))


def recolectar_locuciones_objetivo(materiales: dict) -> dict[int, set[tuple[str, ...]]]:
    """Recorre todos los materiales linguisticos y devuelve, agrupadas por
    numero de palabras (n), las locuciones (n>=2) que hace falta poder
    contar en el corpus. Se usa para indexar solo esas locuciones concretas
    en una unica pasada por el corpus, en vez de repetir una busqueda de
    texto completo por cada una (demasiado lento para un corpus grande)."""
    objetivo: dict[int, set[tuple[str, ...]]] = defaultdict(set)

    def registrar(forma: str) -> None:
        tokens = tokenizar_forma(forma)
        if len(tokens) >= 2:
            objetivo[len(tokens)].add(tokens)

    for e in materiales["vocabulario"]:
        for w in e["valenciano"] + e["catalan"]:
            registrar(w)
    for w in materiales["val_especificas"]:
        registrar(w)
    for d in materiales["demostratius"]:
        registrar(d["valenciano"])
        registrar(d["catalan"])
    for loc in materiales["locucions"]:
        registrar(loc["valenciano"])
        registrar(loc["catalan"])
    for r in materiales["morfologia"]:
        registrar(r["cat"].lstrip("-"))
        registrar(r["val"].lstrip("-"))

    return dict(objetivo)


class CorpusIndexado:
    """Indice de frecuencias del corpus: Counter de palabras sueltas (global
    y por anio) mas Counter de las locuciones concretas que interesan
    (`locuciones_objetivo`), acumulado en una unica pasada por documento."""

    def __init__(self, locuciones_objetivo: dict[int, set[tuple[str, ...]]]) -> None:
        self.locuciones_objetivo = locuciones_objetivo
        self.frecuencia: dict[str, Counter] = {"catalan": Counter(), "valenciano": Counter()}
        self.frecuencia_por_anio: dict[tuple[str, int], Counter] = defaultdict(Counter)
        self.frecuencia_locucion: dict[str, Counter] = {"catalan": Counter(), "valenciano": Counter()}
        self.num_documentos = 0
        self.anios: set[int] = set()
        self.paginas_totales = 0
        self.caracteres_totales = {"catalan": 0, "valenciano": 0}
        self.tokens_totales = {"catalan": 0, "valenciano": 0}
        self.docs_por_anio: Counter = Counter()
        self.docs_alineados_por_posicion = 0
        self.pares_parrafos_alineados: list[tuple[str, str, list[str], list[str]]] = []
        self.parrafos_tabla_excluidos = {"catalan": 0, "valenciano": 0}

    def _acumular_locuciones(self, tokens: list[str], idioma: str) -> None:
        total = len(tokens)
        contador = self.frecuencia_locucion[idioma]
        for n, conjunto in self.locuciones_objetivo.items():
            if n > total:
                continue
            for i in range(total - n + 1):
                ventana = tuple(tokens[i : i + n])
                if ventana in conjunto:
                    contador[ventana] += 1

    def indexar(self, corpus: list[dict]) -> None:
        for doc in corpus:
            self.num_documentos += 1
            anio = doc["anio"]
            self.anios.add(anio)
            self.docs_por_anio[anio] += 1

            parrafos_por_idioma = {}
            for idioma in ("catalan", "valenciano"):
                info = doc[idioma]
                self.paginas_totales += info.get("num_paginas", 0)

                parrafos_todos = segmentar_parrafos(info["texto"])
                parrafos = [p for p in parrafos_todos if not es_tabla(p)]
                self.parrafos_tabla_excluidos[idioma] += len(parrafos_todos) - len(parrafos)
                texto_limpio = "\n".join(parrafos)
                self.caracteres_totales[idioma] += len(texto_limpio)

                tokens = PATRON_TOKEN.findall(normalizar(texto_limpio))
                self.tokens_totales[idioma] += len(tokens)

                contador_doc = Counter(tokens)
                self.frecuencia[idioma].update(contador_doc)
                self.frecuencia_por_anio[(idioma, anio)].update(contador_doc)
                self._acumular_locuciones(tokens, idioma)

                parrafos_por_idioma[idioma] = parrafos

            if (
                len(parrafos_por_idioma["catalan"]) == len(parrafos_por_idioma["valenciano"])
                and len(parrafos_por_idioma["catalan"]) > 0
            ):
                self.docs_alineados_por_posicion += 1
                self.pares_parrafos_alineados.append(
                    (doc["id"], doc["fecha"], parrafos_por_idioma["catalan"], parrafos_por_idioma["valenciano"])
                )


def contar_forma(forma: str, indice: CorpusIndexado, idioma: str) -> int:
    """Cuenta una forma (palabra o locucion) en el idioma indicado: Counter
    de palabras sueltas si es una sola palabra, Counter de locuciones
    (precalculado en CorpusIndexado.indexar) si son varias."""
    tokens = tokenizar_forma(forma)
    if not tokens:
        return 0
    if len(tokens) == 1:
        return indice.frecuencia[idioma].get(tokens[0], 0)
    return indice.frecuencia_locucion[idioma].get(tokens, 0)


def contar_sinonimos(formas: list[str], indice: CorpusIndexado, idioma: str) -> int:
    return sum(contar_forma(f, indice, idioma) for f in formas)


# ---------------------------------------------------------------------------
# Analisis
# ---------------------------------------------------------------------------

def fidelidad(uso_lado_esperado: int, uso_lado_contrario: int) -> float | None:
    total = uso_lado_esperado + uso_lado_contrario
    if total == 0:
        return None
    return round(100 * uso_lado_esperado / total, 1)


def analizar_vocabulario(entradas: list[dict], indice: CorpusIndexado) -> dict:
    filas = []
    for e in entradas:
        uso_val = contar_sinonimos(e["valenciano"], indice, "valenciano")
        uso_cat_en_val = contar_sinonimos(e["catalan"], indice, "valenciano")
        uso_cat = contar_sinonimos(e["catalan"], indice, "catalan")
        uso_val_en_cat = contar_sinonimos(e["valenciano"], indice, "catalan")
        total = uso_val + uso_cat_en_val + uso_cat + uso_val_en_cat
        if total == 0:
            continue
        filas.append(
            {
                "valenciano": " / ".join(e["valenciano"]),
                "catalan": " / ".join(e["catalan"]),
                "castellano": " / ".join(e.get("castellano", [])),
                "categoria": e["categoria"],
                "uso_val_en_val": uso_val,
                "uso_cat_en_val": uso_cat_en_val,
                "uso_cat_en_cat": uso_cat,
                "uso_val_en_cat": uso_val_en_cat,
                "total": total,
                "fidelidad_val": fidelidad(uso_val, uso_val_en_cat),
                "fidelidad_cat": fidelidad(uso_cat, uso_cat_en_val),
            }
        )
    filas.sort(key=lambda f: -f["total"])
    return {
        "filas": filas,
        "total_entradas": len(entradas),
        "entradas_con_uso": len(filas),
        "suma_uso_val_en_val": sum(f["uso_val_en_val"] for f in filas),
        "suma_uso_cat_en_val": sum(f["uso_cat_en_val"] for f in filas),
        "suma_uso_cat_en_cat": sum(f["uso_cat_en_cat"] for f in filas),
        "suma_uso_val_en_cat": sum(f["uso_val_en_cat"] for f in filas),
    }


def analizar_val_especificas(lista_palabras: list[str], meta: dict, indice: CorpusIndexado) -> dict:
    filas = []
    for forma in lista_palabras:
        uso_val = contar_forma(forma, indice, "valenciano")
        uso_cat = contar_forma(forma, indice, "catalan")
        total = uso_val + uso_cat
        if total == 0:
            continue
        info = meta.get(forma, {})
        filas.append(
            {
                "forma": forma,
                "categoria": info.get("categoria", ""),
                "paradigma": info.get("paradigma", ""),
                "uso_val": uso_val,
                "uso_cat": uso_cat,
                "total": total,
                "fidelidad": fidelidad(uso_val, uso_cat),
            }
        )
    filas.sort(key=lambda f: -f["total"])
    return {
        "filas": filas,
        "total_formas": len(lista_palabras),
        "formas_con_uso": len(filas),
        "suma_uso_val": sum(f["uso_val"] for f in filas),
        "suma_uso_cat": sum(f["uso_cat"] for f in filas),
    }


_PATRON_EPSILON = re.compile(r"^-?[∅]$")


def analizar_morfologia(reglas: list[dict], indice: CorpusIndexado) -> dict:
    filas = []
    for r in reglas:
        cat_suf = r["cat"].strip()
        val_suf = r["val"].strip()
        contable = not (_PATRON_EPSILON.match(cat_suf) or _PATRON_EPSILON.match(val_suf))
        uso_cat = uso_val = None
        fidelidad_cat = None
        if contable:
            cat_limpio = cat_suf.lstrip("-").lower()
            val_limpio = val_suf.lstrip("-").lower()
            if " " in cat_limpio or " " in val_limpio:
                uso_cat = contar_forma(cat_limpio, indice, "catalan")
                uso_val = contar_forma(val_limpio, indice, "valenciano")
                uso_cat_en_val = contar_forma(cat_limpio, indice, "valenciano")
            else:
                uso_cat = sum(f for palabra, f in indice.frecuencia["catalan"].items() if palabra.endswith(cat_limpio))
                uso_val = sum(f for palabra, f in indice.frecuencia["valenciano"].items() if palabra.endswith(val_limpio))
                uso_cat_en_val = sum(
                    f for palabra, f in indice.frecuencia["valenciano"].items() if palabra.endswith(cat_limpio)
                )
            fidelidad_cat = fidelidad(uso_cat, uso_cat_en_val)
        filas.append(
            {
                **r,
                "contable": contable,
                "uso_cat": uso_cat,
                "uso_val": uso_val,
                "fidelidad_cat": fidelidad_cat,
            }
        )
    filas.sort(key=lambda f: -((f["uso_cat"] or 0) + (f["uso_val"] or 0)))
    return {"filas": filas}


def analizar_demostratius(demostratius: list[dict], indice: CorpusIndexado) -> dict:
    filas = []
    for d in demostratius:
        uso_val_en_val = contar_forma(d["valenciano"], indice, "valenciano")
        uso_cat_en_val = contar_forma(d["catalan"], indice, "valenciano")
        uso_val_en_cat = contar_forma(d["valenciano"], indice, "catalan")
        uso_cat_en_cat = contar_forma(d["catalan"], indice, "catalan")
        filas.append(
            {
                "valenciano": d["valenciano"],
                "catalan": d["catalan"],
                "uso_val_en_val": uso_val_en_val,
                "uso_cat_en_val": uso_cat_en_val,
                "uso_val_en_cat": uso_val_en_cat,
                "uso_cat_en_cat": uso_cat_en_cat,
            }
        )

    series_anio = []
    for anio in sorted(indice.anios):
        c_val = indice.frecuencia_por_anio.get(("valenciano", anio), Counter())
        c_cat = indice.frecuencia_por_anio.get(("catalan", anio), Counter())
        est_val = sum(c_val.get(d["valenciano"], 0) for d in demostratius)
        aquest_val = sum(c_val.get(d["catalan"], 0) for d in demostratius)
        est_cat = sum(c_cat.get(d["valenciano"], 0) for d in demostratius)
        aquest_cat = sum(c_cat.get(d["catalan"], 0) for d in demostratius)
        total_val = est_val + aquest_val
        total_cat = est_cat + aquest_cat
        series_anio.append(
            {
                "anio": anio,
                "pct_est_en_val": round(100 * est_val / total_val, 1) if total_val else None,
                "pct_est_en_cat": round(100 * est_cat / total_cat, 1) if total_cat else None,
                "muestras_val": total_val,
                "muestras_cat": total_cat,
            }
        )

    return {"filas": filas, "series_anio": series_anio}


def analizar_locucions(locucions: list[dict], indice: CorpusIndexado) -> dict:
    filas = []
    for loc in locucions:
        uso_val_en_val = contar_forma(loc["valenciano"], indice, "valenciano")
        uso_cat_en_val = contar_forma(loc["catalan"], indice, "valenciano")
        uso_val_en_cat = contar_forma(loc["valenciano"], indice, "catalan")
        uso_cat_en_cat = contar_forma(loc["catalan"], indice, "catalan")
        filas.append(
            {
                **loc,
                "uso_val_en_val": uso_val_en_val,
                "uso_cat_en_val": uso_cat_en_val,
                "uso_val_en_cat": uso_val_en_cat,
                "uso_cat_en_cat": uso_cat_en_cat,
            }
        )
    return {"filas": filas}


MAX_TOKENS_SUSTITUCION = 4


def _construir_lookup_conocidos(materiales: dict) -> set[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Pares (catalan, valencia) ya catalogados en los materiales linguisticos
    (como tuplas de tokens normalizados), para poder marcar si una
    sustitucion encontrada por diff ya era conocida o es un hallazgo nuevo."""
    conocidos = set()
    for e in materiales["vocabulario"]:
        for val_forma, cat_forma in itertools.product(e["valenciano"], e["catalan"]):
            conocidos.add((tokenizar_forma(cat_forma), tokenizar_forma(val_forma)))
    for d in materiales["demostratius"]:
        conocidos.add((tokenizar_forma(d["catalan"]), tokenizar_forma(d["valenciano"])))
    for loc in materiales["locucions"]:
        conocidos.add((tokenizar_forma(loc["catalan"]), tokenizar_forma(loc["valenciano"])))
    return conocidos


def _construir_reglas_morfologicas_simples(materiales: dict) -> list[dict]:
    """Reglas de terminacion de una sola palabra (sin espacios, sin '∅'),
    listas para comprobar por sufijo+raiz sobre un par de palabras suelto."""
    reglas = []
    for r in materiales["morfologia"]:
        cat_limpio = r["cat"].strip().lstrip("-").lower()
        val_limpio = r["val"].strip().lstrip("-").lower()
        if not cat_limpio or not val_limpio or " " in cat_limpio or " " in val_limpio:
            continue
        if _PATRON_EPSILON.match(r["cat"].strip()) or _PATRON_EPSILON.match(r["val"].strip()):
            continue
        reglas.append({"cat": cat_limpio, "val": val_limpio, "rasgos": f'{r["categoria"]} · {r["rasgos"]}'})
    return reglas


def _match_regla_morfologica(cat_tok: str, val_tok: str, reglas_simples: list[dict]) -> str | None:
    for r in reglas_simples:
        if not cat_tok.endswith(r["cat"]) or not val_tok.endswith(r["val"]):
            continue
        raiz_cat = cat_tok[: len(cat_tok) - len(r["cat"])]
        raiz_val = val_tok[: len(val_tok) - len(r["val"])]
        if raiz_cat and raiz_cat == raiz_val:
            return r["rasgos"]
    return None


def _marcar_html(tokens_mostrar: list[str], rangos_resaltados: list[tuple[int, int, str]]) -> str:
    """Reconstruye el HTML de una frase a partir de sus tokens originales
    (con acentos/mayusculas/puntuacion intactos), envolviendo en <mark
    class="..."> los rangos [inicio, fin) marcados como distintos."""
    resaltado_de = {}
    for inicio, fin, clase in rangos_resaltados:
        for i in range(inicio, fin):
            resaltado_de[i] = clase

    partes = []
    clase_actual = None
    buffer: list[str] = []

    def cerrar():
        if not buffer:
            return
        texto = _escapar("".join(buffer))
        if clase_actual:
            partes.append(f'<mark class="{clase_actual}">{texto}</mark>')
        else:
            partes.append(texto)
        buffer.clear()

    for i, tok in enumerate(tokens_mostrar):
        clase = resaltado_de.get(i)
        if clase != clase_actual:
            cerrar()
            clase_actual = clase
        buffer.append(tok)
    cerrar()
    return "".join(partes)


VENTANA_CONTEXTO_PAR = 8  # tokens a cada lado del cambio, para el ejemplo de la tabla de pares


def _fragmento_contexto(tokens: list[str], ini: int, fin: int, clase: str, ventana: int = VENTANA_CONTEXTO_PAR) -> str:
    """Recorta `tokens` alrededor de [ini, fin) con una ventana de
    `ventana` tokens a cada lado, marcando el cambio (vore `_marcar_html`)
    y anadiendo "…" cuando se recorta. Pensado para los ejemplos de la
    tabla de pares de sustitucion: no hace falta la frase entera (a veces
    un parrafo legal larguisimo) para ver el cambio, y el HTML resultante
    pesa una fraccion de lo que pesaria la frase completa x 44.200 filas."""
    a = max(0, ini - ventana)
    b = min(len(tokens), fin + ventana)
    html = _marcar_html(tokens[a:b], [(ini - a, fin - a, clase)])
    if a > 0:
        html = "…" + html
    if b < len(tokens):
        html = html + "…"
    return html


def analizar_diff_textual(indice: CorpusIndexado, materiales: dict) -> dict:
    """Diff palabra a palabra (difflib) de cada documento cuyos parrafos se
    alinean 1 a 1, para ver exactamente que cambia entre la version
    catalana y la valenciana de un mismo texto oficial: tanto un resumen
    agregado (que pares de palabras cambian, en que documentos) como un
    "visor" con el HTML de cada unidad para leerla resaltada tal cual.

    El ejemplo de cada par en `filas_pares` (`ejemplo_frase_cat`/
    `ejemplo_frase_val`) NO es la frase completa, es un fragmento recortado
    alrededor del cambio (vore `_fragmento_contexto`) -- con ~44.000 pares
    distintos, guardar la frase entera (a veces un parrafo legal larguisimo)
    por cada uno multiplicaba el peso del informe HTML sin anadir nada que
    el fragmento ya no enseñe.

    SEÑALES DE CONFIANZA DIALECTAL (02/10/2026, vore conversacion sobre
    "estilo del traductor vs. variacion dialectal" -- acordado implementar
    3 de las 4 propuestas, como columnas visibles y ordenables en vez de
    una sola puntuacion opaca, para que se pueda juzgar a ojo si cada una
    aporta o no antes de fiarse de ella):

      1. `ratio_medio_frase`: similitud media (difflib) de las frases donde
         aparece el par, APARTE del propio cambio. Un par que casi siempre
         ocurre en frases practicamente identicas salvo por el es mas
         fiable que uno que suele aparecer en frases muy reescritas (ahi la
         coincidencia de palabras podria ser casualidad, no el patron real).
      2. `pct_cambio_aislado`: de todas sus apariciones, en que % fue el
         UNICO cambio de la frase (ni insercion ni otra sustitucion a la
         vez). Señal de dispersion -- un par casi siempre aislado sugiere
         sustitucion puntual y limpia; uno que casi nunca lo es sugiere que
         va siempre acompañado de mas reescritura alrededor (duda planteada
         explicitamente sobre si esta señal aporta de verdad: se deja como
         columna aparte, visible y ordenable, no fusionada en una sola
         cifra, precisamente para poder decidirlo mirando datos reales).
      3. `en_glosario`/`regla_morfologica`/`novedad`: YA EXISTIAN --
         coincide con una regla dialectal ya confirmada en
         `02_regles_dialectals`, o es "novedad" (no catalogada todavia).

    Deliberadamente NO implementada en esta tanda: la 4a señal propuesta
    (consistencia a lo largo de los años, para distinguir una regla
    dialectal estable de la manía de estilo de un traductor concreto en un
    periodo concreto) -- pendiente de una proxima iteracion.

    Alineacion en dos niveles (parrafo primero, frase despues), no una
    unica posicion global de frase: un documento puede tener el mismo
    numero de PARRAFOS en los dos idiomas (la unidad de traduccion natural
    del BOE: cada articulo/parrafo es 1 a 1) aunque el numero de FRASES
    difiera un poco parrafo a parrafo. Solo se opera sobre los documentos
    con el mismo numero de parrafos (`indice.pares_parrafos_alineados`, el
    mismo subconjunto que ya se reporta en el resumen general); en el
    resto no hay forma fiable de saber que parrafo corresponde a cual sin
    un alineador mas fino. Dentro de cada parrafo ya emparejado, si tambien
    tiene el mismo numero de frases en los dos idiomas se comparan frase a
    frase; si no, se compara el parrafo entero como una sola unidad (evita
    emparejar mal frase a frase sin perder ese parrafo del analisis).

    La comparacion palabra a palabra se hace sobre un tokenizador "sin
    perdidas" (palabras, numeros, espacios y cada signo de puntuacion como
    token aparte: PATRON_TOKEN_COMPLETO) para poder repintar la unidad
    exactamente como estaba, resaltando solo lo que cambia; para el
    recuento agregado de pares de palabras se filtran de cada bloque
    distinto los tokens que no son palabras (espacios, puntuacion), asi que
    un cambio de puntuacion suelto no cuenta como sustitucion lexica.
    """
    conocidos = _construir_lookup_conocidos(materiales)
    reglas_simples = _construir_reglas_morfologicas_simples(materiales)

    contador_pares: Counter = Counter()
    ejemplo_por_par: dict[tuple, tuple[str, str, str]] = {}
    suma_ratio_por_par: dict[tuple, float] = defaultdict(float)
    aislados_por_par: dict[tuple, int] = defaultdict(int)
    stats_doc: dict[str, dict] = {}
    visor: dict[str, dict] = {}

    total_frases = 0
    frases_identicas = 0
    total_inserciones = 0
    total_eliminaciones = 0
    suma_ratios = 0.0

    for doc_id, fecha, parrafos_cat, parrafos_val in indice.pares_parrafos_alineados:
        stats_doc[doc_id] = {
            "id": doc_id,
            "fecha": fecha,
            "frases": 0,
            "frases_identicas": 0,
            "sustituciones": 0,
            "inserciones": 0,
            "eliminaciones": 0,
            "ratio_medio": 0.0,
        }
        suma_ratio_doc = 0.0
        frases_visor = []
        idx = 0

        for num_parrafo, (pc, pv) in enumerate(zip(parrafos_cat, parrafos_val), start=1):
            frases_c = segmentar_parrafo(pc)
            frases_v = segmentar_parrafo(pv)
            if len(frases_c) == len(frases_v) and len(frases_c) > 0:
                unidades = list(zip(frases_c, frases_v))
            else:
                unidades = [(pc, pv)]

            for fc, fv in unidades:
                idx += 1
                total_frases += 1
                stats_doc[doc_id]["frases"] += 1

                if normalizar(fc.strip()) == normalizar(fv.strip()):
                    frases_identicas += 1
                    stats_doc[doc_id]["frases_identicas"] += 1
                    suma_ratios += 1.0
                    suma_ratio_doc += 1.0
                    frases_visor.append(
                        {
                            "idx": idx,
                            "parrafo": num_parrafo,
                            "dif": False,
                            "ratio": 100.0,
                            "html_cat": _escapar(fc),
                            "html_val": _escapar(fv),
                        }
                    )
                    continue

                disp_c = PATRON_TOKEN_COMPLETO.findall(fc)
                disp_v = PATRON_TOKEN_COMPLETO.findall(fv)
                norm_c = [normalizar(t) for t in disp_c]
                norm_v = [normalizar(t) for t in disp_v]
                sm = difflib.SequenceMatcher(None, norm_c, norm_v, autojunk=False)
                ratio = sm.ratio()
                suma_ratios += ratio
                suma_ratio_doc += ratio

                rangos_cat: list[tuple[int, int, str]] = []
                rangos_val: list[tuple[int, int, str]] = []

                opcodes = sm.get_opcodes()
                num_cambios_frase = sum(1 for tag, *_ in opcodes if tag != "equal")

                for tag, i1, i2, j1, j2 in opcodes:
                    if tag == "equal":
                        continue
                    if tag == "insert":
                        rangos_val.append((j1, j2, "ins"))
                        n = sum(1 for t in norm_v[j1:j2] if _es_palabra(t))
                        total_inserciones += n
                        stats_doc[doc_id]["inserciones"] += n
                    elif tag == "delete":
                        rangos_cat.append((i1, i2, "del"))
                        n = sum(1 for t in norm_c[i1:i2] if _es_palabra(t))
                        total_eliminaciones += n
                        stats_doc[doc_id]["eliminaciones"] += n
                    elif tag == "replace":
                        rangos_cat.append((i1, i2, "chg"))
                        rangos_val.append((j1, j2, "chg"))
                        palabras_c = tuple(t for t in norm_c[i1:i2] if _es_palabra(t))
                        palabras_v = tuple(t for t in norm_v[j1:j2] if _es_palabra(t))
                        if (
                            palabras_c
                            and palabras_v
                            and len(palabras_c) <= MAX_TOKENS_SUSTITUCION
                            and len(palabras_v) <= MAX_TOKENS_SUSTITUCION
                        ):
                            clave = (palabras_c, palabras_v)
                            contador_pares[clave] += 1
                            stats_doc[doc_id]["sustituciones"] += 1
                            suma_ratio_por_par[clave] += ratio
                            if num_cambios_frase == 1:
                                aislados_por_par[clave] += 1
                            if clave not in ejemplo_por_par:
                                ejemplo_por_par[clave] = (
                                    doc_id,
                                    _fragmento_contexto(disp_c, i1, i2, "chg"),
                                    _fragmento_contexto(disp_v, j1, j2, "chg"),
                                )

                frases_visor.append(
                    {
                        "idx": idx,
                        "parrafo": num_parrafo,
                        "dif": True,
                        "ratio": round(100 * ratio, 1),
                        "html_cat": _marcar_html(disp_c, rangos_cat),
                        "html_val": _marcar_html(disp_v, rangos_val),
                    }
                )

        stats_doc[doc_id]["ratio_medio"] = (
            round(100 * suma_ratio_doc / stats_doc[doc_id]["frases"], 1) if stats_doc[doc_id]["frases"] else None
        )
        visor[doc_id] = {"fecha": fecha, "frases": frases_visor}

    filas_pares = []
    for (cat_tok, val_tok), frecuencia in contador_pares.items():
        clave = (cat_tok, val_tok)
        doc_id, ejemplo_cat, ejemplo_val = ejemplo_por_par[clave]
        conocido = (cat_tok, val_tok) in conocidos
        regla = (
            _match_regla_morfologica(cat_tok[0], val_tok[0], reglas_simples)
            if len(cat_tok) == 1 and len(val_tok) == 1
            else None
        )
        filas_pares.append(
            {
                "catalan": " ".join(cat_tok),
                "valenciano": " ".join(val_tok),
                "frecuencia": frecuencia,
                "ratio_medio_frase": round(100 * suma_ratio_por_par[clave] / frecuencia, 1),
                "pct_cambio_aislado": round(100 * aislados_por_par[clave] / frecuencia, 1),
                "en_glosario": conocido,
                "regla_morfologica": regla,
                "novedad": not conocido and not regla,
                "ejemplo_doc": doc_id,
                "ejemplo_frase_cat": ejemplo_cat,
                "ejemplo_frase_val": ejemplo_val,
            }
        )
    filas_pares.sort(key=lambda f: -f["frecuencia"])

    filas_documentos = sorted(stats_doc.values(), key=lambda d: -d["sustituciones"])

    return {
        "docs_analizados": len(indice.pares_parrafos_alineados),
        "docs_totales": indice.num_documentos,
        "total_frases": total_frases,
        "frases_identicas": frases_identicas,
        "ratio_medio": round(100 * suma_ratios / total_frases, 1) if total_frases else None,
        "total_inserciones": total_inserciones,
        "total_eliminaciones": total_eliminaciones,
        "pares_distintos": len(filas_pares),
        "pares_nuevos": sum(1 for f in filas_pares if f["novedad"]),
        "filas_pares": filas_pares,
        "filas_documentos": filas_documentos,
        "visor": visor,
    }


UMBRAL_REVISION_BLEUALIGN = 0.3
MAX_CANDIDATOS_REVISION = 400


def _marcar_par_html(fc: str, fv: str) -> tuple[bool, str, str]:
    """Devuelve (hay_diferencias, html_catalan, html_valenciano) resaltando
    palabra a palabra lo que cambia entre las dos frases de un par (mismo
    mecanismo que el visor de la pestaña "Diff textual")."""
    if normalizar(fc.strip()) == normalizar(fv.strip()):
        return False, _escapar(fc), _escapar(fv)

    disp_c = PATRON_TOKEN_COMPLETO.findall(fc)
    disp_v = PATRON_TOKEN_COMPLETO.findall(fv)
    norm_c = [normalizar(t) for t in disp_c]
    norm_v = [normalizar(t) for t in disp_v]
    sm = difflib.SequenceMatcher(None, norm_c, norm_v, autojunk=False)

    rangos_cat: list[tuple[int, int, str]] = []
    rangos_val: list[tuple[int, int, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            rangos_val.append((j1, j2, "ins"))
        elif tag == "delete":
            rangos_cat.append((i1, i2, "del"))
        elif tag == "replace":
            rangos_cat.append((i1, i2, "chg"))
            rangos_val.append((j1, j2, "chg"))

    return True, _marcar_html(disp_c, rangos_cat), _marcar_html(disp_v, rangos_val)


def _completar_visor_con_bleualign(visor: dict[str, dict], registros_bleu: list[dict] | None) -> None:
    """Amplia `visor` (construido por `analizar_diff_textual`, solo con los
    documentos de parrafos alineados 1 a 1 -- en la practica, ~1/3 del
    corpus) anadiendo TODOS los documentos que Bleualign si ha podido
    alinear a nivel de frase (~520 de 521, casi el corpus entero). Antes de
    esto, un documento con un parrafo de mas o de menos en un idioma
    desaparecia en silencio del visor sin ninguna indicacion -- era la
    causa real de que "muchos documentos no se pudieran inspeccionar".

    Cada documento del visor queda marcado con su `metode` ("parrafs" o
    "bleualign") porque la confianza no es la misma: la alineacion por
    parrafos es exacta (misma estructura en los dos idiomas), la de
    Bleualign es por similitud y puede fallar en frases cortas o sin raiz
    lexica comun (vore docstring de `analizar_bleualign`)."""
    for doc in visor.values():
        doc["metode"] = "parrafs"

    if not registros_bleu:
        return

    por_documento: dict[str, list[dict]] = defaultdict(list)
    for r in registros_bleu:
        if r["documento_id"] not in visor:
            por_documento[r["documento_id"]].append(r)

    for doc_id, registros in por_documento.items():
        registros.sort(key=lambda r: r["id"])
        frases_visor = []
        for idx, r in enumerate(registros):
            dif, html_cat, html_val = _marcar_par_html(r["texto_catalan"], r["texto_valenciano"])
            frases_visor.append(
                {
                    "idx": idx,
                    "parrafo": None,
                    "dif": dif,
                    "ratio": round(100 * r["similitud"], 1),
                    "html_cat": html_cat,
                    "html_val": html_val,
                }
            )
        visor[doc_id] = {"fecha": registros[0]["fecha"], "frases": frases_visor, "metode": "bleualign"}


VISOR_SUBDIR = "analitica_corpus_visor"


def _resumen_visor(visor: dict[str, dict]) -> dict[str, dict]:
    """Version ligera de `visor` para embeber en el HTML: solo lo que hace
    falta para poblar el <select> del visor (id, fecha, metodo, cuantas
    frases y cuantas con diferencias) -- NUNCA las frases en si, que es lo
    que pesa (vore `_exportar_visor_a_ficheros`)."""
    return {
        doc_id: {
            "fecha": doc["fecha"],
            "metode": doc["metode"],
            "num_frases": len(doc["frases"]),
            "num_dif": sum(1 for f in doc["frases"] if f["dif"]),
        }
        for doc_id, doc in visor.items()
    }


def _exportar_visor_a_ficheros(visor: dict[str, dict], directorio: Path) -> None:
    """Escribe un .json por documento con sus frases (lo pesado del visor,
    vore docstring del modulo) para que el HTML las cargue con fetch() solo
    cuando se elige ese documento, en vez de meter las 322.300 frases del
    corpus entero en el propio HTML -- eso ya se probo (ver historial) y
    disparaba el fichero a mas de 180 MB."""
    directorio.mkdir(parents=True, exist_ok=True)
    existentes = {p.stem for p in directorio.glob("*.json")}
    for doc_id, doc in visor.items():
        (directorio / f"{doc_id}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )
        existentes.discard(doc_id)
    for stem in existentes:
        (directorio / f"{stem}.json").unlink()


def analizar_bleualign(registros: list[dict] | None) -> dict | None:
    """Analiza ../dades/boe/corpus_bleualign.jsonl (generado aparte por
    alinear_corpus_bleualign.py): cobertura, distribucion de similitud,
    resumen por documento, y una lista acotada de "candidatos a revision"
    (similitud baja) para inspeccionar a ojo la calidad de lo que decide
    Bleualign, no solo confiar en el numero agregado.

    Un matiz importante que se compureba aqui mismo: un par con similitud
    (Jaccard) 0.0 no es necesariamente un error de Bleualign -- frases
    cortas como "1." o alternancias dialectales sin raiz comun comparten
    cero palabras aunque el emparejamiento sea correcto. Por eso los
    candidatos a revision se filtran para exigir que las DOS frases
    tengan al menos alguna palabra real (no solo numeros/puntuacion):
    asi la lista se centra en los casos donde de verdad hay contenido
    para comparar y aun asi no se parece nada.
    """
    if not registros:
        return None

    stats_doc: dict[str, dict] = {}
    buckets: Counter = Counter()
    suma_similitud = 0.0
    candidatos = []

    for r in registros:
        doc_id = r["documento_id"]
        d = stats_doc.setdefault(
            doc_id,
            {"id": doc_id, "fecha": r["fecha"], "pares": 0, "_suma": 0.0, "similitud_minima": 1.0},
        )
        d["pares"] += 1
        d["_suma"] += r["similitud"]
        d["similitud_minima"] = min(d["similitud_minima"], r["similitud"])

        buckets[round(r["similitud"], 1)] += 1
        suma_similitud += r["similitud"]

        if r["similitud"] < UMBRAL_REVISION_BLEUALIGN:
            tiene_palabras_cat = bool(PATRON_TOKEN.findall(normalizar(r["texto_catalan"])))
            tiene_palabras_val = bool(PATRON_TOKEN.findall(normalizar(r["texto_valenciano"])))
            if tiene_palabras_cat and tiene_palabras_val:
                candidatos.append(r)

    filas_documentos = []
    for d in stats_doc.values():
        d["similitud_media"] = round(d["_suma"] / d["pares"], 3)
        d["similitud_minima"] = round(d["similitud_minima"], 3)
        del d["_suma"]
        filas_documentos.append(d)
    filas_documentos.sort(key=lambda d: d["similitud_media"])

    candidatos.sort(key=lambda r: r["similitud"])
    total_candidatos = len(candidatos)
    filas_revision = []
    for r in candidatos[:MAX_CANDIDATOS_REVISION]:
        _, html_cat, html_val = _marcar_par_html(r["texto_catalan"], r["texto_valenciano"])
        filas_revision.append(
            {
                "documento_id": r["documento_id"],
                "fecha": r["fecha"],
                "similitud": r["similitud"],
                "html_catalan": html_cat,
                "html_valenciano": html_val,
            }
        )

    similitudes = sorted(r["similitud"] for r in registros)
    n = len(similitudes)
    mediana = similitudes[n // 2] if n % 2 else (similitudes[n // 2 - 1] + similitudes[n // 2]) / 2

    return {
        "total_pares": len(registros),
        "total_documentos": len(stats_doc),
        "similitud_media": round(suma_similitud / len(registros), 3),
        "similitud_mediana": round(mediana, 3),
        "buckets": dict(sorted(buckets.items())),
        "filas_documentos": filas_documentos,
        "filas_revision": filas_revision,
        "total_candidatos_revision": total_candidatos,
    }


def estadisticas_generales(corpus: list[dict], indice: CorpusIndexado) -> dict:
    return {
        "total_pares": indice.num_documentos,
        "anio_min": min(indice.anios) if indice.anios else None,
        "anio_max": max(indice.anios) if indice.anios else None,
        "docs_por_anio": dict(sorted(indice.docs_por_anio.items())),
        "paginas_totales": indice.paginas_totales,
        "caracteres_totales": indice.caracteres_totales,
        "tokens_totales": indice.tokens_totales,
        "vocabulario_unico": {
            idioma: len(indice.frecuencia[idioma]) for idioma in ("catalan", "valenciano")
        },
        "docs_alineados_por_posicion": indice.docs_alineados_por_posicion,
        "parrafos_tabla_excluidos": indice.parrafos_tabla_excluidos,
    }


# ---------------------------------------------------------------------------
# Generacion de HTML
# ---------------------------------------------------------------------------

def _escapar(texto) -> str:
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _svg_barras(datos: dict[int, int], titulo: str, color: str = "#3b6ea5") -> str:
    if not datos:
        return "<p>Sin datos.</p>"
    anios = sorted(datos)
    valores = [datos[a] for a in anios]
    max_valor = max(valores) or 1
    ancho_barra = 28
    espacio = 8
    alto = 220
    ancho = len(anios) * (ancho_barra + espacio) + espacio
    barras = []
    for i, (anio, valor) in enumerate(zip(anios, valores)):
        x = espacio + i * (ancho_barra + espacio)
        h = round((valor / max_valor) * (alto - 40))
        y = alto - 30 - h
        barras.append(
            f'<rect x="{x}" y="{y}" width="{ancho_barra}" height="{h}" fill="{color}" rx="2">'
            f"<title>{anio}: {valor}</title></rect>"
            f'<text x="{x + ancho_barra/2}" y="{alto-14}" font-size="11" text-anchor="middle" class="etiqueta-eje">{anio}</text>'
            f'<text x="{x + ancho_barra/2}" y="{y-4}" font-size="11" text-anchor="middle" class="etiqueta-valor">{valor}</text>'
        )
    return (
        f'<svg viewBox="0 0 {ancho} {alto}" width="100%" height="{alto}" role="img" aria-label="{_escapar(titulo)}">'
        + "".join(barras)
        + "</svg>"
    )


def _svg_lineas(series: list[dict], titulo: str) -> str:
    puntos_validos = [s for s in series if s["pct_est_en_val"] is not None or s["pct_est_en_cat"] is not None]
    if not puntos_validos:
        return "<p>Sin datos suficientes.</p>"
    anios = [s["anio"] for s in series]
    ancho, alto = max(360, len(anios) * 60), 240
    margen_i, margen_d, margen_s, margen_inf = 40, 10, 10, 30
    zona_ancho = ancho - margen_i - margen_d
    zona_alto = alto - margen_s - margen_inf

    def coords(valores_clave):
        pts = []
        for i, s in enumerate(series):
            v = s[valores_clave]
            if v is None:
                continue
            x = margen_i + (i / max(1, len(series) - 1)) * zona_ancho
            y = margen_s + (1 - v / 100) * zona_alto
            pts.append((x, y, s["anio"], v))
        return pts

    def polilinea(pts, color):
        if not pts:
            return ""
        puntos_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
        circulos = "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"><title>{a}: {v}%</title></circle>'
            for x, y, a, v in pts
        )
        return f'<polyline points="{puntos_attr}" fill="none" stroke="{color}" stroke-width="2"/>' + circulos

    ejes_x = "".join(
        f'<text x="{margen_i + (i / max(1, len(series)-1)) * zona_ancho:.1f}" y="{alto-8}" '
        f'font-size="11" text-anchor="middle" class="etiqueta-eje">{s["anio"]}</text>'
        for i, s in enumerate(series)
    )
    lineas_ref = "".join(
        f'<line x1="{margen_i}" y1="{margen_s + (1-p/100)*zona_alto:.1f}" '
        f'x2="{ancho-margen_d}" y2="{margen_s + (1-p/100)*zona_alto:.1f}" class="linea-ref"/>'
        f'<text x="2" y="{margen_s + (1-p/100)*zona_alto+4:.1f}" font-size="10" class="etiqueta-eje">{p}%</text>'
        for p in (0, 50, 100)
    )

    return (
        f'<svg viewBox="0 0 {ancho} {alto}" width="100%" height="{alto}" role="img" aria-label="{_escapar(titulo)}">'
        + lineas_ref
        + polilinea(coords("pct_est_en_val"), "#c0442c")
        + polilinea(coords("pct_est_en_cat"), "#3b6ea5")
        + ejes_x
        + "</svg>"
    )


def _tabla_interactiva(
    id_tabla: str,
    columnas: list[tuple[str, str]],
    filas: list[dict],
    nota: str = "",
    columnas_html: tuple[str, ...] = (),
) -> str:
    """columnas: lista de (clave, etiqueta). Genera contenedor + JS que
    renderiza filas dinamicamente desde un JSON embebido, con filtro de
    texto, orden por columna al hacer clic en la cabecera, y PAGINACION
    (solo se construyen 300 filas de DOM a la vez, igual que ya hacia el
    visor de frases -- con tablas de decenas de miles de filas, construir
    todo el <tbody> de golpe con innerHTML es tan lento como el propio
    peso del JSON, aunque este ya este cargado).

    `columnas_html`: claves cuyo valor ya es HTML seguro (p.ej. un
    fragmento con <mark> generado por `_marcar_html`/`_fragmento_contexto`)
    y no se debe escapar como las demas columnas (texto plano)."""
    datos_json = json.dumps(filas, ensure_ascii=False)
    claves_json = json.dumps([c[0] for c in columnas])
    html_json = json.dumps(list(columnas_html))
    cabeceras = "".join(
        f'<th data-clave="{c[0]}">{_escapar(c[1])}</th>' for c in columnas
    )
    nota_html = f'<p class="nota-tabla">{nota}</p>' if nota else ""
    return f"""
<div class="tabla-interactiva" id="contenedor-{id_tabla}">
  <div class="tabla-controles">
    <input type="text" placeholder="Filtrar..." class="filtro-tabla" data-tabla="{id_tabla}">
    <span class="contador-filas" id="contador-{id_tabla}"></span>
  </div>
  {nota_html}
  <div class="tabla-scroll">
    <table>
      <thead><tr>{cabeceras}</tr></thead>
      <tbody id="cuerpo-{id_tabla}"></tbody>
    </table>
  </div>
  <button class="visor-mas" id="mas-{id_tabla}" hidden>Cargar mas filas</button>
</div>
<script type="application/json" id="datos-{id_tabla}">{datos_json}</script>
<script>registrarTabla("{id_tabla}", {claves_json}, {html_json});</script>
"""


CSS = """
:root {
  color-scheme: light dark;
  --fondo: #f7f5f0;
  --texto: #22201c;
  --texto-tenue: #5b5750;
  --borde: #ddd7ca;
  --superficie: #ffffff;
  --acento: #3b6ea5;
  --acento-val: #c0442c;
  --fila-alt: #f1efe8;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fondo: #1c1a17;
    --texto: #ece8e0;
    --texto-tenue: #a89f8f;
    --borde: #3a352d;
    --superficie: #26231e;
    --fila-alt: #211f1a;
  }
}
:root[data-theme="dark"] {
  --fondo: #1c1a17;
  --texto: #ece8e0;
  --texto-tenue: #a89f8f;
  --borde: #3a352d;
  --superficie: #26231e;
  --fila-alt: #211f1a;
}
* { box-sizing: border-box; }
body {
  background: var(--fondo);
  color: var(--texto);
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  line-height: 1.5;
  margin: 0;
  padding: 0 0 4rem;
}
header.cabecera {
  padding: 2rem 1.5rem 1.5rem;
  max-width: 1100px;
  margin: 0 auto;
}
header.cabecera h1 { margin: 0 0 .25rem; font-size: 1.6rem; }
header.cabecera p { color: var(--texto-tenue); margin: 0; }
nav.pestanas {
  position: sticky; top: 0; z-index: 5;
  background: var(--fondo);
  border-bottom: 1px solid var(--borde);
  display: flex; gap: .25rem; flex-wrap: wrap;
  padding: .5rem 1.5rem;
  max-width: 1100px; margin: 0 auto;
}
nav.pestanas button {
  background: none; border: none; cursor: pointer;
  padding: .5rem .9rem; border-radius: 6px;
  color: var(--texto-tenue); font-size: .92rem;
}
nav.pestanas button.activa { background: var(--acento); color: white; }
main { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem; }
section.pestana { display: none; }
section.pestana.activa { display: block; }
h2 { font-size: 1.25rem; border-bottom: 1px solid var(--borde); padding-bottom: .4rem; margin-top: 2rem; }
h3 { font-size: 1.05rem; margin-top: 1.6rem; }
p.explicacion { color: var(--texto-tenue); max-width: 70ch; }
.tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: .75rem; margin: 1rem 0; }
.tarjeta { background: var(--superficie); border: 1px solid var(--borde); border-radius: 10px; padding: .9rem 1rem; }
.tarjeta .valor { font-size: 1.5rem; font-weight: 600; }
.tarjeta .etiqueta { color: var(--texto-tenue); font-size: .82rem; }
.grafico { background: var(--superficie); border: 1px solid var(--borde); border-radius: 10px; padding: 1rem; margin: 1rem 0; }
.etiqueta-eje, .etiqueta-valor { fill: var(--texto-tenue); }
.linea-ref { stroke: var(--borde); stroke-width: 1; }
.leyenda { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--texto-tenue); margin-top: .3rem; }
.leyenda span.punto { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: .3rem; }
.tabla-interactiva { margin: 1rem 0 2rem; }
.tabla-controles { display: flex; justify-content: space-between; align-items: center; margin-bottom: .5rem; gap: 1rem; }
.filtro-tabla { padding: .4rem .6rem; border: 1px solid var(--borde); border-radius: 6px; background: var(--superficie); color: var(--texto); min-width: 220px; }
.contador-filas { color: var(--texto-tenue); font-size: .85rem; white-space: nowrap; }
.nota-tabla { color: var(--texto-tenue); font-size: .85rem; margin: 0 0 .5rem; }
.tabla-scroll { overflow-x: auto; border: 1px solid var(--borde); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: .87rem; }
thead th { position: sticky; top: 0; background: var(--superficie); text-align: left; padding: .5rem .6rem; cursor: pointer; border-bottom: 1px solid var(--borde); white-space: nowrap; }
thead th:hover { color: var(--acento); }
tbody td { padding: .4rem .6rem; border-bottom: 1px solid var(--borde); white-space: nowrap; }
tbody tr:nth-child(even) { background: var(--fila-alt); }
footer { max-width: 1100px; margin: 2rem auto 0; padding: 0 1.5rem; color: var(--texto-tenue); font-size: .82rem; }
code { background: var(--fila-alt); padding: .1rem .35rem; border-radius: 4px; }
mark.chg { background: rgba(230,160,20,.38); color: inherit; border-radius: 3px; padding: 0 .1em; }
mark.ins { background: rgba(40,160,80,.32); color: inherit; border-radius: 3px; padding: 0 .1em; }
mark.del { background: rgba(200,60,60,.28); color: inherit; text-decoration: line-through; border-radius: 3px; padding: 0 .1em; }
.visor-controles { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; margin: .75rem 0; }
.visor-controles select, .visor-controles input[type=text] { padding: .4rem .6rem; border: 1px solid var(--borde); border-radius: 6px; background: var(--superficie); color: var(--texto); }
.visor-controles select { min-width: 320px; max-width: 100%; }
.visor-controles input[type=text] { min-width: 180px; }
.visor-lista { display: flex; flex-direction: column; gap: .6rem; margin: .75rem 0; }
.visor-frase { background: var(--superficie); border: 1px solid var(--borde); border-radius: 10px; padding: .6rem .8rem; }
.visor-frase.con-dif { border-left: 3px solid var(--acento-val); }
.visor-num { font-size: .78rem; color: var(--texto-tenue); margin-bottom: .3rem; }
.visor-linea { display: flex; gap: .5rem; align-items: baseline; padding: .1rem 0; }
.visor-tag { font-size: .7rem; font-weight: 700; color: var(--texto-tenue); border: 1px solid var(--borde); border-radius: 4px; padding: 0 .3rem; flex: none; }
.visor-texto { line-height: 1.6; }
.visor-mas { margin: .5rem 0 1.5rem; padding: .5rem 1rem; border: 1px solid var(--borde); border-radius: 6px; background: var(--superficie); color: var(--texto); cursor: pointer; }
.visor-mas:hover { color: var(--acento); }
"""

JS_FUNCIONES = """
function registrarTabla(id, claves, clavesHtml) {
  const datos = JSON.parse(document.getElementById('datos-' + id).textContent);
  const cuerpo = document.getElementById('cuerpo-' + id);
  const contador = document.getElementById('contador-' + id);
  const btnMas = document.getElementById('mas-' + id);
  const LOTE = 300;
  let ordenClave = null, ordenAsc = true;
  let filasActuales = [];
  let mostradas = 0;

  function celda(valor, clave) {
    let v = valor;
    if (v === null || v === undefined) v = '–';
    if (typeof v === 'number' && !Number.isInteger(v)) v = v.toFixed(1);
    if (clavesHtml.includes(clave)) return '<td>' + v + '</td>';
    return '<td>' + String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</td>';
  }

  function pintarLote() {
    const siguiente = filasActuales.slice(mostradas, mostradas + LOTE);
    cuerpo.insertAdjacentHTML('beforeend', siguiente.map(f =>
      '<tr>' + claves.map(c => celda(f[c], c)).join('') + '</tr>'
    ).join(''));
    mostradas += siguiente.length;
    btnMas.hidden = mostradas >= filasActuales.length;
  }

  function aplicar() {
    const filtroEl = document.querySelector('.filtro-tabla[data-tabla="' + id + '"]');
    const texto = (filtroEl ? filtroEl.value : '').toLowerCase();
    let filas = datos.filter(f => !texto || claves.some(c => String(f[c] ?? '').toLowerCase().includes(texto)));
    if (ordenClave) {
      filas = filas.slice().sort((a, b) => {
        let va = a[ordenClave], vb = b[ordenClave];
        if (va === null || va === undefined) va = -Infinity;
        if (vb === null || vb === undefined) vb = -Infinity;
        if (typeof va === 'string') { va = va.toLowerCase(); vb = String(vb).toLowerCase(); }
        if (va < vb) return ordenAsc ? -1 : 1;
        if (va > vb) return ordenAsc ? 1 : -1;
        return 0;
      });
    }
    filasActuales = filas;
    mostradas = 0;
    cuerpo.innerHTML = '';
    contador.textContent = filas.length + ' fila(s)';
    pintarLote();
  }

  document.querySelector('.filtro-tabla[data-tabla="' + id + '"]').addEventListener('input', aplicar);
  document.querySelectorAll('#contenedor-' + id + ' thead th').forEach(th => {
    th.addEventListener('click', () => {
      const clave = th.dataset.clave;
      if (ordenClave === clave) { ordenAsc = !ordenAsc; } else { ordenClave = clave; ordenAsc = true; }
      aplicar();
    });
  });
  btnMas.addEventListener('click', pintarLote);
  aplicar();
}

function activarPestana(nombre) {
  document.querySelectorAll('section.pestana').forEach(s => s.classList.toggle('activa', s.id === 'pestana-' + nombre));
  document.querySelectorAll('nav.pestanas button').forEach(b => b.classList.toggle('activa', b.dataset.pestana === nombre));
  try { localStorage.setItem('analitica_boe_pestana', nombre); } catch (e) {}
}

function registrarVisor() {
  // `datos` es solo el RESUMEN por documento (id, fecha, metode, num_frases,
  // num_dif) -- deliberadamente ligero. Las frases de cada documento (lo
  // pesado: 322.300 frases en total si se cuenta la cobertura bleualign)
  // se cargan en `analitica_corpus_visor/<id>.json` SOLO cuando se elige
  // ese documento -- meterlas todas aqui dentro disparaba el HTML a mas
  // de 180 MB (probado: peor que no tener la mejora).
  const resumen = JSON.parse(document.getElementById('datos-visor').textContent);
  const select = document.getElementById('visor-doc');
  const soloDif = document.getElementById('visor-solo-dif');
  const soloParrafos = document.getElementById('visor-solo-parrafos');
  const filtro = document.getElementById('visor-filtro');
  const lista = document.getElementById('visor-lista');
  const contador = document.getElementById('visor-contador');
  const btnMas = document.getElementById('visor-mas');
  const LOTE = 300;
  const cache = {};
  let frasesFiltradas = [];
  let mostradas = 0;

  const todosIds = Object.keys(resumen).sort((a, b) => (resumen[a].fecha || '').localeCompare(resumen[b].fecha || '') || a.localeCompare(b));

  function repoblarSelect() {
    const seleccionPrevia = select.value;
    const ids = soloParrafos.checked ? todosIds.filter(id => resumen[id].metode === 'parrafs') : todosIds;
    select.innerHTML = ids.map(id => {
      const d = resumen[id];
      const etiqueta = d.metode === 'bleualign' ? '[bleualign]' : '[parrafos]';
      return `<option value="${id}">${etiqueta} ${id} · ${d.fecha || '?'} · ${d.num_frases} frases (${d.num_dif} con diferencias)</option>`;
    }).join('');
    if (ids.includes(seleccionPrevia)) select.value = seleccionPrevia;
  }

  function pintarLote() {
    const siguiente = frasesFiltradas.slice(mostradas, mostradas + LOTE);
    lista.insertAdjacentHTML('beforeend', siguiente.map(f => `
      <div class="visor-frase${f.dif ? ' con-dif' : ''}">
        <div class="visor-num">#${f.idx + 1}${f.dif ? ' &middot; ' + f.ratio + '% similar' : ' &middot; identica'}</div>
        <div class="visor-linea"><span class="visor-tag visor-tag-ca">CA</span><span class="visor-texto">${f.html_cat}</span></div>
        <div class="visor-linea"><span class="visor-tag visor-tag-va">VA</span><span class="visor-texto">${f.html_val}</span></div>
      </div>
    `).join(''));
    mostradas += siguiente.length;
    btnMas.hidden = mostradas >= frasesFiltradas.length;
  }

  function aplicarFiltroSobre(frases) {
    const texto = filtro.value.trim().toLowerCase();
    frasesFiltradas = frases.filter(f => {
      if (soloDif.checked && !f.dif) return false;
      if (texto && !(f.html_cat.toLowerCase().includes(texto) || f.html_val.toLowerCase().includes(texto))) return false;
      return true;
    });
    mostradas = 0;
    lista.innerHTML = '';
    contador.textContent = frasesFiltradas.length + ' de ' + frases.length + ' frase(s)';
    pintarLote();
  }

  async function cargarYAplicar() {
    const id = select.value;
    if (!id) { lista.innerHTML = ''; contador.textContent = ''; return; }
    if (cache[id]) { aplicarFiltroSobre(cache[id].frases); return; }
    lista.innerHTML = '<p class="explicacion">Cargando documento...</p>';
    try {
      const resp = await fetch('analitica_corpus_visor/' + id + '.json');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const doc = await resp.json();
      cache[id] = doc;
      aplicarFiltroSobre(doc.frases);
    } catch (e) {
      lista.innerHTML = '<p class="explicacion"><strong>No se pudo cargar el documento.</strong> '
        + 'Esta pestana carga cada documento por separado (son 322.300 frases en total entre todos: '
        + 'meterlas todas en este HTML lo habria dejado en mas de 180 MB). La mayoria de navegadores '
        + 'bloquean esa carga si abres el fichero haciendo doble clic (<code>file://</code>). '
        + 'Arranca un servidor local desde <code>dades/boe/</code> y abre la URL que indica:<br>'
        + '<code>python -m http.server 8000</code> &rarr; '
        + '<code>http://localhost:8000/analitica_corpus.html</code><br>'
        + 'El resto de pestanas (resumen, vocabulario, pares de sustitucion...) funcionan igual sin esto.</p>';
    }
  }

  select.addEventListener('change', cargarYAplicar);
  soloDif.addEventListener('change', () => { if (cache[select.value]) aplicarFiltroSobre(cache[select.value].frases); });
  soloParrafos.addEventListener('change', () => { repoblarSelect(); cargarYAplicar(); });
  filtro.addEventListener('input', () => { if (cache[select.value]) aplicarFiltroSobre(cache[select.value].frases); });
  btnMas.addEventListener('click', pintarLote);

  repoblarSelect();
  if (todosIds.length) cargarYAplicar();
}
"""

JS_INIT = """
document.querySelectorAll('nav.pestanas button').forEach(b => {
  b.addEventListener('click', () => activarPestana(b.dataset.pestana));
});

(function () {
  let inicial = 'resumen';
  try { inicial = localStorage.getItem('analitica_boe_pestana') || inicial; } catch (e) {}
  if (!document.getElementById('pestana-' + inicial)) inicial = 'resumen';
  activarPestana(inicial);
})();
"""


def generar_html(
    resumen: dict, vocab: dict, val_esp: dict, morfo: dict, demo: dict, loc: dict, diff: dict, bleu: dict | None
) -> str:
    anios_txt = f'{resumen["anio_min"]}-{resumen["anio_max"]}' if resumen["anio_min"] else "-"

    tarjetas_resumen = "".join(
        f'<div class="tarjeta"><div class="valor">{v}</div><div class="etiqueta">{k}</div></div>'
        for k, v in [
            ("Parejas de documentos", resumen["total_pares"]),
            ("Periodo cubierto", anios_txt),
            ("Paginas totales (ambos idiomas)", resumen["paginas_totales"]),
            ("Caracteres · catala", f'{resumen["caracteres_totales"]["catalan"]:,}'.replace(",", ".")),
            ("Caracteres · valencia", f'{resumen["caracteres_totales"]["valenciano"]:,}'.replace(",", ".")),
            ("Palabras (tokens) · catala", f'{resumen["tokens_totales"]["catalan"]:,}'.replace(",", ".")),
            ("Palabras (tokens) · valencia", f'{resumen["tokens_totales"]["valenciano"]:,}'.replace(",", ".")),
            ("Vocabulario unico · catala", f'{resumen["vocabulario_unico"]["catalan"]:,}'.replace(",", ".")),
            ("Vocabulario unico · valencia", f'{resumen["vocabulario_unico"]["valenciano"]:,}'.replace(",", ".")),
            (
                "Documentos con parrafos alineables 1 a 1",
                f'{resumen["docs_alineados_por_posicion"]} / {resumen["total_pares"]}',
            ),
            (
                "Parrafos tabulares excluidos (cat / val)",
                f'{resumen["parrafos_tabla_excluidos"]["catalan"]} / {resumen["parrafos_tabla_excluidos"]["valenciano"]}',
            ),
        ]
    )

    grafico_docs_anio = _svg_barras(resumen["docs_por_anio"], "Documentos por anio")

    resumen_vocab_tarjetas = "".join(
        f'<div class="tarjeta"><div class="valor">{v}</div><div class="etiqueta">{k}</div></div>'
        for k, v in [
            ("Entradas del glosario", vocab["total_entradas"]),
            ("Con al menos 1 aparicion", vocab["entradas_con_uso"]),
            ("Forma valenciana en texto valencia", vocab["suma_uso_val_en_val"]),
            ("Forma catalana en texto valencia (fuga)", vocab["suma_uso_cat_en_val"]),
            ("Forma catalana en texto catala", vocab["suma_uso_cat_en_cat"]),
            ("Forma valenciana en texto catala (fuga)", vocab["suma_uso_val_en_cat"]),
        ]
    )

    tabla_vocab = _tabla_interactiva(
        "vocab",
        [
            ("valenciano", "Valencia"),
            ("catalan", "Catala"),
            ("castellano", "Castellano"),
            ("categoria", "Categoria"),
            ("uso_val_en_val", "Uso forma-val en textos val"),
            ("uso_cat_en_val", "Uso forma-cat en textos val"),
            ("uso_cat_en_cat", "Uso forma-cat en textos cat"),
            ("uso_val_en_cat", "Uso forma-val en textos cat"),
            ("total", "Total apariciones"),
            ("fidelidad_val", "Fidelidad val (%)"),
            ("fidelidad_cat", "Fidelidad cat (%)"),
        ],
        vocab["filas"],
        nota=(
            f"{vocab['entradas_con_uso']} de {vocab['total_entradas']} entradas del glosario aparecen al menos "
            "una vez en el corpus. 'Fidelidad val' = % de apariciones de la palabra (forma valenciana o "
            "catalana) que caen en el lado esperado (textos en valencia); 100% = separacion perfecta, "
            "valores bajos indican que el texto etiquetado como valencia usa en realidad la forma catalana "
            "(o al reves)."
        ),
    )

    tabla_val_esp = _tabla_interactiva(
        "valesp",
        [
            ("forma", "Forma (solo valencia segons Apertium)"),
            ("categoria", "Categoria gramatical"),
            ("paradigma", "Paradigma"),
            ("uso_val", "Uso en textos valencia"),
            ("uso_cat", "Uso en textos catala (fuga)"),
            ("total", "Total"),
            ("fidelidad", "Fidelidad (%)"),
        ],
        val_esp["filas"],
        nota=(
            f"{val_esp['formas_con_uso']} de {val_esp['total_formas']} formas del diccionario Apertium "
            "marcadas exclusivamente <code>v=\"val_gva\"</code> (sin equivalente <code>cat</code> en la misma "
            "entrada) aparecen en el corpus."
        ),
    )

    tabla_morfo = _tabla_interactiva(
        "morfo",
        [
            ("categoria", "Categoria"),
            ("rasgos", "Tiempo / rasgos"),
            ("cat", "Terminacion cat"),
            ("val", "Terminacion val"),
            ("cobertura", "Cobertura (dic.)"),
            ("ejemplo", "Ejemplo"),
            ("uso_cat", "Uso terminacion-cat en textos cat"),
            ("uso_val", "Uso terminacion-val en textos val"),
            ("fidelidad_cat", "Fidelidad cat (%)"),
        ],
        morfo["filas"],
        nota=(
            "Cuenta, entre las palabras realmente presentes en el corpus, cuantas terminan en la "
            "terminacion catalana o valenciana de cada regla morfologica. Filas con '&ndash;' corresponden a "
            "reglas con terminacion vacia (&empty;) que no se pueden contar de forma fiable por sufijo."
        ),
    )

    filas_demo = demo["filas"]
    tabla_demo = _tabla_interactiva(
        "demo",
        [
            ("valenciano", "Valencia (est-)"),
            ("catalan", "Catala (aquest-)"),
            ("uso_val_en_val", "'est-' en textos val"),
            ("uso_cat_en_val", "'aquest-' en textos val"),
            ("uso_val_en_cat", "'est-' en textos cat"),
            ("uso_cat_en_cat", "'aquest-' en textos cat"),
        ],
        filas_demo,
    )
    grafico_demo = _svg_lineas(demo["series_anio"], "Evolucion del uso de demostratius 'est-' por anio")

    tabla_loc = _tabla_interactiva(
        "loc",
        [
            ("valenciano", "Valencia"),
            ("catalan", "Catala"),
            ("fuente", "Fuente"),
            ("uso_val_en_val", "En textos val"),
            ("uso_cat_en_val", "'cat' en textos val"),
            ("uso_val_en_cat", "'val' en textos cat"),
            ("uso_cat_en_cat", "En textos cat"),
        ],
        loc["filas"],
    )

    tarjetas_diff = "".join(
        f'<div class="tarjeta"><div class="valor">{v}</div><div class="etiqueta">{k}</div></div>'
        for k, v in [
            ("Documentos comparables (frases 1 a 1)", f'{diff["docs_analizados"]} / {diff["docs_totales"]}'),
            ("Frases comparadas", f'{diff["total_frases"]:,}'.replace(",", ".")),
            (
                "Frases identicas letra a letra",
                f'{diff["frases_identicas"]:,}'.replace(",", ".")
                + (f' ({100*diff["frases_identicas"]//diff["total_frases"]}%)' if diff["total_frases"] else ""),
            ),
            ("Similitud media por frase", f'{diff["ratio_medio"]}%' if diff["ratio_medio"] is not None else "–"),
            ("Pares de sustitucion distintos", f'{diff["pares_distintos"]:,}'.replace(",", ".")),
            ("...de ellos, no catalogados antes", diff["pares_nuevos"]),
            ("Palabras insertadas (sin pareja)", diff["total_inserciones"]),
            ("Palabras eliminadas (sin pareja)", diff["total_eliminaciones"]),
        ]
    )

    tabla_diff_pares = _tabla_interactiva(
        "diffpares",
        [
            ("catalan", "Catala (texto real)"),
            ("valenciano", "Valencia (texto real)"),
            ("frecuencia", "Veces encontrado"),
            ("ratio_medio_frase", "Similitud media de la frase (%)"),
            ("pct_cambio_aislado", "% veces que es el unico cambio"),
            ("en_glosario", "¿En el glosario?"),
            ("regla_morfologica", "Regla morfologica"),
            ("novedad", "Novedad"),
            ("ejemplo_doc", "Documento ejemplo"),
            ("ejemplo_frase_cat", "Frase catala (ejemplo)"),
            ("ejemplo_frase_val", "Frase valencia (ejemplo)"),
        ],
        diff["filas_pares"],
        nota=(
            f"{diff['pares_distintos']} pares de sustitucion distintos encontrados por diff palabra a palabra "
            f"(difflib) sobre las frases alineadas 1 a 1; {diff['pares_nuevos']} no coinciden con ningun par del "
            "glosario ni con ninguna regla morfologica (columna 'Novedad') — candidatos a marcador dialectal no "
            "catalogado todavia, o simplemente ruido de la extraccion/segmentacion. Bloques de mas de "
            f"{MAX_TOKENS_SUSTITUCION} palabras seguidas se descartan (no se consideran una sustitucion lexica "
            "puntual sino una frase mal alineada o reescrita). Los ejemplos muestran solo el fragmento alrededor "
            "del cambio (no la frase entera) para que el informe cargue rapido con ~44.000 filas. "
            "'Similitud media de la frase' y '% veces que es el unico cambio' son dos señales para distinguir "
            "sustitucion dialectal limpia de reescritura de estilo del traductor: alta en las dos = cambio puntual "
            "en frases por lo demas identicas (mas fiable); bajas = suele aparecer en frases muy reescritas o junto "
            "a otros cambios (mas sospechoso de ser ruido o estilo, no un patron dialectal estable). Ordena por "
            "estas columnas para juzgarlo tu mismo caso por caso, no es un filtro automatico."
        ),
        columnas_html=("ejemplo_frase_cat", "ejemplo_frase_val"),
    )

    tabla_diff_documentos = _tabla_interactiva(
        "diffdocs",
        [
            ("id", "Documento"),
            ("fecha", "Fecha"),
            ("frases", "Frases comparadas"),
            ("frases_identicas", "Identicas"),
            ("sustituciones", "Sustituciones"),
            ("inserciones", "Inserciones"),
            ("eliminaciones", "Eliminaciones"),
            ("ratio_medio", "Similitud media (%)"),
        ],
        diff["filas_documentos"],
        nota=(
            "Ordenada por defecto por numero de sustituciones, pero eso mezcla dos cosas distintas: documentos "
            "donde de verdad cambia mucho vocabulario, y documentos donde el mismo numero de parrafos en total "
            "es casualidad y no se corresponden bien posicion a posicion (sintoma: 'Similitud media' baja y "
            "muchas inserciones/eliminaciones a la vez que pocas 'Identicas'). Para encontrar los documentos "
            "mejor alineados, ordena por 'Similitud media' o por 'Identicas' de mayor a menor."
        ),
    )

    boton_bleu = ""
    seccion_bleu = ""
    if bleu:
        tarjetas_bleu = "".join(
            f'<div class="tarjeta"><div class="valor">{v}</div><div class="etiqueta">{k}</div></div>'
            for k, v in [
                ("Pares alineados", f'{bleu["total_pares"]:,}'.replace(",", ".")),
                ("Documentos con datos", bleu["total_documentos"]),
                ("Similitud media", bleu["similitud_media"]),
                ("Similitud mediana", bleu["similitud_mediana"]),
                (f"Candidatos a revision (similitud < {UMBRAL_REVISION_BLEUALIGN})", bleu["total_candidatos_revision"]),
            ]
        )
        grafico_bleu = _svg_barras(bleu["buckets"], "Distribucion de similitud (Bleualign)")

        tabla_bleu_documentos = _tabla_interactiva(
            "bleudocs",
            [
                ("id", "Documento"),
                ("fecha", "Fecha"),
                ("pares", "Pares alineados"),
                ("similitud_media", "Similitud media"),
                ("similitud_minima", "Similitud minima"),
            ],
            bleu["filas_documentos"],
            nota="Ordenada por similitud media ascendente: arriba, los documentos donde Bleualign encuentra menos parecido entre las dos versiones (a revisar primero).",
        )

        filas_revision_html = "".join(
            f"""
      <div class="visor-frase con-dif">
        <div class="visor-num">{_escapar(r["documento_id"])} &middot; {_escapar(r["fecha"])} &middot; similitud {r["similitud"]:.2f}</div>
        <div class="visor-linea"><span class="visor-tag visor-tag-ca">CA</span><span class="visor-texto">{r["html_catalan"]}</span></div>
        <div class="visor-linea"><span class="visor-tag visor-tag-va">VA</span><span class="visor-texto">{r["html_valenciano"]}</span></div>
      </div>"""
            for r in bleu["filas_revision"]
        )
        nota_revision = (
            f"{bleu['total_candidatos_revision']} pares con similitud por debajo de {UMBRAL_REVISION_BLEUALIGN} "
            "Y palabras reales en los dos lados (se excluyen a proposito los pares donde alguno de los dos lados "
            "es solo un numero/marca de lista tipo '1.', que dan similitud 0 aunque el emparejamiento sea "
            f"correcto). Se muestran los {min(len(bleu['filas_revision']), MAX_CANDIDATOS_REVISION)} peores. "
            "La mayoria seguiran siendo emparejamientos correctos con muy poco solapamiento lexico (numeros "
            "escritos de forma distinta, alternancias dialectales sin raiz comun); son los que de verdad valen "
            "la pena revisar a mano si te preocupa la calidad de una zona concreta del corpus."
        )

        boton_bleu = '<button data-pestana="bleualign">Bleualign</button>'
        seccion_bleu = f"""
<section class="pestana" id="pestana-bleualign">
  <h2>Alineacion con Bleualign</h2>
  <p class="explicacion">Resultado de <code>alinear_corpus_bleualign.py</code> (independiente de
     <code>corpus.json</code> — se genera aparte y es opcional). Bleualign alinea por similitud de texto en vez
     de por coincidencia exacta de conteo; aqui se usa el propio catala como si fuera su traduccion al valencia
     (ver README). La "similitud" de cada par es Jaccard sobre palabras normalizadas, recalculada por este
     script porque Bleualign no expone su puntuacion BLEU interna por par.</p>
  <div class="tarjetas">{tarjetas_bleu}</div>
  <h3>Distribucion de similitud</h3>
  <div class="grafico">{grafico_bleu}</div>
  <h3>Por documento</h3>
  {tabla_bleu_documentos}
  <h3>Candidatos a revision (similitud mas baja)</h3>
  <p class="explicacion">{nota_revision}</p>
  <div class="visor-lista">{filas_revision_html}</div>
</section>
"""

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Analitica corpus BOE catala/valencia</title>
<style>{CSS}</style>
<script>{JS_FUNCIONES}</script>
</head>
<body>
<header class="cabecera">
  <h1>Analitica del corpus paralelo BOE catala / valencia</h1>
  <p>{resumen["total_pares"]} documentos emparejados &middot; periodo {anios_txt} &middot; generado a partir de
     <code>../dades/boe/corpus.json</code> y los materiales de <code>02_regles_dialectals</code>.</p>
</header>

<nav class="pestanas">
  <button data-pestana="resumen" class="activa">Resumen</button>
  <button data-pestana="vocab">Lexico dialectal</button>
  <button data-pestana="valesp">Formas exclusivas valencia</button>
  <button data-pestana="morfo">Morfologia</button>
  <button data-pestana="demo">Demostratius</button>
  <button data-pestana="loc">Locucions</button>
  <button data-pestana="diff">Diff textual</button>
  {boton_bleu}
  <button data-pestana="metodologia">Metodologia</button>
</nav>

<main>

<section class="pestana activa" id="pestana-resumen">
  <h2>Resumen general</h2>
  <div class="tarjetas">{tarjetas_resumen}</div>
  <h3>Documentos por anio</h3>
  <div class="grafico">{grafico_docs_anio}</div>
  <p class="explicacion">Cada documento es una pareja de PDF (mismo BOE, mismo dia) con traduccion oficial en
     catala y en valencia. "Parrafos alineables 1 a 1" cuenta documentos donde ambas versiones tienen el mismo
     numero de parrafos reales (cada articulo/parrafo del BOE es una unidad de traduccion 1 a 1; ver
     <code>construir_corpus.py</code>); el resto necesitaria un alineador mas fino. Es la base de la pestaña
     "Diff textual". "Parrafos tabulares excluidos" son presupuestos/aranceles/formularios (ver
     <code>texto_comun.es_tabla</code>) descartados antes de contar palabras o comparar parrafos — no son prosa,
     asi que ni las estadisticas de vocabulario ni el diff los tienen en cuenta.</p>
</section>

<section class="pestana" id="pestana-vocab">
  <h2>Lexico dialectal (glosario valencia/catala)</h2>
  <p class="explicacion">Basado en <code>palabras_traducidas.json</code> (glosario curado + parejas del
     diccionario Apertium). Para cada palabra se cuenta cuantas veces aparece su forma valenciana y su forma
     catalana, tanto en los textos etiquetados como valencia como en los etiquetados como catala.</p>
  <div class="tarjetas">{resumen_vocab_tarjetas}</div>
  {tabla_vocab}
</section>

<section class="pestana" id="pestana-valesp">
  <h2>Formas exclusivas del valencia (Apertium)</h2>
  <p class="explicacion">Formas del diccionario <code>apertium-cat.cat.dix</code> marcadas unicamente
     <code>v="val_gva"</code> (variante valenciana AVL), sin marca <code>cat</code> en la misma entrada
     (<code>palabras_val.json</code>). Si aparecen en textos catalanes seria una fuga dialectal real.</p>
  {tabla_val_esp}
</section>

<section class="pestana" id="pestana-morfo">
  <h2>Morfologia verbal y de pronombres/adjectius</h2>
  <p class="explicacion">108 reglas de terminacion derivadas de los paradigmas de flexion del diccionario
     Apertium (<code>regles_cat_val.md</code>, seccion 1). Aqui se comprueba, palabra a palabra del corpus,
     cuantas terminan en la forma catalana o valenciana de cada regla.</p>
  {tabla_morfo}
</section>

<section class="pestana" id="pestana-demo">
  <h2>Demostratius: est- (valencia) vs aquest- (catala)</h2>
  <p class="explicacion">El marcador dialectal mas conocido entre valencia col·loquial i catala. La AVL tambien
     admite <em>aquest/aquesta</em> como forma normativa en valencia, asi que cierto uso de "aquest-" en textos
     valencians es esperable y no es necesariamente una fuga.</p>
  {tabla_demo}
  <h3>Evolucion por anio</h3>
  <div class="grafico">
    {grafico_demo}
    <div class="leyenda">
      <span><span class="punto" style="background:#c0442c"></span>% "est-" en textos valencia</span>
      <span><span class="punto" style="background:#3b6ea5"></span>% "est-" en textos catala</span>
    </div>
  </div>
</section>

<section class="pestana" id="pestana-loc">
  <h2>Locucions</h2>
  <p class="explicacion">Locuciones sueltas (fuera del sistema de marcas <code>v=</code> del diccionario),
     <code>regles_cat_val.md</code> seccion 4.</p>
  {tabla_loc}
</section>

<section class="pestana" id="pestana-diff">
  <h2>Diff textual: que cambia realmente entre las dos versiones</h2>
  <p class="explicacion">Cada documento es la misma norma traducida oficialmente dos veces (catala y valencia).
     Para los documentos donde ambas versiones tienen el mismo numero de parrafos reales, se compara cada
     parrafo catala con su parrafo valencia correspondiente; dentro de cada parrafo, si tambien tiene el mismo
     numero de frases en los dos idiomas se compara frase a frase, si no, el parrafo entero como una unidad,
     siempre palabra a palabra (<code>difflib</code>), en vez de partir de un glosario cerrado. Esto encuentra
     sustituciones reales tal como aparecen en el corpus, catalogadas o no, y sirve tanto para validar el
     glosario como para descubrir pares nuevos.</p>
  <div class="tarjetas">{tarjetas_diff}</div>

  <h3>Visor frase a frase</h3>
  <p class="explicacion">Elige un documento y lee sus frases con las palabras que cambian resaltadas: en
     <mark class="chg">ambar</mark> las que se sustituyen por otra, en <mark class="ins">verde</mark> las que
     solo estan en la version valenciana, en <mark class="del">rojo tachado</mark> las que solo estan en la
     catalana. Sirve para revisar a ojo la calidad/consistencia de las traducciones oficiales del BOE, no solo
     el recuento agregado de abajo. Cada documento indica con que metodo se alineo:
     <strong>[parrafos]</strong> (exacto, mismo numero de parrafos en los dos idiomas) o
     <strong>[bleualign]</strong> (por similitud, frase a frase -- cubre casi todo el corpus pero puede fallar en
     frases cortas o sin palabras en comun; la % de cada frase es la similitud que le asigno Bleualign, no un
     ratio de difflib).</p>
  <div class="visor-controles">
    <select id="visor-doc"></select>
    <label><input type="checkbox" id="visor-solo-parrafos"> Solo alineacion exacta (parrafos)</label>
    <label><input type="checkbox" id="visor-solo-dif" checked> Solo frases con diferencias</label>
    <input type="text" id="visor-filtro" placeholder="Buscar palabra...">
    <span class="contador-filas" id="visor-contador"></span>
  </div>
  <div class="visor-lista" id="visor-lista"></div>
  <button class="visor-mas" id="visor-mas" hidden>Cargar mas frases</button>
  <script type="application/json" id="datos-visor">{json.dumps(_resumen_visor(diff["visor"]), ensure_ascii=False)}</script>
  <script>registrarVisor();</script>

  <h3>Pares de sustitucion encontrados (resumen agregado)</h3>
  {tabla_diff_pares}
  <h3>Por documento</h3>
  <p class="explicacion">Ordenado por numero de sustituciones: arriba, los documentos donde mas cambia el
     vocabulario entre las dos versiones.</p>
  {tabla_diff_documentos}
</section>
{seccion_bleu}
<section class="pestana" id="pestana-metodologia">
  <h2>Metodologia y limitaciones</h2>
  <ul>
    <li><strong>Diff textual:</strong> solo se hace sobre el subconjunto de documentos con el mismo numero de
        <em>parrafos</em> reales en ambas versiones (ver pestaña Resumen; parrafo = bloque de texto de PyMuPDF,
        que en el BOE equivale a un articulo/parrafo real, no a una linea de PDF renderizada); en el resto no
        hay forma fiable de emparejar nada sin un alineador mas fino. Dentro de cada parrafo ya emparejado, si
        tambien tiene el mismo numero de frases en los dos idiomas se comparan frase a frase; si no, se compara
        el parrafo entero como una unica unidad (mas grande, pero sigue siendo una correspondencia fiable). El
        diff dentro de cada unidad es palabra a palabra: dos sustituciones cercanas pueden aparecer como un
        unico bloque "reemplazado" en vez de dos palabras sueltas si difflib no encuentra un punto de anclaje
        entre ellas. Ojo: mismo numero total de parrafos no garantiza que el parrafo i de un idioma corresponda
        al parrafo i del otro en todo el documento (puede coincidir el total y no la correspondencia interna);
        la pestaña "Diff textual" incluye una tabla por documento con la similitud media y el numero de
        unidades identicas para detectar estos casos.</li>
    <li><strong>Visor frase a frase:</strong> usa un tokenizador "sin perdidas" (palabras, numeros, espacios y
        cada signo de puntuacion) para poder repintar la frase exacta con solo lo distinto resaltado; el
        recuento agregado de pares de palabras, en cambio, ignora los tramos que son solo puntuacion o
        espacios. El filtro de texto del visor busca dentro del HTML ya generado (incluye alguna marca de
        resaltado), asi que una busqueda muy corta puede dar algun falso positivo ocasional.</li>
    <li><strong>Extraccion de texto:</strong> PyMuPDF sobre los PDF oficiales, con limpieza de cabeceras/pies
        repetidos por pagina (ver <code>construir_corpus.py</code>).</li>
    <li><strong>Tokenizacion:</strong> heuristica basada en regex Unicode (letras, con guiones/apostrofos/
        interpunct dentro de palabra para no romper <em>l'article</em>, <em>col·legi</em>, <em>vint-i-cinc</em>).
        No es un analizador morfologico real.</li>
    <li><strong>Segmentacion en frases:</strong> la misma heuristica de <code>texto_comun.py</code>
        (puntuacion + mayuscula siguiente), no un tokenizador linguistico completo.</li>
    <li><strong>Parrafos tabulares:</strong> se excluyen antes de contar palabras o comparar parrafos si tienen
        puntos-guia (".  .  .  .") o menos de 55% de letras sobre caracteres no-espacio
        (<code>texto_comun.es_tabla</code>) — presupuestos, aranceles y formularios, no prosa. Calibrado a mano
        sobre el corpus real (ver README): marca ~1,1% de los parrafos, sin falsos positivos detectados en una
        muestra de revision.</li>
    <li><strong>Conteo de vocabulario/locucions:</strong> coincidencia de palabra completa o frase completa
        (con limites de palabra), sin distinguir mayusculas/minusculas ni desambiguar sentido; una forma
        ambigua que coincide por casualidad con otro uso se contaria igualmente.</li>
    <li><strong>Conteo de morfologia:</strong> se comprueba el sufijo sobre el vocabulario unico del corpus
        (no sobre cada aparicion individual salvo al ponderar por frecuencia), y no se comprueba la categoria
        gramatical real de cada palabra — puede haber falsos positivos cuando una terminacion corta coincide
        con el final de una palabra no relacionada.</li>
    <li><strong>"Fidelidad":</strong> definida como el % de apariciones de una forma (en todo el corpus) que
        caen en el lado dialectal donde se esperaria encontrarla. No implica necesariamente un error: la AVL
        admite variantes compartidas para varias formas (p.ej. demostratius), y algunas palabras del glosario
        son sinonimos validos en ambas variantes.</li>
    <li><strong>Fuente de los materiales linguisticos:</strong> carpeta <code>02_regles_dialectals</code>
        (diccionario Apertium <code>apertium-cat.cat.dix</code>, glosario curado y reglas derivadas).</li>
  </ul>
</section>

</main>
<footer>Generado por <code>analizar_corpus.py</code>.</footer>
<script>{JS_INIT}</script>
</body>
</html>
"""


def main() -> None:
    print("Cargando corpus...")
    corpus = cargar_corpus()
    print(f"  {len(corpus)} parejas de documentos")

    print("Cargando materiales linguisticos...")
    materiales = cargar_materiales()
    print(f"  {len(materiales['vocabulario'])} entradas de vocabulario")
    print(f"  {len(materiales['val_especificas'])} formas exclusivas de valencia")
    print(f"  {len(materiales['morfologia'])} reglas morfologicas")
    print(f"  {len(materiales['demostratius'])} demostratius, {len(materiales['locucions'])} locucions")

    locuciones_objetivo = recolectar_locuciones_objetivo(materiales)
    print(f"  {sum(len(v) for v in locuciones_objetivo.values())} locuciones distintas a rastrear")

    print("Indexando frecuencias del corpus...")
    indice = CorpusIndexado(locuciones_objetivo)
    indice.indexar(corpus)

    print("Analizando vocabulario dialectal...")
    vocab = analizar_vocabulario(materiales["vocabulario"], indice)
    print("Analizando formas exclusivas de valencia...")
    val_esp = analizar_val_especificas(materiales["val_especificas"], materiales["val_especificas_meta"], indice)
    print("Analizando morfologia...")
    morfo = analizar_morfologia(materiales["morfologia"], indice)
    print("Analizando demostratius...")
    demo = analizar_demostratius(materiales["demostratius"], indice)
    print("Analizando locucions...")
    loc = analizar_locucions(materiales["locucions"], indice)
    print("Haciendo diff palabra a palabra de los parrafos alineados...")
    diff = analizar_diff_textual(indice, materiales)
    print(
        f"  {diff['docs_analizados']} documentos comparables, {diff['pares_distintos']} pares de sustitucion "
        f"distintos ({diff['pares_nuevos']} nuevos)"
    )
    resumen = estadisticas_generales(corpus, indice)

    print("Cargando alineacion de Bleualign (si existe)...")
    registros_bleu = cargar_bleualign()
    if registros_bleu is None:
        print(f"  {BLEUALIGN_JSONL} no existe, se omite esa pestaña (ejecuta alinear_corpus_bleualign.py si la quieres)")
        bleu = None
    else:
        print(f"  {len(registros_bleu)} pares cargados")
        bleu = analizar_bleualign(registros_bleu)
        print(f"  {bleu['total_candidatos_revision']} candidatos a revision (similitud < {UMBRAL_REVISION_BLEUALIGN})")

    print("Completando el visor con Bleualign para los documentos sin parrafos alineados 1 a 1...")
    docs_antes = len(diff["visor"])
    _completar_visor_con_bleualign(diff["visor"], registros_bleu)
    print(f"  visor: {docs_antes} documentos (parrafos) -> {len(diff['visor'])} documentos (+ bleualign)")

    visor_dir = CORPUS_DIR / VISOR_SUBDIR
    print(f"Exportando el visor a {visor_dir}/ (un .json por documento, cargado con fetch() bajo demanda)...")
    _exportar_visor_a_ficheros(diff["visor"], visor_dir)

    print("Generando HTML...")
    html = generar_html(resumen, vocab, val_esp, morfo, demo, loc, diff, bleu)
    SALIDA_HTML.write_text(html, encoding="utf-8")
    print(f"Guardado: {SALIDA_HTML}")


if __name__ == "__main__":
    main()
