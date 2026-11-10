"""
compara_models.py -- Compara FLOR-760M amb KenLM i fastText en la decisió
de les paraules ambigües del sistema cat->val (10/11/2026; pla en la
memòria del projecte: substituir FLOR per un model més lleuger en CPU).

El sistema ja accepta qualsevol "puntuador" amb `logprob(frase) ->
(puntuació, n)`: el motor construïx les frases valencianes completes de
cada candidat i guanya la de més puntuació (amb `Criteri`: marge i què es
queda per defecte). Ací cada model és un puntuador:

| clau            | puntuació d'una frase                                  |
|-----------------|--------------------------------------------------------|
| `flor`          | log P(frase) de FLOR-760M (el sistema actual)          |
| `kenlm_cat`     | − log P_cat (gana la MENYS probable en català; idea de l'usuari) |
| `kenlm_cat30`   | ídem amb el model del 30 % de MaCoCu (efecte de la grandària) |
| `kenlm_val`     | log P_val (KenLM valencià, totes les frases del filtre) |
| `kenlm_val_net` | log P_val (KenLM valencià net: ≥ 2 marcadors o el seu document) |
| `diff`          | log P_val − log P_cat (el que més guanya en valencià)  |
| `diff_net`      | ídem amb el valencià net                               |
| `fasttext`      | logit(val) − logit(cat) del classificador (sense la saturació de `predict`) |

Els logaritmes de KenLM (base 10) es passen a naturals, com FLOR, perquè
els marges siguen comparables. Cada model puntua UNA vegada cada frase de
cada benchmark; després es proven tots els criteris (`--marges`,
`--per-defecte catala motor`, `--lams`) sense tornar a cridar el model.

Mètriques, per benchmark:
- `sentit`: en els homògrafs (v1, 99 frases amb paraula i candidat
  esperat; v2, 160), el candidat triat és l'esperat. `sentit_model`: el
  mateix, només en col·lisions + irresolubles (on decidix el model).
- exactes, BLEU, chrF, TER i WER (`avlizador.avaluacio`).
- GD i GDV de l'eixida (global, sumant marcadors) en el manual.
- cost: segons per frase del model (descomptat el motor), memòria que
  ocupa en carregar-lo (VmRSS) i grandària del fitxer.

El "millor criteri" de cada model es tria per `sentit_model` dels
homògrafs v1 + v2 (desempat: exactes del manual). Com que els criteris
s'ajusten sobre els mateixos homògrafs, també s'informa de cada model amb
el criteri fix del sistema (marge 2, la catalana per defecte).

Ús (des de l'arrel del repositori; en Abaco, `compara_models.sh`):
    python pipeline/03_seleccio_de_model/model_llengua/compara_models.py
    python pipeline/03_seleccio_de_model/model_llengua/compara_models.py --models motor kenlm_val fasttext --limit 20
Eixida: `pipeline/03_seleccio_de_model/resultats/compara_models_<data>.{md,json}`.
"""

from __future__ import annotations

import argparse
import gc
import itertools
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ARREL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ARREL / "pipeline" / "08_traduccio_corpus" / "macocu" / "kenlm"))
from exporta_text import normalitza  # noqa: E402  (la normalització de l'entrenament de KenLM)

from avlizador.avaluacio.avalua import resumeix  # noqa: E402
from avlizador.avaluacio.metriques import calcula_metriques, normalitza_apostrofa  # noqa: E402
from avlizador.traductor_cat_val.model_llengua import Criteri, aplica_tries, puntua_punts  # noqa: E402
from avlizador.traductor_cat_val.model_llengua.punts import TIPUS  # noqa: E402

RESULTATS = ARREL / "pipeline" / "03_seleccio_de_model" / "resultats"
DIR_MODELS = ARREL / "dades" / "macocu"
BENCHMARKS = {
    "homografs": ("Homògrafs v1 + 151 (253)", "homografs/benchmark_sistema_final_cat_val.json"),
    "homografs_v2": ("Homògrafs v2 (160)", "homografs/benchmark_homografs_v2_cat_val.json"),
    "manual": ("Manual BOE + AVL (458)", "manual/benchmark_manual_cat_val.json"),
}
TIPUS_MODEL = ("colisio", "irresoluble")
LN10 = math.log(10)
MODELS = ("motor", "flor", "kenlm_cat", "kenlm_cat30", "kenlm_val", "kenlm_val_net", "diff", "diff_net", "fasttext")


