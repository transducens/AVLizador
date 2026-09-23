# Glosario dinámico por frase — cómo funciona y qué falla

> **Actualización**: el pipeline ya no lee `palabras_traducidas.json` — desde
> que se detectaron las entradas de esta página, se sustituyó por
> `materiales conversion/lexico/lexico_fiable.json` (194 entradas revisadas
> a mano). El mecanismo de abajo no ha cambiado, solo el fichero de origen;
> las referencias a `palabras_traducidas.json` en el resto de esta página
> son historial (así se encontraron los problemas), no la situación actual.

Además del system prompt (`system_prompt.md`), cada frase recibe una pista
extra construida sobre la marcha a partir del léxico fiable, con formato
`[VOCABULARI: valenciano=catalán, ...]` insertado delante de la frase a
traducir. Código en `evalua_modelos/evalua_models.py`, funciones
`carrega_lexic()` (línea 148) y `glossari_per_frase()` (línea 239).

## Cómo se decide qué palabras entran en la pista

Para cada palabra de la frase de origen (tokenizada, en minúsculas):

1. Se descarta si tiene menos de 4 caracteres (`MIN_LONG`).
2. Se descarta si está en `_STOPWORDS_GLOSSARI` (lista de abajo).
3. Se descarta si su forma valenciana está en `EXCLOSES` al cargar el
   léxico (otra lista, abajo) — esto pasa **una vez**, al arrancar, no por
   frase.
4. Se descarta si `categoria` de la entrada es `"nombre"` (arreglado
   recientemente — antes "Ramon"/"Manuel" se colaban como si fueran
   variantes dialectales).
5. Lo que sobrevive se busca literal en `palabras_traducidas.json`; si hay
   coincidencia, esa palabra entra en la pista `[VOCABULARI: ...]`.

**El punto clave**: es una búsqueda por **string exacto**, sin ningún tipo
de comprensión de significado. Si una palabra del léxico coincide con una
palabra común de otro campo semántico (un adjetivo, un nombre de lugar...),
la pista se dispara igual, aunque no venga a cuento.

## `EXCLOSES` — palabras que nunca entran en el léxico (`evalua_models.py:172`)

```python
EXCLOSES = {
    # Demostratius (gestionats a les regles)
    "este", "esta", "estos", "estes",
    # Temporal (gestionat a les regles)
    "hui", "vesprada",
    # Preposicions i articles — NO al glossari (causen en→amb, a→macu/a, etc.)
    "a", "ab", "amb", "en", "de", "per", "per a", "fins", "fins a",
    "el", "la", "els", "les", "l", "un", "una", "uns", "unes",
    # Pronoms febles i personals curts
    "es", "se", "ho", "li", "hi", "ne", "en", "vos", "us", "jo", "tu",
    "ell", "ella", "ells", "elles", "yo", "ya",
    # Conjuncions
    "i", "o", "ni", "que", "si", "com", "però", "mes",
    # Adverbis curts ja gestionats
    "on", "ja",
    # Paraules curtes amb falsos positius al JSON (≤3 car.)
    "foc", "nus", "pes", "cel", "cos", "peu", "pla", "pou", "res",
    "riu", "rot", "sal", "set", "sol", "son", "tos", "tot", "vel",
    "via", "veu", "vot", "gel", "got", "gos", "gas", "fas", "poc",
    "dos", "tot", "ben", "molt", "cap", "tan",
}
```

## `_STOPWORDS_GLOSSARI` — no entran en la pista aunque pasen el filtro de longitud (`evalua_models.py:230`)

```python
_STOPWORDS_GLOSSARI = {
    "molt", "cada", "quan", "però", "aquest", "aquesta", "aquests", "aquestes",
    "mateix", "mateixa", "també", "encara", "entre", "sobre", "altre", "altra",
    "altres", "algun", "alguna", "alguns", "algunes", "sense", "segons",
    "mentre", "perquè", "perque", "doncs", "llavors", "després", "abans",
    "sempre", "sovint", "potser", "nomes", "només", "totes", "tots",
}
```

## Entradas problemáticas encontradas (auditoría + revisión manual)

