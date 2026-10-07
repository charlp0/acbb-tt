# Schémas — fiches joueurs et base Supabase (à jour au 07/10/2026)

Deux parties : le profil JSON produit par le collecteur FFTT (`data/players/<licence>.json`), puis les tables de la base Supabase telles que les migrations `supabase/migrations/01..08` et la fonction Edge `api` (`supabase/functions/api/index.ts`) les définissent et les utilisent. Les valeurs des exemples sont fictives (licence `9000001`, joueur `EXEMPLE Alex`).

## 1. Profil joueur — data/players/<licence>.json

Généré par `scripts/fftt_build.py` (source : API FFTT SmartPing).

```jsonc
{
  "lic": "9000001",
  "nom": "EXEMPLE", "prenom": "Alex", "club": "08920049",
  "classement": {
    "officiel": 953,   // points figés de la phase (xml_licence_b <point>)
    "mensuel": 1031,   // classement mensuel officiel (<pointm>)
    "debut":   896,    // 1er mensuel saison (<initm>)
    "avenir":  1042    // initm + tous points (validés réels + non-validés estimés grille)
  },
  "timeline": [ {"m":"Sept","v":896}, ... {"m":"Juil","v":1042,"avenir":true} ],  // escalier mensuel
  "saison": {
    "V":33,"D":24,"parties":57,"winpct":58,
    "perfs":9,"contre_perfs":9,                      // perf = battu mieux classé ; contre = perdu vs - classé
    "best":  {"delta":..,"opp":..,"opp_cls":..,"my":..,"date":..,"comp":..},
    "worst": {"delta":..,"opp":..,"opp_cls":..,"my":..,"date":..,"comp":..}
  },
  "competitions": [   // une entrée par compétition jouée (triée par nb matchs)
    {
      "key":"criterium","label":"Critérium fédéral",
      "V":16,"D":12,"winpct":57,
      "pg":197.2,"pl":-38.2,"solde":159.0,            // points gagnés / perdus / solde
      "perf":7,"cperf":1,
      "matches":[ {"date":..,"opp":..,"opp_cls":..,"won":true,"pts":..}, ... ]
    }
  ]
}
```

### Catégorisation (par nom d'épreuve API `<epreuve>`)
| mot-clé épreuve            | catégorie (`key`) |
|----------------------------|-------------------|
| `…Équipes…`                | `equipe`          |
| `…Critérium…`              | `criterium`       |
| `…Championnat de Paris…`   | `paris`           |
| `…TOURNOI…`                | `tournoi`         |
| `…Coupe…`                  | `coupe`           |
| (autre)                    | `autre`           |

### Précision
- Matchs **homologués** : points = `pointres` réels de l'API → **exact**.
- Matchs **non encore homologués** (récents) : points = **estimation grille FFTT** → se corrige automatiquement à l'homologation.
- `opp_cls` = classement **officiel courant** de l'adversaire (≈ niveau au match, à quelques points près).

L'index `data/players_index.json` (même collecteur) liste tous les licenciés : `[{lic, nom, prenom, officiel, mensuel, debut, V, D, parties, solde}]`.

## 2. Base Supabase (projet `vhhmageufrcenruywawg`)

Principes communs :
- **RLS activée sans aucune politique** sur toutes les tables, et droits `anon`/`authenticated` retirés : ni la clé publique ni un utilisateur authentifié ne lisent rien. Seule la fonction Edge `api` (clé `service_role`, qui contourne la RLS) et les scripts lancés avec `SUPA_SERVICE_KEY` y accèdent.
- **Journaux, pas états** : la plupart des tables reçoivent une ligne par saisie ; la plus récente (par licence, par slot, par équipe et journée…) fait foi. Rien n'est réécrit, l'historique reste lisible.
- Les migrations sont idempotentes (`create … if not exists`). `01` et `02` sont jouées par `scripts/refonte_deploy.sh` ; `03` à `08` ont été appliquées à la main (voir `DEPLOYMENT.md`).
- Sauvegarde quotidienne (`scripts/backup_private.py`, bucket `club-backups`) des tables listées dans `scripts/private_store.py` (`TABLES`) : `tags_log, scenarios_log, dispos_log, gate_log, signalements_log, licences_valides, liens, naissances, tentatives, appareils, debriefs_log, journal, liens_usages, private_config`. Au 07/10/2026, `criterium_log`, `cdp_dispos_log` et `cdp_compo_log` n'y figurent pas.

