"""
numerals.py -- Dos fenòmens numerals independents, de naturalesa molt
diferent (per això van junts en un mòdul però són DOS mecanismes, no una
sola regla). Font: final/02_reglas_dialectales/reglas_dialectales.md,
secció 6.

  1. Arrel "huit" -> "vuit" (determinista): apareix dins de QUALSEVOL
     numeral que la continga, sol o en compost amb guionet
     (huitanta-huit, cinquanta-huit, huit-cents...). Com el tokenitzador
     d'este paquet tracta "cinquanta-huit" com UN sol token (vore la
     decisió de disseny a rules/__init__.py), esta regla busca la
     subcadena "huit" DINS del token, no fa un lookup exacte de paraula
     sencera -- si no, mai trobaria "huit" dins d'un compost.
     Excepció real i documentada: "díhuit" -> "divuit" NO ve d'esta arrel
     (perdria l'accent de manera incorrecta si s'aplicara la substitució
     de subcadena: "díhuit" contindria "huit" i donaria "dívuit", que no
     és la forma oriental correcta) -- per això és un cas a part, resolt
     ABANS de mirar la subcadena genèrica.

  2. Ordinals -é -> -è: patró general segons la font (113 lemes
     confirmats a Apertium), però ací NOMÉS s'implementen els casos que la
     font dona explícitament com a taula (secció 6.1) -- NO una regla de
     sufix genèrica "-é final -> -è final" aplicada a qualsevol paraula,
     perquè hi ha paraules que acaben en é sense ser ordinals (p.ex.
     manlleus com "cafè/café") i la font no dona cap llista tancada
     d'exclusions per a poder generalitzar seguint amb seguretat.
     # AMBIGÚ: la font (secció 6, taula de compostos) escriu alguns
     # exemples occidentals amb è en compte de é ("huitantè",
     # "huitanta-cinquè" a la taula de huit/vuit, quan la resta del
     # document diu que l'ordinal occidental acaba en é) -- sembla una
     # errata de transcripció del document font, no un patró real
     # diferent. No s'ha "arreglat" en silenci: esta implementació aplica
     # els dos mecanismes (arrel + sufix ordinal) per separat, així que
     # el resultat final és correcte encara que eixe exemple concret del
     # document tinga l'accent que no toca.

NO s'implementa ací (queda pendent, no hi ha taula font prou àmplia):
compostos ordinals amb guionet fora dels que ja dona explícitament la
taula de la secció 6.1 (p.ex. "vint-i-uné", "trenta-dosé" -- la font els
esmenta com a exemple del patró general però no els llista un a un).

  4. Arrels "dinou"/"disset" -> "dinou"/"disset" oriental amb accent
     obert ("dènou" -> "dinou", "dèsset" -> "disset"), i els seus derivats
     en "-ena"/"-é" ("denovena" -> "dinovena", "dessetè" -> "dissetè").
     Font: `numerales_limpio.json` de Mauricio (equip AVLizador,
     29/09/2026), contrastat contra Apertium. A diferència de "huit"/
     "vuit", estes arrels NO comparteixen cap subcadena comuna entre els
     dos dialectes, així que no poden generalitzar-se amb una substitució
     de subcadena com `_substitueix_huit` -- són una llista tancada de 10
     formes (2 arrels + 4 derivats cada una). La resta del fitxer de
     Mauricio (compostos de la família huit/vuit, p.ex. "huitantena" ->
     "vuitantena") ja queda coberta correctament per la substitució de
     subcadena existent -- comprovat una a una, no calia afegir cap
     entrada nova per a eixa família.
     # AMBIGÚ: el fitxer font també conté 4 entrades per a "vuitavat"
     ("huitavdes"/"huitavda"/"huitavts"/"huitavt", totes mapejades al
     mateix catalan "vuitavat") que semblen una extracció trencada
     (probablement havien de ser les 4 formes de gènere/nombre
     "vuitavat/vuitavada/vuitavats/vuitavades" i es va perdre
     l'alineació) -- no s'han incorporat ací; de totes formes ja contenen
     "huit" com a subcadena, així que la substitució genèrica ja les
     tractaria raonablement bé encara que no estiguen en cap llista.

  3. Concordança de gènere de "dos": NO és una substitució de text fixa
     (vore secció 6.3 de la font, "Advertència d'aplicació" explícita).
     L'occidental fa servir "dos" per als dos gèneres; l'oriental exigix
     "dues" en femení. Sense spaCy (pos == "" quasi sempre), esta regla
     mira la paraula IMMEDIATAMENT següent i aplica una heurística feble:
     si acaba en "-a" o "-es" (marca típica -però no infal·lible- de
     femení), tracta "dos" com a femení i el canvia a "dues".
     # AMBIGÚ: esta heurística falla amb substantius femenins que no
     # acaben en -a/-es/-ió/-ions (p.ex. "dos mans" hauria de ser "dues
     # mans", però "mans" no dispara l'heurística -- es queda "dos" per
     # error). És un fals negatiu conegut, no arreglat: preferible a un
     # fals positiu (canviar "dos" a "dues" davant d'un substantiu
     # masculí seria un error més visible i estrany).

     Ampliació (29/09/2026, RC062): quan darrere de "dos" NO ve cap
     paraula (típicament puntuació, com en "...en dos: establir..."),
     "dos" pot referir-se ANAFÒRICAMENT a un nom ja dit abans a la mateixa
     frase ("les seues funcions... en dos:"). En eixe cas concret, la
     regla mira cap arrere (`_paraula_anterior_plural_femenina`) buscant
     la paraula més pròxima que semble femenina, aturant-se en un final
     de frase real. Només s'activa quan la cerca cap avant no ha trobat
     CAP paraula (mai quan sí n'ha trobat una i simplement no pareix
     femenina, com "dos xics" -- eixe cas es queda intacte igual que
     abans). De pas s'ha ampliat `_sembla_femeni` per a reconéixer també
     "-ió"/"-ions" ("funcions"), un sufix fiable (pràcticament cap nom
     acabat així és masculí en català), a diferència de generalitzar més
     el "-a"/"-es" existent.
"""

