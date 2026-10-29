"""Preuve a double sens de l'oracle des redirections (TF-1997, noeud 28).

Fixtures synthetiques uniquement (domaines example.com, serveur HTTP local sur
127.0.0.1) : aucune donnee client, aucun appel reseau sortant, rien d'ecrit dans
la forge -- les fichiers passent par un dossier temporaire du systeme.

Le fait qui fonde l'oracle, mesure par le pilot le 25/08/2026 : dans une Page Rule,
`$1` dans l'URL cible preserve le chemin. La meme reference s'ecrit `${1}` dans une
Single Redirect et `:splat` dans un fichier `_redirects` ; recopiee telle quelle
d'un vehicule a l'autre, elle arrive litterale dans l'en-tete Location, et chaque
lien profond atterrit sur une URL cassee ou sur l'accueil.

  VERT  : les formes que la documentation lue le 29/10/2026 decrit passent, pour
          chacun des cinq vehicules (cas tires des exemples des pages).
  ROUGE : reference d'un autre vehicule, chemin perdu, reference sans joker, motif
          qui ne correspond jamais : chaque defaut est refuse pour la bonne raison.
  REMEDE JOUE (TF-1013) : la cible que l'oracle propose en remede, rejugee, passe.
  DONNEE : la syntaxe vient de referentiel/cloudflare.json ; un referentiel altere
          change le verdict, preuve que rien n'est code en dur.
  SONDE : un serveur local rend les redirections fautives et justes ; la sonde
          les distingue sans suivre la redirection.

Usage :
    python scripts/test_oracle_redirections.py
"""

from __future__ import annotations

import copy
import http.server
import io
import json
import socket
import sys
import tempfile
import threading
from contextlib import redirect_stdout
from pathlib import Path

from oracle_redirections import (
    AVERTISSEMENT,
    BLOQUANT,
    analyser_bulk_redirects,
    analyser_fichier_redirects,
    analyser_page_rules,
    analyser_single_redirects,
    assembler,
    charger_referentiel,
    detecter_vehicule,
    main,
    sonder,
)

REF = charger_referentiel()
cas: list[tuple[str, bool, str]] = []


def noter(etiquette: str, nom: str, ok: bool, detail: str = "") -> None:
    cas.append((f"{etiquette} {nom}", ok, detail))


def genres(regle: dict) -> set[tuple[str, str]]:
    """(genre, gravite) des constats non assumes d'une regle ou d'une sonde."""
    return {(c["genre"], c["gravite"]) for c in regle["constats"] if not c.get("assume")}


def bloquants(regle: dict) -> set[str]:
    return {g for g, grav in genres(regle) if grav == BLOQUANT}


def une(regles: list[dict]) -> dict:
    assert len(regles) == 1, f"une regle attendue, {len(regles)} obtenue(s)"
    return regles[0]


def suggestion(regle: dict, genre: str) -> str | None:
    for c in regle["constats"]:
        if c["genre"] == genre:
            return c.get("cible_suggeree")
    return None


