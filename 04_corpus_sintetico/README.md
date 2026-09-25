*[Llegeix-ho en castellà](README.es.md)*

# Corpus sintètic paral·lel valencià → català

Genera un corpus de parells de frases (valencià original / català sintètic)
per a entrenar o afinar un model de traducció occidental↔oriental.

## Font i model

- **Font**: `data/avl/final/dialectal/corpus_occidental_net.jsonl` — no el
  `unified.jsonl` general, sinó el subconjunt que `estudi_dialectal.py` ja va
  filtrar i verificar com a valencià pur (1.778 documents, 821K tokens, sense
  contaminació de textos orientals). Traduir des d'ací en compte del corpus
  complet evita ensenyar-li al model parelles on l'"original" ja estava en
  català.
- **Model**: `qwen2.5:14b` via Ollama local, amb el mateix system prompt i el
  mateix glossari dinàmic per frase que `03_seleccion_de_modelo/evalua_models.py`
  (BLEU 90,87 / chrF 95,86 / chrF++ 95,55 al benchmark del 17/09/2026, amb
  el lèxic de 194 entrades i les regles de pretèrit perifràstic/institucions/
  elisió ja afegides) — la millor configuració provada fins ara. Comparat
  també amb salamandra-7b-instruct (BSC) — vore
  `../documentacion/metodologia_y_resultados.md` secció 5 per a la comparativa completa.
- **Diferència respecte al benchmark**: el benchmark tradueix frases soltes
  sense noms d'institucions. En aplicar-ho a text real de l'AVL es va
  detectar que el model "traduïa" sigles (`AVL` → `IEC`), un error factual,
  no dialectal. Aquest script afig una regla extra al system prompt (només
  ací, sense tocar `evalua_models.py`) perquè `AVL`, `GVA`, `GNV`, `GVB` i
  `RACV` es queden sempre intactes, i marca com a sospitosa qualsevol parella
  on açò falle igualment.

## Ús

```bash
# Prova ràpida (10 frases, per comprovar que Ollama respon bé)
python genera_corpus_sintetico.py --limit 10 --verbose

# Mostra aleatòria de N frases (per avaluar qualitat abans del run llarg)
python genera_corpus_sintetico.py --sample 500

# Generació completa — reanudable amb Ctrl+C i tornar a llançar el mateix comandament
python genera_corpus_sintetico.py

# Regenerar només els fitxers nets d'exportació (sense tornar a traduir res)
python genera_corpus_sintetico.py --nomes-exporta
```

Paràmetres més rellevants (`--help` per a la llista completa):

| Paràmetre | Per defecte | Per a què serveix |
|---|---|---|
| `--model` | `qwen2.5:14b` | Model d'Ollama |
| `--ollama-url` | `http://localhost:11434` | URL del servidor Ollama (canvia-la per apuntar a un Ollama remot, p.ex. un node GPU — veure `slurm/README.md`) |
| `--ollama-timeout` | 300 | Segons d'espera per petició |
| `--max-caracters` | 280 | Frases més llargues es descarten (evita talls a la resposta) |
| `--sample N` / `--limit N` | — | Mostra aleatòria / les N primeres, mutuament excloents |
| `--incloure-sospitosos` | no | Inclou a l'exportació neta també les parelles marcades |
| `--num-shards N` / `--shard-id I` | 1 / 0 | Reparteix el corpus en N fragments (per a N GPUs a la vegada) — veure `slurm/generar_corpus_paralelo.sh` |
| `--merge-shards N` | — | Fusiona els N fragments en el fitxer final (no tradueix res) |

## ⚠️ Temps d'execució (llegeix això abans de llançar-ho tot)

Aquesta màquina **no té GPU** (Ollama carrega qwen2.5:14b sencer en CPU).
Amb una prova real de 5 frases, el ritme estable és **~30-60 s/frase**.

El corpus font conté **46.315 frases úniques**. Als ritmes mesurats:

| Abast | Temps estimat |
|---|---|
| 200 frases (prova) | ~2-3 hores |
| 8.000 frases (mostra gran) | ~3-6 dies continus |
| 46.315 frases (corpus complet) | **~16-32 dies continus** |

