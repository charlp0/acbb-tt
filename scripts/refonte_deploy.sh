#!/usr/bin/env bash
# ============================================================================
# ACBB TT — refonte 2026/27 : déploiement Supabase
#   a) schéma SQL (01_refonte_schema.sql)     via API de gestion  /database/query
#   b) buckets `debriefs` (privé) et `debriefs-publies` (public)  via Storage API
#   c) secrets de la fonction (ACBB_PEPPER, ANTHROPIC_API_KEY)   via /secrets
#   d) fonction Edge `api` (verify_jwt=false)                     via /functions/deploy
#   e) test : GET /functions/v1/api/me → {"role":null}
#
# Usage :
#   scripts/refonte_deploy.sh                 déploiement complet (a→e)
#   scripts/refonte_deploy.sh --only-sql      seulement a)
#   scripts/refonte_deploy.sh --only-function seulement d) + e)
#   scripts/refonte_deploy.sh --sportive "Minh"   crée le PREMIER lien sportive (amorçage :
#                                             il faut un lien sportive pour en générer d'autres
#                                             depuis la page Accès). L'URL n'est affichée qu'une fois.
#   scripts/refonte_deploy.sh --lock [--yes]  exécute 02_switchover_lock.sql — UNIQUEMENT quand
#                                             l'ancien site est retiré (il lit encore les tables
#                                             avec la clé publique).
#
# Secrets lus dans ~/Documents/Claude/Context/.secrets.env (jamais affichés) :
#   SUPABASE_ACCESS_TOKEN  jeton personnel (sbp_…) de l'API de gestion   — OBLIGATOIRE
#   SUPA_SERVICE_KEY       clé service_role du projet (buckets, tests)   — OBLIGATOIRE
#   ACBB_PEPPER            sel de hachage (jetons + dates), ≥ 16 car.    — OBLIGATOIRE
#   ANTHROPIC_API_KEY      correction IA des debriefs                    — optionnel
# Aucun secret ne transite par la ligne de commande : en-têtes (curl -H @fichier)
# et corps (--data-binary @fichier) passent par des fichiers temporaires privés.
# ============================================================================
set -euo pipefail

REF="vhhmageufrcenruywawg"
SUPABASE_URL="https://${REF}.supabase.co"
MGMT="https://api.supabase.com"
ANON_KEY="sb_publishable_NuRpgtxqVQ87R6K8txw57Q_oBUt4qay"   # clé publique déjà dans le front : n'ouvre aucune table
SITE_URL="${ACBB_SITE_URL:-https://team.acbb-tt.fr/refonte}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="${ACBB_SECRETS_FILE:-$HOME/Documents/Claude/Context/.secrets.env}"
FN_SRC="$ROOT/supabase/functions/api/index.ts"
SQL_SCHEMA="$ROOT/supabase/migrations/01_refonte_schema.sql"
SQL_LOCK="$ROOT/supabase/migrations/02_switchover_lock.sql"

# ---- Options ---------------------------------------------------------------
LOCK=0; YES=0; ONLY=""; SPORTIVE_NOM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --lock) LOCK=1 ;;
    --yes) YES=1 ;;
    --only-sql) ONLY="sql" ;;
    --only-function) ONLY="function" ;;
    --sportive) shift; SPORTIVE_NOM="${1:-}"; [ -n "$SPORTIVE_NOM" ] || { echo "--sportive attend un nom" >&2; exit 2; } ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $1 (voir --help)" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
ok()   { printf '  ✅ %s\n' "$*"; }
warn() { printf '  ⚠️  %s\n' "$*"; }
die()  { printf '\n❌ %s\n' "$*" >&2; exit 1; }
apercu() { head -c "${2:-400}" "$1" 2>/dev/null | tr '\n' ' '; echo; }

command -v curl >/dev/null || die "curl est requis"
command -v python3 >/dev/null || die "python3 est requis (construction des corps JSON)"

# Fichiers temporaires privés (en-têtes, corps, réponses) — effacés à la sortie
TMP="$(mktemp -d "${TMPDIR:-/tmp}/acbb-deploy.XXXXXX")"
chmod 700 "$TMP"
trap 'rm -rf "$TMP"' EXIT

# ---- Secrets ---------------------------------------------------------------
[ -f "$SECRETS" ] || die "Fichier de secrets introuvable : $SECRETS"
# shellcheck disable=SC1090
source "$SECRETS"
if [ -z "${SUPABASE_ACCESS_TOKEN:-}" ]; then
  cat >&2 <<EOF

