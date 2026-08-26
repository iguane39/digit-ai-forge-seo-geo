---
id: 54
branche: GEO
noeud: Entités
volet: TRANSVERSAL
statut_instrumentation: SD
source_requise: "crawl (schema, page « à propos ») + recherche web"
doublon_de: null
modeles: b2b-lead-gen,e-commerce,local,media-affiliation,saas
# --- rempli pendant la mission ---
etat: a-faire
motif_hors_perimetre: null
verdict: null
niveau_preuve: null
date_mesure: null
actions_liees: []
---

# GEO / Entités

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

La marque et ses sujets sont-ils structurés comme des entités reconnaissables ?

## Source requise

crawl (schema, page « à propos ») + recherche web

## Methode

vérifier le balisage `Organization` / `Person`, la cohérence des informations d'identité sur toutes les pages, les liens `sameAs` vers des profils tiers, et l'existence d'une page d'identité factuelle

## Critere de verdict

balisage d'entité présent · identité cohérente partout · ≥ 3 `sameAs` vérifiables

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