El script és totalment **reanudable**: cada frase es guarda (append + flush)
just després de traduir-se, així que es pot interrompre amb Ctrl+C en
qualsevol moment i tornar a llançar el mateix comandament — no repeteix cap
frase ja feta.

### Executar-ho en GPU (recomanat per al corpus complet)

Amb GPU, el mateix qwen2.5:14b sol anar de 10 a 30 vegades més ràpid que en
CPU (uns 9-10 GB de VRAM), cosa que convertiria les ~3 setmanes estimades a
dalt en de l'ordre d'1-2 dies. `--ollama-url` permet apuntar a un Ollama que
corre en un altre lloc. Ja hi ha un script preparat:

- `slurm/` — scripts `sbatch` per al clúster GPU de la universitat: túnel
  SSH per a provar-ho, un job autònom amb 1 GPU, i un altre que reparteix el
  corpus entre **totes les GPUs lliures a la vegada** (`--num-shards`) si el
  clúster en té diverses en la mateixa màquina — amb 8 GPUs lliures, açò
  pot convertir 1-2 dies en unes poques hores. Detalls complets al seu
  README.

## Sortida

```
data/sintetico/
├── corpus_sintetic_val_cat.jsonl   # Fitxer principal: totes les parelles + metadades + qualitat
├── parallel_val_cat.jsonl          # Exportació neta {"val", "cat"} (sense sospitoses)
├── parallel.val / parallel.cat     # El mateix, en 2 fitxers alineats línia a línia (format Moses/OPUS)
├── generacio.log                   # Log complet amb timestamp
└── informe_generacio.txt           # Resum: parelles per tipus de document, sospitoses, temps
```

## Estat del corpus generat

- **v1** (lèxic i prompt anteriors a esta ronda de millores): 46.315
  frases, auditada per complet — vore `data/sintetico/` i
  `../documentacion/metodologia_y_resultados.md` secció 6 per als bugs
  trobats i corregits.
- **v2**: regeneració amb el lèxic de 194 entrades i totes les regles
  madures — és la versió que cal usar una vegada estiga llesta. Fitxer
  final: `data/sintetico/parallel_val_cat.jsonl` (format
  `{"val": "...", "cat": "..."}`, una parella per línia, llest per a
  entrenar).

`corpus_sintetic_val_cat.jsonl` guarda, per cada frase única: el text
valencià, la traducció, el document d'origen (`doc_id`, `source_url`,
`doc_type`), quantes vegades apareixia la frase al corpus original
(`n_ocurrencies`) i una llista `motius_sospita` (buida si tot sembla
correcte). Motius possibles:

- `buit` — el model no ha tornat res
- `fuga_prompt` — el bloc `[VOCABULARI: ...]` ha aparegut a la resposta
- `possible_explicacio` — sembla que ha afegit una nota en lloc de traduir
- `longitud_anormal` — la traducció és molt més curta o llarga que l'original
- `no_traduit` — l'original tenia marcadors occidentals clars i la traducció és idèntica
- `entitat_alterada` — una sigla d'institució (AVL, GVA...) ha desaparegut
- `instruccio_filtrada` — el literal «Frase a traduir:» (part del prompt) ha aparegut filtrat a la resposta
- `sigla_introduida` — el model s'ha inventat una sigla que no era a l'original (p.ex. "l'Acadèmia" → "l'AVL")
- `possible_glitch` — fragment de paraula duplicat just després d'una elisió (p.ex. "M'm-interessa"), un tipus de soroll de generació vist en text llarg

Les parelles sospitoses **no es descarten** del fitxer principal (per si vols
revisar-les tu mateix); simplement queden fora de `parallel_val_cat.jsonl` i
dels fitxers `.val`/`.cat`, que són els pensats per a entrenament.

**Estos filtres no ho atrapen tot.** Són heurístics barats (regex, longitud,
paraules clau) pensats per a detectar els errors més freqüents i evidents —
no substitueixen una revisió humana. En una prova amb 10 frases reals es van
detectar errors ortogràfics subtils (p.ex. pèrdua d'un accent: "àmbit" →
"ambit") que cap heurístic actual capta. Per a un corpus que vulgues fer
servir per a entrenar, és recomanable revisar a mà una mostra abans de
confiar-hi cegament, sobretot si has pujat molt `--max-caracters`.
