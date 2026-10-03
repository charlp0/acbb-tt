-- ============================================================================
-- Critérium Fédéral : confirmations de présence des joueurs du club
--
-- Le CD92 publie les groupes de chaque tour (PDF -> data/criterium2627.json).
-- Un joueur confirme sa présence depuis la page publique après s'être identifié
-- par licence + date de naissance, le même contrôle que l'espace joueur.
--
-- Journal, pas état : on insère une ligne par déclaration, la plus récente par
-- (licence, tour) fait foi. Même modèle que dispos_log — on garde ainsi la trace
-- d'un joueur qui se déclare présent puis se désiste.
--
-- ⚠️ Cette confirmation est INTERNE au club. Elle ne vaut pas excuse auprès du
-- comité, qui exige un écrit à cdtt92@gmail.com dans les délais annoncés.
-- ============================================================================
create table if not exists public.criterium_log (
  id          bigserial primary key,
  created_at  timestamptz not null default now(),
  licence     text        not null,
  tour        smallint    not null check (tour between 1 and 4),
  present     boolean     not null,
  ip          text
);

create index if not exists criterium_log_tour_idx on public.criterium_log (tour, licence, id desc);

-- RLS active et AUCUNE policy : seule la fonction Edge, qui porte la clé
-- service_role, lit et écrit. Les clés publiques ne voient rien.
alter table public.criterium_log enable row level security;
revoke all on table public.criterium_log from anon, authenticated;
