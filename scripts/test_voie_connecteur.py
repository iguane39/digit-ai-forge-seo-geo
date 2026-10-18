"""Preuve a double sens de la voie « connecteur » de Search Console et de GA4 (TF-1854).

CE QUI A ETE MESURE. `referentiel/sources-donnees.md` declarait « Absents, sans exception : Google
Search Console, Google Analytics » et laissait 16 noeuds non mesurables faute d'export. Le 17/10/2026,
un produit a lu Search Console (`sites.list` 200, `searchAnalytics/query` 200) et GA4 (`runReport`
200) avec le compte de son client, en portees de lecture. La phrase etait fausse, et AUCUN controle ne
jugeait ce referentiel : il etait lu par des agents, juge par personne.

DEUX CONTROLES, JOUES ICI DANS LES DEUX SENS (une fixture verte qui passe, une rouge qui echoue pour
la bonne raison, et le remede propose par le message rejoue jusqu'au vert) :

  - `validate.controler_voie_connecteur` (controle 14 du referentiel) juge le TEXTE : la voie existe,
    avec ses garde-fous, son renvoi vers la procedure du pilot, sa ligne de matrice, sans identifiant ;
  - `validate.controler_lectures_connecteur` (controle 6 d'une etude) juge les MESURES : une lecture
    par connecteur est T1 et porte sa date de lecture et sa periode.

Puis les LECTEURS du referentiel : le schema du snapshot et `rapport_html.manque_a_fournir` ne
refusent pas une source ouverte par connecteur (contre-epreuve : une source fermee reste demandee).

Usage :
    python scripts/test_voie_connecteur.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from grille import RACINE  # noqa: E402
from rapport_html import manque_a_fournir  # noqa: E402
from schema import valider  # noqa: E402
from validate import (  # noqa: E402
    FICHIER_SOURCES,
    controler_lectures_connecteur,
    controler_voie_connecteur,
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


def texte_sources(texte: str) -> list[str]:
    """Les ecarts que le controle 14 rend sur un TEXTE donne (ecrit puis relu, comme en vrai)."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "sources-donnees.md"
        f.write_text(texte, encoding="utf-8")
        ecarts, _ = controler_voie_connecteur(f)
    return ecarts


def ecart_dit(ecarts: list[str], morceau: str) -> bool:
    return any(morceau.lower() in e.lower() for e in ecarts)


REEL = FICHIER_SOURCES.read_text(encoding="utf-8")

print("Test de la voie connecteur — referentiel des sources (TF-1854)\n")

# ---- A · LE TEXTE ---------------------------------------------------------------------------
print("A. controle 14 — le texte du referentiel")
ecarts, resume = controler_voie_connecteur()
verifier(ecarts == [], f"VERTE : le referentiel reel passe ({resume})")

# La phrase d'avant, remise telle quelle : c'est elle que le controle existe pour refuser.
ancienne = ("**Absents, sans exception** : Google Search Console, Google Analytics, index de backlinks "
            "(Ahrefs / Semrush / Majestic), source de volume de recherche, logs serveur, navigateur headless.")
phrase_nouvelle = ("**Absents, sans exception** : index de backlinks (Ahrefs / Semrush / Majestic), "
                   "source de volume de recherche, logs serveur, navigateur headless.")
verifier(phrase_nouvelle in REEL, "(controle de la fixture) la phrase remplacee est bien celle du referentiel")
rouge = REEL.replace(phrase_nouvelle, ancienne)
ecarts = texte_sources(rouge)
verifier(ecart_dit(ecarts, "absents, sans exception") and len(ecarts) == 1,
         "ROUGE : « Absents, sans exception : Google Search Console, Google Analytics » est refuse, et lui seul")
verifier(texte_sources(rouge.replace(ancienne, phrase_nouvelle)) == [],
         "remede rejoue : retirer GSC et GA de la liste des absents repasse au vert")

# La section des garde-fous.
sans_section = REEL.split("\n## Deux voies", 1)[0] + "\n## Matrice source" + REEL.split("\n## Matrice source", 1)[1]
verifier(ecart_dit(texte_sources(sans_section), "section « Deux voies » absente"),
         "ROUGE : sans la section « Deux voies », la voie n'est pas ecrite")