# --- fichier _redirects (Workers Static Assets et Pages) ------------------------------
def cas_fichier_redirects() -> None:
    def juger(ligne: str) -> dict:
        return une(analyser_fichier_redirects(ligne + "\n", REF, "_redirects"))

    r = juger("/blog/* https://blog.example.com/:splat 301")
    noter("VERT ", "_redirects : * repris par :splat, 301", not genres(r), str(genres(r)))

    r = juger("/blog/* https://blog.example.com/$1 301")
    noter("ROUGE", "_redirects : $1 des Page Rules recopie (fait du 25/08 transpose) -> jeton litteral",
          "jeton-litteral" in bloquants(r), str(genres(r)))
    s = suggestion(r, "jeton-litteral")
    r2 = juger(f"/blog/* {s} 301") if s else None
    noter("REMED", "_redirects : la cible proposee (:splat) passe une fois rejugee",
          r2 is not None and not bloquants(r2), f"suggestion={s!r}")

    r = juger("/blog/* https://blog.example.com/ 301")
    noter("ROUGE", "_redirects : * sans :splat -> chemin perdu", "chemin-perdu" in bloquants(r), str(genres(r)))
    s = suggestion(r, "chemin-perdu")
    r2 = juger(f"/blog/* {s} 301") if s else None
    noter("REMED", "_redirects : la cible proposee pour le chemin perdu passe",
          r2 is not None and not bloquants(r2), f"suggestion={s!r}")

    r = juger("/movies/:title /media/:title 301")
    noter("VERT ", "_redirects : parametre nomme repris (exemple de la page)", not genres(r), str(genres(r)))

    r = juger("/movies/:title /media/ 301")
    noter("ROUGE", "_redirects : parametre nomme non repris -> chemin perdu",
          "chemin-perdu" in bloquants(r), str(genres(r)))

    r = juger("/ancien /nouveau")
    noter("AVERT", "_redirects : code absent = 302 par defaut, signale sans bloquer",
          genres(r) == {("code-non-permanent", AVERTISSEMENT)}, str(genres(r)))

    r = juger("/a /b 301 Country=us")
    noter("AVERT", "_redirects : ligne hors format, ignoree par Cloudflare, signalee",
          ("ligne-ignoree", AVERTISSEMENT) in genres(r) and not bloquants(r), str(genres(r)))

    r = juger("/page https://example.com/:splat 301")
    noter("ROUGE", "_redirects : :splat sans joker dans la source -> reference hors joker",
          "reference-hors-joker" in bloquants(r), str(genres(r)))

    r = juger("/blog/* https://blog.example.com/${1} 301")
    noter("ROUGE", "_redirects : ${1} des Single Redirects -> jeton litteral",
          "jeton-litteral" in bloquants(r), str(genres(r)))

    regles = analyser_fichier_redirects("# commentaire\n\n   \n", REF, "_redirects")
    noter("VERT ", "_redirects : commentaires et lignes vides ne font pas de regle",
          regles == [], f"{len(regles)} regle(s)")


# --- Page Rules (Forwarding URL) ------------------------------------------------------
def page_rule(motif: str, url: str, code: int = 301, statut: str = "active", ident: str = "pr1") -> dict:
    return {"result": [{"id": ident, "status": statut,
                        "targets": [{"target": "url", "constraint": {"operator": "matches", "value": motif}}],
                        "actions": [{"id": "forwarding_url", "value": {"url": url, "status_code": code}}]}]}


