"""Calcule le score des actions et ecrit le CSV que validate.py controle (TF-0056),
a partir d'un contenu redige par la mission -- jamais fabrique ici.

Meme separation que remplir_fiches.py (TF-0030) : la mecanique du barème
(referentiel/scoring.md) et l'ecriture aux colonnes imposees par livrables.py
(COLONNES_ACTIONS, source unique -- reimportees ici, jamais recopiees) vivent dans
la forge ; le libelle de chaque action, le gain/effort/confiance retenus et la
preuve du cran cite sont le jugement d'un audit d'un client donne, et restent chez
la mission.

CE QUI RESTE CHEZ LA MISSION : le contenu. `--contenu` pointe un fichier JSON --
une liste d'objets, un par action -- ecrit par la mission (a la main ou assiste par
IA, validation humaine). Ce script ne juge jamais un gain ou un effort a la place
de l'auditeur : il calcule le score a partir des crans qu'on lui donne, controle
qu'ils respectent les echelles et vocabulaires du referentiel, trie, et ecrit.

Formule imposee par referentiel/scoring.md :

    score = (gain x confiance) / effort

Toujours recalculee ici, jamais relue depuis le contenu : une mission qui corrige
un cran apres coup laisserait un score perime dans son fichier source si le calcul
n'etait pas la seule autorite.

Encodage du CSV : UTF-8 SANS BOM (TF-0056 -- un CSV remis par une mission portait
un BOM, preuve d'un producteur hors forge ; livrables.py, seul autre ecrivain de ce
fichier, ecrit deja sans BOM avec `encoding="utf-8"`. On aligne ce script sur cette
convention, deja etablie, plutot que d'en ouvrir une seconde. Le lecteur commun,
`livrables.lire_actions()`, ouvre en `utf-8-sig` et accepte les deux formes -- ce
choix ne casse donc rien en aval).

Usage :
    python scripts/scorer_actions.py --projet C:/dev/mon-client --contenu seo/actions.json
    python scripts/scorer_actions.py --projet . --contenu seo/actions.json --verifier

Format du contenu (JSON, une LISTE d'objets -- un objet par action) :

    [
      {
        "id": "A1", "action": "...", "volet": "ETAT",
        "noeuds_couverts": [43, 19, 74],
        "gain": 4, "cran_gain_cite": "gain 4 -- ...",
        "effort": 2, "cran_effort_cite": "effort 2 -- ...",
        "confiance": 4, "cran_confiance_cite": "confiance 4 -- ...",
        "horizon": "quick-win",
        "delai_realisation": 2, "delai_effet_mesurable": 28,
        "critere_acceptation": "...", "hypothese_structurante": "...",
        "axe_execution": "IA", "regime_automatisation": "ia-assistee-validation-humaine",
        "axe_cout": "GRATUIT", "cout_eur": 0, "trimestre_cible": "T1",
        "dependance_de": null
      }
    ]

`score` n'est PAS un champ du contenu : il est toujours calcule, jamais lu.
`horizon`, `axe_execution`, `regime_automatisation` et `axe_cout` suivent le
vocabulaire ferme de referentiel/snapshot.schema.json -- une valeur hors liste est
un REFUS, pas une donnee tolerarante qui degraderait le rapport en silence.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from livrables import COLONNES_ACTIONS, ids_noeuds

VOLETS = {"ETAT", "STRATEGIE"}
# Vocabulaire ferme -- copie de referentiel/snapshot.schema.json (enums de `actions[]`),
# pas de scoring.md dont la prose ecrit "quick win" (espace) la ou le schema, seul
# controle mecaniquement par schema.valider(), exige "quick-win" (trait d'union).
HORIZONS = {"quick-win", "structurant", "fondation"}
AXES_EXECUTION = {"IA", "MANUEL"}
REGIMES_AUTOMATISATION = {"bout-en-bout", "ia-assistee-validation-humaine", "manuel-strict"}
AXES_COUT = {"GRATUIT", "PAYANT"}

# Champs que le contenu doit fournir. `score` en est absent : il se calcule, il ne
# se lit pas. `dependance_de` en est absent : seul champ optionnel du lot.
CHAMPS_REQUIS = (
    "id", "action", "volet", "noeuds_couverts", "gain", "cran_gain_cite",
    "effort", "cran_effort_cite", "confiance", "cran_confiance_cite",
    "horizon", "delai_realisation", "delai_effet_mesurable",
    "critere_acceptation", "hypothese_structurante", "axe_execution",
    "regime_automatisation", "axe_cout", "cout_eur", "trimestre_cible",
)


def charger_contenu(chemin: Path) -> list[dict]:
    if not chemin.exists():
        raise SystemExit(f"REFUS : contenu introuvable -- {chemin}")
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(brut, list):
        raise SystemExit(
            f"REFUS : {chemin.name} doit contenir une LISTE d'actions, "
            f"obtenu {type(brut).__name__}"
        )
    return brut


def valider_action(a: dict, connus: set) -> list[str]:
    """Controles de forme, avant tout calcul. Un cran hors echelle 1-5 ou un
    horizon hors vocabulaire produirait un score ou un rapport faux en silence --
    exactement le mode d'echec que ce script existe pour empecher."""
    erreurs: list[str] = []
    manquants = [
        c for c in CHAMPS_REQUIS
        if c not in a or (a[c] in (None, "") and not (c == "cout_eur" and a.get(c) == 0))
    ]
    if manquants:
        return [f"action {a.get('id', '?')!r} : champ(s) manquant(s) {manquants}"]

    ident = a["id"]
    for champ in ("gain", "effort", "confiance"):
        v = a[champ]
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 5):
            erreurs.append(f"action {ident} : {champ}={v!r} hors echelle 1-5")
    if a["volet"] not in VOLETS:
        erreurs.append(f"action {ident} : volet {a['volet']!r} hors {sorted(VOLETS)}")
    if a["horizon"] not in HORIZONS:
        erreurs.append(f"action {ident} : horizon {a['horizon']!r} hors {sorted(HORIZONS)}")
    if a["axe_execution"] not in AXES_EXECUTION:
        erreurs.append(
            f"action {ident} : axe_execution {a['axe_execution']!r} hors {sorted(AXES_EXECUTION)}"
        )
    if a["regime_automatisation"] not in REGIMES_AUTOMATISATION:
        erreurs.append(
            f"action {ident} : regime_automatisation {a['regime_automatisation']!r} "
            f"hors {sorted(REGIMES_AUTOMATISATION)}"
        )
    if a["axe_cout"] not in AXES_COUT:
        erreurs.append(f"action {ident} : axe_cout {a['axe_cout']!r} hors {sorted(AXES_COUT)}")
    if not ids_noeuds(a["noeuds_couverts"]):
        erreurs.append(f"action {ident} : noeuds_couverts ne cite aucun identifiant")
    dep = a.get("dependance_de")
    if dep and dep not in connus:
        erreurs.append(f"action {ident} : dependance_de {dep!r} ne designe aucune action du lot")
    return erreurs


