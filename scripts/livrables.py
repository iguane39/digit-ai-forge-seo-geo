"""Assemble les livrables mecaniques d'une etude, sans jamais inventer de contenu.

Ce qui est DERIVABLE des fiches est genere ; ce qui releve du jugement humain est
preserve tel quel s'il existe deja, et laisse vide sinon.

  derivable   : noeuds[] du snapshot, dette d'instrumentation, compteurs d'avancement
  humain      : cible, sensibilite, maturite, actions — jamais fabriques ici

Motif : `actions-*.csv` et `snapshot-*.json` sont des fichiers a schema fixe saisis a
la main aujourd'hui, donc faux des la premiere faute de frappe. Une cle mal
orthographiee disparait du rapport sans un mot.

Usage :
    python scripts/livrables.py --projet C:/dev/mon-client
    python scripts/livrables.py --projet . --verifier    # etat seul, aucune ecriture

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

from gabarits import MOTIF_MODELE, front_matter, version_snapshot
from grille import NB_NOEUDS, RACINE
from schema import valider

SCHEMA = RACINE / "referentiel" / "snapshot.schema.json"
MANIFESTE = RACINE / "seo" / "manifest.json"

# Colonnes imposees par referentiel/scoring.md. Les generer evite la faute de frappe
# qui fait disparaitre une colonne du rapport sans erreur.
COLONNES_ACTIONS = [
    "id", "action", "volet", "noeuds_couverts", "gain", "cran_gain_cite",
    "effort", "cran_effort_cite", "confiance", "cran_confiance_cite", "score",
    "horizon", "delai_realisation", "delai_effet_mesurable", "critere_acceptation",
    "hypothese_structurante", "axe_execution", "regime_automatisation", "axe_cout",
    "cout_eur", "trimestre_cible", "dependance_de",
]


# ------------------------------------------------------- lecture des actions
#
# Ce module CREE actions-*.csv : il en porte donc aussi le lecteur. Il vivait dans
# rapport_html.py, seul consommateur a l'epoque ; validate.py en a besoin a son
# tour (TF-0056) et deux lecteurs auraient diverge -- exactement ce que la forge
# s'interdit ailleurs pour les generateurs de fiches.

# En-tete minimal attendu : sert a valider le dialecte retenu.
COLONNES_RECONNUES = {"id", "action", "libelle", "gain", "effort", "horizon", "score"}


def ids_noeuds(brut) -> list[int]:
    """Identifiants de noeuds cites par une cellule, quel que soit le separateur
    employe a la main : « 43 19 74 », « 43,19,74 » ou « 43;19;74 »."""
    return [int(x) for x in re.findall(r"\d+", str(brut or ""))]


def lire_actions(chemin: Path, trace=None) -> list[dict]:
    """Lit actions-*.csv sans presumer du separateur (TF-0045).

    `csv.DictReader(f)` sans `delimiter` lit en virgule. Un CSV point-virgule --
    separateur par defaut d'Excel en locale francaise -- est alors lu comme un champ
    unique par ligne : toutes les colonnes tombent a None et le rapport imprime
    « n/d » sur l'integralite du tableau, sans le moindre avertissement.

    On sonde, puis on VERIFIE que l'en-tete obtenu contient bien des colonnes
    connues. Si aucun dialecte ne rend un en-tete reconnaissable, on REFUSE : un
    tableau d'actions integralement vide qui se presente comme complet est pire
    qu'une erreur.

    `trace` recoit le message de dialecte non standard. Il est optionnel : un
    appelant qui rend du JSON sur stdout ne peut pas se permettre une ligne de
    texte au milieu de son objet.
    """
    brut = chemin.read_text(encoding="utf-8-sig")
    premiere = brut.split("\n", 1)[0]
    candidats = [";", ",", "\t", "|"]
    try:
        sonde = csv.Sniffer().sniff(premiere, delimiters="".join(candidats)).delimiter
        candidats = [sonde] + [c for c in candidats if c != sonde]
    except csv.Error:
        pass

    for sep in candidats:
        # L'en-tete se lit sur `fieldnames`, PAS sur la premiere ligne de donnees :
        # un CSV fraichement genere n'a que son en-tete, et le sonder par ses lignes
        # le declarait « sans colonne connue » -- donc REFUS sur le fichier que la
        # forge venait elle-meme d'ecrire (constate par la fixture de TF-0056).
        lecteur = csv.DictReader(io.StringIO(brut), delimiter=sep)
        entete = {(c or "").strip().lower() for c in (lecteur.fieldnames or [])}
        if entete & COLONNES_RECONNUES:
            if sep != "," and trace:
                trace(f"  actions : separateur « {sep} » detecte dans {chemin.name}")
            return list(lecteur)
    raise SystemExit(
        f"REFUS : {chemin.name} n'expose aucune colonne connue "
        f"({', '.join(sorted(COLONNES_RECONNUES))}) quel que soit le separateur essaye "
        f"({' '.join(repr(c) for c in candidats)}).\n"
        "Un tableau d'actions rempli de « n/d » qui se presente comme complet est pire "
        "qu'un refus. Verifier l'en-tete du fichier."
    )


def lire_fiches(base: Path) -> list[dict]:
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    out = []
    for n in manifeste["noeuds"]:
        f = base / "analyse" / n["chemin"] / "_fiche.md"
        if f.exists():
            out.append({**n, **front_matter(f)})
    return out


def compteurs(fiches: list[dict]) -> dict:
    c = {"total": NB_NOEUDS, "a_faire": 0, "en_cours": 0, "fait": 0, "hors_perimetre": 0}
    for n in fiches:
        e = (n.get("etat") or "a-faire").replace("-", "_")
        if e in c:
            c[e] += 1
    return c


def noeuds_snapshot(fiches: list[dict]) -> list[dict]:
    """Projection mecanique des fiches. Aucun jugement, aucune invention."""
    out = []
    for n in fiches:
        motif = (n.get("motif_hors_perimetre") or "").strip('"')
        verdict = n.get("verdict")
        e = {
            # front_matter renvoie des chaines : sans ce cast, l'identifiant entier du
            # manifeste est ecrase par la valeur textuelle de la fiche.
            "id": int(n["id"]),
            "branche": n["branche"],
            "noeud": n["noeud"],
            "volet": n["volet"],
            "statut": n["statut"],
            "actions_liees": [],
        }
        # Un noeud non encore juge n'a pas de verdict : la cle est absente, pas nulle.
        if verdict and verdict != "null":
            e["verdict"] = verdict
        if motif and motif != "null":
            e["motif_non_mesure"] = motif
        out.append(e)
    return out


def dette(fiches: list[dict], date: str) -> list[dict]:
    """Ni les noeuds hors portee du modele, ni les renvois ne sont une dette : dans
    les deux cas il n'y a rien a obtenir pour les lever."""
    out = []
    for n in fiches:
        if n.get("etat") != "hors-perimetre":
            continue
        motif = (n.get("motif_hors_perimetre") or "").strip('"')
        if MOTIF_MODELE in motif or n["statut"] == "RV":
            continue
        out.append({
            # TF-0042 : `front_matter()` rend des CHAINES. `noeuds_snapshot()` le
            # corrigeait par un int() explicite, la correction n'avait pas ete
            # reportee ici. Consequence : snapshot juge non conforme, RIEN d'ecrit,
            # donc toute etude comportant au moins un noeud hors perimetre bloquee.
            "noeud_id": int(n["id"]),
            "motif": motif or "non renseigné",
            "a_obtenir": (n.get("source_requise") or "").strip('"') or "à préciser",
            "date_premiere_constatation": date,
        })
    return out


