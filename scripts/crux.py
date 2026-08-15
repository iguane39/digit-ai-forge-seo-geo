"""Etape 1 bis : collecte des metriques de terrain (CrUX) pour le noeud 31 (TF-0105).

Le noeud 31 (Performance) demande des « donnees de terrain publiques (CrUX /
PageSpeed Insights) » mais rien ne les collectait : chaque auditeur relevait a
la main dans l'interface PageSpeed Insights, sans trace ni reproductibilite
d'un audit a l'autre. Ce script appelle directement l'API CrUX (Chrome UX
Report) -- publique et gratuite, aucune facturation -- et ecrit un JSON
horodate dans `seo/donnees/performance/`.

Cle API : gratuite, sans facturation, a obtenir sur
https://developer.chrome.com/docs/crux/api#getting_an_api_key -- jamais
codee en dur, jamais lue depuis un `.env` par ce script : elle se fournit en
argument (`--cle`) ou variable d'environnement `CRUX_API_KEY`, deposee par
qui l'utilise.

Le referentiel (grille-noeuds.md, noeud 31, garde-fou 4) est explicite : « le
jeu de metriques et leurs seuils changent, verifier avant de conclure ». Ce
script ne code donc AUCUN seuil numerique (2,5 s, 0,1, 200 ms...) : il relaie
la repartition bon / a ameliorer / mauvais telle que l'API CrUX la classe
elle-meme, jamais un seuil recopie a la main qui se perimerait en silence.

Usage :
    python scripts/crux.py --projet . --url https://exemple.fr/produit --cle AIza...
    python scripts/crux.py --projet . --url https://exemple.fr --origine
    CRUX_API_KEY=AIza... python scripts/crux.py --projet . --url https://exemple.fr

Python 3, bibliotheque standard uniquement (urllib).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
FACTEURS_FORME = ("PHONE", "DESKTOP", "TABLET", "ALL_FORM_FACTORS")

# Ou l'etude range ses releves de terrain, et comment on reconnait un noeud qui en
# depend. Le motif se cherche dans `source_requise` du manifeste, jamais sur un
# identifiant de noeud : les identifiants bougent d'une version de grille a
# l'autre, la source requise, non.
DOSSIER_TERRAIN = ("donnees", "performance")
MOTIF_SOURCE_TERRAIN = "crux"

# Noeud que ce script instrumente, et donc qu'il laisse non mesure quand il ne peut
# pas mesurer (meme convention qu'agents_ia.py, TF-0260).
NOEUDS = [31]

# TF-0273 -- symetrie avec agents_ia.py : un « non mesure » de terrain laisse une
# TRACE, au meme endroit que la sortie mesuree et au meme vocabulaire. Sans cle, le
# script sortait en 1 sans rien ecrire : l'etude ne gardait aucune preuve datee que
# le noeud 31 n'avait pas ete mesure, et un run suivant ne pouvait pas distinguer
# « jamais tente » de « tente sans la donnee requise ».
DONNEE_MANQUANTE = (
    "clé API CrUX (gratuite, sans facturation) — fournie par `--cle` ou la variable "
    "d'environnement CRUX_API_KEY, jamais lue d'un .env par ce script"
)

# Le message que TOUT refus de mesure de terrain doit porter. Une cle CrUX est
# gratuite et sans facturation : le run du 15/08 a conclu « conforme » sur 21 ms
# de mediane serveur faute de l'avoir demandee, quand le terrain donnait 1 162 ms
# de TTFB p75. Le cout de la cle etait deux commandes.
OBTENIR_LA_CLE = (
    "Clé CrUX GRATUITE, sans facturation, deux commandes :\n"
    "    gcloud services enable chromeuxreport.googleapis.com\n"
    '    gcloud services api-keys create --display-name="CrUX forge-seo"\n'
    "  (ou en un clic : https://developer.chrome.com/docs/crux/api#getting_an_api_key)\n"
    "  Puis : python scripts/crux.py --projet <chemin> --url <site> --origine"
)

COMMENT_L_OBTENIR = [
    "Compte Google Cloud — gcloud services enable chromeuxreport.googleapis.com "
    'puis gcloud services api-keys create --display-name="CrUX forge-seo".',
    "Sans gcloud — création de la clé en un clic : "
    "https://developer.chrome.com/docs/crux/api#getting_an_api_key",
    "Clé obtenue — la passer par `--cle` ou la variable CRUX_API_KEY, et relancer "
    "ce script (ajouter `--origine` sur un site à faible trafic par page).",
    "Aucune clé obtenable — le nœud 31 (Performance) reste NON MESURÉ : aucune "
    "mesure de laboratoire ne s'y substitue (le 15/08, 21 ms de médiane serveur "
    "ont valu « conforme » quand le terrain donnait 1 162 ms de TTFB p75). C'est "
    "une limite déclarée du livrable, pas un oubli.",
]


def verdict_non_mesurable(motif_source: str, aujourdhui: str, cible: str, mode: str,
                          facteur_forme: str) -> dict:
    """Sortie du script quand la donnee d'entree n'existe pas (TF-0273).

    Meme forme que la sortie mesuree -- un consommateur lit `mesurable` et sait ou
    il en est --, et jamais de metrique fabriquee : `disponible: false` sans
    `metriques` fait que terrain_disponible() ne prend JAMAIS cette trace pour un
    releve exploitable. « Pas de donnees de terrain publiees » (404, un resultat
    mesure) et « personne n'a interroge l'API » (ici) sont deux constats
    differents : les confondre ferait juger le noeud 31 sur du vide.
    """
    return {
        "collecte": {
            "outil": "forge-seo/crux.py",
            "date": aujourdhui,
            "cible": cible,
            "mode": mode,
            "facteur_forme": facteur_forme,
            "source": "aucune — l'API CrUX n'a pas été interrogée",
        },
        "mesurable": False,
        "verdict": "non-mesurable",
        "noeuds_concernes": NOEUDS,
        "disponible": False,
        "motif": (
            f"Non mesurable en l'état — {motif_source}. Donnée requise : "
            f"{DONNEE_MANQUANTE}."
        ),
        "motif_indisponible": (
            f"non mesuré — {motif_source} (aucun appel à l'API CrUX ; distinct d'un "
            "site sous le seuil de publication CrUX, qui est un résultat mesuré)"
        ),
        "donnee_manquante": DONNEE_MANQUANTE,
        "comment_l_obtenir": COMMENT_L_OBTENIR,
        # Explicitement nuls, jamais des dictionnaires vides : voir la docstring.
        "metriques": None,
        "cle_enregistrement": None,
        "periode_collecte": None,
    }


def noeud_exige_terrain(source_requise: str | None) -> bool:
    """Ce noeud se juge-t-il sur des donnees de TERRAIN (CrUX) ?

    TF-0264 -- le noeud 31 (Performance) demande « données de terrain publiques
    (CrUX / PageSpeed Insights) ». Sans cle, le run se rabattait sur ce qu'il
    avait -- un temps de reponse serveur mesure en laboratoire -- et rendait
    « conforme » sur la mauvaise grandeur. Laboratoire et terrain divergeaient
    d'un facteur cinquante. Un verdict de conformite sur un tel noeud exige donc
    la donnee que la grille nomme, ou il n'est pas rendu.
    """
    return MOTIF_SOURCE_TERRAIN in (source_requise or "").lower()


def terrain_disponible(base_etude: Path) -> tuple[bool, str]:
    """Un releve CrUX EXPLOITABLE existe-t-il dans l'etude ? (verdict, resume)

    « Exploitable » exclut le releve marque `disponible: false` : un site sous le
    seuil de publication de CrUX n'a pas de donnees de terrain, et c'est un
    resultat -- non-mesurable -- pas un feu vert pour juger sur autre chose.
    """
    dossier = base_etude.joinpath(*DOSSIER_TERRAIN)
    fichiers = sorted(dossier.glob("crux-*.json")) if dossier.is_dir() else []
    if not fichiers:
        return False, "aucun relevé CrUX dans seo/donnees/performance/"
    vides = []
    for f in fichiers:
        try:
            brut = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            vides.append(f"{f.name} illisible ({e})")
            continue
        if brut.get("disponible") and brut.get("metriques"):
            return True, f"{f.name} — {len(brut['metriques'])} métrique(s) de terrain"
        vides.append(f"{f.name} : {brut.get('motif_indisponible') or 'aucune métrique'}")
    return False, " ; ".join(vides)


def interpreter_reponse(corps: dict) -> dict:
    """Traduit un enregistrement CrUX brut en resume exploitable, SANS jamais
    recopier de seuil numerique -- seulement ce que l'API elle-meme classe.

    Fonction pure, testable sur des reponses en boite (aucun reseau) : c'est
    la preuve a double sens de ce script (scripts/test_crux.py).
    """
    record = corps.get("record", {})
    metriques = {}
    for nom, donnee in record.get("metrics", {}).items():
        histogramme = donnee.get("histogram", [])
        # CrUX ordonne TOUJOURS ses classes bon / a-ameliorer / mauvais dans cet
        # ordre -- on relaie la position, jamais une valeur de coupure en dur.
        etiquettes = ["bonne", "a_ameliorer", "mauvaise"]
        repartition = {
            etiquettes[i]: bucket.get("density")
            for i, bucket in enumerate(histogramme[:3])
        }
        metriques[nom] = {
            "p75": donnee.get("percentiles", {}).get("p75"),
            "repartition_experience": repartition,
        }
    return {
        "cle_enregistrement": record.get("key", {}),
        "periode_collecte": record.get("collectionPeriod", {}),
        "metriques": metriques,
    }


def appeler_api(cle: str, cible: str, mode: str, facteur_forme: str) -> tuple[int, dict | bytes]:
    """Appelle l'API CrUX. Retourne (code_http, corps_json_ou_brut)."""
    charge = {mode: cible}
    if facteur_forme != "ALL_FORM_FACTORS":
        charge["formFactor"] = facteur_forme
    req = urllib.request.Request(
        f"{ENDPOINT}?key={urllib.parse.quote(cle)}",
        data=json.dumps(charge).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        brut = e.read()
        try:
            return e.code, json.loads(brut.decode("utf-8"))
        except json.JSONDecodeError:
            return e.code, brut
    except urllib.error.URLError as e:
        return 0, {"error": {"message": str(e.reason)}}


def nom_fichier(cible: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", cible.replace("https://", "").replace("http://", ""))


def main() -> int:
    p = argparse.ArgumentParser(
        description="Collecte les metriques de terrain CrUX pour le noeud 31 (Performance)."
    )
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument("--url", required=True, help="URL ou origine a interroger")
    p.add_argument(
        "--origine", action="store_true",
        help="interroge l'ORIGINE entiere (tout le domaine) plutot que l'URL exacte -- "
             "seule facon d'obtenir des donnees sur un site a faible trafic par page",
    )
    p.add_argument(
        "--facteur-forme", choices=FACTEURS_FORME, default="PHONE",
        help="PHONE par defaut -- le referentiel demande le mobile en priorite",
    )
    p.add_argument(
        "--cle", default=os.environ.get("CRUX_API_KEY"),
        help="cle API CrUX -- ou variable d'environnement CRUX_API_KEY",
    )
    args = p.parse_args()

    dossier = Path(args.projet).resolve() / "seo" / "donnees" / "performance"
    if not dossier.parent.parent.is_dir():
        print(f"{dossier.parent.parent} absent — créer l'étude avec new_mission.py")
        return 1
    dossier.mkdir(parents=True, exist_ok=True)

    aujourdhui = dt.date.today().isoformat()
    mode = "origin" if args.origine else "url"

    # TF-0273 -- sans cle, le refus reste un refus (la cle est gratuite et s'obtient
    # en deux commandes : ce n'est pas une donnee hors de portee, sortie 1 conservee),
    # mais il ECRIT desormais sa trace, au meme endroit et au meme vocabulaire que la
    # sortie mesuree. Nom de fichier distinct de celui d'un releve : une absence de
    # mesure n'ecrase jamais une mesure.
    if not args.cle:
        resultat = verdict_non_mesurable(
            "aucune clé API CrUX fournie (--cle ou variable d'environnement "
            "CRUX_API_KEY absente)", aujourdhui, args.url, mode, args.facteur_forme)
        trace = dossier / f"crux-non-mesure-{nom_fichier(args.url)}-{aujourdhui}.json"
        trace.write_text(
            json.dumps(resultat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"NON MESURABLE — nœud {', '.join(str(n) for n in NOEUDS)}")
        print(f"  {resultat['motif']}")
        print("  Comment l'obtenir :")
        for piste in COMMENT_L_OBTENIR:
            print(f"    · {piste}")
        print(f"écrit : {trace.relative_to(Path(args.projet).resolve())}")
        print(OBTENIR_LA_CLE)
        return 1

    print(f"CrUX : interrogation de {mode}={args.url} ({args.facteur_forme})")
    code, corps = appeler_api(args.cle, args.url, mode, args.facteur_forme)

    # `mesurable` vaut True des lors que l'API a repondu : un 404 CrUX (site sous le
    # seuil de publication) est un RESULTAT mesure, pas une absence de mesure -- seul
    # le cas « pas de cle » ci-dessus est non mesurable (TF-0273).
    resultat = {
        "mesurable": True,
        "verdict": "mesure",
        "noeuds_concernes": NOEUDS,
        "collecte": {
            "outil": "forge-seo/crux.py",
            "date": aujourdhui,
            "cible": args.url,
            "mode": mode,
            "facteur_forme": args.facteur_forme,
            "source": (
                "Chrome UX Report API (chromeuxreport.googleapis.com) — données de "
                "terrain agrégées sur 28 jours glissants"
            ),
            "limite": (
                "Répartition bonne/à améliorer/mauvaise CLASSÉE PAR L'API elle-même — "
                "aucun seuil numérique recopié ici. Le référentiel (nœud 31, garde-fou "
                "4) demande de vérifier au run le jeu de métriques CWV en vigueur : il "
                "change."
            ),
        },
    }

    if code == 200 and isinstance(corps, dict):
        resultat["disponible"] = True
        resultat.update(interpreter_reponse(corps))
        n = len(resultat["metriques"])
        print(f"  disponible — {n} métrique(s) : {', '.join(resultat['metriques'])}")
    elif code == 404:
        resultat["disponible"] = False
        resultat["motif_indisponible"] = (
            "aucun enregistrement CrUX — trafic insuffisant pour publication (Google "
            "n'expose pas de données en dessous d'un seuil d'échantillon)."
        )
        print("  indisponible — trafic insuffisant pour un enregistrement CrUX publié "
              "(résultat honnête, pas une erreur du script)")
    else:
        message = (corps.get("error", {}).get("message") if isinstance(corps, dict)
                   else str(corps))
        print(f"ÉCHEC : HTTP {code} — {message}")
        return 1

    cible_fichier = dossier / f"crux-{nom_fichier(args.url)}-{aujourdhui}.json"
    cible_fichier.write_text(
        json.dumps(resultat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"écrit : {cible_fichier.relative_to(Path(args.projet).resolve())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
