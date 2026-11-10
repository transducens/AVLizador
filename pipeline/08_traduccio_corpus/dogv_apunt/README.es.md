# DOGV y noticias de la UA

*(Versión en valenciano: [README.md](README.md).)*

Textos valencianos que bajaron los compañeros (10/11/2026), en
`dades/dogv_apunt/` (fuera de git):

| Fichero | Qué es |
|---|---|
| `dogv_documents.tsv` | 10.289 documentos del DOGV de 2025-2026 (`signatura`, `title`, `text`; los saltos de línea vienen como `\n` literal) |
| `ua_noticias_va.jsonl` | 15.766 noticias de la Universitat d'Alacant en valenciano (`VA`, `url`, `url_es` = la versión castellana); una línea rota (una "r" delante del JSON) |

## Análisis (`analitza_dogv_apunt.py`)

Salida en `dades/dogv_apunt/analisi_dogv_apunt.{md,json}` (35 min; casi
todo el GD de 600 documentos largos del DOGV).

| | DOGV | Noticias UA |
|---|---|---|
| Palabras | 13,8 M | 6,3 M |
| Frases aprovechables únicas (8-40 palabras) | 92.165 (+84.297 repetidas: fórmulas) | 116.658 |
| GD global (muestra de 600 documentos) | **0,84** | **0,46** |
| Documentos con GD ≥ 0,8 / ≤ 0,5 | 69 % / 21 % | 8 % / 63 % |
| este / aquest | 91.022 / 29.096 | 183 / 47.833 |
| servici / servei | 25.568 / 7.797 | 3 / 5.484 |
| -ix / -eix | 39.553 / 25.220 | 2.265 / 22.847 |
| hui / avui | 40 / 1 | 29 / 2.846 |
| colp / cop | 6 / 9 | 57 / 9 |
| reeixida / èxit | 0 / 141 | 43 / 1.470 |

- **DOGV**: valenciano normativo de la AVL en registro administrativo;
  sirve, quitando los documentos de GD bajo y las frases repetidas.
- **Noticias de la UA**: siguen el estándar de la universidad (aquest,
  avui, servei, -eix): **no** para el KenLM valenciano. Pueden servir más
  adelante para castellano–valenciano (`url_es`).
- Ninguna de las dos arregla "cop" (KenLM elige "vegada" donde va
  "colp") ni "reeixida": el DOGV tiene 6 "colp" frente a 7.337 "vegada".

## Texto del DOGV para el KenLM (`prepara_dogv.py`)

Frases de los documentos con GD ≥ 0,8 (GD del documento = suma de los
marcadores de sus frases, calculado con el mismo código por lotes del
filtro valenciano), sin repetidas, sin las que por sí solas son más
catalanas que valencianas ni las de los benchmarks, normalizadas como el
texto del KenLM. Salida: `dades/dogv_apunt/dogv_net.txt` y `.json`.

```bash
python pipeline/08_traduccio_corpus/dogv_apunt/prepara_dogv.py --processos 6
```

En Abaco se junta con el texto del KenLM valenciano limpio y se entrena
`valencia_net_dogv` (`kenlm/entrena_kenlm.sh`; el `.json` hace que el
script no vuelva a exportar):

```bash
cd ~/scrapeo/AVLizador/dades/macocu/kenlm
cat valencia_net.txt ../../dogv_apunt/dogv_net.txt > valencia_net_dogv.txt
echo '{"fonts": ["valencia_net.txt", "dogv_net.txt"]}' > valencia_net_dogv.json
cd ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/kenlm
NOM=valencia_net_dogv MEM_LMPLZ=8G sbatch --cpus-per-task=4 --mem=12000M --time=01:00:00 entrena_kenlm.sh
```

Se compara con `compara_models.py` (`kenlm_val_net_dogv`).
