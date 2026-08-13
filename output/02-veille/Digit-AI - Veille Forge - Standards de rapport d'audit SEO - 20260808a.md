# Digit-AI — Veille Forge — Standards de rapport d'audit SEO — 20260808a

Vérification exigée par le chantier « rapport HTML client » : ce que livrent les rapports
d'audit SEO de référence, confronté à ce que produit `forge-seo`.

**Sources consultées le 2026-08-08** — voir la liste en fin de document. Aucune assertion de
ce document ne repose sur la mémoire du modèle : ce qui n'a pas été vérifié est signalé comme
tel.

---

## 1. Structure attendue d'un rapport en 2026

Le consensus des sources converge sur six domaines, plus une couche récente :

| Domaine attendu | Couvert par `forge-seo` | Où |
|---|---|---|
| **Technique** — crawlabilité, indexation, vitesse, mobile, HTTPS, données structurées | ✅ | branches `Technique` (27-32) et `Indexation` (33-37) |
| **On-page** — titles, meta descriptions, titres, structure d'URL, maillage interne | ⚠️ partiel | `Discover/Titres` (49), `Architecture/Maillage` (14) — **meta descriptions et structure d'URL ne sont pas des nœuds** |
| **Contenu** — unicité, E-E-A-T, intention de recherche | ✅ | branche `Contenu` (21-26), `GEO/Contenu Utile` (56), `Idée/Intention` (2) |
| **Off-page** — profil de liens, domaines référents, **distribution des ancres** | ⚠️ partiel | branche `Autorité` (38-42) — **la distribution des ancres n'est pas un nœud** |
| **Local** — fiche d'établissement, cohérence NAP, citations locales | ❌ **absent** | aucun nœud. Écart réel, voir §2 |
| **Expérience** — Core Web Vitals, navigation, **accessibilité** | ⚠️ partiel | `Technique/Performance` (31) — **l'accessibilité n'est pas un nœud** |
| **Visibilité IA** — AI Overviews, AI Mode, citations par les moteurs génératifs | ✅ | branche `GEO` (53-57), en particulier `Présence Dans Les Réponses IA` (57) |

Sur la couche IA, les sources de 2026 la décrivent comme attendue dans un rapport complet.
`forge-seo` la couvre — et va plus loin que ce que décrivent les sources en **déclarant que le
taux de citation relevé n'est ni stable ni reproductible**, donc que c'est une photographie
datée et non une métrique de suivi. Aucune source consultée ne pose cette limite ; nous la
maintenons.

## 2. Écart le plus significatif : le SEO local

Aucun des 82 nœuds ne traite la fiche d'établissement, la cohérence NAP ni les citations
locales. C'est un écart de fond, et il est aggravé par une incohérence interne : le formulaire
de cadrage de `forge-seo` propose `local` comme modèle d'acquisition, alors que la grille n'a
rien pour l'auditer. Un client local recevrait un rapport structurellement muet sur ce qui
compte le plus pour lui.

**Non corrigé volontairement.** La grille des 82 nœuds dérive du schéma source fourni ; y
ajouter une branche change le référentiel entier — comptes, manifeste, arborescence des
missions existantes, contrôles de `validate.py`. C'est une décision de périmètre, pas une
correction de bug. Deux options à arbitrer :

1. **Ajouter une branche `Local` de 5 nœuds** (fiche d'établissement, cohérence NAP, citations
   et annuaires, avis, pages par zone) — la grille passerait à 87 nœuds, et toutes les études
   en cours seraient sur une version antérieure, ce que `validate.py --mission` détecte déjà
   via l'empreinte de grille.
2. **Retirer `local` des modèles d'acquisition** du cadrage, et assumer que `forge-seo`
   n'adresse pas ce marché.

Ne rien faire est la seule option à écarter : elle laisse une promesse non tenue dans le
formulaire d'entrée.

## 3. Écarts mineurs, à traiter dans les nœuds existants

- **Meta descriptions** et **structure d'URL** — absorbables dans `Discover/Titres Qui Attirent`
  (49) et `Architecture/Silos` (11) en élargissant leur question d'audit, sans toucher au
  nombre de nœuds.
- **Distribution des ancres** — absorbable dans `Autorité/Pertinence Thématique` (40), qui est
  déjà `PY` (index de backlinks requis) : l'ancre vient de la même source.
- **Accessibilité** — hors périmètre SEO au sens strict, mais l'oracle `oracle-a11y.py` de
  `quality-oracles` existe déjà. À traiter comme prestation distincte plutôt que comme nœud.

## 4. Ce que les sources confirment de nos choix

- **Public double.** « Les dirigeants doivent comprendre l'impact business en quelques pages,
  pendant que développeurs et marketeurs reçoivent des tâches concrètes et un calendrier
  réaliste. » C'est exactement la divulgation progressive du rapport — synthèse ouverte,
  détail replié — plutôt que trois documents séparés.
- **Priorisation et actionnabilité** citées comme critères de qualité du rapport, pas comme
  options. Le barème gain/effort/confiance et le dispatch en quadrants y répondent.
- **Rapport par URL** confirmé comme attendu — c'est ce qui a motivé l'ajout du bloc `pages[]`
  au schéma de snapshot (v1.1.0).

## 5. Ce que nous faisons et que les sources ne mentionnent pas

- **L'étiquetage du niveau de preuve** (T1 observé / T2 déclaré / T3 tiers / T4 inféré) et son
  rendu visuel. Aucune source consultée ne distingue une mesure d'une estimation dans le
  livrable. C'est notre principal écart de méthode — et, à notre lecture, le principal défaut
  des rapports du marché.
- **L'absence déclarée** : afficher un nœud non mesurable avec son motif et son remède, plutôt
  que masquer la section.
- **Le mode comparatif** entre deux runs comme partie du livrable.

## 6. Limite de cette veille

Cette vérification repose sur des articles de blog d'éditeurs d'outils SEO, dont plusieurs ont
un intérêt commercial à la définition qu'ils donnent d'un audit « complet ». Elle n'est pas une
norme. Aucun document normatif ni source primaire (documentation de moteur) n'a été consulté
ici. À rejouer à chaque évolution significative du domaine, et au minimum une fois par an.

---

## Sources

Consultées le 2026-08-08 :

- [SEO Report for Clients: The 2026 Guide (GA4, AI Visibility & Automation) — SE Ranking](https://seranking.com/blog/seo-reports-for-clients/)
- [SEO Audit Checklist 2026: A Step-by-Step Website Audit Guide — Seeklab](https://seeklab.io/blog/the-complete-seo-audit-checklist-for-2026-a-step-by-step-guide/)
- [The Complete SEO Audit Checklist for 2026 — QuickSEO](https://quickseo.ai/blog/the-complete-seo-audit-checklist-for-2026)
- [SEO Audit Checklist 2026: 50+ Checks for SEO + AEO + GEO — SEO Score Tools](https://seoscore.tools/blog/seo-audit-checklist/)
- [How to Read an SEO Audit Report: 12 Sections (2026) — AI Rank Lab](https://www.airanklab.com/blog/how-to-read-seo-audit-report)
- [SEO Audit Report Template for Agencies: Structure, Format & Examples (2026) — Reportr](https://reportr.agency/blog/seo-audit-report-template-guide)
