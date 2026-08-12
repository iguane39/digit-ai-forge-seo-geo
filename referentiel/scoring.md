# Scoring et priorisation

À charger en **R4**. Trois échelles ancrées, une formule, un trait de coupe, trois horizons.

Règle transversale : une note posée sans pouvoir désigner le cran de l'échelle qui la justifie n'est pas une note, c'est une impression. Chaque action doit citer le cran retenu.

---

## GAIN 1-5

Le gain se lit sur **deux registres**. Le registre trafic est toujours disponible ; le registre business ne l'est que si les nœuds 8 (`Valeur Du Client`) et 67 (`Revenu Par Page`) sont renseignés. **Si le registre business est indisponible, note sur le trafic seul et déclare-le — n'invente pas d'équivalent en euros.**

| Cran | Registre trafic qualifié | Registre business (si valeur client connue) |
|---|---|---|
| **1** | effet marginal ou indirect : < 2 % du trafic organique du site, ou un gain non attribuable à une page précise | < 1 lead supplémentaire par mois |
| **2** | gain localisé sur une poignée de pages secondaires : 2-5 % du trafic organique | 1-2 leads par mois |
| **3** | gain net sur un silo ou une famille de requêtes : **5-15 % du trafic organique**, mesurable sur un groupe de pages identifié | 3-8 leads par mois, ou déblocage d'une famille de requêtes commerciales |
| **4** | gain structurant : 15-40 % du trafic organique, ou ouverture d'un territoire nouveau à demande démontrée | 9-25 leads par mois |
| **5** | changement de palier : **> 40 % du trafic organique**, ou levée d'un blocage qui empêche toute progression (site non indexable, pages money absentes, cannibalisation généralisée) | > 25 leads par mois, ou déblocage du canal organique entier |

Les pourcentages se lisent sur la baseline du run. **Sans baseline GSC, le gain est noté sur le potentiel des requêtes cibles, et la note porte la mention `sans baseline` — la confiance est alors plafonnée à 2.**

---

## EFFORT 1-5

Ancré en **jours-homme**, avec la compétence requise. Compter la mise en œuvre complète : conception, réalisation, recette, publication.

| Cran | Charge | Compétence typique | Exemple |
|---|---|---|---|
| **1** | < 0,5 j-h | n'importe qui avec les accès | corriger un `robots.txt`, ajouter un sitemap, réécrire 10 balises `title` |
| **2** | 0,5 à 2 j-h | rédacteur ou intégrateur | réécrire une page, poser un balisage schema sur un gabarit, fusionner deux pages |
| **3** | 2 à 10 j-h | SEO senior, ou dev + rédacteur | produire une page pilier documentée, restructurer le maillage d'un silo, corriger les canonicals d'un gabarit |
| **4** | 10 à 30 j-h | équipe, ou prestation externe | ouvrir un silo complet (10-20 contenus), refondre l'architecture d'URL avec plan de redirection, monter un dispositif de contenu programmatique |
| **5** | > 30 j-h | projet, arbitrage de direction | migration de domaine, refonte technique, campagne de netlinking sur 6 mois, création d'un média |

Si une action exige une compétence **absente** chez le client et non budgétée, l'effort monte d'un cran et le coût bascule en `PAYANT`.

---

## CONFIANCE 1-5

Force de la preuve **derrière l'estimation de gain** — pas la certitude que l'action est réalisable.