# --------------------------------------------------------------------------
# Puntuadors
# --------------------------------------------------------------------------

class KenLM:
    """log P (natural) d'una frase normalitzada com el text d'entrenament.
    `signe=-1`: gana la menys probable (KenLM català)."""

    def __init__(self, model, signe: float = 1.0) -> None:
        self.model, self.signe = model, signe

    def logprob(self, text: str) -> tuple[float, int]:
        frase = normalitza(text)
        return self.signe * self.model.score(frase, bos=True, eos=True) * LN10, len(frase.split()) + 1


class Diferencia:
    """log P_val − log P_cat."""

    def __init__(self, val, cat) -> None:
        self.val, self.cat = KenLM(val), KenLM(cat)

    def logprob(self, text: str) -> tuple[float, int]:
        v, n = self.val.logprob(text)
        return v - self.cat.logprob(text)[0], n


class FastText:
    """logit(val) − logit(cat): la sortida lineal del classificador abans
    del softmax (amb `predict` les probabilitats ixen saturades a 1 i
    1e-5 i dos candidats empatarien)."""

    def __init__(self, model) -> None:
        import numpy as np

        self.np = np
        self.model = model
        etiquetes = list(model.get_labels())
        self.i_val, self.i_cat = etiquetes.index("__label__val"), etiquetes.index("__label__cat")
        # Els logits només es poden traure així amb softmax o one-vs-all
        # (l'autotune pot haver triat una altra pèrdua: llavors, probabilitats).
        self.perdua = str(model.f.getArgs().loss).lower()
        self.logits = "softmax" in self.perdua or "ova" in self.perdua
        if self.logits:
            self.sortida = np.asarray(model.get_output_matrix())

    def logprob(self, text: str) -> tuple[float, int]:
        frase = normalitza(text)
        n = len(frase.split()) + 1
        if self.logits:
            logits = self.sortida @ self.np.asarray(self.model.get_sentence_vector(frase))
            return float(logits[self.i_val] - logits[self.i_cat]), n
        # `f.predict` directe (el `predict` de Python falla amb NumPy 2): (probabilitat, etiqueta)
        resultat = dict((e, p) for p, e in self.model.f.predict(frase + "\n", 2, 0.0, "strict"))
        return (math.log(resultat.get("__label__val", 1e-5)) - math.log(resultat.get("__label__cat", 1e-5)), n)


def memoria_mb() -> float:
    """Memòria resident del procés (Linux: /proc; si no, psutil o 0)."""
    try:
        for linia in Path("/proc/self/status").read_text().splitlines():
            if linia.startswith("VmRSS:"):
                return int(linia.split()[1]) / 1024
    except OSError:
        pass
    try:
        import psutil

        return psutil.Process().memory_info().rss / 2**20
    except ImportError:
        return 0.0


class Carregador:
    """Carrega cada fitxer de model una sola vegada i apunta el temps, la
    memòria que hi afig i la grandària del fitxer."""

    def __init__(self, dir_models: Path, fils: int | None) -> None:
        self.dir, self.fils = dir_models, fils
        self.cache: dict[str, object] = {}
        self.cost: dict[str, dict] = {}

    def _kenlm(self, nom: str):
        if nom not in self.cache:
            import kenlm

            path = self.dir / "kenlm" / f"{nom}_o5.binary"
            self._mesura(nom, path, lambda: kenlm.Model(str(path)))
        return self.cache[nom]

    def _mesura(self, nom: str, path: Path | None, carrega) -> None:
        gc.collect()
        m0, t0 = memoria_mb(), time.time()
        self.cache[nom] = carrega()
        self.cost[nom] = {"carrega_s": round(time.time() - t0, 1), "memoria_mb": round(memoria_mb() - m0),
                          "fitxer_mb": round(path.stat().st_size / 2**20) if path and path.exists() else None}

    def puntuador(self, clau: str):
        if clau == "motor":
            return None
        if clau == "flor":
            if "flor" not in self.cache:
                from avlizador.traductor_cat_val.model_llengua.puntuador import ModelLlengua

                self._mesura("flor", None, lambda: ModelLlengua(fils=self.fils))
            return self.cache["flor"]
        if clau == "kenlm_cat":
            return KenLM(self._kenlm("macocu_tot"), -1.0)
        if clau == "kenlm_cat30":
            return KenLM(self._kenlm("macocu_30pc"), -1.0)
        if clau == "kenlm_val":
            return KenLM(self._kenlm("valencia"))
        if clau == "kenlm_val_net":
            return KenLM(self._kenlm("valencia_net"))
        if clau == "diff":
            return Diferencia(self._kenlm("valencia"), self._kenlm("macocu_tot"))
        if clau == "diff_net":
            return Diferencia(self._kenlm("valencia_net"), self._kenlm("macocu_tot"))
        if clau == "fasttext":
            if "fasttext" not in self.cache:
                import fasttext

                path = self.dir / "fasttext" / "autotune.bin"
                self._mesura("fasttext", path, lambda: fasttext.load_model(str(path)))
            return FastText(self.cache["fasttext"])
        raise ValueError(clau)

    def fitxers(self, clau: str) -> list[str]:
        return {"flor": ["flor"], "kenlm_cat": ["macocu_tot"], "kenlm_cat30": ["macocu_30pc"],
                "kenlm_val": ["valencia"], "kenlm_val_net": ["valencia_net"],
                "diff": ["valencia", "macocu_tot"], "diff_net": ["valencia_net", "macocu_tot"],
                "fasttext": ["fasttext"]}.get(clau, [])


