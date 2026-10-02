*[Llegeix-ho en castellà](README.es.md)*

# Post-processat amb LLM dels casos marcats (PENDENT -- no implementat)

Esta carpeta encara no conté codi. Documenta la decisió d'arquitectura
presa el 02/10/2026: en compte de forçar el motor de regles a resoldre
TOT (arriscat -- cada vegada que s'ha provat una heurística automàtica
massa àmplia en este projecte, de l'escaneig de gènere a
`flexio_genere_avl.json` a la distinció "per"/"per a", el resultat ha
sigut pitjor que no tocar-ho), el pla és dividir el problema en dos:

1. **El motor de regles (`traductor/`) tradueix i, de pas, marca** els
   punts on no té prou confiança -- sense intentar adivinar-los.
2. **Un LLM revisa NOMÉS eixos punts marcats**, amb el context de la
   frase i les guies de `../../02_regles_dialectals/docs_gramatica/`
   (GEIEC/GNV completes + les comparatives dialectals derivades) com a
   referència normativa -- no tota la frase de zero, com fan les etapes
   3-4 amb el corpus sintètic actual.

## Per què així i no d'una altra manera

L'alternativa (un LLM que revisa/corregix la frase sencera) ja existix en
este projecte: és exactament el que fan les etapes 3-4
(`03_seleccio_de_model/`, `04_corpus_sintetic/`) amb qwen2.5:14b. Eixe
enfocament funciona raonablement bé (BLEU ~93) però **al·lucina** -- la
revisió manual va trobar ~20% d'errors reals sense relació amb cap regla
dialectal (vore `../../documentacio/metodologia_i_resultats.md`, seccions
6 i 9). L'interés d'un motor de regles és precisament que no pot
al·lucinar: si no sap una paraula, no la toca. Mantindre eixa propietat
vol dir que el LLM només ha d'intervindre a on el motor ho demane
explícitament, no sobre el text sencer.

## El que falta decidir abans d'escriure cap codi

- **Format de la marca**: a nivell de `Token` (afegir un camp com
  `necessita_revisio: bool` o `candidat_regla: str | None` a la classe
  `Token` de `traductor/rules/__init__.py`), a nivell de frase sencera, o
  tots dos. Encara no decidit -- no tocar `Token` fins que es decidisca.
- **Quines regles etiquegen i quan**: per exemple, una futura regla per a
  "per"/"per a" podria NO decidir, i en compte d'això marcar el token
  "per" com a candidat quan detecte el patró ambigu (vore
  `traductor/README.md`, secció "DECISIÓ D'ARQUITECTURA" 02/10/2026, per
  als 3 casos ja identificats com a massa arriscats per a una regla
  directa).
- **Quin model**: local via Ollama (coherent amb la resta del projecte,
  qwen2.5:14b ja en ús) o un altre -- pendent de provar cost/qualitat
  sobre una mostra xicoteta de casos marcats abans de triar.
- **El LLM proposa o nomes senyala**: si l'eixida del LLM substituïx
  directament el text marcat, o si nomes genera un informe per a revisió
  humana (més lent, però cap risc d'al·lucinació silenciosa sobre dades
  ja marcades com a dubtoses).

## Com continuar quan es retome

1. Decidir el format de marca i afegir-lo a `Token` + a, almenys, una
   regla real (candidat natural: la distinció "per"/"per a" documentada
   a `docs_gramatica/guia_traduccio_dialectal.md`, bloc C2).
2. Executar `../traduccio_massiva.py` sobre un corpus real i comptar
   quants punts queden marcats -- això dona una primera idea del volum
   real abans de triar model ni dissenyar el prompt.
3. Provar el LLM triat sobre una mostra xicoteta dels punts marcats,
   mateix mètode que la resta del projecte: evidència abans que
   implementació completa.
