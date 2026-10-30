"""
llm/cat_val.py -- Capa de LLM per a català -> valencià (22/10/2026).

Un tipus de punt ambigu: **homògrafs de la mateixa categoria**. Les
entrades `problema: "homonimia_lexica"` del lèxic diuen quina forma és
ambigua (`forma_problematica`) i quines lectures té (`lemas`). Quan les
lectures tenen categories distintes ("nou": adj/n/num) ja ho resol spaCy
dins del motor (`rules/__init__.py::carrega_homografs`). Quan són de la
mateixa categoria, spaCy no pot: "calces" (bragues o calces de pantaló,
dos noms), "gandula" (hamaca o dona gandula). Eixos són els únics punts
d'esta capa. Només compten les entrades amb la forma ambigua al costat
CATALÀ (les que afecten esta direcció); la llista ix sempre del lèxic,
cap paraula està escrita ací.

El motor tradueix sempre (criteri de l'usuari). El LLM només respon "si"
(la paraula té el sentit de l'entrada: es queda la traducció del motor) o
"no" (té un altre sentit: es deixa la paraula catalana). Si no hi ha
Ollama, no respon o respon una altra cosa, es queda el motor. Una frase
sense cap d'estes paraules no fa cap crida.

Límit conegut: si la paraula canvia de gènere en traduir-se, el
determinant d'abans ja l'ha corregit el motor i "no" no el desfà (cap cas
hui: "calces"/"bragues" i "gandula"/"hamaca" tenen el mateix gènere).

Prova en local (amb Ollama en marxa i el model baixat): vore
`prova_cat_val.py`.
"""

from __future__ import annotations

import json
import re

from avlizador.traductor_cat_val.rules import LEXIC_GENERAL_PATH, Token, carrega_homografs, detokenize, separa_prefix_elidit
from avlizador.traductor_cat_val.rules.cat_val.engine import RuleEngineInvers
from .punts import PuntAmbigu, resol

_LECTURA_RE = re.compile(r"^\s*(.+?)\s*\[([^\]]*)\]\s*$")
_HOMOGRAFS: dict[str, dict] | None = None


def carrega_homografs_llm() -> dict[str, dict]:
    """Homògrafs del lèxic que el motor no pot resoldre amb spaCy i que
    afecten cat->val: `{forma catalana: {"valencia", "sentit", "lectures"}}`.

    >>> h = carrega_homografs_llm()
    >>> sorted(h)
    ['calces', 'gandula', 'gandules']
    >>> h["calces"]["valencia"], h["calces"]["sentit"], h["calces"]["lectures"]
    ('bragues', 'bragas', ['calces (n)', 'calça (n)'])
    """
    global _HOMOGRAFS
    if _HOMOGRAFS is not None:
        return _HOMOGRAFS
    _, irresolubles = carrega_homografs()
    dades = json.loads(LEXIC_GENERAL_PATH.read_text(encoding="utf-8"))
    resultat: dict[str, dict] = {}
    for entrada in dades:
        if entrada.get("problema") != "homonimia_lexica":
            continue
        forma = (entrada.get("forma_problematica") or "").strip().lower()
        catalan = (entrada.get("catalan") or "").strip().lower()
        if forma not in irresolubles or forma != catalan:
            continue
        lectures, lemes = [], []
        for lema in entrada.get("lemas") or []:
            m = _LECTURA_RE.match(lema)
            lectures.append(f"{m.group(1)} ({m.group(2)})" if m else lema)
            if m:
                lemes.append((m.group(1), [c.strip() for c in m.group(2).split(",")]))
        resultat[forma] = {
            "valencia": (entrada.get("valenciano") or "").strip(),
            "sentit": (entrada.get("espanol") or "").strip(),
            "lectures": lectures,
            "lemes": lemes,
        }
    _HOMOGRAFS = resultat
    return resultat


def detecta_punts(tokens: list[Token]) -> list[PuntAmbigu]:
    """Homògrafs de la mateixa categoria que el motor ha traduït.

    >>> motor = RuleEngineInvers()
    >>> punts = detecta_punts(motor.tradueix_tokens("Es va posar les calces del pantaló."))
    >>> [(p.marcada, p.opcions, p.per_defecte) for p in punts]
    [('calces', {'si': ('bragues',), 'no': ('calces',)}, 'si')]
    >>> detecta_punts(motor.tradueix_tokens("La casa és gran."))
    []
    """
    homografs = carrega_homografs_llm()
    punts = []
    for i, tok in enumerate(tokens):
        if tok.surface.isspace():
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        paraula = prefix_resta[1] if prefix_resta else tok.surface
        cas = homografs.get(paraula.lower())
        if cas is None or tok.translated == tok.surface:
            continue
        punts.append(PuntAmbigu(
            "homograf", (i,), tok.surface,
            {"si": (tok.translated,), "no": (tok.surface,)},
            "si", extra={**cas, "paraula": paraula},
        ))
    return punts


