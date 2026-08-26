# Grille des nœuds d'audit SEO

Instrumentation du schéma SEO source, étendue du SEO local. **17 branches, 89 nœuds, aucun omis.**

Les 16 premières branches (84 nœuds) instrumentent le schéma d'origine. La 17ᵉ, `Local`,
en est une **extension assumée** : le schéma source ne couvrait pas le SEO local, alors que
le cadrage propose `local` comme modèle d'acquisition. Voir « Portée par modèle » ci-dessous.

La colonne `branche` est portée par le titre de section (une section par branche) plutôt que répétée sur chaque ligne — les 8 champs requis sont tous présents.

## Légende des statuts

*Ce que chaque sigle engage : ce qu'on peut mesurer sans rien demander au client, ce qui dépend d'un export, et ce qui ne se mesure pas du tout. Un nœud dont le statut est mal lu produit soit une demande inutile au client, soit un verdict rendu sans la donnée qui le porte.*

| Code | Signification |
|---|---|
| `SD` | instrumenté sans dépendance externe (crawl, HTTP, HTML, recherche web) |
| `EX` | instrumenté **si export fourni** (GSC / GA / CRM) — sinon non mesurable |
| `PY` | instrumenté **si outil payant** (index de backlinks, volume de recherche) — dégradation possible, indiquée |
| `NM` | **non mesurable** — motif obligatoire, remonté dans `dette-instrumentation` |
| `RV` | **renvoi** — doublon du schéma source, la branche homonyme est autoritaire |
| `CA` | **cadrage** — entrée du run et cible de sortie, pas un nœud d'audit |

## Arbitrage des doublons du schéma source

Le schéma contient deux nœuds en collision avec une branche de même nom. **La branche est autoritaire ; la feuille homonyme est un renvoi et n'est jamais auditée deux fois.**

| Feuille en doublon | Renvoie vers | Décision |
|---|---|---|
| `Technique / Indexation` (nœud 29) | branche `Indexation` (nœuds 34-38) | auditer dans la branche `Indexation` uniquement |
| `Objectif / Autorité` (nœud 87) | branche `Autorité` (nœuds 39-43) | auditer dans la branche `Autorité` uniquement |

Les deux lignes restent présentes dans la grille : le compte est **89 = 89**.

## Routage des 17 branches par volet

*Où chaque branche s'audite, et sous quel volet. Le tableau se lit branche par branche dans l'ordre du parcours — de l'idée à l'objectif ; la colonne « volet » dit à quel moment du run la branche est instruite, et non son importance. Aucune branche n'y est exclue : les dix-sept y figurent, et une branche absente de ce tableau serait un défaut de ce document.*

| Branche | Volet | Justification |
|---|---|---|
| Idée | `STRATÉGIE` | qualifie un territoire à conquérir, pas un état constaté |
| Validation | `STRATÉGIE` | valide économiquement une cible avant d'y investir |
| Architecture | `TRANSVERSAL` | structure existante **et** structure cible |
| Mots Clés | `TRANSVERSAL` | couverture actuelle **et** requêtes à conquérir |
| Contenu | `TRANSVERSAL` | inventaire existant **et** plan éditorial |
| Technique | `ÉTAT` | purement constaté à l'instant du crawl |
| Indexation | `ÉTAT` | purement constaté |
| Autorité | `TRANSVERSAL` | profil actuel **et** plan d'acquisition |
| Signaux | `ÉTAT` | mesures comportementales du passé |
| Discover | `TRANSVERSAL` | performance passée **et** angles à produire |
| GEO | `TRANSVERSAL` | présence actuelle **et** construction d'entité |
| Local | `TRANSVERSAL` | présence cartographique actuelle **et** couverture de zone à construire |
| Automatisation | `TRANSVERSAL` | maturité outillage actuelle ; **alimente l'axe IA du dispatch R5** |
| Mesure | `TRANSVERSAL` | baseline **et** KPI cibles |
| Optimisation | `TRANSVERSAL` | dette sur l'existant **et** boucle d'amélioration à installer |
| Croissance | `STRATÉGIE` | extension de périmètre |
| Objectif | `CADRAGE` | entrée du run (objectif déclaré) et sortie (cible chiffrée) |

Répartition : `ÉTAT` 16 · `STRATÉGIE` 15 · `TRANSVERSAL` 53 · `CADRAGE` 5 = **89**.

## Portée par modèle d'acquisition

**Par défaut, un nœud s'applique à tous les modèles.** Seules les exceptions figurent
ci-dessous. Un nœud hors périmètre pour le modèle de l'étude est marqué
`hors-perimetre — modèle d'acquisition <m>` : c'est un **résultat**, pas une dette
d'instrumentation, et le rapport les sépare.

Restreindre est plus risqué qu'élargir : un nœud retiré à tort disparaît silencieusement de
l'audit. La liste est donc volontairement courte, et chaque restriction est justifiée.

| Nœuds | Modèles concernés | Justification |
|---|---|---|
| 60-64 (branche `Local`) | `local` | fiche d'établissement, NAP, annuaires et zones n'ont pas d'objet hors présence physique |
| 26 `Contenu Programmatique` | `e-commerce` · `media-affiliation` · `local` | la génération de pages à l'échelle suppose un catalogue, un corpus ou des zones |
| 49-53 (branche `Discover`) | `media-affiliation` · `e-commerce` | surface de découverte éditoriale ; marginale en B2B et SaaS |
| 74 `Revenu Par Page` | `e-commerce` · `media-affiliation` | le revenu s'attribue à une page quand la page vend ; ailleurs il s'attribue au lead |
| 87 `Ventes` | `e-commerce` | pour les autres modèles, la cible terminale est le lead (nœud 86) |

**Restriction la plus discutable** : `Discover`. Une marque e-commerce ou B2B forte peut y
apparaître. Elle est isolée sur une seule ligne pour être révisée sans toucher au reste.

---

## 1. Idée — volet STRATÉGIE

