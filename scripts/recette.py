"""Recette de la forge : joue TOUTE la suite de verification en une commande (TF-0274).

Le probleme ferme ici. Les verifications de forge-seo sont des scripts a `main()`,
pas des tests pytest : `python -m pytest scripts/` collecte 0 test (aucune fonction
`test_*`, tout vit dans `main()`). Chacune se lancait donc a la main, une par une, et
le README n'en citait que cinq sur dix -- `test_agents_ia.py`, `test_crux.py`,
`test_json_ld.py`, `test_rendu_js.py` et `test_scorer_actions.py` n'y figuraient pas.
Un test neuf etait oublie d'une campagne a l'autre sans que rien ne le signale.

Ce que ce runner garantit.
  1. DECOUVERTE, jamais liste en dur : toute `scripts/test_*.py` est jouee du seul
     fait d'exister. Deposer un test neuf suffit a le faire entrer dans la recette.
     Les deux verifications historiques qui ne suivent pas la convention de nommage
     (`validate.py`, `autotest.py`) sont nommees explicitement, et leur absence du
     disque est une erreur, pas un silence.
  2. AUCUNE VERIFICATION MUETTE : un script dont la sortie ne porte pas de compte
     « N/M » est signale et fait echouer la recette. Compter 0 cas en silence
     reviendrait a laisser passer un test qui n'a rien execute.
  3. RIEN N'EST TOUCHE : chaque script est lance tel quel, dans son propre process,
     avec le meme cwd que lorsqu'on le lance seul -- ils restent tous lancables
     individuellement, ce runner n'est qu'un chef d'orchestre.

Usage :
    python scripts/recette.py              # joue tout, exit 0 si tout est vert
    python scripts/recette.py --liste      # ce qui SERAIT joue, sans rien executer
    python scripts/recette.py --fixture    # preuve a double sens du runner lui-meme

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

# Verifications anterieures a la convention `test_*.py` : nommees, donc jamais
# perdues -- mais c'est la SEULE liste en dur, et elle ne peut que se reduire.
VERIFICATIONS_NOMMEES = ("validate.py", "autotest.py")

# Toute sortie de verification finit par un compte « N/M » (preuves conformes, cas
# conformes, controles passes). C'est le contrat de sortie que ce runner impose.
RE_COMPTE = re.compile(r"(\d+)\s*/\s*(\d+)")


def decouvrir(dossier: Path) -> list[Path]:
    """Les verifications a jouer : glob d'abord, liste nommee ensuite.

    Le glob est ce qui rend l'oubli impossible : un `test_*.py` depose dans le
    dossier est joue sans qu'aucun fichier n'ait a etre edite.
    """
    trouves = sorted(p for p in dossier.glob("test_*.py") if p.name != Path(__file__).name)
    for nom in VERIFICATIONS_NOMMEES:
        candidat = dossier / nom
        if candidat.exists():
            trouves.append(candidat)
    return trouves


def jouer(script: Path) -> dict:
    """Lance UNE verification dans son propre process et lit son compte de cas.

    `cwd` = le dossier du script, comme quand on le lance a la main : les
    verifications importent leurs voisins par nom de module (`from crux import ...`).
    """
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(
        [sys.executable, script.name],
        cwd=script.parent, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    lignes = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    derniere = lignes[-1] if lignes else ""
    m = RE_COMPTE.search(derniere)
    return {
        "nom": script.name,
        "code": r.returncode,
        "cas_ok": int(m.group(1)) if m else None,
        "cas_total": int(m.group(2)) if m else None,
        "muette": m is None,
        "derniere_ligne": derniere or "(aucune sortie)",
        "stderr": (r.stderr or "").strip(),
    }


def rapporter(resultats: list[dict]) -> tuple[int, list[str]]:
    """Rend (code de sortie, lignes de rapport). Vert exige : tout exit 0, aucune muette."""
    lignes = []
    for v in resultats:
        if v["muette"]:
            etat = "MUETTE"
        elif v["code"] != 0:
            etat = "ECHEC "
        else:
            etat = "OK    "
        compte = "— aucun compte lu" if v["muette"] else f"{v['cas_ok']}/{v['cas_total']} cas"
        lignes.append(f"  [{etat}] {v['nom']:<26} {compte}")
        if v["muette"]:
            lignes.append(f"           sortie : {v['derniere_ligne'][:90]}")
            lignes.append("           une verification sans compte « N/M » n'est pas comptable :"
                          " la recette refuse de la compter 0 en silence")
        elif v["code"] != 0:
            lignes.append(f"           {v['derniere_ligne'][:120]}")
            if v["stderr"]:
                lignes.append(f"           stderr : {v['stderr'].splitlines()[-1][:120]}")

    muettes = [v["nom"] for v in resultats if v["muette"]]
    echecs = [v["nom"] for v in resultats if v["code"] != 0]
    cas = sum(v["cas_total"] or 0 for v in resultats)
    reussis = sum(v["cas_ok"] or 0 for v in resultats)
    lignes.append("")
    lignes.append(f"RECETTE forge-seo : {len(resultats)} verification(s), "
                  f"{reussis}/{cas} cas conformes")
    if echecs:
        lignes.append(f"  ECHECS : {', '.join(echecs)}")
    if muettes:
        lignes.append(f"  MUETTES (contrat de sortie « N/M » non tenu) : {', '.join(muettes)}")
    return (1 if (echecs or muettes) else 0), lignes


def fixture() -> int:
    """Preuve a double sens du runner (jamais dans la forge : dossier temporaire).

    VERTE : trois verifications posees dans un dossier vierge sont DECOUVERTES et
            jouees du seul fait d'exister -- aucune liste a mettre a jour.
    ROUGES : une verification qui echoue fait echouer la recette ; une verification
            MUETTE (sans compte « N/M ») la fait echouer aussi, au lieu d'etre
            comptee 0 en silence -- c'est exactement ainsi qu'un test cesse d'etre
            joue sans que personne ne s'en apercoive.
    """
    echecs = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "test_faux_vert.py").write_text(
            "print('  [OK  ] temoin')\nprint('3/3 preuves conformes')\n", encoding="utf-8")
        (d / "test_faux_rouge.py").write_text(
            "import sys\nprint('1/2 preuves conformes')\nsys.exit(1)\n", encoding="utf-8")
        (d / "test_faux_muet.py").write_text(
            "print('tout va bien')\n", encoding="utf-8")

        decouverts = [p.name for p in decouvrir(d)]
        ok_decouverte = decouverts == ["test_faux_muet.py", "test_faux_rouge.py", "test_faux_vert.py"]
        print(f"  [{'OK  ' if ok_decouverte else 'ECHEC'}] VERT  les 3 verifications sont "
              f"decouvertes par leur seule presence (obtenu {decouverts})")
        if not ok_decouverte:
            echecs.append("la decouverte doit etre un glob, jamais une liste en dur")

        resultats = [jouer(p) for p in decouvrir(d)]
        code, _ = rapporter(resultats)
        par_nom = {v["nom"]: v for v in resultats}

        ok_vert = par_nom["test_faux_vert.py"]["cas_total"] == 3 and par_nom["test_faux_vert.py"]["code"] == 0
        print(f"  [{'OK  ' if ok_vert else 'ECHEC'}] VERT  une verification verte est jouee "
              "et son compte de cas relu (3 cas)")
        if not ok_vert:
            echecs.append("le compte de cas d'une verification verte doit etre relu")

        ok_rouge = par_nom["test_faux_rouge.py"]["code"] == 1
        print(f"  [{'OK  ' if ok_rouge else 'ECHEC'}] ROUGE une verification qui echoue est "
              "vue comme telle (exit 1 relaye)")
        if not ok_rouge:
            echecs.append("un echec doit etre relaye")

        ok_muette = par_nom["test_faux_muet.py"]["muette"] is True
        print(f"  [{'OK  ' if ok_muette else 'ECHEC'}] ROUGE une verification sans compte "
              "« N/M » est declaree MUETTE, jamais comptee 0 en silence")
        if not ok_muette:
            echecs.append("une verification muette doit etre declaree")

        ok_verdict = code == 1
        print(f"  [{'OK  ' if ok_verdict else 'ECHEC'}] ROUGE la recette entiere sort en 1 "
              f"des qu'une verification echoue ou se tait (obtenu {code})")
        if not ok_verdict:
            echecs.append("le verdict global doit tomber a rouge")

        # VERTE de controle : les memes trois, purgees de l'echec et du mutisme,
        # rendent bien un verdict vert -- sinon le rouge ci-dessus ne prouverait rien.
        (d / "test_faux_rouge.py").unlink()
        (d / "test_faux_muet.py").unlink()
        code_vert, _ = rapporter([jouer(p) for p in decouvrir(d)])
        ok_reversible = code_vert == 0
        print(f"  [{'OK  ' if ok_reversible else 'ECHEC'}] VERT  les memes verifications, "
              f"une fois saines, rendent un verdict vert (obtenu {code_vert})")
        if not ok_reversible:
            echecs.append("le verdict vert doit etre atteignable")

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n6/6 preuves conformes")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Joue toute la suite de verification de forge-seo en une commande.")
    p.add_argument("--liste", action="store_true",
                   help="affiche ce qui SERAIT joue, sans rien executer")
    p.add_argument("--fixture", action="store_true",
                   help="preuve a double sens du runner lui-meme (dossier temporaire)")
    args = p.parse_args()

    if args.fixture:
        return fixture()

    verifications = decouvrir(SCRIPTS)
    manquantes = [n for n in VERIFICATIONS_NOMMEES if not (SCRIPTS / n).exists()]
    if manquantes:
        print(f"REFUS : verification(s) nommee(s) introuvable(s) : {manquantes}")
        return 1
    if args.liste:
        print(f"{len(verifications)} verification(s) decouverte(s) dans {SCRIPTS} :")
        for v in verifications:
            print(f"  · {v.name}")
        return 0

    print(f"RECETTE forge-seo — {len(verifications)} verification(s) decouverte(s)\n")
    resultats = [jouer(v) for v in verifications]
    code, lignes = rapporter(resultats)
    print("\n".join(lignes))
    return code


if __name__ == "__main__":
    sys.exit(main())
