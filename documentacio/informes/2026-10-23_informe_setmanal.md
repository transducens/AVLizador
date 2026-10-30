# Informe semanal — AVLizador (traductor dialectal valenciano↔catalán)

**Semana del 19 al 23 de octubre de 2026**

## 1. Novedades de la semana

- **El trabajo se centra ya solo en la dirección catalán→valenciano**, que
  es la que se entregará a la Conselleria junto con el Índice de Pureza
  Dialectal (IPD), para equipos con pocos recursos y sin tarjeta gráfica.
  La dirección valenciano→catalán queda aparcada.
- **El traductor funciona ya solo con los diccionarios oficiales del
  proveedor de datos.** Se completó la integración de sus conjugaciones
  verbales (más de 43.000 formas) y se retiraron todos los ficheros y
  listas de palabras que el equipo había hecho a mano. Algunas de esas
  listas tapaban errores de datos en vez de corregirlos. Ahora cada
  decisión sale del propio diccionario o del análisis gramatical
  automático, y no hay palabras escritas a mano en el código.
- **Nuevos bancos de prueba a partir del BOE completo.** Se han construido
  dos conjuntos de pares catalán/valenciano reales del BOE: uno
  "estricto" (9.453 pares en los que solo cambian rasgos dialectales, para
  detectar errores) y uno "amplio" (para ver qué le falta al traductor).
  Desde esta semana son la referencia principal, junto con el banco de
  151 frases y el dataset público de 1.958 frases.
- **Resultados actuales de catalán→valenciano:**
  - BOE estricto: **8.857 de 9.453 frases idénticas a la oficial (93,7%)**.
  - Dataset público: **1.479 de 1.958 (75,5%)**, frente a 1.212 la semana
    pasada.
  - Banco de 151 frases: 146 de 154. No es comparable con semanas
    anteriores, porque esta semana se corrigieron sus referencias para que
    sigan la norma.
- **Las reglas de la guía de traducción se contrastaron con los textos
  oficiales (AVL y BOE).** De las reglas de la guía, solo tres se cumplen
  de verdad en el valenciano oficial ("per a" delante de infinitivo,
  "ací" en lugar de "aquí" y "on" sin "a"), y son las que se han aplicado.
  Las demás se midieron y se descartaron con datos.
- **Palabras ambiguas resueltas con un modelo de lenguaje pequeño.** Hay
  unas pocas palabras catalanas con dos traducciones posibles según el
  sentido: "cop" puede ser "colp" (golpe) o "vegada" (vez), y "gandula"
  puede ser "hamaca" o persona vaga. Se ha añadido una capa opcional que
  construye las dos frases posibles y deja que un modelo de lenguaje
  pequeño (FLOR, del proyecto AINA) elija la más natural. Este modelo no
  escribe nada: solo elige entre traducciones del diccionario. Funciona
  sin tarjeta gráfica y solo se activa en las frases con esas palabras.
  En el banco de prueba de estas palabras se pasa de **190 a 227 frases
  correctas de 253**, sin cambiar ninguna de las demás.
- **Un primer intento con modelos de IA conversacionales (LLM) no dio
  resultado** en esta dirección: los modelos que caben en un ordenador
  normal no conocían esas palabras, y el que sí las conocía tardaba unos
  12 segundos por respuesta. Por eso se cambió al método del punto
  anterior.
- El traductor es ahora **más del doble de rápido** (de unas 87 a unas
  250 frases por segundo en un solo núcleo) sin cambiar ninguna
  traducción.

## 2. Tareas en las que hemos avanzado

- **Errores de datos encontrados y corregidos en origen**, con el permiso
  correspondiente: una palabra mal escrita en el diccionario ("hamaces"
  por "hamaques") y dos identificadores repetidos o erróneos. El primero
  es instructivo: el modelo de lenguaje parecía no entender la palabra, y
  en realidad lo que fallaba era el dato. El modelo sirve así también para
  encontrar formas sospechosas del diccionario.
- **Documentación puesta al día**: la metodología completa del proyecto,
  los manuales del traductor y de cada parte describen ya la estructura y
  los resultados actuales.
- **Nuevo encargo: un banco de prueba revisado a mano**, con 200 frases
  del BOE y 200 de los textos de la AVL de todos los tipos (notas de
  prensa, acuerdos normativos, boletín, gramática, glosario…), elegidas
  para que contengan los rasgos dialectales que el traductor debe resolver
  y distintas del banco de 151 frases. Hecho esta semana:
  - el plan completo paso a paso;
  - el detector automático de los rasgos de cada frase;
  - una primera selección de 760 frases candidatas de la AVL.

## 3. Tareas pendientes

- Terminar el banco de prueba revisado a mano: seleccionar las candidatas
  del BOE (la extracción quedó a medias y hay que hacerla más rápida),
  elegir 250 candidatas de cada fuente y repartirlas en el equipo para
  revisarlas y corregirlas a mano.
- Guardar en el repositorio el trabajo de los últimos días, que todavía no
  está confirmado.
- Pasar al proveedor de datos los problemas encontrados que no podemos
  corregir nosotros:
  - una palabra que el diccionario aplica también cuando es un verbo
    ("afecta" → "carinya");
  - los numerales ordinales del BOE ("octava", "dèsset"), que el
    diccionario escribe de otra forma;
  - algunos topónimos que coinciden con palabras comunes ("les
    Garrigues").
- Preparar la entrega a la Conselleria: instalación sencilla y forma de
  uso desde la línea de órdenes o como servicio.

## 4. Asuntos urgentes

- No hay incidencias bloqueantes esta semana.
- Hay que confirmar con el equipo el criterio de reparto del banco de
  prueba manual (cuántas frases de cada tipo de rasgo) antes de empezar la
  revisión.