❌ SUPABASE_ACCESS_TOKEN absent de $SECRETS — arrêt.
   1. Crée un jeton personnel : https://supabase.com/dashboard/account/tokens
   2. Ajoute dans $SECRETS la ligne :
        SUPABASE_ACCESS_TOKEN=sbp_xxxxxxxxxxxxxxxx
   3. Relance ce script.
EOF
  exit 1
fi
: "${SUPA_SERVICE_KEY:?SUPA_SERVICE_KEY absent de $SECRETS}"
: "${ACBB_PEPPER:?ACBB_PEPPER absent de $SECRETS}"
[ "${#ACBB_PEPPER}" -ge 16 ] || die "ACBB_PEPPER trop court (16 caractères minimum)"

# En-têtes dans des fichiers : rien de sensible dans la ligne de commande ni dans \`ps\`
printf 'Authorization: Bearer %s\nContent-Type: application/json\n' "$SUPABASE_ACCESS_TOKEN" > "$TMP/h_mgmt"
printf 'Authorization: Bearer %s\n' "$SUPABASE_ACCESS_TOKEN" > "$TMP/h_mgmt_multipart"
printf 'apikey: %s\nAuthorization: Bearer %s\nContent-Type: application/json\n' "$SUPA_SERVICE_KEY" "$SUPA_SERVICE_KEY" > "$TMP/h_service"
printf 'apikey: %s\nAuthorization: Bearer %s\n' "$ANON_KEY" "$ANON_KEY" > "$TMP/h_anon"

# http MÉTHODE URL FICHIER_ENTÊTES [args curl…] → corps dans $TMP/resp, affiche le code HTTP
http() {
  local method="$1" url="$2" hdr="$3"; shift 3
  local code
  code=$(curl -sS -o "$TMP/resp" -w '%{http_code}' -X "$method" "$url" -H "@$hdr" "$@") || code="000"
  echo "$code"
}

# ---- a) SQL ------------------------------------------------------------------
run_sql() { # run_sql FICHIER.sql LIBELLÉ
  local f="$1" lib="$2"
  [ -f "$f" ] || die "SQL introuvable : $f"
  # Le SQL est encapsulé en JSON par python (jamais interpolé dans la ligne de commande)
  python3 - "$f" > "$TMP/sql.json" <<'PY'
import json, sys
print(json.dumps({"query": open(sys.argv[1], encoding="utf-8").read()}))
PY
  local code
  code=$(http POST "$MGMT/v1/projects/$REF/database/query" "$TMP/h_mgmt" --data-binary "@$TMP/sql.json")
  case "$code" in
    200|201) ok "$lib exécuté (HTTP $code)" ;;
    *) echo "  Réponse : $(apercu "$TMP/resp" 600)"; die "$lib : HTTP $code" ;;
  esac
}

# ---- b) Buckets --------------------------------------------------------------
create_bucket() { # create_bucket ID PUBLIC(true|false)
  local id="$1" pub="$2" code
  printf '{"id":"%s","name":"%s","public":%s,"file_size_limit":5242880,"allowed_mime_types":["image/jpeg","image/png","image/webp"]}' \
    "$id" "$id" "$pub" > "$TMP/bucket.json"
  code=$(http POST "$SUPABASE_URL/storage/v1/bucket" "$TMP/h_service" --data-binary "@$TMP/bucket.json")
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    ok "bucket $id créé (public=$pub)"
  elif [ "$code" = "409" ] || grep -qiE 'already exists|Duplicate' "$TMP/resp"; then
    ok "bucket $id déjà présent"
    # on aligne quand même le flag public (idempotent)
    printf '{"public":%s}' "$pub" > "$TMP/bucket_upd.json"
    code=$(http PUT "$SUPABASE_URL/storage/v1/bucket/$id" "$TMP/h_service" --data-binary "@$TMP/bucket_upd.json")
    [ "$code" = "200" ] || warn "mise à jour du flag public du bucket $id : HTTP $code"
  else
    echo "  Réponse : $(apercu "$TMP/resp")"; die "bucket $id : HTTP $code"
  fi
}

