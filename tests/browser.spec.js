const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const read=n=>JSON.parse(fs.readFileSync('data/'+n+'.json','utf8'));
function fixture(){
 const players=['Alex','Sam','Chris','Jo','Nova'].map((pre,i)=>({...read('scoring').players[0],lic:'9000000'+(i+1),key:undefined,nom:'EXEMPLE'+(i+1),pre,men:1250-i*30}));
 const tags=Object.fromEntries(players.map((p,i)=>[p.lic,{e:i===4?'M15':'M11',r:'T'}]));
 const poules=read('poules2627');
 const site=read('site');
 Object.values(site.DATA).forEach(p=>p.teams.forEach(t=>t.journees=[]));
 const own=site.DATA.M11.teams.find(t=>t.acbb);
 own.journees=[{journee:1,match_score:22,opp_score:20,players:players.slice(0,4).map(p=>({nom:p.nom,prenom:p.pre,cls:p.men,vic:2})),opponent:'Adversaire Test'}];
 const rows=[{id:12,slot:'j2',author:'Test A',created_at:'2026-09-29T10:00:00Z',tags:{M11:{p:players.slice(0,4).map(p=>p.lic),st:'draft',note:''}}},
  {id:11,slot:'j1',author:'Test A',created_at:'2026-09-20T10:00:00Z',tags:{M9:{p:[players[0].lic],st:'sent'},M15:{p:[players[4].lic],st:'sent'}}}];
 const votes=players.map((p,i)=>({id:i+1,licence:p.lic,nom:p.nom,prenom:p.pre,created_at:'2026-09-29T09:00:00Z',dispos:{j1:true,j2:i!==1,j3:true,j4:true,j5:true,j6:true,j7:true},n:6}));
 return {players,tags,poules,site,rows,votes,saves:[],conflict:false,role:'sportive',documents:[],nonParticipations:[]};
}
async function install(context,state){
 await context.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url());
  const send=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
  if(url.pathname.includes('/functions/v1/api/')){
   const api=url.pathname.split('/api/')[1],body=req.method()==='POST'?req.postDataJSON():null;
   if(api==='me')return send({role:state.role,equipe:'M11',nom:'Test'});
   if(api==='spo/config/extras')return send({ex:{},a_confirmer:{}});
   if(api==='spo/config/non-participations')return send(state.nonParticipations);
   if(api==='spo/rest'){
    if(body.method!=='select')throw new Error('Écriture non prévue dans le test');
    if(body.table==='tags_log')return send([{id:1,tags:state.tags}]);
    if(body.table==='dispos_log')return send(state.votes);
    if(body.table==='scenarios_log')return send(/eq\.(fem|contraintes|annuaire)/.test(body.query)?[]:state.rows);
    return send([]);
   }
   if(api==='spo/documents'){state.documents.push(body);return send({ok:true,row:{id:25,tags:body.kind==='contraintes'?{liste:Object.values(body.changes).filter(Boolean)}:{...state.tags,...body.changes}}});}
   if(api==='spo/compositions'){
    state.saves.push(body);
    if(state.conflict){state.conflict=false;return send({error:'conflit_composition',conflicts:['M11'],current:{id:13,slot:'j2',author:'Test B',created_at:'2026-09-30T10:00:00Z',tags:{M11:{p:[state.players[4].lic],st:'valid',note:'Note partagée'}}}},409);}
    const row={id:14,slot:body.slot,author:'Test',created_at:'2026-09-30T11:00:00Z',tags:body.changes};state.rows.unshift(row);return send({ok:true,row});
   }
   if(api==='cap/dispos')return send({equipe:'M11',journees:state.poules.poules.find(x=>x.acbb==='M11').cal,joueurs:state.players.slice(0,4).map((p,i)=>({...state.votes[i],prenom:p.pre,statut:'T',saved_at:'2026-09-29T09:00:00Z',changes:[],exemptions:[],non_participations:state.nonParticipations.filter(n=>n.k===p.lic)}))});
   if(api==='cap/debriefs'||api==='public/journee')return send({items:[]});
   if(api==='cap/poule')return send({equipe:'M11',resultats:[]});
   if(api==='spo/alerts/dispos')return send({message:'Avis privé fictif'});
   if(api.startsWith('public/'))return send({items:[]});
   return send({});
  }
  if(url.hostname!=='127.0.0.1')return route.abort(); // jamais le réseau de production
  if(url.pathname==='/data/scoring.js')return route.fulfill({contentType:'text/javascript',body:'window.__SCORING='+JSON.stringify({players:state.players})+';'});
  if(url.pathname==='/data/scoring.json')return send({built:new Date().toISOString(),players:state.players});
  if(url.pathname==='/data/poules2627.json')return send(state.poules);
  if(url.pathname==='/data/site.json')return send(state.site);
  if(url.pathname==='/data/sexes.json')return send(Object.fromEntries(state.players.map(p=>[p.lic,'M'])));
  return route.continue();
 });
}
test('J1 réelle, J2 éditable, joueur indisponible non bloquant et export fidèle',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/journee.html?j=2');
 const note=page.locator('[data-note="M11"]');await expect(note).toBeVisible();
 await note.fill('RDV test');await note.blur();
 await expect(page.locator('#saveBtn')).toBeEnabled();await page.locator('#saveBtn').click();
 await expect(page.locator('#saveBtn')).toBeDisabled();
 expect(state.saves).toHaveLength(1);expect(state.saves[0].expected_id).toBe(12);expect(Object.keys(state.saves[0].changes)).toEqual(['M11']);
 const exported=await page.evaluate(()=>waText('M11',2,{adresse:false}));
 expect(exported).toContain('1. Alex EXEMPLE1');expect(exported).toContain('Sam EXEMPLE2');expect(exported).toContain('J2');
 await page.goto('/sportive/journee.html?j=1');
 await expect(page.locator('[data-note="M11"]')).toBeVisible();
 const official=await page.evaluate(()=>waText('M11',1,{adresse:false}));expect(official).toContain('Alex EXEMPLE1');
 expect(await page.locator('[data-st="M11"]').count()).toBe(0);
 expect(errors).toEqual([]);
});
test('un conflit conserve le brouillon et demande un choix explicite',async({page,context})=>{
 const state=fixture();state.conflict=true;await install(context,state);
 await page.goto('/sportive/journee.html?j=2');const note=page.locator('[data-note="M11"]');
 await note.fill('Ma note');await note.blur();await page.locator('#saveBtn').click();
 const dialog=page.locator('dialog');await expect(dialog).toBeVisible();await expect(dialog).toContainText('Nova EXEMPLE5');
 await dialog.locator('select').selectOption('mine');await dialog.locator('[data-apply]').click();
 await expect(note).toHaveValue('Ma note');await page.locator('#saveBtn').click();
 await expect(page.locator('#saveBtn')).toBeDisabled();expect(state.saves[1].expected_id).toBe(13);
});
test('une feuille manquante est signalée une fois et les alertes ciblent les historiques inconnus',async({page,context})=>{
 const state=fixture();await install(context,state);
 await page.goto('/sportive/journee.html?j=2');
 const team=page.locator('.tc[data-team="M11"]');await expect(team).toBeVisible();
 await expect(page.locator('#historyNote')).toContainText('M2 J1');
 await expect(page.locator('#historyNote')).not.toContainText('M1 J1');
 await expect(team).not.toContainText('Historique à vérifier');
 await expect(team).toContainText('feuilles FFTT et exemptions confirmées');
 // Retirer la confirmation d'un seul joueur sans changer le plan J2.
 state.site.DATA.M11.teams.find(t=>t.acbb).journees[0].players.pop();
 await page.reload();await expect(team).toContainText('Historique à vérifier pour Jo EXEMPLE4');
 await expect(team).not.toContainText('Historique à vérifier pour Alex');
});
test('M1 hors gestion : aucun historique manquant et NJ sans correction individuelle',async({page,context})=>{
 const state=fixture();state.poules.poules=state.poules.poules.filter(p=>['M1','M11'].includes(p.acbb));
 state.site.DATA.M11.teams.find(t=>t.acbb).journees[0].players.pop();
 await install(context,state);
 await page.goto('/sportive/journee.html?j=2');
 await expect(page.locator('.tc[data-team="M11"]')).toBeVisible();
 await expect(page.locator('#historyNote')).toBeHidden();
 await expect(page.locator('.tc[data-team="M11"]')).not.toContainText('Historique à vérifier');
 await page.goto('/capitaine.html');
 const row=page.locator('.prow').nth(3);
 await expect(row.locator('.tick').first()).toHaveText('NJ');
 await expect(row.locator('.mj')).toHaveText('0/1');
});
test('capitaine : compteurs réels, cases vertes/rouges conservées, vues sportive chargeables',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/capitaine.html');await expect(page.locator('.prow')).toHaveCount(4);
 await expect(page.locator('.prow').first().locator('.mj')).toHaveText('1/1');
 await expect(page.locator('.prow').first().locator('.tick').first()).toHaveText('M11');
 await expect(page.locator('.prow').nth(1).locator('.tick').nth(1)).toHaveClass(/no/);
 for(const path of ['/sportive/quijoue.html','/sportive/contraintes.html','/sportive/poules.html','/sportive/suivi-dispos.html']){
  await page.goto(path);
  if(path.includes('contraintes')){await expect(page.locator('[data-rule="feminines"] .t')).toContainText('deux féminines maximum');await expect(page.locator('[data-rule="n1"] .teams')).toHaveText('M2, M3, M4, F1');}
  if(path.includes('suivi-dispos'))await expect(page.getByText('Avis privé fictif')).toHaveCount(1);
 }
 expect(errors).toEqual([]);
});