### 2.1 Tables héritées de l'ancien site (créées hors dépôt)
Colonnes telles que le code les lit et les écrit. Verrouillées par `02_switchover_lock.sql` (voir 2.3).

**`dispos_log`** — dispos du championnat par équipe (une ligne par saisie ; la dernière par licence fait foi).
| colonne | type | rôle |
|---|---|---|
| `id` | bigint, pk | ordre chronologique |
| `created_at` | timestamptz | horodatage de la saisie |
| `licence` | text | n° de licence ; les anciennes lignes du formulaire 25/26 portent une clé `SN-NOM-PRENOM` (joueur alors sans licence), rapprochée par nom et prénom |
| `nom`, `prenom` | text | identité au moment de la saisie |
| `dispos` | jsonb | `{"j1":true, …, "j7":false, "roles":[…]}` ; `roles` est recopié de la ligne précédente (le formulaire ne le demande plus) |
| `n` | int | nombre de journées cochées |
| `ip` | text | écrite par la fonction ; jamais renvoyée par `/spo/rest` |
Déclencheur `trg_dispos_notify_github` (AFTER INSERT → `notify_github_dispos()`, voir 2.9) et fonction garde `dispos_guard()` (hors dépôt).

**`tags_log`** — effectif tagué et réglages du scoring (la dernière ligne fait foi).
| colonne | type | rôle |
|---|---|---|
| `id`, `created_at` | bigint pk, timestamptz | |
| `tags` | jsonb | `{"<clé joueur>": {"r":"T"|"R", "e":"M6", "d":…, "e2":…}, "_params": {"k":…, "cap":…}, "_meta": {…}}` ; clé joueur = licence ou `NOM|Prénom` |
| `author` | text | imposé par le serveur : `"<nom du lien> — <note>"` |

**`scenarios_log`** — documents par slot (la dernière ligne par `slot` fait foi).
| colonne | type | rôle |
|---|---|---|
| `id`, `created_at` | bigint pk, timestamptz | |
| `slot` | text | `^[a-z0-9_]{1,16}$` |
| `tags` | jsonb | contenu du document (ci-dessous) |
| `author` | text | imposé par le serveur |
Slots connus : `j1`..`j7` compositions d'une journée `{"<équipe>": {"p":["9000001", …] (≤ 6), "st":"draft"|"valid"|"sent", "note":"…"}, "_meta": {"j", "saved", "by", "base_id", "previous_id"}}` ; `fem` effectif féminin `{"<clé>": {"e":"F2", "r":"T"|"R"}}` ; `contraintes` `{"liste":[{"id", "type", …}]}` (`shared/contraintes.js`) ; `annuaire` `{"phones": {"NOM|PRENOM":"06…"}, "extra": {…}}` (`scripts/push_annuaire.py`) ; `criterium_lic` `{"tour":"1", "lic": {"<id groupe>": {"<pos>":"9000001"}}}` (`scripts/criterium_push_lic.py`).

**`gate_log`** — ancien contrôle d'accès de `scoring.html`. Colonnes non décrites dans le dépôt ; fonction garde `gate_guard()`. Encore lisible par `/spo/rest` et sauvegardée.

