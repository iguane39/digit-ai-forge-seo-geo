"""Cree l'espace de travail SEO DANS LE PROJET AUDITE.

Le projet demandeur possede son etude : donnees, analyse et livrables vivent chez
lui, dans `<projet>/seo/`. La forge ne fournit que la methode et le referentiel --
elle n'heberge aucune donnee client, aucun livrable.

Produit :
  <projet>/seo/METHODE.md         la methode, copiee depuis la forge
  <projet>/seo/README.md          mode d'emploi de l'espace
  <projet>/seo/cadrage.md         entrees de la mission
  <projet>/seo/etat.json          avancement, permet la reprise
  <projet>/seo/.forge-seo.json    provenance : version de la grille, date
  <projet>/seo/.gitignore         garde-fou de confidentialite
  <projet>/seo/donnees/{gsc,ga,crm,logs,crawl}/
  <projet>/seo/analyse/           104 dossiers, 87 fiches hydratees
  <projet>/seo/livrables/

REFUS D'ECRASEMENT : si <projet>/seo/ existe deja, le script s'arrete. Ecraser une
etude en cours detruirait du travail sans trace. Aucun --force ici : pour repartir
de zero, supprimer le dossier a la main, apres avoir regarde ce qu'il contient.

Usage :
    python scripts/new_mission.py --projet C:/dev/mon-client --client "Acme" --domaine acme.fr
    python scripts/new_mission.py --liste

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from gabarits import (
    SOUS_DOSSIERS_DONNEES,
    Compteur,
    cadrage,
    dossier,
    ecrire,
    etat,
    fiche_branche,
    fiche_noeud,
    gitignore_mission,
    gitkeep,
    provenance,
    readme_mission,
    registre_charger,
    registre_ecrire,
)
from grille import MODELES, RACINE, lire, version_grille

REGISTRE = RACINE / "missions.json"


# ------------------------------------------------------------------- registre


def _registre_lire() -> list[dict]:
    if REGISTRE.exists():
        return json.loads(REGISTRE.read_text(encoding="utf-8"))
    return []


def _registre_ajouter(entree: dict) -> None:
    entrees = [e for e in _registre_lire() if e["chemin"] != entree["chemin"]]
    entrees.append(entree)
    entrees.sort(key=lambda e: e["chemin"])
    REGISTRE.write_text(
        json.dumps(entrees, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def lister() -> int:
    entrees = _registre_lire()
    if not entrees:
        print("aucune mission enregistree")
        print("(le registre missions.json ne liste que les missions creees depuis")
        print(" cette forge ; il ne contient aucune donnee client)")
        return 0
    print(f"{len(entrees)} mission(s) :")
    for e in entrees:
        chemin = Path(e["chemin"])
        presente = "" if (chemin / "seo").is_dir() else "  [DOSSIER INTROUVABLE]"
        print(f"  {e['client']:<24} {e['domaine']:<24} {e['date']}{presente}")
        print(f"    {e['chemin']}")
    return 0


# -------------------------------------------------------------------- creation


def creer(projet: Path, client: str, domaine: str, modele: str | None = None) -> int:
    projet = projet.resolve()

    if not projet.is_dir():
        print(f"REFUS : {projet} n'existe pas ou n'est pas un dossier.")
        print("Le projet audite doit exister. Ce script n'invente pas d'arborescence")
        print("hors de la forge.")
        return 1

    if projet == RACINE or RACINE in projet.parents or projet in RACINE.parents:
        print(f"REFUS : {projet} est la forge ou la contient.")
        print("L'etude appartient au projet audite, pas a la forge. Choisir un")
        print("repertoire de projet distinct.")
        return 1

    base = projet / "seo"
    if base.exists():
        print(f"REFUS : {base} existe deja.")
        print("Une etude ne s'ecrase pas. Pour repartir de zero, supprimer le dossier")
        print("a la main apres avoir verifie ce qu'il contient.")
        return 1

    donnees = lire()
    c = Compteur()
    registre: dict = {}
    aujourdhui = dt.date.today().isoformat()

    dossier(base, c)

    # La methode est COPIEE dans l'etude, pas seulement referencee : l'audit
    # s'enclenche en ouvrant ce fichier, et l'etude reste lisible meme detachee de
    # la forge. L'empreinte de grille dans .forge-seo.json dit sur quelle version.
    methode = (RACINE / "referentiel" / "methode.md").read_text(encoding="utf-8")
    ecrire(
        base / "METHODE.md",
        f"<!-- Copie de referentiel/methode.md — forge {RACINE} — grille "
        f"{version_grille()} — {aujourdhui}. Ne pas editer ici : la source est dans "
        f"la forge. -->\n\n{methode}",
        c, registre, False, base,
    )
    ecrire(base / "README.md", readme_mission(client), c, registre, False, base)
    ecrire(base / "cadrage.md", cadrage(), c, registre, False, base)
    ecrire(base / "etat.json", etat(client, domaine, aujourdhui, modele), c, registre, False, base)
    ecrire(base / ".gitignore", gitignore_mission(), c, registre, False, base)
    ecrire(
        base / ".forge-seo.json",
        provenance(version_grille(), str(RACINE), aujourdhui),
        c,
        registre,
        False,
        base,
    )

    dd = base / "donnees"
    dossier(dd, c)
    for sous in SOUS_DOSSIERS_DONNEES:
        d = dd / sous
        dossier(d, c)
        gitkeep(d, c, registre, False, base)

    da = base / "analyse"
    dossier(da, c)
    for b in donnees["branches"]:
        db = da / b["slug"]
        dossier(db, c)
        ecrire(db / "_branche.md", fiche_branche(b, canonique=False), c, registre, False, base)
        for n in b["noeuds"]:
            dn = db / n["slug_noeud"]
            dossier(dn, c)
            ecrire(dn / "_fiche.md", fiche_noeud(n, modele), c, registre, False, base)

    dl = base / "livrables"
    dossier(dl, c)
    gitkeep(dl, c, registre, False, base)

    registre_ecrire(base, registre)

    _registre_ajouter(
        {
            "client": client,
            "domaine": domaine,
            "chemin": str(projet),
            "date": aujourdhui,
            "version_grille": version_grille(),
        }
    )

    print(f"etude creee : {base}")
    print(f"  client   : {client}")
    print(f"  domaine  : {domaine}")
    print(f"  dossiers : {c.dossiers}")
    print(f"  fichiers : {c.crees}")
    if modele:
        hors = sum(
            1
            for b in donnees["branches"]
            for n in b["noeuds"]
            if not n["doublon_de"] and modele not in n.get("modeles", [])
        )
        print(f"  modele   : {modele} — {hors} nœud(s) hors portée, pré-marqués")
    else:
        print("  modele   : non déclaré — aucun nœud pré-marqué hors portée")
    print("")
    print("Etapes suivantes, DANS LE PROJET AUDITE :")
    print(f"  1. remplir  {base / 'cadrage.md'} (champs OBLIGATOIRE)")
    print(f"  2. deposer les exports dans {base / 'donnees'}")
    print(f"  3. ouvrir {base / 'METHODE.md'} et derouler le runbook")
    print(f"  4. python <forge>/scripts/rapport_html.py --projet . --verifier")
    print("")
    print(f"Verification : python scripts/validate.py --mission \"{projet}\"")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Cree l'espace de travail SEO dans le projet audite."
    )
    p.add_argument("--projet", help="chemin du projet audite (doit exister)")
    p.add_argument("--client", help="nom du client, pour les metadonnees")
    p.add_argument("--domaine", help="domaine audite, sans protocole")
    p.add_argument("--modele", choices=sorted(MODELES),
                   help="modele d'acquisition ; pre-marque les noeuds hors portee")
    p.add_argument("--liste", action="store_true", help="liste les missions creees")
    args = p.parse_args()

    if args.liste:
        return lister()
    if not (args.projet and args.client and args.domaine):
        p.error("--projet, --client et --domaine sont requis (ou utiliser --liste)")
    return creer(Path(args.projet), args.client, args.domaine, args.modele)


if __name__ == "__main__":
    sys.exit(main())
