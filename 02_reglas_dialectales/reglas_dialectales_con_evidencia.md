# Del valencià occidental al català oriental: guia de diferències dialectals

Document de referència amb les diferències sistemàtiques entre el valencià
occidental (norma AVL/GVA) i el català oriental (norma IEC) que s'utilitzen
per a la conversió automàtica d'un dialecte a l'altre. Pensat per a ser
revisat per algú amb coneixement de les dos normes, per a confirmar que
cada regla està ben formulada.

---

## 0. Marc general

El valencià i el català no són dues llengües, són **dos estàndards d'una
mateixa llengua**, cadascun basat en una autoritat normativa diferent:

- **Valencià occidental** — norma de l'AVL (Acadèmia Valenciana de la
  Llengua) i la GVA (Generalitat Valenciana).
- **Català oriental** — norma de l'IEC (Institut d'Estudis Catalans).

La immensa majoria del vocabulari, la sintaxi i l'ortografia són
**idèntics**. Les diferències es concentren en un nombre relativament
xicotet de patrons sistemàtics (morfologia verbal, demostratius,
possessius...) més un conjunt de paraules amb forma pròpia a cada banda
(lèxic diferencial). Este document cobrix totes dos coses per separat.

**Advertència de mètode**: cap d'estes regles és absoluta al 100%. Són les
formes *dominants* en cada norma; en tots dos estàndards hi ha variació
interna, registres i excepcions dialectals menors dins del mateix bloc
occidental o oriental.

---

## 1. Demostratius

| Occidental | Oriental |
|---|---|
| este / esta / estos / estes | aquest / aquesta / aquests / aquestes |
| eixe / eixa / eixos / eixes | aqueix / aqueixa / aqueixos / aqueixes |

L'AVL també admet *aquest/aquesta* com a forma normativa pròpia — per això
esta alternança és coneixement general de la variació dialectal, no una
equivalència mecànica derivada directament d'un diccionari.

## 2. Possessius

| Occidental | Oriental |
|---|---|
| meua / meues | meva / meves |
| teua / teues | teva / teves |
| seua / seues | seva / seves |

Només afecta les formes **febles femenines** (meua, teua, seua i plurals).
Les formes masculines (meu, teu, seu) i les tòniques (mia, tua, sua) no
canvien.

## 3. Pronoms personals

| Occidental | Oriental |
|---|---|
| vos | us |

## 4. Infinitius irregulars

| Occidental | Oriental |
|---|---|
| traure | treure |
| tindre | tenir |
| vindre | venir |
| vore | veure |
| eixir | sortir |
| valdre | valer |

Estos verbs deriven en formes conjugades pel mateix patró (p. ex. *tinga*
ve de *tindre*) — veure secció 5.

## 5. Morfologia verbal

### 5.1 Present d'indicatiu (1a persona singular, verbs de la 1a conjugació)

| Occidental | Oriental |
|---|---|
| parle | parlo |
| mire | miro |
| compre | compro |
| treballe | treballo |
| done | dono |

Patró general, confirmat al diccionari Apertium per a tots els verbs
regulars acabats en *-ar* (paradigma `abander/ar__vblex` i equivalents): la
1a persona singular del present d'indicatiu acaba en **-e** en occidental
i en **-o** en oriental. Només afecta la 1a conjugació — els verbs de la
2a i 3a (*tindre/tenir*, *venir*...) segueixen patrons propis, ja coberts
per altres regles d'este document (veure 4 i 5.6).

Variant ortogràfica del mateix patró: als verbs acabats en *-gar*/*-car*
cal mantindre el so dur amb una *u*, per això l'occidental fa *-gue*/*-que*
en lloc de *-ge*/*-ce* (*jugar* → *jugue*, no *"juge"*), mentre l'oriental
manté *-go*/*-co* (*jugo*). No és una excepció al patró, és ortografia.

### 5.2 Present de subjuntiu

| Persona | Occidental | Oriental |
|---|---|---|
| jo | puga, tinga, vinga, vaja, siga, haja | pugui, tingui, vingui, vagi, sigui, hagi |
| ells/elles | puguen, tinguen, vinguen, vagen, siguen, hagen | puguin, tinguin, vinguin, vagin, siguin, hagin |

