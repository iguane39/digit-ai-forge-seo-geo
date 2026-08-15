"""Gabarit du rapport HTML client — charte, tokens, squelette, composants.

Socle `digit-ai-page-html` : tokens :root, Roboto titres / DM Sans corps, theme
clair, aucun hex hors :root, WCAG 2.2 AA, lang="fr", un seul <h1>.

Autonomie totale : aucun appel reseau. CSS et JS inline, polices en repli systeme.
Le fichier s'ouvre hors ligne, dans deux ans, derriere un proxy.

Ce module ne lit aucune donnee : il ne sait que mettre en forme. La collecte est
dans rapport_html.py.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import html as _html
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOCLE = Path.home() / ".claude" / "skills" / "digit-ai-page-html" / "assets"
VENDOR = RACINE / "assets" / "vendor"

# Densite : le document doit PARAITRE trois fois plus court et CONTENIR deux fois
# plus. On stratifie, on ne tronque JAMAIS (regle L1 du socle). Le niveau 1 s'arrete
# a une frontiere grammaticale, le niveau 2 porte le texte integral.
PLAFOND_N1 = 170


def _asset(nom: str) -> str:
    """Lit un composant du socle, avec repli sur la copie vendoree."""
    for base in (SOCLE, VENDOR):
        p = base / nom
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def source_filtres() -> tuple[str, str]:
    """Retourne (code, origine) du composant de filtres."""
    if (SOCLE / "table-filters.js").exists():
        return (SOCLE / "table-filters.js").read_text(encoding="utf-8"), "digit-ai-page-html"
    if (VENDOR / "table-filters.js").exists():
        return (VENDOR / "table-filters.js").read_text(encoding="utf-8"), "copie vendoree"
    return "", "absent"


# --------------------------------------------------------- niveaux de preuve

# Discriminables SANS dependre de la couleur seule (WCAG) : chaque tier porte un
# glyphe distinct ET un style de bordure distinct. C'est la contrainte centrale du
# livrable -- une mise en forme uniforme rendrait un chiffre infere identique a un
# chiffre mesure, et annulerait tout le dispositif anti-hallucination.
PREUVES = {
    "T1": ("●", "observé", "mesuré directement : crawl, HTTP, HTML, rendu"),
    "T2": ("◐", "déclaré", "export client (GSC / GA / CRM), avec sa période"),
    "T3": ("◔", "tiers", "source nommée, avec URL et date de consultation"),
    "T4": ("○", "inféré", "hypothèse : fourchette et calcul visibles, jamais une prévision"),
    "NM": ("⊘", "non mesuré", "hors de portée en l'état — ce qu'il faut fournir est indiqué"),
}


# Un livrable client ne porte pas de pictogramme : l'icone se dessine, elle ne se
# tape pas. La regle vaut aussi pour ce qui REMONTE des fiches de mission -- une
# prose d'auditeur peut contenir une fleche decorative, et c'est le producteur du
# livrable qui tient la charte, pas la source. Table explicite et courte : on ne
# supprime jamais un caractere sans savoir par quoi il se lit.
PICTOGRAMMES = {
    "↔": " vs ",   # ↔ confrontation de deux sources
    "↕": " vs ",   # ↕
    "⚠": "",       # ⚠ le mot « attention » porte deja le sens
    "✅": "oui",    # ✅
    "❌": "non",    # ❌
}


def sans_pictogrammes(html: str) -> str:
    """Retire les pictogrammes connus du HTML produit, en gardant leur sens."""
    for glyphe, sens in PICTOGRAMMES.items():
        html = html.replace(glyphe, sens)
    return html


def esc(valeur) -> str:
    """Echappement systematique. Les fiches peuvent contenir des extraits de pages
    crawlees : injecte tel quel, c'est du XSS dans un document envoye a un client."""
    if valeur is None:
        return ""
    return _html.escape(str(valeur), quote=True)


def badge_preuve(tier: str, compact: bool = False) -> str:
    """Le badge reste visible dans TOUTES les vues, y compris compactes."""
    tier = (tier or "").upper()
    if tier not in PREUVES:
        return ""
    glyphe, libelle, aide = PREUVES[tier]
    cl = "pv pv-" + tier.lower() + (" pv-c" if compact else "")
    return (
        f'<span class="{cl}" title="{esc(libelle)} — {esc(aide)}">'
        f'<span class="pv-g" aria-hidden="true">{glyphe}</span>'
        + ("" if compact else f'<span class="pv-t">{esc(tier)}</span>')
        + f'<span class="sr">&nbsp;{esc(tier)} {esc(libelle)}</span></span>'
    )


def legende_preuves() -> str:
    lignes = "".join(
        f"<li>{badge_preuve(t)} <b>{esc(PREUVES[t][1])}</b> — {esc(PREUVES[t][2])}</li>"
        for t in ("T1", "T2", "T3", "T4", "NM")
    )
    return (
        '<aside class="legende" aria-label="Légende des niveaux de preuve">'
        "<h3>Comment lire ce rapport</h3>"
        # Le mot « nœud » revient partout des la premiere page (« nœud 74 ») et
        # n'etait defini nulle part : le lecteur butait dessus sans recours.
        "<p><b>Un « nœud »</b> est l'unité d'analyse de ce rapport : une question "
        "d'audit précise, posée à ce site, avec son critère de verdict et sa méthode de "
        "mesure. Les nœuds sont numérotés une fois pour toutes — « nœud 74 » désigne "
        "toujours la même question. Chaque constat, chaque verdict et chaque action y "
        'renvoie. La liste complète est au chapitre <a href="#couverture" title="Aller '
        'au chapitre Couverture de la grille">Couverture de la grille</a>.</p>'
        "<p>Chaque affirmation chiffrée porte son <b>niveau de preuve</b>. "
        "Un chiffre sans marque est une erreur de production, pas une donnée.</p>"
        f'<ul class="pv-legend">{lignes}</ul></aside>'
    )


# ------------------------------------------------------------- stratification


def tete(texte: str, plafond: int = 170) -> str:
    """Niveau 1 : la premiere unite de sens COMPLETE. Jamais une coupure.

    Regle L1 du socle : aucun texte ne se termine par une amputation. On ne
    raccourcit qu'en s'arretant a une frontiere grammaticale REELLE -- fin de phrase,
    deux-points, tiret cadratin. Si le texte n'en offre aucune avant `plafond`
    caracteres, il est rendu ENTIER : une ligne longue est lisible, un fragment
    ampute ne l'est pas.

    L'ancien `resume()` coupait a 12 mots et ajoutait une ellipse. C'est le defaut 1
    du rapport reel -- « Sur deux des… » -- et il etait present AUSSI au niveau 2,
    ce qui rendait la suite definitivement inaccessible.
    """
    t = " ".join((texte or "").split())
    if not t:
        return ""
    coupes = []
    for sep in (" : ", " — ", " – ", ". ", " ; "):
        i = t.find(sep)
        if 0 < i <= plafond:
            coupes.append(i)
    if coupes:
        return t[:min(coupes)].strip(" .;:—–")
    return t


# Sous ce volume de contenu cache, un depliant coute plus qu'il ne rapporte.
SEUIL_REPLI = 200

# --------------------------------------------------------------- glossaire
#
# Le lecteur d'un rapport SEO n'est pas SEO. Chaque terme de metier est defini AU
# PREMIER USAGE, dans la phrase, en langage courant -- pas dans un glossaire en
# annexe que personne n'ouvre. La definition n'apparait qu'une fois par document.
GLOSSAIRE = {
    "cannibalisation": "deux de vos pages se battent pour la même recherche, "
                       "et Google n'en retient souvent aucune",
    "cannibalisent": "se battent pour la même recherche",
    "doublon": "deux pages qui disent la même chose sous deux adresses différentes",
    "arbitrage": "décider laquelle des deux pages garde la main",
    "canonique": "l'étiquette qui désigne, parmi plusieurs pages jumelles, celle que "
                 "Google doit retenir",
    "orphelines": "des pages qu'aucun lien du site ne mène à découvrir",
    "maillage": "les liens que vos pages se font entre elles",
    "indexable": "que Google a le droit d'afficher dans ses résultats",
    "gabarit": "le moule d'une famille de pages — toutes les fiches de gîte, par exemple",
    "profondeur de clic": "le nombre de clics depuis l'accueil pour y arriver",
    "SERP": "la page de résultats de Google",
    "CTR": "la part des gens qui cliquent quand votre page leur est montrée",
    "impressions": "le nombre de fois où votre page a été montrée dans les résultats",
    "méta-description": "le texte gris affiché sous le titre dans les résultats de Google",
}
# Ni a l'interieur d'une balise, ni DEJA suivie de son libelle (« A1 · … »). Sans ce
# second garde-fou, une reference deja nommee par le verdict genere se faisait
# renommer une seconde fois et le libelle sortait en double.
RE_ACTION = re.compile(r"(?<![\w#>])(A\d{1,2})\b(?!\s*·)(?![^<]*>)")


class Vocabulaire:
    """Definit chaque terme de metier UNE FOIS, a son premier usage dans le document.

    L'etat est porte par le document et non par le bloc : redefinir
    « cannibalisation » a chaque fiche serait aussi penible que ne jamais la definir.
    """

    def __init__(self) -> None:
        self.vus: set[str] = set()

    def glose(self, html: str) -> str:
        for terme, sens in GLOSSAIRE.items():
            if terme in self.vus:
                continue
            # Hors balise et hors attribut : `(?![^<]*>)` garantit qu'on est dans du
            # texte, pas dans un title= ou un href=.
            motif = re.compile(r"(?<![\w-])(" + re.escape(terme) + r")(?![\w-])(?![^<]*>)",
                               re.I)
            html, n = motif.subn(
                lambda m, sens=sens: (
                    f'<span class="glose" title="{esc(sens)}">{m.group(1)}</span>'
                    f'<span class="glose-d"> — {esc(sens)}</span>'),
                html, count=1)
            if n:
                self.vus.add(terme)
        return html


def refs_actions(html: str, libelles: dict) -> str:
    """« traité par A5 » ne dit rien a personne. « A5 · Poser une balise canonique
    auto-référente » dit ce qu'on fait. Les libelles viennent du CSV d'actions : on
    ne les invente pas, on cesse de les cacher."""
    if not libelles:
        return html

    def _nomme(m):
        ident = m.group(1)
        libelle = libelles.get(ident)
        if not libelle:
            return ident
        court = tete(" ".join(libelle.split()), 80)
        return (f'<span class="ref-a" title="{esc(libelle)}">{esc(ident)} · '
                f"{esc(court)}</span>")

    return RE_ACTION.sub(_nomme, html)


