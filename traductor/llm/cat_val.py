"""
llm/cat_val.py -- Capa de LLM per a català -> valencià (21/10/2026).

Dos tipus de punt ambigu, els dos dependents del SIGNIFICAT (cap regla ni
spaCy els pot resoldre; vore `documentacio/hoja_de_ruta_traductor_invers.md`):

1. **"aquest" -> "este" / "eixe"** (guia A3). El català central fon el 1r i
   el 2n grau demostratiu en "aquest"; el valencià els distingix. El motor
   posa "este" per defecte (77% d'encerts al benchmark de 151). L'intent
   anterior amb LLM (Fase 3, `qwen2.5:14b`) va empitjorar el resultat per
   dos errors de mètode (criteri calibrat amb 6 casos esbiaixats i validat
   amb la mateixa mostra); per això el criteri d'ací és conservador
   ("eixe" només quan és clar) i SEMPRE s'ha de validar contra un
   benchmark complet abans d'activar-lo per defecte.

2. **B4: "l'hi", "la hi", "les hi", "els hi" i enclítics** (guia B4). El
   català té quatre lectures que només distingix el significat (mesurat
   cas a cas al BOE):
     - "datiu":  li + acusatiu -> "li'l", "li la", "li les", "li'ls"
     - "neutre": li + ho       -> "li ho"
     - "plural": a ells + el   -> "los el"
     - "lloc":   acusatiu + hi de lloc o de règim -> es queda igual
   El motor no ho toca (= "lloc"). Molt poc freqüent (~25 casos en 268.000
   línies del BOE).

Ús:

    from traductor.llm import ClientLLM, tradueix_cat_val
    text, punts = tradueix_cat_val("Aquest llibre l'hi donaré.", ClientLLM("qwen3:8b"))

Sense client (`None`) torna exactament la sortida del motor i la llista de
punts detectats (útil per a saber quants punts hi hauria sense cridar cap
model).
"""

from __future__ import annotations

from ..rules import Token, preserva_majuscula, separa_prefix_elidit
from ..rules.cat_val.engine import RuleEngineInvers
from .punts import PuntAmbigu, marca_en_frase, resol

_DEMOSTRATIUS = {
    "aquest": ("este", "eixe"),
    "aquesta": ("esta", "eixa"),
    "aquests": ("estos", "eixos"),
    "aquestes": ("estes", "eixes"),
}

# Enclítics catalans de B4 -> {etiqueta: sufix valencià}. "lloc" = igual.
_ENCLITICS_B4 = {
    "-l'hi": {"datiu": "-li'l", "neutre": "-li-ho", "plural": "-los-el"},
    "-la-hi": {"datiu": "-li-la"},
    "-les-hi": {"datiu": "-li-les"},
    "-los-hi": {"datiu": "-li'ls"},
    "'ls-hi": {"datiu": "-li'ls"},
}


def _seguent(tokens: list[Token], index: int) -> int | None:
    for j in range(index + 1, len(tokens)):
        if not tokens[j].surface.isspace():
            return j
    return None


def _detecta_demostratius(tokens: list[Token]) -> list[PuntAmbigu]:
    punts = []
    for i, tok in enumerate(tokens):
        if tok.is_proper_noun or not tok.is_translated:
            continue
        prefix_resta = separa_prefix_elidit(tok.surface)
        prefix, paraula = prefix_resta if prefix_resta else ("", tok.surface)
        formes = _DEMOSTRATIUS.get(paraula.lower())
        if formes is None:
            continue
        este, eixe = (prefix + preserva_majuscula(paraula, f) for f in formes)
        if tok.translated.lower() != este.lower():
            continue  # el motor no hi ha posat el valor per defecte: no és este cas
        punts.append(PuntAmbigu("demostratiu", (i,), tok.surface, {"este": (este,), "eixe": (eixe,)}, "este"))
    return punts


def _detecta_b4(tokens: list[Token]) -> list[PuntAmbigu]:
    punts = []
    for i, tok in enumerate(tokens):
        if tok.is_translated or tok.is_proper_noun or tok.surface.isspace():
            continue
        baix = tok.surface.lower()
        if baix == "l'hi":
            maj = lambda forma: preserva_majuscula(tok.surface, forma)  # noqa: E731
            punts.append(PuntAmbigu("b4", (i,), tok.surface, {
                "datiu": (maj("li'l"),), "neutre": (maj("li ho"),),
                "plural": (maj("los el"),), "lloc": (tok.surface,),
            }, "lloc"))
            continue
        for sufix, opcions in _ENCLITICS_B4.items():
            if baix.endswith(sufix) and len(baix) > len(sufix):
                arrel = tok.surface[: -len(sufix)]
                totes = {etiqueta: (arrel + s,) for etiqueta, s in opcions.items()}
                totes["lloc"] = (tok.surface,)
                punts.append(PuntAmbigu("b4", (i,), tok.surface, totes, "lloc"))
                break
        else:
            if baix not in ("la", "les", "els"):
                continue
            j = _seguent(tokens, i)
            if j is None or tokens[j].surface.lower() != "hi" or tokens[j].is_translated:
                continue
            indexs = tuple(range(i, j + 1))
            espais = tuple(tokens[k].surface for k in indexs[1:-1])
            igual = tuple(tokens[k].surface for k in indexs)
            maj = lambda forma: preserva_majuscula(tok.surface, forma)  # noqa: E731
            if baix in ("la", "les"):
                opcions = {"datiu": (maj("li"),) + espais + (baix,), "lloc": igual}
            else:
                buit = tuple("" for _ in indexs[1:])
                opcions = {"datiu": (maj("li'ls"),) + buit, "plural": (maj("los"),) + buit, "lloc": igual}
            punts.append(PuntAmbigu("b4", indexs, f"{tok.surface} hi", opcions, "lloc"))
    return punts


