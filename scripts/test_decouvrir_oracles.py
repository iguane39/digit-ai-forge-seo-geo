"""Preuve a double sens de oracles/decouvrir-oracles.mjs (TF-1319, 23/09/2026).

La decouverte dit au juge d'enclenchement du pilot ce que cette forge porte comme
oracles : le juge confronte cette liste aux verdicts consignes au ledger d'un run.
Une decouverte qui raterait un oracle le rendrait invisible au juge ; une decouverte
qui prendrait une recette, une fixture ou un entrant pour un oracle ferait accuser un
run de n'avoir pas joue ce qui n'en est pas un. Les deux sens se prouvent.

  VERT  : la forge decouvre ses oracles sur son propre disque (contrat
          digit-ai/decouverte-oracles@1, chaque chemin rendu existe) ; un oracle pose
          sur un arbre jetable est decouvert ; un oracle AJOUTE l'est au passage
          suivant, sans liste a tenir.
  ROUGE : une recette `test_*.py`, `validate.py`, une fixture, une archive `Old/`, une
          dependance et un entrant `input/` ne sont JAMAIS pris pour des oracles ; une
          racine absente sort en 2 avec son motif.

La decouverte est un script Node (le contrat du parc est commun) : sans `node` sur le
poste, rien n'est joue et la sortie le dit, avec un compte 0/0 plutot qu'un silence.

Usage :
    python scripts/test_decouvrir_oracles.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DECOUVRIR = RACINE / "oracles" / "decouvrir-oracles.mjs"


def decouvre(node: str, racine: Path | None) -> tuple[int, dict | None]:
    args = [node, str(DECOUVRIR)] + (["--racine", str(racine)] if racine else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, None


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("node introuvable sur ce poste : la decouverte (script Node, contrat commun du parc)"
              " n'a pas ete jouee -- prerequis du poste, pas un defaut de la forge")
        print("0/0 preuves jouees")
        return 0

    cas: list[tuple[str, bool]] = []

    code, j = decouvre(node, None)
    oracles = (j or {}).get("oracles") or []
    tenu = (code == 0 and j is not None and j.get("contrat") == "digit-ai/decouverte-oracles@1"
            and j.get("forge") == "digit-ai-forge-seo-geo" and len(oracles) > 0
            and all((RACINE / o["chemin"]).exists() for o in oracles)
            and any(o["nom"] == "oracle_interaction" for o in oracles))
    cas.append((f"VERT  la forge decouvre {len(oracles)} oracle(s) sur son propre disque, "
                "oracle_interaction compris, contrat tenu", tenu))

    with tempfile.TemporaryDirectory(prefix="forge-seo-geo-decouverte-") as brut:
        tmp = Path(brut)

        def poser(rel: str) -> None:
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# fixture de decouverte\n", encoding="utf-8")

        for rel in ("scripts/oracle_alpha.py", "oracles/oracle-beta.mjs"):
            poser(rel)
        leurres = ["scripts/test_oracle_alpha.py", "scripts/validate.py", "scripts/recette.py",
                   "fixtures/oracle_faux.py", "Old/oracle_vieux.py",
                   "node_modules/paquet/oracle-dep.mjs", "input/oracle_entrant.py"]
        for rel in leurres:
            poser(rel)
        code, j = decouvre(node, tmp)
        noms = sorted(o["nom"] for o in (j or {}).get("oracles") or [])
        cas.append((f"VERT  un oracle pose sur le disque est decouvert (obtenu {noms})",
                    code == 0 and noms == ["oracle-beta", "oracle_alpha"]))
        chemins = {o["chemin"] for o in (j or {}).get("oracles") or []}
        cas.append((f"ROUGE recette, validate.py, fixture, archive, dependance et entrant ne sont"
                    f" JAMAIS pris pour des oracles ({len(leurres)} leurres refuses)",
                    code == 0 and not chemins.intersection(leurres)))
        poser("scripts/oracle_gamma.py")
        code, j = decouvre(node, tmp)
        cas.append(("VERT  un oracle AJOUTE est decouvert au passage suivant, sans liste a tenir",
                    any(o["chemin"] == "scripts/oracle_gamma.py" for o in (j or {}).get("oracles") or [])))

    absente = Path(tempfile.gettempdir()) / "forge-seo-geo-racine-qui-n-existe-pas"
    code, j = decouvre(node, absente)
    cas.append((f"ROUGE une racine absente sort en 2 avec son motif (obtenu exit {code})",
                code == 2 and j is not None and j.get("oracles") == [] and "introuvable" in (j.get("motif") or "")))

    for libelle, ok in cas:
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {libelle}")
    tenus = sum(1 for _, ok in cas if ok)
    if tenus != len(cas):
        print(f"\nECHECS : {len(cas) - tenus}")
        print(f"{tenus}/{len(cas)} preuves conformes")
        return 1
    print(f"\n{tenus}/{len(cas)} preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
