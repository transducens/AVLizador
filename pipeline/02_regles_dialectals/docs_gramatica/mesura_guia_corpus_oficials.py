"""Compliment de les regles de `guia_traduccio_dialectal.md` (BLOC B, C, D)
en text valencià oficial (AVL i BOE) i conversió català->valencià al BOE
alineat. Dona PERCENTATGES: de cada vegada que apareix el context d'una
regla, quantes voltes el text oficial fa servir la forma de la norma.

Dos mesures:
  1. Compliment en valencià oficial (monolingüe): AVL sencera
     (`dades/avl/final/unified.jsonl`) i una mostra de 80.000 línies del
     BOE valencià.
  2. Conversió al BOE alineat: quan la línia catalana té el patró, què fa
     la línia valenciana (sense comptar les reformulacions).

Execució des de l'arrel del repo (els corpus de `dades/` no estan a git):

    python pipeline/02_regles_dialectals/docs_gramatica/mesura_guia_corpus_oficials.py

Resultat del 21/10/2026 a `mesura_guia_corpus_oficials_resultats_20261021.txt`;
conclusions a `documentacio/hoja_de_ruta_traductor_invers.md`."""
import json, random, re, difflib, collections, spacy

nlp = spacy.load("ca_core_news_sm", disable=["ner", "parser", "lemmatizer"])
TOK = nlp.tokenizer
VOCALS = "aeiouàèéíòóúïü"


def comenca_vocal(w):
    w = w.lower()
    return bool(w) and (w[0] in VOCALS or (w[0] == "h" and len(w) > 1 and w[1] in VOCALS))


def es_inf(t):
    return t.morph.get("VerbForm") == ["Inf"]


def es_verb(t):
    return t.pos_ in ("VERB", "AUX")


B1 = "B1 acusatiu masc. sg. davant consonant: 'lo' (norma) vs 'el'"
B1PC = "B1/B2 plural davant consonant: 'los' (norma) vs 'els'"
B1PV = "B1/B2 plural davant vocal: 'los' (norma) vs 'els'"
B3 = "B3 partitiu davant consonant: 'ne' (norma) vs 'en'"
B1E = "B1 enclític darrere consonant: '-lo/-los' (norma) vs '-el/-els'"
B3E = "B3 enclític darrere consonant: '-ne' (norma) vs '-en'"
B4 = "B4 datiu+acusatiu: 'li'l/li la...' (norma) vs 'l'hi/la hi...'"
C1 = "C1 preposició + article definit (TOTS els usos, no sols lloc): 'en' vs 'a'"
C2 = "C2 'per a' + infinitiu (norma) vs 'per' + infinitiu (sense 'per haver')"
C3 = "C3 relatiu 'on' (norma formal) vs 'a on'"
C4 = "C4 temporal a inici de clàusula: 'en + infinitiu' vs 'quan'"
D1 = "D1 adverbi 1r/2n grau: 'ací'/'ahí' (norma) vs 'aquí'"
NORMA = {B1: "lo", B1PC: "los", B1PV: "los", B3: "ne", B1E: "-lo/-los", B3E: "-ne", B4: "li'l / li la...",
         C1: "en", C2: "per a", C3: "on", C4: "en + inf", D1: "ací"}


def compliment(docs):
    R = collections.defaultdict(collections.Counter)
    for doc in docs:
        toks = list(doc)
        for k, t in enumerate(toks):
            w = t.text.lower()
            n = toks[k + 1] if k + 1 < len(toks) else None
            p = toks[k - 1] if k > 0 else None
            if n is not None and es_verb(n) and t.pos_ == "PRON":
                if w in ("el", "lo") and not comenca_vocal(n.text):
                    R[B1][w] += 1
                if w in ("els", "los"):
                    R[B1PV if comenca_vocal(n.text) else B1PC][w] += 1
                if w in ("en", "ne") and not comenca_vocal(n.text):
                    R[B3][w] += 1
            if w in ("-lo", "-los", "-el", "-els") and p is not None and p.text[-1:].lower() not in VOCALS:
                R[B1E]["-lo/-los" if w in ("-lo", "-los") else "-el/-els"] += 1
            if w in ("-ne", "-en") and p is not None and p.text[-1:].lower() not in VOCALS:
                R[B3E][w] += 1
            if w == "per" and n is not None:
                n2 = toks[k + 2] if k + 2 < len(toks) else None
                if n.text.lower() == "a" and n2 is not None and es_inf(n2) and n2.text.lower() != "haver":
                    R[C2]["per a"] += 1
                elif es_inf(n) and n.text.lower() != "haver":
                    R[C2]["per"] += 1
            if w == "on" and t.pos_ in ("PRON", "ADV"):
                R[C3]["a on" if p is not None and p.text.lower() == "a" else "on"] += 1
            if w in ("ací", "ahí", "aquí"):
                R[D1][w] += 1
            if w == "en" and t.pos_ == "ADP" and n is not None and es_inf(n) and (p is None or p.is_punct):
                R[C4]["en + inf"] += 1
            if w == "quan" and (p is None or p.is_punct):
                R[C4]["quan"] += 1
            if t.pos_ == "ADP" and w in ("en", "a") and n is not None and n.text.lower() in ("el", "la", "els", "les", "l'"):
                R[C1][w] += 1
            if w in ("al", "als"):
                R[C1]["a"] += 1
        text = doc.text.lower()
        R[B4]["li'l / li la..."] += len(re.findall(r"(?<![\w])(li'ls?|li la|li les)(?![\w])", text))
        R[B4]["l'hi / la hi..."] += len(re.findall(r"(?<![\w])(l'hi|la hi|les hi)(?![\w])", text))
    return R


