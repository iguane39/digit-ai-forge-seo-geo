"""Migre une etude d'une empreinte de grille perimee vers l'empreinte courante.

POURQUOI CE SCRIPT EXISTE

TF-0048 a rendu l'evolution de grille DECLARATIVE : toute renumerotation
d'identifiants entre dans `referentiel/correspondances-grille.json`, et
`validate.py --mission` refuse une etude dont la version de grille ne se relie
pas a celle de la forge. TF-0093 a fait usage du mecanisme -- 87 noeuds -> 88,
30 identifiants decales, un noeud nouveau.

Il manquait la moitie du geste. Le registre dit COMMENT transposer ; rien ne
transposait. Une etude auditee sur l'ancienne grille se retrouvait donc
condamnee : `rapport_html.py` refuse de la restituer (le refus est juste -- un
rapport partiel qui se presente comme complet est pire qu'aucun rapport), et le
seul contournement pratique observe a ete d'epingler un worktree de la forge sur
un ancien commit. Un contournement n'est pas une voie : il fige l'etude sur une
grille morte, et il produit un livrable que la forge courante ne sait plus
reproduire.

Ce script est la voie. Il applique la chaine de correspondances, ajoute les
noeuds nouveaux a l'etat EXPLICITE de non-instruit, deplace l'empreinte de
l'etude, et JOURNALISE l'operation dans l'etude elle-meme.

CE QU'IL NE FAIT PAS

Il n'invente aucun verdict. Un noeud ajoute par une evolution de grille n'a pas
ete mesure sur ce site : il nait `etat: a-faire`, `verdict: null`, exactement
comme le scaffold le produirait. Le rapport le restitue comme non instruit et le
compteur de couverture le compte au denominateur, pas au numerateur. Un audit
qui gagne un noeud PERD un point de couverture -- c'est la verite, et l'afficher
est le seul comportement acceptable.

Il ne reecrit pas la PROSE. Un constat qui cite « nœud 63 » en toutes lettres
dans une justification saisie a la main n'est pas transposable sans jugement :
le script les DETECTE et les signale, il ne les corrige pas. Deviner ici, ce
serait reecrire le texte d'un auditeur.

CE QU'IL TRANSPOSE, ET OU

Les identifiants de noeud vivent a quatre endroits STRUCTURES d'une etude. Les
oublier, c'est laisser un constat designer un autre noeud que celui mesure --
exactement le defaut que TF-0048 nomme :

  1. `analyse/**/_fiche.md`      champ `id` du front-matter
  2. `analyse/*/_branche.md`     tableau de branche (regenere depuis la grille)
  3. `livrables/actions-*.csv`   colonne `noeuds_couverts`
  4. `livrables/snapshot-*.json` `noeuds[].id` et `dette_instrumentation[].noeud_id`

Les livrables (3 et 4) sont COPIES intacts sous `livrables/pre-migration-<de>/`
avant reecriture : ce qui a ete remis au client reste consultable tel quel.

REFUS PLUTOT QUE PERTE

Le script s'arrete -- sans rien ecrire -- des qu'une donnee serait perdue ou
qu'une transposition serait ambigue : aucune chaine de correspondances, table non
injective, identifiant retire par une evolution alors que sa fiche porte du
travail, fiche dont l'identifiant transpose contredit le manifeste courant, fiche
orpheline instruite, ou noeud a creer dont le dossier existe deja.

Usage :
    python scripts/migrer_mission.py --projet C:/dev/mon-client --verifier
    python scripts/migrer_mission.py --projet C:/dev/mon-client

`--verifier` est un blanc : il calcule le plan complet, l'imprime, et n'ecrit
rien. Code de sortie 0 si la migration est possible ou inutile, 1 si elle est
refusee.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

from gabarits import (
    empreinte,
    fiche_branche,
    fiche_noeud,
    front_matter,
    registre_charger,
    registre_ecrire,
)
from grille import (
    NB_NOEUDS,
    RACINE,
    chaine_correspondance,
    lire,
    registre_evolutions,
    version_grille,
)
from livrables import compteurs, ids_noeuds, lire_actions, lire_fiches

MANIFESTE = RACINE / "seo" / "manifest.json"

RE_ID = re.compile(r"^(id:\s*)(\d+)(\s*)$", re.M)
RE_COMMENT = re.compile(r"<!--.*?-->", re.S)

# Citations de noeud en toutes lettres dans de la prose saisie a la main. Le
# script ne corrige PAS ces occurrences -- il les nomme, pour qu'un humain
# tranche.
#
# Pourquoi ne PAS les transposer, alors que la table est sans ambiguite : parce
# que la prose porte des PLAGES. La forge elle-meme a du trancher a la main sur
# le critere du noeud « Machine SEO » -- « justifie par les nœuds 58-62, 63-67 et
# 68-72 » est devenu « 58-62, 64-68 et 69-73 » : la premiere plage n'a PAS bouge,
# parce que le noeud nouveau l'a rejointe par le sens. Aucune table ne dit cela.
# Une plage se rejuge, elle ne se decale pas.
#
# Les numeros nus (« ..., aucune alerte de surveillance (65), ... ») ne sont pas
# cherches du tout : sans le mot, rien ne distingue un identifiant de noeud d'un
# chiffre quelconque, et les chercher au jugé serait l'invention meme que ce
# script refuse. Ils restent donc invisibles a ce controle -- c'est une limite
# connue, pas un oubli.
RE_NOEUD_CITE = re.compile(
    r"n(?:œ|oe)uds?\s+(\d{1,2}(?:\s*(?:[-–—,;/]|et)\s*\d{1,2})*)", re.I
)
RE_PLAGE = re.compile(r"\d\s*[-–—]\s*\d")

CHAMPS_MISSION = ("verdict", "niveau_preuve", "date_mesure", "motif_hors_perimetre")
VIDES = {"", "null", "none", "[]"}


class Refus(RuntimeError):
    """La migration ne peut pas etre faite sans perdre ou inventer. On s'arrete."""


