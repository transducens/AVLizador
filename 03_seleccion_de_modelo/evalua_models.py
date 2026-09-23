"""
evalua_models.py — Benchmark de traducció occidental→oriental
--------------------------------------------------------------
Avalua models de traducció amb mètriques BLEU i chrF.
Carrega les frases de benchmark_corpus.json, envia cada frase al model
i compara la sortida amb la referència humana.

Millores respecte a la versió anterior:
  · Sistema de regles carrega el lèxic sencer de lexico_fiable.json
    (revisat a mà, sense les entrades sense revisar de palabras_traducidas.json)
    en lloc de les ~40 codificades a mà.
  · System prompt reescrit en català, amb morfologia del .md i sense
    llistat de paraules aïllades (el model no pot generalitzar una llista
    de 1.600 mots en context limitat).
  · Lookup dinàmic per frase: abans de cridar el LLM es busquen les
    paraules valencianes presents a la frase dins del JSON i s'afegeix
    al prompt un glossari mínim i rellevant.
  · El system prompt va al camp `system` separat del `prompt`/`messages`,
    tant a Ollama com a Claude.
  · temperature=0 per a reproductibilitat del benchmark.

Claude és completament OPCIONAL (només cal si es passa --api-key);
sense crèdit d'Anthropic, tot funciona igual amb Ollama i/o el
sistema de regles.

COMET és també OPCIONAL (només cal si es passa --comet). És una mètrica
neuronal (usa src+hipòtesi+referència) que sol correlacionar millor amb
el judici humà que BLEU/chrF, però requereix baixar un model de ~1-2 GB
(pytorch + unbabel-comet) la primera vegada que s'executa.

NLLB-200 (Meta) és també OPCIONAL (només cal si es passa --model nllb/tots).
Es carrega amb transformers (AutoModelForSeq2SeqLM), amb caché global perquè
no es recarregue entre frases, i tradueix TOT el benchmark en lots
(--nllb-batch-size) abans d'entrar al pipeline d'avaluació normal — així
s'aprofita la GPU si n'hi ha, en lloc d'anar frase a frase com Ollama/Claude.

INSTAL·LACIÓ:
    pip install sacrebleu requests
    (anthropic només cal si s'usa --model claude/tots amb --api-key)
    (unbabel-comet + torch només cal si s'usa --comet; s'instal·len sols)
    (transformers + torch només cal si s'usa --model nllb/tots; s'instal·len sols)

ÚS:
    # Avalua un model d'Ollama
    python evalua_models.py --model ollama --ollama-model llama3.1:8b

    # Avalua diversos models d'Ollama en la mateixa passada (separats per coma)
    python evalua_models.py --model ollama --ollama-model llama3.1:8b,qwen2.5:7b

    # Model gran (14b): sense GPU pot trigar molt per frase, per això es puja el timeout
    python evalua_models.py --model ollama --ollama-model qwen2.5:14b --ollama-timeout 300

    # Avalua TOTS els models que ja tens baixats a Ollama (autodetecta)
    python evalua_models.py --model ollama

    # Sistema de regles antic (baseline, substitucions regex sobre el text sencer)
    python evalua_models.py --model regles

    # Motor de regles nou (paquet traductor/, basat en tokens amb flags
    # is_translated/is_proper_noun -- vore final/05_motor_reglas/README.md)
    python evalua_models.py --model traductor

    # Tot el que hi haja disponible (regles + tots els Ollama + Claude si hi ha --api-key)
    python evalua_models.py --model tots

    # Amb Claude (opcional, requereix crèdit d'Anthropic)
    python evalua_models.py --model claude --api-key TU_API_KEY

    # Amb la mètrica COMET a més de BLEU/chrF (baixa un model la 1a vegada)
    python evalua_models.py --model ollama --comet

    # NLLB-200 de Meta (baixa el model la 1a vegada; per defecte el distilled-600M)
    python evalua_models.py --model nllb

    # NLLB-200 més gran, amb lots més grans si hi ha prou VRAM
    python evalua_models.py --model nllb --nllb-model facebook/nllb-200-3.3B --nllb-batch-size 32

    # Diverses instàncies d'Ollama en paral·lel (una per GPU/port): cal
    # apuntar cada crida al seu port amb --ollama-url
    python evalua_models.py --model ollama --ollama-model gemma3:12b --ollama-url http://127.0.0.1:11435

    # Servidor compatible amb l'API d'OpenAI (p.ex. vLLM servint un model
    # que NO es recomana per Ollama, com BSC-LT/salamandraTA-7b-instruct):
    #   --openai-mode regles: mateix system prompt de regles dialectals que Ollama
    #   --openai-mode traduccio: plantilla oficial de traducció del model
    python evalua_models.py --model openai \
        --openai-url http://127.0.0.1:8000/v1 \
        --openai-model BSC-LT/salamandraTA-7b-instruct --openai-mode regles

SORTIDA:
    resultats/benchmark_<model>_<timestamp>.json
    resultats/informe_comparatiu_<timestamp>.txt
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# La consola de Windows sol anar en cp1252 i peta amb caràcters com ✓/→;
# forcem UTF-8 a l'eixida perquè els prints amb accents/símbols no fallen.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# ─── Normalització d'apòstrofs ───────────────────────────────────────────────
# El benchmark té ´ (U+00B4, accent agut) en lloc de ' (apòstrof), i també
# ' / ' (cometes tipogràfiques). Els normalitzem a ' estàndard (U+0027) per
# evitar que el regex \b i el lookup fallin en contextos com d´este o l´edat.

def normalitza_apostrofa(text: str) -> str:
    """Normalitza totes les variants d'apòstrof a l'apòstrof estàndard ASCII."""
    return (
        text
        .replace('\u00b4', "'")   # ´ accent agut (el bug principal del benchmark)
        .replace('\u2018', "'")   # ' cometa tipogràfica esquerra
        .replace('\u2019', "'")   # ' cometa tipogràfica dreta
        .replace('\u02bc', "'")   # ʼ modificador carta apòstrof
        .replace('\u0060', "'")   # ` accent greu
    )


# ─── Instal·lació automàtica de dependències ──────────────────────────────────

# Alguns models (p. ex. salamandra-7b-instruct) no entenen que l'EXEMPLE del
# system prompt es nomes il·lustratiu i repeteixen etiquetes del prompt al
# principi de CADA resposta: primer es va detectar "Resposta correcta:"
# (52/60 frases, ~9 punts de BLEU), i despres de traure eixa etiqueta de
# l'EXEMPLE, va aparéixer "(La) frase a traduir:" en el seu lloc (2/60 al
# benchmark del 17/09) -- el model no copia una etiqueta fixa, copia
# QUALSEVOL etiqueta que vega al prompt. Per aixo esta neteja cobreix les
# dos i queda oberta a ampliar-se si en sorgeix una altra.
import re as _re_preambul
_PREAMBULS_FUGATS = _re_preambul.compile(
    r"^\s*(la\s+)?(resposta\s+correcta|resposta|traducci[oó]\s+correcta|"
    r"traducci[oó]|frase\s+a\s+traduir)\s*:\s*",
    _re_preambul.IGNORECASE,
)


def neteja_preambul(text: str) -> str:
    """Lleva una etiqueta de preambul fugada del bloc EXEMPLE (p. ex.
    'Resposta correcta: ') si el model l'ha copiat al principi de la resposta."""
    return _PREAMBULS_FUGATS.sub("", text, count=1).strip()


def instala_si_cal():
    import subprocess
    paquets = ["sacrebleu", "requests"]
    for p in paquets:
        try:
            __import__(p)
        except ImportError:
            print(f"Instal·lant {p}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", p, "-q"])

instala_si_cal()

import sacrebleu
import requests

# ─── Configuració ─────────────────────────────────────────────────────────────

