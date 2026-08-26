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
import json
import re
import sys
from pathlib import Path

from gabarits import (
    SOUS_DOSSIERS_DONNEES,
    VERSION_ETAT,
    VERSION_MANIFESTE,
    front_matter,
    version_snapshot,
)
from crux import noeud_exige_terrain, terrain_disponible
from livrables import compteurs, ids_noeuds, lire_actions, lire_fiches
from schema import valider
from grille import (
    GRILLE,
    NB_BRANCHES,
    NB_NOEUDS,
    RACINE,
    chaine_correspondance,
    lire,
    registre_evolutions,
    version_grille,
)

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

# Verdicts qui AFFIRMENT quelque chose sur l'etat du site (par opposition a
# « non-mesure » et « sans-objet », qui declarent une absence).
VERDICTS_AFFIRMATIFS = {"conforme", "partiel", "non-conforme"}

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


def controler_versions(base: Path) -> tuple[list[str], str]:
    """Versions de schema declarees par l'etude contre celles que la forge produit.

    TF-0028 : sans ce controle, une etude creee par une forge anterieure gardait un
    etat.json ou un snapshot au contrat perime, et RIEN ne le signalait -- ni le
    texte ni le JSON. La derive n'etait visible qu'a l'oeil, en ouvrant trois
    fichiers a la main.
    """
    ecarts: list[str] = []
    resume: list[str] = []

    attendus: list[tuple[str, Path, str]] = [("etat.json", base / "etat.json", VERSION_ETAT)]
    snaps = (
        sorted((base / "livrables").glob("snapshot-*.json"))
        if (base / "livrables").is_dir()
        else []
    )
    if snaps:
        attendus.append((snaps[-1].name, snaps[-1], version_snapshot()))

    for nom, chemin, attendu in attendus:
        if not chemin.exists():
            ecarts.append(f"{nom} : absent")
            continue
        try:
            declare = json.loads(chemin.read_text(encoding="utf-8")).get("schema_version")
        except json.JSONDecodeError as e:
            ecarts.append(f"{nom} : illisible -- {e}")
            continue
        resume.append(f"{nom} {declare}")
        if declare != attendu:
            ecarts.append(
                f"{nom} : schema_version {declare!r}, la forge produit {attendu!r}"
            )
    return ecarts, " · ".join(resume)


def controler_verdicts_de_terrain(base: Path, fiches: list[dict]) -> tuple[list[str], str]:
    """Aucun verdict affirmatif sur un noeud de terrain sans la donnee de terrain.

    TF-0264 : le noeud 31 (Performance) a ete declare CONFORME sur 21 ms de temps
    de reponse serveur median, quand CrUX donnait 1 162 ms de TTFB p75 sur
    utilisateurs reels -- un facteur cinquante, et trois seuils sur quatre
    manques. La grille dit pourtant « données de terrain publiques (CrUX /
    PageSpeed Insights) » : le run s'est rabattu sur ce qu'il avait.

    Le controle ne lit AUCUN identifiant de noeud en dur : il interroge
    `source_requise`, donc il suit la grille si elle evolue. Il regarde ce que
    l'etude CONTIENT, pas comment elle a ete produite -- un verdict pose a la
    main dans une fiche est attrape aussi bien qu'un verdict genere.
    """
    concernes = [n for n in fiches if noeud_exige_terrain(n.get("source_requise"))]
    if not concernes:
        return [], "aucun noeud adosse a des donnees de terrain dans cette grille"

    dispo, resume = terrain_disponible(base)
    if dispo:
        return [], f"{len(concernes)} noeud(s) de terrain — donnee presente : {resume}"

    ecarts = [
        f"noeud {n['id']} ({n['noeud']}) : verdict « {n.get('verdict')} » rendu sans "
        f"donnee de terrain — {resume}. Attendu : « non-mesure ». Aucune mesure de "
        "laboratoire ne se substitue au terrain, elles ne portent pas sur la meme "
        "grandeur (TF-0264)."
        for n in concernes if n.get("verdict") in VERDICTS_AFFIRMATIFS
    ]
    return ecarts, (
        f"{len(concernes)} noeud(s) de terrain, aucune donnee ({resume}) — "
        f"{len(ecarts)} verdict(s) affirmatif(s) indu(s)"
    )


