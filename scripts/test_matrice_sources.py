"""Preuve a double sens du controle 15 : la matrice des sources suit la grille (TF-1869).

CE QUI A ETE MESURE. `referentiel/sources-donnees.md` n'avait pas ete touche entre le 08/08/2026
(grille a 87 noeuds) et le 18/10/2026. La grille est passee a 89 noeuds et a decale 68 identifiants :
la matrice envoyait « 34 » sur Sitemap quand Search Console etait devenu 35, le tableau « Principe »
annoncait 53 noeuds sur 87, et la ligne « Export GSC » listait 17 identifiants pour « 16 noeuds ».
Les controles 12 (registre de correspondance) et 13 (syntheses de la grille) etaient verts : aucun
controle ne lisait ce fichier. Le premier cas ci-dessous rejoue l'etat d'avant sur la grille du jour.

Chaque cas rouge est FAUX sur un seul point et JUSTE sur tout le reste, et son remede est rejoue
jusqu'au vert. Rien n'est fige en dur : les lignes perturbees sont lues dans le referentiel reel, si
bien qu'une evolution legitime de la grille ne casse pas ce test pour une autre raison que la sienne.

TF-1894 etend la preuve aux textes HORS matrice (section D) : le 19/10/2026, apres le realignement de
la matrice, le cadrage, les gabarits, le README et la synthese de la grille disaient encore « 16 »,
« 5 » et « 4 noeuds », « noeud 29 » pour les logs, « 7 branches » et « 53 noeuds sur 87 ». La section D
rejoue cet etat, puis chaque defaut seul, et le cas qui dit « 87 noeuds ».

Usage :
    python scripts/test_matrice_sources.py
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate  # noqa: E402
from validate import (  # noqa: E402
    FICHIER_SOURCES,
    TEXTES_HORS_MATRICE,
    controler_matrice_sources,
    controler_textes_hors_matrice,
)

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


def ecarts_de(texte: str) -> list[str]:
    """Les ecarts du controle 15 sur un TEXTE donne (ecrit puis relu, comme en vrai)."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "sources-donnees.md"
        f.write_text(texte, encoding="utf-8")
        ecarts, _ = controler_matrice_sources(f)
    return ecarts


def dit(ecarts: list[str], morceau: str) -> bool:
    return any(morceau.lower() in e.lower() for e in ecarts)


REEL = FICHIER_SOURCES.read_text(encoding="utf-8")
LIGNES = REEL.splitlines()


def ligne(debut: str) -> str:
    return next(l for l in LIGNES if l.startswith(debut))


print("Test de la matrice des sources contre la grille (TF-1869)\n")

# ---- A · LA VERTE ET L'ETAT D'AVANT -----------------------------------------------------------
print("A. le referentiel reel et l'etat d'avant")
ecarts, resume = controler_matrice_sources()
verifier(ecarts == [], f"VERTE : le referentiel reel passe ({resume})")

# L'etat d'avant, tel que le depot le portait a 87 noeuds : numeros d'avant l'insertion des noeuds
# 21 et 59, « 16 noeuds » pour 17 identifiants, « 53 sur 87 ».
avant = (
    REEL
    .replace(ligne("| **Export GSC**"),
             "| **Export GSC** | à demander | 5, 17, 19, 34-37, 39, 43, 48, 52, 68, 69, 70, 73, 74, 75 "
             "| sans export **ni connecteur** : **16 nœuds** en non mesurable |")
    .replace("55 nœuds sur 89", "53 nœuds sur 87")
)
ecarts = ecarts_de(avant)
verifier(dit(ecarts, "« Export GSC » cite le nœud 34 « Sitemap »"),
         "ROUGE : « 34 » sur Sitemap quand Search Console est le 35 est refuse (numero decale)")
verifier(dit(ecarts, "« Export GSC » écrit 16 nœud(s) et en liste 17"),
         "ROUGE : « 16 nœuds » pour 17 identifiants listes est refuse")
verifier(dit(ecarts, "tableau « Principe »"), "ROUGE : « 53 nœuds sur 87 » dans une grille de 89 est refuse")
verifier(ecarts_de(avant.replace("53 nœuds sur 87", "55 nœuds sur 89").replace(
    "5, 17, 19, 34-37, 39, 43, 48, 52, 68, 69, 70, 73, 74, 75", "5, 17, 19, 35-38, 40, 44, 49, 53, 70, 71, 72, 75, 76, 77"
).replace("**16 nœuds** en non mesurable |", "**17 nœuds** en non mesurable |")) == [],
    "remede rejoue : numeros realignes, compte egal aux identifiants, « 55 sur 89 » repasse au vert")