def cas_page_rules() -> None:
    def juger(motif: str, url: str, code: int = 301) -> dict:
        return une(analyser_page_rules(page_rule(motif, url, code), REF))

    r = juger("example.com/*", "https://www.example.com/$1")
    noter("VERT ", "Page Rule : example.com/* -> /$1, la forme mesuree le 25/08", not genres(r), str(genres(r)))

    r = juger("example.com/*", "https://www.example.com/")
    noter("ROUGE", "Page Rule : cible sans variable -> chemin perdu (« you lose anything else in the URL »)",
          "chemin-perdu" in bloquants(r), str(genres(r)))
    s = suggestion(r, "chemin-perdu")
    r2 = juger("example.com/*", s) if s else None
    noter("REMED", "Page Rule : la cible proposee ($1) passe", r2 is not None and not bloquants(r2), f"{s!r}")

    r = juger("*example.com/*", "https://www.example.com/$1")
    noter("ROUGE", "Page Rule : *example.com/* -> /$1 reprend le sous-domaine, pas le chemin",
          "chemin-perdu" in bloquants(r), str(genres(r)))
    s = suggestion(r, "chemin-perdu")
    r2 = juger("*example.com/*", s) if s else None
    noter("REMED", "Page Rule : la cible proposee ($2) passe",
          r2 is not None and not bloquants(r2) and s == "https://www.example.com/$2", f"{s!r}")

    r = juger("example.com/*", "https://www.example.com/$2")
    noter("ROUGE", "Page Rule : $2 avec un seul joker -> reference hors joker",
          "reference-hors-joker" in bloquants(r), str(genres(r)))

    r = juger("example.com/*", "https://www.example.com/:splat")
    noter("ROUGE", "Page Rule : :splat de _redirects -> jeton litteral",
          "jeton-litteral" in bloquants(r), str(genres(r)))

    r = juger("example.com/*", "https://www.example.com/${1}")
    noter("AVERT", "Page Rule : ${1}, forme non attestee par une mesure -> avertissement, la sonde tranche",
          ("forme-non-documentee", AVERTISSEMENT) in genres(r) and not bloquants(r), str(genres(r)))

    r = juger("example.com/*", "https://www.example.com/$1", code=302)
    noter("AVERT", "Page Rule : 302 -> code non permanent, sans bloquer",
          genres(r) == {("code-non-permanent", AVERTISSEMENT)}, str(genres(r)))

    r = juger("example.com/*", "https://www.example.com/prix\\$1")
    noter("ROUGE", "Page Rule : \\$1 echappe est un dollar litteral, le chemin est perdu",
          "chemin-perdu" in bloquants(r), str(genres(r)))

    autres = {"result": [
        {"id": "a", "status": "active", "targets": [{"target": "url", "constraint": {"value": "example.com/*"}}],
         "actions": [{"id": "browser_check", "value": "on"}]},
        page_rule("example.com/*", "https://www.example.com/", statut="disabled")["result"][0],
    ]}
    regles = analyser_page_rules(autres, REF)
    noter("VERT ", "Page Rule : une regle sans renvoi ou desactivee n'est pas jugee", regles == [],
          f"{len(regles)} regle(s)")


# --- Single Redirects ----------------------------------------------------------------
def single(expression: str, cible: dict, code: int = 301, ident: str = "sr1") -> dict:
    return {"result": {"phase": "http_request_dynamic_redirect", "rules": [
        {"id": ident, "expression": expression, "action": "redirect",
         "action_parameters": {"from_value": {"target_url": cible, "status_code": code,
                                              "preserve_query_string": True}}}]}}


def wr(champ: str, motif: str, remplacement: str) -> dict:
    return {"expression": f'wildcard_replace({champ}, r"{motif}", r"{remplacement}")'}


def cas_single_redirects() -> None:
    def juger(expression: str, cible: dict) -> dict:
        return une(analyser_single_redirects(single(expression, cible), REF))

    expr_www = 'http.request.full_uri wildcard r"https://www.example.com/*"'
    r = juger(expr_www, wr("http.request.full_uri", "https://www.example.com/*", "https://example.com/${1}"))
    noter("VERT ", "Single Redirect : exemple 1 du guide de migration (${1})", not genres(r), str(genres(r)))

    expr_http = 'http.request.full_uri wildcard r"http*://www.example.com/*"'
    r = juger(expr_http, wr("http.request.full_uri", "http*://www.example.com/*", "https://example.com/${1}"))
    noter("ROUGE", "Single Redirect : motif http*:// avec ${1} reprend le schema -> chemin perdu",
          "chemin-perdu" in bloquants(r), str(genres(r)))
    s = suggestion(r, "chemin-perdu")
    r2 = juger(expr_http, wr("http.request.full_uri", "http*://www.example.com/*", s)) if s else None
    noter("REMED", "Single Redirect : le remplacement propose (${2}, note du guide) passe",
          r2 is not None and not bloquants(r2) and s == "https://example.com/${2}", f"{s!r}")

    r = juger(expr_www, wr("http.request.full_uri", "https://www.example.com/*", "https://example.com/$1"))
    noter("AVERT", "Single Redirect : $1 recopie d'une Page Rule -> forme non documentee, la sonde tranche",
          ("forme-non-documentee", AVERTISSEMENT) in genres(r) and not bloquants(r), str(genres(r)))

    r = juger('http.request.uri.path wildcard "/blog/*"', {"value": "https://example.com/$1"})
    noter("ROUGE", "Single Redirect statique : $1 dans une chaine litterale -> jeton litteral",
          "jeton-litteral" in bloquants(r), str(genres(r)))

    r = juger('http.host eq "old.example.com"', {"value": "https://example.com/"})
    noter("ROUGE", "Single Redirect statique sans condition de chemin -> tous les chemins vers une URL",
          "chemin-perdu" in bloquants(r), str(genres(r)))

    r = juger('http.request.uri.path eq "/contacts.html"', {"value": "https://example.com/contact"})
    noter("VERT ", "Single Redirect statique d'une seule page -> rien a preserver", not genres(r), str(genres(r)))

    r = juger('http.request.uri.path wildcard "/applications/*"',
              wr("http.request.full_uri", "/applications/*", "/apps/${1}"))
    noter("ROUGE", "Single Redirect : motif de chemin sur full_uri ne correspond jamais (exemple de la page)",
          "motif-jamais-apparie" in bloquants(r), str(genres(r)))

    r = juger('http.host eq "old.example.com"',
              {"expression": 'concat("https://new.example.com", http.request.uri.path)'})
    noter("VERT ", "Single Redirect dynamique qui reprend http.request.uri.path", not genres(r), str(genres(r)))

    r = juger('http.host eq "old.example.com"', {"expression": 'concat("https://new.example.com", "/accueil")'})
    noter("ROUGE", "Single Redirect dynamique qui ne reprend aucun champ de chemin -> chemin perdu",
          "chemin-perdu" in bloquants(r), str(genres(r)))


