const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {PGlite}=require('@electric-sql/pglite');
test('vraie migration PostgreSQL : fusion, conflit, suppression, idempotence et droits',async()=>{
 const db=new PGlite();
 try{
  await db.exec(`create role anon; create role authenticated; create role service_role;
    create schema storage; create table storage.buckets(id text primary key,name text,public boolean);
    create table public.tags_log(id bigserial primary key,tags jsonb,author text,created_at timestamptz default now());
    create table public.scenarios_log(id bigserial primary key,slot text,tags jsonb,author text,created_at timestamptz default now());
    grant all on public.scenarios_log to service_role; grant usage,select on sequence public.scenarios_log_id_seq to service_role;`);
  await db.exec(fs.readFileSync('supabase/migrations/03_private_and_concurrency.sql','utf8'));
  await db.exec(fs.readFileSync('supabase/migrations/04_documents_concurrency.sql','utf8'));
  const call=async(slot,version,changes,who='Test')=>(await db.query('select public.save_composition($1,$2,$3,$4) as result',[slot,version,JSON.stringify(changes),who])).rows[0].result;
  const c=p=>({p:[p],st:'draft',note:''});
  const initial=await call('j2',0,{M9:c('101'),M11:c('102')});
  const first=await call('j2',initial.row.id,{M9:c('103')},'A');
  const second=await call('j2',initial.row.id,{M11:c('104')},'B');
  assert(second.ok);assert.deepEqual(second.row.tags.M9.p,['103']);assert.deepEqual(second.row.tags.M11.p,['104']);
  const conflict=await call('j2',initial.row.id,{M9:c('105')});
  assert.equal(conflict.ok,false);assert.deepEqual(conflict.conflicts,['M9']);
  assert.deepEqual(conflict.current.tags.M9.p,['103']);
  const repeat=await call('j2',initial.row.id,{M11:c('104')});
  assert(repeat.ok);assert(repeat.unchanged);assert.equal(repeat.row.id,second.row.id);
  const del=await call('j2',second.row.id,{M11:null});assert(!del.row.tags.M11);
  const history=await db.query('select tags from public.scenarios_log where id=$1',[initial.row.id]);
  assert.deepEqual(history.rows[0].tags.M9.p,['101']); // aucun plan historique réécrit
  const empty=await call('j3',0,{M11:c('201')});assert(empty.ok);
  await assert.rejects(call('fem',0,{M11:c('201')}));
  await assert.rejects(call('j2',999,{M11:c('201')}));
  await db.exec('set role anon');
  await assert.rejects(call('j2',del.row.id,{M9:c('999')}));
  await assert.rejects(db.query('select * from public.private_config'));
  await db.exec('reset role');
  assert.equal((await db.query("select public from storage.buckets where id='club-backups'")).rows[0].public,false);
  const doc=async(kind,id,changes)=>(await db.query('select public.save_club_document($1,$2,$3,$4) as r',[kind,id,JSON.stringify(changes),'Test'])).rows[0].r;
  const roster=await doc('tags',0,{'101':{e:'M11'},'102':{e:'M9'}});
  await doc('tags',roster.row.id,{'101':{e:'M10'}});
  const merged=await doc('tags',roster.row.id,{'102':{e:'M8'}});
  assert.equal(merged.row.tags['101'].e,'M10');assert.equal(merged.row.tags['102'].e,'M8');
  assert.equal((await doc('tags',roster.row.id,{'101':{e:'M7'}})).ok,false);
  const con=await doc('contraintes',0,{a:{id:'a',type:'rappel',titre:'A'},b:{id:'b',type:'rappel',titre:'B'}});
  await doc('contraintes',con.row.id,{a:{id:'a',type:'rappel',titre:'A2'}});
  const combined=await doc('contraintes',con.row.id,{b:{id:'b',type:'rappel',titre:'B2'}});
  assert.deepEqual(combined.row.tags.liste.map(x=>x.titre),['A2','B2']);
  assert.equal((await doc('contraintes',con.row.id,{a:null})).ok,false);
  const girls=await doc('fem',0,{'201':{e:'F1'}});
  assert.equal(girls.row.slot,'fem');
 }finally{await db.close();}
});
