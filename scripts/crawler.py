"""Etape 1 du pipeline : collecte par crawl. Ecrit dans seo/donnees/crawl/.

Ce que produit ce script est le seul socle `[T1 observe]` de l'etude : 29 des
87 noeuds citent le crawl dans leur methode, et les 53 noeuds marques `SD` supposent
tous qu'on peut lire le site. Sans lui, chaque audit recommence la collecte a la main
et deux audits du meme site ne sont pas comparables.

Garde-fous, tenus par construction :
  - `robots.txt` respecte, sans exception ni option pour le contourner ;
  - plafond de pages declare et applique ;
  - delai entre requetes, pour ne pas peser sur le site audite ;
  - meme hote uniquement, jamais de sortie de domaine ;
  - PAS de rendu JavaScript : ce qui est injecte cote client est invisible. Le
    resultat le declare, et les noeuds concernes basculent en non mesurable plutot
    que de conclure a l'absence d'un contenu qui existe peut-etre.

Usage :
    python scripts/crawler.py --projet . --url https://exemple.fr
    python scripts/crawler.py --projet . --url https://exemple.fr --max 500 --delai 0.3

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import deque
from html.parser import HTMLParser
from pathlib import Path

AGENT = "forge-seo/1.0 (audit SEO ; +contact via le commanditaire de l'audit)"
PLAFOND = 200
DELAI = 0.5
TIMEOUT = 15
TIMEOUT_JS_MS = 20_000

# Heuristique de gabarit : l'URL dit souvent le type de page. Approximative et
# declaree comme telle -- elle sert a stratifier l'echantillon, pas a conclure.
GABARITS = [
    (r"^/?$", "accueil"),
    (r"/(blog|actualite|article|news)/", "article"),
    (r"/(categorie|category|rubrique)/", "categorie"),
    (r"/(produit|product|gite|chambre|offre)/", "produit"),
    (r"/(contact|mentions|cgv|politique|legal)", "service"),
    (r"/(panier|checkout|commande|reservation)", "transactionnel"),
]


class Page(HTMLParser):
    """Extrait ce dont la grille a besoin, sans dependance."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = None
        self.h1 = None
        self.canonical = None
        self.robots = ""
        self.liens: list[tuple[str, bool]] = []   # (href, contextuel)
        self.mots = 0
        self._dans = None
        self._nav = 0          # profondeur dans nav/header/footer/aside
        self._script = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "header", "footer", "aside"):
            self._nav += 1
        elif tag in ("script", "style"):
            self._script += 1
        elif tag == "title" and self.title is None:
            self._dans = "title"
        elif tag == "h1" and self.h1 is None:
            self._dans = "h1"
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href")
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.robots = (a.get("content") or "").lower()
        elif tag == "a" and a.get("href"):
            self.liens.append((a["href"], self._nav == 0))

    def handle_endtag(self, tag):
        if tag in ("nav", "header", "footer", "aside"):
            self._nav = max(0, self._nav - 1)
        elif tag in ("script", "style"):
            self._script = max(0, self._script - 1)
        elif tag in ("title", "h1"):
            self._dans = None

    def handle_data(self, data):
        if self._dans == "title":
            self.title = (self.title or "") + data
        elif self._dans == "h1":
            self.h1 = (self.h1 or "") + data
        elif self._script == 0:
            self.mots += len(data.split())


def normaliser(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    chemin = p.path or "/"
    if len(chemin) > 1 and chemin.endswith("/"):
        chemin = chemin[:-1]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, chemin, p.query, ""))


def gabarit(chemin: str) -> str:
    for motif, nom in GABARITS:
        if re.search(motif, chemin):
            return nom
    return "page"


