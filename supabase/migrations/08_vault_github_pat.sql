-- 08 — Audit sécurité du 07/10/2026 : jeton GitHub sorti du code SQL, droits anon/authenticated resserrés.
--
-- Pourquoi : la fonction trigger notify_github_dispos() (AFTER INSERT sur dispos_log, déclencheur
-- trg_dispos_notify_github) prévient GitHub (repository_dispatch « dispos » → workflow « Alerte dispos
-- privée ») avec un jeton personnel fine-grained. Ce jeton était écrit EN CLAIR dans le corps de la
-- fonction : lisible par quiconque lit pg_proc (éditeur SQL, dumps de schéma, sauvegardes). Il vit
-- désormais dans Supabase Vault (chiffré au repos) et la fonction le lit au moment de l'appel.
--
-- ÉTAPE MANUELLE, UNE SEULE FOIS, HORS DÉPÔT — ranger le jeton dans Vault avant d'appliquer ce fichier :
--   select vault.create_secret('<jeton GitHub fine-grained>', 'github_dispatch_pat',
--     'PAT GitHub fine-grained : repository_dispatch dispos → workflow Alerte dispos privée');
-- Rotation ultérieure (la fonction n'a pas à changer) :
--   select vault.update_secret(id, '<nouveau jeton>') from vault.secrets where name = 'github_dispatch_pat';
--
-- Appliqué sur la base live le 07/10/2026 (test : insertion SN-TEST-AUDIT → GitHub 204, ligne supprimée).
begin;

-- ── 1. notify_github_dispos : le jeton est lu dans Vault ────────────────────────────────────────────
-- Même comportement qu'avant (même URL, mêmes en-têtes, même event_type « dispos », même payload {id}),
-- security definer conservé (le propriétaire postgres lit Vault et écrit la file pg_net), search_path figé.
create or replace function public.notify_github_dispos()
returns trigger
language plpgsql
security definer
set search_path = public, net, vault
as $$
declare
  pat text;
begin
  select decrypted_secret into pat from vault.decrypted_secrets where name = 'github_dispatch_pat';
  if pat is null or pat = '' then
    -- Sans jeton on n'empêche pas la saisie du joueur : le workflow tourne aussi à heure fixe (cron).
    raise warning 'notify_github_dispos : secret Vault github_dispatch_pat absent, dispatch GitHub non envoyé';
    return new;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/charlp0/acbb-tt/dispatches',
    headers := jsonb_build_object(
      'Accept', 'application/vnd.github+json',
      'Authorization', 'Bearer ' || pat,
      'User-Agent', 'acbb-tt-supabase',
      'Content-Type', 'application/json'),
    body := jsonb_build_object('event_type', 'dispos', 'client_payload', jsonb_build_object('id', new.id))
  );
  return new;
end $$;
-- Le déclencheur existant est inchangé et reste attaché :
--   create trigger trg_dispos_notify_github after insert on public.dispos_log
--     for each row execute function public.notify_github_dispos();

-- ── 2. Fonctions trigger : EXECUTE retiré aux rôles du navigateur ──────────────────────────────────
-- dispos_log et gate_log ne reçoivent plus que des écritures service_role (fonction Edge `api`).
-- PostgreSQL accorde EXECUTE à PUBLIC par défaut, donc à anon et authenticated par héritage : la
-- révocation doit viser PUBLIC aussi pour être effective. Un déclencheur se déclenche sans EXECUTE ;
-- postgres (propriétaire) et service_role conservent leur droit explicite.
-- corse_chat_guard, corse_rows_guard et signalements_guard ne sont PAS touchés : leurs tables
-- reçoivent des insertions anon directes.
revoke execute on function public.notify_github_dispos() from public, anon, authenticated;
revoke execute on function public.dispos_guard() from public, anon, authenticated;
revoke execute on function public.gate_guard() from public, anon, authenticated;

-- ── 3. Tables corse_* (site des vacances, même base) : privilèges anon/authenticated réduits ───────
-- Les grants par défaut du schéma public donnaient ALL. TRUNCATE n'est pas filtré par la RLS (une
-- requête anon pouvait vider une table) ; REFERENCES et TRIGGER n'ont aucun usage depuis le navigateur.
-- SELECT, INSERT, UPDATE et DELETE restent accordés ; les policies RLS sont inchangées.
revoke truncate, references, trigger on public.corse_blocks_extra from anon, authenticated;
revoke truncate, references, trigger on public.corse_chat from anon, authenticated;
revoke truncate, references, trigger on public.corse_planning from anon, authenticated;
revoke truncate, references, trigger on public.corse_votes from anon, authenticated;

commit;
