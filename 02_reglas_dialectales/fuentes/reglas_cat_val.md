# Guia de regles català (oriental) ↔ valencià GVA (occidental)

Document de referència lingüística generat a partir de dues fonts amb
metodologies distintes, indicades en cada secció perquè es puga valorar la
seua fiabilitat:

- **Diccionari morfològic** `apertium-cat.cat.dix` (seccions 1-3): es
  comparen les formes marcades `v="cat"` amb les marcades `v="val_gva"` per
  a cada paradigma de flexió. Cada patró indica la seua **cobertura**
  (quants casos reals del diccionari el segueixen, del total de casos amb
  eixa combinació gramatical) — una cobertura baixa vol dir que hi ha
  excepcions freqüents i que NO s'ha d'aplicar de manera mecànica.
- **Anàlisi del benchmark de traducció** (secció 4): patrons detectats
  comparant les 60 frases occidental/oriental de `evalua_modelos/benchmark_corpus.json`
  frase per frase — útil per a diferències sintàctiques que el diccionari
  de paraules soles no pot mostrar (com l'orde dels temps verbals).
- **`paralelos.txt`** (secció 5): llista de vocabulari revisada a mà,
  en verificació activa.

Este document és la base bruta amb les xifres de suport de cada regla; el
document pensat per a llegir com un tema d'estudi, ja net i sense taules
d'evidència, és
[`guia_dialectal_valencia_catala.md`](../reglas_prompt/guia_dialectal_valencia_catala.md).
Les regles que ja estan integrades en el prompt real del model es poden
consultar literalment a
[`system_prompt.md`](../reglas_prompt/system_prompt.md).

---

## 1. Morfologia verbal

### 1.1 Patrons fiables (confirmats en múltiples classes de verbs)

Estos patrons apareixen, amb els mateixos sufixos, en diverses classes
verbals del diccionari (verbs regulars, modals, `ser`/`esser`, `haver`,
auxiliars) — es presenten junts perquè són la mateixa regla, no regles
distintes per casualitat.

| Patró | Oriental | Occidental | Cobertura | Exemple |
|---|---|---|---|---|
| Imperfet de subjuntiu, totes les persones | -és/-essis/-éssim/-éssiu/-essin | -era/-eres/-érem/-éreu/-eren | 78-84% en verbs generals; 95-100% en auxiliars/modals/`ser`/`haver` | *hagués* → *haguera*, *fóssim* → *fórem* |
| Imperfet d'indicatiu, 1a i 2a plural | -èiem / -èieu | -éiem / -éieu | **11/11 (100%)** | *quèiem* → *quéiem*, *quèieu* → *quéieu* |
| Present de subjuntiu i imperatiu (3a persona, sg. i pl.) | -ui / -in | -a / -en | 40-70% (verbs irregulars) | *sigui* → *siga*, *vagin* → *vagen* |

Nota sobre la fila 3: en català, l'imperatiu de tractament formal (vostè,
vostès) i l'imperatiu de 3a persona reutilitzen literalment les formes del
present de subjuntiu — per això les dos combinacions gramaticals
("imperatiu" i "pres. subjuntiu" al diccionari) mostren exactament el
mateix sufix i la mateixa cobertura. No és una coincidència, són la mateixa
forma. Per la cobertura moderada (40-70%, és a dir, fins a 6 de cada 10
verbs poden no seguir-lo), el prompt real no generalitza este patró: nomes
aplica als verbs irregulars ja confirmats un a un (*puga/tinga/vinga/
vaja/siga/haja* i els seus plurals — vore `system_prompt.md`, regla 5).

### 1.2 Patrons puntuals o de baixa fiabilitat (NO recomanats com a regla general)

Apareixen al diccionari però amb massa poc suport (menys de la mitat dels
casos, o només 1-2 exemples) per a aplicar-los de manera automàtica sense
revisar cada verb:

