*[Llegeix-ho en castellà](README.es.md)*

# Regles passades al model — documentació per a revisió

Esta carpeta reunix, en text pla fàcil de llegir, **tot allò que de veres
se li diu al model** en generar el corpus sintètic — per a poder
revisar-ho i detectar errors sense haver d'anar a buscar strings de Python
dins de dos fitxers distints.

| Fitxer | Què conté |
|---|---|
| [`guia_dialectal_valencia_catala.md`](guia_dialectal_valencia_catala.md) | **Comença per ací.** Document purament lingüístic: les diferències dialectals entre valencià i català explicades amb exemples (com un tema de llibre), sense res de codi ni d'anàlisi del corpus. La secció 9 (lèxic) té com a base les 368 formes que Apertium marca explícitament com a valencianes (no la llista curada de ~1.600) — d'elles, 68 tenen parella catalana confirmada dins del propi diccionari i 3 queden pendents de determinar, sense traducció inventada. |
| [`lexic_per_frequencia.md`](lexic_per_frequencia.md) | **Per a revisar ràpid, usa açò en lloc del JSON cru.** Les 472 paraules del lèxic que de veres s'usen al corpus, ordenades per quantes vegades apareixen — de més a menys impacte real. Les 1.020 paraules restants (68% del lèxic) no apareixen ni una vegada al corpus actual. |
| [`system_prompt.md`](system_prompt.md) | El system prompt literal (regles de demostratius, possessius, subjuntiu, numerals, lèxic base...) tal com se li passa al model, més la regla 8 (sigles/noms propis) afegida només per al corpus. |
| [`glossari_dinamic.md`](glossari_dinamic.md) | Com es construïx la pista `[VOCABULARI: ...]` que s'afig a cada frase, les llistes d'exclusió completes, i la llista d'entrades del lèxic que col·lisionen amb paraules comunes (amb quines ja estan arreglades i quines no). |

## Flux de treball

1. Mana a revisar (o revisa tu mateix) `guia_dialectal_valencia_catala.md`
   — és el document lingüístic pur, sense referències a codi ni al
   corpus generat.
2. Amb les correccions/confirmacions en mà, dis-me quins canvis aplicar
   — es porten a `evalua_models.carrega_lexic()` (codi) i/o a
   `palabras_traducidas.json` (dades), i després s'actualitza també
   `system_prompt.md`/`glossari_dinamic.md` perquè esta carpeta no quede
   desactualitzada.
3. Si vols que les correccions també s'apliquen al corpus ja
   generat (no només a futures generacions), s'amplia
   `04_corpus_sintetic/repara_corpus.py` amb les noves reversions. L'
   anàlisi de què falla al corpus viu a banda, en
   `../../dades/sintetico/analisi_corpus.html` i en les revisions
   manuals — no en esta carpeta.

## Relació amb la resta del projecte

- El text d'estos documents **no s'edita ací** — estan copiats de
  `03_seleccio_de_model/evalua_models.py` i `04_corpus_sintetic/genera_corpus_sintetico.py`.
  Si decidixes canviar una regla, el canvi real es fa en eixos fitxers de
  codi; torna a copiar el text actualitzat ací després perquè esta
  carpeta no quede desactualitzada.
- El lèxic que usa de veres el pipeline és
  `../lexico/lexico_fiable.json` (194 entrades revisades a mà) — ja no
  `palabras_traducidas.json`, que es va retirar per tindre entrades sense
  revisar d'origen poc fiable. Afegir paraules noves: editant eixe JSON directament.
- El lèxic antic (per a seguir traent paraules confirmades d'ahí) i el
  llistat combinat més ampli (Apertium + llista curada + lèxic del
  corpus) estan en `../lexico/` (vore el README general de
  `02_regles_dialectals/`).
- Les regles morfològiques "de fons" (d'on va eixir el número exacte de
  casos de cada regla) estan en `../fuentes/reglas_cat_val.md` — este
  document nou es centra en el prompt i el glossari, no en repetir eixa
  taula.
- L'auditoria completa de quant es complix cada regla al corpus real
  està en `../../dades/sintetico/analisi_corpus.html`.
