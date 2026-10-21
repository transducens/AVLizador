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
from .punts import PuntAmbigu, resol

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


# Còpia LITERAL de `pipeline/08_traduccio_corpus/postprocessat_llm/compara_postprocessat.py`
# (CRITERI_MODE_VERBAL + system i prompt de `via_c`), el que va donar 129/151
# amb qwen3:8b. Restaurada el 21/10/2026: la primera versió d'este mòdul
# l'havia escurçada i havia posat la paraula entre claudàtors dins de la
# frase, i la prova en Abaco (qwen3:8b, 20 frases) va eixir esbiaixada cap
# al subjuntiu. No canviar sense tornar a mesurar contra el benchmark.
CRITERI_MODE_VERBAL = '\nCRITERI PER A DECIDIR INDICATIU VS. SUBJUNTIU (la guia de dialectologia no\ncobrix mode verbal, nomes determinants/pronoms/preposicions -- este criteri\nes general, no ve d\'eixe document):\n- SUBJUNTIU si la paraula va en una oracio subordinada introduïda per "que"\n  depenent d\'un verb de voluntat, necessitat, dubte, sentiment o valoracio\n  ("vull que", "cal que", "és necessari que", "sempre que", "a fi que"), o\n  darrere de "perquè" amb valor final, o en frases de relatiu amb valor\n  hipotetic/indefinit ("qualsevol que...", "el que siga que...").\n- INDICATIU si expressa un fet asseverat (en qualsevol persona, singular\n  o plural), normalment en oracio principal o subordinada completiva\n  sense eixe matís de voluntat/dubte ("jo declare que...", "per la\n  present jo autorize...", "els experts creuen que...", "molts pares\n  poden quedar...").\nATENCIO -- NO confongues la paraula marcada en el verb de la SEUA PROPIA\nsubordinada: en "jo em centre en que el partit isca bé", la paraula\nmarcada ("centre") es el verb PRINCIPAL, que asseverA un fet ("centrar-se\nen" = fixar l\'atencio en), encara que vaja seguit de "que" i encara que el\nverb DINS d\'eixa subordinada ("isca") siga, ell si, subjuntiu de veres.\nVerbs assertius/factuals seguits de "en que"/"que" com "centrar-se en\nque", "basar-se en que", "fixar-se en que", "constatar que" son INDICATIU\nencara que hi haja un "que" immediatament darrere -- NO es el mateix\npatro que "vull que" (ahi el verb marcat seria "vull", no el verb de la\nsubordinada). Mira SEMPRE si la paraula marcada es la que GOVERNA el\n"que" (verb principal, asseveratiu -> INDICATIU) o la que ve DESPRES del\n"que" depenent d\'un verb de voluntat/dubte/valoracio (-> SUBJUNTIU).\nATENCIO -- frases de relatiu REALS (amb antecedent concret, conegut,\nexistent) son INDICATIU, encara que hi haja un "que" de relatiu: "els\nalumnes que opten a estudiar-hi" (uns alumnes reals i concrets que, de\nfet, trien aixo -> opten, INDICATIU), "les persones que creuen aixo"\n(persones reals que, de fet, ho creuen -> creuen, INDICATIU). Son\nSUBJUNTIU NOMES les frases de relatiu HIPOTETIQUES o INDEFINIDES, on\nl\'antecedent NO es cap persona/cosa concreta coneguda sino "qualsevol\nque complisca la condicio" ("qualsevol que vinga", "el primer que\narribe", "no hi ha ningu que ho sapia"). La prova: si pots substituir\n"que" per "qui de fet" o afegir "en concret" sense que la frase perda\nsentit (p.ex. "els alumnes que, en concret, opten..."), es relatiu REAL\n-> INDICATIU; si nomes te sentit amb "siga qui siga" o "qualsevol que",\nes relatiu HIPOTETIC -> SUBJUNTIU.\nATENCIO -- "quan" NO sempre es el mateix mode: si introduïx un fet REAL,\nHABITUAL o ja ocorregut ("quan vaig arribar, plovia", "quan plou, no\nixc", "quan el tractament es base de fet en X" parlant d\'un cas concret\nja establit) es INDICATIU. Es SUBJUNTIU quan "quan" (igual que "sempre\nque", "fins que", "a fi que") introduïx una condicio FUTURA o\nHIPOTETICA encara NO verificada -- patro molt comu en textos legals/\nnormatius: "Quan el tractament es base en el seu consentiment, [...]"\nvol dir "en el cas que / sempre que es base" (una condicio que pot\ncomplir-se o no en el futur, no un fet ja establit), per tant SUBJUNTIU\n("basi"), encara que no hi haja cap verb de voluntat/dubte explicit\ndavant. La prova: si pots substituir "quan" per "sempre que" o "en el\ncas que" sense que la frase perda sentit, es la lectura condicional/\nhipotetica -> SUBJUNTIU; si nomes te sentit com "en el moment en que,\nde fet," (un moment concret, real o habitual), es INDICATIU.\n'

SYSTEM_MODE_VERBAL = 'Ets un expert en gramatica catalana/valenciana. {CRITERI}\nSe\'t dona una frase en valencia i una paraula marcada que, segons les dades, POT ser una forma verbal ambigua entre un mode d\'indicatiu (present o pretèrit perfet simple) i el corresponent de subjuntiu (present o imperfet), en qualsevol persona (singular o plural) d\'un verb rar. ATENCIO: la mateixa forma sovint es en realitat un substantiu, preposicio o un atra categoria gramatical NO relacionada amb eixe verb (p.ex. "base", "entre", "poble") -- mira el context amb cura. Classifica EIXA PARAULA EN EIXE CONTEXT concret:\n- \'indicatiu\' si ahi funciona com un mode d\'indicatiu del verb (present o pretèrit perfet simple -- expressa un fet asseverat).\n- \'subjuntiu\' si ahi funciona com el corresponent de subjuntiu (present o imperfet -- voluntat, dubte, concessio...).\n- \'cap\' si la paraula marcada NO es en absolut este verb ahi (es un substantiu, preposicio, una atra categoria gramatical sense relacio -- NO triga \'cap\' nomes perque has descartat subjuntiu; si es este verb pero en mode indicatiu, la resposta es \'indicatiu\', mai \'cap\').\nRespon amb UNA SOLA PARAULA: \'indicatiu\', \'subjuntiu\' o \'cap\'. Sense cap explicacio ni raonament, nomes la paraula.'.replace("{CRITERI}", CRITERI_MODE_VERBAL)


def _prompt(text: str, punt: PuntAmbigu) -> str:
    return f'Frase: "{text}"\n\nParaula marcada: {punt.marcada}'


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
