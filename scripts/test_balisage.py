"""Preuve a double sens des detecteurs de balisage du crawler (TF-0262).

Le run du 15/08 a conclu « aucune balise canonique sur 79 pages » et fonde une
action dessus. Verification directe : les canoniques existaient toutes. L'outil
cherchait `rel="canonical"` PUIS `href` ; le site ecrit `href` en premier. Une
absence etant indiscernable d'une non-detection, aucun controle ne pouvait
l'attraper -- le constat est sorti propre, chiffre et faux.

Ce fichier pose la discipline manquante : chaque detecteur d'attribut est
eprouve sur les DEUX ordres d'ecriture, et la fixture rouge est validee comme
fixture -- on verifie qu'elle fait bien ECHOUER un detecteur naif ecrit en
expression reguliere. Une fixture rouge qu'aucun detecteur naif ne rate ne
prouve rien : elle serait passee au vert par accident.

  VERT  : canonical, meta robots, hreflang et Open Graph sont detectes quel que
          soit l'ordre des attributs, la casse, le type de guillemets, la
          presence d'espaces ou de jetons `rel` multiples.
  ROUGE : le detecteur naif (regex `rel="canonical"` puis `href`) rate la page
          qui ecrit `href` en premier -- c'est la panne exacte du 15/08,
          reproduite ici pour que la fixture ait une valeur discriminante.

Fixtures synthetiques uniquement, en memoire : aucun reseau, aucun fichier.

Usage :
    python scripts/test_balisage.py
"""

from __future__ import annotations

import re
import sys

from crawler import Page

# --------------------------------------------------------------------- fixtures

# Ordre « canonique » : rel avant href. Le detecteur naif le trouve.
REL_AVANT_HREF = """<html><head>
<link rel="canonical" href="https://exemple.fr/page-a">
<meta name="robots" content="index, follow">
<link rel="alternate" hreflang="en" href="https://exemple.fr/en/page-a">
<meta property="og:title" content="Page A">
</head><body><h1>A</h1></body></html>"""

# LA fixture du defaut : href avant rel, exactement ce qu'ecrivait le site
# audite. Le detecteur naif la rate ; le detecteur du crawler doit la lire.
HREF_AVANT_REL = """<html><head>
<link href="https://exemple.fr/page-b" rel="canonical">
<meta content="noindex, nofollow" name="robots">
<link href="https://exemple.fr/en/page-b" hreflang="en" rel="alternate">
<meta content="Page B" property="og:title">
</head><body><h1>B</h1></body></html>"""

# Variantes hostiles : casse melangee, guillemets simples, espaces autour des
# valeurs, `rel` a plusieurs jetons, balise auto-fermante.
BRUITEE = """<html><head>
<LINK HREF='https://exemple.fr/page-c'  REL=' Alternate  Canonical ' />
<META CONTENT=' NOINDEX '  NAME='Robots'/>
<link href="https://exemple.fr/de/page-c" hreflang="DE" rel="ALTERNATE">
<meta content="Page C" name="og:title">
</head><body><h1>C</h1></body></html>"""

# Page reellement SANS canonique : le detecteur ne doit rien inventer.
SANS_CANONICAL = """<html><head><title>D</title>
<link rel="stylesheet" href="/style.css">
<meta name="description" content="pas de canonique ici">
</head><body><h1>D</h1></body></html>"""


# ------------------------------------------------------- le detecteur en panne

RE_NAIF = re.compile(r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', re.I)


def canonical_naif(html: str) -> str | None:
    """Le detecteur du 15/08, conserve ici comme temoin de panne.

    Il lit la balise de gauche a droite et suppose un ordre d'attributs. Il
    n'est PAS utilise par la forge : il sert a prouver que la fixture rouge
    discrimine. S'il venait a passer sur HREF_AVANT_REL, la fixture serait
    devenue inoffensive et ce test le dirait.
    """
    m = RE_NAIF.search(html)
    return m.group(1) if m else None


def lire(html: str) -> Page:
    p = Page()
    p.feed(html)
    return p


# ---------------------------------------------------------------- verificateur


class Bilan:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.cas = 0

    def attendu(self, etiquette: str, nom: str, ok: bool, detail: str = "") -> None:
        self.cas += 1
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {etiquette} {nom}"
              + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)

    def rendre(self) -> int:
        print(f"\n{self.cas - len(self.echecs)}/{self.cas} preuves conformes")
        if self.echecs:
            print("ECHECS : " + ", ".join(self.echecs))
            return 1
        return 0


def main() -> int:
    b = Bilan()

    print("\nTF-0262 -- canonical, quel que soit l'ordre des attributs")
    a = lire(REL_AVANT_HREF)
    b.attendu("VERT ", "canonical lue quand rel precede href",
              a.canonical == "https://exemple.fr/page-a", a.canonical or "aucune")
    c = lire(HREF_AVANT_REL)
    b.attendu("VERT ", "canonical lue quand href precede rel",
              c.canonical == "https://exemple.fr/page-b", c.canonical or "aucune")
    d = lire(BRUITEE)
    b.attendu("VERT ", "canonical lue en casse melangee, guillemets simples, "
              "rel a deux jetons",
              d.canonical == "https://exemple.fr/page-c", d.canonical or "aucune")
    e = lire(SANS_CANONICAL)
    b.attendu("VERT ", "aucune canonique inventee sur une page qui n'en porte pas",
              e.canonical is None, repr(e.canonical))

    print("\nTF-0262 -- la fixture rouge fait bien echouer le detecteur naif")
    b.attendu("ROUGE", "detecteur naif : trouve la canonique quand rel precede href",
              canonical_naif(REL_AVANT_HREF) == "https://exemple.fr/page-a",
              "sinon la fixture verte serait fausse, pas le detecteur")
    b.attendu("ROUGE", "detecteur naif : RATE la canonique quand href precede rel",
              canonical_naif(HREF_AVANT_REL) is None,
              "panne du 15/08 reproduite -- la fixture discrimine")
    b.attendu("ROUGE", "detecteur naif : RATE la canonique sur la page bruitee",
              canonical_naif(BRUITEE) is None,
              "guillemets simples et rel a deux jetons")

    print("\nTF-0262 -- meta robots, hreflang et Open Graph")
    b.attendu("VERT ", "meta robots lu quand name precede content",
              a.robots == "index, follow", repr(a.robots))
    b.attendu("VERT ", "meta robots lu quand content precede name",
              c.robots == "noindex, nofollow", repr(c.robots))
    b.attendu("VERT ", "noindex reconnu malgre casse et espaces",
              "noindex" in d.robots, repr(d.robots))
    b.attendu("VERT ", "hreflang lu quand hreflang precede rel",
              c.hreflang == [{"hreflang": "en",
                              "href": "https://exemple.fr/en/page-b"}],
              str(c.hreflang))
    b.attendu("VERT ", "hreflang normalise en minuscules (DE -> de)",
              [h["hreflang"] for h in d.hreflang] == ["de"], str(d.hreflang))
    b.attendu("VERT ", "og:title lu quand content precede property",
              c.og.get("og:title") == "Page B", str(c.og))
    b.attendu("VERT ", "og:title lu quand le CMS ecrit name= au lieu de property=",
              d.og.get("og:title") == "Page C", str(d.og))
    b.attendu("VERT ", "aucun hreflang ni og inventes sur une page nue",
              e.hreflang == [] and e.og == {}, f"{e.hreflang} / {e.og}")

    return b.rendre()


if __name__ == "__main__":
    sys.exit(main())
