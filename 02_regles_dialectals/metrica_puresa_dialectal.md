# Índex de Puresa Dialectal (IPD)

> **Estat: proposta de disseny, encara no implementada.** Este document
> especifica la mètrica perquè es puga revisar i estudiar la seua
> viabilitat abans d'escriure cap codi. Les taules de marcadors que
> reutilitza (`traductor/rules/*.py`) encara estan en evolució — s'aniran
> ampliant/corregint amb el temps, i esta mètrica hereta eixos canvis
> automàticament en tornar-se a calcular.

## 1. Què mesura

Un score **bidireccional** de fins a quin punt un text s'ajusta a la
variant dialectal que se suposa que té (occidental o oriental), basat en
la presència de marcadors de l'altra variant. No mesura "correcció
normativa" (castellanismes, barbarismes) — això seria un eix distint, no
cobert per l'IPD. L'IPD només respon una pregunta: *este text que diu ser
valencià occidental, té de veres marcadors catalans orientals colats a
dins (o al revés)?*

Generalitza el mecanisme que ja fa servir `01_extraccio_i_neteja/estudi_dialectal.py`
(ratio de marcadors occidentals/orientals per a classificar documents AVL),
convertint-lo en:
- Una funció reutilitzable des de qualsevol corpus (AVL, BOE, sintètic),
  no només des del pipeline de classificació AVL.
- Un score continu (0-1) en compte de només una classificació en bins.
- Basat en un diccionari de marcadors molt més ampli: les 38 regles
  dialectals ja documentades i codificades a `traductor/rules/`, no la
  llista curta i hardcodejada que usa hui `estudi_dialectal.py`.

## 2. Terminologia

| Terme | Què és |
|---|---|
| **IPD** (Índex de Puresa Dialectal) | El nom de la mètrica, per a citar-la en informes/documentació (taules junt a BLEU/chrF) |
| `puresa_dialectal` | El camp/variable al codi i als JSON de sortida — el score en si, 0-1 |
| `contaminacio_creuada` | El seu complementari, `1 - puresa_dialectal`, també disponible com a camp de sortida |

## 3. Fonts de dades (marcadors)

No es curen dades noves: es reutilitza tot el que ja existix i ja està
validat, repartit en 3 fonts:

### 3a. `traductor/rules/*.py` — 38 regles ja codificades

| Fitxer | Aportació | Tipus de marcador |
|---|---|---|
| `demostratius.py` | 8 parells literals (`este→aquest`, `eixe→aquest`...) | Lookup exacte |
| `possessius.py` | 6 parells literals (`meua→meva`...) | Lookup exacte |
| `morfologia_verbal.py` (fases 1 i 2) | 12 parells literals (`parle→parlo`, `puga→pugui`, `tinguen→tinguin`...) | Lookup exacte |
| `morfologia_verbal.py` (fase 6) | Sufix `-ix→-eix`, amb excepcions `{baix, calaix, dibuix, guix}` | Regla de sufix (regex) |
| `numerals.py` (ordinals) | 14 parells literals (`cinqué→cinquè`...) | Lookup exacte |
| `numerals.py` (arrel huit/vuit) | `huit↔vuit` | Lookup exacte — el tokenitzador de `estudi_dialectal.py` ja separa per guionet, així que `cinquanta-huit` arriba com dos tokens i no cal lògica de subcadena |
| `gentilicis.py` | Sufix `-és→-ès`, amb excepcions `{és, més, després}` ja depurades empíricament | Regla de sufix (regex) |
| `perfet.py` | Sufixos `-à/-aren/-àrem/-àreu` (occidental), amb llista negra `{està, valencià, català, castellà}` ja depurada | Regla de sufix (regex), **només aporta marcador occidental** (vore exclusions, §4) |
| `locucions.py` | `cap a on`/`dalt de`/`baix de` (occidental) vs `cap on`/`a dalt de`/`a baix de` (oriental) | Lookup exacte multi-paraula |

**Nota (28/09/2026, canvi de decisió sobre "eixe")**: `demostratius.py` ara
tradueix `eixe→aquest` en compte de `eixe→aqueix` (vore
`reglas_dialectales_con_evidencia.md` §1 per al raonament — l'oriental
contemporani ha col·lapsat el 2n grau cap al 1r). Efecte sobre l'IPD:
"aqueix" ja no isca d'esta taula com a marcador oriental exclusiu. Com que
"aqueix" seguix sent vocabulari real i exclusivament oriental (encara que
rar), es podria afegir com a marcador solt a banda (no des d'un parell de
traducció, sinó com a entrada independent) si en la implementació es vol
recuperar eixe senyal — decisió pendent, no crítica per a la viabilitat.

### 3b. `lexico_fiable.json` (194 entrades)

Parells valencià↔català reals més enllà de la morfologia (p.ex.
`ametla/ametles → ametlla/ametlles`), amb la mateixa estructura que
`demostratius.py`. S'afigen com a lookup exacte addicional.

### 3c. `OCCIDENTAL_MARKERS`/`ORIENTAL_MARKERS` d'`estudi_dialectal.py`