*Ce que le projet vise avant d'avoir un site : le marché, la demande, la promesse. Ces nœuds se répondent au cadrage, pas à la mesure.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 1 | Niche | STRATÉGIE | Le site couvre-t-il une niche identifiable et défendable, ou est-il dispersé ? | crawl du site | clustering thématique des URLs par segment d'URL et par H1 ; lecture des 3 pages les plus liées en interne | ≥ 70 % des pages rattachables à ≤ 3 thèmes cohérents | `SD` |
| 2 | Intention De Recherche | STRATÉGIE | Les pages cibles répondent-elles au **format** d'intention dominant de leur requête ? | SERP approximée + contenu de la page | pour 10 requêtes cibles du cadrage, relever le format des 5 premiers résultats (transactionnel / informationnel / comparatif / local) et le comparer au format de la page du site | mismatch de format sur ≤ 20 % des requêtes testées | `SD` — SERP approximée, preuves en `[T3]` |
| 3 | Potentiel Business | STRATÉGIE | La niche porte-t-elle une valeur transactionnelle réelle ? | CPC (outil payant) ; à défaut signaux monétaires SERP | comptage des annonces, blocs Shopping et comparateurs en SERP sur les requêtes cibles ; CPC moyen si outil disponible | à calibrer — pas de seuil universel, dépend du modèle d'acquisition | `PY` — dégradation `SD` : signaux SERP seuls, sans CPC |
| 4 | Concurrence SERP | STRATÉGIE | Quelle est la force des sites occupant le top 10 des requêtes cibles ? | SERP approximée + crawl léger des concurrents | pour 10 requêtes, relever les domaines présents et les classer : marque nationale / pure player spécialisé / média généraliste / concurrent direct / résultat faible (forum, page fine, hors-sujet) | ≥ 2 résultats classés « faibles » en top 10 = requête attaquable | `SD` |
| 5 | Opportunité Cachée | STRATÉGIE | Existe-t-il des requêtes à demande réelle mal servies par la SERP actuelle ? | GSC (requêtes en impressions sans clic, positions 11-30) + questions People-Also-Ask | croiser les requêtes GSC hors top 10 avec les questions suggérées en SERP ; retenir celles dont aucun résultat top 5 ne traite le sujet en page dédiée | ≥ 10 requêtes qualifiées pour ouvrir un chantier | `EX` — dégradation `SD` très partielle : PAA seuls, sans preuve de demande propre au site |

---

## 2. Validation — volet STRATÉGIE

*Si la demande existe vraiment, et à quelle échelle. C'est la branche qui dit si le reste du parcours a un objet.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 6 | Volume Réel | STRATÉGIE | Quel volume de recherche mensuel réel sur les requêtes cibles ? | outil de volume (Keyword Planner, Semrush, Ahrefs) ou impressions GSC comme proxy | relevé direct ; à défaut, impressions GSC sur 12 mois comme plancher observé (jamais comme volume de marché) | aucun — donnée de cadrage, pas de verdict | `PY` — ou `EX` via impressions GSC. **Jamais estimé de tête** |
| 7 | Coût Du Lead | STRATÉGIE | Combien coûte l'acquisition d'un lead sur ce marché ? | CRM + dépenses média du client | déclaratif client, à reprendre en `[T2]` | aucun — donnée de cadrage | `NM` — motif : exige CRM et données de dépense média, hors périmètre observable |
| 8 | Valeur Du Client | STRATÉGIE | Quelle valeur porte un client acquis (panier moyen, LTV, récurrence) ? | CRM ou e-commerce | déclaratif client, à reprendre en `[T2]`. Sans lui, aucun gain ne peut être exprimé en € | aucun — donnée de cadrage | `NM` — motif : exige CRM ou back-office e-commerce |
| 9 | Difficulté SEO | STRATÉGIE | Quelle difficulté à ranker sur les requêtes cibles ? | index de backlinks (autorité des top 10) ; à défaut proxy observable | proxy sans outil : nombre de marques fortes en top 10 + profondeur et ancienneté des pages classées + longueur/profondeur du contenu classé | à calibrer par marché ; produire un score relatif 1-5, jamais un score absolu emprunté à un outil absent | `PY` — dégradation `SD` : proxy structurel, à déclarer comme tel |
| 10 | Vitesse De Monétisation | STRATÉGIE | Combien de temps entre publication d'une page et premier revenu attribuable ? | GA + CRM + historique de publication | croiser date de publication, date de première conversion attribuée, et délai médian | aucun — donnée de calibrage des projections | `NM` — motif : exige GA **et** CRM ; devient `EX` si les deux sont fournis |

---

## 3. Architecture — volet TRANSVERSAL

*Comment le site est organisé pour être compris — silos, maillage, profondeur. Une architecture fausse rend tous les nœuds de contenu difficiles à corriger.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 11 | Silos | TRANSVERSAL | La structure d'URL et le maillage matérialisent-ils des silos thématiques ? | crawl | arbre d'URL + graphe de liens internes ; mesurer le taux de liens internes restant dans le même silo | ≥ 60 % des liens internes intra-silo | `SD` |
| 12 | Pages Money | TRANSVERSAL | Les pages à intention transactionnelle sont-elles identifiées, uniques et hautes dans l'arbre ? | crawl + cadrage (requêtes money) | pour chaque requête money du cadrage, identifier la page cible ; détecter les cas où deux pages visent la même requête | 1 page par requête money (0 cannibalisation) **et** profondeur ≤ 2 clics | `SD` |
| 13 | Pages Satellites | TRANSVERSAL | Des pages de soutien pointent-elles vers les pages money ? | crawl | compter les liens internes contextuels entrants vers chaque page money, en excluant menus et pieds de page | ≥ 3 satellites par page money, liens en corps de texte | `SD` |
| 14 | Maillage Interne | TRANSVERSAL | Le maillage concentre-t-il l'autorité interne sur les pages à valeur ? | crawl | compter les liens internes entrants par page (hors navigation) ; classer par décile | les pages money figurent dans le décile supérieur | `SD` |
| 15 | Profondeur De Clic | TRANSVERSAL | À quelle profondeur se trouvent les pages à valeur ? | crawl | parcours en largeur depuis l'accueil ; profondeur minimale par URL | 0 page money > 3 clics **et** ≥ 90 % des pages à valeur ≤ 4 clics | `SD` |

