"""Auto-test a fixtures des controles de validate.py.

Un controle qu'on n'a jamais vu ECHOUER n'est pas un controle : c'est une ligne
qui imprime OK. Chaque regle ajoutee ici porte donc deux fixtures --
une VERTE qui doit passer, une ROUGE qui doit echouer, et pour la bonne raison.

Les fixtures sont construites dans un repertoire temporaire du systeme : rien
n'est ecrit dans la forge, rien n'est ecrit chez une mission.

Usage :
    python scripts/autotest.py

Sortie non-zero des qu'un cas ne rend pas le verdict attendu.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

from gabarits import VERSION_ETAT, version_snapshot
from grille import NB_NOEUDS, chaine_correspondance
from livrables import COLONNES_ACTIONS
from remplir_fiches import en_prose
from validate import (
    controler_actions,
    controler_verdicts_de_terrain,
    controler_versions,
)

IDS_GRILLE = set(range(1, NB_NOEUDS + 1))

# --------------------------------------------------------------------- socle


def etude_minimale(base: Path) -> Path:
    """Squelette d'etude reduit a ce que le controle teste regarde."""
    (base / "livrables").mkdir(parents=True, exist_ok=True)
    (base / "etat.json").write_text(
        json.dumps({"schema_version": VERSION_ETAT, "domaine": "exemple.fr"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return base


def snapshot(base: Path, version: str, jour: str = "20260101") -> Path:
    f = base / "livrables" / f"snapshot-exemple.fr-{jour}.json"
    f.write_text(json.dumps({"schema_version": version}, indent=2) + "\n", encoding="utf-8")
    return f


def actions_csv(base: Path, lignes: list[dict], jour: str = "20260101") -> Path:
    """CSV d'actions au gabarit reel : memes colonnes que celles generees."""
    f = base / "livrables" / f"actions-exemple.fr-{jour}.csv"
    with f.open("w", encoding="utf-8", newline="") as sortie:
        w = csv.DictWriter(sortie, fieldnames=COLONNES_ACTIONS)
        w.writeheader()
        for ligne in lignes:
            w.writerow({c: ligne.get(c, "") for c in COLONNES_ACTIONS})
    return f


# ---------------------------------------------------------------- verificateur


class Bilan:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.cas = 0

    def attendu(self, nom: str, obtenu_rouge: bool, attendu_rouge: bool, detail: str = "") -> None:
        self.cas += 1
        ok = obtenu_rouge == attendu_rouge
        etiquette = "ROUGE" if attendu_rouge else "VERT "
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {etiquette} {nom}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)

    def rendre(self) -> int:
        print(f"\n{self.cas - len(self.echecs)}/{self.cas} cas conformes")
        if self.echecs:
            print("ECHECS : " + ", ".join(self.echecs))
            return 1
        return 0


# ------------------------------------------------------------------- TF-0028


def cas_versions(b: Bilan, racine: Path) -> None:
    base = etude_minimale(racine / "versions-vert" / "seo")
    snapshot(base, version_snapshot())
    ecarts, resume = controler_versions(base)
    b.attendu("versions de schema alignees", bool(ecarts), False, resume)

    base = etude_minimale(racine / "versions-rouge-etat" / "seo")
    snapshot(base, version_snapshot())
    (base / "etat.json").write_text(
        json.dumps({"schema_version": "0.9.0", "domaine": "exemple.fr"}) + "\n",
        encoding="utf-8",
    )
    ecarts, _ = controler_versions(base)
    b.attendu(
        "etat.json a une version perimee",
        bool(ecarts) and "etat.json" in ecarts[0],
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )

    base = etude_minimale(racine / "versions-rouge-snapshot" / "seo")
    snapshot(base, "1.0.0")
    ecarts, _ = controler_versions(base)
    b.attendu(
        "snapshot a une version perimee",
        bool(ecarts) and "snapshot" in ecarts[0],
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )


# ------------------------------------------------------------------- TF-0056


def cas_actions(b: Bilan, racine: Path) -> None:
    base = etude_minimale(racine / "actions-vert" / "seo")
    actions_csv(base, [
        {"id": "A1", "action": "Reecrire les titles", "noeuds_couverts": "43 19 74"},
        {"id": "A2", "action": "Creer les pages locales", "noeuds_couverts": "62,5,73"},
    ])
    ecarts, resume = controler_actions(base, IDS_GRILLE)
    b.attendu("actions rattachees a des noeuds existants", bool(ecarts), False, resume)

    base = etude_minimale(racine / "actions-vert-entete" / "seo")
    actions_csv(base, [])
    ecarts, resume = controler_actions(base, IDS_GRILLE)
    b.attendu("CSV a en-tete seul, aucune action", bool(ecarts), False, resume)

    base = etude_minimale(racine / "actions-rouge-inconnu" / "seo")
    actions_csv(base, [
        {"id": "A1", "action": "Reecrire les titles", "noeuds_couverts": "43 19 74"},
        {"id": "A2", "action": "Action fantome", "noeuds_couverts": "92 5"},
    ])
    ecarts, _ = controler_actions(base, IDS_GRILLE)
    b.attendu(
        "une action cite un noeud inexistant",
        any("92" in e for e in ecarts),
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )

    base = etude_minimale(racine / "actions-rouge-detache" / "seo")
    actions_csv(base, [
        {"id": "A1", "action": "Reecrire les titles", "noeuds_couverts": ""},
        {"id": "A2", "action": "Creer les pages locales", "noeuds_couverts": ""},
    ])
    ecarts, _ = controler_actions(base, IDS_GRILLE)
    b.attendu(
        "taux de rattachement nul sur un CSV rempli",
        any("rattachee" in e for e in ecarts),
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )


# ------------------------------------------------------------------- TF-0048


REGISTRE_FIXTURE = {
    "version_courante": "cccccccccccc",
    "evolutions": [
        {
            "de": "aaaaaaaaaaaa",
            "vers": "bbbbbbbbbbbb",
            "date": "2026-01-01",
            "motif": "82 -> 87 noeuds",
            "correspondances": {"70": 75, "71": 76},
            "identifiants_retires": [],
            "identifiants_nouveaux": [83, 84, 85, 86, 87],
        },
        {
            "de": "bbbbbbbbbbbb",
            "vers": "cccccccccccc",
            "date": "2026-02-01",
            "motif": "branche Local",
            "correspondances": {},
            "identifiants_retires": [],
            "identifiants_nouveaux": [],
        },
    ],
}


def cas_correspondances(b: Bilan, racine: Path) -> None:
    chaine = chaine_correspondance("cccccccccccc", "cccccccccccc", REGISTRE_FIXTURE)
    b.attendu(
        "etude sur la grille courante",
        chaine is None,
        False,
        "aucune transposition necessaire",
    )

    chaine = chaine_correspondance("bbbbbbbbbbbb", "cccccccccccc", REGISTRE_FIXTURE)
    b.attendu(
        "une evolution relie l'etude a la forge",
        chaine is None,
        False,
        f"{len(chaine)} table(s)" if chaine is not None else "aucune",
    )

    chaine = chaine_correspondance("aaaaaaaaaaaa", "cccccccccccc", REGISTRE_FIXTURE)
    b.attendu(
        "deux evolutions chainees relient l'etude a la forge",
        chaine is None,
        False,
        f"{len(chaine)} table(s) : "
        + " puis ".join(e["motif"] for e in chaine) if chaine is not None else "aucune",
    )

    chaine = chaine_correspondance("999999999999", "cccccccccccc", REGISTRE_FIXTURE)
    b.attendu(
        "grille evoluee sans table applicable",
        chaine is None,
        True,
        "aucune suite d'evolutions ne relie 999999999999 a cccccccccccc",
    )

    orphelin = {"version_courante": "cccccccccccc", "evolutions": []}
    chaine = chaine_correspondance("aaaaaaaaaaaa", "cccccccccccc", orphelin)
    b.attendu(
        "registre vide face a une etude anterieure",
        chaine is None,
        True,
        "registre sans evolution declaree",
    )


# ------------------------------------------------------------------- TF-0030


TABLE = (
    "La niche est **identifiable** mais large.\n\n"
    "| Segment | Pages | Part |\n|---|---|---|\n"
    "| Gîtes | 12 | 40 % |\n| Chambres | 18 | 60 % |\n\n"
    "- Deux segments cohabitent, cf. `donnees/crawl/`."
)

BALISAGE = set("|*`>")


def cas_prose(b: Bilan, racine: Path) -> None:
    """Le rapport echappe le texte des fiches sans interpreter le markdown : un
    tableau y sortirait en soupe de barres verticales. La regle est donc qu'AUCUN
    balisage ne survit a en_prose -- et que la donnee, elle, survit."""
    rendu = en_prose(TABLE)
    b.attendu(
        "aucun balisage ne survit a la mise en prose",
        bool(BALISAGE & set(rendu)),
        False,
        rendu.replace("\n", " / ")[:110],
    )
    b.attendu(
        "les valeurs du tableau survivent",
        not all(v in rendu for v in ("Gîtes", "12", "40 %", "Chambres", "18", "60 %")),
        False,
        "6 cellules retrouvees dans la prose",
    )
    b.attendu(
        "le tableau brut, lui, porte bien du balisage",
        bool(BALISAGE & set(TABLE)),
        True,
        "fixture rouge : sans en_prose, le rapport recevrait ces caracteres",
    )


# ------------------------------------------------------------------- TF-0264


SOURCE_TERRAIN = "données de terrain publiques (CrUX / PageSpeed Insights)"
SOURCE_CRAWL = "crawl (HTML + en-têtes)"


def fiche_noeud(id_: int, noeud: str, source: str, verdict: str) -> dict:
    """Fiche reduite a ce que le controle de terrain regarde."""
    return {"id": id_, "noeud": noeud, "source_requise": source, "verdict": verdict}


def crux_depose(base: Path, disponible: bool) -> Path:
    """Releve CrUX au format que crux.py ecrit reellement."""
    dossier = base / "donnees" / "performance"
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / "crux-exemple.fr-2026-01-01.json"
    corps = (
        {"disponible": True, "metriques": {"largest_contentful_paint": {"p75": 3128}}}
        if disponible else
        {"disponible": False,
         "motif_indisponible": "trafic insuffisant pour publication"}
    )
    f.write_text(json.dumps(corps, indent=2) + "\n", encoding="utf-8")
    return f


def cas_terrain(b: Bilan, racine: Path) -> None:
    """Laboratoire n'est pas terrain : un verdict de conformite sur un noeud de
    terrain exige la donnee de terrain, ou il n'est pas rendu.

    Le 15/08, le noeud 31 a ete declare CONFORME sur 21 ms de temps de reponse
    serveur median quand CrUX donnait 1 162 ms de TTFB p75 : un facteur cinquante.
    """
    performance = fiche_noeud(31, "Performance", SOURCE_TERRAIN, "conforme")
    canonical = fiche_noeud(30, "Canonical", SOURCE_CRAWL, "conforme")

    base = etude_minimale(racine / "terrain-vert" / "seo")
    crux_depose(base, disponible=True)
    ecarts, resume = controler_verdicts_de_terrain(base, [performance, canonical])
    b.attendu("verdict de terrain adosse a un releve CrUX", bool(ecarts), False, resume)

    base = etude_minimale(racine / "terrain-vert-non-mesure" / "seo")
    ecarts, resume = controler_verdicts_de_terrain(
        base, [fiche_noeud(31, "Performance", SOURCE_TERRAIN, "non-mesure")])
    b.attendu(
        "sans releve, « non-mesure » est le verdict attendu et passe",
        bool(ecarts), False, resume,
    )

    base = etude_minimale(racine / "terrain-vert-hors-portee" / "seo")
    ecarts, resume = controler_verdicts_de_terrain(base, [canonical])
    b.attendu(
        "un noeud sans dependance au terrain n'est pas concerne",
        bool(ecarts), False, resume,
    )

    base = etude_minimale(racine / "terrain-rouge-absent" / "seo")
    ecarts, _ = controler_verdicts_de_terrain(base, [performance, canonical])
    b.attendu(
        "« conforme » rendu sans aucune donnee de terrain",
        len(ecarts) == 1 and "noeud 31" in ecarts[0],
        True,
        ecarts[0][:120] if ecarts else "aucun ecart releve",
    )

    base = etude_minimale(racine / "terrain-rouge-indisponible" / "seo")
    crux_depose(base, disponible=False)
    ecarts, _ = controler_verdicts_de_terrain(base, [performance])
    b.attendu(
        "releve CrUX present mais VIDE (trafic sous le seuil) : toujours pas un feu vert",
        bool(ecarts) and "trafic insuffisant" in ecarts[0],
        True,
        ecarts[0][:120] if ecarts else "aucun ecart releve",
    )


# ----------------------------------------------------------------------- main


CAS = [
    ("TF-0028 -- versions de schema", cas_versions),
    ("TF-0056 -- actions rattachees a la grille", cas_actions),
    ("TF-0048 -- tables de correspondance de grille", cas_correspondances),
    ("TF-0030 -- mise en prose des fiches", cas_prose),
    ("TF-0264 -- verdicts de terrain adosses au terrain", cas_terrain),
]


def main() -> int:
    b = Bilan()
    racine = Path(tempfile.mkdtemp(prefix="forge-seo-autotest-"))
    try:
        for titre, fonction in CAS:
            print(f"\n{titre}")
            fonction(b, racine)
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    return b.rendre()


if __name__ == "__main__":
    sys.exit(main())
