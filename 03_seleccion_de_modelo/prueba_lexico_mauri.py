"""
prueba_lexico_mauri.py -- Evalua si val la pena incorporar el lexic
exhaustiu que ha recopilat un company (02_reglas_dialectales/lexico/mauri/)
al pipeline real.

Reutilitza el motor d'evalua_models.py (mateix SYSTEM_PROMPT_BASE, mateixa
funcio de traduccio via Ollama) per a poder comparar frases REALS del
corpus font traduides amb dos lexics distints:
  (a) nomes lexico_fiable.json (el que usa el pipeline ara mateix)
  (b) lexico_fiable.json + les entrades noves del lexic del company

Aixo permet vore, amb frases reals (no inventades), si una entrada nova
canvia la traduccio i si eixe canvi es correcte o es un error nou.

US:
    python prueba_lexico_mauri.py --informe
        Nomes analisi estatica: quantes entrades son noves, quantes ja
        estaven, i amb quina frequencia real apareixen al corpus font.
        No crida cap model, es instantani.

    python prueba_lexico_mauri.py --compara --mostra 15
        Agarra 15 frases reals del corpus font que continguen alguna
        paraula NOVA del lexic del company, i les tradueix DOS vegades
        (amb el lexic actual, i amb el lexic actual + el nou) per a
        comparar costat a costat.

    python prueba_lexico_mauri.py --compara --paraula blanca
        Prova nomes amb frases que continguen eixa paraula en concret.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evalua_models as em  # noqa: E402  (reutilitza prompt + traduccio + lexic actual)

BASE_DIR = Path(__file__).parent.parent
MAURI_DIR = BASE_DIR / "02_reglas_dialectales" / "lexico" / "mauri"
CORPUS_PATH = BASE_DIR / "corpus" / "final" / "dialectal" / "corpus_occidental_net.jsonl"

MAURI_FILES = [
    "acentuacion_cat_val.json",
    "apertium-spa-cat.spa-cat_variantes.json",
]


def carrega_candidats() -> dict[str, str]:
    """Llig els fitxers del company i retorna {valencia_lower: catala},
    ja filtrats: sense noms propis (majuscula inicial -- mai s'han de
    traduir, regla 10 del prompt) i sense parelles identiques (no son una
    diferencia real)."""
    candidats: dict[str, str] = {}
    for nom_fitxer in MAURI_FILES:
        path = MAURI_DIR / nom_fitxer
        if not path.exists():
            print(f"AVIS: no trobat {path}, se salta.")
            continue
        dades = json.loads(path.read_text(encoding="utf-8"))
        for entrada in dades:
            val = entrada.get("valenciano", "").strip()
            cat = entrada.get("catalan") or entrada.get("catalán") or ""
            cat = cat.strip()
            if not val or not cat:
                continue
            if val[0].isupper():
                continue  # nom propi -- mai es toca, regla 10
            if val.lower() == cat.lower():
                continue  # identic -- no es una diferencia real
            candidats.setdefault(val.lower(), cat.lower())
    return candidats


def compta_frequencia(paraules: set[str]) -> dict[str, int]:
    """Compta, per a cada paraula, quantes vegades apareix com a token
    exacte al corpus font real (no com a subcadena)."""
    text = []
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for linia in f:
            d = json.loads(linia)
            text.append(d.get("text", "").lower())
    corpus_text = "\n".join(text)

    freq = {}
    for paraula in paraules:
        n = len(re.findall(r"\b" + re.escape(paraula) + r"\b", corpus_text))
        if n > 0:
            freq[paraula] = n
    return freq


def informe():
    candidats = carrega_candidats()
    ja_al_lexic = {v.lower() for e in em.LEXIC_ENTRADES for v in e.get("valenciano", [])}
    nous = {k: v for k, v in candidats.items() if k not in ja_al_lexic}

    print(f"Candidats totals (sense noms propis ni identics): {len(candidats)}")
    print(f"Ja estaven a lexico_fiable.json: {len(candidats) - len(nous)}")
    print(f"NOUS: {len(nous)}")
    print()
    print("Comptant frequencia real al corpus font (pot trigar unes desenes de segons)...")
    freq = compta_frequencia(set(nous.keys()))
    print(f"Dels {len(nous)} nous, apareixen >=1 vegada al corpus: {len(freq)}")
    print()

    ordenats = sorted(freq.items(), key=lambda kv: -kv[1])
    print(f"{'Valencia':<20} {'Catala':<20} {'Vegades al corpus'}")
    print("-" * 60)
    for paraula, n in ordenats[:40]:
        print(f"{paraula:<20} {nous[paraula]:<20} {n}")

    print()
    print("ATENCIO: una frequencia alta NO vol dir que l'entrada siga bona.")
    print("Comprova a ma les primeres files -- paraules gramaticals molt")
    print("curtes (articles, pronoms, verbs auxiliars) amb frequencia molt")
    print("alta solen ser falsos positius (la paraula te un altre sentit")
    print("habitual que no es el que capta l'entrada del lexic).")


def frases_amb_paraula(paraula: str, maxim: int = 200) -> list[str]:
    """Extrau del corpus font fins a `maxim` frases que continguen
    `paraula` com a token exacte, ja segmentades (reutilitza el
    segmentador de genera_corpus_sintetico si esta disponible; si no,
    fa una segmentacio simple per punt)."""
    trobades = []
    patro = re.compile(r"\b" + re.escape(paraula) + r"\b", re.IGNORECASE)
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for linia in f:
            d = json.loads(linia)
            for frase in re.split(r"(?<=[.!?])\s+", d.get("text", "")):
                frase = frase.strip()
                if 20 <= len(frase) <= 280 and patro.search(frase):
                    trobades.append(frase)
                    if len(trobades) >= maxim:
                        return trobades
    return trobades


def compara(mostra: int, paraula_filtre: str | None, timeout: int, model: str):
    candidats = carrega_candidats()
    ja_al_lexic = {v.lower() for e in em.LEXIC_ENTRADES for v in e.get("valenciano", [])}
    nous = {k: v for k, v in candidats.items() if k not in ja_al_lexic}

    if paraula_filtre:
        paraules_a_provar = [paraula_filtre.lower()]
        if paraula_filtre.lower() not in nous:
            print(f"AVIS: '{paraula_filtre}' no esta a la llista de candidats nous, es prova igualment.")
    else:
        freq = compta_frequencia(set(nous.keys()))
        paraules_a_provar = [p for p, _ in sorted(freq.items(), key=lambda kv: -kv[1])]

    lexic_ampliat = dict(em.LEXIC_LOOKUP)
    for val, cat in nous.items():
        lexic_ampliat.setdefault(val, [cat])

    fetes = 0
    for paraula in paraules_a_provar:
        if fetes >= mostra:
            break
        frases = frases_amb_paraula(paraula, maxim=1)
        if not frases:
            continue
        frase = frases[0]

        prompt_base = em.construeix_prompt_usuari(frase)
        glossari_ampliat = em.glossari_per_frase(em.normalitza_apostrofa(frase), lexic_ampliat)
        prompt_ampliat = (
            f"{glossari_ampliat}\nFrase a traduir: {em.normalitza_apostrofa(frase)}"
            if glossari_ampliat else f"Frase a traduir: {em.normalitza_apostrofa(frase)}"
        )

        hip_base = em.neteja_preambul(em.tradueix_ollama(frase, model, timeout=timeout, system=em.SYSTEM_PROMPT_BASE))

        # tradueix_ollama construeix el seu propi prompt d'usuari amb el lexic
        # GLOBAL (em.LEXIC_LOOKUP); ací volem el lexic ampliat nomes per a esta
        # crida, per aixo es fa la peticio directament en lloc de reutilitzar-la.
        import requests
        payload = {
            "model": model,
            "system": em.SYSTEM_PROMPT_BASE,
            "prompt": prompt_ampliat,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 200},
        }
        try:
            r = requests.post(f"{em.OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
            r.raise_for_status()
            hip_ampliada = em.neteja_preambul(r.json().get("response", "").strip())
        except Exception as e:
            hip_ampliada = f"ERROR: {e}"

        print()
        print(f"=== paraula candidata: {paraula} -> {nous.get(paraula, '?')} ===")
        print(f"FRASE:            {frase}")
        print(f"HIP (lexic actual):  {hip_base}")
        print(f"HIP (lexic + nou):   {hip_ampliada}")
        if hip_base.strip() == hip_ampliada.strip():
            print("-> SENSE CANVI (la paraula nova no s'ha activat o no ha canviat res)")
        else:
            print("-> HA CANVIAT -- revisa a ma si el canvi es correcte o es un error nou")
        fetes += 1

    if fetes == 0:
        print("No s'ha trobat cap frase real al corpus amb les paraules candidates.")


def main():
    parser = argparse.ArgumentParser(description="Prova el lexic exhaustiu del company (02_reglas_dialectales/lexico/mauri/)")
    parser.add_argument("--informe", action="store_true", help="Analisi estatica: noves entrades + frequencia real, sense cridar cap model")
    parser.add_argument("--compara", action="store_true", help="Tradueix frases reals dos vegades (lexic actual vs lexic+nou) i compara")
    parser.add_argument("--mostra", type=int, default=10, help="Quantes paraules candidates provar en --compara (per defecte 10, les mes frequents)")
    parser.add_argument("--paraula", default=None, help="Prova nomes esta paraula concreta en --compara")
    parser.add_argument("--model", default="qwen2.5:14b", help="Model d'Ollama a fer servir")
    parser.add_argument("--ollama-timeout", type=int, default=180, help="Segons d'espera per peticio")
    args = parser.parse_args()

    if args.informe:
        informe()
    elif args.compara:
        compara(args.mostra, args.paraula, args.ollama_timeout, args.model)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
