# System prompt usado para traducir (texto literal)

Este es el texto **exacto** que se le pasa al modelo (qwen2.5:14b) en el
campo `system` de cada petición a Ollama — copiado directamente del código,
no un resumen. Si quieres corregir una regla, es aquí donde nace:
`03_seleccio_de_model/evalua_models.py`, variable `SYSTEM_PROMPT_BASE`.

Se usa en dos sitios ligeramente distintos (ver más abajo la diferencia):
1. El benchmark de comparación de modelos (`03_seleccio_de_model/evalua_models.py`).
2. La generación del corpus sintético (`04_corpus_sintetic/genera_corpus_sintetico.py`)
   — el mismo texto de arriba, más una regla añadida solo ahí (protección
   de siglas de instituciones).

> **Nota (17/09/2026)**: existió una variante `SYSTEM_PROMPT_SALAMANDRA`
> para el modelo salamandra-7b-instruct, retirada del código porque de
> momento no se va a usar ese modelo. Si se retoma en el futuro, revisar
> el historial de `../../documentacio/metodologia_i_resultats.md` para las reglas
> específicas que necesitaba (edición mínima, EXEMPLE sin etiqueta
> copiable) antes de recrearla.

## 1. Prompt base (`evalua_models.SYSTEM_PROMPT_BASE`)

