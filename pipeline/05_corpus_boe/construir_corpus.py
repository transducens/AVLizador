#!/usr/bin/env python3
"""Construye ../dades/boe/corpus.json a partir de los PDF ya descargados.

Empareja cada documento en català con su equivalente en valencià (mismo ID
base BOE-X-YYYY-NNNNN, ya garantizado por scraper_boe.py), extrae el texto
de ambos PDF con PyMuPDF a nivel de bloque (page.get_text("blocks")), que en
el BOE corresponde a párrafos reales (cada artículo/párrafo es un bloque,
con sus líneas ya unidas) en vez de a líneas de renderizado de página —
importante porque català y valencià envuelven cada párrafo en un número de
líneas distinto (la traducción no ocupa el mismo espacio), así que separar
por línea de PDF en vez de por párrafo desalineaba las frases entre los dos
idiomas. Limpia las cabeceras/pies de página repetidos en cada página del
BOE, y guarda un JSON con un registro por pareja:

{
  "id": "BOE-A-2009-3022",          # ID compartido, sin idioma
  "fecha": "2009-02-24",
  "anio": 2009,
  "catalan":    {"id": "BOE-A-2009-3022-C", "titulo": ..., "texto": ..., ...},
  "valenciano": {"id": "BOE-A-2009-3022-V", "titulo": ..., "texto": ..., ...}
}

Es reanudable/incremental de facto: simplemente recorre lo que haya en disco
en cada ejecución, así que se puede relanzar según el scraper vaya
descargando más parejas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

BOE_DIR = Path(__file__).resolve().parent
# Los datos del BOE ahora viven en dades/boe/ (junto a los del resto de
# fuentes del proyecto), no dentro de boe/ como antes.
CORPUS_DIR = BOE_DIR.parent / "dades" / "boe"
PROGRESO_PATH = CORPUS_DIR / "progreso.json"
SALIDA_PATH = CORPUS_DIR / "corpus.json"

IDIOMAS = {
    "catalan": {"sufijo": "-C", "dir": "catala"},
    "valenciano": {"sufijo": "-V", "dir": "valencia"},
}

DIAS_SEMANA = (
    "Dilluns|Dimarts|Dimecres|Dijous|Divendres|Dissabte|Diumenge"
)

LINEAS_RUIDO = [
    re.compile(r"^BOLET[ÍI]N OFICIAL DEL ESTADO\s*$"),
    re.compile(r"^Suplement en (llengua catalana|valencià) al núm\.\s*\d+\s*$"),
    # "de " davant de mes que comença en consonant (gener, febrer, març...)
    # pero "d'" (elisio) davant de mes que comença en vocal (abril, agost,
    # octubre) -- bug real trobat 02/10/2026: la versio anterior nomes
    # cobria "de ", així que la capcalera de pagina NO es filtrava en cap
    # document datat en estos 3 mesos (una cuarta part dels documents),
    # colant-se literalment enmig d'una frase quan el salt de pagina cau
    # ahi (vore conversa sobre "BOE-A-2015-4607").
    re.compile(rf"^(?:{DIAS_SEMANA}) \d{{1,2}} (?:de |d')\w+ de \d{{4}}\s*$"),
    re.compile(r"^Secc\.\s*\S+\.?\s*Pàg\.?\s*\d+\s*$"),
    re.compile(r"^https?://www\.boe\.es\s*$"),
    re.compile(r"^D\.\s*L\.:.*ISSN.*$"),
    re.compile(r"^cve:\s*BOE-\S+\s*$"),
]


ESPACIOS_UNICODE = re.compile("[    　]")


def limpiar_bloque(texto_bloque: str) -> str:
    """Limpia un bloque (parrafo) linea a linea y las une en una sola frase
    continua: dentro de un bloque, los saltos de linea son solo el ajuste
    de palabra del renderizador de PDF, no una separacion real."""
    lineas_limpias = []
    for linea in texto_bloque.splitlines():
        linea_normalizada = ESPACIOS_UNICODE.sub(" ", linea).strip()
        if not linea_normalizada:
            continue
        if any(patron.match(linea_normalizada) for patron in LINEAS_RUIDO):
            continue
        lineas_limpias.append(linea_normalizada)
    return " ".join(lineas_limpias)


TERMINADORES_PARRAFO = (".", "!", "?", ":", "»", '"', "”", "’", ")")


def _parece_titular(parrafo: str) -> bool:
    """Heuristica para "CAP DE L'ESTAT", "I.  DISPOSICIONS GENERALS"...:
    parrafos cortos, todo en mayusculas, que legitimamente no terminan en
    puntuacion de cierre de frase pero tampoco deben fusionarse con lo que
    venga despues."""
    letras = [c for c in parrafo if c.isalpha()]
    return bool(letras) and all(c.isupper() for c in letras)


PATRON_ENCABEZADO_ESTRUCTURAL = re.compile(
    r"^(Article|Disposició (final|addicional|transitòria|derogatòria)"
    r"|CAPÍTOL|Secció|ANNEX|TÍTOL|Preàmbul)\b",
    re.IGNORECASE,
)
"""Encabezados estructurales del BOE ("Article 3.", "Disposició final segona.",
"CAPÍTOL II"...): nunca se fusionan con el parrafo anterior, aunque este no
acabe en puntuacion de cierre. Hace falta ademas de la comprobacion de
tipografia (ver extraer_texto_pdf): a veces la asimetria de puntuacion pasa
entre dos parrafos de cuerpo normal (mismo estilo en los dos), como
"...article 149.1.25a" (sin punto en valencia, con punto en catala) seguido
de "Disposició final segona.  Entrada en vigor." — sin este patron, ese
titol se fusionaba con el parrafo anterior solo en el idioma que le faltaba
el punto, desalineando el resto del documento."""


def _texto_de_bloque_dict(bloque: dict) -> str:
    """Reconstruye el texto del bloque con un salto de linea entre cada
    linea interna (igual que get_text("blocks")), necesario para que
    limpiar_bloque pueda seguir filtrando linea a linea la cabecera/pie de
    pagina; los spans dentro de una misma linea se concatenan tal cual
    (ya incluyen su propio espaciado)."""
    return "\n".join("".join(span["text"] for span in linea["spans"]) for linea in bloque["lines"])


def _estilo_extremo(bloque: dict, primero: bool) -> str | None:
    """Fuente (p.ej. 'ArialMT' vs 'Arial-ItalicMT') del primer o ultimo
    span con texto real de un bloque. Los titulos de articulo del BOE van
    en cursiva y el cuerpo en redonda; comparar el estilo en el punto de
    union es lo que permite distinguir "el bloque siguiente es la
    continuacion visual de este" de "el bloque siguiente ya es otro
    parrafo", con independencia de si el traductor puso o no punto final
    (ver nota mas abajo: eso variaba entre catala y valencia)."""
    spans = [s for linea in bloque["lines"] for s in linea["spans"] if s["text"].strip()]
    if not spans:
        return None
    return spans[0 if primero else -1]["font"]


def extraer_texto_pdf(ruta: Path) -> tuple[str, int]:
    """Extrae el texto por bloques (parrafos) de cada pagina y filtra los
    que quedan vacios tras la limpieza (cabecera/pie de pagina repetidos en
    cada pagina). Cuando un bloque no acaba en puntuacion de cierre de
    frase, no parece un titular Y ademas comparte tipografia con el
    bloque siguiente en el punto de union, se fusiona con el: el caso
    tipico es un parrafo cortado a mitad de frase por un salto de pagina
    (PyMuPDF extrae bloque a bloque dentro de cada pagina, asi que un
    parrafo que continua en la pagina siguiente llega partido en dos).

    La condicion de tipografia es necesaria porque el criterio de
    puntuacion solo no basta: los titulos de articulo ("Article 1.
    Modificacio de la Llei...", en cursiva) a veces no llevan punto final
    en una de las dos versiones (catala) pero si en la otra (valencia) —
    una pequenya inconsistencia real del PDF oficial, no un error de
    extraccion — asi que fusionar solo por "no acaba en punto" desalineaba
    el parrafo siguiente entre idiomas justo ahi. Al exigir tambien que la
    fuente coincida en el punto de union, el titulo (cursiva) nunca se
    fusiona con el cuerpo del articulo (redona) en ninguno de los dos
    idiomas, se lleve o no punto final.

    Los parrafos finales se unen con una linea en blanco, para que "\n\n"
    marque siempre un limite de parrafo real."""
    parrafos: list[str] = []
    estilo_final: list[str | None] = []
    with pymupdf.open(ruta) as doc:
        for pagina in doc:
            bloques = sorted(
                (b for b in pagina.get_text("dict")["blocks"] if b.get("type") == 0),
                key=lambda b: (b["bbox"][1], b["bbox"][0]),
            )
            for bloque in bloques:
                parrafo = limpiar_bloque(_texto_de_bloque_dict(bloque))
                if not parrafo:
                    continue
                estilo_inicio = _estilo_extremo(bloque, primero=True)
                anterior = parrafos[-1] if parrafos else ""
                fusionable = (
                    anterior
                    and not anterior.endswith(TERMINADORES_PARRAFO)
                    and not _parece_titular(anterior)
                    and not PATRON_ENCABEZADO_ESTRUCTURAL.match(parrafo)
                    and estilo_final[-1] == estilo_inicio
                )
                if fusionable:
                    parrafos[-1] = f"{anterior} {parrafo}"
                else:
                    parrafos.append(parrafo)
                    estilo_final.append(None)
                estilo_final[-1] = _estilo_extremo(bloque, primero=False)
        num_paginas = doc.page_count
    return "\n\n".join(parrafos), num_paginas


def cargar_metadatos_progreso() -> dict:
    if not PROGRESO_PATH.exists():
        return {}
    datos = json.loads(PROGRESO_PATH.read_text(encoding="utf-8"))
    return datos.get("documentos", {})


def listar_ids_base(idioma: str) -> dict[str, Path]:
    cfg = IDIOMAS[idioma]
    sufijo = cfg["sufijo"]
    directorio = CORPUS_DIR / cfg["dir"]
    resultado: dict[str, Path] = {}
    if not directorio.exists():
        return resultado
    for ruta in directorio.rglob(f"*{sufijo}.pdf"):
        base = ruta.stem[: -len(sufijo)]
        resultado[base] = ruta
    return resultado


def main() -> None:
    metadatos = cargar_metadatos_progreso()
    ids_catalan = listar_ids_base("catalan")
    ids_valenciano = listar_ids_base("valenciano")

    bases_emparejadas = sorted(set(ids_catalan) & set(ids_valenciano))
    print(f"Parejas encontradas en disco: {len(bases_emparejadas)}")
    print(f"  Solo català (sin pareja, se ignoran): {len(set(ids_catalan) - set(ids_valenciano))}")
    print(f"  Solo valencià (sin pareja, se ignoran): {len(set(ids_valenciano) - set(ids_catalan))}")

    corpus = []
    for base in bases_emparejadas:
        entrada_pareja = {"id": base}
        fecha = None
        for idioma, cfg in IDIOMAS.items():
            ruta = ids_catalan[base] if idioma == "catalan" else ids_valenciano[base]
            doc_id = f"{base}{cfg['sufijo']}"
            texto, num_paginas = extraer_texto_pdf(ruta)
            meta = metadatos.get(doc_id, {})
            if meta.get("fecha"):
                fecha = meta["fecha"]
            entrada_pareja[idioma] = {
                "id": doc_id,
                "titulo": meta.get("titulo", ""),
                "url": meta.get("url", ""),
                "archivo": str(ruta.relative_to(CORPUS_DIR)),
                "num_paginas": num_paginas,
                "num_caracteres": len(texto),
                "texto": texto,
            }
        entrada_pareja["fecha"] = fecha
        entrada_pareja["anio"] = int(fecha[:4]) if fecha else int(base.split("-")[2])
        corpus.append(entrada_pareja)

    corpus.sort(key=lambda d: (d["fecha"] or "", d["id"]))

    SALIDA_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Guardado: {SALIDA_PATH} ({len(corpus)} parejas de documentos)")


if __name__ == "__main__":
    main()
