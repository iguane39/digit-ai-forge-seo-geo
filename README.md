# forge-seo

Outil d'audit et de stratégie SEO. La forge porte **la méthode** — une grille de
88 nœuds, un barème, des garde-fous — et chaque projet audité reçoit **son étude chez
lui**, dans son propre dossier `seo/`.

Là où un rapport se produit puis s'oublie, ce dispositif accumule : étude après étude,
sur une grille stable, comparable et versionnée.

---

## Catalogue de services

> Section proposée par la campagne « catalogues » du pilot (2026-08-13) — générée depuis
> la source unique `catalogues/catalogue.jsonl` du pilot (v1.6.0, challengée état de
> l'art le 12/08/2026). **prouvé** = preuve exécutée ; *déclaré* = méthode documentée seulement.

| Service | Intention (« je veux… ») | Point d'entrée | Statut |
|---|---|---|---|
| **Créer une mission d'audit SEO** | ouvrir une étude SEO outillée chez mon produit | `python scripts\new_mission.py (CLI stdlib)` | prouvé (production) |
| **Dérouler l'audit 87 nœuds** | auditer mon site en ligne sur toute la grille, preuves à l'appui | `seo\METHODE.md déroulée en session (mandat humain requis — jamais de déclenchement automatique)` | prouvé (production) |
| **Valider forge et mission** | vérifier mécaniquement l'intégrité de la forge et d'une mission | `python scripts\validate.py [--mission <chemin>]` | prouvé (production) |
| **Rapport HTML vérifié** | recevoir un rapport d'audit autonome et contrôlé avant remise | `python scripts\rapport_html.py --verifier` | prouvé (production) |
| **Runs de suivi récurrents** | suivre l'évolution SEO d'un site entre deux audits | `méthode documentée (récurrence post-MEP)` | déclaré (experimental) |
| **Instrumentation de crawl avancée** | mesurer aussi les sites JS, le balisage, les CWV terrain et les crawlers IA | `python scripts\{crawler.py --rendu-js, crux.py, agents_ia.py}` | prouvé (experimental) |
| **Scorer et écrire le CSV d'actions** | transformer les actions rédigées de la mission en CSV scoré, trié et contrôlé | `python scripts\scorer_actions.py --mission <chemin>` | prouvé (experimental) |

Le catalogue consolidé des dix forges vit chez le pilot :
[digit-ai-forge-pilot/catalogues/CATALOGUES.md](https://github.com/iguane39/digit-ai-forge-pilot/blob/main/catalogues/CATALOGUES.md).

## Invoquer forge-seo depuis un projet extérieur

C'est l'usage principal : tu travailles dans `c:\dev\mon-client`, tu veux une étude SEO.

**Rien ne se déclenche tout seul.** Il n'y a pas de skill, pas de mot-clé qui active
l'audit sur une phrase. Un audit engage des heures de travail et un livrable facturé :
il commence par une commande explicite. C'est l'invocation du projet qui l'enclenche.

```bash
cd c:/dev/mon-client

# 1. créer l'espace de travail — 114 dossiers, 88 fiches hydratées
python c:/dev/digit-ai-forge-seo/scripts/new_mission.py \
       --projet . --client "Acme" --domaine acme.fr --modele b2b-lead-gen

# 2. remplir seo/cadrage.md, déposer les exports dans seo/donnees/{gsc,ga,crm,logs}/

# 3. collecter — crawl du site, étape 1 du pipeline
python c:/dev/digit-ai-forge-seo/scripts/crawler.py --projet . --url https://acme.fr
#    lit sitemap.xml (via robots.txt, index suivis) AVANT de suivre les liens :
#    l'inventaire mesuré est celui du site, pas celui du graphe de navigation.
#    --rendu-js exécute le JS côté client (Playwright/Chromium) sur un site SPA.
#    Le JSON-LD (application/ld+json) est extrait automatiquement, sans option.

# 3 bis. (optionnel, noeud 31) donnees de terrain CrUX -- gratuit, cle API requise
CRUX_API_KEY=... python c:/dev/digit-ai-forge-seo/scripts/crux.py --projet . --url https://acme.fr
#    cle gratuite (aucune facturation) : https://developer.chrome.com/docs/crux/api

# 3 ter. (optionnel, noeuds 29/58, si logs serveur fournis) ventilation par agent IA nommé
python c:/dev/digit-ai-forge-seo/scripts/agents_ia.py --projet . --logs seo/donnees/logs/access.log
#    catalogue daté des agents (GPTBot, ClaudeBot, PerplexityBot…) dans referentiel/agents-ia.json

# 4. ouvrir seo/METHODE.md — garde-fous, runbook, contrat de sortie. Constater et
#    interpréter dans les fiches de seo/analyse/ : c'est la partie humaine.

# 4 bis. (run de version) poser un contenu rédigé dans les 88 fiches, et reporter
#        les constats du run précédent — appariés par (branche, nœud), jamais par id
python c:/dev/digit-ai-forge-seo/scripts/remplir_fiches.py \
       --projet . --contenu seo/fiches.json --reprise ../docs/seo/analyse

# 5. assembler ce qui se déduit des fiches — snapshot, dette, compteurs
python c:/dev/digit-ai-forge-seo/scripts/livrables.py --projet .

# 5 bis. (étape 5 du pipeline : Actions) calculer le score des actions rédigées
#        par la mission et écrire seo/livrables/actions-<domaine>-<jour>.csv
python c:/dev/digit-ai-forge-seo/scripts/scorer_actions.py \
       --projet . --contenu seo/actions.json
#    la mission rédige libellé, gain/effort/confiance et la preuve du cran cité
#    (referentiel/scoring.md) ; le script calcule score = (gain × confiance) /
#    effort, trie, et écrit aux colonnes imposées par livrables.py (TF-0056).

# 6. produire le rapport client
python c:/dev/digit-ai-forge-seo/scripts/rapport_html.py --projet . --verifier

# à tout moment : contrôler l'étude
python c:/dev/digit-ai-forge-seo/scripts/validate.py --mission .
```

`--modele` prend `b2b-lead-gen`, `e-commerce`, `media-affiliation`, `local` ou `saas`.
Il pré-marque les nœuds hors portée : inutile de les instruire, et ils n'entrent pas
dans la dette d'instrumentation. Omis, aucun nœud n'est écarté.

Les scripts s'exécutent depuis n'importe quel répertoire courant — ils localisent la
forge par leur propre chemin. Aucune dépendance : Python 3 et sa bibliothèque standard.

### Ce qui atterrit chez le client

```
mon-client/seo/
├── METHODE.md           la méthode — à ouvrir pour commencer
├── README.md            mode d'emploi de l'espace
├── cadrage.md           entrées de la mission
├── etat.json            avancement — permet la reprise
├── .forge-seo.json      provenance : chemin de la forge, version de grille, date
├── .gitignore           garde-fou de confidentialité
├── donnees/             exports bruts — gsc/ ga/ crm/ logs/ crawl/
├── analyse/             105 dossiers, 88 fiches hydratées
└── livrables/           snapshot, actions.csv, rapport HTML client
```

**Quatre livrables, pas six.** L'audit, la trajectoire (roadmap) et la dette
d'instrumentation ne sont **pas** des fichiers séparés : ce sont des blocs du rapport
HTML, alimentés par le snapshot. Le choix est explicite dans `referentiel/methode.md` —
un jumeau Markdown créerait une seconde source, qui divergerait au premier correctif.
Cette ligne annonçait encore les cinq livrables du prompt d'origine (`prompts/`,
archivé) : le référentiel fait foi, l'archive non.

**Rien ne reste dans la forge.** C'est un invariant testé : le contrôle 8 de
`validate.py` échoue si une étude s'y installe, et `new_mission.py` refuse de viser la
forge ou un dossier qui la contient.

**Deux axes délibérément séparés.** `donnees/` est indexé par **source**, `analyse/`
par **concept SEO** — un export GSC alimente 16 nœuds répartis dans 7 branches, les deux
indexations ne peuvent pas être la même. Et `analyse/` est la matière première quand
`livrables/` est le document assemblé : les confondre rend le rapport impossible à
composer.

---

## Où vit quoi

```
forge-seo/
├── referentiel/         LA MÉTHODE — source de vérité
│   ├── methode.md               garde-fous, runbook, contrat de sortie
│   ├── grille-noeuds.md         17 branches, 88 nœuds, portée par modèle
│   ├── scoring.md               échelles ancrées, formule, trait de coupe
│   ├── sources-donnees.md       matrice source → nœuds, dégradations
│   ├── strategie-future.md      méthode du volet 12-24 mois
│   ├── cadrage.template.md      formulaire d'entrée détaillé
│   ├── snapshot.schema.json     contrat de l'état persistant, appliqué
│   ├── correspondances-grille.json  évolutions de la grille, ancien id → nouvel id
│   └── agents-ia.json           catalogue daté des agents IA nommés (noeuds 29/58)
├── seo/                 arborescence canonique générée depuis referentiel/ — lecture seule
├── scripts/             grille · gabarits · scaffold · new_mission · validate
│                        · schema · crawler · crux · agents_ia · livrables
│                        · scorer_actions · gabarit_html · rapport_html
│                        · oracle_interaction · remplir_fiches · autotest
├── assets/vendor/       composant de filtres, copie verbatim tracée
├── output/              livrables : 01-decisions/ et 02-veille/
├── prompts/             archives datées du chantier
└── input/               le schéma d'origine, archivé
```

**Aucun déclencheur, aucun skill.** Le projet est entièrement piloté par ses scripts et
son référentiel. La méthode se lit — elle ne s'active pas.

`methode.md` porte les 7 garde-fous, et `new_mission.py` en dépose une copie dans chaque
étude sous `seo/METHODE.md`, estampillée de la version de grille. Deux raisons : ils
doivent être lus **avant** la première mesure, pas au moment où l'on va chercher une
référence ; et l'étude reste lisible même détachée de la forge.

Si la forge est introuvable au moment de charger les références, la méthode dit de
s'arrêter plutôt que d'improviser. Une grille reconstituée de mémoire n'est pas la
grille, et rien ne le signalerait.

## Maintenir la forge

```bash
python scripts/scaffold.py                      # régénère seo/ depuis referentiel/
python scripts/validate.py                      # 12 contrôles, non-zéro si échec
python scripts/validate.py --json               # même verdict, en objet machine
python scripts/autotest.py                      # fixtures vertes ET rouges des contrôles
python scripts/new_mission.py --liste           # registre local des études créées
```

`autotest.py` existe parce qu'un contrôle qu'on n'a jamais vu **échouer** n'est pas un
contrôle : c'est une ligne qui imprime OK. Chaque règle y porte une fixture verte qui
passe et une fixture rouge qui échoue pour la bonne raison, construites dans un
répertoire temporaire du système — rien n'est écrit dans la forge ni chez une mission.

`missions.json` est un registre local — client, domaine, chemin, date, version de
grille. Aucune donnée client. Il n'est pas versionné.

---

## Le pipeline — 5 étapes aux sorties disjointes

| Étape | Produit | Destination |
|---|---|---|
| 1. Collecte | données brutes, horodatées | `seo/donnees/` |
| 2. Constat | ce qui est, mesuré, avec niveau de preuve | `seo/analyse/**/_fiche.md` § Constat |
| 3. Interprétation | le mécanisme : ce que ça coûte et pourquoi | `seo/analyse/**/_fiche.md` § Interprétation |
| 4. Projection | où ça peut aller, borné et calculé | `seo/livrables/` |
| 5. Actions | quoi faire, chiffré, priorisé, dispatché | `seo/livrables/actions-*.csv` |

« Audit », « analyse » et « expertise » désignaient la même opération sous trois noms :
ce sont les étapes 2 et 3. Chaque étape produit un **type d'objet différent**, ce qui
interdit structurellement à la suivante de répéter la précédente.

## Le rapport client

`rapport_html.py` produit une page **autonome** — zéro requête réseau, CSS et JS inline,
ouvrable hors ligne dans deux ans, imprimable. Douze blocs, synthèse ouverte et détail
replié : le dirigeant comprend en trente secondes, le consultant exploite en trente
minutes, sans deux documents.

Sa contrainte centrale : le **niveau de preuve est une dimension visuelle de premier
ordre**. `[T1 observé]`, `[T2 déclaré]`, `[T3 tiers]`, `[T4 inféré]` et « non mesuré »
portent chacun un glyphe et un style de bordure distincts — discriminables sans dépendre
de la couleur —, avec légende en tête et compteur de répartition en synthèse. Sans cela,
une belle page rendrait un chiffre inféré indiscernable d'une mesure, et annulerait en
CSS tout le dispositif anti-hallucination.

Si un snapshot antérieur existe pour le domaine, la page affiche le **diff** : ce qui a
bougé, quelles actions ont produit un effet mesurable. C'est ce que le client achète au
second audit.

## Pourquoi `input/Schéma SEO.MD` n'est jamais parsé

Son bloc `Objectif` (lignes 219-229) a une indentation cassée : ses 5 feuilles sont
écrites au niveau racine. Un parseur naïf produit **21 branches et 77 feuilles** au lieu
de 16 et 82, crée 5 dossiers racine parasites — et, effet de bord plus grave, cesse de
détecter `Autorité` comme doublon. Le contrôle de cohérence passe alors au vert sur une
arborescence fausse. Vérifié, puis contourné : la source est
`referentiel/grille-noeuds.md`. Voir `scripts/grille.py`.

## Conventions

**Nommage** — slug ASCII kebab-case préfixé du numéro d'ordre : `06-technique/`,
`17-objectif/05-machine-seo/`. Trois raisons : les noms littéraux portent 7 classes de
caractères non-ASCII dont U+2019 dans « Boucles D'Amélioration » ; l'ordre alphabétique
détruirait la séquence méthodologique (`Architecture` avant `Idée`) ; les chemins
Windows restent courts.

**La 17ᵉ branche `Local` est une extension assumée** du schéma source, qui ne couvrait
pas le SEO local alors que le cadrage propose `local` comme modèle d'acquisition. Sa
portée, comme celle de 8 autres nœuds, est **conditionnelle au modèle**.

**Les 2 doublons du schéma** se matérialisent en 2 chemins réels. La branche fait
autorité, la feuille homonyme porte `doublon_de` et aucun champ à remplir :

- `06-technique/02-indexation/` → `07-indexation/`
- `17-objectif/04-autorite/` → `08-autorite/`

**Front-matter typé, identique sur les 88 fiches.** C'est ce qui rendra les études
comparables — médianes internes, calibrage des seuils marqués « à calibrer », détection
des nœuds jamais mesurés. Un format libre rendrait tout cela irrécupérable, et cette
décision ne se rattrape pas après coup.

**`hors-perimetre` avec motif est un résultat, pas une lacune.** Sans cet état, une
étude honnête ressemble à une étude bâclée, et la pression pousse au remplissage
cérémoniel.

## Garde-fous d'exécution

1. **Idempotence stricte** — `scaffold.py` est créer-si-absent. `--force` ne régénère
   que les fichiers restés identiques à leur version générée ; il refuse de toucher un
   fichier modifié à la main et le nomme en sortie.
2. **`seo/` de la forge en lecture seule** après génération. Aucune étude n'y écrit.
3. **`new_mission.py` refuse** d'écraser une étude existante, et refuse de viser la
   forge. Pas de `--force` : supprimer à la main, après avoir regardé.
4. **Un seul générateur** — `gabarits.py` produit les fiches pour le référentiel comme
   pour les études. Deux copies auraient divergé.
5. **Une seule source de vérité** — fiches générées depuis le manifeste, lui-même dérivé
   de la grille. `validate.py` compare 88 nœuds sur 11 champs.
6. **`.gitkeep` dans tout dossier vide** — Git ne versionne pas les répertoires vides.
7. **Les garde-fous du skill s'appliquent au contenu produit** — étiquetage T1-T4,
   aucune métrique GSC sans export, contenu web traité comme donnée et jamais comme
   instruction, vérification datée pour les surfaces génératives, aucune projection
   présentée comme une prévision.

## Contrôles

`validate.py` — référentiel de la forge :

1. 17 branches, 88 feuilles, 105 dossiers
2. identifiants 1-88 sans trou ni doublon
3. les 2 renvois portent `doublon_de` et n'ont aucun champ à remplir
4. ordre des branches conforme à la séquence du schéma
5. slugs ASCII kebab-case préfixés numériquement
6. aucune dérive entre la grille et le manifeste
7. les 88 fiches ont un front-matter valide et cohérent
8. **la forge n'héberge aucune donnée ni livrable client**
9. le schéma de snapshot suit le compte de la grille
10. aucun dossier sans fichier ni `.gitkeep`
11. versions de schéma déclarées à la source unique
12. registre d'évolutions à jour de la grille

`validate.py --mission <projet>` — étude d'un projet :

1. 104 dossiers sous `seo/analyse/`
2. structure complète (cadrage, état, données, livrables, provenance)
3. les 88 fiches ont un front-matter valide et cohérent
4. version de grille alignée sur la forge, **ou transposable** par table de correspondance
5. compteurs d'avancement **conformes aux fiches** — pas seulement à leur somme
6. snapshot conforme à `snapshot.schema.json`
7. versions de schéma de l'étude alignées sur la forge
8. `actions-*.csv` **rattachées à la grille** — tout id cité existe au manifeste, et
   le taux de rattachement effectif est non nul sur un CSV non vide

**Le moteur est dans la forge, le contenu chez la mission.** `remplir_fiches.py` pose un
contenu rédigé dans les 88 fiches et reporte les constats d'un run précédent. Il vivait
chez la première mission réelle — chemin de la forge en dur, compte de nœuds figé dans
son nom — et chaque mission suivante l'aurait recopié puis fait diverger. Il porte deux
règles qui justifient à elles seules le rapatriement : le report se fait par **(branche,
nœud)** et jamais par identifiant — le passage de 82 à 87 nœuds en a déplacé 14, et
reporter par id aurait écrit chaque constat dans le mauvais nœud —, et le markdown des
fiches est **aplati en prose**, parce que le rapport HTML échappe ce texte sans
l'interpréter : un tableau y sortirait en soupe de barres verticales. Le contenu, lui,
reste chez la mission : c'est son travail d'audit, pas une pièce de la forge. Format
recommandé, un JSON indexé par identifiant de nœud ; un module Python exposant `F` est
accepté pour les études déjà écrites ainsi.

**Une évolution de grille exige sa table de correspondance.** Le passage de 82 à 87
nœuds a déplacé 14 identifiants : une étude ouverte avant continuait de citer les
anciens numéros, chaque constat désignant dès lors un autre nœud que celui mesuré, sans
un mot. `referentiel/correspondances-grille.json` rend l'évolution déclarative — `de`,
`vers`, `correspondances` (ancien id → nouvel id), identifiants retirés et nouveaux — et
deux contrôles la rendent opposable : le 12 du référentiel échoue tant que
`version_courante` ne suit pas l'empreinte de la grille (on ne peut donc pas faire
évoluer l'une sans déclarer l'autre), et le 4 d'une étude refuse une version de grille
divergente **sans table applicable**. Les évolutions se chaînent : une étude qui a sauté
plusieurs versions reste récupérable tant qu'une suite d'entrées relie sa version à la
version courante. Un identifiant retiré ne se réaffecte jamais.

