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
# Borne DURE de `--jusqu-a-epuisement` : « jusqu'a epuisement » ne veut pas dire
# « sans limite ». Un site a pagination infinie ou a parametres combinatoires
# engendre une file qui ne se vide jamais ; la borne est declaree au resultat,
# et si elle est atteinte le crawl retombe dans le cas « couverture incomplete »,
# donc dans le refus motive -- jamais dans un chiffre qu'on croirait complet.
BORNE_DURE = 2000
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


def jeton(attrs: dict, nom: str) -> str:
    """Valeur d'un attribut normalisee pour COMPARAISON : minuscules, blancs reduits.

    TF-0262 -- un detecteur de balisage ne doit JAMAIS dependre de l'ordre d'ecriture
    des attributs. Le run du 15/08 a conclu « aucune balise canonique sur 79 pages »
    et fonde une action dessus : l'outil cherchait `rel="canonical"` PUIS `href`, le
    site ecrivait `href` en premier. Une absence etant indiscernable d'une
    non-detection, rien ne pouvait l'attraper. On passe donc par les paires
    d'attributs rendues par HTMLParser -- ou l'ordre n'existe plus -- et jamais par
    une expression reguliere qui lit la balise de gauche a droite.
    `scripts/test_balisage.py` le prouve a double sens : une fixture rouge portant
    `href` avant `rel` fait echouer le detecteur naif et passer celui-ci.
    """
    return " ".join((attrs.get(nom) or "").split()).lower()


def valeur(attrs: dict, nom: str) -> str | None:
    """Valeur d'un attribut telle quelle (casse preservee : URL, contenu), ou None."""
    v = (attrs.get(nom) or "").strip()
    return v or None


