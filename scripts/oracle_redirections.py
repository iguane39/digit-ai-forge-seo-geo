"""Oracle des redirections : le chemin demande arrive-t-il a destination ? (TF-1997, noeud 28)

LE FAIT. Le 25/08/2026, le pilot a mesure qu'une Page Rule de Cloudflare preserve le
chemin quand son URL cible porte `$1` : un lien profond atterrit sur la meme page et non
sur l'accueil, ce qui change tout pour le referencement. La meme reference s'ecrit
`${1}` dans une Single Redirect (guide de migration des Page Rules, lu le 29/10/2026)
et `:splat` dans un fichier `_redirects`. Recopiee d'un vehicule a l'autre, elle n'est
pas substituee : l'en-tete Location porte `$1` en toutes lettres et chaque lien profond
aboutit sur une URL cassee. Rien dans la forge ne le voyait : le noeud 28 releve les
chaines de redirection du site crawle, pas les domaines ni les chemins qui redirigent
vers lui.

CE QUE L'ORACLE JUGE, par deux voies complementaires :
  1. les REGLES declarees : fichier `_redirects`, ou export JSON de l'API Cloudflare
     (Page Rules, Single Redirects, Bulk Redirects), vehicule reconnu au contenu ;
  2. la SONDE d'une URL en ligne : un chemin temoin unique est demande sans suivre la
     redirection, et l'en-tete Location doit le porter. La sonde juge l'effet, quel que
     soit le vehicule (Snippet ou code de Worker compris).
La syntaxe de chaque vehicule (motif et gabarit des references, cible litterale, code
et parametres par defaut) est une DONNEE de `referentiel/cloudflare.json`, datee et
sourcee : rien n'est code en dur ici, un changement chez Cloudflare se corrige dans le
referentiel.

CONSTATS. Bloquants : jeton-litteral (reference d'un autre vehicule, jamais substituee
ici), chemin-perdu (la source couvre plusieurs chemins, la cible n'en reprend aucun),
reference-hors-joker (reference a un joker que le motif ne porte pas),
motif-jamais-apparie (motif de chemin applique a l'URL complete). Avertissements :
forme-non-documentee (forme plausible que les pages lues ne decrivent pas : la sonde
tranche), code-non-permanent (302 ou 307, dont le 302 implicite de `_redirects`),
ligne-ignoree, sans-redirection. Un chemin perdu peut etre une decision, comme un
ancien site entier renvoye sur l'accueil : `--assume <id>` la consigne, le constat reste
affiche et cesse de bloquer. Rien d'autre ne s'assume.

Usage :
    python scripts/oracle_redirections.py --regles public/_redirects
    python scripts/oracle_redirections.py --regles export-pagerules.json [--vehicule page-rules]
    python scripts/oracle_redirections.py --sonder https://ancien-domaine.fr [--sonder ...]
    python scripts/oracle_redirections.py ... --assume page-rules:<id> --projet . --json

Sortie : 0 PASS, 1 FAIL (au moins un bloquant non assume), 2 rien de juge ou usage.
Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from crawler import AGENT, TIMEOUT
from grille import RACINE

REFERENTIEL = RACINE / "referentiel" / "cloudflare.json"

# Noeud que cet oracle instrumente (chaines de redirection du noeud Crawl).
NOEUDS = [28]

BLOQUANT = "bloquant"
AVERTISSEMENT = "avertissement"

# Seul un chemin perdu peut etre une decision du proprietaire : un jeton litteral ou une
# reference sans joker ne servent aucune intention.
ASSUMABLES = {"chemin-perdu"}

CODES_REDIRECTION = {301, 302, 303, 307, 308}

RE_NOM = re.compile(r":([A-Za-z]\w*)")
RE_CHAMP_CHEMIN = re.compile(r"http\.request\.(?:uri\.path|uri\b|full_uri)")

NON_JUGE = [
    "la sonde demande un seul chemin témoin par URL : une règle qui ne couvre qu'une partie des "
    "chemins n'est jugée que sur celui-là",
    "l'expression source d'une Single Redirect est lue par motifs (wildcard, starts_with, "
    "ends_with, contains, matches, eq, in) : une condition plus fine n'est pas jugée, et une "
    "expression indéterminée ne produit aucun chemin perdu",
    "Snippets et code d'un Worker ne sont pas lus comme règles : seule la sonde en juge l'effet",
    "la chaîne complète (sauts suivants, boucles) relève de crawler.py, nœud 28",
    "la chaîne de requête (preserve_query_string) n'est pas jugée",
    "les syntaxes viennent de referentiel/cloudflare.json, daté : une page Cloudflare plus récente "
    "peut les contredire",
]


# --- referentiel ---------------------------------------------------------------------
def charger_referentiel(chemin: Path = REFERENTIEL) -> dict:
    if not chemin.exists():
        raise SystemExit(f"REFUS : {chemin} absent -- referentiel des vehicules de redirection "
                         "introuvable. Le maintenir en donnee, pas en dur dans ce script.")
    return json.loads(chemin.read_text(encoding="utf-8"))


def _vehicule(ref: dict, ident: str) -> dict:
    for v in ref["vehicules_redirection"]:
        if v["id"] == ident:
            return v
    raise SystemExit(f"REFUS : vehicule « {ident} » absent de referentiel/cloudflare.json")


def _codes_permanents(ref: dict) -> set[int]:
    return set(ref["codes_permanents"]["valeurs"])


def _motifs(v: dict, porte: str | None = None, sonde: bool | None = None) -> list[re.Pattern]:
    return [re.compile(r["motif"]) for r in v["references"]
            if (porte is None or r["porte"] == porte) and (sonde is None or r["sonde"] is sonde)]


def _gabarit_joker(v: dict) -> str | None:
    return next((r.get("gabarit") for r in v["references"] if r["porte"] == "joker"), None)


def _ecrire(gabarit: str, rang: int) -> str:
    return gabarit % rang if "%d" in gabarit else gabarit


# --- constats ------------------------------------------------------------------------
def _constat(genre: str, gravite: str, message: str, remede: str | None = None, **extra) -> dict:
    c = {"genre": genre, "gravite": gravite, "message": message}
    if remede:
        c["remede"] = remede
    c.update({k: v for k, v in extra.items() if v is not None})
    return c


def _regle(ident: str, vehicule: str, source, cible, code, constats: list[dict]) -> dict:
    return {"id": ident, "vehicule": vehicule, "source": source, "cible": cible, "code": code,
            "constats": constats}


def _juger_code(code: int | None, v: dict, ref: dict) -> list[dict]:
    effectif = code if code is not None else v.get("code_par_defaut")
    if effectif is None or effectif == 200 or effectif in _codes_permanents(ref):
        return []
    implicite = " (code absent : défaut du véhicule)" if code is None else ""
    return [_constat("code-non-permanent", AVERTISSEMENT,
                     f"redirection {effectif}{implicite} : un moteur garde l'URL d'origine en index",
                     "écrire 301 ou 308 si le déplacement est définitif")]


def _jetons_etrangers(cible: str, v: dict, ref: dict) -> list[dict]:
    """References des AUTRES vehicules presentes dans une cible : ce vehicule ne les substitue pas.

    `ambigu` : le dollar a un sens dans ce vehicule (il s'y echappe), la forme d'un autre
    vehicule y est donc plausible mais non decrite par les pages lues -- avertissement, la
    sonde tranche. Sinon le jeton arrive tel quel dans Location : bloquant.
    """
    trouves: dict[str, dict] = {}
    for autre in ref["vehicules_redirection"]:
        if autre["id"] == v["id"]:
            continue
        for motif in _motifs(autre, sonde=True):
            for m in motif.finditer(cible):
                ambigu = "$" in m.group(0) and bool(v.get("echappement_dollar")) and not v["cible_litterale"]
                trouves.setdefault(m.group(0), {"jeton": m.group(0), "vehicule": autre["id"],
                                                "nom": autre["nom"], "ambigu": ambigu})
    return list(trouves.values())


# --- jokers et references ------------------------------------------------------------
def jokers(motif: str, echappement: bool = False) -> list[dict]:
    """Rang (1..n, de gauche a droite) et partie couverte (schema, hote, chemin) de chaque `*`.

    Un motif qui commence par `/` est un chemin ; sinon l'hote va du debut (ou de `://`)
    au premier `/`. Un joker final sans `/` apres l'hote peut absorber le chemin : il
    compte comme joker de chemin. `echappement` : `\\*` est un asterisque litteral
    (wildcard_replace), il n'est pas compte.
    """
    if motif.startswith("/"):
        fin_schema, debut_chemin = -1, 0
    else:
        i = motif.find("://")
        fin_schema = i
        j = motif.find("/", i + 3 if i >= 0 else 0)
        debut_chemin = j if j >= 0 else len(motif)
    res, rang, k = [], 0, 0
    while k < len(motif):
        c = motif[k]
        if echappement and c == "\\":
            k += 2
            continue
        if c == "*":
            rang += 1
            if 0 <= k < fin_schema:
                partie = "schema"
            elif k >= debut_chemin or (k == len(motif) - 1 and debut_chemin == len(motif)):
                partie = "chemin"
            else:
                partie = "hote"
            res.append({"rang": rang, "partie": partie})
        k += 1
    return res


def _references(cible: str, v: dict) -> list[int]:
    """Rangs de joker cites par la cible, dans la forme documentee du vehicule, dans l'ordre."""
    trouves = []
    for motif in _motifs(v, porte="joker"):
        trouves += [(m.start(), int(m.group(1))) for m in motif.finditer(cible)
                    if m.groups() and m.group(1) and m.group(1).isdigit()]
    return [rang for _, rang in sorted(trouves)]


def _cible_suggeree(cible: str, v: dict, cites: list[int], rang_chemin: int) -> str | None:
    """La cible corrigee : la derniere reference d'hote ou de schema devient celle du chemin,
    ou la reference du chemin s'ajoute en fin de cible."""
    gabarit = _gabarit_joker(v)
    if not gabarit:
        return None
    nouvelle = _ecrire(gabarit, rang_chemin)
    if cites:
        ancienne = _ecrire(gabarit, cites[-1])
        i = cible.rfind(ancienne)
        if i >= 0:
            return cible[:i] + nouvelle + cible[i + len(ancienne):]
    return cible + nouvelle if cible.endswith("/") else f"{cible}/{nouvelle}"


def _juger_motif(v: dict, motif: str, cible: str, code: int | None, ref: dict,
                 echappement_joker: bool = False) -> list[dict]:
    """Page Rule ou wildcard_replace : le joker du chemin est-il repris par la cible ?"""
    constats: list[dict] = []
    js = jokers(motif, echappement_joker)
    rangs_chemin = [j["rang"] for j in js if j["partie"] == "chemin"]
    nette = cible.replace(v["echappement_dollar"], "") if v.get("echappement_dollar") else cible
    cites = _references(nette, v)
    gabarit = _gabarit_joker(v) or "%d"
    etrangers = _jetons_etrangers(nette, v, ref)
    for e in etrangers:
        if e["ambigu"]:
            constats.append(_constat(
                "forme-non-documentee", AVERTISSEMENT,
                f"« {e['jeton']} » est la forme de {e['nom']} ; les pages lues ne la "
                f"décrivent pas pour {v['nom']}, dont la forme attestée est {_ecrire(gabarit, 1)}",
                "écrire la forme attestée, ou jouer --sonder sur une URL de la règle pour trancher"))
        else:
            remplacement = _ecrire(gabarit, rangs_chemin[0]) if rangs_chemin else None
            constats.append(_constat(
                "jeton-litteral", BLOQUANT,
                f"« {e['jeton']} » est la forme de référence de {e['nom']} : {v['nom']} ne la "
                "substitue pas, elle arrive telle quelle dans Location et le chemin est perdu",
                f"écrire la référence de ce véhicule : {v['forme_reference']}",
                cible_suggeree=cible.replace(e["jeton"], remplacement) if remplacement else None))
    hors = sorted({r for r in cites if r > len(js)})
    if hors:
        constats.append(_constat(
            "reference-hors-joker", BLOQUANT,
            f"la cible cite {', '.join(_ecrire(gabarit, r) for r in hors)} alors que le motif ne "
            f"porte que {len(js)} joker(s)",
            f"référence la plus haute admise : {_ecrire(gabarit, len(js))}" if js
            else "retirer la référence, ou ajouter un joker au motif"))
    litteral = any(c["genre"] == "jeton-litteral" for c in constats)
    ambigu = any(e["ambigu"] for e in etrangers)
    valides = [r for r in cites if r <= len(js)]
    if rangs_chemin and not set(valides) & set(rangs_chemin) and not litteral and not ambigu:
        constats.append(_constat(
            "chemin-perdu", BLOQUANT,
            f"le motif couvre plusieurs chemins (joker n° {rangs_chemin[0]} dans le chemin) et la "
            f"cible n'en reprend aucun : tous les liens profonds aboutissent sur {cible}",
            "reprendre le joker du chemin dans la cible, ou consigner la décision par --assume",
            cible_suggeree=_cible_suggeree(cible, v, valides, rangs_chemin[0])))
    return constats + _juger_code(code, v, ref)


# --- fichier _redirects --------------------------------------------------------------
def analyser_fichier_redirects(texte: str, ref: dict, nom: str = "_redirects") -> list[dict]:
    v = _vehicule(ref, "fichier-redirects")
    admis = set(v["codes_admis"]) | {200}
    regles = []
    for no, brute in enumerate(texte.splitlines(), 1):
        ligne = brute.strip()
        if not ligne or ligne.startswith("#"):
            continue
        ident = f"{nom}:{no}"
        morceaux = ligne.split()
        code = int(morceaux[2]) if len(morceaux) == 3 and morceaux[2].isdigit() else None
        if len(morceaux) not in (2, 3) or (len(morceaux) == 3 and code not in admis):
            regles.append(_regle(ident, v["id"], ligne, None, code, [_constat(
                "ligne-ignoree", AVERTISSEMENT,
                "ligne hors du format « source destination [code] », ou code non pris en charge : "
                "Cloudflare l'ignore",
                "une redirection par ligne, code parmi " + ", ".join(map(str, v["codes_admis"])))]))
            continue
        source, destination = morceaux[0], morceaux[1]
        regles.append(_regle(ident, v["id"], source, destination, code,
                             _juger_fichier(source, destination, code, v, ref)))
    return regles


def _juger_fichier(source: str, destination: str, code: int | None, v: dict, ref: dict) -> list[dict]:
    constats: list[dict] = []
    nb_jokers = source.count("*")
    noms_source = list(dict.fromkeys(RE_NOM.findall(source)))
    noms_dest = {n for n in RE_NOM.findall(destination) if n != "splat"}
    a_splat = ":splat" in destination
    etrangers = _jetons_etrangers(destination, v, ref)
    if nb_jokers > 1:
        constats.append(_constat("ligne-ignoree", AVERTISSEMENT,
                                 f"{nb_jokers} jokers : la page n'en admet qu'un par URL", "garder un seul *"))
    for e in etrangers:
        constats.append(_constat(
            "jeton-litteral", BLOQUANT,
            f"« {e['jeton']} » est la forme de référence de {e['nom']} : _redirects ne la substitue "
            "pas, elle arrive telle quelle dans Location et le chemin est perdu",
            "dans _redirects, le joker se reprend par :splat et un paramètre par :nom",
            cible_suggeree=destination.replace(e["jeton"], ":splat") if nb_jokers else None))
    if a_splat and not nb_jokers:
        constats.append(_constat("reference-hors-joker", BLOQUANT,
                                 ":splat dans la destination alors que la source ne porte aucun *",
                                 "ajouter * à la source, ou retirer :splat"))
    orphelins = sorted(noms_dest - set(noms_source))
    if orphelins:
        constats.append(_constat(
            "reference-hors-joker", AVERTISSEMENT,
            f"{', '.join(':' + n for n in orphelins)} : aucun paramètre de ce nom dans la source, "
            "texte littéral ou paramètre mal nommé",
            "nommer le paramètre dans la source, ou laisser ce texte s'il est voulu"))
    porte = (nb_jokers and a_splat) or bool(set(noms_source) & noms_dest)
    if (nb_jokers or noms_source) and not porte and not etrangers:
        ajout = ":splat" if nb_jokers else f":{noms_source[0]}"
        constats.append(_constat(
            "chemin-perdu", BLOQUANT,
            f"la source {source} couvre plusieurs chemins et la destination n'en reprend aucun : "
            f"tous aboutissent sur {destination}",
            "reprendre :splat ou le paramètre dans la destination, ou consigner la décision par --assume",
            cible_suggeree=destination + ajout if destination.endswith("/") else f"{destination}/{ajout}"))
    return constats + _juger_code(code, v, ref)


# --- Page Rules ----------------------------------------------------------------------
def _liste(donnees) -> list:
    """Accepte la reponse brute de l'API (`{"result": [...]}`) ou la liste seule."""
    if isinstance(donnees, dict) and "result" in donnees:
        donnees = donnees["result"]
    return donnees if isinstance(donnees, list) else []


def analyser_page_rules(donnees, ref: dict) -> list[dict]:
    """Reponse de GET /zones/{zone_id}/pagerules : seules les regles actives a renvoi sont jugees."""
    v = _vehicule(ref, "page-rules")
    regles = []
    for i, pr in enumerate(_liste(donnees), 1):
        if not isinstance(pr, dict) or pr.get("status", "active") != "active":
            continue
        renvoi = next((a for a in pr.get("actions", []) if a.get("id") == "forwarding_url"), None)
        if renvoi is None:
            continue
        motif = next((t.get("constraint", {}).get("value") for t in pr.get("targets", [])
                      if t.get("target", "url") == "url"), None)
        valeur = renvoi.get("value") or {}
        cible, code = valeur.get("url"), valeur.get("status_code")
        ident = f"page-rules:{pr.get('id') or i}"
        if not motif or not cible:
            regles.append(_regle(ident, v["id"], motif, cible, code, [_constat(
                "ligne-ignoree", AVERTISSEMENT, "règle sans motif ou sans URL cible : non jugée")]))
            continue
        regles.append(_regle(ident, v["id"], motif, cible, code, _juger_motif(v, motif, cible, code, ref)))
    return regles


# --- Single Redirects ----------------------------------------------------------------
def _lire_chaine(texte: str, k: int) -> tuple[str | None, int]:
    """Litterale de chaine du langage des regles a la position k : r#"..."#, r"..." ou "..."."""
    if texte.startswith('r#"', k):
        fin = texte.find('"#', k + 3)
        return (texte[k + 3:fin], fin + 2) if fin >= 0 else (None, k)
    if texte.startswith('r"', k):
        fin = texte.find('"', k + 2)
        return (texte[k + 2:fin], fin + 1) if fin >= 0 else (None, k)
    if texte.startswith('"', k):
        j, sortie = k + 1, []
        while j < len(texte):
            c = texte[j]
            if c == "\\" and j + 1 < len(texte):
                sortie.append(texte[j + 1])
                j += 2
                continue
            if c == '"':
                return "".join(sortie), j + 1
            sortie.append(c)
            j += 1
    return None, k


def lire_wildcard_replace(expression: str) -> tuple[str, str, str] | None:
    """(champ, motif, remplacement) d'un appel wildcard_replace(), ou None."""
    i = expression.find("wildcard_replace(")
    if i < 0:
        return None
    k = i + len("wildcard_replace(")
    m = re.match(r"\s*([\w.]+)\s*,\s*", expression[k:])
    if not m:
        return None
    champ, k = m.group(1), k + m.end()
    motif, k = _lire_chaine(expression, k)
    m = re.match(r"\s*,\s*", expression[k:]) if motif is not None else None
    if not m:
        return None
    remplacement, _ = _lire_chaine(expression, k + m.end())
    return (champ, motif, remplacement) if remplacement is not None else None


def couvre_plusieurs_chemins(expression: str) -> bool | None:
    """L'expression source d'une regle correspond-elle a plusieurs chemins ? None : indetermine.

    Aucune condition sur le chemin : tous les chemins de l'hote correspondent. Joker, prefixe,
    suffixe, sous-chaine ou expression reguliere : plusieurs. Egalite ou liste : des pages
    precises.
    """
    if not RE_CHAMP_CHEMIN.search(expression):
        return True
    if (re.search(r'\bwildcard\b\s*r?#?"[^"]*\*', expression)
            or re.search(r"\b(?:starts_with|ends_with)\(\s*http\.request\.(?:uri\.path|uri|full_uri)", expression)
            or re.search(r"\b(?:matches|contains)\b|\s~\s", expression)):
        return True
    if re.search(r"http\.request\.(?:uri\.path|uri|full_uri)\s+(?:eq|==|in)\b", expression):
        return False
    return None


def _juger_sans_motif(v: dict, expression: str, cible: str, code: int | None, ref: dict,
                      reprend_chemin: bool) -> list[dict]:
    """Cible statique, ou expression dynamique hors wildcard_replace."""
    constats = [_constat(
        "jeton-litteral", BLOQUANT,
        f"« {e['jeton']} » est la forme de référence de {e['nom']} : dans {v['nom']}, elle reste "
        "une chaîne littérale et arrive telle quelle dans Location",
        "passer en redirection par motif (wildcard_replace) dont la cible reprend ${n}, "
        "comme le guide de migration des Page Rules")
        for e in _jetons_etrangers(cible, v, ref)]
    if couvre_plusieurs_chemins(expression) and not reprend_chemin and not constats:
        constats.append(_constat(
            "chemin-perdu", BLOQUANT,
            f"l'expression « {expression} » couvre plusieurs chemins et la cible ne reprend aucun champ "
            f"de chemin : tous aboutissent sur {cible}",
            "reprendre http.request.uri.path dans la cible, passer en redirection par motif, ou "
            "consigner la décision par --assume"))
    return constats + _juger_code(code, v, ref)


def _regles_ruleset(donnees) -> list:
    d = donnees.get("result", donnees) if isinstance(donnees, dict) else donnees
    if isinstance(d, dict):
        d = d.get("rules", [])
    return d if isinstance(d, list) else []


def analyser_single_redirects(donnees, ref: dict) -> list[dict]:
    """Ruleset de la phase http_request_dynamic_redirect (reponse de l'API Rulesets, ou ses regles)."""
    statique = _vehicule(ref, "single-redirects-statique")
    dynamique = _vehicule(ref, "single-redirects-dynamique")
    joker = _vehicule(ref, "single-redirects-joker")
    regles = []
    for i, r in enumerate(_regles_ruleset(donnees), 1):
        if not isinstance(r, dict) or r.get("action") != "redirect" or r.get("enabled", True) is False:
            continue
        fv = (r.get("action_parameters") or {}).get("from_value")
        if not fv:  # from_list : regle de Bulk Redirects, jugee par ses listes
            continue
        tu = fv.get("target_url") or {}
        code = fv.get("status_code")
        expression = r.get("expression", "")
        ident = f"single-redirects:{r.get('id') or r.get('ref') or i}"
        if "value" in tu:
            regles.append(_regle(ident, statique["id"], expression, tu["value"], code,
                                 _juger_sans_motif(statique, expression, tu["value"], code, ref, False)))
            continue
        cible_expr = tu.get("expression", "")
        appel = lire_wildcard_replace(cible_expr)
        if appel is None:
            reprend = bool(RE_CHAMP_CHEMIN.search(cible_expr) or "regex_replace(" in cible_expr)
            regles.append(_regle(ident, dynamique["id"], expression, cible_expr, code,
                                 _juger_sans_motif(dynamique, expression, cible_expr, code, ref, reprend)))
            continue
        champ, motif, remplacement = appel
        if champ == "http.request.full_uri" and motif.startswith("/"):
            constats = [_constat(
                "motif-jamais-apparie", BLOQUANT,
                f"le motif « {motif} » ne décrit qu'un chemin, or http.request.full_uri est l'URL complète : "
                "wildcard_replace() ne trouve aucune correspondance et rend l'URL d'origine",
                "écrire le motif complet (https://hôte/chemin/*), ou appliquer la fonction à "
                "http.request.uri.path")] + _juger_code(code, joker, ref)
        else:
            constats = _juger_motif(joker, motif, remplacement, code, ref, echappement_joker=True)
        regles.append(_regle(ident, joker["id"], motif, remplacement, code, constats))
    return regles


# --- Bulk Redirects ------------------------------------------------------------------
def analyser_bulk_redirects(donnees, ref: dict) -> list[dict]:
    """Elements d'une liste de redirections (reponse de l'API Lists, ou objets `redirect`)."""
    v = _vehicule(ref, "bulk-redirects")
    regles = []
    for i, el in enumerate(_liste(donnees), 1):
        red = el.get("redirect", el) if isinstance(el, dict) else None
        if not isinstance(red, dict) or "source_url" not in red:
            continue
        p = {**v["parametres_par_defaut"], **{k: red[k] for k in v["parametres_par_defaut"] if k in red}}
        cible, code = red.get("target_url", ""), red.get("status_code")
        ident = f"bulk-redirects:{el.get('id') or red['source_url']}"
        etrangers = _jetons_etrangers(cible, v, ref)
        constats = [_constat(
            "jeton-litteral", BLOQUANT,
            f"« {e['jeton']} » est la forme de référence de {e['nom']} : Bulk Redirects est statique, "
            "elle arrive telle quelle dans Location",
            "retirer la référence ; les sous-chemins se reprennent par subpath_matching et preserve_path_suffix")
            for e in etrangers]
        if "*" in red["source_url"]:
            constats.append(_constat(
                "forme-non-documentee", AVERTISSEMENT,
                "Bulk Redirects ne documente aucun joker dans source_url",
                "couvrir les sous-chemins par subpath_matching"))
        if p["subpath_matching"] and not p["preserve_path_suffix"] and not etrangers:
            constats.append(_constat(
                "chemin-perdu", BLOQUANT,
                f"subpath_matching sans preserve_path_suffix : tous les sous-chemins de {red['source_url']} "
                f"aboutissent sur {cible}",
                "remettre preserve_path_suffix à true (sa valeur par défaut), ou consigner la décision par --assume",
                parametre_suggere={"preserve_path_suffix": True}))
        regles.append(_regle(ident, v["id"], red["source_url"], cible, code, constats + _juger_code(code, v, ref)))
    return regles


ANALYSEURS = {
    "page-rules": analyser_page_rules,
    "single-redirects": analyser_single_redirects,
    "bulk-redirects": analyser_bulk_redirects,
}


def detecter_vehicule(donnees) -> str | None:
    """Le vehicule d'un export JSON, reconnu a sa forme ; None si elle n'est pas reconnue."""
    d = donnees.get("result", donnees) if isinstance(donnees, dict) else donnees
    if isinstance(d, dict) and isinstance(d.get("rules"), list):
        return "single-redirects"
    if isinstance(d, list) and d and isinstance(d[0], dict):
        e = d[0]
        if "targets" in e and "actions" in e:
            return "page-rules"
        if "redirect" in e or "source_url" in e:
            return "bulk-redirects"
        if "action" in e and "expression" in e:
            return "single-redirects"
    return None


# --- sonde ---------------------------------------------------------------------------
class _SansSuivi(urllib.request.HTTPRedirectHandler):
    """La redirection est l'objet mesure : on lit son en-tete Location, on ne la suit pas."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sonder(url: str, temoin: str | None = None, ref: dict | None = None, delai: float = TIMEOUT) -> dict:
    """Demande url + chemin temoin sans suivre la redirection, et juge l'en-tete Location."""
    ref = ref or charger_referentiel()
    temoin = temoin or f"forge-seo-sonde-{secrets.token_hex(4)}/temoin"
    demandee = url.rstrip("/") + "/" + temoin
    base = {"id": url, "url_sondee": demandee, "temoin": temoin}
    gestionnaires = [_SansSuivi()]
    if urllib.parse.urlsplit(demandee).hostname in ("127.0.0.1", "localhost", "::1"):
        gestionnaires.append(urllib.request.ProxyHandler({}))  # jamais de mandataire vers la boucle locale
    requete = urllib.request.Request(demandee, headers={"User-Agent": AGENT})
    try:
        with urllib.request.build_opener(*gestionnaires).open(requete, timeout=delai) as r:
            code, location = r.status, None
    except urllib.error.HTTPError as e:
        code, location = e.code, e.headers.get("Location")
    except Exception as e:  # reseau, DNS, TLS, delai
        return {**base, "joignable": False, "code": None, "location": None,
                "motif": f"{type(e).__name__} : {e}", "constats": []}
    if code not in CODES_REDIRECTION or not location:
        return {**base, "joignable": True, "code": code, "location": location, "constats": [_constat(
            "sans-redirection", AVERTISSEMENT, f"réponse {code} sans redirection sur le chemin témoin",
            "vérifier que l'URL sondée est bien celle qui doit rediriger")]}
    lue = urllib.parse.unquote(urllib.parse.urljoin(demandee, location))
    constats = []
    jetons = [(v["nom"], m.group(0)) for v in ref["vehicules_redirection"]
              for motif in _motifs(v, sonde=True) for m in motif.finditer(lue)]
    if jetons:
        constats.append(_constat(
            "jeton-litteral", BLOQUANT,
            f"Location porte « {jetons[0][1]} » tel quel, forme de référence de {jetons[0][0]} non substituée : {lue}",
            "corriger la syntaxe de la règle (referentiel/cloudflare.json), puis rejouer la sonde"))
    elif temoin not in lue:
        constats.append(_constat(
            "chemin-perdu", BLOQUANT, f"le chemin témoin « {temoin} » n'arrive pas : Location = {lue}",
            "reprendre le chemin dans la cible de la règle, ou consigner la décision par --assume"))
    if code not in _codes_permanents(ref):
        constats.append(_constat("code-non-permanent", AVERTISSEMENT,
                                 f"redirection {code} : un moteur garde l'URL d'origine en index",
                                 "écrire 301 ou 308 si le déplacement est définitif"))
    return {**base, "joignable": True, "code": code, "location": lue, "constats": constats}


# --- verdict -------------------------------------------------------------------------
def _conforme(objet: dict) -> bool:
    return not any(c["gravite"] == BLOQUANT and not c.get("assume") for c in objet["constats"])


def assembler(regles: list[dict], sondes: list[dict], assumes: list[str], ref: dict) -> dict:
    """Verdict d'ensemble. Un --assume ne couvre qu'un chemin perdu de l'identifiant nomme."""
    assumes_set, utilises = set(assumes or []), set()
    for objet in [*regles, *sondes]:
        for c in objet["constats"]:
            if objet["id"] in assumes_set and c["genre"] in ASSUMABLES:
                c["assume"] = True
                utilises.add(objet["id"])
    joignables = [s for s in sondes if s.get("joignable")]
    juges = [*regles, *joignables]
    conformes = sum(1 for o in juges if _conforme(o))
    verdict = "SKIP" if not juges else ("PASS" if conformes == len(juges) else "FAIL")
    return {
        "oracle": "redirections",
        "verdict": verdict,
        "noeuds": NOEUDS,
        "date": dt.date.today().isoformat(),
        "referentiel": {"chemin": "referentiel/cloudflare.json", "version": ref.get("version"),
                        "date_verification": ref.get("date_verification")},
        "compte": {"conformes": conformes, "total": len(juges), "non_mesurables": len(sondes) - len(joignables)},
        "assumes_sans_effet": sorted(assumes_set - utilises),
        "regles": regles,
        "sondes": sondes,
        "non_juge": NON_JUGE,
    }


def rapporter(res: dict) -> list[str]:
    lignes = [f"oracle redirections — referentiel/cloudflare.json vérifié le "
              f"{res['referentiel']['date_verification']}", ""]
    for o in [*res["regles"], *res["sondes"]]:
        if "url_sondee" in o:
            tete = f"{o['url_sondee']} -> {o.get('code')} {o.get('location') or ''}".rstrip()
            if not o.get("joignable"):
                lignes.append(f"  [NON MESURÉ] {o['id']}  {tete} — {o.get('motif')}")
                continue
        else:
            tete = f"{o['source']} -> {o.get('cible')}" + (f" ({o['code']})" if o.get("code") else "")
        if not _conforme(o):
            etat = "ECHEC"
        elif any(c.get("assume") for c in o["constats"]):
            etat = "ASSUMÉ"
        else:
            etat = "AVERT" if o["constats"] else "OK   "
        lignes.append(f"  [{etat}] {o['id']}  {tete}")
        for c in o["constats"]:
            lignes.append(f"          {'assumé' if c.get('assume') else c['gravite']} {c['genre']} : {c['message']}")
            if c.get("remede"):
                lignes.append(f"          remède : {c['remede']}")
            if c.get("cible_suggeree"):
                lignes.append(f"          cible proposée : {c['cible_suggeree']}")
            if c.get("parametre_suggere"):
                lignes.append(f"          paramètre proposé : {json.dumps(c['parametre_suggere'])}")
    if res["assumes_sans_effet"]:
        lignes.append(f"  --assume sans effet (aucun chemin perdu sous cet identifiant) : "
                      f"{', '.join(res['assumes_sans_effet'])}")
    if res["compte"]["non_mesurables"]:
        lignes.append(f"  {res['compte']['non_mesurables']} sonde(s) non mesurée(s) : hôte injoignable, "
                      "jamais comptée(s) conforme(s)")
    lignes += ["", f"{res['compte']['conformes']}/{res['compte']['total']} règles et sondes conformes "
                   f"— verdict {res['verdict']}"]
    return lignes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Juge si les redirections préservent le chemin (nœud 28).")
    p.add_argument("--regles", action="append", default=[], metavar="CHEMIN",
                   help="fichier _redirects, ou export JSON de l'API (Page Rules, Single ou Bulk Redirects)")
    p.add_argument("--vehicule", choices=["fichier-redirects", *ANALYSEURS],
                   help="impose le véhicule au lieu de le reconnaître au contenu")
    p.add_argument("--sonder", action="append", default=[], metavar="URL",
                   help="URL en ligne qui doit rediriger : un chemin témoin y est ajouté")
    p.add_argument("--temoin", help="chemin témoin imposé (défaut : aléatoire)")
    p.add_argument("--assume", action="append", default=[], metavar="ID",
                   help="consigne qu'un chemin perdu est voulu pour cet identifiant (règle ou URL sondée)")
    p.add_argument("--projet", help="étude où écrire seo/donnees/crawl/redirections-<date>.json")
    p.add_argument("--json", action="store_true", help="sortie JSON")
    args = p.parse_args(argv)

    if not args.regles and not args.sonder:
        print("rien à juger : donner --regles <fichier> ou --sonder <url>")
        return 2
    if args.projet and not (Path(args.projet) / "seo").is_dir():
        print(f"REFUS : {args.projet} ne porte pas d'étude (dossier seo/ absent)")
        return 2

    ref = charger_referentiel()
    regles: list[dict] = []
    for chemin in args.regles:
        f = Path(chemin)
        if not f.is_file():
            print(f"REFUS : {f} introuvable")
            return 2
        texte = f.read_text(encoding="utf-8-sig")
        vehicule = args.vehicule or (None if f.suffix.lower() == ".json" else "fichier-redirects")
        if vehicule == "fichier-redirects":
            regles += analyser_fichier_redirects(texte, ref, f.name)
            continue
        try:
            donnees = json.loads(texte)
        except json.JSONDecodeError as e:
            print(f"REFUS : {f} n'est pas un JSON lisible ({e})")
            return 2
        vehicule = vehicule or detecter_vehicule(donnees)
        if vehicule is None:
            print(f"REFUS : véhicule de {f} non reconnu ; le nommer par --vehicule")
            return 2
        regles += ANALYSEURS[vehicule](donnees, ref)

    sondes = [sonder(u, args.temoin, ref) for u in args.sonder]
    res = assembler(regles, sondes, args.assume, ref)
    if args.projet:
        dossier = Path(args.projet).resolve() / "seo" / "donnees" / "crawl"
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / f"redirections-{res['date']}.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False) if args.json else "\n".join(rapporter(res)))
    return {"PASS": 0, "FAIL": 1}.get(res["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
