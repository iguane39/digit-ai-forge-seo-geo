"""Preuve a double sens de l'extraction JSON-LD au crawl (TF-0105, noeud 32).

  VERT  : deux scripts application/ld+json valides, dont un `@graph` groupant
          plusieurs entites (motif courant des plugins SEO) -- les trois
          entites sont extraites et comptees individuellement par @type.
  ROUGE : un script application/ld+json syntaxiquement invalide -- attendu :
          zero bloc valide, UNE erreur declaree (pas une extraction silencieuse
          qui l'ignorerait, pas un crash qui perdrait toute la page).

Aucun appel reseau externe : serveur local, port ephemere.

Usage :
    python scripts/test_json_ld.py
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler import crawler

PAGE_VALIDE = b"""<!doctype html>
<html><head><title>Fiche produit</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Chaise"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"Organization","name":"Acme"},
  {"@type":"WebSite","name":"Acme"}
]}
</script>
</head><body><h1>Chaise</h1></body></html>
"""

PAGE_INVALIDE = b"""<!doctype html>
<html><head><title>Page mal balisee</title>
<script type="application/ld+json">
{ceci n'est pas du JSON valide}
</script>
</head><body><h1>Page</h1></body></html>
"""


def gabarit_serveur(corps: bytes):
    class Gabarit(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)
            else:
                self.send_response(404)
                self.end_headers()

    return Gabarit


def crawl_une_page(corps: bytes) -> dict:
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), gabarit_serveur(corps))
    port = serveur.server_address[1]
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    try:
        res = crawler(f"http://127.0.0.1:{port}/", plafond=1, delai=0)
        return res["pages"][0], res["synthese"]
    finally:
        serveur.shutdown()
        fil.join(timeout=5)


def main() -> int:
    echecs = []

    page, synthese = crawl_une_page(PAGE_VALIDE)
    ok_blocs = len(page["json_ld"]) == 2
    ok_erreurs = page["json_ld_erreurs"] == []
    ok_types = synthese["types_json_ld"] == {"Organization": 1, "Product": 1, "WebSite": 1}
    print(f"  [{'OK  ' if ok_blocs else 'ECHEC'}] VERT  2 blocs JSON-LD extraits "
          f"(dont @graph deplie) -- {len(page['json_ld'])} bloc(s)")
    print(f"  [{'OK  ' if ok_erreurs else 'ECHEC'}] VERT  aucune erreur sur du JSON-LD valide")
    print(f"  [{'OK  ' if ok_types else 'ECHEC'}] VERT  3 entites comptees par @type -- "
          f"{synthese['types_json_ld']}")
    if not (ok_blocs and ok_erreurs and ok_types):
        echecs.append("extraction JSON-LD valide")

    page2, synthese2 = crawl_une_page(PAGE_INVALIDE)
    ok_zero_valide = page2["json_ld"] == []
    ok_une_erreur = len(page2["json_ld_erreurs"]) == 1
    ok_page_pas_perdue = page2["code_http"] == 200  # le crawl de la page continue
    print(f"  [{'OK  ' if ok_zero_valide else 'ECHEC'}] ROUGE JSON-LD invalide -- "
          f"0 bloc valide (obtenu {len(page2['json_ld'])})")
    print(f"  [{'OK  ' if ok_une_erreur else 'ECHEC'}] ROUGE JSON-LD invalide -- "
          f"1 erreur declaree, pas avalee (obtenu {len(page2['json_ld_erreurs'])})")
    print(f"  [{'OK  ' if ok_page_pas_perdue else 'ECHEC'}] ROUGE la page reste crawlee "
          "malgre le JSON-LD casse (pas de crash)")
    if not (ok_zero_valide and ok_une_erreur and ok_page_pas_perdue):
        echecs.append("declaration d'erreur sur JSON-LD invalide")

    if echecs:
        print(f"\nECHECS : {echecs}")
        return 1
    print("\n6/6 preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