BENCHMARK_PATH  = Path(__file__).parent / "benchmark_corpus.json"
# lexico_fiable.json (revisado a mano) sustituye a palabras_traducidas.json:
# ese fichero tenía entradas sin revisar de origen poco fiable (ver
# 02_reglas_dialectales/reglas_prompt/glossari_dinamic.md para el historial).
LEXIC_PATH      = Path(__file__).parent.parent / "02_reglas_dialectales" / "lexico" / "lexico_fiable.json"
OUTPUT_DIR      = Path(__file__).parent / "resultats"
OUTPUT_DIR.mkdir(exist_ok=True)
OLLAMA_URL      = "http://localhost:11434"
COMET_MODEL_NAME = "Unbabel/wmt22-comet-da"

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"
NLLB_SRC_LANG   = "val_Latn"
NLLB_TGT_LANG   = "cat_Latn"

_comet_model = None  # es carrega de manera peresosa, només si --comet

_nllb_model = None       # caché global: es carrega una sola vegada, només si --model nllb/tots
_nllb_tokenizer = None
_nllb_device = None

# ─── Càrrega del lèxic ────────────────────────────────────────────────────────

def carrega_lexic(path: Path) -> tuple[dict, list]:
    """
    Carrega lexico_fiable.json i retorna:
      · lookup: dict {forma_valenciana_lower → [formes_catalanes]}
                (inclou totes les formes valencianes de cada entrada)
      · entrades: llista original (per al sistema de regles)
    Si el fitxer no existeix, retorna estructures buides i avisa.
    """
    if not path.exists():
        print(f"AVÍS: No es troba el lèxic a {path}. El sistema de regles usarà "
              f"només les substitucions morfològiques codificades.")
        return {}, []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    entrades = data.get("entrades", data.get("entradas", []))
    lookup: dict[str, list[str]] = {}

    # Paraules excloses del lookup lèxic:
    #  a) Gestionades per les regles morfològiques codificades a mà (evita conflictes)
    #  b) Paraules gramaticals (preposicions, articles, pronoms) — context-dependents,
    #     el model les tradueix malament si les veu al glossari (p.ex. en→amb, a→macu/a)
    #  c) Paraules curtes amb falsos positius al JSON
    EXCLOSES = {
        # Demostratius (gestionats a les regles)
        "este", "esta", "estos", "estes",
        # Temporal (gestionat a les regles)
        "hui", "vesprada",
        # Preposicions i articles — NO al glossari (causen en→amb, a→macu/a, etc.)
        "a", "ab", "amb", "en", "de", "per", "per a", "fins", "fins a",
        "el", "la", "els", "les", "l", "un", "una", "uns", "unes",
        # Pronoms febles i personals curts
        "es", "se", "ho", "li", "hi", "ne", "en", "vos", "us", "jo", "tu",
        "ell", "ella", "ells", "elles", "yo", "ya",
        # Conjuncions
        "i", "o", "ni", "que", "si", "com", "però", "mes",
        # Adverbis curts ja gestionats
        "on", "ja",
        # Paraules curtes amb falsos positius al JSON (≤3 car.)
        "foc", "nus", "pes", "cel", "cos", "peu", "pla", "pou", "res",
        "riu", "rot", "sal", "set", "sol", "son", "tos", "tot", "vel",
        "via", "veu", "vot", "gel", "got", "gos", "gas", "fas", "poc",
        "dos", "tot", "ben", "molt", "cap", "tan",
    }

    # Longitud mínima de clau per evitar falsos positius amb paraules gramaticals
    MIN_LONG = 4

    for e in entrades:
        # Noms de persona (categoria "nombre") no s'han de traduir mai — el propi
        # JSON ja ho etiqueta així. Sense este filtre, entrades com "Ramon"→"Ramó"
        # o "Manuel"→"Manel" es disparaven amb qualsevol persona real amb eixe nom.
        if e.get("categoria") == "nombre":
            continue
        formes_val = e.get("valenciano", e.get("valencià", []))
        formes_cat = e.get("catalan",    e.get("català",   []))
        if not formes_val or not formes_cat:
            continue
        for fv in formes_val:
            clau = normalitza_apostrofa(fv.strip().lower())
            # Descarta: buits, ja registrats, exclosos, o massa curts (evita gramàtiques)
            if not clau or clau in lookup or clau in EXCLOSES or len(clau) < MIN_LONG:
                continue
            # Normalitza apòstrofs i minúscules en les formes catalanes
            lookup[clau] = [
                normalitza_apostrofa(fc.strip().lower())
                for fc in formes_cat if fc.strip()
            ]

    print(f"Lèxic carregat: {len(lookup)} formes valencianes ({path.name})")
    return lookup, entrades


# Carrega global (es fa una sola vegada en importar el mòdul)
LEXIC_LOOKUP, LEXIC_ENTRADES = carrega_lexic(LEXIC_PATH)


# ─── Glossari per frase (lookup dinàmic per al LLM) ──────────────────────────

# Paraules gramaticals que no han d'anar al glossari del LLM encara que
# superin el filtre de longitud (eviten soroll i el bug en→amb).
_STOPWORDS_GLOSSARI = {
    "molt", "cada", "quan", "però", "aquest", "aquesta", "aquests", "aquestes",
    "mateix", "mateixa", "també", "encara", "entre", "sobre", "altre", "altra",
    "altres", "algun", "alguna", "alguns", "algunes", "sense", "segons",
    "mentre", "perquè", "perque", "doncs", "llavors", "després", "abans",
    "sempre", "sovint", "potser", "nomes", "només", "totes", "tots",
}


def glossari_per_frase(frase: str, lookup: dict, max_entrades: int = 12) -> str:
    """
    Donada una frase en valencià (ja normalitzada), cerca les paraules lèxiques
    presents al lookup i retorna un glossari en format [VAL=CAT, ...].

    Format entre claudàtors en lloc de text lliure → el model no el reprodueix
    com a part de la hipòtesi ni el copia com a encapçalament de la sortida.
    Tokens de menys de 4 caràcters i stopwords queden filtrats.
    """
    if not lookup:
        return ""

    # Noms propis (persones, llocs, cognoms...) NO han d'entrar mai al
    # glossari, encara que la seua forma en minuscules coincidisca amb una
    # entrada coneguda -- este es el bug real que vam trobar amb "Blanca"
    # (ocell) vs. "blanca" (adjectiu) i "Roig" (cognom) vs. "roig" (color).
    # Heuristica: una paraula que apareix en majuscula i NO es la primera
    # paraula de la frase es tracta com un possible nom propi.
    frase_original = normalitza_apostrofa(frase)
    tokens_originals = re.findall(
        r"[a-zA-ZàáâäèéêëìíîïòóôöùúûüçñÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÇÑ]+",
        frase_original,
    )
    noms_propis_sospitosos = {
        t.lower() for i, t in enumerate(tokens_originals)
        if i > 0 and t[:1].isupper()
    }

    frase_norm = frase_original.lower()
    tokens = set(re.findall(r"[a-zA-Zàáâäèéêëìíîïòóôöùúûüçñ]+", frase_norm))

    parells = {}  # val → cat (dict per deduplicar)
    for token in tokens:
        if len(token) < 4 or token in _STOPWORDS_GLOSSARI:
            continue
        if token in noms_propis_sospitosos:
            continue  # probable nom propi -- mai es tradueix (regla 10)
        if token in lookup:
            parells[token] = lookup[token][0]
        # Prova sense apòstrof final (traure'n → traure)
        token_base = token.rstrip("-'")
        if token_base != token and len(token_base) >= 4 and token_base not in parells:
            if token_base in lookup:
                parells[token_base] = lookup[token_base][0]

    if not parells:
        return ""

    # Ordena per longitud descendent (les entrades més específiques primer)
    entrades = sorted(parells.items(), key=lambda x: -len(x[0]))[:max_entrades]
    glossari_str = ", ".join(f"{v}={c}" for v, c in entrades)
    return f"[VOCABULARI: {glossari_str}]"


# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """Ets un expert en dialectologia valenciana. La teua tasca és traduir frases del valencià occidental (norma AVL/GVA) al català oriental (norma IEC).

