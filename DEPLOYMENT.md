# Publication des corrections de l’audit

Cette procédure accompagne les recommandations 1 à 6. Les feuilles FFTT et les plans enregistrés restent distincts. Aucun script de migration ne réécrit les compositions existantes.

## Vérifications avant publication

`npm ci --ignore-scripts`, `npm test`, `python3 -m unittest discover -s tests -p 'test_*.py'`, `python3 scripts/check_data.py`, puis construction et contrôle du dossier public. Installer Chromium pour Playwright, puis `npm run test:browser`.

Les tests SQL utilisent un PostgreSQL embarqué. Ils vérifient les versions, les fusions, les conflits, les permissions et l’intégrité des versions précédentes ; ils ne reproduisent pas la charge de plusieurs connexions PostgreSQL. Les tests navigateur interceptent tous les appels externes et n’écrivent jamais en production.

Le workflow de collecte peut être lancé avec `dry_run=1` sur une branche : aucune publication, aucun envoi d’alerte. `sample=1` vérifie trois profils (messieurs, dames et sans match). Les identifiants FFTT restent exclusivement dans les secrets GitHub.

## Ordre de bascule

1. Sauvegarder en privé le code serveur actuel, les tables et la configuration des statuts. Conserver la référence Git de départ. Vérifier l’état distant pour préserver les commits du robot.
2. Appliquer `03_private_and_concurrency.sql` et `04_documents_concurrency.sql`. Elles ajoutent un stockage privé et des fonctions transactionnelles ; elles ne modifient aucun plan existant.
3. Importer les statuts avec `import_private_config.py` et vérifier leur relecture. Lancer `backup_private.py` et vérifier que le bucket refuse un accès public. Cette sauvegarde contient les tables et les références des photos ; elle ne duplique pas les objets photo.
4. Déployer la fonction avec `ACBB_REQUIRE_COMPOSITION_VERSION=false` pendant la courte transition. Les anciennes pages restent utilisables. Tester les lectures publiques et privées, sans modifier une journée réelle.
5. Activer GitHub Pages en mode GitHub Actions, puis publier la version validée. Seul `build/public` est déployé ; les scripts, archives internes et exports privés sont exclus. Les références aux scripts et styles portent une empreinte pour éviter un mélange de versions en cache.
6. Vérifier la publication et les anciens liens, puis passer `ACBB_REQUIRE_COMPOSITION_VERSION=true`. Un ancien onglet encore ouvert doit être rechargé avant d’enregistrer. Les nouveaux brouillons conservent leur version de départ et ne remplacent jamais silencieusement une modification distante.
7. Vérifier les premières sauvegardes et collectes. Les résultats d’équipes ont leur traitement indépendant ; les profils ne retardent plus leur publication. Une collecte incomplète conserve la dernière version publiée.

## Retour arrière

Conserver le dossier public précédemment déployé et le code serveur antérieur dans le dossier privé de préparation. Revenir à l’artefact précédent pour l’interface si nécessaire ; remettre temporairement le mode de compatibilité pour les anciennes pages. Les tables ajoutées peuvent rester en place : ne supprimer aucune donnée et ne réécrire aucun journal. Si un correctif serveur est nécessaire, redéployer le fichier antérieur sauvegardé. Une indisponibilité de la FFTT ne justifie jamais de remplacer les données par un lot vide.

## Nettoyage historique séparé

Supprimer les fichiers de la version courante ne retire pas leurs anciennes versions Git. Archiver en privé les alertes et l’historique concernés, préparer la liste exacte des chemins et références à nettoyer, puis obtenir l’accord explicite de Charles avant toute réécriture irréversible. Les copies externes et caches de tiers ne peuvent pas être garantis effacés.

## Limites identifiées

- Les feuilles absentes et identités non rapprochées restent « à vérifier ». La poule Pro B n’est pas encore couverte par le collecteur actuel.
- Le numéro d’entrée de Bartholdi reste à confirmer : deux pages ACBB indiquent respectivement 28 et 30 rue de l’Ancienne-Mairie. Aucune fausse adresse de piscine n’est utilisée pour cette salle.
- La salle habituelle d’un club FFTT n’est pas une confirmation du lieu d’une rencontre. Les exceptions explicitement enregistrées priment.
