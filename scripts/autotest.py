"""Auto-test a fixtures des controles de validate.py.

Un controle qu'on n'a jamais vu ECHOUER n'est pas un controle : c'est une ligne
qui imprime OK. Chaque regle ajoutee ici porte donc deux fixtures --
une VERTE qui doit passer, une ROUGE qui doit echouer, et pour la bonne raison.

Les fixtures sont construites dans un repertoire temporaire du systeme : rien
n'est ecrit dans la forge, rien n'est ecrit chez une mission.

Usage :
    python scripts/autotest.py

Sortie non-zero des qu'un cas ne rend pas le verdict attendu.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from gabarits import VERSION_ETAT, version_snapshot
from validate import controler_versions

# --------------------------------------------------------------------- socle


def etude_minimale(base: Path) -> Path:
    """Squelette d'etude reduit a ce que le controle teste regarde."""
    (base / "livrables").mkdir(parents=True, exist_ok=True)
    (base / "etat.json").write_text(
        json.dumps({"schema_version": VERSION_ETAT, "domaine": "exemple.fr"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return base


def snapshot(base: Path, version: str, jour: str = "20260101") -> Path:
    f = base / "livrables" / f"snapshot-exemple.fr-{jour}.json"
    f.write_text(json.dumps({"schema_version": version}, indent=2) + "\n", encoding="utf-8")
    return f


# ---------------------------------------------------------------- verificateur


class Bilan:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.cas = 0

    def attendu(self, nom: str, obtenu_rouge: bool, attendu_rouge: bool, detail: str = "") -> None:
        self.cas += 1
        ok = obtenu_rouge == attendu_rouge
        etiquette = "ROUGE" if attendu_rouge else "VERT "
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {etiquette} {nom}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)

    def rendre(self) -> int:
        print(f"\n{self.cas - len(self.echecs)}/{self.cas} cas conformes")
        if self.echecs:
            print("ECHECS : " + ", ".join(self.echecs))
            return 1
        return 0


# ------------------------------------------------------------------- TF-0028


def cas_versions(b: Bilan, racine: Path) -> None:
    base = etude_minimale(racine / "versions-vert" / "seo")
    snapshot(base, version_snapshot())
    ecarts, resume = controler_versions(base)
    b.attendu("versions de schema alignees", bool(ecarts), False, resume)

    base = etude_minimale(racine / "versions-rouge-etat" / "seo")
    snapshot(base, version_snapshot())
    (base / "etat.json").write_text(
        json.dumps({"schema_version": "0.9.0", "domaine": "exemple.fr"}) + "\n",
        encoding="utf-8",
    )
    ecarts, _ = controler_versions(base)
    b.attendu(
        "etat.json a une version perimee",
        bool(ecarts) and "etat.json" in ecarts[0],
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )

    base = etude_minimale(racine / "versions-rouge-snapshot" / "seo")
    snapshot(base, "1.0.0")
    ecarts, _ = controler_versions(base)
    b.attendu(
        "snapshot a une version perimee",
        bool(ecarts) and "snapshot" in ecarts[0],
        True,
        ecarts[0] if ecarts else "aucun ecart releve",
    )


# ----------------------------------------------------------------------- main


CAS = [
    ("TF-0028 -- versions de schema", cas_versions),
]


def main() -> int:
    b = Bilan()
    racine = Path(tempfile.mkdtemp(prefix="forge-seo-autotest-"))
    try:
        for titre, fonction in CAS:
            print(f"\n{titre}")
            fonction(b, racine)
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    return b.rendre()


if __name__ == "__main__":
    sys.exit(main())
