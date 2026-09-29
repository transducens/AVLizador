"""
morfologia_verbal.py -- Morfologia verbal: la categoria de regles més
extensa del projecte (font: final/02_reglas_dialectales/reglas_dialectales.md,
secció 5). Es fa per FASES, no tot de colp, perquè cada temps verbal té les
seues pròpies excepcions i és fàcil introduir regressions silencioses si
es fa a soles:

    [ FASE 1 -- implementada ací ]
        Present d'indicatiu, 1a persona singular, 1a conjugació (-ar):
        parle -> parlo, mire -> miro, compre -> compro, treballe ->
        treballo, done -> dono (secció 5.1), més "jugue -> jugo" (variant
        ortogràfica -gue/-que citada en la mateixa secció, no en la taula
        però donada com a exemple explícit al text).

        DECISIÓ DE DISSENY IMPORTANT: açò és una llista TANCADA de verbs
        concrets, NO una regla general "qualsevol paraula acabada en -e
        canvia a -o". Encara que el patró gramatical siga general (tots
        els verbs regulars de 1a conjugació en 1a persona), aplicar-ho com
        a sufix cec seria perillosíssim: MOLTÍSSIMES paraules catalanes
        acaben en "-e" sense ser verbs en primera persona (este, interesse,
        blanque, whatever...), i cap d'eixes s'ha de tocar. Sense spaCy que
        confirme la categoria gramatical (pos == "" quasi sempre), la única
        manera segura de no generar falsos positius és llistar els verbs
        concrets ja confirmats per la font, i ampliar la llista a mà quan
        es confirme un altre verb regular, no generalitzar per sufix.

    [ FASE 2 -- implementada ací ]
        Present de subjuntiu (secció 5.2), només les persones "jo" i
        "ells/elles" que dona la font (llista tancada, mateix motiu que
        fase 1: "puga"/"puguen" etc. no es poden distingir d'un substantiu
        sense spaCy, així que és perillós generalitzar per sufix -a/-en ->
        -i/-in). Confirmat com a error real: qwen3:14b (el millor model
        provat fins ara) no aplicava esta conversió de manera fiable al
        benchmark de 150 frases -- este mòdul cobrix ara el cas determinista,
        independentment del que faça o no faça cap LLM.

        EXCEPCIÓ trobada auditant el mateix benchmark: "o siga" (locució
        fixa, "és a dir") NO és el verb "ser" en subjuntiu -- el gold
        reference del benchmark el deixa invariable als dos dialectes
        ("o siga" en els dos costats). Esta regla ho detecta mirant si la
        paraula immediatament anterior és "o", i en eixe cas no toca
        "siga". Mateixa família de precaució que "fora" a fase 3.

    [ TODO fase 3 ]  Imperfet de subjuntiu (secció 5.3): terminacions
        -era/-eres/-érem/-éreu/-eren -> -és/-essis/-éssim/-éssiu/-essin,
        aplicades sobre 4 arrels (hagu-, pogu-, tingu-, fo-). ATENCIÓ:
        la font marca explícitament "fora" com a homògraf perillós amb
        l'adverbi "fora" (=a l'exterior) -- NO implementar amb un simple
        lookup de paraula solta sense abans decidir com distingir els dos
        usos (la font diu que cal mirar el context).
    [ TODO fase 4 ]  Imperfet d'indicatiu, 1a/2a plural (secció 5.4):
        patró de sufix -éiem/-éieu -> -èiem/-èieu, confirmat 11/11 -- este
        SÍ podria generalitzar-se per sufix amb més seguretat que fase 1/2
        (la terminació -éiem/-éieu és molt més específica que un simple
        -e final), però encara no s'ha fet: queda per a quan es revise amb
        cura quantes paraules NO verbals podrien acabar igual.
    [ TODO fase 5 ]  Participi del verb "ser" (secció 5.5): sigut -> estat.
        Nota: esta és, de fet, una substitució lèxica d'una sola paraula
        (no un patró productiu -- cap altre verb té "sigut" com a
        participi), així que probablement encaixa millor com a entrada de
        lexico_fiable.json que com a regla d'este mòdul. Queda apuntat ací
        perquè la font la classifica dins de "morfologia verbal", però la
        decisió final és a valorar (vore final/05_motor_reglas/README.md).

    [ FASE 6 -- implementada ací ]
        Verbs incoatius -ix/-eix (secció 5.6): establix -> estableix,
        servix -> serveix. A diferència de fase 1/2, la font el documenta
        explícitament com a "patró general" (no dona una llista tancada
        d'excepcions com als altres patrons productius -é/-è, -és/-ès), així
        que s'implementa com a REGLA DE SUFIX -- però amb dos proteccions,
        totes dos trobades auditant el benchmark real, no per teoria:

        1. Mai toca paraules que ja acaben en "-eix" (no només "-ix"):
           "aparéixer"/"desaparéixer"/"comparéixer" ja tenen l'infix
           incoatiu "-eix-" DINS del propi infinitiu (a diferència
           d'"establir", un verb pur en "-ir" sense eixe infix), així que
           la seua 3a persona ("apareix", "desapareix") és IDÈNTICA en
           els dos dialectes -- no és una alternança dialectal en
           absolut. Sense esta exclusió, la regla trencaria "mateix"
           (adjectiu "same/molt", no un verb), "tanmateix" (adverbi
           "nevertheless") i "apareix"/"desapareix" mateixos, tots trobats
           realment al benchmark de 150 frases donant falsos positius.
        2. Llista negra de paraules catalanes reals que acaben en
           consonant+"ix" sense ser verbs incoatius: `baix`, `calaix`,
           `dibuix`, `guix`, `fix`, `prefix`, `sufix` -- sense esta
           protecció, "el calaix" es convertiria incorrectament en "el
           calaeix", o "el prefix" en "el prefeix" (irònic, tractant-se
           d'una regla de sufix). És d'esperar que calga ampliar-la si
           apareixen més casos reals.

        També ignora tokens completament en majúscules (`XIX`, `AVL`...):
        sense esta guarda, un numeral romà com "segle XIX" es tractaria
        com si acabara en "-ix" i es convertiria en l'absurd "XEIX".

AMBIGÚ (aplica a totes les fases, no només la 1): sense spaCy, moltes
formes verbals occidentals són indistingibles d'un substantiu/adjectiu
només per la forma escrita. Les llistes tancades de fase 1/2 eviten el
problema per construcció (només hi ha verbs a la llista); fase 6 sí
generalitza per sufix i per això porta les proteccions de dalt -- qualsevol
fase futura que es plantege generalitzar per sufix ha de documentar ací
qualsevol fals positiu trobat en proves, no arreglar-lo en silenci.
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula, separa_prefix_elidit

_PRESENT_INDICATIU_1A_PERSONA = {
    "parle": "parlo",
    "mire": "miro",
    "compre": "compro",
    "treballe": "treballo",
    "done": "dono",
    "jugue": "jugo",  # variant ortogràfica -gue/-que, citada en prosa a la font (secció 5.1)
}

# Fase 2 -- present de subjuntiu, només "jo" i "ells/elles" (l'únic que dona
# la font, secció 5.2). Resta de persones (tu/nosaltres/vosaltres) no
# incloses perquè no hi ha taula confirmada per a elles.
_PRESENT_SUBJUNTIU = {
    "puga": "pugui", "tinga": "tingui", "vinga": "vingui",
    "vaja": "vagi", "siga": "sigui", "haja": "hagi",
    "puguen": "puguin", "tinguen": "tinguin", "vinguen": "vinguin",
    "vagen": "vagin", "siguen": "siguin", "hagen": "hagin",
}

# Fase 6 -- incoatius -ix -> -eix, com a regla de sufix (vore docstring del
# mòdul). Llista negra de paraules catalanes reals que acaben en consonant +
# "-ix" i NO són verbs incoatius (les que acaben en "-eix" ja queden fora
# per construcció, vore _SUFIX_IX_RE).
_EXCEPCIONS_INCOATIUS = {"baix", "calaix", "dibuix", "guix", "fix", "prefix", "sufix"}
# Exigix que la lletra just abans de "ix" NO siga "e" -- així mai toca
# paraules que ja acaben en "-eix" (aparéixer, mateix, tanmateix...), que
# no són alternances dialectals (vore docstring del mòdul).
_SUFIX_IX_RE = re.compile(r"(?<!e)ix$", re.IGNORECASE)


class MorfologiaVerbalRule:
    """Fase 1 (present d'indicatiu, 1a persona, 1a conjugació) + fase 2
    (present de subjuntiu, "jo"/"ells") + fase 6 (incoatius -ix->-eix).
    Fase 1/2 són llistes tancades; fase 6 és una regla de sufix amb llista
    negra (vore docstring del mòdul per a per què cada una és com és).

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Jo parle valencià i mire la tele.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('parle', 'parlo'), ('mire', 'miro')]

    Paraules que casualment acaben en "-e" però NO estan a la llista
    tancada es queden intactes (este és, precisament, el cas que fa
    perillosa una regla de sufix genèrica):

    >>> toks = tokenize("Este cotxe és blanque.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Present de subjuntiu (fase 2), "jo" i "ells/elles":

    >>> toks = tokenize("Vull que puga vindre encara que no tinguen temps.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('puga', 'pugui'), ('tinguen', 'tinguin')]

    Incoatius -ix->-eix (fase 6), amb la llista negra protegint paraules
    reals que no són verbs:

    >>> toks = tokenize("Este servix per a establix una nova norma.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('servix', 'serveix'), ('establix', 'estableix')]

    >>> toks = tokenize("Obri el calaix de baix.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Paraules que ja acaben en "-eix" no es toquen mai -- no són una
    alternança dialectal, l'infix incoatiu ja forma part de l'infinitiu
    (aparéixer, no "aparir"):

    >>> toks = tokenize("Açò mateix apareix i desapareix, tanmateix.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    "prefix"/"sufix"/"fix" tampoc són verbs (llista negra):

    >>> toks = tokenize("El prefix i el sufix d'esta paraula són fix.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Numerals romans en majúscules mai es toquen:

    >>> toks = tokenize("En el segle XIX ja es documentava esta forma.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    "o siga" (locució fixa, "és a dir") no és el verb "ser" en subjuntiu:

    >>> toks = tokenize("El recompte acaba hui, o siga, el 29 de febrer.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    []

    Però "siga" SÍ es tradueix quan és de veres el verb (no precedit de "o"):

    >>> toks = tokenize("Vull que siga possible.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('siga', 'sigui')]

    Forma de fase 2 enganxada a un prefix elidit ("n'hagen" = partitiu
    "en" + "hagen", "haja"/"hagen" comencen per h muda i per tant elidixen
    amb normalitat):

    >>> toks = tokenize("Espere que n'hagen prou per a tots.")
    >>> marca_noms_propis(toks)
    >>> toks = MorfologiaVerbalRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [("n'hagen", "n'hagin")]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            # Token tot en majúscules (XIX, AVL...): mai és una forma
            # verbal, evita convertir numerals romans en absurds ("XEIX").
            if len(tok.surface) > 1 and tok.surface.isupper():
                continue
            minuscules = tok.surface.lower()

            if minuscules == "siga" and _paraula_anterior_es(tokens, i, "o"):
                continue

            forma = _PRESENT_INDICATIU_1A_PERSONA.get(minuscules)
            if forma is None:
                forma = _PRESENT_SUBJUNTIU.get(minuscules)
            if forma is not None:
                tok.translated = preserva_majuscula(tok.surface, forma)
                tok.is_translated = True
                continue

            if minuscules not in _EXCEPCIONS_INCOATIUS and _SUFIX_IX_RE.search(minuscules) and len(minuscules) > 2:
                nova = _SUFIX_IX_RE.sub("eix", minuscules)
                tok.translated = preserva_majuscula(tok.surface, nova)
                tok.is_translated = True
                continue

            # Forma de fase 1/2 enganxada a un prefix elidit (p.ex. "n'hagen",
            # partitiu "en" + "hagen" -- "haja"/"hagen" comencen per h muda,
            # així que elidixen amb normalitat). Vore separa_prefix_elidit a
            # rules/__init__.py; fase 6 (-ix->-eix) no ho necessita perquè és
            # sufix, no lookup exacte, i ja travessa qualsevol prefix sol.
            prefix_resta = separa_prefix_elidit(tok.surface)
            if prefix_resta is None:
                continue
            prefix, resta = prefix_resta
            resta_min = resta.lower()
            forma = _PRESENT_INDICATIU_1A_PERSONA.get(resta_min) or _PRESENT_SUBJUNTIU.get(resta_min)
            if forma is not None:
                tok.translated = prefix + preserva_majuscula(resta, forma)
                tok.is_translated = True
        return tokens


def _paraula_anterior_es(tokens: list[Token], index: int, paraula: str) -> bool:
    for tok in reversed(tokens[:index]):
        if tok.surface.isspace():
            continue
        return tok.surface.lower() == paraula
    return False