| Categoria | Tret | Oriental | Occidental | Cobertura |
|---|---|---|---|---|
| Verb | Imperatiu 1a pl | -guem | -em | 2/4 |
| Verb | Imperatiu 2a pl | -gueu | -eu | 1/1 |
| Verb | Imperatiu/pres. ind. 2a sg | -eu(s) | -au(s) | 2-3/12-13 |
| Verb | Pres. ind. 2a/3a pl | -euen | -auen | 3/11 |
| Verb | Pres. ind. 3a sg | -eu | -au | 3/13 |
| Verb | Infinitiu | -enir | -indre | 4/13 |
| Verb | Participi f sg/pl | -erta/-ertes | -ida/-ides | 2/4 |
| Verb | Participi m pl | -s | -os | 2/6 |
| Verb `ser/esser` | Pres. ind. 2a sg | -ets | -eres | 1/1 (cas únic: *ets* → *eres*) |

Els verbs irregulars de la fila "Infinitiu -enir/-indre" (*tindre/tenir*,
*vindre/venir*...) ja estan coberts un a un a la regla 4 del prompt
(infinitius irregulars) — no fa falta cap regla general de sufix perquè la
cobertura (31%) és massa baixa per a fiar-se'n fora d'eixa llista tancada.

### 1.3 Participi amb accent (-ès/-és)

| Oriental | Occidental | Cobertura |
|---|---|---|
| -ès (participi m sg) | -és | 6/11 (55%) |

Coincidix en la forma amb el patró de gentilicis de la secció 3, però és
una combinació gramatical distinta (participi verbal, no adjectiu de
nacionalitat) — es tracta com a paraules soltes ja confirmades
individualment (*atés→atès*, *desentés→desentès*...), no com a regla
general, perquè 45% dels casos NO seguixen este patró.

---

## 2. Pronoms i possessius

| Categoria | Oriental | Occidental | Cobertura | Exemple |
|---|---|---|---|---|
| Pronom tònic de tractament (3a persona) | vostè/vostès | vosté/vostés | 2/2 (100%) | *vostè* → *vosté* |
| Possessiu feble de 3a persona, en qualsevol ús gramatical (pronom, adjectiu, determinant, relatiu) | -va / -ves | -ua / -ues | 100% en tots els usos (3/3 cada un) | *la meva* → *la meua*, *les seves* → *les seues* |
| Pronom tònic + "mateix/a" | -è/-ès mateix(a/os/es) | -é/-és mateix(a/os/es) | 1/1-1/2 (mostra molt xicoteta) | *ell mateix* → *ell mateix* (sense canvi real) |

La fila de possessius junta el que al diccionari apareixia repartit en
quatre etiquetes gramaticals distintes (pronom, adjectiu, determinant,
relatiu) perquè és exactament la mateixa alternança -va/-ua en tots els
casos — coincidix amb la regla 3 del prompt (meua→meva) i no fa falta
tractar-la per separat.

---

## 3. Numerals, ordinals i gentilicis

Estos tres blocs es tracten junts perquè comparteixen el mateix mecanisme
(una arrel o sufix que canvia, independent de la paraula concreta):

| Bloc | Patró | Cobertura | Detall |
|---|---|---|---|
| Numerals amb "huit" | huit → vuit (arrel, aplica dins de compostos) | confirmat en tots els casos trobats | Vore `guia_dialectal_valencia_catala.md` secció 6 |
| Ordinals | -é (occidental) → -è (oriental) | 113 lemes confirmats (*cinqué→cinquè*, *novè→nové*...) | Regla general, secció 6.1 de la guia |
| Numerals compostos -vuit-cents/-huit-cents | -vuit- → -huit- | 3/3 | Cas particular de la regla "huit" |
| Gentilicis de país/idioma | -és (occidental) → -ès (oriental) | **300+ lemes confirmats** (paradigmes `afgan/ès__adj` i `angl/ès__n`) | Regla general, secció 6.2/7 de la guia — NO aplica a "és" (verb ser) ni "més" (quantitat) |
| Nom comú "colp" | colp → cop (i derivats: colpet→copet) | ja al lèxic fiable | *de colp→de cop*, *cada colp→cada cop* |
| Sustantiu masculí singular -ès/-és (fora de gentilicis) | -ès | -és | 4/10 (36%, baixa) | No generalitzable — paraules soltes ja confirmades individualment (interés, imprés...) |

---

## 4. Sintaxi (evidència del benchmark, no del diccionari de paraules)

Els dos patrons d'ací baix no es poden detectar comparant paraules soltes
al diccionari — són diferències d'estructura de la frase, detectades
comparant les 60 frases completes del benchmark occidental/oriental.

### 4.1 Pretèrit perfet simple → perifràstic ✅ confirmat, ja al prompt

