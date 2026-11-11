"""
traductor/model_llengua -- Postprocessat cat->val amb un MODEL DE LLENGUA
per als homògrafs que el motor no pot resoldre (23/10/2026). Opcional:
`traductor.translate_cat_val` no canvia i no necessita res d'açò.

Com funciona: el motor tradueix la frase; per a cada paraula ambigua del
lèxic (vore `punts.py`) es construïxen les frases valencianes completes,
una per candidat ("Una vegada acabada la reunió..." / "Un colp acabada
la reunió..."), i guanya la que el model de llengua veu més probable. No
es pregunta res al model ni genera text: només puntua frases.

Sistema per tipus de punt (decisió de l'usuari, 23/10/2026):
- `colisio` ("cop", "cops"): el model de llengua.
- `irresoluble` ("calces", "gandula", "gandules"): dos capes. (1) spaCy, si
  dona una categoria que només té l'altra lectura ("molt gandula": ADJ ->
  no es tradueix; `punts.decisio_spacy`); (2) si no, el model, que només
  canvia el motor si guanya per més de `marge` (5; des del 05/11/2026, vore
  `per_defecte` més avall). Primer es va descartar
  el model ací (no separava "gandules" tumbona/persona), però la causa era
  un error de dades: E0592 deia "hamaces" (forma incorrecta; el plural és
  "hamaques") i el model la castigava sempre. Corregida (permís de
  l'usuari), el model separa bé "gandula/gandules" (diferència traduir -
  deixar: tumbona -2,9..+4,8, persona -7,1..-11,7). "calces" no la separa:
  queda com el motor ("bragues").
- `resoluble` ("deu", "reeixida"): spaCy dins del motor i, des del
  29/10/2026, també el model (només canvia el motor si guanya per més de
  `marge`). "nou", "manca", "recuita"... són irresolubles des del 29/10/2026:
  els `lemas` diuen que l'adjectiu també fa de nom. La capa d'spaCy
  dels irresolubles deixa la paraula catalana quan spaCy dona una categoria
  distinta de la dialectal ("un nou procés" ADJ, "la regió manca de" VERB);
  amb NOUN decidix el model.
- Des del 29/10/2026 `traductor.translate_cat_val` és SEMPRE este sistema
  (decisió de l'usuari); el motor sol és `translate_cat_val_motor`.

Resultats (23/10/2026, FLOR-760M): benchmark combinat
`pipeline/03_seleccio_de_model/benchmark_sistema_final_cat_val.json`
motor 190/253 -> sistema 227/253 (151 igual, colisio 0 -> 31/33,
irresoluble 12 -> 18/24; sense el model als irresolubles, 14/24 i 223/253);
BOE ampli 2.000 frases: 1.206/2.000 (el motor sol en dona 1.200 a les mesures
anteriors; al BOE no hi ha cap irresoluble).

Criteri (`Criteri`); el valor per defecte és el millor de l'avaluació del
23/10/2026 amb FLOR-760M:
- `lam` (PMI): es resta `lam` x log P(candidat sol), per a compensar que
  una paraula siga més freqüent que l'altra en general.
- `norma`: "suma" (log-probabilitat de tota la frase) o "mitjana" (per token).
- `marge` i `per_defecte`: als homògrafs (el motor ja ha traduït), la
  forma per defecte només canvia si l'altra guanya per més de `marge` punts
  de log-probabilitat. Des del 05/11/2026 (decisió de l'usuari) és
  `per_defecte="catala"` amb `marge=2`: només es tradueix si el model veu
  la traducció més probable per més de 2 punts (unes 7 vegades més
  probable); si no, es queda la paraula catalana. Criteri: és millor no
  traduir (la paraula catalana, sovint vàlida també en valencià) que
  traduir malament (canvia el sentit: "calces" d'època -> "bragues").
  Abans era `per_defecte="motor"` amb `marge=5`. Detall i xifres al README
  (secció "Margen 2 con la catalana por defecto").
- `puntuacio`: "frase" (tota la frase) o "dreta" (experimental: només el
  que ve DESPRÉS de la paraula, condicionat a la paraula; deixa fora el
  terme "com de freqüent és la paraula ací", on hi ha el biaix del model
  cap a la forma catalana).
- `spacy_irresolubles`: la capa 1 d'spaCy per als irresolubles.
- `model_irresolubles`: el model també per als irresolubles quan spaCy no
  decidix (per defecte `True`; amb `False` es queda el motor i el model ni
  es crida).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rules import detokenize
from .punts import TIPUS_PER_DEFECTE, Punt, base_neutra, carrega_punts, decisio_spacy, detecta, frases_candidates

CONCORDANCA_PER_DEFECTE = "variants"


@dataclass(frozen=True)
class Criteri:
    lam: float = 0.5
    norma: str = "suma"
    marge: float = 2.0  # 05/11/2026, decisió de l'usuari (abans 5,0 amb `per_defecte="motor"`)
    tipus: tuple[str, ...] = TIPUS_PER_DEFECTE
    puntuacio: str = "frase"
    spacy_irresolubles: bool = True
    model_irresolubles: bool = True  # decisió de l'usuari, 23/10/2026 (després de corregir E0592)
    # Què es queda quan el model no guanya per més de `marge`: "catala" (la
    # paraula catalana sense traduir, si és un dels candidats; decisió de
    # l'usuari, 05/11/2026) o "motor" (la tria del motor, normalment la
    # traducció; el criteri d'abans, amb `marge=5.0`).
    per_defecte: str = "catala"


def _valor(d: dict, criteri: Criteri, normalitza: bool = True) -> float:
    if criteri.puntuacio == "dreta":
        valor, n = d["dreta"], d["n_dreta"]
    else:
        valor, n = d["lp"] - criteri.lam * d["prior"], d["n"]
    return valor / max(n, 1) if normalitza and criteri.norma == "mitjana" else valor


def puntuacio(d: dict, criteri: Criteri) -> float:
    """
    >>> d = {"lp": -20.0, "n": 10, "prior": -5.0, "dreta": -8.0, "n_dreta": 4}
    >>> puntuacio(d, Criteri(lam=0.0)), puntuacio(d, Criteri(lam=1.0))
    (-20.0, -15.0)
    >>> puntuacio(d, Criteri(lam=0.0, norma="mitjana")), puntuacio(d, Criteri(puntuacio="dreta"))
    (-2.0, -8.0)
    """
    return _valor(d, criteri)


def tria(punt: Punt, criteri: Criteri) -> str | None:
    """Candidat guanyador. Deixa en `punt.decidit` qui l'ha triat.

    >>> p = Punt(0, "cop", "", "colisio", ["colp", "vegada"], None)
    >>> p.puntuacions = {"colp": {"lp": -30.0, "n": 9, "prior": -35.0},
    ...                  "vegada": {"lp": -25.0, "n": 9, "prior": -20.0}}
    >>> tria(p, Criteri(lam=0.0)), tria(p, Criteri(lam=1.0)), p.decidit
    ('vegada', 'colp', 'model')

    Amb el motor ja decidit, el model només el canvia si guanya per més de
    `marge`:

    >>> p = Punt(0, "calces", "", "irresoluble", ["bragues", "calces"], "bragues")
    >>> p.puntuacions = {"bragues": {"lp": -30.0, "n": 9, "prior": 0.0},
    ...                  "calces": {"lp": -28.0, "n": 9, "prior": 0.0}}
    >>> amb_model = dict(model_irresolubles=True, per_defecte="motor")
    >>> tria(p, Criteri(marge=0.0, **amb_model)), tria(p, Criteri(marge=5.0, **amb_model)), p.decidit
    ('calces', 'bragues', 'motor')

    Amb `per_defecte="catala"` és al revés: es queda la paraula catalana i
    la traducció només entra si guanya per més de `marge`:

    >>> p.puntuacions["bragues"]["lp"] = -26.0
    >>> tria(p, Criteri(per_defecte="catala", marge=1.0)), p.decidit
    ('bragues', 'model')
    >>> tria(p, Criteri(per_defecte="catala", marge=5.0)), p.decidit
    ('calces', 'catala')
    >>> tria(p, Criteri()), p.decidit
    ('calces', 'catala')
    >>> p.puntuacions["bragues"]["lp"] = -25.0
    >>> tria(p, Criteri()), p.decidit
    ('bragues', 'model')
    >>> p.puntuacions["bragues"]["lp"] = -30.0

    Capa d'spaCy dels irresolubles: "molt gandula" (ADJ) no es tradueix,
    sense mirar el model:

    >>> p = Punt(0, "gandula", "", "irresoluble", ["hamaca", "gandula"], "hamaca", pos="ADJ",
    ...          categoria="n", lectures=[{"adj", "n"}, {"n"}])
    >>> p.puntuacions = {"hamaca": {"lp": -1.0, "n": 9, "prior": 0.0},
    ...                  "gandula": {"lp": -50.0, "n": 9, "prior": 0.0}}
    >>> tria(p, Criteri()), p.decidit
    ('gandula', 'spacy')
    >>> tria(p, Criteri(spacy_irresolubles=False, model_irresolubles=True)), p.decidit
    ('hamaca', 'model')

    Sense el model als irresolubles (`model_irresolubles=False`): spaCy i,
    si no decidix, el motor:

    >>> p.pos = "NOUN"
    >>> tria(p, Criteri(model_irresolubles=False)), p.decidit
    ('hamaca', 'motor')
    """
    if punt.tipus == "irresoluble" and criteri.spacy_irresolubles:
        decisio = decisio_spacy(punt)
        if decisio is not None:
            punt.decidit = "spacy"
            return decisio
    usa_model = punt.tipus in criteri.tipus and (punt.tipus != "irresoluble" or criteri.model_irresolubles)
    if not punt.puntuacions or not usa_model:
        punt.decidit = "motor"
        return punt.motor
    valors = {c: puntuacio(d, criteri) for c, d in punt.puntuacions.items()}
    millor = max(valors, key=valors.get)
    defecte, qui = punt.motor, "motor"
    if criteri.per_defecte == "catala" and punt.motor is not None:
        catala = next((c for c in punt.candidats if c.lower() == punt.paraula.lower()), None)
        if catala is not None:
            defecte, qui = catala, "catala"
    if defecte in valors and millor != defecte:
        diferencia = _valor(punt.puntuacions[millor], criteri, False) - _valor(punt.puntuacions[defecte], criteri, False)
        if diferencia <= criteri.marge:
            punt.decidit = qui
            return defecte
    punt.decidit = "model"
    return millor


_MOTOR = None
_PUNTS = None


def _motor():
    global _MOTOR, _PUNTS
    if _MOTOR is None:
        from ..rules.cat_val.engine import RuleEngineInvers

        _MOTOR, _PUNTS = RuleEngineInvers(), carrega_punts()
    return _MOTOR, _PUNTS


def puntua_punts(text: str, model, tipus=TIPUS_PER_DEFECTE,
                 concordanca: str = CONCORDANCA_PER_DEFECTE, tipus_model=None) -> tuple[str, list[Punt]]:
    """Traducció del motor i punts amb les puntuacions del model per a cada
    candidat (cada punt amb la resta de la frase tal com l'ha deixada el
    motor; amb `concordanca="variants"`, la millor variant de concordança
    de cada candidat). `avalua.py` ho usa per a provar molts criteris sense
    tornar a cridar el model. `tipus_model`: els tipus que es puntuen (per
    defecte, tots els de `tipus`); la resta es detecten però el model no es
    crida."""
    motor, punts = _motor()
    tokens = motor.tradueix_tokens(text)
    trobats = detecta(tokens, punts, tipus)
    for punt in trobats:
        base = base_neutra(motor, text, [punt])
        if tipus_model is not None and punt.tipus not in tipus_model:
            # sense model: les frases candidates igualment (spaCy pot triar-ne una)
            punt.frases = {c: detokenize(v[0]) for c, v in frases_candidates(base, punt, "motor").items()}
            continue
        for candidat, variants in frases_candidates(base, punt, concordanca).items():
            millor = None
            for toks in variants:
                frase = detokenize(toks)
                lp, n = model.logprob(frase)
                if millor is None or lp > millor["lp"]:
                    lp_fins, n_fins = model.logprob(detokenize(toks[: punt.index + 1]))
                    millor = {"frase": frase, "lp": lp, "n": n, "dreta": lp - lp_fins, "n_dreta": n - n_fins}
            # Prior = log P(candidat sol). Un model pot donar el seu (`prior`):
            # KenLM amb <s> i </s> no dona la freqüència de la paraula.
            millor["prior"] = getattr(model, "prior", model.logprob)(candidat.lower())[0]
            punt.puntuacions[candidat] = millor
            punt.frases[candidat] = millor["frase"]
    return detokenize(tokens), trobats


def aplica_tries(text_motor: str, trobats: list[Punt], criteri: Criteri) -> str:
    """Text final. Amb un sol punt canviat, la frase guanyadora tal qual;
    amb més d'un, es van encadenant d'esquerra a dreta sobre la frase
    guanyadora de l'anterior (cada frase candidata només difereix del
    motor al seu punt)."""
    text = text_motor
    for punt in trobats:
        punt.tria = tria(punt, criteri)
        if punt.tria is not None and punt.tria != punt.motor:
            nova = punt.frases[punt.tria]
            text = nova if text == text_motor else _fusiona(text, text_motor, nova)
    return text


def _fusiona(actual: str, motor: str, nova: str) -> str:
    """Aplica a `actual` el canvi que `nova` fa respecte de `motor` (per a
    frases amb més d'un punt). Es fa per paraules: les paraules del motor
    que encara estan igual en `actual` donen la posició on va el canvi.

    Abans (fins al 03/11/2026) només es copiaven els canvis d'igual nombre
    de paraules, i es perdia el que desfà un apòstrof ("d'anous" -> "de
    nous"):

    >>> motor = "Hem comprat un cotxe anou i un sac d'anous."
    >>> actual = "Hem comprat un cotxe nou i un sac d'anous."
    >>> _fusiona(actual, motor, "Hem comprat un cotxe anou i un sac de nous.")
    'Hem comprat un cotxe nou i un sac de nous.'
    >>> _fusiona("Una vegada més, d'anous.", "Un cop més, d'anous.", "Un cop més, de nous.")
    'Una vegada més, de nous.'
    """
    import difflib

    a, m, n = actual.split(" "), motor.split(" "), nova.split(" ")
    # paraula del motor -> la mateixa paraula en `actual` (les no tocades)
    mapa = {}
    for op, i1, i2, j1, _ in difflib.SequenceMatcher(a=m, b=a, autojunk=False).get_opcodes():
        if op == "equal":
            mapa.update({i1 + k: j1 + k for k in range(i2 - i1)})
    canvis = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=m, b=n, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        if i1 == i2:  # inserció: just abans de la paraula i1 (o després de la i1-1)
            if i1 in mapa:
                inici = fi = mapa[i1]
            elif i1 - 1 in mapa:
                inici = fi = mapa[i1 - 1] + 1
            else:
                continue
        else:
            posicions = [mapa.get(k) for k in range(i1, i2)]
            if None in posicions or posicions != list(range(posicions[0], posicions[0] + len(posicions))):
                continue  # el canvi toca paraules que ja ha canviat un punt anterior
            inici, fi = posicions[0], posicions[-1] + 1
        canvis.append((inici, fi, n[j1:j2]))
    resultat = list(a)
    for inici, fi, paraules in sorted(canvis, reverse=True):
        resultat[inici:fi] = paraules
    return " ".join(resultat)


def tradueix_cat_val_ml(
    text: str, model=None, criteri: Criteri = Criteri(), concordanca: str = CONCORDANCA_PER_DEFECTE
) -> tuple[str, list[Punt]]:
    """Traducció cat->val amb el postprocessat del model de llengua.
    `model`: un `puntuador.ModelLlengua` (o qualsevol objecte amb
    `logprob(text) -> (float, int)`); sense model, el motor tal qual.
    `concordanca`: "motor" o "variants" (vore `punts.variants_concordanca`).

    >>> class Fals:
    ...     def logprob(self, text):
    ...         return (-1.0 if "una vegada" in text.lower() else -9.0, 5)
    >>> tradueix_cat_val_ml("Un cop acabada la reunió, marxem.", Fals(), Criteri(lam=0.0))[0]
    'Una vegada acabada la reunió, marxem.'
    >>> tradueix_cat_val_ml("Un cop acabada la reunió, marxem.")[0]
    'Un cop acabada la reunió, marxem.'

    Irresoluble decidit per spaCy sense cridar el model (abans d'arreglar-ho
    petava i `evalua_models.py` tornava la frase catalana sense traduir):

    >>> tradueix_cat_val_ml("Aquesta noia és molt gandula i no vol sortir de casa.", Fals(),
    ...                     Criteri(model_irresolubles=False))[0]
    'Esta xica és molt gandula i no vol eixir de casa.'
    """
    motor, punts = _motor()
    if model is None:
        tokens = motor.tradueix_tokens(text)
        return detokenize(tokens), detecta(tokens, punts, criteri.tipus)
    tipus_model = tuple(t for t in criteri.tipus if t != "irresoluble" or criteri.model_irresolubles)
    text_motor, trobats = puntua_punts(text, model, criteri.tipus, concordanca, tipus_model)
    return aplica_tries(text_motor, trobats, criteri), trobats


_MODEL_PER_DEFECTE = None


def translate_cat_val_ml(text: str, model_id: str | None = None, criteri: Criteri = Criteri()) -> str:
    """El sistema final, només el text: motor + model de llengua amb
    `criteri` (per defecte, el criteri per defecte). Carrega el model la
    primera vegada (FLOR-760M si no es diu cap altre). És el que avalua
    `evalua_models.py --model traductor_ml --direccio cat-val`."""
    global _MODEL_PER_DEFECTE
    if _MODEL_PER_DEFECTE is None or (model_id and _MODEL_PER_DEFECTE.model_id != model_id):
        from .puntuador import MODEL_PER_DEFECTE, ModelLlengua

        _MODEL_PER_DEFECTE = ModelLlengua(model_id or MODEL_PER_DEFECTE)
    return tradueix_cat_val_ml(text, _MODEL_PER_DEFECTE, criteri)[0]


__all__ = ["Criteri", "tradueix_cat_val_ml", "translate_cat_val_ml", "puntua_punts", "aplica_tries", "tria"]
