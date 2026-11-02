# Informe semanal — AVLizador (traductor dialectal catalán→valenciano)

**Semana del 26 al 30 de octubre de 2026**

## 1. Novedades de la semana

- **El traductor y la métrica de grado dialectal ya se pueden instalar
  como un paquete.** Las dos herramientas que se entregarán a la
  Conselleria forman ahora un paquete de Python, `avlizador`, que se
  instala con una sola orden y se usa desde la línea de órdenes
  (`avlizador tradueix`, `avlizador gd`, `avlizador avalua`) o desde
  código. Funciona solo con CPU. Se ha comprobado en Windows y en el
  clúster Abaco (Linux): las traducciones son idénticas a las de antes en
  los 8 bancos de prueba (8.329 frases). El repositorio se ha ordenado: el
  diccionario tiene una sola ubicación, todos los bancos de prueba están
  en el repositorio y el resto del trabajo queda como registro.
- **Banco de prueba revisado a mano, terminado.** Tiene 458 frases: 246
  del BOE, revisadas por el equipo desde el texto original, y 212 de los
  textos de la AVL. Se ha elegido como **banco de evaluación** del
  proyecto. Hay también un banco solo con la parte del BOE y otro solo con
  la de la AVL.
- **El sistema final es el motor de reglas más el modelo de lenguaje
  FLOR-760M**, que decide en las palabras ambiguas ("cop" → *colp* o
  *vegada*, "nou" → *nou* o *anou*). Se compararon 9 modelos de lenguaje
  pequeños para ese papel y FLOR-760M fue el mejor y el más rápido.
- **Resultados en el banco de evaluación (458 frases):**
  - Sistema final: **227 frases idénticas a la referencia (49,6 %)**;
    motor solo: 214.
  - En las frases de la AVL: **195 de 212 (92,0 %)**.
  - En las del BOE: 32 de 246 (13,0 %). La cifra es baja porque la
    traducción oficial del BOE reformula mucho (pone en futuro lo que el
    catalán dice en presente, cambia sinónimos que no son dialectales…),
    no por fallos dialectales. Aun así, solo hay que corregir una de cada
    diez palabras.
- **Dos medidas nuevas de calidad**: el TER y el WER dicen qué parte de
  las palabras habría que editar para llegar a la referencia. En el
  banco de evaluación el sistema final se queda en un **5,6 %**.
- **Resultados en el resto de bancos** (sistema final): banco de 151
  frases, 146 de 154; banco de palabras ambiguas, 226 de 253; BOE
  estricto, 1.880 de 2.000 (94,0 %); dataset público, 1.544 de 1.958
  (78,9 %).
- **La métrica de grado dialectal se ha renombrado y ampliado.** El
  antiguo Índice de Pureza Dialectal (IPD) se llama ahora **Grau Dialectal
  (GD)**. Se han añadido dos índices complementarios: el **GDV** (cuánto
  de valenciano es un texto) y el **GDC** (cuánto de catalán), pensados
  también para evaluar la salida de un traductor. Se han medido en todos
  los corpus. En el banco de evaluación, el valenciano da un GD de 0,997 y
  el catalán, de 0,027, que es lo esperado.
- **Ha empezado la comparación con modelos de IA conversacionales
  generalistas.** La pregunta es si nuestro sistema mejora lo que ya
  existe. Se comparan 9 modelos (llama3.1, qwen2.5, qwen3, gemma3, gemma4,
  salamandra y mistral-nemo, de 7.000 a 14.000 millones de parámetros),
  usados tal cual, con la misma instrucción mínima y sin ayudas. Se
  ejecutan en Abaco usando como mucho 2 tarjetas gráficas a la vez, para
  no acaparar el clúster. En una prueba con 10 frases del BOE, llama3.1
  no acertó ninguna y dejó palabras en catalán ("realitzi", "aquests",
  "seva"). Los resultados completos llegarán la semana que viene.

## 2. Tareas en las que hemos avanzado

- **Diccionario**: se ha incorporado la nueva versión del léxico y de los
  verbos que entregó el compañero. Gracias a ella, la métrica deja de
  contar mal la palabra "després" y el traductor ya cambia "petit" por
  "xicotet" y usa "obtindre" y "mantindre".
- **Errores detectados en la métrica de grado dialectal**, documentados
  pero todavía sin corregir:
  - Hay formas verbales valencianas que se escriben igual que formas
    catalanas normales ("permet", "consideren"). Esto penaliza a los
    textos catalanes, y es la principal fuente de error que queda.
  - Algunos datos nuevos del diccionario hacen que "finalitat" cuente
    como catalán.
- **Comparación con Apertium descartada de momento.** Apertium no tiene
  un par catalán → valenciano. Se probó la vía castellano, pero el
  servicio público daba error en todas las peticiones.
- Documentación puesta al día: metodología, resultados de cada banco con
  todas las medidas, manuales del paquete y registro de las decisiones.

## 3. Tareas pendientes

- **Recoger los resultados de la comparación con los modelos de IA** en
  cuanto terminen en Abaco y presentarlos en una tabla junto con los de
  nuestro sistema.
- Analizar en detalle cómo decide el sistema en las palabras ambiguas:
  qué categoría gramatical da el analizador y qué elige el modelo de
  lenguaje en cada caso.
- Corregir un error del analizador gramatical: a principio de frase toma
  algunos verbos por nombres propios ("Necessito…") y entonces el
  traductor no los cambia.
- Pasar al compañero del diccionario los datos que convendría revisar:
  la pareja "finalitat"/"fi" y "naixement"/"naixença".
- Avisar al equipo de la nueva ubicación del diccionario. El correo con la
  nueva estructura ya está redactado.
- Preparar la documentación de decisiones y el paquete final de entrega.

## 4. Asuntos urgentes

- **Hay que decidir la licencia del repositorio** con el grupo. Hasta
  entonces no se publica ninguna. La propuesta es una licencia de software
  (Apache-2.0 o MIT) para el código y Creative Commons BY 4.0 para los
  datos y los bancos de prueba. Antes de decidir hay que confirmar que
  podemos licenciar el diccionario del proveedor y los textos del BOE y de
  la AVL.
