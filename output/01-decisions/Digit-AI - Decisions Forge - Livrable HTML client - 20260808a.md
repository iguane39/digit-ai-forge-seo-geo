# Digit-AI — Décisions Forge — Livrable HTML client — 20260808a

**Réponse candidate à la question Q1 de `forge-organization`.**

`Digit-AI - Decisions Forge - Conventions d'organisation - 20260808a.md` laisse Q1 ouverte
et la marque **bloquante** :

> « les fichiers HTML… » vise quoi : la charte (skill `digit-ai-page-html`), l'autonomie du
> fichier (zéro CDN, tout inline), ou le choix du format HTML pour les livrables visuels ?

La question était restée ouverte faute de cas concret. Le rapport d'audit SEO client est ce
cas : il sort du projet, il part chez un tiers, il doit s'imprimer. Les décisions ci-dessous
sont prises **pour toute la forge**, pas seulement pour le SEO, et attendent validation ou
correction.

Émetteur : chantier `forge-seo`, 2026-08-08. Statut : **proposé**, non intégré au référentiel.

---

## D-08 — Les trois axes de Q1 sont trois décisions distinctes, toutes trois « oui »

Q1 posait un choix entre trois lectures. C'est un faux choix : les trois sont nécessaires et
indépendantes. Un fichier peut respecter la charte sans être autonome, être autonome sans
respecter la charte, et le choix du format est encore autre chose.

**Décision** : les trois axes s'appliquent cumulativement à tout livrable HTML destiné à
sortir du projet. Ils sont tranchés séparément en D-09, D-10 et D-11.

## D-09 — Charte : socle `digit-ai-page-html` obligatoire

**Décision** : tout livrable HTML sortant applique le socle `digit-ai-page-html` — tokens
`:root`, Roboto pour les titres, DM Sans pour le corps, JetBrains Mono pour le monospace,
thème clair, aucun hex en dur hors `:root`, WCAG 2.2 AA, `lang="fr"`, `<meta viewport>`,
un `<h1>` unique, police Syne interdite.

**Conséquence** : la recette passe par `check_html.py` et `render_page.py` du skill. Un
livrable non recetté n'est pas un livrable.

**Écart admis** : un livrable peut ajouter des tokens sémantiques absents du socle (le
rapport SEO ajoute `--danger` et une échelle de niveau de preuve). Ils sont déclarés dans
`:root` comme les autres. Le socle est un plancher, pas un plafond.

## D-10 — Autonomie : totale, zéro requête réseau

**Décision** : un livrable HTML sortant est **entièrement autonome**. Aucun CDN, aucune
police distante, aucune image externe, aucun appel réseau d'aucune sorte. CSS et JS sont
inline, les images en `data:` URI, les polices en repli système.

**Trois motifs, dans cet ordre d'importance :**

1. **Confidentialité.** Une requête sortante signale l'ouverture du document : quand, depuis
   quelle adresse, combien de fois. Un rapport d'audit est lu par des tiers dont nous n'avons
   pas à connaître les habitudes de lecture, et dont le client n'a pas à ce que nous les
   connaissions.
2. **Durabilité.** Le client rouvre le fichier dans deux ans. Un CDN disparu rend la page
   illisible, et personne ne saura pourquoi.
3. **Contexte de lecture.** Pièce jointe ouverte hors ligne, dans un train, derrière un proxy
   d'entreprise qui bloque les domaines inconnus.

**Vérification** : recherche de motif dans le fichier produit — aucune occurrence de
`http://`, `https://`, `//cdn`, `@import url(`, `src="//"` en dehors des attributs
documentaires. Contrôle exécutable, pas déclaratif.

## D-11 — Format : HTML pour le visuel sortant, Markdown pour la matière

**Décision** : le HTML est le format des livrables **visuels destinés à sortir du projet**.
Le Markdown reste le format de la matière première et des documents de travail.

**Ce n'est pas un remplacement.** `forge-seo` continue de produire ses cinq livrables
Markdown/CSV/JSON : ils sont la source, versionnable, diffable, lisible en revue. Le HTML est
une **projection** de cette source, régénérable, jamais éditée à la main. Éditer le HTML
livré serait créer une seconde vérité.

**Conséquence** : tout livrable HTML sortant est produit par un générateur, jamais saisi.
Un gabarit HTML qu'on remplit à la main est un anti-patron : il ne survit pas au deuxième
usage, et il diverge de sa source dès la première correction.

## D-12 — Composant de filtres : inliné, jamais installé en douce

**Contexte** : `output/composant-filtres-tableau/` de `forge-organization` fournit un
composant testé (6 règles G1-G6, fixtures rouge/verte, test de mutation passé). Son
`INSTALLATION.md` est explicite : **« Rien n'a été installé… attend un accord explicite »**,
car il modifie `digit-ai-page-html` et `quality-oracles`, deux skills en production.

**Décision** : un projet qui a besoin du composant avant son installation en **inline une
copie verbatim**, avec provenance et date, et **n'installe rien** dans un skill tiers.

`table-filters.js` est un IIFE autonome de 204 lignes sans dépendance : il s'inline sans
adaptation. Cela satisfait simultanément D-10 (autonomie) et la convergence — le jour où le
composant est installé, le générateur lit l'asset du skill au lieu de sa copie, sans changer
le HTML produit, puisque le contrat de marquage est identique.

**Règle G6 rappelée** : les lignes masquées par un filtre sont **réaffichées à l'impression**.
Sans elle, le client imprime un tableau filtré en croyant l'avoir en entier. C'est un défaut
de véracité, pas de mise en page.

---

## Ce que ces décisions ne tranchent pas

- **Q3** (flux seul ou stock aussi) et **Q3-bis** (préfixe projet ou émetteur) restent
  ouvertes. Le rapport SEO applique l'hypothèse de travail de D-03 — préfixe `Digit-AI` pour
  ce qui sort du projet — **en la déclarant comme hypothèse**, pas comme acquis.
- **Q4** (conventions internes aux fichiers) n'est pas abordée ici.
- Le sort de `docs/` (D-06, non tranché) n'est pas affecté.

## Ce qu'il faut faire de ce document

Le reporter dans `forge-organization` pour intégration au référentiel, ou le corriger. Tant
qu'il n'y est pas, Q1 reste formellement ouverte et d'autres projets improviseront leur
propre réponse — ce que ce document existe précisément pour éviter.