def informe(nom, R):
    print(f"\n######## {nom}")
    for regla in sorted(R):
        tot = sum(R[regla].values())
        if not tot:
            print(f"  {regla}\n      -> sense casos")
            continue
        pct = 100 * R[regla][NORMA[regla]] / tot
        det = ", ".join(f"{k} {100 * v / tot:.1f}%" for k, v in R[regla].most_common())
        print(f"  {regla}\n      -> norma '{NORMA[regla]}': {pct:.1f}%   [{det}]  (n={tot})")


avl = []
for linia in open("dades/avl/final/unified.jsonl", encoding="utf-8"):
    d = json.loads(linia)
    for par in (d.get("text") or "").split("\n"):
        if par.strip():
            avl.append(par.replace("’", "'"))
informe("AVL (dades/avl/final/unified.jsonl, valencià oficial, sencer)", compliment(nlp.pipe(avl, batch_size=128)))

C = open("dades/boe/catala/corpus_entrenamiento.catala.txt", encoding="utf-8").read().replace("’", "'").split("\n")
V = open("dades/boe/valencia/corpus_entrenamiento.valencia.txt", encoding="utf-8").read().replace("’", "'").split("\n")
random.seed(7)
mostra = random.sample(range(min(len(C), len(V))), 80000)
informe("BOE valencià (mostra aleatòria de 80.000 línies)", compliment(nlp.pipe((V[i] for i in mostra), batch_size=256)))

A = collections.defaultdict(collections.Counter)
for doc, i in zip(nlp.pipe((C[i] for i in mostra), batch_size=256), mostra):
    cl = [t.text.lower() for t in doc]
    vl = [t.text.lower() for t in TOK(V[i])]
    if not cl or abs(len(cl) - len(vl)) > 0.3 * len(cl):
        continue
    al = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, cl, vl, autojunk=False).get_opcodes():
        for k in range(i1, i2):
            al[k] = (j1 + (k - i1), j1 + (k - i1) + 1) if op == "equal" else (j1, j2)
    for k, t in enumerate(doc):
        w = cl[k]
        n = doc[k + 1] if k + 1 < len(doc) else None
        a, b = al.get(k, (0, 0))
        vt = " ".join(vl[a:b + 2])
        v0 = vl[a] if a < len(vl) else ""
        if t.pos_ == "PRON" and n is not None and es_verb(n):
            if w == "el" and not comenca_vocal(n.text):
                A["B1 'el' pronom davant consonant -> 'lo'"]["lo" if v0 == "lo" else ("el" if v0 == "el" else "reformulat")] += 1
            if w == "els":
                A["B1/B2 'els' pronom -> 'los'"]["los" if v0 == "los" else ("els" if v0 == "els" else "reformulat")] += 1
            if w == "en" and not comenca_vocal(n.text):
                A["B3 'en' partitiu -> 'ne'"]["ne" if v0 == "ne" else ("en" if v0 == "en" else "reformulat")] += 1
        if w in ("-el", "-els"):
            A["B1 enclític '-el/-els' -> '-lo/-los'"]["-lo/-los" if v0 in ("-lo", "-los") else ("igual" if v0 == w else "reformulat")] += 1
        if w == "-en":
            A["B3 enclític '-en' -> '-ne'"]["-ne" if v0 == "-ne" else ("igual" if v0 == w else "reformulat")] += 1
        if w == "l'hi" or (w in ("la", "les", "els") and n is not None and n.text.lower() == "hi"):
            A["B4 'l'hi/la hi/les hi/els hi' -> 'li'l/li la...'"]["li..." if re.search(r"\bli\b|li'", vt) else "igual/reformulat"] += 1
        if (w == "a" and n is not None and n.text.lower() in ("la", "les", "l'")) or w in ("al", "als"):
            A["C1 'a/al' + article -> 'en' + article"]["en" if v0 == "en" else ("a" if v0 in ("a", "al", "als") else "reformulat")] += 1
        if w == "per" and n is not None and es_inf(n):
            clau = "C2 'per haver' (causal) -> es manté 'per'" if n.text.lower() == "haver" else "C2 'per' + infinitiu -> 'per a'"
            A[clau]["per a" if re.match(r"per a\b", vt) else ("per" if v0 == "per" else "reformulat")] += 1
        if w == "on" and (k == 0 or cl[k - 1] != "a"):
            pv = vl[a - 1] if a > 0 else ""
            A["C3 'on' -> 'a on'"]["a on" if pv == "a" and v0 == "on" else ("on" if v0 == "on" else "reformulat")] += 1
        if w == "quan":
            A["C4 'quan' -> 'en' + infinitiu"]["en + inf" if v0 == "en" else ("quan" if v0 == "quan" else "reformulat")] += 1
        if w == "aquí":
            A["D1 'aquí' -> 'ací'"][v0 if v0 in ("ací", "ahí", "aquí") else "reformulat"] += 1
print("\n######## BOE alineat català -> valencià (mateixa mostra): quan el català té el patró, què fa el valencià")
for r in sorted(A):
    tot = sum(A[r].values())
    ref = sum(v for kk, v in A[r].items() if kk != "reformulat")
    det = ", ".join(f"{kk} {100 * v / tot:.1f}%" for kk, v in A[r].most_common())
    sense = ", ".join(f"{kk} {100 * v / ref:.1f}%" for kk, v in A[r].most_common() if kk != "reformulat") if ref else "-"
    print(f"  {r}\n      tot: [{det}] (n={tot})\n      sense reformulats: [{sense}] (n={ref})")