def enumeration(texte: str):
    """Detecte une enumeration `cle — valeur ; cle — valeur ; …` et la rend en table.

    Regle L12 du socle : au-dela de trois elements, ce n'est plus de la prose, c'est
    un tableau que l'auteur a refuse d'assumer. Le lecteur ne peut ni comparer, ni
    trier, ni reperer la valeur aberrante. Retourne (html_table, ligne_de_lecture),
    ou None si le texte n'est pas une enumeration.

    Deux formes rencontrees en production, toutes deux acceptees :
      « Informations — pages 7, etendue en mots 386-567 ; Inclus — pages 7, … »
      « Faits attribuables : absent — aucune date ; Balisage (JSON-LD) : 0 sur 79 ; … »
    Le separateur est le premier ` : ` ou ` — ` de chaque segment. Un segment qui n'en
    porte aucun disqualifie l'ensemble : mieux vaut laisser en prose que decouper de
    travers.

    La ligne de lecture produite ici est FACTUELLE -- comptages, total, etendue. Elle
    ne pretend pas dire ce que l'analyste en conclut : ca, c'est le travail de la
    fiche, et ce qu'il en reste est declare comme limite.
    """
    t = " ".join((texte or "").split())
    segments = [x.strip(" .") for x in t.split(";") if x.strip(" .")]
    if len(segments) < 3:
        return None

    # Le separateur se CHOISIT sur l'ensemble, pas segment par segment. Sinon une cle
    # qui contient elle-meme un tiret -- une fourchette de positions « 1 – 3 » -- se
    # fait couper en deux et l'enumeration entiere devient illisible ou irreparable.
    sep = next((c for c in (" — ", " : ", " – ")
                if all(c in seg for seg in segments)), None)
    if sep is None:
        return None
    couples = []
    for seg in segments:
        cle, _, reste = seg.partition(sep)
        cle, reste = cle.strip(), reste.strip()
        if len(cle) < 2 or len(reste) < 2 or len(cle) > 70:
            return None
        couples.append((cle, reste))

    # Sous-decoupage par virgules : seulement s'il est REGULIER sur toutes les lignes,
    # et sans casser les decimales -- « ctr 26,66 % » est une valeur, pas deux.
    parts = [[c[0]] + [x.strip() for x in re.split(r",(?=\s*[^\d\s])", c[1]) if x.strip()]
             for c in couples]
    largeur = max(len(x) for x in parts)
    if largeur < 2 or any(len(x) != largeur for x in parts):
        parts = [[c[0], c[1]] for c in couples]
        largeur = 2

    # Un intitule de colonne n'est retenu que s'il prefixe TOUTES les lignes. Sinon
    # il decrirait une partie du tableau et mentirait sur le reste -- « Absent » en
    # tete d'une colonne dont une ligne sur cinq vaut « 0 sur 79 pages ».
    entetes = ["Élément"]
    for i in range(1, largeur):
        prefixes = [re.match(r"^([^\d]{2,})\s", l[i]) for l in parts]
        communs = {m.group(1).strip().lower() for m in prefixes if m}
        commun = (next(iter(communs)) if len(communs) == 1
                  and all(prefixes) else None)
        entetes.append(commun.capitalize() if commun else "Constat")
    if len(entetes) != len(set(entetes)):
        entetes = ["Élément"] + [f"Constat {i}" for i in range(1, largeur)]

    def _val(cellule, entete):
        v = re.sub(r"^" + re.escape(entete) + r"\s*", "", cellule, flags=re.I).strip()
        return (v or cellule).lstrip("—– ").strip() or cellule

    th = "".join(f'<th scope="col">{esc(h)}</th>' for h in entetes)
    tr = "".join(
        "<tr>" + "".join(
            f"<td>{md(l[0] if i == 0 else _val(l[i], entetes[i]))}</td>"
            for i in range(largeur))
        + "</tr>"
        for l in parts
    )
    table = ('<table class="mini" data-filterable="off" '
             'data-filterable-reason="relevé d\'une fiche, lu en place">'
             f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>")

    bits = [f"{len(parts)} éléments relevés"]
    if largeur >= 2:
        n1 = [re.findall(r"\d+", l[1]) for l in parts]
        if all(len(x) == 1 for x in n1):
            bits.append(f"{sum(int(x[0]) for x in n1)} {entetes[1].lower()} au total")
    # L'etendue ne s'annonce que si CHAQUE ligne porte un nombre dans la derniere
    # colonne : sinon on donne la fourchette d'un sous-ensemble en la presentant
    # comme celle du tableau.
    par_ligne = [re.findall(r"\d+(?:[.,]\d+)?", l[-1]) for l in parts]
    if all(par_ligne) and entetes[-1] != "Constat":
        nombres = [float(x.replace(",", ".")) for xs in par_ligne for x in xs]
        if min(nombres) != max(nombres):
            bits.append(f"{entetes[-1].lower()} de {min(nombres):g} à {max(nombres):g}")
    lecture = "Ce que montre ce relevé — " + ", ".join(bits) + "."
    return table, lecture


def champs(paires: list[tuple[str, str]]) -> str:
    """Champs etiquetes, une ligne PLEINE LARGEUR par champ.

    Constat utilisateur du 09/08 : « a qui sert ce bouton ? un tiers d'informations
    supplementaires, aucun interet ». La cause n'etait pas la quantite d'information
    mais sa mise en page -- une grille a deux colonnes dont la premiere, reservee aux
    etiquettes, occupait 267 px sur 1 215 (22 %). Le contenu etait tasse a droite dans
    les deux tiers restants, et la mesure L2 au rendu ne le voyait pas : chaque
    colonne remplissait bien SA case de grille. L'angle mort etait la grille.

    Une etiquette de champ s'ecrit EN TETE DE LIGNE, pas dans une colonne. Le texte
    reprend toute la largeur, et l'etiquette reste reperable parce qu'elle est en
    gras et en tete.
    """
    # <div> et non <p> : la valeur peut contenir des paragraphes rendus depuis le
    # markdown d'une fiche, et un <p> dans un <p> fait FERMER le premier par le
    # parseur -- le champ « Preuves » sortait alors du bloc et se posait dans la
    # marge de la page. Vu sur la capture, invisible dans le code.
    return "".join(
        f'<div class="champ"><b>{esc(k)}</b> — {v}</div>'
        for k, v in paires
        if v
    )


def strate(n1: str, n2_titre: str, n2_corps: list[tuple[str, str]],
           n2_suffixe: str = "") -> str:
    """Niveau 1 toujours visible, niveau 2 depliable EN PLACE, INTEGRAL.

    `n2_titre` doit annoncer l'USAGE du depliant, pas son contenu : « verifier ce
    constat », pas « details ». Un lecteur qui ne sait pas a quoi sert un bouton ne
    l'ouvre pas -- et s'il l'ouvre, il juge inutile ce qu'il y trouve.
    `n2_suffixe` : ce qui identifie l'element (numero de noeud, identifiant), remonte
    dans le summary pour economiser une ligne dediee.

    Pas de ligne inseree : une <tr> supplementaire casserait le composant de filtres,
    qui itere les lignes du tbody.
    """
    lignes = champs(n2_corps)
    if not lignes:
        return f'<div class="st"><div class="n1">{n1}</div></div>'
    suffixe = f'<span class="n2-s">{esc(n2_suffixe)}</span>' if n2_suffixe else ""
    # Un depliant coute un clic et une decision. Sous SEUIL_REPLI caracteres caches,
    # le contenu tient a l'ecran : le replier fabrique un obstacle, et le lecteur qui
    # l'ouvre se sent trompe -- « a qui sert ce bouton ? un tiers d'informations
    # supplementaires, aucun interet ». En dessous, on affiche en pied de bloc, en
    # style discret. Regle L9(c) du socle.
    utile = len(re.sub(r"<[^>]+>", "", lignes))
    if utile < SEUIL_REPLI:
        return (
            '<div class="st">'
            f'<div class="n1">{n1}</div>'
            f'<div class="meta-pied">{lignes}'
            + (f'<div class="champ meta-id">{esc(n2_suffixe)}</div>'
               if n2_suffixe else "")
            + "</div></div>"
        )
    return (
        '<div class="st">'
        f'<div class="n1">{n1}</div>'
        f'<details class="n2"><summary>{esc(n2_titre)}{suffixe}</summary>'
        f'<div class="n2-c">{lignes}</div></details></div>'
    )


# ------------------------------------------------------------------ markdown

RE_MD_GRAS = re.compile(r"\*\*(.+?)\*\*", re.S)
RE_MD_CODE = re.compile(r"`([^`\n]+)`")
RE_MD_ITAL = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
RE_MD_LIGNE_TABLE = re.compile(r"^\s*\|.*\|\s*$")
RE_MD_SEP_TABLE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def md(valeur) -> str:
    """Rend le sous-ensemble sur du markdown des fiches, en ligne (TF-0046).

    Les fiches sont des .md et le referentiel lui-meme met du gras dans les gabarits
    (`critere_verdict` en contient). Injecte par `esc()` seul, le lecteur voit des
    asterisques. On echappe D'ABORD -- le balisage est produit apres, jamais avant,
    sinon un extrait de page crawlee redevient injectable.
    """
    s = esc(valeur)
    s = RE_MD_GRAS.sub(r"<b>\1</b>", s)
    s = RE_MD_CODE.sub(r"<code>\1</code>", s)
    s = RE_MD_ITAL.sub(r"<i>\1</i>", s)
    return s


def md_bloc(valeur) -> str:
    """Rend un bloc markdown : paragraphes, listes a puces et TABLEAUX de preuve.

    Sans cela les tableaux des fiches sortent en soupe de barres verticales -- c'est
    le cout constate de TF-0046, contourne cote mission par un convertisseur ad hoc.
    """
    brut = str(valeur or "").replace("\r\n", "\n")
    if not brut.strip():
        return ""
    out, tampon_liste, tampon_table, tampon_para = [], [], [], []

    def vider_para():
        # Les fiches sont ecrites en markdown, donc repliees a ~80 colonnes. Traiter
        # chaque ligne comme un paragraphe disloquait les phrases : « ...sur
        # /contact/gites : » puis « meme titre, et... » devenaient deux blocs. Seule
        # une ligne VIDE separe deux paragraphes.
        if not tampon_para:
            return
        texte = " ".join(tampon_para)
        tampon_para.clear()
        # Une enumeration de donnees n'est pas un paragraphe : c'est un tableau que
        # l'auteur a refuse d'assumer. On l'assume a sa place (regle L12).
        enum = enumeration(texte)
        if enum:
            table, lecture = enum
            out.append(f'<p class="lecture">{md(lecture)}</p>{table}')
            return
        out.append("<p>" + md(texte) + "</p>")

    def vider_liste():
        if tampon_liste:
            out.append("<ul class=\"md-l\">"
                       + "".join(f"<li>{md(x)}</li>" for x in tampon_liste) + "</ul>")
            tampon_liste.clear()

    def vider_table():
        if not tampon_table:
            return
        cellules = [
            [c.strip() for c in ligne.strip().strip("|").split("|")]
            for ligne in tampon_table if not RE_MD_SEP_TABLE.match(ligne)
        ]
        tampon_table.clear()
        if not cellules:
            return
        entete, corps = cellules[0], cellules[1:]
        th = "".join(f'<th scope="col">{md(c)}</th>' for c in entete)
        tr = "".join(
            "<tr>" + "".join(f"<td>{md(c)}</td>" for c in l) + "</tr>" for l in corps
        )
        # Table de preuve imbriquee : hors perimetre du composant de filtres (elle
        # se lit, elle ne se parcourt pas), exemptee AVEC son motif.
        out.append(
            '<table class="mini" data-filterable="off" '
            'data-filterable-reason="table de preuve d\'une fiche, lue en place">'
            f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"
        )

    for ligne in brut.split("\n"):
        t = ligne.rstrip()
        if RE_MD_LIGNE_TABLE.match(t):
            vider_para()
            vider_liste()
            tampon_table.append(t)
            continue
        vider_table()
        nu = t.strip()
        if nu.startswith(("- ", "* ", "• ")):
            vider_para()
            tampon_liste.append(nu[2:].strip())
            continue
        vider_liste()
        if nu:
            tampon_para.append(nu)
        else:
            vider_para()
    vider_para()
    vider_liste()
    vider_table()
    return "".join(out)


# ------------------------------------------------------------------- fragments


def absence(titre: str, motif: str, cout: str, remede: str) -> str:
    """Une absence est une information : ce qui manque, pourquoi, ce que ça coûte au
    lecteur, et comment la lever."""
    return (
        f'<div class="absence"><p class="abs-t">{badge_preuve("NM")} {esc(titre)}</p>'
        f"<p>{esc(motif)}</p>"
        f'<p class="abs-c"><b>Ce que ça coûte</b> — {esc(cout)}</p>'
        f'<p class="abs-r"><b>Pour la lever</b> — {esc(remede)}</p></div>'
    )


def chapitre(num: int, ident: str, titre: str, corps: str, apprend: str = "",
             exemple: str = "", annexe: str = "") -> str:
    """`annexe` : si fourni, le corps est replie derriere ce libelle.

    `apprend` (regle L7) : ce que ce chapitre apprend au lecteur. Un chapitre qui
    ouvre sur un tableau oblige a lire le tableau pour savoir s'il interesse.
    `exemple` (regle L10) : comment se lit une ligne, pour les chapitres de donnees.
    Sans lui, une table exacte reste un vidage de donnees filtrable.

    Les tables de reference — couverture, inventaire d'URL — sont consultees, pas
    lues. Les laisser ouvertes rallonge le document de plusieurs milliers de pixels
    sans rien apporter au lecteur qui parcourt.
    """
    tete_ch = (f'<p class="ch-apprend"><b>Ce que ce chapitre vous apprend</b> — '
               f"{esc(apprend)}</p>" if apprend else "")
    ex = (f'<p class="exemple-lecture"><b>Comment lire</b> — {esc(exemple)}</p>'
          if exemple else "")
    if annexe:
        corps = (f'<details class="annexe"><summary>{esc(annexe)}</summary>'
                 f'<div class="annexe-c">{ex}{corps}</div></details>')
        ex = ""
    return (
        f'<section id="{esc(ident)}" class="ch">'
        f'<h2><span class="ch-n">{num}</span>{esc(titre)}</h2>'
        f"{tete_ch}{ex}{corps}</section>"
    )


def sommaire(entrees: list[tuple[int, str, str, str, str]]) -> str:
    """Sommaire collant. `entrees` = (num, ident, titre, annonce, compte).

    Regle L6 : chaque entree porte une ANNONCE. Un sommaire de titres nus oblige a
    ouvrir chaque chapitre pour savoir s'il interesse -- il coute plus qu'il ne
    rapporte, et c'est le defaut 7 du rapport reel.
    """
    li = "".join(
        f'<li><a href="#{esc(i)}"><span class="toc-hd">'
        f'<span class="toc-n">{n}</span>'
        f'<span class="toc-t">{esc(t)}</span>'
        + (f'<span class="toc-c">{esc(c)}</span>' if c else "")
        + f'</span><span class="toc-d">{esc(a)}</span></a></li>'
        for n, i, t, a, c in entrees
    )
    return (
        '<nav class="toc" aria-label="Sommaire"><details open><summary>'
        '<span class="toc-h">Sommaire — ce que chaque chapitre apporte</span>'
        '<span class="toc-x" aria-hidden="true"></span></summary>'
        f"<ol>{li}</ol></details></nav>"
    )


# ------------------------------------------------- restitution lisible (RL)
#
# Referentiel : <forge-design>/REFERENTIEL-RESTITUTION.md, famille « rapport ».
# Le rapport se lit par VUES : une question par vue, une navigation permanente,
# des chiffres qui portent leur lecture. Les chapitres existants ne sont ni
# resumes ni tronques -- ils changent de conteneur, rien de plus.


def nav_vues(entrees: list[tuple[str, str, str, str]]) -> str:
    """Navigation de vues. `entrees` = (ident, numero, titre, annonce).

    Elle tient le role de sommaire du document (regle L6 du socle : chaque entree
    porte une annonce d'au moins 12 caracteres) ET celui de navigation de vues du
    referentiel de restitution (RL-1 : chaque entree porte `data-vue`).
    """
    li = "".join(
        f'<li><a href="#{esc(i)}" data-vue="{esc(i)}" role="tab" '
        f'aria-selected="{"true" if k == 0 else "false"}">'
        f'<span class="toc-hd"><span class="toc-n">{esc(n)}</span>'
        f'<span class="toc-t">{esc(t)}</span></span>'
        f'<span class="toc-d">{esc(a)}</span></a></li>'
        for k, (i, n, t, a) in enumerate(entrees)
    )
    return (
        '<nav class="toc vues" aria-label="Sommaire" role="tablist">'
        '<details open><summary>'
        '<span class="toc-h">Sommaire — six vues, une question par vue</span>'
        '<span class="toc-x" aria-hidden="true"></span></summary>'
        f"<ol>{li}</ol></details></nav>"
    )


def vue(ident: str, titre: str, objectif: str, corps: str, active: bool = False) -> str:
    """Une vue : son titre (lu par les technologies d'assistance), ce qu'elle
    apprend au lecteur (regle L7 du socle, regle RL-2 du referentiel), son corps."""
    return (
        f'<section class="vue{" active" if active else ""}" id="{esc(ident)}" '
        f'role="tabpanel" aria-label="{esc(titre)}">'
        f'<h2 class="sr">{esc(titre)}</h2>'
        f'<p class="objectif ch-apprend"><b>Ce que cette vue vous apprend</b> — '
        f"{esc(objectif)}</p>{corps}</section>"
    )


def kpi(label: str, valeur: str, definition: str, repere: str,
        ident: str, unite: str = "", action: tuple[str, str] | None = None) -> str:
    """Composant RL-3 : un chiffre affiche porte sa valeur, sa definition, son
    repere de lecture, et l'action qu'il appelle s'il en appelle une.

    `valeur` et `unite` sont du HTML deja echappe par l'appelant (une valeur peut
    porter un badge de preuve). `ident` sert d'ancre au repere : c'est lui que
    `aria-describedby` designe, pour que le chiffre ne se lise jamais seul.
    """
    lien = ""
    if action:
        libelle, href = action
        lien = f'<a class="k-action" href="{esc(href)}">{esc(libelle)}</a>'
    return (
        '<article class="kpi">'
        f'<span class="k-label">{esc(label)}</span>'
        f'<span class="k-valeur" aria-describedby="{esc(ident)}">{valeur}'
        + (f" <small>{esc(unite)}</small>" if unite else "")
        + "</span>"
        f'<span class="kpi-d">{esc(definition)}</span>'
        f'<span class="k-repere" id="{esc(ident)}">{esc(repere)}</span>'
        f"{lien}</article>"
    )


def figure_barres(question: str, sous_titre: str,
                  lignes: list[tuple[str, str, float, str]]) -> str:
    """Graphique en barres horizontales (RL-4). `lignes` = (nom, valeur affichee,
    part de 0 a 1, lecture accessible).

    Un seul `rect` par `svg` : la piste est le FOND du svg, en CSS. Deux rects
    superposes dans un meme svg sont un chevauchement au sens du controle V1-V7 du
    socle, et le rendu le refuse -- a juste titre, rien ne dit lequel est devant.
    """
    corps = "".join(
        f'<div class="g-ligne"><span class="g-nom">{esc(nom)}</span>'
        f'<svg class="g-piste" viewBox="0 0 100 8" preserveAspectRatio="none" '
        f'role="img" aria-label="{esc(aria)}">'
        f'<rect x="0" y="0" width="{max(0.6, min(100.0, part * 100)):.1f}" height="8" '
        f'rx="1" fill="var(--{"blue" if k == 0 else "teal"})"/></svg>'
        f'<span class="g-val">{esc(val)}</span></div>'
        for k, (nom, val, part, aria) in enumerate(lignes)
    )
    return (
        '<figure class="graphe"><figcaption>' + esc(question) + "</figcaption>"
        f'<p class="g-sous">{esc(sous_titre)}</p>{corps}</figure>'
    )


def figure_empilee(question: str, sous_titre: str,
                   segments: list[tuple[str, int, str]]) -> str:
    """Graphique en barre empilee (RL-4). `segments` = (libelle, valeur, jeton de
    couleur). Les segments sont juxtaposes, jamais superposes.

    La legende est en HTML et non dans le SVG : elle doit rester lisible quand le
    graphique est reduit, et se chercher avec la recherche globale.
    """
    total = sum(max(0, v) for _, v, _ in segments)
    if not total:
        return ""
    parts, x = [], 0.0
    for libelle, valeur, jeton in segments:
        w = 100.0 * max(0, valeur) / total
        parts.append((libelle, valeur, jeton, x, w))
        x += w
    rects = "".join(
        f'<rect x="{gx:.2f}" y="0" width="{max(0.0, gw):.2f}" height="8" '
        f'fill="var(--{jeton})"/>'
        for _, _, jeton, gx, gw in parts
    )
    aria = ", ".join(f"{libelle} : {valeur}" for libelle, valeur, _, _, _ in parts)
    legende = "".join(
        f'<li><span class="g-puce" style="background:var(--{jeton})" '
        f'aria-hidden="true"></span><b>{valeur}</b> {esc(libelle)}</li>'
        for libelle, valeur, jeton, _, _ in parts
    )
    return (
        '<figure class="graphe"><figcaption>' + esc(question) + "</figcaption>"
        f'<p class="g-sous">{esc(sous_titre)}</p>'
        f'<svg class="g-empile" viewBox="0 0 100 8" preserveAspectRatio="none" '
        f'role="img" aria-label="{esc(aria)}">{rects}</svg>'
        f'<ul class="g-legende">{legende}</ul></figure>'
    )


def chemins(entrees: list[tuple[str, str]]) -> str:
    """« Vous etes X, commencez ici » (RL-9). `entrees` = (lecteur, conduite).

    La conduite est du HTML : elle porte les liens vers les vues.
    """
    li = "".join(
        f'<li class="chemin"><b>{esc(qui)}</b>{quoi}</li>' for qui, quoi in entrees
    )
    return ('<h3>Par où commencer, selon qui vous êtes</h3>'
            f'<ul class="chemins">{li}</ul>')


def manifeste_ecarts(ecarts: list[str]) -> str:
    """Manifeste d'ecarts (RL-10). Un ecart se declare ; « aucun ecart » aussi."""
    items = ecarts or ["Aucun écart déclaré : les règles RL-1 à RL-10 sont tenues "
                       "sur les données de cette mission."]
    return (
        '<footer class="ecarts"><h2>Ce que ce rapport ne fait pas — manifeste '
        "d'écarts</h2><ul>"
        + "".join(f"<li>{esc(x)}</li>" for x in items)
        + "</ul></footer>"
    )


def recherche_globale() -> str:
    return (
        '<div class="find"><label class="sr" for="q">Rechercher dans le document</label>'
        '<input id="q" type="search" placeholder="Rechercher dans tout le rapport…" '
        'autocomplete="off">'
        '<span id="qn" class="find-n" aria-live="polite"></span></div>'
    )


def tableau(
    ident: str,
    colonnes: list[dict],
    lignes: list[list],
    libelle: str,
    groupes: list[tuple[str, int]] | None = None,
    tri_defaut: tuple[int, int] | None = None,
) -> str:
    """Tableau interactif : filtres de colonne, tri, regroupement, filtre texte.

    `colonnes`   : [{'t': intitulé, 'w': largeur %, 'tri': 'num'|'txt'|None}]
    `lignes`     : cellules — str, ou (html, valeur_de_tri)
    `groupes`    : [(libellé, index de colonne)] — clés commutables
    `tri_defaut` : (index, sens), sens 1 croissant / -1 décroissant
    """
    if not lignes:
        return ""

    # `aide` : identifiant d'un bloc qui EXPLIQUE la colonne. Obligatoire des que la
    # colonne porte une valeur calculee -- c'est elle qui ordonne le tableau, et sans
    # sa formule le lecteur doit la croire sur parole (regle L3(c) du socle).
    th = "".join(
        '<th scope="col"'
        + (f' style="width:{c["w"]}%"' if c.get("w") else "")
        + (f' data-tri="{c["tri"]}"' if c.get("tri") else "")
        + (f' aria-describedby="{esc(c["aide"])}"' if c.get("aide") else "")
        + f'>{esc(c["t"])}</th>'
        for c in colonnes
    )
    tr = "".join(
        "<tr>"
        + "".join(
            f'<td data-l="{esc(colonnes[i]["t"] if i < len(colonnes) else "")}"'
            + (f' data-v="{esc(c[1])}"' if isinstance(c, tuple) else "")
            + f">{c[0] if isinstance(c, tuple) else c}</td>"
            for i, c in enumerate(l)
        )
        + "</tr>"
        for l in lignes
    )

    filtrable = " data-filterable" if len(lignes) >= 5 else ""
    grp = ""
    if groupes:
        opts = "".join(f'<option value="{i}">{esc(nom)}</option>' for nom, i in groupes)
        grp = (
            '<label class="tb-g">Grouper par '
            f'<select data-groupe-for="{esc(ident)}">'
            f'<option value="">— aucun —</option>{opts}</select></label>'
        )
    tri = f' data-tri-defaut="{tri_defaut[0]},{tri_defaut[1]}"' if tri_defaut else ""

    outils = (
        f'<div class="tb" role="toolbar" aria-label="Outils — {esc(libelle)}">'
        f'<label class="tb-q"><span class="sr">Filtrer {esc(libelle)}</span>'
        f'<input type="search" data-q-for="{esc(ident)}" placeholder="Filtrer ces lignes…" '
        'autocomplete="off"></label>'
        f"{grp}"
        f'<span class="tf-count" data-tf-count-for="{esc(ident)}" aria-live="polite"></span>'
        '<span class="tb-aide">Cliquer un en-tête pour trier</span>'
        "</div>"
    )

    return (
        f"{outils}"
        f'<div class="tw"><table id="{esc(ident)}"{filtrable}{tri}>'
        f'<caption class="sr">{esc(libelle)}</caption>'
        f"<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>"
    )


# Baremes : ce que valent les crans. Un score sans bareme n'informe pas -- « maturite
# 1/5 » ne dit ni ce qu'est 1, ni ce qu'il faudrait pour atteindre 2. Regle L3 du
# socle : le bareme existe DANS la page (il doit survivre au PDF, ou aucun `title`
# ne subsiste) et chaque valeur y renvoie par aria-describedby.
BAREMES = {
    # Le barème se designe par le NOM du noeud, pas par son numero : ce module est
    # de la presentation pure, il n'a pas acces au manifeste, et un numero fige ici
    # designe autre chose des la premiere evolution de grille -- « nœud 87 » a cesse
    # d'etre la Machine SEO le 11/08/2026, en silence.
    "maturite": ("Barème de maturité de la machine SEO (nœud « Machine SEO », "
                 "branche Objectif)", [
        ("1", "aucun dispositif — le site ne produit ni ne mesure sa visibilité"),
        ("2", "dispositif partiel non instrumenté — on publie, on ne mesure pas"),
        ("3", "mesure en place sans boucle de correction — on constate, on ne corrige pas"),
        ("4", "boucle de correction outillée et périodique, sans objectif chiffré"),
        ("5", "pilotage continu : objectifs chiffrés, revue périodique, arbitrage documenté"),
    ]),
    "gain": ("Barème de gain attendu d'une action", [
        ("1", "effet marginal, non mesurable isolément"),
        ("2", "effet mesurable sur un indicateur secondaire"),
        ("3", "effet mesurable sur le trafic ou la conversion d'un gabarit"),
        ("4", "effet mesurable sur le trafic global du site"),
        ("5", "lève un blocage structurel dont dépendent d'autres actions"),
    ]),
    "effort": ("Barème d'effort de mise en œuvre", [
        ("1", "moins d'une demi-journée, sans dépendance"),
        ("2", "1 à 2 jours, une compétence disponible en interne"),
        ("3", "3 à 5 jours, ou une compétence à mobiliser"),
        ("4", "1 à 3 semaines, ou une dépendance externe (agence, éditeur)"),
        ("5", "chantier de plus d'un mois, ou refonte d'un composant du site"),
    ]),
    "confiance": ("Barème de confiance dans l'estimation", [
        ("1", "hypothèse non étayée — à requalifier avant engagement"),
        ("2", "analogie avec un cas voisin, sans mesure sur ce site"),
        ("3", "mécanisme connu, ampleur estimée par fourchette"),
        ("4", "mécanisme constaté sur ce site, ampleur encadrée par une mesure"),
        ("5", "effet déjà observé sur ce site lors d'un run précédent"),
    ]),
    # Le lecteur naif : « je dois vous croire sur parole pour la seule colonne qui
    # classe vos actions ». La formule est au referentiel (referentiel/scoring.md) ;
    # elle n'etait nulle part dans le livrable. Un score sans formule est un barème
    # absent (regle L3(c)).
    "score": ("Score de priorité — comment il est calculé", [
        ("Formule", "score = (gain × confiance) ÷ effort, chacun noté de 1 à 5"),
        ("Amplitude", "de 0,2 (gain 1, confiance 1, effort 5) à 25 (gain 5, "
                      "confiance 5, effort 1)"),
        ("Pourquoi la confiance au numérateur", "une action à fort gain supposé mais "
         "non étayé doit reculer derrière une action à gain moyen et prouvé — c'est ce "
         "qui empêche le plan de se remplir de paris"),
        ("≥ 6", "à engager sur les deux premiers trimestres"),
        ("2 à 6", "backlog qualifié — à engager quand la capacité se libère, ou après "
                  "avoir levé l'incertitude qui plafonne la confiance"),
        ("< 2", "ne pas engager, sauf si l'action est la dépendance d'une action "
                "au-dessus du trait"),
    ]),
    # Enum du schema de snapshot : affiche nu, `ia-assistee-validation-humaine` ne se
    # lit pas. Regle L3(d).
    "regime": ("Régimes d'automatisation — comment l'action s'exécute", [
        ("bout-en-bout", "automatisable de bout en bout : le dispositif posé, l'action "
                         "se répète sans intervention humaine"),
        ("ia-assistee-validation-humaine", "l'IA produit, un humain valide avant "
                                           "publication — le gain porte sur le temps de "
                                           "production, jamais sur la décision"),
        ("manuel-strict", "aucune part automatisable : arbitrage, négociation, ou "
                          "production qui engage la marque"),
    ]),
    # Vocabulaire de base du rapport, employe des la synthese (« nœud 74 ») et jamais
    # defini : le lecteur naif butait dessus.
    "noeud": ("Nœud — l'unité d'analyse de ce rapport", [
        ("Définition", "une question d'audit précise, posée à ce site, avec son critère "
                       "de verdict et sa méthode de mesure"),
        ("Numérotation", "les nœuds sont numérotés une fois pour toutes dans la grille "
                         "de forge-seo ; « nœud 74 » désigne toujours la même question"),
        ("Pourquoi ça compte", "chaque constat, chaque verdict et chaque action renvoie "
                               "au nœud qui l'a produit — c'est ce qui rend le rapport "
                               "opposable plutôt que déclaratif"),
        ("Où les voir tous", "chapitre « Couverture de la grille » : la liste complète, "
                             "avec le sort de chacun"),
    ]),
}


def bareme(cle: str) -> str:
    """Le bareme publie, cible des aria-describedby des valeurs correspondantes."""
    titre, crans = BAREMES[cle]
    li = "".join(f"<li><b>{esc(n)}</b> — {esc(t)}</li>" for n, t in crans)
    return (f'<div class="bareme" id="bareme-{esc(cle)}">'
            f"<b>{esc(titre)}</b><ol class=\"bareme-l\">{li}</ol></div>")


def baremes(cles: list[str], ident: str = "baremes-scores") -> str:
    """Bloc replie qui publie les baremes de la page. UNE seule fois.

    Un bareme duplique produirait des id en double : aria-describedby ne resoudrait
    plus de facon deterministe, et le controle L3 le dirait.
    """
    return (
        f'<details class="baremes" id="{esc(ident)}" open>'
        "<summary>Vocabulaire et barèmes — ce que désigne un nœud, comment se calcule "
        "un score, ce que valent les crans</summary>"
        '<div class="baremes-c">'
        + "".join(bareme(c) for c in cles if c in BAREMES)
        + "</div></details>"
    )


def legende_valeur(cle: str, valeur) -> str:
    """Rend une valeur d'enum AVEC sa legende liee (regle L3(d)).

    Un jeton comme `ia-assistee-validation-humaine` est ecrit pour une machine.
    Affiche nu, il demande au lecteur de deviner -- et il ne devine pas.
    """
    v = str(valeur or "").strip()
    if not v:
        return ""
    sens = dict(BAREMES.get(cle, ("", []))[1]).get(v, "")
    if not sens:
        return esc(v)
    return (f'<span class="jeton" title="{esc(sens)}" '
            f'aria-describedby="bareme-{esc(cle)}">{esc(v)}</span>'
            f'<span class="jeton-d">{esc(sens)}</span>')


def barre(valeur, maxi: int = 5, libelle: str = "", cle: str = "") -> str:
    """Echelle 1-5 lisible sans couleur : carres pleins et vides.

    `cle` designe le bareme publie auquel la valeur renvoie. Sans lui, la valeur
    n'est pas interpretable et le controle L3 la refuse -- c'est voulu.
    """
    try:
        v = int(float(valeur))
    except (TypeError, ValueError):
        return '<span class="sc-na">n/d</span>'
    v = max(0, min(maxi, v))
    cle = cle or libelle
    titre, crans = BAREMES.get(cle, ("", []))
    sens = dict(crans).get(str(v), "")
    aide = f"{libelle or cle} {v} sur {maxi}" + (f" — {sens}" if sens else "")
    lien = f' aria-describedby="bareme-{esc(cle)}"' if cle in BAREMES else ""
    return (
        f'<span class="sc" title="{esc(aide)}"{lien}>'
        f'<span aria-hidden="true">{"▩" * v}{"▢" * (maxi - v)}</span>'
        f'<span class="sr">{esc(aide)}</span></span>'
    )


# ------------------------------------------------------------------------- CSS

CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0}

