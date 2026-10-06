#!/usr/bin/env python3
"""Genera una muestra de frases reales del BOE donde el motor `traductor/`
detecta al menos un marcador dialectal conocido (alguna de las 9 reglas
le cambia algo al traducir el valenciano) -- pensada para revisar y
corregir a mano y usar despues como conjunto de TEST del traductor sobre
corpus real (no solo las 150 frases curadas del benchmark de AVL).

Por que por regla disparada y no por palabra clave: las reglas de sufijo
(accentuacio, incoatius) y de concordancia (concordanca_dos_dues,
relatiu_on) no son listas de palabras -- la unica forma fiable de saber
si una frase "tiene marcador dialectal" es ejecutar el motor de verdad y
ver si cambia algo, igual que se ejecutara en produccion.

Estratificado por regla: en vez de muestreo puramente aleatorio (que
saldria dominado por lexic.py y conjugacions_dict.py, las reglas con mas
cobertura), se reparte el cupo entre las 9 reglas para que la muestra
sirva de test de TODAS, no solo de las mas frecuentes.

Uso:
    python genera_muestra_test_dialectal.py
    python genera_muestra_test_dialectal.py --total 300 --por-regla 40
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from traductor.rules import Token, detokenize, marca_noms_propis, tokenize  # noqa: E402
from traductor.rules.accentuacio import AccentuacioRule  # noqa: E402
from traductor.rules.concordanca_dos_dues import ConcordancaDosDuesRule  # noqa: E402
from traductor.rules.conjugacions_dict import ConjugacionsDictRule  # noqa: E402
from traductor.rules.demostratius import DemostratiusRule  # noqa: E402
from traductor.rules.incoatius import IncoatiusRule  # noqa: E402
from traductor.rules.lexic import LexicRule  # noqa: E402
from traductor.rules.numerals import NumeralsRule  # noqa: E402
from traductor.rules.possessius import PossessiusRule  # noqa: E402
from traductor.rules.relatiu_on import RelatiuOnRule  # noqa: E402

ENTRADA_PATH = ROOT_DIR / "dades" / "boe_net" / "corpus_entrenamiento_net.jsonl"
SALIDA_PATH = ROOT_DIR / "dades" / "boe_net" / "muestra_test_dialectal.json"

# Mateix orde que `traductor/rules/engine.py::RuleEngine.__init__` -- cal
# replicar-lo a ma ací per a poder saber QUINA regla concreta ha canviat
# cada token (RuleEngine no ho exposa, nomes torna el text final).
REGLES = [
    ("lexic", LexicRule()),
    ("conjugacions_dict", ConjugacionsDictRule()),
    ("possessius", PossessiusRule()),
    ("numerals", NumeralsRule()),
    ("concordanca_dos_dues", ConcordancaDosDuesRule()),
    ("relatiu_on", RelatiuOnRule()),
    ("demostratius", DemostratiusRule()),
    ("accentuacio", AccentuacioRule()),
    ("incoatius", IncoatiusRule()),
]


def traduix_amb_atribucio(text: str) -> tuple[str, list[str]]:
    """Com `translate()`, pero torna tambe la llista de noms de regla que
    han canviat ALGUN token -- comparant quins tokens passen a
    `is_translated=True` just despres de cada `regla.apply()`."""
    tokens: list[Token] = tokenize(text)
    marca_noms_propis(tokens)
    disparades = []
    for nom, regla in REGLES:
        abans = [t.is_translated for t in tokens]
        tokens = regla.apply(tokens)
        if any(t.is_translated and not a for t, a in zip(tokens, abans)):
            disparades.append(nom)
    return detokenize(tokens), disparades


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--total", type=int, default=200, help="Tamany final de la mostra")
    parser.add_argument(
        "--por-regla", type=int, default=None,
        help="Cupo maxim per regla (per defecte, total/num_regles arredonit cap amunt)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    cupo = args.por_regla or -(-args.total // len(REGLES))

    if not ENTRADA_PATH.exists():
        raise SystemExit(f"No existe {ENTRADA_PATH}; ejecuta primero depurar_ruido_estilistico.py")

    print("Procesando corpus con el motor traductor/ (puede tardar unos minutos)...")
    candidatas_por_regla: dict[str, list[dict]] = {nom: [] for nom, _ in REGLES}
    total_procesadas = 0
    total_con_marcador = 0

    with open(ENTRADA_PATH, encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            total_procesadas += 1
            hipotesis, disparadas = traduix_amb_atribucio(registro["texto_valenciano"])
            if not disparadas:
                continue
            total_con_marcador += 1
            fila = {
                "id": registro["id"],
                "documento_id": registro["documento_id"],
                "fecha": registro.get("fecha", ""),
                "similitud": registro.get("similitud"),
                "texto_valenciano": registro["texto_valenciano"],
                "texto_catalan_boe": registro["texto_catalan"],
                "hipotesis_traductor": hipotesis,
                "reglas_disparadas": disparadas,
            }
            for nom in disparadas:
                candidatas_por_regla[nom].append(fila)

    print(f"  {total_procesadas} frases procesadas, {total_con_marcador} con al menos un marcador")
    for nom, candidatas in candidatas_por_regla.items():
        print(f"  {nom}: {len(candidatas)} candidatas")

    random.seed(args.seed)
    elegidas: dict[str, dict] = {}  # por id, para no repetir si dispara varias reglas
    for nom, candidatas in candidatas_por_regla.items():
        random.shuffle(candidatas)
        añadidas = 0
        for fila in candidatas:
            if añadidas >= cupo:
                break
            if fila["id"] in elegidas:
                continue
            elegidas[fila["id"]] = fila
            añadidas += 1

    muestra = list(elegidas.values())
    random.shuffle(muestra)
    if len(muestra) > args.total:
        muestra = muestra[: args.total]
    muestra.sort(key=lambda f: (f["documento_id"], f["id"]))

    SALIDA_PATH.write_text(json.dumps(muestra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado: {SALIDA_PATH} ({len(muestra)} frases)")
    from collections import Counter

    cobertura = Counter(r for f in muestra for r in f["reglas_disparadas"])
    print("Cobertura por regla en la muestra final:")
    for nom, _ in REGLES:
        print(f"  {nom}: {cobertura.get(nom, 0)}")


if __name__ == "__main__":
    main()
