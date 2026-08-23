"""Preuve a double sens du controle 10 — plan de mesure d'un noeud NON REPRODUCTIBLE (TF-0476).

CE QUI A ETE MESURE, ET POURQUOI C'EST LE FRERE DU NOEUD 31. TF-0264 avait corrige un cas exact :
le noeud Performance declare CONFORME sur une mesure de laboratoire quand le terrain donnait
cinquante fois pire. Le correctif — `controler_verdicts_de_terrain` — affirme dans son docstring
ne lire aucun identifiant de noeud en dur : « il interroge source_requise, donc il suit la grille
si elle evolue ». MESURE SUR LE DEPOT (HEAD 55f76c8, 19/08) : son predicat est le mot litteral
« crux », et `noeud_exige_terrain()` rend True sur la source du noeud 31 et False sur celle du
noeud 57. Le controle ne suivait donc pas la grille : IL SUIVAIT UNE SEULE FAMILLE DE SOURCE.

Le noeud 57 (Presence Dans Les Reponses IA) est la meme classe de defaut, autre source : un
verdict affirmatif rendu sur une grandeur que la source ne porte pas. La grille declare
elle-meme, et depuis toujours, que son resultat est « non reproductible et non stable : ne jamais
presenter le taux comme une metrique de suivi fiable ». Cette phrase vivait dans le referentiel et
NULLE PART AILLEURS — la fiche que l'auditeur remplit ne la portait pas (0 occurrence), son
front-matter n'offrait aucun champ de plan, et son critere de verdict se lisait « taux de citation
sur les requetes cibles, releve et date ». UN TAUX DATE SUFFISAIT DONC FORMELLEMENT.

Ce que dit l'etat de l'art, et ce n'est pas un avis : la langue de la requete explique 26,5 % de
la variance d'une reponse et l'identite de la marque 1,5 % (ICC 0,0146, decomposition REML sur
12 933 reponses, arXiv 2607.13304) ; le reechantillonnage PUR pese 34,8 % sur le sous-ensemble de
stabilite ; et l'hypothese produit des outils du marche — « le prompt de suivi represente
l'intention d'achat » — est testee et INVALIDEE (arXiv 2605.27440).

Usage :
    python scripts/test_plan_de_mesure.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate import (  # noqa: E402
    controler_plan_de_mesure,
    noeud_non_reproductible,
)

RESERVE_57 = (
    "résultat non reproductible et non stable : le déclarer explicitement, ne jamais "
    "présenter le taux comme une métrique de suivi fiable"
)
BASE = Path(".")
_ok = 0
_ko: list[str] = []


def verifier(condition: bool, quoi: str) -> None:
    global _ok
    if condition:
        _ok += 1
        print(f"  [OK ] {quoi}")
    else:
        _ko.append(quoi)
        print(f"  [KO ] {quoi}")


def fiche(**champs) -> dict:
    base = {"id": 57, "noeud": "Présence Dans Les Réponses IA", "reserve": RESERVE_57}
    return {**base, **champs}


PLAN_COMPLET = {
    "plan_formulations": "6",
    "plan_langues": "fr, en",
    "plan_surfaces": "surface A, surface B",
    "plan_reexecutions": "3",
    "plan_dates": "2026-08-10, 2026-08-17, 2026-08-23",
    "dispersion": "12 % a 31 % selon la reexecution (ecart-type 8,4)",
}

print("Test du controle 10 — plan de mesure (TF-0476)\n")

# ---- le PREDICAT suit la grille, jamais un identifiant -------------------------------------
verifier(noeud_non_reproductible(RESERVE_57), "la reserve de la grille declenche le controle")
verifier(not noeud_non_reproductible("SD"), "un noeud sans reserve n'est pas concerne")
verifier(not noeud_non_reproductible(None), "une reserve absente ne declenche rien")
verifier(
    not noeud_non_reproductible("donnees de terrain publiques (CrUX / PageSpeed Insights)"),
    "le noeud 31 (terrain) n'est PAS capte ici : c'est le controle 9 qui le juge",
)

# ---- A1 · ROUGE : un taux, mono-formulation, mono-langue, une execution, verdict affirmatif --
ecarts, resume = controler_plan_de_mesure(BASE, [fiche(verdict="conforme")])
verifier(len(ecarts) == 1, "verdict affirmatif SANS aucun plan : refuse (1 ecart)")
verifier("manque" in ecarts[0] and "plan_formulations" in ecarts[0],
         "le constat NOMME les champs manquants")
verifier("26,5" in ecarts[0] and "1,5" in ecarts[0],
         "le constat porte l'ordre de grandeur : la langue pese 26,5 %, la marque 1,5 %")
verifier("non-mesure" in ecarts[0], "le constat dit le verdict ATTENDU a la place")

mono = {**PLAN_COMPLET, "plan_formulations": "1", "plan_langues": "fr", "plan_reexecutions": "1"}
ecarts, _ = controler_plan_de_mesure(BASE, [fiche(verdict="conforme", **mono)])
verifier(any("n'est pas un plan" in e for e in ecarts),
         "UNE SEULE execution est refusee : c'est un tirage, pas une mesure")
verifier(any("TENDANCE" in e for e in ecarts),
         "le constat nomme le pire usage : deux runs feraient une tendance sur du bruit")

sans_dispersion = {**PLAN_COMPLET, "dispersion": "null"}
ecarts, _ = controler_plan_de_mesure(BASE, [fiche(verdict="conforme", **sans_dispersion)])
verifier(len(ecarts) == 1 and "SANS DISPERSION" in ecarts[0],
         "un chiffre nu, sans dispersion, n'est pas un taux")

# ---- A2 · VERTE : le meme noeud avec plan declare et dispersion affichee --------------------
ecarts, resume = controler_plan_de_mesure(BASE, [fiche(verdict="conforme", **PLAN_COMPLET)])
verifier(ecarts == [], "plan complet + dispersion : ACCEPTE")
verifier("1 noeud(s) declare(s) non reproductible(s)" in resume,
         "le resume DIT combien de noeuds etaient concernes")

# ---- A3 · CONTRE-EPREUVE anti-faux-positif -------------------------------------------------
# Une absence LEGITIME ne devient pas un echec : sinon l'exigence apprend a etre contournee.
for verdict in ("non-mesure", "sans-objet", None):
    ecarts, _ = controler_plan_de_mesure(BASE, [fiche(verdict=verdict)])
    verifier(ecarts == [], f"verdict « {verdict} » sans plan : PASSE (absence assumee)")

ecarts, resume = controler_plan_de_mesure(BASE, [{"id": 31, "noeud": "Performance",
                                                  "reserve": "", "verdict": "conforme"}])
verifier(ecarts == [] and "aucun noeud declare non reproductible" in resume,
         "une grille sans noeud non reproductible rend un resume explicite, jamais un echec muet")

# La recette du depot lit un compte « N/M cas » : une verification sans compte comptable est
# declaree MUETTE et refusee — un total qu on ne peut pas lire vaut zero.
print(f"\n{_ok}/{_ok + len(_ko)} cas conformes")
if _ko:
    for quoi in _ko:
        print(f"  ECHEC : {quoi}")
sys.exit(1 if _ko else 0)