---

## 4. Mots Clés — volet TRANSVERSAL

*Ce que les gens tapent réellement, et dans quels mots le site leur répond. C'est ici que se juge l'écart entre le vocabulaire du site et celui de son marché — y compris par langue.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 16 | Money Keywords | TRANSVERSAL | Les requêtes à intention d'achat sont-elles couvertes par une page dédiée ? | cadrage + crawl (couverture) ; GSC (performance) | croiser la liste des requêtes money du cadrage avec les pages existantes | 100 % des requêtes money ont une page dédiée | `SD` pour la couverture — la performance exige `EX` |
| 17 | Longue Traîne | TRANSVERSAL | Quelle part du trafic organique vient de requêtes à faible volume ? | GSC (requêtes, clics) | distribution des clics par requête ; part des requêtes < 10 clics/mois | ≥ 40 % des clics issus de la traîne = base saine ; < 15 % = dépendance à quelques requêtes | `EX` — motif sinon : la distribution du trafic par requête n'est pas observable de l'extérieur |
| 18 | Questions Clients | TRANSVERSAL | Les questions réelles des utilisateurs sont-elles traitées sur le site ? | People-Also-Ask, forums et communautés du secteur, GSC | extraire 30 questions récurrentes ; vérifier pour chacune l'existence d'une réponse identifiable sur le site | ≥ 70 % des 30 questions traitées, réponse repérable sous un titre | `SD` |
| 19 | Requêtes Sous Exploitées | TRANSVERSAL | Quelles requêtes génèrent des impressions sans clic, ou stagnent en position 11-30 ? | GSC exclusivement | filtrer les requêtes à impressions élevées et CTR bas, et celles en position 11-30 avec volume | liste priorisée par (impressions × écart de CTR attendu) | `EX` — **`NM` sans GSC, sans exception** (garde-fou 2) |
| 20 | SERP Faibles | TRANSVERSAL | Quelles requêtes cibles ont une SERP attaquable ? | SERP approximée | scorer la faiblesse du top 10 : présence de forums, pages fines, résultats hors intention, absence de page dédiée chez les concurrents | ≥ 3 signaux de faiblesse sur le top 10 = requête prioritaire | `SD` |
| 21 | Adéquation Lexicale par Marché | TRANSVERSAL | Le vocabulaire SERVI dans chaque locale est-il celui que ce marché emploie réellement ? | catalogue de langue servi + glossaire du projet (`docs\projet\GLOSSAIRE.md`, R-53 du pilot) + complétions de recherche par marché ; Search Console par pays si export fourni | pour chaque locale servie, confronter le vocabulaire des QUATRE niveaux — title/meta, H1, corps et navigation, puis hreflang/sitemap/canoniques — aux termes réellement employés dans cette langue pour cette catégorie de produit ; signaler les HOMOGRAPHES TROMPEURS, cas le plus coûteux et le moins visible ; DÉCLARER les limites de la sonde — pas de volume, pas de géolocalisation fiable, le paramètre de langue d'une complétion fixe l'INTERFACE et non le pays du chercheur | pour chaque locale, le terme retenu est celui du marché, établi par AU MOINS DEUX sources de nature différente · zéro homographe trompeur non signalé · les quatre niveaux COHÉRENTS entre eux — corriger le title sans le corps crée une incohérence entre ce que la page promet et ce qu'elle contient | `SD` partiel — Search Console `EX` |

---

## 5. Contenu — volet TRANSVERSAL

*Ce que le site dit, à qui, et si cela répond à une intention identifiée. Un contenu juste sur une intention absente ne rapporte rien.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 22 | Pages Piliers | TRANSVERSAL | Chaque silo a-t-il une page pilier exhaustive et bien liée ? | crawl | pour chaque silo identifié au nœud 11, chercher la page la plus complète et la plus liée | 1 pilier par silo, couvrant le sujet de bout en bout, ≥ 5 liens sortants internes vers son silo | `SD` |
| 23 | Guides | TRANSVERSAL | L'intention informationnelle du parcours d'achat est-elle couverte ? | crawl + questions du nœud 18 | cartographier les contenus par étape du parcours (découverte / évaluation / décision) | aucune étape du parcours sans contenu | `SD` |
| 24 | Comparatifs | TRANSVERSAL | Les requêtes comparatives sont-elles couvertes (« vs », « alternatives », « meilleur ») ? | crawl + SERP | vérifier l'existence de pages comparatives ; relever qui occupe ces SERP | présence d'au moins une page par famille comparative pertinente | `SD` |
| 25 | FAQ | TRANSVERSAL | Les questions sont-elles traitées en format directement répondable ? | crawl (HTML) | échantillonner les blocs de questions ; mesurer la distance entre le titre-question et la réponse | réponse en ≤ 60 mots immédiatement sous le titre de la question | `SD` |
| 26 | Contenu Programmatique | TRANSVERSAL | Des gabarits génèrent-ils des pages à l'échelle, et sont-elles de qualité indexable ? | crawl | détecter les motifs d'URL répétés ; échantillonner 10 pages du même motif ; mesurer la part de contenu unique hors gabarit | ≥ 40 % de contenu unique par page **et** valeur propre pour l'utilisateur, sinon candidat au nœud 76 | `SD` |
| 27 | Contenu Pensé Pour Les LLM | TRANSVERSAL | Le contenu est-il citable par un moteur génératif ? | crawl (HTML brut) + vérification web datée | vérifier : réponse directe en tête de page, affirmations factuelles attribuables, structure de titres explicite, données chiffrées sourcées, contenu essentiel présent dans le HTML et non injecté en JS | ≥ 4 des 5 critères sur les pages à enjeu | `SD` — **garde-fou 4 : vérification web datée obligatoire, les critères de citabilité évoluent** |