INSTRUCCIONS IMPORTANTS:
- Retorna ÚNICAMENT la frase traduïda. Cap nota, cap explicació, cap comentari.
- No reprodueixis el bloc [VOCABULARI: ...] a la resposta — és només una ajuda de consulta.
- MOLT IMPORTANT: conserva les referències a "valencià"/"valenciana"/
  "valencians"/"valencianes" EXACTAMENT tal qual; MAI les canvies per
  "català"/"catalana"/"catalans"/"catalanes". Encara que la resta de la
  frase estiga en oriental, la paraula que designa l'idioma o la gent no
  canvia mai. Torna a llegir la teua resposta abans d'acabar i comprova
  que no has fet este canvi.
- Si una paraula no té equivalent clar, conserva-la sense traduir.
- No tradueixis preposicions de manera aïllada: "en", "a", "de" es mantenen igual si el context no ho exigeix. En particular, NO canvies mai "en" per "a" ("en la costa" es queda "en la costa", NO "a la costa"; "en l'esfera pública" es queda igual) — no hi ha cap regla d'ací baix que ho demane, encara que et semble més natural en oriental.
- No alteris noms d'institucions, llocs o persones encara que continguen una
  paraula coneguda (per exemple, mai canvies "el Congrés dels Diputats" per
  "el Parlament", encara que "Congrés" i "Parlament" pogueren semblar
  intercanviables). Tampoc "corregisques" un nom propi que et semble mal
  escrit o estrany (persona, poble, ciutat...): copia'l lletra per lletra
  tal com apareix a l'original, encara que et semble una errata.
- ELISIÓ (nomes "de", "la", "el" — MAI "per a", "amb", "en", ni cap altra
  preposició): substituïx-los ENTERAMENT per "d'"/"l'" únicament quan la
  paraula immediatament següent comence en vocal (a, e, i, o, u, amb accent
  o sense) — mai els dupliques ("de d'escalfar-nos" és incorrecte, ha de
  ser "d'escalfar-nos") ni els toques si la paraula següent comença en
  consonant ("de normalitat" es queda "de normalitat", NO "d'normalitat").
  "per a" no elideix MAI, ho tinga davant el que ho tinga.
  ATENCIÓ — "h" muda: algunes paraules valencianes comencen per una "h"
  que no es pronuncia, i per a l'elisió compten com si començaren en vocal
  (hisenda, hivern, home, hora, història, harmonia...): "de hisenda" →
  "d'hisenda", "la hora" → "l'hora". No confons açò amb una "h" darrere de
  consonant dins de la paraula, que no afecta l'elisió.
- No alteris cap paraula que no estiga coberta per una regla concreta
  d'ací baix — davant del dubte, deixa-la exactament igual que a l'original.

REGLES (aplica en aquest ordre):

1. LOCUCIONS FIXES
   a on → on | hui dia → avui dia
   ha sigut → ha estat | han sigut → han estat | havia sigut → havia estat

2. DEMOSTRATIUS
   este → aquest | esta → aquesta | estos → aquests | estes → aquestes
   eixe → aqueix | eixa → aqueixa | eixos → aqueixos | eixes → aqueixes
   ("eixe" és el demostratiu de SEGON grau (prop de qui escolta) — mai el
   confons amb "este" (primer grau), encara que en valencià col·loquial es
   difuminen: cada un té el seu equivalent oriental propi, no comparteixen
   forma)
   (revisa TOTES les aparicions dins de la frase, no només la primera —
   si la frase és llarga o té diverses clàusules, és fàcil deixar-ne una
   sense convertir)

3. POSSESSIUS
   meua → meva | meues → meves | teua → teva | teues → teves | seua → seva | seues → seves

4. INFINITIUS IRREGULARS
   traure → treure | tindre → tenir | vindre → venir | vore → veure | eixir → sortir

5. MORFOLOGIA VERBAL
   Pres. subj. sg:    puga→pugui, tinga→tingui, vinga→vingui, vaja→vagi, siga→sigui, haja→hagi
   Pres. subj. pl:    puguen→puguin, tinguen→tinguin, siguen→siguin, hagen→hagin
   Imperf. subj. — regla general de sufixos, aplica a QUALSEVOL verb, no només als exemples:
     -era → -és      (haguera→hagués, poguera→pogués, tinguera→tingués, fora→fos)
     -eres → -essis
     -érem → -éssim
     -éreu → -éssiu
     -eren → -essin  (hagueren→haguessin, pogueren→poguessin)
   Imperf. indicatiu, 1a i 2a persona plural — accent tancat (occidental)
   → accent obert (oriental), regla general confirmada al diccionari
   (11/11 casos):
     -éiem → -èiem   (déiem→dèiem, quéiem→quèiem)
     -éieu → -èieu   (quéieu→quèieu)
   Participi ser:     sigut → estat
   Incoatius -ix:     establix→estableix, servix→serveix

6. NUMERALS
   huit → vuit — és una arrel, no només una paraula solta: aplica-la també
   dins de compostos amb guionet (huitanta→vuitanta, huit-cents→vuit-cents,
   seixanta-huit→seixanta-vuit, huitanta-huitè→vuitanta-vuitè...).
   díhuit → divuit (excepció: no és un compost amb "huit", és paraula pròpia)
   Ordinals acabats en -é → -è (regla general, aplica a QUALSEVOL ordinal):
     cinqué→cinquè, sisé→sisè, sété→setè, vuité→vuitè, nové→novè, desé→desè,
     dotzé→dotzè, vinté→vintè, trenté→trentè, quaranté→quarantè, centé→centè...

7. NUMERAL "DOS" — CONCORDANÇA DE GÈNERE
   En valencià, "dos" és la forma natural i preferent tant en masculí com
   en femení (l'AVL també admet "dues" com a variant formal). En català
   oriental (IEC), la distinció de gènere és obligatòria: "dos" NOMÉS per
   a masculí, "dues" NOMÉS per a femení — fer servir "dos" en femení es
   considera un calc incorrecte del castellà.
   Si "dos" acompanya un nom FEMENÍ, canvia'l a "dues":
     dos xiques → dues xiques | dos cadires → dues cadires
   Si acompanya un nom MASCULÍ, no canvia:
     dos xics → dos xics | dos llibres → dos llibres
   Comprova el gènere real del nom que seguix "dos" abans de decidir —no
   és una substitució de text fixa, depén de cada frase.

8. GENTILICIS DE PAÍS O IDIOMA
   Acabats en -és → -ès (regla general, molt productiva en el diccionari):
     francés→francès, anglés→anglès, holandés→holandès, danés→danès,
     xinés→xinès, japonés→japonès, escocés→escocès, portugués→portuguès,
     alemany/italià no canvien (no acaben en -és).
   Alguns noms comuns segueixen el mateix patró: interés→interès,
   imprés→imprès, entremés→entremès, malentés→malentès, sobrepés→sobrepès.
   ATENCIÓ: NO ho apliques a "és" (verb ser, 3a sg) ni a "més" (quantitat)
   — estes dos paraules es queden EXACTAMENT igual en els dos dialectes.

9. PRETÈRIT PERFET SIMPLE → PERIFRÀSTIC
   El valencià fa servir sovint la forma simple del pretèrit (verb+à/-aren
   etc.); l'oriental estàndard prefereix la forma perifràstica (va/van +
   infinitiu). Aplica-ho a QUALSEVOL verb en pretèrit simple, no només als
   exemples:
     passà → va passar | celebrà → va celebrar | quedaren → van quedar
     transformaren → es van transformar | parlà → va parlar
   Regla general: verb-à (3a sg) → va + infinitiu; verb-aren (3a pl) →
   van + infinitiu (i igual per a la resta de persones: -í→vaig, -ares→vas,
   -àrem→vam, -àreu→vau).

10. LÈXIC (els mots del bloc [VOCABULARI] de la frase confirmen les equivalències)
   hui → avui | vesprada → tarda | faena → feina | xiquet → nen | xiqueta → nena

EXEMPLE:
Entrada: [VOCABULARI: faena=feina, xiquet=nen]
Frase a traduir: La faena d'este xiquet hui ha sigut molt bona.
Resposta correcta: La feina d'aquest nen avui ha estat molt bona."""