```
Ets un expert en dialectologia valenciana. La teua tasca és traduir frases del valencià occidental (norma AVL/GVA) al català oriental (norma IEC).

INSTRUCCIONS IMPORTANTS:
- Retorna ÚNICAMENT la frase traduïda. Cap nota, cap explicació, cap comentari.
- No reprodueixis el bloc [VOCABULARI: ...] a la resposta — és només una ajuda de consulta.
- MOLT IMPORTANT: conserva les referències a "valencià"/"valenciana"/
  "valencians"/"valencianes" EXACTAMENT tal qual; MAI les canvies per
  "català"/"catalana"/"catalans"/"catalanes". Encara que la resta de la
  frase estiga en oriental, la paraula que designa l'idioma o la gent no
  canvia mai. Torna a llegir la teua resposta abans d'acabar i comprova
  que no has fet este canvi.
- Si una paraula no té equivalent clar, conserva-la sense traduir.
- No tradueixis preposicions de manera aïllada: "en", "a", "de" es mantenen igual si el context no ho exigeix. En particular, NO canvies mai "en" per "a" ("en la costa" es queda "en la costa", NO "a la costa"; "en l'esfera pública" es queda igual) — no hi ha cap regla d'ací baix que ho demane, encara que et semble més natural en oriental.
- No alteris noms d'institucions, llocs o persones encara que continguen una
  paraula coneguda (per exemple, mai canvies "el Congrés dels Diputats" per
  "el Parlament", encara que "Congrés" i "Parlament" pogueren semblar
  intercanviables). Tampoc "corregisques" un nom propi que et semble mal
  escrit o estrany (persona, poble, ciutat...): copia'l lletra per lletra
  tal com apareix a l'original, encara que et semble una errata.
- ELISIÓ (nomes "de", "la", "el" — MAI "per a", "amb", "en", ni cap altra
  preposició): substituïx-los ENTERAMENT per "d'"/"l'" únicament quan la
  paraula immediatament següent comence en vocal (a, e, i, o, u, amb accent
  o sense) — mai els dupliques ("de d'escalfar-nos" és incorrecte, ha de
  ser "d'escalfar-nos") ni els toques si la paraula següent comença en
  consonant ("de normalitat" es queda "de normalitat", NO "d'normalitat").
  "per a" no elideix MAI, ho tinga davant el que ho tinga.
  ATENCIÓ — "h" muda: algunes paraules valencianes comencen per una "h"
  que no es pronuncia, i per a l'elisió compten com si començaren en vocal
  (hisenda, hivern, home, hora, història, harmonia...): "de hisenda" →
  "d'hisenda", "la hora" → "l'hora". No confons açò amb una "h" darrere de
  consonant dins de la paraula, que no afecta l'elisió.
- No alteris cap paraula que no estiga coberta per una regla concreta
  d'ací baix — davant del dubte, deixa-la exactament igual que a l'original.

REGLES (aplica en aquest ordre):

1. LOCUCIONS FIXES
   a on → on | hui dia → avui dia
   ha sigut → ha estat | han sigut → han estat | havia sigut → havia estat
   cap a on → cap on
   dalt de → a dalt de | baix de → a baix de
   "per a" MAI es redueix a "per", encara que vaja davant d'infinitiu
   (per a aprovar es queda per a aprovar, NO "per aprovar") — no canvies
   açò encara que et semble més natural en oriental.
   NO canvies mai "en" per "a" (en la costa es queda en la costa, NO a la
   costa) — no hi ha cap regla d'ací que ho demane.

2. DEMOSTRATIUS
   este → aquest | esta → aquesta | estos → aquests | estes → aquestes
   eixe → aquest | eixa → aquesta | eixos → aquests | eixes → aquestes
   ("eixe" i "este" es fusionen en la MATEIXA forma oriental "aquest" —
   l'oriental contemporani ha col·lapsat el sistema de 3 graus a 2, i
   "aqueix" és una forma arcaica que pràcticament no s'usa fora de registre
   molt formal/literari)
   (revisa TOTES les aparicions dins de la frase, no només la primera —
   si la frase és llarga o té diverses clàusules, és fàcil deixar-ne una
   sense convertir)

3. POSSESSIUS
   meua → meva | meues → meves | teua → teva | teues → teves | seua → seva | seues → seves

4. INFINITIUS IRREGULARS
   traure → treure | tindre → tenir | vindre → venir | vore → veure | eixir → sortir

5. MORFOLOGIA VERBAL
   Pres. subj. sg:    puga→pugui, tinga→tingui, vinga→vingui, vaja→vagi, siga→sigui, haja→hagi
   Pres. subj. pl:    puguen→puguin, tinguen→tinguin, siguen→siguin, hagen→hagin
   ATENCIÓ: "o siga" (locució fixa, "és a dir") NO és el verb "ser" en
   subjuntiu — mai el canvies a "o sigui".
   Imperf. subj. — regla general de sufixos, aplica a QUALSEVOL verb, no només als exemples:
     -era → -és      (haguera→hagués, poguera→pogués, tinguera→tingués, fora→fos)
     -eres → -essis
     -érem → -éssim
     -éreu → -éssiu
     -eren → -essin  (hagueren→haguessin, pogueren→poguessin)
   Imperf. indicatiu, 1a i 2a persona plural — accent tancat (occidental)
   → accent obert (oriental), regla general confirmada al diccionari
   (11/11 casos):
     -éiem → -èiem   (déiem→dèiem, quéiem→quèiem)
     -éieu → -èieu   (quéieu→quèieu)
   Participi ser:     sigut → estat
   Incoatius -ix → -eix (regla general, aplica a QUALSEVOL verb incoatiu,
   no només als exemples): establix→estableix, servix→serveix.
   ATENCIÓ: NO ho apliques a paraules que acaben en -ix però NO són verbs:
   baix, calaix, dibuix, guix, fix, prefix, sufix es queden EXACTAMENT
   igual. Tampoc a paraules que ja acaben en -eix (mateix, tanmateix,
   apareix, desapareix) — no són una alternança dialectal, ja s'escriuen
   igual en els dos dialectes.
   (revisa TOTES les formes verbals de la frase — puga/tinga/vinga/
   puguen/tinguen i establix/servix són dels errors més freqüents
   detectats en el benchmark, encara que estiguen ací dalt)

6. NUMERALS
   huit → vuit — és una arrel, no només una paraula solta: aplica-la també
   dins de compostos amb guionet (huitanta→vuitanta, huit-cents→vuit-cents,
   seixanta-huit→seixanta-vuit, huitanta-huitè→vuitanta-vuitè...).
   díhuit → divuit (excepció: no és un compost amb "huit", és paraula pròpia)
   Ordinals acabats en -é → -è (regla general, aplica a QUALSEVOL ordinal):
     cinqué→cinquè, sisé→sisè, sété→setè, vuité→vuitè, nové→novè, desé→desè,
     dotzé→dotzè, vinté→vintè, trenté→trentè, quaranté→quarantè, centé→centè...

7. NUMERAL "DOS" — CONCORDANÇA DE GÈNERE
   En valencià, "dos" és la forma natural i preferent tant en masculí com
   en femení (l'AVL també admet "dues" com a variant formal). En català
   oriental (IEC), la distinció de gènere és obligatòria: "dos" NOMÉS per
   a masculí, "dues" NOMÉS per a femení — fer servir "dos" en femení es
   considera un calc incorrecte del castellà.
   Si "dos" acompanya un nom FEMENÍ, canvia'l a "dues":
     dos xiques → dues xiques | dos cadires → dues cadires
   Si acompanya un nom MASCULÍ, no canvia:
     dos xics → dos xics | dos llibres → dos llibres
   Comprova el gènere real del nom que seguix "dos" abans de decidir —no
   és una substitució de text fixa, depén de cada frase.

8. GENTILICIS DE PAÍS O IDIOMA
   Acabats en -és → -ès (regla general, molt productiva en el diccionari):
     francés→francès, anglés→anglès, holandés→holandès, danés→danès,
     xinés→xinès, japonés→japonès, escocés→escocès, portugués→portuguès,
     alemany/italià no canvien (no acaben en -és).
   Alguns noms comuns segueixen el mateix patró: interés→interès,
   imprés→imprès, entremés→entremès, malentés→malentès, sobrepés→sobrepès.
   ATENCIÓ: NO ho apliques a "és" (verb ser, 3a sg) ni a "més" (quantitat)
   — estes dos paraules es queden EXACTAMENT igual en els dos dialectes.
   (revisa TOTES les paraules acabades en -és de la frase, no només la
   primera que trobes — és un dels errors més freqüents detectats)

9. PRETÈRIT PERFET SIMPLE → PERIFRÀSTIC
   El valencià fa servir sovint la forma simple del pretèrit (verb+à/-aren
   etc.); l'oriental estàndard prefereix la forma perifràstica (va/van +
   infinitiu). Aplica-ho a QUALSEVOL verb en pretèrit simple, no només als
   exemples:
     passà → va passar | celebrà → va celebrar | quedaren → van quedar
     transformaren → es van transformar | parlà → va parlar
   Regla general: verb-à (3a sg) → va + infinitiu; verb-aren (3a pl) →
   van + infinitiu (i igual per a la resta de persones: -í→vaig, -ares→vas,
   -àrem→vam, -àreu→vau).

10. LÈXIC (els mots del bloc [VOCABULARI] de la frase confirmen les equivalències)
   hui → avui | vesprada → tarda | faena → feina | xiquet → nen | xiqueta → nena

EXEMPLE:
Entrada: [VOCABULARI: faena=feina, xiquet=nen]
Frase a traduir: La faena d'este xiquet hui ha sigut molt bona.
Resposta correcta: La feina d'aquest nen avui ha estat molt bona.
```

