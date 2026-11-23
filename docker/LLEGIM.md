# docker/

Fitxers opcionals per a construir la imatge (`docker compose up --build`).

- `kenlm/` (ignorada per git): si hi poses els tres fitxers del model KenLM
  (`valencia_net_dogv_o5.binary`, `valencia_net_dogv_freq.json` i
  `sentit.json`), la imatge porta eixos. Si la carpeta no hi és o està buida,
  la construcció baixa el model de Hugging Face
  (`transducens/avlizador-kenlm-va`, la revisió que diu el paquet o la de
  `--build-arg KENLM_REVISIO=...`). Serveix per a provar un model encara no
  publicat. Des del 23/11/2026 (`prepara_kenlm.py`) es mira fitxer a fitxer:
  els que hi són es copien i els que falten es baixen.

- Opció amb lemes (`--model kenlm-lemes`, 23/11/2026): amb `KENLM_LEMES: "1"`
  en `docker-compose.yml` (el valor que hi ha des del 23/11; `""` per a no
  portar-la) o `--build-arg KENLM_LEMES=1` la imatge porta
  també `valencia_net_dogv_lemes_o5.binary` i `valencia_net_dogv_lemes_freq.json`
  (~80 MB més), de `kenlm/` si hi són o de Hugging Face (el mateix
  repositori). Sense, no s'hi posen encara que siguen en `kenlm/`. Dins del
  contenidor: `docker compose exec avlizador avlizador tradueix --model
  kenlm-lemes "..."` (la interfície web usa sempre l'opció per defecte).

- `prepara_kenlm.py`: el que posa el model en `/opt/kenlm` en construir la
  imatge (s'executa dins de la construcció).

- `ca_core_news_md-3.8.0-py3-none-any.whl` (ignorat per git): el model
  català d'spaCy. Normalment pip el baixa dels *releases* de GitHub en
  construir la imatge; si eixa descàrrega falla dins de Docker (passa amb
  algunes xarxes i VPN: `SSLError ... UNEXPECTED_EOF_WHILE_READING`, encara
  que en el navegador o en PowerShell sí que baixe), baixa'l fora i deixa'l
  ací amb este nom exacte:

  ```
  Invoke-WebRequest https://github.com/explosion/spacy-models/releases/download/ca_core_news_md-3.8.0/ca_core_news_md-3.8.0-py3-none-any.whl -OutFile docker\ca_core_news_md-3.8.0-py3-none-any.whl
  ```

  La construcció l'instal·la d'ací i no el baixa.

En funcionament la imatge no es connecta a internet: el model ja va dins.
