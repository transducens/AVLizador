#!/usr/bin/env python3
"""Genera un visor HTML de TODAS las frases de `dades/boe_net/corpus_entrenamiento_net.jsonl`
que tienen alguna diferencia real, con DOS pestanyas:

  - "Mayor diferencia primero" (similitud ascendente): para encontrar
    errores de alineamiento reales, empezando por lo mas sospechoso.
  - "Mayor similitud primero" (similitud descendente): para ver las
    frases casi identicas salvo por un detalle -- normalmente el tipo de
    caso mas limpio de sustitucion dialectal puntual (vore conversacion
    sobre `ratio_medio_frase` en `depurar_ruido_estilistico.py`, misma
    idea aplicada aqui a nivel de frase entera, no de par de palabras).

El diff de cada frase (`_marcar_par_html`, lo caro de calcular) se hace
UNA sola vez por frase y se reutiliza para las dos pestanyas -- solo
cambia el orden en que se escriben los chunks, no se recalcula nada dos
veces.

Complementa a `analizar_corpus.py` (que solo mira los 169 documentos con
parrafos alineados 1 a 1) y a `depurar_ruido_estilistico.py` (que agrupa
por PAR de palabras, no por frase): este visor es a nivel de FRASE y
cubre los 520 documentos completos via `corpus_entrenamiento_net.jsonl`.

Arquitectura de fichero (misma lección que `analizar_corpus.py`, vore su
README): las frases NO se embeben todas en el HTML -- con ~178.000 frases
eso pesaria mas de 150 MB otra vez. Se escriben en "chunks" (trozos) de
`TAMANO_CHUNK` frases cada uno, ya ordenados, y el HTML los carga con
fetch() uno a uno segun el usuario hace scroll / pulsa "Cargar mas" --
por eso hace falta un servidor local para usarlo (vore el aviso que
imprime el script y el mensaje de error en la propia pagina).

Uso:
    python generar_visor_diferencias.py
    python generar_visor_diferencias.py --limit 20000   # solo las 20.000 frases (de cada orden), para probar rapido
    python generar_visor_diferencias.py --solo-html     # solo reescribe el HTML, no recalcula nada
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOE_DIR = Path(__file__).resolve().parent
NET_DIR = BOE_DIR.parent / "dades" / "boe_net"
ENTRADA_PATH = NET_DIR / "corpus_entrenamiento_net.jsonl"
SALIDA_HTML = NET_DIR / "visor_diferencias.html"
CHUNKS_DIR_GRANDES = NET_DIR / "visor_diferencias_chunks"
CHUNKS_DIR_PEQUENAS = NET_DIR / "visor_diferencias_chunks_similares"

sys.path.insert(0, str(BOE_DIR))
from analizar_corpus import CSS, _marcar_par_html  # noqa: E402

TAMANO_CHUNK = 1000


def cargar_frases(limite: int | None) -> list[dict]:
    """Lee el corpus net y descarta las identicas -- SIN ordenar todavia,
    el orden lo decide quien llama segun para que pestanya es."""
    frases = []
    with open(ENTRADA_PATH, encoding="utf-8") as f:
        for linea in f:
            r = json.loads(linea)
            if r["texto_catalan"].strip() == r["texto_valenciano"].strip():
                continue  # identicas: diferencia cero, no aportan nada a este visor
            frases.append(r)
    if limite is not None:
        frases.sort(key=lambda r: r["similitud"])
        frases = frases[:limite] + frases[-limite:]
    return frases


def procesar_marcado(frases: list[dict]) -> list[dict]:
    """Calcula el HTML resaltado de cada frase UNA sola vez (lo caro),
    para poder reordenarlo despues sin repetir el diff."""
    procesadas = []
    for r in frases:
        _, html_cat, html_val = _marcar_par_html(r["texto_catalan"], r["texto_valenciano"])
        procesadas.append(
            {
                "doc": r["documento_id"],
                "fecha": r.get("fecha", ""),
                "similitud": round(r["similitud"], 3),
                "html_cat": html_cat,
                "html_val": html_val,
            }
        )
    return procesadas


def escribir_chunks(filas_procesadas: list[dict], directorio: Path, ascendente: bool) -> int:
    """Ordena (sin recalcular el marcado) y escribe los chunks. `ascendente=True`
    -> similitud ascendente (mayor diferencia primero); `False` -> mayor
    similitud primero."""
    directorio.mkdir(parents=True, exist_ok=True)
    for viejo in directorio.glob("chunk_*.json"):
        viejo.unlink()

    filas_ordenadas = sorted(filas_procesadas, key=lambda f: f["similitud"], reverse=not ascendente)

    num_chunks = 0
    for inicio in range(0, len(filas_ordenadas), TAMANO_CHUNK):
        trozo = filas_ordenadas[inicio : inicio + TAMANO_CHUNK]
        (directorio / f"chunk_{num_chunks:04d}.json").write_text(
            json.dumps(trozo, ensure_ascii=False), encoding="utf-8"
        )
        num_chunks += 1
    return num_chunks


HTML_TEMPLATE = """<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visor de diferencias — corpus BOE net</title>
<style>{css}
.resumen {{ color: var(--texto-tenue); margin: 0 0 1rem; }}
.aviso-servidor {{ background: var(--superficie); border: 1px solid var(--borde); border-radius: 10px; padding: 1rem; margin: 1rem 0; }}
.aviso-servidor code {{ display: block; margin: .4rem 0; }}
</style>
</head>
<body>
<header class="cabecera">
  <h1>Visor de diferencias — corpus BOE net</h1>
  <p>{total} frases con diferencia real. Fuente: <code>dades/boe_net/corpus_entrenamiento_net.jsonl</code>
     (520 documentos, ya sin ruido de mayusculas ni reordenamiento puro).</p>
