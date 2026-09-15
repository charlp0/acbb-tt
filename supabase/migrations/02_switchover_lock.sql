-- ============================================================================
-- ACBB TT — refonte 2026/27 : VERROU DE BASCULE (switchover)
-- ----------------------------------------------------------------------------
-- ⚠️  À N'EXÉCUTER QUE LORSQUE L'ANCIEN SITE EST RETIRÉ (pages team.acbb-tt.fr
--     hors /refonte : dispo.html, suivi-dispos.html, sportive/*, report.js…).
--
-- L'ancien site lit et écrit ces tables DIRECTEMENT avec la clé publique
-- (sb_publishable_…). Activer la RLS sans policy coupe immédiatement cet accès :
--   - dispo.html            → n'écrira plus dans dispos_log
--   - suivi-dispos / sportive → ne liront plus tags_log / scenarios_log / dispos_log
--   - scoring / gate         → n'écriront plus gate_log
--   - report.js (signalements) → n'écrira plus signalements_log
--     (Formspree reste en double envoi, mais la lecture du briefing matin par
--      Claude/scripts/check_signalements.sh utilise la clé service : inchangée).
--
-- Après ce verrou, seule la fonction Edge `api` (service_role) accède aux
-- tables. Idempotent : rejouable sans effet supplémentaire.
-- Exécution : scripts/refonte_deploy.sh --lock
-- ============================================================================

alter table if exists public.dispos_log        enable row level security;
alter table if exists public.tags_log          enable row level security;
alter table if exists public.scenarios_log     enable row level security;
alter table if exists public.gate_log          enable row level security;
alter table if exists public.signalements_log  enable row level security;
alter table if exists public.licences_valides  enable row level security;

-- Si d'anciennes policies « ouvertes » existent (ex. « allow anon insert »),
-- elles continueraient d'autoriser l'accès malgré la RLS : on les liste ici pour
-- contrôle manuel (la suppression reste volontaire, table par table).
--   select schemaname, tablename, policyname, roles, cmd
--     from pg_policies
--    where tablename in ('dispos_log','tags_log','scenarios_log','gate_log',
--                        'signalements_log','licences_valides');
-- Pour supprimer : drop policy if exists "<policyname>" on public.<table>;
