"""Remplit les fiches d'une etude a partir d'un contenu redige, et reporte les
constats d'un run precedent.

Ce moteur vivait chez la mission -- `remplir87.py`, avec le chemin de la forge et
celui du run precedent en dur, et un compte de noeuds fige dans son nom. Chaque
mission suivante l'aurait recopie, puis fait diverger : c'est la forme meme de la
derive que cette forge s'interdit ailleurs. Il rentre ici, parametre (TF-0030).

CE QUI RESTE CHEZ LA MISSION : le CONTENU. Les constats, preuves et
interpretations sont le travail d'audit d'un client donne ; la forge fournit la
mecanique qui les pose dans les bonnes fiches, jamais la matiere.

DEUX REGLES QUE CE SCRIPT PORTE, et qui sont la raison d'etre du rapatriement :

  1. Le report d'un run precedent se fait par (branche, noeud), JAMAIS par
     identifiant. Le passage de 82 a 87 noeuds a deplace 14 identifiants :
     reporter par id aurait ecrit chaque constat dans le mauvais noeud.
  2. Le markdown des fiches est aplati en prose. Le rapport HTML echappe le texte
     des fiches sans interpreter le balisage : un tableau y sortirait en soupe de
     barres verticales. La donnee doit vivre dans la phrase.

Usage :
    python scripts/remplir_fiches.py --projet C:/dev/mon-client --contenu fiches.json
    python scripts/remplir_fiches.py --projet . --contenu fiches.py \
           --reprise ../docs/seo/analyse --deplacements deplacements.json
    python scripts/remplir_fiches.py --projet . --contenu fiches.json --verifier

Format du contenu (JSON, recommande) : un objet dont les cles sont les
identifiants de noeuds du manifeste courant.

    {
      "12": {
        "verdict": "non-conforme",
        "niveau_preuve": "T1",
        "constat": "...",
        "preuves": "...",
        "interpretation": "...",
        "actions": ["A3"]
      },
      "13": { "verdict": "partiel", "niveau_preuve": "T2", "reprise": true }
    }

`reprise: true` : le constat vient du run precedent et est repris tel quel ; seuls
le verdict et le niveau de preuve sont redeclares. Un module Python exposant un
dictionnaire `F` de meme forme est accepte pour les etudes deja ecrites ainsi,
mais le JSON est la forme a preferer : un contenu est une donnee, pas du code.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path

from gabarits import front_matter
from grille import NB_NOEUDS, RACINE

MANIFESTE = RACINE / "seo" / "manifest.json"

# Vocabulaire impose par snapshot.schema.json et par le rapport.
VERDICTS = {"conforme", "partiel", "non-conforme", "non-mesure", "sans-objet"}

# Motif de hors-perimetre par statut d'instrumentation. Un noeud sans contenu
# n'est pas un oubli quand la grille declare elle-meme qu'il n'est pas mesurable
# dans les conditions du run : le motif le dit, et le rapport l'affiche comme un
# resultat, pas comme un blanc.
MOTIFS = {
    "PY": "outil payant requis ({src}) — aucun abonnement déclaré au cadrage",
    "NM": "non mesurable par construction : {src} — non fourni",
    "EX": "source externe requise ({src}) — non fournie à la date de l'audit",
    "CA": "relève du cadrage, renseigné dans `cadrage.md`",
    "RV": "renvoi de la grille vers une autre branche — rien à mesurer ici",
}

CHAMPS_ECRITS = ("etat", "motif_hors_perimetre", "verdict", "niveau_preuve",
                 "date_mesure", "actions_liees")


# ------------------------------------------------------------------- contenu


def charger_contenu(chemin: Path) -> dict[int, dict]:
    """Contenu des fiches, indexe par identifiant de noeud.

    Le JSON est la forme normale. Le module Python n'existe que pour les etudes
    deja redigees ainsi : le charger EXECUTE le fichier, ce qui n'est acceptable
    que parce qu'il s'agit du propre fichier de la mission qui invoque le script.
    """
    if not chemin.exists():
        raise SystemExit(f"REFUS : contenu introuvable — {chemin}")

    if chemin.suffix == ".json":
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    elif chemin.suffix == ".py":
        spec = importlib.util.spec_from_file_location("contenu_etude", chemin)
        if spec is None or spec.loader is None:
            raise SystemExit(f"REFUS : {chemin.name} n'est pas un module chargeable")
        module = importlib.util.module_from_spec(spec)
        sys.modules["contenu_etude"] = module
        spec.loader.exec_module(module)
        brut = getattr(module, "F", None)
        if not isinstance(brut, dict):
            raise SystemExit(
                f"REFUS : {chemin.name} n'expose pas de dictionnaire `F`. "
                "Un module de contenu declare ses fiches dans `F`, indexees par "
                "identifiant de noeud."
            )
    else:
        raise SystemExit(
            f"REFUS : {chemin.name} — contenu attendu en .json (recommande) ou .py"
        )

    return {int(k): v for k, v in brut.items()}


# ----------------------------------------------------- lecture d'une fiche ecrite


def sections(texte: str) -> dict:
    """Decoupe Constat / Preuves / Interpretation d'une fiche deja remplie."""
    out = {"constat": "", "preuves": "", "interpretation": ""}
    tampon: dict[str, list[str]] = {k: [] for k in out}
    cle = None
    for ligne in texte.split("\n---\n", 2)[-1].split("\n"):
        bas = ligne.strip().lower()
        if bas.startswith("## "):
            t = bas[3:]
            cle = ("constat" if t.startswith("constat")
                   else "preuves" if t.startswith("preuve")
                   else "interpretation" if t.startswith("interpr")
                   else None)
            continue
        if cle:
            tampon[cle].append(ligne)
    for k in out:
        out[k] = "\n".join(tampon[k]).strip()
    return out


