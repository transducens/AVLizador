*[Llegeix-ho en castellà](README.es.md)*

# Motor de regles determinista — etapa 5

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
relació amb cap regla dialectal (vore `../documentacion/metodologia_y_resultados.md`,
seccions 6 i 9).

La conversió occidental→oriental és, en la seua major part, un problema
**morfològic i lèxic determinista** (demostratius, possessius,
numerals...), no de traducció lliure. Un motor de regles no pot
al·lucinar: si una paraula no està en cap taula, senzillament no la toca.
Este paquet no substituïx el LLM (encara no cobrix ni de lluny totes les
regles documentades — vore "Què falta" més avall), però és una base
determinista, auditable i sense dependències, pensada per a:
- comparar directament contra el LLM en el mateix benchmark (`--model
  traductor` en `03_seleccion_de_modelo/evalua_models.py`, junt al `--model
  regles` ja existent — vore "Relació amb el sistema de regles antic"),
- servir de capa de post-processament/verificació sobre l'eixida del LLM,
- o, a mesura que crixca, substituir el LLM en els casos que ja cobrix amb
  garanties, deixant el LLM només per al genuïnament ambigu.

## Arquitectura

Pipeline seqüencial de capes sobre una llista de `Token`, no substitucions
de text sobre la frase sencera:

```
text ──tokenize()──▶ [Token, Token, ...] ──marca_noms_propis()──▶
    ──▶ LexicRule ──▶ DemostratiusRule ──▶ PossessiusRule ──▶ NumeralsRule
    ──▶ GentilicisRule ──▶ MorfologiaVerbalRule ──▶ LocucionsRule
    ──▶ PerfetRule ──▶ ElisioRule ──▶ detokenize() ──▶ text convertit
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
continue`). Sense açò, dos regles independents podrien trepitjar-se sense
que ningú se n'adonara — p.ex. la regla de possessius "arreglant" per
accident una paraula que ja havia tocat el lèxic. Amb un flag explícit,
l'orde de les capes queda documentat i cada una sap exactament què li
toca encara.

### Decisió de disseny: apòstrofs i guionets són part de la paraula

`tokenize()` tracta `d'escola`, `l'AVL` o `dir-li` com **un sol token**
cada un, no com a paraula+frontera. Separar-los al tokenitzador obligaria
a decidir el tall sense conéixer encara la regla gramatical que ho
justifica — eixa decisió es deixa a `elisio.py`, que és qui de veres sap
si `d'` s'ha de desfer o no. Com a contrapartida, `numerals.py` ha de
buscar la subcadena `"huit"` **dins** del token en lloc de fer un lookup
de paraula completa, perquè compostos com `cinquanta-huit` arriben com un
únic token.

**Conseqüència que va costar trobar (29/09/2026)**: eixa mateixa decisió
fa que un token com `d'este` mai coincidisca amb l'entrada `"este"` d'un
diccionari — el lookup exacte de `demostratius.py`, `lexic.py`,
`conjugacions_dict.py`, les taules de `morfologia_verbal.py` i els
diccionaris de `numerals.py` es quedaven sense traduir qualsevol paraula
enganxada a un prefix elidit (`d'este`, `s'oferisca`, `n'hagen`...).
`separa_prefix_elidit()` (`rules/__init__.py`) és el fix compartit: cada
regla de lookup exacte l'usa com a segon intent quan la cerca directa
falla, separant el prefix i buscant només la part real de la paraula.
Les regles basades en sufix (`gentilicis.py`, `perfet.py`) no el
necessiten: ja operaven amb `.sub()` sobre tot el token, que travessa
qualsevol prefix sense haver de separar-lo.

### Protecció de noms propis (`marca_noms_propis`)