**Actions ↔ grille — deux règles, pas une.** Rien ne reliait le CSV d'actions au
manifeste : une action citant le nœud 92 sur une grille qui s'arrête à 87 ne produisait
aucune erreur, seulement un « Nœuds couverts : — » dans le rapport. Le contrôle 8 exige
donc (a) que tout id cité existe, et (b) que le taux de rattachement effectif soit non
nul — car (a) seule reste verte quand *aucun* id n'est cité (colonne absente, mal
orthographiée ou vide partout), c'est-à-dire précisément quand le rapport est le plus
faux. Le lecteur de CSV vit désormais dans `livrables.py`, le module qui **crée** ces
fichiers : deux lecteurs auraient divergé.

**Versions de schéma — une seule déclaration.** Trois artefacts générés portent un
`schema_version` : `etat.json`, `seo/manifest.json` et le snapshot. Ils sont déclarés
dans `gabarits.py` (`VERSION_ETAT`, `VERSION_MANIFESTE`, `version_snapshot()` — cette
dernière **lue** dans `snapshot.schema.json`, jamais recopiée). Leurs numéros restent
volontairement différents : ce sont trois contrats distincts, et les aligner ferait
croire qu'un bump de l'un vaut bump des autres. Ce qui est mutualisé, c'est la
déclaration, pas la valeur — avant, trois littéraux vivaient dans trois fichiers et
rien ne disait s'ils divergeaient par intention ou par oubli.