### 5.3 Imperfet de subjuntiu

La diferència és sistemàtica en la terminació personal, igual per als
quatre verbs de la taula (haver, poder, tindre, ser): l'occidental fa
servir la terminació **-era** (jo/ell), **-eres** (tu), **-érem**
(nosaltres), **-éreu** (vosaltres), **-eren** (ells); l'oriental fa servir
**-és**, **-essis**, **-éssim**, **-éssiu**, **-essin** en eixe mateix
orde. La resta de la paraula (l'arrel: hagu-, pogu-, tingu-, fo-) no canvia.

| Persona | Occidental | Oriental |
|---|---|---|
| jo / ell / ella | haguera, poguera, tinguera, fora | hagués, pogués, tingués, fos |
| tu | hagueres, pogueres, tingueres, fores | haguessis, poguessis, tinguessis, fossis |
| nosaltres | haguérem, poguérem, tinguérem, fórem | haguéssim, poguéssim, tinguéssim, fóssim |
| vosaltres | haguéreu, poguéreu, tinguéreu, fóreu | haguéssiu, poguéssiu, tinguéssiu, fóssiu |
| ells / elles | hagueren, pogueren, tingueren, foren | haguessin, poguessin, tinguessin, fossin |

**Nota important sobre "fora"**: esta paraula és homògrafa amb l'adverbi
"fora" (=fora de, a l'exterior), idèntic en els dos dialectes (p. ex.
*"queden fora de l'àmbit..."*). Només correspon a la forma oriental
*fos/fossin* quan és realment el verb "ser" en subjuntiu imperfet (com en
*"si fora possible"*, equivalent oriental *"si fos possible"*). Qualsevol
aplicació mecànica d'esta regla ha de tindre en compte el context per a no
confondre els dos usos.

### 5.4 Imperfet d'indicatiu (1a i 2a persona plural)

| Occidental | Oriental |
|---|---|
| déiem | dèiem |
| quéiem | quèiem |
| quéieu | quèieu |

Patró general confirmat al diccionari Apertium amb **11/11 (100%)** de
cobertura: l'accent tancat (é) de l'occidental correspon a l'accent obert
(è) de l'oriental en estes dues persones de l'imperfet d'indicatiu.

### 5.5 Participi del verb "ser"

| Occidental | Oriental |
|---|---|
| sigut | estat |

### 5.6 Verbs incoatius (-ix / -eix)

| Occidental | Oriental |
|---|---|
| establix | estableix |
| servix | serveix |

Patró general: la 3a persona del present d'indicatiu dels verbs incoatius
acaba en *-ix* en occidental i en *-eix* en oriental.

## 6. Numerals i altres patrons d'accent -é/-è

El patró central és **huit → vuit**: l'occidental manté la h- i l'oriental
la substitueix per v-. No és una paraula aïllada, és una arrel que apareix
dins de qualsevol numeral que la continga, tant si "huit" hi és sol com si
forma part d'un compost amb guionet (les desenes, els centenars, els
ordinals...):

| Occidental | Oriental |
|---|---|
| huit | vuit |
| huitanta | vuitanta |
| huitantè | vuitantè |
| huit-cents / huit-centes | vuit-cents / vuit-centes |
| huit-centè | vuit-centè |
| huitcentista | vuitcentista |
| díhuit | divuit |
| cinquanta-huit, seixanta-huit, setanta-huit, huitanta-huit, noranta-huit... | cinquanta-vuit, seixanta-vuit, setanta-vuit, vuitanta-vuit, noranta-vuit... |
| huitanta-u, huitanta-dos, huitanta-tres... huitanta-cinquè, huitanta-sisè... | vuitanta-u, vuitanta-dos, vuitanta-tres... vuitanta-cinquè, vuitanta-sisè... |

`díhuit` (18) és l'única excepció que **no** es deriva d'esta arrel: és una
paraula pròpia, no un compost amb guionet, així que cal una entrada a part
en lloc de dependre del patró huit→vuit.

### 6.1 Ordinals (-é → -è)

