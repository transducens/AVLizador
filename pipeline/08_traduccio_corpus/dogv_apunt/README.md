# DOGV i notícies de la UA

*(Versió en castellà, més completa: [README.es.md](README.es.md).)*

Textos valencians baixats pels companys (10/11/2026), en
`dades/dogv_apunt/` (fora de git): `dogv_documents.tsv` (DOGV 2025-2026,
10.289 documents) i `ua_noticias_va.jsonl` (15.766 notícies de la
Universitat d'Alacant, amb la URL castellana).

- `analitza_dogv_apunt.py`: GD, norma (este/aquest, servici/servei,
  -ix/-eix...), frases aprofitables i repetides. El DOGV és valencià de
  l'AVL (GD 0,84); les notícies de la UA seguixen l'estàndard de la
  universitat (GD 0,46) i no servixen per al KenLM valencià.
- `prepara_dogv.py`: frases dels documents del DOGV amb GD ≥ 0,8, sense
  repetides, normalitzades com el text del KenLM → `dades/dogv_apunt/dogv_net.txt`,
  per a entrenar `valencia_net_dogv` (MaCoCu net + DOGV).
