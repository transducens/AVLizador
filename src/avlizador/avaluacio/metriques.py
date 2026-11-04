"""Mètriques de traducció: exactes, BLEU, chrF, chrF++, TER i WER.

Les mateixes que `pipeline/03_seleccio_de_model/evalua_models.py` (que ara
les importa d'ací). Necessita `sacrebleu` (extra `[avaluacio]`).
"""

from __future__ import annotations

import sacrebleu


def normalitza_apostrofa(text: str) -> str:
    """Normalitza totes les variants d'apòstrof a l'apòstrof estàndard ASCII.

    >>> normalitza_apostrofa("d´este l’edat")
    "d'este l'edat"
    """
    return (
        text
        .replace('´', "'")   # ´ accent agut (el bug principal del benchmark)
        .replace('‘', "'")   # ' cometa tipogràfica esquerra
        .replace('’', "'")   # ' cometa tipogràfica dreta
        .replace('ʼ', "'")   # ʼ modificador carta apòstrof
        .replace('`', "'")   # ` accent greu
    )


def distancia_paraules(hipotesi: str, referencia: str) -> int:
    """Distància d'edició (Levenshtein) per paraules: substitucions,
    insercions i esborrats. És el numerador del WER. Separa per espais,
    distingix majúscules i la puntuació va enganxada a la paraula (igual
    que el TER de sacrebleu per defecte).

    >>> distancia_paraules("a b c d", "a x c d e")
    2
    >>> distancia_paraules("", "a b")
    2
    """
    hip, ref = hipotesi.split(), referencia.split()
    anterior = list(range(len(ref) + 1))
    for i, h in enumerate(hip, 1):
        actual = [i]
        for j, r in enumerate(ref, 1):
            actual.append(min(anterior[j] + 1, actual[j - 1] + 1,
                              anterior[j - 1] + (h != r)))
        anterior = actual
    return anterior[-1]


def calcula_metriques(hipotesi: str, referencia: str) -> dict:
    """Calcula BLEU, chrF, chrF++, TER i WER per a un parell hipòtesi/referència.
    Normalitza apòstrofs abans de comparar per no penalitzar diferències tipogràfiques.

    TER i WER (30/10/2026): % d'edicions sobre les paraules de la referència,
    com més baix millor. El TER compta també el desplaçament d'un bloc de
    paraules com una sola edició; el WER no (un canvi d'orde costa una edició
    per paraula). Es guarden les edicions i la llargària de la referència per
    a poder fer la mitjana de corpus (suma d'edicions / suma de paraules).

    >>> m = calcula_metriques("a b c d", "a x c d e")
    >>> m["ter"], m["wer"], m["ter_edicions"], m["wer_edicions"], m["ref_paraules"]
    (40.0, 40.0, 2, 2, 5)
    """
    hip = normalitza_apostrofa(hipotesi.strip().lower())
    ref = normalitza_apostrofa(referencia.strip().lower())
    # Usa les versions normalitzades també per BLEU/chrF
    hipotesi = normalitza_apostrofa(hipotesi.strip())
    referencia = normalitza_apostrofa(referencia.strip())

    try:
        bleu_score = sacrebleu.sentence_bleu(hipotesi, [referencia]).score
    except Exception:
        bleu_score = 0.0

    try:
        chrf_score = sacrebleu.sentence_chrf(hipotesi, [referencia]).score
    except Exception:
        chrf_score = 0.0

    try:
        chrf_pp_score = sacrebleu.sentence_chrf(hipotesi, [referencia], word_order=2).score
    except Exception:
        chrf_pp_score = 0.0

    ref_paraules = len(referencia.split())
    try:
        ter = sacrebleu.sentence_ter(hipotesi, [referencia])
        ter_score, ter_edicions = ter.score, ter.num_edits
    except Exception:
        ter_score, ter_edicions = 100.0, float(ref_paraules)

    wer_edicions = distancia_paraules(hipotesi, referencia)
    wer_score = wer_edicions / ref_paraules * 100 if ref_paraules else 0.0

    return {
        "bleu":    round(bleu_score, 2),
        "chrf":    round(chrf_score, 2),
        "chrf_pp": round(chrf_pp_score, 2),
        "ter":     round(ter_score, 2),
        "wer":     round(wer_score, 2),
        "ter_edicions": ter_edicions,
        "wer_edicions": wer_edicions,
        "ref_paraules": ref_paraules,
        "exacte":  (hip == ref),
    }


def ter_wer_corpus(resultats: list[dict], camp_edicions: str) -> float:
    """TER o WER de corpus: suma d'edicions / suma de paraules de la
    referència × 100 (`camp_edicions`: "ter_edicions" o "wer_edicions").

    >>> ter_wer_corpus([{"wer_edicions": 1, "ref_paraules": 4},
    ...                 {"wer_edicions": 0, "ref_paraules": 6}], "wer_edicions")
    10.0
    """
    paraules = sum(r["ref_paraules"] for r in resultats)
    if not paraules:
        return 0.0
    return round(sum(r[camp_edicions] for r in resultats) / paraules * 100, 2)
