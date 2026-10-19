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

Usage :
    python scripts/test_matrice_sources.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate import FICHIER_SOURCES, controler_matrice_sources  # noqa: E402

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

print(f"\n{_ok}/{_ok + len(_ko)} cas conformes")
if _ko:
    for quoi in _ko:
        print(f"  ECHEC : {quoi}")
sys.exit(1 if _ko else 0)
