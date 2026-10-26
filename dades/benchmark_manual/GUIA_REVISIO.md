# Guía de revisión del benchmark manual catalán → valenciano

Esta guía explica cómo revisar a mano las frases de `revisio_persona1.json` y
`revisio_persona2.json`. Cada persona revisa **solo su fichero**.

## Para qué sirve

Queremos un banco de unas **400 frases** (200 del BOE y 200 de la AVL) con
las que medir el traductor **catalán → valenciano**. Cada frase tiene un
catalán de entrada y un valenciano de referencia. Al traductor se le da el
catalán, y su salida se compara con el valenciano.

Por eso las dos frases de cada par tienen que decir **lo mismo, con las mismas
palabras y la misma estructura**. Solo pueden cambiar las diferencias
dialectales: "aquesta/esta", "seva/seua", "avui/hui", "sigui/siga", "per
fer/per a fer", "dues/dos", "serveix/servix", "francès/francés"…

Hay más candidatas de las necesarias (unas 235 por persona) para poder
descartar las que no sirvan.

## Qué hay en el fichero

El fichero es un JSON con dos claves: `instruccions` (un resumen de esta
guía) y `frases`, la lista de frases. Cada frase es un objeto así:

```json
{
 "valida": null,
 "oriental_corregit": null,
 "occidental_corregit": null,
 "comentari": "",
 "id": "BM-AVL-002",
 "font": "avl",
 "oriental": "Com t'haig dit adès, no crec que hagi estat ell.",
 "oriental_es_esborrany": true,
 "occidental": "Com t'he dit adés, no crec que haja sigut ell.",
 "fenomens": ["CONJ_IND: haig → he", "CONJ_IND: hagi → haja", "CONJ_PART: estat → sigut", "ACC: adès → adés"],
 "ipd_valencia": 1.0,
 "marcadors_valencians": ["he", "haja", "sigut"],
 "ipd_catala": null,
 "marcadors_catalans": null,
 "doc_type": "gramatica_normativa",
 "document": "AVL-001658",
 "titol": "27. ELS ADVERBIS",
 "url": "https://www.avl.gva.es/gnv/buscador.jsp?gramatica=GNV&index=GNV#capitol_27",
 "data": "2006-01-01T00:00:00",
 "id_origen": "AVL-001658"
}
```

### Campos que rellenas tú (los cuatro primeros)

| campo | qué poner |
|---|---|
| `valida` | `true` si la frase sirve, `false` si no sirve, `"dubtosa"` si no lo tienes claro (explica por qué en `comentari`). |
| `oriental_corregit` | Si el **catalán** necesita algún cambio, la frase catalana **entera** ya corregida. Si está bien, déjalo en `null`. |
| `occidental_corregit` | Si el **valenciano** necesita algún cambio, la frase valenciana **entera** ya corregida. Si está bien, déjalo en `null`. |
| `comentari` | Opcional. Cualquier cosa que quieras señalar (por qué la descartas, una duda…). |

### Campos de información (no se tocan)

| campo | qué es |
|---|---|
| `id` | Identificador de la frase: `BM-BOE-…` o `BM-AVL-…`. |
| `font` | De dónde sale: `boe` o `avl`. |
| `oriental` | La frase en **catalán** (la entrada del traductor). |
| `oriental_es_esborrany` | `true` en las frases de la AVL: ese catalán **no es humano**, lo ha generado el traductor valenciano → catalán y **hay que revisarlo siempre**. `false` en el BOE (catalán oficial). |
| `occidental` | La frase en **valenciano** (la referencia). |
| `fenomens` | Las diferencias dialectales que se han detectado en la frase, como `CÓDIGO: catalán → valenciano` (los códigos están en la tabla de abajo). Sirven para fijarte en ellas; no hace falta corregir esta lista. Si en la AVL pone `[l'esborrany no ho ha convertit]`, el borrador catalán ha dejado esa palabra en valenciano: corrígela. `(homògraf)` indica una palabra con dos sentidos. |
| `ipd_valencia`, `marcadors_valencians` | Índice de pureza dialectal del valenciano (1,0 = todas las formas marcadas son valencianas) y las palabras que lo marcan. |
| `ipd_catala`, `marcadors_catalans` | Lo mismo para el catalán (0,0 = todas catalanas). Solo en el BOE. |
| `doc_type`, `document`, `titol`, `url`, `data`, `id_origen` | De qué documento sale la frase. Usa `url` si necesitas ver el contexto. |

### Códigos de fenómenos

| código | qué es | ejemplo catalán → valenciano |
|---|---|---|
| `LEX_NOM`, `LEX_ADJ`, `LEX_ADV`, `LEX_ALTRES` | léxico: nombre, adjetivo, adverbio, otros | feina → faena, avui → hui |
| `DEM` | demostrativos | aquesta → esta |
| `POS` | posesivos | seva → seua |
| `NUM` | numerales y ordinales | vuit → huit |
| `CONJ_IND`, `CONJ_SUBJ`, `CONJ_IMP`, `CONJ_INF`, `CONJ_PART` | formas verbales: indicativo, subjuntivo, imperativo, infinitivo, participio | sigui → siga, tenir → tindre |
| `CONJ_ARREL`, `CONJ_ALTRES` | verbos con raíz distinta; formas sin clasificar | sortir → eixir |
| `PER_A` | "per" + infinitivo → "per a" | per fer → per a fer |
| `DOS_DUES` | "dues" → "dos" | les dues parts → les dos parts |
| `INC` | verbos incoativos | ofereix → oferix |
| `ACC` | acentuación | francès → francés |

