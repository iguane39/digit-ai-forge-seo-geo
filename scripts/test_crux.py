"""Preuve a double sens de crux.py (TF-0105, noeud 31).

Aucun appel reseau, aucune cle API : `interpreter_reponse()` est une fonction
PURE testee sur des reponses CrUX en boite -- la forme reelle documentee par
Google (record.metrics.<nom>.{percentiles.p75, histogram[]}).

  VERT  : une reponse 200 realiste (LCP + CLS) se traduit en p75 et
          repartition bon/a-ameliorer/mauvais, SANS qu'aucun seuil numerique
          ne soit code en dur cote script (garde-fou 4 du referentiel).
  ROUGE : une reponse d'erreur 404 (« NOT_FOUND », trafic insuffisant) ne doit
          jamais etre lue par interpreter_reponse() -- main() la routes a part
          (branche `code == 404`) ; ce test verifie que la fonction, appelee a
          tort sur un corps d'erreur sans "record", ne fabrique pas de fausses
          metriques mais rend un resultat vide et explicite.

Usage :
    python scripts/test_crux.py
"""

from __future__ import annotations

import sys

from crux import interpreter_reponse

REPONSE_VALIDE = {
    "record": {
        "key": {"url": "https://exemple.fr/produit", "formFactor": "PHONE"},
        "metrics": {
            "largest_contentful_paint": {
                "histogram": [
                    {"start": 0, "end": 2500, "density": 0.72},
                    {"start": 2500, "end": 4000, "density": 0.18},
                    {"start": 4000, "density": 0.10},
                ],
                "percentiles": {"p75": 2200},
            },
            "cumulative_layout_shift": {
                "histogram": [
                    {"start": "0.00", "end": "0.10", "density": 0.85},
                    {"start": "0.10", "end": "0.25", "density": 0.10},
                    {"start": "0.25", "density": 0.05},
                ],
                "percentiles": {"p75": "0.05"},
            },
        },
        "collectionPeriod": {
            "firstDate": {"year": 2026, "month": 7, "day": 15},
            "lastDate": {"year": 2026, "month": 8, "day": 11},
        },
    },
}

REPONSE_404 = {
    "error": {
        "code": 404,
        "message": "chrome ux report data not found",
        "status": "NOT_FOUND",
    },
}


def main() -> int:
    echecs = []

    # --- VERT : reponse valide, deux metriques, aucun seuil recopie ------------
    r = interpreter_reponse(REPONSE_VALIDE)
    ok_p75_lcp = r["metriques"]["largest_contentful_paint"]["p75"] == 2200
    ok_repartition_lcp = r["metriques"]["largest_contentful_paint"]["repartition_experience"] == {
        "bonne": 0.72, "a_ameliorer": 0.18, "mauvaise": 0.10,
    }
    ok_deux_metriques = len(r["metriques"]) == 2
    ok_cle = r["cle_enregistrement"]["formFactor"] == "PHONE"
    print(f"  [{'OK  ' if ok_p75_lcp else 'ECHEC'}] VERT  p75 LCP relaye tel quel (2200 ms)")
    print(f"  [{'OK  ' if ok_repartition_lcp else 'ECHEC'}] VERT  repartition LCP = densites "
          "CrUX telles quelles, aucun seuil recalcule")
    print(f"  [{'OK  ' if ok_deux_metriques else 'ECHEC'}] VERT  2 metriques extraites "
          f"(obtenu {len(r['metriques'])})")
    print(f"  [{'OK  ' if ok_cle else 'ECHEC'}] VERT  cle d'enregistrement (formFactor) preservee")
    if not (ok_p75_lcp and ok_repartition_lcp and ok_deux_metriques and ok_cle):
        echecs.append("interpretation d'une reponse CrUX valide")

    # --- ROUGE : corps d'erreur -- aucune metrique fabriquee -------------------
    r404 = interpreter_reponse(REPONSE_404)
    ok_vide = r404["metriques"] == {}
    print(f"  [{'OK  ' if ok_vide else 'ECHEC'}] ROUGE corps d'erreur 404 -- 0 metrique "
          f"fabriquee (obtenu {len(r404['metriques'])}) : main() route ce cas a part, "
          "jamais vers interpreter_reponse() en pratique")
    if not ok_vide:
        echecs.append("un corps d'erreur ne doit jamais produire de fausses metriques")

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n5/5 preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
