*[Llegeix-ho en castellà](README.es.md)*

# Motor de diccionari determinista — etapa 5

Este paquet (`traductor/`) viu a l'arrel del repositori, sense el prefix
numèric de les altres etapes (`01_...` a `04_...`), perquè és un paquet
Python que s'importa pel nom (`import traductor`) des d'altres parts del
codi — un nom de mòdul no pot començar per un dígit en Python.
Conceptualment és l'etapa 5 del projecte.

## Per què existix açò

Les etapes 1-4 usen un LLM (qwen2.5:14b) amb un system prompt de regles +
glossari dinàmic per a generar el corpus sintètic. Funciona raonablement
bé (BLEU ~93 en el benchmark de 60 frases), però la revisió manual va
trobar un ~20% d'errors reals enfront del ~1,5% que detecten les
comprovacions automàtiques — la majoria, al·lucinacions del model sense
relació amb cap regla dialectal (vore `../documentacio/metodologia_i_resultats.md`,
seccions 6 i 9).

Un motor de diccionari no pot al·lucinar: si una paraula no està en cap
taula, senzillament no la toca. Este paquet no substituïx el LLM, però és
una base determinista, auditable i sense dependències.

## DECISIÓ D'ARQUITECTURA (30/09/2026): pur lookup de diccionari + 2 sufixos productius

Fins al 29/09/2026 este paquet tenia 10 capes: lookup de diccionari
(lèxic, conjugacions) + regles morfològiques i de sufix generalitzades
(demostratius, gentilicis, incoatius, pretèrit perfet, locucions, elisió).
Eixes regles cobrien més casos, però barrejaven dades de diverses fonts
(Apertium, Paula Guerrero, taules escrites a mà) amb la font de Mauricio.

El mateix dia 30/09/2026, a la vesprada, es va reduir el traductor a
**NOMÉS lookup exacte de diccionari, i NOMÉS amb dades de
`02_regles_dialectals/lexic/font_mauricio/`** (equip AVLizador) — cap
regla de sufix, patró morfològic ni reconstrucció algorítmica, i cap font
que no siga Mauricio.

**Conseqüència, mesurada, no assumida**: el benchmark de 150 frases va
passar de **89/150 (59,3%)** amb l'arquitectura de 10 capes a **27/150
(18,0%)** amb l'arquitectura pura de diccionari. La pèrdua venia sobretot
de: demostratius (`este/eixe→aquest`, la conversió més freqüent del
corpus, sense font a Mauricio), possessius masculins/tònics (mai van
tindre regla, no canvien), el patró general de gentilicis `-és→-ès`
(només cobria les 695 paraules literals d'accentuació, no qualsevol
gentilici),
els incoatius `-ix→-eix` (només els verbs concrets que ja estaven a
`conjugacions_dialectals.json`), i el pretèrit perfet simple → perifràstic
(`celebrà→va celebrar`, cap diccionari dona formes perifràstiques).

**Ampliació (mateix dia, més tard)**: es va confirmar que un pur
diccionari mai pot cobrir un patró OBERT i PRODUCTIU -- per definició, un
diccionari només conté paraules que algú ja hi ha ficat. Es van tornar a
afegir 2 regles de sufix (no llistes tancades) per als 3 patrons més
productius i millor evidenciats: `accentuacio.py` (`-és→-ès`,
`-éixer→-èixer`) i `incoatius.py` (`-ix→-eix`). No es va tornar arrere en
la resta encara (pretèrit perfet, locucions, elisió automàtica general)
-- vore "Coses que ja no es cobrixen" a `font_mauricio/README.md`. Amb
això el benchmark va pujar a **28/150 (18,7%)** -- una millora xicoteta
perquè la majoria dels casos d'estos 2 patrons ja estaven coberts pel
diccionari d'accentuació.

**Recreat el mateix dia, encara més tard**: `demostratius.py`
(`este/eixe/aqueix→aquest`, `açò→això`) -- l'eliminació del 30/09/2026
havia sigut un error, no un patró que "no calia" com els altres: és el
paradigma gramatical MÉS FREQÜENT del corpus, i cap diccionari de
Mauricio el llista (és una llista tancada, no lèxic obert). Amb això el
benchmark va pujar de cop a **83/150 (55,3%)** -- el salt més gran de tots
els canvis d'esta sessió, confirmant que els demostratius eren la peça
que més faltava.