S'executa una sola vegada, abans de la primera regla: marca
`is_proper_noun` en tota paraula capitalitzada que **no** siga la primera
del text (la primera lletra d'una frase sempre va en majúscula, siga o no
nom propi). És la mateixa heurística ja provada en
`03_seleccion_de_modelo/evalua_models.py::glossari_per_frase()`, afegida
allí després d'un incident real amb `blanca`/`Blanca` i `roig`/`Roig`
(vore `../documentacion/metodologia_y_resultados.md`, secció 6). Límit
conegut, heretat sense arreglar: un nom propi que és la **primera**
paraula del text mai es detecta.

## Orde de les regles, i per què

| # | Regla | Per què en esta posició |
|---|---|---|
| 1 | `lexic` | Lookup directe, la més "seca" — convé que corra abans que qualsevol regla morfològica toque la mateixa paraula per un altre motiu |
| 2 | `conjugacions_dict` | Ídem, però de formes verbals (font Mauricio/Apertium, 29/09/2026) — mateixa naturalesa que `lexic`, per això va justa després |
| 3 | `demostratius` | Patró tancat i sense ambigüitat, no interactua amb res més |
| 4 | `possessius` | Ídem |
| 5 | `numerals` | Ídem (inclou la concordança "dos/dues") |
| 6 | `gentilicis` | Regla de sufix general, però acotada per les excepcions "és"/"més" |
| 7 | `morfologia_verbal` | Fases 1, 2 i 6 (present indicatiu, present subjuntiu, incoatius); llista tancada per a 1/2, sufix amb excepcions per a 6 |
| 8 | `locucions` | Substitucions de frase fixa (`cap a on`, `dalt/baix de`) — no interactua amb res anterior |
| 9 | `perfet` | Genera una **frase** ("va passar"), no una paraula — millor després que tota la resta ja estiga resolta paraula per paraula |
| 10 | `elisio` | **Deliberadament l'última**: opera sobre el resultat ja transformat (`tok.translated`, no `tok.surface`) de la paraula següent. Si fóra abans, una regla posterior podria canviar eixa paraula i deixar l'elisió apuntant a una vocal/consonant que ja no hi és — és exactament el que diu la font (`../02_reglas_dialectales/reglas_dialectales_con_evidencia.md`, §11.2): "cal aplicar l'elisió cada vegada que una altra regla la dispara" |

**Bug real trobat en verificar este orde** (no només revisat a ull, amb
doctest de regressió en `elisio.py`): la primera implementació
d'`ElisioRule` mirava `tok.surface` de la paraula següent en lloc de
`tok.translated`. Amb `"de huitanta"`, `numerals.py` ja havia convertit
`huitanta→vuitanta` (comença per consonant, no elideix), però `elisio.py`
mirava la forma original `huitanta` (comença per h muda + vocal, sí
pareix elidir) i produïa `"d'vuitanta"`, incorrecte. Arreglat mirant
`tok.translated`; el cas queda com a test de regressió permanent.

## Cada regla, en una frase