---

## 6. Technique — volet ÉTAT

*Ce qui empêche une page d'être servie, chargée ou comprise. Ces nœuds mesurent un état à un instant : ils se rejouent, ils ne se raisonnent pas.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 28 | Crawl | ÉTAT | Le site est-il crawlable sans obstacle ? | `robots.txt`, codes HTTP, chaînes de redirection | vérifier les directives `robots.txt` contre les pages à valeur ; relever les codes HTTP et les chaînes de redirection sur l'échantillon | 0 blocage sur page à valeur · 0 chaîne de redirection > 2 sauts · 0 boucle | `SD` |
| 29 | Indexation | ÉTAT | *(doublon du schéma)* | — | **renvoi vers la branche `Indexation`, nœuds 34-38** | ne pas auditer ici | `RV` |
| 30 | Logs Serveur | ÉTAT | Comment Googlebot consomme-t-il réellement le budget de crawl ? | logs serveur ou CDN | analyse des hits Googlebot par type de page et par profondeur ; détection du crawl gaspillé | aucun — diagnostic descriptif | `NM` — motif : exige un accès aux logs serveur ou CDN. **Impact : budget de crawl réel, fréquence de passage et gaspillage restent invisibles** |
| 31 | Canonical | ÉTAT | Les canonicals sont-elles cohérentes et auto-référentes ? | crawl (HTML + en-têtes) | relever la canonical de chaque page de l'échantillon ; détecter les canonicals croisées, vers non-200, ou incohérentes avec le sitemap et les hreflang | 0 canonical vers une page non-200 · 0 canonical croisée non intentionnelle · cohérence avec hreflang | `SD` |
| 32 | Performance | ÉTAT | Les métriques d'expérience de page sont-elles dans le vert sur données de terrain ? | données de terrain publiques (CrUX / PageSpeed Insights) | relever les métriques de terrain sur les gabarits principaux, mobile en priorité | seuils **à vérifier au run** — ne pas citer de métrique retirée du référentiel | `SD` — **garde-fou 4 : le jeu de métriques et leurs seuils changent, vérifier avant de conclure** |
| 33 | Schema | ÉTAT | Les données structurées sont-elles présentes, valides et adaptées au type de page ? | crawl (JSON-LD, microdata) | extraire le balisage de l'échantillon ; valider la syntaxe ; vérifier l'adéquation type de balisage / type de page ; détecter le balisage non conforme aux règles d'éligibilité | 0 erreur bloquante · balisage présent sur 100 % des gabarits éligibles · 0 balisage abusif | `SD` |

---

## 7. Indexation — volet ÉTAT

*Ce que le moteur a réellement pris, par opposition à ce que le site propose. L'écart entre les deux est le sujet entier de cette branche.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 34 | Sitemap | ÉTAT | Le sitemap existe-t-il, est-il propre et complet ? | `sitemap.xml` + crawl | croiser les URLs du sitemap avec les codes HTTP, les `noindex` et les canonicals | 0 URL non-200 · 0 URL en `noindex` · 0 URL canonicalisée ailleurs · ≥ 95 % des pages à valeur présentes | `SD` |
| 35 | Search Console | ÉTAT | Quel est l'état de couverture d'indexation déclaré par Google ? | GSC — rapport d'indexation des pages | relever les pages indexées, non indexées et leur motif ; hiérarchiser les motifs par volume | 0 page à valeur en « détectée non indexée » ou « explorée non indexée » | `EX` — `NM` sinon |
| 36 | Découverte Google | ÉTAT | Les nouvelles pages sont-elles découvertes rapidement ? | GSC + dates de publication | délai médian entre date de publication et première impression | délai médian ≤ 7 jours | `EX` — `NM` sinon |
| 37 | Pages Profondes | ÉTAT | Les pages situées en profondeur sont-elles indexées ? | GSC (fiable) ; à défaut inspection page par page | échantillonner les pages de profondeur ≥ 4 issues du nœud 15 et vérifier leur statut d'indexation | ≥ 80 % des pages profondes à valeur indexées | `EX` — dégradation à déclarer : l'opérateur `site:` **n'est pas** une mesure d'indexation fiable |
| 38 | Indexation De Masse | ÉTAT | Le ratio pages publiées / pages indexées est-il sain ? | GSC + crawl | comparer le nombre de pages crawlables à valeur au nombre de pages indexées | ≥ 80 % — un ratio plus bas signale du contenu jugé sans valeur par Google, pas un problème technique | `EX` — `NM` sinon |

---

## 8. Autorité — volet TRANSVERSAL

*Ce qui rend le domaine crédible aux yeux du moteur et des tiers — liens, mentions, signaux de marque. La branche la plus lente à bouger, donc celle où un diagnostic faux coûte le plus longtemps.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 39 | Backlinks | TRANSVERSAL | Quel est le profil de liens entrants du site ? | index de backlinks tiers (payant) | relevé des domaines référents, de leur thématique et de leur qualité ; comparaison aux concurrents du cadrage | aucun seuil absolu — comparaison relative aux concurrents uniquement | `PY` — dégradation `SD` très partielle : liens détectables par recherche web seulement |
| 40 | Trafic GSC | TRANSVERSAL | Quel est le trafic organique réel du site ? | GSC (clics, impressions) | relevé sur 12 mois glissants, avec tendance | aucun — baseline | `EX` — **`NM` sinon : non observable de l'extérieur** (garde-fou 2) |
| 41 | Pertinence Thématique | TRANSVERSAL | Les liens et mentions entrants sont-ils thématiquement cohérents avec le site ? | index de backlinks ; à défaut mentions trouvées en recherche web | classer les domaines référents par proximité thématique | ≥ 60 % des domaines référents thématiquement proches | `PY` — dégradation `SD` partielle |
| 42 | Mentions De Marque | TRANSVERSAL | La marque est-elle mentionnée hors de son propre site ? | recherche web | rechercher la marque hors du domaine propre ; compter et qualifier les sources (presse, annuaire, forum, partenaire, avis) | ≥ 10 mentions qualifiées hors annuaires automatiques | `SD` |
| 43 | Liens Déjà Visibles | TRANSVERSAL | Quels liens existants sont récupérables (mentions non liées, liens vers 404) ? | recherche web + crawl des 404 | croiser les mentions du nœud 42 sans lien sortant, et les URLs en 404 recevant des liens | liste nominative d'opportunités, chiffrée en nombre de domaines | `SD` partiel — `PY` pour la détection exhaustive des liens vers 404 |

