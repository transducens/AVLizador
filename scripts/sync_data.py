"""
sync_data.py -- Sincronitza les còpies de `traductor/data/` amb els
fitxers font reals de `pipeline/02_regles_dialectals/lexic/` (equip
AVLizador; abans dins d'una subcarpeta `font_proveidor/`, aplanada el
14/10/2026 en no quedar-hi cap altra font al costat). Des del 30/09/2026
el traductor és pur lookup de
diccionari del proveïdor oficial -- ja no hi ha fonts Apertium/Paula Guerrero.

Per què cal esta sincronització manual: `traductor/rules/*.py` mai llig
`pipeline/02_regles_dialectals/` en temps d'execució -- llig NOMÉS còpies pròpies
dins de `traductor/data/` (decisió de disseny: el paquet `traductor/` ha
de poder funcionar de manera autònoma, sense dependre de la resta del
repositori). Si algú edita un fitxer font directament (com el 30/09/2026,
quan es va editar `acentuacion_limpio.json` a mà: es va llevar una entrada
i afegir-ne una altra), eixe canvi NO arriba al motor fins que algú torna
a copiar el fitxer -- este script ho fa d'una tacada per a totes les
fonts, i diu exactament què ha canviat (entrades afegides/llevades) en
compte de sobreescriure en silenci.

Ús:
    python -m traductor.sync_data            # sincronitza i mostra el resum
    python -m traductor.sync_data --check    # només comprova (exit 1 si cal sincronitzar), no escriu res

Nota: la sincronització és una còpia/embolcall MECÀNIC -- els filtres de
negoci (descartar `_PENDENT`, topònims, resoldre `canonica`, excloure
"després" de l'accentuació, etc.) NO viuen ací, viuen als loaders de cada
regla (`lexic.py`, `numerals.py`...) i s'apliquen soles la pròxima vegada
que s'instancie `RuleEngine` -- este script només s'assegura que la
matèria primera (les còpies de `traductor/data/`) estiga al dia.

Excepció deliberada (05/10/2026): `_marca_ambigues_dins_del_mateix_fitxer`
SÍ és una xicoteta decisió de negoci feta ací, no al loader. Raó: nomes
ací, en processar cada fitxer font UN A UN (abans de fusionar-los), es pot
distingir "ambigüitat gramatical real dins d'un fitxer" (indicatiu/
subjuntiu que col·lapsen en la mateixa forma valenciana) de "dos fonts que
prioritzen traduccions distintes per a la mateixa forma" (com "eixir",
vore comentari a FONTS) -- una volta fusionat tot en una sola llista
"entradas", eixa distinció es perd. Equival a l'anotació `problematica`
que el proveïdor oficial ja posa a mà a les seues fonts, només que
automatitzada i nomes aplicada quan el propi fitxer font ho confirma
interiorment.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ARREL = Path(__file__).resolve().parent.parent
# 30/10/2026: les fonts del proveïdor viuen a `dades/lexic/` (font única;
# abans `pipeline/02_regles_dialectals/lexic/diccionarios/`) i les còpies a
# `src/avlizador/traductor_cat_val/data/` (abans `traductor/data/`).
LEXIC = ARREL / "dades" / "lexic"
DATA = ARREL / "src" / "avlizador" / "traductor_cat_val" / "data"

def _marca_ambigues_dins_del_mateix_fitxer(dades: list[dict]) -> list[dict]:
    """Afig `problematica: true` a qualsevol entrada la forma valenciana de
    la qual té MÉS D'UNA forma catalana distinta DINS D'ESTE MATEIX FITXER
    (ambiguitat gramatical real, típicament indicatiu/subjuntiu que
    col·lapsen en la mateixa forma en valencià -- vore docstring de
    `conjugacions_dict.py`). Mai lleva una marca ja posada a mà.

    A PROPÒSIT nomes mira dins d'un sol fitxer font, no del conjunt ja
    fusionat: una forma que discrepa ENTRE fitxers (com "eixir", vore
    comentari baix) no és ambigua de veres, és que dos fonts prioritzen
    traduccions distintes -- eixe cas ja el resol `setdefault` per orde
    de prioritat, i marcar-lo ací com a "problematica" el llevaria del
    lookup sense necessitat. Verificat (05/10/2026) que este criteri
    reproduix EXACTAMENT les 20 marques manuals ja existents a
    `conjugaciones_limpio.json` que tenen duplicat intern, sense tocar les
    15 que estan marcades per coneixement lingüístic encara que eixe
    fitxer concret només en llistara una forma, ni les 16 d'"eixir" que
    discrepen entre fitxers -- vore conversa 05/10/2026 per als números."""
    per_valencia: dict[str, set[str]] = {}
    for entrada in dades:
        valenciano = entrada["valenciano"].strip().lower()
        per_valencia.setdefault(valenciano, set()).add(entrada["catalan"].strip())
    ambigues = {v for v, cats in per_valencia.items() if len(cats) > 1}

    resultat = []
    for entrada in dades:
        valenciano = entrada["valenciano"].strip().lower()
        if valenciano in ambigues and not entrada.get("problematica"):
            entrada = {**entrada, "problematica": True}
        resultat.append(entrada)
    return resultat


_CONJUGACIONS_DESCRIPCIO = (
    "Formes verbals valencia/catala que difereixen entre dialectes. Des del "
    "19/10/2026 les fonts OFICIALS (prioritat maxima) son les de "
    "'diccionarios/' del proveïdor oficial (renombrada des de 'diccionarios_v1/' el "
    "19/10/2026): 'conjugaciones_general.json' (43.242 "
    "formes, camp 'morfologia' amb el temps/mode -- descodificat amb "
    "evidencia real, vore documentacio/hoja_de_ruta_migracio_diccionarios_v1.md: "
    "pri=present indicatiu, prs=present subjuntiu, pii=imperfet indicatiu, "
    "pis=imperfet subjuntiu, imp=imperatiu, pp=participi, inf=infinitiu) i "
    "'verbos_diferentes_conjugados.json' (912 parells d'arrel verbal distinta, "
    "p.ex. telefonar/trucar). "
    "El camp 'problematica' marca formes on "
    "el valencia usa la mateixa paraula per al present d'indicatiu i el de subjuntiu "
    "(p.ex. abalance = jo abalanco / que jo abalanci), cosa que fa la conversio "
    "ambigua sense analisi gramatical (pos-tagging); conjugacions_dict.py exclou estes "
    "entrades del lookup automatic i les deixa documentades aci per si en el futur es "
    "pot afegir un mecanisme de desambiguacio.\n\n"
    "RETIRATS 19/10/2026, mesurat amb els 4 benchmarks (151 + gplsi, les dos "
    "direccions) ZERO diferencia en cap: 'verbos_no_ambiguos.json', "
    "'verbos_todos_anotados.json' i 'conjugaciones_nuevo.json'. Comprovat "
    "verb a verb que els seus infinitius d'una sola paraula ja estan TOTS "
    "coberts per les fonts oficials -- l'unica cosa que aportaven de mes "
    "eren frases multi-paraula ('llençar la brossa', 'fer cara de'...) que "
    "el motor mai ha pogut fer servir (no hi ha mecanisme de coincidencia "
    "multi-paraula per a verbs). Es van guardar primer a "
    "`lexic/backup_pendent/` com a xarxa de seguretat, pero "
    "eixa carpeta ja s'ha esborrat del tot (mateix dia, confirmat que no "
    "quedava res pendent) -- el contingut es conserva a l'historial de "
    "git si mai calguera.\n\n"
    "'conjugaciones_limpio.json' (968 formes, 111 verbs, el fitxer ORIGINAL "
    "de l'equip AVLizador, 29/09/2026) RETIRAT DEL TOT el 19/10/2026: les SEUES "
    "968 files s'han fusionat SENCERES (no nomes un subconjunt) dins de "
    "'conjugaciones_general.json' mateix, amb IDs 'LIMPIO_1'..'LIMPIO_968' "
    "(per no col·lidir amb la numeracio del proveïdor), 'morfologia' derivat "
    "a mà per a 95 formes seguint el mateix descodificat (resta null, "
    "mateix valor que ja usa el proveïdor per a formes sense classificar), i "
    "el flag 'problematica' preservat tal qual en 55 files que ja el "
    "portaven. **Important, apresa a cops (19/10/2026)**: la primera "
    "temptativa va fusionar NOMES les 97 formes 'noves' (les que faltaven "
    "al lookup val->cat), i això va trencar el doctest de "
    "`cat_val/conjugacions_dict.py` -- 'sofrisquen'->'sofreixin' queda "
    "exclosa del lookup val->cat pel filtre de risc de 3a plural (per aixo "
    "no eixia com a 'forma nova' des d'eixe costat), pero SI fa falta en "
    "brut per a que `carrega_conjugacions_invers()` detecte correctament "
    "que 'sofreixin' es ambigua (patisquen/sofrisquen) i l'excloga. "
    "Fusionar el fitxer SENCER evita este tipus de forat invisible des "
    "d'una sola direccio. El fitxer original es va guardar primer a "
    "'lexic/backup_pendent/', ja esborrada del tot (conservada a "
    "l'historial de git). **Pendent d'informar al proveïdor**: "
    "el paradigma de present de subjuntiu del verb 'ser' seguix sent un "
    "forat real de la seua font (nosaltres ho hem apedaçat local, pero no "
    "soluciona l'origen)."
)


@dataclass(frozen=True)
class FontSpec:
    dest: str
    font: Path | tuple[Path, ...]
    # Extrau la llista d'entrades "crues" a partir de l'estructura tal com
    # ve a CADA fitxer font (independentment de si el dest l'embolica o
    # no). Si `font` és una tupla, s'aplica a cada un i es concatenen en
    # eixe orde -- el PRIMER fitxer de la tupla guanya en cas de conflicte
    # (vore `carrega_conjugacions`, que fa `setdefault`).
    entrades: Callable[[object], list[dict]]
    # Si no és None, el dest NO és una còpia literal del font -- s'embolica
    # amb metadades (vore conjugacions_dialectals.json). Rep la llista
    # d'entrades ja concatenada i torna l'estructura completa a escriure.
    embolica: Callable[[list[dict]], object] | None = None
    # Camps a mostrar en el resum humanament llegible (primer que exista).
    camps: tuple[str, str] = ("valenciano", "catalan")

    @property
    def fonts(self) -> tuple[Path, ...]:
        return self.font if isinstance(self.font, tuple) else (self.font,)


FONTS: list[FontSpec] = [
    FontSpec(
        # 16/10/2026: "diccionarios/lexico_general.json" substituix
        # "unificado.json" -- primera entrega del proveïdor amb categoria
        # gramatical real (camp "categoria") i resolucio de colisions
        # explicita (camp "canonica", "problema", "id_colision"). Mesurat
        # abans de canviar (vore documentacio/hoja_de_ruta_migracio_diccionarios_v1.md):
        # net +175 entrades (1.027->1.202 tras els mateixos filtres),
        # nomes ~10 paraules realment perdudes (<1%), 1 millora real
        # confirmada ("hereua"->"hereva", abans "hereu" amb gènere mal
        # aparellat).
        #
        # Este mateix fitxer ara alimenta TAMBÉ numerals.py (categoria
        # "num") i l'antiga capa d'accentuació (categoria "adj"/"n",
        # retirada com a font a banda -- vore docstring de
        # `rules/val_cat/lexic.py`): ja NO fan falta
        # "numerals_general.json" ni "lexic_acentuacio_general.json"
        # com a còpies separades.
        #
        # Possessius (19/10/2026): l'usuari ha enganxat les 12 files de
        # l'antic "posesivos_cat_val.json" (equip AVLizador) DINS d'este
        # mateix fitxer (`categoria: "det"`, `fuente: "avl_equip"`), aixina
        # que ja no fa falta cap FontSpec a banda ni cap
        # "possessius_general.json" -- `rules/val_cat/possessius.py` i
        # `rules/cat_val/possessius.py` llegixen directament
        # "lexic_general.json" (el dest d'esta font), filtrant per
        # `fuente == "avl_equip"` per no barrejar-se amb els demostratius
        # (que també fan servir `categoria: "det"` dins del mateix fitxer).
        dest="lexic_general.json",
        font=LEXIC / "lexico_general.json",
        entrades=lambda d: d,
    ),
    FontSpec(
        # 19/10/2026: nomes les 2 fonts OFICIALS de diccionarios/. Els
        # 4 fitxers vells de l'equip AVLizador (29-30/09/2026) ja no fan
        # falta cap -- vore _CONJUGACIONS_DESCRIPCIO per al detall i les
        # xifres de cada un. Els 3 primers (verbos_no_ambiguos.json,
        # verbos_todos_anotados.json, conjugaciones_nuevo.json) no
        # aportaven cap infinitiu d'una sola paraula que no estiguera ja
        # ací (mesurat amb els 4 benchmarks: zero diferencia). El 4t
        # (conjugaciones_limpio.json) SÍ aportava cobertura real -- les
        # seues 968 files SENCERES ja s'han fusionat dins de
        # "diccionarios/conjugaciones_general.json" (19/10/2026, IDs
        # "LIMPIO_1".."LIMPIO_968", vore eixe fitxer i
        # _CONJUGACIONS_DESCRIPCIO per a per què SENCERES i no nomes un
        # subconjunt), aixina que el fitxer ja no fa falta tampoc. Els 4
        # es van guardar primer a lexic/backup_pendent/, ja
        # esborrada del tot (conservats a l'historial de git).
        dest="conjugacions_dialectals.json",
        font=(
            LEXIC / "verbos_diferentes_conjugados.json",
            LEXIC / "conjugaciones_general.json",
        ),
        entrades=_marca_ambigues_dins_del_mateix_fitxer,
        embolica=lambda entrades: {
            "total_entradas": len(entrades),
            "descripcio": _CONJUGACIONS_DESCRIPCIO,
            "entradas": entrades,
        },
        camps=("valenciano", "catalan"),
    ),
]


def _signatura(entrada: dict) -> str:
    return json.dumps(entrada, sort_keys=True, ensure_ascii=False)


def _resum_entrada(entrada: dict, camps: tuple[str, str]) -> str:
    a, b = camps
    if a in entrada:
        return f"{entrada[a]!r} -> {entrada.get(b)!r}"
    return repr(entrada)


def _entrades_actuals_dest(spec: FontSpec, dest_dades: object) -> list[dict]:
    if spec.embolica is None:
        return spec.entrades(dest_dades)
    return dest_dades.get("entradas", []) if isinstance(dest_dades, dict) else []


def sync(check_only: bool = False) -> bool:
    """Torna `True` si calia sincronitzar alguna cosa (encara que
    `check_only=True` i per tant no s'haja escrit res de veres)."""
    calen_canvis = False
    for spec in FONTS:
        entrades_noves: list[dict] = []
        for font_path in spec.fonts:
            font_dades = json.loads(font_path.read_text(encoding="utf-8"))
            entrades_noves.extend(spec.entrades(font_dades))
        dest_path = DATA / spec.dest

        entrades_velles: list[dict] = []
        if dest_path.exists():
            dest_dades = json.loads(dest_path.read_text(encoding="utf-8"))
            entrades_velles = _entrades_actuals_dest(spec, dest_dades)

        sig_noves = {_signatura(e): e for e in entrades_noves}
        sig_velles = {_signatura(e): e for e in entrades_velles}
        afegides = sig_noves.keys() - sig_velles.keys()
        llevades = sig_velles.keys() - sig_noves.keys()

        if not afegides and not llevades and dest_path.exists():
            print(f"= {spec.dest}: sense canvis ({len(entrades_noves)} entrades)")
            continue

        calen_canvis = True
        etiqueta = "NOU FITXER" if not dest_path.exists() else f"+{len(afegides)} / -{len(llevades)}"
        print(f"~ {spec.dest}: {etiqueta} (total {len(entrades_noves)})")
        for sig in sorted(llevades):
            print(f"   - {_resum_entrada(sig_velles[sig], spec.camps)}")
        for sig in sorted(afegides):
            print(f"   + {_resum_entrada(sig_noves[sig], spec.camps)}")

        if not check_only:
            if spec.embolica is not None:
                nova_dest = spec.embolica(entrades_noves)
            else:
                # Còpia literal: només té sentit amb UN sol fitxer font
                # (sense embolcall no hi ha manera de fusionar dos
                # estructures completes en una), es reaprofita tal qual.
                (font_path,) = spec.fonts
                nova_dest = json.loads(font_path.read_text(encoding="utf-8"))
            dest_path.write_text(
                json.dumps(nova_dest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    return calen_canvis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Només comprova si cal sincronitzar (exit 1 si sí); no escriu res.",
    )
    args = parser.parse_args(argv)

    calen_canvis = sync(check_only=args.check)

    if args.check:
        if calen_canvis:
            print("\nCalen canvis -- executa `python -m traductor.sync_data` sense --check.")
            return 1
        print("\nTot sincronitzat.")
        return 0

    if calen_canvis:
        print(
            "\nSincronitzat. Recorda: si has canviat lexic_general.json o "
            "lexic_acentuacio_general.json, torna a córrer el benchmark per "
            "confirmar que no s'ha introduït cap regressió (vore traductor/README.md)."
        )
    else:
        print("\nJa estava tot sincronitzat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