El valencià fa servir sovint la forma simple del pretèrit (*passà*,
*celebrà*, *quedaren*, *transformaren*); l'oriental estàndard prefereix la
forma perifràstica (*va passar*, *va celebrar*, *van quedar*, *es van
transformar*).

**Cobertura: 4/4 (100%)** — són els únics 4 casos de pretèrit simple que
apareixen en tot el benchmark de 60 frases, i les 4 referències ho
converteixen a perifràstic sense excepció. Regla afegida al prompt base
(`SYSTEM_PROMPT_BASE`, regla 8) arran d'este anàlisi.

### 4.2 "A/al + infinitiu" → "en + infinitiu" ⚠️ pendent de confirmar

| Occidental | Oriental |
|---|---|
| Al parlar de la predicació verbal... | En parlar de la predicació verbal... |
| A l'eixir a l'exterior... | En sortir a l'exterior... |

**Cobertura: 2/2, però només 2 casos en tot el benchmark** — massa poca
mostra per a fixar-ho com a regla dura. Aplicar-ho sense més confirmació
podria trencar frases on "al"/"a" siga correcte per algun altre motiu. **NO
s'ha afegit al prompt** — queda ací documentat com a candidat, pendent de
trobar més casos (al diccionari Apertium o en text real) abans de
promoure'l a regla.

---

## 5. Vocabulari

