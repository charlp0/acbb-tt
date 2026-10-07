# Publication et déploiement (à jour au 07/10/2026)

Cette procédure accompagne les recommandations 1 à 6 de l'audit du 01/10/2026 ; la bascule qu'elle décrit a été réalisée, elle reste la référence pour un redéploiement ou un retour arrière. Les feuilles FFTT et les plans enregistrés restent distincts. Aucun script de migration ne réécrit les compositions existantes. L'architecture, les routes et les tables sont décrites dans [ARCHITECTURE.md](ARCHITECTURE.md) et [scripts/SCHEMA.md](scripts/SCHEMA.md).

## Vérifications avant publication

`npm ci --ignore-scripts`, `npm test`, `python3 -m unittest discover -s tests -p 'test_*.py'`, `python3 scripts/check_data.py`, puis construction et contrôle du dossier public (`python3 scripts/build_public.py`, `python3 scripts/check_public.py`). Installer Chromium pour Playwright (`npx playwright install chromium`), puis `npm run test:browser`.

Cette suite tourne dans deux workflows : « Publier le site vérifié » (`pages.yml`) sur `main`, avant chaque déploiement, et « Vérifications du site » (`verify.yml`) sur chaque pull request. Depuis le 07/10/2026, `verify.yml` ne tourne plus sur `push` (doublon de `pages.yml`).

Les tests SQL utilisent un PostgreSQL embarqué (PGlite) et rejouent les migrations `03` et `04`. Ils vérifient les versions, les fusions, les conflits, les permissions et l'intégrité des versions précédentes ; ils ne reproduisent pas la charge de plusieurs connexions PostgreSQL. Les tests navigateur interceptent tous les appels externes et n'écrivent jamais en production.

Le workflow de collecte peut être lancé avec `dry_run=1` sur une branche : aucune publication, aucun envoi d'alerte. `sample=1` vérifie trois profils (messieurs, dames et sans match). Les identifiants FFTT restent exclusivement dans les secrets GitHub.

## Ordre de bascule (réalisé le 16/09/2026, puis complété le 01/10/2026)

1. Sauvegarder en privé le code serveur actuel, les tables et la configuration des statuts. Conserver la référence Git de départ. Vérifier l'état distant pour préserver les commits du robot.
2. Appliquer `03_private_and_concurrency.sql` et `04_documents_concurrency.sql`. Elles ajoutent un stockage privé et des fonctions transactionnelles ; elles ne modifient aucun plan existant.
3. Importer les statuts avec `import_private_config.py` et vérifier leur relecture. Lancer `backup_private.py` et vérifier que le bucket refuse un accès public. Cette sauvegarde contient les tables et les références des photos ; elle ne duplique pas les objets photo.
4. Déployer la fonction avec `ACBB_REQUIRE_COMPOSITION_VERSION=false` pendant la courte transition. Les anciennes pages restent utilisables. Tester les lectures publiques et privées, sans modifier une journée réelle.
5. Activer GitHub Pages en mode GitHub Actions, puis publier la version validée. Seul `build/public` est déployé ; les scripts, archives internes et exports privés sont exclus. Les références aux scripts et styles portent une empreinte pour éviter un mélange de versions en cache.
6. Vérifier la publication et les anciens liens, puis passer `ACBB_REQUIRE_COMPOSITION_VERSION=true`. Un ancien onglet encore ouvert doit être rechargé avant d'enregistrer. Les nouveaux brouillons conservent leur version de départ et ne remplacent jamais silencieusement une modification distante.
7. Vérifier les premières sauvegardes et collectes. Les résultats d'équipes ont leur traitement indépendant ; les profils ne retardent plus leur publication. Une collecte incomplète conserve la dernière version publiée.

## Migrations ajoutées depuis (05 → 08)

`scripts/refonte_deploy.sh` ne joue que `01_refonte_schema.sql` (et `02_switchover_lock.sql` avec `--lock`). Les migrations suivantes s'appliquent à la main, dans l'éditeur SQL de Supabase ou par l'API de gestion (`/v1/projects/<ref>/database/query`), dans l'ordre et une seule fois ; toutes sont idempotentes.