test('mobile : accueil public et équipe restent consultables',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');await expect(page.locator('#iLic')).toBeVisible();
 await page.goto('/capitaine.html');await expect(page.locator('.prow')).toHaveCount(4);
 const overflow=await page.evaluate(()=>Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width})).slice(0,12));
 expect(overflow).toEqual([]);
 expect(errors).toEqual([]);
});
test('capitaine : NJ confirmé et colonnes alignées malgré un compteur encore incertain',async({page,context})=>{
 const state=fixture();
 state.site.DATA.M11.teams.find(t=>t.acbb).journees[0].players=state.site.DATA.M11.teams.find(t=>t.acbb).journees[0].players.slice(0,2);
 state.nonParticipations=[{k:state.players[2].lic,j:1,championnat:'M',saison:'2026/2027',phase:1,confirmed:true}];
 state.votes[2].dispos.j1=false;
 await install(context,state);
 for(const width of [1280,390,320]){
  await page.setViewportSize({width,height:900});await page.goto('/capitaine.html');
  const rows=page.locator('.prow');await expect(rows).toHaveCount(4);
  await expect(rows.nth(2).locator('.tick').first()).toHaveText('NJ');
  await expect(rows.nth(2).locator('.tick').first()).toHaveClass(/no/);
  await expect(rows.nth(2).locator('.mj')).toHaveText('0/1');
  await expect(rows.nth(3).locator('.mj')).toHaveText('0/1 ?');
  const bounds=await rows.evaluateAll(rs=>rs.map(r=>Array.from(r.querySelectorAll('.tick,.mj'),e=>{const b=e.getBoundingClientRect();return {x:b.x,w:b.width,right:b.right};})));
  for(const row of bounds)for(let i=0;i<8;i++){
   expect(Math.abs(row[i].x-bounds[0][i].x)).toBeLessThan(.5);
   expect(Math.abs(row[i].w-bounds[0][i].w)).toBeLessThan(.5);
   expect(row[i].right).toBeLessThanOrEqual(width);
  }
 }
});