- **`lexic.py`** — substitució directa via `traductor/data/lexico_fiable.json`
  (còpia de treball de `02_reglas_dialectales/lexico/lexico_fiable.json`,
  347 entrades). El JSON usa arrays paral·lels singular/plural
  (`["ametla","ametles"] → ["ametlla","ametlles"]`), no "una paraula,
  diverses alternatives" — només hi ha una excepció real de longituds
  distintes (`corder/corders → xai/be/anyell`), resolta agafant sempre el
  primer sinònim (documentat, no arreglat del tot: dona `corders→xai` en
  singular en lloc de plural). El 29/09/2026 es van incorporar 150
  entrades noves d'un diccionari català-valencià aportat per Mauricio
  (equip AVLizador, basat en l'apertium bilingüe), més els 3 parells
  solts que ja estaven documentats a la font però encara no implementats
  (`vindre→venir`, `valdre→valer` §4, `vos→us` §3) — vore
  `02_reglas_dialectales/lexico/font_mauricio/` per a les dades brutes i
  el criteri de filtratge exacte (excloent entrades `_PENDENT` sense
  verificar i conflictes amb entrades ja revisades a mà, que sempre
  guanyen).
- **`demostratius.py`** — este/esta/estos/estes→aquest...; eixe/eixa/eixos/eixes→aquest...
  (des del 28/09/2026 "eixe" es fusiona amb "este" cap a la mateixa forma
  oriental — l'oriental real ha col·lapsat el sistema de 3 graus a 2; vore
  `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` §1 per al
  raonament complet).
- **`possessius.py`** — meua/teua/seua (+ plurals) → meva/teva/seva. Només
  formes àtones femenines; masculines i tòniques no canvien (§2).
- **`conjugacions_dict.py`** — lookup exacte de 904 formes verbals (111
  verbs) del diccionari de Mauricio (equip AVLizador, apertium bilingüe,
  29/09/2026): cobrix alternances irregulars que `morfologia_verbal.py`
  no pot generalitzar per sufix (`oferisca→ofereixi`, `traure→treure`...).
  Exclou deliberadament les 65 formes marcades `problematica` a la font
  (valencià usa la mateixa forma per a indicatiu i subjuntiu en eixos
  casos, i sense pos-tagging no hi ha manera fiable de triar quina toca)
  — vore docstring del mòdul.
- **`numerals.py`** — quatre mecanismes independents: arrel `huit→vuit`
  (cerca de subcadena, amb `díhuit→divuit` com a excepció real resolta a
  banda), ordinals `-é→-è` (taula tancada, **no** regla de sufix
  genèrica — hi ha paraules com a préstecs acabats en -é que no són
  ordinals), concordança `dos/dues` (heurística feble: mira si la
  paraula següent acaba en "-a"/"-es"/"-ió"/"-ions" — este últim sufix
  afegit 29/09/2026, fiable perquè quasi cap nom acabat en "-ió" és
  masculí; fals negatiu conegut amb femenins que no acaben en cap d'estos,
  p.ex. "dos mans"), i arrels `dinou/disset` + els seus derivats en
  `-ena`/`-é` (taula tancada de 10 formes, afegida 29/09/2026 amb dades de
  Mauricio — no comparteixen subcadena amb l'oriental com sí fa
  `huit/vuit`). La concordança `dos/dues` també mira cap ARRERE
  (29/09/2026, cas real RC062) quan no hi ha cap paraula darrere de "dos"
  (típicament puntuació: `"...en dos: establir..."`) — "dos" ahí es
  referix anafòricament a un nom ja dit abans a la mateixa frase.
- **`gentilicis.py`** — sufix `-és→-ès`, sí com a regla general (300+
  lemes confirmats segons la font), amb les dos excepcions explícites de
  la font (`és` verb, `més` quantitat) que mai canvien, més una tercera
  trobada empíricament en córrer el benchmark complet: `"després"`
  (adverbi) es trencava en `"desprès"` — la font només donava 2
  excepcions, no és una llista exhaustiva.
- **`morfologia_verbal.py`** — **fase 1** (present indicatiu, 1a persona,
  1a conjugació: parle→parlo...) i **fase 2** (present subjuntiu, "jo"/
  "ells": puga→pugui, tinguen→tinguin...), totes dos com a llista tancada
  i no regla de sufix genèrica: massa paraules catalanes acaben en "-e"/
  "-a"/"-en" sense ser eixes formes verbals concretes. **Fase 6**
  (incoatius -ix→-eix: establix→estableix) sí és regla de sufix, perquè
  la font ho documenta com a patró general — porta llista negra
  (`baix`, `calaix`, `dibuix`, `guix`) per a no tocar paraules reals que
  acaben igual sense ser verbs. Fases 3-5 (imperfet de subjuntiu,
  imperfet d'indicatiu, participi de "ser") documentades com a TODO
  explícit dins del propi fitxer, amb la raó de per què cada una
  necessita més cura abans d'implementar-se.
- **`locucions.py`** — dos patrons: `cap a on→cap on` (substitució
  literal) i `dalt de/baix de→a dalt de/a baix de` (prefix, amb majúscula
  gestionada a mà com a `perfet.py`). "per a→per" davant d'infinitiu es va
  provar i **retirar**: l'auditoria del benchmark real (28/09/2026) va
  trobar que de 17 aparicions de "per a + infinitiu", cap la reduïx a
  "per" — sempre es manté "per a" (vore
  `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` §7.1).
  Pendents, documentats però NO implementats ací (§7.2 de la font): "a
  on"/"on" segons ubicació estàtica o direcció, i "en"→"a" en
  construccions locatives (este últim, a més, contradiu una protecció ja
  existent al system prompt de l'LLM — pendent de confirmar l'abast exacte
  abans de tocar-lo).
- **`perfet.py`** — pretèrit perfet simple → perifràstic, només 1a
  conjugació (`-ar`). Reconstruïx l'infinitiu llevant la terminació i
  afegint "-ar". Abast retallat amb dades reals, no només teoria: en
  córrer el benchmark complet, les terminacions curtes `-í` i `-ares` van
  donar **0 encerts i 7 falsos positius** (`llatí`, `així`, `pares`,
  `clares`...) — es van llevar del tot. `-à` i `-aren` sí tenen encerts
  reals confirmats (`celebrà`, `passà`, `quedaren`) i es queden, amb una
  llista negra per als seus propis falsos positius confirmats (`està`,
  `valencià`, `castellà`, `català`).
- **`elisio.py`** — `de/la/el → d'/l'` davant de vocal real o *h* muda.
  Mai duplica una elisió que ja vinguera feta en l'original (eixes
  arriben com un únic token des de `tokenize()`, mai coincidixen amb
  "de"/"la"/"el" solts). Excepció confirmada (29/09/2026): `la` (mai
  `el`/`de`) no elideix mai davant de paraula que comença per `i`/`u`
  (`la intenció`, `la universitat`, mai `l'intenció`/`l'universitat`) —
  convenció ortogràfica per a no perdre la distinció de gènere en la
  lectura, no un fenomen fonètic; de pas resol com a efecte lateral el
  cas `la iaia` que abans es documentava ací com a diftong semiconsonàntic
  sense arreglar.

## Què falta (buits coneguts, no una promesa del que es farà)

Regles que **sí estan documentades** en `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` però que
**cap** fitxer de `traductor/` cobrix encara:

| Secció de la font | Contingut | On encaixaria |
|---|---|---|
| §5.3-§5.5 | Imperfet de subjuntiu, imperfet d'indicatiu, participi de "ser" | Documentat fase a fase dins de `morfologia_verbal.py`, vore el fitxer (fases 1/2/6 ja implementades) |
| §7.2 | `hui→avui`, `vesprada→tarda`... (parells lèxics solts, no els de `locucions.py`) | Candidats a `lexico_fiable.json`, mateix criteri que §3/§4 (ja resolts, vore baix) |
| §7.1 | `per a`→`per` davant d'infinitiu | **Provat i retirat**: contradit per 17/17 casos del benchmark real, sempre es manté "per a" |
| §7.2 | `a on`→`on`/`a on` (estàtic/direcció), `en`→`a` (locatiu) | Pendents de confirmar — vore `locucions.py`, ja cobrix la resta de patrons d'esta secció |
| §11.3 | `al + infinitiu → en + infinitiu` | La pròpia font ho marca com a "pendent de confirmar" (2/2 però mostra insuficient) — no implementar sense més evidència |
| — | Topònims (`Ademuz→Ademús`, `Alcublas→les Alcubles`...) | 73 parells al diccionari de Mauricio (`tipo: "v:top_gva"`), NO incorporats: el motor protegix tots els noms propis de traducció (`is_proper_noun`, vore §"Protecció de noms propis" dalt), així que encara que s'afigueren a `lexico_fiable.json` mai s'aplicarien. Cal decidir primer si els topònims han de traduir-se en absolut i, si sí, com distingir-los d'altres noms propis que mai s'han de tocar — vore les dades brutes a `02_reglas_dialectales/lexico/font_mauricio/lexico_general_limpio.json` |

**Resolt el 29/09/2026** (documentat ací abans, ara ja implementat): §3
Pronoms personals (`vos→us`) i §4 Infinitius irregulars (`traure→treure`
i `sigut→estat` §5.5 venen del diccionari de conjugacions de Mauricio,
via `conjugacions_dict.py`; `tindre→tenir`, `vindre→venir`, `vore→veure`,
`eixir→sortir`, `valdre→valer` i `vos→us` són a `lexico_fiable.json`) —
tots eren parells solts, no patrons productius, tal com ja preveia este
mateix README.

Patró general: qualsevol cosa que siga "un parell de paraules concret"
(no un sufix o patró productiu) encaixa millor en el lèxic que en una
regla nova — és el mateix criteri que ja va usar la font per a
`vosté/vostés`.

## Com afegir una regla nova

1. Confirma la taula/patró en `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md`
   — **mai la inventes**; si la font no la confirma amb evidència, no
   s'implementa (vore com es van documentar els buits de dalt).
2. Decidix: és un patró productiu (sufix/regla general) o un grapat de
   parells solts? Els parells solts van a `lexico_fiable.json`, no a un
   fitxer nou.
3. Si és un patró nou, crea `traductor/rules/nombre_regla.py` amb la
   mateixa interfície que totes les altres:
   ```python
   class NombreReglaRule:
       def apply(self, tokens: list[Token]) -> list[Token]:
           for tok in tokens:
               if tok.is_translated or tok.is_proper_noun:
                   continue
               # lògica ací
           return tokens
   ```
4. Si la regla necessita mirar tokens veïns (com `elisio.py` o la
   concordança de `numerals.py`), itera per índex, no per valor — però
   la firma pública seguix sent `apply(tokens) -> tokens`.
5. Afig doctests reals en el docstring (no només descripció) — és
   l'única suite de tests d'este paquet. Executa:
   ```bash
   python -c "import doctest, traductor.rules.nombre_regla as m; print(doctest.testmod(m))"
   ```
   (`python -m doctest fichero.py` **no** funciona ací pels imports
   relatius del paquet — usa l'import de dalt.)
6. Registra-la en `RuleEngine.__init__` (`traductor/rules/engine.py`), en
   el punt de l'orde que li corresponga, i documenta el perquè en la
   taula d'"Orde de les regles" d'este README.
7. Si alguna cosa és lingüísticament ambigua (és esta forma valenciana o
   ja oriental? aplica sempre o depén d'un context que no podem vore
   sense spaCy?), comenta-ho amb `# AMBIGÚ:` explicant el perquè — no ho
   resolgues endevinant.

## Relació amb el sistema de regles antic

`03_seleccion_de_modelo/evalua_models.py` ja tenia un sistema de regles
(`tradueix_regles`, opció `--model regles`) — substitucions amb regex
sobre la frase completa. És distint i **no s'ha tocat ni substituït**: el
paquet `traductor/` s'afig com una opció nova, `--model traductor`, per a
poder comparar els dos directament en el mateix benchmark:

```bash
cd 03_seleccion_de_modelo
python evalua_models.py --model traductor                    # motor nou (traductor/)
python evalua_models.py --model regles                       # sistema antic (regex)
python evalua_models.py --model tots                          # tot a la vegada, inclosos els dos
```

L'adaptador (`tradueix_traductor_nou` en `evalua_models.py`) afig l'arrel
del repositori a `sys.path` abans d'importar `traductor/`, perquè
l'script sempre s'executa des de dins de `03_seleccion_de_modelo/` i
Python no troba ahí un paquet que viu en la carpeta del costat.

## Ús directe

```bash
python -m traductor.cli "Este xiquet mira la meua obra i vaig ser el cinqué de huitanta."
# -> Aquest nen mira la meva obra i vaig ser el cinquè de vuitanta.
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
    'traductor.rules.demostratius', 'traductor.rules.possessius', 'traductor.rules.numerals',
    'traductor.rules.gentilicis', 'traductor.rules.morfologia_verbal', 'traductor.rules.locucions',
    'traductor.rules.perfet', 'traductor.rules.elisio', 'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