:root{
  --blue:#2563EB; --blue-fill:#EFF4FE; --blue-line:#C9DBFC;
  --bg:#FAFBFF; --surface:#FDFDFF; --card:#FDFDFF;
  --ink:#0F172A; --muted:#475569; --faint:#64748B; --line:#E6EAF2;
  --amber:#B45309; --amber-fill:#FFFBEB; --amber-line:#FDE9C8;
  --teal:#0E7490;  --teal-fill:#EFFDFB;  --teal-line:#C7F0EA;
  --green:#15803D; --green-fill:#F2FCF5; --green-line:#CFEEDD;
  --danger:#B91C1C; --danger-fill:#FEF2F2; --danger-line:#FBD5D5;
  --mark:#FEF08A;
  --accent:var(--blue);
  --r:12px; --r-sm:8px;
  --head:"Roboto",system-ui,-apple-system,"Segoe UI",sans-serif;
  --sans:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"Consolas",monospace;
  /* CONSTAT 2 du 09/08 -- « le texte s'arrete a la moitie de son conteneur ».
     La doctrine precedente bornait CHAQUE PARAGRAPHE a 75ch. Sur un conteneur de
     1245px, cela donnait 606px de texte et 639px de vide : exactement le defaut
     de largeur qu'elle pretendait eviter, une iteration plus tot. Le controle
     statique de L2 passait au vert -- il lit le CSS du conteneur, pas la boite
     rendue.
     Regle retenue : la mesure de lecture est portee par le CONTENEUR. Si les
     lignes doivent etre courtes, on retrecit la colonne (`.mesure`) et le texte
     la remplit ; on ne laisse jamais un paragraphe flotter dans une boite deux
     fois plus large que lui. Mesure au rendu : render_page.py, ratio >= 0,85. */
  --w:min(92vw,1680px);
  --mesure:88ch;
}

