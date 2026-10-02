*[Llegeix-ho en castellà](README.es.md)*

# Etapa 8 — Traducció de corpus complet amb el motor de regles

Aplica `traductor/` (el motor determinista de regles, etapa 5) a un
corpus **sencer**, document a document -- no a una sola frase solta (com
`python -m traductor.cli`) ni a les 150 frases ja curades a mà del
benchmark (`03_seleccio_de_model/evalua_models.py --model traductor`).

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
08_traduccio_corpus/
├── traduccio_massiva.py   aplica traductor/ a un corpus .jsonl sencer
├── eixides/               fitxers generats (gitignored, regenerables)
└── postprocessat_llm/     fase 2 del pla, encara NO implementada (vore baix)
```

## Ús

```bash
cd 08_traduccio_corpus
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
- **Cap mecanisme d'etiquetatge encara**: l'eixida només té el text
  traduït, no diu QUINES paraules o construccions són d'alta confiança
  (regla de lookup exacte) i quines són dubtoses o no s'han tocat. Això
  és la fase 2 del pla (vore baix) -- a propòsit encara no implementat.

## El pla complet (2 fases)

**Fase 1 -- esta carpeta (feta)**: traduir el corpus sencer amb el motor
de regles tal com està hui, pur determinista, sense cap LLM. Bona per a
casos d'alta confiança (lookup exacte, concordances inequívoques), però
sap que hi ha fenòmens gramaticals documentats a
`02_regles_dialectals/docs_gramatica/` que NO pot resoldre amb seguretat
(p.ex. "per"→"per a", que depén de si té valor de causa o de finalitat --
vore `traductor/README.md`, secció "DECISIÓ D'ARQUITECTURA" 02/10/2026).

**Fase 2 -- `postprocessat_llm/` (pendent, NO implementada)**: en compte
d'intentar que el motor de regles ho resolga tot (arriscat, com ja s'ha
vist amb els intents d'heurística automàtica de gènere), el pla és
**etiquetar** dins de `traductor/` els casos on una regla és dubtosa o on
cap regla actua però se sap que hi pot haver una diferència dialectal, i
que un model de llenguatge revise NOMÉS eixos punts marcats -- no tota la
frase -- usant les guies de `docs_gramatica/` com a referència. Encara
s'ha de decidir:
- Quin format tindrà la marca (al nivell de `Token`? de frase sencera?).
- Quin model LLM (local via Ollama, com la resta del projecte, o un altre).
- Si el LLM proposa un canvi o nomes senyala per a revisió humana.

Vore `postprocessat_llm/README.md` per a l'estat d'esta decisió.