**Ampliació final del mateix dia**: `flexio_genere_avl.json` (dins de
`lexic.py`) afig derivació de gènere/nombre per a un grapat curat de
paraules amb variació real (`xiquet/xiqueta/xiquets/xiquetes→nen/nena/nens/nenes`).
Provat també l'enfocament "escanejar tot el lèxic per patró de sufix" --
descartat de seguida: la majoria de paraules acabades en consonant
"segura" són verbs/adverbis sense gènere, donant formes absurdes
("cercar"→"cercara"). Amb la llista curada, el benchmark va pujar a
**92/150 (61,3%)**.

Esta xifra es deixa ací a propòsit, sense suavitzar-la: és la
conseqüència directa i coneguda de la decisió, no un bug.

## DECISIÓ D'ARQUITECTURA (01/10/2026): concordança `dos→dues`, primera capa (article/demostratiu)

Pèrdua ja documentada des del 30/09/2026 (vore docstring de
`numerals.py`): la concordança de gènere `dos/dues` s'havia llevat en
passar a pur lookup de diccionari, perquè "dos"/"dues" s'escriuen igual
als dos dialectes (no és una substitució lèxica Mauricio) -- el motor
simplement no corregia el desacord quan el valencià col·loquial usa "dos"
invariable davant d'un nom femení ("tinc dos germanes" en compte de "dues
germanes").

