"""
cat_val/concordanca_genere_sn.py -- Concordança de gènere dins del sintagma
nominal (SN) quan una paraula canvia de gènere en traduir-se del català al
valencià (entrades `problema: "cambio_genero"` del diccionari).

**El problema (10/11/2026)**: algunes paraules catalanes es tradueixen a una
forma valenciana d'un altre gènere gramatical (p. ex. "la galleda" [f] ->
"el poal" [m]). El diccionari substitueix la paraula nucli, però la resta
del SN queda amb el gènere original: "la galleda plena" -> "el poal plena"
(mal) en compte de "el poal ple" (bé). Esta regla detecta eixos casos i
corregix els determinants i adjectius que concorden amb el nucli.

**Estratègia**:
1. `LexicInversRule` ja ha substituït la paraula nucli i li ha posat
   `is_translated = True`. Esta regla s'aplica DESPRÉS, quan ja es pot
   reconèixer la paraula nova.
2. Es carreguen del `lexic_general.json` totes les entrades amb
   `problema: "cambio_genero"` -- les formes valencianes que han canviat
   de gènere respecte al català original.
3. El **determinant immediatament anterior** es corregix sempre amb el
   gènere del diccionari (`corregeix_determinant_abans`), sense spaCy. Si
   l'article va dins del mateix token del nucli ("L'aranja" -> "La pomelo"),
   es corregix dins del token.
4. spaCy (AMB parser, `pos_tagger.analitza(..., amb_parser=True)`) dona la resta de
   paraules que concorden amb el nucli:
   - fills del nucli `det`, `amod`, `acl` i `flat` ("la xocolata blanca",
     "la carta rebuda");
   - **atribut/predicatiu**: si el nucli és el subjecte (`nsubj`) d'un
     adjectiu o participi ("la galleda estava plena", "el llimoner és
     vell"), o d'un verb amb un complement predicatiu `xcomp` ("les
     calamarses solen ser intenses");
   - adjectius coordinats amb qualsevol dels anteriors ("dolça i cremosa");
   - verbs copulatius que spaCy no reconeix com a tals ("quedar", "semblar",
     "romandre"...): l'adjectiu ve marcat com a `obj` ("la galleda semblava
     plena", "l'estel va quedar enganxat");
   - **pronoms** que es referixen al nucli dins de la frase: l'interrogatiu
     de "siga quina siga la seua finalitat" i el relatiu "el qual" / "la
     qual" d'una oració de relatiu que penja del nucli (11/11/2026).
   Mai es tocen els complements del nom (`nmod`): en "les vivendes de la
   zona", "la zona" no concorda amb "vivendes".
5. Per a cada paraula trobada:
   - **determinant conegut**: taula tancada `_DET_M_A_F` / `_DET_F_A_M`;
   - **adjectiu o participi**: es busca en
     `catalan_sin_top_loc_prefijos_participios.txt` el mateix lema i nombre
     amb el gènere nou. Només lectures `adj` i `vblex` (participi), mai
     `n`: la regla no canvia noms.

**Fitxer .txt** (`catalan_sin_top_loc_prefijos_participios.txt`):
  Una línia per forma, format `forma_sup:lema<cat><gen><num>` (pot portar un
  comentari `# ...` al final). Les etiquetes de gènere són `<m>`, `<f>`,
  `<mf>` (invariable) i `<sp>` (singular i plural alhora). Les `<mf>` i
  `<sp>` s'ignoren per a esta regla (no canvien de gènere/nombre). Les
  formes de diverses paraules són locucions ("ple de gom a gom") i
  s'ignoren.

**Posició en el pipeline**: immediatament DARRERE de `LexicInversRule` (i
darrere de `CliticLhiRule`), perquè necessita que el nucli del SN ja estiga
traduït i marcat.

**Adjectiu enganxat al nucli (11/11/2026)**: quan spaCy analitza malament
l'adjectiu que ve just darrere del nom ("tendra" com a nom propi, "ben
freda" amb "freda" penjant de "ben"), es corregix igualment si (1) és la
paraula següent, o la següent a un adverbi de grau ("molt", "ben",
"força"...), (2) spaCy no la fa nom, verb ni determinant, i (3) el fitxer
morfològic li dona una lectura d'adjectiu o participi del gènere ORIGINAL
del nucli (és a dir, concordava amb ell abans de la traducció).

**Fora del motor**: `model_llengua/punts.py` també crida
`concorda_dependents` quan posa un candidat d'un homògraf ("deu" ->
"brollador"), perquè la frase que puntua FLOR ja porte els adjectius de
darrere concordats.

**Límits coneguts**: spaCy opera sobre el TEXT ORIGINAL (català). Quan
l'anàlisi és incorrecta i l'adjectiu no és just darrere del nom, no es troba
i es queda com estava (preferix fals negatiu). Els pronoms febles
("fondre-la") i les referències a altres frases no es toquen. Si spaCy no està disponible, només es corregix el determinant
anterior. El parser és l'únic punt del motor que l'executa: la resta de
crides a spaCy el desactiven (vore `pos_tagger.analitza`).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .. import (
    _COMENCA_EN_VOCAL_O_H_MUDA_RE,
    _PREFIX_ELIDIT_RE,
    DET_FEM_A_MASC,
    DET_MASC_A_FEM,
    Token,
    corregeix_determinant_abans,
    preserva_majuscula,
    te_problema,
)
from ..pos_tagger import analitza

_DATA = Path(__file__).resolve().parent.parent.parent / "data"
LEXIC_GENERAL_PATH = _DATA / "lexic_general.json"
MORFOLOGIA_PATH = _DATA / "catalan_sin_top_loc_prefijos_participios.txt"

# ---------------------------------------------------------------------------
# Taules tancades de determinants / possessius / demostratius amb
# concordança de gènere. La forma de DESTÍ és sempre la VALENCIANA: esta
# regla s'aplica abans de `DemostratiusInversRule` i `PossessiusInversRule`
# i marca el token com a traduït, així que eixes regles ja no el toquen.
# Abans "aquesta" -> "aquest" (forma catalana) es quedava així ("Amb
# aquest fi", 4 frases del benchmark manual) i "seva" no hi era ("la seva
# finalitat" -> "el seua fi"), 10/11/2026. Dos taules escrites a mà, no
# invertides: les formes catalanes i valencianes no són simètriques
# ("aquest" -> "esta", però "esta" -> "este").
# Invariables ("nostres", "altres", "cap") no hi són: no canvien.
# ---------------------------------------------------------------------------
_DET_M_A_F: dict[str, str] = {
    # Articles
    "el": "la", "els": "les", "un": "una", "uns": "unes",
    # Demostratius valencians i catalans -> valencià
    "este": "esta", "estos": "estes",
    "eixe": "eixa", "eixos": "eixes",
    "aquest": "esta", "aquests": "estes",
    "aqueix": "eixa", "aqueixos": "eixes",
    "aquell": "aquella", "aquells": "aquelles",
    # Possessius (mateixa forma masculina als dos dialectes)
    "meu": "meua", "meus": "meues",
    "teu": "teua", "teus": "teues",
    "seu": "seua", "seus": "seues",
    "nostre": "nostra", "vostre": "vostra",
    # Quantificadors
    "tot": "tota", "tots": "totes",
    "molt": "molta", "molts": "moltes",
    "poc": "poca", "pocs": "poques",
    "cert": "certa", "certs": "certes",
    "altre": "altra",
    "mateix": "mateixa", "mateixos": "mateixes",
    # Interrogatiu / exclamatiu ("siga quin siga el seu fi", "quina despesa!")
    "quin": "quina", "quins": "quines",
}
_DET_F_A_M: dict[str, str] = {
    # Articles
    "la": "el", "les": "els", "una": "un", "unes": "uns",
    # Demostratius valencians i catalans -> valencià
    "esta": "este", "estes": "estos",
    "eixa": "eixe", "eixes": "eixos",
    "aquesta": "este", "aquestes": "estos",
    "aqueixa": "eixe", "aqueixes": "eixos",
    "aquella": "aquell", "aquelles": "aquells",
    # Possessius valencians i catalans -> valencià
    "meua": "meu", "meues": "meus", "meva": "meu", "meves": "meus",
    "teua": "teu", "teues": "teus", "teva": "teu", "teves": "teus",
    "seua": "seu", "seues": "seus", "seva": "seu", "seves": "seus",
    "nostra": "nostre", "vostra": "vostre",
    # Quantificadors
    "tota": "tot", "totes": "tots",
    "molta": "molt", "moltes": "molts",
    "poca": "poc", "poques": "pocs",
    "certa": "cert", "certes": "certs",
    "altra": "altre",
    "mateixa": "mateix", "mateixes": "mateixos",
    "quina": "quin", "quines": "quins",
}

# Dependències d'un participi que vol dir que té el seu propi complement:
# "inclosa l'amortització" concorda amb "amortització", no amb el nom del
# qual spaCy el fa penjar per error (BM-BOE-226, 10/11/2026).
_DEPS_COMPLEMENT_PROPI = frozenset({"obj", "iobj", "nsubj", "nsubj:pass", "ccomp"})

# Articles que `LexicInversRule` deixa DINS del token del nucli quan desfà
# un prefix elidit ("L'espatlla" -> "El muscle", "L'aranja" -> "La pomelo").
_ARTICLES_INTERNS = {"el", "la", "els", "les"}

# Categories del fitxer morfològic que esta regla pot canviar, per orde de
# preferència quan una forma té diverses lectures ("blanca": adj de
# "blanc" i nom "blanca"). Els noms (`n`) no es canvien mai.
_CATEGORIES_CONCORDANTS = ("adj", "vblex")

# Verbs que fan de còpula però spaCy analitza com a verbs plens, amb
# l'adjectiu de complement directe (`obj`): "la galleda semblava plena",
# "l'estel va quedar enganxat" (benchmark_genero #109, 11/11/2026).
_VERBS_COPULATIUS = frozenset({
    "quedar", "semblar", "parèixer", "restar", "romandre", "esdevenir",
    "resultar", "tornar", "continuar", "seguir", "mantenir", "estar", "ser", "ésser",
})

# Adverbis de grau que poden anar entre el nom i l'adjectiu ("una síndria
# ben freda"): l'heurística de l'adjectiu enganxat els salta.
_ADVERBIS_GRAU = frozenset({
    "molt", "ben", "força", "prou", "bastant", "massa", "tan", "més", "menys", "poc", "gens",
})

# "cada + nom + més/menys + adjectiu" ("cada cop més interconnectat", "cada
# dia més car"): construcció fixa en què l'adjectiu no concorda amb el nom
# (BM-AVL-005, 11/11/2026).
_COMPARATIUS = frozenset({"més", "menys"})

# Formes del relatiu que porta article ("el qual", "de la qual", "les quals").
_RELATIU_AMB_ARTICLE = frozenset({"qual", "quals"})


# ---------------------------------------------------------------------------
# Càrrega del fitxer morfològic
# ---------------------------------------------------------------------------

# Línia del fitxer: "forma:lema<cat>(<gen>)?(<num>)?(<extra>)*(# comentari)?"
_LINIA_RE = re.compile(
    r"^(?P<forma>[^:]+):(?P<lema>[^<]+)"
    r"(?P<tags>(?:<[^>]+>)+)"
    r"(?:\s*#.*)?$"
)
_TAG_RE = re.compile(r"<([^>]+)>")


def _parseja_linia(linia: str) -> tuple[str, str, str, str, str] | None:
    """Torna `(forma, lema, categoria, genere, nombre)` o `None`."""
    m = _LINIA_RE.match(linia.strip())
    if m is None:
        return None
    forma = m.group("forma").strip()
    lema = m.group("lema").strip()
    tags = _TAG_RE.findall(m.group("tags"))
    if not tags:
        return None
    cat = tags[0]  # primer tag: categoria (n, adj, v...)
    genere = ""
    nombre = ""
    for t in tags[1:]:
        if t in ("m", "f", "mf"):
            genere = t
        elif t in ("sg", "pl", "sp"):
            nombre = t
        # acr, num, etc. s'ignoren
    return forma, lema, cat, genere, nombre


@lru_cache(maxsize=None)
def carrega_morfologia(
    path: Path = MORFOLOGIA_PATH,
) -> dict[tuple[str, str, str, str], str]:
    """Índex morfològic del fitxer .txt: `{(lema, cat, genere, nombre): forma}`.

    Només entrades amb gènere `m` o `f` i nombre `sg` o `pl` (les `mf`/`sp`
    no canvien de gènere/nombre, per tant no cal invertir-les). Les formes
    de diverses paraules són locucions i s'ignoren: abans "ple de gom a gom"
    apareixia abans que "ple" i es quedava com a masculí de "ple" (10/11/2026,
    7.113 claus afectades).

    El resultat es guarda (`lru_cache`) i el compartixen totes les
    instàncies de la regla (el motor i `model_llengua/punts.py`): no s'ha de
    modificar.

    >>> idx = carrega_morfologia()
    >>> idx[("gonoccòcic", "adj", "f", "pl")]
    'gonoccòciques'
    >>> idx[("gonoccòcic", "adj", "m", "sg")]
    'gonoccòcic'
    >>> idx[("ple", "adj", "m", "sg")], idx[("ple", "adj", "f", "sg")]
    ('ple', 'plena')
    """
    idx: dict[tuple[str, str, str, str], str] = {}
    with open(path, encoding="utf-8") as fh:
        for linia in fh:
            parsed = _parseja_linia(linia)
            if parsed is None:
                continue
            forma, lema, cat, genere, nombre = parsed
            if genere not in ("m", "f") or nombre not in ("sg", "pl"):
                continue
            if " " in forma:
                continue  # locució ("ple de gom a gom")
            clau = (lema.lower(), cat, genere, nombre)
            if clau not in idx:  # primera aparició guanya
                idx[clau] = forma
    return idx


@lru_cache(maxsize=None)
def _index_invers(path: Path = MORFOLOGIA_PATH) -> dict[str, list[tuple[str, str, str, str]]]:
    """`{forma en minúscules: TOTES les seues claus (lema, cat, genere,
    nombre)}`. Abans es guardava només l'última i "blanca" quedava com a nom
    ("blanca") en compte d'adjectiu ("blanc"). Compartit com
    `carrega_morfologia`."""
    invers: dict[str, list[tuple[str, str, str, str]]] = {}
    for clau, forma in carrega_morfologia(path).items():
        invers.setdefault(forma.lower(), []).append(clau)
    return invers


# ---------------------------------------------------------------------------
# Càrrega de les formes valencianes amb cambio_genero
# ---------------------------------------------------------------------------

def carrega_formes_cambio_genero(
    path: Path = LEXIC_GENERAL_PATH,
) -> dict[str, str]:
    """Formes valencianes que han canviat de gènere respecte al català.

    Torna `{primera_paraula_valenciana_minuscules: genere_valencia}` on
    `genere_valencia` és "m" o "f" (el gènere NOU, és a dir, el del
    valencià).

    S'usa la PRIMERA PARAULA de la forma valenciana com a clau, perquè
    `LexicInversRule` assigna tota la traducció (fins i tot la multi-paraula)
    al primer token i buida els altres.

    Entrades on `genero_val` és una llista amb més d'un gènere distint (casos
    ambigus com "petó"->"bes" [f,m] o "nou"->"anou" [f,m]) s'ometen: no hi
    ha un gènere nou clar i no cal fer cap correcció.
    """
    dades = json.loads(Path(path).read_text(encoding="utf-8"))
    resultat: dict[str, str] = {}
    for entrada in dades:
        if not te_problema(entrada, "cambio_genero"):
            continue
        val = (entrada.get("valenciano") or "").strip().lower()
        if not val:
            continue
        # Normalitzem genero_val (pot ser str o list)
        genere_val_raw = entrada.get("genero_val") or ""
        if isinstance(genere_val_raw, list):
            generes = {v.strip().lower() for v in genere_val_raw if v}
            # Si hi ha més d'un gènere distint (ambigu), l'entrada s'omet
            generes_nets = generes & {"m", "f"}
            if len(generes_nets) != 1:
                continue
            genere_val = next(iter(generes_nets))
        else:
            genere_val = genere_val_raw.strip().lower()

        if genere_val not in ("m", "f"):
            continue

        # Clau = primera paraula de la forma valenciana (pot ser multi-paraula)
        primera = val.split()[0]
        # En cas de col·lisió (p.ex. "tomaca" apareix com a singular i com a
        # part de "tomaca d'arbre"), la primera entrada guanya -- en el lookup
        # posterior spaCy ens dirà si el nucli del SN coincidix.
        if primera not in resultat:
            resultat[primera] = genere_val
    return resultat


def paraula_nucli(traduccio: str) -> tuple[str, str]:
    """`(article intern, paraula nucli)` de la traducció d'un token.
    `LexicInversRule` deixa l'article dins del token quan desfà un prefix
    elidit ("L'espatlla" -> "El muscle") i el manté apostrofat si la paraula
    nova comença en vocal ("L'abraçada" -> "L'abraç"). La clau de
    `cambio_genero` és la paraula, sense l'article.

    >>> paraula_nucli("El muscle"), paraula_nucli("L'abraç")
    (('El', 'muscle'), ("L'", 'abraç'))
    >>> paraula_nucli("tomaca cherry"), paraula_nucli("meló d'Alger")
    (('', 'tomaca'), ('', 'meló'))
    """
    paraules = traduccio.split()
    if not paraules:
        return "", ""
    if len(paraules) > 1 and paraules[0].lower() in _ARTICLES_INTERNS:
        return paraules[0], paraules[1]
    m = _PREFIX_ELIDIT_RE.match(paraules[0])
    if m and m.group(1).lower() == "l":
        return paraules[0][: len(paraules[0]) - len(m.group(2))], m.group(2)
    return "", paraules[0]


# ---------------------------------------------------------------------------
# Regla principal
# ---------------------------------------------------------------------------

# Fills del nucli que concorden amb ell. `acl` cobrix participis ("la carta
# rebuda") i `flat` adjectius que spaCy pren per part d'un nom propi ("La
# joguina preferida"). Sense `nmod`/`appos`/`compound`/`nummod`: són altres
# noms (o numerals, que fa `ConcordancaDosDuesInversRule`) amb el seu propi
# gènere, i els seus determinants no s'han de tocar.
_DEPS_NUCLI = frozenset({"det", "amod", "acl", "flat"})
_DEPS_SUBJECTE = frozenset({"nsubj", "nsubj:pass"})


def _es_adjectival(dt) -> bool:
    """Adjectiu o participi segons spaCy."""
    return dt.pos_ == "ADJ" or "Part" in dt.morph.get("VerbForm")


def _te_complement_propi(dt, nucli=None) -> bool:
    """Participi amb complement propi SENSE preposició ("inclosa
    l'amortització"): concorda amb el complement, no amb el nom del qual
    spaCy el fa penjar. Amb preposició sí que concorda amb el nom ("les
    despeses associades a les inversions", BM-BOE-135). No compten el
    nucli mateix ("La mongeta tendra": spaCy fa "mongeta" subjecte de
    "tendra") ni un relatiu, que es referix al nucli ("la despesa, la qual
    és alta")."""
    # Per índex: spaCy crea un objecte Token nou a cada accés (`is` no val).
    return any(g.dep_ in _DEPS_COMPLEMENT_PROPI and (nucli is None or g.i != nucli.i)
               and "Rel" not in g.morph.get("PronType")
               and not any(gg.dep_ == "case" for gg in g.children)
               for g in dt.children)


def _temps_compost(dt) -> bool:
    """Participi d'un temps compost ("hem parlat"): és verb, no concorda
    amb el subjecte (benchmark_genero #95, 11/11/2026). La passiva ("va ser
    aprovada") sí que concorda: el seu auxiliar és "ser", no "haver". I
    també l'obligació "haver de" + ser/estar ("ha de ser precisa", "han
    d'estar ben citades", #46 i #42): spaCy hi penja "haver" de l'adjectiu.

    >>> from ..pos_tagger import analitza
    >>> def cap(text, paraula):
    ...     return _temps_compost(next(d for d in analitza(text, amb_parser=True) if d.text == paraula))
    >>> cap("Molts cops hem parlat d'aquest tema.", "parlat"), cap("La dosificació ha de ser precisa.", "precisa")
    (True, False)
    """
    fills = list(dt.children)
    return ("Part" in dt.morph.get("VerbForm")
            and any(c.dep_ == "aux" and c.lemma_.lower() in ("haver", "haure") for c in fills)
            and not any(c.lemma_.lower() in ("ser", "ésser", "estar") for c in fills))


def _cada_mes(dt_nucli, dt) -> bool:
    """`dt` és l'adjectiu de "cada <nucli> més/menys <adjectiu>"."""
    return (any(c.dep_ == "det" and c.text.lower() == "cada" for c in dt_nucli.children)
            and any(c.text.lower() in _COMPARATIUS for c in dt.children))


def _text_original(tokens: list[Token]) -> str:
    """Text català original dels tokens, tal com el veu spaCy."""
    return "".join(t.surface for t in tokens).replace("ʼ", "'")


class ConcordancaGenereSnRule:
    """Corregix el gènere dels determinants i adjectius que concorden amb
    un nucli que ha canviat de gènere en la traducció català->valencià.

    >>> from .engine import RuleEngineInvers
    >>> e = RuleEngineInvers()
    >>> e.translate("El llimoner del jardí és vell.")
    'La llimera del jardí és vella.'
    >>> e.translate("La xocolata blanca és molt dolça i cremosa.")
    'El xocolate blanc és molt dolç i cremós.'
    >>> e.translate("L'espatlla dreta li feia mal.")
    'El muscle dret li feia mal.'

    Els complements del nom no es toquen:

    >>> e.translate("Els habitatges de la zona eren antics.")
    'Les vivendes de la zona eren antigues.'

    Demostratius i possessius catalans ixen ja en valencià, i els
    predeterminants també concorden; un participi amb complement propi no
    es toca encara que spaCy el penge del nom:

    >>> e.translate("Amb aquesta finalitat i la seva galleda.")
    'Amb este fi i el seu poal.'
    >>> e.translate("Cal cobrir totes les despeses, inclosa l'amortització.")
    "Cal cobrir tots els gastos, inclosa l'amortització."

    Adjectiu enganxat al nom encara que spaCy l'analitze malament, i verbs
    copulatius que spaCy pren per verbs plens (11/11/2026):

    >>> e.translate("La mongeta tendra és excel·lent.")
    'El fesol tendre és excel·lent.'
    >>> e.translate("Va recomanar una síndria ben freda.")
    "Va recomanar un meló d'Alger ben fred."
    >>> e.translate("L'estel va quedar enganxat en un arbre.")
    'La milotxa va quedar enganxada en un arbre.'

    Però no en un temps compost, en un participi absolut ni en "cada ...
    més" (`translate` amb el nom traduït a mà, com fa FLOR):

    >>> from .. import tokenize, detokenize
    >>> regla = ConcordancaGenereSnRule()
    >>> def amb(text, i, trad):
    ...     toks = tokenize(text); toks[i].translated = trad; toks[i].is_translated = True
    ...     regla.concorda_dependents(toks, i, "f")
    ...     return detokenize(toks)
    >>> amb("Molts cops hem parlat d'aquest tema.", 2, "vegades")
    "Moltes vegades hem parlat d'aquest tema."
    >>> amb("El Decret, un cop aprovat formalment, integrarà l'ordenament.", 7, "vegada")
    "El Decret, un vegada aprovat formalment, integrarà l'ordenament."
    >>> amb("Vivim en un món cada cop més interconnectat.", 10, "vegada")
    'Vivim en un món cada vegada més interconnectat.'

    Pronoms interrogatius i relatius que es referixen al nucli:

    >>> e.translate("Sigui quina sigui la seva finalitat.")
    'Siga quin siga el seu fi.'
    >>> e.translate("Cal pagar la despesa, la qual és molt alta.")
    'Cal pagar el gasto, el qual és molt alt.'

    El determinant immediatament anterior es corregix sempre, amb o sense
    spaCy. Si spaCy no està disponible, només es fa això.
    """

    def __init__(
        self,
        lexic_path: Path = LEXIC_GENERAL_PATH,
        morfologia_path: Path = MORFOLOGIA_PATH,
    ) -> None:
        self._formes_cg = carrega_formes_cambio_genero(lexic_path)
        self._morfologia = carrega_morfologia(morfologia_path)
        self._forma_a_claus = _index_invers(morfologia_path)
        # Última anàlisi amb parser: `punts.py` crida `concorda_dependents`
        # per a cada candidat de la mateixa frase.
        self._ultima_analisi: tuple[str, object] | None = None

    def genere_nou(self, paraula: str) -> str | None:
        """Gènere valencià ("m"/"f") si `paraula` (la traducció, amb article
        intern o sense) és una forma amb `cambio_genero`; si no, `None`.

        >>> r = ConcordancaGenereSnRule()
        >>> r.genere_nou("brollador"), r.genere_nou("El muscle"), r.genere_nou("casa")
        ('m', 'm', None)
        """
        return self._formes_cg.get(paraula_nucli(paraula)[1].lower())

    def _analitza(self, text: str):
        if self._ultima_analisi is None or self._ultima_analisi[0] != text:
            self._ultima_analisi = (text, analitza(text, amb_parser=True))
        return self._ultima_analisi[1]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _canvia_determinant(self, forma: str, genere_nou: str) -> str | None:
        """Torna la forma del determinant en `genere_nou`, o `None`."""
        taula = _DET_M_A_F if genere_nou == "f" else _DET_F_A_M
        return taula.get(forma.lower())

    def _canvia_per_morfologia(self, forma: str, genere_nou: str) -> str | None:
        """Forma de `genere_nou` amb el mateix lema i nombre. Prova les
        lectures `adj` i després `vblex` (participi); mai `n`.

        >>> r = ConcordancaGenereSnRule()
        >>> r._canvia_per_morfologia("blanca", "m"), r._canvia_per_morfologia("citats", "f")
        ('blanc', 'citades')
        >>> r._canvia_per_morfologia("plena", "m"), r._canvia_per_morfologia("taula", "m")
        ('ple', None)
        """
        claus = self._forma_a_claus.get(forma.lower(), [])
        for cat_preferida in _CATEGORIES_CONCORDANTS:
            for lema, cat, genere_orig, nombre in claus:
                if cat != cat_preferida or genere_orig == genere_nou:
                    continue
                nova = self._morfologia.get((lema, cat, genere_nou, nombre))
                if nova is not None:
                    return nova
        return None

    def _te_lectura_concordant(self, forma: str, genere: str) -> bool:
        """Si `forma` té una lectura d'adjectiu o participi de `genere`."""
        return any(cat in _CATEGORIES_CONCORDANTS and g == genere
                   for _, cat, g, _ in self._forma_a_claus.get(forma.lower(), []))

    @staticmethod
    def _corregeix_article_intern(tok: Token, article: str, genere_nou: str) -> None:
        """Article dins del token del nucli ("La pomelo" -> "El pomelo";
        "La abraç" no es dona perquè davant de vocal ja ve apostrofat)."""
        if article.lower() not in _ARTICLES_INTERNS:
            return
        taula = _DET_M_A_F if genere_nou == "f" else _DET_F_A_M
        nou = taula.get(article.lower())
        if nou is None:
            return
        resta = tok.translated[len(article):].lstrip()
        if nou in ("el", "la") and _COMENCA_EN_VOCAL_O_H_MUDA_RE.match(resta):
            tok.translated = preserva_majuscula(article, "l'") + resta
        else:
            tok.translated = preserva_majuscula(article, nou) + " " + resta

    def _corregeix_determinant_anterior(self, tokens: list[Token], i: int, genere_nou: str) -> None:
        """Determinant immediatament anterior al nucli. Els demostratius i
        possessius que només té la taula d'esta regla ("aquesta", "seva")
        van per ella, perquè ixen ja en valencià ("aquesta" -> "este");
        la resta (articles, contraccions "del"/"de la") per
        `corregeix_determinant_abans`."""
        j = i - 1
        while j >= 0 and tokens[j].surface.isspace():
            j -= 1
        if j >= 0 and not tokens[j].is_translated:
            anterior = tokens[j]
            forma = anterior.translated.lower()
            compartides = DET_FEM_A_MASC if genere_nou == "m" else DET_MASC_A_FEM
            nova = self._canvia_determinant(forma, genere_nou)
            if nova is not None and forma not in compartides:
                anterior.translated = preserva_majuscula(anterior.translated, nova)
                anterior.is_translated = True
                return
        corregeix_determinant_abans(tokens, i, genere_nou)

    def _membres(self, dt_nucli) -> list:
        """Tokens d'spaCy que concorden amb `dt_nucli` (sense ell)."""
        membres = [
            c for c in dt_nucli.children
            if c.dep_ in _DEPS_NUCLI
            # Participi amb complement propi: spaCy el penja mal del nom
            # ("totes les despeses, inclosa l'amortització"). Només compta
            # un complement SENSE preposició: spaCy també marca `obj` en
            # "les despeses associades a les inversions" (BM-BOE-135), i
            # ahí "associades" sí que concorda amb "despeses".
            and not (c.dep_ != "det" and _te_complement_propi(c, dt_nucli))
            and not _cada_mes(dt_nucli, c)
        ]
        # Predeterminants: "totes" penja de "les", no del nom ("totes les
        # despeses" -> "tots els gastos").
        for d in [m for m in membres if m.dep_ == "det"]:
            membres.extend(g for g in d.children if g.dep_ == "det" and g not in membres)
        # Atribut / predicatiu: el nucli és el subjecte d'un adjectiu o
        # participi ("la galleda estava plena"), o d'un verb amb `xcomp`
        # adjectival ("solen ser intenses"). Si el subjecte és coordinat
        # ("la casa i el jardí són bonics"), no es toca: concorda amb tots.
        coordinat = any(c.dep_ == "conj" for c in dt_nucli.children)
        if dt_nucli.dep_ in _DEPS_SUBJECTE and not coordinat:
            cap = dt_nucli.head
            if _es_adjectival(cap) and not _temps_compost(cap):
                membres.append(cap)
            membres.extend(c for c in cap.children if c.dep_ == "xcomp" and _es_adjectival(c))
            # Verb copulatiu que spaCy pren per verb ple: l'adjectiu és el
            # seu `obj` ("semblava plena", "va quedar enganxat"). Només si
            # no porta determinant (no és un SN: "va quedar el primer").
            if cap.lemma_.lower() in _VERBS_COPULATIUS:
                membres.extend(
                    c for c in cap.children
                    if c.dep_ == "obj" and _es_adjectival(c) and c not in membres
                    and not any(g.dep_ == "det" for g in c.children))
            # Interrogatiu del mateix verb: "siga quina siga la seua
            # finalitat" ("quina" és `obj` de "siga" i el nucli, el subjecte;
            # en frases curtes spaCy fa "quina" el cap mateix).
            membres.extend(
                c for c in [cap, *cap.children]
                if c not in membres and c.pos_ == "PRON" and "Int" in c.morph.get("PronType")
                and c.text.lower() in _DET_M_A_F.keys() | _DET_F_A_M.keys())
        # Adjectius coordinats amb els anteriors ("dolça i cremosa")
        for m in list(membres):
            if m.dep_ == "det":
                continue
            for c in m.children:
                if c.dep_ == "conj" and c not in membres:
                    membres.append(c)
        return [m for m in membres if m.i != dt_nucli.i]

    @staticmethod
    def _relatius(dt_nucli) -> list:
        """Relatius "qual(s)" de les oracions de relatiu que pengen del
        nucli ("la despesa, la qual és alta"; "la finalitat de la qual").
        L'article que porten el corregix `corregeix_determinant_abans`, que
        també fa les contraccions ("de la qual" -> "del qual")."""
        return [
            d for c in dt_nucli.children if c.dep_.startswith("acl")
            for d in c.subtree
            if d.text.lower() in _RELATIU_AMB_ARTICLE and "Rel" in d.morph.get("PronType")
        ]

    # ------------------------------------------------------------------
    # Dependents del nucli
    # ------------------------------------------------------------------

    def _canvia_token(self, tok: Token, dt, genere_nou: str) -> None:
        """Canvia `tok` (no traduït encara) al gènere nou: taula de
        determinants per a determinants i pronoms, fitxer morfològic per a
        adjectius i participis."""
        forma = tok.translated  # pot ser distinta de surface
        if dt is not None and (dt.dep_ == "det" or dt.pos_ == "PRON"):
            nova = self._canvia_determinant(forma, genere_nou)
        else:
            nova = self._canvia_per_morfologia(forma, genere_nou)
        if nova is not None:
            tok.translated = preserva_majuscula(forma, nova)
            tok.is_translated = True

    def _adjectiu_enganxat(self, tokens: list[Token], i: int, genere_nou: str, doc, dt_nucli) -> int | None:
        """Índex de l'adjectiu just darrere del nucli `tokens[i]` (saltant un
        adverbi de grau), si concordava amb ell. Per als casos en què spaCy
        l'analitza malament ("tendra" PROPN, "ben freda" amb "freda" penjant
        de "ben"); vore el docstring del mòdul."""
        def seguent(k):
            k += 1
            while k < len(tokens) and tokens[k].surface.isspace():
                k += 1
            return k if k < len(tokens) else None

        j = seguent(i)
        if j is not None and tokens[j].surface.lower() in _ADVERBIS_GRAU:
            if tokens[j].surface.lower() in _COMPARATIUS and any(
                    c.dep_ == "det" and c.text.lower() == "cada" for c in dt_nucli.children):
                return None  # "cada cop més interconnectat"
            j = seguent(j)
        if j is None or tokens[j].is_translated or not tokens[j].surface.isalpha():
            return None
        dt = next((d for d in doc if d.idx == tokens[j].start), None)
        if dt is None or dt.pos_ in ("NOUN", "VERB", "AUX", "DET", "PRON", "ADP", "NUM") and not _es_adjectival(dt):
            return None
        if _te_complement_propi(dt, dt_nucli):
            return None  # "un cop acabat el partit": concorda amb "partit"
        # Només adjectius: un participi darrere del nom sovint és una
        # construcció absoluta ("El Decret, un cop aprovat, ...", BM-AVL-074),
        # i si spaCy el fa penjar d'un ALTRE nom, és d'eixe nom.
        if "Part" in dt.morph.get("VerbForm"):
            return None
        if dt.head.i != dt_nucli.i and dt.head.pos_ in ("NOUN", "PROPN") and dt.dep_ in ("amod", "acl"):
            return None
        genere_original = "m" if genere_nou == "f" else "f"
        if not self._te_lectura_concordant(tokens[j].translated, genere_original):
            return None
        return j

    def concorda_dependents(self, tokens: list[Token], i: int, genere_nou: str, doc=None) -> None:
        """Posa en `genere_nou` les paraules que concorden amb el nucli
        `tokens[i]` (que ja porta la traducció): adjectius, determinants
        que spaCy penja del nom, predicatius, interrogatius i relatius. El
        determinant immediatament anterior NO (el fa `apply`, o qui crida).
        Sense spaCy no fa res. `doc`: l'anàlisi amb parser del text
        original, si ja la té qui crida."""
        if doc is None:
            doc = self._analitza(_text_original(tokens))
            if doc is None:
                return
        tok = tokens[i]
        # Nucli a spaCy: el NOM dins del rang del token ("L'espatlla" són
        # dos tokens d'spaCy, "L'" i "espatlla").
        dins = [d for d in doc if tok.start <= d.idx < tok.start + len(tok.surface)]
        dt_nucli = next((d for d in dins if d.pos_ in ("NOUN", "PROPN")), dins[-1] if dins else None)
        if dt_nucli is None:
            return
        pos_a_idx = {t.start: k for k, t in enumerate(tokens)}
        for dt in self._membres(dt_nucli):
            j = pos_a_idx.get(dt.idx)
            if j is None or j == i or tokens[j].is_translated:
                continue  # nucli, token no trobat o ja tocat per una altra regla
            self._canvia_token(tokens[j], dt, genere_nou)
        j = self._adjectiu_enganxat(tokens, i, genere_nou, doc, dt_nucli)
        if j is not None:
            self._canvia_token(tokens[j], None, genere_nou)
        for dt in self._relatius(dt_nucli):
            j = pos_a_idx.get(dt.idx)
            if j is not None:
                corregeix_determinant_abans(tokens, j, genere_nou)

    # ------------------------------------------------------------------
    # Mètode principal
    # ------------------------------------------------------------------

    def apply(self, tokens: list[Token]) -> list[Token]:
        # Text original (surface) per a spaCy, AMB parser: abans la regla
        # usava el model de `pos_tagger` sense parser i `.children` sempre
        # era buit, no trobava cap adjectiu (10/11/2026).
        doc = self._analitza(_text_original(tokens))

        for i, tok in enumerate(tokens):
            if not tok.is_translated or not tok.translated:
                continue
            # Clau: la paraula nucli de la traducció, sense l'article que
            # pot portar dins ("El muscle" -> "muscle") i, si és
            # multi-paraula, la primera ("tomaca cherry" -> "tomaca").
            article, nucli = paraula_nucli(tok.translated)
            genere_nou = self._formes_cg.get(nucli.lower())
            if genere_nou is None:
                continue

            # Determinant (10/11/2026): es corregix SEMPRE amb el gènere del
            # diccionari, sense dependre del parse d'spaCy. Si va dins del
            # token ("La pomelo"), es corregix ací; si no, el token anterior
            # ("Els revoltims" -> "Les reboliques"; també contraccions,
            # "dels" -> "de les"). Les dos funcions són idempotents.
            if article:
                self._corregeix_article_intern(tok, article, genere_nou)
            else:
                self._corregeix_determinant_anterior(tokens, i, genere_nou)

            self.concorda_dependents(tokens, i, genere_nou, doc)
        return tokens