Independentment de l'arrel huit/vuit, **tots** els numerals ordinals
segueixen un segon patró, també general: acaben en *-é* en occidental i en
*-è* en oriental. Confirmat al diccionari Apertium amb el paradigma
`cinqu/è__adj`, que genera aquest patró per a 113 lemes (tots els ordinals
simples i compostos, del 5é al 1000é):

| Occidental | Oriental |
|---|---|
| cinqué, sisé, seté, vuité, nové | cinquè, sisè, setè, vuitè, novè |
| desé, dotzé, tretzé, catorzé, quinzé | desè, dotzè, tretzè, catorzè, quinzè |
| vinté, trenté, quaranté, cinquanté... | vintè, trentè, quarantè, cinquantè... |
| vint-i-uné, trenta-dosé... (compostos) | vint-i-unè, trenta-dosè... (compostos) |

### 6.2 Gentilicis de país o idioma (-és → -ès)

Un tercer patró general, independent dels numerals però amb la mateixa
mecànica d'accent: els adjectius/noms de nacionalitat o idioma acabats en
*-és* en occidental passen a *-ès* en oriental. És un dels patrons més
productius de tot el diccionari Apertium: confirmat amb més de 300 lemes
(paradigmes `afgan/ès__adj` i `angl/ès__n`).

| Occidental | Oriental |
|---|---|
| francés, anglés, holandés, danés | francès, anglès, holandès, danès |
| xinés, japonés, escocés, portugués | xinès, japonès, escocès, portuguès |

El mateix patró s'aplica també a una vintena de noms comuns que no són
gentilicis: `interés→interès`, `imprés→imprès`, `entremés→entremès`,
`malentés→malentès`, `sobrepés→sobrepès`, `desinterés→desinterès`,
`contrapés→contrapès`.

**Excepció important**: `és` (el verb ser, 3a persona singular) i `més`
(quantitat) **no** canvien mai — es queden exactament igual en els dos
dialectes. No formen part d'este patró perquè no són gentilicis ni noms:
són paraules gramaticals curtes que casualment acaben en la mateixa
seqüència de lletres.

### 6.3 Numeral "dos" — concordança de gènere

A diferència dels patrons anteriors, este no és un canvi de forma d'una
paraula, sinó una diferència en **quan s'aplica** la concordança de gènere.
En valencià, "dos" és la forma natural i preferent tant en masculí com en
femení; l'AVL admet "dues" com a variant, però formal/literària, no com la
forma estàndard esperada. En canvi, per a l'IEC (norma del català oriental)
la distinció de gènere és **obligatòria**: "dos" només per a masculí,
"dues" només per a femení — fer servir "dos" en femení es considera un
calc del castellà.

| Gènere | Occidental | Oriental |
|---|---|---|
| Masculí | dos xics, dos llibres | dos xics, dos llibres (sense canvi) |
| Femení | dos xiques, dos cadires | dues xiques, dues cadires |

**Advertència d'aplicació**: a diferència de la resta de regles d'esta
secció, esta no es pot aplicar com una simple substitució de text — cal
identificar el gènere real del nom que acompanya "dos" en cada frase
concreta abans de decidir si canvia o no.

## 7. Adverbis, locucions i temps

| Occidental | Oriental |
|---|---|
| a on | on |
| hui | avui |
| hui dia | avui dia |
| vesprada / de vesprada | tarda / a la tarda |
| ha sigut / han sigut / havia sigut | ha estat / han estat / havia estat |

## 8. Formes morfològiques addicionals

