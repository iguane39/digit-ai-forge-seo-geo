"""Preuve a double sens de la ventilation par agent IA (TF-0105, noeuds 29/58).

Fixtures synthetiques uniquement -- aucune donnee client, ecrites dans un
fichier temporaire du systeme.

  VERT  : des lignes Combined Log Format bien formees, portant des UA d'agents
          IA connus (GPTBot, ClaudeBot) et un UA humain, se ventilent
          correctement : hits comptes par agent, categorie reprise du
          catalogue, humain jamais compte comme agent IA, blocage heuristique
          declenche sur l'agent majoritairement en 403.
  ROUGE : une ligne mal formee (pas le format Combined attendu) et un UA
          inconnu du catalogue ne doivent ni faire planter le script, ni etre
          comptes comme un agent IA par erreur -- ils doivent apparaitre
          comme ignores/non rattaches, jamais silencieusement absorbes.

Usage :
    python scripts/test_agents_ia.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from agents_ia import charger_catalogue, ventiler

LIGNES = [
    # GPTBot : 2 hits, tous 200
    '66.249.66.1 - - [12/Aug/2026:10:00:00 +0000] "GET /produit/chaise HTTP/1.1" '
    '200 512 "-" "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; '
    '+https://openai.com/gptbot)"',
    '66.249.66.1 - - [12/Aug/2026:10:00:05 +0000] "GET /produit/table HTTP/1.1" '
    '200 480 "-" "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"',
    # ClaudeBot : 1 hit en 200, 2 hits en 403 -> blocage probable (2/3 > 50%)
    '54.12.1.1 - - [12/Aug/2026:10:01:00 +0000] "GET /blog/article-1 HTTP/1.1" '
    '200 900 "-" "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"',
    '54.12.1.1 - - [12/Aug/2026:10:01:05 +0000] "GET /blog/article-2 HTTP/1.1" '
    '403 0 "-" "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"',
    '54.12.1.1 - - [12/Aug/2026:10:01:10 +0000] "GET /blog/article-3 HTTP/1.1" '
    '403 0 "-" "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"',
    # visiteur humain : ne doit jamais etre compte comme agent IA
    '203.0.113.9 - - [12/Aug/2026:10:02:00 +0000] "GET /accueil HTTP/1.1" '
    '200 2048 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"',
    # UA inconnu du catalogue, format bien forme -- ne doit rattacher a AUCUN agent
    '198.51.100.4 - - [12/Aug/2026:10:03:00 +0000] "GET /page HTTP/1.1" '
    '200 300 "-" "SomeRandomBot/3.0"',
]

LIGNE_MAL_FORMEE = "ceci n'est pas une ligne de log au format Combined\n"


def main() -> int:
    catalogue = charger_catalogue()
    echecs = []

    with tempfile.TemporaryDirectory() as tmp:
        fichier = Path(tmp) / "access.log"
        fichier.write_text("\n".join(LIGNES) + "\n" + LIGNE_MAL_FORMEE, encoding="utf-8")

        r = ventiler([fichier], catalogue)

        # --- VERT --------------------------------------------------------------
        ok_gptbot = r["par_agent"].get("GPTBot", {}).get("hits") == 2
        ok_claudebot = r["par_agent"].get("ClaudeBot", {}).get("hits") == 3
        ok_categorie = r["par_agent"].get("GPTBot", {}).get("categorie") == "entrainement"
        ok_bloque = "ClaudeBot" in r["agents_probablement_bloques"]
        ok_gptbot_pas_bloque = "GPTBot" not in r["agents_probablement_bloques"]
        print(f"  [{'OK  ' if ok_gptbot else 'ECHEC'}] VERT  GPTBot : 2 hits comptes")
        print(f"  [{'OK  ' if ok_claudebot else 'ECHEC'}] VERT  ClaudeBot : 3 hits comptes "
              "(1x200, 2x403)")
        print(f"  [{'OK  ' if ok_categorie else 'ECHEC'}] VERT  categorie reprise du "
              "catalogue (GPTBot = entrainement)")
        print(f"  [{'OK  ' if ok_bloque else 'ECHEC'}] VERT  ClaudeBot signale probablement "
              "bloque (2/3 hors 2xx/3xx)")
        print(f"  [{'OK  ' if ok_gptbot_pas_bloque else 'ECHEC'}] VERT  GPTBot NON signale "
              "bloque (0/2 hors 2xx/3xx)")
        if not (ok_gptbot and ok_claudebot and ok_categorie and ok_bloque and ok_gptbot_pas_bloque):
            echecs.append("ventilation des agents IA connus")

        # --- ROUGE ---------------------------------------------------------------
        noms_agents = set(r["par_agent"])
        ok_humain_absent = not (noms_agents & {"Chrome", "Windows"})  # aucun agent invente
        ok_inconnu_absent = "SomeRandomBot" not in noms_agents
        ok_une_ligne_ignoree = r["lignes_ignorees"] == 1
        ok_exemple_conserve = len(r["exemples_lignes_ignorees"]) == 1
        print(f"  [{'OK  ' if ok_humain_absent else 'ECHEC'}] ROUGE visiteur humain jamais "
              "compte comme agent IA")
        print(f"  [{'OK  ' if ok_inconnu_absent else 'ECHEC'}] ROUGE UA inconnu du "
              "catalogue non rattache a un agent (SomeRandomBot absent des comptes)")
        print(f"  [{'OK  ' if ok_une_ligne_ignoree else 'ECHEC'}] ROUGE 1 ligne mal formee "
              f"declaree ignoree (obtenu {r['lignes_ignorees']}), pas absorbee en silence")
        print(f"  [{'OK  ' if ok_exemple_conserve else 'ECHEC'}] ROUGE exemple de ligne "
              "ignoree conserve pour diagnostic")
        if not (ok_humain_absent and ok_inconnu_absent and ok_une_ligne_ignoree
                and ok_exemple_conserve):
            echecs.append("non-rattachement du trafic non-IA / lignes mal formees")

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n9/9 preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