# TF-0636 (26/08/2026, lot Produit-02 20260825c) — LA PRESENCE N'EST PAS L'EXACTITUDE.
#
# LE FAIT. Le noeud « Acces & Directives IA » pose DEUX questions : les agents peuvent-ils acceder
# au site, et les directives sont-elles POSEES ? Son constat sur un projet reel portait entierement
# sur la premiere : « le serveur repond HTTP 200 et 17 421 octets a l'identique a un navigateur, a
# GPTBot, a ClaudeBot et a PerplexityBot ». Exact, verifiable, et sans aucun rapport avec ce que le
# fichier DIT.
#
# MESURE QUI L'ETABLIT : la chaine « llms » n'apparaissait que DEUX FOIS dans tout le code Python
# de cette forge, jamais pour en lire le contenu. Un llms.txt annoncant des tarifs perimes, des
# capacites fausses ou des URLs mortes passait donc le noeud sans une remarque.
#
# POURQUOI CE FICHIER PLUS QU'UN AUTRE : il existe pour etre repris SANS verification par des
# modeles de langue. Une erreur y porte plus loin qu'ailleurs — elle est recopiee, pas lue.
#
# MEME DOCTRINE QUE LES CONTROLES 9 ET 10 : aucun identifiant de noeud en dur. Le predicat
# interroge `source_requise`, donc il suit la grille si elle evolue.
#
# LA BORNE, et elle evite le faux positif evident : un constat qui declare le fichier ABSENT n'a
# aucun contenu a citer. L'exiger de lui reviendrait a punir la seule reponse honnete.
FICHIER_DIRECTIVES = "llms.txt"
#: Ce qui prouve qu'on a LU : une citation, ou un denombrement de ce que le fichier porte.
_LU = re.compile(
    r"«[^»]{3,}»|`[^`]{3,}`|\b\d+\s*(?:URL|lien|entr[ée]e|section|ligne|item|rubrique)s?\b",
    re.IGNORECASE,
)
#: Ce qui dit qu'il n'y a rien a lire — la seule reponse honnete quand le fichier n'existe pas.
_ABSENT = re.compile(r"\b(absent|introuvable|n\'existe pas|404|non servi|aucun llms)\b", re.IGNORECASE)


def _constat_de(base: Path, chemin_noeud: str) -> str:
    """Le corps « ## Constat » d'une fiche, ou une chaine vide. Ne leve jamais."""
    f = base / "analyse" / chemin_noeud / "_fiche.md"
    try:
        corps = f.read_text(encoding="utf-8").split("\n---\n", 1)[-1]
    except OSError:
        return ""
    bloc = corps.split("## Constat", 1)
    if len(bloc) < 2:
        return ""
    return bloc[1].split("## Interpretation", 1)[0].split("## Preuves", 1)[0]


