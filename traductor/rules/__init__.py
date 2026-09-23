"""
rules/__init__.py -- Fonaments compartits per totes les regles del motor de
conversió dialectal: la classe Token que viatja per tot el pipeline, i les
funcions tokenize()/detokenize() que converteixen text pla en una llista de
Token i la reconstruïxen sense perdre ni un caràcter (espais, puntuació i
majúscules incloses).

Per què un Token per paraula i no operar sobre l'string sencer amb regex de
substitució directa: cada capa (lèxic, demostratius, possessius...) ha de
poder marcar "ja he tocat esta paraula" (`is_translated`) perquè les capes
següents no la sobreescriguen. Fer-ho amb substitucions de text pla sobre
tot el paràgraf faria que dos regles independents pogueren xocar sense
adonar-se'n -- p.ex. la regla de possessius podria "arreglar" per accident
una forma que ja havia tocat el lèxic, o l'elisió podria trencar una
substitució feta per la morfologia verbal. Amb un flag per token, l'orde de
les capes és explícit i cada una sap exactament quins tokens li toquen
encara (vore engine.py per l'orde complet).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Token:
    """Una unitat mínima del text: una paraula, un número, un espai en
    blanc o un signe de puntuació solt -- tokenize() no distingix estos
    tipus a nivell de classe, cada regla decidix ella mateixa si un token
    li interessa (típicament comprovant si `surface` casa amb una paraula
    coneguda; els espais/puntuació mai casaran amb cap taula lèxica, així
    que cap regla els toca sense voler).

    `surface` no canvia mai -- és la forma original tal com apareixia al
    text d'entrada, útil per a depurar o per a regles que necessiten saber
    com estava escrita la paraula abans que cap altra regla la tocara (p.ex.
    per a decidir si conservar la majúscula inicial). `translated` és la
    que es va sobreescrivint a mesura que el token passa per les capes;
    comença sent idèntica a `surface`, i és la que llig detokenize().

    Nota sobre `pos`: l'especificació original no li posava valor per
    defecte, però com que el tokenitzador base (sense spaCy) mai calcula
    cap etiqueta gramatical, se li ha posat `= ""` ací -- si no,
    tokenize() no podria crear cap Token sense dependre de spaCy, que és
    justament el que NO volem (dependència opcional, no obligatòria).
    """

    surface: str
    translated: str
    pos: str = ""
    is_translated: bool = False
    is_proper_noun: bool = False
    start: int = 0


# Orde de l'alternança (importa: la primera que casa guanya, d'esquerra a
# dreta, a cada posició del text):
#   1. números (amb separador decimal . o , per a no partir "18,5" en dos)
#   2. paraules -- INCLOENT apòstrofs i guionets interns (vore nota baix)
#   3. espais en blanc (qualsevol longitud, tabs i salts de línia inclosos)
#   4. qualsevol altre caràcter solt (puntuació, símbols, emoji...)
# Les quatre alternatives juntes cobrixen el 100% dels caràcters possibles,
# així que tokenize() mai "perd" cap tros del text original.
#
# DECISIÓ DE DISSENY -- apòstrofs i guionets es tracten com a PART de la
# paraula ("d'escola", "l'AVL", "dir-li" són UN sol token cadascun), no com
# a frontera. Separar-los ací obligaria a decidir on talla la paraula sense
# saber encara la regla gramatical que ho justifica: eixa decisió es deixa
# a rules/elisio.py, que és qui de veritat sap si "d'" ha de convertir-se
# en "de" (o a l'inrevés) segons la paraula següent. Tocar-ho ací per error
# trencaria silenciosament totes les altres regles, que només volen "la
# paraula tal com està escrita", sencera.
_TOKEN_RE = re.compile(
    r"[0-9]+(?:[.,][0-9]+)*"
    r"|[A-Za-zÀ-ÖØ-öø-ÿ·]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ·]+)*"
    r"|\s+"
    r"|.",
    re.UNICODE | re.DOTALL,
)


def tokenize(text: str) -> list[Token]:
    """Parteix `text` en una llista de Token que, reconstruïts amb
    `detokenize()`, donen EXACTAMENT el text original (espais, puntuació i
    majúscules incloses -- res es normalitza ací).

    >>> [t.surface for t in tokenize("Hui és un bon dia, oi?")]
    ['Hui', ' ', 'és', ' ', 'un', ' ', 'bon', ' ', 'dia', ',', ' ', 'oi', '?']

    >>> [t.surface for t in tokenize("d'escola i l'AVL")]
    ["d'escola", ' ', 'i', ' ', "l'AVL"]

    >>> [t.surface for t in tokenize("Vine't-en, dir-li-ho")]
    ["Vine't-en", ',', ' ', 'dir-li-ho']

    >>> detokenize(tokenize("Té 18,5 €.")) == "Té 18,5 €."
    True

    >>> detokenize(tokenize("")) == ""
    True
    """
    return [
        Token(surface=m.group(0), translated=m.group(0), start=m.start())
        for m in _TOKEN_RE.finditer(text)
    ]


def detokenize(tokens: list[Token]) -> str:
    """Reconstruïx el text final concatenant `translated` de cada token, en
    orde. Com que els espais i la puntuació també són tokens (amb
    `translated == surface` mentre cap regla els toque), no cal reinserir
    espais a mà enlloc -- per això cada regla NOMÉS ha de reassignar
    `translated` dels tokens que són paraules de veritat, i deixar la
    resta intacta.

    >>> toks = tokenize("Hola, món!")
    >>> detokenize(toks) == "Hola, món!"
    True

    >>> toks = tokenize("Este xiquet")
    >>> toks[0].translated = "Aquest"  # simula el que faria una regla
    >>> detokenize(toks)
    'Aquest xiquet'
    """
    return "".join(t.translated for t in tokens)


def preserva_majuscula(original: str, nova: str) -> str:
    """Si `original` començava en majúscula, torna `nova` amb la primera
    lletra també en majúscula (per a no convertir, p.ex., un "Este" a
    principi de frase en "este" en minúscula en compte de "Aquest"). No
    toca la resta de la paraula -- evita ficar-se amb sigles o paraules
    TOT EN MAJÚSCULES, que cap regla d'este paquet hauria de tocar de
    totes maneres. Utilitat compartida per totes les regles de
    substitució (lexic, demostratius, possessius, numerals, gentilicis,
    morfologia_verbal, perfet).

    >>> preserva_majuscula("Este", "aquest")
    'Aquest'
    >>> preserva_majuscula("este", "aquest")
    'aquest'
    """
    if original[:1].isupper():
        return nova[:1].upper() + nova[1:]
    return nova


def marca_noms_propis(tokens: list[Token]) -> None:
    """Marca com a possible nom propi (`is_proper_noun = True`) tot token
    que és una paraula, comença en majúscula, i NO és la primera paraula
    del text -- la primera lletra d'una frase sempre va en majúscula
    encara que no siga cap nom propi, així que eixa posició s'ignora
    sempre. Muta `tokens` en lloc (a diferència de tokenize/detokenize):
    és un pas de preparació que TOTES les regles han de vore abans de
    començar, no una capa amb la mateixa interfície `apply()`.

    Heurística senzilla, sense NLP real -- és la mateixa ja provada al
    pipeline de generació del corpus sintètic
    (evalua_modelos/evalua_models.py, `glossari_per_frase()`), afegida
    allí després d'un incident real: paraules com "blanca"/"Blanca" o
    "roig"/"Roig" són a la vegada un adjectiu de color normal i un nom o
    cognom, i el lèxic les estava traduint totes dos sense distinció.

    Límit conegut (documentat, no arreglat): un nom propi que és la
    PRIMERA paraula del text mai es detecta -- no hi ha manera de
    distingir "Blanca va vindre" (nom) de "Blanca és la paret" (adjectiu)
    sense més context que la sola majúscula inicial.

    >>> toks = tokenize("Pere i Blanca van vindre.")
    >>> marca_noms_propis(toks)
    >>> [t.surface for t in toks if t.is_proper_noun]
    ['Blanca']

    >>> toks = tokenize("Blanca és la paret.")
    >>> marca_noms_propis(toks)
    >>> [t.surface for t in toks if t.is_proper_noun]
    []
    """
    paraula_trobada = False
    for tok in tokens:
        if not tok.surface[:1].isalpha():
            continue  # espai, puntuació o número -- no és una paraula
        if paraula_trobada and tok.surface[:1].isupper():
            tok.is_proper_noun = True
        paraula_trobada = True


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