def recuperer(url: str, xml: bool = False) -> tuple[int, str, bytes, list[str]]:
    """Retourne (code, url_finale, corps, chaine_de_redirection).

    `xml=True` pour robots.txt et les sitemaps : le filtre sur le Content-Type HTML
    les jetterait sinon, et le sitemap serait declare illisible alors qu'il repond 200.
    """
    chaine: list[str] = []

    class Suivi(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            chaine.append(f"{code} → {newurl}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    ouvreur = urllib.request.build_opener(Suivi)
    req = urllib.request.Request(url, headers={
        "User-Agent": AGENT,
        "Accept": ("application/xml,text/xml,text/plain,*/*" if xml
                   else "text/html,application/xhtml+xml"),
        "Accept-Encoding": "gzip",
    })
    try:
        with ouvreur.open(req, timeout=TIMEOUT) as r:
            brut = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or url.endswith(".gz"):
                try:
                    brut = gzip.decompress(brut)
                except OSError:
                    pass
            if not xml and "html" not in (r.headers.get("Content-Type") or ""):
                return r.status, r.url, b"", chaine
            return r.status, r.url, brut, chaine
    except urllib.error.HTTPError as e:
        return e.code, url, b"", chaine
    except Exception as e:  # reseau, DNS, TLS, timeout
        return 0, url, str(e).encode(), chaine


def recuperer_rendu(page_pw, url: str) -> tuple[int, str, bytes, list[str]]:
    """Meme contrat que recuperer(), le DOM apres execution du JavaScript (TF-0105).

    `page_pw` est une page Playwright REUTILISEE d'une URL a l'autre : ouvrir un
    navigateur par page couterait un ordre de grandeur en duree sur un crawl de
    plusieurs centaines d'URL. `wait_until="networkidle"` attend que le site ait
    fini ses appels XHR d'hydratation -- c'est precisement ce qu'un fetch HTTP nu
    ne peut jamais voir (cf. la limite `rendu_javascript` declaree sans ce flag).
    """
    from playwright.sync_api import Error as ErreurPlaywright
    from playwright.sync_api import TimeoutError as DelaiPlaywright

    try:
        reponse = page_pw.goto(url, wait_until="networkidle", timeout=TIMEOUT_JS_MS)
    except DelaiPlaywright:
        # Reseau jamais silencieux (SPA qui poll en continu, par exemple) : on
        # degrade sur ce que le DOM contient AU MOMENT du timeout plutot que de
        # perdre la page entiere -- une mesure partielle vaut mieux qu'une absence.
        try:
            return 0, page_pw.url, page_pw.content().encode("utf-8"), []
        except ErreurPlaywright:
            return 0, url, b"", []
    except ErreurPlaywright as e:
        return 0, url, str(e).encode(), []
    if reponse is None:
        return 0, url, b"", []
    return reponse.status, page_pw.url, page_pw.content().encode("utf-8"), []


RE_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
RE_SITEMAP_INDEX = re.compile(r"<sitemapindex", re.I)


def lire_sitemaps(depart: str, robots_txt: str, plafond_index: int = 25) -> dict:
    """Lit le ou les sitemap.xml et retourne l'inventaire DECLARE du site (TF-0043).

    L'ancien crawler ne lisait `robots.txt` que pour ses permissions et ignorait sa
    directive `Sitemap:`. L'ensemble des URL connues n'etait alimente que par les
    liens suivis : `urls_decouvertes` ne mesurait pas le site mais ce qu'on atteint
    en navigant. Sur Produit-02.fr, 79 annoncees contre 286 declarees.

    Les index de sitemaps sont suivis d'un niveau, avec plafond. gzip supporte.
    """
    candidats, vus, urls = [], set(), []
    for ligne in (robots_txt or "").splitlines():
        if ligne.strip().lower().startswith("sitemap:"):
            candidats.append(ligne.split(":", 1)[1].strip())
    if not candidats:
        candidats = [urllib.parse.urljoin(depart, "/sitemap.xml")]

    fichiers_lus, erreurs = [], []
    file_sm = deque(candidats)
    while file_sm and len(fichiers_lus) < plafond_index:
        url = file_sm.popleft()
        if url in vus:
            continue
        vus.add(url)
        code, _, corps, _ = recuperer(url, xml=True)
        if code != 200 or not corps:
            erreurs.append(f"{url} → HTTP {code}")
            continue
        texte = corps.decode("utf-8", "replace")
        fichiers_lus.append(url)
        locs = [urllib.parse.unquote(x) for x in RE_LOC.findall(texte)]
        if RE_SITEMAP_INDEX.search(texte):
            for x in locs:
                file_sm.append(x)
        else:
            urls.extend(locs)

    hote = urllib.parse.urlsplit(depart).netloc
    propres, hors = [], 0
    for u in urls:
        n = normaliser(u)
        if urllib.parse.urlsplit(n).netloc != hote:
            hors += 1
            continue
        propres.append(n)
    return {
        "fichiers": fichiers_lus,
        "erreurs": erreurs,
        "urls": sorted(set(propres)),
        "urls_hors_hote": hors,
    }


def crawler(racine: str, plafond: int, delai: float, rendu_js: bool = False) -> dict:
    depart = normaliser(racine)
    hote = urllib.parse.urlsplit(depart).netloc

    # Playwright est optionnel : robots.txt et les sitemaps restent lus par
    # urllib (jamais de JS a y executer) ; seule la visite des pages HTML change.
    pw_ctx, navigateur, page_pw = None, None, None
    if rendu_js:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise SystemExit(
                "REFUS : --rendu-js demande Playwright, absent de cet environnement.\n"
                "Installer : pip install playwright && python -m playwright install chromium"
            ) from e
        pw_ctx = sync_playwright().start()
        navigateur = pw_ctx.chromium.launch()
        page_pw = navigateur.new_page(user_agent=AGENT)

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(depart, "/robots.txt"))
    robots_txt = ""
    try:
        rp.read()
        robots_lu = True
    except Exception:
        robots_lu = False
    _, _, brut_robots, _ = recuperer(urllib.parse.urljoin(depart, "/robots.txt"), xml=True)
    robots_txt = brut_robots.decode("utf-8", "replace") if brut_robots else ""

    sitemap = lire_sitemaps(depart, robots_txt)

    vues: dict[str, dict] = {}
    entrants: dict[str, int] = {}     # liens contextuels : flux d'autorite
    entrants_tous: dict[str, int] = {}  # tous liens : detection d'orphelines
    # L'inventaire DECLARE amorce la file : le crawl part du sitemap ET de l'accueil,
    # pas du seul graphe de liens. Les URL du sitemap sont a profondeur inconnue tant
    # qu'aucun lien n'y mene -- on les met en fin de file, apres le parcours en
    # largeur, pour que la profondeur de clic reste juste pour les pages liees.
    file = deque([(depart, 0)])
    connus = {depart}
    for u in sitemap["urls"]:
        if u not in connus:
            connus.add(u)
    bloquees = 0

    def vider_file():
        nonlocal bloquees
        while file and len(vues) < plafond:
            url, prof = file.popleft()
            if url in vues:
                continue
            if robots_lu and not rp.can_fetch(AGENT, url):
                bloquees += 1
                continue
            visiter(url, prof)

    def visiter(url, prof):
        if rendu_js:
            code, finale, corps, chaine = recuperer_rendu(page_pw, url)
        else:
            code, finale, corps, chaine = recuperer(url)
        time.sleep(delai)

        p = Page()
        if corps:
            try:
                p.feed(corps.decode("utf-8", "replace"))
            except Exception:
                pass

        chemin = urllib.parse.urlsplit(url).path or "/"
        indexable = None
        if code == 200:
            indexable = "noindex" not in p.robots
            if p.canonical:
                if normaliser(urllib.parse.urljoin(url, p.canonical)) != normaliser(url):
                    indexable = False

        vues[url] = {
            "url": chemin,
            "type_gabarit": gabarit(chemin),
            # None = page DECLAREE au sitemap qu'aucun lien interne n'atteint. Le
            # schema l'autorise, et c'est la seule valeur honnete : elle n'a pas de
            # profondeur de clic puisqu'aucun clic n'y mene.
            "profondeur_clic": prof,
            "declaree_sitemap": url in declarees,
            "decouverte": "lien" if prof is not None else "sitemap",
            "code_http": code,
            "title": (p.title or "").strip() or None,
            "h1": (p.h1 or "").strip() or None,
            "canonical": (urllib.parse.urlsplit(
                urllib.parse.urljoin(url, p.canonical)).path if p.canonical else None),
            "indexable": indexable,
            "liens_internes_entrants": 0,
            "poids_ko": round(len(corps) / 1024, 1) if corps else 0.0,
            "preuve": "T1",
            "_mots": p.mots,
            "_redirections": chaine,
        }

        for href, contextuel in p.liens:
            cible = normaliser(urllib.parse.urljoin(url, href))
            if urllib.parse.urlsplit(cible).netloc != hote:
                continue
            entrants_tous[cible] = entrants_tous.get(cible, 0) + 1
            if contextuel:
                entrants[cible] = entrants.get(cible, 0) + 1
            if cible not in vues and len(connus) < plafond * 5:
                connus.add(cible)
                file.append((cible, None if prof is None else prof + 1))

    declarees = set(sitemap["urls"])

    try:
        # Phase 1 : parcours en largeur depuis l'accueil — profondeur de clic exacte.
        vider_file()
        # Phase 2 : les URL DECLAREES au sitemap qu'aucun lien n'a fait decouvrir. Sans
        # cette phase le crawl mesure ce qu'on atteint en navigant, pas le site (TF-0043).
        restantes = [u for u in sitemap["urls"] if u not in vues]
        file.extend((u, None) for u in restantes)
        vider_file()
    finally:
        # Le navigateur se ferme meme si le crawl est interrompu (plafond, erreur) --
        # un Chromium orphelin ne se remarque qu'au prochain « port deja utilise ».
        if navigateur is not None:
            navigateur.close()
        if pw_ctx is not None:
            pw_ctx.stop()
    non_visitees = [u for u in connus if u not in vues]

    for url, v in vues.items():
        # Le champ du schema mesure le flux d'autorite : liens contextuels seuls,
        # navigation et pied de page exclus.
        v["liens_internes_entrants"] = entrants.get(url, 0)
        v["_entrants_tous"] = entrants_tous.get(url, 0)

    pages = sorted(vues.values(),
                   key=lambda x: (x["profondeur_clic"] is None,
                                  x["profondeur_clic"] or 0, x["url"]))
    # TF-0044 -- l'ancienne definition etait INSATISFIABLE : « page du crawl avec zero
    # lien entrant et profondeur > 0 ». Or une page n'entrait dans le crawl que parce
    # qu'un lien y menait. Le controle ne pouvait pas echouer, donc il ne prouvait
    # rien, et il affichait un zero rassurant sur un site a 208 orphelines.
    #
    # Definition juste : orpheline = URL DECLAREE (sitemap) qu'aucun lien interne du
    # site ne cite. Elle suppose l'inventaire declare, d'ou TF-0043 en amont.
    orphelines = sorted(
        u for u in declarees
        if entrants_tous.get(u, 0) == 0 and u != depart
    )
    # Honnetete de la mesure : les liens entrants ne sont connus que des pages
    # effectivement crawlees. Si le plafond a coupe, le compte d'orphelines est un
    # MAJORANT, et le resultat le declare plutot que de l'affirmer.
    couverture_complete = not non_visitees
    titres: dict[str, int] = {}
    for p in pages:
        if p["title"]:
            titres[p["title"]] = titres.get(p["title"], 0) + 1

    return {
        "collecte": {
            "outil": "forge-seo/crawler.py",
            "date": dt.date.today().isoformat(),
            "racine": depart,
            "plafond": plafond,
            "delai_s": delai,
            "robots_txt_lu": robots_lu,
            "urls_bloquees_par_robots": bloquees,
            "rendu_javascript": rendu_js,
            "sitemaps_lus": sitemap["fichiers"],
            "sitemaps_en_erreur": sitemap["erreurs"],
            "limite": (
                "Rendu JavaScript actif (Playwright / Chromium) : le DOM mesuré est "
                "celui obtenu après exécution du JS côté client, réseau inactif "
                "(networkidle) ou délai de 20 s atteint."
                if rendu_js else
                "Sans rendu JavaScript : le contenu injecté côté client est "
                "invisible. Ne pas conclure à l'absence d'un contenu qui "
                "pourrait ne pas être dans le HTML initial. Relancer avec "
                "--rendu-js sur un site suspecté SPA."
            ),
            "limite_orphelines": (
                "Compte exact : toutes les URL déclarées ont été crawlées."
                if couverture_complete else
                f"MAJORANT : {len(vues)} URL crawlées sur {len(connus)} connues "
                f"(plafond {plafond}). Les liens sortants des pages non crawlées ne "
                "sont pas comptés — une page ici dite orpheline peut être citée par "
                "l'une d'elles. Relancer avec --max supérieur pour un compte exact."),
        },
        "synthese": {
            "pages_crawlees": len(pages),
            "urls_decouvertes": len(connus),
            "urls_declarees_sitemap": len(declarees),
            "urls_declarees_non_crawlees": len([u for u in declarees if u not in vues]),
            "profondeur_max": max((p["profondeur_clic"] or 0 for p in pages), default=0),
            "erreurs_4xx_5xx": sum(1 for p in pages if p["code_http"] >= 400),
            "non_indexables": sum(1 for p in pages if p["indexable"] is False),
            "pages_orphelines": len(orphelines),
            "pages_orphelines_exemples": orphelines[:10],
            "orphelines_compte_exact": couverture_complete,
            "pages_sans_lien_contextuel": sum(
                1 for p in pages if p["liens_internes_entrants"] == 0),
            "titles_dupliques": sum(n for n in titres.values() if n > 1) -
                                sum(1 for n in titres.values() if n > 1),
            "pages_fines_sous_300_mots": sum(1 for p in pages if 0 < p["_mots"] < 300),
        },
        "pages": pages,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Crawl du site audité — étape 1 du pipeline.")
    p.add_argument("--projet", required=True, help="chemin du projet audité")
    p.add_argument("--url", required=True, help="URL racine du site")
    p.add_argument("--max", type=int, default=PLAFOND, help=f"plafond de pages ({PLAFOND})")
    p.add_argument("--delai", type=float, default=DELAI, help=f"délai entre requêtes ({DELAI}s)")
    p.add_argument(
        "--rendu-js", action="store_true",
        help="rend le JavaScript côté client avant de lire le DOM (Playwright/Chromium) "
             "— pour les sites SPA, où le HTML brut mesure un contenu tronqué (TF-0105)",
    )
    args = p.parse_args()

    dossier = Path(args.projet).resolve() / "seo" / "donnees" / "crawl"
    if not dossier.parent.parent.is_dir():
        print(f"{dossier.parent.parent} absent — créer l'étude avec new_mission.py")
        return 1
    dossier.mkdir(parents=True, exist_ok=True)

    print(f"crawl de {args.url} — plafond {args.max} pages, délai {args.delai}s"
          + (", rendu JS actif (Playwright)" if args.rendu_js else ""))
    debut = time.time()
    res = crawler(args.url, args.max, args.delai, rendu_js=args.rendu_js)
    s = res["synthese"]

    # Le netloc peut porter un port (`localhost:8765`) : sous Windows, un `:` dans
    # un nom de fichier cree un flux de donnees alterne NTFS — le fichier semble
    # ecrit et n'existe pas comme fichier. On assainit toujours.
    domaine = re.sub(r"[^A-Za-z0-9.-]+", "-",
                     urllib.parse.urlsplit(res["collecte"]["racine"]).netloc)
    cible = dossier / f"crawl-{domaine}-{dt.date.today():%Y%m%d}.json"
    cible.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nécrit : {cible.relative_to(Path(args.projet).resolve())}")
    print(f"  durée               : {round(time.time() - debut)} s")
    print(f"  pages crawlées      : {s['pages_crawlees']} / {res['collecte']['plafond']}")
    print(f"  URLs découvertes    : {s['urls_decouvertes']}")
    print(f"  déclarées au sitemap: {s['urls_declarees_sitemap']} "
          f"({len(res['collecte']['sitemaps_lus'])} fichier(s) lu(s))")
    print(f"  profondeur max      : {s['profondeur_max']} clics")
    print(f"  erreurs 4xx/5xx     : {s['erreurs_4xx_5xx']}")
    print(f"  non indexables      : {s['non_indexables']}")
    print(f"  pages orphelines    : {s['pages_orphelines']}"
          f"{'' if s['orphelines_compte_exact'] else ' (MAJORANT — plafond atteint)'}")
    print(f"  titles dupliqués    : {s['titles_dupliques']}")
    print(f"  pages < 300 mots    : {s['pages_fines_sous_300_mots']}")
    if not res["collecte"]["robots_txt_lu"]:
        print("  ATTENTION robots.txt illisible — crawl mené sans ses directives")
    if res["collecte"]["urls_bloquees_par_robots"]:
        print(f"  {res['collecte']['urls_bloquees_par_robots']} URL(s) écartée(s) par robots.txt")
    print("\nÉtape suivante : python scripts/livrables.py --projet <chemin>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
