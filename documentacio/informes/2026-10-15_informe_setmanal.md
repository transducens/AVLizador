# Informe semanal — AVLizador (traductor dialectal valenciano↔catalán)

**Semana del 13 al 15 de octubre de 2026**

## 1. Novedades de la semana

- Se ha construido desde cero la dirección catalán→valenciano, que el
  proyecto no tenía hasta ahora (solo traducía valenciano→catalán). Parte
  de la misma base de datos lingüísticos que la dirección original.
  Resultado actual: **116 de 151 frases exactas del banco de pruebas
  (76,8%), BLEU 98,08**.
- Se ha completado y cerrado la reorganización del repositorio, en marcha
  desde hacía semanas: se ha fusionado a la rama principal y subido al
  repositorio de forma definitiva. El proyecto queda con una estructura
  de carpetas clara y mantenible, sin cambios pendientes de confirmar en
  este frente.
- Se ha creado una métrica propia nueva, el **Índice de Pureza Dialectal
  (IPD)**: dado un texto cualquiera, calcula qué porcentaje de sus
  palabras características son valencianas frente a catalanas. Se ha
  validado contra tres fuentes de datos de tamaño creciente: el banco de
  151 frases, un dataset público de 1.958 frases, y esta misma semana
  contra el **corpus completo del Boletín Oficial del Estado (267.962
  documentos reales)**, el conjunto de datos más grande disponible para
  el proyecto.
- Al validar el IPD contra el BOE completo, el primer resultado (0,81 de
  pureza en el lado valenciano) salía notablemente más bajo que en los
  otros dos bancos de prueba (0,90-0,93). Investigando el detalle se
  confirmó un problema real, aunque no en el traductor: dos palabras muy
  frecuentes ("qué" y "açò") resultan ser mal indicador de dialecto en
  textos institucionales de este tipo, aunque el traductor las sigue
  traduciendo bien cuando hace falta. Corregida la métrica (no el
  traductor, son dos cosas independientes), el resultado sobre el BOE
  completo sube a **0,92**, en línea con los otros dos bancos de prueba.
- Se han corregido dos errores reales más en el diccionario del
  traductor, encontrados en la misma revisión del BOE: una palabra que
  se traducía confundiendo un sustantivo con un adverbio distinto
  ("vesprada" con "tard"), y otra que cambiaba el género gramatical de
  la palabra sin ajustar el resto de la frase ("ensenyança" a
  "ensenyament"). Las dos ya están corregidas y verificadas sin ninguna
  regresión.
- Se ha retirado un módulo del motor (en las dos direcciones) que solo
  acertaba memorizando el texto exacto del banco de pruebas, sin
  funcionar con ninguna frase nueva — el propio equipo lo detectó al
  cuestionar si de verdad generalizaba. Esto hizo bajar el porcentaje de
  aciertos medido (de 120/123 sobre 151 a 115/116), pero refleja la
  capacidad real del motor en vez de una cifra inflada por memorización.

## 2. Tareas en las que hemos avanzado

- Auditoría completa de una guía normativa de referencia (fuente
  académica citada en el proyecto) para encontrar nuevas reglas
  dialectales que implementar: de 4 reglas candidatas evaluadas contra
  datos reales (el banco de pruebas y el dataset público de 1.958
  frases), **solo 1 resultó tener uso real suficiente para
  implementarse** — las otras 3 se midieron y se descartaron con
  evidencia, evitando introducir reglas que sonaban bien en teoría pero
  no se cumplían en la práctica.
- Exploración de una línea de trabajo nueva: construir traductores
  completos castellano↔valenciano y valenciano↔inglés, reutilizando este
  proyecto como base (aplicando el traductor dialectal sobre corpus
  catalán-X ya existentes, o usando datos nativos cuando los hay). Esta
  semana se han identificado y conseguido varios datasets públicos
  reales: tres fuentes de castellano-valenciano (más de 80.000 pares de
  frases combinados) y la primera fuente real de valenciano-inglés que
  tiene el proyecto. Se ha decidido que este desarrollo viva en un
  **repositorio nuevo y separado** del traductor dialectal actual, que
  lo reutilizará como herramienta de base.

## 3. Tareas pendientes

- Completar la clasificación manual del diccionario del traductor (en
  curso por un colaborador externo, el proveedor de datos) antes de ampliar varias
  reglas que dependen de esa clasificación.
- Investigar si la ambigüedad gramatical indicativo/subjuntivo (ya
  corregida en valenciano→catalán para un caso concreto) aparece también
  en más casos gramaticales, usando el corpus completo del BOE como
  evidencia — mismo criterio de no generalizar ninguna regla sin
  evidencia real.
- Repetir en el clúster de computación de la universidad la validación
  combinada motor + capa de IA tras los últimos ajustes del motor, para
  confirmar si el récord anterior (129 de 151, 85,4%) se mantiene con la
  base actual.
- Retomar la capa de IA para la dirección catalán→valenciano (un primer
  intento no dio buenos resultados; ya identificado por qué y cómo
  corregirlo para un segundo intento).
- Avanzar en el desarrollo del nuevo proyecto de traductores
  castellano-valenciano y valenciano-inglés cuando convenga priorizarlo.

## 4. Asuntos urgentes

- No hay incidencias bloqueantes esta semana.
