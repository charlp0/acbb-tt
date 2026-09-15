# ACBB TT — refonte 2026/27 (`/refonte`)

Site statique GitHub Pages + **une fonction serveur Supabase** (`api`) qui est le seul guichet vers la base.
Aucune page ne lit ni n'écrit une table directement. La clé publique Supabase sert uniquement à joindre la fonction.

## Rôles
| Rôle | Entrée | Voit / fait |
|---|---|---|
| Public | rien | données FFTT statiques (`../data/*.json`), scores + debriefs publiés (`/public/journee`) |
| Joueur | n° de licence + date de naissance (`/joueur/*`) | ses propres dispos J1..J7, les modifie. Jamais de compo. |
| Capitaine | lien unique (`#t=<jeton>` → localStorage `acbb_token`) | onglets bleus « Mon équipe » (dispos de l'équipe + debrief/photo) et « Ma poule » (scouting). Jamais de compo. |
| Sportive | lien unique nominatif (Minh, Cyril, Charles) | tout : proxy `/spo/rest` vers les tables + debriefs, accès, journal |

Le menu (`shared/nav.js`, `renderNav({active, role, team, name})`) affiche les onglets publics + ceux du rôle. Rôle connu via `GET /me`.

## Client (`shared/api.js`)
`ACBB.api(route)` = GET, `ACBB.api(route, body)` = POST JSON. En-têtes : `x-acbb-token` (jeton brut, depuis `#t=` ou localStorage), `x-acbb-device` (uuid local). `ACBB.upload(route, file, fields)` multipart. `ACBB.json(path)` pour les JSON statiques. `ACBB.toast`, `ACBB.esc`.
Erreurs : `err.status`, `err.body.error` (code court, voir routes). URL fonction : `https://vhhmageufrcenruywawg.supabase.co/functions/v1/api/<route>`.

## Routes de la fonction `api` (Deno, `supabase/functions/api/index.ts`, `verify_jwt=false`)
Réponses JSON. Erreurs : `{error:"code", ...}` avec statut HTTP.

### Public (sans jeton)
- `GET /public/journee?j=1` → `{items:[{equipe, journee, score_acbb, score_adv, publie, texte, photo_url, auteur, publie_at}]}` — scores dès qu'un capitaine les saisit ; `texte/photo_url/auteur` seulement si `publie`.
- `POST /public/signaler {page, type, message, email, url, title, ua}` → `{ok:true}` — bandeau « Signale-le » (`shared/report.js`), insertion seule dans `signalements_log`, 5 par IP et par heure (`429 trop_signalements`).
- `GET /me` → `{role:null}` sans jeton ; `{role:'capitaine', equipe:'M6', nom:'David Intins'}` ; `{role:'sportive', nom:'Minh'}`. Met à jour `liens.last_used_at`.

### Joueur (licence + date, pas de jeton)
- `POST /joueur/entree {licence, dob:'AAAA-MM-JJ'}` → `{licence, nom, prenom, equipe, dispos:{j1..j7:bool}|null, saved_at|null, premiere:bool}`.
  Règles : licence doit exister dans `licences_valides` ; hash = sha256(PEPPER+':'+licence+':'+dob) comparé à `naissances.hash` ; **si aucune ligne `naissances` : la première saisie fait foi** (insert `source='saisie'`) ; le fichier des inscriptions (`source='fichier'`) l'emporte toujours.
  Erreurs : `404 licence_inconnue` · `401 date_incorrecte {restants}` · `429 trop_essais {retry_s}` (5 échecs / IP / 10 min, 3 / licence / h — table `tentatives`) · `403 appareil_limite` (max 3 licences distinctes par `x-acbb-device` — table `appareils`).
- `POST /joueur/dispos {licence, dob, dispos:{j1..j7:bool}}` → `{ok:true, saved_at}`. Insère dans `dispos_log` (`licence, nom, prenom, dispos:{j1..j7, roles:<copié de la ligne précédente>}, n, ip`). Journal.

### Capitaine (jeton rôle `capitaine`, équipe fixée par le lien)
- `GET /cap/dispos` → `{equipe, journees:[{j,date,opp,dom}], joueurs:[{licence, nom, prenom, statut:'T'|'renfort', dispos|null, saved_at|null, changes:[str], jamais:bool}]}`. Effectif = titulaires de `tags_log` (dernier, `r=='T' && e==equipe`) + pour F1..F3 le slot `fem` de `scenarios_log` (toutes `e==equipe`) + joueurs alignés dans l'équipe dans les slots `j1..j7`. `changes` = tableau (≤ 3 éléments : deux libellés puis « et N autres ») issu du diff entre les 2 dernières lignes `dispos_log` du joueur (« plus dispo en J5 », « de nouveau dispo en J2 », « première saisie ») ; le front fait `join(' · ')`. `journees[]` porte aussi `exempt`.
- `GET /cap/debriefs` → `{items:[debrief par journée de l'équipe, avec photo_url (URL signée 1 h)]}` ; `POST /cap/debrief {journee, score_acbb, score_adv, texte, visible_club}` → `{id}` (insert, la dernière ligne par (equipe,journee) fait foi) ; `POST /cap/photo` multipart `file, journee` → `{photo_path}` (bucket privé `debriefs`, ≤ 5 Mo, jpg/png/webp).
- `GET /cap/poule` → `{equipe, resultats:[{journee, score_acbb, score_adv}]}` (le reste vient de `../data/poules2627.json`, `salles2627.json`).

### Sportive (jeton rôle `sportive`)
- `POST /spo/rest {table, method:'select'|'insert', query, body}` — allowlist `select` : `tags_log, scenarios_log, dispos_log, gate_log, signalements_log, debriefs_log, journal` ; `insert` : `tags_log, scenarios_log` (le serveur remplace/complète `author` par `"<nom du lien> — <suffixe fourni>"`). `query` = chaîne PostgREST (`select=…&order=…&limit=…`). Retourne les lignes.
- `GET /spo/liens` → `[{id, role, equipe, nom, actif, created_at, last_used_at}]` (jamais le jeton).
- `POST /spo/liens/generer {role:'capitaine'|'sportive', equipe, nom}` → `{id, token, url}` — le jeton n'est renvoyé qu'une fois. Révoque les liens actifs précédents du même (role, equipe, nom) si `remplacer:true`.
- `POST /spo/liens/revoquer {id}` → `{ok}`.
- `GET /spo/naissances` → `{fichier, saisie, sans, sans_liste:[{licence,nom,prenom}]}` ; `POST /spo/naissances/import {rows:[{licence, dob}]}` → `{importees, remplacees}` (upsert `source='fichier'`).
- `GET /spo/debriefs?j=1` → `{items:[dernière ligne par équipe/journée, avec photo_url_signee (1 h)]}` ; `POST /spo/debriefs/publier {id, publie:bool, texte_final}` (copie la photo vers le bucket public `debriefs-publies`) ; `POST /spo/debriefs/corriger {id}` → `{texte_corrige}` via l'API Anthropic (secret `ANTHROPIC_API_KEY`, consigne : orthographe/accents/coquilles uniquement, ni ton ni phrases) — `503 ia_indisponible` si pas de clé ; `POST /spo/debriefs/renvoyer {id, message}`.
- `GET /spo/journal?limit=200` → `[{at, acteur, role, action, details}]`.

Codes d'erreur communs : `jeton_requis`, `jeton_invalide`, `role_incorrect`, `postgrest`, `config_manquante`, `ia_indisponible`/`ia_erreur`.

Amorçage : `/spo/liens/generer` exige un jeton sportive ; le premier lien sportive se crée par `scripts/refonte_deploy.sh --sportive "Minh"` (SQL direct, même formule de hachage).

Toute écriture (joueur, capitaine, sportive) ajoute une ligne `journal` (`acteur` = nom du lien, ou « Prénom Nom (joueur) »).

## Tables ajoutées (`supabase/migrations/01_refonte_schema.sql`)
`liens(id, token_hash unique, role, equipe, nom, actif, created_at, last_used_at)` · `naissances(licence pk, hash, source 'fichier'|'saisie', created_at, updated_at)` · `tentatives(id, ip, licence, ok, at)` · `appareils(device_id, licence, first_at, pk(device_id,licence))` · `debriefs_log(id, created_at, equipe, journee, auteur, score_acbb, score_adv, texte, texte_corrige, texte_final, photo_path, photo_public_url, visible_club, publie, publie_par, publie_at, renvoye_message)` · `journal(id, at, acteur, role, action, details jsonb)`.
RLS activée sur ces tables sans aucune politique : seule la fonction (service role) y accède.
`02_switchover_lock.sql` : active la RLS sans politique sur `dispos_log, tags_log, scenarios_log, gate_log, signalements_log` — **à exécuter uniquement quand l'ancien site est retiré** (il lit encore ces tables avec la clé publique).

## Secrets fonction
`ACBB_PEPPER` (hachage jetons + dates ; même valeur que `~/Documents/Claude/Context/.secrets.env`), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (fournis par Supabase), `ANTHROPIC_API_KEY` (optionnel).

## Déploiement
`scripts/refonte_deploy.sh` (API de gestion Supabase, jeton `SUPABASE_ACCESS_TOKEN` dans `.secrets.env`) : SQL → buckets → secrets → fonction. `scripts/refonte_seed_naissances.py` : lit le fichier des inscriptions (xlsx) et insère les hachés `source='fichier'`.

## Données statiques utilisées par le front (`../data/`)
`scoring.json` (effectif, points), `players_index.json` + `players/<lic>.json` (fiches), `poules2627.json` (poules, calendriers, niveaux 25/26), `salles2627.json` (adresses, dom/ext), `resultats2627.json` (résultats FFTT quand disponibles), `site.json` (`STANDINGS` par équipe quand disponibles), `capitaines.json`, `categories.json`, `extra_communautaires.json`.