for mot, quoi in (
    ("jamais un compte de la forge", "l'interdiction d'un compte de la forge"),
    ("date de lecture", "la date de lecture"),
    ("references/INTEGRATIONS-FOURNISSEURS.md", "le renvoi vers la procedure du pilot"),
    ("Search Console — API, portées et lecture", "la section « Search Console »"),
):
    ecarts = texte_sources(REEL.replace(mot, "XXXX"))
    verifier(ecart_dit(ecarts, quoi), f"ROUGE : un referentiel qui perd « {mot} » est refuse")
    verifier(texte_sources(REEL.replace(mot, "XXXX").replace("XXXX", mot)) == [],
             f"remede rejoue : remettre « {mot} » repasse au vert")

# La matrice : une ligne connecteur par source, memes noeuds que l'export, jamais T2.
lignes = REEL.splitlines()
ligne_gsc = next(l for l in lignes if l.startswith("| **Connecteur GSC**"))
ligne_ga = next(l for l in lignes if l.startswith("| **Connecteur GA4**"))
ecarts = texte_sources(REEL.replace(ligne_gsc + "\n", ""))
verifier(ecart_dit(ecarts, "aucune ligne « Connecteur GSC »"),
         "ROUGE : sans ligne « Connecteur GSC » a cote de l'export, la matrice ment")
ecarts = texte_sources(REEL.replace(ligne_ga + "\n", ""))
verifier(ecart_dit(ecarts, "aucune ligne « Connecteur GA4 »"),
         "ROUGE : sans ligne « Connecteur GA4 » a cote de l'export, la matrice ment")
verifier(texte_sources(REEL.replace(ligne_ga + "\n", "").replace(
    "| **Export GA** |", ligne_ga + "\n| **Export GA** |", 1)) == [],
    "remede rejoue : remettre la ligne (meme a une autre place) repasse au vert")
ecarts = texte_sources(REEL.replace(ligne_gsc, ligne_gsc.replace("**16 nœuds**", "**15 nœuds**")))
verifier(ecart_dit(ecarts, "memes noeuds que l'export"),
         "ROUGE : une ligne connecteur qui dit 15 noeuds quand l'export en dit 16 est refusee")
ecarts = texte_sources(REEL.replace(ligne_ga, ligne_ga.replace("T1 observé", "T2 déclaré")))
verifier(ecart_dit(ecarts, "T1 observe, jamais T2"),
         "ROUGE : une voie connecteur etiquetee T2 est refusee (une lecture datee est T1)")

# La version.
sans_version = "\n".join(l for l in lignes if not l.startswith("**Version "))
verifier(ecart_dit(texte_sources(sans_version), "numero de version"),
         "ROUGE : un referentiel sans numero de version est refuse")
verifier(texte_sources(sans_version + "\n**Version 1.1.0 — 2026-10-18.** rattrapee\n") == [],
         "remede rejoue : poser la ligne de version repasse au vert")

# Aucun identifiant de client.
for intrus in ("sc-domain:exemple.fr", "properties/123456789", "client@exemple.fr",
               "123-abc.apps.googleusercontent.com", "ya29.a0AfH6SMB", "G-ABCDEFGH12"):
    verifier(ecart_dit(texte_sources(REEL + f"\nPropriete lue : {intrus}\n"), "identifiant de client"),
             f"ROUGE : « {intrus} » dans le referentiel est refuse")
verifier(texte_sources(REEL + "\nLa propriete lue se nomme au cadrage de l'etude.\n") == [],
         "contre-epreuve : une phrase sans identifiant ne declenche rien")

# ---- B · LES MESURES D'UNE ETUDE --------------------------------------------------------------
print("\nB. controle 6 — les mesures « connecteur » d'une etude")
SOURCE_OK = "connecteur GSC, lu le 2026-10-18, période 2026-09-01 → 2026-09-28"


def mesure(**champs) -> dict:
    return {"cle": "clics_organiques", "valeur": 9800, "unite": "clics", "preuve": "T1",
            "source": SOURCE_OK, **champs}


def snapshot_avec(m: dict) -> dict:
    return {"baseline": {"metriques": [m]}, "noeuds": [{"id": 72, "mesures": [m]}]}


