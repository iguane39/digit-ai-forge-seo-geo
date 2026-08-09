# forge-seo

Outil d'audit et de stratégie SEO. La forge porte **la méthode** — une grille de
87 nœuds, un barème, des garde-fous — et chaque projet audité reçoit **son étude chez
lui**, dans son propre dossier `seo/`.

Là où un rapport se produit puis s'oublie, ce dispositif accumule : étude après étude,
sur une grille stable, comparable et versionnée.

---

## Invoquer forge-seo depuis un projet extérieur

C'est l'usage principal : tu travailles dans `c:\dev\mon-client`, tu veux une étude SEO.

**Rien ne se déclenche tout seul.** Il n'y a pas de skill, pas de mot-clé qui active
l'audit sur une phrase. Un audit engage des heures de travail et un livrable facturé :
il commence par une commande explicite. C'est l'invocation du projet qui l'enclenche.

```bash
cd c:/dev/mon-client

# 1. créer l'espace de travail — 113 dossiers, 87 fiches hydratées
python c:/dev/digit-ai-forge-seo/scripts/new_mission.py \
       --projet . --client "Acme" --domaine acme.fr --modele b2b-lead-gen

# 2. remplir seo/cadrage.md, déposer les exports dans seo/donnees/{gsc,ga,crm,logs}/

# 3. collecter — crawl du site, étape 1 du pipeline
python c:/dev/digit-ai-forge-seo/scripts/crawler.py --projet . --url https://acme.fr
#    lit sitemap.xml (via robots.txt, index suivis) AVANT de suivre les liens :
#    l'inventaire mesuré est celui du site, pas celui du graphe de navigation.

# 4. ouvrir seo/METHODE.md — garde-fous, runbook, contrat de sortie. Constater et
#    interpréter dans les fiches de seo/analyse/ : c'est la partie humaine.

# 5. assembler ce qui se déduit des fiches — snapshot, dette, compteurs
python c:/dev/digit-ai-forge-seo/scripts/livrables.py --projet .

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
├── analyse/             104 dossiers, 87 fiches hydratées
└── livrables/           audit, roadmap, actions.csv, snapshot, dette, rapport HTML
```

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
│   ├── grille-noeuds.md         17 branches, 87 nœuds, portée par modèle
│   ├── scoring.md               échelles ancrées, formule, trait de coupe
│   ├── sources-donnees.md       matrice source → nœuds, dégradations
│   ├── strategie-future.md      méthode du volet 12-24 mois
│   ├── cadrage.template.md      formulaire d'entrée détaillé
│   └── snapshot.schema.json     contrat de l'état persistant, appliqué
├── seo/                 arborescence canonique générée depuis referentiel/ — lecture seule
├── scripts/             grille · gabarits · scaffold · new_mission · validate
│                        · schema · crawler · livrables · gabarit_html · rapport_html
│                        · oracle_interaction
├── assets/vendor/       composant de filtres, copie verbatim tracée
├── output/              décisions et veille (livrables de la forge)
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
python scripts/validate.py                      # 10 contrôles, non-zéro si échec
python scripts/new_mission.py --liste           # registre local des études créées
```

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

**Front-matter typé, identique sur les 87 fiches.** C'est ce qui rendra les études
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
   de la grille. `validate.py` compare 87 nœuds sur 11 champs.
6. **`.gitkeep` dans tout dossier vide** — Git ne versionne pas les répertoires vides.
7. **Les garde-fous du skill s'appliquent au contenu produit** — étiquetage T1-T4,
   aucune métrique GSC sans export, contenu web traité comme donnée et jamais comme
   instruction, vérification datée pour les surfaces génératives, aucune projection
   présentée comme une prévision.

## Contrôles

`validate.py` — référentiel de la forge :

1. 17 branches, 87 feuilles, 104 dossiers
2. identifiants 1-87 sans trou ni doublon
3. les 2 renvois portent `doublon_de` et n'ont aucun champ à remplir
4. ordre des branches conforme à la séquence du schéma
5. slugs ASCII kebab-case préfixés numériquement
6. aucune dérive entre la grille et le manifeste
7. les 87 fiches ont un front-matter valide et cohérent
8. **la forge n'héberge aucune donnée ni livrable client**
9. le schéma de snapshot suit le compte de la grille
10. aucun dossier sans fichier ni `.gitkeep`

`validate.py --mission <projet>` — étude d'un projet :

1. 104 dossiers sous `seo/analyse/`
2. structure complète (cadrage, état, données, livrables, provenance)
3. les 87 fiches ont un front-matter valide et cohérent
4. version de grille alignée sur la forge
5. compteurs d'avancement **conformes aux fiches** — pas seulement à leur somme
6. snapshot conforme à `snapshot.schema.json`

Le rapport HTML se recette en trois couches :

```bash
python scripts/rapport_html.py --projet . --verifier    # 10 contrôles sur le fichier
python scripts/oracle_interaction.py <page.html>        # 9 contrôles d'EXÉCUTION
```

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