---
id: 34
branche: Indexation
noeud: Sitemap
volet: ETAT
statut_instrumentation: SD
source_requise: "`sitemap.xml` + crawl"
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

# Indexation / Sitemap

> Volet **ETAT** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

Le sitemap existe-t-il, est-il propre et complet ?

## Source requise

`sitemap.xml` + crawl

## Methode

croiser les URLs du sitemap avec les codes HTTP, les `noindex` et les canonicals

## Critere de verdict

0 URL non-200 · 0 URL en `noindex` · 0 URL canonicalisée ailleurs · ≥ 95 % des pages à valeur présentes

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