---

## 9. Signaux — volet ÉTAT

*Ce que le comportement des visiteurs renvoie au moteur. Ces nœuds dépendent d'exports : sans eux, le verdict attendu est « non-mesuré », jamais une déduction.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 44 | CTR SERP | ÉTAT | Le taux de clic en SERP est-il conforme à l'attendu par position ? | GSC (impressions, clics, position) | comparer le CTR observé au CTR médian du site pour la même tranche de position | écart négatif > 30 % vs médiane du site = titre/meta à retravailler | `EX` — **`NM` sinon : non observable de l'extérieur** (garde-fou 2) |
| 45 | Trafic Référent | ÉTAT | Quelles sources externes envoient du trafic ? | GA (acquisition) | relevé des domaines référents par sessions ; PART IA isolée (décision du 11/08/2026) : segmenter les référents des assistants génératifs (chatgpt.com, perplexity.ai, copilot.microsoft.com, gemini.google.com, claude.ai…) — liste à rafraîchir par vérification web datée au run | part IA du trafic référent relevée et datée ; le reste descriptif | `EX` — `NM` sinon |
| 46 | Trafic Social | ÉTAT | Le contenu génère-t-il du trafic depuis les réseaux ? | GA (acquisition) | part des sessions d'origine sociale | aucun — descriptif. **La présence sociale est observable ; le trafic qu'elle génère ne l'est pas** | `EX` — `NM` sinon |
| 47 | Comportement Post Clic | ÉTAT | Que font les visiteurs organiques après l'arrivée ? | GA (engagement, parcours) | taux d'engagement, pages par session et conversions sur le segment organique | à calibrer sur la médiane du site, jamais sur un standard sectoriel emprunté | `EX` — `NM` sinon |
| 48 | Retours Utilisateurs | ÉTAT | Quels signaux qualitatifs publics existent sur le site ou la marque ? | avis publics, commentaires, forums | collecter et classer les retours par thème récurrent (produit, service, contenu, expérience) | ≥ 3 thèmes récurrents identifiés, avec verbatims cités | `SD` |

---

## 10. Discover — volet TRANSVERSAL

*L'exposition hors requête, où le site est proposé sans avoir été cherché. Les règles y diffèrent assez de la recherche classique pour mériter leur branche.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 49 | Angles Chauds | TRANSVERSAL | Le site produit-il du contenu sur des sujets à intérêt momentané ? | crawl (dates) + recherche web | repérer les contenus liés à l'actualité du secteur et leur fraîcheur ; comparer au rythme du secteur | ≥ 1 contenu d'actualité par mois pour un site à ambition Discover, sinon nœud hors périmètre | `SD` — la performance Discover réelle exige `EX` (rapport dédié GSC) |
| 50 | Titres Qui Attirent | TRANSVERSAL | Les titres sont-ils formulés pour le clic sans être trompeurs ? | crawl (balises `title`, H1) | échantillon de 20 titres : longueur, présence d'un bénéfice ou d'une tension, unicité, cohérence avec le contenu réel | 0 titre dupliqué · 0 promesse non tenue par la page · longueur adaptée à l'affichage SERP | `SD` |
| 51 | Fraîcheur | TRANSVERSAL | À quelle cadence le site publie-t-il et met-il à jour ? | dates observables + `lastmod` du sitemap | distribution des dates de publication et de modification sur 12 mois | cadence régulière et déclarée ; 0 `lastmod` faussement actualisé en masse | `SD` |
| 52 | Signaux Externes | TRANSVERSAL | Le contenu circule-t-il hors du site (reprises, citations, partages) ? | recherche web | rechercher les reprises de titres et d'extraits ; relever les sources reprenant le contenu | ≥ 3 reprises hors agrégateurs automatiques | `SD` partiel |
| 53 | Pics De Trafic | TRANSVERSAL | Le site a-t-il connu des pics, et sur quoi ? | GSC / GA (séries temporelles) | détecter les ruptures de série et les rattacher à une page ou un sujet | aucun — diagnostic descriptif, sert à identifier ce qui fonctionne | `EX` — `NM` sinon |

---

## 11. GEO — volet TRANSVERSAL

