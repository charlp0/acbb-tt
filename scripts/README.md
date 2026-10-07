# Scripts du site ACBB TT

Tous les scripts se lancent **depuis la racine du dépôt** (`python3 scripts/x.py`) : plusieurs
chargent `scripts/fftt_build.py` par chemin relatif. Les identifiants FFTT viennent des variables
d'environnement `FFTT_ID` / `FFTT_PWD`, la clé service Supabase de `SUPA_SERVICE_KEY` (secrets
GitHub en CI, `~/Documents/Claude/Context/.secrets.env` en local). Aucun secret dans le dépôt.

## Lancés par les automatisations

Liste tirée de `grep -hoE "scripts/[a-z0-9_]+\.(py|sh)" .github/workflows/*.yml | sort -u`.

| Script | Workflow (fichier) |
|---|---|
| `collect_profiles.py` (→ `fftt_build.py` en sous-processus), `fftt_scoring.py`, `fftt_site.py`, `check_data.py` | « Mise à jour données FFTT » (`update-data.yml`), 4 fois par jour |
| `fftt_site.py`, `check_data.py` | « Résultats équipes FFTT » (`results.yml`), à la fin de la mise à jour des données |
| `check_data.py`, `build_public.py`, `check_public.py` | « Publier le site vérifié » (`pages.yml`) et « Vérifications du site » (`verify.yml`) |
| `check_data.py --require-fresh` | « Vérif fraîcheur des données » (`check-freshness.yml`), 09:00 et 19:00 UTC |
| `fftt_brulages.py` | « Brûlage des adversaires (FFTT) » (`brulages.yml`) |
| `fftt_categories.py` | « Catégories d'âge FFTT » (`categories.yml`), quotidien |
| `fftt_salles_adverses.py` | « Salles des adversaires (FFTT) » (`salles-adverses.yml`), hebdomadaire |
| `criterium_stats.py` | « Bilans critérium (FFTT) » (`criterium-stats.yml`), manuel par tour |
| `backup_private.py` | « Sauvegarde Supabase privée » (`ping-supabase.yml`), quotidien |
| `restore_alert_cursor.py`, `dispos_alert.py`, `publish_private_alert.py` | « Alerte dispos privée » (`dispos-alert.yml`), toutes les heures 05-20 UTC |
| `fftt_archive.py` | « Archive — rattrapage scan cx_poule 25/26 » (`archive-scan.yml`), one-shot |
| `fftt_check_nolic.py` | « Vérif licences manquantes (one-shot) » (`check-nolic.yml`) |
| `classify_autres.py` | « Classement Vétérans / Challenge (one-shot) » (`classify-autres.yml`) |
| `recover_autres.py` | « Récupération parties manquantes 25/26 (one-shot) » (`recover-autres.yml`) |
| `probes/probe_partie.py` (valeur par défaut, autre sonde au choix) | « Sonde API FFTT (one-shot) » (`probe-api.yml`) |