# ---- B · UN SEUL DEFAUT A LA FOIS -------------------------------------------------------------
print("\nB. un defaut a la fois, juste sur tout le reste")
gsc = ligne("| **Export GSC**")

# 1. Un identifiant decale d'un rang.
decale = gsc.replace("35-38", "34-37")
verifier(decale != gsc, "(controle de la fixture) la plage 35-38 est bien dans la ligne « Export GSC »")
ecarts = ecarts_de(REEL.replace(gsc, decale))
# Deux ecarts attendus, pas un : la ligne « Connecteur GSC » herite des identifiants de l'export.
verifier(len(ecarts) == 2 and all("nœud 34 « Sitemap »" in e for e in ecarts),
         "ROUGE : un seul numero decale d'un rang est refuse (ligne export + ligne connecteur heritee), et lui seul")
verifier(ecarts_de(REEL.replace(gsc, decale).replace(decale, gsc)) == [],
         "remede rejoue : remettre 35-38 repasse au vert")

# 2. Un compte qui n'egale pas les identifiants listes.
faux = gsc.replace("**17 nœuds**", "**16 nœuds**")
verifier(faux != gsc, "(controle de la fixture) « 17 nœuds » est bien dans la ligne « Export GSC »")
ecarts = ecarts_de(REEL.replace(gsc, faux))
verifier(len(ecarts) == 1 and dit(ecarts, "écrit 16 nœud(s) et en liste 17"),
         "ROUGE : un compte ecrit different du nombre d'identifiants est refuse, et lui seul")
verifier(ecarts_de(REEL.replace(gsc, faux).replace(faux, gsc)) == [],
         "remede rejoue : remettre le compte repasse au vert")

# 3. Le compte de la ligne connecteur, qui herite des identifiants de l'export.
con = ligne("| **Connecteur GSC**")
ecarts = ecarts_de(REEL.replace(con, con.replace("**17 nœuds** sont mesurables", "**16 nœuds** sont mesurables")))
verifier(dit(ecarts, "« Connecteur GSC » écrit 16 nœud(s) et en liste 17"),
         "ROUGE : la ligne connecteur est comptee contre les identifiants de l'export dont elle herite")

# 4. Un identifiant qui n'existe pas dans la grille.
nb = int(re.search(r"sur (\d+) restent", REEL).group(1))
ecarts = ecarts_de(REEL.replace("| 30 | 1 nœud", f"| 30, {nb + 1} | 1 nœud"))
verifier(dit(ecarts, f"nœud {nb + 1}, absent de la grille"),
         f"ROUGE : un identifiant {nb + 1} hors d'une grille de {nb} noeuds est refuse")

# 5. Le tableau « Principe ».
for faux_p, quoi in (
    (REEL.replace(f"sur {nb} restent", f"sur {nb - 2} restent"), "le total de la grille"),
    (re.sub(r"(\d+) nœuds sur (\d+) restent", lambda m: f"{int(m.group(1)) - 2} nœuds sur {m.group(2)} restent", REEL),
     "le nombre de noeuds instrumentes"),
    (re.sub(r"(\d+) basculent", lambda m: f"{int(m.group(1)) + 1} basculent", REEL),
     "le nombre de noeuds non mesurables"),
):
    ecarts = ecarts_de(faux_p)
    verifier(len(ecarts) == 1 and dit(ecarts, "tableau « Principe »"),
             f"ROUGE : un tableau « Principe » faux sur {quoi} est refuse, et lui seul")
verifier(ecarts_de(REEL) == [], "remede rejoue : la phrase du referentiel reel repasse au vert")

# ---- C · BORNES -------------------------------------------------------------------------------
print("\nC. bornes — un fichier qui ne dit rien ne passe pas pour juste")
sans_matrice = REEL.split("\n## Matrice source", 1)[0]
ecarts = ecarts_de(sans_matrice)
verifier(dit(ecarts, "Matrice source"),
         "ROUGE : sans section « Matrice source », le controle le dit au lieu de passer au vert")