def _table_en_prose(lignes: list[str]) -> str:
    """Aplatit un tableau markdown en une enumeration lisible."""
    cells = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lignes]
    cells = [c for c in cells if not all(re.fullmatch(r":?-{2,}:?", x or "-") for x in c)]
    if len(cells) < 2:
        return " ".join(" ".join(c) for c in cells)
    tete, corps = cells[0], cells[1:]
    out = []
    for ligne in corps:
        if len(ligne) == 2:
            out.append(f"{ligne[0]} : {ligne[1]}")
        else:
            reste = ", ".join(
                f"{tete[i].lower()} {ligne[i]}"
                for i in range(1, min(len(ligne), len(tete))) if ligne[i]
            )
            out.append(f"{ligne[0]} — {reste}" if reste else ligne[0])
    return " ; ".join(out) + "."


def en_prose(texte: str) -> str:
    """Retire le balisage que le rapport ne sait pas rendre, sans perdre de donnee."""
    sortie: list[str] = []
    tampon: list[str] = []
    for ligne in texte.split("\n"):
        if ligne.lstrip().startswith("|"):
            tampon.append(ligne)
            continue
        if tampon:
            sortie.append(_table_en_prose(tampon))
            tampon = []
        sortie.append(re.sub(r"^\s*[-*]\s+", "", ligne))
    if tampon:
        sortie.append(_table_en_prose(tampon))
    t = "\n".join(sortie)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)   # gras, meme sur deux lignes
    t = re.sub(r"(?<!`)`([^`]+)`(?!`)", r"\1", t)        # code et etiquettes de preuve
    t = re.sub(r"^\s*>\s?", "", t, flags=re.M)           # citations
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def bloc(titre: str, contenu: str) -> str:
    return f"## {titre}\n\n{en_prose(contenu)}\n\n"


# ------------------------------------------------------------------- reprise


