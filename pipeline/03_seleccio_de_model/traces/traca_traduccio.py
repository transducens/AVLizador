"""
traca_traduccio.py -- Traça completa d'una traducció català -> valencià
(02/11/2026): què fa spaCy amb cada paraula, què troba en el diccionari,
què canvia cada capa del motor (i per què NO canvia una paraula que sí
que està en el diccionari) i, si hi ha paraules ambigües, tot el
postprocessat amb FLOR-760M: la decisió d'spaCy, les frases que rep el
model, les seues puntuacions i la tria final.

Fora del paquet a propòsit (decisió de l'usuari): no canvia cap
traducció. Reproduïx els mateixos passos que `translate_cat_val` (les
mateixes capes, en el mateix orde, amb el mateix model i el mateix
criteri) i comprova que la traducció final ix idèntica.

Ús (des de l'arrel del repo, amb el paquet instal·lat: `pip install -e ".[ml]"`):
    python pipeline/03_seleccio_de_model/traces/traca_traduccio.py "Un cop acabada la reunió, el noi marxarà."
    python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --fitxer frases.txt --html traces.html
    python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --benchmark manual --nomes-ambigues --html traces.html
    python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --benchmark homografs --ids HG001 HG002 --json traces.json
    python pipeline/03_seleccio_de_model/traces/traca_traduccio.py --motor "..."   # sense FLOR

L'HTML (`--html`) és una pàgina sola, sense servidor, feta a partir de
`visor_traces.html` amb les dades dins. El visor també obri un JSON de
`--json` (botó "Obrir JSON").
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from avlizador.traductor_cat_val.rules import (
    detokenize,
    homograf_compatible,
    pos_tagger,
    separa_prefix_elidit,
    separa_sufix_elidit,
    tokenize,
)
from avlizador.traductor_cat_val.rules.cat_val.conjugacions_dict import _descompon
from avlizador.traductor_cat_val.rules.cat_val.engine import RuleEngineInvers

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

DIR = Path(__file__).resolve().parent
PLANTILLA = DIR / "visor_traces.html"
DATA = Path(pos_tagger.__file__).resolve().parents[1] / "data"

CAPES = {
    "LexicInversRule": "Léxico",
    "ConjugacionsDictInversRule": "Conjugaciones",
    "PossessiusInversRule": "Posesivos",
    "NumeralsInversRule": "Numerales",
    "ConcordancaDosDuesInversRule": "dos/dues",
    "DemostratiusInversRule": "Demostrativos",
    "IncoatiusInversRule": "Incoativos",
    "AccentuacioInversRule": "Acentuación",
    "PerAInfinitiuInversRule": "per a + infinitivo",
}

# Rasgos de spaCy que el traductor copia al Token y usa (pos_tagger.etiqueta).
RASGOS_USADOS = {
    "POS": "categoría: filtros de las conjugaciones y de los homógrafos, incoativos, "
           "'per a' y la decisión de spaCy en las palabras ambiguas",
    "lemma": "incoativos (el lema tiene que acabar en -ir y estar en las conjugaciones)",
    "Gender": "concordancia del artículo tras cambiar una palabra y candidatos de FLOR",
    "VerbForm": "participios usados como adjetivo (conjugaciones) e infinitivo ('per a')",
}
RASGOS_CALCULADOS_NO_USADOS = {"Mood": "se guarda en el Token, pero ninguna regla de cat→val lo consulta"}


# ─── Recursos (se cargan una vez) ────────────────────────────────────────────

class Recursos:
    def __init__(self, amb_model: bool):
        self.motor = RuleEngineInvers()
        self.capes = {type(r).__name__: r for r in self.motor._regles}
        self.nlp = pos_tagger._carrega_spacy()
        self.lexic_cru = self._index(json.loads((DATA / "lexic_general.json").read_text(encoding="utf-8")))
        conj = json.loads((DATA / "conjugacions_dialectals.json").read_text(encoding="utf-8"))
        self.conj_cru = self._index(conj["entradas"])
        self.model = None
        self.criteri = None
        self.punts = None
        if amb_model:
            from avlizador.traductor_cat_val.model_llengua import Criteri
            from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts
            from avlizador.traductor_cat_val.model_llengua.puntuador import MODEL_PER_DEFECTE, ModelLlengua

            self.model = ModelLlengua(MODEL_PER_DEFECTE)
            self.criteri = Criteri()
            self.punts = carrega_punts()
        else:
            from avlizador.traductor_cat_val.model_llengua.punts import carrega_punts

            self.punts = carrega_punts()

    @staticmethod
    def _index(entrades: list[dict]) -> dict[str, list[dict]]:
        idx: dict[str, list[dict]] = {}
        for e in entrades:
            cat = (e.get("catalan") or "").strip().lower()
            if cat:
                idx.setdefault(cat, []).append(e)
        return idx


# ─── 1. spaCy ────────────────────────────────────────────────────────────────

def analisi_spacy(rec: Recursos, tokens) -> tuple[list[dict], dict[int, int]]:
    """Todas las palabras de spaCy con todos sus rasgos, y qué palabra de
    spaCy le toca a cada token nuestro. El emparejamiento es EL MISMO que
    `pos_tagger.etiqueta`: la primera palabra de spaCy con el mismo texto
    (no la de la misma posición)."""
    text = "".join(t.surface for t in tokens).replace("ʼ", "’")
    doc = rec.nlp(text)
    paraules = [{
        "i": d.i, "text": d.text, "inici": d.idx, "pos": d.pos_, "tag": d.tag_,
        "lema": d.lemma_, "rasgos": d.morph.to_dict(),
    } for d in doc]
    emparellament = {}
    for n, tok in enumerate(tokens):
        if not tok.surface[:1].isalpha():
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        buscada = (prefix_resta[1] if prefix_resta else tok.surface).replace("ʼ", "’")
        candidates = [buscada.lower()]
        sufix_resta = separa_sufix_elidit(buscada)
        if sufix_resta is not None:
            candidates.append(sufix_resta[0].lower())
        dt = next((d for b in candidates for d in doc if d.text.lower() == b), None)
        if dt is not None:
            emparellament[n] = dt.i
    return paraules, emparellament


# ─── 2. Diccionario ──────────────────────────────────────────────────────────

def _entrada_lexic(e: dict) -> dict:
    return {k: e[k] for k in ("id", "catalan", "valenciano", "categoria", "canonica", "problema",
                              "forma_problematica", "lemas", "tipo") if e.get(k) not in (None, "")}


def _entrada_conj(e: dict) -> dict:
    return {k: e[k] for k in ("id", "catalan", "valenciano", "verbo", "infinitiu_cat", "morfologia",
                              "morfologies", "problema", "canonica", "ambigu") if e.get(k) not in (None, "")}


def info_diccionari(rec: Recursos, tok) -> dict:
    """Qué hay de esta palabra en cada capa (lo que el motor ha cargado) y
    en los ficheros de datos (las entradas tal cual, también las que el
    motor descarta al cargar)."""
    superficie = tok.surface
    prefix_resta = separa_prefix_elidit(superficie)
    paraula = (prefix_resta[1] if prefix_resta else superficie).lower()
    L, C = rec.capes["LexicInversRule"], rec.capes["ConjugacionsDictInversRule"]
    capes = []
    if paraula in L._lookup:
        capa = {"capa": "Léxico", "candidat": L._lookup[paraula]}
        if paraula in L._homografs:
            capa["homografo_exige"] = sorted(L._homografs[paraula])
        capes.append(capa)
    if superficie.lower() in L._frases_per_inici:
        capes.append({"capa": "Léxico (frases)", "frases": [
            {"catala": " ".join(f), "valencia": v} for f, v in L._frases_per_inici[superficie.lower()]]})
    for prefix, arrel, sufix in _descompon(superficie):
        forma = C._lookup.get(arrel.lower())
        if forma is not None:
            capes.append({"capa": "Conjugaciones", "arrel": arrel, "candidat": forma,
                          "exige_verbo": arrel.lower() in C._amb_filtre_pos,
                          "prefix": prefix, "sufix": sufix})
            break
    for nom, clau in (("Posesivos", "PossessiusInversRule"), ("Numerales", "NumeralsInversRule"),
                      ("Demostrativos", "DemostratiusInversRule")):
        d = rec.capes[clau]._lookup
        if paraula in d:
            capes.append({"capa": nom, "candidat": d[paraula]})
    ambigua = rec.punts.get(paraula)
    return {
        "capes": capes,
        "ambigua": ({"tipus": ambigua["tipus"], "candidats": ambigua["candidats"]} if ambigua else None),
        "lexic_cru": [_entrada_lexic(e) for e in rec.lexic_cru.get(paraula, [])][:8],
        "conj_cru": [_entrada_conj(e) for e in rec.conj_cru.get(paraula, [])][:8],
    }


# ─── 3. Motor ────────────────────────────────────────────────────────────────

def traca_motor(rec: Recursos, tokens) -> list[dict]:
    """Aplica las capas como `RuleEngineInvers.tradueix_tokens` y anota qué
    cambia cada una (también los vecinos: artículo, contracciones)."""
    passos = []
    for regla in rec.motor._regles:
        abans = [t.translated for t in tokens]
        tokens[:] = regla.apply(tokens)
        if len(tokens) == len(abans):
            canvis = []
            for i, (t, a) in enumerate(zip(tokens, abans)):
                if t.translated == a or a.isspace() or (not a and not t.translated):
                    continue
                canvi = {"i": i, "abans": a, "despres": t.translated}
                if not t.translated:
                    canvi["nota"] = "se une a la palabra siguiente (apóstrofo o contracción)"
                canvis.append(canvi)
        else:  # una capa que cambia el número de tokens (no debería pasar)
            canvis = [{"i": -1, "abans": "".join(abans), "despres": detokenize(tokens)}]
        passos.append({"capa": CAPES.get(type(regla).__name__, type(regla).__name__), "canvis": canvis})
    return passos


def motiu_sense_canvi(rec: Recursos, tok, dicc: dict) -> str | None:
    """Por qué una palabra que está en el diccionario no ha cambiado
    (reproduce las condiciones de cada capa)."""
    L = rec.capes["LexicInversRule"]
    prefix_resta = separa_prefix_elidit(tok.surface)
    paraula = (prefix_resta[1] if prefix_resta else tok.surface).lower()
    for c in dicc["capes"]:
        if c["capa"] == "Léxico" and not homograf_compatible(tok.pos, paraula, L._homografs):
            return (f"Léxico: homógrafo; solo se cambia si spaCy da {'/'.join(c.get('homografo_exige', []))}, "
                    f"y spaCy da {tok.pos or '—'}")
        if c["capa"] == "Conjugaciones":
            if c["exige_verbo"]:
                es_part = tok.pos == "ADJ" and tok.verb_form == "Part"
                if tok.pos not in ("VERB", "AUX") and not es_part:
                    return (f"Conjugaciones: la forma también puede no ser verbo (o es de raíz distinta); "
                            f"solo se cambia si spaCy da VERB/AUX o participio, y spaCy da {tok.pos or '—'}")
            elif tok.pos == "PROPN":
                return "Conjugaciones: spaCy la etiqueta como nombre propio (PROPN) y no se cambia"
    if dicc["capes"] and tok.translated.lower() == tok.surface.lower():
        candidats = {str(c.get("candidat", "")).lower() for c in dicc["capes"]}
        if tok.surface.lower() in candidats:
            return "la traducción es igual que la palabra catalana"
    if dicc["ambigua"]:
        return "palabra ambigua: la decide el postprocesado (abajo)"
    if not dicc["capes"] and (dicc["lexic_cru"] or dicc["conj_cru"]):
        return ("está en los ficheros de datos, pero el motor la descarta al cargar (por ejemplo, "
                "varias traducciones sin ninguna canónica, o igual en los dos lados)")
    return None


# ─── 4. Postprocesado (FLOR) ─────────────────────────────────────────────────

def traca_postprocessat(rec: Recursos, text: str, tokens_motor) -> dict:
    from avlizador.traductor_cat_val.model_llengua import (
        CONCORDANCA_PER_DEFECTE, _valor, aplica_tries, puntua_punts, puntuacio, tradueix_cat_val_ml,
    )
    from avlizador.traductor_cat_val.model_llengua.punts import (
        _CATEGORIA_PER_POS, base_neutra, decisio_spacy, detecta, frases_candidates,
    )

    criteri = rec.criteri
    detectats = detecta(tokens_motor, rec.punts, criteri.tipus)
    # palabras de la lista que aparecen pero no llegan (las ha consumido otra capa)
    consumides = []
    indexs = {p.index for p in detectats}
    for i, tok in enumerate(tokens_motor):
        pr = separa_prefix_elidit(tok.surface)
        w = (pr[1] if pr else tok.surface).lower()
        if w in rec.punts and i not in indexs:
            consumides.append({"i": i, "paraula": tok.surface, "traduccio": tok.translated})
    if not detectats:
        return {
            "entra": False,
            "motiu": ("ninguna de las %d palabras ambiguas del léxico aparece en la frase" % len(rec.punts)
                      if not consumides else "las palabras ambiguas que aparecen ya las ha cambiado otra capa"),
            "consumides": consumides,
            "criteri": vars(criteri) if hasattr(criteri, "__dict__") else str(criteri),
            "punts": [],
        }

    tipus_model = tuple(t for t in criteri.tipus if t != "irresoluble" or criteri.model_irresolubles)
    text_motor, trobats = puntua_punts(text, rec.model, criteri.tipus, CONCORDANCA_PER_DEFECTE, tipus_model)
    final = aplica_tries(text_motor, trobats, criteri)
    referencia = tradueix_cat_val_ml(text, rec.model, criteri)[0]

    punts = []
    for punt in trobats:
        cat_spacy = _CATEGORIA_PER_POS.get(punt.pos)
        d_spacy = decisio_spacy(punt) if punt.tipus == "irresoluble" and criteri.spacy_irresolubles else None
        # todas las variantes que ve FLOR (las mismas llamadas; el modelo las tiene en caché)
        variants = {}
        if punt.puntuacions:
            base = base_neutra(rec.motor, text, [punt])
            for candidat, vs in frases_candidates(base, punt, CONCORDANCA_PER_DEFECTE).items():
                variants[candidat] = []
                for toks in vs:
                    frase = detokenize(toks)
                    lp, n = rec.model.logprob(frase)
                    variants[candidat].append({"frase": frase, "lp": round(lp, 3), "n": n,
                                               "triada": frase == punt.puntuacions[candidat]["frase"]})
        candidats = []
        for c in punt.candidats:
            d = punt.puntuacions.get(c)
            fila = {"candidat": c, "es_del_motor": c == punt.motor, "triat": c == punt.tria}
            if d:
                fila.update({"frase": d["frase"], "lp": round(d["lp"], 3), "n": d["n"],
                             "prior": round(d["prior"], 3), "puntuacio": round(puntuacio(d, criteri), 3),
                             "variants": variants.get(c, [])})
            else:
                fila["frase"] = punt.frases.get(c)
            candidats.append(fila)
        explicacio, diferencia = _explica(punt, criteri, cat_spacy, d_spacy, _valor)
        punts.append({
            "i": punt.index, "paraula": punt.paraula, "prefix": punt.prefix, "tipus": punt.tipus,
            "candidats_lexic": punt.candidats, "motor": punt.motor, "tria": punt.tria, "decidit": punt.decidit,
            "spacy": {"pos": punt.pos, "categoria": cat_spacy, "categoria_dialectal": punt.categoria,
                      "lectures": [sorted(l) for l in punt.lectures], "decisio": d_spacy},
            "candidats": candidats, "diferencia": diferencia, "marge": criteri.marge,
            "explicacio": explicacio,
        })
    return {
        "entra": True,
        "motiu": f"{len(trobats)} palabra(s) ambigua(s) del léxico en la frase",
        "consumides": consumides,
        "criteri": {"lam": criteri.lam, "norma": criteri.norma, "marge": criteri.marge,
                    "concordanca": CONCORDANCA_PER_DEFECTE, "model": rec.model.model_id,
                    "context": getattr(rec.model, "context", None),
                    "formula": "puntuació = lp − lam × prior (lp: log-probabilitat de la frase; "
                               "prior: log-probabilitat de la paraula sola; les dos, darrere del "
                               "paràgraf de context si n'hi ha)"},
        "punts": punts,
        "text_motor_base": text_motor,
        "final": final,
        "coincideix_amb_translate": final == referencia,
    }


def _explica(punt, criteri, cat_spacy, d_spacy, _valor) -> tuple[str, float | None]:
    if punt.decidit == "spacy":
        return (f"spaCy da {punt.pos} ({cat_spacy}), y la lectura dialectal es '{punt.categoria}': "
                f"ese sentido no es posible → se deja la palabra catalana '{punt.tria}' sin preguntar a FLOR"), None
    if not punt.puntuacions:
        return "este tipo de palabra no se manda a FLOR: se queda la elección del motor", None
    valors = {c: _valor(d, criteri, False) for c, d in punt.puntuacions.items()}
    millor = max(valors, key=valors.get)
    if punt.motor is None:
        segon = sorted(valors.values())[-2] if len(valors) > 1 else valors[millor]
        dif = round(valors[millor] - segon, 3)
        return (f"el motor no elige (colisión): gana la frase con más puntuación de FLOR, '{millor}', "
                f"por {dif}"), dif
    dif = round(valors[millor] - valors[punt.motor], 3)
    if millor == punt.motor:
        return f"FLOR prefiere lo mismo que el motor ('{punt.motor}'): no cambia nada", dif
    if dif <= criteri.marge:
        return (f"FLOR prefiere '{millor}', pero solo por {dif} (margen {criteri.marge}): "
                f"se mantiene la del motor, '{punt.motor}'"), dif
    return f"FLOR prefiere '{millor}' por {dif}, más que el margen {criteri.marge}: cambia la del motor", dif


# ─── Traza completa de una frase ─────────────────────────────────────────────

def traca(rec: Recursos, text: str, id_: str = "", referencia: str | None = None) -> dict:
    tokens = tokenize(text)
    pos_tagger.etiqueta(tokens)
    paraules_spacy, emparellament = analisi_spacy(rec, tokens)

    dicc = [info_diccionari(rec, t) for t in tokens]
    passos = traca_motor(rec, tokens)
    text_motor = detokenize(tokens)
    assert text_motor == rec.motor.translate(text), "el motor de la traza no coincide con el del paquete"

    capa_de = {}
    for p in passos:
        for c in p["canvis"]:
            capa_de.setdefault(c["i"], []).append(p["capa"])

    files = []
    for i, tok in enumerate(tokens):
        if tok.surface.isspace():
            continue
        es_paraula = tok.surface[:1].isalpha()
        fila = {
            "i": i, "superficie": tok.surface, "traduccio": tok.translated,
            "spacy_i": emparellament.get(i), "pos": tok.pos, "lema": tok.lemma, "genere": tok.gender,
            "mode": tok.mood, "verb_form": tok.verb_form, "es_paraula": es_paraula,
            "diccionari": dicc[i], "capes": capa_de.get(i, []),
        }
        if es_paraula and fila["spacy_i"] is not None and paraules_spacy[fila["spacy_i"]]["inici"] != tok.start:
            # Etiqueta prestada de otra aparición: solo avisa si la suya propia sería distinta.
            usada = paraules_spacy[fila["spacy_i"]]
            propia = next((s for s in paraules_spacy if s["inici"] <= tok.start < s["inici"] + len(s["text"])
                           and s["text"].lower() == usada["text"].lower()), None)
            if propia and (propia["pos"], propia["lema"], propia["rasgos"]) != (usada["pos"], usada["lema"], usada["rasgos"]):
                fila["avis_emparellament"] = (
                    f"el traductor usa la etiqueta de otra aparición de '{usada['text']}' ({usada['pos']}, "
                    f"{usada['lema']}); la de esta posición sería {propia['pos']}, {propia['lema']}, "
                    + ",".join(f"{k}={v}" for k, v in propia["rasgos"].items()))
                fila["spacy_propia_i"] = propia["i"]
        if es_paraula and not fila["capes"]:
            fila["motiu"] = motiu_sense_canvi(rec, tok, dicc[i])
        files.append(fila)

    resultat = {
        "id": id_, "origen": text, "motor": text_motor,
        "spacy": {"model": rec.nlp.meta.get("name", "") if rec.nlp else None,
                  "versio": rec.nlp.meta.get("version", "") if rec.nlp else None,
                  "paraules": paraules_spacy},
        "paraules": files, "passos_motor": passos,
    }
    if rec.model is not None:
        post = traca_postprocessat(rec, text, tokens)
        resultat["postprocessat"] = post
        resultat["final"] = post.get("final", text_motor)
    else:
        resultat["postprocessat"] = {"entra": False, "motiu": "sin FLOR (--motor)", "punts": []}
        resultat["final"] = text_motor
    if referencia is not None:
        resultat["referencia"] = referencia
        resultat["exacta"] = resultat["final"].strip() == referencia.strip()
        paraules_ref = paraules_de(referencia)
        for p in resultat["postprocessat"].get("punts", []):
            en_ref = [c for c in p["candidats_lexic"] if c.lower() in paraules_ref]
            p["referencia"] = en_ref
            # acierto solo si la referencia usa exactamente un candidato
            p["encert"] = (p["tria"] in en_ref) if len(en_ref) == 1 else None
    return resultat


def paraules_de(text: str) -> set[str]:
    """Palabras de un texto en minúsculas, sin puntuación y sin el prefijo
    apostrofado ("d'anous" -> "anous").

    >>> sorted(paraules_de("Un sac d'anous, i la nou."))
    ['anous', 'i', 'la', 'nou', 'sac', 'un']
    """
    import re

    paraules = set()
    for w in re.findall(r"[\w·’'ʼ-]+", text.lower()):
        pr = separa_prefix_elidit(w)
        paraules.add(pr[1] if pr else w)
    return paraules


# ─── Salida en la terminal ───────────────────────────────────────────────────

def imprimeix(t: dict) -> None:
    w = print
    w("=" * 100)
    w(f"FRASE {t['id']}: {t['origen']}")
    w("\n1. SPACY Y DICCIONARIO " + "─" * 60)
    w(f"   {'#':>3}  {'palabra':<16} {'POS':<6} {'lema':<14} {'rasgos':<34} diccionario / capa")
    sp = t["spacy"]["paraules"]
    for f in t["paraules"]:
        if not f["es_paraula"]:
            continue
        rasgos = sp[f["spacy_i"]]["rasgos"] if f["spacy_i"] is not None else {}
        rasgos_txt = ",".join(f"{k}={v}" + ("*" if k in RASGOS_USADOS else "") for k, v in rasgos.items())
        d = f["diccionari"]
        info = []
        for c in d["capes"]:
            info.append(f"{c['capa']}: {c.get('candidat') or c.get('frases')}"
                        + (" [exige verbo]" if c.get("exige_verbo") else "")
                        + (f" [homógrafo: {c['homografo_exige']}]" if c.get("homografo_exige") else ""))
        if d["ambigua"]:
            info.append(f"AMBIGUA ({d['ambigua']['tipus']}): {'/'.join(d['ambigua']['candidats'])}")
        if f["capes"]:
            nova = f["traduccio"] or "∅ (se une a la palabra siguiente)"
            info.append(f"→ {nova} ({', '.join(f['capes'])})")
        elif f.get("motiu"):
            info.append(f"sin cambio: {f['motiu']}")
        w(f"   {f['i']:>3}  {f['superficie']:<16} {f['pos']:<6} {f['lema']:<14} {rasgos_txt[:34]:<34} "
          + (" | ".join(info) if info else "—"))
        if f.get("avis_emparellament"):
            w(f"        ⚠ {f['avis_emparellament']}")
    w("   (* = rasgo que usa el traductor; el lema y la POS también)")
    w("\n2. MOTOR " + "─" * 74)
    for p in t["passos_motor"]:
        if p["canvis"]:
            w(f"   {p['capa']:<20} " + "; ".join(f"{c['abans']} → {c['despres'] or '∅'}" for c in p["canvis"]))
    w(f"   Resultado del motor: {t['motor']}")
    post = t["postprocessat"]
    w("\n3. POSTPROCESADO (FLOR) " + "─" * 59)
    w(f"   Entra: {'sí' if post['entra'] else 'no'} — {post['motiu']}")
    for p in post.get("punts", []):
        s = p["spacy"]
        w(f"   · '{p['paraula']}' ({p['tipus']}): candidatos {p['candidats_lexic']}, motor: {p['motor']}")
        w(f"     spaCy: {s['pos']} ({s['categoria']}); lectura dialectal: {s['categoria_dialectal']}; "
          f"lecturas: {s['lectures']}")
        for c in p["candidats"]:
            if "lp" in c:
                w(f"     {'✔' if c['triat'] else ' '} {c['candidat']:<10} lp {c['lp']:>9}  prior {c['prior']:>8}  "
                  f"puntuació {c['puntuacio']:>9}  «{c['frase']}»")
                for v in c["variants"]:
                    if not v["triada"]:
                        w(f"         variante descartada: lp {v['lp']:>9}  «{v['frase']}»")
            else:
                w(f"     {'✔' if c['triat'] else ' '} {c['candidat']:<10} (sin FLOR)  «{c.get('frase')}»")
        w(f"     → {p['explicacio']}")
        if "encert" in p:
            estat = {True: "ACIERTO", False: "FALLO", None: "sin decidir"}[p["encert"]]
            w(f"     referencia: {', '.join(p['referencia']) or 'ninguno'} → {estat}")
    w(f"\nRESULTADO: {t['final']}")
    if "referencia" in t:
        w(f"REFERENCIA: {t['referencia']}  [{'exacta' if t['exacta'] else 'distinta'}]")
    if post.get("entra") and not post.get("coincideix_amb_translate", True):
        w("⚠ La traza no coincide con translate_cat_val: revisar.")


# ─── Entrada / salida ────────────────────────────────────────────────────────

def normalitza_apostrofs(text: str) -> str:
    """Todas las variantes de apóstrofo a ' (como `normalitza_apostrofa` de
    `avlizador.avaluacio.metriques`, que normaliza la entrada y la
    referencia antes de evaluar; copiada para no exigir el extra
    `[avaluacio]`).

    >>> normalitza_apostrofs("d´este l’edat, l‘any i lʼEstat")
    "d'este l'edat, l'any i l'Estat"
    """
    for variant in ("´", "‘", "’", "ʼ", "`"):
        text = text.replace(variant, "'")
    return text


def frases_entrada(args) -> list[tuple[str, str, str | None]]:
    frases = frases_sense_normalitzar(args)
    return [(i, normalitza_apostrofs(t), normalitza_apostrofs(r) if r is not None else None) for i, t, r in frases]


def frases_sense_normalitzar(args) -> list[tuple[str, str, str | None]]:
    frases = [(f"T{n + 1:03d}", f, None) for n, f in enumerate(args.text)]
    if args.fitxer:
        linies = [l.strip() for l in args.fitxer.read_text(encoding="utf-8").splitlines() if l.strip()]
        frases += [(f"F{n + 1:03d}", l, None) for n, l in enumerate(linies)]
    if args.benchmark:
        from avlizador.avaluacio.avalua import BENCHMARKS, troba_dir_benchmarks

        if args.benchmark in BENCHMARKS:
            path = troba_dir_benchmarks() / BENCHMARKS[args.benchmark][1]
        else:
            path = Path(args.benchmark)
        for x in json.loads(path.read_text(encoding="utf-8")):
            if not args.ids or x["id"] in args.ids:
                frases.append((x["id"], x["oriental"], x["occidental"]))
    return frases[: args.limit] if args.limit else frases


def escriu_html(traces: list[dict], desti: Path) -> None:
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    dades = json.dumps({"generat": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "rasgos_usados": RASGOS_USADOS, "rasgos_no_usados": RASGOS_CALCULADOS_NO_USADOS,
                        "traces": traces}, ensure_ascii=False).replace("</", "<\\/")
    desti.write_text(plantilla.replace("/*__DADES__*/null", dades), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("text", nargs="*", help="Frase(s) catalanas.")
    parser.add_argument("--fitxer", type=Path, help="Fichero de texto, una frase por línea.")
    parser.add_argument("--benchmark", help="Benchmark (nombre de `avlizador avalua --llista` o ruta a un JSON).")
    parser.add_argument("--ids", nargs="+", help="Solo estos ids del benchmark.")
    parser.add_argument("--limit", type=int, help="Solo las N primeras frases.")
    parser.add_argument("--nomes-ambigues", action="store_true",
                        help="Solo las frases que pasan por el postprocesado (palabras ambiguas).")
    parser.add_argument("--motor", action="store_true", help="Sin FLOR: solo spaCy, diccionario y motor.")
    parser.add_argument("--json", type=Path, help="Guarda las trazas en JSON.")
    parser.add_argument("--html", type=Path, help="Página HTML con las trazas (visor_traces.html con los datos).")
    parser.add_argument("--silencios", action="store_true", help="No escribe las trazas en la terminal.")
    args = parser.parse_args(argv)

    frases = frases_entrada(args)
    if not frases:
        parser.error("cap frase: pasa un texto, --fitxer o --benchmark")
    rec = Recursos(amb_model=not args.motor)
    traces = []
    for n, (id_, text, ref) in enumerate(frases, 1):
        if args.nomes_ambigues:
            toks = rec.motor.tradueix_tokens(text)
            from avlizador.traductor_cat_val.model_llengua.punts import detecta
            if not detecta(toks, rec.punts):
                continue
        t = traca(rec, text, id_, ref)
        traces.append(t)
        if not args.silencios:
            imprimeix(t)
        elif n % 50 == 0:
            print(f"  {n}/{len(frases)}", file=sys.stderr)

    if args.json:
        args.json.write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON: {args.json}", file=sys.stderr)
    if args.html:
        escriu_html(traces, args.html)
        print(f"HTML: {args.html}", file=sys.stderr)
    no_coincidixen = [t["id"] for t in traces if not t["postprocessat"].get("coincideix_amb_translate", True)]
    print(f"{len(traces)} frase(s) trazadas" + (f"; NO coinciden con translate_cat_val: {no_coincidixen}"
                                               if no_coincidixen else ""), file=sys.stderr)
    return 1 if no_coincidixen else 0


if __name__ == "__main__":
    sys.exit(main())
