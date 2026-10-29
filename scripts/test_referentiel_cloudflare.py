"""Preuve a double sens du referentiel Cloudflare (TF-1997).

Le referentiel est une donnee perissable (loi 4 de la Factory). Il ne vaut que s'il dit
d'ou vient chaque fait, a quelle date la page l'affichait, et a quel noeud de la grille
il s'applique -- par identifiant ET par chemin, parce que les identifiants bougent : le
26/08/2026, l'evolution 6245d81445b9 -> 27e2527398eb a deplace 29 en 30, 31 en 32 et
58 en 59 (referentiel/correspondances-grille.json), et un fichier qui ne citait que
l'identifiant aurait designe un autre noeud sans un mot.

  VERT  : le fichier de la forge tient ces engagements, et la methode le charge.
  ROUGE : copies alterees en memoire -- noeud deplace, source sans date, date
          posterieure a la verification, citation vide, page hors documentation,
          vehicule sans cible_litterale, motif illisible, identifiant en double,
          vehicule requis absent, reglage sans noeud, methode qui ne le cite plus --
          toutes refusees pour la bonne raison.

Ce test ne relit pas les pages : la conformite verbatim des citations a ete
verifiee le jour de la redaction contre les pages telechargees (rapport de TF-1997).

Usage :
    python scripts/test_referentiel_cloudflare.py
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import re
import sys

from grille import RACINE
from oracle_redirections import REFERENTIEL, charger_referentiel

MANIFESTE = RACINE / "seo" / "manifest.json"
METHODE = RACINE / "referentiel" / "methode.md"
PREFIXE = "https://developers.cloudflare.com/"
VEHICULES_REQUIS = ("page-rules", "single-redirects-joker", "single-redirects-statique",
                    "single-redirects-dynamique", "bulk-redirects", "fichier-redirects")


def sources(noeud, chemin="$"):
    """Toute entree {page, date_affichee, citation} du referentiel, ou qu'elle soit."""
    if isinstance(noeud, dict):
        if "page" in noeud or "citation" in noeud:
            yield chemin, noeud
        for k, v in noeud.items():
            yield from sources(v, f"{chemin}.{k}")
    elif isinstance(noeud, list):
        for i, v in enumerate(noeud):
            yield from sources(v, f"{chemin}[{i}]")


def verifier_referentiel(ref: dict, manifeste: dict) -> list[str]:
    ecarts: list[str] = []
    for cle in ("version", "date_verification", "provenance", "codes_permanents",
                "vehicules_redirection", "reglages"):
        if cle not in ref:
            ecarts.append(f"clé absente : {cle}")
    try:
        verification = dt.date.fromisoformat(ref.get("date_verification") or "")
    except ValueError:
        verification = None
        ecarts.append("date_verification illisible")

    for chemin, s in sources(ref):
        if not str(s.get("page", "")).startswith(PREFIXE):
            ecarts.append(f"{chemin} : page hors de la documentation Cloudflare ({s.get('page')!r})")
        date = s.get("date_affichee")
        if date != "non datée":
            try:
                lue = dt.date.fromisoformat(date or "")
                if verification and lue > verification:
                    ecarts.append(f"{chemin} : date affichée {date} postérieure à la vérification")
            except (TypeError, ValueError):
                ecarts.append(f"{chemin} : date_affichee illisible ({date!r})")
        if not str(s.get("citation") or "").strip():
            ecarts.append(f"{chemin} : citation vide")

    ids: list[str] = []
    for v in ref.get("vehicules_redirection", []):
        ids.append(v.get("id"))
        for cle, attendu in (("cible_litterale", bool), ("references", list), ("sources", list)):
            if not isinstance(v.get(cle), attendu):
                ecarts.append(f"véhicule {v.get('id')} : {cle} absent ou mal typé")
        if not v.get("sources"):
            ecarts.append(f"véhicule {v.get('id')} : aucune source")
        if v.get("code_par_defaut") is not None and v["code_par_defaut"] not in v.get("codes_admis", []):
            ecarts.append(f"véhicule {v.get('id')} : code par défaut hors des codes admis")
        for r in v.get("references", []) if isinstance(v.get("references"), list) else []:
            try:
                re.compile(r["motif"])
            except (re.error, KeyError, TypeError):
                ecarts.append(f"véhicule {v.get('id')} : motif de référence illisible {r!r}")
            if r.get("porte") == "joker" and not r.get("gabarit"):
                ecarts.append(f"véhicule {v.get('id')} : référence de joker sans gabarit d'écriture")

    chemins = {n["id"]: n["chemin"] for n in manifeste["noeuds"]}
    for g in ref.get("reglages", []):
        ids.append(g.get("id"))
        if not g.get("sources"):
            ecarts.append(f"réglage {g.get('id')} : aucune source")
        if not g.get("noeuds"):
            ecarts.append(f"réglage {g.get('id')} : aucun nœud")
        for n in g.get("noeuds", []):
            if chemins.get(n.get("id")) != n.get("chemin"):
                ecarts.append(f"réglage {g.get('id')} : le nœud {n.get('id')} n'est pas {n.get('chemin')} "
                              f"au manifeste (il y est {chemins.get(n.get('id'))!r})")

    doublons = sorted({i for i in ids if ids.count(i) > 1})
    if doublons:
        ecarts.append(f"identifiants en double : {doublons}")
    for requis in VEHICULES_REQUIS:
        if requis not in ids:
            ecarts.append(f"véhicule requis par oracle_redirections.py absent : {requis}")
    return ecarts