def controler_directives_ia(base: Path, fiches: list[dict]) -> tuple[list[str], str]:
    """Un verdict affirmatif sur un noeud de directives IA a LU le fichier, pas seulement atteint.

    Le controle ne se declenche que si le constat PARLE du fichier : un noeud rendu non-conforme
    parce que `robots.txt` bloque un agent n'a rien a dire de `llms.txt`, et l'accuser serait
    inventer une exigence que la grille ne porte pas.
    """
    concernes = [n for n in fiches
                 if FICHIER_DIRECTIVES in (n.get("source_requise") or "").lower()]
    if not concernes:
        return [], "aucun noeud de directives IA dans cette grille"

    ecarts = []
    examines = 0
    for n in concernes:
        if n.get("verdict") not in VERDICTS_AFFIRMATIFS:
            continue
        constat = _constat_de(base, n.get("chemin", ""))
        if FICHIER_DIRECTIVES not in constat.lower():
            continue
        examines += 1
        if _ABSENT.search(constat) or _LU.search(constat):
            continue
        ecarts.append(
            f"noeud {n['id']} ({n['noeud']}) : verdict « {n.get('verdict')} » rendu sur "
            f"{FICHIER_DIRECTIVES} sans qu'aucune trace de LECTURE du contenu figure au constat — "
            "ni citation, ni denombrement de ce qu'il porte. Repondre HTTP 200 a un agent prouve "
            "l'ACCES, jamais l'EXACTITUDE : un fichier annoncant des tarifs perimes ou des URLs "
            "mortes repond 200 comme un autre, et il existe pour etre repris SANS verification "
            "par des modeles de langue (TF-0636)."
        )
    if not examines:
        return [], (f"{len(concernes)} noeud(s) de directives IA — aucun verdict affirmatif "
                    f"parlant de {FICHIER_DIRECTIVES}, rien a corroborer")
    return ecarts, (f"{examines} verdict(s) affirmatif(s) parlant de {FICHIER_DIRECTIVES} — "
                    f"{len(ecarts)} sans trace de lecture du contenu")


# TF-0476 (23/08/2026) — LES CHAMPS D'UN PLAN DE MESURE. Ce ne sont pas des metadonnees de
# confort : ce sont les quatre facteurs dont la litterature 2026 mesure qu'ils DOMINENT le
# resultat. Decomposition de variance par REML sur 12 933 reponses (arXiv 2607.13304) : la
# LANGUE de la requete explique 26,5 % de la variance, l'identite de la marque 1,5 % (ICC
# 0,0146), et sur le sous-ensemble de stabilite le REECHANTILLONNAGE pur pese 34,8 %. Fragilite
# a la paraphrase (arXiv 2605.27440) : l'hypothese produit des outils du marche — « le prompt de
# suivi represente l'intention d'achat sous-jacente » — est testee et INVALIDEE.
# Autrement dit : sans ces quatre declarations, le chiffre publie est domine par des facteurs qui
# ne sont pas la marque.
# Cles PLATES : le front-matter de ce depot l'est par choix (« le rester est un controle en
# soi »), et un bloc imbriquerait ses enfants comme des cles de premier niveau.
CHAMPS_PLAN = ("plan_formulations", "plan_langues", "plan_surfaces", "plan_reexecutions")
VIDES = {"", "null", "none", "~", "-", "0"}


def noeud_non_reproductible(reserve: str | None) -> bool:
    """La grille declare-t-elle elle-meme le resultat de ce noeud non reproductible ?

    MEME DOCTRINE QUE `noeud_exige_terrain`, et pour la meme raison : aucun identifiant de noeud
    en dur. Le predicat interroge la RESERVE portee par la grille, donc il suit la grille si elle
    evolue. Le controle de TF-0264 disait deja cela de lui-meme — et il ne le tenait pas : son
    predicat etait le mot litteral « crux », une seule FAMILLE DE SOURCE. Mesure du 19/08 :
    `noeud_exige_terrain()` rend True sur la source du noeud 31 et False sur celle du noeud 57,
    qui est pourtant son frere de classe — un verdict affirmatif rendu sur une grandeur que la
    source ne porte pas. Ici, le predicat lit une phrase que la grille ECRIT.
    """
    return "non reproductible" in (reserve or "").lower()