SYSTEM_HOMOGRAF = (
    "Ets un expert en lèxic català i valencià. Se't dona una frase en català i "
    "una paraula marcada que té diversos significats del mateix tipus "
    "gramatical. Has de dir si, en eixa frase concreta, la paraula té el "
    "significat que se't pregunta.\n"
    "Respon amb UNA SOLA PARAULA: 'si' o 'no'. Sense cap explicació."
)


def _prompt(text: str, punt: PuntAmbigu) -> str:
    cas = punt.extra
    sentit = f"«{cas['sentit']}» en castellà" if cas["sentit"] else f"el que en valencià es diu «{cas['valencia']}»"
    return (
        f'Frase: "{text}"\n\n'
        f"Paraula marcada: {cas['paraula']}\n"
        f"Lectures possibles de la paraula: {', '.join(cas['lectures'])}.\n"
        f"Pregunta: en esta frase, «{cas['paraula']}» vol dir {sentit} "
        f"(en valencià, «{cas['valencia']}»)?"
    )


# Versió 2 (22/10/2026), en castellà: la primera prova en local
# (qwen2.5:7b) va respondre "no" a les dos frases de "gandula", també a
# la de la tumbona. Ací els significats van un per línia, amb la categoria
# escrita, i la pregunta és només sobre el sentit del diccionari.
_CATEGORIA_ES = {"n": "nombre", "adj": "adjetivo", "adv": "adverbio", "v": "verbo", "pr": "preposición"}

SYSTEM_HOMOGRAF_V2 = (
    "Eres un experto en léxico del catalán. Se te da una frase en catalán y "
    "una palabra marcada que, escrita igual, puede ser palabras distintas. "
    "Di si en esa frase la palabra tiene el significado por el que se "
    "pregunta. Responde con UNA SOLA PALABRA: 'si' o 'no'."
)


def _prompt_v2(text: str, punt: PuntAmbigu) -> str:
    cas = punt.extra
    paraula = cas["paraula"]
    linies = [
        f"  - una forma de «{lema}» ({' o '.join(_CATEGORIA_ES.get(c, c) for c in cats)})"
        for lema, cats in cas["lemes"]
    ]
    sentit = cas["sentit"] or cas["valencia"]
    return (
        f'Frase en catalán: "{text}"\n\n'
        f"Palabra marcada: «{paraula}»\n"
        f"En catalán, «{paraula}» puede ser:\n" + "\n".join(linies) + "\n\n"
        f"Pregunta: en esta frase, ¿«{paraula}» significa «{sentit}»? (si / no)"
    )


PROMPTS = {"homograf": (SYSTEM_HOMOGRAF, _prompt)}
PROMPTS_V2 = {"homograf": (SYSTEM_HOMOGRAF_V2, _prompt_v2)}

# Versió 3 (22/10/2026): sense pregunta de sí o no. Amb v1 i v2, qwen2.5:7b
# i qwen3:8b responien "no" a tot (també a "gandula" = tumbona i "calces" =
# bragues): una pregunta sobre un sentit concret i poc freqüent empeny el
# model cap al "no". Ací el model només TRADUÏX la paraula al castellà tal
# com s'usa en la frase, i el codi la compara amb el sentit del lèxic
# (`espanol`). La resposta no entra mai al text.
SYSTEM_HOMOGRAF_V3 = (
    "Eres un traductor de catalán a castellano. Se te da una frase en catalán "
    "y una palabra marcada. Traduce al castellano SOLO esa palabra, con el "
    "significado que tiene en esa frase. Responde únicamente con la palabra "
    "traducida, sin explicaciones."
)


def _prompt_v3(text: str, punt: PuntAmbigu) -> str:
    return f'Frase en catalán: "{text}"\n\nPalabra marcada: «{punt.extra["paraula"]}»\n\nTraducción al castellano:'


