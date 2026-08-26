---
id: 59
branche: GEO
noeud: Accès & Directives IA
volet: TRANSVERSAL
statut_instrumentation: SD
source_requise: "crawl (robots.txt, llms.txt, en-têtes) + logs si fournis"
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

# GEO / Accès & Directives IA

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

Les agents des moteurs génératifs peuvent-ils accéder au site, et les directives IA sont-elles posées ?

## Source requise

crawl (robots.txt, llms.txt, en-têtes) + logs si fournis

## Methode

vérifier robots.txt pour chaque agent IA de recherche (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended…) — posture par défaut : AUTORISÉ (décision du 11/08/2026), tout blocage est une décision consignée et datée du propriétaire ; distinguer agents d'entraînement et agents de recherche ; LIRE le contenu de llms.txt — pas seulement constater sa présence : chaque URL qu'il cite doit répondre, et ce qu'il annonce doit correspondre à ce que le site sert ; vérifier aussi sa cohérence avec le sitemap (standard émergent ADOPTÉ par décision du 11/08/2026 — consommation par les moteurs à réévaluer par vérification web datée à chaque run). Ce fichier existe pour être repris SANS vérification par des modèles de langue : une erreur y porte plus loin qu'ailleurs ; contrôler qu'aucun blocage CDN/WAF ne frappe ces UA quand les logs le montrent

## Critere de verdict

aucun agent IA de recherche interdit sans décision consignée · llms.txt présent ET SON CONTENU LU — URLs citées vivantes, annonces confrontées à ce que le site sert, cohérence avec le sitemap ; la présence et l'accessibilité ne valent PAS vérification du contenu · zéro blocage CDN/WAF constaté sur les UA IA (si logs fournis)

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