`--json` rend le même verdict sur stdout en objet machine — `verdict`, `controles[]`
(nom, ok, détail), `echecs[]` — pour qu'un orchestrateur lise le résultat sans parser
du texte. Le mode texte reste le défaut, et les deux sorties dérivent des mêmes données :
un mode qui recalculerait son verdict à part finirait par diverger de l'autre.

Le rapport HTML se recette en trois couches :

```bash
python scripts/rapport_html.py --projet . --verifier    # 10 contrôles sur le fichier
python scripts/oracle_interaction.py <page.html>        # 9 contrôles d'EXÉCUTION
```

Nommage du livrable — **décision Q3-bis du 09/08/2026** : dans le nom d'un fichier, le
**projet prime sur l'émetteur**. Le motif est `<Projet> - <Objet> - AAAAMMJJ<indice>.ext`,
soit `Produit-02 - Audit SEO - 20260809a.html`. Un client classe ses documents
par affaire, pas par prestataire ; et préfixer par l'émetteur ferait changer de nom un même
rapport selon qui le produit, ce qui casse le chaînage entre deux runs. Les livrables déjà
émis sous l'ancien motif ne sont ni renommés ni archivés : l'historique reste tel qu'il a
été livré.

Le 9e contrôle est la **lisibilité L1-L11**, déléguée au socle `digit-ai-page-html`
(`check_html.py --regles L`) : texte tronqué, largeur de lecture, score sans barème lié,
liste longue non filtrable, surlignage qui casse les mots, sommaire muet ou à ancre morte,
chapitre sans chapeau, lien interne sans destination, détail vide, table de données sans
exemple de lecture. La règle appartient au socle, pas à cette forge : on l'applique, on ne
la redéfinit pas — et le contrôle échoue bruyamment si le socle est introuvable, plutôt que
de rendre un vert par défaut.

puis par les oracles des skills `digit-ai-page-html` et `quality-oracles` :
`check_html.py`, `render_page.py` (V1-V7, trois breakpoints), `oracle-filtres-tableau.mjs`
et `oracle-a11y.py`.

`oracle_interaction.py` existe parce que les autres sont **statiques ou visuels** : ils
lisent le marquage ou mesurent des boîtes, aucun ne dit si le script tourne. Le rapport
a déjà porté un défaut exactement de cette nature — un `</script>` en commentaire dans
un composant inline terminait l'élément, tout le JS suivant devenait du HTML mort, et
les trois oracles étaient au vert. Celui-ci charge la page dans un navigateur et vérifie
ce qui n'existe que si le code s'est exécuté. Vérifié par mutation : sans l'échappement,
il rend 2/9 avec erreurs JS.