**Anàlisi prèvia a implementar res** (evidència, no teoria): es van
revisar els 150 casos del benchmark buscant totes les frases amb
"dos"/"dues" per a veure quin senyal distingix els casos reals. De ~28
frases amb "dos→dues" real, **13 anaven precedides directament per un
article o demostratiu que ja marca femení plural per si mateix** (`les`,
`estes`, `eixes`, `aqueixes`): "**les** dos institucions"→dues, "**estes**
dos circumstàncies"→dues. La resta eren casos "pelats" sense marcador
davant ("dos entitats", "dos terceres parts"), on només el sufix de la
paraula següent (-tat, -ció, -a) delata el gènere -- i un cas ("dos
consonants") no té cap marca formal, només es pot saber de memòria.

**Decisió**: implementar NOMÉS la primera capa (marcador davant), en un
fitxer a banda (`concordanca_dos_dues.py`) per a tindre-la controlada per
separat, i deixar la capa de sufix pendent expressament fins mesurar
l'impacte d'esta primera -- mateix criteri que `flexio_genere_avl.json`:
preferix un senyal segur i acotat abans que una heurística més àmplia amb
més risc de falsos positius. Els casos purament lèxics ("consonants") es
deixen fora a propòsit, per a una futura llista curada a mà si algun dia
donen problemes reals -- mai amb una regla general de gènere sobre tot el
lèxic (mateix motiu pel qual es va descartar l'escaneig automàtic a
`flexio_genere_avl.json`).

**Risc acceptat conscientment**: el benchmark mateix és inconsistent en 2
casos (cites de registre antic/dialectal) on la referència deixa "dos"
sense corregir expressament. La regla el corregix igualment -- es
prioritza la correcció gramatical real sobre eixes 2 coincidències
concretes.

**Resultat, mesurat**: el benchmark va pujar de **99/150 (66,0%)** a
**111/150 (74,0%)** -- el canvi individual més gran des de la recreació
dels demostratius.

## Arquitectura

Pipeline seqüencial de capes sobre una llista de `Token`, no substitucions
de text sobre la frase sencera:

```
text ──tokenize()──▶ [Token, Token, ...] ──marca_noms_propis()──▶
    ──▶ LexicRule ──▶ ConjugacionsDictRule ──▶ PossessiusRule ──▶ NumeralsRule
    ──▶ ConcordancaDosDuesRule ──▶ DemostratiusRule ──▶ AccentuacioRule
    ──▶ IncoatiusRule ──▶ detokenize() ──▶ text convertit
```

### `Token` (`rules/__init__.py`)

```python
@dataclass
class Token:
    surface: str          # forma original, mai canvia
    translated: str        # es va sobreescrivint capa a capa
    pos: str = ""           # etiqueta gramatical; "" si no hi ha spaCy (opcional, no instal·lat)
    is_translated: bool = False
    is_proper_noun: bool = False
    start: int = 0
```

`detokenize()` simplement concatena `translated` de tots els tokens en
orde — com els espais i la puntuació també són tokens (amb
`translated == surface` mentre cap regla els toque), el text es
reconstruïx exacte sense lògica de reinserció d'espais.

### Per què un flag per token i no regex sobre el text sencer

Cada capa marca `is_translated = True` en el moment que toca un token, i
totes les capes posteriors respecten eixe flag (`if tok.is_translated:
continue`). Amb 8 capes independents, açò evita que dos fonts es
trepitgen sense que ningú se n'adone — la primera capa que reconeix una
paraula es queda el mèrit, la resta la salta.

### Decisió de disseny: apòstrofs i guionets són part de la paraula

`tokenize()` tracta `d'escola`, `l'AVL` o `dir-li` com **un sol token**
cada un, no com a paraula+frontera. Conseqüència: un token com `d'este`
mai coincidix amb l'entrada `"este"` d'un diccionari.
`separa_prefix_elidit()` (`rules/__init__.py`) és el fix -- `lexic.py` i
`conjugacions_dict.py` (les úniques 2 capes on el prefix pot canviar de
sentit segons la paraula trobada) l'usen com a segon intent quan la cerca
directa falla: separa el prefix elidit (`d'`, `l'`, `s'`, `m'`, `t'`,
`n'`) i torna a buscar només la part real de la paraula.

**Bug real trobat i arreglat (30/09/2026)**: reconstruir sempre
`prefix + forma_trobada` no basta -- si la paraula trobada canvia de
vocal inicial a consonant inicial (p.ex. "eixir"→"sortir"), l'elisió
original ja no té sentit: "a l'eixir" donava l'incorrecte "a l'sortir" en
compte de "al sortir". `aplica_amb_prefix_elidit()` (`rules/__init__.py`)
ho gestiona: si la forma trobada ja no comença en vocal/h muda, DESFÀ
l'elisió (torna el prefix a la seua forma completa: "l'"→"el", "d'"→"de"...)
i, si el resultat és "el" i el token anterior és la preposició "a"/"de",
els contrau ("a"+"el"→"al", "de"+"el"→"del") en compte de deixar "a el".

### Protecció de noms propis (`marca_noms_propis`)

S'executa una sola vegada, abans de la primera regla: marca
`is_proper_noun` en tota paraula capitalitzada que **no** siga la primera
del text (la primera lletra d'una frase sempre va en majúscula, siga o no
nom propi). És la mateixa heurística ja provada en
`03_seleccio_de_model/evalua_models.py::glossari_per_frase()`, afegida
allí després d'un incident real amb `blanca`/`Blanca` i `roig`/`Roig`
(vore `../documentacio/metodologia_i_resultats.md`, secció 6). Límit
conegut, heretat sense arreglar: un nom propi que és la **primera**
paraula del text mai es detecta.

## Les 8 capes

- **`lexic.py`** — lookup de lèxic general + accentuació + gènere/nombre.
  Fusiona `flexio_genere_avl.json` (prioritat màxima, vore baix),
  `lexic_mauricio.json` (còpia de `lexico_general_limpio.json`, filtrat:
  exclou `_PENDENT`, topònims, multi-paraula, resol `canonica`) i
  `lexic_acentuacio_mauricio.json` (còpia de `acentuacion_limpio.json`,
  695 parelles). Exclou a mà "després" (bug de dades confirmat al fitxer
  font: el llista com si seguira el patró d'accentuació, però no canvia
  mai en cap dels dos dialectes).
  **Gènere/nombre (`flexio_genere_avl.json`, afegit 30/09/2026)**: llista
  CURADA a mà (no escaneig automàtic de tot el lèxic -- es va provar i la
  majoria de paraules acabades en consonant "segura" eren verbs/adverbis
  sense gènere, donant formes absurdes com "cercara"). Dos categories:
  `regulars` (deriva fem/plural automàticament: `xiquet→nen` dona també
  `xiqueta→nena`, `xiquets→nens`, `xiquetes→nenes`) i `irregulars`
  (formes exactes per a quan el patró "+a" no val, com `menut→menuda` --
  irregularitat participial que no es pot generalizar amb seguretat, ja
  que "petit" acaba igual però és regular: "petita", no "petida"). De pas
  resol la regressió que hi havia amb "xiquet" (abans guanyava "noi" per
  ambigüitat a Mauricio sense font externa que ho desempatara).
- **`conjugacions_dict.py`** — lookup de formes verbals. Fusiona
  `conjugaciones_limpio.json` (969 formes, 111 verbs) i
  `verbos_no_ambiguos.json` (261 formes més, 45 verbs, afegit 30/09/2026,
  totes marcades `ambigu: false`) a `conjugacions_dialectals.json`.
  Exclou les formes `problematica: true` (ambigües indicatiu/subjuntiu
  sense pos-tagging) -- només "haja"/"hagen" es queden sense traduir per
  això (tota la conjugació de "haver" és `problematica`). Protegix "o
  siga" (locució fixa "és a dir") perquè no es confonga amb el verb "ser"
  en subjuntiu.
- **`possessius.py`** — lookup de possessius febles femenins
  (`meua/teua/seua` + plurals → `meva/teva/seva`). Font:
  `possessius_mauricio.json` (còpia de `posesivos_cat_val.json`), un
  producte cartesià sense filtrar del qual només es queden els 6 parells
  on el número (singular/plural) casa als dos costats.
- **`demostratius.py`** — lookup de demostratius: `este/eixe/aqueix`
  (tots tres col·lapsen cap a `aquest`, mateixa família + plurals) i el
  neutre `açò→això`. **Recreat 30/09/2026** (s'havia llevat del tot en
  passar a "pur diccionari de Mauricio" i era un error: cap diccionari
  pot cobrir un paradigma gramatical tancat que Mauricio no llista).
  Font: `demostratius_avl.json` (paradigma sourced de
  `regles_dialectals_amb_evidencia.md` §1). `aquell`/`allò` són idèntics
  als dos dialectes i no tenen entrada. La taula INVERSA (`aqueix→eixe`,
  per a un hipotètic traductor oriental→occidental) es queda documentada
  al mateix fitxer sense implementar-se -- este motor només tradueix en
  un sentit.
- **`numerals.py`** — lookup exacte contra `numerals_mauricio.json` (còpia
  de `numerales_limpio.json`, 180 files): tota la família huit/vuit,
  "dinou"/"disset" + derivats, i "díhuit"→"divuit" sense cap cas especial
  (és lookup exacte, no substitució de subcadena). Exclou 4 files de
  "vuitavat" que semblen una extracció trencada al fitxer font (mateix
  català repetit per a 4 valencians diferents).
- **`concordanca_dos_dues.py`** — regla de CONCORDANÇA (afegida
  01/10/2026, vore "DECISIÓ D'ARQUITECTURA"): corregix `dos→dues` quan el
  token immediatament anterior és `les`/`estes`/`eixes`/`aqueixes`/
  `aquelles`/`unes` (marcador de femení plural inequívoc, mai cap
  diccionari). No llig cap fitxer de dades -- la llista de marcadors és
  una constant xicoteta i tancada al mateix mòdul. NO cobrix casos
  "pelats" sense marcador davant (`dos entitats`) ni casos purament
  lèxics (`dos consonants`) -- vore la decisió per al perquè.
- **`accentuacio.py`** — 2 regles de SUFIX productives (afegides
  30/09/2026, vesprada, vore "DECISIÓ D'ARQUITECTURA"): `-és→-ès`
  (`francés→francès`, mateix patró que 695 paraules literals de
  `lexic_acentuacio_mauricio.json` però ara generalitzat a QUALSEVOL
  paraula) i `-éixer→-èixer` (`conéixer→conèixer`). Excepcions del primer
  patró (`és`/`més`, i 7 més trobades empíricament: `només`, `després`,
  `procés`, `congrés`, `accés`, `progrés`, `través`): set de Python, no
  fitxer -- cap diccionari diferencial pot confirmar que una paraula NO
  canvia.
- **`incoatius.py`** — regla de SUFIX productiva `-ix→-eix`
  (`establix→estableix`, afegida 30/09/2026), amb dos proteccions: mai
  toca paraules que ja acaben en "-eix" (`aparéixer`, `mateix`...) i
  llista negra de paraules reals acabades en consonant+ix que no són
  verbs (`baix`, `calaix`, `dibuix`, `guix`, `fix`, `prefix`, `sufix`).

## Mantindre `traductor/data/` sincronitzat amb les fonts

`traductor/rules/*.py` mai llig `02_regles_dialectals/lexic/` en temps
d'execució -- només llig còpies pròpies dins de `traductor/data/` (perquè
el paquet funcione de manera autònoma). Si edites un fitxer font de
`font_mauricio/` directament, eixe canvi no arriba al motor fins que
sincronitzes:

