"""Preuve a double sens du refus de mesure quand le plafond coupe (TF-0261).

Le 15/08, un crawl a 200 pages a rendu « pages orphelines : 89 (MAJORANT) »
alors que le site en comptait 10 : la relance a --max 320 l'a montre. Le crawler
SAVAIT qu'il n'avait pas fini -- urls_decouvertes valait 289 -- et a quand meme
ecrit un nombre. Un chiffre marque « majorant » reste un chiffre qu'on cite :
c'est le defaut, pas la parade.

Site de fixture servi en local (127.0.0.1, port ephemere, aucun reseau
externe) : 12 URL declarees au sitemap, dont 4 seulement sont atteignables en
suivant les liens depuis l'accueil. Le compte d'orphelines EXACT vaut donc 8.

  ROUGE : plafond a 4 -- la couverture est incomplete. Aucun compteur de graphe
          ne s'ecrit : pages_orphelines vaut None, mesures_refusees nomme chaque
          compteur refuse et dit la relance exacte (--max >= 12). Le test verifie
          en plus qu'AUCUN nombre n'a ete ecrit -- l'ancien comportement
          (un entier accompagne d'une etiquette) echouerait ici.
  VERT  : plafond a 50, puis --jusqu-a-epuisement depuis un plafond de 4 : la
          file se vide, la couverture est complete, le compte vaut 8 exactement.
  ROUGE : --jusqu-a-epuisement sous une borne dure de 4 -- la borne ne fabrique
          pas une couverture complete : le refus revient, et son motif parle de
          la borne dure, pas de --max.

Usage :
    python scripts/test_crawl_plafond.py
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler import crawler

# 4 pages atteignables en suivant les liens : l'accueil et trois pages liees.
LIEES = ["/a", "/b", "/c"]
# 8 pages declarees au sitemap qu'AUCUN lien interne ne cite : les orphelines.
ORPHELINES = [f"/orpheline-{i}" for i in range(1, 9)]
TOUTES = ["/"] + LIEES + ORPHELINES

ACCUEIL = ("<html><head><title>Accueil</title>"
           "<link href='/' rel='canonical'></head><body><h1>Accueil</h1>"
           + "".join(f"<p><a href='{u}'>{u}</a></p>" for u in LIEES)
           + "</body></html>")


def page(chemin: str) -> str:
    return (f"<html><head><title>{chemin}</title>"
            f"<link href='{chemin}' rel='canonical'></head>"
            f"<body><h1>{chemin}</h1><p>contenu de fixture.</p></body></html>")


def sitemap(base: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{base}{u.lstrip('/')}</loc></url>" for u in TOUTES)
            + "</urlset>")


class Gabarit(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence le journal du serveur de test
        pass

    def do_GET(self):
        base = f"http://{self.headers.get('Host')}/"
        if self.path == "/robots.txt":
            self._rendre(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n",
                         "text/plain")
        elif self.path == "/sitemap.xml":
            self._rendre(sitemap(base), "application/xml")
        elif self.path == "/":
            self._rendre(ACCUEIL, "text/html; charset=utf-8")
        elif self.path in LIEES + ORPHELINES:
            self._rendre(page(self.path), "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _rendre(self, texte: str, mime: str) -> None:
        corps = texte.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


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
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gabarit)
    port = serveur.server_address[1]
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    racine = f"http://127.0.0.1:{port}/"
    b = Bilan()

    try:
        print("\nTF-0261 -- plafond a 4 sur un site de 12 URL connues")
        tronque = crawler(racine, plafond=4, delai=0)
        s = tronque["synthese"]
        refus = tronque["mesures_refusees"]
        b.attendu("ROUGE", "le crawler SAIT qu'il n'a pas fini",
                  s["urls_decouvertes"] > tronque["collecte"]["plafond_effectif"],
                  f"{s['urls_decouvertes']} URL connues pour un plafond de "
                  f"{tronque['collecte']['plafond_effectif']}")
        b.attendu("ROUGE", "aucun compte d'orphelines ecrit",
                  s["pages_orphelines"] is None, repr(s["pages_orphelines"]))
        b.attendu("ROUGE", "aucun exemple d'orpheline cite",
                  s["pages_orphelines_exemples"] is None,
                  repr(s["pages_orphelines_exemples"]))
        b.attendu("ROUGE", "aucun compte de pages sans lien contextuel ecrit",
                  s["pages_sans_lien_contextuel"] is None,
                  repr(s["pages_sans_lien_contextuel"]))
        b.attendu("ROUGE", "les trois compteurs de graphe sont nommes au refus",
                  set(refus) == {"pages_orphelines", "pages_orphelines_exemples",
                                 "pages_sans_lien_contextuel"},
                  f"{len(refus)} refus motive(s)")
        motif = refus.get("pages_orphelines", "")
        b.attendu("ROUGE", "le motif dit la relance exacte (--max >= URL connues)",
                  f"--max ≥ {s['urls_decouvertes']}" in motif, motif[:120])
        b.attendu("ROUGE", "aucune valeur numerique de graphe ne subsiste ailleurs",
                  not any(isinstance(v, int) and not isinstance(v, bool)
                          for k, v in s.items()
                          if "orphelin" in k or "sans_lien" in k),
                  "un entier ici serait le defaut du 15/08, reintroduit")
        b.attendu("ROUGE", "la couverture incomplete est declaree comme telle",
                  s["couverture_complete"] is False, str(s["couverture_complete"]))

        print("\nTF-0261 -- plafond suffisant : le compte exact revient")
        complet = crawler(racine, plafond=50, delai=0)
        sc = complet["synthese"]
        b.attendu("VERT ", "aucun refus quand la file est videe",
                  complet["mesures_refusees"] == {}, str(complet["mesures_refusees"]))
        b.attendu("VERT ", "8 orphelines comptees, la valeur vraie du site de fixture",
                  sc["pages_orphelines"] == len(ORPHELINES),
                  f"obtenu {sc['pages_orphelines']}, attendu {len(ORPHELINES)}")
        b.attendu("VERT ", "12 pages crawlees sur 12 declarees",
                  sc["pages_crawlees"] == len(TOUTES), str(sc["pages_crawlees"]))

        print("\nTF-0261 -- --jusqu-a-epuisement releve le plafond lui-meme")
        epuise = crawler(racine, plafond=4, delai=0, jusqu_a_epuisement=True)
        se = epuise["synthese"]
        b.attendu("VERT ", "un plafond de 4 ne coupe plus rien sous --jusqu-a-epuisement",
                  epuise["mesures_refusees"] == {} and
                  se["pages_orphelines"] == len(ORPHELINES),
                  f"{se['pages_crawlees']} pages, {se['pages_orphelines']} orphelines")
        b.attendu("VERT ", "la borne dure est declaree au resultat",
                  epuise["collecte"]["borne_dure"] is not None
                  and epuise["collecte"]["jusqu_a_epuisement"] is True,
                  f"borne dure {epuise['collecte']['borne_dure']}")

        print("\nTF-0261 -- la borne dure ne fabrique pas une couverture complete")
        borne = crawler(racine, plafond=999, delai=0, jusqu_a_epuisement=True,
                        borne_dure=4)
        b.attendu("ROUGE", "borne dure atteinte : le refus revient",
                  borne["synthese"]["pages_orphelines"] is None
                  and bool(borne["mesures_refusees"]),
                  repr(borne["synthese"]["pages_orphelines"]))
        b.attendu("ROUGE", "le motif parle de la borne dure, pas de --max",
                  "borne dure" in borne["mesures_refusees"]["pages_orphelines"],
                  borne["mesures_refusees"]["pages_orphelines"][:120])
    finally:
        serveur.shutdown()
        fil.join(timeout=5)

    return b.rendre()


if __name__ == "__main__":
    sys.exit(main())