def methode_charge_le_referentiel(texte: str) -> bool:
    """La methode le cite dans sa table des references : sinon le referentiel est orphelin."""
    return "| `referentiel/cloudflare.json` |" in texte


def main() -> int:
    ref = charger_referentiel()
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    cas: list[tuple[str, bool, str]] = []

    ecarts = verifier_referentiel(ref, manifeste)
    nb_sources = sum(1 for _ in sources(ref))
    noeuds = sorted({n["id"] for g in ref["reglages"] for n in g["noeuds"]})
    cas.append(("VERT  le referentiel de la forge est date, source et rattache a la grille", not ecarts,
                f"{len(ref['reglages'])} reglages, {len(ref['vehicules_redirection'])} vehicules, "
                f"{nb_sources} sources, noeuds {noeuds} ; ecarts : {ecarts[:3]}"))
    cas.append(("VERT  la methode charge le referentiel (table des references)",
                methode_charge_le_referentiel(METHODE.read_text(encoding="utf-8")), str(METHODE.name)))
    cas.append(("ROUGE une methode qui ne le cite plus est refusee",
                not methode_charge_le_referentiel("| `referentiel/grille-noeuds.md` | toujours |"), ""))

    def altere(nom: str, mutation, attendu: str) -> None:
        copie = copy.deepcopy(ref)
        mutation(copie)
        trouves = verifier_referentiel(copie, manifeste)
        ok = any(attendu in e for e in trouves)
        cas.append((f"ROUGE {nom}", ok, f"attendu « {attendu} », obtenu {trouves[:2]}"))

    def deplacer_noeud(r):
        for g in r["reglages"]:
            for n in g["noeuds"]:
                if n["id"] == 59:
                    n["id"] = 58

    altere("noeud deplace par une evolution de grille (59 lu comme 58)", deplacer_noeud, "n'est pas 11-geo/06-acces")
    altere("source sans date affichee",
           lambda r: r["reglages"][0]["sources"][0].pop("date_affichee"), "date_affichee illisible")
    altere("date affichee posterieure a la verification",
           lambda r: r["reglages"][0]["sources"][0].update(date_affichee="2026-10-30"), "postérieure")
    altere("citation vide", lambda r: r["reglages"][1]["sources"][0].update(citation="  "), "citation vide")
    altere("page hors de la documentation Cloudflare",
           lambda r: r["reglages"][2]["sources"][0].update(page="https://blog.exemple.fr/cloudflare"),
           "hors de la documentation")
    altere("vehicule sans cible_litterale",
           lambda r: r["vehicules_redirection"][0].pop("cible_litterale"), "cible_litterale absent")
    altere("motif de reference illisible",
           lambda r: r["vehicules_redirection"][0]["references"][0].update(motif="\\$("), "motif de référence illisible")
    altere("identifiant en double",
           lambda r: r["reglages"][1].update(id=r["reglages"][0]["id"]), "en double")
    altere("vehicule requis par l'oracle absent",
           lambda r: r.update(vehicules_redirection=[v for v in r["vehicules_redirection"]
                                                     if v["id"] != "bulk-redirects"]), "requis")
    altere("reglage sans noeud", lambda r: r["reglages"][0].update(noeuds=[]), "aucun nœud")

    echecs = 0
    for nom, ok, detail in cas:
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom} -- {detail}" if (detail and (not ok or nom.startswith("VERT")))
              else f"  [{'OK  ' if ok else 'ECHEC'}] {nom}")
        echecs += 0 if ok else 1
    print(f"\nreferentiel : {REFERENTIEL.relative_to(RACINE).as_posix()} (verifie le {ref['date_verification']})")
    if echecs:
        print(f"\nECHECS : {echecs}")
        print(f"{len(cas) - echecs}/{len(cas)} preuves conformes")
        return 1
    print(f"\n{len(cas)}/{len(cas)} preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
