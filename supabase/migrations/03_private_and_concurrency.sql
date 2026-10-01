-- À appliquer avant le nouveau front. Aucun plan existant n'est modifié.
begin;

create table if not exists public.private_config (
  name text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.private_config enable row level security;
revoke all on public.private_config from public, anon, authenticated;
grant all on public.private_config to service_role;

-- Sauvegardes complètes, jamais publiées ni attachées à un run public.
insert into storage.buckets (id, name, public)
values ('club-backups', 'club-backups', false)
on conflict (id) do update set public = false;

create or replace function public.save_composition(
  p_slot text, p_expected_id bigint, p_changes jsonb, p_author text
) returns jsonb
language plpgsql security invoker set search_path = public
as $$
declare
  current_row public.scenarios_log%rowtype;
  base_row public.scenarios_log%rowtype;
  saved_row public.scenarios_log%rowtype;
  merged jsonb;
  changed record;
  conflicts jsonb := '[]'::jsonb;
begin
  if p_slot !~ '^j[1-7]$' or p_expected_id < 0 or p_expected_id is null
     or jsonb_typeof(p_changes) <> 'object' or p_changes = '{}'::jsonb
     or length(coalesce(p_author,'')) = 0 then
    raise exception 'composition_invalide' using errcode = '22023';
  end if;
  -- Le verrou couvre lecture, comparaison et écriture dans la même transaction.
  perform pg_advisory_xact_lock(hashtextextended('acbb-composition:' || p_slot, 0));
  select * into current_row from public.scenarios_log
    where slot = p_slot order by id desc limit 1;
  if p_expected_id > 0 then
    select * into base_row from public.scenarios_log where id = p_expected_id and slot = p_slot;
    if not found then raise exception 'version_inconnue' using errcode = '22023'; end if;
  end if;
  merged := coalesce(current_row.tags, '{}'::jsonb);
  for changed in select * from jsonb_each(p_changes) loop
    if changed.key !~ '^(M([1-9]|1[0-7])|F[1-3])$' then
      raise exception 'equipe_invalide' using errcode = '22023';
    end if;
    if changed.value <> 'null'::jsonb and (
      jsonb_typeof(changed.value) <> 'object'
      or jsonb_typeof(changed.value->'p') is distinct from 'array'
      or jsonb_array_length(changed.value->'p') > 6
      or coalesce(changed.value->>'st','') not in ('draft','valid','sent')
    ) then raise exception 'compo_invalide' using errcode = '22023'; end if;
    if coalesce(current_row.id,0) <> p_expected_id
       and (current_row.tags->changed.key) is distinct from (base_row.tags->changed.key)
       and (current_row.tags->changed.key) is distinct from nullif(changed.value,'null'::jsonb) then
      conflicts := conflicts || jsonb_build_array(changed.key);
    end if;
    if changed.value = 'null'::jsonb then merged := merged - changed.key;
    else merged := jsonb_set(merged, array[changed.key], changed.value); end if;
  end loop;
  if jsonb_array_length(conflicts) > 0 then
    return jsonb_build_object('ok',false,'conflicts',conflicts,'current',to_jsonb(current_row));
  end if;
  -- Même demande réessayée après une réponse réseau perdue : aucun doublon.
  if (merged - '_meta') = (coalesce(current_row.tags,'{}'::jsonb) - '_meta') then
    return jsonb_build_object('ok',true,'row',to_jsonb(current_row),'unchanged',true);
  end if;
  merged := jsonb_set(merged, '{_meta}', jsonb_build_object(
    'j',substring(p_slot from 2)::int,'saved',now(),'by',p_author,
    'base_id',p_expected_id,'previous_id',current_row.id));
  insert into public.scenarios_log (slot,tags,author) values (p_slot,merged,p_author)
    returning * into saved_row;
  return jsonb_build_object('ok',true,'row',to_jsonb(saved_row));
end;
$$;
revoke all on function public.save_composition(text,bigint,jsonb,text) from public, anon, authenticated;
grant execute on function public.save_composition(text,bigint,jsonb,text) to service_role;

commit;
