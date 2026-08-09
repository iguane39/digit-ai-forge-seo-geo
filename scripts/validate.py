"""Controles durs du referentiel forge-seo.

Neuf controles sur le referentiel canonique. Sortie non-zero des qu'un seul
echoue : ce script existe pour attraper exactement le mode d'echec le plus
dangereux du projet -- une arborescence fausse qui passe au vert.

Usage :
    python scripts/validate.py
    python scripts/validate.py --mission C:/dev/mon-client
    python scripts/validate.py --json            # sortie machine sur stdout

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from gabarits import SOUS_DOSSIERS_DONNEES, front_matter
from livrables import compteurs, lire_fiches
from schema import valider
from grille import GRILLE, NB_BRANCHES, NB_NOEUDS, RACINE, lire

SEO = RACINE / "seo"

RE_SLUG = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")

CHAMPS_FICHE = [
    "id",
    "branche",
    "noeud",
    "volet",
    "statut_instrumentation",
    "source_requise",
    "doublon_de",
    "modeles",
    "etat",
    "motif_hors_perimetre",
    "verdict",
    "niveau_preuve",
    "date_mesure",
    "actions_liees",
]

ETATS = {"a-faire", "en-cours", "fait", "hors-perimetre"}

# Artefacts de mission : leur presence dans la forge signifie qu'une etude
# client s'y est installee, ce que l'architecture interdit.
ARTEFACTS_MISSION = ("donnees", "livrables", "analyse", "cadrage.md", "etat.json")


class Rapport:
    """Accumule les verdicts puis les rend, en texte ou en JSON.

    Les deux sorties viennent des MEMES donnees : un mode qui recalculerait son
    verdict a part finirait par diverger de l'autre, et c'est exactement le genre
    de faux vert que ce script existe pour attraper.
    """

    def __init__(self, cible: str, json_mode: bool = False, projet: str | None = None) -> None:
        self.cible = cible
        self.projet = projet
        self.json_mode = json_mode
        self.echecs: list[str] = []
        self.controles: list[dict] = []
        self.erreur: str | None = None

    def entete(self, titre: str) -> None:
        if not self.json_mode:
            print(titre + "\n")

    def controle(
        self, nom: str, ok: bool, detail: str = "", lignes: list[str] | None = None
    ) -> None:
        lignes = list(lignes or [])
        self.controles.append({"nom": nom, "ok": ok, "detail": detail, "lignes": lignes})
        if not self.json_mode:
            print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom}" + (f" -- {detail}" if detail else ""))
            for msg in lignes:
                print(f"          {msg}")
        if not ok:
            self.echecs.append(nom)

    def abandon(self, message: str, conseils: list[str] | None = None) -> int:
        """Sortie anticipee : rien n'est controlable. Le mode JSON doit quand meme
        rendre un objet, sinon l'appelant machine recoit du vide et croit au vert."""
        self.erreur = message
        if self.json_mode:
            return self.bilan()
        print(f"  {message}")
        for c in conseils or []:
            print(f"  {c}")
        return 1

    def _charge_utile(self) -> dict:
        return {
            "outil": "validate",
            "cible": self.cible,
            "projet": self.projet,
            "verdict": "PASS" if not (self.echecs or self.erreur) else "FAIL",
            "controles_total": len(self.controles),
            "controles_passes": len(self.controles) - len(self.echecs),
            "controles": self.controles,
            "echecs": self.echecs,
            "erreur": self.erreur,
        }

    def bilan(self) -> int:
        if self.json_mode:
            print(json.dumps(self._charge_utile(), indent=2, ensure_ascii=False))
            return 0 if not (self.echecs or self.erreur) else 1
        print(f"\n{len(self.controles) - len(self.echecs)}/{len(self.controles)} controles passes")
        if self.echecs:
            print("ECHECS : " + ", ".join(self.echecs))
            return 1
        return 0