*Branche à forte volatilité : le garde-fou 4 s'applique à l'ensemble des nœuds ci-dessous. Vérification web datée obligatoire à chaque run avant de conclure.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 54 | Entités | TRANSVERSAL | La marque et ses sujets sont-ils structurés comme des entités reconnaissables ? | crawl (schema, page « à propos ») + recherche web | vérifier le balisage `Organization` / `Person`, la cohérence des informations d'identité sur toutes les pages, les liens `sameAs` vers des profils tiers, et l'existence d'une page d'identité factuelle | balisage d'entité présent · identité cohérente partout · ≥ 3 `sameAs` vérifiables | `SD` |
| 55 | Marque | TRANSVERSAL | La marque est-elle identifiable sans ambiguïté ? | recherche web | rechercher le nom de marque seul ; détecter les homonymies et les entités concurrentes qui captent la requête | le site occupe la première position sur son nom de marque, sans confusion d'entité | `SD` |
| 56 | Citations | TRANSVERSAL | Le site est-il cité comme source sur ses sujets par des tiers ? | recherche web | rechercher les sujets propriétaires du site et relever qui est cité comme source | ≥ 3 citations comme source sur des sujets du site | `SD` partiel — exhaustivité `PY` |
| 57 | Contenu Utile | TRANSVERSAL | Le contenu apporte-t-il une information non substituable ? | crawl + recherche web | échantillon de 10 pages : chercher au moins un élément introuvable ailleurs (donnée propre, expérience vécue, méthode, chiffre original) | ≥ 60 % des pages de l'échantillon portent un élément non substituable | `SD` |
| 58 | Présence Dans Les Réponses IA | TRANSVERSAL | La marque ou le site apparaît-il dans les réponses des moteurs génératifs sur ses requêtes cibles ? | test manuel documenté + vérification web datée du protocole | **protocole à établir au run** : les surfaces et leur comportement changent. Tester N requêtes cibles, consigner la formulation exacte, la date, la surface interrogée, et si le site est cité | taux de citation sur les requêtes cibles, relevé et daté | `SD` — **résultat non reproductible et non stable : le déclarer explicitement, ne jamais présenter le taux comme une métrique de suivi fiable** |
| 59 | Accès & Directives IA | TRANSVERSAL | Les agents des moteurs génératifs peuvent-ils accéder au site, et les directives IA sont-elles posées ? | crawl (robots.txt, llms.txt, en-têtes) + logs si fournis | vérifier robots.txt pour chaque agent IA de recherche (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended…) — posture par défaut : AUTORISÉ (décision du 11/08/2026), tout blocage est une décision consignée et datée du propriétaire ; distinguer agents d'entraînement et agents de recherche ; LIRE le contenu de llms.txt — pas seulement constater sa présence : chaque URL qu'il cite doit répondre, et ce qu'il annonce doit correspondre à ce que le site sert ; vérifier aussi sa cohérence avec le sitemap (standard émergent ADOPTÉ par décision du 11/08/2026 — consommation par les moteurs à réévaluer par vérification web datée à chaque run). Ce fichier existe pour être repris SANS vérification par des modèles de langue : une erreur y porte plus loin qu'ailleurs ; contrôler qu'aucun blocage CDN/WAF ne frappe ces UA quand les logs le montrent | aucun agent IA de recherche interdit sans décision consignée · llms.txt présent ET SON CONTENU LU — URLs citées vivantes, annonces confrontées à ce que le site sert, cohérence avec le sitemap ; la présence et l'accessibilité ne valent PAS vérification du contenu · zéro blocage CDN/WAF constaté sur les UA IA (si logs fournis) | `SD` partiel — logs `EX` |

---

## 12. Local — volet TRANSVERSAL

*Branche conditionnelle : ne s'applique qu'au modèle d'acquisition `local`. Sur tout autre
modèle, ses 5 nœuds sont marqués `hors-perimetre — modèle d'acquisition non local`, ce qui
est un résultat et non une dette d'instrumentation.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 60 | Fiche D'Établissement | TRANSVERSAL | La fiche d'établissement existe-t-elle, est-elle complète et revendiquée ? | recherche web sur la marque + le lieu | relever la présence de la fiche, son exhaustivité (catégorie principale, horaires, description, photos, attributs) et l'existence d'un propriétaire déclaré | fiche revendiquée · catégorie principale exacte · horaires à jour · ≥ 5 photos | `SD` |
| 61 | Cohérence NAP | TRANSVERSAL | Le nom, l'adresse et le téléphone sont-ils identiques partout ? | crawl du site + recherche web | comparer le triplet du site (mentions légales, contact, pied de page, balisage) à celui de la fiche d'établissement et des annuaires trouvés | 0 divergence sur les 3 champs, balisage d'établissement présent et cohérent | `SD` |
| 62 | Citations Et Annuaires | TRANSVERSAL | La présence sur les annuaires locaux et sectoriels est-elle établie ? | recherche web | inventorier les annuaires du secteur et de la zone ; relever présence, exactitude et fraîcheur de chaque fiche | présence sur ≥ 60 % des annuaires de référence du secteur, sans donnée périmée | `SD` |
| 63 | Avis Locaux | TRANSVERSAL | Quel est le volume, la note et la dynamique des avis, et sont-ils traités ? | avis publics | relever volume, note moyenne, rythme d'acquisition sur 12 mois et taux de réponse du gestionnaire | rythme régulier · taux de réponse ≥ 50 % · aucune période de 3 mois sans avis | `SD` |
| 64 | Pages Par Zone | TRANSVERSAL | Existe-t-il une page par zone desservie, et portent-elles un contenu propre ? | crawl | repérer les pages géolocalisées ; mesurer la part de contenu unique hors gabarit et la présence d'éléments propres à la zone | 1 page par zone à enjeu · ≥ 40 % de contenu unique · 0 duplication entre zones | `SD` |

---

## 13. Automatisation — volet TRANSVERSAL

*Cette branche est diagnostique **et** opérationnelle : elle détermine l'étiquette `IA` / `MANUEL` de chaque action au dispatch R5.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 65 | Agents IA | TRANSVERSAL | Quelles tâches SEO sont déjà agentifiées chez le client ? | déclaratif client | inventaire des automatisations existantes et de leur périmètre | aucun — sert à calibrer le régime d'automatisation des actions | `SD` (déclaratif, à étiqueter `[T2]`) |
| 66 | Audits Massifs | TRANSVERSAL | La capacité d'auditer N pages en série existe-t-elle ? | déclaratif + observation de l'outillage | vérifier l'existence d'un crawler, d'un accès aux données, d'un format de sortie exploitable | capacité présente ou absente, avec le coût de sa mise en place | `SD` |
| 67 | Monitoring | TRANSVERSAL | Existe-t-il une surveillance des positions, de l'indexation et des erreurs ? | déclaratif | inventaire des alertes en place et de leur destinataire | alerte active sur : chute d'indexation, erreurs 5xx, chute de trafic organique | `SD` |
| 68 | Génération De Pages | TRANSVERSAL | Des pages sont-elles générées à l'échelle, et avec quel contrôle qualité ? | crawl (nœud 26) + déclaratif | relier les motifs d'URL détectés au processus de génération déclaré ; identifier le point de contrôle qualité | tout gabarit génératif a un contrôle qualité nommé avant publication | `SD` |
| 69 | Détection Opportunités | TRANSVERSAL | Existe-t-il un mécanisme de détection continue d'opportunités ? | déclaratif | vérifier l'existence d'une boucle : source de données → règle de détection → destinataire | mécanisme présent ou absent ; s'il est absent, candidat prioritaire au quadrant `IA + gratuit` | `SD` |

