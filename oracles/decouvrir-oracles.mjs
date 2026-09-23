#!/usr/bin/env node
/**
 * decouvrir-oracles.mjs — les oracles de forge-seo-geo, LUS SUR LE DISQUE, jamais recopiés d'une
 * liste (TF-1319, 23/09/2026 : temps 2 du verdict O3 de l'étude du pilot du 19/08/2026 sur le
 * méta-oracle d'enclenchement).
 *
 * POURQUOI. Un run consigne au ledger une entrée `oracles_verdict` par oracle qui a tourné (forme
 * canonique TF-0385). Pour dire lesquels MANQUENT, le juge du pilot doit savoir ce que chaque forge
 * mobilisée porte. Mesuré le 23/09/2026 : cette forge porte UN fichier nommé comme un oracle,
 * `scripts/oracle_interaction.py` (l'oracle d'EXÉCUTION du rapport HTML). `scripts/recette.py`
 * découvre bien ses TESTS par leur nom depuis TF-0274, mais rien ne découvrait ses ORACLES.
 *
 * POURQUOI UN SCRIPT NODE DANS UNE FORGE PYTHON. Le contrat de découverte est COMMUN au parc et
 * son juge est un oracle Node du pilot : une entrée au même chemin et dans le même langage partout
 * évite au juge de tenir une table des forges et de leurs interpréteurs — ce serait la liste écrite
 * à la main que ce temps 2 existe pour supprimer. Node est déjà un prérequis bloquant du poste
 * (`bootstrap.mjs` du pilot : git, node >= 18). La recette, elle, suit les conventions d'ici.
 *
 * LE CONTRAT, COMMUN AU PARC (`digit-ai/decouverte-oracles@1`, CONTRAT-INTERFACE.md §3 du pilot) :
 *   node oracles/decouvrir-oracles.mjs [--racine <dossier>]
 *   stdout : { contrat, forge, racine, regle, oracles: [{ nom, chemin }], non_juge: [] }
 *   exit 0 : découverte faite — une liste vide est un résultat, et elle se lit comme telle ;
 *   exit 2 : racine illisible, motif dit. Jamais d'exit 1 : découvrir n'est pas juger.
 * Ce script ne lance aucun oracle, n'ouvre aucun navigateur et n'écrit rien.
 *
 * LA RÈGLE : tout fichier nommé `oracle-<nom>.mjs|.cjs|.js` ou `oracle[-_]<nom>.py`, où qu'il vive
 * dans le dépôt, hors des dossiers qui ne portent pas d'oracle EN SERVICE — dépendances, caches,
 * archives `Old`/`old`, `fixtures`, entrants `input`. `scripts/validate.py` (contrôles durs du
 * référentiel de la forge) n'y entre pas : son nom ne se déclare pas oracle, et le non_juge le dit.
 *
 * Recette à double sens : `scripts/test_decouvrir_oracles.py`, jouée par `scripts/recette.py`.
 */
import { existsSync, readdirSync, statSync } from "node:fs";
import { basename, dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const CONTRAT = "digit-ai/decouverte-oracles@1";
export const FORGE = "digit-ai-forge-seo-geo";
export const REGLE = "tout fichier `oracle-<nom>.(mjs|cjs|js)` ou `oracle[-_]<nom>.py` du dépôt, "
  + "hors dépendances, caches, `Old`/`old`, `fixtures` et `input` — lu sur le disque à chaque appel";

//: Les dossiers où un fichier nommé comme un oracle n'est pas un oracle en service. Nommés un par
//: un : un motif large écarterait aussi ce qu'on cherche, et une exclusion qui ne se lit pas ne se
//: conteste pas.
export const ECARTES = new Set([".git", "node_modules", ".venv", "venv", "__pycache__",
  ".pytest_cache", ".ruff_cache", ".mypy_cache", ".oracles", "Old", "old", "fixtures", "vendor",
  "input"]);

//: Le nom EST la déclaration. Une recette n'est pas un oracle : `test_oracle_x.py` ne commence pas
//: par `oracle`, et `oracle-x.test.mjs` s'arrête au premier point.
export const EST_UN_ORACLE = (nom) => /^oracle-[\w-]+\.(?:mjs|cjs|js)$/.test(nom) || /^oracle[-_]\w[\w-]*\.py$/.test(nom);

const PROFONDEUR_MAX = 12;

function parcourir(dossier, trouves, profondeur) {
  if (profondeur > PROFONDEUR_MAX) return;
  let entrees;
  try { entrees = readdirSync(dossier, { withFileTypes: true }); } catch { return; }
  for (const e of entrees) {
    const p = join(dossier, e.name);
    if (e.isDirectory()) { if (!ECARTES.has(e.name)) parcourir(p, trouves, profondeur + 1); }
    else if (e.isFile() && EST_UN_ORACLE(e.name)) trouves.push(p);
  }
}

/** La découverte elle-même, importable par une recette ou un lanceur. */
export function decouvrirOracles(racine) {
  const base = { contrat: CONTRAT, forge: FORGE, racine, regle: REGLE, oracles: [] };
  let estDossier = false;
  try { estDossier = existsSync(racine) && statSync(racine).isDirectory(); } catch { estDossier = false; }
  if (!estDossier) {
    return { ...base, motif: `racine introuvable ou illisible : ${racine} — rien n'a été découvert`, non_juge: [] };
  }
  const trouves = [];
  parcourir(racine, trouves, 0);
  const oracles = trouves
    .map((p) => ({ nom: basename(p, extname(p)), chemin: relative(racine, p).split("\\").join("/") }))
    .sort((a, b) => (a.chemin < b.chemin ? -1 : a.chemin > b.chemin ? 1 : 0));
  const parNom = new Map();
  for (const o of oracles) parNom.set(o.nom, [...(parNom.get(o.nom) || []), o.chemin]);
  const doublons = [...parNom.entries()].filter(([, c]) => c.length > 1);
  return {
    ...base,
    oracles,
    non_juge: [
      "la règle lit le NOM du fichier : un contrôle exécutable nommé autrement n'est pas découvert ici — `scripts/validate.py` (contrôles durs du référentiel de la forge) en est un",
      "découvrir n'est pas lancer : cette liste ne dit ni qu'un oracle a tourné, ni sur quel artefact il s'applique (granularité retenue : la forge, étude du 19/08 §5)",
      ...doublons.map(([nom, chemins]) => `nom porté par ${chemins.length} fichiers (${chemins.join(", ")}) : un verdict qui le nomme ne dit pas lequel a tourné`),
    ],
  };
}

// ---- CLI -------------------------------------------------------------------------------------
const lanceEnDirect = process.argv[1]
  && fileURLToPath(import.meta.url).toLowerCase().split("\\").join("/")
     === resolve(process.argv[1]).toLowerCase().split("\\").join("/");
if (lanceEnDirect) {
  const args = process.argv.slice(2);
  const i = args.indexOf("--racine");
  const racine = resolve(i >= 0 && args[i + 1] ? args[i + 1] : join(dirname(fileURLToPath(import.meta.url)), ".."));
  const r = decouvrirOracles(racine);
  console.log(JSON.stringify(r, null, 1));
  process.exit(r.motif ? 2 : 0);
}