class Page(HTMLParser):
    """Extrait ce dont la grille a besoin, sans dependance."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = None
        self.h1 = None
        self.canonical = None
        self.robots = ""
        self.hreflang: list[dict] = []      # noeud 30 : coherence canonical / hreflang
        self.og: dict[str, str] = {}        # noeud 32 : balisage de partage
        self.liens: list[tuple[str, bool]] = []   # (href, contextuel)
        self.mots = 0
        self._dans = None
        self._nav = 0          # profondeur dans nav/header/footer/aside
        self._script = 0
        self.json_ld_bruts: list[str] = []  # un script application/ld+json = une entree
        self._dans_ldjson = False
        self._ldjson_buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "header", "footer", "aside"):
            self._nav += 1
        elif tag in ("script", "style"):
            self._script += 1
            if tag == "script" and (a.get("type") or "").strip().lower() == "application/ld+json":
                self._dans_ldjson = True
                self._ldjson_buf = []
        elif tag == "title" and self.title is None:
            self._dans = "title"
        elif tag == "h1" and self.h1 is None:
            self._dans = "h1"
        elif tag == "link":
            # `rel` est une liste de jetons separes par des blancs (`rel="alternate
            # canonical"` est licite) : on teste l'appartenance, jamais l'egalite.
            rels = set(jeton(a, "rel").split())
            if "canonical" in rels and valeur(a, "href") and self.canonical is None:
                self.canonical = valeur(a, "href")
            if "alternate" in rels and jeton(a, "hreflang"):
                self.hreflang.append({
                    "hreflang": jeton(a, "hreflang"),
                    "href": valeur(a, "href"),
                })
        elif tag == "meta":
            # Open Graph s'ecrit `property=`, quelques CMS emettent `name=` : les deux
            # sont lus. Le couple (cle, contenu) se lit par nom d'attribut, donc
            # independamment de l'ordre d'ecriture.
            nom = jeton(a, "name")
            if nom == "robots":
                self.robots = jeton(a, "content")
            cle = jeton(a, "property") or nom
            if cle.startswith("og:") and valeur(a, "content"):
                self.og.setdefault(cle, valeur(a, "content"))
        elif tag == "a" and a.get("href"):
            self.liens.append((a["href"], self._nav == 0))

    def handle_endtag(self, tag):
        if tag in ("nav", "header", "footer", "aside"):
            self._nav = max(0, self._nav - 1)
        elif tag in ("script", "style"):
            self._script = max(0, self._script - 1)
            if tag == "script" and self._dans_ldjson:
                self.json_ld_bruts.append("".join(self._ldjson_buf))
                self._dans_ldjson = False
                self._ldjson_buf = []
        elif tag in ("title", "h1"):
            self._dans = None

    def handle_data(self, data):
        if self._dans_ldjson:
            self._ldjson_buf.append(data)
        elif self._dans == "title":
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


def crawler(racine: str, plafond: int, delai: float, rendu_js: bool = False,
            jusqu_a_epuisement: bool = False, borne_dure: int = BORNE_DURE) -> dict:
    depart = normaliser(racine)
    hote = urllib.parse.urlsplit(depart).netloc
    # Option assumee (TF-0261) : plutot que de rendre un compte tronque, on releve
    # le plafond jusqu'a vider la file -- sous une borne dure, declaree au resultat.
    plafond_effectif = borne_dure if jusqu_a_epuisement else plafond

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
        while file and len(vues) < plafond_effectif:
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

        # Extraction JSON-LD (TF-0105, noeud 32) : chaque script application/ld+json
        # est parse independamment -- un bloc invalide n'invalide pas les autres, et
        # l'erreur est conservee plutot qu'avalee (une page mal balisee doit le rester
        # dans le rapport, pas redevenir muette).
        json_ld, json_ld_erreurs = [], []
        for brut in p.json_ld_bruts:
            brut = brut.strip()
            if not brut:
                continue
            try:
                json_ld.append(json.loads(brut))
            except json.JSONDecodeError as e:
                json_ld_erreurs.append(str(e))

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
            "hreflang": p.hreflang,
            "og": p.og,
            "indexable": indexable,
            "liens_internes_entrants": 0,
            "poids_ko": round(len(corps) / 1024, 1) if corps else 0.0,
            "preuve": "T1",
            "json_ld": json_ld,
            "json_ld_erreurs": json_ld_erreurs,
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
            if cible not in vues and len(connus) < plafond_effectif * 5:
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
    # TF-0261 -- un chiffre marque « MAJORANT » reste un chiffre qu'on cite. Le
    # 15/08, « orphelines 89 (MAJORANT) » est parti tel quel dans un rapport ; la
    # relance a --max 320 en donnait 10, un ordre de grandeur d'ecart. Et le crawler
    # SAVAIT : urls_decouvertes valait 289 pour un plafond de 200. Quand la
    # couverture est incomplete, les compteurs qui dependent du graphe de liens
    # COMPLET ne s'ecrivent donc plus du tout -- un refus motive les remplace, qui
    # dit quoi relancer. On ne peut pas citer un nombre qui n'existe pas.
    couverture_complete = not non_visitees
    refus: dict[str, str] = {}
    if not couverture_complete:
        relance = (
            f"relancer avec --max ≥ {len(connus)} (ou --jusqu-a-epuisement)"
            if not jusqu_a_epuisement else
            f"borne dure de {borne_dure} pages atteinte sans vider la file : "
            "relancer avec --borne-dure supérieure, après avoir vérifié que le site "
            "n'engendre pas d'URL à l'infini (pagination, paramètres combinatoires)"
        )
        motif = (
            f"plafond atteint : {len(vues)} page(s) crawlée(s) sur {len(connus)} URL "
            f"connues (plafond effectif {plafond_effectif}). Ce compteur exige le "
            f"graphe de liens COMPLET — {relance}."
        )
        refus = {
            "pages_orphelines": motif,
            "pages_orphelines_exemples": motif,
            "pages_sans_lien_contextuel": motif,
        }
    titres: dict[str, int] = {}
    for p in pages:
        if p["title"]:
            titres[p["title"]] = titres.get(p["title"], 0) + 1

    # Distribution des @type JSON-LD (noeud 32) : compte les entites d'un
    # `@graph` individuellement -- motif courant des plugins SEO qui regroupent
    # plusieurs entites (Organization, WebSite, BreadcrumbList...) dans un seul
    # script. Un @type absent ou mal forme est ignore, pas compte comme erreur :
    # json_ld_erreurs porte deja les blocs illisibles.
    types_json_ld: dict[str, int] = {}
    for p in pages:
        for bloc in p["json_ld"]:
            entites = bloc.get("@graph") if isinstance(bloc, dict) else None
            entites = entites if isinstance(entites, list) else [bloc]
            for entite in entites:
                if not isinstance(entite, dict):
                    continue
                t = entite.get("@type")
                for nom in (t if isinstance(t, list) else [t] if t else []):
                    types_json_ld[str(nom)] = types_json_ld.get(str(nom), 0) + 1

    return {
        "collecte": {
            "outil": "forge-seo/crawler.py",
            "date": dt.date.today().isoformat(),
            "racine": depart,
            "plafond": plafond,
            "plafond_effectif": plafond_effectif,
            "jusqu_a_epuisement": jusqu_a_epuisement,
            "borne_dure": borne_dure if jusqu_a_epuisement else None,
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
                "Compte exact : toutes les URL connues ont été crawlées."
                if couverture_complete else
                "Compteurs de graphe NON MESURÉS — voir mesures_refusees. Les liens "
                "sortants des pages non crawlées ne sont pas connus : aucune valeur "
                "n'est avancée, pas même un majorant."),
        },
        "synthese": {
            "pages_crawlees": len(pages),
            "urls_decouvertes": len(connus),
            "urls_declarees_sitemap": len(declarees),
            "urls_declarees_non_crawlees": len([u for u in declarees if u not in vues]),
            "profondeur_max": max((p["profondeur_clic"] or 0 for p in pages), default=0),
            "erreurs_4xx_5xx": sum(1 for p in pages if p["code_http"] >= 400),
            "non_indexables": sum(1 for p in pages if p["indexable"] is False),
            "pages_orphelines": None if refus else len(orphelines),
            "pages_orphelines_exemples": None if refus else orphelines[:10],
            # Renomme (TF-0261) : « orphelines_compte_exact » qualifiait un compte
            # qui n'existe plus quand il est faux. Le drapeau porte desormais ce
            # qu'il dit vraiment -- la file a-t-elle ete videe.
            "couverture_complete": couverture_complete,
            "pages_sans_lien_contextuel": None if refus else sum(
                1 for p in pages if p["liens_internes_entrants"] == 0),
            "titles_dupliques": sum(n for n in titres.values() if n > 1) -
                                sum(1 for n in titres.values() if n > 1),
            "pages_fines_sous_300_mots": sum(1 for p in pages if 0 < p["_mots"] < 300),
            # TF-0262 -- le compte de canoniques est produit ICI, par le detecteur
            # indifferent a l'ordre des attributs, et non plus reconstitue a la main
            # au moment de rediger : c'est la reconstitution qui avait rendu « aucune
            # canonique sur 79 pages » sur un site qui en portait partout.
            "pages_200_avec_canonical": sum(
                1 for p in pages if p["code_http"] == 200 and p["canonical"]),
            "pages_200_sans_canonical": sum(
                1 for p in pages if p["code_http"] == 200 and not p["canonical"]),
            "pages_avec_hreflang": sum(1 for p in pages if p["hreflang"]),
            "pages_avec_og": sum(1 for p in pages if p["og"]),
            "pages_avec_json_ld": sum(1 for p in pages if p["json_ld"]),
            "pages_json_ld_en_erreur": sum(1 for p in pages if p["json_ld_erreurs"]),
            "types_json_ld": dict(
                sorted(types_json_ld.items(), key=lambda kv: (-kv[1], kv[0]))),
            # Les compteurs ci-dessus autres que ceux du graphe restent EXACTS, mais
            # sur l'echantillon crawle et non sur le site : leur denominateur est dit
            # ici pour qu'aucune proportion ne se calcule sur le mauvais total (le
            # rapport du 15/08 annoncait « 39 % de pages minces » sur 27 % du site).
            "base_des_proportions": (
                f"{len(pages)} page(s) crawlée(s) — couverture complète, "
                "toute proportion porte sur le site entier."
                if couverture_complete else
                f"{len(pages)} page(s) crawlée(s) sur {len(connus)} URL connues : "
                "toute proportion calculée sur ces compteurs porte sur l'échantillon, "
                "PAS sur le site."),
        },
        # Vide quand la couverture est complete. Non vide, il nomme chaque compteur
        # non ecrit et dit comment l'obtenir : un refus motive, pas un blanc.
        "mesures_refusees": refus,
        "pages": pages,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Crawl du site audité — étape 1 du pipeline.")
    p.add_argument("--projet", required=True, help="chemin du projet audité")
    p.add_argument("--url", required=True, help="URL racine du site")
    p.add_argument("--max", type=int, default=PLAFOND, help=f"plafond de pages ({PLAFOND})")
    p.add_argument("--delai", type=float, default=DELAI, help=f"délai entre requêtes ({DELAI}s)")
    p.add_argument(
        "--jusqu-a-epuisement", action="store_true",
        help="ignore --max et crawle jusqu'à ce que la file soit vide, sous la borne "
             f"dure de --borne-dure ({BORNE_DURE}) — seule façon d'obtenir les "
             "compteurs de graphe (orphelines) sur un site plus grand que le plafond",
    )
    p.add_argument(
        "--borne-dure", type=int, default=BORNE_DURE,
        help=f"borne dure de --jusqu-a-epuisement ({BORNE_DURE} pages) ; atteinte, "
             "elle laisse le crawl en couverture incomplète, donc en refus motivé",
    )
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

    print(f"crawl de {args.url} — "
          + (f"jusqu'à épuisement (borne dure {args.borne_dure} pages)"
             if args.jusqu_a_epuisement else f"plafond {args.max} pages")
          + f", délai {args.delai}s"
          + (", rendu JS actif (Playwright)" if args.rendu_js else ""))
    debut = time.time()
    res = crawler(args.url, args.max, args.delai, rendu_js=args.rendu_js,
                  jusqu_a_epuisement=args.jusqu_a_epuisement,
                  borne_dure=args.borne_dure)
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
    print(f"  pages crawlées      : {s['pages_crawlees']} / "
          f"{res['collecte']['plafond_effectif']}")
    print(f"  URLs découvertes    : {s['urls_decouvertes']}")
    print(f"  déclarées au sitemap: {s['urls_declarees_sitemap']} "
          f"({len(res['collecte']['sitemaps_lus'])} fichier(s) lu(s))")
    print(f"  profondeur max      : {s['profondeur_max']} clics")
    print(f"  erreurs 4xx/5xx     : {s['erreurs_4xx_5xx']}")
    print(f"  non indexables      : {s['non_indexables']}")
    if res["mesures_refusees"]:
        # TF-0261 : pas de nombre, pas de « majorant » — le refus et sa relance.
        print("  pages orphelines    : NON MESURÉ")
        print("  pages sans lien ctx : NON MESURÉ")
        print(f"    motif : {res['mesures_refusees']['pages_orphelines']}")
    else:
        print(f"  pages orphelines    : {s['pages_orphelines']}")
    print(f"  titles dupliqués    : {s['titles_dupliques']}")
    print(f"  canonical (HTTP 200): {s['pages_200_avec_canonical']} avec · "
          f"{s['pages_200_sans_canonical']} sans"
          + (f" · hreflang sur {s['pages_avec_hreflang']}" if s["pages_avec_hreflang"] else "")
          + (f" · Open Graph sur {s['pages_avec_og']}" if s["pages_avec_og"] else ""))
    print(f"  pages < 300 mots    : {s['pages_fines_sous_300_mots']}")
    print(f"  pages avec JSON-LD  : {s['pages_avec_json_ld']}"
          + (f" — types : {', '.join(f'{t} ({n})' for t, n in s['types_json_ld'].items())}"
             if s['types_json_ld'] else ""))
    if s["pages_json_ld_en_erreur"]:
        print(f"  JSON-LD illisible   : {s['pages_json_ld_en_erreur']} page(s) — "
              "voir json_ld_erreurs dans le fichier de crawl")
    if not res["collecte"]["robots_txt_lu"]:
        print("  ATTENTION robots.txt illisible — crawl mené sans ses directives")
    if res["collecte"]["urls_bloquees_par_robots"]:
        print(f"  {res['collecte']['urls_bloquees_par_robots']} URL(s) écartée(s) par robots.txt")
    print("\nÉtape suivante : python scripts/livrables.py --projet <chemin>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