def lire_reprises(dossier: Path) -> dict[tuple[str, str], dict]:
    """Constats du run precedent, appariee par (branche, noeud).

    Par (branche, noeud) et jamais par identifiant : les identifiants bougent
    d'une version de grille a l'autre, les noms non.
    """
    repris: dict[tuple[str, str], dict] = {}
    if not dossier.is_dir():
        return repris
    for p in sorted(dossier.glob("**/_fiche.md")):
        texte = p.read_text(encoding="utf-8")
        try:
            fm = front_matter(p)
        except ValueError:
            continue
        if fm.get("etat") != "fait":
            continue
        repris[(fm.get("branche", "").lower(), fm.get("noeud", "").lower())] = sections(texte)
    return repris


def lire_deplacements(chemin: Path | None) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """Noeuds dont le contenu du run precedent doit changer de casier.

    Un constat mesure et non reporte est purement perdu : le deplacement est
    declare, date et relu, jamais devine.
    """
    if chemin is None:
        return []
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    entrees = brut.get("deplacements", brut) if isinstance(brut, dict) else brut
    out = []
    for e in entrees:
        de, vers = e["de"], e["vers"]
        out.append(((de[0].lower(), de[1].lower()), (vers[0].lower(), vers[1].lower())))
    return out


# -------------------------------------------------------------------- moteur