# --- Bulk Redirects ------------------------------------------------------------------
def bulk(**redirect) -> dict:
    base = {"source_url": "example.com/ancien/", "target_url": "https://example.com/nouveau/", "status_code": 301}
    base.update(redirect)
    return {"result": [{"id": "b1", "redirect": base}]}


def cas_bulk_redirects() -> None:
    r = une(analyser_bulk_redirects(bulk(subpath_matching=True, preserve_path_suffix=True), REF))
    noter("VERT ", "Bulk : sous-chemins et suffixe preserve", not genres(r), str(genres(r)))

    r = une(analyser_bulk_redirects(bulk(subpath_matching=True, preserve_path_suffix=False), REF))
    noter("ROUGE", "Bulk : preserve_path_suffix false -> chemin perdu (exemple de la page)",
          "chemin-perdu" in bloquants(r), str(genres(r)))
    s = next((c.get("parametre_suggere") for c in r["constats"] if c["genre"] == "chemin-perdu"), None)
    r2 = une(analyser_bulk_redirects(bulk(subpath_matching=True, **(s or {})), REF)) if s else None
    noter("REMED", "Bulk : le parametre propose (preserve_path_suffix true) passe",
          r2 is not None and not bloquants(r2), f"{s!r}")

    r = une(analyser_bulk_redirects(bulk(target_url="https://example.com/nouveau/$1", subpath_matching=True), REF))
    noter("ROUGE", "Bulk : $1 dans une cible statique -> jeton litteral",
          "jeton-litteral" in bloquants(r), str(genres(r)))

    r = une(analyser_bulk_redirects(bulk(subpath_matching=False, preserve_path_suffix=False), REF))
    noter("VERT ", "Bulk : correspondance exacte, rien a preserver", not genres(r), str(genres(r)))

    r = une(analyser_bulk_redirects(bulk(subpath_matching=True), REF))
    noter("VERT ", "Bulk : preserve_path_suffix absent vaut true (defaut documente)", not genres(r), str(genres(r)))