verifier(controler_lectures_connecteur(snapshot_avec(mesure())) == [],
         "VERTE : une lecture T1 datee, avec sa periode, passe — dans la baseline comme dans un noeud")
verifier(controler_lectures_connecteur(snapshot_avec(mesure(preuve="T2", source="export GSC, période 2026-09"))) == [],
         "VERTE : un export T2 n'est pas concerne par la regle connecteur")
verifier(controler_lectures_connecteur({"noeuds": []}) == [],
         "VERTE : un snapshot sans mesure connecteur ne declenche rien")

ecarts = controler_lectures_connecteur(snapshot_avec(mesure(preuve="T2")))
verifier(any("est T1" in e for e in ecarts), "ROUGE : une lecture connecteur etiquetee T2 est refusee")
ecarts = controler_lectures_connecteur(snapshot_avec(mesure(source="connecteur GSC, période 2026-09-01 → 2026-09-28")))
verifier(any("lu le AAAA-MM-JJ" in e for e in ecarts),
         "ROUGE : une lecture connecteur sans date de lecture est refusee")
ecarts = controler_lectures_connecteur(snapshot_avec(mesure(source="connecteur GA4, lu le 2026-10-18")))
verifier(any("periode interrogee" in e for e in ecarts),
         "ROUGE : une lecture connecteur sans periode interrogee est refusee")
verifier(controler_lectures_connecteur(snapshot_avec(mesure(
    source="connecteur GA4, lu le 2026-10-18, période 2026-09-01 → 2026-09-28"))) == [],
    "remede rejoue : ajouter la periode repasse au vert")
verifier(len(controler_lectures_connecteur(snapshot_avec(mesure(preuve="T2", source="connecteur GSC")))) >= 6,
         "chaque defaut est dit (T2, date, periode), sur la baseline ET sur le noeud : rien n'est tu")

# ---- C · LES LECTEURS DU REFERENTIEL ----------------------------------------------------------
print("\nC. lecteurs — le schema du snapshot et le rapport ne refusent pas une source ouverte")
sch = json.loads((RACINE / "referentiel" / "snapshot.schema.json").read_text(encoding="utf-8"))
source_ouverte = {"disponible": True, "periode_debut": "2026-09-01", "periode_fin": "2026-09-28",
                  "note": "connecteur GSC, lu le 2026-10-18, compte du client, lecture seule"}
verifier(valider({"gsc": source_ouverte, "ga": dict(source_ouverte, note="connecteur GA4")},
                 sch["properties"]["sources"], sch) == [],
         "VERTE : le schema accepte une source GSC et GA ouvertes par connecteur")
verifier(valider(mesure(), sch["$defs"]["metrique"], sch) == [],
         "VERTE : le schema accepte une mesure T1 lue par connecteur")
verifier(valider({"gsc": {"periode_debut": "2026-09-01"}}, sch["properties"]["sources"], sch) != [],
         "ROUGE : le schema refuse toujours une source sans `disponible` (contre-epreuve)")

with tempfile.TemporaryDirectory() as d:
    base = Path(d)
    (base / "donnees" / "gsc").mkdir(parents=True)
    (base / "donnees" / "ga").mkdir(parents=True)
    ouvertes = {"snapshot": {"sources": {"gsc": source_ouverte, "ga": source_ouverte,
                                         "crm": {"disponible": True}}}, "base": base}
    verifier(manque_a_fournir(ouvertes) == [],
             "VERTE : GSC et GA ouverts par connecteur ne sont plus demandes au client")
    fermees = {"snapshot": {"sources": {"gsc": {"disponible": False}, "ga": {"disponible": False},
                                        "crm": {"disponible": True}}}, "base": base}
    manques = manque_a_fournir(fermees)
    verifier(len(manques) == 2 and all("connecteur" in m for m in manques),
             "ROUGE : sources fermees et dossiers vides, GSC et GA restent demandes — et la voie connecteur est nommee")

# La recette du depot lit un compte « N/M cas » : une verification sans compte comptable est
# declaree MUETTE et refusee.
print(f"\n{_ok}/{_ok + len(_ko)} cas conformes")
if _ko:
    for quoi in _ko:
        print(f"  ECHEC : {quoi}")
sys.exit(1 if _ko else 0)