body{background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55}
.wrap{max-width:var(--w);margin:0 auto;padding:20px 20px 64px}
h1,h2,h3,h4{font-family:var(--head);line-height:1.22;margin:0 0 .45em}
h1{font-size:1.85rem;letter-spacing:-.01em}
h2{font-size:1.15rem;margin:0 0 .6em;display:flex;align-items:baseline;gap:8px}
h3{font-size:.82rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;
  margin:16px 0 8px}
p{margin:0 0 .7em}
/* Colonne de mesure explicite, a poser sur un CONTENEUR quand un bloc de
   prose merite des lignes courtes. Jamais sur le paragraphe lui-meme. */
.mesure{max-width:var(--mesure)}
a{color:var(--blue)}
code,.mono{font-family:var(--mono);font-size:.88em}
/* DEFAUT 6 -- le surlignage coupait « clics » en « clic|s ». La cause n'etait pas
   le decoupage du noeud de texte (texte + <mark> + texte, correct et inline) mais
   ce padding de 1px : il ecarte physiquement la partie surlignee du reste du mot.
   Regle L5 du socle : surlignage inline, sans espacement ni changement de boite. */
mark.find{background:var(--mark);color:inherit;padding:0;margin:0;border-radius:0;
  display:inline;font:inherit;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:0px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}

