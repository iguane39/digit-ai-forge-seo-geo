"""Preuve a double sens du flag --rendu-js (TF-0105).

Sert un site local dont le <h1> n'existe QUE lorsqu'un script cote client
l'injecte -- exactement le cas SPA que crawler.py declare, l.13 et l.359-362 de
l'ancienne version, ne pas savoir mesurer.

  ROUGE (attendue) : sans --rendu-js, le crawl lit le HTML brut -- le <h1> est
                      absent. Le controle echoue pour la bonne raison : c'est
                      la limite documentee, pas un bug.
  VERT              : avec --rendu-js, Playwright execute le script avant
                      lecture du DOM -- le <h1> est present.

Aucun appel reseau externe : le serveur est local (127.0.0.1, port ephemere).

Usage :
    python scripts/test_rendu_js.py

Sortie non-zero si l'une des deux preuves ne rend pas le verdict attendu.
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler import crawler

PAGE_SPA = b"""<!doctype html>
<html><head><title>Site SPA de test</title></head>
<body>
  <div id="racine"></div>
  <script>
    document.getElementById('racine').innerHTML = '<h1>Rendu JS</h1><p>' +
      'contenu injecte cote client, invisible sans execution du script.</p>';
  </script>
</body></html>
"""


class Gabarit(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence le journal du serveur de test
        pass

    def do_GET(self):
        if self.path in ("/", "/robots.txt", "/sitemap.xml"):
            corps = PAGE_SPA if self.path == "/" else b""
            code = 200 if self.path == "/" else 404
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
        else:
            self.send_response(404)
            self.end_headers()


def h1_crawle(racine: str, rendu_js: bool) -> str | None:
    res = crawler(racine, plafond=1, delai=0, rendu_js=rendu_js)
    if not res["pages"]:
        return None
    return res["pages"][0]["h1"]


def main() -> int:
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gabarit)
    port = serveur.server_address[1]
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    racine = f"http://127.0.0.1:{port}/"

    echecs = []
    try:
        # --- ROUGE : sans rendu JS, le <h1> injecte n'existe pas dans le HTML brut
        h1_brut = h1_crawle(racine, rendu_js=False)
        ok_rouge = h1_brut is None
        print(f"  [{'OK  ' if ok_rouge else 'ECHEC'}] sans --rendu-js : h1={h1_brut!r} "
              "(attendu : absent -- limite documentee)")
        if not ok_rouge:
            echecs.append("sans --rendu-js aurait du laisser le h1 absent")

        # --- VERT : avec rendu JS, Playwright execute le script, le h1 apparait
        try:
            h1_rendu = h1_crawle(racine, rendu_js=True)
        except SystemExit as e:
            print(f"  [ECHEC] avec --rendu-js : Playwright indisponible -- {e}")
            echecs.append("Playwright absent de l'environnement")
            h1_rendu = None
        else:
            ok_vert = h1_rendu == "Rendu JS"
            print(f"  [{'OK  ' if ok_vert else 'ECHEC'}] avec --rendu-js : h1={h1_rendu!r} "
                  "(attendu : 'Rendu JS')")
            if not ok_vert:
                echecs.append("avec --rendu-js aurait du capturer le h1 injecte")
    finally:
        serveur.shutdown()
        fil.join(timeout=5)

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n2/2 preuves conformes -- le flag --rendu-js change bien ce qui est mesure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