# --- assomption, detection, donnee ---------------------------------------------------
def cas_assomption_detection_donnee() -> None:
    perdu = analyser_page_rules(page_rule("old.example.com/*", "https://www.example.com/", ident="vers-accueil"), REF)
    res = assembler(perdu, [], ["page-rules:vers-accueil"], REF)
    noter("VERT ", "assume : un regroupement decide sur l'accueil n'est plus bloquant, et reste affiche",
          res["verdict"] == "PASS" and any(c.get("assume") for c in res["regles"][0]["constats"]),
          res["verdict"])

    litteral = analyser_page_rules(page_rule("example.com/*", "https://www.example.com/:splat", ident="x"), REF)
    res = assembler(litteral, [], ["page-rules:x"], REF)
    noter("ROUGE", "assume : ne couvre jamais un jeton litteral (aucune intention ne le justifie)",
          res["verdict"] == "FAIL", res["verdict"])

    noter("VERT ", "detection : reponse de l'API Page Rules",
          detecter_vehicule(page_rule("a/*", "b")) == "page-rules", "")
    noter("VERT ", "detection : ruleset de la phase http_request_dynamic_redirect",
          detecter_vehicule(single("true", {"value": "x"})) == "single-redirects", "")
    noter("VERT ", "detection : elements d'une liste Bulk Redirects",
          detecter_vehicule(bulk()) == "bulk-redirects", "")
    noter("ROUGE", "detection : un JSON inconnu n'est attribue a aucun vehicule",
          detecter_vehicule({"autre": 1}) is None, "")

    altere = copy.deepcopy(REF)
    for v in altere["vehicules_redirection"]:
        if v["id"] == "page-rules":
            v["references"] = [{"motif": "%([1-9])", "porte": "joker", "sonde": False}]
    r = une(analyser_page_rules(page_rule("example.com/*", "https://www.example.com/$1"), altere))
    noter("DONNE", "la syntaxe vient du referentiel : $1 n'y est plus une reference -> chemin perdu",
          "chemin-perdu" in bloquants(r), str(genres(r)))