Modules importés, jamais lancés seuls : `fftt_build.py` (collecteur FFTT, chargé par `importlib`
dans la plupart des collecteurs ; schéma des fiches dans `SCHEMA.md`), `fftt_quality.py`
(contrôles de cache et de régression), `private_store.py` (accès service aux tables et au
stockage privés), `team_identity.py` (rapprochement prudent des noms d'équipes).

## Outils manuels

**`criterium_pdf.py`** — groupes du Critérium Fédéral départemental (CD92) : convertit les deux
PDF du comité (jeunes, puis -19 ans et adultes) en `data/criterium2627.json`, une à deux semaines
avant chaque tour. `python3 scripts/criterium_pdf.py <tour> <date JJ/MM/AAAA> <pdf> [pdf…]`
(dépend de `pdfplumber`).

**`criterium_reg_nat_pdf.py`** — échelons régional (R1/R2) et national (N2) du critérium, depuis
les PDF de la ligue Île-de-France et de la FFTT (liste globale + qualifiés N2) ; salles et
horaires sont repris en dur dans le script, à mettre à jour à chaque tour.
`python3 scripts/criterium_reg_nat_pdf.py <tour> <liste_globale.pdf> <n2.pdf> [n2.pdf…]`.

**`criterium_n1_xlsx.py`** — Nationale 1 du critérium, depuis l'export xlsx du classeur Google
Sheets de la FFTT (ne retient que les onglets de la saison demandée).
`python3 scripts/criterium_n1_xlsx.py <tour> <saison> <salle> <classeur.xlsx>` (dépend d'`openpyxl`).

**`criterium_push_lic.py`** — après les convertisseurs ci-dessus : dépose la table privée des
licences (`data/_criterium_lic.json`, ignoré par git) dans `scenarios_log` pour que « Bilans
critérium » interroge la FFTT sans licence dans le dépôt. `python3 scripts/criterium_push_lic.py [tour]`.

**`fftt_officiel.py`** — instantané des points OFFICIELS de la saison pour tout l'effectif
(`data/officiel2627.json`), à lancer quand la FFTT publie les classements d'une nouvelle phase :
**à relancer début janvier 2027 pour les points officiels de la phase 2**.
`FFTT_ID=… FFTT_PWD=… python3 scripts/fftt_officiel.py` (s'arrête sans écrire si l'API rend
moins de 80 % des classements).

**`fftt_poules2627.py`** — poules régionales et départementales de la phase 1 2026/2027
(saisies à la main depuis les PDF ligue et CD92) et niveau moyen 25/26 des adversaires depuis
l'archive → `data/poules2627.json`. À adapter puis relancer pour la phase 2.
`python3 scripts/fftt_poules2627.py`.

**`import_naissances_fftt.py`** — réimporte les dates de naissance depuis l'export licences
FFTT (source de vérité) et les enregistre hachées dans la table `naissances`, jamais en clair.
`python3 scripts/import_naissances_fftt.py --csv CHEMIN [--dry-run]` (secrets `SUPA_SERVICE_KEY`,
`ACBB_PEPPER`).

**`refonte_seed_naissances.py`** — même principe depuis le fichier des inscriptions (xlsx,
onglet « 2026-2027 »), apparié à l'effectif de `scoring.json`.
`python3 scripts/refonte_seed_naissances.py [--dry-run] [--xlsx CHEMIN] [--sheet NOM]`.

**`push_annuaire.py`** — publie l'annuaire téléphonique (fichier local hors dépôt) dans le
magasin protégé `scenarios_log` (slot `annuaire`), lu uniquement par la fonction Edge pour un
porteur de lien sportive. `python3 scripts/push_annuaire.py [annuaire.json]`.

**`refonte_deploy.sh`** — déploiement Supabase de la refonte : schéma SQL, buckets, secrets de
la fonction, fonction Edge `api`, test `/me`. `scripts/refonte_deploy.sh [--only-sql |
--only-function | --sportive "Nom" | --lock]` (jeton `SUPABASE_ACCESS_TOKEN` dans `.secrets.env`).

**`import_private_config.py`** — migration explicite des statuts extra-communautaires vers la
table `private_config` (étape 3 de l'ordre de bascule, `DEPLOYMENT.md`). Déjà exécutée ; conservé
car la procédure le cite. `python3 scripts/import_private_config.py fichier.json [--apply]`.

**`google_form_signalement.gs`** — Apps Script à coller une seule fois dans script.google.com
pour générer le formulaire de signalement et sa feuille de réponses.

## Sondes et archives

**`probes/`** — scripts ponctuels en lecture seule qui interrogent l'API FFTT pour trancher une
question (forme d'une réponse, existence d'un point d'entrée, contrôle de licences). Ils se
lancent via le workflow « Sonde API FFTT » (entrée `script`, par exemple
`scripts/probes/probe_salles.py`) et impriment dans le journal du run ; rien n'est écrit. Chacun
ajoute `scripts/` à `sys.path` en tête pour garder ses imports depuis la racine.
`probe_partie` (codechamp → catégorie), `probe_bilan` / `probe_parties_vd` / `probe_parties_forme` /
`probe_parties_saison` (bilans et parties : ce que la FFTT rend vraiment), `probe_licences_j2` /
`probe_licences_tous` / `probe_legall` (validation des licences), `probe_salles` / `probe_salles2` /
`probe_salles3` (salles des adversaires), `probe_equipes_club` / `probe_renforts` (équipes d'un
club, renforts possibles au sens du II.112), `probe_results` (feuilles J2 M14/M16).

**`archive/`** — conservés pour mémoire, plus référencés nulle part : `split_equipe_mf.py` et
`rebuild_splits_mf.py` (one-shot de juillet 2026 : scission Masculin/Féminin et fusion des phases
dans les fiches 25/26) ; `archive_acbb_index.py` (index `data/archive/2025-2026/acbb-vs.json`
des rencontres de l'ACBB en 25/26, lu par `sportive/poules.html` — l'archive source est figée,
le script ne se relance que si elle changeait). Leur racine est recalculée pour rester
exécutables depuis ce dossier.
