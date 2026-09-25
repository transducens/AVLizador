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

    [ TODO fase 2 ]  Present de subjuntiu (secció 5.2): taula per persona
        donada (puga/pugui, tinga/tingui... jo; puguen/puguin... ells) --
        mateix problema de fals positiu que fase 1 si es generalitza per
        sufix -a/-en -> -i/-in.
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
    [ TODO fase 6 ]  Verbs incoatius -ix/-eix (secció 5.6): establix ->
        estableix, servix -> serveix -- patró de sufix, però cal la
        mateixa cautela que fase 1 sobre paraules no verbals acabades en
        -ix.

AMBIGÚ (aplica a totes les fases, no només la 1): sense spaCy, moltes
formes verbals occidentals són indistingibles d'un substantiu/adjectiu
només per la forma escrita. La llista tancada de fase 1 evita el problema
per construcció (només hi ha verbs a la llista), però qualsevol fase
futura que es plantege generalitzar per sufix ha de documentar ací
qualsevol fals positiu trobat en proves, no arreglar-lo en silenci.
"""

from __future__ import annotations

from . import Token, preserva_majuscula

_PRESENT_INDICATIU_1A_PERSONA = {
    "parle": "parlo",
    "mire": "miro",
    "compre": "compro",
    "treballe": "treballo",
    "done": "dono",
    "jugue": "jugo",  # variant ortogràfica -gue/-que, citada en prosa a la font (secció 5.1)
}


class MorfologiaVerbalRule:
    """Fase 1 únicament: present d'indicatiu, 1a persona, 1a conjugació
    (llista tancada, vore docstring del mòdul per a per què no és una
    regla de sufix genèrica).

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
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for tok in tokens:
            if tok.is_translated or tok.is_proper_noun:
                continue
            forma = _PRESENT_INDICATIU_1A_PERSONA.get(tok.surface.lower())
            if forma is None:
                continue
            tok.translated = preserva_majuscula(tok.surface, forma)
            tok.is_translated = True
        return tokens
