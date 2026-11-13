*[Leer en castellano](README.es.md)*

# KenLM amb MaCoCu-ca sencer (primera prova, 09/11/2026)

Primera prova per a substituir FLOR en la decisió de les paraules
ambigües: un model de n-grames [KenLM](https://github.com/kpu/kenlm)
entrenat amb **tot MaCoCu-ca sense filtrar** (decisió de l'usuari).

- `exporta_text.py`: XML → text, una frase per línia, normalitzat
  (`normalitza`: minúscules, apòstrof pegat a la paraula d'abans, números
  a "0", puntuació separada). Entra tot menys els paràgrafs d'un altre
  idioma i les frases de menys de 3 tokens (~2.100 M de tokens, ~11 GB).
- `entrena_kenlm.sh`: job de SLURM, exporta → `lmplz` (ordre 5, poda de
  singletons) → `build_binary` (trie quantitzat).
- `prova_kenlm.py`: puntua frases i compara variants.

Els passos (compilar KenLM, prova xicoteta, model sencer) estan en
[README.es.md](README.es.md).

**KenLM valencià (10/11/2026)**: el mateix script amb les frases del
filtre valencià (totes les de `valencia.jsonl`, decisió de l'usuari):
`JSONL=dades/macocu/valencia/valencia.jsonl NOM=valencia sbatch entrena_kenlm.sh`
(vore README.es.md).

**KenLM valencià net (10/11/2026)**: `MARCADORS_DOC=2 NOM=valencia_net` (frases de
>= 2 marcadors o del mateix document que una d'elles: 1.211.204 frases).

**KenLM de lemes (12/11/2026, experiment)**: `lematitza_text.py` (+ `.sh`)
passa `valencia_net_dogv.txt` a lemes (es queden en la seua forma les
paraules candidates, les que concorden en gènere i la puntuació) i
`entrena_kenlm.sh` l'entrena (`NOM=valencia_net_dogv_lemes`). Tot es llança
amb `pipeline/03_seleccio_de_model/model_llengua/prova_lemes.sh` (vore
README.es.md i `documentacio/resultats_model_llengua_kenlm.md`, secció 4.16).
