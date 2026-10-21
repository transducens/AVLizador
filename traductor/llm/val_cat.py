"""
llm/val_cat.py -- Capa de LLM per a valencià -> català (21/10/2026).

Un tipus de punt ambigu: **el mode verbal**. El valencià escriu igual
algunes formes d'indicatiu i de subjuntiu que el català distingix:

- 3a persona del plural: "creuen" (ells creuen / que ells creuen) ->
  català "creuen" (indicatiu) o "creuin" (subjuntiu).
- 1a persona del singular: una forma valenciana amb dos traduccions
  catalanes que només canvien la vocal final ("-o" indicatiu, "-i"
  subjuntiu).

El motor deixa estes formes SENSE traduir a propòsit
(`rules/val_cat/conjugacions_dict.py`, `es_risc_mode_3a_plural`). Este
mòdul porta dins de `traductor/` la "via C" que ja funcionava
(`pipeline/08_traduccio_corpus/postprocessat_llm/`, rècord 129/151 amb
`qwen3:8b`): mateix criteri de mode verbal, mateixes tres etiquetes
("indicatiu", "subjuntiu", "cap"). Diferència: les ambigüitats es calculen
NOMÉS amb `traductor/data/conjugacions_dialectals.json` -- la versió de
`pipeline/08` llegia quatre fitxers de conjugacions retirats el
19/10/2026 i ja no podia funcionar.

Filtre previ amb spaCy (igual que la via C): si la paraula no és VERB/AUX
en eixa frase (un substantiu homògraf, "base", "entre"...), no es crida el
model i es deixa igual.
"""

from __future__ import annotations

import json
from collections import defaultdict

from ..rules import Token, preserva_majuscula, separa_prefix_elidit
from ..rules.val_cat.conjugacions_dict import (
    DEFAULT_CONJUGACIONS_PATH,
    SEMPRE_VERB,
    es_risc_mode_3a_plural,
)
from ..rules.val_cat.engine import RuleEngine
from .punts import PuntAmbigu, marca_en_frase, resol

_AMBIGUITATS: dict[str, dict[str, str]] | None = None


def carrega_ambiguitats() -> dict[str, dict[str, str]]:
    """`{forma_valenciana: {"indicatiu": ..., "subjuntiu": ...}}`.

    >>> amb = carrega_ambiguitats()
    >>> amb["creuen"]
    {'indicatiu': 'creuen', 'subjuntiu': 'creuin'}
    """
    global _AMBIGUITATS
    if _AMBIGUITATS is not None:
        return _AMBIGUITATS
    dades = json.loads(DEFAULT_CONJUGACIONS_PATH.read_text(encoding="utf-8"))
    tots: dict[str, set[str]] = defaultdict(set)
    nets: dict[str, set[str]] = defaultdict(set)
    for entrada in dades.get("entradas", []):
        v = (entrada.get("valenciano") or "").strip().lower()
        c = (entrada.get("catalan") or "").strip().lower()
        if not v or not c or " " in v:
            continue
        tots[v].add(c)
        if not entrada.get("problematica"):
            nets[v].add(c)
    resultat: dict[str, dict[str, str]] = {}
    # 1a persona: dos candidats que només canvien -o / -i
    for v, catalans in tots.items():
        if len(catalans) != 2:
            continue
        a, b = sorted(catalans)
        if a[:-1] == b[:-1] and {a[-1], b[-1]} == {"o", "i"}:
            resultat[v] = {"indicatiu": a if a.endswith("o") else b, "subjuntiu": b if b.endswith("i") else a}
    # 3a plural: l'indicatiu és la mateixa forma valenciana sense canviar
    for v, catalans in nets.items():
        if v in SEMPRE_VERB or len(catalans) != 1:
            continue
        subjuntiu = next(iter(catalans))
        if es_risc_mode_3a_plural(v, subjuntiu):
            resultat[v] = {"indicatiu": v, "subjuntiu": subjuntiu}
    _AMBIGUITATS = resultat
    return resultat


def detecta_punts(tokens: list[Token]) -> list[PuntAmbigu]:
    """Formes verbals ambigües que el motor ha deixat sense traduir.

    >>> motor = RuleEngine()
    >>> punts = detecta_punts(motor.tradueix_tokens("Vull que creuen el carrer."))
    >>> [(p.marcada, p.opcions["subjuntiu"], p.per_defecte) for p in punts]
    [('creuen', ('creuin',), 'cap')]
    """
    ambiguitats = carrega_ambiguitats()
    punts = []
    for i, tok in enumerate(tokens):
        if tok.is_translated or tok.is_proper_noun or tok.surface.isspace():
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        prefix, paraula = prefix_resta if prefix_resta else ("", tok.surface)
        cas = ambiguitats.get(paraula.lower())
        if cas is None:
            continue
        if tok.pos and tok.pos not in ("VERB", "AUX"):
            continue  # filtre spaCy: no és el verb (substantiu homògraf...)
        forma = lambda f: prefix + preserva_majuscula(paraula, f)  # noqa: E731
        punts.append(PuntAmbigu("mode_verbal", (i,), tok.surface, {
            "indicatiu": (forma(cas["indicatiu"]),),
            "subjuntiu": (forma(cas["subjuntiu"]),),
            "cap": (tok.surface,),
        }, "cap", extra=cas))
    return punts


