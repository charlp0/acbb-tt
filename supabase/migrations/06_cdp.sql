-- ============================================================================
-- Championnat de Paris Île-de-France : dispos des joueurs, compositions de la sportive
--
-- Journaux, pas états : une ligne par déclaration et par enregistrement, la plus récente
-- fait foi. Même modèle que dispos_log et criterium_log.
--
-- cdp_dispos_log : « je joue le CDP cette saison » + oui/non pour chacune des 7 journées.
-- Distinct des dispos du championnat par équipe. Réponse attendue avant le 21/10/2026 ;
-- après, elle reste acceptée et la sportive la voit marquée « en retard ».
--
-- cdp_compo_log : la composition d'une journée, équipe par équipe et groupe par groupe
-- (1 = PE1, 2 = PE2, 3 = Honneur : 3 groupes ; 4 = Promo Honneur : 2 ; 5 = D2 : 1),
-- une licence par case, null pour un absent. Les compositions des journées passées font
-- l'historique qui sert au contrôle du brûlage (art. 12 du règlement CDP du 15/06/2026).
-- ============================================================================
create table if not exists public.cdp_dispos_log (
  id          bigserial primary key,
  created_at  timestamptz not null default now(),
  licence     text        not null,
  joue        boolean     not null,
  dates       jsonb       not null default '{}'::jsonb,
  ip          text
);
create index if not exists cdp_dispos_log_lic_idx on public.cdp_dispos_log (licence, id desc);

create table if not exists public.cdp_compo_log (
  id          bigserial primary key,
  created_at  timestamptz not null default now(),
  journee     smallint    not null check (journee between 1 and 7),
  compo       jsonb       not null,
  statut      text        not null default 'brouillon' check (statut in ('brouillon', 'envoyee')),
  auteur      text
);
create index if not exists cdp_compo_log_j_idx on public.cdp_compo_log (journee, id desc);

-- RLS active et AUCUNE policy : seule la fonction Edge, qui porte la clé service_role,
-- lit et écrit. Les clés publiques ne voient rien.
alter table public.cdp_dispos_log enable row level security;
alter table public.cdp_compo_log  enable row level security;
revoke all on table public.cdp_dispos_log from anon, authenticated;
revoke all on table public.cdp_compo_log  from anon, authenticated;