---

## 14. Mesure — volet TRANSVERSAL

*Ce que le dispositif sait observer de lui-même. Un site sans mesure ne se corrige pas, il se devine — et ces nœuds disent lesquelles des mesures existent vraiment.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 70 | Impressions | TRANSVERSAL | Quel volume d'impressions et quelle tendance ? | GSC | relevé 12 mois glissants, tendance et saisonnalité | aucun — baseline et KPI cible | `EX` — **`NM` sinon** (garde-fou 2) |
| 71 | Clics | TRANSVERSAL | Quel volume de clics organiques et quelle tendance ? | GSC | relevé 12 mois glissants | aucun — baseline et KPI cible | `EX` — **`NM` sinon** (garde-fou 2) |
| 72 | Positions | TRANSVERSAL | Quelles positions moyennes sur les requêtes cibles ? | GSC | position moyenne par requête cible, avec le volume d'impressions associé | aucun — baseline et KPI cible | `EX` — **`NM` sinon** (garde-fou 2) |
| 73 | Leads | TRANSVERSAL | Combien de leads le canal organique génère-t-il ? | GA (conversions) + CRM | relevé des conversions attribuées à l'organique, avec le modèle d'attribution déclaré | aucun — baseline et KPI cible | `NM` — motif : exige GA **et** définition de conversion validée ; devient `EX` si fournis |
| 74 | Revenu Par Page | TRANSVERSAL | Quelles pages génèrent du revenu, et combien ? | GA e-commerce ou CRM rapproché des pages d'entrée | croiser pages d'entrée organiques et revenu attribué | aucun — sert à pondérer le gain des actions en € | `NM` — motif : exige un back-office e-commerce ou un CRM rapprochable |

---

## 15. Optimisation — volet TRANSVERSAL