# Mateix criteri que `pipeline/08_traduccio_corpus/postprocessat_llm/compara_postprocessat.py`
# (CRITERI_MODE_VERBAL + via C), el que va donar 129/151 amb qwen3:8b.
CRITERI_MODE_VERBAL = """
CRITERI PER A DECIDIR INDICATIU VS. SUBJUNTIU:
- SUBJUNTIU si la paraula va en una oracio subordinada introduïda per "que"
  depenent d'un verb de voluntat, necessitat, dubte, sentiment o valoracio
  ("vull que", "cal que", "és necessari que", "sempre que", "a fi que"), o
  darrere de "perquè" amb valor final, o en frases de relatiu amb valor
  hipotetic/indefinit ("qualsevol que...", "el que siga que...").
- INDICATIU si expressa un fet asseverat (en qualsevol persona, singular
  o plural), normalment en oracio principal o subordinada completiva
  sense eixe matís de voluntat/dubte ("jo declare que...", "els experts
  creuen que...", "molts pares poden quedar...").
ATENCIO -- NO confongues la paraula marcada amb el verb de la SEUA PROPIA
subordinada: en "jo em centre en que el partit isca bé", la paraula
marcada ("centre") es el verb PRINCIPAL, que assevera un fet -> INDICATIU.
Mira SEMPRE si la paraula marcada es la que GOVERNA el "que" (verb
principal -> INDICATIU) o la que ve DESPRES del "que" depenent d'un verb
de voluntat/dubte/valoracio (-> SUBJUNTIU).
ATENCIO -- frases de relatiu REALS (antecedent concret i existent) son
INDICATIU: "els alumnes que opten a estudiar-hi", "les persones que creuen
aixo". Son SUBJUNTIU NOMES les HIPOTETIQUES o INDEFINIDES ("qualsevol que
vinga", "no hi ha ningu que ho sapia").
ATENCIO -- "quan": INDICATIU si introduïx un fet REAL, HABITUAL o ja
ocorregut ("quan plou, no ixc"); SUBJUNTIU si introduïx una condicio
FUTURA o HIPOTETICA no verificada, frequent en textos legals ("Quan el
tractament es base en el consentiment, [...]" = "en el cas que es base").
"""

SYSTEM_MODE_VERBAL = (
    "Ets un expert en gramatica catalana/valenciana. " + CRITERI_MODE_VERBAL + "\n"
    "Se't dona una frase en valencia i una paraula marcada que pot ser una "
    "forma verbal ambigua entre indicatiu (present o pretèrit perfet simple) "
    "i el corresponent de subjuntiu (present o imperfet). ATENCIO: la mateixa "
    "forma pot ser en realitat un substantiu o una altra categoria sense "
    "relacio amb el verb (p.ex. \"base\", \"entre\", \"poble\"). Classifica "
    "EIXA PARAULA EN EIXE CONTEXT:\n"
    "- 'indicatiu' si ahi funciona com a indicatiu del verb (fet asseverat).\n"
    "- 'subjuntiu' si ahi funciona com a subjuntiu (voluntat, dubte, "
    "condicio hipotetica...).\n"
    "- 'cap' si la paraula NO es este verb ahi (si es el verb en indicatiu, "
    "la resposta es 'indicatiu', mai 'cap').\n"
    "Respon amb UNA SOLA PARAULA: 'indicatiu', 'subjuntiu' o 'cap'."
)


def _prompt(text: str, punt: PuntAmbigu) -> str:
    return f'Frase: "{marca_en_frase(text, punt.marcada)}"\n\nParaula marcada: {punt.marcada}'


PROMPTS = {"mode_verbal": (SYSTEM_MODE_VERBAL, _prompt)}

_MOTOR: RuleEngine | None = None


def tradueix_val_cat(text: str, client=None) -> tuple[str, list[PuntAmbigu]]:
    """Traducció val->cat amb la capa de LLM. Sense client, idèntica al motor.

    >>> tradueix_val_cat("Este xiquet vol vindre hui.")[0]
    'Aquest nen vol venir avui.'
    """
    global _MOTOR
    if _MOTOR is None:
        _MOTOR = RuleEngine()
    tokens = _MOTOR.tradueix_tokens(text)
    return resol(text, tokens, detecta_punts(tokens), PROMPTS, client)