sans_principe = re.sub(r"\d+ nœuds sur \d+ restent instrumentés et \d+ basculent en non mesurable",
                       "une partie des nœuds reste instrumentée", REEL)
verifier(dit(ecarts_de(sans_principe), "phrase « N nœuds sur M"),
         "ROUGE : sans la phrase du tableau « Principe », le controle le dit")
renvoi_mort = REEL.replace("que la ligne « Export GA »", "que la ligne « Export GAX »")
verifier(dit(ecarts_de(renvoi_mort), "« Export GAX »"),
         "ROUGE : une ligne connecteur qui renvoie a une ligne inexistante est refusee")

# ---- D · LES TEXTES HORS MATRICE (TF-1894) ----------------------------------------------------
print("\nD. les textes hors matrice — README, methode, cadrage, grille, gabarits")
LUS = {p.relative_to(validate.RACINE).as_posix(): p.read_text(encoding="utf-8") for p in TEXTES_HORS_MATRICE}
README, CADRAGE = "README.md", "referentiel/cadrage.template.md"
GRILLE, GABARITS = "referentiel/grille-noeuds.md", "scripts/gabarits.py"


def ecarts_textes(textes: dict[str, str], **kw) -> list[str]:
    return controler_textes_hors_matrice(textes, **kw)[0]


def perturber(fichier: str, motif: str, delta: int, groupe: int = 1) -> tuple[dict[str, str], int]:
    """Les textes REELS, dont UN nombre (le groupe `groupe` du motif) est decale de `delta`."""
    texte = LUS[fichier]
    m = re.search(motif, texte)
    assert m, f"fixture : motif absent de {fichier} : {motif}"
    valeur = int(m.group(groupe)) + delta
    return {**LUS, fichier: texte[:m.start(groupe)] + str(valeur) + texte[m.end(groupe):]}, valeur


ecarts, resume = controler_textes_hors_matrice()
verifier(ecarts == [] and ecarts_textes(LUS) == [],
         f"VERTE : les textes hors matrice du depot passent ({resume})")
verifier(int(re.search(r"(\d+) affirmation", resume).group(1)) > 0,
         "la verte juge bien des affirmations (un controle qui ne lit rien serait vert pour rien)")

# 1. L'etat du 19/10/2026 : les defauts du constat d'origine, tous ensemble, sur les textes du jour.
avant = {
    **LUS,
    README: re.sub(r"alimente (\d+) nœuds répartis dans (\d+) branches",
                   lambda m: f"alimente {int(m.group(1)) - 1} nœuds répartis dans {int(m.group(2)) - 1} branches",
                   LUS[README]),
    CADRAGE: re.sub(r"invisibles \(nœud (\d+)\)", lambda m: f"invisibles (nœud {int(m.group(1)) - 1})",
                    re.sub(r"\*\*(\d+) nœuds\*\* en non mesurable",
                           lambda m: f"**{int(m.group(1)) - 1} nœuds** en non mesurable", LUS[CADRAGE])),
    GRILLE: re.sub(r"(\d+) nœuds sur (\d+) restent instrumentés \((\d+) %\)",
                   lambda m: f"{int(m.group(1)) - 2} nœuds sur {int(m.group(2)) - 2} restent instrumentés (61 %)",
                   LUS[GRILLE]).replace("mobilise les 89 nœuds", "mobilise les 87 nœuds"),
    GABARITS: re.sub(r"(Sans export GSC ni connecteur : |Sans export GA ni connecteur : |Sans CRM : )(\d+)",
                     lambda m: f"{m.group(1)}{int(m.group(2)) - 1}",
                     re.sub(r"alimente\s+(\d+) noeuds repartis dans (\d+) branches",
                            lambda m: f"alimente {int(m.group(1)) - 1} noeuds repartis dans {int(m.group(2)) - 1} branches",
                            LUS[GABARITS])),
}
ecarts = ecarts_textes(avant)
verifier(all(avant[f] != LUS[f] for f in (README, CADRAGE, GRILLE, GABARITS)),
         "(controle de la fixture) les quatre textes du constat d'origine sont bien perturbes")