from __future__ import annotations

import re

from . import Token, preserva_majuscula

# ─── 1. Arrel huit -> vuit ──────────────────────────────────────────────────

_DIHUIT_EXCEPCIO = {"díhuit": "divuit"}
_HUIT_RE = re.compile(r"huit", re.IGNORECASE)


def _substitueix_huit(paraula: str) -> str | None:
    """Torna la paraula amb "huit" canviat per "vuit", o None si no en
    conté. Comprova primer l'excepció "díhuit" (vore docstring del mòdul).

    >>> _substitueix_huit("huitanta")
    'vuitanta'
    >>> _substitueix_huit("cinquanta-huit")
    'cinquanta-vuit'
    >>> _substitueix_huit("díhuit")
    'divuit'
    >>> _substitueix_huit("xiquet") is None
    True
    """
    minuscules = paraula.lower()
    if minuscules in _DIHUIT_EXCEPCIO:
        return preserva_majuscula(paraula, _DIHUIT_EXCEPCIO[minuscules])
    if "huit" not in minuscules:
        return None
    nova = _HUIT_RE.sub("vuit", minuscules)
    return preserva_majuscula(paraula, nova)


# ─── 2. Ordinals -é -> -è (només els confirmats explícitament a la font) ────

_ORDINALS = {
    "cinqué": "cinquè",
    "sisé": "sisè",
    "seté": "setè",
    "vuité": "vuitè",
    "nové": "novè",
    "desé": "desè",
    "dotzé": "dotzè",
    "tretzé": "tretzè",
    "catorzé": "catorzè",
    "quinzé": "quinzè",
    "vinté": "vintè",
    "trenté": "trentè",
    "quaranté": "quarantè",
    "cinquanté": "cinquantè",
}

# ─── 4. Arrels "dinou"/"disset" (i derivats), vore mecanisme 4 del docstring ─

_DINOU_DISSET = {
    "dènou": "dinou",
    "denovena": "dinovena",
    "denovens": "dinovens",
    "denovenes": "dinovenes",
    "denové": "dinovè",
    "dèsset": "disset",
    "dessetena": "dissetena",
    "dessetens": "dissetens",
    "dessetenes": "dissetenes",
    "desseté": "dissetè",
}

# ─── 3. Concordança "dos" / "dues" ──────────────────────────────────────────

# "-ió"/"-ions" s'afig a la banda del "-a"/"-es" general perquè és un cas
# fiable, no una generalització arriscada: en català pràcticament cap nom
# acabat en "-ió" és masculí (funció, informació, nació...), a diferència
# de "-a"/"-es", on sí hi ha excepcions conegudes (vore mòdul gentilicis).
# Trobat auditant el benchmark real (RC062, 29/09/2026): "les seues
# funcions" mai disparava l'heurística perquè "funcions" no acaba en
# "-a"/"-es".
_FEMENI_FEBLE_RE = re.compile(r"(a|es|ions?)$", re.IGNORECASE)

# Puntuació que talla la recerca cap arrere de l'antecedent de "dos"
# (vore _paraula_anterior_plural_femenina): més enllà d'un final de frase
# real, l'antecedent ja no és fiable.
_FI_CLAUSULA = {".", "!", "?"}

# Paraules funcionals curtes que casualment acaben en "-a"/"-es" sense ser
# mai el nom que done gènere a "dos" (article, pronom feble...) -- sense
# esta exclusió, "es" (pronom reflexiu) donaria un fals positiu trivial en
# QUALSEVOL frase reflexiva ("es poden agrupar en dos: ..."), ja que la
# paraula sencera "es" casa amb el sufix "-es" per pura coincidència de
# longitud. Trobat provant `_paraula_anterior_plural_femenina` amb un
# exemple negatiu sintètic ("dos" masculí després de puntuació).
_PARAULES_FUNCIONALS = {"es", "se", "la", "les", "el", "els", "un", "uns", "una", "unes"}