def construeix_prompt_usuari(frase: str) -> str:
    """
    Construeix el prompt d'usuari amb glossari dinàmic en format segur.
    Normalitza apòstrofs de l'entrada abans de processar i enviar al model.
    """
    frase_norm = normalitza_apostrofa(frase)
    glossari = glossari_per_frase(frase_norm, LEXIC_LOOKUP)
    if glossari:
        return f"{glossari}\nFrase a traduir: {frase_norm}"
    return f"Frase a traduir: {frase_norm}"


# ─── COMET (opcional) ─────────────────────────────────────────────────────────

def carrega_comet_model(nom_model: str = COMET_MODEL_NAME):
    global _comet_model
    if _comet_model is not None:
        return _comet_model

    try:
        from comet import download_model, load_from_checkpoint
    except ImportError:
        print(
            "\nERROR: No s'ha pogut instal·lar unbabel-comet automàticament.\n"
            "El paquet requereix Python 3.10 o 3.11 i no és compatible amb Python 3.13.\n"
            "Solució: crea un entorn nou i executa des d'allà:\n"
            "  conda create -n comet_env python=3.10\n"
            "  conda activate comet_env\n"
            "  pip install sacrebleu requests unbabel-comet\n"
            "  python evalua_models.py --model regles --comet\n"
        )
        sys.exit(1)

    print(f"Carregant model COMET '{nom_model}' (només la 1a vegada baixa ~1-2 GB)...")
    ruta_model = download_model(nom_model)
    _comet_model = load_from_checkpoint(ruta_model)
    return _comet_model


# ─── Mètriques ────────────────────────────────────────────────────────────────

def calcula_metriques(hipotesi: str, referencia: str) -> dict:
    """Calcula BLEU, chrF i chrF++ per a un parell hipòtesi/referència.
    Normalitza apòstrofs abans de comparar per no penalitzar diferències tipogràfiques.
    """
    hip = normalitza_apostrofa(hipotesi.strip().lower())
    ref = normalitza_apostrofa(referencia.strip().lower())
    # Usa les versions normalitzades també per BLEU/chrF
    hipotesi = normalitza_apostrofa(hipotesi.strip())
    referencia = normalitza_apostrofa(referencia.strip())

    try:
        bleu_score = sacrebleu.sentence_bleu(hipotesi, [referencia]).score
    except Exception:
        bleu_score = 0.0

    try:
        chrf_score = sacrebleu.sentence_chrf(hipotesi, [referencia]).score
    except Exception:
        chrf_score = 0.0

    try:
        chrf_pp_score = sacrebleu.sentence_chrf(hipotesi, [referencia], word_order=2).score
    except Exception:
        chrf_pp_score = 0.0

    return {
        "bleu":    round(bleu_score, 2),
        "chrf":    round(chrf_score, 2),
        "chrf_pp": round(chrf_pp_score, 2),
        "exacte":  (hip == ref),
    }


# ─── Adaptadors de model ──────────────────────────────────────────────────────

def tradueix_claude(frase: str, api_key: str) -> str:
    """Tradueix amb Claude Sonnet via API Anthropic (opcional, requereix crèdit)."""
    try:
        import anthropic
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
        import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    missatge = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT_BASE,                  # <-- camp system separat
        messages=[
            {"role": "user", "content": construeix_prompt_usuari(frase)}
        ]
    )
    return missatge.content[0].text.strip()


def ollama_disponible() -> bool:
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def ollama_models_instal_lats() -> list[str]:
    """Retorna els noms dels models que ja hi ha baixats a Ollama."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def tradueix_ollama(frase: str, model: str = "llama3.1:8b", timeout: int = 120,
                     system: str = SYSTEM_PROMPT_BASE) -> str:
    """Tradueix amb un model local via Ollama."""
    payload = {
        "model":  model,
        "system": system,                           # <-- camp system separat
        "prompt": construeix_prompt_usuari(frase),  # <-- glossari dinàmic aquí
        "stream": False,
        # "think": false -- desactiva el "extended thinking" dels models que
        # ho suporten (p.ex. gemma4, hereu de Gemini 3). Sense açò, el model
        # gasta TOT el "num_predict" raonant internament i el camp
        # "response" torna buit -- confirmat amb gemma4:12b (0.00 BLEU/60,
        # "hipotesi": "" en les 60 frases, tot i que el servidor Ollama
        # responia 200 OK generant ~157-158 tokens -- eixe raonament, no la
        # traducció). Inofensiu per a qwen/gemma3, que no tenen "thinking":
        # el paràmetre simplement s'ignora.
        "think": False,
        "options": {
            "temperature": 0,    # reproductibilitat del benchmark
            "num_predict": 200,
        }
    }
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload, timeout=timeout
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: no es pot connectar amb Ollama (està engegat 'ollama serve'?)"
    except Exception as e:
        return f"ERROR: {e}"


def tradueix_openai(frase: str, url: str, model: str, mode: str = "regles",
                     system: str = SYSTEM_PROMPT_BASE, timeout: int = 120) -> str:
    """Tradueix cridant un servidor compatible amb l'API de chat d'OpenAI
    (p.ex. vLLM servint un model que Ollama no gestiona bé, com
    BSC-LT/salamandraTA-7b-instruct -- el propi model card ho desaconsella
    explícitament per problemes de compatibilitat que degraden el
    rendiment). Tres maneres de construir el prompt:

      - 'regles': el mateix system prompt amb les regles dialectals i el
        glossari dinàmic que s'usa amb Ollama -- per a comparar en igualtat
        de condicions amb qwen/gemma. CONFIRMAT que no funciona amb
        SalamandraTA: en lloc d'aplicar les regles, el model repeteix
        fragments literals de les pròpies instruccions com si foren la
        traducció (p.ex. torna "ELISION (només 'de', 'la', 'el')..." en
        compte de traduir la frase) -- no sap què fer amb una instrucció
        complexa en el system prompt, perquè no és un instructor de
        propòsit general, és un model de traducció.
      - 'traduccio': la plantilla oficial de traducció d'un model MT
        instructiu tipus SalamandraTA ("Translate the following text from
        X into Y..."), sense cap regla explícita -- per a vore si el
        model ja sap fer la conversió de variant tot sol, sense que li ho
        expliquem. SalamandraTA tracta valencià i català com una sola
        entrada ("Catalan (and Catalan-Valencian variety)"), així que
        aquest mode NO té garantit que sàpia distingir la direcció.
        Resultat real: funciona (83,54 BLEU) però per davall de qwen/gemma.
      - 'traduccio_lexic': la MATEIXA plantilla nativa de 'traduccio', però
        afegint-hi el glossari dinàmic curt en format [VOCABULARI: ...]
        (el mateix que ja usen qwen/gemma, dissenyat perquè el model NO el
        repetisca a la resposta) -- a diferència de 'regles', que li dona
        les 10 categories de regles gramaticals senceres en un system
        prompt llarg (~2200 tokens) que confonia el model, este mode li
        dona només 2-3 paraules concretes rellevants per a EIXA frase, dins
        de la mateixa plantilla curta que ja sap seguir. Hipòtesi a
        comprovar: potser el problema no era "no pot seguir cap pista",
        sinó "no sap què fer amb un bloc d'instruccions llarg i en un rol
        'system' que no és el seu format d'entrenament".
    """
    if mode in ("traduccio", "traduccio_lexic"):
        pista = ""
        if mode == "traduccio_lexic":
            frase = normalitza_apostrofa(frase)
            glossari = glossari_per_frase(frase, LEXIC_LOOKUP)
            if glossari:
                pista = f" {glossari}"
        prompt = (
            "Translate the following text from Catalan (Valencian variety) "
            f"into Catalan.{pista}\n"
            f"Catalan (Valencian variety): {frase}\nCatalan:"
        )
        messages = [{"role": "user", "content": prompt}]
    else:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": construeix_prompt_usuari(frase)},
        ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 200,
    }
    try:
        r = requests.post(
            f"{url.rstrip('/')}/chat/completions",
            json=payload, timeout=timeout
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: no es pot connectar amb el servidor OpenAI-compatible (està engegat vLLM?)"
    except Exception as e:
        return f"ERROR: {e}"


# ─── NLLB-200 (opcional) ──────────────────────────────────────────────────────
# A diferència de Claude/Ollama (una petició de xarxa per frase), NLLB es
# carrega en memòria local i tradueix TOT el benchmark en lots abans d'entrar
# al pipeline d'avalua_model() — el batching és el que fa que valga la pena
# la GPU amb un seq2seq xicotet com aquest.

def instala_nllb_si_cal():
    """Instal·la transformers i torch si no hi són (igual que sacrebleu/requests
    a instala_si_cal(); torch pot trigar una mica més a baixar-se)."""
    import subprocess
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        print("Instal·lant transformers i torch (necessaris per a NLLB-200, pot trigar)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "transformers", "torch", "-q"])


def carrega_model_nllb(model_id: str = NLLB_MODEL_NAME):
    """Carrega el model i el tokenizer de NLLB-200 una sola vegada (caché
    global, igual que carrega_comet_model). Detecta CUDA automàticament; si
    no n'hi ha, avisa i continua per CPU sense fallar."""
    global _nllb_model, _nllb_tokenizer, _nllb_device

    if _nllb_model is not None and _nllb_tokenizer is not None:
        return _nllb_model, _nllb_tokenizer, _nllb_device

    instala_nllb_si_cal()
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _nllb_device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\nCarregant NLLB-200: {model_id}")
    print(f"  Device: {_nllb_device}")
    if _nllb_device == "cuda":
        try:
            nom_gpu = torch.cuda.get_device_name(0)
            vram_lliure, vram_total = torch.cuda.mem_get_info()
            print(
                f"  GPU: {nom_gpu} — {vram_lliure / 1024**3:.1f} GiB lliures "
                f"de {vram_total / 1024**3:.1f} GiB"
            )
        except Exception:
            pass
    else:
        print("  AVÍS: no s'ha detectat CUDA; NLLB anirà per CPU (més lent, "
              "sobretot amb els models 1.3B/3.3B).")

    _nllb_tokenizer = AutoTokenizer.from_pretrained(model_id)
    _nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_id).to(_nllb_device)
    _nllb_model.eval()

    print(f"  Model carregat: {model_id}\n")
    return _nllb_model, _nllb_tokenizer, _nllb_device


