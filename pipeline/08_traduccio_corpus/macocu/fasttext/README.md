# Classificador fastText valencià/català

*(Versió en castellà, més completa: [README.es.md](README.es.md).)*

Primer pas (10/11/2026) per a provar [fastText](https://fasttext.cc/) en
lloc de FLOR en la decisió de les paraules ambigües, junt amb els dos
KenLM (`../kenlm/`).

fastText no és un model de llengua sinó un **classificador** (`val` /
`cat`) amb paraules, parells de paraules i trossos de 3 a 5 lletres. Es
farà servir com FLOR: el motor genera la frase valenciana de cada
candidat, fastText dona la probabilitat que siga valenciana i guanya la
més alta (amb el mateix `Criteri`). Mesura "quant sona a valencià", no
el sentit.

- `prepara_dades.py`: `cat` = `catala_pur.jsonl` (GD 0, ≥ 2 marcadors);
  `val` = `valencia/valencia.jsonl` amb GD 1,0 i ≥ 2 marcadors; mateixa
  quantitat per classe, 10.000 de validació, fora els benchmarks, text
  normalitzat com el de KenLM. Eixida en `dades/macocu/fasttext/`.
- `entrena_fasttext.sh` (Abaco, 4 CPU, 8 GB): prepara, entrena, test,
  `quantize` (`.ftz`) i parells de prova.

```bash
cd ~ && git clone https://github.com/facebookresearch/fastText.git && cd fastText && make
cd ~/scrapeo/AVLizador/pipeline/08_traduccio_corpus/macocu/fasttext
sbatch entrena_fasttext.sh
```
