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

import json
import re
from dataclasses import dataclass
from pathlib import Path


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

    `gender` (afegit 08/10/2026, mateix mecanisme opcional que `pos`): el
    tret morfològic `Gender` d'spaCy ("Fem", "Masc") per a NOUN/ADJ. A
    diferencia de `mood`, este SÍ es consulta -- per `ConcordancaDosDuesRule`
    per a la concordança "dos"/"dues" davant de nom/adjectiu femení sense
    marcador explícit al davant. No és infal·lible (provat amb casos reals
    del benchmark: "consonants" l'etiqueta Masc per error, hauria de ser
    Fem), per això nomes s'actua quan diu Fem explícitament -- si diu Masc,
    buit, o spaCy no està disponible, no es toca "dos" (preferix fals
    negatiu, vore `pos_tagger.py`).

    `lemma` (afegit 20/10/2026, mateix mecanisme opcional que `pos`): el
    lema d'spaCy en minúscules ("serveix" -> "servir"). El consulta
    `cat_val/incoatius.py`, sempre validat contra els infinitius reals de
    `conjugacions_dialectals.json` (spaCy s'inventa lemes per a verbs que
    no coneix: "apareix" -> "aparir").

    `verb_form` (afegit 21/10/2026): el tret `VerbForm` d'spaCy ("Inf",
    "Fin", "Part", "Ger"). El consulta `cat_val/per_a_infinitiu.py`.
    """

    surface: str
    translated: str
    pos: str = ""
    mood: str = ""
    gender: str = ""
    lemma: str = ""
    verb_form: str = ""
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
    r"|[A-Za-zÀ-ÖØ-öø-ÿ·]+(?:['’ʼ-][A-Za-zÀ-ÖØ-öø-ÿ·]+)*"
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

    L'apòstrof "ʼ" (U+02BC, 1.589 vegades al BOE català) també compta
    (22/10/2026; abans "lʼEstat" es partia en "lʼ" + "Estat"):

    >>> [t.surface for t in tokenize("de lʼEstat")]
    ['de', ' ', 'lʼEstat']

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

    Paraula sencera en majúscules (22/10/2026, títols del BOE: "SERVEIS"
    -> "SERVICIS", abans "Servicis"). Es compten només les lletres, i en
    fan falta almenys dos: un prefix elidit "L’" no és una paraula en
    majúscules.

    >>> preserva_majuscula("SERVEIS", "servicis"), preserva_majuscula("L’", "la")
    ('SERVICIS', 'La')
    """
    lletres = [c for c in original if c.isalpha()]
    if len(lletres) >= 2 and all(c.isupper() for c in lletres):
        return nova.upper()
    if original[:1].isupper():
        return nova[:1].upper() + nova[1:]
    return nova


# Prefixos elidits reals de valencià/català: preposicions/articles (d'/l')
# i pronoms febles (s'/m'/t'/n'), sempre una sola consonant + apòstrof.
# "qu'" (de "que") s'exclou a propòsit: no és un cas real d'este projecte
# (el corpus real no l'ha mostrat mai) i afegiria un fals positiu segur
# amb "qu'" seguit d'una paraula que casualment estiga al diccionari.
_PREFIX_ELIDIT_RE = re.compile(r"^([dlsmtn])['’ʼ](.+)$", re.IGNORECASE)


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


