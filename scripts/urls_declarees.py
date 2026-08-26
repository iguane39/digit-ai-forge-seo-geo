"""Toute URL que le site DECLARE de lui-meme doit repondre 200, SANS redirection.

============================================================================================
POURQUOI (TF-0658, lot Produit-02 20260826c, 26/08/2026)
============================================================================================

LE FAIT, MESURE EN PRODUCTION. La page servie en `/gites` declarait
`<link rel="canonical" href=".../gites.html">` — et `/gites.html` repond 301 vers `/gites`.
*La canonique designait une URL qui redirige vers la page elle-meme.*

AMPLEUR : 203 canoniques sur 203, 203 `<loc>` de sitemap sur 203, 1 624 alternates hreflang, 15
liens de `llms.txt`. Les sept pages d'accueil portaient une CHAINE DE DEUX redirections.

TROIS ORACLES AU VERT, UN DEFAUT SITE-ENTIER. Le controle SEO verifiait que la balise canonique
EXISTE, jamais ou elle mene. Le controle de liens verifiait que les cibles existent SUR LE DISQUE —
et sur le disque `gites.html` existe : c'est le SERVEUR qui redirige, en URL propres. Le controle de
redirections testait les ANCIENNES URL du site precedent, jamais les nouvelles. Chacun disait vrai
sur son objet, et l'objet qui comptait n'appartenait a aucun d'eux.

CLASSE GENERIQUE, et c'est ce qui justifie un oracle plutot qu'un correctif de projet : *tout site
statique servi en URL propres pendant que le generateur emet des `.html` porte le meme defaut.*

============================================================================================
CE QUI EST JUGE, ET CE QUI NE PEUT PAS L'ETRE
============================================================================================

  U1  toute CANONIQUE declaree par une page repond 200 sans redirection ;
  U2  tout ALTERNATE hreflang declare repond 200 sans redirection ;
  U3  toute URL declaree au SITEMAP repond 200 sans redirection.

CET ORACLE N'APPELLE RIEN. Il travaille sur l'artefact de crawl deja produit, qui porte pour chaque
page son `code_http` et sa `_redirections`. C'est deliberé : un oracle qui refait des requetes
echoue quand le reseau tombe, et son echec d'environnement devient indiscernable d'un defaut — la
classe exacte de TF-0648, ouverte le meme jour par le meme produit.

LA BORNE : une URL declaree qui n'a PAS ete crawlee n'est pas jugee, elle est NOMMEE. Un crawl
plafonne ne voit pas tout, et conclure d'une absence de mesure serait affirmer ce que la donnee ne
porte pas.

Usage : python scripts/urls_declarees.py <crawl.json>   → verdict JSON
        python scripts/urls_declarees.py --self-test    → fixtures double sens

Contrat : JSON {oracle, verdict, findings[], non_juge[]} · exit 0 PASS / 1 FAIL / 2 erreur.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

NON_JUGE = [
    "une URL declaree que le crawl n a PAS visitee n est pas jugee : elle est nommee. Un crawl "
    "plafonne ne voit pas tout, et conclure d une absence de mesure serait affirmer ce que la "
    "donnee ne porte pas",
    "les liens de llms.txt ne sont pas juges ici : ils ne figurent pas dans l artefact de crawl. "
    "C est le noeud des directives IA qui lit ce fichier, et il exige desormais que son contenu "
    "soit LU (TF-0636)",
    "cet oracle ne REFAIT aucune requete : il lit ce que le crawl a mesure. Une redirection posee "
    "APRES le crawl n est donc pas vue — le remede est de recrawler, pas d appeler ici",
    "la JUSTESSE d une canonique n est pas jugee : qu elle designe la bonne page demande de "
    "comprendre le contenu. Ce qui est juge, c est qu elle ne designe pas une URL qui redirige",
]


def _chemin(url: str) -> str:
    """Le chemin d'une URL, absolue ou relative — c'est la cle que le crawl emploie."""
    return urllib.parse.urlsplit(url).path or "/"


def juger(crawl: dict) -> list[dict]:
    findings: list[dict] = []

    def ok(regle: str, message: str) -> None:
        findings.append({"regle": regle, "statut": "PASS", "message": message})

    def ko(regle: str, message: str, ou: str = "") -> None:
        f = {"regle": regle, "statut": "FAIL", "message": message}
        if ou:
            f["ou"] = ou
        findings.append(f)

    pages = crawl.get("pages") or []
    if not pages:
        return [{"regle": "U0", "statut": "SANS_OBJET",
                 "message": "aucune page dans l artefact de crawl — rien a confronter"}]

    par_chemin = {_chemin(p.get("url") or ""): p for p in pages}
    non_vues: set[str] = set()

    def etat(cible: str) -> tuple[str, str]:
        """(verdict, motif) pour une URL declaree : `ok`, `redirige`, `erreur` ou `non_vue`."""
        c = _chemin(cible)
        p = par_chemin.get(c)
        if p is None:
            non_vues.add(c)
            return "non_vue", ""
        chaine = p.get("_redirections") or []
        if chaine:
            return "redirige", " → ".join(str(x) for x in chaine[:3])
        code = p.get("code_http")
        if code != 200:
            return "erreur", f"HTTP {code}"
        return "ok", ""

    # ---- U1 : les canoniques -------------------------------------------------------------
    declarants = [p for p in pages if p.get("canonical")]
    ecarts = []
    for p in declarants:
        verdict, motif = etat(p["canonical"])
        if verdict in ("redirige", "erreur"):
            ecarts.append(f"{p.get('url')} → canonique `{p['canonical']}` {verdict} ({motif})")
    if not declarants:
        findings.append({"regle": "U1", "statut": "SANS_OBJET", "message": "aucune canonique declaree"})
    elif ecarts:
        ko("U1", f"{len(ecarts)} canonique(s) sur {len(declarants)} designent une URL qui NE REPOND PAS 200 "
                 "directement — une canonique qui redirige n a pas d arbitrage possible : le moteur recoit "
                 "deux affirmations contradictoires sur la meme page. Mesure fondatrice : 203 sur 203",
           " · ".join(ecarts[:4]))
    else:
        ok("U1", f"{len(declarants)} canonique(s), toutes en 200 direct")

    # ---- U2 : les alternates hreflang ----------------------------------------------------
    total_alt, ecarts_alt = 0, []
    for p in pages:
        for alt in p.get("hreflang") or []:
            href = alt.get("href") or alt.get("url")
            if not href:
                continue
            total_alt += 1
            verdict, motif = etat(href)
            if verdict in ("redirige", "erreur"):
                ecarts_alt.append(f"{p.get('url')} → alternate `{alt.get('hreflang')}` {href} {verdict} ({motif})")
    if not total_alt:
        findings.append({"regle": "U2", "statut": "SANS_OBJET", "message": "aucun alternate hreflang declare"})
    elif ecarts_alt:
        ko("U2", f"{len(ecarts_alt)} alternate(s) sur {total_alt} designent une URL qui redirige ou echoue — "
                 "un cluster hreflang dont un membre redirige n est plus garanti valide cote moteur",
           " · ".join(ecarts_alt[:4]))
    else:
        ok("U2", f"{total_alt} alternate(s) hreflang, tous en 200 direct")

    # ---- U3 : les URL declarees au sitemap -----------------------------------------------
    au_sitemap = [p for p in pages if p.get("declaree_sitemap")]
    ecarts_sm = []
    for p in au_sitemap:
        chaine = p.get("_redirections") or []
        if chaine:
            ecarts_sm.append(f"{p.get('url')} ({' → '.join(str(x) for x in chaine[:2])})")
        elif p.get("code_http") != 200:
            ecarts_sm.append(f"{p.get('url')} (HTTP {p.get('code_http')})")
    if not au_sitemap:
        findings.append({"regle": "U3", "statut": "SANS_OBJET", "message": "aucune URL declaree au sitemap"})
    elif ecarts_sm:
        ko("U3", f"{len(ecarts_sm)} URL(s) du sitemap sur {len(au_sitemap)} redirigent ou echouent — "
                 "un sitemap qui declare des URL redirigees demande au moteur de decouvrir des adresses "
                 "que le site ne sert pas",
           " · ".join(ecarts_sm[:4]))
    else:
        ok("U3", f"{len(au_sitemap)} URL(s) de sitemap, toutes en 200 direct")

    if non_vues:
        findings.append({"regle": "U0", "statut": "SANS_OBJET",
                         "message": f"{len(non_vues)} URL declaree(s) NON VISITEE(s) par le crawl, donc non jugees : "
                                    + ", ".join(sorted(non_vues)[:6])})
    return findings


def verdict_de(findings: list[dict]) -> str:
    if any(f["statut"] == "FAIL" for f in findings):
        return "FAIL"
    return "PASS" if any(f["statut"] == "PASS" for f in findings) else "SANS_OBJET"


def _page(url: str, **kw) -> dict:
    base = {"url": url, "code_http": 200, "canonical": None, "hreflang": [],
            "declaree_sitemap": False, "_redirections": []}
    base.update(kw)
    return base


def _self_test() -> int:
    casse: list[str] = []

    def att(cond, message):
        if not cond:
            casse.append(message)

    # ROUGE — le cas fondateur, mot pour mot : la page servie en `/gites` declare `/gites.html`,
    # et `/gites.html` repond 301 vers `/gites`.
    rouge = {"pages": [
        _page("/gites", canonical="/gites.html", declaree_sitemap=True,
              hreflang=[{"hreflang": "en", "href": "/en/cottages.html"}]),
        _page("/gites.html", _redirections=["301 → /gites"]),
        _page("/en/cottages.html", _redirections=["301 → /en/cottages"]),
    ]}
    f = juger(rouge)
    att(verdict_de(f) == "FAIL", "la fixture ROUGE ne FAIL pas")
    for regle in ("U1", "U2"):
        att(any(x["regle"] == regle and x["statut"] == "FAIL" for x in f),
            f"la rouge echoue mais pas sur {regle}")
    u1 = next((x for x in f if x["regle"] == "U1"), {})
    att("gites.html" in (u1.get("ou") or ""), "la canonique fautive n est pas NOMMEE")

    # VERTE — les memes declarations, mais vers des URL servies directement. Sans ce cas, une
    # regle qui crierait sur toute canonique passerait le cas rouge.
    verte = {"pages": [
        _page("/gites", canonical="/gites", declaree_sitemap=True,
              hreflang=[{"hreflang": "en", "href": "/en/cottages"}]),
        _page("/en/cottages"),
    ]}
    f = juger(verte)
    att(verdict_de(f) == "PASS", f"la fixture VERTE ne passe pas : {f}")

    # BORNE — une declaration vers une URL que le crawl n a PAS visitee n est pas jugee, elle est
    # NOMMEE. Conclure d une absence de mesure serait affirmer ce que la donnee ne porte pas.
    borne = {"pages": [_page("/a", canonical="/jamais-crawlee")]}
    f = juger(borne)
    att(verdict_de(f) != "FAIL", "une URL non visitee est comptee comme un defaut")
    att(any(x["regle"] == "U0" and "NON VISITEE" in x["message"] for x in f),
        "les URL non visitees ne sont pas nommees")

    # BORNE — un crawl vide ne rend pas un vert : il rend SANS_OBJET.
    att(verdict_de(juger({"pages": []})) == "SANS_OBJET", "un crawl vide passe pour conforme")

    print("SELF-TEST urls_declarees : " + ("FAIL — " + " · ".join(casse) if casse
          else "5/5 PASS (rouge FAIL sur U1 et U2 avec l URL nommee, verte PASS, "
               "URL non visitee NON JUGEE et nommee, crawl vide SANS_OBJET)"))
    return 1 if casse else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    if len(sys.argv) < 2:
        print(json.dumps({"oracle": "urls-declarees", "verdict": "ERREUR",
                          "message": "usage : urls_declarees.py <crawl.json> | --self-test"}, ensure_ascii=False))
        return 2
    chemin = Path(sys.argv[1])
    if not chemin.exists():
        print(json.dumps({"oracle": "urls-declarees", "verdict": "ERREUR",
                          "message": f"artefact de crawl introuvable : {chemin}"}, ensure_ascii=False))
        return 2
    crawl = json.loads(chemin.read_text(encoding="utf-8"))
    findings = juger(crawl)
    verdict = verdict_de(findings)
    print(json.dumps({"oracle": "urls-declarees", "version": "1.0.0", "cible": str(chemin),
                      "verdict": verdict, "findings": findings, "non_juge": NON_JUGE},
                     ensure_ascii=False, indent=1))
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
