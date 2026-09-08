# Données de recherche — doctrine multilingue et cadence

**À charger pour instruire, en contexte multilingue ou multi-marché, les nœuds 3
(Potentiel Business), 6 (Volume Réel), 9 (Difficulté SEO), 17 (Longue Traîne), 20 (SERP
Faibles), 21 (Adéquation Lexicale par Marché), 39/41/43 (branche Autorité) et 51
(Fraîcheur).** Absent de ce périmètre, ce document n'a rien à ajouter à l'audit.

Provenance (TF-0792, décision humaine du 08/09/2026) : ce corpus généralise, pour
`forge-seo-geo`, l'expertise capitalisée par `references/SEO-RECHERCHE.md` v1.0.0 du
pilot `digit-ai-factory` (chantier « données de recherche » du produit pionnier,
candidature TF-0741, décisions D-1 à D-3 du 01/09/2026). Le pilot garde la version
transverse, réutilisable par toute forge ; cette version-ci est **adaptée à la grille**
de `forge-seo-geo` — vocabulaire `SD`/`EX`/`PY`/`NM`, étiquettes de preuve `[T1]`-`[T4]`,
garde-fous du `SKILL.md` — et n'a pas vocation à rester synchronisée mot pour mot avec
l'original : une évolution de l'un ne réécrit pas silencieusement l'autre.

## 1. Les six familles, rattachées à la grille

Nommer d'abord la famille de données mobilisée évite d'acheter un outil avant d'avoir
nommé le besoin. Correspondance avec les nœuds de `grille-noeuds.md` :

| Famille | Ce qu'elle mesure | Nœuds instruits | Statut |
|---|---|---|---|
| **F1 · Performance propriétaire** (GSC, Bing Webmaster Tools) | ce que le moteur a vu du site — impressions, clics, CTR, position, par requête | 40 (Trafic GSC), 44 (CTR SERP), 70-72 (Impressions/Clics/Positions) | `EX` — **`NM` sans export, sans exception** (garde-fou 2) |
| **F2 · Volumes de recherche** | demande mensuelle moyenne par pays et langue, saisonnalité, prix publicitaire | 6 (Volume Réel) | `PY` — dégradation `EX` par les impressions GSC comme **plancher observé**, jamais comme volume de marché |
| **F3 · SERP et positions** | la page de résultats relevée, et qui occupe les places par marché | 4 (Concurrence SERP), 20 (SERP Faibles), 72 (Positions) | `SD` pour la SERP approximée (`[T3]`) — `EX` pour la position exacte |
| **F4 · Idées de mots-clés et longue traîne** | d'une amorce vers les requêtes voisines réellement tapées, par langue | 17 (Longue Traîne), 21 (Adéquation Lexicale par Marché) | `SD` partiel — `EX` pour la distribution réelle des clics |
| **F5 · Liens entrants** | crédibilité vue des moteurs | 39 (Backlinks), 41 (Pertinence Thématique), 43 (Liens Déjà Visibles) | `PY` — dégradation `SD` : liens détectables par recherche web seulement |
| **F6 · Audit technique (hreflang)** | crawl, vitesse, et le balisage qui sert la bonne langue au bon marché | 21 (les quatre niveaux : title/meta, H1, corps, hreflang/sitemap/canoniques), 31 (Canonical) | `SD` |

## 2. Doctrine de cadence — la cadence de mesure est la cadence de décision

**On remesure quand une décision neuve attend le chiffre, pas parce qu'un mois est
passé.** Applicable aux nœuds 6, 39-43 et 51 :

- **Nœud 6 (Volume Réel)** : moyenne lissée sur 12 mois glissants, historique mensuel
  embarqué à chaque relevé — les racheter souvent rachète le même nombre. Cadence utile :
  par saison du produit (avant chaque fenêtre de décision), plus un re-ratissage large
  annuel (§3).
- **Nœud 72 (Positions)** : bouge vite et répond aux actions du site — cadence courte
  (hebdomadaire) **seulement en zone pilotable**, entre les rangs 5 et 20. En dessous, un
  suivi mesure une grandeur sur laquelle personne ne peut agir — le déclarer plutôt que
  de le suivre en pure perte.
- **Nœud 40 / 70-72 (F1)** : relevé en continu — gratuit, et c'est la famille qui rend
  les verdicts (garde-fou 2 : jamais de déduction en son absence).
