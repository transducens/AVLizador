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