Els ~54 marcadors lèxics que ja existixen hui (`xiquet/nen`, `hui/avui`,
`faena/feina`, `dacsa/blat de moro`...) — arrels de paraula distintes, no
alternances morfològiques, així que complementen (no dupliquen) les fonts
3a/3b.

## 4. Què queda fora, i per què

| Exclòs | Motiu |
|---|---|
| `numerals.py` — concordança dos/dues | "dos" també és vàlid en oriental per a masculí; comptar-lo com a marcador occidental donaria molts falsos positius |
| `perfet.py` — el costat oriental (`va/van/vam/vau`) | "va" és una paraula freqüent en TOT el català, no un marcador dialectal fiable per si sola. Esta regla només aporta senyal occidental, i està bé que siga asimètrica |
| `elisio.py` | No és una substitució paraula→paraula sinó inserció d'apòstrof segons context fonètic — no encaixa en un mecanisme de recompte per token |

## 5. Mecanisme de recompte

Reutilitza `count_markers_combined()` d'`estudi_dialectal.py` tal qual
(indexació per primera paraula + coincidència *greedy* de més llarga a més
curta, per a no comptar dos vegades un marcador contingut dins d'un altre
més llarg), ampliada amb una passada extra per als 2 marcadors basats en
regex (gentilicis, perfet) sobre els tokens que no hagen fet ja match
literal.

## 6. Fórmules

Per a un text `T` que se suposa de la variant `V` (occidental o oriental):

```
occ_count = Σ ocurrències de marcadors occidentals (lookup literal + regex gentilicis/perfet)
or_count  = Σ ocurrències de marcadors orientals (lookup literal + regex gentilicis)
denom     = occ_count + or_count
```

**Puresa dialectal:**
```
                  ⎧ occ_count / denom       si V = occidental
puresa_dialectal = ⎨
                  ⎩ or_count  / denom       si V = oriental
```

**Contaminació creuada (complementari):**
```
contaminacio_creuada = 1 - puresa_dialectal
```

**Condició de fiabilitat (nou respecte al codi actual):**
```
si denom < min_marcadors (per defecte 3):
    puresa_dialectal = None   # "no_determinat", sense prou senyal
```
`estudi_dialectal.py` hui només exigix `denom > 0` (almenys 1 marcador).
Amb textos curts (frases soltes del BOE, per exemple, en compte de
documents complets com als de l'AVL), un únic marcador pot ser soroll —
per això es proposa pujar l'exigència mínima a 3.

**Bins opcionals** (per a mantindre compatibilitat amb la classificació en
categories que ja usa `estudi_dialectal.py`, si es vol seguir mostrant-los
junt al score continu):

| `puresa_dialectal` (per a V=occidental) | Categoria |
|---|---|
| ≥ 0,80 | `occidental_clar` |
| ≥ 0,60 | `occidental_predominant` |
| ≥ 0,40 | `mixt` |
| ≥ 0,20 | `oriental_predominant` |
| < 0,20 | `oriental_clar` |

(Mateixos talls que ja usa `classify()` hui — no hi ha motiu per a
canviar-los, ja estan calibrats a ull sobre el corpus AVL real.)

## 7. On s'aplicaria

1. **Corpus AVL** — recalcular la classificació ja existent amb el
   diccionari de marcadors ampliat (més cobertura que hui).
2. **BOE** — cas ideal: el mateix document oficial existix en suplement
   valencià i suplement català a la vegada. Aplicar l'IPD al costat
   "valencià" hauria de donar `puresa_dialectal` pròxim a 1 si la
   traducció oficial és fidel al valencià normatiu.
3. **Corpus sintètic** — comprovar el costat "oriental" (traduït) per
   residus occidentals, donant un score continu en compte del flag binari
   `no_traduit` que ja existix hui a `motius_sospita`.

Eixida: score per document/frase, i agregat per font/`doc_type` (mitjana +
distribució) — permet respostes com "el supl. valencià del BOE té una
contaminació oriental mitjana del 2%".

## 8. Limitacions conegudes

1. Cobertura limitada als marcadors documentats (38 regles + lèxic
   existent) — contaminació per formes no catalogades no es detecta.
2. Textos molt curts poden no tindre cap marcador encara que
   `denom >= min_marcadors` es complisca just al límit — el score seria
   estadísticament fràgil amb pocs marcadors (3-4).
3. Cal heretar les exclusions ja depurades a `traductor/rules/`
   (homògrafs, excepcions) per a no introduir falsos positius que eixos
   mòduls ja van haver de resoldre amb evidència real.
4. Les taules de `traductor/rules/` estan en evolució activa — cada
   ampliació/canvi ahí recalcula silenciosament l'IPD de tots els corpus
   ja mesurats; no hi ha versionat encara d'esta mètrica per fixar "amb
   quina versió del diccionari es va calcular tal número".

## 9. Pròxim pas

Exposar com a constants públiques (sense guionet baix) les taules internes
de `traductor/rules/demostratius.py`, `possessius.py`,
`morfologia_verbal.py`, `numerals.py`, `gentilicis.py` i `perfet.py`, i
crear `traductor/marcadors_dialectals.py` amb la implementació de les
fórmules d'este document.
