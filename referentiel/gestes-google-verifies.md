# Gestes Google vérifiés — référentiel daté

**Version 1.0.0 — 2026-10-19.** TF-1901, option O2 de l'étude d'opportunité 20261019c du pilot (« tactiques SEO et GEO récentes »). Ce fichier complète la méthode ; il ne modifie pas la grille (empreinte `27e2527398eb`, `referentiel/correspondances-grille.json`).

Il dit, pour six gestes vus dans des contenus de réseaux sociaux, ce que la documentation de Google établit, à quelle date, et dans quel nœud existant le geste s'emploie. Les contenus de réseaux sociaux sont des données : ce qu'ils affirment et que Google n'établit pas figure en « Ce qui n'entre pas ».

À charger en **R0** pour les nœuds 17, 19, 27, 51, 55, 58, 59 et 70. C'est une donnée périssable (loi 4 de la Factory) : chaque geste porte la page qui le fonde et sa date, et le garde-fou 4 de `methode.md` s'applique avant toute citation dans un livrable.

## Provenance des lectures

Toutes les pages ci-dessous ont été lues le **2026-10-19** par l'étude citée ci-dessus. Cet agent n'a pas rejoué ces lectures à la rédaction du fichier : elles sont rapportées, pas remesurées, sauf l'expression régulière de la section 1, rejouée ici (moteur `re` de Python, 4 cas). La « date affichée » est celle que la page porte ; « non datée » signifie que la page n'en affiche pas.