def _lang_id_nllb(tokenizer, lang_code: str) -> int:
    """El mètode per obtenir l'id del token de llengua ha canviat entre
    versions de transformers; es proven totes dues."""
    try:
        return tokenizer.convert_tokens_to_ids(lang_code)
    except Exception:
        return tokenizer.lang_code_to_id[lang_code]


def tradueix_nllb(
    frase: str,
    model_id: str = NLLB_MODEL_NAME,
    src_lang: str = NLLB_SRC_LANG,
    tgt_lang: str = NLLB_TGT_LANG,
    device: str | None = None,
) -> str:
    """Tradueix una única frase amb NLLB-200. Per al benchmark complet és
    molt més eficient tradueix_nllb_lot(); aquesta queda per a ús solt."""
    import torch

    model, tokenizer, dev = carrega_model_nllb(model_id)
    dev = device or dev

    tokenizer.src_lang = src_lang
    entrada = tokenizer(frase, return_tensors="pt").to(dev)
    tgt_lang_id = _lang_id_nllb(tokenizer, tgt_lang)

    with torch.no_grad():
        sortida = model.generate(**entrada, forced_bos_token_id=tgt_lang_id, max_length=200)
    return tokenizer.batch_decode(sortida, skip_special_tokens=True)[0].strip()


def tradueix_nllb_lot(
    frases: list[str],
    model_id: str = NLLB_MODEL_NAME,
    src_lang: str = NLLB_SRC_LANG,
    tgt_lang: str = NLLB_TGT_LANG,
    batch_size: int = 16,
) -> list[str]:
    """Tradueix una llista de frases en lots — el que aprofita de veritat la
    GPU amb un model xicotet com NLLB. Retorna les traduccions en el mateix
    ordre que `frases`."""
    import torch

    model, tokenizer, dev = carrega_model_nllb(model_id)
    tokenizer.src_lang = src_lang
    tgt_lang_id = _lang_id_nllb(tokenizer, tgt_lang)

    resultats: list[str] = []
    n_lots = (len(frases) + batch_size - 1) // batch_size
    for i in range(0, len(frases), batch_size):
        lot = frases[i:i + batch_size]
        entrada = tokenizer(lot, return_tensors="pt", padding=True, truncation=True).to(dev)
        with torch.no_grad():
            sortida = model.generate(**entrada, forced_bos_token_id=tgt_lang_id, max_length=200)
        resultats.extend(t.strip() for t in tokenizer.batch_decode(sortida, skip_special_tokens=True))
        print(f"  NLLB: lot {i // batch_size + 1}/{n_lots} traduït")

    return resultats


def prepara_traductor_nllb(benchmark: list[dict], args) -> "callable":
    """Pre-tradueix tot el benchmark en lots i retorna una funció
    frase -> traducció que simplement consulta la memòria cau. Així
    avalua_model() no ha de canviar gens: per a NLLB rep una funció
    d'una sola frase igual que per a Claude/Ollama, però la faena grossa
    (la crida batejada al model) ja s'ha fet abans."""
    frases = [normalitza_apostrofa(item["occidental"]) for item in benchmark]
    traduccions = tradueix_nllb_lot(
        frases,
        model_id=args.nllb_model,
        src_lang=args.nllb_src_lang,
        tgt_lang=args.nllb_tgt_lang,
        batch_size=args.nllb_batch_size,
    )
    cache = dict(zip(frases, traduccions))
    return lambda frase: cache.get(normalitza_apostrofa(frase), "")


# ─── Sistema de regles (baseline) ────────────────────────────────────────────
# Construït en dos nivells:
#   1. Substitucions morfològiques codificades a mà (alta precisió, ordre important)
#   2. Lookup lèxic des de lexico_fiable.json (cobertura reduida, nomes revisat a ma)