def controler_plan_de_mesure(base: Path, fiches: list[dict]) -> tuple[list[str], str]:
    """Un taux publie sur un noeud NON REPRODUCTIBLE porte son plan de mesure et sa dispersion.

    Trois invariants, et le troisieme est celui qui protege du pire usage :
      I1 un releve sans plan declare (formulations, langues, surfaces, reexecutions) n'est pas
         publiable comme constat — le verdict attendu est « non-mesure » motive, exactement ce
         que la grille fait deja quand la donnee de terrain manque ;
      I2 un taux publie porte sa DISPERSION, ou ce n'est pas un taux : un chiffre nu est refuse ;
      I3 une seule reexecution ne fait pas un plan. C'est le point ou le service de runs
         recurrents fabriquerait une TENDANCE a partir de bruit — sur une grandeur dont la
         marque explique 1,5 % de la variance.

    ANTI-FAUX-POSITIF, et il est aussi important que le controle : une fiche declaree
    NON MESURABLE (hors perimetre, acces absent, verdict « non-mesure ») passe. L'exigence ne
    doit pas transformer une absence legitime en echec — sinon elle apprend a etre contournee.
    """
    concernes = [n for n in fiches if noeud_non_reproductible(n.get("reserve"))]
    if not concernes:
        return [], "aucun noeud declare non reproductible par la grille"

    ecarts: list[str] = []
    for n in concernes:
        if n.get("verdict") not in VERDICTS_AFFIRMATIFS:
            continue  # non-mesure, hors perimetre, vide : rien a exiger d'une absence assumee
        manquants = [
            c for c in CHAMPS_PLAN
            if str(n.get(c) or "").strip().strip('"').lower() in VIDES
        ]
        if manquants:
            ecarts.append(
                f"noeud {n['id']} ({n['noeud']}) : verdict « {n.get('verdict')} » rendu sans "
                f"plan de mesure — manque {', '.join(manquants)}. La grille declare ce resultat "
                "NON REPRODUCTIBLE ; sans le plan, le chiffre est domine par la langue de la "
                "requete (26,5 % de la variance mesuree) et le reechantillonnage (34,8 %), pas "
                "par la marque (1,5 %). Attendu : « non-mesure » motive, ou le plan declare."
            )
            continue
        try:
            reexecutions = int(str(n.get("plan_reexecutions")).strip().strip('"'))
        except (TypeError, ValueError):
            reexecutions = 0
        if reexecutions < 2:
            ecarts.append(
                f"noeud {n['id']} ({n['noeud']}) : plan declare avec {reexecutions or 'aucune'} "
                "reexecution — une seule execution n'est pas un plan, c'est un tirage. Deux "
                "runs successifs deviendraient une TENDANCE construite sur du bruit."
            )
        if str(n.get("dispersion") or "").strip().strip('"').lower() in VIDES:
            ecarts.append(
                f"noeud {n['id']} ({n['noeud']}) : taux publie SANS DISPERSION — un chiffre nu "
                "n'est pas un taux. Declarer l'ecart entre reexecutions (min-max, ecart-type), "
                "sinon le lecteur croit lire une mesure la ou il lit un tirage."
            )
    return ecarts, (
        f"{len(concernes)} noeud(s) declare(s) non reproductible(s) par la grille — "
        f"{len(ecarts)} ecart(s) de plan de mesure"
    )


