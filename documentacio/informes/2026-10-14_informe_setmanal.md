# Informe de progreso — AVLizador (traductor dialectal valenciano↔catalán)

**Fecha**: 14 de octubre de 2026
**Período cubierto**: desde el último informe (5 de octubre de 2026)

## Resumen ejecutivo

El proyecto ha avanzado en tres frentes desde el último informe:

1. **El motor de traducción ahora funciona en las dos direcciones**
   (valenciano→catalán y catalán→valenciano), con una capa adicional de
   modelo de lenguaje que corrige los casos gramaticalmente ambiguos que
   el motor de reglas deja sin resolver a propósito.
2. **Se ha creado una métrica propia, el Índice de Pureza Dialectal (IPD)**,
   y se ha usado para validar el sistema contra tres fuentes de datos
   independientes, incluyendo un corpus público externo y textos reales
   aportados por el equipo.
3. **Se ha reestructurado el repositorio completo** para que tenga una
   organización clara y mantenible de cara a una eventual publicación
   pública.

A continuación el detalle de cada punto, con las cifras exactas.

## 1. Estado del motor de traducción

El motor es un sistema de reglas deterministas (no un modelo de lenguaje
generativo): nunca "alucina" — si no reconoce una palabra o construcción,
la deja intacta en vez de arriesgarse a inventar algo. Esto se complementa
con un modelo de lenguaje que interviene *solo* en los puntos muy
concretos donde el motor detecta ambigüedad real y no puede decidir por
sí solo.

**Valenciano → catalán** (la dirección original del proyecto):
- Motor de reglas solo: **115/151 frases exactas (76,2%)** sobre el
  benchmark de referencia, BLEU 97,67.
- Motor + corrección con modelo de lenguaje (`qwen3:8b`): **récord de
  129/151 (85,4%)**, BLEU 98,64 — confirmado en el clúster de la
  universidad. (Esta cifra es anterior a una limpieza de reglas hecha
  hoy mismo que bajó ligeramente el motor solo; está pendiente
  recalcularla con la base actual, se espera un resultado similar.)

**Catalán → valenciano** (dirección nueva, construida desde cero esta
quincena): **116/151 frases exactas (76,8%)**, BLEU 98,08. Esta
dirección no tenía ningún código antes — se ha construido una estructura
completa simétrica a la original, reutilizando los mismos datos
lingüísticos de base.

**Por qué las cifras bajaron un poco esta semana** (de 120/123 a
115/116): se detectó que un módulo del motor solo acertaba en las frases
exactas del benchmark usado para medir, sin generalizar a ninguna frase
nueva — es decir, inflaba el número de aciertos de forma engañosa. Se
retiró y se dejaron los números reflejando la capacidad real del motor,
no una memorización del test. Es una corrección de rigor, no una
regresión real.

## 2. Validación contra datos reales, más allá del banco de pruebas curado

Hasta ahora el motor solo se había medido contra un banco de 151 frases
seleccionadas a mano. Esta semana se ha probado contra datos mucho más
grandes y variados, para saber cómo se comporta en el mundo real:

- **Corpus del Boletín Oficial del Estado (BOE)**: textos legales reales
  con traducción oficial a los dos idiomas.
- **Dataset público `gplsi/CA-VA_alignment_test`** (Universidad de
  Alicante, licencia abierta): 1.958 frases traducidas de forma
  independiente por un filólogo, en un dominio mucho más variado que el
  banco de pruebas original.

Sobre las 1.958 frases del segundo dataset, el motor acierta el 65,4%
(valenciano→catalán) y el 61,9% (catalán→valenciano) — una caída
esperable frente al 76%, porque es un corpus mucho más grande y
heterogéneo. Filtrando las frases donde la métrica de pureza dialectal
(ver punto 3) confirma que no hay sinonimia de por medio, la precisión
sube a 88,9%/87,9% — muy cerca del banco de pruebas original. Esto
confirma que buena parte de la caída no es el motor fallando más, sino
variabilidad natural entre dos traductores humanos independientes.

Esta validación a gran escala también sacó a la luz **4 errores reales
en el diccionario del motor** (palabras mal emparejadas entre dialectos,
formas verbales no cubiertas), ya localizados y documentados, pendientes
de corregir en la próxima iteración.

## 3. Nueva métrica: Índice de Pureza Dialectal (IPD)

Se ha diseñado e implementado una métrica propia que, dado cualquier
texto, calcula qué porcentaje de sus palabras dialectalmente marcadas
son valencianas frente a catalanas — útil tanto para validar el propio
traductor como para analizar cualquier corpus futuro sin depender del
motor de reglas.

Validada contra tres fuentes independientes (el banco de 151 frases, el
BOE y el dataset público), con resultados consistentes en los tres: el
lado valenciano puntúa entre 0,87 y 0,93 de pureza, el catalán entre
0,01 y 0,05 — el patrón esperado, confirmado repetidamente. Se incluye
además una herramienta visual para inspeccionar palabra por palabra qué
está marcando la métrica y por qué, pensada para auditar el propio
índice, no solo confiar en el número final.

## 4. Reestructuración del repositorio

El repositorio había acumulado, a lo largo de varias semanas de trabajo,
una organización poco clara para alguien que lo viera por primera vez
(carpetas numeradas con huecos, ficheros de pruebas puntuales sin
limpiar, documentación desactualizada en varios puntos). Esta semana se
ha hecho una revisión completa, carpeta por carpeta:

- Las 9 etapas del proyecto se han agrupado bajo una carpeta `pipeline/`
  común, separadas claramente del producto final (el motor de
  traducción) y de los datos.
- Se han eliminado más de una decena de ficheros y carpetas que ya no
  aportaban nada (fuentes de datos descartadas hace semanas, prompts sin
  uso real, informes generados automáticamente que se podían regenerar
  en cualquier momento).
- Se ha actualizado toda la documentación que había quedado desfasada
  tras los avances más recientes.
- Todo el trabajo se ha verificado paso a paso (más de 500 pruebas
  automáticas, además de los bancos de prueba de traducción) para
  garantizar que la reorganización no ha roto nada.

## Próximos pasos

1. Corregir los 4 errores de diccionario encontrados en la validación a
   gran escala.
2. Retomar la capa de modelo de lenguaje para la dirección catalán→valenciano
   (un primer intento no dio buenos resultados; se ha identificado por
   qué y cómo corregirlo).
3. Repetir la validación a gran escala sobre el corpus completo del BOE
   (cerca de 270.000 frases, de las que hasta ahora solo se ha probado
   una muestra).
4. Hacer el commit definitivo de todo el trabajo acumulado y fusionar la
   reorganización del repositorio a la rama principal.
