*[Read it in Catalan](README.md)*

# Etapa 8 — Traducción de corpus completo con el motor de reglas

Aplica `traductor/` (el motor determinista de reglas, etapa 5) a un
corpus **entero**, documento a documento -- no a una sola frase suelta
(como `python -m traductor.cli`) ni a las 150 frases ya curadas a mano
del benchmark (`03_seleccio_de_model/evalua_models.py --model traductor`).

## Por qué hace falta una etapa aparte

Hasta ahora, cada vez que se mide si una regla nueva
(`concordanca_dos_dues.py`, `relatiu_on.py`...) funciona bien, se mide
SOLO contra esas 150 frases -- y son frases elegidas precisamente porque
contienen ejemplos claros de los fenómenos dialectales documentados. Eso
dice si una regla es correcta, pero no dice **cómo se comporta sobre
miles de frases reales sin seleccionar**, que es donde aparecerán los
casos raros, las combinaciones inesperadas de reglas, o los fenómenos que
el benchmark simplemente no cubre por azar.

El objetivo final (ver "El plan completo" abajo) no es solo tener un
benchmark perfecto, es **poder confiar en el motor cuando se traduce un
corpus completo** -- y eso solo se puede comprobar traduciendo uno de
verdad.

## Estructura

```
08_traduccio_corpus/
├── traduccio_massiva.py   aplica traductor/ a un corpus .jsonl entero
├── eixides/               ficheros generados (gitignored, regenerables)
└── postprocessat_llm/     fase 2 del plan, todavía NO implementada (ver abajo)
```

## Uso

```bash
cd 08_traduccio_corpus
python traduccio_massiva.py
# por defecto lee ../dades/avl/final/dialectal/corpus_occidental_net.jsonl
# y escribe eixides/corpus_traduit_regles.jsonl

python traduccio_massiva.py --limit 50          # solo los primeros 50 documentos, para pruebas
python traduccio_massiva.py --input otro.jsonl --camp-text cuerpo --output eixides/prueba.jsonl
```

Cada línea de la salida es `{"id", "text_occidental", "text_oriental_regles"}`.

## Limitaciones conocidas (a propósito, documentadas, no arregladas todavía)

- **Segmentación de frases simplificada**: `segmenta_frases()` separa por
  punto/interrogación/exclamación + espacio. No gestiona abreviaturas
  ("Dr.", "núm.") ni puntos suspensivos con precisión -- una abreviatura
  puede cortar una frase por la mitad. Necesario porque
  `marca_noms_propis()` (ver `traductor/rules/__init__.py`) solo exime de
  sospecha de nombre propio a la PRIMERA palabra de todo lo que se le
  pasa -- sin esta segmentación, la primera palabra de cada frase (2ª,
  3ª...) de un documento se marcaría erróneamente como posible nombre
  propio y se saltaría.
- **Un único campo de texto por documento** (`--camp-text`, por defecto
  `"text"`): no combina `title` + `text`, no gestiona estructura HTML/
  Markdown dentro del texto.
- **Ningún mecanismo de etiquetado todavía**: la salida solo tiene el
  texto traducido, no dice QUÉ palabras o construcciones son de alta
  confianza (regla de lookup exacto) y cuáles son dudosas o no se han
  tocado. Eso es la fase 2 del plan (ver abajo) -- a propósito todavía no
  implementado.

## El plan completo (2 fases)

**Fase 1 -- esta carpeta (hecha)**: traducir el corpus entero con el
motor de reglas tal como está hoy, puro determinista, sin ningún LLM.
Buena para casos de alta confianza (lookup exacto, concordancias
inequívocas), pero se sabe que hay fenómenos gramaticales documentados en
`02_regles_dialectals/docs_gramatica/` que NO puede resolver con
seguridad (p.ej. "per"→"per a", que depende de si tiene valor de causa o
de finalidad -- ver `traductor/README.es.md`, sección "DECISIÓN DE
ARQUITECTURA" 02/10/2026).

**Fase 2 -- `postprocessat_llm/` (pendiente, NO implementada)**: en vez
de intentar que el motor de reglas lo resuelva todo (arriesgado, como ya
se ha visto con los intentos de heurística automática de género), el
plan es **etiquetar** dentro de `traductor/` los casos donde una regla es
dudosa o donde ninguna regla actúa pero se sabe que puede haber una
diferencia dialectal, y que un modelo de lenguaje revise SOLO esos puntos
marcados -- no toda la frase -- usando las guías de `docs_gramatica/`
como referencia. Todavía queda por decidir:
- Qué formato tendrá la marca (¿a nivel de `Token`? ¿de frase entera?).
- Qué modelo LLM (local vía Ollama, como el resto del proyecto, u otro).
- Si el LLM propone un cambio o solo señala para revisión humana.

Ver `postprocessat_llm/README.es.md` para el estado de esta decisión.