# --------------------------------------------------------------------------
# Avaluació
# --------------------------------------------------------------------------

def carrega_benchmark(clau: str, limit: int | None) -> list[dict]:
    dades = json.loads((ARREL / "dades" / "benchmarks" / BENCHMARKS[clau][1]).read_text(encoding="utf-8"))
    files = dades["frases"] if isinstance(dades, dict) else dades
    for f in files:  # v1: el tipus va en `categoria` ("homografs_colisio")
        if not f.get("tipus") and str(f.get("categoria", "")).startswith("homografs_"):
            f["tipus"] = f["categoria"].removeprefix("homografs_")
    return files[:limit] if limit else files


def puntua(benchmark: list[dict], model) -> tuple[list, float]:
    """(frase, text del motor, punts puntuats) de cada frase; segons/frase."""
    t0 = time.time()
    eixida = []
    for it in benchmark:
        text = normalitza_apostrofa(it["oriental"])
        if model is None:
            from avlizador.traductor_cat_val.model_llengua import tradueix_cat_val_ml

            text_motor, punts = tradueix_cat_val_ml(text)
        else:
            text_motor, punts = puntua_punts(text, model, TIPUS)
        eixida.append((it, text_motor, punts))
    return eixida, (time.time() - t0) / max(len(benchmark), 1)


def punt_avaluat(it: dict, punts: list):
    paraula = (it.get("paraula") or "").lower()
    return next((p for p in punts if paraula and p.paraula.lower() == paraula), None)


def avalua(puntuats: list, criteri: Criteri | None) -> dict:
    """Mètriques d'un benchmark amb un criteri (`None` = motor sol)."""
    files, sentit, sentit_model, n_sentit, n_model = [], 0, 0, 0, 0
    for it, text_motor, punts in puntuats:
        hip = text_motor if criteri is None else aplica_tries(text_motor, punts, criteri)
        ref = normalitza_apostrofa(it["occidental"])
        files.append({"id": it["id"], "hipotesi": hip, "error": False, **calcula_metriques(hip, ref)})
        p = punt_avaluat(it, punts)
        if it.get("esperat") and (it.get("tipus") or "") != "control":
            tria = p.motor if (p is not None and criteri is None) else (p.tria if p is not None else None)
            encert = tria == it["esperat"]
            n_sentit += 1
            sentit += encert
            if it.get("tipus") in TIPUS_MODEL:
                n_model += 1
                sentit_model += encert
    r = resumeix(files)
    r.update(sentit=sentit, n_sentit=n_sentit, sentit_model=sentit_model, n_model=n_model)
    r["hipotesis"] = [f["hipotesi"] for f in files]
    return r


def gd_eixida(hipotesis: list[str]) -> dict:
    """GD i GDV globals de l'eixida (sumant marcadors i paraules)."""
    from avlizador.grau_dialectal import calcula_gd

    occ = ori = paraules = 0
    for h in hipotesis:
        r = calcula_gd(h)
        occ, ori, paraules = occ + r["total_occidentals"], ori + r["total_orientals"], paraules + r["total_paraules"]
    return {"gd": round(occ / (occ + ori), 4) if occ + ori else None,
            "gdv": round(1 - ori / paraules, 4) if paraules else None, "orientals": ori}