for fichier, morceau, quoi in (
    (README, "branches des nœuds de l'export GSC", "« 7 branches » pour un export GSC"),
    (README, "ligne « Export GSC »", "« 16 nœuds » pour l'export GSC, dans le README"),
    (CADRAGE, "ligne « Export GSC »", "« 16 nœuds » pour Search Console, dans le cadrage"),
    (CADRAGE, "ligne « Export GA »", "« 5 nœuds » pour GA, dans le cadrage"),
    (CADRAGE, "ligne « CRM / e-commerce »", "« 4 nœuds » pour le CRM, dans le cadrage"),
    (CADRAGE, "pour les logs serveur", "« nœud 29 » pour les logs, dans le cadrage"),
    (GRILLE, "nœuds instrumentés sans export", "« 53 nœuds » instrumentés, dans la grille"),
    (GRILLE, "total de la grille", "« sur 87 », dans la grille"),
    (GRILLE, "part des nœuds instrumentés", "« 61 % » pour 55 sur 89, dans la grille"),
    (GRILLE, "n'est aucun compte de la grille", "« les 87 nœuds », dans la grille"),
    (GABARITS, "ligne « Export GSC »", "« 16 noeuds » pour GSC, dans les gabarits"),
    (GABARITS, "ligne « Export GA »", "« 5 noeuds » pour GA, dans les gabarits"),
    (GABARITS, "ligne « CRM / e-commerce »", "« 4 noeuds » pour le CRM, dans les gabarits"),
    (GABARITS, "branches des nœuds de l'export GSC", "« 7 branches » dans les gabarits"),
):
    verifier(any(e.startswith(fichier) and morceau in e for e in ecarts), f"ROUGE (etat du 19/10) : {quoi} est refuse")
verifier(ecarts_textes({**avant, README: LUS[README], CADRAGE: LUS[CADRAGE], GRILLE: LUS[GRILLE],
                        GABARITS: LUS[GABARITS]}) == [],
         "remede rejoue : les quatre textes remis a leur valeur repassent au vert")

# 2. Un defaut a la fois, juste sur tout le reste, remede rejoue.
cas = (
    (README, r"alimente (\d+) nœuds répartis", -1, 1, "ligne « Export GSC »", "README : le compte de l'export GSC"),
    (README, r"répartis dans (\d+) branches", -1, 1, "branches des nœuds de l'export GSC", "README : le nombre de branches"),
    (README, r"(\d+) nœuds, un barème", -2, 1, "n'est aucun compte de la grille", "README : le total de la grille"),
    (GABARITS, r"export GSC ni connecteur : (\d+)", -1, 1, "ligne « Export GSC »", "gabarits : le compte GSC"),
    (GABARITS, r"export GA ni connecteur : (\d+)", -1, 1, "ligne « Export GA »", "gabarits : le compte GA"),
    (GABARITS, r"Sans CRM : (\d+)", -1, 1, "ligne « CRM / e-commerce »", "gabarits : le compte CRM"),
    (GABARITS, r"repartis dans (\d+) branches", -1, 1, "branches des nœuds de l'export GSC", "gabarits : le nombre de branches"),
    (CADRAGE, r"\*\*(\d+) nœuds\*\* en non mesurable : positions", -1, 1, "ligne « Export GSC »", "cadrage : le compte GSC"),
    (CADRAGE, r"\*\*(\d+) nœuds\*\* en non mesurable : trafic référent", -1, 1, "ligne « Export GA »", "cadrage : le compte GA"),
    (CADRAGE, r"\*\*(\d+) nœuds\*\* en non mesurable\. \*\*Aucun gain ne peut être exprimé en euros", -1, 1,
     "ligne « CRM / e-commerce »", "cadrage : le compte CRM"),
    (CADRAGE, r"invisibles \(nœud (\d+)\)", -1, 1, "pour les logs serveur", "cadrage : le numero du noeud des logs"),
    (CADRAGE, r"transforment (\d+) nœuds non mesurables", 1, 1, "nœuds non mesurables sans export", "cadrage : le total non mesurable"),
    (GRILLE, r"(\d+) nœuds sur \d+ restent", -1, 1, "nœuds instrumentés sans export", "grille : les noeuds instrumentes"),
    (GRILLE, r"\d+ nœuds sur (\d+) restent", -2, 1, "total de la grille", "grille : le total apres « sur »"),
    (GRILLE, r"restent instrumentés \((\d+) %\)", -1, 1, "part des nœuds instrumentés", "grille : le pourcentage"),
    (GRILLE, r"(\d+) basculent en non mesurable", 1, 1, "nœuds non mesurables sans export", "grille : le total non mesurable"),
    (GRILLE, r"(\d+) `EX`", 1, 1, "nœuds `EX`", "grille : le compte EX"),
    (GRILLE, r"(\d+) `NM`", 1, 1, "nœuds `NM`", "grille : le compte NM"),
    (GRILLE, r"mobilise les (\d+) nœuds", -2, 1, "n'est aucun compte de la grille", "grille : « mobilise les N noeuds »"),
)
for fichier, motif, delta, groupe, morceau, quoi in cas:
    textes, valeur = perturber(fichier, motif, delta, groupe)
    ecarts = ecarts_textes(textes)
    verifier(len(ecarts) == 1 and ecarts[0].startswith(fichier) and morceau in ecarts[0]
             and (str(valeur) in ecarts[0]),
             f"ROUGE : {quoi} ({valeur}) est refuse, et lui seul")
    verifier(ecarts_textes({**textes, fichier: LUS[fichier]}) == [], f"remede rejoue : {quoi} remis, vert")