/* --- bandeau --- */
.band{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:16px 20px;margin-bottom:12px}
.band .eyebrow{font-family:var(--head);font-size:.7rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint);margin:0 0 4px}
.band h1{max-width:none}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:8px 16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}
.meta div{min-width:0}
.meta dt{font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint)}
.meta dd{margin:4px 0 0;font-weight:600;overflow-wrap:anywhere;font-size:.9rem}

/* --- barre collante : sommaire + recherche ---
   Les insets d'ecran (encoche, indicateur de home) sont pris en compte : une barre
   collee a un bord passe sinon SOUS le materiel sur telephone. Ils valent 0 partout
   ailleurs, la regle est donc sans effet hors mobile. */
.sticky{position:sticky;top:0;z-index:40;background:var(--bg);
  padding:calc(8px + env(safe-area-inset-top)) env(safe-area-inset-right) 8px
    env(safe-area-inset-left);
  margin-bottom:12px;border-bottom:1px solid var(--line)}
.sticky-in{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
.toc{flex:1 1 460px;min-width:0}
.toc details{background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r-sm)}
.toc summary{list-style:none;cursor:pointer;padding:8px 12px;display:flex;
  align-items:center;justify-content:space-between;gap:8px}
.toc summary::-webkit-details-marker{display:none}
.toc-h{font-family:var(--head);font-size:.72rem;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);min-width:0;overflow-wrap:anywhere}
.toc-x{flex:0 0 8px;width:8px;height:8px;border-right:1px solid var(--faint);
  border-bottom:1px solid var(--faint);transform:rotate(45deg)}
.toc details[open] .toc-x{transform:rotate(-135deg)}
.toc ol{list-style:none;margin:0;padding:0 8px 8px;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:4px}
.toc li{max-width:none}
.toc a{display:block;text-decoration:none;color:var(--ink);
  font-size:.78rem;padding:4px 8px;border-radius:var(--r-sm);border:1px solid transparent}
.toc a:hover{background:var(--blue-fill);border-color:var(--blue-line)}
.toc-hd{display:flex;align-items:center;gap:4px}
.toc-n{font-family:var(--mono);font-size:.68rem;color:var(--faint);min-width:1.1em}
.toc-t{font-weight:600}
.toc-c{font-family:var(--mono);font-size:.66rem;color:var(--faint);margin-left:auto}
.toc-d{display:block;font-size:.7rem;color:var(--muted);line-height:1.35;margin-top:4px}
.find{flex:0 1 320px;display:flex;flex-direction:column;gap:4px}
.find input{width:100%;padding:8px 8px;border:1px solid var(--line);
  border-radius:var(--r-sm);font:inherit;font-size:.85rem;background:var(--surface)}
.find-n{font-size:.7rem;color:var(--muted);min-height:1em;padding-left:4px}
.find-n.zero{color:var(--danger)}

/* --- chapitres --- */
section.ch{background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);padding:16px 20px;margin-bottom:12px;scroll-margin-top:90px}
section.ch>h2{border-left:1px solid var(--accent);padding-left:8px}
.ch-n{font-family:var(--mono);font-size:.8rem;color:var(--faint)}
.ch-st{color:var(--muted);font-size:.86rem;margin:-4px 0 12px}
/* L7 : ce que le chapitre apprend, avant toute donnee. L10 : comment lire une
   ligne. Deux blocs courts qui evitent au lecteur d'ouvrir pour savoir. */
.ch-apprend{color:var(--ink);font-size:.88rem;margin:0px 0 8px;padding:8px 12px;
  background:var(--blue-fill);border-left:1px solid var(--blue-line);
  border-radius:var(--r-sm)}
.exemple-lecture{color:var(--muted);font-size:.82rem;margin:0 0 8px;padding:8px 12px;
  background:var(--bg);border:1px dashed var(--line);border-radius:var(--r-sm)}
.ch-apprend b,.exemple-lecture b{font-family:var(--head);color:var(--ink)}

/* --- baremes : un score sans bareme n'informe pas (L3) --- */
details.baremes{margin:12px 0 0}
details.baremes>summary{list-style:none;cursor:pointer;font-family:var(--head);
  font-size:.76rem;color:var(--accent);display:inline-flex;align-items:center;gap:8px;
  padding:4px 12px;border:1px solid var(--blue-line);border-radius:var(--r-sm);
  background:var(--blue-fill)}
details.baremes>summary::-webkit-details-marker{display:none}
details.baremes>summary::before{content:"+";font-family:var(--mono);font-weight:700}
details.baremes[open]>summary::before{content:"−"}
.baremes-c{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:8px;margin-top:8px}
.bareme{border:1px solid var(--line);border-radius:var(--r-sm);padding:8px 12px;
  background:var(--surface);font-size:.8rem;break-inside:avoid}
.bareme>b{font-family:var(--head);display:block;margin-bottom:4px}
.bareme-l{margin:0;padding-left:1.1em;color:var(--muted)}
.bareme-l li{max-width:none;margin-bottom:4px}
.bareme.large{grid-column:1/-1}
.bareme.large .bareme-l{list-style:none;padding-left:0}
.bareme-l b{font-family:var(--mono);color:var(--ink)}

/* --- verdict en langage courant, en tete de fiche --- */
.clair{background:var(--blue-fill);border-left:1px solid var(--accent);
  border-radius:var(--r-sm);padding:8px 12px;margin:0 0 8px}
.clair-l{margin:0 0 .4em;font-size:.88rem;color:var(--ink)}
.clair-l:last-child{margin:0}
.clair-l>b{font-family:var(--head);font-size:.68rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--accent)}

/* --- jargon defini au premier usage, et references d'action nommees --- */
.glose{border-bottom:1px dotted var(--accent)}
.glose-d{color:var(--muted);font-style:italic}
.ref-a{font-weight:500}

/* --- ligne de lecture d'un releve mis en table (L12) --- */
.lecture{font-size:.8rem;color:var(--muted);margin:.5em 0 .3em;font-style:italic}

/* --- pied de bloc : ce qui ne merite pas un depliant (L9c) --- */
.meta-pied{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line)}
.meta-pied .champ{font-size:.74rem;color:var(--muted);margin:0 0 .25em}
.meta-pied .champ>b{font-size:.64rem}
.meta-id{font-family:var(--mono);color:var(--faint)}

.jeton{display:inline-block;max-width:100%;font-family:var(--mono);font-size:.9em;
  border-bottom:1px dotted var(--faint);overflow-wrap:anywhere}
/* La definition prend sa PROPRE ligne : le jeton se replie sur plusieurs lignes et
   sa boite couvrait alors celle de la definition posee a sa suite. Sur une ligne
   dediee, elle se lit mieux ET les boites cessent de se recouvrir (V4). */
.jeton-d{display:block;color:var(--muted);font-size:.95em}

/* --- markdown rendu des fiches (TF-0046) --- */
.md-l{margin:4px 0;padding-left:1.1em}
table.mini{width:100%;margin:4px 0;font-size:.78rem;border:1px solid var(--line);
  border-radius:var(--r-sm);table-layout:auto}
table.mini th{background:var(--bg);font-size:.66rem}
table.mini th,table.mini td{padding:4px 8px}
details.annexe>summary{list-style:none;cursor:pointer;font-family:var(--head);
  font-size:.78rem;color:var(--accent);display:inline-flex;align-items:center;gap:8px;
  padding:4px 12px;border:1px solid var(--blue-line);border-radius:var(--r-sm);
  background:var(--blue-fill)}
details.annexe>summary::-webkit-details-marker{display:none}
details.annexe>summary::before{content:"+";font-family:var(--mono);font-weight:700}
details.annexe[open]>summary::before{content:"−"}
.annexe-c{margin-top:12px}