- **Nœud 51 (Fraîcheur)** : la moyenne lissée écrase l'événement ponctuel prévisible par
  un calendrier (temps fort sectoriel, date annoncée). Un calendrier événementiel par
  marché pilote la publication AVANT le pic ; la donnée de recherche vérifie ensuite que
  la demande s'est matérialisée. Complément `[T3]` : Google Trends — courbes relatives
  quasi temps réel par pays, utile pour repérer un frémissement et comparer deux
  formulations, **jamais** pour chiffrer un volume (c'est un indice, pas un volume).

## 3. Nœud 21 — découverte de mots-clés multilingue : explorer large, exploiter serré

Complément opérationnel à la méthode du nœud 21 (`referentiel/grille-noeuds.md`, branche
Mots Clés) :

- **Jamais de traduction littérale seule** : chaque langue a ses formulations natives
  qu'aucune traduction ne produit. Les candidats viennent de F1 (requêtes propres), F4
  (idées natives par marché amorcées par 2-3 germes traduits), F3 (requêtes des
  concurrents classés) et des attributs de l'offre elle-même.
- **Une langue sans pays de mesure ne se mesure pas** : « l'anglais transverse » n'existe
  pas pour un volume — l'ancrer sur ses pays sources réels, et le déclarer `[T2]`/`[T3]`
  avec le pays retenu à côté de la langue.
- **Première campagne large, puis resserrage** : mesurer jusqu'au plafond de facturation
  par marché la première fois (le plafond est un forfait, ratisser large ne coûte rien de
  plus), puis travailler un jeu resserré par langue — la capacité d'action éditoriale
  borne le jeu, pas la mesure. Re-ratisser une fois par an pour attraper les formulations
  neuves.
- Rappel du garde-fou du nœud 21 : **quatre niveaux cohérents entre eux** (title/meta, H1,
  corps et navigation, puis hreflang/sitemap/canoniques) et **zéro homographe trompeur non
  signalé** — le cas le plus coûteux et le moins visible d'une expansion multilingue mal
  conduite.

## 4. Nœud 3 — la doctrine CPC : l'intention prime le prix du clic

Le CPC est un prix d'enchère, pas une mesure de valeur pour le site audité : il monte
avec l'intention commerciale mais aussi avec la densité de concurrents. Ce qui prédit la
transformation, ce n'est pas le CPC mais **l'adéquation requête ↔ offre** — un clic bon
marché à fort volume sur une requête informationnelle produit des visites sans
conversion ; une requête transactionnelle spécifique convertit à tout prix de clic
raisonnable. L'arbitrage final (coût d'acquisition rapporté à la valeur d'une conversion)
**exige un suivi de conversion côté client** (nœuds 45-47, 73) — sans lui, toute promesse
de transformation reste `NM`, jamais approchée par une moyenne sectorielle (garde-fou 2 du
`SKILL.md` : « non mesurable » est une réponse valide, un chiffre inventé ne l'est jamais).

## 5. Nœuds 65-69 (Automatisation) — le pattern budgétaire en escalier

Utile pour dispatcher les actions issues d'un chantier de données de recherche entre les
quadrants du `scoring.md` : des **paliers cumulatifs conditionnés aux résultats mesurés**,
jamais un choix unique figé.

- Palier 0 : socle gratuit propriétaire (F1 des deux moteurs, fourchettes de volumes par
  impressions GSC, audit hreflang ponctuel — nœud 21).
- Palier 1 : achat à l'acte (API facturée à la requête) — sous mandat humain du client,
  dépôt minimal comme plafond de perte.
- Palier 2 : première suite par abonnement, quand le nœud 72 (Positions) devient
  pilotable.
- Palier 3 : suite complète + budget d'acquisition, quand des conversions attribuées au
  canal organique (nœud 73) le justifient en euros.

Chaque passage de palier porte un critère mesurable écrit d'avance et daté — c'est une
décision du client, jamais une recommandation chiffrée de tête (garde-fou 7 : aucune
projection présentée comme une prévision).

## 6. Ce que ce document ne couvre pas

Le schéma d'intégration côté produit du chantier d'origine (secrets sur le runner
d'intégration continue, déclenchement humain des appels payants, restitution dans la
console existante) relève du produit qui consomme ces données de recherche, pas du site
audité par `forge-seo-geo` : il reste décrit dans `references/SEO-RECHERCHE.md` §7 du
pilot, hors du périmètre de cette forge.