# ---- c) Secrets --------------------------------------------------------------
push_secrets() {
  # Le JSON est construit par python depuis l'environnement d'un sous-shell (pas d'argument en clair)
  ( export ACBB_PEPPER; export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    python3 - > "$TMP/secrets.json" <<'PY'
import json, os
s = [{"name": "ACBB_PEPPER", "value": os.environ["ACBB_PEPPER"]}]
if os.environ.get("ANTHROPIC_API_KEY"):
    s.append({"name": "ANTHROPIC_API_KEY", "value": os.environ["ANTHROPIC_API_KEY"]})
print(json.dumps(s))
PY
  )
  local code
  code=$(http POST "$MGMT/v1/projects/$REF/secrets" "$TMP/h_mgmt" --data-binary "@$TMP/secrets.json")
  case "$code" in
    200|201|204)
      ok "secret ACBB_PEPPER posé"
      if [ -n "${ANTHROPIC_API_KEY:-}" ]; then ok "secret ANTHROPIC_API_KEY posé"; else warn "ANTHROPIC_API_KEY absent : la correction IA répondra 503 ia_indisponible"; fi ;;
    *) echo "  Réponse : $(apercu "$TMP/resp")"; die "secrets : HTTP $code" ;;
  esac
}

# ---- d) Fonction -------------------------------------------------------------
deploy_function() {
  [ -f "$FN_SRC" ] || die "Source de la fonction introuvable : $FN_SRC"
  local code

  # 1) Endpoint moderne (celui du CLI) : upload des sources, bundle côté serveur, imports npm: gérés.
  #    Forme documentée par Supabase : -F metadata=<json> -F file=@<source> (entrypoint_path = filename du fichier).
  code=$(http POST "$MGMT/v1/projects/$REF/functions/deploy?slug=api" "$TMP/h_mgmt_multipart" \
    -F 'metadata={"entrypoint_path":"index.ts","name":"api","verify_jwt":false}' \
    -F "file=@$FN_SRC;filename=index.ts;type=application/typescript")
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    ok "fonction api déployée via /functions/deploy (HTTP $code)"; return 0
  fi
  warn "/functions/deploy → HTTP $code : $(apercu "$TMP/resp" 300)"

  # 2) Repli : API historique. La source est envoyée en JSON (champ `body`, texte), création
  #    (POST /functions) si la fonction n'existe pas, sinon mise à jour (PATCH /functions/api).
  #    Limite connue : fichier unique ; si l'API n'accepte plus que l'eszip
  #    (Content-Type application/vnd.denoland.eszip), passer par le CLI (étape 3).
  warn "repli : API historique POST/PATCH /functions avec body texte"
  python3 - "$FN_SRC" > "$TMP/fn.json" <<'PY'
import json, sys
src = open(sys.argv[1], encoding="utf-8").read()
print(json.dumps({"slug": "api", "name": "api", "verify_jwt": False, "body": src}))
PY
  code=$(http GET "$MGMT/v1/projects/$REF/functions/api" "$TMP/h_mgmt")
  if [ "$code" = "200" ]; then
    code=$(http PATCH "$MGMT/v1/projects/$REF/functions/api?verify_jwt=false" "$TMP/h_mgmt" --data-binary "@$TMP/fn.json")
  else
    code=$(http POST "$MGMT/v1/projects/$REF/functions?slug=api&name=api&verify_jwt=false" "$TMP/h_mgmt" --data-binary "@$TMP/fn.json")
  fi
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    ok "fonction api déployée via l'API historique (HTTP $code)"; return 0
  fi
  warn "API historique → HTTP $code : $(apercu "$TMP/resp" 300)"

  # 3) Dernier repli : CLI Supabase s'il est installé (même arborescence supabase/functions/api/).
  if command -v supabase >/dev/null; then
    warn "repli : supabase functions deploy (CLI)"
    ( cd "$ROOT" && SUPABASE_ACCESS_TOKEN="$SUPABASE_ACCESS_TOKEN" supabase functions deploy api --no-verify-jwt --project-ref "$REF" ) \
      && { ok "fonction api déployée via le CLI"; return 0; }
  else
    warn "CLI supabase non installé (brew install supabase/tap/supabase) — repli impossible"
  fi
  die "déploiement de la fonction impossible : vérifie le jeton SUPABASE_ACCESS_TOKEN (droits sur le projet $REF) et le format accepté par l'API"
}

# ---- e) Test -----------------------------------------------------------------
test_function() {
  local code body
  code=$(http OPTIONS "$SUPABASE_URL/functions/v1/api/me" "$TMP/h_anon" -H 'Origin: https://team.acbb-tt.fr' \
         -H 'Access-Control-Request-Method: GET' -H 'Access-Control-Request-Headers: x-acbb-token, x-acbb-device' -D "$TMP/cors_hdr")
  if [ "$code" = "204" ] || [ "$code" = "200" ]; then ok "préflight CORS OK (HTTP $code)"; else warn "préflight CORS : HTTP $code"; fi

  code=$(http GET "$SUPABASE_URL/functions/v1/api/me" "$TMP/h_anon")
  body="$(apercu "$TMP/resp" 300)"
  if [ "$code" = "200" ] && printf '%s' "$body" | grep -q '"role":null'; then
    ok "GET /api/me → $body"
  else
    warn "GET /api/me → HTTP $code : $body"
    warn "Si 'config_manquante' : les secrets ne sont pas encore visibles (redéploie / attends 30 s). Si 404 : slug ou chemin incorrect."
    return 1
  fi
}