# ------------------------------------------------------------------ lecture


def _texte(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8")


def _ecrire(chemin: Path, texte: str) -> None:
    """Ecrit en CONSERVANT les fins de ligne du fichier remplace.

    Sans cette precaution, changer un caractere dans une fiche CRLF la reecrit
    entiere en LF (ou l'inverse) : le diff montre 60 lignes modifiees la ou une
    seule l'a ete, et la revue humaine de la migration devient impraticable --
    donc n'a pas lieu. Un fichier neuf suit la convention du poste, comme le
    reste de la forge.
    """
    fin = "\n"
    if chemin.exists():
        octets = chemin.read_bytes()
        fin = "\r\n" if b"\r\n" in octets else "\n"
    else:
        fin = os.linesep
    with chemin.open("w", encoding="utf-8", newline=fin) as sortie:
        sortie.write(texte)


def _ecrire_bom(chemin: Path, texte: str) -> None:
    """Meme regle, pour un fichier a BOM (les CSV lus par Excel en portent un)."""
    fin = "\r\n" if chemin.exists() and b"\r\n" in chemin.read_bytes() else "\n"
    with chemin.open("w", encoding="utf-8-sig", newline=fin) as sortie:
        sortie.write(texte)


def _vide(valeur: str | None) -> bool:
    return (valeur or "").strip().strip('"').strip("'").lower() in VIDES


def corps_redige(chemin: Path) -> bool:
    """Vrai si le corps de la fiche porte autre chose que le gabarit.

    Le gabarit ne contient que des titres et des commentaires HTML : toute ligne
    de texte qui survit a leur retrait est du travail d'auditeur.
    """
    parts = _texte(chemin).split("\n---\n", 2)
    if len(parts) < 3:
        # Fiche de renvoi : pas de separateur de corps. On la traite comme
        # portant du travail -- prudence, jamais l'inverse.
        return True
    corps = RE_COMMENT.sub("", parts[2])
    return any(
        ligne.strip() and not ligne.lstrip().startswith(("#", ">"))
        for ligne in corps.split("\n")
    )


def porte_du_travail(chemin: Path) -> bool:
    """Vrai si la fiche a ete instruite, a quelque degre que ce soit."""
    fm = front_matter(chemin)
    if (fm.get("etat") or "a-faire") != "a-faire":
        return True
    if any(not _vide(fm.get(c)) for c in CHAMPS_MISSION):
        return True
    if not _vide(fm.get("actions_liees")):
        return True
    return corps_redige(chemin)


def citations_prose(chemin: Path, table: dict[int, int]) -> list[dict]:
    """Occurrences « nœud N » dont le numero BOUGE, dans un fichier de l'etude.

    Filtrer sur les seuls numeros qui bougent n'est pas de la complaisance : une
    liste de 91 citations dont 80 sont exactes noie les 11 qui sont devenues
    fausses, et un avertissement qu'on ne lit pas ne protege personne.
    """
    sorties = []
    for m in RE_NOEUD_CITE.finditer(_texte(chemin)):
        cites = ids_noeuds(m.group(1))
        bougent = [(i, table.get(i, i)) for i in cites if table.get(i, i) != i]
        if bougent:
            sorties.append({
                "texte": " ".join(m.group(0).split()),
                "bougent": bougent,
                "plage": bool(RE_PLAGE.search(m.group(1))),
            })
    return sorties


# --------------------------------------------------------------- table cumulee


PLAFOND_IDS = 400


def table_cumulee(chaine: list[dict]) -> tuple[dict[int, int], list[int]]:
    """Compose les correspondances des evolutions successives en une seule table.

    Une etude peut avoir saute plusieurs versions : composer, c'est appliquer les
    tables dans l'ordre, chaque sortie devenant l'entree de la suivante. Les
    identifiants nouveaux d'une etape intermediaire suivent eux aussi les
    renumerotations des etapes d'apres, sinon on creerait un noeud a un numero
    qui a deja bouge.

    Le domaine est borne large (PLAFOND_IDS) plutot que sur la grille courante :
    une etude ancienne peut porter des identifiants au-dela du compte du jour, et
    les omettre de la table les laisserait passer inchanges, sans un mot.
    """
    table = {i: i for i in range(1, PLAFOND_IDS + 1)}
    nouveaux: list[int] = []
    for evo in chaine:
        corr = {int(k): int(v) for k, v in (evo.get("correspondances") or {}).items()}
        sortants = {int(x) for x in (evo.get("identifiants_retires") or [])}
        table = {
            ancien: corr.get(courant, courant)
            for ancien, courant in table.items()
            if courant not in sortants
        }
        nouveaux = [corr.get(n, n) for n in nouveaux]
        nouveaux += [int(x) for x in (evo.get("identifiants_nouveaux") or [])]
    return table, nouveaux


def _retires_cumules(chaine: list[dict]) -> list[int]:
    """Identifiants retires, exprimes dans la numerotation de l'etude d'origine.

    On remonte la chaine a l'envers : un identifiant retire a l'etape k porte le
    numero de l'etape k, pas celui de l'etude. Sans cette remontee, le controle
    de perte chercherait une fiche sous un numero qui n'a jamais existe chez elle.
    """
    origine: list[int] = []
    for k, evo in enumerate(chaine):
        for sortant in (evo.get("identifiants_retires") or []):
            courant = int(sortant)
            for anterieure in reversed(chaine[:k]):
                corr = {int(v): int(a)
                        for a, v in (anterieure.get("correspondances") or {}).items()}
                courant = corr.get(courant, courant)
            origine.append(courant)
    return sorted(origine)


# -------------------------------------------------------------------- plan


def construire_plan(projet: Path) -> dict:
    """Calcule tout ce que la migration ferait, sans rien ecrire.

    Le plan est la seule source du mode `--verifier` comme du mode reel : deux
    calculs separes finiraient par diverger, et le blanc cesserait de dire la
    verite sur ce que fait l'application.
    """
    base = projet.resolve() / "seo"
    if not base.is_dir():
        raise Refus(f"{base} absent — ce projet ne porte pas d'etude forge-seo.")

    prov_f = base / ".forge-seo.json"
    if not prov_f.exists():
        raise Refus(
            f"{prov_f} absent — l'etude ne declare pas sur quelle grille elle a ete "
            "produite.\nSans empreinte de depart, aucune table n'est applicable : "
            "transposer reviendrait a deviner."
        )
    prov = json.loads(_texte(prov_f))
    declaree = (prov.get("version_grille") or "").strip()
    actuelle = version_grille()

    if not declaree:
        raise Refus("`version_grille` absente ou vide dans .forge-seo.json.")

    chaine = chaine_correspondance(declaree, actuelle)
    if chaine is None:
        raise Refus(
            f"aucune chaine de correspondances ne relie {declaree} a {actuelle}.\n"
            "Le registre referentiel/correspondances-grille.json ne declare pas cette "
            "evolution : la transposer serait une invention.\n"
            "Declarer l'evolution (de, vers, correspondances ancien_id -> nouvel_id) "
            "avant de rejouer ce script."
        )

    manifeste = json.loads(_texte(MANIFESTE))
    par_chemin = {n["chemin"]: n for n in manifeste["noeuds"]}
    donnees = lire()

    table, nouveaux = table_cumulee(chaine)
    retires = _retires_cumules(chaine)

    plan: dict = {
        "base": base,
        "projet": projet.resolve(),
        "prov": prov,
        "declaree": declaree,
        "actuelle": actuelle,
        "chaine": chaine,
        "table": table,
        "retires": retires,
        "nouveaux": sorted(nouveaux),
        "a_jour": declaree == actuelle,
        "renumerotations": [],
        "inchanges": [],
        "ajouts": [],
        "branches": [],
        "branches_intouchables": [],
        "orphelins": [],
        "actions": [],
        "snapshots": [],
        "derives_grille": [],
        "citations": [],
        "refus": [],
    }

    if plan["a_jour"]:
        return plan

    # -- fiches existantes : transposition et controle contre le manifeste
    analyse = base / "analyse"
    if not analyse.is_dir():
        raise Refus(f"{analyse} absent — l'etude n'a pas d'arborescence d'analyse.")

    presents: dict[str, Path] = {}
    for fiche in sorted(analyse.rglob("_fiche.md")):
        chemin = fiche.parent.relative_to(analyse).as_posix()
        presents[chemin] = fiche

    for chemin, fiche in presents.items():
        try:
            fm = front_matter(fiche)
        except ValueError as e:
            plan["refus"].append(f"{chemin} : front-matter illisible ({e})")
            continue
        try:
            ancien = int(fm.get("id"))
        except (TypeError, ValueError):
            plan["refus"].append(f"{chemin} : identifiant illisible {fm.get('id')!r}")
            continue

        noeud = par_chemin.get(chemin)
        if noeud is None:
            # Chemin absent de la grille courante : soit l'identifiant a ete
            # retire, soit l'arborescence a derive. Dans les deux cas, on ne
            # detruit rien -- on refuse si la fiche porte du travail.
            plan["orphelins"].append((chemin, ancien, porte_du_travail(fiche)))
            if porte_du_travail(fiche):
                plan["refus"].append(
                    f"{chemin} (noeud {ancien}) : ce chemin n'existe plus dans la grille "
                    f"{actuelle} et la fiche porte du travail — migrer l'effacerait du "
                    "compte des noeuds."
                )
            continue

        attendu = table.get(ancien, ancien)
        if attendu != noeud["id"]:
            plan["refus"].append(
                f"{chemin} : l'etude porte le noeud {ancien}, la table le transpose en "
                f"{attendu}, le manifeste courant y place {noeud['id']} — transposition "
                "ambigue."
            )
            continue

        if ancien == noeud["id"]:
            plan["inchanges"].append(chemin)
        else:
            plan["renumerotations"].append((chemin, ancien, noeud["id"]))

        # -- derive de grille : la question, la methode ou le critere du noeud ont
        #    change entre les deux versions. Rien n'est perdu, mais un verdict rendu
        #    sous l'ancien critere est desormais confronte au nouveau. On le dit.
        for cle, titre in (
            ("question_audit", "Question d'audit"),
            ("methode", "Methode"),
            ("critere_verdict", "Critere de verdict"),
        ):
            ancienne = _section(fiche, titre)
            nouvelle = " ".join(str(noeud.get(cle) or "").split())
            if ancienne and nouvelle and ancienne != nouvelle:
                plan["derives_grille"].append({
                    "noeud": noeud["id"],
                    "chemin": chemin,
                    "champ": cle,
                    "instruit": (fm.get("etat") == "fait"),
                    "avant": ancienne,
                    "apres": nouvelle,
                })

        for citation in citations_prose(fiche, table):
            plan["citations"].append({"source": chemin, **citation})

    par_id_etude = {}
    for chemin, fiche in presents.items():
        try:
            par_id_etude[int(front_matter(fiche).get("id"))] = (chemin, fiche)
        except (TypeError, ValueError):
            continue

    # -- table injective SUR LES IDENTIFIANTS QUE L'ETUDE PORTE. La juger sur tout
    #    le domaine entier serait faux : au-dela du compte de la grille de depart,
    #    la table est l'identite et deux numeros inexistants s'y superposent sans
    #    qu'aucun constat ne soit en jeu. Ce qui compte, c'est que deux fiches
    #    REELLES n'atterrissent pas au meme numero -- la, deux constats fusionnent.
    collisions: dict[int, list[int]] = {}
    for ancien in sorted(par_id_etude):
        collisions.setdefault(table.get(ancien, ancien), []).append(ancien)
    for nouveau, anciens in sorted(collisions.items()):
        if len(anciens) > 1:
            plan["refus"].append(
                f"table non injective : les noeuds {anciens} de l'etude tombent tous sur "
                f"{nouveau} — deux constats fusionneraient."
            )

    # -- identifiants retires dont la fiche porte du travail
    for sortant in retires:
        entree = par_id_etude.get(sortant)
        if entree and porte_du_travail(entree[1]):
            plan["refus"].append(
                f"noeud {sortant} ({entree[0]}) retire par une evolution, mais sa fiche "
                "est instruite — la migration perdrait ce constat."
            )

    # -- noeuds a creer : ceux du manifeste courant sans fiche dans l'etude
    modele = None
    etat_f = base / "etat.json"
    if etat_f.exists():
        modele = (json.loads(_texte(etat_f)) or {}).get("modele_acquisition")

    par_id_grille = {n["id"]: n for b in donnees["branches"] for n in b["noeuds"]}
    for chemin, noeud in par_chemin.items():
        if chemin in presents:
            continue
        if noeud["id"] not in plan["nouveaux"]:
            plan["refus"].append(
                f"{chemin} (noeud {noeud['id']}) : fiche absente de l'etude, et AUCUNE "
                "evolution ne declare cet identifiant comme nouveau — ce trou n'est pas "
                "explique par la grille."
            )
            continue
        dossier = analyse / chemin
        if dossier.exists() and any(dossier.iterdir()):
            plan["refus"].append(
                f"{chemin} : le dossier existe deja et n'est pas vide — creer la fiche "
                "risquerait d'ecraser du contenu."
            )
            continue
        plan["ajouts"].append({
            "id": noeud["id"],
            "chemin": chemin,
            "noeud": noeud["noeud"],
            "branche": noeud["branche"],
            "grille": par_id_grille.get(noeud["id"], noeud),
            "modele": modele,
        })

    # -- fiches de branche : purement derivees de la grille. On ne les regenere que
    #    si elles sont restees telles que la forge les a ecrites (empreinte au
    #    registre de l'etude). Une branche retouchee a la main reste intacte.
    registre = registre_charger(base)
    for b in donnees["branches"]:
        cible = analyse / b["slug"] / "_branche.md"
        attendu = fiche_branche(b, canonique=False)
        if not cible.exists():
            plan["branches"].append((b["slug"], attendu, "creation"))
            continue
        actuel = _texte(cible)
        if actuel == attendu:
            continue
        cle = cible.relative_to(base).as_posix()
        if registre.get(cle) and registre[cle] != empreinte(actuel):
            plan["branches_intouchables"].append(b["slug"])
        else:
            plan["branches"].append((b["slug"], attendu, "regeneration"))

    # -- livrables : les identifiants y vivent aussi
    livrables = base / "livrables"
    if livrables.is_dir():
        for csv_f in sorted(livrables.glob("actions-*.csv")):
            touches = _plan_actions(csv_f, table)
            if touches["lignes"]:
                plan["actions"].append(touches)
        for snap_f in sorted(livrables.glob("snapshot-*.json")):
            touches = _plan_snapshot(snap_f, table, plan["ajouts"])
            if touches["noeuds"] or touches["dette"] or touches["ajouts"]:
                plan["snapshots"].append(touches)
                for citation in citations_prose(snap_f, table):
                    plan["citations"].append({"source": snap_f.name, **citation})

    return plan


def _section(fiche: Path, titre: str) -> str:
    """Contenu d'une section `## <titre>` de la fiche, replie sur une ligne."""
    texte = _texte(fiche)
    marque = f"\n## {titre}\n"
    if marque not in texte:
        return ""
    bloc = texte.split(marque, 1)[1].split("\n## ", 1)[0].split("\n---\n", 1)[0]
    return " ".join(RE_COMMENT.sub("", bloc).split())


def _plan_actions(chemin: Path, table: dict[int, int]) -> dict:
    lignes = []
    for a in lire_actions(chemin):
        brut = a.get("noeuds_couverts") or ""
        anciens = ids_noeuds(brut)
        if not anciens:
            continue
        nouveaux = [table.get(i, i) for i in anciens]
        if nouveaux != anciens:
            lignes.append({"id": a.get("id"), "avant": anciens, "apres": nouveaux})
    return {"fichier": chemin, "lignes": lignes}


def _plan_snapshot(chemin: Path, table: dict[int, int], ajouts: list[dict]) -> dict:
    """Ce que la migration ferait a un snapshot : transposer, et completer.

    Le snapshot porte la LISTE des noeuds de la grille -- le schema en exige
    exactement NB_NOEUDS. Transposer sans completer laisserait un snapshot a 87
    entrees face a une grille de 88 : validate.py le refuserait, et il aurait
    raison. Le noeud ajoute y entre sans cle `verdict` : dans ce contrat, une cle
    absente est un noeud non juge -- c'est deja le vocabulaire de « non instruit ».
    """
    snap = json.loads(_texte(chemin))
    presents = {
        int(n["id"]) for n in (snap.get("noeuds") or [])
        if str(n.get("id") or "").isdigit()
    }
    noeuds = [
        (int(n["id"]), table.get(int(n["id"]), int(n["id"])))
        for n in (snap.get("noeuds") or [])
        if str(n.get("id") or "").isdigit()
    ]
    transposes = {t for _, t in noeuds} | (presents - {a for a, _ in noeuds})
    dette = [
        (int(x["noeud_id"]), table.get(int(x["noeud_id"]), int(x["noeud_id"])))
        for x in (snap.get("dette_instrumentation") or [])
        if str(x.get("noeud_id") or "").isdigit()
    ]
    return {
        "fichier": chemin,
        "noeuds": [c for c in noeuds if c[0] != c[1]],
        "dette": [c for c in dette if c[0] != c[1]],
        "ajouts": [a for a in ajouts if a["id"] not in transposes],
    }


# ------------------------------------------------------------------ ecriture


def appliquer(plan: dict) -> dict:
    """Applique le plan. N'est appelee qu'apres un plan SANS refus."""
    base: Path = plan["base"]
    analyse = base / "analyse"
    table = plan["table"]
    fait = {"fiches": 0, "branches": 0, "ajouts": 0, "actions": 0, "snapshots": 0}

    # 1. identifiants des fiches. Substitution du SEUL champ `id` du front-matter :
    #    tout le reste de la fiche est du travail d'auditeur, on n'y touche pas.
    for chemin, ancien, nouveau in plan["renumerotations"]:
        fiche = analyse / chemin / "_fiche.md"
        texte = _texte(fiche)
        entete, separateur, reste = texte.partition("\n---\n")
        remplace, n = RE_ID.subn(rf"\g<1>{nouveau}\g<3>", entete, count=1)
        if n != 1:
            raise Refus(f"{chemin} : champ `id` introuvable dans le front-matter.")
        _ecrire(fiche, remplace + separateur + reste)
        fait["fiches"] += 1

    # 2. fiches de branche derivees
    registre = registre_charger(base)
    for slug, contenu, _ in plan["branches"]:
        cible = analyse / slug / "_branche.md"
        cible.parent.mkdir(parents=True, exist_ok=True)
        _ecrire(cible, contenu)
        registre[cible.relative_to(base).as_posix()] = empreinte(contenu)
        fait["branches"] += 1

    # 3. noeuds nouveaux, a l'etat de naissance : non instruits, sans verdict.
    for ajout in plan["ajouts"]:
        dossier = analyse / ajout["chemin"]
        dossier.mkdir(parents=True, exist_ok=True)
        gabarit = fiche_noeud(ajout["grille"], ajout["modele"])
        cible = dossier / "_fiche.md"
        _ecrire(cible, _marquer(gabarit, plan))
        # L'empreinte enregistree est celle du GABARIT NU, pas du contenu ecrit :
        # la note de migration compte ainsi comme du contenu non genere, et un
        # scaffold ulterieur ne l'ecrasera pas en silence.
        registre[cible.relative_to(base).as_posix()] = empreinte(gabarit)
        fait["ajouts"] += 1

    registre_ecrire(base, registre)

    # 4. livrables : copie intacte avant reecriture
    archive = base / "livrables" / f"pre-migration-{plan['declaree']}"
    if plan["actions"] or plan["snapshots"]:
        archive.mkdir(parents=True, exist_ok=True)

    for touche in plan["actions"]:
        _copier(touche["fichier"], archive)
        _reecrire_actions(touche["fichier"], table)
        fait["actions"] += 1

    for touche in plan["snapshots"]:
        _copier(touche["fichier"], archive)
        _reecrire_snapshot(touche["fichier"], table, touche["ajouts"])
        fait["snapshots"] += 1

    # 5. empreinte de l'etude et journal
    _journaliser(plan, fait)

    # 6. compteurs d'avancement : validate.py les oppose aux fiches reelles.
    etat_f = base / "etat.json"
    if etat_f.exists():
        etat = json.loads(_texte(etat_f))
        etat["noeuds"] = compteurs(lire_fiches(base))
        _ecrire(etat_f, json.dumps(etat, indent=2, ensure_ascii=False) + "\n")

    return fait


def _marquer(gabarit: str, plan: dict) -> str:
    """Insere la note de migration entre le front-matter et le corps.

    Elle vit dans la fiche parce que c'est la que quelqu'un l'ouvrira. Le
    front-matter, lui, n'est pas touche : l'etat de naissance dit deja tout ce
    que la machine doit savoir -- `etat: a-faire`, `verdict: null`.
    """
    tete, separateur, reste = gabarit.partition("\n---\n")
    note = (
        f"\n<!-- NOEUD AJOUTE PAR MIGRATION DE GRILLE le {dt.date.today().isoformat()} :"
        f" {plan['declaree']} -> {plan['actuelle']}.\n"
        "     Ce noeud n'existait pas dans la grille sur laquelle cette etude a ete\n"
        "     auditee. Il est donc NON INSTRUIT : aucune mesure n'a ete prise sur ce\n"
        "     site pour cette question, et aucun verdict n'a ete rendu. L'instruire\n"
        "     suppose un nouveau passage de collecte, pas une deduction. -->\n"
    )
    return tete + separateur + note + reste


def _copier(source: Path, archive: Path) -> None:
    cible = archive / source.name
    if cible.exists():
        return
    shutil.copy2(source, cible)


def _reecrire_actions(chemin: Path, table: dict[int, int]) -> None:
    """Transpose `noeuds_couverts`, et VERIFIE que rien d'autre n'a bouge."""
    brut = chemin.read_text(encoding="utf-8-sig")
    avant = lire_actions(chemin)
    if not avant:
        return
    colonnes = list(avant[0].keys())
    separateur = ";" if brut.split("\n", 1)[0].count(";") > brut.split("\n", 1)[0].count(",") else ","

    apres = []
    for ligne in avant:
        copie = dict(ligne)
        anciens = ids_noeuds(copie.get("noeuds_couverts"))
        if anciens:
            copie["noeuds_couverts"] = " ".join(
                str(table.get(i, i)) for i in anciens
            )
        apres.append(copie)

    sortie = io.StringIO()
    w = csv.DictWriter(sortie, fieldnames=colonnes, delimiter=separateur,
                       lineterminator="\n")
    w.writeheader()
    for ligne in apres:
        w.writerow({c: ligne.get(c, "") for c in colonnes})

    # Controle de non-perte AVANT de toucher au fichier. Le CSV candidat est ecrit
    # a cote, relu, compare cellule a cellule, et ne prend la place de l'original
    # que s'il en sort indemne : un round-trip qui mange une valeur ne doit pas
    # pouvoir laisser l'etude a moitie migree.
    tampon = chemin.with_name(chemin.name + ".migration-tmp")
    try:
        tampon.write_text("\ufeff" + sortie.getvalue(), encoding="utf-8")
        relu = lire_actions(tampon)
        if len(relu) != len(avant):
            raise Refus(f"{chemin.name} : {len(avant)} action(s) avant, {len(relu)} apres.")
        for a, b in zip(avant, relu):
            for cle in colonnes:
                if (cle or "").strip().lower().endswith("noeuds_couverts"):
                    continue
                if (a.get(cle) or "") != (b.get(cle) or ""):
                    raise Refus(
                        f"{chemin.name} : la colonne {cle!r} de l'action {a.get('id')} "
                        "n'a pas survecu a la reecriture."
                    )
        _ecrire_bom(chemin, tampon.read_text(encoding="utf-8-sig"))
    finally:
        tampon.unlink(missing_ok=True)


def _reecrire_snapshot(chemin: Path, table: dict[int, int], ajouts: list[dict]) -> None:
    snap = json.loads(_texte(chemin))
    noeuds = list(snap.get("noeuds") or [])
    for n in noeuds:
        if str(n.get("id") or "").isdigit():
            n["id"] = table.get(int(n["id"]), int(n["id"]))
    for x in (snap.get("dette_instrumentation") or []):
        if str(x.get("noeud_id") or "").isdigit():
            x["noeud_id"] = table.get(int(x["noeud_id"]), int(x["noeud_id"]))
    for a in ajouts:
        g = a["grille"]
        # Ni `verdict` ni `motif_non_mesure` : le contrat de snapshot dit qu'une
        # cle absente est un noeud non juge. En poser une ici, meme prudente,
        # serait fabriquer un resultat que personne n'a mesure.
        noeuds.append({
            "id": a["id"],
            "branche": g["branche"],
            "noeud": g["noeud"],
            "volet": g["volet"],
            "statut": g["statut"],
            "actions_liees": [],
        })
    if noeuds:
        snap["noeuds"] = sorted(noeuds, key=lambda n: n.get("id") or 0)
    _ecrire(chemin, json.dumps(snap, indent=2, ensure_ascii=False) + "\n")


def _journaliser(plan: dict, fait: dict) -> None:
    """Ecrit l'empreinte nouvelle ET la trace de l'operation dans .forge-seo.json.

    Deplacer l'empreinte sans dire par quoi, quand et par qui, ce serait rendre la
    migration indiscernable d'une etude nee sur la grille courante.
    """
    base: Path = plan["base"]
    prov = dict(plan["prov"])
    prov["version_grille"] = plan["actuelle"]
    journal = list(prov.get("migrations") or [])
    try:
        operateur = getpass.getuser()
    except Exception:  # environnement sans utilisateur nomme
        operateur = "inconnu"
    journal.append({
        "de": plan["declaree"],
        "vers": plan["actuelle"],
        "date": dt.date.today().isoformat(),
        "par": "scripts/migrer_mission.py",
        "forge": str(RACINE),
        "operateur": operateur,
        "evolutions_appliquees": [e.get("motif", "?") for e in plan["chaine"]],
        "identifiants_renumerotes": len(plan["renumerotations"]),
        "correspondances": {
            str(a): str(n) for chemin, a, n in plan["renumerotations"]
        },
        "noeuds_ajoutes_non_instruits": [
            {
                "id": a["id"],
                "chemin": a["chemin"],
                "noeud": a["noeud"],
                "branche": a["branche"],
                "etat": "a-faire",
                "verdict": None,
                "note": "noeud absent de la grille d'audit de cette etude — non mesure "
                        "sur ce site, aucun verdict rendu",
            }
            for a in plan["ajouts"]
        ],
        "identifiants_retires": plan["retires"],
        "branches_regenerees": fait["branches"],
        "livrables_transposes": sorted(
            [t["fichier"].name for t in plan["actions"]]
            + [t["fichier"].name for t in plan["snapshots"]]
        ),
        "livrables_archives": (
            f"livrables/pre-migration-{plan['declaree']}/"
            if (plan["actions"] or plan["snapshots"]) else None
        ),
        "a_reinstruire": [
            {"noeud": d["noeud"], "champ": d["champ"], "avant": d["avant"],
             "apres": d["apres"]}
            for d in plan["derives_grille"] if d["instruit"]
        ],
        "citations_en_prose_non_transposees": [
            {
                "source": c["source"],
                "texte": c["texte"],
                "plage": c["plage"],
                "identifiants_devenus_faux": [
                    {"lu": a, "designe_desormais": n} for a, n in c["bougent"]
                ],
            }
            for c in plan["citations"]
        ],
    })
    prov["migrations"] = journal
    _ecrire(base / ".forge-seo.json",
            json.dumps(prov, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------- sortie


def imprimer(plan: dict, verifier: bool) -> None:
    print(f"migration d'etude — {plan['projet']}")
    print(f"  grille de l'etude : {plan['declaree']}")
    print(f"  grille de la forge: {plan['actuelle']}")
    if plan["a_jour"]:
        print("  l'etude est deja sur la grille courante — rien a faire.")
        return
    print(f"  chaine            : {len(plan['chaine'])} evolution(s)")
    for e in plan["chaine"]:
        print(f"      {e.get('de')} -> {e.get('vers')} ({e.get('date')})")
    print(f"  identifiants a renumeroter : {len(plan['renumerotations'])}")
    for chemin, a, n in plan["renumerotations"][:5]:
        print(f"      {a:>3} -> {n:<3} {chemin}")
    if len(plan["renumerotations"]) > 5:
        print(f"      … (+{len(plan['renumerotations']) - 5})")
    print(f"  fiches inchangees          : {len(plan['inchanges'])}")
    print(f"  noeuds a ajouter NON INSTRUITS : {len(plan['ajouts'])}")
    for a in plan["ajouts"]:
        print(f"      [{a['id']}] {a['branche']} / {a['noeud']} — {a['chemin']}")
        print("           etat: a-faire · verdict: null — aucune mesure prise sur ce site")
    print(f"  fiches de branche a regenerer  : {len(plan['branches'])}")
    if plan["branches_intouchables"]:
        print(f"      conservees (retouchees a la main) : "
              f"{', '.join(plan['branches_intouchables'])}")
    for t in plan["actions"]:
        print(f"  actions : {t['fichier'].name} — {len(t['lignes'])} ligne(s) transposee(s)")
    for t in plan["snapshots"]:
        print(f"  snapshot: {t['fichier'].name} — {len(t['noeuds'])} noeud(s) transpose(s), "
              f"{len(t['dette'])} entree(s) de dette, {len(t['ajouts'])} noeud(s) ajoute(s) "
              "sans verdict")
    if plan["orphelins"]:
        print(f"  fiches orphelines (chemin absent de la grille) : {len(plan['orphelins'])}")
        for chemin, ancien, travail in plan["orphelins"]:
            print(f"      {chemin} (noeud {ancien})"
                  + (" — INSTRUITE" if travail else " — vide, conservee en place"))

    a_reinstruire = [d for d in plan["derives_grille"] if d["instruit"]]
    if a_reinstruire:
        print(f"\n  AVERTISSEMENT — {len(a_reinstruire)} noeud(s) instruit(s) dont la "
              "grille a change de question, de methode ou de critere :")
        for d in a_reinstruire:
            print(f"      noeud {d['noeud']} · {d['champ']}")
            print(f"        avant : {d['avant'][:120]}")
            print(f"        apres : {d['apres'][:120]}")
        print("      Le verdict existant a ete rendu sous l'ANCIEN critere. La migration "
              "ne le touche pas :")
        print("      le rejuger est une decision d'auditeur, pas une transposition.")

    if plan["citations"]:
        print(f"\n  AVERTISSEMENT — {len(plan['citations'])} citation(s) de noeud EN PROSE "
              "dont le numero a bouge :")
        for c in plan["citations"][:12]:
            bouge = ", ".join(f"{a} designe desormais {n}" for a, n in c["bougent"])
            marque = " [PLAGE — a rejuger, pas a decaler]" if c["plage"] else ""
            print(f"      {c['source']} : « {c['texte']} » — {bouge}{marque}")
        if len(plan["citations"]) > 12:
            print(f"      … (+{len(plan['citations']) - 12})")
        print("      Ces numeros ne sont PAS transposes : reecrire la prose d'un auditeur "
              "serait une invention.")
        print("      Les citations dont le numero ne bouge pas ne sont pas listees : "
              "elles restent exactes.")

    if verifier:
        print("\n--verifier : aucune ecriture. Le plan ci-dessus est ce qui serait fait.")


def migrer(projet: Path, verifier: bool = False) -> int:
    try:
        plan = construire_plan(projet)
    except Refus as e:
        print(f"REFUS : {e}")
        return 1

    imprimer(plan, verifier)

    if plan["refus"]:
        print(f"\nREFUS : {len(plan['refus'])} obstacle(s) — rien n'a ete ecrit.")
        for motif in plan["refus"]:
            print(f"  · {motif}")
        print("\nUne migration qui perd ou fusionne un constat est pire qu'une etude "
              "figee sur une grille ancienne.")
        return 1

    if plan["a_jour"] or verifier:
        return 0

    try:
        fait = appliquer(plan)
    except Refus as e:
        print(f"\nREFUS en cours d'application : {e}")
        return 1

    print(f"\nmigration appliquee : {plan['declaree']} -> {plan['actuelle']}")
    print(f"  fiches renumerotees : {fait['fiches']}")
    print(f"  fiches de branche   : {fait['branches']}")
    print(f"  noeuds ajoutes      : {fait['ajouts']} (non instruits)")
    print(f"  livrables transposes: {fait['actions'] + fait['snapshots']}")
    print(f"  journal ecrit dans  : {plan['base'] / '.forge-seo.json'}")
    print("\nEtape suivante :")
    print(f'  python scripts/validate.py --mission "{plan["projet"]}"')
    print(f'  python scripts/rapport_html.py --projet "{plan["projet"]}" --verifier')
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Migre une etude SEO d'une empreinte de grille vers l'actuelle."
    )
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument("--verifier", action="store_true",
                   help="blanc : calcule et imprime le plan, n'ecrit rien")
    args = p.parse_args()
    return migrer(Path(args.projet), args.verifier)


if __name__ == "__main__":
    sys.exit(main())