# 3. Le cas demande : un texte qui dit « 87 noeuds » dans une grille de 89 echoue.
textes, valeur = perturber(README, r"(\d+) nœuds, un barème", -2)
verifier(valeur == 87 and dit(ecarts_textes(textes), "« 87 nœuds »"),
         "ROUGE : un texte qui dit « 87 nœuds » dans une grille de 89 est refuse")

# 4. Ce qui ne doit PAS echouer : un fait d'histoire, « de 82 a 87 noeuds ».
verifier(ecarts_textes({**LUS, README: LUS[README] + "\nLe passage de 82 à 87 nœuds en a déplacé 14.\n"}) == [],
         "VERTE : « de 82 à 87 nœuds » (un fait d'histoire, pas une affirmation sur la grille) n'est pas juge")

# 5. Bornes : un controle qui ne lit rien, ou qui n'a rien a quoi comparer, le dit.
verifier(dit(ecarts_textes({"vide.md": "Aucun compte de nœuds ici."}), "ne lit plus rien"),
         "ROUGE : des textes sans aucune affirmation de noeuds ne passent pas pour justes")
with tempfile.TemporaryDirectory() as d:
    sans_logs = Path(d) / "sources-donnees.md"
    sans_logs.write_text(REEL.replace(ligne("| **Logs serveur**"), ""), encoding="utf-8")
    verifier(dit(ecarts_textes(LUS, sources=sans_logs), "« Logs serveur » absente"),
             "ROUGE : sans ligne « Logs serveur » dans la matrice, le controle le dit au lieu de juger dans le vide")

# 6. Le cablage : le controle 15 de validate.py, joue tel quel, juge ces textes.
def controle_15_de_validate(textes: dict[str, str]) -> dict:
    """Le controle 15 tel que `validate.py --json` le rend, sur des copies jetables des textes."""
    with tempfile.TemporaryDirectory() as d:
        chemins = []
        for nom, texte in textes.items():
            copie = Path(d) / Path(nom).name
            copie.write_text(texte, encoding="utf-8")
            chemins.append(copie)
        avant_chemins = validate.TEXTES_HORS_MATRICE
        validate.TEXTES_HORS_MATRICE = tuple(chemins)
        sortie = io.StringIO()
        try:
            with contextlib.redirect_stdout(sortie):
                validate.valider_referentiel(json_mode=True)
        finally:
            validate.TEXTES_HORS_MATRICE = avant_chemins
    return next(c for c in json.loads(sortie.getvalue())["controles"] if c["nom"].startswith("15."))


c15 = controle_15_de_validate(LUS)
verifier(c15["ok"] and "hors matrice" in c15["nom"], "VERTE : le controle 15 de validate.py passe sur les textes du depot et le dit")
textes, valeur = perturber(README, r"alimente (\d+) nœuds répartis", -1)
c15 = controle_15_de_validate(textes)
verifier(not c15["ok"] and any("README.md" in l and str(valeur) in l for l in c15["lignes"]),
         "ROUGE : le controle 15 de validate.py ECHOUE sur un README faux, et nomme le fichier")

print(f"\n{_ok}/{_ok + len(_ko)} cas conformes")
if _ko:
    for quoi in _ko:
        print(f"  ECHEC : {quoi}")
sys.exit(1 if _ko else 0)
