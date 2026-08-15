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

    if not args.cle:
        print(
            "REFUS : aucune cle API CrUX fournie (--cle ou variable d'environnement "
            "CRUX_API_KEY).\n"
            "Sans elle, le noeud 31 (Performance) reste NON MESURE : il se juge sur "
            "des donnees de terrain,\net aucune mesure de laboratoire ne s'y "
            "substitue — le 15/08, 21 ms de mediane serveur\nont valu « conforme » "
            "quand le terrain donnait 1 162 ms de TTFB p75.\n"
            + OBTENIR_LA_CLE
        )
        return 1

    dossier = Path(args.projet).resolve() / "seo" / "donnees" / "performance"
    if not dossier.parent.parent.is_dir():
        print(f"{dossier.parent.parent} absent — créer l'étude avec new_mission.py")
        return 1
    dossier.mkdir(parents=True, exist_ok=True)

    mode = "origin" if args.origine else "url"
    print(f"CrUX : interrogation de {mode}={args.url} ({args.facteur_forme})")
    code, corps = appeler_api(args.cle, args.url, mode, args.facteur_forme)

    aujourdhui = dt.date.today().isoformat()
    resultat = {
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