def criteris(args) -> list[tuple[str, Criteri]]:
    eixida = []
    for marge, defecte, lam in itertools.product(args.marges, args.per_defecte, args.lams):
        eixida.append((f"marge={marge:g} defecte={defecte} lam={lam:g}",
                       Criteri(marge=marge, per_defecte=defecte, lam=lam)))
    return eixida


def num(x, dec: int = 2) -> str:
    return "—" if x is None else f"{x:.{dec}f}".replace(".", ",")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--models", nargs="+", default=list(MODELS), choices=MODELS)
    p.add_argument("--benchmarks", nargs="+", default=list(BENCHMARKS), choices=list(BENCHMARKS))
    p.add_argument("--marges", nargs="+", type=float, default=[0, 0.5, 1, 2, 3, 5, 8, 12])
    p.add_argument("--per-defecte", nargs="+", default=["catala", "motor"], choices=["catala", "motor"])
    p.add_argument("--lams", nargs="+", type=float, default=[0.0, 0.5])
    p.add_argument("--dir-models", type=Path, default=DIR_MODELS)
    p.add_argument("--fils", type=int, default=None, help="fils de torch per a FLOR")
    p.add_argument("--limit", type=int, default=None, help="només les N primeres frases de cada benchmark (proves)")
    args = p.parse_args(argv)

    benchmarks = {b: carrega_benchmark(b, args.limit) for b in args.benchmarks}
    carregador = Carregador(args.dir_models, args.fils)
    llista = criteris(args)
    fix = Criteri()  # el criteri del sistema: marge 2, la catalana per defecte, lam 0,5
    resultat: dict = {"data": datetime.now().isoformat(timespec="minutes"), "limit": args.limit,
                      "criteri_fix": {"marge": fix.marge, "per_defecte": fix.per_defecte, "lam": fix.lam},
                      "models": {}}
    temps_motor = {}
    # Calfa el motor i spaCy abans de cronometrar res (si no, la primera
    # frase del primer benchmark porta la càrrega d'spaCy i dels diccionaris).
    puntua([{"id": "_", "oriental": "Un cop acabada la reunió, marxem.", "occidental": ""}], None)

    for clau in args.models:
        print(f"\n=== {clau} ===", flush=True)
        model = carregador.puntuador(clau)
        if clau == "fasttext":
            resultat["fasttext_puntuacio"] = (f"logits (pèrdua {model.perdua})" if model.logits
                                              else f"probabilitats (pèrdua {model.perdua})")
            print(f"  fastText: {resultat['fasttext_puntuacio']}", flush=True)
        puntuats, segons = {}, {}
        for b, files in benchmarks.items():
            puntuats[b], segons[b] = puntua(files, model)
            if clau == "motor":
                temps_motor[b] = segons[b]
            print(f"  {b}: {segons[b] * 1000:.1f} ms/frase", flush=True)

        files_criteris = [("motor sol", None)] if clau == "motor" else llista
        taula = []
        for nom, criteri in files_criteris:
            r = {b: avalua(puntuats[b], criteri) for b in benchmarks}
            taula.append((nom, criteri, r))

        def clau_ordre(fila):
            r = fila[2]
            return (sum(r[b]["sentit_model"] for b in r if b.startswith("homografs")),
                    r.get("manual", {}).get("exactes", 0))

        millor = max(taula, key=clau_ordre)
        amb_fix = next((f for f in taula if f[1] == fix), None)
        fila_fix = amb_fix or (millor if clau == "motor" else None)
        if fila_fix is None:  # el criteri fix no era en la graella: es calcula a banda
            fila_fix = ("fix", fix, {b: avalua(puntuats[b], fix) for b in benchmarks})

        def descriu(fila):
            nom, _, r = fila
            d = {"criteri": nom}
            for b, v in r.items():
                d[b] = {k: v[k] for k in ("n_frases", "exactes", "bleu_mitja", "chrf_mitja", "ter_corpus",
                                          "wer_corpus", "sentit", "n_sentit", "sentit_model", "n_model")}
                if b == "manual":
                    d[b] |= gd_eixida(v["hipotesis"])
            return d

        cost = {"ms_frase": {b: round(segons[b] * 1000, 1) for b in benchmarks},
                "ms_frase_model": {b: round((segons[b] - temps_motor.get(b, 0)) * 1000, 1) for b in benchmarks},
                "fitxers": {f: carregador.cost.get(f) for f in carregador.fitxers(clau)}}
        resultat["models"][clau] = {
            "millor": descriu(millor), "fix": descriu(fila_fix), "cost": cost,
            "graella": [{"criteri": nom, **{b: {k: v[k] for k in ("exactes", "sentit_model", "chrf_mitja")}
                                            for b, v in r.items()}} for nom, _, r in taula],
        }
        print(f"  millor: {millor[0]} -> " + ", ".join(
            f"{b}: sentit {millor[2][b]['sentit_model']}/{millor[2][b]['n_model']}, exactes {millor[2][b]['exactes']}"
            for b in benchmarks), flush=True)
        del puntuats, taula
        gc.collect()

    RESULTATS.mkdir(parents=True, exist_ok=True)
    sufix = f"{datetime.now():%Y%m%d_%H%M}" + (f"_limit{args.limit}" if args.limit else "")
    (RESULTATS / f"compara_models_{sufix}.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    (RESULTATS / f"compara_models_{sufix}.md").write_text(informe(resultat, benchmarks), encoding="utf-8")
    print(f"\n-> {RESULTATS / f'compara_models_{sufix}.md'}")


def informe(resultat: dict, benchmarks: dict) -> str:
    md = [f"# Comparació de models per a les paraules ambigües ({resultat['data']})", ""]
    if resultat["limit"]:
        md += [f"**Prova amb només {resultat['limit']} frases per benchmark.**", ""]
    md += ["`sentit` = candidat esperat en col·lisions + irresolubles (on decidix el model); "
           "TER/WER, com més baix millor. El cost en ms/frase és el del model (descomptat el motor).", ""]
    for tipus, titol in (("fix", "Amb el criteri del sistema (marge 2, la catalana per defecte)"),
                         ("millor", "Amb el millor criteri de cada model (triat sobre els homògrafs)")):
        md += [f"## {titol}", ""]
        cap = ["Model", "Criteri"]
        for b in benchmarks:
            cap += [f"{b}: sentit", f"{b}: exactes", f"{b}: chrF"]
        cap += ["manual: TER", "manual: WER", "manual: GD", "manual: GDV"]
        md += ["| " + " | ".join(cap) + " |", "|" + "---|" * len(cap)]
        for clau, m in resultat["models"].items():
            d = m[tipus]
            fila = [clau, d["criteri"]]
            for b in benchmarks:
                v = d[b]
                fila += [f"{v['sentit_model']}/{v['n_model']}" if v["n_model"] else "—",
                         f"{v['exactes']}/{v['n_frases']}", num(v["chrf_mitja"])]
            v = d.get("manual", {})
            fila += [num(v.get("ter_corpus")), num(v.get("wer_corpus")), num(v.get("gd"), 4), num(v.get("gdv"), 4)]
            md.append("| " + " | ".join(fila) + " |")
        md.append("")
    md += ["## Cost en CPU", "", "| Model | ms/frase del model (manual) | Memòria (MB) | Fitxer (MB) | Càrrega (s) |",
           "|---|---|---|---|---|"]
    for clau, m in resultat["models"].items():
        fitxers = [c for c in m["cost"]["fitxers"].values() if c]
        memoria = sum(c["memoria_mb"] for c in fitxers) if fitxers else 0
        fitxer = sum(c["fitxer_mb"] or 0 for c in fitxers) if fitxers else 0
        carrega = sum(c["carrega_s"] for c in fitxers) if fitxers else 0
        ms = m["cost"]["ms_frase_model"].get("manual", next(iter(m["cost"]["ms_frase_model"].values())))
        md.append(f"| {clau} | {num(ms, 1)} | {memoria} | {fitxer or '—'} | {num(carrega, 1)} |")
    md += ["", "Memòria: la que afig cada fitxer de model en carregar-lo (VmRSS), sumant tots els que "
           "necessita el model (`diff` = valencià + català). `motor` no carrega cap model."]
    if any("fasttext" in m["cost"]["fitxers"] for m in resultat["models"].values()):
        md += ["", f"fastText puntua amb {resultat.get('fasttext_puntuacio', 'logits')}."]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
