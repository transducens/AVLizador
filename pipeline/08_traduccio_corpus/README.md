*[Llegeix-ho en castellà](README.es.md)*

# Etapa 8 — Traducció de corpus complet amb el motor de regles

Aplica `traductor/` (el motor determinista de regles, etapa 5) a un
corpus **sencer**, document a document -- no a una sola frase solta (com
`python -m traductor.cli`) ni a les 150 frases ja curades a mà del
benchmark (`pipeline/03_seleccio_de_model/evalua_models.py --model traductor`).

## Per què cal una etapa a banda

Fins ara, cada vegada que es mesura si una regla nova (`concordanca_dos_dues.py`,
`relatiu_on.py`...) funciona bé, es mesura NOMÉS contra eixes 150 frases
-- i són frases triades precisament perquè contenen exemples clars dels
fenòmens dialectals documentats. Això diu si una regla és correcta, però
no diu **com es comporta sobre miles de frases reals sense seleccionar**,
que és on apareixeran els casos rars, les combinacions inesperades de
regles, o els fenòmens que el benchmark simplement no cobrix per atzar.

L'objectiu final (vore "El pla complet" baix) no és només tindre un
benchmark perfecte, és **poder confiar en el motor quan es traduïx un
corpus complet** -- i això només es pot comprovar traduint-ne un de
veres.

## Estructura

```
pipeline/08_traduccio_corpus/
├── traduccio_massiva.py   aplica traductor/ a un corpus .jsonl sencer
├── eixides/               fitxers generats (gitignored, regenerables)
└── postprocessat_llm/     fase 2 del pla (vía C, qwen3:8b), ja implementada i en ús (vore baix)
```

## Ús

```bash
cd pipeline/08_traduccio_corpus
python traduccio_massiva.py
# per defecte llig ../dades/avl/final/dialectal/corpus_occidental_net.jsonl
# i escriu eixides/corpus_traduit_regles.jsonl

python traduccio_massiva.py --limit 50          # només els primers 50 documents, per a proves
python traduccio_massiva.py --input altre.jsonl --camp-text cos --output eixides/prova.jsonl
```

Cada línia de l'eixida és `{"id", "text_occidental", "text_oriental_regles"}`.

## Limitacions conegudes (a propòsit, documentades, no arreglades encara)

- **Segmentació de frases simplificada**: `segmenta_frases()` separa per
  punt/interrogació/exclamació + espai. No gestiona abreviatures ("Dr.",
  "núm.") ni punts suspensius amb precisió -- una abreviatura pot tallar
  una frase pel mig. Necessari perquè `marca_noms_propis()` (vore
  `traductor/rules/__init__.py`) només eximix de sospita de nom propi la
  PRIMERA paraula de tot el que se li passa -- sense esta segmentació,
  la primera paraula de cada frase (2a, 3a...) d'un document es marcaria
  erròniament com a possible nom propi i es saltaria.
- **Un únic camp de text per document** (`--camp-text`, per defecte
  `"text"`): no combina `title` + `text`, no gestiona estructura HTML/
  Markdown dins del text.
- **Cap mecanisme d'etiquetatge ací mateix**: l'eixida d'este script
  només té el text traduït, no diu QUINES paraules o construccions són
  d'alta confiança (regla de lookup exacte) i quines són dubtoses o no
  s'han tocat. La fase 2 (vía C, vore baix) SÍ existix i funciona, però
  com a script a banda (`postprocessat_llm/benchmark_integrat.py`), no
  integrat encara dins d'este script ni dins de `traductor/` mateix.

## El pla complet (2 fases)

**Fase 1 -- esta carpeta (feta)**: traduir el corpus sencer amb el motor
de regles tal com està hui, pur determinista, sense cap LLM. Bona per a
casos d'alta confiança (lookup exacte, concordances inequívoques), però
sap que hi ha fenòmens gramaticals documentats a
`pipeline/02_regles_dialectals/docs_gramatica/` que NO pot resoldre amb seguretat
(p.ex. "per"→"per a", que depén de si té valor de causa o de finalitat --
vore `traductor/README.md`, secció "DECISIÓ D'ARQUITECTURA" 02/10/2026).

**Fase 2 -- `postprocessat_llm/` (IMPLEMENTADA i en ús actiu, actualitzat
14/10/2026)**: en compte d'intentar que el motor de regles ho resolga
tot (arriscat, com ja s'ha vist amb els intents d'heurística automàtica
de gènere), el problema es va dividir en dos: el motor de regles
tradueix, i un LLM revisa NOMÉS els punts concrets on el motor ha
decidit expressament no actuar per ambigüitat coneguda -- mai la frase
sencera. La versió que es va integrar de veres (**"vía C"**, classificar
entre 2 candidats ja coneguts, mai generar text nou) és un script
embolcall (`benchmark_integrat.py`) que replica les 9 regles per fora de
`traductor/`, no un canvi dins de la classe `Token` com es plantejava
originalment més avall -- un camí mes senzill i de menys risc que es va
acabar triant en la pràctica. **Rècord actual: qwen3:8b + vía C, 129/151
(85,4%) al benchmark val→cat**, confirmat en Abaco. Vore
`postprocessat_llm/README.md` per a tot el detall (per què vía C i no
A/B, les xifres de l'experiment, com llançar-ho de veres hui).

## `genera_muestra_test_dialectal.py` -- mostra de 200 frases per a test real

```bash
python genera_muestra_test_dialectal.py
# -> ../dades/boe_net/muestra_test_dialectal.json
```

Les 150 frases del benchmark (`pipeline/03_seleccio_de_model/benchmark_corpus.json`)
són curades a mà, pensades per a il·lustrar un fenomen dialectal cada una.
Esta mostra és distinta: 200 frases REALS del BOE (`dades/boe_net/`) on el
motor `traductor/` detecta de veres almenys un marcador (alguna de les 9
regles li canvia alguna cosa al traduir) -- pensada per a revisar i
corregir a mà i servir despres com a segon conjunt de test, sobre corpus
real en compte de frases ja triades per a demostrar cada regla.

**Com**: executa el motor regla a regla (mateix orde que `engine.py`),
comparant quins tokens passen a `is_translated` just despres de cada
`regla.apply()` -- no es pot saber per paraules clau perque les regles de
sufix (`accentuacio`, `incoatius`) i de concordança
(`concordanca_dos_dues`, `relatiu_on`) no son llistes de paraules.
**Estratificada per regla** (no mostreig pur a l'atzar, que eixiria
dominat per `demostratius`/`conjugacions_dict`): es reparteix el cupo
entre les 9 regles perquè la mostra servisca de test de totes, no només
de les mes freqüents.

Cada fila porta `texto_valenciano` (font), `texto_catalan_boe` (referencia
oficial, bon punt de partida per a corregir), `hipotesis_traductor`
(l'eixida actual del motor) i `reglas_disparadas` -- tot el que cal per a
comparar i corregir sense tornar a executar res.

Troballa real en generar-la: **`numerals` no es dispara ni una sola
vegada en les 260.345 frases del corpus** -- el seu patró (huit/vuit,
dinou/disset...) senzillament no apareix en prosa legal formal. No es un
error de l'script, és una dada real sobre quant de freqüent és cada
fenomen fora del benchmark curat.