| Cran | Fondement |
|---|---|
| **1** | analogie sectorielle ou intuition ; aucune donnée propre au site |
| **2** | preuve structurelle uniquement (`[T1]` sur le défaut, mais aucune mesure de son coût réel), **ou** absence de baseline |
| **3** | preuve `[T1]` du défaut **et** ordre de grandeur du volume concerné établi |
| **4** | preuve `[T2]` du manque à gagner (impressions sans clic, position 11-30 à volume établi) |
| **5** | preuve `[T2]` **et** précédent mesuré sur ce site même (une action comparable a déjà produit l'effet, tracé dans un snapshot antérieur) |

Le cran 5 est **inatteignable au premier run** : il exige un historique. Le déclarer plutôt que de le forcer.

---

## Formule de priorisation

```
Priorité = (Gain × Confiance) / Effort
```

Amplitude : 0,2 (gain 1, confiance 1, effort 5) à 25 (gain 5, confiance 5, effort 1).

La confiance est au **numérateur** délibérément : une action à fort gain supposé mais non étayé doit reculer derrière une action à gain moyen et prouvé. C'est ce qui empêche la liste de se remplir de paris.

### Trait de coupe

| Score | Décision |
|---|---|
| **≥ 6** | à engager sur les deux premiers trimestres |
| **2 à 6** | backlog qualifié — à engager quand la capacité se libère, ou après avoir levé l'incertitude qui plafonne la confiance |
| **< 2** | ne pas engager, **sauf si l'action est une dépendance** d'une action au-dessus du trait (voir ci-dessous) |

### Exception de dépendance

Une action sous le trait de coupe remonte au-dessus si une action prioritaire en dépend. Exemples réels : poser la mesure avant d'optimiser, corriger l'indexabilité avant de produire du contenu, restructurer l'architecture avant de créer les pages money. **Toute remontée par dépendance est nommée dans le livrable** : `remontée — prérequis de l'action #N`.

### Ajustement par la capacité déclarée

Le trait de coupe est un tri, pas un plan. Confronte la somme des efforts des actions retenues à la capacité mensuelle déclarée au cadrage :

- si la somme dépasse la capacité sur 4 trimestres, **coupe par le bas et dis ce qui a été coupé** — un plan de 40 actions pour une capacité de 2 j-h par mois est un plan qui ne sera pas exécuté ;
- si la capacité n'est pas déclarée, produis la liste complète **et** signale qu'aucun trait de coupe réaliste n'est possible.

Ne jamais présenter une liste que la capacité connue ne permet pas d'exécuter sans dire, en clair, combien de trimestres elle représente réellement.

---

## HORIZON

Étiquette obligatoire, indépendante du score. Elle empêche une correction technique de 2 heures de concurrencer une stratégie de contenu de 8 mois sur la même liste.

| Horizon | Délai avant effet mesurable | Nature |
|---|---|---|
| `quick-win` | < 1 mois | correction, déblocage, optimisation d'existant |
| `structurant` | 1 à 6 mois | production de contenu, restructuration, balisage à l'échelle |
| `fondation` | > 6 mois | autorité, entité de marque, actif cumulatif, nouveau territoire |

**Le délai avant effet mesurable est distinct du délai de réalisation.** Une réécriture de balises `title` se fait en une journée mais ne se mesure qu'après réindexation. Renseigner les deux dans le CSV.

---

## Colonnes obligatoires du CSV d'actions

```
id · action · volet · noeuds_couverts · gain · cran_gain_cite · effort · cran_effort_cite ·
confiance · cran_confiance_cite · score · horizon · delai_realisation · delai_effet_mesurable ·
critere_acceptation · hypothese_structurante · axe_execution · regime_automatisation ·
axe_cout · cout_eur · trimestre_cible · dependance_de
```

### Critère d'acceptation — la colonne qui filtre les vœux

Le critère doit être **vérifiable par quelqu'un d'autre, sans jugement**. Test simple : deux personnes qui le lisent doivent trancher pareil.

| Rejeté | Accepté |
|---|---|
| « améliorer le maillage interne » | « les 8 pages money reçoivent chacune ≥ 3 liens internes contextuels depuis leur silo, hors menu et pied de page » |
| « optimiser les titres » | « les 40 balises `title` des pages du silo X sont uniques, ≤ 60 caractères, et contiennent la requête cible » |
| « travailler l'autorité » | « 5 domaines référents thématiquement proches, non présents au snapshot initial, pointent vers une page du silo X » |
| « améliorer la performance » | « les métriques de terrain des 3 gabarits principaux passent au vert sur mobile, mesurées sur données CrUX » |

Une action dont le critère ne passe pas ce test est reformulée ou supprimée. Elle n'est jamais livrée telle quelle.