1. `05_criterium.sql` (03/10/2026) — table `criterium_log`. Aucune dépendance.
2. `06_cdp.sql` (05/10/2026) — tables `cdp_dispos_log`, `cdp_compo_log`. Aucune dépendance.
3. `07_role_cdp.sql` (05/10/2026) — ajoute `cdp` à la contrainte `liens_role_check`. À appliquer **avant** de déployer une fonction qui génère des liens `cdp`, sinon l'insertion échoue sur la contrainte.
4. `08_vault_github_pat.sql` (07/10/2026) — **étape manuelle préalable** : ranger le jeton GitHub fine-grained dans Vault (`select vault.create_secret('<jeton>', 'github_dispatch_pat', '…')`). Le fichier recrée ensuite `notify_github_dispos()` (lecture du secret dans Vault), révoque `EXECUTE` sur les fonctions trigger et réduit les privilèges des tables `corse_*`. Appliqué sur la base le 07/10/2026 et testé ainsi (commentaire en tête du fichier) : insertion d'une ligne de test dans `dispos_log`, réponse `204` de GitHub, ligne supprimée. Rotation du jeton sans toucher à la fonction : `vault.update_secret`.

Après une nouvelle migration, redéployer la fonction si elle en dépend (`scripts/refonte_deploy.sh --only-function`), puis vérifier `GET /me` → `{"role":null}` et un parcours réel de chaque rôle concerné.

## Retour arrière

Conserver le dossier public précédemment déployé et le code serveur antérieur dans le dossier privé de préparation. Revenir à l'artefact précédent pour l'interface si nécessaire ; remettre temporairement le mode de compatibilité pour les anciennes pages. Les tables ajoutées peuvent rester en place : ne supprimer aucune donnée et ne réécrire aucun journal. Si un correctif serveur est nécessaire, redéployer le fichier antérieur sauvegardé. Une indisponibilité de la FFTT ne justifie jamais de remplacer les données par un lot vide.

## Surveillance

« Vérif fraîcheur des données » (`check-freshness.yml`, 09:00 et 19:00 UTC) ouvre une issue si une source FFTT dépasse 18 h, et une autre si la fonction Edge `api` ne répond plus en 200 sur `/me` ou `/public/journee?j=1` (trois essais espacés de 20 s). « Résultats équipes FFTT » ouvre « Résultats équipes FFTT à vérifier » en cas d'échec ; « Mise à jour données FFTT » ouvre une issue datée à chaque échec. Les issues de fraîcheur, de serveur et de résultats ne sont ouvertes que si aucune du même titre n'est déjà ouverte.

## Nettoyage historique séparé

Supprimer les fichiers de la version courante ne retire pas leurs anciennes versions Git. Archiver en privé les alertes et l'historique concernés, préparer la liste exacte des chemins et références à nettoyer, puis obtenir l'accord explicite de Charles avant toute réécriture irréversible. Les copies externes et caches de tiers ne peuvent pas être garantis effacés.

## Limites identifiées

- Les feuilles absentes et identités non rapprochées restent « à vérifier ». La poule Pro B n'est pas couverte par le collecteur (`shared/participations.js` exclut M1).
- Le numéro d'entrée de Bartholdi reste à confirmer : deux pages ACBB indiquent respectivement 28 et 30 rue de l'Ancienne-Mairie. Aucune fausse adresse de piscine n'est utilisée pour cette salle.
- La salle habituelle d'un club FFTT n'est pas une confirmation du lieu d'une rencontre. Les exceptions explicitement enregistrées priment.
- La sauvegarde quotidienne (`scripts/private_store.py`, `TABLES`) ne couvre pas encore `criterium_log`, `cdp_dispos_log` et `cdp_compo_log` (constat du 07/10/2026).
- `brulages.yml` et `keepalive.yml` ne figurent pas dans la liste `workflow_run` de `pages.yml` : leurs commits (poussés avec `GITHUB_TOKEN`, donc sans événement `push`) sont publiés à la publication suivante.
