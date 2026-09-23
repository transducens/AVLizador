#!/usr/bin/env python3
"""Estudi dialectal (occidental vs oriental) del corpus unificat AVL.

Execucio:
    python estudi_dialectal.py --task 1|2|3|4|5|6|all
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BASE_DIR / "corpus"
FINAL_DIR = CORPUS_DIR / "final"
UNIFIED_PATH = FINAL_DIR / "unified.jsonl"

DIALECT_DIR = FINAL_DIR / "dialectal"
LOG_PATH = DIALECT_DIR / "estudi.log"

CLASSIFICACIO_PATH = DIALECT_DIR / "classificacio_documents.jsonl"
CONTAMINACIO_PATH = DIALECT_DIR / "contaminacio_oriental.json"
COLOCACIONS_PATH = DIALECT_DIR / "colocacions.json"
CORPUS_NET_PATH = DIALECT_DIR / "corpus_occidental_net.jsonl"
CORPUS_NET_STATS_PATH = DIALECT_DIR / "corpus_occidental_net_stats.json"
INFORME_HTML_PATH = DIALECT_DIR / "informe_dialectal.html"
NOUS_MARCADORS_PATH = DIALECT_DIR / "nous_marcadors_candidats.csv"

logger = logging.getLogger("estudi_dialectal")

# --------------------------------------------------------------------------
# Marcadors dialectals
# --------------------------------------------------------------------------


# Nota: "va, fa, fer, té, pot, dir, diu, vol, ve, deu" (occidental) i
# "on, té, fa, fer, dir, diu, pot, vol, ve, deu" (oriental) s'han exclos
# perque son formes/paraules compartides per ambdues variants i no
# constitueixen marcadors dialectals genuins.
# "veu, anar, saber" (occidental) tambe s'han exclos pel mateix motiu.

OCCIDENTAL_MARKERS = [
    "este", "esta", "estos", "estes", "faena", "faenes", "xiquet", "xiqueta",
    "xiquets", "xiquetes", "hui", "traure", "trague", "traguen", "calfar",
    "espentar", "llavar", "dacsa", "bresquilla", "creïlla", "cacau", "parlar",
    "parlant", "parla", "parlen", "servix", "servixen", "eixir", "ix", "ixen",
    "vore", "vegen", "tindre", "tinga", "tinguen", "vindre",
    "vinga", "vinguen", "faga", "faguen", "diga",
    "diguen", "vaja", "vagen", "sap", "sàpia", "poder",
    "puga", "puguen", "deure", "dega", "deguen", "voler",
    "vullga", "vullguen", "a on", "hui dia", "de vesprada", "de matí",
]

ORIENTAL_MARKERS = [
    "aquest", "aquesta", "aquests", "aquestes", "feina", "feines", "nen",
    "nena", "nens", "nenes", "avui", "treure", "tregui", "treguin", "escalfar",
    "empènyer", "rentar", "blat de moro", "préssec", "patata", "cacauet",
    "xerrar", "noi", "noia", "nois", "noies", "rebre", "sortir", "surt",
    "surten", "veure", "vegi", "vegin", "tenir", "tingui", "tinguin",
    "venir", "vine", "vingui", "vinguin", "faci", "facin",
    "digui", "diguin", "anar", "va", "vagi", "vagin", "saber", "sap",
    "sàpiga", "poder", "pugui", "puguin", "deure", "degui",
    "deguin", "voler", "vulgui", "vulguin", "avui dia",
    "a la tarda", "al matí",
]

STOPWORDS = {
    "el", "la", "els", "les", "un", "una", "de", "del", "en", "i", "a",
    "que", "es", "per", "amb", "no", "al", "mes", "tambe", "pero", "com",
    "si", "tot", "ja", "molt", "seva", "seu", "dels", "han", "ser", "va",
    "era", "ha", "més", "també", "però",
}

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

CLASSIFICATION_ORDER = [
    "occidental_clar", "occidental_predominant", "occidental_assumit", "mixt",
    "oriental_predominant", "oriental_clar", "no_determinat",
]

# fonts institucionals AVL: sense marcadors detectats, s'assumeix valencia
# occidental llevat de les fitxes de tipus "pagina" (massa curtes/generiques)
ASSUMIT_SOURCES = {"AVL", "AVL-GNV", "AVL-GVB"}

# classificacions amb ratio_occ no informatiu (sense cap marcador detectat):
# s'exclouen dels calculs de ratio_occ mitja i dels rankings per ratio
NON_RATIO_CLASSES = {"no_determinat", "occidental_assumit"}

CLASSIFICATION_COLORS = {
    "occidental_clar": "#1b5e20",
    "occidental_predominant": "#4caf50",
    "occidental_assumit": "#8bc34a",
    "mixt": "#f0ad4e",
    "oriental_predominant": "#e08a3c",
    "oriental_clar": "#c0392b",
    "no_determinat": "#95a5a6",
}


def _build_marker_index(markers: list[str]) -> dict[str, list[tuple[str, ...]]]:
    idx: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for marker in markers:
        parts = tuple(marker.split(" "))
        idx[parts[0]].append(parts)
    return idx


OCC_INDEX = _build_marker_index(OCCIDENTAL_MARKERS)
OR_INDEX = _build_marker_index(ORIENTAL_MARKERS)

# index combinat: primera_paraula -> [(marker_str, parts, dialecte), ...]
COMBINED_INDEX: dict[str, list[tuple[str, tuple[str, ...], str]]] = defaultdict(list)
for _marker in OCCIDENTAL_MARKERS:
    _parts = tuple(_marker.split(" "))
    COMBINED_INDEX[_parts[0]].append((_marker, _parts, "occ"))
for _marker in ORIENTAL_MARKERS:
    _parts = tuple(_marker.split(" "))
    COMBINED_INDEX[_parts[0]].append((_marker, _parts, "or"))


# --------------------------------------------------------------------------
# Utilitats generals
# --------------------------------------------------------------------------

def setup_logging() -> None:
    DIALECT_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Linia il·legible a %s:%d -> %s", path, lineno, exc)


def require_file(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existeix {path}. {hint}")


def write_csv(path: Path, header: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _esc(s) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def classify(total_occ: int, total_or: int, source_name: str, doc_type: str) -> tuple[float, str]:
    denom = total_occ + total_or
    if denom == 0:
        if source_name in ASSUMIT_SOURCES and doc_type != "pagina":
            return 0.0, "occidental_assumit"
        return 0.0, "no_determinat"
    ratio = total_occ / denom
    if ratio >= 0.80:
        return ratio, "occidental_clar"
    if ratio >= 0.60:
        return ratio, "occidental_predominant"
    if ratio >= 0.40:
        return ratio, "mixt"
    if ratio >= 0.20:
        return ratio, "oriental_predominant"
    return ratio, "oriental_clar"


def count_markers_combined(tokens: list[str]) -> tuple[Counter, Counter]:
    """Compta marcadors amb coincidencia de mes llarga a mes curta (greedy),
    per evitar comptar dues vegades una paraula continguda dins una frase
    mes llarga (p.ex. "on" dins de "a on")."""
    occ: Counter = Counter()
    orc: Counter = Counter()
    n = len(tokens)
    i = 0
    while i < n:
        candidates = COMBINED_INDEX.get(tokens[i])
        if not candidates:
            i += 1
            continue
        matches = []
        for marker_str, parts, dialect in candidates:
            length = len(parts)
            if tokens[i:i + length] == list(parts):
                matches.append((length, marker_str, dialect))
        if not matches:
            i += 1
            continue
        max_len = max(m[0] for m in matches)
        for length, marker_str, dialect in matches:
            if length == max_len:
                (occ if dialect == "occ" else orc)[marker_str] += 1
        i += max_len
    return occ, orc


# --------------------------------------------------------------------------
# TASCA 1 - Localitzacio de variants orientals
# --------------------------------------------------------------------------

def task1_classificacio() -> None:
    logger.info("=== TASCA 1: Localitzacio i classificacio de documents ===")
    require_file(UNIFIED_PATH, "Genera'l amb analisi_corpus.py --task 1.")

    n_docs = 0
    counter_class: Counter = Counter()

    with CLASSIFICACIO_PATH.open("w", encoding="utf-8") as out:
        for doc in read_jsonl(UNIFIED_PATH):
            tokens = tokenize(doc.get("text") or "")
            occ_counts, or_counts = count_markers_combined(tokens)
            total_occ = sum(occ_counts.values())
            total_or = sum(or_counts.values())
            tokens_approx = doc.get("tokens_approx", 0)
            source_name = doc.get("source_name") or ""
            doc_type = doc.get("doc_type") or ""
            ratio_occ, classificacio = classify(total_occ, total_or, source_name, doc_type)

            record = {
                "corpus_id": doc.get("corpus_id"),
                "title": doc.get("title"),
                "doc_type": doc.get("doc_type"),
                "source_name": doc.get("source_name"),
                "tokens_approx": doc.get("tokens_approx", 0),
                "total_occ": total_occ,
                "total_or": total_or,
                "ratio_occ": round(ratio_occ, 6),
                "classificacio": classificacio,
                "marcadors_occ_trobats": dict(occ_counts),
                "marcadors_or_trobats": dict(or_counts),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_docs += 1
            counter_class[classificacio] += 1

    logger.info("Documents processats: %d", n_docs)
    for cls in CLASSIFICATION_ORDER:
        logger.info("  %s: %d", cls, counter_class.get(cls, 0))
    logger.info("Guardat %s", CLASSIFICACIO_PATH)


# --------------------------------------------------------------------------
# TASCA 2 - Informe de contaminacio oriental
# --------------------------------------------------------------------------

def task2_contaminacio() -> None:
    logger.info("=== TASCA 2: Informe de contaminacio oriental ===")
    require_file(CLASSIFICACIO_PATH, "Executa --task 1 abans.")

    docs = list(read_jsonl(CLASSIFICACIO_PATH))
    total_docs = len(docs)
    total_tokens = sum(d["tokens_approx"] for d in docs)

    # 2a. Resum global
    dist_docs: Counter = Counter(d["classificacio"] for d in docs)
    tokens_per_class: Counter = Counter()
    for d in docs:
        tokens_per_class[d["classificacio"]] += d["tokens_approx"]

    resum_global = {
        "total_documents": total_docs,
        "total_tokens": total_tokens,
        "distribucio_classificacions": {
            cls: dist_docs.get(cls, 0) for cls in CLASSIFICATION_ORDER
        },
        "percentatge_tokens_per_classificacio": {
            cls: round(tokens_per_class.get(cls, 0) / total_tokens * 100, 4) if total_tokens else 0.0
            for cls in CLASSIFICATION_ORDER
        },
    }

    def doc_summary(d: dict, incloure_occ: bool = False) -> dict:
        top_or = sorted(d["marcadors_or_trobats"].items(), key=lambda kv: -kv[1])[:5]
        info = {
            "corpus_id": d["corpus_id"],
            "title": d["title"],
            "doc_type": d["doc_type"],
            "source_name": d["source_name"],
            "tokens_approx": d["tokens_approx"],
            "ratio_occ": d["ratio_occ"],
            "top5_marcadors_orientals": [{"paraula": w, "frequencia": f} for w, f in top_or],
        }
        if incloure_occ:
            top_occ = sorted(d["marcadors_occ_trobats"].items(), key=lambda kv: -kv[1])[:5]
            info["top5_marcadors_occidentals"] = [{"paraula": w, "frequencia": f} for w, f in top_occ]
        return info

    # 2b. Documents orientals
    docs_orientals = [
        doc_summary(d) for d in docs
        if d["classificacio"] in ("oriental_clar", "oriental_predominant")
    ]

    # 2c. Documents mixtos
    docs_mixtos = [doc_summary(d, incloure_occ=True) for d in docs if d["classificacio"] == "mixt"]

    # 2d. Analisi per source_name
    def per_group_stats(key: str) -> dict:
        groups: dict[str, list[dict]] = defaultdict(list)
        for d in docs:
            groups[d.get(key) or "desconegut"].append(d)
        result = {}
        for group_name, items in groups.items():
            dist = Counter(it["classificacio"] for it in items)
            defined_ratios = [it["ratio_occ"] for it in items if it["classificacio"] not in NON_RATIO_CLASSES]
            result[group_name] = {
                "total_documents": len(items),
                "distribucio_classificacions": {cls: dist.get(cls, 0) for cls in CLASSIFICATION_ORDER},
                "ratio_occ_mitja": round(statistics.fmean(defined_ratios), 6) if defined_ratios else None,
            }
        return result

    analisi_per_source = per_group_stats("source_name")
    analisi_per_doc_type = per_group_stats("doc_type")

    output = {
        "resum_global": resum_global,
        "documents_orientals": docs_orientals,
        "documents_mixtos": docs_mixtos,
        "analisi_per_source_name": analisi_per_source,
        "analisi_per_doc_type": analisi_per_doc_type,
    }

    with CONTAMINACIO_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(
        "Docs orientals=%d, docs mixtos=%d", len(docs_orientals), len(docs_mixtos)
    )
    logger.info("Guardat %s", CONTAMINACIO_PATH)


# --------------------------------------------------------------------------
# TASCA 3 - Col·locacions dels marcadors
# --------------------------------------------------------------------------

def task3_colocacions() -> None:
    logger.info("=== TASCA 3: Col·locacions dels marcadors ===")
    require_file(CLASSIFICACIO_PATH, "Executa --task 1 abans.")
    require_file(UNIFIED_PATH, "Genera'l amb analisi_corpus.py --task 1.")

    global_occ_freq: Counter = Counter()
    global_or_freq: Counter = Counter()
    for d in read_jsonl(CLASSIFICACIO_PATH):
        global_occ_freq.update(d["marcadors_occ_trobats"])
        global_or_freq.update(d["marcadors_or_trobats"])

    top10_occ = [m for m, _ in global_occ_freq.most_common(10)]
    top10_or = [m for m, _ in global_or_freq.most_common(10)]
    selected_markers = top10_occ + top10_or
    logger.info("Top10 occidentals: %s", top10_occ)
    logger.info("Top10 orientals: %s", top10_or)

    freq_total = {m: global_occ_freq.get(m, 0) + global_or_freq.get(m, 0) for m in selected_markers}

    selected_index: dict[str, list[tuple[str, tuple[str, ...]]]] = defaultdict(list)
    for marker in selected_markers:
        parts = tuple(marker.split(" "))
        selected_index[parts[0]].append((marker, parts))

    collocations: dict[str, Counter] = {m: Counter() for m in selected_markers}

    n_docs = 0
    for doc in read_jsonl(UNIFIED_PATH):
        tokens = tokenize(doc.get("text") or "")
        n = len(tokens)
        i = 0
        while i < n:
            candidates = selected_index.get(tokens[i])
            if not candidates:
                i += 1
                continue
            matches = []
            for marker, parts in candidates:
                length = len(parts)
                if tokens[i:i + length] == list(parts):
                    matches.append((length, marker))
            if not matches:
                i += 1
                continue
            length, marker = max(matches, key=lambda m: m[0])
            start, end = i, i + length  # [start, end) es la frase
            context = tokens[max(0, start - 3):start] + tokens[end:end + 3]
            for ctx_word in context:
                if ctx_word not in STOPWORDS and ctx_word not in parts_of(marker):
                    collocations[marker][ctx_word] += 1
            i += length
        n_docs += 1

    result = {}
    for marker in selected_markers:
        top20 = collocations[marker].most_common(20)
        result[marker] = {
            "frequencia_total": freq_total[marker],
            "colocacions": [{"paraula": w, "coocurrencies": c} for w, c in top20],
        }

    with COLOCACIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Processats %d documents. Guardat %s", n_docs, COLOCACIONS_PATH)


def parts_of(marker: str) -> set[str]:
    return set(marker.split(" "))


# --------------------------------------------------------------------------
# TASCA 4 - Corpus net occidental
# --------------------------------------------------------------------------

def task4_corpus_net() -> None:
    logger.info("=== TASCA 4: Corpus net occidental ===")
    require_file(CLASSIFICACIO_PATH, "Executa --task 1 abans.")
    require_file(UNIFIED_PATH, "Genera'l amb analisi_corpus.py --task 1.")

    keep_classes = {"occidental_clar", "occidental_predominant", "occidental_assumit"}
    info_by_id = {
        d["corpus_id"]: d for d in read_jsonl(CLASSIFICACIO_PATH) if d["classificacio"] in keep_classes
    }

    total_docs_complet = 0
    total_tokens_complet = 0
    kept_docs = 0
    kept_tokens = 0
    per_doc_type: dict[str, dict] = defaultdict(lambda: {"documents": 0, "tokens": 0})
    per_source: dict[str, dict] = defaultdict(lambda: {"documents": 0, "tokens": 0})

    with CORPUS_NET_PATH.open("w", encoding="utf-8") as out:
        for doc in read_jsonl(UNIFIED_PATH):
            total_docs_complet += 1
            total_tokens_complet += doc.get("tokens_approx", 0)

            info = info_by_id.get(doc.get("corpus_id"))
            if info is None:
                continue

            new_doc = dict(doc)
            new_doc["ratio_occ"] = info["ratio_occ"]
            new_doc["classificacio"] = info["classificacio"]
            new_doc["total_occ"] = info["total_occ"]
            new_doc["total_or"] = info["total_or"]
            out.write(json.dumps(new_doc, ensure_ascii=False) + "\n")

            kept_docs += 1
            kept_tokens += doc.get("tokens_approx", 0)
            dtype = doc.get("doc_type") or "desconegut"
            per_doc_type[dtype]["documents"] += 1
            per_doc_type[dtype]["tokens"] += doc.get("tokens_approx", 0)
            source = doc.get("source_name") or "desconegut"
            per_source[source]["documents"] += 1
            per_source[source]["tokens"] += doc.get("tokens_approx", 0)

    stats = {
        "total_documents": kept_docs,
        "total_tokens": kept_tokens,
        "per_doc_type": dict(per_doc_type),
        "per_source_name": dict(per_source),
        "comparacio_amb_corpus_complet": {
            "total_documents_complet": total_docs_complet,
            "total_tokens_complet": total_tokens_complet,
            "percentatge_documents_conservats": round(kept_docs / total_docs_complet * 100, 4) if total_docs_complet else 0.0,
            "percentatge_tokens_conservats": round(kept_tokens / total_tokens_complet * 100, 4) if total_tokens_complet else 0.0,
        },
    }
    with CORPUS_NET_STATS_PATH.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info(
        "Corpus net: %d/%d documents (%.2f%%), %d/%d tokens (%.2f%%)",
        kept_docs, total_docs_complet,
        stats["comparacio_amb_corpus_complet"]["percentatge_documents_conservats"],
        kept_tokens, total_tokens_complet,
        stats["comparacio_amb_corpus_complet"]["percentatge_tokens_conservats"],
    )
    logger.info("Guardat %s i %s", CORPUS_NET_PATH, CORPUS_NET_STATS_PATH)


# --------------------------------------------------------------------------
# TASCA 5 - Informe HTML interactiu
# --------------------------------------------------------------------------

def _svg_pie_chart(labels: list[str], values: list[float], colors: list[str], size: int = 260) -> str:
    total = sum(values)
    cx = cy = size / 2
    r = size / 2 - 10
    nonzero = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">']
    if not nonzero:
        parts.append("</svg>")
        return "\n".join(parts)
    if len(nonzero) == 1:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{nonzero[0][2]}"><title>{_esc(nonzero[0][0])}</title></circle>')
    else:
        start_angle = -90.0
        for label, value, color in nonzero:
            angle = value / total * 360.0
            end_angle = start_angle + angle
            x1 = cx + r * math.cos(math.radians(start_angle))
            y1 = cy + r * math.sin(math.radians(start_angle))
            x2 = cx + r * math.cos(math.radians(end_angle))
            y2 = cy + r * math.sin(math.radians(end_angle))
            large_arc = 1 if angle > 180 else 0
            path = f"M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z"
            parts.append(f'<path d="{path}" fill="{color}" stroke="white" stroke-width="1"><title>{_esc(label)}: {value:.0f}</title></path>')
            start_angle = end_angle
    parts.append("</svg>")
    return "\n".join(parts)


def _svg_bar_chart(labels: list[str], values: list[float], width: int = 760, bar_height: int = 26,
                    color: str = "#2b6cb0") -> str:
    if not labels:
        return "<p>Sense dades.</p>"
    max_val = max(values) if max(values) > 0 else 1
    label_col = 220
    chart_w = width - label_col - 90
    height = bar_height * len(labels) + 20
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'font-family="Segoe UI, Arial, sans-serif" font-size="12">']
    for i, (label, val) in enumerate(zip(labels, values)):
        y = i * bar_height + 10
        bar_w = (val / max_val) * chart_w
        safe_label = (label[:28] + "…") if len(label) > 29 else label
        parts.append(f'<text x="0" y="{y + bar_height * 0.65:.1f}" fill="#1a202c">{_esc(safe_label)}</text>')
        parts.append(f'<rect x="{label_col}" y="{y}" width="{bar_w:.2f}" height="{bar_height - 8}" fill="{color}" rx="3"/>')
        parts.append(f'<text x="{label_col + bar_w + 6:.1f}" y="{y + bar_height * 0.65:.1f}" fill="#1a202c">{val:.3f}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def task5_informe() -> None:
    logger.info("=== TASCA 5: Informe HTML interactiu ===")
    require_file(CLASSIFICACIO_PATH, "Executa --task 1 abans.")

    docs = list(read_jsonl(CLASSIFICACIO_PATH))

    dist_docs: Counter = Counter(d["classificacio"] for d in docs)
    pie_labels = CLASSIFICATION_ORDER
    pie_values = [dist_docs.get(c, 0) for c in pie_labels]
    pie_colors = [CLASSIFICATION_COLORS[c] for c in pie_labels]
    pie_svg = _svg_pie_chart(pie_labels, pie_values, pie_colors)

    def mean_ratio_per(key: str) -> list[tuple[str, float]]:
        groups: dict[str, list[float]] = defaultdict(list)
        for d in docs:
            if d["classificacio"] not in NON_RATIO_CLASSES:
                groups[d.get(key) or "desconegut"].append(d["ratio_occ"])
        means = [(g, statistics.fmean(v)) for g, v in groups.items() if v]
        means.sort(key=lambda kv: -kv[1])
        return means

    doc_type_means = mean_ratio_per("doc_type")
    source_means = mean_ratio_per("source_name")

    chart_doc_type = _svg_bar_chart([m[0] for m in doc_type_means], [m[1] for m in doc_type_means], color="#2b6cb0")
    chart_source = _svg_bar_chart([m[0] for m in source_means], [m[1] for m in source_means], color="#805ad5")

    global_occ_freq: Counter = Counter()
    for d in docs:
        global_occ_freq.update(d["marcadors_occ_trobats"])
    top20_occ = global_occ_freq.most_common(20)
    top20_occ_rows = "".join(
        f"<tr><td>{i + 1}</td><td>{_esc(w)}</td><td>{f}</td></tr>" for i, (w, f) in enumerate(top20_occ)
    )

    top10_oriental_docs = sorted(
        (d for d in docs if d["classificacio"] not in NON_RATIO_CLASSES),
        key=lambda d: d["ratio_occ"],
    )[:10]
    top10_rows = "".join(
        f"<tr><td>{_esc(d['corpus_id'])}</td><td>{_esc(d['title'])}</td><td>{_esc(d['doc_type'])}</td>"
        f"<td>{_esc(d['source_name'])}</td><td>{d['tokens_approx']}</td><td>{d['ratio_occ']:.4f}</td></tr>"
        for d in top10_oriental_docs
    )

    table_rows = []
    for d in docs:
        title = d["title"] or ""
        table_rows.append(
            f'<tr class="cls-{d["classificacio"]}" data-title="{_esc(title.lower())}">'
            f"<td>{_esc(title)}</td><td>{_esc(d['doc_type'])}</td><td>{_esc(d['source_name'])}</td>"
            f"<td>{d['tokens_approx']}</td><td>{d['ratio_occ']:.4f}</td>"
            f'<td><span class="badge">{_esc(d["classificacio"])}</span></td></tr>'
        )
    table_rows_html = "".join(table_rows)

    legend_items = "".join(
        f'<div class="legend-item"><span class="dot" style="background:{CLASSIFICATION_COLORS[c]}"></span>'
        f"{_esc(c)}: {dist_docs.get(c, 0)}</div>"
        for c in pie_labels
    )

    css_classes = "".join(
        f".cls-{cls} .badge {{ background:{color}; }}\n"
        for cls, color in CLASSIFICATION_COLORS.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<title>Informe dialectal del corpus AVL</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 2rem; background: #f7fafc; color: #1a202c; }}
  h1 {{ color: #2b6cb0; }}
  h2 {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3rem; margin-top: 2.5rem; }}
  .row {{ display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: flex-start; }}
  .chart-wrap {{ background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
  .legend {{ display: flex; flex-direction: column; gap: 0.4rem; padding: 1rem; }}
  .legend-item {{ font-size: 0.9rem; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
  table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th, td {{ text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid #edf2f7; font-size: 0.85rem; }}
  th {{ background: #2b6cb0; color: white; position: sticky; top: 0; }}
  .table-wrap {{ max-height: 520px; overflow-y: auto; margin-top: 0.5rem; }}
  .badge {{ color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; }}
  {css_classes}
  #searchBox {{ padding: 0.5rem; width: 320px; margin-bottom: 0.6rem; border: 1px solid #cbd5e0; border-radius: 6px; }}
  footer {{ margin-top: 3rem; font-size: 0.8rem; color: #718096; }}
</style>
</head>
<body>
<h1>Informe dialectal del corpus AVL (occidental vs oriental)</h1>

<h2>Distribucio de classificacions</h2>
<div class="row">
  <div class="chart-wrap">{pie_svg}</div>
  <div class="chart-wrap legend">{legend_items}</div>
</div>

<h2>Ratio occidental mitja per doc_type</h2>
<div class="chart-wrap">{chart_doc_type}</div>

<h2>Ratio occidental mitja per source_name</h2>
<div class="chart-wrap">{chart_source}</div>

<h2>Top 20 marcadors occidentals trobats</h2>
<div class="table-wrap">
<table>
<thead><tr><th>#</th><th>Marcador</th><th>Frequencia</th></tr></thead>
<tbody>{top20_occ_rows}</tbody>
</table>
</div>

<h2>Top 10 documents mes orientals (per investigar)</h2>
<div class="table-wrap">
<table>
<thead><tr><th>corpus_id</th><th>Titol</th><th>doc_type</th><th>Font</th><th>Tokens</th><th>ratio_occ</th></tr></thead>
<tbody>{top10_rows}</tbody>
</table>
</div>

<h2>Tots els documents</h2>
<input id="searchBox" type="text" placeholder="Cerca per titol...">
<div class="table-wrap">
<table id="docsTable">
<thead><tr><th>Titol</th><th>doc_type</th><th>Font</th><th>Tokens</th><th>ratio_occ</th><th>Classificacio</th></tr></thead>
<tbody>{table_rows_html}</tbody>
</table>
</div>

<footer>Generat automaticament per estudi_dialectal.py</footer>

<script>
document.getElementById('searchBox').addEventListener('input', function (e) {{
  var q = e.target.value.toLowerCase();
  var rows = document.querySelectorAll('#docsTable tbody tr');
  for (var i = 0; i < rows.length; i++) {{
    var title = rows[i].getAttribute('data-title') || '';
    rows[i].style.display = title.indexOf(q) !== -1 ? '' : 'none';
  }}
}});
</script>
</body>
</html>
"""
    INFORME_HTML_PATH.write_text(html, encoding="utf-8")
    logger.info("Guardat %s (%d documents a la taula)", INFORME_HTML_PATH, len(docs))