def calculer(actions: list[dict]) -> list[dict]:
    """Applique la formule et trie par score decroissant. Fonction pure : aucune
    lecture ni ecriture disque, pour rester testable sans mission ni tempfile."""
    lignes = []
    for a in actions:
        score = round(a["gain"] * a["confiance"] / a["effort"], 2)
        lignes.append({
            "id": a["id"], "action": a["action"], "volet": a["volet"],
            "noeuds_couverts": " ".join(str(n) for n in ids_noeuds(a["noeuds_couverts"])),
            "gain": a["gain"], "cran_gain_cite": a["cran_gain_cite"],
            "effort": a["effort"], "cran_effort_cite": a["cran_effort_cite"],
            "confiance": a["confiance"], "cran_confiance_cite": a["cran_confiance_cite"],
            "score": score, "horizon": a["horizon"],
            "delai_realisation": a["delai_realisation"],
            "delai_effet_mesurable": a["delai_effet_mesurable"],
            "critere_acceptation": a["critere_acceptation"],
            "hypothese_structurante": a["hypothese_structurante"],
            "axe_execution": a["axe_execution"],
            "regime_automatisation": a["regime_automatisation"],
            "axe_cout": a["axe_cout"], "cout_eur": a["cout_eur"],
            "trimestre_cible": a["trimestre_cible"],
            "dependance_de": a.get("dependance_de") or "",
        })
    lignes.sort(key=lambda l: -l["score"])
    return lignes


def ecrire(projet: Path, contenu: Path, verifier: bool = False) -> int:
    base = projet.resolve() / "seo"
    if not base.is_dir():
        print(f"{base} absent -- creer l'etude avec new_mission.py")
        return 1

    etat_f = base / "etat.json"
    if not etat_f.exists():
        print(f"{etat_f} absent -- l'etude n'a pas de domaine declare")
        return 1
    domaine = json.loads(etat_f.read_text(encoding="utf-8")).get("domaine") or "site"

    actions = charger_contenu(contenu)
    connus = {a.get("id") for a in actions if isinstance(a, dict)}
    erreurs = [e for a in actions for e in valider_action(a, connus)]
    ids = [a.get("id") for a in actions]
    doublons = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    if doublons:
        erreurs.append(f"identifiant(s) d'action duplique(s) : {doublons}")
    if erreurs:
        print(f"REFUS -- {len(erreurs)} anomalie(s) dans {contenu.name} :")
        for e in erreurs:
            print("   ", e)
        return 1

    lignes = calculer(actions)
    bornes = f"score {lignes[0]['score']} a {lignes[-1]['score']}" if lignes else "aucune action"

    livrables = base / "livrables"
    jour = dt.date.today().strftime("%Y%m%d")
    cible = livrables / f"actions-{domaine}-{jour}.csv"

    if verifier:
        print(f"[verification] {len(lignes)} action(s) valide(s), {bornes}")
        print(f"[verification] cible : {cible.name}"
              + (" (deja present -- serait remplace)" if cible.exists() else ""))
        return 0

    livrables.mkdir(exist_ok=True)
    remplace = cible.exists()
    with cible.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLONNES_ACTIONS)
        w.writeheader()
        w.writerows(lignes)

    print(f"{'remplace' if remplace else 'ecrit'} : {cible.name} -- {len(lignes)} action(s), "
          f"{bornes}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Calcule le score des actions (referentiel/scoring.md) et ecrit "
        "le CSV controle par validate.py."
    )
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument(
        "--contenu", required=True,
        help="fichier JSON listant les actions redigees par la mission (voir docstring)",
    )
    p.add_argument("--verifier", action="store_true",
                    help="controles et calcul seuls, aucune ecriture")
    args = p.parse_args()
    return ecrire(Path(args.projet), Path(args.contenu), args.verifier)


if __name__ == "__main__":
    sys.exit(main())