def aplica_amb_prefix_elidit(
    tokens: list[Token], index: int, prefix: str, resta: str, forma: str, genere: str = ""
) -> None:
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

    Amb `genere="f"` (22/10/2026, el gènere de la paraula nova segons
    spaCy), "l'" es desfà en "la" i no es contrau:

    >>> toks = tokenize("Agafa l'escombra.")
    >>> aplica_amb_prefix_elidit(toks, 2, "l'", "escombra", "granera", "f")
    >>> detokenize(toks)
    'Agafa la granera.'
    >>> toks = tokenize("Parla de l'escombra.")
    >>> idx = [t.surface for t in toks].index("l'escombra")
    >>> aplica_amb_prefix_elidit(toks, idx, "l'", "escombra", "granera", "f")
    >>> detokenize(toks)
    'Parla de la granera.'
    """
    tok = tokens[index]
    forma_cap = preserva_majuscula(resta, forma)
    if _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(forma):
        tok.translated = prefix + forma_cap
        return

    lletra = prefix[0].lower()
    complet = _PREFIX_COMPLET.get(lletra, prefix)
    if lletra == "l" and genere == "f":
        complet = "la"

    if complet == "el":
        anterior = _token_anterior_real(tokens, index)
        if anterior is not None:
            contraccio = _PREPOSICIONS_CONTRAIBLES.get(anterior.translated.lower())
            if contraccio is not None:
                anterior.translated = preserva_majuscula(anterior.surface, contraccio)
                anterior.is_translated = True
                tok.translated = forma_cap
                return

    if resta.isupper() and len(resta) > 1:
        complet = complet.upper()  # "L’HABITATGE" -> "LA VIVENDA"
    tok.translated = preserva_majuscula(prefix, complet) + " " + forma_cap


def corregeix_elisio_de_abans(tokens: list[Token], index: int) -> None:
    """Si `tokens[index]` ha canviat de consonant inicial a vocal/h muda
    com a resultat d'una substitució (lookup exacte), i el token real
    anterior és la preposició "de" solta (sense apòstrof -- si ja en tenia
    un, és un cas distint, el de `aplica_amb_prefix_elidit`), la convertix
    a "d'" eliminant l'espai intermedi. Al revés que
    `aplica_amb_prefix_elidit` (que DESFÀ una elisió que ja no té sentit),
    esta funció AFIG una elisió que no existia perquè el text original no
    en necessitava cap.

    Cas real trobat (08/10/2026, RC032): "la manera de calfar-nos" ->
    "la manera de escalfar-nos" en compte de "d'escalfar-nos", perquè
    "calfar" (consonant inicial) es tradueix a "escalfar" (vocal inicial)
    -- `conjugacions_dict.py` és l'únic cridador conegut hui.

    >>> toks = tokenize("de calfar-nos")
    >>> toks[-1].translated = "escalfar-nos"
    >>> corregeix_elisio_de_abans(toks, len(toks) - 1)
    >>> detokenize(toks)
    "d'escalfar-nos"

    Si el token anterior no és "de" (solt), no fa res:

    >>> toks = tokenize("per a calfar-nos")
    >>> toks[-1].translated = "escalfar-nos"
    >>> corregeix_elisio_de_abans(toks, len(toks) - 1)
    >>> detokenize(toks)
    'per a escalfar-nos'

    Si la forma traduïda seguix començant en consonant, tampoc fa res:

    >>> toks = tokenize("de parlar-nos")
    >>> toks[-1].translated = "parlar-nos"
    >>> corregeix_elisio_de_abans(toks, len(toks) - 1)
    >>> detokenize(toks)
    'de parlar-nos'
    """
    tok = tokens[index]
    if not _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(tok.translated):
        return
    i_anterior = None
    for i in range(index - 1, -1, -1):
        if tokens[i].surface.isspace():
            continue
        i_anterior = i
        break
    if i_anterior is None or tokens[i_anterior].translated.lower() != "de":
        return
    anterior = tokens[i_anterior]
    anterior.translated = preserva_majuscula(anterior.surface, "d'")
    anterior.is_translated = True
    for espai in tokens[i_anterior + 1 : index]:
        espai.translated = ""


# Contraccions "a"+"el" -> "al", "de"+"el" -> "del" -- mateixa taula que
# `_PREPOSICIONS_CONTRAIBLES` pero invertida (clau = contracció, valor =
# preposició solta), per a `corregeix_contraccio_al_abans`.
_CONTRACCIO_A_PREPOSICIO = {"al": "a", "del": "de"}


def corregeix_contraccio_al_abans(tokens: list[Token], index: int) -> None:
    """Si `tokens[index]` ha canviat de consonant inicial a vocal/h muda
    com a resultat d'una substitució (lookup exacte), i el token real
    anterior és la contracció "al" o "del" ("a"+"el", "de"+"el"), la
    desfà en "a"/"de" solt seguit de "l'" enganxat a la paraula ja
    traduïda -- "al sortir" -> "a l'eixir" quan "sortir" (consonant
    inicial) es tradueix a "eixir" (vocal inicial).

    Mirall invers d'`aplica_amb_prefix_elidit` (que DESFÀ una elisió que
    ja no té sentit perquè la paraula ha passat de vocal a consonant);
    ací el cas és el contrari -- una paraula consonant es torna vocal i
    cal CREAR l'elisió que abans no calia, igual que
    `corregeix_elisio_de_abans` pero partint d'una contracció ("al"/"del")
    en compte d'una preposició solta ("de").

    Cas real trobat (13/10/2026, RC016, cat->val): "Al sortir a
    l'exterior, la lava discorre..." es convertia en "Al eixir a
    l'exterior..." en compte d'"A l'eixir a l'exterior...".
    `cat_val/lexic.py` és el cridador conegut hui (lookup d'una paraula).

    >>> toks = tokenize("Al sortir a l'exterior.")
    >>> toks[2].translated = "eixir"
    >>> corregeix_contraccio_al_abans(toks, 2)
    >>> detokenize(toks)
    "A l'eixir a l'exterior."

    Si el token anterior no és "al"/"del", no fa res:

    >>> toks = tokenize("Vaig eixir a l'exterior.")
    >>> toks[2].translated = "eixir"
    >>> corregeix_contraccio_al_abans(toks, 2)
    >>> detokenize(toks)
    "Vaig eixir a l'exterior."

    Si la forma traduïda seguix començant en consonant, tampoc fa res:

    >>> toks = tokenize("Al parlar clar.")
    >>> toks[2].translated = "parlar"
    >>> corregeix_contraccio_al_abans(toks, 2)
    >>> detokenize(toks)
    'Al parlar clar.'
    """
    tok = tokens[index]
    if not _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(tok.translated):
        return
    i_anterior = None
    for i in range(index - 1, -1, -1):
        if tokens[i].surface.isspace():
            continue
        i_anterior = i
        break
    if i_anterior is None:
        return
    anterior = tokens[i_anterior]
    preposicio = _CONTRACCIO_A_PREPOSICIO.get(anterior.translated.lower())
    if preposicio is None:
        return
    anterior.translated = preserva_majuscula(anterior.surface, preposicio)
    anterior.is_translated = True
    tok.translated = "l'" + tok.translated


# "la" NO s'apostrofa davant de i/u àtones (amb h o sense): "la universitat",
# "la idea", "la humitat" -- norma ortogràfica general, igual als dos
# dialectes. Davant de í/ú tòniques (accentuades) sí: "l'última".
_I_U_ATONES_RE = re.compile(r"^[hH]?[iuïüIUÏÜ]")


def corregeix_article_abans(tokens: list[Token], index: int) -> None:
    """Germana de `corregeix_contraccio_al_abans` per a l'article solt: si
    `tokens[index]` ha passat a començar en vocal/h muda per una
    substitució, i el token real anterior és l'article "el"/"la", l'apostrofa
    ("el darrer" -> "el últim" -> "l'últim").

    Casos reals trobats (20/10/2026, gplsi cat->val, ~15 aparicions): "el
    darrer"->"l'últim", "la darrera"->"l'última", "el batlle"->"l'alcalde",
    "la sortida"->"l'eixida".

    >>> toks = tokenize("Va ser el darrer viatge.")
    >>> toks[6].translated = "últim"
    >>> corregeix_article_abans(toks, 6)
    >>> detokenize(toks)
    "Va ser l'últim viatge."

    Majúscula de l'article conservada:

    >>> toks = tokenize("El batlle parla.")
    >>> toks[2].translated = "alcalde"
    >>> corregeix_article_abans(toks, 2)
    >>> detokenize(toks)
    "L'alcalde parla."

    "la" davant d'i/u àtona no s'apostrofa, davant de tònica sí:

    >>> toks = tokenize("la cosa")
    >>> toks[2].translated = "universitat"
    >>> corregeix_article_abans(toks, 2)
    >>> detokenize(toks)
    'la universitat'
    >>> toks = tokenize("la darrera")
    >>> toks[2].translated = "última"
    >>> corregeix_article_abans(toks, 2)
    >>> detokenize(toks)
    "l'última"

    Si la forma traduïda seguix començant en consonant, no fa res:

    >>> toks = tokenize("el noi")
    >>> toks[2].translated = "xic"
    >>> corregeix_article_abans(toks, 2)
    >>> detokenize(toks)
    'el xic'
    """
    tok = tokens[index]
    if not _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(tok.translated):
        return
    i_anterior = None
    for i in range(index - 1, -1, -1):
        if tokens[i].surface.isspace():
            continue
        i_anterior = i
        break
    if i_anterior is None:
        return
    anterior = tokens[i_anterior]
    article = anterior.translated.lower()
    if article not in ("el", "la"):
        return
    if article == "la" and _I_U_ATONES_RE.match(tok.translated):
        return
    apostrof = "L'" if anterior.translated[:1].isupper() else "l'"
    anterior.translated = ""
    anterior.is_translated = True
    for espai in tokens[i_anterior + 1 : index]:
        espai.translated = ""
        espai.is_translated = True
    tok.translated = apostrof + tok.translated


# Determinants femenins i el seu parell masculí -- mateixes formes ja
# documentades a `concordanca_dos_dues.py` (`_MARCADORS_FEMENI_PLURAL`)
# mes les singulars. Taula tancada, curada a mà. Compartida entre les dos
# direccions (08/10/2026, abans vivia només a `lexic.py`): tant
# "LexicRule" (occidental->oriental, vore eixe mòdul) com la seua futura
# parella en sentit invers necessiten corregir el determinant quan una
# substitució canvia el gènere gramatical sencer de la paraula.
DET_FEM_A_MASC = {
    "la": "el",
    "una": "un",
    "esta": "este",
    "eixa": "eixe",
    "aqueixa": "aqueix",
    "aquella": "aquell",
    "les": "els",
    "unes": "uns",
    "estes": "estos",
    "eixes": "eixos",
    "aqueixes": "aqueixos",
    "aquelles": "aquells",
}
DET_MASC_A_FEM = {masc: fem for fem, masc in DET_FEM_A_MASC.items()}

# Contraccions preposició + article masculí i la seua forma desfeta en
# femení (22/10/2026): "del blat de moro" -> "de la dacsa".
_CONTRACCIO_A_FEMENI = {
    "al": "a la", "del": "de la", "pel": "per la",
    "als": "a les", "dels": "de les", "pels": "per les",
}
_PREPOSICIO_ARTICLE_A_CONTRACCIO = {
    (desfeta.split()[0], "el" if contr.endswith("l") else "els"): contr
    for contr, desfeta in _CONTRACCIO_A_FEMENI.items()
}


def _index_anterior_real(tokens: list[Token], index: int) -> int | None:
    for i in range(index - 1, -1, -1):
        if not tokens[i].surface.isspace():
            return i
    return None


def corregeix_determinant_abans(tokens: list[Token], index: int, genere_nou: str) -> None:
    """Corregix el determinant IMMEDIATAMENT anterior (saltant espais)
    perquè concorde amb `genere_nou` ("m" o "f"). Si no hi ha determinant
    conegut just davant, no fa res (preferix fals negatiu). L'apòstrof
    ("la eixida" -> "l'eixida") el posa després `corregeix_article_abans`.

    >>> toks = tokenize("la dacsa")
    >>> corregeix_determinant_abans(toks, 2, "m")
    >>> [t.translated for t in toks]
    ['el', ' ', 'dacsa']

    >>> toks = tokenize("el blat de moro")
    >>> corregeix_determinant_abans(toks, 2, "f")
    >>> [t.translated for t in toks]
    ['la', ' ', 'blat', ' ', 'de', ' ', 'moro']

    Contraccions, en els dos sentits:

    >>> toks = tokenize("Pel blat")
    >>> toks[2].translated = "dacsa"
    >>> corregeix_determinant_abans(toks, 2, "f")
    >>> detokenize(toks)
    'Per la dacsa'
    >>> toks = tokenize("de les despeses")
    >>> toks[4].translated = "gastos"
    >>> corregeix_determinant_abans(toks, 4, "m")
    >>> detokenize(toks)
    'dels gastos'

    Davant de vocal la preposició no es contrau (l'apòstrof el posa
    `corregeix_article_abans`):

    >>> toks = tokenize("de la sortida")
    >>> toks[4].translated = "eixit"
    >>> corregeix_determinant_abans(toks, 4, "m")
    >>> detokenize(toks)
    'de el eixit'
    """
    i_anterior = _index_anterior_real(tokens, index)
    if i_anterior is None:
        return
    anterior = tokens[i_anterior]
    actual = anterior.translated.lower()
    if genere_nou == "f" and actual in _CONTRACCIO_A_FEMENI:
        anterior.translated = preserva_majuscula(anterior.surface, _CONTRACCIO_A_FEMENI[actual])
        anterior.is_translated = True
        return
    taula = DET_FEM_A_MASC if genere_nou == "m" else DET_MASC_A_FEM
    nova_forma = taula.get(actual)
    if nova_forma is None:
        return
    anterior.translated = preserva_majuscula(anterior.translated, nova_forma)
    anterior.is_translated = True
    if genere_nou != "m" or _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(tokens[index].translated):
        return
    i_prep = _index_anterior_real(tokens, i_anterior)
    if i_prep is None:
        return
    prep = tokens[i_prep]
    contraccio = _PREPOSICIO_ARTICLE_A_CONTRACCIO.get((prep.translated.lower(), nova_forma))
    if contraccio is None:
        return
    prep.translated = preserva_majuscula(prep.translated, contraccio)
    prep.is_translated = True
    anterior.translated = ""
    for espai in tokens[i_prep + 1 : index]:
        if espai.surface.isspace():
            espai.translated = ""
            espai.is_translated = True
    tokens[i_prep + 1].translated = " "


# Pronoms febles enclítics reals de valencià/català, enganxats al final
# d'un verb amb apòstrof (quan el verb acaba en vocal i el clític comença
# en vocal/h muda: "traure'n", "porta'l") o amb guionet (la resta de
# casos: "dir-li", "vine't-en"). Llista TANCADA dels clítics simples mes
# habituals -- els combinats (dos clítics seguits, "porta-te'l") no estan
# coberts perque encara no hi ha cap cas real que ho necessite; s'amplia
# nomes amb evidencia, com la resta de llistes d'este projecte.
_SUFIX_ELIDIT_RE = re.compile(
    r"^(.+?)(['’ʼ-])(me|te|se|nos|vos|los|les|la|lo|li|ho|hi|ne|ls|ns|m|t|s|n|l)$",
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


def paraules_segudents_son(tokens: list[Token], index: int, paraules: list[str]) -> bool:
    """Torna `True` si les properes `len(paraules)` paraules reals despres
    de `index` (saltant espais en blanc) son exactament `paraules`, en
    orde i comparades en minuscules sobre `tok.surface` (no
    `tok.translated` -- aixina la comprovacio val siga quin siga l'orde
    d'esta capa respecte a `possessius.py`/`demostratius.py`).

    Usat per locucions prepositives fixes (vore
    `preposicions_locucions.py`) on cal mirar diverses paraules seguides,
    no nomes una. Normalitza l'apòstrof (`'`/`’`) als dos costats abans de
    comparar, perquè el corpus real barreja els dos (p.ex. "l’interior"
    amb apòstrof tipogràfic) -- mateix criteri que `separa_prefix_elidit`.

    >>> toks = tokenize("La seu en la ciutat de Valencia.")
    >>> idx = [t.surface for t in toks].index("en")
    >>> paraules_segudents_son(toks, idx, ["la", "ciutat"])
    True
    >>> paraules_segudents_son(toks, idx, ["la", "poble"])
    False
    >>> paraules_segudents_son(toks, idx, ["la", "ciutat", "de", "valencia"])
    True

    >>> toks = tokenize("Esta en l’interior de la frase.")
    >>> idx = [t.surface for t in toks].index("en")
    >>> paraules_segudents_son(toks, idx, ["l'interior"])
    True
    """
    def _normalitza(s: str) -> str:
        return s.replace("’", "'").replace("ʼ", "'")

    trobades: list[str] = []
    for tok in tokens[index + 1 :]:
        if tok.surface.isspace():
            continue
        trobades.append(_normalitza(tok.surface.lower()))
        if len(trobades) == len(paraules):
            break
    return trobades == [_normalitza(p.lower()) for p in paraules]


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
    (pipeline/03_seleccio_de_model/evalua_models.py, `glossari_per_frase()`), afegida
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


# Homògrafs entre categories (22/10/2026): substituïx
# `categoria_gramatical_lexic.json`, una llista feta a mà, pel que ja diu
# el propi lèxic del proveïdor. Les entrades `problema: "homonimia_lexica"`
# porten `forma_problematica` (la forma ambigua), `categoria` (la de la
# lectura dialectal) i `lemas` (totes les lectures possibles amb la seua
# categoria: "nou [adj]", "nou [n]", "nou [num]"). Segons la guia del
# proveïdor, si cap altra lectura comparteix la categoria de l'entrada,
# spaCy pot decidir; si la comparteix, no (caldria un LLM). Mateix criteri
# que l'IPD des del 21/10/2026, que ara el reutilitza d'ací.
LEXIC_GENERAL_PATH = Path(__file__).resolve().parent.parent / "data" / "lexic_general.json"

# Categoria del proveïdor -> etiquetes POS d'spaCy.
_POS_PER_CATEGORIA = {
    "n": frozenset({"NOUN", "PROPN"}),
    "adj": frozenset({"ADJ"}),
    "adv": frozenset({"ADV"}),
    "pr": frozenset({"ADP"}),
    "num": frozenset({"NUM"}),
    "v": frozenset({"VERB", "AUX"}),
}
_CATEGORIES_LEMA_RE = re.compile(r"\[([^\]]*)\]")


def carrega_homografs(
    path: Path = LEXIC_GENERAL_PATH,
) -> tuple[dict[str, frozenset[str]], frozenset[str]]:
    """Homògrafs declarats pel proveïdor. Torna:

    - `resolubles`: `{forma_problematica: etiquetes spaCy de la lectura
      dialectal}` quan cap altra lectura dels `lemas` comparteix la
      categoria de l'entrada -- spaCy pot decidir;
    - `irresolubles`: formes on la categoria dialectal la comparteix una
      altra lectura -- spaCy no pot decidir.

    >>> resolubles, irresolubles = carrega_homografs()
    >>> sorted(resolubles["nou"]), sorted(resolubles["manca"])
    (['NOUN', 'PROPN'], ['NOUN', 'PROPN'])
    >>> "bes" in irresolubles, "blanca" in irresolubles
    (True, True)
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    resolubles: dict[str, frozenset[str]] = {}
    irresolubles: set[str] = set()
    for entrada in dades:
        if entrada.get("problema") != "homonimia_lexica":
            continue
        forma = (entrada.get("forma_problematica") or "").strip().lower()
        categoria = entrada.get("categoria")
        if not forma:
            continue
        lectures = [
            {c.strip() for c in m.group(1).split(",")}
            for lema in entrada.get("lemas") or []
            for m in [_CATEGORIES_LEMA_RE.search(lema)]
            if m
        ]
        amb_categoria = sum(1 for cats in lectures if categoria in cats)
        if categoria in _POS_PER_CATEGORIA and amb_categoria == 1:
            resolubles[forma] = _POS_PER_CATEGORIA[categoria]
        else:
            irresolubles.add(forma)
    irresolubles -= set(resolubles)
    return resolubles, frozenset(irresolubles)


def homograf_compatible(tok_pos: str, paraula: str, resolubles: dict[str, frozenset[str]]) -> bool:
    """`True` si `paraula` no és un homògraf resoluble, o si spaCy li dona
    la categoria de la lectura dialectal. Sense etiqueta d'spaCy, `False`
    (preferix fals negatiu: sense spaCy "nou" mai es tradueix a "anou").

    >>> res = {"nou": frozenset({"NOUN"})}
    >>> homograf_compatible("NOUN", "nou", res), homograf_compatible("ADJ", "nou", res)
    (True, False)
    >>> homograf_compatible("", "nou", res), homograf_compatible("ADJ", "casa", res)
    (False, True)
    """
    lectura = resolubles.get(paraula.lower())
    if lectura is None:
        return True
    return tok_pos in lectura


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