**En verificació** — esta secció ja no usa el lèxic combinat antic
(`palabras_traducidas.txt` + `apertium-cat.cat.dix`, 1.601 paraules). De
moment reflecteix únicament `fuentes/paralelos.txt` (358 parells en total),
que és el fitxer que s'està revisant i confirmant a mà ara mateix. D'eixos,
**285** tenen forma distinta entre valencià i català (taula d'ací baix) i
**73** ja coincidixen en els dos dialectes (s'inclouen a `paralelos.txt`
com a referència del que NO canvia, però no apareixen ací per no ser una
diferència real).

| Valencià | Català |
|---|---|
| a colp calent | a cop calent |
| a imatge i semblança seua | a imatge i semblança seva |
| a la faena | a la feina |
| a la vesprada | a la tarda |
| a les huit | a les vuit |
| a les vesprades | a les tardes |
| a mig vesprada | a mitja tarda |
| a mitja vesprada | a mitja tarda |
| a mitjan vesprada | a mig tarda |
| a petició meua | a petició meva |
| a petició seua | a petició seva |
| a petició teua | a petició teva |
| abellir | plaure |
| acatxar | ajupir |
| acurtar | escurçar |
| ací | aquí |
| ahir a la vesprada | ahir a la tarda |
| al caient de la vesprada | al capvespre |
| al més prompte | al més aviat |
| al més prompte possible | al més aviat possible |
| alfàbega | alfàbrega |
| algeps | guix |
| algepsaire | guixaire |
| amb prou faenes | amb prou feines |
| amerar | xopar |
| ametla | ametlla |
| ametler | ametller |
| amprar | manllevar |
| anar a la seua | anar a la seva |
| anou | nou |
| antevespra | antevigília |
| aparéixer | aparèixer |
| aqueix | aquell |
| aquesta vesprada | aquesta tarda |
| argilaga | argelaga |
| arrancada | arrencada |
| arrancament | arrencament |
| arrancar | arrencar |
| arrancar a córrer | arrencar a córrer |
| arrancar el bull | arrencar el bull |
| arrancar la cabellera | arrencar la cabellera |
| arrere | enrere |
| atés | atès |
| avant | endavant |
| batle | batlle |
| bellota | gla |
| bes | petó |
| beset | petonet |
| bigot | bigoti |
| bitla | bitlla |
| bla | tou |
| bona vesprada | bona tarda |
| bresquilla | préssec |
| bresquillera | presseguer |
| buscar | cercar |
| butla | butlla |
| cada colp | cada cop |
| calfament | escalfament |
| calfaplats | escalfaplats |
| calfar | escalfar |
| camallada | gambada |
| cap ací | cap aquí |
| cinquanta-huit | cinquanta-vuit |
| clòtxina | musclo |
| colpet | copet |
| com més prompte | com més aviat |
| com més prompte millor | com més aviat millor |
| comité de direcció | comitè de direcció |
| comité executiu | comitè executiu |
| comités executius | comitès executius |
| company de faena | company de feina |
| comparéixer | comparèixer |
| contramotlura | contramotllura |
| convéncer | convèncer |
| conéixer | conèixer |
| conéixer el marro | conèixer el marro |
| corder | xai / be / anyell |
| cosquerelles | pessigolles |
| coste el que coste | costi el que costi |
| creïlla | patata |
| cuixa de corder | cuixa de xai / cuixa d'anyell |
| cércol | cèrcol |
| d'ara en avant | d'ara endavant |
| d'hora a la vesprada | d'hora a la tarda |
| d'un colp de ploma | d'un cop de ploma |
| dacsa | blat de moro |
| de colp | de cop |
| de colp i volta | de cop i volta |
| de vesprada | a la tarda |
| demà a la vesprada | demà a la tarda |
| depòsit | dipòsit |
| depòsit funerari | dipòsit funerari |
| depòsits funeraris | dipòsits funeraris |
| desaparéixer | desaparèixer |
| desconéixer | desconèixer |
| desembossar | desembussar |
| despús-ahir | abans-d'ahir |
| despús-anit | fa dues nits |
| despús-demà | demà passat |
| desunflar | desinflar |
| desvetlar | desvetllar |
| dènou | dinou |
| dèsset | disset |
| díhuit | divuit |
| eixida | sortida |
| eixir d'un mal pas | sortir d'un mal pas |
| embossar | embutxacar |
| embós | embús |
| emmotlar | emmotllar |
| emmotlurar | emmotllurar |
| emotlament | emmotllament |
| empenyiment | embranzida |
| en contra de la meua voluntat | en contra de la meva voluntat |
| en data de hui | en data d'avui |
| en la mesura que siga possible | en la mesura que sigui possible |
| en tant que siga possible | en tant que sigui possible |
| entropessar | ensopegar |
| envernissador | vernissador |
| envernissar | vernissar |
| escaló | graó |
| esguitar | esquitxar |
| espatla | espatlla |
| espatla ibèrica d'enceball | espatlla ibèrica de gla |
| espatlar | espatllar |
| espatlera | espatllera |
| espatles ibèriques d'enceball | espatllles ibèriques de gla |
| espatleta | espatlleta |
| espentar | empènyer |
| espill | mirall |
| espuma | escuma |
| espumadora | escumadora |
| espumejar | escumejar |
| estrela | estrella |
| faena | feina |
| faena a mitja jornada | feina a mitja jornada |
| fardatxo | llangardaix |
| fenoll | fonoll |
| fer cosquerelles | fer pessigolles |
| fer el desentés | fer el desentès |
| fer marxa arrere | fer marxa enrere |
| fer una besada | fer un petó |
| fesol | mongeta |
| fins hui | fins avui |
| fins prompte | fins aviat |
| forma de reembossament | forma de reemborsament |
| gestor d'arrancada | gestor d'arrencada |
| granera | escombra |
| guardaespatles | guardaespatlles |
| guatla | guatlla |
| heus ací | heus aquí |
| hui | avui |
| hui dia | avui dia |
| hui en dia | avui dia |
| huit | vuit |
| huit-cents | vuit-cents |
| huit-centè | vuit-centè |
| huitanta | vuitanta |
| huitanta-cinc | vuitanta-cinc |
| huitanta-cinquè | vuitanta-cinquè |
| huitanta-dos | vuitanta-dos |
| huitanta-dosè | vuitanta-dosè |
| huitanta-huit | vuitanta-vuit |
| huitanta-huitè | vuitanta-vuitè |
| huitanta-nou | vuitanta-nou |
| huitanta-novè | vuitanta-novè |
| huitanta-quatre | vuitanta-quatre |
| huitanta-quatrè | vuitanta-quatrè |
| huitanta-set | vuitanta-set |
| huitanta-setè | vuitanta-setè |
| huitanta-sis | vuitanta-sis |
| huitanta-sisè | vuitanta-sisè |
| huitanta-tres | vuitanta-tres |
| huitanta-tresè | vuitanta-tresè |
| huitanta-u | vuitanta-u |
| huitanta-un | vuitanta-un |
| huitanta-unè | vuitanta-unè |
| huitantè | vuitantè |
| huitavt | vuitè |
| huitcentista | vuitcentista |
| joguet | joguina |
| jupetí | armilla |
| l'altra vesprada | l'altra tarda |
| llavable | rentable |
| llavadora | rentadora |
| llavamans | rentamans |
| llavaplats | rentaplats |
| llavar | rentar |
| llentilla | llentia |
| manganés | manganès |
| matí i vesprada | matí i tarda |
| matí vesprada i nit | matí tarda i nit |
| meló d'Alger | síndria |
| mesclar | barrejar |
| misto | llumí |
| molt arrere | molt enrere |
| motle | motlle |
| motlura | motllura |
| motlurar | motllurar |
| més arrere | més enrere |
| més avant | més endavant |
| nadador | nedador |
| nadar | nedar |
| no reconéixer | no reconèixer |
| noranta-huit | noranta-vuit |
| noranta-huitè | noranta-vuitè |
| o siga | o sigui |
| oroneta | oreneta |
| pallola | xarampió |
| paracolps | paracops |
| parlant de patuès | parlant de patès |
| parlant de patués | parlant de patès |
| parèixer | semblar |
| paréixer | semblar |
| pellorfa | pellofa |
| per la meua banda | per la meva banda |
| per la seua banda | per la seva banda |
| per la seua part | per la seva part |
| per la teua banda | per la teva banda |
| per part meua | per part meva |
| per part seua | per part seva |
| per part teua | per part teva |
| per primer colp | per primer cop |
| per segon colp | per segon cop |
| per tercer colp | per tercer cop |
| per un colp de sort | per un cop de sort |
| pescateria | peixateria |
| pesebre | pessebre |
| pimentó | pebrot |
| pista de bitles | pista de bitlles |
| pitxer | gerra |
| precalfament | preescalfament |
| prima de reembossament | prima de reemborsament |
| prompte | aviat |
| punyada | cop de puny |
| pésol | pèsol |
| quaranta-huit | quaranta-vuit |
| que trau foc pels queixals | que treu foc pels queixals |
| rabosa | guineu |
| rascar | gratar |
| reaparéixer | reaparèixer |
| recalfar | reescalfar |
| reconéixer | reconèixer |
| redonesa | rodonia |
| reembossable | reemborsable |
| reembossar | reemborsar |
| renyonera | ronyonera |
| respatler | respatller |
| revetla | revetlla |
| romer | romaní |
| seixanta-huit | seixanta-vuit |
| sempre a la seua disposició | sempre a la seva disposició |
| setanta-huit | setanta-vuit |
| siga com siga | sigui com sigui |
| siga el que siga | sigui el que sigui |
| sobrecalfament | sobreescalfament |
| sobrecalfar | sobreescalfar |
| sàndwitx | sandvitx |
| ségol | sègol |
| sémola | sèmola |
| tan bé com siga possible | tan bé com sigui possible |
| tan prompte | tan aviat |
| tancar de colp | tancar de cop |
| tenir fam | tenir gana |
| terratrémol | terratrèmol |
| tomaca | tomàquet |
| trenta-huit | trenta-vuit |
| tret d'eixida | tret de sortida |
| trévol | trèvol |
| térbol | tèrbol |
| ulls ametlats | ulls ametllats |
| vesprada | tarda |
| vetla | vetlla |
| vetlada | vetllada |
| vetlar | vetllar |
| vint-i-huit | vint-i-vuit |
| vuitavat | vuitè |
| xafable | trepitjable |
| xarrada | xerrada |
| xarrar | xerrar |
| xic | noi |
| ximenera | xemeneia |
| xiquet | nen |
| xocolate | xocolata |
| xuplar | xuclar |
| òbila | òliba |

---

## 6. Demostratius

Alternança d'ús general entre el valencià col·loquial (est-) i el català
(aquest-); l'AVL també admet *aquest/aquesta* com a forma normativa, per
això no apareix amb `v="val_gva"` al diccionari Apertium — regla de
coneixement general, no derivada mecànicament.

| Valencià | Català |
|---|---|
| este | aquest |
| esta | aquesta |
| estos | aquests |
| estes | aquestes |

## 7. Locucions

| Valencià | Català | Font |
|---|---|---|
| a on | on | coneixement general (al dix sense `v=`) |
| hui dia | avui dia | dix (`v="val_gva"` vs `v="cat val_uni"`) |