def controler_actions(base: Path, ids_grille: set[int]) -> tuple[list[str], str]:
    """Coherence referentielle entre actions-*.csv et la grille.

    TF-0056 : rien ne reliait le CSV d'actions au manifeste. Une action pouvait
    citer un noeud inexistant -- 92 sur une grille qui s'arrete a 87, ou un
    identifiant herite d'une grille anterieure -- et le rapport se contentait de
    ne rien rattacher : « Nœuds couverts : — », branche « — », sans une erreur.
    Deux regles, parce qu'une seule laisse passer l'autre panne :

      a) tout identifiant cite existe dans le manifeste ;
      b) le taux de rattachement effectif est non nul sur un CSV non vide.

    (b) attrape le cas ou aucun identifiant n'est cite du tout -- colonne absente,
    mal orthographiee, ou vide sur toutes les lignes. (a) seule serait alors verte
    sur un rattachement integralement nul.
    """
    livrables = base / "livrables"
    csvs = sorted(livrables.glob("actions-*.csv")) if livrables.is_dir() else []
    if not csvs:
        return [], "aucun fichier d'actions — rien a rattacher"

    cible = csvs[-1]
    try:
        lignes = lire_actions(cible)
    except SystemExit as e:
        return [f"{cible.name} : illisible -- {str(e).splitlines()[0]}"], cible.name
    except OSError as e:
        return [f"{cible.name} : illisible -- {e}"], cible.name

    lignes = [l for l in lignes if any((v or "").strip() for v in l.values())]
    if not lignes:
        return [], f"{cible.name} — en-tete seul, aucune action a rattacher"

    ecarts: list[str] = []
    rattachees = 0
    couverts: set[int] = set()
    for ligne in lignes:
        ids = ids_noeuds(ligne.get("noeuds_couverts"))
        connus = [i for i in ids if i in ids_grille]
        inconnus = [i for i in ids if i not in ids_grille]
        if inconnus:
            ecarts.append(
                f"{cible.name} : action {ligne.get('id') or '?'} cite "
                f"{inconnus} — absent(s) du manifeste"
            )
        if connus:
            rattachees += 1
            couverts.update(connus)

    taux = rattachees / len(lignes)
    if not rattachees:
        ecarts.append(
            f"{cible.name} : aucune des {len(lignes)} action(s) n'est rattachee a un "
            "noeud de la grille — colonne noeuds_couverts absente, mal orthographiee "
            "ou vide"
        )

    resume = (
        f"{cible.name} — {rattachees}/{len(lignes)} action(s) rattachee(s) "
        f"({taux:.0%}), {len(couverts)} noeud(s) distinct(s) couvert(s)"
    )
    return ecarts, resume


# ------------------------------------------------------- referentiel canonique