test('effectifs : seuls les joueurs modifiés sont enregistrés avec la version chargée',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/index.html');await expect(page.locator('.tagbtn[data-k="90000001"]')).toBeVisible();
 await page.locator('.tagbtn[data-k="90000001"]').click();await page.locator('#tmE').selectOption('M9');await page.locator('#tmOk').click();
 await page.locator('#saveTags').click();await expect(page.locator('#saveSt')).toContainText('Enregistré');
 expect(state.documents).toHaveLength(1);expect(state.documents[0].expected_id).toBe(1);expect(Object.keys(state.documents[0].changes)).toEqual(['90000001']);
 expect(errors).toEqual([]);
});
test('historique : restauration en brouillon uniquement, aucune écriture automatique',async({page,context})=>{
 const state=fixture();state.rows.push({id:10,slot:'j2',author:'Test',created_at:'2026-09-28T10:00:00Z',tags:{M11:{p:[state.players[4].lic],st:'draft',note:'Version ancienne'}}});await install(context,state);
 await page.goto('/sportive/journee.html?j=2');await expect(page.locator('[data-note="M11"]')).toBeVisible();
 await page.locator('#historyBtn').click();const d=page.locator('dialog');await expect(d).toBeVisible();
 await d.locator('[data-version]').selectOption('2');await d.locator('[data-team="M11"]').check();await d.locator('[data-restore]').click();
 await expect(page.locator('[data-note="M11"]')).toHaveValue('Version ancienne');expect(state.saves).toHaveLength(0);await expect(page.locator('#saveBtn')).toBeEnabled();
});