def _seguent_paraula(tokens: list[Token], index: int) -> Token | None:
    """Torna el següent token que és una paraula real, saltant espais en
    blanc. S'atura (torna None) si troba puntuació abans -- "dos" seguit
    de coma o punt no té cap substantiu clar que li done gènere."""
    for tok in tokens[index + 1 :]:
        if tok.surface.isspace():
            continue
        if tok.surface[:1].isalpha():
            return tok
        return None
    return None


def _paraula_anterior_plural_femenina(tokens: list[Token], index: int) -> bool:
    """Fallback quan `_seguent_paraula` no troba cap paraula darrere de
    "dos" (típicament perquè ve seguit de puntuació, com en "...en dos:
    establir..."): mira cap arrere buscant la paraula més pròxima que
    semble femenina (`_sembla_femeni`), aturant-se en trobar un final de
    frase real o l'inici del text.

    Cas real (RC062, 29/09/2026): "Les seues funcions es poden
    sintetitzar en dos: establir..." -- "dos" ací es referix
    anafòricament a "funcions" (dit abans a la mateixa frase), no a cap
    paraula que vinga darrere (que és puntuació, ":"). No fa falta cap
    llista de paraules buides ("es", "poden", "sintetitzar", "en"): cap
    d'elles casa amb `_sembla_femeni`, així que la recerca les travessa
    soles fins arribar a "funcions".

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Les funcions es poden sintetitzar en dos: fer.")
    >>> marca_noms_propis(toks)
    >>> idx = [t.surface for t in toks].index("dos")
    >>> _paraula_anterior_plural_femenina(toks, idx)
    True

    >>> toks = tokenize("Els xics es poden agrupar en dos: alts i baixos.")
    >>> marca_noms_propis(toks)
    >>> idx = [t.surface for t in toks].index("dos")
    >>> _paraula_anterior_plural_femenina(toks, idx)
    False
    """
    for tok in reversed(tokens[:index]):
        if tok.surface.isspace():
            continue
        if tok.surface in _FI_CLAUSULA:
            return False
        if not tok.surface[:1].isalpha():
            continue
        if tok.surface.lower() in _PARAULES_FUNCIONALS:
            continue
        if _sembla_femeni(tok.surface):
            return True
    return False


def _sembla_femeni(paraula: str) -> bool:
    """Heurística feble de gènere sense spaCy -- vore AMBIGÚ al docstring
    del mòdul per les seues limitacions conegudes.

    >>> _sembla_femeni("xiques")
    True
    >>> _sembla_femeni("cadira")
    True
    >>> _sembla_femeni("funcions")
    True
    >>> _sembla_femeni("xics")
    False
    >>> _sembla_femeni("mans")  # fals negatiu conegut (vore AMBIGÚ)
    False
    """
    return bool(_FEMENI_FEBLE_RE.search(paraula.lower()))


class NumeralsRule:
    """Aplica, en este orde, els tres mecanismes documentats al mòdul.

    >>> from . import tokenize, marca_noms_propis
    >>> toks = tokenize("Tinc huitanta anys i vaig ser el cinqué.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('huitanta', 'vuitanta'), ('cinqué', 'cinquè')]

    >>> toks = tokenize("Dos xiques i dos xics van vindre.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('Dos', 'Dues')]

    Arrels "dinou"/"disset" i derivats (mecanisme 4, vore docstring):

    >>> toks = tokenize("Tenia dènou anys i vivia al pis denové.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dènou', 'dinou'), ('denové', 'dinovè')]

    "dos" que es referix a un nom dit ABANS a la mateixa frase, quan
    darrere no ve cap paraula (puntuació) -- fallback amb
    `_paraula_anterior_plural_femenina`, cas real RC062:

    >>> toks = tokenize("Les seues funcions es poden sintetitzar en dos: fer normes.")
    >>> marca_noms_propis(toks)
    >>> toks = NumeralsRule().apply(toks)
    >>> [(t.surface, t.translated) for t in toks if t.is_translated]
    [('dos', 'dues')]
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.is_translated or tok.is_proper_noun:
                continue
            minuscules = tok.surface.lower()

            if minuscules == "dos":
                seguent = _seguent_paraula(tokens, i)
                if seguent is not None:
                    if _sembla_femeni(seguent.surface):
                        tok.translated = preserva_majuscula(tok.surface, "dues")
                        tok.is_translated = True
                elif _paraula_anterior_plural_femenina(tokens, i):
                    tok.translated = preserva_majuscula(tok.surface, "dues")
                    tok.is_translated = True
                continue

            nova_huit = _substitueix_huit(tok.surface)
            if nova_huit is not None:
                tok.translated = nova_huit
                tok.is_translated = True
                continue

            ordinal = _ORDINALS.get(minuscules)
            if ordinal is not None:
                tok.translated = preserva_majuscula(tok.surface, ordinal)
                tok.is_translated = True
                continue

            dinou_disset = _DINOU_DISSET.get(minuscules)
            if dinou_disset is not None:
                tok.translated = preserva_majuscula(tok.surface, dinou_disset)
                tok.is_translated = True
        return tokens