def controler_fiches(base: Path, noeuds: list[dict]) -> list[str]:
    """Presence, validite et coherence du front-matter des 87 fiches."""
    invalides: list[str] = []
    for n in noeuds:
        fiche = base / n["chemin"] / "_fiche.md"
        if not fiche.exists():
            invalides.append(f"{n['chemin']} : fiche absente")
            continue
        try:
            fm = front_matter(fiche)
        except ValueError as e:
            invalides.append(f"{n['chemin']} : {e}")
            continue
        manquants = [c for c in CHAMPS_FICHE if c not in fm]
        if manquants:
            invalides.append(f"{n['chemin']} : champs manquants {manquants}")
        if fm.get("id") != str(n["id"]):
            invalides.append(f"{n['chemin']} : id incoherent")
        if fm.get("volet") != n["volet"]:
            invalides.append(f"{n['chemin']} : volet incoherent")
        if fm.get("etat") not in ETATS:
            invalides.append(f"{n['chemin']} : etat invalide {fm.get('etat')!r}")
    return invalides


# ------------------------------------------------------- referentiel canonique


def valider_referentiel(json_mode: bool = False) -> int:
    r = Rapport("referentiel", json_mode)
    r.entete("validate -- referentiel canonique de la forge")

    if not SEO.exists():
        return r.abandon("seo/ absent. Lancer d'abord : python scripts/scaffold.py")

    donnees = lire()
    manifeste = json.loads((SEO / "manifest.json").read_text(encoding="utf-8"))
    branches = sorted(p for p in SEO.iterdir() if p.is_dir())
    feuilles = sorted(f for b in branches for f in b.iterdir() if f.is_dir())

    r.controle(
        f"1. {NB_BRANCHES} branches, {NB_NOEUDS} feuilles, {NB_BRANCHES + NB_NOEUDS} dossiers sous seo/",
        len(branches) == NB_BRANCHES and len(feuilles) == NB_NOEUDS,
        f"{len(branches)} branches, {len(feuilles)} feuilles, "
        f"{len(branches) + len(feuilles)} au total",
    )

    ids = sorted(n["id"] for n in manifeste["noeuds"])
    r.controle(
        f"2. identifiants 1-{NB_NOEUDS} sans trou ni doublon",
        ids == list(range(1, NB_NOEUDS + 1)),
        f"{len(ids)} identifiants, min {ids[0]}, max {ids[-1]}",
    )

    renvois = [n for n in manifeste["noeuds"] if n["statut"] == "RV"]
    ok, detail = len(renvois) == 2, []
    for n in renvois:
        fiche = SEO / n["chemin"] / "_fiche.md"
        if not fiche.exists():
            ok = False
            detail.append(f"{n['chemin']} sans fiche")
            continue
        fm = front_matter(fiche)
        corps = fiche.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        if n["doublon_de"] is None or fm.get("doublon_de") in (None, "null"):
            ok = False
            detail.append(f"{n['chemin']} sans doublon_de")
        if fm.get("etat") != "hors-perimetre" or "## Constat" in corps:
            ok = False
            detail.append(f"{n['chemin']} a des champs a remplir")
        detail.append(f"{n['chemin']} -> {n['doublon_de']}")
    r.controle(
        "3. les 2 renvois portent doublon_de et n'ont aucun champ a remplir",
        ok,
        " ; ".join(detail),
    )

    rangs = [b["rang"] for b in manifeste["branches"]]
    noms_m = [b["nom"] for b in manifeste["branches"]]
    r.controle(
        "4. ordre des branches conforme a la sequence du schema",
        rangs == list(range(1, NB_BRANCHES + 1))
        and noms_m == [b["nom"] for b in donnees["branches"]],
        f"{noms_m[0]} -> {noms_m[-1]}",
    )

    mauvais = [p.name for p in branches + feuilles if not RE_SLUG.match(p.name)]
    non_ascii = [p.name for p in branches + feuilles if not p.name.isascii()]
    r.controle(
        "5. tous les slugs ASCII kebab-case prefixes numeriquement",
        not mauvais and not non_ascii,
        f"{len(mauvais)} non conforme(s), {len(non_ascii)} non-ASCII"
        if (mauvais or non_ascii)
        else f"{NB_BRANCHES + NB_NOEUDS} slugs conformes",
    )

    champs = (
        "id", "branche", "noeud", "chemin", "volet", "statut",
        "question_audit", "source_requise", "methode", "critere_verdict", "doublon_de",
    )
    par_id = {n["id"]: n for n in manifeste["noeuds"]}
    ecarts = []
    for n in donnees["noeuds"]:
        m = par_id.get(n["id"])
        if m is None:
            ecarts.append(f"noeud {n['id']} absent du manifeste")
            continue
        ecarts += [f"noeud {n['id']}, champ {k}" for k in champs if n[k] != m[k]]
    r.controle(
        "6. aucune derive entre grille-noeuds.md et manifest.json",
        not ecarts,
        f"{len(ecarts)} ecart(s)" if ecarts else f"{NB_NOEUDS} noeuds identiques sur 11 champs",
    )

    invalides = controler_fiches(SEO, manifeste["noeuds"])
    r.controle(
        f"7. les {NB_NOEUDS} fiches ont un front-matter valide et coherent",
        not invalides,
        f"{len(invalides)} fiche(s) invalide(s)"
        if invalides
        else f"{NB_NOEUDS} fiches, {len(CHAMPS_FICHE)} champs types chacune",
        invalides[:5],
    )

    # 8 -- la forge n'heberge aucune etude client
    intrus = [str(p.relative_to(RACINE)) for p in (RACINE / "missions",) if p.exists()]
    intrus += [
        f"seo/{a}" for a in ARTEFACTS_MISSION if (SEO / a).exists()
    ]
    r.controle(
        "8. la forge n'heberge aucune donnee ni livrable client",
        not intrus,
        f"intrus : {intrus}" if intrus else "referentiel vierge, etudes chez les projets",
    )

    # 9 bis -- le schema de snapshot fige un compte de noeuds : il doit suivre.
    sch = json.loads((RACINE / "referentiel" / "snapshot.schema.json").read_text(encoding="utf-8"))
    bornes = sch["properties"]["noeuds"]
    r.controle(
        "9. le schema de snapshot suit le compte de la grille",
        bornes.get("minItems") == bornes.get("maxItems") == NB_NOEUDS,
        f"schema {bornes.get('minItems')}-{bornes.get('maxItems')}, grille {NB_NOEUDS}",
    )

    vides = [
        str(d.relative_to(RACINE))
        for d in SEO.rglob("*")
        if d.is_dir() and not any(d.iterdir())
    ]
    r.controle(
        "10. aucun dossier sans fichier ni .gitkeep",
        not vides,
        f"{len(vides)} dossier(s) vide(s)" if vides else "arborescence survivra au clone",
    )

    return r.bilan()


