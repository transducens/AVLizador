# Benchmarks de catalán → valenciano

Todos con el mismo formato: una lista JSON de `{"id", "oriental",
"occidental", ...}`, donde `oriental` es el catalán (la entrada) y
`occidental` el valenciano (la referencia). Se evalúan con:

```bash
avlizador avalua --llista                 # nombres cortos de cada uno
avlizador avalua --benchmarks manual      # el de evaluación
avlizador avalua --fitxer otro.json       # cualquier fichero con este formato
```

Son **copias** (30/10/2026) de los benchmarks que se construyeron en
`pipeline/` y `dades/`; los originales y los scripts que los generan
siguen allí (columna "Origen").

| Carpeta / fichero | Frases | Qué mide | Origen |
|---|---|---|---|
| **`manual/benchmark_manual_cat_val.json`** | **458** | **Benchmark de evaluación**: BOE + AVL juntas, revisadas a mano | `dades/benchmark_manual/`, `pipeline/03_seleccio_de_model/benchmark_manual/construeix_benchmark.py` |
| `manual/benchmark_manual_boe_cat_val.json` | 246 | Textos oficiales del BOE, catalán y valenciano oficiales, revisados desde el original; elegidos para cubrir los fenómenos de los diccionarios y las reglas | ídem |
| `manual/benchmark_manual_avl_cat_val.json` | 212 | Valenciano de los textos de la AVL; el catalán, borrador automático corregido a mano | ídem |
| `curat_151/benchmark_corpus.json` | 154 | Banco curado: cada frase ilustra un fenómeno dialectal | `pipeline/03_seleccio_de_model/benchmark_corpus.json` |
| `homografs/benchmark_sistema_final_cat_val.json` | 253 | 151 + 98 homógrafos inventados ("cop", "nou", "manca", "gandula"...) + 1 de gplsi | `pipeline/03_seleccio_de_model/construeix_benchmark_sistema_final.py` |
| `homografs/benchmark_homografs_cat_val.json` | 98 | Solo los homógrafos (para el modelo de lenguaje) | `pipeline/03_seleccio_de_model/model_llengua/genera_benchmark.py` |
| `boe_dialectal/benchmark_boe_dialectal_estricte.json` | 2.000 | BOE, pares con solo diferencias dialectales seguras (**regresiones**) | `pipeline/05_corpus_boe/construeix_boe_dialectal.py` (ver `README_construccio.es.md`) |
| `boe_dialectal/benchmark_boe_dialectal_estricte_complet.json` | 9.453 | El estricto entero | ídem |
| `boe_dialectal/benchmark_boe_dialectal_ampli.json` | 2.000 | BOE, pares sin reformulación (**huecos** del diccionario) | ídem |
| `boe_dialectal/benchmark_boe_dialectal_ampli_complet.json` | 73.705 | El amplio entero (22 MB) | ídem |
| `boe_dialectal/benchmark_boe_mostra_2000.json` | 2.000 | BOE sin filtrar, con todo el ruido de estilo | ídem |
| `gplsi/benchmark_gplsi.json` | 1.958 | Dataset público `gplsi/CA-VA_alignment_test` (dos traducciones humanas independientes desde el castellano) | `dades/gplsi_ca_va_alignment_test/` |

## Licencias y atribución

- **gplsi**: CC BY 4.0, grupo GPLSI de la Universitat d'Alacant. El
  fichero original (`CA-VA_alignment_test.tsv`) y su README
  (`README_dataset_original.md`, con la cita) se conservan tal cual.
- **BOE**: textos oficiales del Boletín Oficial del Estado.
- **AVL**: textos públicos de la web de l'Acadèmia Valenciana de la Llengua.
- Los benchmarks propios (manual, curado, homógrafos): licencia del
  repositorio (pendiente de confirmar).

## Reglas

- No se editan a mano los ficheros de aquí: si un benchmark cambia, se
  regenera con su script de origen y se vuelve a copiar.
- Las cifras de cada benchmark, en
  `pipeline/03_seleccio_de_model/resultats_benchmarks_cat_val.md`.