El código del verbo puede no ser exacto en alguna forma con dos lecturas
(por ejemplo, "suspèn → suspén" sale como imperativo). No importa para la
revisión.

## Qué hay que hacer con cada frase

### 1. ¿Sirve? (`valida`)

Pon `false` si:

- No es una frase completa y natural: está cortada, es un título, una lista o
  tiene restos de formato o de OCR.
- Es **metalingüística**: habla de palabras ("La variant *trast*…", "es diu…",
  citas en latín…).
- El valenciano no es **valenciano estándar de la AVL**: formas coloquiales o
  subdialectales que la norma no recoge, o catalanismos.
- En el BOE, el valenciano reformula tanto que no compensa corregirlo.

Si sirve (aunque haya que corregir algo), pon `true`.

### 2. Frases del BOE (`font: "boe"`)

- El **catalán** es el oficial. Normalmente se queda igual (`oriental_corregit:
  null`). Corrígelo solo si tiene un error claro o una forma valenciana.
- El **valenciano** tiene que ser una **adaptación dialectal fiel** del
  catalán. A veces el BOE reformula: cambia el orden, parte la frase, cambia
  un tiempo verbal, añade o quita palabras. En ese caso escribe en
  `occidental_corregit` el valenciano que corresponde palabra por palabra al
  catalán, cambiando solo lo dialectal.

  Ejemplo (BM-BOE-069):
  - catalán: "El transcurs dels terminis que estableix l’apartat precedent
    determina la caducitat del procediment administratiu sancionador, i cal
    procedir a dictar un nou acord d’incoació mentre no hagi prescrit la
    infracció de conformitat amb el que disposa l’article 60. 5."
  - valenciano del BOE (reformula: "establits en", "determinarà", parte la
    frase, "Caldrà"): "El transcurs dels terminis establits en l’apartat
    precedent determinarà la caducitat del procediment administratiu
    sancionador. Caldrà dictar un nou acord d’incoació mentres no haja
    prescrit la infracció, de conformitat amb el que disposa l’article 60. 5."
  - `occidental_corregit`: "El transcurs dels terminis que establix
    l’apartat precedent determina la caducitat del procediment administratiu
    sancionador, i cal procedir a dictar un nou acord d’incoació mentres no
    haja prescrit la infracció de conformitat amb el que disposa l’article
    60. 5."

### 3. Frases de la AVL (`font: "avl"`)

- El **valenciano** es el texto original de la AVL. Normalmente se queda igual.
- El **catalán** es un **borrador automático** y **siempre hay que revisarlo**.
  Tiene que quedar como **catalán estándar (norma del IEC), natural**, y
  equivalente palabra por palabra al valenciano, salvo las diferencias
  dialectales. Escribe la frase catalana entera en `oriental_corregit` aunque
  solo cambies una palabra; si el borrador ya está perfecto, deja `null`.

  Ejemplo (BM-AVL-002): borrador "Com t'haig dit adès, no crec que hagi estat
  ell." → corrección "Com t'he dit adès, no crec que hagi estat ell."
  ("t'haig dit" no es correcto; en catalán es "t'he dit").

  Errores típicos del borrador:
  - **Verbos en 3ª persona del plural en "-en"**: en valenciano "guien",
    "recuperen" pueden ser indicativo o subjuntivo, y el borrador a veces pone
    subjuntivo cuando es indicativo ("es guien i cacen" → borrador "es guiïn",
    debe ser "es guien"). Mira siempre el sentido.
  - "naix" → el borrador pone "naeix"; debe ser "neix".
  - Palabras que se han quedado en valenciano (las marcadas con
    `[l'esborrany no ho ha convertit]`).

## Cómo editar el fichero

- Ábrelo con **VS Code** (o cualquier editor de texto), no con Word.
- Toca **solo** los cuatro primeros campos de cada frase.
- Escribe los textos entre comillas dobles: `"oriental_corregit": "La frase…"`.
  Si la frase tiene comillas dobles dentro, cámbialas por « » o escríbelas como
  `\"`.
- `true`, `false` y `null` van **sin comillas** y en minúscula. `"dubtosa"` va
  con comillas.
- Respeta el apóstrofo que use la frase (`'` o `’`).
- Guarda en **UTF-8** (es lo normal en VS Code). Si VS Code subraya algo en
  rojo, el JSON se ha roto: suele ser una coma o una comilla.
- Puedes guardar y seguir otro día; no se pierde nada.

## Cuando termines

Devuelve el fichero con el mismo nombre. Con las dos revisiones se aplican las
correcciones, se recalcula el IPD de las frases corregidas y, si algún
fenómeno se queda por debajo del mínimo, se propone una segunda tanda corta.

El criterio completo y las decisiones del proyecto están en
`documentacio/hoja_de_ruta_benchmark_manual.md`.