# ---- Amorçage : premier lien sportive ---------------------------------------
bootstrap_sportive() { # bootstrap_sportive NOM
  local nom="$1"
  # jeton 24 octets base64url + hash sha256(PEPPER:jeton), même formule que la fonction (hashJeton)
  ( export ACBB_PEPPER; export LIEN_NOM="$nom"
    python3 - > "$TMP/lien.env" <<'PY'
import base64, hashlib, json, os, secrets
tok = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip("=")
h = hashlib.sha256(f"{os.environ['ACBB_PEPPER']}:{tok}".encode()).hexdigest()
nom = os.environ["LIEN_NOM"].replace("'", "''")
sql = f"insert into public.liens (token_hash, role, equipe, nom, actif) values ('{h}', 'sportive', null, '{nom}', true) returning id;"
print("TOKEN=" + tok)
print("SQLJSON=" + json.dumps(json.dumps({"query": sql})))
PY
  )
  local TOKEN SQLJSON code
  TOKEN=$(sed -n 's/^TOKEN=//p' "$TMP/lien.env")
  SQLJSON=$(sed -n 's/^SQLJSON=//p' "$TMP/lien.env")
  printf '%s' "$SQLJSON" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()))' > "$TMP/lien.json"
  code=$(http POST "$MGMT/v1/projects/$REF/database/query" "$TMP/h_mgmt" --data-binary "@$TMP/lien.json")
  case "$code" in
    200|201)
      ok "lien sportive créé pour « $nom » (id $(apercu "$TMP/resp" 80))"
      printf '\n  🔗 URL à transmettre UNE SEULE FOIS (le jeton n'"'"'est stocké que haché) :\n     %s/sportive/index.html#t=%s\n\n' "$SITE_URL" "$TOKEN" ;;
    *) echo "  Réponse : $(apercu "$TMP/resp")"; die "création du lien : HTTP $code" ;;
  esac
}

# ============================================================================
say "ACBB TT — déploiement refonte (projet $REF)"
echo "  dépôt : $ROOT"
echo "  secrets : $SECRETS (SUPABASE_ACCESS_TOKEN ✓, SUPA_SERVICE_KEY ✓, ACBB_PEPPER ✓, ANTHROPIC_API_KEY $([ -n "${ANTHROPIC_API_KEY:-}" ] && echo ✓ || echo '— absent'))"

if [ "$ONLY" = "sql" ] || [ -z "$ONLY" ]; then
  say "a) Schéma : 01_refonte_schema.sql"
  run_sql "$SQL_SCHEMA" "01_refonte_schema.sql"
fi

if [ -z "$ONLY" ]; then
  say "b) Buckets Storage"
  create_bucket "debriefs" false
  create_bucket "debriefs-publies" true

  say "c) Secrets de la fonction"
  push_secrets
fi

if [ "$ONLY" = "function" ] || [ -z "$ONLY" ]; then
  say "d) Fonction Edge api (verify_jwt=false)"
  deploy_function
  say "e) Test"
  sleep 3
  test_function || true
fi

if [ -n "$SPORTIVE_NOM" ]; then
  say "Amorçage : premier lien sportive"
  bootstrap_sportive "$SPORTIVE_NOM"
fi

if [ "$LOCK" = "1" ]; then
  say "VERROU DE BASCULE : 02_switchover_lock.sql"
  echo "  Active la RLS sans policy sur dispos_log, tags_log, scenarios_log, gate_log, signalements_log, licences_valides."
  echo "  L'ANCIEN SITE (dispo.html, sportive/*, report.js…) CESSERA DE FONCTIONNER."
  if [ "$YES" != "1" ]; then
    read -r -p "  Tape OUI pour confirmer : " rep
    [ "$rep" = "OUI" ] || die "verrou annulé"
  fi
  run_sql "$SQL_LOCK" "02_switchover_lock.sql"
fi

say "Terminé"
cat <<EOF
  Reste à faire (hors script) :
   • python3 scripts/refonte_seed_naissances.py        → hachés des dates (source=fichier)
   • scripts/refonte_deploy.sh --sportive "Minh"        → premier lien sportive (si pas déjà fait)
   • depuis la page Accès (sportive) : générer les liens capitaines
   • quand l'ancien site est retiré : scripts/refonte_deploy.sh --lock
EOF
