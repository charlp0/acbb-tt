-- Même contrôle de version pour les effectifs et les contraintes.
begin;
create or replace function public.save_club_document(
  p_kind text, p_expected_id bigint, p_changes jsonb, p_author text
) returns jsonb language plpgsql security invoker set search_path=public as $$
declare
  tab text;
  cur jsonb; base jsonb; saved jsonb;
  cur_doc jsonb; base_doc jsonb; merged jsonb; tags jsonb;
  item record; conflicts jsonb := '[]'::jsonb;
begin
  if p_kind not in ('tags','fem','contraintes') or p_expected_id is null or p_expected_id<0
     or jsonb_typeof(p_changes) is distinct from 'object' or p_changes='{}'::jsonb
     or coalesce(p_author,'')='' then raise exception 'document_invalide'; end if;
  tab := case when p_kind='tags' then 'tags_log' else 'scenarios_log' end;
  perform pg_advisory_xact_lock(hashtextextended('acbb-document:'||p_kind,0));
  if p_kind='tags' then
    select to_jsonb(r) into cur from public.tags_log r order by id desc limit 1;
    select to_jsonb(r) into base from public.tags_log r where id=p_expected_id;
  else
    select to_jsonb(r) into cur from public.scenarios_log r where slot=p_kind order by id desc limit 1;
    select to_jsonb(r) into base from public.scenarios_log r where slot=p_kind and id=p_expected_id;
  end if;
  if p_expected_id>0 and base is null then raise exception 'version_inconnue'; end if;
  cur_doc := coalesce(cur->'tags','{}'::jsonb)-'_meta';
  base_doc := coalesce(base->'tags','{}'::jsonb)-'_meta';
  if p_kind='contraintes' then
    select coalesce(jsonb_object_agg(e->>'id',e),'{}'::jsonb) into cur_doc
      from jsonb_array_elements(coalesce(cur_doc->'liste','[]'::jsonb)) e;
    select coalesce(jsonb_object_agg(e->>'id',e),'{}'::jsonb) into base_doc
      from jsonb_array_elements(coalesce(base_doc->'liste','[]'::jsonb)) e;
  end if;
  merged:=cur_doc;
  for item in select * from jsonb_each(p_changes) loop
    if length(item.key) not between 1 and 120 or item.key='_meta'
       or (item.value<>'null'::jsonb and jsonb_typeof(item.value)<>'object')
       or (p_kind='contraintes' and item.value<>'null'::jsonb and item.value->>'id' is distinct from item.key)
      then raise exception 'changement_invalide'; end if;
    if coalesce((cur->>'id')::bigint,0)<>p_expected_id
       and (cur_doc->item.key) is distinct from (base_doc->item.key)
       and (cur_doc->item.key) is distinct from nullif(item.value,'null'::jsonb) then
      conflicts:=conflicts||jsonb_build_array(item.key);
    end if;
    if item.value='null'::jsonb then merged:=merged-item.key;
    else merged:=jsonb_set(merged,array[item.key],item.value); end if;
  end loop;
  if jsonb_array_length(conflicts)>0 then return jsonb_build_object('ok',false,'conflicts',conflicts,'current',cur); end if;
  if merged=cur_doc then return jsonb_build_object('ok',true,'row',cur,'unchanged',true); end if;
  tags:=merged;
  if p_kind='contraintes' then
    -- Garder l'ordre existant ; les nouvelles contraintes sont ajoutées à la fin.
    select jsonb_build_object('liste',coalesce(jsonb_agg(m.value order by coalesce(o.ord,2147483647),m.key),'[]'::jsonb)) into tags
      from jsonb_each(merged) m left join lateral (
        select ord from jsonb_array_elements(coalesce(cur->'tags'->'liste','[]'::jsonb)) with ordinality as a(e,ord)
        where e->>'id'=m.key limit 1
      ) o on true;
  end if;
  if p_kind='tags' then
    insert into public.tags_log(tags,author) values(tags,p_author) returning to_jsonb(tags_log.*) into saved;
  else
    insert into public.scenarios_log(slot,tags,author) values(p_kind,tags,p_author) returning to_jsonb(scenarios_log.*) into saved;
  end if;
  return jsonb_build_object('ok',true,'row',saved);
end;
$$;
revoke all on function public.save_club_document(text,bigint,jsonb,text) from public,anon,authenticated;
grant execute on function public.save_club_document(text,bigint,jsonb,text) to service_role;
commit;