</header>
<nav class="pestanas">
  <button data-pestana="grandes" class="activa">Mayor diferencia primero</button>
  <button data-pestana="pequenas">Mayor similitud primero</button>
</nav>
<main>
  <div id="aviso" class="aviso-servidor" hidden>
    <strong>No se pudo cargar.</strong> Esta pagina carga las frases por trozos con <code>fetch()</code>
    (son demasiadas para meterlas todas en el HTML). La mayoria de navegadores bloquean eso si abres
    el fichero haciendo doble clic (<code>file://</code>). Arranca un servidor local desde esta carpeta:
    <code>cd dades/boe_net &amp;&amp; python -m http.server 8000</code>
    y abre <code>http://localhost:8000/visor_diferencias.html</code>
  </div>

  <section id="pestana-grandes" class="pestana activa">
    <p class="explicacion">Ordenadas de mas a menos diferencia (similitud ascendente) -- para encontrar
       errores de alineamiento reales, empezando por las mas sospechosas.</p>
    <div class="visor-controles">
      <input type="text" id="filtro-grandes" placeholder="Buscar palabra o documento...">
      <span class="contador-filas" id="contador-grandes"></span>
    </div>
    <div class="visor-lista" id="lista-grandes"></div>
    <button class="visor-mas" id="mas-grandes">Cargar mas frases</button>
  </section>

  <section id="pestana-pequenas" class="pestana">
    <p class="explicacion">Ordenadas de mas a menos similitud (similitud descendente) -- casi identicas salvo
       un detalle, normalmente el caso mas limpio de sustitucion dialectal puntual.</p>
    <div class="visor-controles">
      <input type="text" id="filtro-pequenas" placeholder="Buscar palabra o documento...">
      <span class="contador-filas" id="contador-pequenas"></span>
    </div>
    <div class="visor-lista" id="lista-pequenas"></div>
    <button class="visor-mas" id="mas-pequenas">Cargar mas frases</button>
  </section>
</main>
<footer>Generado por <code>generar_visor_diferencias.py</code>. {num_chunks_grandes} + {num_chunks_pequenas}
  trozos de datos en <code>visor_diferencias_chunks*/</code>.</footer>
<script>
const aviso = document.getElementById('aviso');

document.querySelectorAll('nav.pestanas button').forEach(b => {{
  b.addEventListener('click', () => {{
    document.querySelectorAll('nav.pestanas button').forEach(x => x.classList.toggle('activa', x === b));
    document.querySelectorAll('section.pestana').forEach(s => s.classList.toggle('activa', s.id === 'pestana-' + b.dataset.pestana));
  }});
}});

function crearVisor(prefijo, directorioChunks, numChunks) {{
  const lista = document.getElementById('lista-' + prefijo);
  const contador = document.getElementById('contador-' + prefijo);
  const btnMas = document.getElementById('mas-' + prefijo);
  const filtro = document.getElementById('filtro-' + prefijo);

  let siguienteChunk = 0;
  let todasLasFilas = [];  // acumula TODO lo ya cargado, para poder filtrar sin re-pedir nada

  function repintar() {{
    const texto = filtro.value.trim().toLowerCase();
    const visibles = !texto ? todasLasFilas : todasLasFilas.filter(f =>
      f.html_cat.toLowerCase().includes(texto) || f.html_val.toLowerCase().includes(texto) ||
      f.doc.toLowerCase().includes(texto));
    lista.innerHTML = visibles.map(f => `
      <div class="visor-frase con-dif">
        <div class="visor-num">${{f.doc}} &middot; ${{f.fecha || '?'}} &middot; ${{(f.similitud*100).toFixed(1)}}% similar</div>
        <div class="visor-linea"><span class="visor-tag visor-tag-ca">CA</span><span class="visor-texto">${{f.html_cat}}</span></div>
        <div class="visor-linea"><span class="visor-tag visor-tag-va">VA</span><span class="visor-texto">${{f.html_val}}</span></div>
      </div>
    `).join('');
    const etiquetaFiltro = texto ? ' (filtradas de ' + todasLasFilas.length + ' cargadas)' : '';
    contador.textContent = visibles.length + ' frase(s)' + etiquetaFiltro + ' -- ' + siguienteChunk + ' de ' + numChunks + ' trozos cargados';
  }}

  async function cargarSiguienteChunk() {{
    if (siguienteChunk >= numChunks) {{ btnMas.hidden = true; return; }}
    try {{
      const resp = await fetch(directorioChunks + '/chunk_' + String(siguienteChunk).padStart(4, '0') + '.json');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const filas = await resp.json();
      todasLasFilas = todasLasFilas.concat(filas);
      siguienteChunk++;
      repintar();
      if (siguienteChunk >= numChunks) btnMas.hidden = true;
    }} catch (e) {{
      aviso.hidden = false;
      btnMas.hidden = true;
    }}
  }}

  filtro.addEventListener('input', repintar);
  btnMas.addEventListener('click', cargarSiguienteChunk);
  cargarSiguienteChunk();
}}

crearVisor('grandes', 'visor_diferencias_chunks', {num_chunks_grandes});
crearVisor('pequenas', 'visor_diferencias_chunks_similares', {num_chunks_pequenas});
</script>
</body>
</html>
"""


def contar_chunks_y_filas(directorio: Path) -> tuple[int, int]:
    archivos = list(directorio.glob("chunk_*.json"))
    total = sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in archivos)
    return len(archivos), total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Solo las N frases con mas diferencia + N con mas similitud (para pruebas)",
    )
    parser.add_argument(
        "--solo-html",
        action="store_true",
        help="No recalcula los chunks (lento, recorre todo el corpus) -- solo reescribe el HTML "
        "a partir de los chunks ya existentes. Util tras un cambio en la plantilla/JS.",
    )
    args = parser.parse_args()

    if args.solo_html:
        num_chunks_grandes, total_grandes = contar_chunks_y_filas(CHUNKS_DIR_GRANDES)
        num_chunks_pequenas, _ = contar_chunks_y_filas(CHUNKS_DIR_PEQUENAS)
        if num_chunks_grandes == 0:
            raise SystemExit(f"No hay chunks en {CHUNKS_DIR_GRANDES}; ejecuta primero sin --solo-html")
        total = total_grandes
    else:
        if not ENTRADA_PATH.exists():
            raise SystemExit(f"No existe {ENTRADA_PATH}; ejecuta primero depurar_ruido_estilistico.py")

        print("Cargando frases con diferencia real...")
        frases = cargar_frases(args.limit)
        print(f"  {len(frases)} frases")

        print("Calculando el diff resaltado de cada frase (una sola vez)...")
        procesadas = procesar_marcado(frases)
        total = len(procesadas)

        print(f"Escribiendo '{CHUNKS_DIR_GRANDES.name}/' (mayor diferencia primero)...")
        num_chunks_grandes = escribir_chunks(procesadas, CHUNKS_DIR_GRANDES, ascendente=True)
        print(f"  {num_chunks_grandes} trozos")

        print(f"Escribiendo '{CHUNKS_DIR_PEQUENAS.name}/' (mayor similitud primero)...")
        num_chunks_pequenas = escribir_chunks(procesadas, CHUNKS_DIR_PEQUENAS, ascendente=False)
        print(f"  {num_chunks_pequenas} trozos")

    html = HTML_TEMPLATE.format(
        css=CSS, total=total, num_chunks_grandes=num_chunks_grandes, num_chunks_pequenas=num_chunks_pequenas
    )
    SALIDA_HTML.write_text(html, encoding="utf-8")
    print(f"Guardado: {SALIDA_HTML}")
    print()
    print("Para abrirlo, hace falta un servidor local (fetch() no funciona con doble clic):")
    print(f"  cd {NET_DIR}")
    print("  python -m http.server 8000")
    print("  -> http://localhost:8000/visor_diferencias.html")


if __name__ == "__main__":
    main()