def detecta_punts(tokens: list[Token]) -> list[PuntAmbigu]:
    """Punts ambigus de cat->val sobre els tokens ja traduïts pel motor.

    >>> motor = RuleEngineInvers()
    >>> punts = detecta_punts(motor.tradueix_tokens("Aquest llibre, l'hi donaré demà."))
    >>> [(p.tipus, p.marcada, sorted(p.opcions), p.per_defecte) for p in punts]
    [('demostratiu', 'Aquest', ['eixe', 'este'], 'este'), ('b4', "l'hi", ['datiu', 'lloc', 'neutre', 'plural'], 'lloc')]
    """
    return _detecta_demostratius(tokens) + _detecta_b4(tokens)


SYSTEM_DEMOSTRATIU = """Ets un expert en gramàtica valenciana normativa (AVL). Traduïm del català
central al valencià. El català central usa "aquest/aquesta/aquests/aquestes"
per al 1r i el 2n grau demostratiu; el valencià els distingix:
- "este" (1r grau): el referent és prop de qui parla o escriu, o és el
  mateix text, document, norma, lloc o moment present ("esta llei", "este
  decret", "este any", "este apartat"). També és l'opció per a l'ús
  anafòric normal que recupera una cosa acabada d'esmentar pel mateix
  autor. EN CAS DE DUBTE, "este".
- "eixe" (2n grau): el referent és prop de qui escolta o llig ("eixe llibre
  que tens"), o pertany a l'interlocutor ("eixe problema que dius"), o és
  un moment o situació que l'autor presenta com allunyat però no tant com
  "aquell" ("en eixe moment" parlant d'un passat ja narrat).
Tria "eixe" NOMÉS si el context ho deixa clar. Respon amb UNA SOLA PARAULA:
"este" o "eixe"."""

SYSTEM_B4 = """Ets un expert en gramàtica valenciana normativa (AVL). Traduïm del català
central al valencià. En català central, la forma marcada pot amagar quatre
combinacions de pronoms febles diferents; tria quina és en esta frase:
- "datiu": pronom de complement directe (el, la, els, les: una cosa o
  persona) + "li" (a algú, el destinatari). Ex.: "una altra persona l'hi
  causi" (li causi l'avortament) -> "li'l cause"; "la hi ha transmès un
  altre" (li ha transmès la legitimació) -> "li l'ha transmés";
  "lliurar-la-hi" -> "entregar-li-la".
- "neutre": "ho" (això, una idea o oració) + "li". Ex.: "comunicar-l'hi"
  quan es comunica un fet -> "comunicar-li-ho".
- "plural": complement directe + "los" (a ells/elles, diversos
  destinataris). Ex.: "sense enviar-l'hi" (enviar el document a ells) ->
  "enviar-los-el".
- "lloc": el "hi" NO és cap destinatari: indica un lloc o és part del verb
  ("transportar-los-hi" = transportar-los per la xarxa; "posar-les-hi").
Respon amb UNA SOLA PARAULA: "datiu", "neutre", "plural" o "lloc"."""


def _prompt(text: str, punt: PuntAmbigu) -> str:
    return f'Frase en català: "{marca_en_frase(text, punt.marcada)}"\nForma marcada: {punt.marcada}'


PROMPTS = {"demostratiu": (SYSTEM_DEMOSTRATIU, _prompt), "b4": (SYSTEM_B4, _prompt)}

_MOTOR: RuleEngineInvers | None = None


def tradueix_cat_val(text: str, client=None, tipus: set[str] | None = None) -> tuple[str, list[PuntAmbigu]]:
    """Traducció cat->val amb la capa de LLM. `tipus` limita quins punts es
    consulten ({"demostratiu"}, {"b4"}...); per defecte tots.

    Sense client, el text és idèntic al del motor:

    >>> tradueix_cat_val("Aquest llibre és bo.")[0]
    'Este llibre és bo.'
    """
    global _MOTOR
    if _MOTOR is None:
        _MOTOR = RuleEngineInvers()
    tokens = _MOTOR.tradueix_tokens(text)
    punts = [p for p in detecta_punts(tokens) if tipus is None or p.tipus in tipus]
    return resol(text, tokens, punts, PROMPTS, client)