**`signalements_log`** — copie serveur des signalements du bandeau « Signale-le » (l'autre copie part chez Formspree).
| colonne | type | rôle |
|---|---|---|
| `id`, `created_at` | | |
| `page`, `type`, `message`, `email`, `url`, `title`, `ua` | text | champs du formulaire, tronqués par la fonction (500/120/4000/200/500/300/300 car.) |
| `ip` | text | IP du visiteur, écrite par la fonction depuis le 07/10/2026 (le garde `signalements_guard`, 30/h par IP, compte dessus) |

**`licences_valides`** — `licence text pk` : l'effectif autorisé à l'entrée joueur (`404 licence_inconnue` sinon). Alimentée hors dépôt.

### 2.2 Migration `01_refonte_schema.sql` — guichet serveur
**`liens`** — liens d'accès `#t=<jeton>` ; le jeton brut n'est jamais stocké.
| colonne | type | rôle |
|---|---|---|
| `id` | bigint identity, pk | |
| `token_hash` | text, unique, not null | `sha256(PEPPER + ':' + jeton)` |
| `role` | text, not null | `check (role in ('capitaine','sportive','cdp'))` — contrainte `liens_role_check`, étendue à `cdp` par `07_role_cdp.sql` |
| `equipe` | text | `M6`, `F2`… ; obligatoire pour un capitaine, optionnelle pour `sportive`/`cdp` (la personne est aussi capitaine de cette équipe) |
| `nom` | text, not null | nom affiché du porteur |
| `actif` | boolean, default true | révocation = `actif=false` |
| `created_at`, `last_used_at` | timestamptz | `last_used_at` mis à jour à chaque passage |
Index `liens_actif_role_idx (actif, role, equipe)`.

**`naissances`** — hachés des dates de naissance.
| colonne | type | rôle |
|---|---|---|
| `licence` | text, pk | |
| `hash` | text, not null | `sha256(PEPPER + ':' + licence + ':' + AAAA-MM-JJ)` ; la fonction compare à ±1 jour |
| `source` | text | `'fichier'` (import, fait foi) ou `'saisie'` (première saisie du joueur) |
| `created_at`, `updated_at` | timestamptz | |

**`tentatives`** — limite d'essais de l'entrée joueur (5 échecs / IP / 10 min, 3 échecs / licence / h, calculé par la fonction).
`id` bigint pk · `ip` text · `licence` text · `ok` boolean default false · `at` timestamptz. Index `(ip, at desc)`, `(licence, at desc)`. Purge possible au-delà de 30 jours.

**`appareils`** — couples (appareil, licence) vus à l'entrée joueur : `device_id` text · `licence` text · `first_at` timestamptz · pk `(device_id, licence)`. Limite appliquée par la fonction : 6 licences distinctes par appareil (3 jusqu'au 02/10/2026).

**`debriefs_log`** — debriefs de match (une ligne par enregistrement ; la dernière par (équipe, journée) fait foi).
| colonne | type | rôle |
|---|---|---|
| `id`, `created_at` | bigint identity pk, timestamptz | |
| `equipe` | text, not null | |
| `journee` | int, 1..30 | |
| `auteur` | text | nom du lien capitaine |
| `score_acbb`, `score_adv` | int, 0..50 ou null | en parties gagnées |
| `texte` | text | texte brut du capitaine (≤ 6000 car.) |
| `texte_corrige` | text | proposition de l'IA (orthographe seulement) |
| `texte_final` | text | texte retenu par la sportive |
| `photo_path` | text | chemin dans le bucket privé `debriefs` (`<equipe>/j<n>/<horodatage>-<aléa>.<ext>`) |
| `photo_public_url` | text | URL dans le bucket public `debriefs-publies` |
| `visible_club` | boolean, default true | souhait du capitaine |
| `publie` | boolean, default false | depuis le 06/10/2026 la fonction insère `true` (publication directe) ; la sportive peut repasser à `false` |
| `publie_par`, `publie_at` | text, timestamptz | |
| `renvoye_message` | text | message de la sportive au capitaine (`/spo/debriefs/renvoyer` remet `publie=false`) |
Index `(equipe, journee, id desc)`, `(journee, id desc)`.

**`journal`** — toute écriture passe ici : `id` bigint pk · `at` timestamptz · `acteur` text (nom du lien, « Prénom Nom (joueur) », « visiteur ») · `role` text (`public`, `joueur`, `capitaine`, `sportive`, `cdp`) · `action` text not null · `details` jsonb. Index `(at desc)`, `(action, at desc)`. Actions : voir `ARCHITECTURE.md`. Jamais de jeton, de date ni de hachage.

**`liens_usages`** — un enregistrement par (lien, appareil) pour repérer un lien partagé : `lien_id` bigint fk → `liens(id)` on delete cascade · `device_id` text · `ip` text · `first_at`, `last_at` timestamptz · `n` int default 1 · pk `(lien_id, device_id)`. Index `(lien_id, last_at desc)`. `GET /spo/liens` n'en renvoie que des comptes.

### 2.3 Migration `02_switchover_lock.sql` — verrou de bascule (appliqué le 16/09/2026)
Active la RLS sur `dispos_log`, `tags_log`, `scenarios_log`, `gate_log`, `signalements_log`, `licences_valides`, supprime les anciennes politiques publiques (« insertion publique dispos », « lecture publique dispos », `gate_insert`, `gate_select`, `lv_select`, « scenarios insert public », « scenarios select public », « signalements insert public », « insertion publique », « lecture publique ») et retire tous les droits `anon`/`authenticated`. L'ancien site, qui lisait ces tables avec la clé publique, ne fonctionne plus depuis.