/* --- niveaux de preuve --- */
.pv{display:inline-flex;align-items:center;gap:4px;font-family:var(--mono);
  font-size:.66rem;font-weight:700;padding:0 4px;border-radius:var(--r-sm);
  vertical-align:baseline;white-space:nowrap}
.pv-c{padding:0 4px}
.pv-g{font-size:.8em;line-height:1}
.pv-t1{color:var(--green);background:var(--green-fill);border:2px solid var(--green)}
.pv-t2{color:var(--teal);background:var(--teal-fill);border:1px solid var(--teal)}
.pv-t3{color:var(--amber);background:var(--amber-fill);border:1px dashed var(--amber)}
.pv-t4{color:var(--danger);background:var(--danger-fill);border:1px dotted var(--danger)}
.pv-nm{color:var(--faint);background:var(--surface);border:1px dashed var(--faint);
  font-style:italic}
.pv-legend{list-style:none;padding:0;margin:8px 0 0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:4px 16px}
.pv-legend li{font-size:.8rem;color:var(--muted);max-width:none}
.legende{background:var(--blue-fill);border:1px solid var(--blue-line);
  border-radius:var(--r-sm);padding:12px 16px;margin:16px 0 0}
.legende h3{margin:0 0 4px;color:var(--ink)}
.legende p{margin:0;font-size:.84rem;color:var(--muted)}

.repart{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 0;padding:0;list-style:none}
.repart li{border:1px solid var(--line);border-radius:var(--r-sm);padding:4px 8px;
  font-size:.76rem;background:var(--bg);max-width:none}
.repart b{font-family:var(--mono)}

/* --- cartes --- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:12px 16px;break-inside:avoid}
.card h3{margin:0 0 4px}
.card p{max-width:none}
/* `.chiffre` : le chiffre nu d'une carte. Il s'appelait `.kpi` — nom repris depuis
   par le composant complet du referentiel de restitution (valeur + definition +
   repere), qui n'est PAS la meme chose. Deux composants sous un meme nom rendaient
   l'oracle RL-3 rouge sur des cartes qui ne pretendaient rien de tel. */
.chiffre{font-family:var(--head);font-size:1.4rem;font-weight:700;line-height:1.1;margin:0}
.chiffre small{display:block;font-size:.7rem;font-weight:400;color:var(--faint);
  text-transform:none;letter-spacing:0;margin-top:4px;line-height:1.4}

/* --- synthese --- */
.verdict{background:var(--blue-fill);border:1px solid var(--blue-line);
  border-left:1px solid var(--accent);border-radius:var(--r-sm);padding:12px 16px;
  margin:0 0 16px}
.verdict p{margin:0 0 .4em}
.verdict p:last-child{margin:0}
.bl-n{display:block;font-weight:600;font-family:var(--head);margin:4px 0 4px}
.bl-t p{margin:0 0 .5em}
.bl-t p:last-child{margin:0 0 .6em}
.bl-c{font-size:.8rem;color:var(--muted)}
.top3{list-style:none;padding:0;margin:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px}
.top3 li{border:1px solid var(--line);border-left:1px solid var(--accent);
  border-radius:var(--r-sm);padding:8px 12px;background:var(--bg);max-width:none}
.top3 .t{font-weight:600;font-size:.88rem;display:block;margin-bottom:4px}
.top3 .m{font-size:.72rem;color:var(--muted);font-family:var(--mono);
  display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}

/* --- constats --- */
.constats{list-style:none;padding:0;margin:0}
.constats>li{border:1px solid var(--line);border-left:1px solid var(--line);
  border-radius:var(--r-sm);padding:8px 12px;margin-bottom:8px;break-inside:avoid;
  max-width:none}
.constats>li.fort{border-left-color:var(--green)}
.constats>li.faible{border-left-color:var(--danger)}
.constats .t{font-weight:600;margin:0 0 4px;display:flex;gap:8px;align-items:baseline;
  flex-wrap:wrap}
/* DEFAUT 4 : « L'existant » etait verbeux et sans suite. Chaque constat porte
   desormais sa chaine complete -- ce qu'on observe, ce que ca coute, ce qu'on fait,
   ce qu'on en attend -- sur quatre lignes etiquetees. */
.chaine{display:grid;gap:4px;margin:8px 0 0;font-size:.82rem}
.chaine>div{display:grid;grid-template-columns:minmax(72px,10%) minmax(0,1fr);gap:8px}
.chaine dt,.chaine .et{font-family:var(--head);font-size:.64rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--faint);padding-top:4px}
.chaine .va{color:var(--ink);min-width:0}
.chaine .vide{color:var(--faint);font-style:italic}
.trace{font-size:.68rem;color:var(--faint);font-family:var(--mono)}

/* --- stratification --- */
.st{min-width:0}
.n1{font-weight:500}
details.n2{margin-top:4px}
details.n2>summary{list-style:none;cursor:pointer;font-size:.72rem;color:var(--accent);
  font-family:var(--head);letter-spacing:.02em;display:inline-flex;align-items:center;
  gap:4px;padding:4px 8px;border:1px solid var(--blue-line);border-radius:var(--r-sm);
  background:var(--blue-fill)}
details.n2>summary::-webkit-details-marker{display:none}
details.n2>summary::before{content:"+";font-family:var(--mono);font-weight:700}
details.n2[open]>summary::before{content:"−"}
/* Champs etiquetes : etiquette EN TETE DE LIGNE, jamais en colonne. La grille a
   deux colonnes precedente reservait 22 % de la largeur aux etiquettes (267px sur
   1215) et tassait le contenu dans le reste -- « un tiers d'informations
   supplementaires, aucun interet ». L2 au rendu ne l'attrapait pas : chaque colonne
   remplissait bien SA case. L'angle mort etait la grille elle-meme. */
.n2-c{margin:8px 0 4px}
.champ{margin:0 0 .5em;font-size:.82rem;color:var(--ink);overflow-wrap:anywhere}
.champ:last-child{margin:0}
.champ>b{font-family:var(--head);font-size:.7rem;text-transform:uppercase;
  letter-spacing:.04em;color:var(--faint);font-weight:700}
.champ p{margin:0 0 .4em;display:inline}
.champ p+p{display:block;margin-top:.4em}
.champ .md-l{margin:.2em 0 .4em;display:block}
.champ table.mini{margin-top:.4em}
.chaine .va p{margin:0 0 .4em;max-width:none}
.chaine .va p:last-child{margin:0}
.chaine .va .md-l{margin:.2em 0 .4em}
/* --muted et non --faint : sur le fond bleu du summary, --faint rend 4,32:1,
   sous le seuil WCAG AA de 4,5:1 a cette taille. Mesure V2. */
.n2-s{color:var(--muted);font-family:var(--mono);font-size:.92em;margin-left:4px}

/* --- barre d'outils de tableau --- */
.tb{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin:0 0 8px;
  padding:8px 8px;background:var(--bg);border:1px solid var(--line);
  border-radius:var(--r-sm)}
.tb input[type=search],.tb select{padding:4px 8px;border:1px solid var(--line);
  border-radius:var(--r-sm);font:inherit;font-size:.8rem;background:var(--surface)}
.tb-q input{min-width:190px}
.tb-g{font-size:.76rem;color:var(--muted);display:flex;align-items:center;gap:4px}
.tb-aide{font-size:.68rem;color:var(--faint);margin-left:auto}
.tf-count{font-size:.72rem;color:var(--muted);font-family:var(--mono)}
.tf-count.zero{color:var(--danger)}

/* --- tableaux --- */
.tw{border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.83rem;
  background:var(--surface)}
th,td{text-align:left;padding:8px 8px;border-bottom:1px solid var(--line);
  vertical-align:top;overflow-wrap:break-word}
td .mono{overflow-wrap:anywhere}
td p{max-width:none}
thead th{position:relative;background:var(--bg);font-family:var(--head);
  font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
thead th[data-tri]{cursor:pointer;user-select:none}
thead th[data-tri]:hover{color:var(--accent)}
thead th[data-tri]::after{content:"↕";font-size:.85em;opacity:.35;margin-left:4px}
thead th[data-sens="1"]::after{content:"↑";opacity:1;color:var(--accent)}
thead th[data-sens="-1"]::after{content:"↓";opacity:1;color:var(--accent)}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--bg)}
/* Etiquette de groupe posee sur la 1re cellule du 1er element de chaque groupe :
   inserer une <tr> casserait le composant de filtres, qui itere les rows. */
td[data-grp]::before{content:attr(data-grp);display:block;margin:4px 0 8px;
  font-family:var(--head);font-size:.68rem;text-transform:uppercase;
  letter-spacing:.06em;color:var(--accent);border-top:2px solid var(--blue-line);
  padding-top:4px}
.num{font-family:var(--mono);white-space:nowrap}
.sc{font-family:var(--mono);letter-spacing:-1px;white-space:nowrap}
.sc-na{color:var(--faint);letter-spacing:0}

/* --- filtres du socle : affordance rendue visible, sans forker le composant --- */
.tf-btn{border:1px solid var(--line);background:var(--surface);cursor:pointer;
  font:inherit;font-family:var(--head);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);padding:4px 4px;border-radius:4px;
  margin-left:4px;white-space:nowrap}
.tf-btn::after{content:" filtrer"}
.tf-btn:hover{border-color:var(--accent);color:var(--accent)}
.tf-btn[aria-expanded="true"],.tf-btn.tf-on{color:var(--surface);
  background:var(--accent);border-color:var(--accent)}
.tf-panel{position:absolute;z-index:30;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r-sm);padding:8px;
  box-shadow:0 6px 20px rgba(15,23,42,.12);min-width:190px}
.tf-panel[hidden]{display:none}
.tf-opts{max-height:220px;overflow-y:auto;font-size:.78rem;text-transform:none;
  letter-spacing:0}
.tf-opts label{display:block;padding:4px 0;font-weight:400;color:var(--ink)}
.tf-panel input[type=search]{width:100%;margin-bottom:8px;padding:4px 8px;
  border:1px solid var(--line);border-radius:var(--r-sm);font:inherit;font-size:.78rem}

/* --- matrice gain x effort --- */
.mx{display:grid;gap:4px;margin-top:8px;font-size:.7rem}
.mx .axl{font-family:var(--head);font-size:.64rem;text-transform:uppercase;
  letter-spacing:.05em;color:var(--faint);display:flex;align-items:center;
  justify-content:center;padding:4px;text-align:center}
.mx .cell{background:var(--bg);border:1px solid var(--line);border-radius:var(--r-sm);
  min-height:44px;padding:4px;display:flex;flex-direction:column;gap:4px}
.mx .cell.hot{background:var(--green-fill);border-color:var(--green-line)}
.mx .cell.cold{background:var(--danger-fill);border-color:var(--danger-line)}
.mx .chip{display:block;width:100%;min-width:0;max-width:100%;text-align:left;background:var(--surface);
  border:1px solid var(--line);border-radius:4px;padding:4px 4px;font:inherit;
  font-size:.66rem;cursor:pointer;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;color:var(--ink)}
.mx .chip:hover{border-color:var(--accent);color:var(--accent)}
.mx .chip b{font-family:var(--mono);font-size:.9em;color:var(--faint);margin-right:4px}
.axis-y{writing-mode:vertical-rl;transform:rotate(180deg)}