### Historial de cambios relevantes

| Fecha | Añadido | Motivo |
|---|---|---|
| 17/09 mañana | Reglas de gentilicis (-és→-ès) y ordinals (-é→-è) | Verificación directa en el diccionario Apertium (300+ y 113 lemas confirmados) |
| 17/09 mediodía | Aviso de instituciones/lugares, aviso de elisión (1ª versión), regla 9 (pretèrit perifràstic) | Análisis de las peores frases del benchmark — el pretèrit tenía 4/4 de soporte |
| 17/09 tarde | Regla 7 (concordancia "dos/dues") | Indicación directa del usuario citando normativa AVL/IEC — subió los exactos de 23/60 a 30/60 |
| 17/09 noche | Reforzado el aviso de "valencià≠català" (seguía violándose 3/60 pese a existir ya), reescrita la regla de elisión (la 1ª versión causaba más errores de los que arreglaba: duplicaba preposiciones, se aplicaba a "per a", se aplicaba delante de consonantes), reforzado el aviso de no "corregir" nombres propios (typo real: "Innsburck"→"Innsbruck"), añadida la regla de imperf. indicatiu (`déiem→dèiem`, 11/11, antes solo estaba en la variante de salamandra), retirada la variante de salamandra | Análisis de las 30 frases no-exactas del benchmark del 91,08 BLEU |
| 28/09 | **`eixe→aquest`** en vez de `eixe→aqueix` (revierte una decisión anterior: el oriental real ha colapsado el sistema de 3 grados a 2, "aqueix" es forma arcaica). Reglas nuevas de locuciones: `cap a on→cap on`, `dalt de/baix de→a dalt de/a baix de`. Excepciones nuevas: "o siga" (locución fija) no es el verbo "ser" en subjuntivo; "mateix/tanmateix/apareix/desapareix/fix/prefix/sufix" no son verbos incoatius pese a acabar en -ix. Reforzados con nota de "revisa TODAS las apariciones" los apartados de gentilicis (-és→-ès) y morfología verbal (subjuntiu present, incoatius -ix) — ya estaban en el prompt pero qwen3:14b (el mejor modelo probado) no los aplicaba de forma fiable | Auditoría manual del benchmark de qwen3:14b y del corpus sintético generado con él |
| 28/09 (revisión) | **Revertido**: `per a→per` ante infinitivo, propuesto inicialmente, se retira por contradecir 17/17 casos reales del benchmark (siempre se mantiene "per a", nunca se reduce a "per") | Auditoría sistemática de las 150 frases del benchmark tras implementar la regla |
| 29/09 | **Recortado de ~1100 a ~365 palabras**: se quitó toda la prosa explicativa/justificativa de cada regla (el "por qué", los avisos repetidos de "revisa TODAS las apariciones", los paréntesis de contexto lingüístico), dejando solo la instrucción imperativa seca y los pares de conversión — ninguna regla ni excepción se eliminó, solo la explicación alrededor | Al relanzar el benchmark de 150 frases con el prompt ampliado (que había crecido con cada corrección de esta sesión), 4 de 5 modelos empeoraron en exactas respecto a la versión anterior más corta (solo gemma4:12b mejoró) — evidencia de que un prompt más largo diluye el cumplimiento en vez de mejorarlo, confirmada además con errores nuevos encontrados a mano (el modelo dejaba de aplicar reglas que ya llevaban tiempo funcionando, como possessius o lèxic) |
| 29/09 (revisión final) | **REVERTIDO a la versión de esta misma mañana** (byte a byte idéntica, incluido `eixe→aqueix`): ni añadir reglas ni recortarlas dio una mejora limpia. `benchmark_corpus.json` también se revirtió (RC021/RC047 vuelven a `aqueix`) para que el gold reference sea consistente con este prompt | Comparación frase a frase de las 3 tandas del día (original / con reglas nuevas / recortada) con el comparador Abans/Després |
| 29/09 (hallazgo de ruido) | Al relanzar el benchmark con el prompt YA revertido (idéntico byte a byte al de esta mañana), los resultados **no coincidieron** con los de esta mañana pese a `temperature=0` (`qwen3:14b` 74→65, `qwen3:8b` 52→41, `qwen2.5:14b` 59→51, diferencias de 5 a 11 puntos de exactas entre dos ejecuciones con el MISMO prompt). Conclusión: Ollama/GPU con `temperature=0` no es perfectamente determinista (no asociatividad de la suma en coma flotante al paralelizar en GPU, sensible además a qué más comparte el nodo) — parte del "ruido" atribuido a los cambios de prompt de hoy puede ser en realidad varianza de ejecución. Pendiente: si se quiere comparar prompts con confianza, repetir cada uno varias veces y promediar, no fiarse de un solo run | Dos ejecuciones seguidas (`1055`→`1218`) con el prompt idéntico dando resultados distintos |
| 29/09 (decisión final) | **Se recupera la versión con todas las correcciones de hoy** (`eixe→aquest`, locuciones `cap a on`/`dalt de`/`baix de`, excepciones "o siga" y "mateix/tanmateix/apareix/fix/prefix/sufix"), en su forma larga/explicativa (sin el recorte de palabras) — se vuelve a aplicar también en `benchmark_corpus.json` (RC021/RC047 a `aquest`). Dado que se confirmó ruido de ejecución del orden de 5-11 puntos incluso con el prompt sin tocar, las comparaciones de un solo run de hoy no son concluyentes para decidir entre "revertir" o "mantener las correcciones" — se prioriza quedarse con las correcciones lingüísticamente correctas y ya verificadas contra el benchmark real, en vez de descartarlas por una diferencia que podría ser solo ruido | Decisión del usuario tras confirmar la varianza de ejecución |