# ------------------------------------------------------------ mission externe


def valider_mission(projet: Path, json_mode: bool = False) -> int:
    base = projet.resolve() / "seo"
    r = Rapport("mission", json_mode, str(projet.resolve()))
    r.entete(f"validate -- etude SEO de {projet.resolve()}")

    if not base.is_dir():
        return r.abandon(
            f"{base} absent.",
            ["Creer l'etude : python scripts/new_mission.py --projet <chemin> ..."],
        )

    donnees = lire()
    analyse = base / "analyse"

    branches = sorted(p for p in analyse.iterdir() if p.is_dir()) if analyse.is_dir() else []
    feuilles = sorted(f for b in branches for f in b.iterdir() if f.is_dir())
    r.controle(
        f"1. {NB_BRANCHES + NB_NOEUDS} dossiers sous seo/analyse/",
        len(branches) == NB_BRANCHES and len(feuilles) == NB_NOEUDS,
        f"{len(branches)} branches, {len(feuilles)} feuilles",
    )

    attendus = {
        "README.md", "cadrage.md", "etat.json", ".forge-seo.json", ".gitignore",
    }
    manquants = sorted(a for a in attendus if not (base / a).exists())
    manquants += [
        f"donnees/{s}" for s in SOUS_DOSSIERS_DONNEES if not (base / "donnees" / s).is_dir()
    ]
    if not (base / "livrables").is_dir():
        manquants.append("livrables")
    r.controle(
        "2. structure complete (cadrage, etat, donnees, livrables, provenance)",
        not manquants,
        f"manquants : {manquants}" if manquants else "tous les elements presents",
    )

    invalides = controler_fiches(analyse, donnees["noeuds"])
    r.controle(
        f"3. les {NB_NOEUDS} fiches ont un front-matter valide et coherent",
        not invalides,
        f"{len(invalides)} fiche(s) invalide(s)" if invalides else f"{NB_NOEUDS} fiches valides",
        invalides[:5],
    )

    prov_f = base / ".forge-seo.json"
    if prov_f.exists():
        prov = json.loads(prov_f.read_text(encoding="utf-8"))
        actuelle = hashlib.sha256(GRILLE.read_bytes()).hexdigest()[:12]
        a_jour = prov.get("version_grille") == actuelle
        r.controle(
            "4. version de grille alignee sur la forge",
            a_jour,
            f"etude {prov.get('version_grille')} vs forge {actuelle}"
            + ("" if a_jour else " -- la grille a evolue depuis la creation"),
        )
    else:
        r.controle("4. provenance tracee", False, ".forge-seo.json absent")

    etat_f = base / "etat.json"
    if etat_f.exists():
        e = json.loads(etat_f.read_text(encoding="utf-8"))
        # Comparer les compteurs de etat.json a ce que les fiches disent VRAIMENT.
        # L'ancienne version verifiait que le total valait 87 : comme rien ne mettait
        # jamais ces compteurs a jour, il valait toujours 87 et le controle ne pouvait
        # pas echouer. Un faux vert est pire que pas de controle.
        reel = compteurs(lire_fiches(base))
        declare = e.get("noeuds", {})
        ok = all(declare.get(k) == v for k, v in reel.items())
        r.controle(
            "5. compteurs d'avancement conformes aux fiches",
            ok,
            f"{reel['fait']} fait / {reel['en_cours']} en cours / {reel['a_faire']} a faire "
            f"/ {reel['hors_perimetre']} hors perimetre"
            + ("" if ok else f" — etat.json declare {declare}. "
                             "Lancer : python scripts/livrables.py --projet <chemin>"),
        )
    else:
        r.controle("5. etat.json present", False, "absent")

    # 6 -- le snapshot respecte son contrat
    snaps = sorted((base / "livrables").glob("snapshot-*.json")) if (base / "livrables").is_dir() else []
    if not snaps:
        r.controle("6. snapshot conforme au schema", True, "aucun snapshot — rien a valider")
    else:
        sch = json.loads((RACINE / "referentiel" / "snapshot.schema.json").read_text(encoding="utf-8"))
        ecarts = valider(json.loads(snaps[-1].read_text(encoding="utf-8")), sch)
        r.controle(
            "6. snapshot conforme au schema",
            not ecarts,
            f"{snaps[-1].name} — {len(ecarts)} ecart(s)" if ecarts else snaps[-1].name,
            ecarts[:5],
        )

    return r.bilan()


def main() -> int:
    p = argparse.ArgumentParser(description="Controles durs de forge-seo.")
    p.add_argument("--mission", help="chemin d'un projet audite, pour valider son etude")
    p.add_argument(
        "--json",
        action="store_true",
        help="sortie machine sur stdout (verdict, controles, echecs) ; "
        "le texte humain reste le mode par defaut",
    )
    args = p.parse_args()
    if args.mission:
        return valider_mission(Path(args.mission), args.json)
    return valider_referentiel(args.json)


if __name__ == "__main__":
    sys.exit(main())