def construeix_subs_morfologiques() -> list[tuple[str, str]]:
    """
    Retorna la llista ordenada de substitucions morfològiques codificades.
    S'apliquen ABANS del lèxic perquè algunes formen part de locucions fixes.
    """
    return [
        # — Locucions fixes (ordre crític: primer les més llargues) —
        (r'\ba on\b',           'on'),
        (r'\bhui dia\b',        'avui dia'),
        (r'\bde vesprada\b',    'a la tarda'),
        (r'\bha sigut\b',       'ha estat'),
        (r'\bhan sigut\b',      'han estat'),
        (r'\bhavia sigut\b',    'havia estat'),
        (r'\bhavien sigut\b',   'havien estat'),

        # — Demostratius —
        # (?<!\w) en lloc de \b per gestionar l'apostrofat (d'este, l'esta…)
        # Substituts en minúscules: _substitueix_conservant_majuscules s'encarrega
        # de capitalitzar si l'original comença amb majúscula.
        (r"(?<!\w)[Ee]ste(?!\w)",   'aquest'),
        (r"(?<!\w)[Ee]sta(?!\w)",   'aquesta'),
        (r"(?<!\w)[Ee]stos(?!\w)",  'aquests'),
        (r"(?<!\w)[Ee]stes(?!\w)",  'aquestes'),

        # — Possessius —
        (r'\bmeua\b',   'meva'),
        (r'\bmeues\b',  'meves'),
        (r'\bteua\b',   'teva'),
        (r'\bteues\b',  'teves'),
        (r'\bseua\b',   'seva'),
        (r'\bseues\b',  'seves'),

        # — Pronom personal —
        (r'\bvos\b',    'us'),
        (r'\bvosatres\b', 'vosaltres'),
        (r'\bvosatros\b', 'vosaltres'),

        # — Temporal —
        (r'\bhui\b',        'avui'),
        (r'\bvesprada\b',   'tarda'),

        # — Infinitius irregulars —
        (r'\btraure\b',  'treure'),
        (r'\btindre\b',  'tenir'),
        (r'\bvindre\b',  'venir'),
        (r'\bvore\b',    'veure'),
        (r'\beixir\b',   'sortir'),
        (r'\bvaldre\b',  'valer'),

        # — Subjuntiu present (formes fortes: cal fer-ho per paraula completa) —
        (r'\bpuga\b',    'pugui'),
        (r'\bpuguen\b',  'puguin'),
        (r'\btinga\b',   'tingui'),
        (r'\btinguen\b', 'tinguin'),
        (r'\bvinga\b',   'vingui'),
        (r'\bvinguen\b', 'vinguin'),
        (r'\bvaja\b',    'vagi'),
        (r'\bvagen\b',   'vagin'),
        (r'\bdiga\b',    'digui'),
        (r'\bdiguen\b',  'diguin'),
        (r'\bfaga\b',    'faci'),
        (r'\bfaguen\b',  'facin'),
        (r'\bvullga\b',  'vulgui'),
        (r'\bvullguen\b','vulguin'),
        (r'\bsiga\b',    'sigui'),
        (r'\bsiguen\b',  'siguin'),
        (r'\bhaja\b',    'hagi'),
        (r'\bhagen\b',   'hagin'),

        # — Subjuntiu imperfet —
        (r'\bhaguera\b',   'hagués'),
        (r'\bhagueres\b',  'haguessis'),
        (r'\bhagueren\b',  'haguessin'),
        (r'\bhaguérem\b',  'haguéssim'),
        (r'\bhaguéreu\b',  'haguéssiu'),
        (r'\bpoguera\b',   'pogués'),
        (r'\bpogueres\b',  'poguessis'),
        (r'\bpogueren\b',  'poguessin'),
        (r'\btinguera\b',  'tingués'),
        (r'\btingueres\b', 'tinguessis'),
        (r'\btingueren\b', 'tinguessin'),
        (r'\bfórem\b',     'fóssim'),
        (r'\bfóreu\b',     'fóssiu'),
        (r'\bfores\b',     'fossis'),
        (r'\bforen\b',     'fossin'),

        # — Participi 'ser' —
        (r'\bsigut\b',  'estat'),

        # — Morfologia -ix → -eix —
        (r'\bestablix\b',  'estableix'),
        (r'\bservix\b',    'serveix'),
        (r'\bix\b',        'surt'),

        # — Numerals —
        (r'\bhuit-cents\b',   'vuit-cents'),
        (r'\bhuit-centes\b',  'vuit-centes'),
        (r'\bhuitanta\b',     'vuitanta'),
        (r'\bhuit\b',         'vuit'),

        # — Léxic freqüent no present al JSON —
        (r'\bxiquet\b',   'nen'),
        (r'\bxiqueta\b',  'nena'),
        (r'\bxiquets\b',  'nens'),
        (r'\bxiquetes\b', 'nenes'),
        (r'\bfaena\b',    'feina'),
        (r'\bfaenes\b',   'feines'),
        (r'\bya\b',       'ja'),
        (r'\byo\b',       'jo'),
    ]


def construeix_subs_lexic(lookup: dict) -> list[tuple[str, str]]:
    """
    Construeix substitucions regex a partir del lookup lèxic.
    Usa sempre la primera forma catalana com a traducció (la més freqüent/normativa).
    Ordena per longitud descendent per evitar substitucions parcials.
    """
    subs = []
    for forma_val, formes_cat in lookup.items():
        if not formes_cat:
            continue
        patro = r'\b' + re.escape(forma_val) + r'\b'
        subs.append((patro, formes_cat[0]))

    # Formes més llargues primer per evitar substitucions parcials
    subs.sort(key=lambda x: len(x[0]), reverse=True)
    return subs


def _substitueix_conservant_majuscules(patro: str, substitut: str, text: str) -> str:
    """
    Substitueix `patro` per `substitut` conservant la capitalització original:
    - PARAULA → SUBSTITUT (tot majúscules)
    - Paraula → Substitut (primera lletra majúscula)
    - paraula → substitut (tot minúscules)
    """
    def reemplaca(m):
        original = m.group(0)
        if original.isupper():
            return substitut.upper()
        if original[0].isupper():
            return substitut[0].upper() + substitut[1:]
        return substitut
    return re.sub(patro, reemplaca, text, flags=re.IGNORECASE)


# Preconstruïm les llistes una sola vegada
_SUBS_MORFOLOGIQUES = construeix_subs_morfologiques()
_SUBS_LEXIC         = construeix_subs_lexic(LEXIC_LOOKUP)


def tradueix_regles(frase: str) -> str:
    """
    Sistema de traducció basat en regles (baseline).
    Normalitza apòstrofs, aplica primer les substitucions morfològiques
    (codificades, alta precisió) i després el lèxic complet del JSON.
    Conserva la capitalització original en ambdós passos.
    """
    resultat = normalitza_apostrofa(frase)

    # Pas 1: morfologia
    for patro, substitut in _SUBS_MORFOLOGIQUES:
        resultat = _substitueix_conservant_majuscules(patro, substitut, resultat)

    # Pas 2: lèxic del JSON
    for patro, substitut in _SUBS_LEXIC:
        resultat = _substitueix_conservant_majuscules(patro, substitut, resultat)

    return resultat


def tradueix_traductor_nou(frase: str) -> str:
    """
    Adaptador cap al paquet `traductor/` (arrel del projecte, fora
    d'03_seleccion_de_modelo/) -- el motor de regles nou basat en tokens amb flags
    `is_translated`/`is_proper_noun`, en compte de les substitucions regex
    sobre el text sencer que fa `tradueix_regles()` de dalt ("Sistema_de_
    Regles"). Import fet dins de la funció (peresós) perquè
    evalua_models.py no ha de dependre del paquet `traductor/` per a la
    resta d'usos -- només es carrega quan es tria `--model traductor`.
    Vore final/05_motor_reglas/README.md per l'arquitectura completa.

    `traductor/` viu a l'arrel del projecte (germana d'esta carpeta,
    03_seleccion_de_modelo/), no dins d'ella -- s'afig eixa arrel a sys.path ací
    perquè l'script sempre s'ha executat des de dins d'03_seleccion_de_modelo/
    (vore els exemples d'ús dalt), on Python no la troba per defecte.
    """
    import sys
    from pathlib import Path

    arrel_projecte = str(Path(__file__).resolve().parent.parent)
    if arrel_projecte not in sys.path:
        sys.path.insert(0, arrel_projecte)

    from traductor.translate import translate
    return translate(frase)


# ─── Pipeline d'avaluació ─────────────────────────────────────────────────────

