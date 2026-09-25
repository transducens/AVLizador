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
    ──▶ GentilicisRule ──▶ MorfologiaVerbalRule ──▶ PerfetRule ──▶ ElisioRule
    ──▶ detokenize() ──▶ text convertit
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
| 2 | `demostratius` | Patró tancat i sense ambigüitat, no interactua amb res més |
| 3 | `possessius` | Ídem |
| 4 | `numerals` | Ídem (inclou la concordança "dos/dues") |
| 5 | `gentilicis` | Regla de sufix general, però acotada per les excepcions "és"/"més" |
| 6 | `morfologia_verbal` | Només fase 1 (present indicatiu); llista tancada, sense risc d'interacció |
| 7 | `perfet` | Genera una **frase** ("va passar"), no una paraula — millor després que tota la resta ja estiga resolta paraula per paraula |
| 8 | `elisio` | **Deliberadament l'última**: opera sobre el resultat ja transformat (`tok.translated`, no `tok.surface`) de la paraula següent. Si fóra abans, una regla posterior podria canviar eixa paraula i deixar l'elisió apuntant a una vocal/consonant que ja no hi és — és exactament el que diu la font (`../02_reglas_dialectales/reglas_dialectales_con_evidencia.md`, §11.2): "cal aplicar l'elisió cada vegada que una altra regla la dispara" |

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
  194 entrades; **provisional**, a l'espera del lèxic complet). El JSON
  usa arrays paral·lels singular/plural (`["ametla","ametles"] → ["ametlla","ametlles"]`),
  no "una paraula, diverses alternatives" — només hi ha una excepció real
  de longituds distintes (`corder/corders → xai/be/anyell`), resolta
  agafant sempre el primer sinònim (documentat, no arreglat del tot: dona
  `corders→xai` en singular en lloc de plural).
- **`demostratius.py`** — este/esta/estos/estes→aquest...; eixe/eixa/eixos/eixes→aqueix...
  Taula copiada literal de `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` §1.
- **`possessius.py`** — meua/teua/seua (+ plurals) → meva/teva/seva. Només
  formes àtones femenines; masculines i tòniques no canvien (§2).
- **`numerals.py`** — tres mecanismes independents: arrel `huit→vuit`
  (cerca de subcadena, amb `díhuit→divuit` com a excepció real resolta a
  banda), ordinals `-é→-è` (taula tancada, **no** regla de sufix
  genèrica — hi ha paraules com a préstecs acabats en -é que no són
  ordinals), i concordança `dos/dues` (heurística feble: mira si la
  paraula següent acaba en "-a"/"-es"; fals negatiu conegut amb femenins
  que no acaben així, p.ex. "dos mans").
- **`gentilicis.py`** — sufix `-és→-ès`, sí com a regla general (300+
  lemes confirmats segons la font), amb les dos excepcions explícites de
  la font (`és` verb, `més` quantitat) que mai canvien, més una tercera
  trobada empíricament en córrer el benchmark complet: `"després"`
  (adverbi) es trencava en `"desprès"` — la font només donava 2
  excepcions, no és una llista exhaustiva.
- **`morfologia_verbal.py`** — **només fase 1** (present indicatiu, 1a
  persona, 1a conjugació: parle→parlo...), a propòsit com a llista
  tancada i no regla de sufix `-e→-o`: massa paraules catalanes acaben en
  "-e" sense ser verbs en primera persona. Fases 2-6 (subjuntiu
  present/imperfet, imperfet d'indicatiu, participi de "ser",
  incoatius) documentades com a TODO explícit dins del propi fitxer, amb
  la raó de per què cada una necessita més cura abans d'implementar-se.
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
  "de"/"la"/"el" solts). Limitació coneguda i documentada, no arreglada:
  no distingix diftongs semiconsonàntics (`la iaia`, no `l'iaia` — este
  motor sí elidiria malament ahí).

## Què falta (buits coneguts, no una promesa del que es farà)

Regles que **sí estan documentades** en `../02_reglas_dialectales/reglas_dialectales_con_evidencia.md` però que
**cap** fitxer de `traductor/` cobrix encara:

| Secció de la font | Contingut | On encaixaria |
|---|---|---|
| §3 Pronoms personals | `vos→us` | És un únic parell, no un patró productiu — millor com a entrada de `lexico_fiable.json` (mateix criteri que `vosté/vostés`, §8 de la font) que com a regla nova |
| §4 Infinitius irregulars | `traure→treure`, `tindre→tenir`, `vindre→venir`, `vore→veure`, `eixir→sortir`, `valdre→valer` | Ídem — són 6 parells solts, no un sufix generalitzable |
| §5.2-§5.6 | Resta de morfologia verbal | Documentat fase a fase dins de `morfologia_verbal.py`, vore el fitxer |
| §5.5 | `sigut→estat` (participi de "ser") | Encara que la font ho classifica com a morfologia verbal, és un únic parell irregular — candidat a `lexico_fiable.json` igual que §3/§4 |
| §7 Adverbis/locucions | `a on→on`, `hui→avui`, `vesprada→tarda`... | Parells solts, mateix criteri |
| §11.3 | `al + infinitiu → en + infinitiu` | La pròpia font ho marca com a "pendent de confirmar" (2/2 però mostra insuficient) — no implementar sense més evidència |

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
    'traductor.rules', 'traductor.rules.lexic', 'traductor.rules.demostratius',
    'traductor.rules.possessius', 'traductor.rules.numerals', 'traductor.rules.gentilicis',
    'traductor.rules.morfologia_verbal', 'traductor.rules.perfet', 'traductor.rules.elisio',
    'traductor.rules.engine', 'traductor.translate',
]
for nom in modulos:
    m = importlib.import_module(nom)
    r = doctest.testmod(m)
    print(nom, r)
"
```
