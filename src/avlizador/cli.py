"""Ordre `avlizador` amb subordres:

    avlizador tradueix "Aquest noi necessita ajuda."   # català -> valencià
    avlizador tradueix --fitxer entrada.txt > eixida.txt
    echo "Aquest noi..." | avlizador tradueix
    avlizador tradueix --motor "..."                   # motor sol, sense model de llengua
    avlizador gd  --text "Este xiquet vol vindre hui." # Grau Dialectal
    avlizador gdv --text "..."                         # GDV
    avlizador gdc --text "..."                         # GDC
    avlizador avalua --benchmarks manual               # avaluació (extra [avaluacio])
    avlizador model info                               # quin model KenLM usa i on és
    avlizador model descarrega [--desti DIR]           # deixa a punt el model (extra [kenlm])
    avlizador model comprova                           # comprova els fitxers del model
    avlizador web                                      # interfície web (extra [web])

`avlizador <subordre> --help` per a les opcions de cada una.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUBORDRES = {
    "tradueix": "Traduïx de català a valencià (motor + KenLM).",
    "gd": "Grau Dialectal (0 = català, 1 = valencià).",
    "gdv": "Grau Dialectal Valencià (1 = valencià pur).",
    "gdc": "Grau Dialectal Català (1 = català pur).",
    "avalua": "Avalua el traductor en els benchmarks de dades/benchmarks/.",
    "model": "Model KenLM: info, descarrega i comprova.",
    "web": "Interfície web i API (extra [web]): http://127.0.0.1:8000.",
}


def tradueix(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="avlizador tradueix",
        description="Traduïx text de català oriental a valencià occidental (norma AVL), "
                    "línia a línia. Sense text ni --fitxer, llig de l'entrada estàndard.",
    )
    parser.add_argument("text", nargs="*", help="Text a traduir.")
    parser.add_argument("--fitxer", type=Path, help="Fitxer de text (UTF-8), una frase o paràgraf per línia.")
    parser.add_argument("--motor", action="store_true",
                        help="Només el motor de regles, sense el model de llengua.")
    parser.add_argument("--model", choices=["kenlm", "kenlm-lemes"], default=None,
                        help="Model de llengua per als homògrafs: kenlm (el per defecte; extra "
                             "[kenlm]; els fitxers es baixen de Hugging Face o d'AVLIZADOR_KENLM_DIR; "
                             "si falten, motor sol i avís) o kenlm-lemes (opció: KenLM de lemes "
                             "parcials, del mateix repositori de Hugging Face o d'AVLIZADOR_KENLM_DIR). Amb --model, si falta alguna "
                             "cosa és un error.")
    args = parser.parse_args(argv)

    from .traductor_cat_val import translate_cat_val, translate_cat_val_motor

    if args.motor:
        funcio = translate_cat_val_motor
    else:
        def funcio(text: str) -> str:
            return translate_cat_val(text, model=args.model)
        if args.model is not None:
            from .traductor_cat_val.model_llengua import sistema_kenlm, sistema_kenlm_lemes
            from .traductor_cat_val.model_llengua.kenlm import FaltaKenLM

            try:  # abans de llegir l'entrada: l'error ix de seguida
                (sistema_kenlm_lemes if args.model == "kenlm-lemes" else sistema_kenlm)()
            except FaltaKenLM as e:
                print(f"ERROR: {e}", file=sys.stderr)
                return 1
    if args.text:
        linies = [" ".join(args.text)]
    elif args.fitxer:
        linies = args.fitxer.read_text(encoding="utf-8").splitlines()
    else:
        linies = sys.stdin.read().splitlines()
    for linia in linies:
        print(funcio(linia) if linia.strip() else linia)
    return 0


def model(argv: list[str]) -> int:
    """`avlizador model info|descarrega|comprova`: el model de llengua KenLM
    (vore `traductor_cat_val/model_llengua/descarrega.py`)."""
    parser = argparse.ArgumentParser(
        prog="avlizador model",
        description="El model de llengua KenLM que usa esta versió del paquet: quin és i on és "
                    "(info), deixar-lo a punt (descarrega) i comprovar que els fitxers són els de la "
                    "revisió (comprova).",
    )
    accions = parser.add_subparsers(dest="accio", required=True, metavar="ACCIÓ")

    p_info = accions.add_parser(
        "info", help="Quin model usa esta versió i on és (sense xarxa).",
        description="Mostra el repositori i la revisió de Hugging Face del model que usa esta versió "
                    "del paquet, la carpeta on el trobaria i quins fitxers hi ha. No baixa res.")
    p_info.add_argument("--dir", type=Path, help="Mirar esta carpeta en lloc de la que usaria el paquet.")
    p_info.add_argument("--json", action="store_true", help="Eixida en JSON.")

    p_desc = accions.add_parser(
        "descarrega", help="Deixa a punt els fitxers del model.",
        description="Baixa de Hugging Face els fitxers del model en la revisió d'esta versió del paquet "
                    "i comprova que són els correctes. Sense --desti, a la memòria cau de Hugging Face "
                    "(on els busca el paquet); amb --desti, en una carpeta per a AVLIZADOR_KENLM_DIR. "
                    "Escriu en l'eixida estàndard la carpeta on queden; els passos, en la d'errors.")
    p_desc.add_argument("--desti", type=Path, help="Carpeta on deixar els fitxers (per a AVLIZADOR_KENLM_DIR).")
    p_desc.add_argument("--origen", type=Path,
                        help="Carpeta amb còpies locals: cada fitxer que corresponga a la revisió es copia "
                             "d'ací en lloc de baixar-lo (només amb --desti).")
    p_desc.add_argument("--lemes", action="store_true",
                        help="També els fitxers de l'opció amb lemes (--model kenlm-lemes).")
    p_desc.add_argument("--revisio", help="Una altra revisió de Hugging Face (per defecte, la del paquet).")
    p_desc.add_argument("--sense-comprovar", action="store_true",
                        help="No comparar els fitxers amb Hugging Face (per a treballar sense xarxa amb "
                             "--origen).")

    p_comp = accions.add_parser(
        "comprova", help="Comprova que els fitxers són els de la revisió.",
        description="Compara la mida i l'empremta de cada fitxer amb les de Hugging Face en la "
                    "revisió d'esta versió del paquet. Ix amb 1 si en falta algun o no correspon.")
    p_comp.add_argument("--dir", type=Path, help="La carpeta a comprovar (per defecte, la que usaria el paquet).")
    p_comp.add_argument("--lemes", action="store_true", help="També els fitxers de l'opció amb lemes.")
    p_comp.add_argument("--revisio", help="Una altra revisió de Hugging Face (per defecte, la del paquet).")

    args = parser.parse_args(argv)
    if args.accio == "descarrega" and args.origen and not args.desti:
        parser.error("--origen només té sentit amb --desti")

    from .traductor_cat_val.model_llengua.descarrega import (ErrorModel, comprova_model, descarrega_model,
                                                             info_model)

    try:
        if args.accio == "info":
            info = info_model(args.dir)
            if args.json:
                import json

                print(json.dumps(info, ensure_ascii=False, indent=2))
            else:
                _escriu_info(info)
            return 0
        if args.accio == "descarrega":
            carpeta = descarrega_model(args.desti, lemes=args.lemes, revisio=args.revisio, origen=args.origen,
                                       comprova=not args.sense_comprovar)
            print(carpeta)
            return 0
        estat = comprova_model(args.dir, lemes=args.lemes, revisio=args.revisio)
        for fitxer, e in estat.items():
            print(f"{e:<13} {fitxer}")
        return 0 if all(e == "bo" for e in estat.values()) else 1
    except ErrorModel as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _escriu_info(info: dict) -> None:
    revisio = info["revisio"] + ("" if info["revisio_del_paquet"] else " (AVLIZADOR_KENLM_REVISIO)")
    llocs = {"argument": "--dir", "AVLIZADOR_KENLM_DIR": "AVLIZADOR_KENLM_DIR", "memoria_cau": "memòria cau de "
             "Hugging Face", None: "cap: es baixarà en el primer ús o amb «avlizador model descarrega»"}
    print(f"avlizador {info['versio_paquet']}")
    print(f"Model:      {info['nom']} (opció amb lemes: {info['nom_lemes']})")
    print(f"Repositori: https://huggingface.co/{info['repo']}")
    print(f"Revisió:    {revisio}")
    print(f"Carpeta:    {info['directori'] or '-'} ({llocs[info['lloc']]})")
    for fitxer, hi_es in info["fitxers"].items():
        print(f"  {'sí' if hi_es else 'no':<3} {fitxer}")
    print(f"Paquet kenlm: {'instal·lat' if info['kenlm_installat'] else 'NO instal·lat (extra [kenlm])'}")
    print(f"Disponible: {'sí' if info['disponible'] else 'no'} (opció amb lemes: "
          f"{'sí' if info['lemes_disponible'] else 'no'})")


def web(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="avlizador web",
        description="Arranca la interfície web i l'API (un sol procés). La configuració es llig "
                    "de les variables d'entorn (vore avlizador.web.main).",
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="Adreça (127.0.0.1 = només este equip; 0.0.0.0 dins de Docker).")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("Falta l'extra [web]: pip install \"avlizador[web]\"", file=sys.stderr)
        return 1
    import os

    # Sense log d'accés: els textos i l'ús del servei no es registren
    # (vore el comentari de PRIVACITAT en avlizador/web/main.py).
    uvicorn.run("avlizador.web.main:app", host=args.host, port=args.port, workers=1,
                access_log=False, log_level=os.environ.get("UVICORN_LOG_LEVEL", "warning"))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for flux in (sys.stdout, sys.stderr):  # en Windows, la consola no és UTF-8
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    if not argv or argv[0] in ("-h", "--help"):
        from . import __version__

        print(__doc__.strip())
        print(f"\nSubordres (avlizador {__version__}):")
        for nom, ajuda in SUBORDRES.items():
            print(f"  {nom:<9} {ajuda}")
        return 0
    if argv[0] in ("-V", "--version"):
        from . import __version__

        print(f"avlizador {__version__}")
        return 0

    subordre, resta = argv[0], argv[1:]
    if subordre == "tradueix":
        return tradueix(resta)
    if subordre in ("gd", "gdv", "gdc"):
        from importlib import import_module

        return import_module(f".grau_dialectal.{subordre}", __package__).main(resta) or 0
    if subordre == "avalua":
        from .avaluacio.avalua import main as avalua

        return avalua(resta)
    if subordre == "model":
        return model(resta)
    if subordre == "web":
        return web(resta)
    print(f"Subordre desconeguda: {subordre!r}. Opcions: {', '.join(SUBORDRES)}.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
