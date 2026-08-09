"""Genere le referentiel canonique seo/ de la forge.

Produit :
  seo/manifest.json                     source de verite machine
  seo/<NN-branche>/_branche.md          17 fiches de branche
  seo/<NN-branche>/<NN-noeud>/_fiche.md 87 fiches de noeud, hydratees

Ce referentiel est le MODELE VIERGE. Il ne contient jamais de donnees client :
l'espace de travail d'une mission est cree par new_mission.py, dans le projet
audite, pas ici.

IDEMPOTENCE STRICTE : creer-si-absent. Aucun fichier existant n'est ecrase.
--force n'ecrase que les fichiers restes identiques a leur version generee ; il
refuse de toucher un fichier modifie a la main et le dit.

Usage :
    python scripts/scaffold.py
    python scripts/scaffold.py --force

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import json
import sys

from gabarits import (
    VERSION_MANIFESTE,
    Compteur,
    dossier,
    ecrire,
    fiche_branche,
    fiche_noeud,
    registre_charger,
    registre_ecrire,
)
from grille import NB_BRANCHES, NB_NOEUDS, RACINE, lire

SEO = RACINE / "seo"

CHAMPS_MANIFESTE = (
    "id",
    "branche",
    "slug_branche",
    "noeud",
    "slug_noeud",
    "chemin",
    "volet",
    "statut",
    "question_audit",
    "source_requise",
    "methode",
    "critere_verdict",
    "doublon_de",
    "modeles",
)


def construire_manifeste(donnees: dict) -> dict:
    return {
        "schema_version": VERSION_MANIFESTE,
        "source": "referentiel/grille-noeuds.md",
        "avertissement": (
            "Genere par scripts/scaffold.py depuis la grille. Ne pas editer a la "
            "main : validate.py detecte toute derive. Le fichier input/Schema "
            "SEO.MD n'est parse par aucun script (indentation cassee du bloc "
            "Objectif -- voir scripts/grille.py)."
        ),
        "comptes": {
            "branches": NB_BRANCHES,
            "noeuds": NB_NOEUDS,
            "dossiers": NB_BRANCHES + NB_NOEUDS,
        },
        "branches": [
            {
                "rang": b["rang"],
                "nom": b["nom"],
                "slug": b["slug"],
                "volet_dominant": b["volet_dominant"],
                "noeuds": [n["id"] for n in b["noeuds"]],
            }
            for b in donnees["branches"]
        ],
        "noeuds": [
            {k: n[k] for k in CHAMPS_MANIFESTE} for n in donnees["noeuds"]
        ],
    }


def generer(force: bool) -> Compteur:
    donnees = lire()
    c = Compteur()
    registre = registre_charger(SEO)

    dossier(SEO, c)
    ecrire(
        SEO / "manifest.json",
        json.dumps(construire_manifeste(donnees), indent=2, ensure_ascii=False) + "\n",
        c,
        registre,
        force,
        SEO,
    )

    for b in donnees["branches"]:
        db = SEO / b["slug"]
        dossier(db, c)
        ecrire(db / "_branche.md", fiche_branche(b, canonique=True), c, registre, force, SEO)
        for n in b["noeuds"]:
            dn = db / n["slug_noeud"]
            dossier(dn, c)
            ecrire(dn / "_fiche.md", fiche_noeud(n), c, registre, force, SEO)

    registre_ecrire(SEO, registre)
    return c


def main() -> int:
    p = argparse.ArgumentParser(description="Genere le referentiel canonique seo/.")
    p.add_argument(
        "--force",
        action="store_true",
        help="regenere les fichiers restes identiques a leur version generee ; "
        "refuse de toucher un fichier modifie a la main",
    )
    args = p.parse_args()

    c = generer(args.force)

    print("scaffold -- referentiel canonique")
    print(f"  dossiers crees   : {c.dossiers}")
    print(f"  fichiers crees   : {c.crees}")
    print(f"  fichiers a jour  : {c.ignores}")
    if args.force:
        print(f"  fichiers remplaces : {c.remplaces}")
    if c.proteges:
        print(f"  PROTEGES ({len(c.proteges)}) -- modifies a la main, non touches :")
        for k in c.proteges:
            print(f"    {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