# --------------------------------------------------------------------------
# TASCA 6 - Nous marcadors candidats
# --------------------------------------------------------------------------

def task6_nous_marcadors() -> None:
    logger.info("=== TASCA 6: Descoberta de nous marcadors candidats ===")
    require_file(CORPUS_NET_PATH, "Executa --task 4 abans.")
    require_file(UNIFIED_PATH, "Genera'l amb analisi_corpus.py --task 1.")

    freq_complet: Counter = Counter()
    total_tokens_complet = 0
    for doc in read_jsonl(UNIFIED_PATH):
        tokens = tokenize(doc.get("text") or "")
        total_tokens_complet += len(tokens)
        for tok in tokens:
            if tok not in STOPWORDS:
                freq_complet[tok] += 1

    freq_occidental: Counter = Counter()
    total_tokens_occidental = 0
    for doc in read_jsonl(CORPUS_NET_PATH):
        tokens = tokenize(doc.get("text") or "")
        total_tokens_occidental += len(tokens)
        for tok in tokens:
            if tok not in STOPWORDS:
                freq_occidental[tok] += 1

    candidates = []
    for word, freq_occ in freq_occidental.items():
        if freq_occ <= 50:
            continue
        freq_tot = freq_complet.get(word, 0)
        if freq_tot == 0 or total_tokens_occidental == 0 or total_tokens_complet == 0:
            continue
        rate_occ = freq_occ / total_tokens_occidental
        rate_tot = freq_tot / total_tokens_complet
        ratio = rate_occ / rate_tot
        if ratio > 1.5:
            candidates.append((word, freq_occ, freq_tot, ratio))

    candidates.sort(key=lambda c: -c[3])
    top100 = candidates[:100]

    write_csv(
        NOUS_MARCADORS_PATH, ["paraula", "freq_occidental", "freq_total", "ratio"],
        ((w, fo, ft, round(r, 4)) for w, fo, ft, r in top100),
    )
    logger.info("Candidats trobats: %d (guardats top %d) a %s", len(candidates), len(top100), NOUS_MARCADORS_PATH)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

TASKS = {
    "1": task1_classificacio,
    "2": task2_contaminacio,
    "3": task3_colocacions,
    "4": task4_corpus_net,
    "5": task5_informe,
    "6": task6_nous_marcadors,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Estudi dialectal del corpus AVL")
    parser.add_argument(
        "--task", choices=["1", "2", "3", "4", "5", "6", "all"], default="all",
        help="Tasca a executar (per defecte: all)",
    )
    args = parser.parse_args()

    setup_logging()
    logger.info("Inici execucio --task %s", args.task)

    try:
        if args.task == "all":
            for key in ["1", "2", "3", "4", "5", "6"]:
                TASKS[key]()
        else:
            TASKS[args.task]()
    except Exception:
        logger.exception("Error durant l'execucio")
        raise

    logger.info("Execucio finalitzada correctament")


if __name__ == "__main__":
    main()