### 2.4 Migration `03_private_and_concurrency.sql` — configuration privée, sauvegardes, compositions versionnées
**`private_config`** — `name` text pk · `value` jsonb · `updated_at` timestamptz. Noms utilisés : `extra_communautaires` (`{"ex": {…}, "a_confirmer": {…}}`, servi par `GET /spo/config/extras`) et `non_participations` (tableau `[{"k", "championnat", "j", "saison", "phase", "confirmed"}]`, servi par `GET /spo/config/non-participations` et filtré par joueur dans `GET /cap/dispos`). Import : `scripts/import_private_config.py`.

Bucket `club-backups` (privé, voir 2.10).

**Fonction `save_composition(p_slot text, p_expected_id bigint, p_changes jsonb, p_author text) → jsonb`** (`security invoker`, `EXECUTE` réservé à `service_role`) : enregistrement transactionnel d'une journée. Verrou `pg_advisory_xact_lock('acbb-composition:<slot>')` pendant lecture, comparaison et écriture. Contrôles : `p_slot ~ '^j[1-7]$'`, `p_expected_id ≥ 0`, `p_changes` objet non vide, auteur non vide (`composition_invalide`) ; `p_expected_id > 0` doit exister pour ce slot (`version_inconnue`) ; clés d'équipe `^(M([1-9]|1[0-7])|F[1-3])$` (`equipe_invalide`) ; valeur `null` = suppression de l'équipe, sinon objet `{p: array ≤ 6, st: draft|valid|sent}` (`compo_invalide`). Si la ligne courante n'est pas celle attendue et qu'une équipe modifiée a changé entre-temps différemment → `{"ok":false, "conflicts":[équipes], "current":<ligne>}`. Fusion identique à l'existant → `{"ok":true, "row":<ligne courante>, "unchanged":true}`. Sinon insertion d'une nouvelle ligne `scenarios_log` avec `_meta = {j, saved, by, base_id, previous_id}` → `{"ok":true, "row":<ligne>}`.