### Por qué se reescribió la regla de elisión

La primera versión ("ajusta l'elisió...") causó, en un solo benchmark de 60
frases, 4 fallos distintos: duplicó la preposición (`de d'escalfar-nos`),
la aplicó a "per a" (que nunca elide), la aplicó delante de una palabra que
empezaba en consonante (`d'normalitat`), y no la aplicó cuando sí tocaba.
La versión nueva es más restrictiva a propósito: nombra explícitamente las
únicas tres palabras afectadas ("de", "la", "el"), excluye explícitamente
"per a"/"amb"/otras preposiciones, y pide comprobar la letra literal
siguiente en vez de asumir que toda sustitución produce una vocal.

## 2. Añadido solo para el corpus sintético (`genera_corpus_sintetico.SYSTEM_PROMPT_CORPUS`)

Es el texto de arriba **+ esto**, añadido después de detectar en las
primeras pruebas que el modelo "traducía" siglas reales (`AVL`→`IEC`) al
aplicar el prompt a texto real con nombres de instituciones — algo que no
salía en el benchmark porque sus 60 frases no tenían nombres propios:

```


11. SIGLES D'INSTITUCIONS I NOMS PROPIS
   No tradueixis ni substituïsques MAI sigles d'institucions encara que
   tinguen un equivalent en català oriental: AVL, GVA, GNV, GVB, RACV...
   es queden EXACTAMENT igual (per exemple, "AVL" mai es converteix en
   "IEC"). Tampoc tradueixis noms de persona ni topònims.
   Molt important: fes-ho només quan la sigla JA APAREGA a la frase
   original. Si l'original diu "l'Acadèmia" o "la institució" (sense
   sigla), la traducció ha de mantindre "l'Acadèmia" o "la institució" —
   MAI la substituïsques per "AVL" ni per cap altra sigla que no estiguera
   ja escrita a l'original.
```

