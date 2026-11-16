# docker/

Fitxers opcionals per a construir la imatge (`docker compose up --build`).

- `kenlm/` (ignorada per git): si hi poses els tres fitxers del model KenLM
  (`valencia_net_dogv_o5.binary`, `valencia_net_dogv_freq.json` i
  `sentit.json`), la imatge porta eixos. Si la carpeta no hi és o està buida,
  la construcció baixa el model de Hugging Face
  (`transducens/avlizador-kenlm-va`, la revisió que diu el paquet o la de
  `--build-arg KENLM_REVISIO=...`). Serveix per a provar un model encara no
  publicat.

En funcionament la imatge no es connecta a internet: el model ja va dins.
