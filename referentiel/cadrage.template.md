# Cadrage — audit & stratégie SEO

> À remplir avant le run. Copier ce fichier dans le projet cible (par exemple `seo-cadrage.md`) et le compléter.
> Les champs `OBLIGATOIRE` bloquent le run. Les champs `OPTIONNEL` ne le bloquent pas, mais chacun porte l'impact précis de son absence : cet impact sera annoncé en tête du livrable.

---

## 1. Site

| Champ | Statut | Valeur |
|---|---|---|
| URL du site | **OBLIGATOIRE** | |
| Nom de la marque (tel qu'un utilisateur le cherche) | **OBLIGATOIRE** | |
| Sous-domaines à inclure ou exclure | OPTIONNEL — *sans précision, le périmètre est le domaine principal seul, et c'est déclaré* | |
| Ordre de grandeur du nombre de pages | OPTIONNEL — *sans précision, il est établi au crawl ; au-delà de 200 URLs l'échantillonnage s'applique* | |
| Le contenu est-il rendu côté client (JavaScript) ? | OPTIONNEL — *détecté au crawl ; le signaler en amont évite de conclure à tort à l'absence d'un contenu* | |
| Refonte, migration ou changement majeur dans les 12 derniers mois | OPTIONNEL — *sans cette information, une chute de trafic peut être imputée à la mauvaise cause* | |

## 2. Marché

| Champ | Statut | Valeur |
|---|---|---|
| Secteur d'activité | **OBLIGATOIRE** | |
| Modèle d'acquisition — B2B lead-gen / e-commerce / média-affiliation / local / SaaS | **OBLIGATOIRE** — *détermine si la stratégie va au volume ou à la qualification ; une erreur ici invalide tout le volet stratégie* | |
| Pays, langue, zone géographique visée | **OBLIGATOIRE** — *conditionne la SERP analysée* | |
| 3 à 5 concurrents (URLs) | **OBLIGATOIRE** — *sans eux, les nœuds `Concurrence SERP`, `SERP Faibles`, `Comparatifs` et toute comparaison relative sont inexploitables* | |
| 10 à 20 requêtes cibles connues | OPTIONNEL — *sans elles, elles sont déduites du contenu du site et des SERP concurrentes, avec un risque d'écart avec l'intention commerciale réelle* | |
| Requêtes à intention d'achat (« money ») | OPTIONNEL — *sans elles, les nœuds `Pages Money` et `Money Keywords` sont audités sur des cibles déduites, pas déclarées* | |

## 3. Objectif

| Champ | Statut | Valeur |
|---|---|---|
| Objectif business à 12 mois, en une phrase | **OBLIGATOIRE** — *c'est la cible du volet stratégie* | |
| Indicateur qui compte vraiment (trafic / leads / CA / notoriété) | **OBLIGATOIRE** | |
| Contrainte de calendrier (échéance, saisonnalité, lancement) | OPTIONNEL — *sans elle, la trajectoire est séquencée par dépendances techniques uniquement* | |
| Audience du livrable — dirigeant / marketing / technique | **OBLIGATOIRE** — *change le vocabulaire, la profondeur et les KPI mis en avant* | |

## 4. Moyens

| Champ | Statut | Valeur |
|---|---|---|
| Budget mensuel mobilisable (€) | OPTIONNEL — *sans lui, aucun trait de coupe réaliste : la priorisation reste complète mais devient une liste de souhaits, et ce sera dit* | |
| Capacité d'exécution (jours-homme par mois) | OPTIONNEL — *sans elle, la trajectoire ne peut pas être confrontée à la réalité ; le nombre de trimestres réels reste inconnu* | |
| Compétences internes disponibles (rédaction, dev, SEO, data) | OPTIONNEL — *sans elles, les actions exigeant une compétence absente ne sont pas repérées, et leur coût est sous-évalué* | |
| Outils SEO déjà payés (lesquels) | OPTIONNEL — *sans cette information, des actions sont classées `PAYANT` alors que l'outil est déjà là* | |
| Automatisations SEO déjà en place | OPTIONNEL — *renseigne les nœuds 58-62 ; sans elles, l'axe `IA` du dispatch est calibré à l'aveugle* | |

## 5. Accès aux données

Ces exports transforment 24 nœuds non mesurables en nœuds mesurés. Les fournir en CSV, ou les déposer dans un dossier lisible (local ou Google Drive) en indiquant le chemin. Pour Google Search Console et Google Analytics 4, une seconde voie existe : donner à la mission un accès **en lecture seule** avec **votre** compte (voie connecteur, `referentiel/sources-donnees.md`) ; chaque mesure est alors datée et prend le niveau `[T1 observé]`, au lieu de `[T2 déclaré]` pour un export.

| Export | Statut | Fourni ? | Chemin / période |
|---|---|---|---|
| **Google Search Console** — requêtes, pages, impressions, clics, CTR, position (12 mois si possible) | OPTIONNEL — *sans lui ni lecture connecteur, **16 nœuds** en non mesurable : positions, impressions, clics, CTR SERP, longue traîne, requêtes sous-exploitées, couverture d'indexation, découverte, pages profondes, indexation de masse, pics, contenus à renforcer. **La cible chiffrée à 12 mois perd sa baseline***  | | |
| **Google Search Console** — rapport d'indexation des pages | OPTIONNEL — *sans lui, l'état de couverture déclaré par Google reste inconnu* | | |
| **Google Analytics** — sessions, sources, conversions, segment organique | OPTIONNEL — *sans lui ni lecture connecteur, **5 nœuds** en non mesurable : trafic référent, trafic social, comportement post-clic, leads, vitesse de monétisation. **Aucun gain ne peut être exprimé en leads*** | | |
| **CRM / e-commerce** — valeur client, panier moyen, coût du lead | OPTIONNEL — *sans lui, **4 nœuds** en non mesurable. **Aucun gain ne peut être exprimé en euros, et le ROI est déclaré non calculable*** | | |
| **Logs serveur ou CDN** | OPTIONNEL — *sans eux, le budget de crawl réel et le crawl gaspillé restent invisibles (nœud 29)* | | |
| **Accès à un index de backlinks** (Ahrefs, Semrush, Majestic) | OPTIONNEL — *sans lui, le profil de liens est réduit aux liens détectables en recherche web, et la difficulté SEO est estimée par proxy structurel — un classement relatif, pas une mesure* | | |
| **Source de volume de recherche** | OPTIONNEL — *sans elle, le volume est remplacé par les impressions GSC comme plancher observé, ou déclaré inconnu. **Il ne sera jamais estimé de mémoire*** | | |

## 6. Contexte libre

Tout ce qui aide et qui n'entre pas dans les cases : historique SEO, sanctions ou chutes passées, prestataires en place, contraintes techniques (CMS verrouillé, validation juridique des contenus), sujets interdits, projets connexes en cours.

```
[texte libre]
```

---

## Rappel de ce qui ne sera pas fait

Quelles que soient les cases cochées :

- aucun chiffre ne sera avancé sans étiquette de niveau de preuve ;
- aucune position, impression, clic ou CTR SERP ne sera produit sans export Google Search Console ni lecture connecteur datée avec votre compte ;
- aucune projection ne sera présentée comme une prévision : fourchette, calcul visible et note de sensibilité obligatoires ;
- aucun volume de recherche ne sera estimé sans source.

Un nœud déclaré non mesurable est un résultat, pas une lacune du livrable.