def assembler(projet: Path, verifier: bool = False) -> int:
    base = projet.resolve() / "seo"
    if not base.is_dir():
        print(f"{base} absent — créer l'étude avec new_mission.py")
        return 1

    etat = json.loads((base / "etat.json").read_text(encoding="utf-8"))
    domaine = etat.get("domaine") or "site"
    jour = dt.date.today().strftime("%Y%m%d")
    aujourdhui = dt.date.today().isoformat()
    livrables = base / "livrables"
    livrables.mkdir(exist_ok=True)

    fiches = lire_fiches(base)
    if len(fiches) != NB_NOEUDS:
        print(f"REFUS : {len(fiches)}/{NB_NOEUDS} fiches trouvées — l'étude ne couvre "
              "pas la grille courante.")
        return 1

    c = compteurs(fiches)
    print(f"fiches   : {c['fait']} fait · {c['en_cours']} en cours · "
          f"{c['a_faire']} à faire · {c['hors_perimetre']} hors périmètre")

    # --- snapshot : parties mecaniques generees, parties humaines preservees ----
    cible = livrables / f"snapshot-{domaine}-{jour}.json"
    anciens = sorted(livrables.glob(f"snapshot-{domaine}-*.json"))
    socle = json.loads(anciens[-1].read_text(encoding="utf-8")) if anciens else {}

    snap = dict(socle)
    # Ecriture, pas setdefault : ce snapshot est produit par CE code, il declare
    # donc le contrat de ce code. Herite du socle, il aurait garde la version du
    # run precedent et menti sur ce qu'il contient.
    snap["schema_version"] = version_snapshot()
    snap.setdefault("run", {})
    snap["run"] = {
        **snap["run"],
        "date": aujourdhui,
        "domaine": domaine,
        "modele_acquisition": etat.get("modele_acquisition") or snap["run"].get(
            "modele_acquisition", "autre"),
        "audience_livrable": snap["run"].get("audience_livrable", "dirigeant"),
    }
    snap.setdefault("perimetre", {"pages_decouvertes": 0, "pages_echantillonnees": 0})
    snap.setdefault("sources", {})
    snap.setdefault("actions", [])

    # --- pages[] : projection du dernier crawl, jamais reconstituee -----------
    crawls = sorted((base / "donnees" / "crawl").glob("crawl-*.json")) \
        if (base / "donnees" / "crawl").is_dir() else []
    if crawls:
        c_data = json.loads(crawls[-1].read_text(encoding="utf-8"))
        champs = ("url", "type_gabarit", "profondeur_clic", "code_http", "title", "h1",
                  "canonical", "indexable", "liens_internes_entrants", "poids_ko",
                  "preuve")
        snap["pages"] = [{k: p[k] for k in champs if k in p} for p in c_data["pages"]]
        s = c_data["synthese"]
        snap["perimetre"] = {
            **snap["perimetre"],
            "pages_decouvertes": s["urls_decouvertes"],
            "pages_echantillonnees": s["pages_crawlees"],
            "rendu_js_detecte": False,
        }
        if s["urls_decouvertes"] > 200:
            snap["perimetre"]["methode_echantillonnage"] = (
                f"parcours en largeur depuis l'accueil, plafond de "
                f"{c_data['collecte']['plafond']} pages sur "
                f"{s['urls_decouvertes']} URLs découvertes")
        print(f"pages    : {len(snap['pages'])} URL depuis {crawls[-1].name}")
    else:
        print("pages    : aucun crawl dans donnees/crawl/ — le rapport affichera "
              "une absence déclarée")
    # Genere : projection des fiches
    snap["noeuds"] = noeuds_snapshot(fiches)
    d = dette(fiches, aujourdhui)
    if d:
        snap["dette_instrumentation"] = d
    elif "dette_instrumentation" in snap:
        del snap["dette_instrumentation"]

    ecarts = valider(snap, json.loads(SCHEMA.read_text(encoding="utf-8")))
    if ecarts:
        print(f"\nSNAPSHOT NON CONFORME — {len(ecarts)} écart(s) au schéma :")
        for e in ecarts[:10]:
            print(f"  {e}")
        if len(ecarts) > 10:
            print(f"  … (+{len(ecarts) - 10})")
        print("\nRien n'est écrit : un snapshot hors contrat se dégrade en silence "
              "dans le rapport.")
        return 1

    # --- actions : en-tete seul si absent, jamais de contenu invente -----------
    csvs = sorted(livrables.glob(f"actions-{domaine}-*.csv"))
    cible_csv = livrables / f"actions-{domaine}-{jour}.csv"
    nouveau_csv = not csvs

    if verifier:
        print(f"\n[verification] snapshot conforme · {len(snap['noeuds'])} nœuds · "
              f"{len(d)} ligne(s) de dette")
        print(f"[verification] actions : {'aucun fichier' if nouveau_csv else csvs[-1].name}")
        maj = etat.get("noeuds") != c
        print(f"[verification] compteurs etat.json : "
              f"{'À METTRE À JOUR' if maj else 'à jour'}")
        return 1 if maj else 0

    cible.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(f"snapshot : {cible.name} — {len(snap['noeuds'])} nœuds, "
          f"{len(d)} ligne(s) de dette, conforme au schéma")

    if nouveau_csv:
        with cible_csv.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(COLONNES_ACTIONS)
        print(f"actions  : {cible_csv.name} — en-tête seul, {len(COLONNES_ACTIONS)} "
              "colonnes. À remplir : une action ne se déduit pas des fiches.")
    else:
        print(f"actions  : {csvs[-1].name} conservé — le contenu est humain, "
              "il n'est jamais régénéré.")

    etat["noeuds"] = c
    (base / "etat.json").write_text(json.dumps(etat, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    print("etat.json: compteurs d'avancement recalculés depuis les fiches")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Assemble les livrables mécaniques.")
    p.add_argument("--projet", required=True, help="chemin du projet audité")
    p.add_argument("--verifier", action="store_true", help="état seul, aucune écriture")
    args = p.parse_args()
    return assembler(Path(args.projet), args.verifier)


if __name__ == "__main__":
    sys.exit(main())