Esta secció tenia una taula de "candidats a confirmar" amb fiabilitats
baixes (p. ex. 4/10 per a -és→-ès). Eixa xifra venia d'una mostra reduïda;
en tornar a comprovar-ho directament contra els paradigmes complets del
diccionari Apertium (`apertium-cat.cat.dix`), dos dels quatre patrons
resulten estar molt més confirmats del que semblava, i ja s'han promogut a
regla general (secció 6.1 i 6.2 d'este mateix document). Els altres dos es
queden ací:

| Categoria | Occidental | Oriental | Fiabilitat* |
|---|---|---|---|
| possessiu tònic fem. | la meua (tònic) | la meva | 3/3 — ja cobert per la regla 3 (possessius), no cal cap entrada a part |

*Fiabilitat = quants casos del diccionari segueixen eixe patró, del total
de casos amb eixa combinació gramatical.

- **Pronom tònic de tractament** (`vosté/vostés → vostè/vostès`): confirmat
  2/2 al diccionari — no és un patró de sufix reutilitzable (és un parell
  de paraules concretes), així que s'ha afegit directament a
  `lexico_fiable.json` en lloc de convertir-se en regla. Vore secció 9.
- **Ordinals** (`nové → novè`): no és un cas aïllat amb fiabilitat 3/4 com
  deia abans — és el mateix patró general que TOTS els ordinals
  (`cinqué→cinquè`, `sisé→sisè`... 113 lemes confirmats al diccionari).
  Vore secció 6.1.
- **Adjectius/substantius acabats en -és** (`interés→interès`,
  `francés→francès`): tampoc és un patró dèbil — és el mateix que el dels
  gentilicis de país/idioma (`anglés→anglès`, `holandés→holandès`..., més
  de 300 lemes confirmats al diccionari), més una vintena de noms comuns
  (`interés`, `imprés`, `entremés`...). Vore secció 6.2. L'única cura:
  "és" (el verb ser) i "més" (quantitat) es queden EXACTAMENT igual en
  els dos dialectes — no acaben en -és per este motiu gramatical, són
  paraules curtes independents, no formes d'eixe patró.

## 9. Lèxic diferencial

Base léxica: las 368 formas que el diccionario Apertium marca explícitamente como valencianas (`v="val_gva"`), recogidas en [`lexico/apertium_368_val_cat.json`](../lexico/apertium_368_val_cat.json) — no la lista curada más amplia de ~1.600 palabras. De esas 368, 296 también son válidas en el valenciano general/unificado (`val_uni`) — no representan una diferencia dialectal que haya que convertir. Las 72 restantes son **exclusivamente occidentales**: de esas, estas son las que tienen pareja catalana confirmada dentro del propio diccionario Apertium (ninguna se ha inventado — o coincide con la lista ya validada, o su forma oriental aparece explícitamente en el mismo diccionario).

> **Nota de estado**: esta sección documenta de dónde sale ese subconjunto
> concreto (368 formas de Apertium), pero **no es el listado completo de
> parejas léxicas que cambian** — se está elaborando aparte un listado más
> amplio y exhaustivo. Hasta que esté listo, tómate esta tabla como
> referencia de origen/procedencia, no como la fuente activa o definitiva
> del léxico diferencial.

### 9.1 Parejas confirmadas (36 formas base)

De las 68 parejas que Apertium confirma, los numerales compuestos con
guionet (`cinquanta-huit`, `huitanta-cinc`, `noranta-huitè`...) se han
colapsado en sus dos formas base, `huit` y `huitanta` (ver la nota al final
de esta tabla y la sección 6) — de ahí que la tabla tenga menos filas que
parejas confirmadas.

| Occidental | Oriental |
|---|---|
| huit | vuit |
| aparéixer | aparèixer |
| atés | atès |
| comité | comitè |
| comités | comitès |
| comparéixer | comparèixer |
| convéncer | convèncer |
| conéixer | conèixer |
| cércol | cèrcol |
| desaparéixer | desaparèixer |
| desconéixer | desconèixer |
| dènou | dinou |
| díhuit | divuit |
| desentés | desentès |
| fins hui | fins avui |
| hui | avui |
| hui dia | avui dia |
| hui en dia | avui dia |
| huitanta | vuitanta |
| huitantè | vuitantè |
| huit-centè | vuit-centè |
| huitcentista | vuitcentista |
| manganés | manganès |
| patués | patuès |
| paréixer | parèixer |
| pésol | pèsol |
| reaparéixer | reaparèixer |
| reconéixer | reconèixer |
| ségol | sègol |
| sémola | sèmola |
| terratrémol | terratrèmol |
| trévol | trèvol |
| térbol | tèrbol |
| véncer | vèncer |
| vosté | vostè |
| vostés | vostès |

Els numerals compostos amb guionet (`cinquanta-huit`, `huitanta-cinc`,
`huitanta-huitè`, `noranta-huit`, `vint-i-huit`...) no tenen fila pròpia:
n'hi ha prou amb `huit`/`huitanta` soles, perquè el mecanisme del glossari
dinàmic (`evalua_models.py`) parteix la frase en paraules per guionet, així
que "huit" o "huitanta" ja es detecten com a paraula solta dins d'eixos
compostos. Vegeu la secció 6 per a la llista completa de numerals afectats.

### 9.2 Pendientes de determinar (3)

Palabras exclusivamente occidentales en Apertium sin una forma oriental confirmada en ninguna de las fuentes disponibles. No se inventa una traducción — quedan abiertas para revisión con una fuente externa.

| Occidental | Categoría |
|---|---|
| dèsset | numeral |
| buscar | verbo |
| recollir | verbo |

## 10. Noms propis i entitats

Els noms de persona, els topònims (noms de lloc) i les sigles
d'institucions **no es tradueixen mai**, encara que continguen una paraula
que coincidisca amb una entrada del lèxic diferencial (per exemple, un
topònim que continga la paraula "real" no s'ha de convertir en "reial"; un
nom de persona no es tradueix encara que coincidisca amb una paraula
comuna d'una altra categoria semàntica). Este principi és independent de
qualsevol de les regles anteriors i té prioritat sobre elles.

## 11. Sintaxi

Diferències d'estructura de la frase, no de paraules soltes — detectades
comparant frases completes (benchmark occidental/oriental), no comparant
paraules aïllades del diccionari. Per això no tenen una xifra de "cobertura
al diccionari" com la resta d'este document, sinó quants casos reals se n'ha
observat.

### 11.1 Pretèrit perfet simple → perifràstic

El valencià fa servir sovint la forma simple del pretèrit (*passà*,
*celebrà*, *quedaren*, *transformaren*); l'oriental estàndard prefereix la
forma perifràstica (*va passar*, *va celebrar*, *van quedar*, *es van
transformar*).

| Occidental (simple) | Oriental (perifràstic) |
|---|---|
| -à (3a sg): *passà* | va + infinitiu: *va passar* |
| -aren (3a pl): *transformaren* | van + infinitiu: *van transformar* |
| -í (1a sg) | vaig + infinitiu |
| -ares (2a sg) | vas + infinitiu |
| -àrem (1a pl) | vam + infinitiu |
| -àreu (2a pl) | vau + infinitiu |

**Fiabilitat: 4/4** — són els únics 4 casos de pretèrit simple que
apareixen en el benchmark de 60 frases, i les 4 referències ho converteixen
a perifràstic sense excepció.

### 11.2 Elisió després d'aplicar una altra regla

Quan una substitució (lèxica o morfològica) produeix una paraula que
comença en vocal, cal ajustar l'elisió de l'article o la preposició
immediatament anterior: *de* → *d'*, *la*/*el* → *l'*. Per exemple,
*calfar→escalfar* fa que "de calfar-nos" passe a "d'escalfar-nos", no "de
escalfar-nos". No és una regla dialectal en si mateixa — és ortografia
catalana general que cal aplicar cada vegada que una altra regla la
dispara.

### 11.3 Pendent de confirmar: "a/al + infinitiu" → "en + infinitiu"

| Occidental | Oriental |
|---|---|
| Al parlar de la predicació verbal... | En parlar de la predicació verbal... |
| A l'eixir a l'exterior... | En sortir a l'exterior... |

**Fiabilitat: 2/2, però només 2 casos observats** — massa poca mostra per
a fixar-ho com a regla. Aplicar-ho sense més confirmació podria trencar
frases on "al"/"a" siga correcte per algun altre motiu. Queda documentat
com a candidat, no com a regla aplicada.

---

## Apèndix: evidència i fiabilitat de cada regla

Les seccions anteriors donen les regles ja depurades, per a llegir com un
tema d'estudi. Este apèndix arreplega **d'on ix cada una** i amb quina
fiabilitat, per a qui vulga auditar les decisions en lloc de confiar-se de
la conclusió. Dos fonts, amb metodologies distintes:

- **Diccionari morfològic** `apertium-cat.cat.dix`: es comparen les formes
  marcades `v="cat"` amb les marcades `v="val_gva"` per a cada paradigma de
  flexió. La **cobertura** indica quants casos reals del diccionari
  seguixen el patró, del total de casos amb eixa combinació gramatical —
  una cobertura baixa vol dir excepcions freqüents, i que la regla NO s'ha
  d'aplicar de manera mecànica.
- **Anàlisi del benchmark de traducció** (60 frases occidental/oriental,
  `03_seleccion_de_modelo/benchmark_corpus.json`): patrons que només es veuen
  comparant frases completes, no paraules soltes — és d'ací d'on ix la
  secció 11 (sintaxi).

### A.1 Morfologia verbal — cobertura detallada

| Patró | Oriental | Occidental | Cobertura | Exemple |
|---|---|---|---|---|
| Imperfet de subjuntiu, totes les persones | -és/-essis/-éssim/-éssiu/-essin | -era/-eres/-érem/-éreu/-eren | 78-84% en verbs generals; 95-100% en auxiliars/modals/`ser`/`haver` | *hagués* → *haguera* |
| Imperfet d'indicatiu, 1a i 2a plural | -èiem / -èieu | -éiem / -éieu | **11/11 (100%)** | *quèiem* → *quéiem* |
| Present de subjuntiu i imperatiu (3a persona) | -ui / -in | -a / -en | 40-70% (verbs irregulars) | *sigui* → *siga* |
| Participi masculí singular | -ès | -és | 6/11 (55%) — es tracta com a paraules soltes ja confirmades, no com a regla general | *atès* → *atés* |

**Descartats per baixa fiabilitat** (apareixen al diccionari però amb massa
poc suport per a aplicar-los sense revisar cada verb): imperatiu 1a/2a
plural (2/4, 1/1), imperatiu/present 2a singular en *-eu/-au* (2-3/12-13),
present 2a/3a plural *-euen/-auen* (3/11), infinitiu *-enir/-indre* (4/13
— ja cobert un a un a la regla d'infinitius irregulars), participi femení
i masculí plural (2/4, 2/6).

### A.2 Pronoms, possessius, numerals, ordinals i gentilicis

| Categoria | Cobertura | Detall |
|---|---|---|
| Pronom tònic de tractament (vostè/vosté) | 2/2 (100%) | — |
| Possessiu feble de 3a persona (qualsevol ús gramatical) | 100% en tots els usos | La regla 2 val igual per a pronom, adjectiu, determinant i relatiu — al diccionari apareixien repartits en 4 etiquetes distintes |
| Numerals amb "huit" | Confirmat en tots els casos trobats | Arrel, no llista de paraules |
| Ordinals -é→-è | 113 lemes confirmats | — |
| Gentilicis de país/idioma -és→-ès | **300+ lemes confirmats** | Corregeix una xifra antiga (4/10) que venia d'una mostra massa xicoteta |
| Sustantiu -ès/-és fora de gentilicis | 4/10 (36%) | No generalitzable, paraules soltes ja confirmades |
| Numeral "dos/dues", concordança de gènere | Font distinta: no ve del diccionari Apertium ni del benchmark, ve de la normativa oficial AVL/IEC | Regla d'aplicació condicional (depén del gènere del nom que acompanya "dos" en cada frase), no una substitució fixa — vore secció 6.3 |

### A.3 Lèxic diferencial: com s'ha construït

`lexico_fiable.json` (194 parelles, fitxer d'esta mateixa carpeta) ve de
tres fonts, totes confirmades, cap inventada:

- 31 parelles de les 368 formes que Apertium marca explícitament com a
  valencianes (`v="val_gva"` exclusiu), amb la seua forma catalana
  confirmada dins del mateix diccionari.
- 34 parelles d'una font externa curada (contrastius Paula Guerrero).
- 129 parelles revisades a mà a partir de `paralelos.txt` (358 parells
  originals, dels quals 73 ja coincidien als dos dialectes i uns altres es
  van descartar per estar ja coberts per una regla general — numerals,
  possessius, "vesprada"... — o per reduir-se a una paraula ja inclosa).

Vore `../documentacion/metodologia_y_resultados.md` per al detall complet del procés i dels
bugs trobats en auditar el corpus generat amb este lèxic.