def avalua_model(
    nom_model: str,
    funcio_traduccio,
    benchmark: list[dict],
    delay: float = 1.0,
    usa_comet: bool = False,
    comet_model_name: str = COMET_MODEL_NAME,
) -> dict:
    """
    Avalua un model sobre totes les frases del benchmark.
    Retorna el resultat complet amb mètriques.
    """
    print(f"\n{'='*60}")
    print(f"AVALUANT: {nom_model}")
    print(f"{'='*60}")

    resultats = []
    errors    = 0

    for i, item in enumerate(benchmark, 1):
        # Normalitza apòstrofs en entrada i referència (el benchmark pot tenir ´ en lloc de ')
        frase_occ  = normalitza_apostrofa(item["occidental"])
        referencia = normalitza_apostrofa(item["oriental"])

        print(f"[{i:02d}/{len(benchmark)}] {frase_occ[:55]}...")

        try:
            hipotesi = neteja_preambul(funcio_traduccio(frase_occ))
        except Exception as e:
            print(f"  ERROR: {e}")
            hipotesi = frase_occ  # fallback: retorna l'original
            errors += 1

        metriques = calcula_metriques(hipotesi, referencia)

        resultats.append({
            "id":         item["id"],
            "categoria":  item.get("categoria",  "sense_categoria"),
            "dificultat": item.get("dificultat", "sense_dificultat"),
            "occidental": frase_occ,
            "referencia": referencia,
            "hipotesi":   hipotesi,
            "regles":     item.get("regles", []),
            **metriques
        })

        print(
            f"  BLEU={metriques['bleu']:5.1f}  "
            f"chrF={metriques['chrf']:5.1f}  "
            f"{'✓ EXACTE' if metriques['exacte'] else ''}"
        )

        if i < len(benchmark):
            time.sleep(delay)

    # COMET: molt més eficient en batch que una a una
    if usa_comet:
        print("Calculant COMET (pot trigar la 1a vegada)...")
        model_comet = carrega_comet_model(comet_model_name)
        dades_comet = [
            {"src": r["occidental"], "mt": r["hipotesi"], "ref": r["referencia"]}
            for r in resultats
        ]
        try:
            sortida = model_comet.predict(dades_comet, batch_size=8, gpus=0, progress_bar=False)
            for r, score in zip(resultats, sortida["scores"]):
                r["comet"] = round(score * 100, 2)
        except Exception as e:
            print(f"  AVÍS: no s'ha pogut calcular COMET: {e}")
            for r in resultats:
                r["comet"] = None

    # Agregació global
    bleu_mitja    = sum(r["bleu"]    for r in resultats) / len(resultats)
    chrf_mitja    = sum(r["chrf"]    for r in resultats) / len(resultats)
    chrf_pp_mitja = sum(r["chrf_pp"] for r in resultats) / len(resultats)
    exactes       = sum(1 for r in resultats if r["exacte"])
    comet_scores  = [r["comet"] for r in resultats if usa_comet and r.get("comet") is not None]
    comet_mitja   = round(sum(comet_scores) / len(comet_scores), 2) if comet_scores else None

    # Per categoria
    per_cat = {}
    for cat in set(r["categoria"] for r in resultats):
        items_cat = [r for r in resultats if r["categoria"] == cat]
        entry = {
            "n":      len(items_cat),
            "bleu":   round(sum(r["bleu"] for r in items_cat) / len(items_cat), 2),
            "chrf":   round(sum(r["chrf"] for r in items_cat) / len(items_cat), 2),
            "exactes": sum(1 for r in items_cat if r["exacte"]),
        }
        cat_comet = [r["comet"] for r in items_cat if r.get("comet") is not None]
        if cat_comet:
            entry["comet"] = round(sum(cat_comet) / len(cat_comet), 2)
        per_cat[cat] = entry

    # Per dificultat
    per_dif = {}
    for dif in set(r["dificultat"] for r in resultats):
        items_dif = [r for r in resultats if r["dificultat"] == dif]
        per_dif[dif] = {
            "n":    len(items_dif),
            "bleu": round(sum(r["bleu"] for r in items_dif) / len(items_dif), 2),
            "chrf": round(sum(r["chrf"] for r in items_dif) / len(items_dif), 2),
        }

    resum = {
        "model":          nom_model,
        "timestamp":      datetime.now().isoformat(),
        "n_frases":       len(resultats),
        "errors":         errors,
        "bleu_mitja":     round(bleu_mitja, 2),
        "chrf_mitja":     round(chrf_mitja, 2),
        "chrf_pp_mitja":  round(chrf_pp_mitja, 2),
        "comet_mitja":    comet_mitja,
        "exactes":        exactes,
        "exactes_pct":    round(exactes / len(resultats) * 100, 1),
        "per_categoria":  per_cat,
        "per_dificultat": per_dif,
        "resultats":      resultats,
    }

    print(f"\n--- RESUM {nom_model} ---")
    print(f"BLEU:    {bleu_mitja:.2f}")
    print(f"chrF:    {chrf_mitja:.2f}")
    print(f"chrF++:  {chrf_pp_mitja:.2f}")
    if comet_mitja is not None:
        print(f"COMET:   {comet_mitja:.2f}")
    print(f"Exactes: {exactes}/{len(resultats)} ({exactes/len(resultats)*100:.1f}%)")

    return resum


# ─── Informe comparatiu ───────────────────────────────────────────────────────