Esta tabla junta **todo** lo que se ha encontrado hasta ahora en
`palabras_traducidas.json` que dispara con una palabra de otro campo
semántico. Las marcadas ✅ ya están arregladas; las marcadas ⚠️ siguen sin
tocar — decide tú si merece la pena añadirlas a `EXCLOSES` o
`_STOPWORDS_GLOSSARI`, o corregir la entrada del propio JSON.

| Entrada del léxico | Colisiona con | Estado | Cómo se arregló / cómo se arreglaría |
|---|---|---|---|
| `Ramon → Ramó` | nombre de persona | ✅ arreglado | excluido por `categoria == "nombre"` |
| `Manuel → Manel` | nombre de persona | ✅ arreglado | excluido por `categoria == "nombre"` |
| `Blanca/Picarassa → Garsa` (el pájaro) | adjetivo "blanca" (=blanco) | ✅ arreglado en el corpus ya generado | revertido con `repara_corpus.py`; la entrada del léxico sigue intacta — **volverá a pasar en cualquier generación futura** si no se corrige la entrada o se añade "blanca" a una lista de exclusión |
| `Pròxim → Proïsme` (sentido religioso "el prójimo") | adjetivo común "pròxim" (=siguiente/cercano) | ✅ arreglado en el corpus ya generado | mismo caso que "blanca": la entrada del JSON sigue ahí |
| `Real → Reial` (adjetivo "real"/regio) | topónimos con "real" (Vila-real...), y cualquier uso no regio de "real" | ⚠️ sin arreglar | encontrado en la revisión manual (`Vila-real Club de Futbol` → `Vila-reial Club de Futbol`); candidato claro a `EXCLOSES` o a revisar caso por caso |
| `Tots → Tothom` (pronombre indefinido) | adjetivo/cuantificador "tots" (=todos), uso mucho más frecuente | ⚠️ sin arreglar | detectado en la auditoría (0,3% de "cumplimiento" — casi siempre NO debería cambiar); candidato a `_STOPWORDS_GLOSSARI` |
| `Temps → Estona` (sentido "un rato") | "temps" (tiempo/meteorológico), uso mucho más frecuente | ⚠️ sin arreglar | mismo tipo de problema que "tots" |
| `Espai → Estona` (sentido temporal) | "espai" (espacio físico) | ⚠️ sin arreglar | ídem |
| `Roig → Vermell` (color) | cognom valenciano muy frecuente ("Roig") | ⚠️ sin arreglar | aquí la entrada del léxico es correcta para el color; el problema es que "Roig" también es apellido — difícil de distinguir sin mirar mayúsculas/contexto |
| `Celebració → Cel.lebració` | — | ✅ arreglado | confirmado como entrada errónea (no es diferencia dialectal real); borrada de `palabras_traducidas.json` y revertidas las 56 apariciones en el corpus ya generado con `repara_corpus.py` |
| `Demanar/Solicitar → Sol·licitar` | — | ⚠️ dudosa, no es variante dialectal | es una recomendación de registro formal (como "pedir" vs "solicitar" en castellano), no una diferencia entre valenciano y catalán — "demanar" es igual de correcto en los dos |
| `Llavors → Aleshores` | — | ⚠️ dudosa, no es variante dialectal | ambas son válidas en catalán estándar general, no es una oposición occidental/oriental clara |

## Qué hacer con esta lista

No hay una única respuesta correcta — depende de cuánto quieras confiar en
el léxico curado frente a intervenir tú a mano. Dos caminos, no excluyentes:

1. **Rápido y seguro**: añadir las palabras de la columna "colisiona con"
   (`real`, `tots`, `temps`, `espai`, `roig`) a `EXCLOSES` en
   `evalua_models.py` — quita esas palabras del glosario dinámico por
   completo. Coste: pierdes la ayuda del glosario en los (pocos) casos
   donde la traducción SÍ era la correcta.
2. **Más fino, más trabajo**: revisar `palabras_traducidas.json` a mano
   (columna "Entrada del léxico") y decidir entrada por entrada si tiene
   sentido conservarla, borrarla, o corregirla — `celebració`,
   `demanar/solicitar` y `llavors` probablemente sobran directamente.

Ninguna de las dos corrige lo que **ya está generado** en el corpus salvo
que vuelvas a ejecutar `repara_corpus.py` con las reglas de reversión
ampliadas, o regeneres esas frases concretas.
