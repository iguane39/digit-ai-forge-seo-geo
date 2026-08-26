---
id: 58
branche: GEO
noeud: Présence Dans Les Réponses IA
volet: TRANSVERSAL
statut_instrumentation: SD
source_requise: "test manuel documenté + vérification web datée du protocole"
doublon_de: null
modeles: b2b-lead-gen,e-commerce,local,media-affiliation,saas
# --- rempli pendant la mission ---
etat: a-faire
motif_hors_perimetre: null
verdict: null
niveau_preuve: null
date_mesure: null
actions_liees: []
# --- plan de mesure (TF-0476) : la grille declare ce resultat NON REPRODUCTIBLE ---
plan_formulations: null
plan_langues: null
plan_surfaces: null
plan_reexecutions: null
plan_dates: null
dispersion: null
---

# GEO / Présence Dans Les Réponses IA

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

La marque ou le site apparaît-il dans les réponses des moteurs génératifs sur ses requêtes cibles ?

## Source requise

test manuel documenté + vérification web datée du protocole

## Reserve du referentiel

> **résultat non reproductible et non stable : le déclarer explicitement, ne jamais présenter le taux comme une métrique de suivi fiable**

> Ce que cela impose ici, et pourquoi. Un verdict affirmatif sans plan de mesure
> est REFUSE par `validate.py` (controle 10) ; le verdict attendu est alors
> « non-mesure » motive. Cinq champs du front-matter, tous obligatoires des lors
> qu un taux est publie :

| Champ | Ce qu il declare | Pourquoi il compte |
|---|---|---|
| `plan_formulations` | combien de formulations distinctes de la meme intention | l hypothese « une formulation represente l intention » a ete testee et INVALIDEE (arXiv 2605.27440) |
| `plan_langues` | quelles langues de requete | la langue explique **26,5 %** de la variance d une reponse |
| `plan_surfaces` | quelles surfaces interrogees, nommees | deux surfaces ne repondent pas la meme chose, et aucune ne s engage |
| `plan_reexecutions` | combien de fois le plan a ete rejoue | le reechantillonnage PUR pese **34,8 %** — une execution est un tirage, pas une mesure |
| `plan_dates` | la date de chaque reexecution | sans dates, aucune comparaison entre runs n est possible |
| `dispersion` | l ecart entre reexecutions (min-max, ecart-type) | un chiffre nu n est pas un taux |

> *Ordre de grandeur a garder en tete : la marque elle-meme explique **1,5 %** de
> la variance (ICC 0,0146, decomposition REML sur 12 933 reponses, arXiv
> 2607.13304). Un taux publie sans plan mesure surtout autre chose que la marque.*

## Methode

**protocole à établir au run** : les surfaces et leur comportement changent. Tester N requêtes cibles, consigner la formulation exacte, la date, la surface interrogée, et si le site est cité

## Critere de verdict

taux de citation sur les requêtes cibles, relevé et daté

---

## Constat

<!-- Etape 2 du pipeline. Ce qui est, mesure. Chaque chiffre porte son
     niveau de preuve : [T1 observe] [T2 declare] [T3 tiers] [T4 infere].
     Si non mesurable : le dire et renseigner motif_hors_perimetre. -->

## Preuves

<!-- Ou la mesure a ete prise : URL, fichier d'export et periode, requete,
     date de consultation. Verifiable par un tiers. -->

## Interpretation

<!-- Etape 3 du pipeline. Le mecanisme : comment ce constat coute du trafic
     ou des leads. "Ce n'est pas optimal" n'est pas un mecanisme. -->
