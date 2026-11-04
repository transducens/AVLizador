"""
cat_val/clitic_lhi.py -- Regla de reordenació i apostrofació del grup
proclític "l'hi" (català) -> "li'l" (valencià).

**El problema (04/11/2026)**: el token "l'hi" és un grup de dos pronoms
clítics proclítics catalans (OD "l'" + locatiu/datiu "hi") que en
valencià es reordenen i donen "li'l" (datiu "li" + OD "l'"). El
diccionari (`lexic_general.json`) té l'entrada directa "l'hi" -> "li'l",
però el resultat brut "li'l" no és una forma lliure que puga quedar al
text tal qual: cal SEPARAR-LA en "li" (que va sol, com a primer clític) i
"l'" (que s'apostrofa cap a la dreta sobre el verb o mot següent).

**Apostrofació cap a la dreta**:
- Si el mot següent comença en vocal o h muda: el token es partix en
  "li" (sol) i "l'" apostrofat cap al verb -> "Li l'enviaré".
- Si el mot següent comença en consonant: "l'" no pot apostrofar, però
  tampoc es desfà en "el" -- la forma correcta en posició proclítica
  davant de consonant és "li'l" (el grup sencer, separat del verb per
  un espai) -> "Li'l porte". El token es queda com a "Li'l" i el verb
  no es toca.

**Majúscules**: si el token original era "L'hi" (majúscula), el resultat
conserva la majúscula: "Li l'..." o "Li'l ...".

**Posició en el pipeline**: esta regla s'aplica DESPRÉS de `LexicInversRule`
(que és qui substitueix "l'hi" per "li'l" via el diccionari) i ABANS de
qualsevol altra capa que puga tocar el verb següent. En `engine.py` va
immediatament darrere de `LexicInversRule`.

Exemples:

    Verb següent comença en vocal:
    "L'hi enviaré"  -> "Li l'enviaré"
    "L'hi aportarà" -> "Li l'aportarà"

    Verb següent comença en consonant:
    "L'hi portaré"  -> "Li'l portaré"
    "L'hi demanarà" -> "Li'l demanarà"

    Token en minúscula (posició no inicial de frase):
    "... que l'hi envie ..." -> "... que li l'envie ..."
"""

from __future__ import annotations

import re

from .. import Token, preserva_majuscula

# La forma que produïx el diccionari per a "l'hi".
_FORMA_ENTRADA = "li'l"

# Detecta vocal inicial (o h muda seguida de vocal), igual que
# `_COMENCA_EN_VOCAL_O_H_MUDA_RE` de `rules/__init__.py` -- es replica
# ací per a no crear una dependència circular entre submòduls.
_VOCAL_INICIAL_RE = re.compile(
    r"^(?:[aeiouàèéíòóúïüAEIOUÀÈÉÍÒÓÚÏÜ]|[hH][aeiouàèéíòóúïüAEIOUÏÜ])"
)


def _primer_token_paraula(tokens: list[Token], des_de: int) -> int | None:
    """Índex del primer token que és una paraula real (no espai ni
    puntuació) a partir de `des_de` (exclòs). Torna `None` si no n'hi ha.
    """
    for i in range(des_de + 1, len(tokens)):
        if tokens[i].surface[:1].isalpha():
            return i
    return None


class CliticLhiRule:
    """Busca tokens on `translated` és "li'l" (resultat de traduir "l'hi"
    via el diccionari) i els processa segons la vocal/consonant inicial
    del mot següent:
    - Vocal: partix en "li" + "l'" apostrofat al mot -> "Li l'enviaré"
    - Consonant: conserva "li'l" sencer (amb majúscula si escau) separat
      del verb per l'espai ja existent -> "Li'l porte"

    >>> from .. import tokenize, detokenize
    >>> from .. import pos_tagger

    >>> def tradueix(text):
    ...     toks = tokenize(text)
    ...     pos_tagger.etiqueta(toks)
    ...     # Simula que LexicInversRule ja ha fet la substitució "l'hi" -> "li'l"
    ...     for t in toks:
    ...         if t.surface.lower() in ("l'hi", "l\u2019hi", "l\u02bchi"):
    ...             t.translated = preserva_majuscula(t.surface, "li'l")
    ...             t.is_translated = True
    ...     return detokenize(CliticLhiRule().apply(toks))

    Verb inicial en vocal:

    >>> tradueix("L'hi enviaré demà.")
    "Li l'enviaré demà."

    Verb inicial en consonant (el grup "li'l" queda sencer):

    >>> tradueix("L'hi portaré demà.")
    "Li'l portaré demà."

    Token en minúscula (mig de frase):

    >>> tradueix("Vull que l'hi envie aviat.")
    "Vull que li l'envie aviat."

    >>> tradueix("Vull que l'hi done.")
    "Vull que li'l done."

    Sense mot següent (fi de frase, cas degenerat):

    >>> tradueix("No sé per què l'hi.")
    "No sé per què li'l."
    """

    def apply(self, tokens: list[Token]) -> list[Token]:
        for i, tok in enumerate(tokens):
            if tok.translated.lower() != _FORMA_ENTRADA:
                continue
            majuscula = tok.surface[:1].isupper()

            i_seg = _primer_token_paraula(tokens, i)

            if i_seg is None:
                # Cap mot seguent: deixa "li'l" tal qual (cas degenerat)
                continue

            mot_seg = tokens[i_seg].translated or tokens[i_seg].surface

            if _VOCAL_INICIAL_RE.match(mot_seg):
                # Vocal: "li" sol + "l'" apostrofat al mot seguent
                tok.translated = "Li" if majuscula else "li"
                tok.is_translated = True
                tokens[i_seg].translated = "l'" + mot_seg
                tokens[i_seg].is_translated = True
            else:
                # Consonant: "li'l" sencer (amb majúscula si escau),
                # el verb no es toca
                tok.translated = "Li'l" if majuscula else "li'l"
                tok.is_translated = True

        return tokens