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

import json
import os
import sys
import tempfile
from pathlib import Path

import crux
from crux import interpreter_reponse, terrain_disponible, verdict_non_mesurable

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

    # --- TF-0273 : un « non mesure » laisse une TRACE, comme agents_ia.py -------
    # Sans cle, le script sortait en 1 sans rien ecrire : l'etude ne gardait aucune
    # preuve datee que le noeud 31 n'avait pas ete mesure. Aucun reseau ici : sans
    # cle, main() n'appelle jamais l'API.
    with tempfile.TemporaryDirectory() as tmp:
        projet = Path(tmp)
        (projet / "seo" / "donnees").mkdir(parents=True)
        argv, cle_env = sys.argv, os.environ.pop("CRUX_API_KEY", None)
        try:
            sys.argv = ["crux.py", "--projet", str(projet), "--url", "https://exemple.fr"]
            code_sortie = crux.main()
        finally:
            sys.argv = argv
            if cle_env is not None:
                os.environ["CRUX_API_KEY"] = cle_env

        traces = sorted((projet / "seo" / "donnees" / "performance").glob("crux-*.json"))
        ok_trace = len(traces) == 1
        print(f"  [{'OK  ' if ok_trace else 'ECHEC'}] VERT  sans cle : une trace ecrite "
              f"dans seo/donnees/performance/ (obtenu {len(traces)})")
        if not ok_trace:
            echecs.append("un « non mesure » de terrain doit laisser une trace")
            trace = {}
        else:
            trace = json.loads(traces[0].read_text(encoding="utf-8"))

        ok_vocabulaire = (
            trace.get("mesurable") is False
            and trace.get("verdict") == "non-mesurable"
            and trace.get("noeuds_concernes") == [31]
            and str(trace.get("motif", "")).startswith("Non mesurable en l'état —")
        )
        print(f"  [{'OK  ' if ok_vocabulaire else 'ECHEC'}] VERT  meme vocabulaire "
              "qu'agents_ia.py (mesurable/verdict/noeuds_concernes, « Non mesurable en "
              "l'état — »)")
        if not ok_vocabulaire:
            echecs.append("vocabulaire du verdict non mesurable")

        ok_pistes = bool(trace.get("donnee_manquante")) and len(trace.get("comment_l_obtenir") or []) >= 3
        print(f"  [{'OK  ' if ok_pistes else 'ECHEC'}] VERT  la trace nomme la donnee "
              "manquante et comment l'obtenir")
        if not ok_pistes:
            echecs.append("la trace doit nommer la donnee manquante et les pistes")

        ok_code = code_sortie == 1
        print(f"  [{'OK  ' if ok_code else 'ECHEC'}] VERT  sortie 1 conservee : une cle "
              f"gratuite en deux commandes reste un refus, pas une fatalite (obtenu {code_sortie})")
        if not ok_code:
            echecs.append("sortie 1 conservee sans cle")

        # ROUGE : la trace ne doit JAMAIS passer pour un releve exploitable, sinon le
        # noeud 31 se jugerait sur du vide -- exactement le defaut que TF-0264 a ferme.
        dispo, resume = terrain_disponible(projet / "seo")
        ok_pas_exploitable = dispo is False and "non mesuré" in resume
        print(f"  [{'OK  ' if ok_pas_exploitable else 'ECHEC'}] ROUGE la trace n'est pas "
              f"un releve : terrain_disponible() reste False et le dit ({resume[:60]})")
        if not ok_pas_exploitable:
            echecs.append("une trace non mesuree ne doit jamais valoir releve de terrain")

        # ROUGE : aucune metrique fabriquee -- None, jamais {} ni 0 (« pas de donnee
        # publiee » et « personne n'a interroge » sont deux constats differents).
        ok_rien_fabrique = trace.get("metriques") is None and trace.get("disponible") is False
        print(f"  [{'OK  ' if ok_rien_fabrique else 'ECHEC'}] ROUGE aucune metrique "
              "fabriquee (metriques=None, jamais {} ni 0)")
        if not ok_rien_fabrique:
            echecs.append("aucune metrique ne doit etre fabriquee par un non-mesure")

        # VERT : un vrai releve depose a cote fait bien basculer le verdict -- la trace
        # non mesuree ne masque pas une mesure reelle, et n'a pas ecrase son fichier.
        (projet / "seo" / "donnees" / "performance" / "crux-exemple.fr-2026-08-15.json").write_text(
            json.dumps({"disponible": True, "metriques": {"largest_contentful_paint": {"p75": 2200}}}),
            encoding="utf-8")
        dispo2, _ = terrain_disponible(projet / "seo")
        ok_cohabitation = dispo2 is True and len(list((projet / "seo" / "donnees" / "performance").glob("crux-*.json"))) == 2
        print(f"  [{'OK  ' if ok_cohabitation else 'ECHEC'}] VERT  un vrai releve depose "
              "a cote reprend la main (fichiers distincts, aucune mesure ecrasee)")
        if not ok_cohabitation:
            echecs.append("la trace non mesuree ne doit ni masquer ni ecraser un releve")

    # Fonction pure : le motif reste porte par l'appelant, jamais invente.
    v = verdict_non_mesurable("motif témoin", "2026-08-15", "https://exemple.fr", "url", "PHONE")
    ok_motif_porte = "motif témoin" in v["motif"] and v["collecte"]["date"] == "2026-08-15"
    print(f"  [{'OK  ' if ok_motif_porte else 'ECHEC'}] VERT  verdict_non_mesurable() "
          "relaie le motif et l'horodatage recus, sans en inventer")
    if not ok_motif_porte:
        echecs.append("verdict_non_mesurable doit relayer motif et date")

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n12/12 preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
