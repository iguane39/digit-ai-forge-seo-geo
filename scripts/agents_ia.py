"""Ventilation du trafic par agent IA nomme, pour les noeuds 29 et 58 (TF-0105).

Les deux noeuds citent le trafic des agents IA sans l'outiller : le 29 (Logs
Serveur) reste `NM` faute d'analyse des logs, le 58 (Acces & Directives IA) ne
verifie que `robots.txt`/`llms.txt` sans jamais confronter au trafic REEL --
un agent AUTORISE par `robots.txt` peut rester bloque en amont par un WAF/CDN,
et rien ne le montrerait. Ce script lit des logs serveur au format Combined
Log Format (Apache/Nginx, le plus repandu) deja deposes par la mission dans
`donnees/logs/`, et compte les hits par agent IA NOMME -- catalogue tenu en
donnee dans `referentiel/agents-ia.json`, jamais en dur ici (une donnee
volatile est une donnee, pas du code : la liste des agents IA change plus vite
que ce fichier).

Usage :
    python scripts/agents_ia.py --projet . --logs seo/donnees/logs/access.log
    python scripts/agents_ia.py --projet . --logs a.log --logs b.log.gz

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
from pathlib import Path

from grille import RACINE

CATALOGUE = RACINE / "referentiel" / "agents-ia.json"

# Combined Log Format : IP - user [date] "METHODE chemin protocole" code taille "referer" "user-agent"
RE_COMBINED = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<date>[^\]]+)\] '
    r'"(?P<methode>[A-Z]+) (?P<chemin>\S+)[^"]*" '
    r'(?P<code>\d{3}) (?P<taille>\S+) "(?P<referer>[^"]*)" "(?P<ua>[^"]*)"'
)

SEUIL_BLOCAGE = 0.5  # heuristique, pas un seuil du referentiel : signale, ne conclut pas seul


def charger_catalogue() -> list[dict]:
    if not CATALOGUE.exists():
        raise SystemExit(
            f"REFUS : {CATALOGUE} absent -- catalogue des agents IA introuvable. "
            "Le maintenir en donnee, pas en dur dans ce script."
        )
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))["agents"]


def identifier_agent(user_agent: str, catalogue: list[dict]) -> str | None:
    """Premier agent du catalogue dont le motif figure dans le user-agent brut.

    Les UA d'agents IA sont explicites par construction (auto-declaration,
    condition de leur acceptation par les editeurs de sites) : une simple
    sous-chaine suffit, pas de heuristique floue qui se tromperait en silence.
    """
    for a in catalogue:
        if a["motif_ua"].lower() in user_agent.lower():
            return a["agent"]
    return None


def lire_lignes(chemin: Path):
    ouvreur = gzip.open if chemin.suffix == ".gz" else open
    with ouvreur(chemin, "rt", encoding="utf-8", errors="replace") as f:
        for ligne in f:
            yield ligne.rstrip("\n")


def ventiler(fichiers: list[Path], catalogue: list[dict]) -> dict:
    par_nom = {a["agent"]: a for a in catalogue}
    stats: dict[str, dict] = {}
    lues, reconnues = 0, 0
    exemples_ignorees: list[str] = []

    for chemin in fichiers:
        for ligne in lire_lignes(chemin):
            if not ligne.strip():
                continue
            lues += 1
            m = RE_COMBINED.match(ligne)
            if not m:
                if len(exemples_ignorees) < 3:
                    exemples_ignorees.append(ligne[:200])
                continue
            reconnues += 1
            agent = identifier_agent(m.group("ua"), catalogue)
            if agent is None:
                continue
            code = int(m.group("code"))
            s = stats.setdefault(agent, {"hits": 0, "codes_http": {}, "chemins": {}})
            s["hits"] += 1
            s["codes_http"][str(code)] = s["codes_http"].get(str(code), 0) + 1
            chemin_url = m.group("chemin")
            s["chemins"][chemin_url] = s["chemins"].get(chemin_url, 0) + 1

    par_agent = {}
    par_categorie: dict[str, int] = {}
    agents_bloques_probable = []
    for agent, s in stats.items():
        total = s["hits"]
        non_succes = sum(n for code, n in s["codes_http"].items() if not code.startswith(("2", "3")))
        taux_non_succes = round(non_succes / total, 3) if total else 0.0
        top_chemins = sorted(s["chemins"].items(), key=lambda kv: -kv[1])[:10]
        cat = par_nom[agent]["categorie"]
        par_categorie[cat] = par_categorie.get(cat, 0) + total
        par_agent[agent] = {
            "editeur": par_nom[agent]["editeur"],
            "categorie": cat,
            "hits": total,
            "codes_http": dict(sorted(s["codes_http"].items())),
            "taux_reponses_non_succes": taux_non_succes,
            "top_chemins": [{"chemin": c, "hits": n} for c, n in top_chemins],
        }
        if taux_non_succes > SEUIL_BLOCAGE:
            agents_bloques_probable.append(agent)

    hits_total_ia = sum(a["hits"] for a in par_agent.values())
    return {
        "lignes_lues": lues,
        "lignes_reconnues_format": reconnues,
        "lignes_ignorees": lues - reconnues,
        "exemples_lignes_ignorees": exemples_ignorees,
        "hits_agents_ia": hits_total_ia,
        "par_agent": dict(sorted(par_agent.items(), key=lambda kv: -kv[1]["hits"])),
        "par_categorie": par_categorie,
        "agents_probablement_bloques": agents_bloques_probable,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Ventile les hits de logs serveur par agent IA nomme (noeuds 29/58)."
    )
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument(
        "--logs", action="append", required=True,
        help="fichier de log au format Combined Log Format (repetable ; .gz accepte)",
    )
    args = p.parse_args()

    base = Path(args.projet).resolve() / "seo" / "donnees" / "logs"
    if not base.parent.parent.is_dir():
        print(f"{base.parent.parent} absent — créer l'étude avec new_mission.py")
        return 1
    base.mkdir(parents=True, exist_ok=True)

    fichiers = [Path(f) for f in args.logs]
    manquants = [str(f) for f in fichiers if not f.exists()]
    if manquants:
        print(f"REFUS : fichier(s) de log introuvable(s) : {manquants}")
        return 1

    catalogue = charger_catalogue()
    print(f"agents IA connus : {len(catalogue)} (referentiel/agents-ia.json, "
          f"verifie {json.loads(CATALOGUE.read_text(encoding='utf-8'))['date_verification']})")

    resultat = ventiler(fichiers, catalogue)
    aujourdhui = dt.date.today().isoformat()
    sortie = {
        "collecte": {
            "outil": "forge-seo/agents_ia.py",
            "date": aujourdhui,
            "fichiers_logs": [str(f) for f in fichiers],
            "format_attendu": (
                'Combined Log Format : IP - user [date] "METHODE chemin proto" '
                'code taille "referer" "user-agent"'
            ),
            "catalogue_agents": {
                "chemin": "referentiel/agents-ia.json",
                "version": json.loads(CATALOGUE.read_text(encoding="utf-8"))["version"],
            },
            "limite": (
                "Ventilation par sous-chaine de user-agent : couvre les agents IA qui "
                "s'auto-declarent (condition de leur acceptation par les editeurs de "
                "sites). Un agent usurpant un autre UA n'est pas detecte -- hors "
                "perimetre de ce script, relever du 27/58 (WAF/CDN)."
            ),
            "lignes_lues": resultat["lignes_lues"],
            "lignes_reconnues_format": resultat["lignes_reconnues_format"],
            "lignes_ignorees": resultat["lignes_ignorees"],
            "exemples_lignes_ignorees": resultat["exemples_lignes_ignorees"],
        },
        "synthese": {
            "hits_agents_ia": resultat["hits_agents_ia"],
            "par_categorie": resultat["par_categorie"],
            "agents_probablement_bloques": resultat["agents_probablement_bloques"],
            "note_blocage": (
                f"heuristique : plus de {int(SEUIL_BLOCAGE * 100)} % de reponses hors "
                "2xx/3xx sur l'agent -- a verifier a la main, pas une conclusion "
                "automatique (nœud 58)."
            ),
        },
        "par_agent": resultat["par_agent"],
    }

    cible = base / f"agents-ia-{aujourdhui}.json"
    cible.write_text(json.dumps(sortie, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"lignes lues        : {resultat['lignes_lues']} "
          f"({resultat['lignes_reconnues_format']} reconnues, "
          f"{resultat['lignes_ignorees']} ignorees)")
    print(f"hits agents IA     : {resultat['hits_agents_ia']}")
    for agent, d in resultat["par_agent"].items():
        print(f"  {agent:<20} {d['hits']:>7} hits · {d['categorie']:<11} · "
              f"{d['taux_reponses_non_succes']:.0%} hors 2xx/3xx")
    if resultat["agents_probablement_bloques"]:
        print(f"ATTENTION : blocage probable — {resultat['agents_probablement_bloques']}")
    print(f"écrit : {cible.relative_to(Path(args.projet).resolve())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