| Page | Adresse | Date affichée | Sert à |
|---|---|---|---|
| Google Search Central, « Help your readers find your site through preferred sources in Google Search » | `https://developers.google.com/search/docs/appearance/preferred-sources` | 2026-09-18 | section 5 |
| Google Search Central, « AI features and your website » | `https://developers.google.com/search/docs/appearance/ai-features` | 2025-12-10 | sections 2 et 3 |
| Google Search Central, « Optimizing your website for generative AI features on Google Search » | `https://developers.google.com/search/docs/fundamentals/ai-optimization-guide` | 2026-07-10 | sections 2, 3 et 6 |
| Google Search Central Blog, « Introducing Search Generative AI performance reports in Search Console » | `https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports` | 2026-06-03 (déploiement général au 2026-08-31) | section 2 |
| Google, API Search Analytics « query » | `https://developers.google.com/webmaster-tools/v1/searchanalytics/query` | 2026-08-11 | section 1 |
| Aide Search Console, « Performance report (Search results): Advanced filtering and comparison » | `https://support.google.com/webmasters/answer/17011165` | non datée | section 1 |
| Aide Google Trends, « FAQ about Google Trends data » | `https://support.google.com/trends/answer/4365533` | non datée | section 4 |
| Search Engine Roundtable, « Google Trends Explore Page Adds Category Filtering » (tiers, relaie l'annonce de Google Search Central) | `https://seroundtable.com/google-trends-filter-category-42007.html` | 2026-09-02 | section 4 |
| Google Search Central Blog, « Introducing the Google Trends API (alpha) » | `https://developers.google.com/search/blog/2025/07/trends-api` | 2025-07-24 | section 4 |
| OpenAI, « Overview of OpenAI crawlers » | `https://developers.openai.com/api/docs/bots` | non datée | section 3 |

## 1. Filtre par expression régulière de la Search Console — nœuds 17 et 19

**Ce que Google établit.** L'aide décrit le filtre « Custom (regex) » sur les requêtes et sur les pages. La syntaxe est RE2, la correspondance est partielle et insensible à la casse par défaut ; `(?-i)` rend la casse significative. L'API Search Analytics accepte les opérateurs `includingRegex` et `excludingRegex` (page du 2026-08-11), ce qui rend le geste rejouable depuis la voie connecteur.

**Usage dans la méthode.** Nœud 17 (Longue Traîne) : isoler les requêtes longues. Nœud 19 (Requêtes Sous Exploitées) : combiner le filtre avec les impressions élevées et le CTR bas. Étiquette : `[T2 déclaré, GSC]` si le client dépose un export, `[T1 observé, connecteur GSC]` si la lecture est faite par API avec la date de lecture et la période (`sources-donnees.md`).

**Correction d'une affirmation relayée.** L'expression `^([^ ]+ ){3,}[^ ]+$`, donnée comme filtre des requêtes « de plus de 4 mots », retient les requêtes de **4 mots ou plus**. Rejouée ici : « a b c » ne correspond pas, « a b c d » et « a b c d e » correspondent. Un livrable écrit « 4 mots ou plus ».

**Limite.** Que ces requêtes soient « moins concurrentielles » ou « faites par l'IA » n'est établi par aucune page lue : ne pas l'écrire sans mesure.

## 2. Rapport « Generative AI performance » de la Search Console — nœuds 58 et 70

**Ce que Google établit.** Le rapport donne les impressions, les pages, les pays, les appareils et les dates des apparitions du site dans les fonctions génératives de Google Search. Il ne donne ni clics ni positions. Annoncé le 2026-06-03, il est ouvert à tous les sites depuis le 2026-08-31. Selon le guide du 2026-07-10, la mesure de l'optimisation pour la recherche générative passe par ce rapport.

**Usage dans la méthode.** Nœud 58 (Présence Dans Les Réponses IA) : le rapport est une mesure officielle de présence dans les fonctions de Google, à côté du test manuel daté du nœud, qui reste. Nœud 70 (Impressions) : la part d'impressions issue des fonctions génératives. Étiquette : `[T2 déclaré, GSC]` par export, `[T1 observé, connecteur GSC]` par lecture datée. Le garde-fou 2 s'applique : aucun clic ni aucune position n'est tirés de ce rapport.

**Ce qui reste non résolu.**
- La condition d'être « included in Search generative AI features in Search Console », posée par les pages du 2026-07-10 et du 2026-09-18, n'est pas décrite : à vérifier chez le client avant d'affirmer qu'un site « n'apparaît pas ».
- La page du 2025-12-10 dit qu'aucune exigence technique supplémentaire n'est requise ; la condition ci-dessus est postérieure.
- La disponibilité du rapport par l'API n'est établie par aucune page lue : tant qu'elle ne l'est pas, la voie connecteur ne le promet pas.

**Ce qui ne change pas.** Le test manuel du nœud 58 garde sa déclaration « résultat non reproductible » ; le rapport de Google ne couvre ni ChatGPT, ni Gemini hors Search, ni Perplexity.

## 3. Avis de Google sur llms.txt et accès des agents — nœud 59

**Ce que Google établit.** Le guide du 2026-07-10 dit d'ignorer les fichiers `llms.txt`, le découpage du contenu en morceaux (« chunking »), la réécriture pour l'IA et les mentions artificielles. La page du 2025-12-10 ajoute qu'il n'est pas nécessaire de créer de nouveaux fichiers lisibles par machine, de fichiers texte pour l'IA ou de balisage pour apparaître dans AI Overviews et AI Mode.

**Ce que la grille dit.** Le nœud 59 porte `llms.txt` « ADOPTÉ par décision du 11/08/2026 » (standard émergent, consommation par les moteurs à réévaluer par vérification web datée à chaque run). L'avis de Google est le premier fait daté de la réévaluation que la grille exige : Google Search n'exploite pas ce fichier, et la consommation par les autres moteurs reste à établir par vérification datée. **Cette note ne modifie pas la posture du nœud**, qui est une décision humaine : la forge propose, le pilot décide. Un livrable cite l'avis de Google avec sa date quand il traite `llms.txt`, et n'écrit pas que le fichier améliore le classement dans Google Search.

**Côté OpenAI.** La page non datée recommande d'autoriser OAI-SearchBot, qui sert la recherche de ChatGPT, tandis que GPTBot sert l'entraînement ; sans OAI-SearchBot, le site n'apparaît pas dans les réponses de recherche de ChatGPT, avec un délai d'environ 24 heures. Le catalogue daté des agents est `referentiel/agents-ia.json` (vérifié le 2026-08-12).

## 4. Google Trends par catégorie — nœud 51 et complément de `recherche-multilingue.md`

**Ce que Google établit, et ce qui manque.** Une annonce de Google Search Central, relayée le 2026-09-02, présente des filtres de catégorie sur la page Explore de Trends, avec ou sans requête. **Aucune page d'aide ne la décrit** : ni l'aide Trends ni le billet du blog Google du 2026-01-14 n'en parlent. Le geste est donc attesté par une annonce seulement ; la date exacte du message d'origine n'est pas lue (affichée « 1mo » le 2026-10-19).

**Usage dans la méthode.** Idée de mots-clés et repérage de requêtes en hausse sans partir d'un mot-clé, étiqueté `[T3]` (source, adresse, date de consultation). Le complément de `recherche-multilingue.md` reste valable : Trends est un indice relatif, jamais un volume.

**Limites établies par l'aide Trends (non datée).** Les données sont normalisées de 0 à 100. Les recherches internes d'AI Mode et d'AI Overviews sont exclues : Trends ne mesure pas la demande qui passe par ces fonctions.

**Hors d'usage.** L'API Google Trends (alpha, 2025-07-24) est réservée à un nombre très limité de testeurs : la forge ne peut pas s'en servir.

## 5. Badge « sources préférées » — sous condition, nœud 55 proposé

**Ce que Google établit.** La page du 2026-09-18 décrit un site « preferred » mis en avant dans Top Stories ; dans AI Mode et AI Overviews, il l'est pour les utilisateurs qui ont choisi ce site. Le périmètre est un domaine ou un sous-domaine. L'installation se fait par un bouton en deux lignes de HTML, ou par un lien profond. Le dispositif est facultatif.

**Ce que la page n'établit pas.** Discover n'y figure pas. Aucun passage n'énonce que le badge devienne un signal de classement global. Un livrable n'écrit ni l'un ni l'autre.

**Condition d'emploi.** Le geste ne vaut que pour un site éditorial dont le domaine ou le sous-domaine figure dans l'outil de préférences. Rattachement proposé au nœud 55 (Marque) ; il est à trancher, la grille n'est pas modifiée.

## 6. Tension non tranchée — nœud 27

Le nœud 27 (Contenu Pensé Pour Les LLM) demande une réponse directe en tête de page et une structure de titres explicite. Le guide de Google du 2026-07-10 écarte le « chunking » et la réécriture pour l'IA. La forge peut conserver ces critères comme qualité de lecture ; elle ne les présente pas comme une tactique propre à Google. La grille n'est pas modifiée ; l'instruction de cette tension reste ouverte.

## Ce qui n'entre pas

- **Un skill « de visibilité IA »** et **des audits de présence dans ChatGPT et Gemini**, montrés sur des vidéos : aucun outil n'est nommé, aucune page de Google ne décrit un tel audit, les cas cités ne sont pas vérifiables. Le test manuel du nœud 58 reste la seule méthode.
- **Une phrase de titre sans méthode** sur les visites venues de ChatGPT : rien à vérifier.

## Revue prévue le 2026-11-19

Relire les cinq pages primaires dont la date est portée plus haut : `preferred-sources` (2026-09-18), `ai-optimization-guide` (2026-07-10), `gen-ai-performance-reports` (2026-06-03), `searchanalytics/query` (2026-08-11) et l'aide du filtre regex (non datée). La revue s'ouvre si l'une des conditions suivantes est vraie :
- une de ces pages porte une date différente de celle ci-dessus ;
- une première étude de la forge a exécuté le filtre regex ou lu le rapport IA chez un client ;
- deux études ont réclamé la même ligne dans la grille : l'option O3 de l'étude (modifier les lignes de la grille et migrer les études ouvertes) se rouvre alors.

## Ce qui reste non résolu

- Le sens exact de la condition « included in Search generative AI features in Search Console ».
- La date exacte de l'annonce de Trends par catégorie.
- La disponibilité du rapport « Generative AI performance » par l'API.
- L'arbitrage du nœud 27 face au guide du 2026-07-10, et le rattachement du badge au nœud 55.