```bash
python -m traductor.sync_data --check   # només mostra què ha canviat, no escriu res
python -m traductor.sync_data           # sincronitza de veres i mostra el mateix resum
```

El resum diu exactament quines entrades s'han afegit/llevat per fitxer
(no sobreescriu en silenci). Els filtres de negoci (descartar `_PENDENT`,
topònims, l'excepció de "després"...) NO viuen ací -- viuen als loaders
de cada regla (`lexic.py`, `numerals.py`...) i s'apliquen soles la pròxima
vegada que s'instancie `RuleEngine`, així que després de sincronitzar
només cal tornar a córrer el benchmark (secció següent) per a confirmar
que no hi ha regressió.

## Com afegir dades noves

**Cas 1 -- una paraula o forma concreta (la majoria dels casos)**: no cal
tocar cap `.py`, és lookup de diccionari.

1. Edita el fitxer font que toque (`lexico_general_limpio.json`,
   `conjugaciones_limpio.json`, `verbos_no_ambiguos.json`,
   `numerales_limpio.json`, `acentuacion_limpio.json`,
   `posesivos_cat_val.json`) directament a `font_mauricio/`.
2. Corre `python -m traductor.sync_data` (vore dalt).
3. Corre el benchmark (secció següent) per a confirmar que no hi ha
   regressió.
4. Si una paraula concreta resulta ser un error del fitxer font (com
   "després", vore `lexic.py`), documenta l'exclusió al loader
   corresponent amb un comentari clar -- no la "arregles" editant el
   fitxer font a mà sense deixar rastre.

**Cas 2 -- un patró de sufix genuïnament PRODUCTIU** (com `accentuacio.py`/
`incoatius.py`, vore "DECISIÓ D'ARQUITECTURA"): açò sí és una regla nova,
no una entrada de diccionari -- però només quan un diccionari no pot
cobrir-ho per definició (el patró aplica a paraules que MAI estaran totes
enumerades). Confirma primer amb evidència real (benchmark, no teoria)
quines excepcions calen, i crea `traductor/rules/nombre_regla.py` amb la
mateixa interfície que la resta (`apply(tokens) -> tokens`, saltant
`is_translated`/`is_proper_noun`). Registra-la en `RuleEngine.__init__`
DESPRÉS de les 4 capes de diccionari (vore `engine.py`), perquè una forma
ja coneguda amb exactitud no ha de deixar-se reprocessar per una regla més
feble.

## Relació amb el sistema de regles antic

`03_seleccio_de_model/evalua_models.py` ja tenia un sistema de regles
(`tradueix_regles`, opció `--model regles`) — substitucions amb regex
sobre la frase completa. És distint i **no s'ha tocat ni substituït**: el
paquet `traductor/` s'afig com una opció nova, `--model traductor`, per a
poder comparar els dos directament en el mateix benchmark:

```bash
cd 03_seleccio_de_model
python evalua_models.py --model traductor                    # motor nou (traductor/)
python evalua_models.py --model regles                       # sistema antic (regex)
python evalua_models.py --model tots                          # tot a la vegada, inclosos els dos
```

L'adaptador (`tradueix_traductor_nou` en `evalua_models.py`) afig l'arrel
del repositori a `sys.path` abans d'importar `traductor/`, perquè
l'script sempre s'executa des de dins de `03_seleccio_de_model/` i
Python no troba ahí un paquet que viu en la carpeta del costat.

## Ús directe

```bash
python -m traductor.cli "Tinc huitanta anys i el meu amic francés parla."
# -> Tinc vuitanta anys i el meu amic francès parla.
```

```python
from traductor import translate
translate("Tinc huitanta anys.")  # -> "Tinc vuitanta anys."
```

## Testing

No hi ha una carpeta `tests/` — cada regla porta els seus propis doctests
reals (no només exemples il·lustratius) en el docstring de la seua
classe, i es verifiquen amb `doctest.testmod()`, no a ull. Per a córrer
els de tot el paquet d'una vegada:

```bash
python -c "
import doctest, importlib
modulos = [
    'traductor.rules', 'traductor.rules.lexic', 'traductor.rules.conjugacions_dict',
    'traductor.rules.possessius', 'traductor.rules.numerals', 'traductor.rules.concordanca_dos_dues',
    'traductor.rules.demostratius', 'traductor.rules.accentuacio', 'traductor.rules.incoatius',
    'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