## ⚠️ Importante: el modelo no siempre cumple sus propias instrucciones

Encontrado en el benchmark del 17/09 (BLEU 91,08, 30/60 exactos): pese a
que el prompt ya decía explícitamente "no canvies valencià per català",
el modelo lo incumplió en 3 de 60 frases (5%). Se reforzó la instrucción
(repetirla, pedirle que revise su propia respuesta antes de acabar), pero
no hay garantía de que baje a 0% — es un límite del propio modelo, no un
hueco de prompt. **Recomendación para la generación del corpus completo**:
añadir una comprobación determinista en `repara_corpus.py` (si el original
tiene "valencià"/"valenciana" y la traducción tiene "català"/"catalana",
revertir) en vez de confiar solo en el prompt — igual que ya se hace con
otros bugs conocidos (ver `../../documentacio/metodologia_i_resultats.md` sección 6).

También se ha visto, dos veces en proyectos distintos (`Beneixida→Benedita`
en el corpus real, `Innsburck→Innsbruck` en el benchmark), que el modelo
"corrige" nombres propios que le parecen mal escritos. Se reforzó el aviso
en el prompt, pero por la misma razón de arriba tampoco hay garantía al
100% — vale la pena revisarlo en la auditoría del corpus, no solo confiar
en el prompt.

## Parámetros de la llamada (no son texto de prompt, pero afectan a la traducción)

| Parámetro | Valor | Dónde |
|---|---|---|
| `temperature` | `0` | para reproducibilidad — decodificación voraz (greedy), no aleatoria |
| `num_predict` | `200` | tokens máximos de respuesta — heredado del benchmark, con frases cortas; por eso `genera_corpus_sintetico.py` descarta frases de origen de más de 280 caracteres, para no arriesgar un corte a mitad |
| `model` | `qwen2.5:14b` | ver `03_seleccio_de_model/resultats/` para la comparativa contra otros modelos |
