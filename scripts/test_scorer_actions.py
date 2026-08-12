"""Preuve a double sens de scorer_actions.py (TF-0073, complement de TF-0056).

Aucune mission reelle, aucun reseau : une etude minimale factice est construite
dans un repertoire temporaire du systeme, comme le fait autotest.py -- rien n'est
ecrit dans la forge ni chez un client.

Trois niveaux de preuve :

  1. calculer()        -- fonction pure : formule et tri, sans disque.
  2. valider_action()  -- une action VALIDE ne remonte aucune erreur (vert) ;
                          cinq actions INVALIDES, chacune pour une raison
                          differente, remontent une erreur qui la designe (rouge).
  3. ecrire()          -- bout en bout : un contenu JSON valide produit le CSV
                          attendu, aux colonnes exactes de livrables.py, trie par
                          score, en UTF-8 SANS BOM (vert) ; un contenu invalide ne
                          fait naitre AUCUN fichier -- le refus est un vrai refus,
                          jamais une ecriture partielle (rouge).

Le decompte final (« N/N preuves conformes ») n'est PAS une constante recopiee a
la main : il compte les verifications reellement executees. Un total fige aurait
pu driver silencieusement d'un ajout de cas -- exactement le defaut que ce fichier
existe pour empecher ailleurs.

Usage :
    python scripts/test_scorer_actions.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from livrables import COLONNES_ACTIONS
from scorer_actions import calculer, ecrire, valider_action

COMPTEUR = {"total": 0}


def verif(prefixe: str, ok: bool, message: str) -> bool:
    COMPTEUR["total"] += 1
    print(f"  [{'OK  ' if ok else 'ECHEC'}] {prefixe} {message}")
    return ok


ACTION_VALIDE = {
    "id": "A1", "action": "Reecrire les balises title dupliquees", "volet": "ETAT",
    "noeuds_couverts": [43, 19, 74],
    "gain": 4, "cran_gain_cite": "gain 4 -- exemple synthetique, aucune donnee reelle",
    "effort": 2, "cran_effort_cite": "effort 2 -- exemple synthetique",
    "confiance": 4, "cran_confiance_cite": "confiance 4 -- exemple synthetique",
    "horizon": "quick-win",
    "delai_realisation": 2, "delai_effet_mesurable": 28,
    "critere_acceptation": "les balises sont uniques", "hypothese_structurante": "exemple",
    "axe_execution": "IA", "regime_automatisation": "ia-assistee-validation-humaine",
    "axe_cout": "GRATUIT", "cout_eur": 0, "trimestre_cible": "T1",
    "dependance_de": None,
}

ACTION_STRUCTURANTE = {
    **ACTION_VALIDE,
    "id": "A2", "action": "Fusionner les pages sous 300 mots", "volet": "ETAT",
    "noeuds_couverts": "74, 25 66",   # separateurs melanges -- doit rester lisible
    "gain": 5, "effort": 4, "confiance": 3, "horizon": "structurant",
    "dependance_de": "A1",
}


def cas_calcul() -> list[str]:
    """VERT -- formule (gain x confiance) / effort, tri decroissant, jamais
    relue depuis le contenu meme si un champ `score` y trainait."""
    echecs = []
    lignes = calculer([ACTION_VALIDE, ACTION_STRUCTURANTE])

    attendu_a1 = round(4 * 4 / 2, 2)   # 8.0
    attendu_a2 = round(5 * 3 / 4, 2)   # 3.75
    ok_a1 = lignes[0]["id"] == "A1" and lignes[0]["score"] == attendu_a1
    ok_a2 = lignes[1]["id"] == "A2" and lignes[1]["score"] == attendu_a2
    if not verif("VERT ", ok_a1,
                 f"A1 : score calcule {lignes[0]['score']} (attendu {attendu_a1}), en tete du tri"):
        echecs.append("calculer() : score ou tri incorrect pour A1")
    if not verif("VERT ", ok_a2,
                 f"A2 : score calcule {lignes[1]['score']} (attendu {attendu_a2}), "
                 "separateurs melanges lus quand meme"):
        echecs.append("calculer() : score ou tri incorrect pour A2")

    ok_noeuds = lignes[1]["noeuds_couverts"] == "74 25 66"
    if not verif("VERT ", ok_noeuds,
                 f"noeuds_couverts normalise en identifiants espaces : "
                 f"{lignes[1]['noeuds_couverts']!r}"):
        echecs.append("calculer() : normalisation de noeuds_couverts incorrecte")

    ok_dep = lignes[0]["dependance_de"] == "" and lignes[1]["dependance_de"] == "A1"
    if not verif("VERT ", ok_dep,
                 "dependance_de absente -> chaine vide, presente -> conservee"):
        echecs.append("calculer() : dependance_de mal normalisee")
    return echecs


def cas_validation() -> list[str]:
    """1 action VALIDE (vert) + 5 variantes INVALIDES (rouge), chacune pour une
    raison distincte -- pas un fourre-tout qui masquerait laquelle echoue."""
    echecs = []
    connus = {"A1"}

    ok_vert = valider_action(ACTION_VALIDE, connus) == []
    if not verif("VERT ", ok_vert, "action conforme -- aucune erreur remontee"):
        echecs.append("valider_action() : une action conforme a ete rejetee")

    variantes = [
        ("gain 6, hors echelle 1-5", {**ACTION_VALIDE, "gain": 6}, "gain"),
        ("horizon avec espace au lieu du trait d'union du schema",
         {**ACTION_VALIDE, "horizon": "quick win"}, "horizon"),
        ("axe_execution hors vocabulaire", {**ACTION_VALIDE, "axe_execution": "AUTOMATIQUE"},
         "axe_execution"),
        ("champ obligatoire absent (critere_acceptation)",
         {k: v for k, v in ACTION_VALIDE.items() if k != "critere_acceptation"},
         "manquant"),
        ("dependance_de vers une action inconnue du lot",
         {**ACTION_VALIDE, "dependance_de": "A99"}, "dependance_de"),
    ]
    for motif, action, attendu_dans_message in variantes:
        erreurs = valider_action(action, connus)
        capte = bool(erreurs) and any(attendu_dans_message in e for e in erreurs)
        if not verif("ROUGE", capte,
                     f"{motif} -- {erreurs[0] if erreurs else 'AUCUNE ERREUR (defaut)'}"):
            echecs.append(f"valider_action() : cas non capte -- {motif}")
    return echecs


def cas_ecriture_bout_en_bout() -> list[str]:
    """VERT : contenu valide -> CSV exact, trie, UTF-8 sans BOM.
    ROUGE : contenu invalide -> ecrire() refuse et n'ecrit RIEN -- pas un fichier
    a moitie rempli qui se presenterait comme complet."""
    echecs = []
    with tempfile.TemporaryDirectory(prefix="forge-seo-test-scorer-") as tmp:
        projet = Path(tmp) / "mission-factice"
        base = projet / "seo"
        (base / "livrables").mkdir(parents=True)
        (base / "etat.json").write_text(
            json.dumps({"domaine": "exemple-synthetique.test"}, indent=2), encoding="utf-8"
        )

        contenu_ok = projet / "actions-valides.json"
        contenu_ok.write_text(
            json.dumps([ACTION_VALIDE, ACTION_STRUCTURANTE], ensure_ascii=False), encoding="utf-8"
        )

        code = ecrire(projet, contenu_ok, verifier=False)
        csvs = sorted((base / "livrables").glob("actions-exemple-synthetique.test-*.csv"))
        ok_code = code == 0
        ok_un_fichier = len(csvs) == 1
        if not verif("VERT ", ok_code, f"ecrire() rend 0 sur contenu valide (obtenu {code})"):
            echecs.append("ecrire() : code de retour incorrect sur contenu valide")
        if not verif("VERT ", ok_un_fichier, f"exactement 1 CSV cree (obtenu {len(csvs)})"):
            echecs.append("ecrire() : nombre de fichiers crees incorrect")

        # Les trois controles suivants portent sur le contenu du CSV : gardes par
        # des valeurs sures si le fichier manque, pour que ce cas imprime toujours
        # le meme nombre de preuves, echec ou pas.
        brut = csvs[0].read_bytes() if csvs else b""
        ok_sans_bom = bool(brut) and not brut.startswith(b"\xef\xbb\xbf")
        if not verif("VERT ", ok_sans_bom,
                     "CSV ecrit en UTF-8 SANS BOM (decision TF-0056, alignee sur livrables.py)"):
            echecs.append("ecrire() : BOM present ou fichier absent -- BOM devrait etre absent")

        lignes = brut.decode("utf-8").splitlines() if brut else []
        entete = lignes[0].split(",") if lignes else []
        ok_entete = entete == COLONNES_ACTIONS
        if not verif("VERT ", ok_entete,
                     "en-tete = COLONNES_ACTIONS de livrables.py (source unique)"):
            echecs.append("ecrire() : en-tete du CSV ne correspond pas a COLONNES_ACTIONS")

        id_col = COLONNES_ACTIONS.index("id")
        ordre = [l.split(",")[id_col] for l in lignes[1:] if l.strip()] if len(lignes) > 1 else []
        ok_tri = ordre == ["A1", "A2"]
        if not verif("VERT ", ok_tri, f"lignes triees par score decroissant (obtenu {ordre})"):
            echecs.append("ecrire() : ordre des lignes incorrect")

        # --- ROUGE : contenu invalide, aucune ecriture -------------------------
        contenu_ko = projet / "actions-invalides.json"
        contenu_ko.write_text(
            json.dumps([{**ACTION_VALIDE, "id": "A9", "effort": 0}], ensure_ascii=False),
            encoding="utf-8",
        )
        avant = sorted((base / "livrables").glob("actions-exemple-synthetique.test-*.csv"))
        code_ko = ecrire(projet, contenu_ko, verifier=False)
        apres = sorted((base / "livrables").glob("actions-exemple-synthetique.test-*.csv"))
        ok_refus = code_ko == 1
        ok_rien_ecrit = avant == apres   # aucun nouveau fichier, aucun remplacement
        if not verif("ROUGE", ok_refus,
                     f"effort=0 (hors echelle 1-5) -- ecrire() rend {code_ko} (attendu 1)"):
            echecs.append("ecrire() : code de retour incorrect sur contenu invalide")
        if not verif("ROUGE", ok_rien_ecrit, "le refus n'a ecrit ni remplace aucun fichier"):
            echecs.append("ecrire() : le cas invalide aurait du refuser sans rien ecrire")

    return echecs


def main() -> int:
    print("scorer_actions.py -- calcul du score")
    echecs = cas_calcul()
    print("\nscorer_actions.py -- validation des champs")
    echecs += cas_validation()
    print("\nscorer_actions.py -- ecriture du CSV, bout en bout")
    echecs += cas_ecriture_bout_en_bout()

    total = COMPTEUR["total"]
    if echecs:
        print(f"\nECHECS ({len(echecs)}/{total}) : {echecs}")
        return 1
    print(f"\n{total}/{total} preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