def genera_informe_comparatiu(resultats_models: list[dict]) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("INFORME COMPARATIU DE MODELS — BENCHMARK OCCIDENTAL↔ORIENTAL")
    lines.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 70)
    lines.append("")

    te_comet = any(r.get("comet_mitja") is not None for r in resultats_models)

    # Taula resum (ordenada per chrF descendent)
    capcalera = f"{'Model':<25} {'BLEU':>8} {'chrF':>8} {'chrF++':>8}"
    if te_comet:
        capcalera += f" {'COMET':>8}"
    capcalera += f" {'Exactes':>10}"
    lines.append(capcalera)
    lines.append("-" * (65 + (9 if te_comet else 0)))

    for r in sorted(resultats_models, key=lambda x: x["chrf_mitja"], reverse=True):
        fila = (
            f"{r['model']:<25} "
            f"{r['bleu_mitja']:>8.2f} "
            f"{r['chrf_mitja']:>8.2f} "
            f"{r['chrf_pp_mitja']:>8.2f} "
        )
        if te_comet:
            comet_txt = f"{r['comet_mitja']:.2f}" if r.get("comet_mitja") is not None else "-"
            fila += f"{comet_txt:>8} "
        fila += f"{r['exactes']:>4}/{r['n_frases']} ({r['exactes_pct']:>4.1f}%)"
        lines.append(fila)
    lines.append("")

    # Detall per categoria
    for r in resultats_models:
        lines.append(f"\n--- {r['model']} per categoria ---")
        for cat, m in sorted(r["per_categoria"].items()):
            fila = (
                f"  {cat:<30} n={m['n']:>2}  "
                f"BLEU={m['bleu']:>5.1f}  chrF={m['chrf']:>5.1f}"
            )
            if "comet" in m:
                fila += f"  COMET={m['comet']:>5.1f}"
            fila += f"  exactes={m['exactes']}"
            lines.append(fila)

    # Errors més comuns (chrF < 70)
    lines.append("\n--- ERRORS MÉS COMUNS ---")
    for r in resultats_models:
        errors_model = [
            item for item in r["resultats"]
            if not item["exacte"] and item["chrf"] < 70
        ]
        if errors_model:
            lines.append(f"\n{r['model']}:")
            for err in sorted(errors_model, key=lambda x: x["chrf"])[:5]:
                lines.append(f"  [{err['id']}] chrF={err['chrf']:.1f}")
                lines.append(f"    OCC: {err['occidental']}")
                lines.append(f"    REF: {err['referencia']}")
                lines.append(f"    HIP: {err['hipotesi']}")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # cal declarar-ho abans de qualsevol ús de OLLAMA_URL en esta funció
    # (p.ex. el default= de --ollama-url una mica més avall)
    global LEXIC_LOOKUP, LEXIC_ENTRADES, OLLAMA_URL

    parser = argparse.ArgumentParser(
        description="Benchmark de traducció occidental↔oriental"
    )
    parser.add_argument(
        "--model",
        choices=["claude", "ollama", "regles", "traductor", "nllb", "openai", "tots"],
        required=True,
        help="Model a avaluar"
    )
    parser.add_argument(
        "--api-key", default=os.getenv("ANTHROPIC_API_KEY"),
        help="API key d'Anthropic (opcional, només per a --model claude/tots)"
    )
    parser.add_argument(
        "--ollama-model", default=None,
        help="Model(s) d'Ollama a avaluar, separats per coma "
             "(p.ex. 'llama3.1:8b,qwen2.5:14b'). "
             "Si no es dona, s'autodetecten TOTS els models baixats a Ollama."
    )
    parser.add_argument(
        "--ollama-timeout", type=int, default=120,
        help="Segons d'espera per petició a Ollama (per defecte 120; puja-ho per a "
             "models grans com qwen2.5:14b si no hi ha GPU)"
    )
    parser.add_argument(
        "--ollama-url", default=OLLAMA_URL,
        help=f"URL base d'Ollama (per defecte {OLLAMA_URL}). Canvia-la per a "
             "llançar diverses instàncies en paral·lel, una per GPU/port."
    )
    parser.add_argument(
        "--openai-model", default=None,
        help="Nom/ruta del model tal com el serveix l'endpoint OpenAI-compatible "
             "(p.ex. BSC-LT/salamandraTA-7b-instruct servit amb vLLM). "
             "Requerit per a --model openai/tots."
    )
    parser.add_argument(
        "--openai-url", default="http://127.0.0.1:8000/v1",
        help="URL base (amb /v1) d'un servidor compatible amb l'API de chat "
             "d'OpenAI (vLLM, etc.)"
    )
    parser.add_argument(
        "--openai-mode", choices=["regles", "traduccio", "traduccio_lexic"], default="regles",
        help="'regles': mateix system prompt de regles dialectals que Ollama "
             "(confirmat que NO funciona amb SalamandraTA). 'traduccio': "
             "plantilla oficial de traducció del model, sense cap pista. "
             "'traduccio_lexic': la mateixa plantilla + glossari dinàmic "
             "curt [VOCABULARI: ...] (sense el system prompt llarg)."
    )
    parser.add_argument(
        "--openai-timeout", type=int, default=120,
        help="Segons d'espera per petició al servidor OpenAI-compatible"
    )
    parser.add_argument(
        "--benchmark",
        default=str(BENCHMARK_PATH),
        help="Fitxer JSON amb les frases de benchmark"
    )
    parser.add_argument(
        "--lexic",
        default=str(LEXIC_PATH),
        help="Fitxer JSON del lèxic (lexico_fiable.json)"
    )
    parser.add_argument(
        "--comet", action="store_true",
        help="Calcula també la mètrica COMET (opcional; baixa ~1-2 GB la 1a vegada)"
    )
    parser.add_argument(
        "--comet-model", default=COMET_MODEL_NAME,
        help=f"Nom del model COMET a Hugging Face (per defecte: {COMET_MODEL_NAME})"
    )
    parser.add_argument(
        "--nllb-model", default=NLLB_MODEL_NAME,
        help=f"Model id de NLLB-200 a Hugging Face (per defecte: {NLLB_MODEL_NAME}). "
             "Altres provats: facebook/nllb-200-distilled-1.3B, facebook/nllb-200-3.3B"
    )
    parser.add_argument(
        "--nllb-src-lang", default=NLLB_SRC_LANG,
        help=f"Codi FLORES-200 de l'idioma d'origen (per defecte: {NLLB_SRC_LANG})"
    )
    parser.add_argument(
        "--nllb-tgt-lang", default=NLLB_TGT_LANG,
        help=f"Codi FLORES-200 de l'idioma de destí (per defecte: {NLLB_TGT_LANG})"
    )
    parser.add_argument(
        "--nllb-batch-size", type=int, default=16,
        help="Mida del lot per a NLLB-200 (per defecte 16; puja-ho si hi ha prou VRAM, "
             "baixa-ho si peta per falta de memòria)"
    )
    args = parser.parse_args()

    # --lexic permet substituir el lexic per defecte (lexico_fiable.json) per
    # un altre fitxer amb el mateix esquema -- recarrega el global perque
    # construeix_prompt_usuari() el fa servir directament.
    lexic_path_args = Path(args.lexic)
    if lexic_path_args != LEXIC_PATH:
        LEXIC_LOOKUP, LEXIC_ENTRADES = carrega_lexic(lexic_path_args)

    # --ollama-url permet apuntar a una instància d'Ollama en un port propi
    # (necessari per a llançar-ne diverses en paral·lel, una per GPU).
    OLLAMA_URL = args.ollama_url

    # Carrega benchmark
    benchmark_path = Path(args.benchmark)
    if not benchmark_path.exists():
        print(f"ERROR: No es troba el benchmark a {benchmark_path}")
        sys.exit(1)

    with open(benchmark_path, encoding="utf-8") as f:
        benchmark = json.load(f)

    print(f"Benchmark carregat: {len(benchmark)} frases ({benchmark_path})")

    # Selecciona models
    models_a_avaluar = []

    if args.model in ("claude", "tots"):
        if not args.api_key:
            missatge = "Sense API key d'Anthropic: se salta Claude."
            if args.model == "claude":
                print("ERROR: Cal una API key d'Anthropic (--api-key o variable ANTHROPIC_API_KEY)")
                sys.exit(1)
            print(missatge)
        else:
            models_a_avaluar.append((
                "Claude_Sonnet_4.6",
                lambda f: tradueix_claude(f, args.api_key),
                1.5
            ))

    if args.model in ("nllb", "tots"):
        try:
            nom_nllb = f"NLLB_{args.nllb_model.rsplit('/', 1)[-1]}"
            funcio_nllb = prepara_traductor_nllb(benchmark, args)
            models_a_avaluar.append((nom_nllb, funcio_nllb, 0.0))
        except Exception as e:
            missatge = f"No s'ha pogut carregar NLLB-200 ({e})."
            if args.model == "nllb":
                print(f"ERROR: {missatge}")
                sys.exit(1)
            print(f"Se salta NLLB: {missatge}")

    if args.model in ("ollama", "tots"):
        if not ollama_disponible():
            missatge = "No es pot connectar amb Ollama a http://localhost:11434 (està engegat 'ollama serve'?)."
            if args.model == "ollama":
                print(f"ERROR: {missatge}")
                sys.exit(1)
            print(f"Se salta Ollama: {missatge}")
        else:
            if args.ollama_model:
                noms_ollama = [m.strip() for m in args.ollama_model.split(",") if m.strip()]
            else:
                noms_ollama = ollama_models_instal_lats()
                if not noms_ollama:
                    print("Ollama està engegat però no hi ha cap model baixat "
                          "(prova 'ollama pull llama3.1:8b').")

            for nom_model in noms_ollama:
                models_a_avaluar.append((
                    f"Ollama_{nom_model}",
                    lambda f, m=nom_model, s=SYSTEM_PROMPT_BASE: tradueix_ollama(
                        f, m, timeout=args.ollama_timeout, system=s
                    ),
                    0.2
                ))

    if args.model in ("openai", "tots"):
        if not args.openai_model:
            missatge = "Cal --openai-model per a --model openai (ruta/nom del model al servidor)."
            if args.model == "openai":
                print(f"ERROR: {missatge}")
                sys.exit(1)
            print(missatge)
        else:
            nom_curt = args.openai_model.rstrip("/").rsplit("/", 1)[-1]
            models_a_avaluar.append((
                f"OpenAI_{nom_curt}_{args.openai_mode}",
                lambda f: tradueix_openai(
                    f, args.openai_url, args.openai_model, args.openai_mode,
                    timeout=args.openai_timeout
                ),
                0.0
            ))

    if args.model in ("regles", "tots"):
        models_a_avaluar.append((
            "Sistema_de_Regles",
            tradueix_regles,
            0.0
        ))

    if args.model in ("traductor", "tots"):
        models_a_avaluar.append((
            "Traductor_Nou",
            tradueix_traductor_nou,
            0.0
        ))

    if not models_a_avaluar:
        print("No hi ha models per avaluar.")
        sys.exit(1)

    print(f"Models a avaluar: {', '.join(n for n, _, _ in models_a_avaluar)}")

    # Avaluació
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    tots_resultats = []

    for nom, funcio, delay in models_a_avaluar:
        resum = avalua_model(
            nom, funcio, benchmark, delay=delay,
            usa_comet=args.comet, comet_model_name=args.comet_model
        )
        tots_resultats.append(resum)

        # Guarda resultats individuals
        # Windows no permet ":" ni "(" ")" en noms de fitxer;
        # sense sanejar-ho, escriu els resultats com a alternate data stream ocult.
        nom_fitxer = re.sub(r'[<>:"/\\|?*]', "-", nom).replace(" ", "_")
        out_path = OUTPUT_DIR / f"benchmark_{nom_fitxer}_{ts}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(resum, f, ensure_ascii=False, indent=2)
        print(f"\nResultats guardats: {out_path}")

    # Informe comparatiu (si hi ha més d'un model)
    if len(tots_resultats) > 1:
        informe = genera_informe_comparatiu(tots_resultats)
        informe_path = OUTPUT_DIR / f"informe_comparatiu_{ts}.txt"
        with open(informe_path, "w", encoding="utf-8") as f:
            f.write(informe)
        print(f"\nInforme comparatiu: {informe_path}")
        print("\n" + informe)


if __name__ == "__main__":
    main()