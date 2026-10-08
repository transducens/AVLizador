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
    Des del 07/10/2026 `RuleEngine.translate()` sí que l'omple, si spaCy
    està instal·lat, cridant `pos_tagger.etiqueta()` just després de
    `marca_noms_propis()` -- vore eixe mòdul per al perquè i per a qui el
    fa servir (`ConjugacionsDictRule`).

    `mood` (afegit 08/10/2026, mateix mecanisme opcional que `pos`): el
    tret morfològic `Mood` d'spaCy ("Ind", "Sub"...) quan es pot calcular.
    Es va provar per a detectar la col·lisió d'indicatiu/subjuntiu en 3a
    plural, pero es va DESCARTAR el mateix dia (vore `pos_tagger.py` per
    al perquè -- spaCy diu "Ind" quasi sempre, siga veritat o no). Cap
    regla el consulta hui; es queda calculat com a informació diagnòstica.
    """

    surface: str
    translated: str
    pos: str = ""
    mood: str = ""
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


# Prefixos elidits reals de valencià/català: preposicions/articles (d'/l')
# i pronoms febles (s'/m'/t'/n'), sempre una sola consonant + apòstrof.
# "qu'" (de "que") s'exclou a propòsit: no és un cas real d'este projecte
# (el corpus real no l'ha mostrat mai) i afegiria un fals positiu segur
# amb "qu'" seguit d'una paraula que casualment estiga al diccionari.
_PREFIX_ELIDIT_RE = re.compile(r"^([dlsmtn])['’](.+)$", re.IGNORECASE)


def separa_prefix_elidit(surface: str) -> tuple[str, str] | None:
    """Si `surface` és un prefix elidit ("d'", "l'", "s'", "m'", "t'",
    "n'") enganxat a una paraula, torna `(prefix_amb_apostrof, resta)`; si
    no, torna `None`.

    Existix perquè el tokenitzador tracta l'apòstrof com a part de la
    paraula (`tokenize()` mai talla "d'este" en dos tokens, vore la
    decisió de disseny explicada dalt), així que un token com eixe MAI
    casa amb una entrada de diccionari que espera la paraula solta
    ("este"). Les regles de lookup exacte (`lexic.py`,
    `conjugacions_dict.py`, `demostratius.py`, `numerals.py`,
    `morfologia_verbal.py`) l'usen com a segon intent quan la cerca
    directa amb `tok.surface.lower()` no troba res -- cerquen `resta` en
    el seu diccionari i, si hi és, reconstruïxen el token com
    `prefix_amb_apostrof + forma_traduïda`.

    `gentilicis.py` i `perfet.py` no necessiten este helper: en compte
    d'un lookup exacte per paraula sencera, apliquen un sufix/patró sobre
    tot el `surface` (regex `.sub()` al final de la cadena), que ja
    travessa qualsevol prefix sense necessitat de separar-lo primer.

    >>> separa_prefix_elidit("d'este")
    ("d'", 'este')
    >>> separa_prefix_elidit("l’avui")
    ('l’', 'avui')
    >>> separa_prefix_elidit("este") is None
    True
    >>> separa_prefix_elidit("qu'este") is None
    True
    """
    m = _PREFIX_ELIDIT_RE.match(surface)
    if m is None:
        return None
    return surface[: m.end(1) + 1], m.group(2)


# Forma completa de cada prefix elidit, per a poder DESFER l'elisió quan
# la paraula trobada al diccionari ja no comença en vocal (vore
# `aplica_amb_prefix_elidit`). "l'" és ambigu entre "el"/"la", però l'ÚNIC
# ús real trobat fins ara ("l'eixir" -> infinitiu nominalitzat) sempre és
# masculí, així que es tria "el" per defecte -- documentat, no una regla
# general de gènere.
_PREFIX_COMPLET = {"d": "de", "l": "el", "s": "es", "m": "em", "t": "et", "n": "en"}

# Preposicions que es contrauen amb l'article "el" quan l'elisió es desfà
# just darrere ("a" + "el" -> "al", "de" + "el" -> "del").
_PREPOSICIONS_CONTRAIBLES = {"a": "al", "de": "del"}

_COMENCA_EN_VOCAL_O_H_MUDA_RE = re.compile(
    r"^(?:[aeiouàèéíòóúïüAEIOUÀÈÉÍÒÓÚÏÜ]|[hH][aeiouàèéíòóúïüAEIOUÀÈÉÍÒÓÚÏÜ])"
)


def _token_anterior_real(tokens: list[Token], index: int) -> Token | None:
    for tok in reversed(tokens[:index]):
        if tok.surface.isspace():
            continue
        return tok
    return None


def aplica_amb_prefix_elidit(tokens: list[Token], index: int, prefix: str, resta: str, forma: str) -> None:
    """Aplica `forma` (ja trobada al diccionari per a `resta`) al token
    `tokens[index]`, que originalment portava el prefix elidit `prefix`
    (p.ex. "l'" a "l'eixir"). Encapsula el cas normal (`forma` seguix
    començant en vocal, es manté l'elisió) i el cas que calia arreglar.

    Bug real trobat (30/09/2026): "a l'eixir" -> "a l'sortir" en compte de
    "al sortir". Com "eixir" (vocal inicial) es traduïx a "sortir"
    (consonant inicial), l'elisió original ja no té sentit -- cal DESFER-
    la, tornant el prefix a la seua forma completa ("l'" -> "el"), i si el
    resultat és "el" i el token anterior és "a"/"de", contraure-ho
    ("a"+"el" -> "al", "de"+"el" -> "del") en compte de deixar "a el".

    >>> from . import tokenize
    >>> toks = tokenize("Vinc d'ametla.")
    >>> aplica_amb_prefix_elidit(toks, 2, "d'", "ametla", "ametlla")
    >>> toks[2].translated
    "d'ametlla"

    >>> toks = tokenize("A l'eixir.")
    >>> aplica_amb_prefix_elidit(toks, 2, "l'", "eixir", "sortir")
    >>> detokenize(toks)
    'Al sortir.'

    >>> toks = tokenize("Ho vaig fer de l'eixir cap ací.")
    >>> idx = [t.surface for t in toks].index("l'eixir")
    >>> aplica_amb_prefix_elidit(toks, idx, "l'", "eixir", "sortir")
    >>> detokenize(toks)
    'Ho vaig fer del sortir cap ací.'

    Sense preposició contraïble davant, es desfà l'elisió amb un espai
    solt ("el sortir", no "al sortir"):

    >>> toks = tokenize("Vaig vore l'eixir de la lluna.")
    >>> idx = [t.surface for t in toks].index("l'eixir")
    >>> aplica_amb_prefix_elidit(toks, idx, "l'", "eixir", "sortir")
    >>> detokenize(toks)
    'Vaig vore el sortir de la lluna.'
    """
    tok = tokens[index]
    forma_cap = preserva_majuscula(resta, forma)
    if _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(forma):
        tok.translated = prefix + forma_cap
        return

    lletra = prefix[0].lower()
    complet = _PREFIX_COMPLET.get(lletra, prefix)

    if complet == "el":
        anterior = _token_anterior_real(tokens, index)
        if anterior is not None:
            contraccio = _PREPOSICIONS_CONTRAIBLES.get(anterior.translated.lower())
            if contraccio is not None:
                anterior.translated = preserva_majuscula(anterior.surface, contraccio)
                anterior.is_translated = True
                tok.translated = forma_cap
                return

    tok.translated = preserva_majuscula(prefix, complet) + " " + forma_cap


# Pronoms febles enclítics reals de valencià/català, enganxats al final
# d'un verb amb apòstrof (quan el verb acaba en vocal i el clític comença
# en vocal/h muda: "traure'n", "porta'l") o amb guionet (la resta de
# casos: "dir-li", "vine't-en"). Llista TANCADA dels clítics simples mes
# habituals -- els combinats (dos clítics seguits, "porta-te'l") no estan
# coberts perque encara no hi ha cap cas real que ho necessite; s'amplia
# nomes amb evidencia, com la resta de llistes d'este projecte.
_SUFIX_ELIDIT_RE = re.compile(
    r"^(.+?)(['’-])(me|te|se|nos|vos|los|les|la|lo|li|ho|hi|ne|ls|ns|m|t|s|n|l)$",
    re.IGNORECASE,
)


def separa_sufix_elidit(surface: str) -> tuple[str, str] | None:
    """Si `surface` acaba en un pronom feble enclític enganxat amb
    apòstrof o guionet ("traure'n", "dir-li"), torna `(arrel, connector_i_sufix)`;
    si no, torna `None`.

    Simetric a `separa_prefix_elidit` pero pel costat contrari: el
    tokenitzador tracta l'apòstrof/guionet com a part de la paraula, així
    que un verb com "traure'n" mai casa amb l'entrada "traure" d'un
    diccionari. Les regles de lookup exacte que ho necessiten (de moment,
    `conjugacions_dict.py`) ho usen com a segon intent quan la cerca
    directa amb `tok.surface.lower()` no troba res -- cerquen `arrel` en
    el seu diccionari i, si hi és, reconstruïxen el token com
    `forma_traduïda + connector_i_sufix`.

    >>> separa_sufix_elidit("traure'n")
    ('traure', "'n")
    >>> separa_sufix_elidit("dir-li")
    ('dir', '-li')
    >>> separa_sufix_elidit("traure") is None
    True
    """
    m = _SUFIX_ELIDIT_RE.match(surface)
    if m is None:
        return None
    arrel, connector, sufix = m.groups()
    return arrel, connector + sufix


def paraula_anterior_es(tokens: list[Token], index: int, paraula: str) -> bool:
    """Torna `True` si la paraula real immediatament anterior a `index`
    (saltant espais en blanc) és exactament `paraula` (comparació en
    minúscules). Torna `False` si no n'hi ha cap abans.

    Usat per protegir locucions fixes homògrafes amb una forma verbal
    real -- p.ex. "o siga" (="és a dir") no és el verb "ser" en subjuntiu,
    encara que "siga" sola sí ho siga (vore `conjugacions_dict.py` i
    `morfologia_verbal.py`).

    >>> toks = tokenize("El recompte acaba hui, o siga, el 29 de febrer.")
    >>> idx = [t.surface for t in toks].index("siga")
    >>> paraula_anterior_es(toks, idx, "o")
    True
    >>> toks = tokenize("Vull que siga possible.")
    >>> idx = [t.surface for t in toks].index("siga")
    >>> paraula_anterior_es(toks, idx, "o")
    False
    """
    for tok in reversed(tokens[:index]):
        if tok.surface.isspace():
            continue
        return tok.surface.lower() == paraula
    return False


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
    (03_seleccio_de_model/evalua_models.py, `glossari_per_frase()`), afegida
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