def _arrel(paraula: str) -> str:
    """Forma per a comparar: minúscules, sense accents ni plural.

    >>> _arrel("Tumbonas"), _arrel("bragas"), _arrel("braga"), _arrel("Perezosa.")
    ('tumbona', 'braga', 'braga', 'perezosa')
    """
    import unicodedata

    neta = "".join(c for c in unicodedata.normalize("NFD", paraula.lower()) if unicodedata.category(c) != "Mn")
    neta = re.sub(r"[^a-zñ]", "", neta)
    for final in ("es", "s"):
        if neta.endswith(final) and len(neta) > len(final) + 3:
            return neta[: -len(final)] if final == "s" or not neta[:-2].endswith(("a", "o")) else neta[:-1]
    return neta


def coincidix_sentit(resposta: str, sentit: str) -> bool | None:
    """`True` si la traducció del model és el sentit del lèxic, `False` si
    és una altra paraula, `None` si la resposta és buida o un error.

    >>> coincidix_sentit("tumbona", "tumbona"), coincidix_sentit("Tumbonas.", "tumbona")
    (True, True)
    >>> coincidix_sentit("perezosa", "tumbona"), coincidix_sentit("", "bragas")
    (False, None)

    Una resposta llarga (el model s'ha posat a raonar i s'ha tallat) no
    val com a "no": es queda el motor.

    >>> coincidix_sentit("Okay, let's tackle this translation request", "tumbona") is None
    True
    """
    paraules = re.findall(r"[^\W\d_]+", resposta)
    if not paraules or resposta.startswith("ERROR:") or len(paraules) > 4:
        return None
    objectiu = _arrel(sentit)
    return any(_arrel(p) == objectiu for p in paraules)


def _resol_v3(text: str, tokens: list[Token], punts: list[PuntAmbigu], client) -> tuple[str, list[PuntAmbigu]]:
    for punt in punts:
        decisio = None
        if client is not None and punt.extra.get("sentit"):
            prompt = _prompt_v3(text, punt)
            if str(getattr(client, "model", "")).startswith("qwen3"):
                prompt += " /no_think"
            punt.resposta_llm = client.crida(SYSTEM_HOMOGRAF_V3, prompt)
            coincidix = coincidix_sentit(punt.resposta_llm, punt.extra["sentit"])
            if coincidix is not None:
                decisio = "si" if coincidix else "no"
        punt.decisio = decisio or punt.per_defecte
        if punt.decisio != punt.per_defecte:
            punt.aplica(tokens, punt.decisio)
    return detokenize(tokens), punts


_MOTOR: RuleEngineInvers | None = None


def tradueix_cat_val(text: str, client=None, prompt: str = "v1") -> tuple[str, list[PuntAmbigu]]:
    """Traducció cat->val amb la capa de LLM. Sense client, idèntica al
    motor (`traductor.translate_cat_val`). `prompt`: "v1" (català, sí/no),
    "v2" (castellà, sí/no) o "v3" (el model traduïx la paraula, vore
    `SYSTEM_HOMOGRAF_V3`).

    >>> class ClientTradueix:
    ...     model = "prova"
    ...     def crida(self, system, prompt):
    ...         return "perezosa" if "molt gandula" in prompt else "tumbona"
    >>> tradueix_cat_val("Aquesta noia és molt gandula.", ClientTradueix(), "v3")[0]
    'Esta xica és molt gandula.'
    >>> tradueix_cat_val("He comprat una gandula.", ClientTradueix(), "v3")[0]
    'He comprat una hamaca.'

    >>> tradueix_cat_val("Es va posar les calces del pantaló.")[0]
    'Es va posar les bragues del pantaló.'

    Amb un client que respon "no" (simulat ací, sense Ollama), es deixa la
    paraula catalana:

    >>> class ClientNo:
    ...     def tria(self, system, prompt, etiquetes):
    ...         return "no", "no"
    >>> text, punts = tradueix_cat_val("Es va posar les calces del pantaló.", ClientNo())
    >>> text, [(p.marcada, p.decisio) for p in punts]
    ('Es va posar les calces del pantaló.', [('calces', 'no')])
    """
    global _MOTOR
    if _MOTOR is None:
        _MOTOR = RuleEngineInvers()
    tokens = _MOTOR.tradueix_tokens(text)
    if prompt == "v3":
        return _resol_v3(text, tokens, detecta_punts(tokens), client)
    prompts = PROMPTS_V2 if prompt == "v2" else PROMPTS
    return resol(text, tokens, detecta_punts(tokens), prompts, client)
