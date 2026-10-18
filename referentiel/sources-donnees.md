# Sources de données — matrice et dégradations

**Version 1.1.0 — 2026-10-18.** TF-1854 : voie « connecteur » ouverte pour Search Console et Google Analytics 4, à côté de la voie « export » (décision humaine D-27 (a) du 18/10/2026). La version 1.0.0 est l'état antérieur, qui ne portait pas de numéro.

À charger en **R0**, pour déclarer honnêtement ce qui sera mesurable avant d'analyser.

## Principe

Le skill tourne **sans aucun export ni connecteur**. Dans ce mode, 53 nœuds sur 87 restent instrumentés et 24 basculent en non mesurable (comptes pour une étude `local`, qui mobilise toute la grille ; sur un autre modèle, les nœuds hors portée s'ajoutent). Ce n'est pas un échec : c'est un périmètre, et il doit être annoncé en tête de livrable, pas découvert en annexe.

Pour Search Console et Google Analytics 4, ce périmètre dépend de la voie ouverte : **export** déposé par le client, **connecteur** (lecture seule avec le compte du client), ou aucune des deux. La section « Deux voies » ci-dessous dit laquelle donne quoi.

Ce qui est interdit : combler un trou de source par une valeur plausible. Voir garde-fous 1 et 2 du `SKILL.md`.

## Ce que le runtime possède réellement

Ce tableau dit ce que la session peut faire d'elle-même, et la limite dure de chaque capacité à déclarer dans le livrable.

| Capacité | Ce qu'elle permet | Limite dure à déclarer |
|---|---|---|
| Récupération d'URL | HTML, en-têtes, codes HTTP, balises, schema, liens | **pas de rendu JavaScript** — un site en rendu client est partiellement aveugle |
| Recherche web | SERP approximée, mentions, avis, veille | **pas de position exacte**, pas de SERP features fiables, pas de géolocalisation contrôlée → preuves en `[T3]`, jamais `[T1]` |
| Scripts | crawl en série, parsing, agrégation | à écrire ; coût en temps à compter dans le plafond de run |
| Lecture de fichiers | exports client déposés localement | — |
| Connecteur Google Drive | lecture d'exports déposés par le client | l'export reste un fichier, pas une API |
| Connecteur Google en lecture (voie « connecteur ») | Search Console et Google Analytics 4, lus par API avec le compte du client | **ouvert seulement quand le client donne son accès**, en portées de lecture ; sans accès, la voie est fermée. Chaque mesure est datée → `[T1 observé]` |

**Absents, sans exception** : index de backlinks (Ahrefs / Semrush / Majestic), source de volume de recherche, logs serveur, navigateur headless.

**Google Search Console et Google Analytics 4 ne sont plus « absents sans exception »** : le runtime les lit par la voie connecteur, quand le client ouvre son accès. Sans cet accès, la voie est fermée et seul l'export les apporte ; sans export non plus, ils sont absents et les nœuds qui en dépendent restent non mesurables. Ce que la voie exige : section suivante.

## Deux voies pour Search Console et Google Analytics 4

Cette section dit comment une donnée de Search Console ou de Google Analytics 4 entre dans l'étude : par l'export du client ou par une lecture avec son compte, et ce que chaque voie engage en date et en niveau de preuve.

| | Voie **export** (inchangée) | Voie **connecteur** (ouverte le 18/10/2026) |
|---|---|---|
| Ce que c'est | fichier produit et déposé par le client dans `donnees/gsc/` ou `donnees/ga/` | lecture par API, faite pendant la mission avec le compte du client, déposée telle quelle dans le même dossier |
| Accès demandé | aucun | un accès du client à sa propriété, en lecture |
| Étiquette | `[T2 déclaré, GSC]` / `[T2 déclaré, GA]` | `[T1 observé, connecteur GSC]` / `[T1 observé, connecteur GA4]` |
| Date portée par la mesure | **période** obligatoire | **date de lecture** ET période interrogée, obligatoires toutes deux |

Règles de la voie connecteur — elles se cumulent :

1. **Lecture seule.** Seules les portées de lecture sont demandées : une portée qui accorde l'écriture est un défaut, même si la lecture fonctionne. Les portées en vigueur sont données par la procédure de connexion (dernier point).
2. **Le compte du client, jamais un compte de la forge.** La forge ne détient aucun compte Google, aucun jeton, aucune clé. L'accès est celui du client ; ce qui sert la lecture n'est écrit ni dans la forge, ni dans l'étude, ni dans un commit.
3. **Une date de lecture par mesure.** Chaque mesure issue du connecteur porte la date à laquelle elle a été lue et la période interrogée, dans son champ `source` du snapshot et dans les « Preuves » de la fiche, sous la forme `connecteur GSC, lu le AAAA-MM-JJ, période AAAA-MM-JJ → AAAA-MM-JJ` (`connecteur GA4` pour Google Analytics 4). Une lecture sans date n'est pas un `[T1 observé]` : elle n'entre pas dans le livrable. Le contrôle 6 de `validate.py --mission` la refuse.
4. **Le niveau de preuve suit la voie.** Une lecture par API datée est `[T1 observé]` ; un export reste `[T2 déclaré]`. Une lecture ne se déclasse pas en T2 pour la forme, un export ne se promeut pas en T1.
5. **La réponse se dépose avant d'être citée.** La réponse d'API est déposée, datée, dans `donnees/gsc/` ou `donnees/ga/` : c'est une donnée du client, avec la même garde de confidentialité que l'export.
6. **Aucune donnée de client, aucun identifiant de compte ni de propriété dans la forge.** Ce référentiel n'en porte pas ; la propriété lue se nomme dans le cadrage de l'étude du client, nulle part ici.
7. **Voie fermée = retombée, pas invention.** Sans accès du client, on demande l'export ; sans export, les nœuds restent non mesurables, comme avant. Aucune valeur n'est comblée (garde-fous 1 et 2 de `methode.md`).
8. **La procédure de connexion n'est pas recopiée ici**, parce que c'est une donnée périssable. Elle vit dans le référentiel du pilot, sous la racine du pilot (`$FORGE_ROOT\digit-ai-factory`) : `references/INTEGRATIONS-FOURNISSEURS.md`, sections « Google — se connecter : voie OAuth « utilisateur » ou compte de service », « Google Analytics 4 — API, portées et lecture » et « Search Console — API, portées et lecture », vérifiées le 18/10/2026. Ce document introuvable, on s'arrête et on demande, on ne reconstitue pas la procédure de mémoire.

**Statut `EX` de la grille.** La légende de la grille dit « instrumenté si export fourni — sinon non mesurable ». Pour les nœuds dont la source est Search Console ou Google Analytics, elle se lit : *export fourni **ou** lecture connecteur datée*. La lettre de la légende n'est pas modifiée, pour ne pas changer l'empreinte de la grille ; ce renvoi tient lieu de correctif.

## Matrice source → nœuds

La matrice dit, pour chaque source, si elle est disponible, quels nœuds elle sert et ce qui devient non mesurable quand elle manque.

| Source | Statut | Nœuds servis | Si absente |
|---|---|---|---|
| **Crawl + HTTP + HTML** | disponible | 1, 2, 4, 11-16, 18, 20-27, 30-33, 42, 49, 50, 53, 56, 59, 62, 66, 74, 75, 77 | — |
| **Recherche web** | disponible | 2, 4, 5, 18, 20, 23, 41, 47, 51, 54, 55, 58, 59, 60, 61, 80 | — |
| **Déclaratif client** | à demander | 63-67, 76 | nœud non renseigné, à marquer `à collecter` (pas `non mesurable`) |
| **Export GSC** | à demander | 5, 17, 19, 34-37, 39, 43, 48, 52, 68, 69, 70, 73, 74, 75 | sans export **ni connecteur** : **16 nœuds** en non mesurable |
| **Connecteur GSC** (lecture seule, compte du client) | à ouvrir avec le client | les mêmes nœuds que la ligne « Export GSC » | ces **16 nœuds** sont mesurables tant que la voie est ouverte, `[T1 observé]` ; voie fermée : retour à l'export, puis **16 nœuds** non mesurables |
| **Export GA** | à demander | 10, 44, 45, 46, 71, 75 | sans export **ni connecteur** : **5 nœuds** en non mesurable |
| **Connecteur GA4** (lecture seule, compte du client) | à ouvrir avec le client | les mêmes nœuds que la ligne « Export GA » | ces **5 nœuds** sont mesurables tant que la voie est ouverte, `[T1 observé]` ; voie fermée : retour à l'export, puis **5 nœuds** non mesurables |
| **CRM / e-commerce** | à demander | 7, 8, 10, 71, 72 | **4 nœuds** en non mesurable |
| **Index de backlinks** | payant | 9, 38, 40, 42, 55 | dégradation partielle documentée, jamais un chiffre inventé |
| **Source de volume** | payant | 3, 6 | volume remplacé par les impressions GSC comme **plancher observé**, ou déclaré inconnu |
| **Logs serveur** | rarement obtenu | 29 | 1 nœud en non mesurable — budget de crawl invisible |

*Certains nœuds apparaissent sur plusieurs lignes : ils sont partiellement servis par une source et complétés par une autre.*

## Impact à annoncer en R0, par export manquant

Formulations à reprendre telles quelles dans le livrable.

### Sans export ni connecteur Google Search Console

> Aucune donnée de performance en recherche n'est disponible, ni par export du client ni par lecture avec son compte. **Positions, impressions, clics et CTR SERP sont déclarés non mesurables** (garde-fou 2). Sont également non mesurables : la distribution du trafic sur la longue traîne, les requêtes sous-exploitées, l'état de couverture d'indexation déclaré par Google, le délai de découverte des nouvelles pages, l'indexation des pages profondes, le ratio d'indexation de masse, les pics de trafic, et la hiérarchisation des contenus à renforcer par potentiel de gain.
>
> Conséquence sur la stratégie : les cibles chiffrées à 12 et 24 mois n'ont **pas de baseline**. Elles sont construites sur le potentiel des requêtes cibles seul, avec une incertitude nettement plus large — à déclarer dans la note de sensibilité.

### Sans export ni connecteur Google Analytics

> Le comportement des visiteurs et l'origine du trafic hors recherche ne sont pas mesurables SANS export fourni ni lecture connecteur datée : trafic référent, trafic social, comportement post-clic, leads attribués à l'organique. La vitesse de monétisation reste inconnue.
>
> Conséquence : aucun gain ne peut être exprimé en leads. Les gains restent exprimés en trafic qualifié, et la conversion en leads est signalée comme non calculable (nœud 84).

### Sans données CRM ou e-commerce

> La valeur d'un client et le revenu par page sont inconnus. **Aucun gain ne peut être exprimé en euros.** Toute estimation de retour sur investissement est déclarée non calculable plutôt qu'approchée.

### Sans index de backlinks

> Le profil de liens entrants n'est connu que par les liens détectables en recherche web — une fraction non quantifiable du profil réel.

> **Part IA du trafic référent (décision du 11/08/2026, nœud 44)** : quand l'export GA
> est fourni ou la lecture connecteur GA4 ouverte, les référents des assistants génératifs (chatgpt.com, perplexity.ai,
> copilot.microsoft.com, gemini.google.com, claude.ai…) sont isolés et datés — la liste
> des domaines se rafraîchit par vérification web datée à chaque run, jamais récitée. La difficulté SEO est estimée par un **proxy structurel** (force des marques présentes en top 10, ancienneté et profondeur des pages classées) et non par un score d'autorité. Ce proxy est un classement relatif, pas une mesure : ne jamais le présenter comme un score de difficulté d'outil.

### Sans logs serveur

> Le budget de crawl réel, la fréquence de passage de Googlebot et le crawl gaspillé sont invisibles. Les recommandations de crawl portent sur ce qui est **structurellement** observable (obstacles, redirections, profondeur), pas sur le comportement réel du robot.

### Si le site rend son contenu en JavaScript côté client

> Le crawl ne dispose pas de rendu JavaScript. Le contenu injecté côté client est invisible à la collecte : les nœuds de contenu, de maillage interne et de balisage concernés basculent en `non mesurable — rendu JS`, avec la liste des gabarits affectés. Ne pas conclure à l'absence d'un contenu qui pourrait simplement ne pas être dans le HTML initial.

## Étiquetage des preuves — rappel opérationnel

Ce rappel dit quelle étiquette porte chaque origine de donnée, avec un exemple de formulation correcte.

| Étiquette | Origine | Exemple de formulation correcte |
|---|---|---|
| `[T1 observé]` | crawl, HTTP, HTML, rendu ; **lecture par API datée** (connecteur GSC ou GA4, compte du client, lecture seule) | « 34 des 120 pages échantillonnées portent une canonical vers une URL en 301 `[T1 observé]` » ; « 9 800 clics organiques du 2026-09-01 au 2026-09-28, lus le 2026-10-18 `[T1 observé, connecteur GSC]` » |
| `[T2 déclaré]` | export client — **période obligatoire** | « 12 400 clics organiques sur la période 2026-02-01 → 2026-07-31 `[T2 déclaré, GSC]` » |
| `[T3 tiers]` | source nommée + URL + date | « le top 3 de la requête X est occupé par A, B et C `[T3, recherche web, consulté le 2026-08-08]` » |
| `[T4 inféré]` | hypothèse — fourchette et calcul visibles | « gain estimé entre 900 et 2 100 clics/mois `[T4 inféré]` : 14 requêtes × 4 800 impressions cumulées × passage d'un CTR de 1,2 % à 4-6 % » |

Un chiffre sans étiquette est un défaut de livraison. Un `[T4]` sans calcul visible et sans fourchette est un défaut de livraison.