*Ce qui se corrige à partir de ce qui est mesuré. Cette branche suppose la précédente : optimiser sans mesurer produit du mouvement, pas du résultat.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 75 | Contenus À Renforcer | TRANSVERSAL | Quelles pages sont proches du seuil de performance ? | GSC (positions 5-20 à fort volume d'impressions) | trier par (impressions × gain de CTR attendu si passage en top 3) ; croiser avec la complétude du contenu | liste des 10 pages au plus fort potentiel de gain à effort faible | `EX` — dégradation `SD` : pages fines ou incomplètes détectables au crawl, sans hiérarchisation par potentiel |
| 76 | Pages À Fusionner | TRANSVERSAL | Quelles pages se cannibalisent ? | crawl (similarité) ; GSC pour confirmation | détecter les pages de sujet proche visant la même intention ; confirmer par GSC (même requête servie par deux URLs) | 0 paire de pages en cannibalisation confirmée | `SD` partiel — `EX` pour la confirmation |
| 77 | Pages À Supprimer | TRANSVERSAL | Quelles pages n'apportent rien (0 trafic, 0 lien, 0 conversion) ? | GSC + GA ; à défaut signaux structurels | croiser absence de clics sur 12 mois, absence de liens entrants et absence de conversion | candidates listées avec, pour chacune, l'arbitrage suppression / fusion / amélioration — **jamais de suppression recommandée sur la seule absence de trafic** | `EX` — dégradation `SD` : pages orphelines, dupliquées ou expirées détectables au crawl |
| 78 | Tests SEO | TRANSVERSAL | Le site a-t-il la capacité de tester une hypothèse SEO ? | déclaratif + observation | vérifier l'existence de groupes de pages comparables et d'un moyen de mesurer l'écart | capacité présente ou absente, avec le prérequis manquant nommé | `SD` |
| 79 | Boucles D'Amélioration | TRANSVERSAL | Existe-t-il un cycle mesurer → agir → remesurer documenté ? | déclaratif + historique des runs | vérifier l'existence d'un état de référence antérieur et d'une trace des actions passées | **c'est le nœud qu'instrumente le couple `snapshot` / `diff` de ce skill** : au premier run, le constat est « boucle absente, snapshot initial posé » | `SD` |

---

## 16. Croissance — volet STRATÉGIE

*Où le dispositif peut s'étendre une fois qu'il tient. Ces nœuds se répondent au cadrage et s'appuient sur les branches d'état : ce sont des paris argumentés, pas des constats.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 80 | Nouveaux Silos | STRATÉGIE | Quels territoires thématiques adjacents sont accessibles ? | nœuds 1, 4, 5, 20 + cadrage | identifier les thèmes adjacents où la SERP est attaquable et où le site a une légitimité démontrable | ≥ 2 silos candidats, chacun avec sa légitimité et sa SERP qualifiée | `SD` |
| 81 | Nouveaux Sites | STRATÉGIE | Un site distinct est-il justifié, ou est-ce une fuite devant la difficulté ? | cadrage + nœuds 1 et 11 | poser la question à l'envers : qu'est-ce qui empêche de le faire sur le domaine existant ? | recommandé **uniquement** si le domaine existant est structurellement inadapté (marque, langue, modèle) — jamais pour contourner un problème d'autorité | `SD` |
| 82 | Nouveaux Médias | STRATÉGIE | D'autres surfaces méritent-elles d'être investies (vidéo, podcast, place de marché) ? | cadrage + SERP | vérifier si les SERP cibles affichent des formats que le site ne produit pas | investissement justifié seulement si la SERP cible affiche déjà ce format | `SD` |
| 83 | Partenariats | STRATÉGIE | Quels partenaires peuvent apporter autorité et audience ? | nœuds 42, 43, 52 + cadrage | identifier les acteurs déjà en relation ou déjà citants, et les opportunités de réciprocité | ≥ 5 partenaires nominatifs, avec l'angle d'approche | `SD` |
| 84 | Actifs Qui Composent | STRATÉGIE | Quels actifs produisent un rendement cumulatif plutôt que ponctuel ? | ensemble de l'audit | distinguer les actions à effet unique (correction technique) des actifs à effet cumulé (pilier qui capte la traîne, outil gratuit qui attire des liens, données propriétaires) | ≥ 3 actifs cumulatifs identifiés dans la trajectoire | `SD` |

---

## 17. Objectif — CADRAGE

*Ces nœuds ne s'auditent pas : ils entrent par le cadrage et sortent en cibles chiffrées au volet STRATÉGIE.*

| # | Nœud | Volet | Question d'audit | Source requise | Méthode | Critère de verdict | Statut |
|---|---|---|---|---|---|---|---|
| 85 | Trafic Qualifié | CADRAGE | Quelle cible de trafic à intention à 12 et 24 mois ? | cadrage client + baseline | dériver de la baseline et du potentiel des requêtes cibles ; calcul visible, fourchette obligatoire | cible chiffrée, étiquetée `[T4]`, avec sa sensibilité | `CA` |
| 86 | Leads Entrants | CADRAGE | Quelle cible de leads organiques ? | cadrage + nœuds 73 et 47 | appliquer le taux de conversion observé au trafic cible ; **si le taux n'est pas mesuré, la cible est non calculable et doit être déclarée telle** | cible chiffrée ou déclaration explicite de non-calculabilité | `CA` |
| 87 | Ventes | CADRAGE | Quelle cible de chiffre d'affaires organique ? | cadrage + nœuds 8 et 74 | appliquer la valeur client aux leads cibles | cible chiffrée ou déclaration explicite de non-calculabilité | `CA` |
| 88 | Autorité | CADRAGE | *(doublon du schéma)* | — | **renvoi vers la branche `Autorité`, nœuds 39-43** | ne pas auditer ici | `RV` |
| 89 | Machine SEO | CADRAGE | Le dispositif est-il autonome et répétable, ou dépend-il d'une impulsion externe ? | synthèse des branches `Automatisation`, `Mesure`, `Optimisation` | scorer la maturité sur 5 : 1 = actions ponctuelles sans mesure · 3 = mesure en place, actions réactives · 5 = détection, action et remesure outillées et cadencées | score de maturité 1-5, justifié par les nœuds 59-63, 65-69 et 70-74 | `SD` |

---

## Comptage de contrôle

*Trois vues du même ensemble, qui doivent toutes tomber juste. Chaque tableau se lit ligne par ligne — un axe, un compte — et le total de chacun vaut le nombre de nœuds de la grille. Ces trois tables sont ce qu'on lit pour PLANIFIER une évolution : elles disent où insérer et quels identifiants bougent. Le contrôle 13 de `validate.py` les recalcule depuis le manifeste et refuse tout écart, parce qu'elles ont menti quinze jours sans que rien ne le voie.*

| Branche | Nœuds | Numéros |
|---|---|---|
| Idée | 5 | 1-5 |
| Validation | 5 | 6-10 |
| Architecture | 5 | 11-15 |
| Mots Clés | 6 | 16-21 |
| Contenu | 6 | 22-27 |
| Technique | 6 | 28-33 |
| Indexation | 5 | 34-38 |
| Autorité | 5 | 39-43 |
| Signaux | 5 | 44-48 |
| Discover | 5 | 49-53 |
| GEO | 6 | 54-59 |
| **Local** | **5** | **60-64** |
| Automatisation | 5 | 65-69 |
| Mesure | 5 | 70-74 |
| Optimisation | 5 | 75-79 |
| Croissance | 5 | 80-84 |
| Objectif | 5 | 85-89 |
| **Total** | **89** | — |

### Par statut

*Combien de nœuds se mesurent sans rien demander, et combien dépendent d'autre chose. C'est cette table qui dit ce qu'un audit peut rendre sur un site dont on n'a reçu aucun export.*

| Statut | Nombre | Lecture |
|---|---|---|
| `SD` — sans dépendance externe | **55** | mesurables sur tout site, sans rien demander au client |
| `EX` — si export fourni | **18** | dépendent de GSC / GA / CRM |
| `PY` — si outil payant | **5** | dépendent d'un index de backlinks ou d'une source de volume |
| `NM` — non mesurable | **6** | logs serveur, CRM, données économiques |
| `RV` — renvoi doublon | **2** | audités dans leur branche autoritaire |
| `CA` — cadrage | **3** | entrées et cibles, pas des audits |
| **Total** | **89** | — |

### Par volet

*À quel moment du run chaque nœud est instruit. Un volet n'est pas un niveau d'importance : c'est une place dans la séquence.*

| Volet | Nombre |
|---|---|
| `ÉTAT` | 16 |
| `STRATÉGIE` | 15 |
| `TRANSVERSAL` | 53 |
| `CADRAGE` | 5 |
| **Total** | **89** |

**Sans aucun export client**, 53 nœuds sur 87 restent instrumentés (61 %), et 24 basculent en non mesurable (18 `EX` + 6 `NM`), dont l'intégralité de la mesure de performance. C'est le chiffre à annoncer en R0.

Ces comptes valent pour une étude **locale**, qui mobilise les 87 nœuds. Sur un autre modèle, les nœuds hors portée s'ajoutent — 5 pour la branche `Local`, jusqu'à 8 de plus selon le modèle.
