# Sources de données — matrice et dégradations

À charger en **R0**, pour déclarer honnêtement ce qui sera mesurable avant d'analyser.

## Principe

Le skill tourne **sans aucun export**. Dans ce mode, 53 nœuds sur 87 restent instrumentés et 24 basculent en non mesurable (comptes pour une étude `local`, qui mobilise toute la grille ; sur un autre modèle, les nœuds hors portée s'ajoutent). Ce n'est pas un échec : c'est un périmètre, et il doit être annoncé en tête de livrable, pas découvert en annexe.

Ce qui est interdit : combler un trou de source par une valeur plausible. Voir garde-fous 1 et 2 du `SKILL.md`.

## Ce que le runtime possède réellement

| Capacité | Ce qu'elle permet | Limite dure à déclarer |
|---|---|---|
| Récupération d'URL | HTML, en-têtes, codes HTTP, balises, schema, liens | **pas de rendu JavaScript** — un site en rendu client est partiellement aveugle |
| Recherche web | SERP approximée, mentions, avis, veille | **pas de position exacte**, pas de SERP features fiables, pas de géolocalisation contrôlée → preuves en `[T3]`, jamais `[T1]` |
| Scripts | crawl en série, parsing, agrégation | à écrire ; coût en temps à compter dans le plafond de run |
| Lecture de fichiers | exports client déposés localement | — |
| Connecteur Google Drive | lecture d'exports déposés par le client | l'export reste un fichier, pas une API |

**Absents, sans exception** : Google Search Console, Google Analytics, index de backlinks (Ahrefs / Semrush / Majestic), source de volume de recherche, logs serveur, navigateur headless.

## Matrice source → nœuds

| Source | Statut | Nœuds servis | Si absente |
|---|---|---|---|
| **Crawl + HTTP + HTML** | disponible | 1, 2, 4, 11-16, 18, 20-27, 30-33, 42, 49, 50, 53, 56, 59, 62, 66, 74, 75, 77 | — |
| **Recherche web** | disponible | 2, 4, 5, 18, 20, 23, 41, 47, 51, 54, 55, 58, 59, 60, 61, 80 | — |
| **Déclaratif client** | à demander | 63-67, 76 | nœud non renseigné, à marquer `à collecter` (pas `non mesurable`) |
| **Export GSC** | à demander | 5, 17, 19, 34-37, 39, 43, 48, 52, 68, 69, 70, 73, 74, 75 | **16 nœuds** en non mesurable |
| **Export GA** | à demander | 10, 44, 45, 46, 71, 75 | **5 nœuds** en non mesurable |
| **CRM / e-commerce** | à demander | 7, 8, 10, 71, 72 | **4 nœuds** en non mesurable |
| **Index de backlinks** | payant | 9, 38, 40, 42, 55 | dégradation partielle documentée, jamais un chiffre inventé |
| **Source de volume** | payant | 3, 6 | volume remplacé par les impressions GSC comme **plancher observé**, ou déclaré inconnu |
| **Logs serveur** | rarement obtenu | 29 | 1 nœud en non mesurable — budget de crawl invisible |

*Certains nœuds apparaissent sur plusieurs lignes : ils sont partiellement servis par une source et complétés par une autre.*

## Impact à annoncer en R0, par export manquant

Formulations à reprendre telles quelles dans le livrable.

### Sans export Google Search Console

> Aucune donnée de performance en recherche n'est disponible. **Positions, impressions, clics et CTR SERP sont déclarés non mesurables** (garde-fou 2). Sont également non mesurables : la distribution du trafic sur la longue traîne, les requêtes sous-exploitées, l'état de couverture d'indexation déclaré par Google, le délai de découverte des nouvelles pages, l'indexation des pages profondes, le ratio d'indexation de masse, les pics de trafic, et la hiérarchisation des contenus à renforcer par potentiel de gain.
>
> Conséquence sur la stratégie : les cibles chiffrées à 12 et 24 mois n'ont **pas de baseline**. Elles sont construites sur le potentiel des requêtes cibles seul, avec une incertitude nettement plus large — à déclarer dans la note de sensibilité.

### Sans export Google Analytics

> Le comportement des visiteurs et l'origine du trafic hors recherche ne sont pas mesurables SANS export fourni : trafic référent, trafic social, comportement post-clic, leads attribués à l'organique. La vitesse de monétisation reste inconnue.
>
> Conséquence : aucun gain ne peut être exprimé en leads. Les gains restent exprimés en trafic qualifié, et la conversion en leads est signalée comme non calculable (nœud 84).

### Sans données CRM ou e-commerce

> La valeur d'un client et le revenu par page sont inconnus. **Aucun gain ne peut être exprimé en euros.** Toute estimation de retour sur investissement est déclarée non calculable plutôt qu'approchée.

### Sans index de backlinks

> Le profil de liens entrants n'est connu que par les liens détectables en recherche web — une fraction non quantifiable du profil réel.

> **Part IA du trafic référent (décision du 11/08/2026, nœud 44)** : quand l'export GA
> est fourni, les référents des assistants génératifs (chatgpt.com, perplexity.ai,
> copilot.microsoft.com, gemini.google.com, claude.ai…) sont isolés et datés — la liste
> des domaines se rafraîchit par vérification web datée à chaque run, jamais récitée. La difficulté SEO est estimée par un **proxy structurel** (force des marques présentes en top 10, ancienneté et profondeur des pages classées) et non par un score d'autorité. Ce proxy est un classement relatif, pas une mesure : ne jamais le présenter comme un score de difficulté d'outil.

### Sans logs serveur

> Le budget de crawl réel, la fréquence de passage de Googlebot et le crawl gaspillé sont invisibles. Les recommandations de crawl portent sur ce qui est **structurellement** observable (obstacles, redirections, profondeur), pas sur le comportement réel du robot.

### Si le site rend son contenu en JavaScript côté client

> Le crawl ne dispose pas de rendu JavaScript. Le contenu injecté côté client est invisible à la collecte : les nœuds de contenu, de maillage interne et de balisage concernés basculent en `non mesurable — rendu JS`, avec la liste des gabarits affectés. Ne pas conclure à l'absence d'un contenu qui pourrait simplement ne pas être dans le HTML initial.

## Étiquetage des preuves — rappel opérationnel

| Étiquette | Origine | Exemple de formulation correcte |
|---|---|---|
| `[T1 observé]` | crawl, HTTP, HTML, rendu | « 34 des 120 pages échantillonnées portent une canonical vers une URL en 301 `[T1 observé]` » |
| `[T2 déclaré]` | export client — **période obligatoire** | « 12 400 clics organiques sur la période 2026-02-01 → 2026-07-31 `[T2 déclaré, GSC]` » |
| `[T3 tiers]` | source nommée + URL + date | « le top 3 de la requête X est occupé par A, B et C `[T3, recherche web, consulté le 2026-08-08]` » |
| `[T4 inféré]` | hypothèse — fourchette et calcul visibles | « gain estimé entre 900 et 2 100 clics/mois `[T4 inféré]` : 14 requêtes × 4 800 impressions cumulées × passage d'un CTR de 1,2 % à 4-6 % » |

Un chiffre sans étiquette est un défaut de livraison. Un `[T4]` sans calcul visible et sans fourchette est un défaut de livraison.