/* --- quadrants : compteurs ; la liste vit dans la table --- */
.quads{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:8px}
.quad{border:1px solid var(--line);border-radius:var(--r);padding:12px 16px;
  background:var(--card);break-inside:avoid}
.quad h3{margin:0 0 4px;color:var(--ink)}
.quad .q-n{font-family:var(--head);font-size:1.5rem;font-weight:700;line-height:1}
.quad .q-d{font-size:.72rem;color:var(--muted);margin:4px 0 8px}
.quad .q-a{font-size:.74rem;color:var(--faint)}
.quad button{margin-top:8px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r-sm);padding:4px 8px;font:inherit;font-size:.72rem;
  cursor:pointer;color:var(--accent)}
.quad button:hover{border-color:var(--accent)}
.warn{background:var(--amber-fill);border:1px solid var(--amber-line);
  border-left:1px solid var(--amber);border-radius:var(--r-sm);padding:12px 16px;
  margin-top:12px;font-size:.85rem}
.warn p{margin:0 0 8px}
.warn p:last-child{margin:0}
.warn-t{font-family:var(--head);font-weight:700;color:var(--amber)}

/* --- absence declaree --- */
.absence{background:var(--bg);border:1px dashed var(--faint);border-radius:var(--r-sm);
  padding:12px 16px;margin:8px 0}
.absence .abs-t{font-weight:600;margin:0 0 4px;display:flex;align-items:center;gap:8px}
.absence p{font-size:.85rem;color:var(--muted);margin:0 0 4px}
.absence .abs-c,.absence .abs-r{color:var(--ink)}
.absence .abs-r{margin:0}

footer.doc{margin-top:20px;padding-top:12px;border-top:1px solid var(--line);
  font-size:.76rem;color:var(--faint)}
.conf{background:var(--danger-fill);border:1px solid var(--danger-line);
  border-radius:var(--r-sm);padding:8px 12px;font-size:.78rem;margin-top:12px}
.haut{position:fixed;right:calc(16px + env(safe-area-inset-right));
  bottom:calc(16px + env(safe-area-inset-bottom));z-index:50;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r);padding:8px 12px;font:inherit;
  font-size:.74rem;cursor:pointer;color:var(--accent);
  box-shadow:0 3px 12px rgba(15,23,42,.10)}

/* ================= restitution lisible (REFERENTIEL-RESTITUTION.md) =========
   Le rapport s'organise en VUES naviguees, une question par vue. Les chapitres ne
   bougent pas : ils changent de conteneur. Rien n'est resume, rien ne disparait. */

nav.vues ol{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
/* 44 px : cible tactile minimale du socle mobile. */
nav.vues a{min-height:44px;display:flex;flex-direction:column;justify-content:center}
nav.vues a[aria-selected="true"]{background:var(--blue-fill);
  border-color:var(--blue-line);font-weight:600}
/* Sur le fond teinte de la vue courante, `--faint` tombe a 4,32:1 — sous le seuil
   AA de 4,5:1 mesure au rendu. Le numero passe donc au ton au-dessus. */
nav.vues a[aria-selected="true"] .toc-n{color:var(--muted)}

section.vue{display:none;scroll-margin-top:90px}
section.vue.active{display:block}
/* Une recherche globale porte sur TOUT le rapport : masquer les autres vues
   pendant qu'on cherche rendrait des occurrences comptees mais introuvables. */
.wrap.toutes-vues section.vue{display:block}
.objectif{color:var(--ink);font-size:.9rem;margin:0 0 12px;padding:8px 12px;
  background:var(--blue-fill);border-left:1px solid var(--accent);
  border-radius:var(--r-sm)}
.objectif b{font-family:var(--head)}

/* --- KPI complet (RL-3) : valeur, definition, repere de lecture, action --- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));
  gap:8px;margin:0 0 16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:12px 16px;display:flex;flex-direction:column;gap:8px;break-inside:avoid}
.k-label{font-family:var(--head);font-size:.66rem;text-transform:uppercase;
  letter-spacing:.06em;color:var(--faint)}
.k-valeur{font-family:var(--head);font-size:1.45rem;font-weight:700;line-height:1.15;
  overflow-wrap:anywhere}
.k-valeur small{font-size:.78rem;font-weight:400;color:var(--muted)}
.kpi-d{font-size:.8rem;color:var(--muted)}
.k-repere{font-size:.78rem;color:var(--ink);background:var(--blue-fill);
  border-radius:var(--r-sm);padding:8px 8px}
.k-action{font-size:.78rem;margin-top:auto}

/* --- graphiques (RL-4) : la question est le titre, jamais l'inverse --- */
.graphes{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:8px;margin:0 0 16px}
figure.graphe{background:var(--card);border:1px solid var(--line);
  border-radius:var(--r);padding:12px 16px;margin:0;min-width:0;break-inside:avoid}
figure.graphe figcaption{font-family:var(--head);font-weight:700;font-size:.95rem;
  margin-bottom:4px}
.g-sous{font-size:.78rem;color:var(--muted);margin:0 0 8px}
.g-ligne{display:grid;grid-template-columns:96px 1fr 64px;gap:8px;
  align-items:center;margin-bottom:8px}
.g-nom{font-size:.78rem;color:var(--muted);text-align:right;min-width:0;
  overflow-wrap:anywhere}
/* La PISTE est le fond CSS du <svg> ; le <svg> ne porte qu'UNE forme, celle de la
   valeur. Deux rects superposes seraient un chevauchement au sens de V4. */
.g-piste{display:block;width:100%;height:16px;background:var(--line);
  border-radius:4px}
.g-val{font-size:.8rem;font-weight:700;font-family:var(--mono);white-space:nowrap;
  text-align:right}
.g-empile{display:block;width:100%;height:26px;border-radius:4px;background:var(--line)}
.g-legende{display:flex;flex-wrap:wrap;gap:8px 16px;margin:8px 0 0;padding:0;
  list-style:none;font-size:.78rem;color:var(--muted)}
.g-legende li{max-width:none}
.g-legende b{font-family:var(--mono);color:var(--ink)}
.g-puce{display:inline-block;width:10px;height:10px;border-radius:3px;
  margin-right:4px;vertical-align:-1px}

/* --- chemins d'entree par lecteur (RL-9) --- */
.chemins{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:8px;margin:0 0 16px;padding:0;list-style:none}
.chemin{font-size:.84rem;padding:8px 12px;background:var(--blue-fill);
  border:1px solid var(--blue-line);border-radius:var(--r-sm);max-width:none}
.chemin b{display:block;font-family:var(--head);margin-bottom:4px}

/* --- manifeste d'ecarts (RL-10) --- */
footer.ecarts{margin-top:16px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);padding:12px 20px;font-size:.8rem;color:var(--muted)}
footer.ecarts h2{font-size:.9rem;color:var(--ink);margin:0 0 8px;display:block}
footer.ecarts ul{margin:0;padding-left:1.1em}
footer.ecarts li{max-width:none;margin-bottom:4px}

@media (max-width:900px){
  .tw{border:0}
  table{display:block}
  thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  thead tr,thead th{display:block;width:1px !important;height:1px;overflow:hidden;
    padding:0;border:0;white-space:nowrap}
  tbody,tr,td{display:block;width:auto}
  tr{border:1px solid var(--line);border-radius:var(--r-sm);margin-bottom:8px;
    padding:4px 0;background:var(--surface)}
  td{display:flex;gap:8px;border:0;padding:4px 12px}
  td>.st,td>*{flex:1 1 0;min-width:0;max-width:100%}
  td::before{content:attr(data-l);flex:0 0 36%;color:var(--faint);
    font-family:var(--head);font-size:.66rem;text-transform:uppercase;
    letter-spacing:.04em;line-height:1.5}
  td[data-grp]::before{content:attr(data-grp);flex:none;display:block}
  td:empty{display:none}
}
@media (max-width:640px){
  .wrap{padding:12px 8px 40px}
  .chaine>div{grid-template-columns:1fr;gap:0}
  .chaine .et{padding-top:4px}
  h1{font-size:1.4rem}
  .mx{font-size:.6rem}
  .mx .cell{min-height:38px}
  .pv-legend{grid-template-columns:1fr}
  .toc ol{max-height:34vh;overflow-y:auto}
  .tb-aide{display:none}
  .g-ligne{grid-template-columns:74px 1fr 56px;gap:8px}
}
/* Le reflow des tables est deja actif a 900px ; il est REAFFIRME sous 768px, la
   borne du contrat mobile. Le dire a la borne du contrat rend la promesse
   verifiable au lieu d'etre deduite d'un breakpoint voisin. */
@media (max-width:768px){
  table,tbody,tr,td{display:block}
  thead tr{display:block}
}
/* Paysage sur telephone : la hauteur utile fond, la barre collante mangerait la
   moitie de l'ecran. Elle rend la main au contenu et redevient un simple bandeau. */
@media (orientation:landscape) and (max-height:520px){
  .sticky{position:static}
  .toc ol{max-height:40vh;overflow-y:auto}
}

@media print{
  body{background:var(--surface)}
  .wrap{max-width:none;padding:0}
  .sticky,.find,.tb,.haut,.quad button{display:none !important}
  /* Le papier n'a pas d'onglets : toutes les vues a plat, dans l'ordre. */
  section.vue{display:block !important}
  section.ch,.band,.legende,.card,.quad,.kpi,figure.graphe{break-inside:avoid;
    box-shadow:none}
  details{display:block}
  details.n2>summary,details.annexe>summary,details.baremes>summary{display:none}
  .baremes-c{display:block}
  .ch-apprend,.exemple-lecture{border:1px solid var(--line)}
  .tf-btn,.tf-panel{display:none !important}
  /* Le client imprime ce qu'il croit avoir : ni un filtre ni un tri ne doivent
     amputer le papier. */
  tr[data-tf-hidden]{display:table-row !important}
  tr[data-q-hidden="1"]{display:table-row !important}
  .tw{border:1px solid var(--line)}
  table{display:table;table-layout:auto}
  thead{position:static;width:auto;height:auto;overflow:visible;clip:auto}
  thead tr{display:table-row}
  thead th{display:table-cell;width:auto !important;height:auto;padding:4px 8px;
    white-space:normal}
  tbody{display:table-row-group}
  tr{display:table-row;border:0;margin:0;padding:0}
  td{display:table-cell;padding:4px 8px;border-bottom:1px solid var(--line)}
  td::before{content:none}
  td[data-grp]::before{content:attr(data-grp);display:block}
  td:empty{display:table-cell}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:.7em;color:var(--muted)}
}
"""

# --------------------------------------------------------------- JS maison

JS_OUTILS = r"""
/* Outils de tableau : tri, regroupement, filtre texte. Complete le composant de
   filtres du socle sans le remplacer -- et sans jamais inserer de <tr>, ce qui
   casserait son iteration des lignes. */