# --- sonde contre un serveur local ---------------------------------------------------
class _Serveur(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_GET(self):
        p = self.path
        reste = p.split("/", 2)[2] if p.count("/") >= 2 else ""
        if p.startswith("/bon/"):
            self._rediriger(301, f"http://127.0.0.1:{self.server.server_port}/nouveau/{reste}")
        elif p.startswith("/perdu/"):
            self._rediriger(301, "/")
        elif p.startswith("/litteral/"):
            self._rediriger(301, "/nouveau/$1")
        elif p.startswith("/accolades/"):
            self._rediriger(301, "/nouveau/$%7B1%7D")
        elif p.startswith("/temporaire/"):
            self._rediriger(302, f"/nouveau/{reste}")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def _rediriger(self, code: int, location: str) -> None:
        self.send_response(code)
        self.send_header("Location", location)
        self.end_headers()


def port_ferme() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def cas_sonde() -> None:
    serveur = http.server.HTTPServer(("127.0.0.1", 0), _Serveur)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    base = f"http://127.0.0.1:{serveur.server_port}"
    temoin = "forge-seo-sonde-test/temoin"
    try:
        s = sonder(f"{base}/bon", temoin=temoin, ref=REF)
        noter("VERT ", "sonde : 301 qui porte le chemin temoin", s["joignable"] and not genres(s), str(genres(s)))
        s = sonder(f"{base}/perdu", temoin=temoin, ref=REF)
        noter("ROUGE", "sonde : 301 vers l'accueil -> chemin perdu", "chemin-perdu" in bloquants(s), str(genres(s)))
        s = sonder(f"{base}/litteral", temoin=temoin, ref=REF)
        noter("ROUGE", "sonde : Location porte $1 tel quel -> jeton litteral",
              "jeton-litteral" in bloquants(s), str(genres(s)))
        s = sonder(f"{base}/accolades", temoin=temoin, ref=REF)
        noter("ROUGE", "sonde : ${1} encode en pourcents est decode puis refuse",
              "jeton-litteral" in bloquants(s), str(genres(s)))
        s = sonder(f"{base}/temporaire", temoin=temoin, ref=REF)
        noter("AVERT", "sonde : 302 qui porte le chemin -> code non permanent seulement",
              genres(s) == {("code-non-permanent", AVERTISSEMENT)}, str(genres(s)))
        s = sonder(f"{base}/page", temoin=temoin, ref=REF)
        noter("AVERT", "sonde : 200 -> aucune redirection, signale",
              genres(s) == {("sans-redirection", AVERTISSEMENT)}, str(genres(s)))
    finally:
        serveur.shutdown()
        serveur.server_close()

    s = sonder(f"http://127.0.0.1:{port_ferme()}/x", temoin=temoin, ref=REF, delai=2)
    res = assembler([], [s], [], REF)
    noter("ROUGE", "sonde : hote injoignable -> non mesurable, jamais compte conforme",
          s["joignable"] is False and res["verdict"] == "SKIP" and res["compte"]["conformes"] == 0,
          f"verdict={res['verdict']} conformes={res['compte']['conformes']}")


# --- ligne de commande ---------------------------------------------------------------
def jouer(argv: list[str]) -> tuple[int, str]:
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        code = main(argv)
    return code, tampon.getvalue()


def cas_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        mauvais = d / "mauvais" / "_redirects"
        mauvais.parent.mkdir()
        mauvais.write_text("/blog/* https://blog.example.com/$1 301\n", encoding="utf-8")
        bon = d / "bon" / "_redirects"
        bon.parent.mkdir()
        bon.write_text("/blog/* https://blog.example.com/:splat 301\n", encoding="utf-8")
        export = d / "pagerules.json"
        export.write_text(json.dumps(page_rule("example.com/*", "https://www.example.com/")), encoding="utf-8")

        code, sortie = jouer(["--regles", str(mauvais)])
        noter("ROUGE", "CLI : un _redirects fautif sort en 1", code == 1 and "jeton-litteral" in sortie, f"exit {code}")
        code, sortie = jouer(["--regles", str(bon)])
        noter("VERT ", "CLI : un _redirects juste sort en 0", code == 0, f"exit {code}")
        code, sortie = jouer(["--regles", str(export)])
        noter("ROUGE", "CLI : un export Page Rules est reconnu sans --vehicule et refuse",
              code == 1 and "chemin-perdu" in sortie, f"exit {code}")
        code, sortie = jouer(["--regles", str(export), "--assume", "page-rules:pr1"])
        noter("VERT ", "CLI : --assume rend la main en 0 et garde la trace", code == 0 and "assum" in sortie,
              f"exit {code}")
        code, _ = jouer([])
        noter("ROUGE", "CLI : rien a juger sort en 2", code == 2, f"exit {code}")

        etude = d / "projet"
        (etude / "seo" / "donnees" / "crawl").mkdir(parents=True)
        code, _ = jouer(["--regles", str(bon), "--projet", str(etude)])
        ecrits = list((etude / "seo" / "donnees" / "crawl").glob("redirections-*.json"))
        lu = json.loads(ecrits[0].read_text(encoding="utf-8")) if ecrits else {}
        noter("VERT ", "CLI : --projet ecrit le verdict horodate dans seo/donnees/crawl/",
              code == 0 and len(ecrits) == 1 and lu.get("verdict") == "PASS" and lu.get("noeuds") == [28],
              f"{len(ecrits)} fichier(s)")
        code, _ = jouer(["--regles", str(bon), "--projet", str(d / "pas-une-etude")])
        noter("ROUGE", "CLI : --projet hors d'une etude est refuse (exit 2)", code == 2, f"exit {code}")


def main_test() -> int:
    cas_fichier_redirects()
    cas_page_rules()
    cas_single_redirects()
    cas_bulk_redirects()
    cas_assomption_detection_donnee()
    cas_sonde()
    cas_cli()
    echecs = 0
    for nom, ok, detail in cas:
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom}" + (f" -- {detail}" if detail and not ok else ""))
        echecs += 0 if ok else 1
    if echecs:
        print(f"\nECHECS : {echecs}")
        print(f"{len(cas) - echecs}/{len(cas)} preuves conformes")
        return 1
    print(f"\n{len(cas)}/{len(cas)} preuves conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main_test())
