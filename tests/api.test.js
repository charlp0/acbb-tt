const test=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const {stripTypeScriptTypes}=require('node:module');
function server(options={}){
 const captain='local_fixture_captain', sportive='local_fixture_sportive';
 const hash=t=>crypto.createHash('sha256').update('fixture-pepper:'+t).digest('hex');
 const tables={
  liens:[{id:1,role:'capitaine',equipe:'M11',nom:'Capitaine Test',actif:true,token_hash:hash(captain)},
         {id:2,role:'sportive',equipe:'M11',nom:'Sportive Test',actif:true,token_hash:hash(sportive)}],
  tags_log:[{id:1,tags:{101:{r:'T',e:'M11'},102:{r:'T',e:'M9'}}}],
  scenarios_log:[{id:1,slot:'j2',tags:{M11:{p:['101','102'],st:'sent'}}},
    {id:2,slot:'j1',tags:{M15:{p:['101','102'],st:'sent'}}}],
  dispos_log:[{id:1,licence:'101',dispos:{j2:true},nom:'TEST',prenom:'Alex'},{id:2,licence:'102',dispos:{j2:false},nom:'SECRET',prenom:'Renfort'}],
  private_config:[{name:'extra_communautaires',value:{ex:{},a_confirmer:{}}}],journal:[],liens_usages:[],
 };
 function from(table){
  let filters=[],limit=Infinity,order=null,single=false,write=null;
  const q={select(){return q;},eq(k,v){filters.push(r=>r[k]===v);return q;},in(k,vs){filters.push(r=>vs.includes(r[k]));return q;},
   like(k,v){filters.push(r=>String(r[k]).startsWith(v.replace('%','')));return q;},order(k,o){order=[k,o];return q;},limit(n){limit=n;return q;},
   maybeSingle(){single=true;return q;},insert(v){write={method:'insert',v};return q;},update(v){write={method:'update',v};return q;},
   then(resolve,reject){try{
    let rows=(tables[table]||[]).filter(r=>filters.every(f=>f(r)));
    if(write){if(write.method==='insert'){(tables[table]||=[]).push(write.v);}else rows.forEach(r=>Object.assign(r,write.v));}
    if(order)rows.sort((a,b)=>(a[order[0]]-b[order[0]])*(order[1].ascending?1:-1));
    rows=rows.slice(0,limit);return Promise.resolve({data:single?(rows[0]||null):rows,error:null}).then(resolve,reject);
   }catch(e){return Promise.reject(e).then(resolve,reject);}}
  };return q;
 }
 let handle,rpcCalls=[];
 const client={from,storage:{from:()=>({download:async()=>({data:new Blob([JSON.stringify({message:'Test privé'})]),error:null})})},rpc:async(name,args)=>{rpcCalls.push({name,args});return {data:{ok:true,row:{id:3,slot:args.p_slot,tags:args.p_changes,author:args.p_author}},error:null};}};
 const env={...options.env,SUPABASE_URL:'https://fixture.invalid',SUPABASE_SERVICE_ROLE_KEY:'fixture-service',ACBB_PEPPER:'fixture-pepper'};
 const source=fs.readFileSync('supabase/functions/api/index.ts','utf8').replace(/import \{ createClient \} from [^;]+;/,'');
 const context=vm.createContext({console,URL,URLSearchParams,Blob,Response,Request,Headers,TextEncoder,crypto:crypto.webcrypto,btoa,
  createClient:()=>client,Deno:{env:{get:k=>env[k]},serve:fn=>{handle=fn;}},
  fetch:async url=>{
   if(url.includes('/rest/v1/')){const u=new URL(url);const rows=tables[u.pathname.split('/').pop()]||[];const n=+u.searchParams.get('offset');return Response.json(rows.slice(n,n+(+u.searchParams.get('limit'))));}
   if(url.endsWith('/scoring.json'))return Response.json({players:[{lic:'101',nom:'TEST',pre:'Alex'},{lic:'102',nom:'SECRET',pre:'Renfort'}]});
   if(url.endsWith('/players_index.json'))return Response.json([]);
   if(url.endsWith('/poules2627.json'))return Response.json({poules:[{acbb:'M11',cal:[{j:2,date:'02/10/2099',oppName:'Adversaire'}]},
    {acbb:'M15',cal:[{j:1,date:'01/01/2020',exempt:true},{j:2,date:'02/10/2099',exempt:true}]}]});
   throw new Error('Requête inattendue dans le test');
  }});
 vm.runInContext(stripTypeScriptTypes(source,{mode:'strip'}),context);
 const request=(path,token,body)=>handle(new Request('https://fixture.invalid/functions/v1/api/'+path,{
  method:body?'POST':'GET',headers:{...(token?{'x-acbb-token':token}:{}),'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined}));
 return {request,captain,sportive,rpcCalls,tables};
}
test('capitaine : aucun renfort futur ni sa disponibilité ne sort de la réponse',async()=>{
 const s=server();const response=await s.request('cap/dispos',s.captain);
 assert.equal(response.status,200);const data=await response.json();
 assert.deepEqual(data.joueurs.map(p=>p.licence),['101']);
 assert(!JSON.stringify(data).includes('SECRET'));
 assert.deepEqual(data.joueurs[0].exemptions,[{j:1,t:'M15'}]);
});
test('routes privées : anonymes refusés, capitaines sans accès aux statuts sportive',async()=>{
 const s=server();
 assert.equal((await s.request('cap/dispos')).status,401);
 assert.equal((await s.request('spo/config/extras')).status,401);
 assert.equal((await s.request('spo/config/extras',s.captain)).status,403);
 assert.equal((await s.request('spo/config/extras',s.sportive)).status,200);
 assert.equal((await s.request('spo/alerts/dispos',s.sportive)).status,200);
 assert.equal((await s.request('spo/alerts/dispos',s.captain)).status,403);
});
test('un ancien client ne peut plus écraser une journée via le proxy générique',async()=>{
 const s=server(),before=s.tables.scenarios_log.length;
 const r=await s.request('spo/rest',s.sportive,{table:'scenarios_log',method:'insert',body:{slot:'j2',tags:{M11:{p:['102']}}}});
 assert.equal(r.status,409);assert.equal(s.tables.scenarios_log.length,before);
});
test('l’auteur est imposé côté serveur et la version est obligatoire',async()=>{
 const s=server();
 const body={slot:'j2',expected_id:1,author:'Imposteur',changes:{M11:{p:['101'],st:'draft',note:''}}};
 assert.equal((await s.request('spo/compositions',s.sportive,body)).status,200);
 assert.equal(s.rpcCalls[0].args.p_author,'Sportive Test');
 delete body.expected_id;
 assert.equal((await s.request('spo/compositions',s.sportive,body)).status,400);
 assert.equal(s.rpcCalls.length,1);
});

test('les historiques longs restent complets et les limites explicites sont respectées',async()=>{
 const s=server();s.tables.dispos_log=Array.from({length:1201},(_,i)=>({id:i+1}));
 const ask=query=>s.request('spo/rest',s.sportive,{table:'dispos_log',method:'select',query});
 let r=await ask('select=id&order=id.asc');assert.equal(r.status,200);assert.equal((await r.json()).length,1201);
 r=await ask('select=id&limit=600');assert.equal((await r.json()).length,600);
 r=await ask('limit=-1');assert.equal(r.status,400);
});
test('compatibilité ancienne page disponible seulement pendant la bascule explicite',async()=>{
 const s=server({env:{ACBB_REQUIRE_COMPOSITION_VERSION:'false'}});
 const r=await s.request('spo/rest',s.sportive,{table:'scenarios_log',method:'insert',body:{slot:'j2',tags:{M11:{p:['101']}}}});
 assert.equal(r.status,200);
});

test('les effectifs et contraintes utilisent aussi une version, aucun contournement par le proxy',async()=>{
 const s=server();
 for(const [table,slot] of [['tags_log',null],['scenarios_log','fem'],['scenarios_log','contraintes']]){
  const r=await s.request('spo/rest',s.sportive,{table,method:'insert',body:{slot,tags:{}}});assert.equal(r.status,409);
 }
 for(const kind of ['tags','fem','contraintes']){
  const changes=kind==='contraintes'?{a:{id:'a',type:'rappel'}}:{'101':{e:'M11'}};
  assert.equal((await s.request('spo/documents',s.sportive,{kind,expected_id:0,changes})).status,200);
  assert.equal((await s.request('spo/documents',s.sportive,{kind,changes})).status,400);
 }
});