def controler_synthese_grille(chemin: Path | None = None) -> tuple[list[str], str]:
    """Les tables de synthese de la grille confrontees a la grille elle-meme.

    Trois tables, trois axes : par BRANCHE (compte et plage d'identifiants), par STATUT
    d'instrumentation, par VOLET. Chacune se recalcule depuis le manifeste, qui est la
    projection machine de la grille — on ne compare donc pas la grille a une seconde
    declaration, on la compare a elle-meme.

    Ne juge que ce qui est ECRIT : une table absente n'est pas un ecart. Ajouter un axe de
    synthese ne demande rien ici tant qu'il n'est pas nomme.
    """
    texte = (chemin or GRILLE).read_text(encoding="utf-8")
    noeuds = json.loads((SEO / "manifest.json").read_text(encoding="utf-8"))["noeuds"]

    par_branche: dict[str, list[int]] = {}
    par_statut: dict[str, int] = {}
    par_volet: dict[str, int] = {}
    for n in noeuds:
        par_branche.setdefault(n["branche"], []).append(n["id"])
        par_statut[(n.get("statut") or "?").strip("`").split()[0].strip("`")] = (
            par_statut.get((n.get("statut") or "?").strip("`").split()[0].strip("`"), 0) + 1
        )
        par_volet[n.get("volet") or "?"] = par_volet.get(n.get("volet") or "?", 0) + 1

    ecarts: list[str] = []
    lues = 0

    # Les lignes de table, quelle que soit leur mise en gras : `| Nom | 5 | 59-63 |`.
    ligne_plage = re.compile(
        r"^\|\s*\*{0,2}`?([^|`*]+?)`?\*{0,2}\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|\s*\*{0,2}(\d+)-(\d+)\*{0,2}\s*\|",
        re.MULTILINE,
    )
    sans_accent = lambda x: (x or "").strip().upper().replace("É", "E").replace("È", "E").replace("Ê", "E")
    branches = {sans_accent(b): ids for b, ids in par_branche.items()}
    for nom, compte, debut, fin in ligne_plage.findall(texte):
        ids = branches.get(sans_accent(nom))
        if ids is None:
            continue
        lues += 1
        attendu = (len(ids), min(ids), max(ids))
        vu = (int(compte), int(debut), int(fin))
        if vu != attendu:
            ecarts.append(
                f"table par branche, « {nom.strip()} » : la synthese dit {vu[0]} noeud(s) {vu[1]}-{vu[2]}, "
                f"la grille porte {attendu[0]} noeud(s) {attendu[1]}-{attendu[2]}"
            )

    # Les totaux : tout `| **Total** | **N** |` doit valoir le nombre reel de noeuds.
    for total in re.findall(r"^\|\s*\*{0,2}Total\*{0,2}\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|", texte, re.MULTILINE):
        lues += 1
        if int(total) != len(noeuds):
            ecarts.append(
                f"un total de synthese annonce {total} noeud(s), la grille en porte {len(noeuds)}"
            )

    # Les comptes par statut et par volet, sur les lignes a deux colonnes chiffrees.
    for cle, reels in (("statut", par_statut), ("volet", par_volet)):
        for nom, compte in re.findall(
            r"^\|\s*`?([A-Z]{2,12})`?[^|]*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|", texte, re.MULTILINE
        ):
            attendu = reels.get(nom)
            if attendu is None:
                continue
            lues += 1
            if int(compte) != attendu:
                ecarts.append(
                    f"table par {cle}, « {nom} » : la synthese dit {compte}, la grille porte {attendu}"
                )

    if not lues:
        return [], "aucune table de synthese chiffree dans la grille — rien a confronter"
    return ecarts, f"{lues} ligne(s) de synthese confrontee(s) a la grille — {len(ecarts)} ecart(s)"


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

    # 11 -- le manifeste declare la version que scaffold.py produit aujourd'hui.
    # Un manifeste regenere par une forge plus recente et laisse en place porterait
    # une structure nouvelle sous un numero ancien : indetectable sans ce controle.
    v_manifeste = manifeste.get("schema_version")
    r.controle(
        "11. versions de schema declarees a la source unique",
        v_manifeste == VERSION_MANIFESTE,
        f"manifest.json {v_manifeste} · snapshot.schema.json {version_snapshot()}"
        + ("" if v_manifeste == VERSION_MANIFESTE
           else f" -- scaffold.py produit {VERSION_MANIFESTE}"),
    )

    # 12 -- une grille qui evolue sans sa table de correspondance reassigne les
    # constats des etudes deja ouvertes. Le registre doit suivre la grille : ce
    # controle rend impossible de modifier l'une sans declarer l'autre.
    reg = registre_evolutions()
    courante, reelle = reg.get("version_courante"), version_grille()
    r.controle(
        "12. registre d'evolutions a jour de la grille",
        courante == reelle,
        f"registre {courante} · grille {reelle} · "
        f"{len(reg.get('evolutions', []))} evolution(s) declaree(s)"
        + ("" if courante == reelle else
           " -- la grille a change sans table de correspondance : ajouter l'evolution "
           "dans referentiel/correspondances-grille.json et y porter version_courante"),
    )

    # TF-0653 (26/08/2026) — LA GRILLE ET SA PROPRE SYNTHESE.
    #
    # LE FAIT, mesure : les TROIS tables de synthese de `grille-noeuds.md` annoncaient « Total 87 »
    # pour 88 noeuds, et depuis QUINZE JOURS. La table par branche faisait chevaucher GEO 53-58 et
    # Local 58-62, et sautait le 73 ; celle par statut comptait SD 53 pour 54 ; celle par volet
    # TRANSVERSAL 51 pour 52.
    #
    # LA CAUSE N'EST PAS UNE ETOURDERIE, c'est un trou de contrat. L'insertion du noeud 58 le 11/08
    # a bien produit sa table de CORRESPONDANCE — 30 identifiants decales, tous declares, comme le
    # registre l'exige. Le registre exige une correspondance ; il n'exigeait RIEN de la synthese
    # lisible. Le controle 12 verifiait donc scrupuleusement une moitie du document.
    #
    # CE QUE CA COUTAIT, et ce n'est pas cosmetique : ces tables sont ce qu'on LIT pour planifier
    # une evolution — « ou inserer un noeud, quels identifiants bougent ». Planifier contre une
    # carte fausse produit une renumerotation fausse, et une renumerotation fausse fait pointer
    # chaque constat d'une etude ouverte sur un autre noeud que celui mesure. C'est exactement le
    # defaut fondateur que ce registre existe pour empecher.
    ecarts_s, resume_s = controler_synthese_grille()
    r.controle(
        "13. les tables de synthese disent ce que la grille porte",
        not ecarts_s,
        resume_s,
        ecarts_s[:6],
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
        actuelle = version_grille()
        declaree = prov.get("version_grille")
        # TF-0048 : une grille qui a evolue ne condamne plus l'etude -- a condition
        # qu'une table de correspondance dise comment ses identifiants se
        # transposent. Sans table, on refuse : laisser passer, c'est laisser les
        # constats designer d'autres noeuds que ceux mesures, sans un mot.
        chaine = chaine_correspondance(declaree or "", actuelle)
        lignes = []
        if chaine is None:
            detail = (
                f"etude {declaree} vs forge {actuelle} -- la grille a evolue et AUCUNE "
                "table de correspondance ne relie les deux"
            )
            lignes = [
                "Ajouter l'evolution dans referentiel/correspondances-grille.json "
                "(de, vers, correspondances ancien_id -> nouvel_id).",
            ]
        elif chaine:
            detail = (
                f"etude {declaree} vs forge {actuelle} -- {len(chaine)} table(s) de "
                "correspondance applicable(s), migration non appliquee : "
                + " puis ".join(e.get("motif", "?") for e in chaine)
            )
        else:
            detail = f"etude {declaree} vs forge {actuelle}"
        r.controle(
            "4. version de grille alignee sur la forge, ou transposable",
            chaine is not None,
            detail,
            lignes,
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

    # 7 -- les contrats sous lesquels l'etude a ete produite sont ceux de la forge
    ecarts_v, resume_v = controler_versions(base)
    r.controle(
        "7. versions de schema de l'etude alignees sur la forge",
        not ecarts_v,
        resume_v or "aucun artefact versionne",
        ecarts_v[:5],
    )

    # 8 -- les actions citent des noeuds qui existent, et elles en citent
    ecarts_a, resume_a = controler_actions(base, {n["id"] for n in donnees["noeuds"]})
    r.controle(
        "8. actions-*.csv rattachees a la grille",
        not ecarts_a,
        resume_a,
        ecarts_a[:5],
    )

    # 9 -- aucun verdict de conformite rendu sur la mauvaise grandeur (TF-0264)
    ecarts_t, resume_t = controler_verdicts_de_terrain(base, lire_fiches(base))
    r.controle(
        "9. verdicts de terrain adosses a des donnees de terrain",
        not ecarts_t,
        resume_t,
        ecarts_t[:5],
    )

    # TF-0476 : le frere non couvert du controle 9. Meme classe de defaut — un verdict affirmatif
    # rendu sur une grandeur que la source ne porte pas — autre source. Le controle 9 suivait une
    # seule FAMILLE de source (« crux ») en croyant suivre la grille ; celui-ci suit la reserve
    # que la grille ECRIT.
    ecarts_p, resume_p = controler_plan_de_mesure(base, lire_fiches(base))
    r.controle(
        "10. taux non reproductible adosse a un plan de mesure declare",
        not ecarts_p,
        resume_p,
        ecarts_p[:5],
    )

    # TF-0636 : le TROISIEME frere des controles 9 et 10, sur un objet de plus. Le 9 refuse un
    # verdict affirmatif sans la DONNEE DE TERRAIN, le 10 sans le PLAN DE MESURE ; celui-ci le
    # refuse sans la trace d'une LECTURE du fichier de directives. Meme doctrine dans les trois :
    # le predicat interroge ce que la grille ECRIT (`source_requise`), jamais un identifiant de
    # noeud en dur, donc il suit la grille si elle evolue.
    ecarts_d, resume_d = controler_directives_ia(base, lire_fiches(base))
    r.controle(
        "11. verdict sur les directives IA adosse a une LECTURE du fichier",
        not ecarts_d,
        resume_d,
        ecarts_d[:5],
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