def remplir(
    projet: Path,
    contenu: Path,
    reprise: Path | None = None,
    deplacements: Path | None = None,
    verifier: bool = False,
) -> int:
    base = projet.resolve() / "seo"
    if not base.is_dir():
        print(f"{base} absent — créer l'étude avec new_mission.py")
        return 1

    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))["noeuds"]
    fiches = charger_contenu(contenu)
    repris = lire_reprises(reprise) if reprise else {}

    deplaces: dict[tuple[str, str], dict] = {}
    for src, dst in lire_deplacements(deplacements):
        if src in repris:
            deplaces[dst] = repris[src]

    aujourdhui = dt.date.today().isoformat()
    ecrites = mesurees = hors = a_faire = 0
    par_statut: dict[str, int] = {}
    soucis: list[str] = []

    for n in manifeste:
        p = base / "analyse" / n["chemin"] / "_fiche.md"
        if not p.exists():
            soucis.append(f"fiche absente : {n['chemin']}")
            continue
        texte = p.read_text(encoding="utf-8")
        statut = n.get("statut", "SD")
        cle = (n["branche"].lower(), n["noeud"].lower())

        d = fiches.get(n["id"])
        if d and d.get("reprise"):
            c = deplaces.get(cle) or repris.get(cle)
            if not c:
                soucis.append(f"reprise annoncée mais introuvable : {n['id']} {n['noeud']}")
                d = None
            else:
                d = {**d, **c}

        if d and d.get("constat"):
            if d.get("verdict") not in VERDICTS:
                soucis.append(f"verdict hors vocabulaire : {n['id']} {d.get('verdict')!r}")
            etat, motif = "fait", "null"
            verdict, preuve = d["verdict"], d.get("niveau_preuve", "null")
            corps = (bloc("Constat", d["constat"])
                     + bloc("Preuves", d.get("preuves", "—"))
                     + bloc("Interpretation", d.get("interpretation", "—")))
            liees = d.get("actions") or []
            actions = "[" + ", ".join(liees) + "]" if liees else "[]"
            mesurees += 1
        elif statut in MOTIFS:
            src = n.get("source_requise") or "source non disponible"
            mt = MOTIFS[statut].format(src=src)
            etat, motif = "hors-perimetre", f'"{mt}"'
            verdict, preuve = "sans-objet", "null"
            corps = (bloc("Constat", f"**Non mesurable en l'état.** {mt.capitalize()}.\n\n"
                          "Aucune valeur n'est avancée : une estimation présentée comme "
                          "une mesure vaudrait moins que ce blanc.")
                     + bloc("Preuves", "—") + bloc("Interpretation", "—"))
            actions = "[]"
            hors += 1
        else:
            etat, motif, verdict, preuve = "a-faire", "null", "null", "null"
            corps = (bloc("Constat", "**Non encore mesuré.** Nœud instrumentable sans "
                          "dépendance externe : il relève du périmètre et reste à traiter.")
                     + bloc("Preuves", "—") + bloc("Interpretation", "—"))
            actions = "[]"
            a_faire += 1

        # Un noeud pre-marque hors perimetre par le modele d'acquisition garde son
        # motif d'origine : le modele est une decision de cadrage, plus informative
        # que « source externe non fournie ». Le noeud a pu etre compte « a faire »
        # juste au-dessus : on BASCULE le compteur au lieu d'en incrementer un
        # second, sinon le total depasse le nombre reel de fiches.
        try:
            fm_actuel = front_matter(p)
        except ValueError:
            fm_actuel = {}
        if fm_actuel.get("etat") == "hors-perimetre" and not (d and d.get("constat")):
            if etat == "a-faire":
                a_faire -= 1
                hors += 1
            etat = "hors-perimetre"
            motif = fm_actuel.get("motif_hors_perimetre", "null")
            verdict, preuve = "sans-objet", "null"
            corps = (bloc("Constat", f"**Hors périmètre.** {motif.strip('\"').capitalize()}.")
                     + bloc("Preuves", "—") + bloc("Interpretation", "—"))

        par_statut[statut] = par_statut.get(statut, 0) + 1

        m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", texte, re.S)
        if not m:
            soucis.append(f"front-matter illisible : {n['chemin']}")
            continue
        fm, reste = m.group(1) + "\n", m.group(2)
        for k, v in zip(CHAMPS_ECRITS,
                        (etat, motif, verdict, preuve, aujourdhui, actions)):
            fm = re.sub(rf"^{k}: .*$", f"{k}: {v}", fm, flags=re.M)
        tete = reste.split("## Constat")[0].rstrip()
        if not verifier:
            p.write_text(f"---\n{fm}---\n{tete}\n\n{corps.rstrip()}\n", encoding="utf-8")
        ecrites += 1

    prefixe = "[verification] " if verifier else ""
    print(f"{prefixe}{ecrites} fiche(s) {'a écrire' if verifier else 'écrites'} sur "
          f"{NB_NOEUDS} · {mesurees} mesurée(s) · {a_faire} restant à faire · "
          f"{hors} hors périmètre")
    if mesurees + a_faire:
        print(f"couverture des nœuds mesurables : {mesurees}/{mesurees + a_faire} "
              f"({mesurees / (mesurees + a_faire) * 100:.0f} %)")
    print("statuts traités :", dict(sorted(par_statut.items())))
    print(f"reprises disponibles du run précédent : {len(repris)}"
          + (f" · {len(deplaces)} déplacement(s) appliqué(s)" if deplaces else ""))
    if soucis:
        print(f"\n!! {len(soucis)} anomalie(s) :")
        for s in soucis:
            print("   ", s)
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Remplit les fiches d'une étude depuis un contenu rédigé."
    )
    p.add_argument("--projet", required=True, help="chemin du projet audité")
    p.add_argument("--contenu", required=True,
                   help="fichier de contenu des fiches (.json recommandé, .py accepté)")
    p.add_argument("--reprise",
                   help="dossier analyse/ d'un run précédent, pour reporter ses constats")
    p.add_argument("--deplacements",
                   help="table JSON des nœuds dont le contenu change de casier")
    p.add_argument("--verifier", action="store_true",
                   help="compte et anomalies, aucune écriture")
    args = p.parse_args()
    return remplir(
        Path(args.projet),
        Path(args.contenu),
        Path(args.reprise) if args.reprise else None,
        Path(args.deplacements) if args.deplacements else None,
        args.verifier,
    )


if __name__ == "__main__":
    sys.exit(main())
