"""Fixtures rouge et verte de la migration d'etude entre deux grilles (TF-0240).

Ce que ce test prouve, et pourquoi il fallait le prouver :

  ROUGE  une etude figee sur une empreinte de grille anterieure est REFUSEE par
         rapport_html.py -- le refus est le comportement voulu, un rapport a 87
         noeuds qui se presente comme la couverture d'une grille de 88 serait un
         document faux remis a un client ;
  VERTE  la MEME etude, apres migrer_mission.py, se restitue sans refus, avec le
         noeud nouveau present et EXPLICITEMENT non instruit.

Un test qui ne verifierait que la branche verte ne prouverait rien : il passerait
tout aussi bien si le refus n'existait pas, c'est-a-dire dans le monde meme que
ce mecanisme existe pour empecher.

La fixture est DERIVEE du registre d'evolutions, jamais ecrite en dur : elle part
de la premiere empreinte declaree dans referentiel/correspondances-grille.json et
remonte la chaine a l'envers pour fabriquer une etude d'epoque. Une evolution de
grille future n'invalide donc pas ce test -- elle l'alimente.

Usage :
    python scripts/test_migrer_mission.py

Sortie non-zero des qu'un cas ne rend pas le verdict attendu. Rien n'est ecrit
dans la forge ni chez une mission : tout vit dans un repertoire temporaire.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import migrer_mission
import rapport_html
from gabarits import (
    SOUS_DOSSIERS_DONNEES,
    VERSION_ETAT,
    fiche_branche,
    fiche_noeud,
    front_matter,
    version_snapshot,
)
from grille import NB_NOEUDS, chaine_correspondance, lire, registre_evolutions, version_grille
from livrables import COLONNES_ACTIONS

MODELE = "local"


# ---------------------------------------------------------------- verificateur


class Bilan:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.cas = 0

    def verifie(self, nom: str, ok: bool, detail: str = "") -> bool:
        self.cas += 1
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)
        return ok

    def rendre(self) -> int:
        print(f"\n{self.cas - len(self.echecs)}/{self.cas} cas conformes")
        for e in self.echecs:
            print(f"  ECHEC : {e}")
        return 1 if self.echecs else 0


# -------------------------------------------------------------------- fixture


def _table_inverse(chaine: list[dict]) -> dict[int, int]:
    """Numerotation courante -> numerotation de l'etude d'epoque."""
    directe, _ = migrer_mission.table_cumulee(chaine)
    return {nouveau: ancien for ancien, nouveau in directe.items()}


def etude_epoque(projet: Path, depart: str, chaine: list[dict]) -> dict:
    """Fabrique une etude telle qu'elle aurait ete produite sur la grille `depart`.

    On part de la grille COURANTE et on remonte : chaque noeud d'aujourd'hui
    reprend le numero qu'il portait alors, et les noeuds nes depuis n'existent
    tout simplement pas. C'est exactement la forme d'une etude ancienne.
    """
    base = projet / "seo"
    inverse = _table_inverse(chaine)
    _, nouveaux = migrer_mission.table_cumulee(chaine)
    donnees = lire()

    (base / "livrables").mkdir(parents=True, exist_ok=True)
    for sous in SOUS_DOSSIERS_DONNEES:
        (base / "donnees" / sous).mkdir(parents=True, exist_ok=True)
        (base / "donnees" / sous / ".gitkeep").write_text("", encoding="utf-8")

    (base / "README.md").write_text("# Etude de fixture\n", encoding="utf-8")
    (base / "cadrage.md").write_text(
        "# Cadrage\n\nProjet : Fixture\nPays / langue : FR\n", encoding="utf-8"
    )
    (base / ".gitignore").write_text("donnees/\n", encoding="utf-8")
    (base / ".forge-seo.json").write_text(
        json.dumps(
            {
                "genere_par": "forge-seo",
                "forge": "fixture",
                "version_grille": depart,
                "date_generation": "2026-01-01",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    absents, instruits, ids_etude = [], [], {}
    analyse = base / "analyse"
    for b in donnees["branches"]:
        noeuds_epoque = [n for n in b["noeuds"] if n["id"] not in nouveaux]
        if not noeuds_epoque:
            continue
        (analyse / b["slug"]).mkdir(parents=True, exist_ok=True)
        # La fiche de branche d'epoque ne connait ni le noeud ne depuis, ni la
        # numerotation d'aujourd'hui : c'est ce qui donne a la migration une vraie
        # regeneration a faire, plutot qu'un fichier deja conforme par accident.
        (analyse / b["slug"] / "_branche.md").write_text(
            fiche_branche(
                {**b, "noeuds": [
                    {**n, "id": inverse.get(n["id"], n["id"])} for n in noeuds_epoque
                ]},
                canonique=False,
            ),
            encoding="utf-8",
        )
        for n in b["noeuds"]:
            if n["id"] in nouveaux:
                absents.append(n["chemin"])
                continue
            ancien = inverse.get(n["id"], n["id"])
            ids_etude[n["chemin"]] = ancien
            dossier = analyse / n["chemin"]
            dossier.mkdir(parents=True, exist_ok=True)
            texte = fiche_noeud({**n, "id": ancien}, MODELE)
            # Une etude reelle est INSTRUITE : sans constat, le rapport rendrait un
            # bloc d'absence et la fixture verte ne prouverait pas grand-chose.
            if "hors-perimetre" not in texte.split("\n---\n", 1)[0]:
                texte = (
                    texte.replace("etat: a-faire", "etat: fait")
                    .replace("verdict: null", "verdict: conforme")
                    .replace("niveau_preuve: null", "niveau_preuve: T1")
                    .replace("date_mesure: null", "date_mesure: 2026-01-01")
                    + f"\nMesure de fixture sur le nœud {ancien}.\n"
                )
                instruits.append(n["chemin"])
            (dossier / "_fiche.md").write_text(texte, encoding="utf-8")

    fiches = [
        {**front_matter(analyse / c / "_fiche.md"), "chemin": c} for c in ids_etude
    ]
    compte = {"total": len(ids_etude), "a_faire": 0, "en_cours": 0, "fait": 0,
              "hors_perimetre": 0}
    for f in fiches:
        compte[(f.get("etat") or "a-faire").replace("-", "_")] += 1
    (base / "etat.json").write_text(
        json.dumps(
            {
                "schema_version": VERSION_ETAT,
                "client": "Fixture",
                "domaine": "fixture.fr",
                "date_creation": "2026-01-01",
                "modele_acquisition": MODELE,
                "etape_courante": "5-actions",
                "etapes": {},
                "noeuds": compte,
                "snapshot_precedent": None,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # Actions et snapshot d'epoque : ils portent des identifiants de noeud, et
    # c'est precisement ce que la migration doit transposer.
    cites = sorted(ids_etude.values())[-4:]
    sortie = io.StringIO()
    w = csv.DictWriter(sortie, fieldnames=COLONNES_ACTIONS, lineterminator="\n")
    w.writeheader()
    w.writerow({
        **{c: "" for c in COLONNES_ACTIONS},
        "id": "A1",
        "action": "Action de fixture",
        "volet": "ETAT",
        "noeuds_couverts": " ".join(str(i) for i in cites),
        "gain": "3", "effort": "2", "confiance": "3", "score": "4.5",
        "horizon": "quick-win", "cout_eur": "0",
    })
    (base / "livrables" / "actions-fixture.fr-20260101.csv").write_text(
        "﻿" + sortie.getvalue(), encoding="utf-8"
    )

    snapshot = {
        "schema_version": version_snapshot(),
        "run": {"date": "2026-01-01", "domaine": "fixture.fr"},
        "perimetre": {},
        "sources": {},
        "baseline": {},
        "pages": [],
        "noeuds": [
            {
                "id": ids_etude[n["chemin"]],
                "branche": n["branche"],
                "noeud": n["noeud"],
                "volet": n["volet"],
                "statut": n["statut"],
                "actions_liees": [],
            }
            for b in donnees["branches"] for n in b["noeuds"]
            if n["chemin"] in ids_etude
        ],
        "cible": {"calculable": False, "motif_non_calculable": "fixture"},
        "actions": [],
        "maturite": {"score": 1, "justification": f"fixture — voir nœud {cites[-1]}"},
        "dette_instrumentation": [
            {
                "noeud_id": cites[0],
                "motif": "fixture",
                "a_obtenir": "rien",
                "date_premiere_constatation": "2026-01-01",
            }
        ],
    }
    (base / "livrables" / "snapshot-fixture.fr-20260101.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return {"absents": absents, "ids": ids_etude, "instruits": instruits,
            "nouveaux": nouveaux, "cites": cites}


# ----------------------------------------------------------------------- cas


def cas_migration(b: Bilan, racine: Path) -> None:
    registre = registre_evolutions()
    evolutions = registre.get("evolutions") or []
    if not evolutions:
        b.verifie("registre d'evolutions non vide", False,
                  "aucune evolution declaree — rien a migrer, rien a prouver")
        return

    depart = evolutions[0]["de"]
    actuelle = version_grille()
    chaine = chaine_correspondance(depart, actuelle)
    if not b.verifie(
        "une chaine relie la premiere empreinte declaree a la grille courante",
        bool(chaine), f"{depart} -> {actuelle} · {len(chaine or [])} evolution(s)",
    ):
        return

    projet = racine / "projet"
    projet.mkdir(parents=True, exist_ok=True)
    fixture = etude_epoque(projet, depart, chaine)
    base = projet / "seo"

    b.verifie(
        "la fixture est bien une etude d'epoque, incomplete au regard de la grille",
        len(fixture["ids"]) == NB_NOEUDS - len(fixture["nouveaux"])
        and len(fixture["absents"]) == len(fixture["nouveaux"]),
        f"{len(fixture['ids'])} fiches pour {NB_NOEUDS} noeuds courants, "
        f"{len(fixture['absents'])} absente(s)",
    )

    # ------------------------------------------------------------------ ROUGE
    try:
        rapport_html.ecrire_rapport(projet)
        refus = None
    except SystemExit as e:
        refus = str(e)
    b.verifie(
        "ROUGE — le rapport REFUSE une etude figee sur une grille anterieure",
        refus is not None and "REFUS" in refus,
        (refus or "aucun refus : un rapport a ete produit").split("\n")[0],
    )
    b.verifie(
        "ROUGE — le refus nomme la grille de l'etude et le noeud manquant",
        bool(refus) and depart in refus
        and any(c in refus for c in fixture["absents"]),
        "le message dit quoi faire, pas seulement que ca echoue",
    )
    b.verifie(
        "ROUGE — aucun rapport n'a ete ecrit",
        not list((base / "livrables").glob("*.html")),
        f"{len(list((base / 'livrables').glob('*.html')))} fichier(s) HTML",
    )

    # -------------------------------------------------------------- --verifier
    avant = (base / ".forge-seo.json").read_bytes()
    empreintes_avant = {
        p: p.read_bytes() for p in sorted(base.rglob("_fiche.md"))
    }
    code = migrer_mission.migrer(projet, verifier=True)
    b.verifie("--verifier rend 0 quand la migration est possible", code == 0, f"code {code}")
    b.verifie(
        "--verifier n'ecrit RIEN",
        (base / ".forge-seo.json").read_bytes() == avant
        and all(p.read_bytes() == v for p, v in empreintes_avant.items()),
        "provenance et fiches inchangees apres le blanc",
    )

    # ------------------------------------------------------------- application
    code = migrer_mission.migrer(projet)
    b.verifie("la migration s'applique sans refus", code == 0, f"code {code}")

    prov = json.loads((base / ".forge-seo.json").read_text(encoding="utf-8"))
    b.verifie(
        "l'empreinte de l'etude est celle de la forge",
        prov.get("version_grille") == actuelle,
        f"{prov.get('version_grille')} attendu {actuelle}",
    )

    journal = (prov.get("migrations") or [{}])[-1]
    complet = all(journal.get(c) for c in ("de", "vers", "date", "par"))
    b.verifie(
        "la migration est journalisee : qui, quand, d'ou, vers ou",
        complet and journal["de"] == depart and journal["vers"] == actuelle,
        f"{journal.get('de')} -> {journal.get('vers')} le {journal.get('date')} "
        f"par {journal.get('par')}",
    )

    ajoutes = journal.get("noeuds_ajoutes_non_instruits") or []
    b.verifie(
        "le journal nomme les noeuds ajoutes et les declare non instruits",
        len(ajoutes) == len(fixture["nouveaux"])
        and all(a.get("etat") == "a-faire" and a.get("verdict") is None for a in ajoutes),
        ", ".join(f"[{a['id']}] {a['noeud']}" for a in ajoutes) or "aucun",
    )

    # -- les identifiants du manifeste courant sont ceux des fiches
    donnees = lire()
    ecarts = []
    for bch in donnees["branches"]:
        for n in bch["noeuds"]:
            fiche = base / "analyse" / n["chemin"] / "_fiche.md"
            if not fiche.exists():
                ecarts.append(f"{n['chemin']} absente")
                continue
            if front_matter(fiche).get("id") != str(n["id"]):
                ecarts.append(f"{n['chemin']} id={front_matter(fiche).get('id')}")
    b.verifie(
        f"les {NB_NOEUDS} fiches portent l'identifiant de la grille courante",
        not ecarts, "; ".join(ecarts[:3]) or "aucun ecart",
    )

    # -- le noeud nouveau est ne NON INSTRUIT, sans verdict fabrique
    neuves = [
        base / "analyse" / n["chemin"] / "_fiche.md"
        for bch in donnees["branches"] for n in bch["noeuds"]
        if n["id"] in fixture["nouveaux"]
    ]
    fm = [front_matter(p) for p in neuves]
    b.verifie(
        "le noeud ajoute est non instruit : etat a-faire, verdict null",
        bool(fm) and all(
            f.get("etat") == "a-faire" and f.get("verdict") == "null" for f in fm
        ),
        ", ".join(f"{f.get('etat')}/{f.get('verdict')}" for f in fm),
    )
    b.verifie(
        "la fiche ajoutee dit dans son corps qu'elle vient d'une migration",
        all("MIGRATION DE GRILLE" in p.read_text(encoding="utf-8") for p in neuves),
        "un humain qui l'ouvre sait pourquoi elle est vide",
    )

    # -- les identifiants cites par les livrables ont suivi
    directe, _ = migrer_mission.table_cumulee(chaine)
    attendus = sorted(directe.get(i, i) for i in fixture["cites"])
    from livrables import ids_noeuds, lire_actions

    action = lire_actions(base / "livrables" / "actions-fixture.fr-20260101.csv")[0]
    b.verifie(
        "les noeuds couverts par les actions sont transposes",
        sorted(ids_noeuds(action.get("noeuds_couverts"))) == attendus,
        f"{action.get('noeuds_couverts')} attendu {attendus}",
    )
    snap = json.loads(
        (base / "livrables" / "snapshot-fixture.fr-20260101.json").read_text(encoding="utf-8")
    )
    b.verifie(
        "le snapshot est transpose ET complete a la taille de la grille",
        len(snap["noeuds"]) == NB_NOEUDS
        and snap["dette_instrumentation"][0]["noeud_id"]
        == directe.get(fixture["cites"][0], fixture["cites"][0]),
        f"{len(snap['noeuds'])} noeuds, dette sur "
        f"{snap['dette_instrumentation'][0]['noeud_id']}",
    )
    ajoute_snap = [n for n in snap["noeuds"] if n["id"] in fixture["nouveaux"]]
    b.verifie(
        "le noeud ajoute entre au snapshot SANS verdict",
        len(ajoute_snap) == len(fixture["nouveaux"])
        and all("verdict" not in n for n in ajoute_snap),
        "une cle absente, jamais un verdict de complaisance",
    )
    branches_courantes = {
        bch["slug"]: fiche_branche(bch, canonique=False) for bch in donnees["branches"]
    }
    b.verifie(
        "les fiches de branche sont regenerees a la numerotation courante",
        all(
            (base / "analyse" / slug / "_branche.md").read_text(encoding="utf-8")
            == attendu
            for slug, attendu in branches_courantes.items()
        ),
        f"{len(branches_courantes)} branche(s) conformes a la grille",
    )

    archive = base / "livrables" / f"pre-migration-{depart}"
    b.verifie(
        "les livrables d'origine sont archives intacts",
        archive.is_dir() and len(list(archive.glob("*"))) == 2,
        f"{len(list(archive.glob('*'))) if archive.is_dir() else 0} fichier(s) sous "
        f"{archive.name}",
    )

    # ------------------------------------------------------------------ VERTE
    try:
        code = rapport_html.ecrire_rapport(projet)
        erreur = None
    except SystemExit as e:
        code, erreur = 1, str(e)
    b.verifie(
        "VERTE — le rapport se genere apres migration",
        code == 0 and erreur is None,
        erreur.split("\n")[0] if erreur else "aucun refus",
    )
    produits = sorted((base / "livrables").glob("*.html"))
    b.verifie("VERTE — un rapport a bien ete ecrit", len(produits) == 1,
              produits[0].name if produits else "aucun")

    if produits:
        html = produits[0].read_text(encoding="utf-8")
        noms = [
            n["noeud"] for bch in donnees["branches"] for n in bch["noeuds"]
            if n["id"] in fixture["nouveaux"]
        ]
        b.verifie(
            "VERTE — le rapport couvre les 88 nœuds de la grille courante",
            f"Les {NB_NOEUDS} nœuds de la grille" in html,
            f"denominateur {NB_NOEUDS}",
        )
        b.verifie(
            "VERTE — le noeud ajoute y figure, nomme",
            all(rapport_html.esc(nom) in html for nom in noms),
            ", ".join(noms),
        )
        b.verifie(
            "VERTE — il y figure comme NON INSTRUIT, pas avec un verdict",
            "non instruit" in html
            and f"{len(fixture['nouveaux'])} nœud(s) non instruit(s)" in html,
            "l'etat est dit en toutes lettres la ou la couverture s'affiche",
        )
        b.verifie(
            "VERTE — aucun verdict n'a ete fabrique pour le noeud ajoute",
            all(
                "verdict" not in front_matter(p) or front_matter(p)["verdict"] == "null"
                for p in neuves
            ),
            "la fiche reste sans verdict apres generation du rapport",
        )


# ----------------------------------------------------------------------- main


CAS = [("TF-0240 -- migration d'etude entre deux grilles", cas_migration)]


def main() -> int:
    b = Bilan()
    racine = Path(tempfile.mkdtemp(prefix="forge-seo-migration-"))
    try:
        for titre, fonction in CAS:
            print(f"\n{titre}")
            fonction(b, racine)
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    return b.rendre()


if __name__ == "__main__":
    sys.exit(main())