(function (root) {
  function corps(t) { var b = t.tBodies && t.tBodies[0]; return b ? Array.prototype.slice.call(b.rows) : []; }
  function val(tr, i) {
    var td = tr.cells[i]; if (!td) return '';
    var d = td.getAttribute('data-v');
    return d !== null ? d : (td.textContent || '').trim();
  }
  function nombre(s) { var m = String(s).replace(',', '.').match(/-?\d+(?:\.\d+)?/); return m ? parseFloat(m[0]) : NaN; }
  function sansAccent(s) {
    return (s || '').toLowerCase()
      .replace(/[àâäá]/g, 'a').replace(/[éèêë]/g, 'e')
      .replace(/[îïí]/g, 'i').replace(/[ôöó]/g, 'o')
      .replace(/[ùûüú]/g, 'u').replace(/ç/g, 'c');
  }

  var etats = {};

  function appliquer(t) {
    var e = etats[t.id], rows = corps(t), tb = t.tBodies[0];
    var ths = t.tHead ? Array.prototype.slice.call(t.tHead.rows[0].cells) : [];

    rows.sort(function (a, b) {
      if (e.groupe !== null) {
        var ga = val(a, e.groupe), gb = val(b, e.groupe);
        if (ga !== gb) return ga.localeCompare(gb, 'fr', { numeric: true });
      }
      if (e.tri === null) return 0;
      var typ = ths[e.tri] ? (ths[e.tri].getAttribute('data-tri') || 'txt') : 'txt';
      var x = val(a, e.tri), y = val(b, e.tri);
      if (typ === 'num') {
        var nx = nombre(x), ny = nombre(y);
        if (isNaN(nx) && isNaN(ny)) return 0;
        if (isNaN(nx)) return 1;
        if (isNaN(ny)) return -1;
        return (nx - ny) * e.sens;
      }
      return x.localeCompare(y, 'fr', { numeric: true }) * e.sens;
    });
    rows.forEach(function (r) { tb.appendChild(r); });

    ths.forEach(function (th, i) {
      if (i === e.tri) th.setAttribute('data-sens', String(e.sens));
      else th.removeAttribute('data-sens');
    });

    rows.forEach(function (r) { if (r.cells[0]) r.cells[0].removeAttribute('data-grp'); });
    if (e.groupe !== null) {
      var comptes = {};
      rows.forEach(function (r) { var v = val(r, e.groupe) || '—'; comptes[v] = (comptes[v] || 0) + 1; });
      var prec = null;
      rows.forEach(function (r) {
        var v = val(r, e.groupe) || '—';
        if (v !== prec && r.cells[0]) { r.cells[0].setAttribute('data-grp', v + '  (' + comptes[v] + ')'); prec = v; }
      });
    }
    filtrerTexte(t);
  }

  function filtrerTexte(t) {
    var e = etats[t.id], q = sansAccent(e.q), rows = corps(t), visibles = 0;
    rows.forEach(function (tr) {
      var ok = !q || sansAccent(tr.textContent).indexOf(q) !== -1;
      if (!ok) { tr.setAttribute('data-q-hidden', '1'); tr.style.display = 'none'; }
      else {
        tr.removeAttribute('data-q-hidden');
        if (!tr.hasAttribute('data-tf-hidden')) { tr.style.display = ''; visibles++; }
      }
    });
    var c = document.querySelector('[data-tf-count-for="' + t.id + '"]');
    if (!c) return;
    if (q) {
      c.textContent = visibles + ' / ' + rows.length + ' ligne' + (visibles > 1 ? 's' : '');
      c.classList.toggle('zero', visibles === 0);
    } else { c.textContent = ''; c.classList.remove('zero'); }
  }

  function init(t) {
    if (!t || !t.id || etats[t.id]) return;
    var d = (t.getAttribute('data-tri-defaut') || '').split(',');
    etats[t.id] = {
      tri: d[0] ? parseInt(d[0], 10) : null,
      sens: d[1] ? parseInt(d[1], 10) : -1,
      groupe: null, q: ''
    };
    if (t.tHead) {
      Array.prototype.forEach.call(t.tHead.rows[0].cells, function (th, i) {
        if (!th.getAttribute('data-tri')) return;
        th.setAttribute('tabindex', '0');
        th.setAttribute('role', 'button');
        function bascule() {
          var e = etats[t.id];
          if (e.tri === i) e.sens = -e.sens;
          else { e.tri = i; e.sens = th.getAttribute('data-tri') === 'num' ? -1 : 1; }
          appliquer(t);
        }
        th.addEventListener('click', function (ev) {
          if (ev.target.closest && ev.target.closest('.tf-btn,.tf-panel')) return;
          bascule();
        });
        th.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); bascule(); }
        });
      });
    }
    var sel = document.querySelector('[data-groupe-for="' + t.id + '"]');
    if (sel) sel.addEventListener('change', function () {
      etats[t.id].groupe = sel.value === '' ? null : parseInt(sel.value, 10);
      appliquer(t);
    });
    var q = document.querySelector('[data-q-for="' + t.id + '"]');
    if (q) q.addEventListener('input', function () { etats[t.id].q = q.value; filtrerTexte(t); });
    appliquer(t);
  }

  /* Filtre la table depuis l'exterieur (pastille de matrice, bouton de quadrant) :
     la vue devient un controle de la table, plus un doublon illisible. */
  function cibler(idTable, texte) {
    var t = document.getElementById(idTable);
    var q = document.querySelector('[data-q-for="' + idTable + '"]');
    if (!t || !q || !etats[t.id]) return;
    q.value = texte; etats[t.id].q = texte; filtrerTexte(t);
    t.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function initAll(racine) {
    Array.prototype.forEach.call((racine || document).querySelectorAll('table[id]'), init);
  }

  root.DigitAITableTools = { init: init, initAll: initAll, cibler: cibler };
})(window);

/* Recherche globale : on deplie les <mark> precedents au lieu de reecrire
   innerHTML -- le reset du composant du socle detruirait les ecouteurs des filtres
   et du tri. On reutilise sa regex et son surligneur. */
(function () {
  var input = document.getElementById('q'), cpt = document.getElementById('qn');
  var zone = document.querySelector('.wrap');
  if (!input || !zone || !window.DigitAIFindInPage) return;
  function nettoyer() {
    Array.prototype.forEach.call(zone.querySelectorAll('mark.find'), function (m) {
      var p = m.parentNode; if (!p) return;
      p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
    });
  }
  input.addEventListener('input', function () {
    nettoyer();
    var re = window.DigitAIFindInPage.buildRegex(input.value);
    if (!re) { cpt.textContent = ''; cpt.classList.remove('zero'); return; }
    var n = window.DigitAIFindInPage.highlight(zone, re);
    cpt.textContent = n === 0 ? 'Aucune occurrence' : n + ' occurrence' + (n > 1 ? 's' : '');
    cpt.classList.toggle('zero', n === 0);
  });
})();

/* Vues : routeur a ancres. Toute ancre interne qui pointe DANS une vue masquee
   active cette vue avant d'y defiler -- sans quoi la moitie des renvois du rapport
   (« voir le chapitre Couverture ») seraient des affordances mortes. */
(function () {
  var vues = Array.prototype.slice.call(document.querySelectorAll('section.vue'));
  if (!vues.length) return;
  var onglets = Array.prototype.slice.call(document.querySelectorAll('nav.vues a[data-vue]'));

  function vueDe(el) {
    while (el && el !== document.body) {
      if (el.classList && el.classList.contains('vue')) return el;
      el = el.parentNode;
    }
    return null;
  }

  function montre(id, cible) {
    vues.forEach(function (s) { s.classList.toggle('active', s.id === id); });
    onglets.forEach(function (a) {
      a.setAttribute('aria-selected', String(a.getAttribute('data-vue') === id));
    });
    if (cible && cible.id !== id) cible.scrollIntoView({ block: 'start' });
    else window.scrollTo({ top: 0 });
  }

  document.addEventListener('click', function (ev) {
    var a = ev.target && ev.target.closest ? ev.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (href.length < 2) return;
    var cible = document.getElementById(decodeURIComponent(href.slice(1)));
    if (!cible) return;
    var v = vueDe(cible);
    if (!v) return;
    ev.preventDefault();
    if (history.replaceState) history.replaceState(null, '', href);
    montre(v.id, cible);
  });

  /* Un lien partage pointe une ancre precise : on ouvre la vue qui la contient. */
  if (location.hash.length > 1) {
    var dep = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    var v0 = dep ? vueDe(dep) : null;
    if (v0) montre(v0.id, dep);
  }

  /* La recherche globale porte sur TOUT le rapport : pendant qu'on cherche, les
     vues s'ouvrent toutes, sinon le compteur annonce des occurrences invisibles. */
  var champ = document.getElementById('q'), zone = document.querySelector('.wrap');
  if (champ && zone) {
    champ.addEventListener('input', function () {
      zone.classList.toggle('toutes-vues', champ.value.trim().length > 0);
    });
  }
})();

/* Sommaire : chapitre courant surligne. Inerte sur la navigation de vues, qui
   marque la vue courante par aria-selected et non par un fond inline. */
(function () {
  var liens = Array.prototype.slice.call(document.querySelectorAll('.toc:not(.vues) a'));
  if (!liens.length || !('IntersectionObserver' in window)) return;
  var secs = liens.map(function (a) { return document.querySelector(a.getAttribute('href')); });
  var io = new IntersectionObserver(function (ents) {
    ents.forEach(function (e) {
      if (!e.isIntersecting) return;
      var i = secs.indexOf(e.target);
      liens.forEach(function (a, k) { a.style.background = k === i ? 'var(--blue-fill)' : ''; });
    });
  }, { rootMargin: '-80px 0px -70% 0px' });
  secs.forEach(function (s) { if (s) io.observe(s); });
})();
"""


def page(titre: str, blocs: list[str], pied: str, restitution: str = "") -> str:
    """Squelette complet. Un seul <h1>, lang fr, viewport, tout inline.

    `restitution` declare la famille du livrable au sens du referentiel de
    restitution (`rapport`, `suivi`, `registre`). Sans elle, l'oracle rend un SKIP
    motive : le perimetre est declaratif, jamais devine.
    """
    filtres, _ = source_filtres()
    recherche = _asset("find-in-page.js")
    init = ("\nDigitAITableFilters.initAll(document);" if filtres else "") + (
        "\nDigitAITableTools.initAll(document);"
    )
    js = filtres + "\n" + recherche + "\n" + JS_OUTILS + init
    # `find-in-page.js` documente son cablage en commentaire, avec un `</script>`
    # dedans. Inline tel quel, il TERMINE l'element script : tout ce qui suit est
    # parse comme du HTML et ne s'execute jamais. Le rendu paraissait correct et
    # aucune interaction ne marchait.
    js = js.replace("</script", "<\\/script")
    return sans_pictogrammes(
        "<!doctype html>\n"
        '<html lang="fr"><head><meta charset="UTF-8">\n'
        # `viewport-fit=cover` : sans lui les env(safe-area-inset-*) de la feuille
        # de style valent 0 et la barre collante repasse sous l'encoche.
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
        'viewport-fit=cover">\n'
        f"<title>{esc(titre)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n<body"
        + (f' data-restitution="{esc(restitution)}"' if restitution else "")
        + ">\n"
        f'<main class="wrap">\n{"".join(blocs)}\n{pied}\n</main>\n'
        '<button class="haut" onclick="window.scrollTo({top:0,behavior:\'smooth\'})">'
        "↑ Haut</button>\n"
        f"<script>{js}</script>\n"
        "</body></html>\n"
    )