### 2.5 Migration `04_documents_concurrency.sql` — documents versionnés
**Fonction `save_club_document(p_kind text, p_expected_id bigint, p_changes jsonb, p_author text) → jsonb`** : même contrat pour `tags` (→ `tags_log`), `fem` et `contraintes` (→ `scenarios_log`, `slot = p_kind`). Fusion clé par clé (joueur, ou identifiant de contrainte ; pour `contraintes`, `value.id` doit égaler la clé et l'ordre existant est conservé, les nouvelles à la fin). Erreurs `document_invalide`, `version_inconnue`, `changement_invalide` ; conflits et `unchanged` comme ci-dessus. Appelée par `POST /spo/documents`.

### 2.6 Migration `05_criterium.sql` — confirmations de présence au Critérium fédéral
**`criterium_log`** — une ligne par déclaration ; la plus récente par (licence, tour) fait foi.
| colonne | type | rôle |
|---|---|---|
| `id` | bigserial, pk | |
| `created_at` | timestamptz | |
| `licence` | text, not null | |
| `tour` | smallint, 1..4 | |
| `present` | boolean, not null | présent / absent |
| `ip` | text | |
Index `criterium_log_tour_idx (tour, licence, id desc)`. Écrite par `POST /joueur/criterium`, lue par `GET /public/criterium` (licence → présent). Cette confirmation est interne au club et ne vaut pas excuse auprès du comité.

### 2.7 Migration `06_cdp.sql` — Championnat de Paris
**`cdp_dispos_log`** — « je joue le CDP cette saison » + oui/non par journée ; distinct de `dispos_log`.
| colonne | type | rôle |
|---|---|---|
| `id` | bigserial, pk | |
| `created_at` | timestamptz | une réponse après `2026-10-21T21:59:59Z` est marquée « en retard » par la fonction (`retard`), mais acceptée |
| `licence` | text, not null | |
| `joue` | boolean, not null | si `false`, toutes les dates sont forcées à `false` |
| `dates` | jsonb, default `{}` | `{"j1":true, …, "j7":false}` |
| `ip` | text | |
Index `cdp_dispos_log_lic_idx (licence, id desc)`.

**`cdp_compo_log`** — composition d'une journée, une ligne par enregistrement ; la dernière par journée fait foi et sert d'historique au brûlage (art. 12).
| colonne | type | rôle |
|---|---|---|
| `id` | bigserial, pk | renvoyé comme `expected_id` au client |
| `created_at` | timestamptz | |
| `journee` | smallint, 1..7 | |
| `compo` | jsonb, not null | `{"1":[[lic,lic,null],[…],[…]], "2":[…×3], "3":[…×3], "4":[…×2], "5":[…×1]}` : équipes 1 = PE1, 2 = PE2, 3 = Honneur (3 groupes), 4 = Promo Honneur (2), 5 = D2 (1) ; une licence (`^\d{5,9}$`) ou `null` (absent) par case ; une licence au plus une fois |
| `statut` | text, default `'brouillon'` | `check (statut in ('brouillon','envoyee'))` |
| `auteur` | text | nom du lien (sportive ou sous-sportive CDP) |
Index `cdp_compo_log_j_idx (journee, id desc)`. Écrite par `POST /spo/cdp/compos` (409 `conflit_composition` si `expected_id` ≠ dernière ligne).

### 2.8 Migration `07_role_cdp.sql` — rôle « cdp »
`alter table liens drop constraint liens_role_check; add constraint liens_role_check check (role in ('capitaine', 'sportive', 'cdp'))`. Un lien `cdp` n'ouvre que `/spo/cdp/*` (et l'espace capitaine de l'équipe éventuellement rattachée).

### 2.9 Migration `08_vault_github_pat.sql` — audit du 07/10/2026
- `notify_github_dispos()` (fonction trigger, `security definer`, `search_path = public, net, vault`) : à chaque insertion dans `dispos_log`, lit `vault.decrypted_secrets` (`name = 'github_dispatch_pat'`) et envoie par `net.http_post` un `repository_dispatch` (`event_type = 'dispos'`, `client_payload = {id}`) au dépôt `charlp0/acbb-tt`, ce qui lance « Alerte dispos privée ». Sans secret, un simple `warning` : la saisie du joueur n'est jamais bloquée (le workflow tourne aussi à heure fixe). Le déclencheur `trg_dispos_notify_github` est inchangé.
- Étape manuelle, une seule fois, hors dépôt : `select vault.create_secret('<jeton>', 'github_dispatch_pat', '…')`. Rotation : `select vault.update_secret(id, '<nouveau jeton>') from vault.secrets where name = 'github_dispatch_pat'`.
- `revoke execute … from public, anon, authenticated` sur `notify_github_dispos()`, `dispos_guard()`, `gate_guard()` (PostgreSQL accorde `EXECUTE` à `PUBLIC` par défaut ; un déclencheur se déclenche sans ce droit).
- Tables `corse_*` (site des vacances, même base, hors périmètre de ce dépôt) : `truncate`, `references`, `trigger` retirés à `anon`/`authenticated` ; `select/insert/update/delete` et leurs politiques inchangés.

### 2.10 Stockage (buckets)
| Bucket | Visibilité | Contenu |
|---|---|---|
| `debriefs` | privé | photos brutes des debriefs, `<equipe>/j<n>/<horodatage>-<aléa>.<jpg|png|webp>` (≤ 5 Mo) ; servies par URL signées 1 h aux capitaines et à la sportive |
| `debriefs-publies` | public | copie des photos des debriefs publiés, même chemin ; `photo_public_url` |
| `club-backups` | privé | `database/AAAA/MM/JJ/HHMMSS.json.gz` (toutes les tables de `TABLES`, format `{format:1, started_at, ended_at, tables}`) et `database/latest.json` (`{path, sha256, ended_at, tables:{table: nb lignes}}`) ; alertes dispos `alerts/dispos/<last_id>.json` et `alerts/dispos/latest.json` (`{cursor, message}`), curseur `alerts/dispos/cursor.json` (`{last_id}`) |

### 2.11 Objets hors dépôt à connaître
Fonctions garde `dispos_guard()`, `gate_guard()`, `signalements_guard()` (30 signalements / h / IP), `corse_chat_guard()`, `corse_rows_guard()` ; déclencheur `trg_dispos_notify_github` ; tables `corse_*`. Leur définition vit dans la base, pas dans `supabase/migrations/`.
