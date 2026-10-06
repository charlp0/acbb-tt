const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
// Les scénarios ci-dessous sont entre J1 et J2, quelle que soit la date de CI.
test.beforeEach(async({page})=>{
 await page.clock.setFixedTime(new Date('2026-09-30T10:00:00Z'));
});
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
   if(api==='spo/liens')return send(state.liens||[]);
   if(api==='spo/liens/revoquer'||api==='spo/liens/equipe'){(state.lienOps||(state.lienOps=[])).push([api,body]);return send({ok:true});}
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
   if(api==='cap/debriefs')return send({items:state.debriefs||[]});
   if(api==='cap/debrief'){
    if(state.debriefError)return send({error:'ecriture_debrief'},500);
    const row={...body,id:70,created_at:'2026-10-04T11:16:00Z',publie:true};   // publié aussitôt (06/10/2026)
    state.debriefs=[row];return send({id:row.id,publie:true});
   }
   if(api==='public/journee')return send({items:[]});
   if(api.startsWith('public/criterium'))return send({presences:state.presences||{}});
   if(api==='joueur/entree'){
    (state.entrees||(state.entrees=[])).push(body);
    if(body.dob!=='2010-03-07')return send({error:'date_incorrecte',restants:2},401);
    const p=state.players.find(x=>x.lic===body.licence);if(!p)return send({error:'licence_inconnue'},404);
    return send({licence:p.lic,nom:p.nom,prenom:p.pre,equipe:'M11',dispos:null,saved_at:null,premiere:false});
   }
   if(api==='joueur/criterium'&&body&&body.dob==='2010-01-01')return send({error:'date_incorrecte',restants:2},401);
   if(api==='joueur/criterium'){
    (state.presenceSaves||(state.presenceSaves=[])).push(body);
    state.presences={[body.licence]:{present:body.present,at:'2026-10-04T12:00:00Z'}};
    return send({ok:true});
   }
   if(api==='joueur/cdp/entree'){
    if(body.dob!=='2010-03-07')return send({error:'date_incorrecte',restants:2},403);
    const p=state.players.find(x=>x.lic===body.licence);if(!p)return send({error:'licence_inconnue'},404);
    return send({licence:p.lic,nom:p.nom,prenom:p.pre,echeance:'2026-10-21T21:59:59Z',reponse:state.cdpRep||null});
   }
   if(api==='joueur/cdp'){(state.cdpSaves||(state.cdpSaves=[])).push(body);return send({ok:true,saved_at:'2026-09-30T10:00:00Z',retard:false});}
   if(api==='spo/cdp/dispos')return send({echeance:'2026-10-21T21:59:59Z',reponses:state.cdpReponses||{}});
   if(api==='spo/cdp/compos'){
    if(!body)return send({compos:state.cdpCompos||{}});
    (state.cdpCompoSaves||(state.cdpCompoSaves=[])).push(body);
    if(state.cdpConflict){state.cdpConflict=false;const current={id:41,journee:body.journee,statut:'brouillon',created_at:'2026-09-30T09:00:00Z',auteur:'Minh'};
     state.cdpCompos={...(state.cdpCompos||{}),[body.journee]:{...current,compo:body.compo}};return send({error:'conflit_composition',current},409);}
    const row={id:50+state.cdpCompoSaves.length,journee:body.journee,compo:body.compo,statut:body.statut,created_at:'2026-09-30T10:00:00Z',auteur:'Test'};
    state.cdpCompos={...(state.cdpCompos||{}),[body.journee]:row};return send({ok:true,row});
   }
   if(api==='cap/poule')return send({equipe:'M11',resultats:[]});
   if(api==='spo/alerts/dispos')return send({message:'Avis privé fictif'});
   if(api.startsWith('public/'))return send({items:[]});
   return send({});
  }
  if(url.hostname!=='127.0.0.1')return route.abort(); // jamais le réseau de production
  if(url.pathname==='/data/scoring.js')return route.fulfill({contentType:'text/javascript',body:'window.__SCORING='+JSON.stringify({players:state.players})+';'});
  if(url.pathname==='/data/scoring.json')return send({built:new Date().toISOString(),players:state.players});
  if(url.pathname==='/data/players_index.json')return send(state.playersIndex||[]);
  if(url.pathname==='/data/poules2627.json')return send(state.poules);
  if(url.pathname==='/data/site.json')return send(state.site);
  if(url.pathname==='/data/brulages2627.json')return state.brulages?send(state.brulages):route.fulfill({status:404,body:''});
  if(url.pathname==='/data/officiel2627.json')return send({saison:'2026/2027',officiel:state.officiel||{}});
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

test('accueil : trois compétitions en tuiles, une popup centrée par équipe avec calendrier et classement',async({page,context})=>{
 const state=fixture(),errors=[];
 state.site.DATA.M11.teams.find(t=>t.acbb).journees[0].opponent='ASNIERES TT 5';   // la vraie J1 de la M11
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/index.html');
 await expect(page.locator('.nv-tiles .nv-tile')).toHaveCount(3);
 const on=page.locator('.nv-tiles a.nv-tile.on');
 await expect(on).toHaveAttribute('aria-current','page');await expect(on).toContainText('Championnat');
 const paris=page.locator('.nv-tiles a.nv-tile[href$="cdp.html"]');   // le Championnat de Paris est ouvert
 await expect(paris).toContainText('de Paris');await expect(page.locator('.nv-tiles .nv-soon')).toHaveCount(0);
 await expect(page.locator('#eqgrid .eqb')).toHaveCount(state.poules.poules.length);
 await page.locator('#eqgrid .eqb[data-t="M11"]').click();
 await expect(page.locator('#ebg')).toBeVisible();
 await expect(page.locator('#eCode')).toContainText('M11');
 await expect(page.locator('#eCal .erow')).toHaveCount(state.poules.poules.find(p=>p.acbb==='M11').cal.length);
 await expect(page.locator('#eCal .erow').first()).toContainText('8 – 6');   // 22 – 20 FFTT, en parties gagnées
 await expect(page.locator('#eSt tr.me')).toContainText('ACBB · M11');
 const b=await page.locator('.emod').boundingBox();expect(Math.abs(b.x+b.width/2-page.viewportSize().width/2)).toBeLessThan(2);
 await page.keyboard.press('Escape');
 await expect(page.locator('#ebg')).toBeHidden();await expect(page.locator('#eqgrid .eqb[data-t="M11"]')).toBeFocused();
 expect(errors).toEqual([]);
});
test('mobile : accueil public et équipe restent consultables',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');await expect(page.locator('#iQ')).toBeVisible();
 await page.goto('/capitaine.html');await expect(page.locator('.prow')).toHaveCount(4);
 const overflow=await page.evaluate(()=>Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width})).slice(0,12));
 expect(overflow).toEqual([]);
 expect(errors).toEqual([]);
});
test('après J2 : la feuille manquante reste inconnue, puis les compteurs suivent la feuille réelle',async({page,context})=>{
 const state=fixture();await install(context,state);
 await page.clock.setFixedTime(new Date('2026-10-03T10:00:00Z'));
 await page.goto('/capitaine.html');
 await expect(page.locator('.prow').first().locator('.mj')).toHaveText('1/2 ?');
 await expect(page.locator('.prow').first().locator('.tick').nth(1)).toHaveText('?');
 // La feuille officielle J2 suffit à confirmer la participation, même si les
 // autres rencontres de la journée ne sont pas encore toutes remontées.
 const own=state.site.DATA.M11.teams.find(t=>t.acbb);
 own.journees.push({...own.journees[0],journee:2});
 await page.reload();
 await expect(page.locator('.prow').first().locator('.mj')).toHaveText('2/2');
 await expect(page.locator('.prow').first().locator('.tick').nth(1)).toHaveText('M11');
 // La FFTT retire parfois le total tout en conservant les parties de la feuille.
 delete own.journees[1].match_score;delete own.journees[1].opp_score;own.journees[1].played_games=5;
 await page.reload();await expect(page.locator('.prow').first().locator('.mj')).toHaveText('2/2');
 await page.goto('/sportive/journee.html?j=2');
 await expect(page.locator('.tc[data-team="M11"] .st')).toContainText('score en attente');
 await expect(page.locator('.tc[data-team="M11"]')).not.toContainText('NaN');
 await expect(page.locator('[data-st="M11"]')).toHaveCount(0);
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

test('critérium : chaque fiche utilise son groupe, y compris les compétitions sur plusieurs jours',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});await page.goto('/criterium.html');
 const data=read('criterium2627'),tour=data.tours[Object.keys(data.tours).sort().at(-1)];
 for(const g of tour.groupes){
  const j=g.joueurs.find(j=>j.acbb&&j.lic);if(!j)continue;
  await page.locator('#vue [data-sel="'+g.id+'|'+j.lic+'"]').click();
  await expect(page.locator('[data-date-groupe]')).toContainText(g.date);
  if(g.date_fin)await expect(page.locator('[data-date-groupe]')).toContainText(g.date_fin);
  else if(g.date!==tour.date)await expect(page.locator('[data-date-groupe]')).not.toContainText(tour.date);
  await page.getByRole('button',{name:'fermer',exact:true}).click();
 }
 // Une date absente ne doit pas être remplacée par le dimanche du tour.
 const withoutDate=structuredClone(data),g=withoutDate.tours['1'].groupes.find(g=>g.joueurs.some(j=>j.acbb));delete g.date;
 await context.route('**/data/criterium2627.json',r=>r.fulfill({json:withoutDate}));
 await page.reload();await page.locator('#vue [data-sel]').first().click();
 await expect(page.locator('[data-date-groupe]')).toHaveText('Date à confirmer');
 expect(errors).toEqual([]);
});

test('critérium mobile : saisie de naissance, validation puis confirmation de présence',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:320,height:568});await page.goto('/criterium.html');
 await page.locator('#vue [data-sel]').first().click();await page.getByRole('button',{name:'Confirmer ma présence',exact:true}).click();
 const dob=page.getByLabel('Date de naissance',{exact:true});
 await expect(dob).toHaveAttribute('type','text');await expect(dob).toHaveAttribute('inputmode','numeric');
 await dob.fill('31022010');await expect(dob).toHaveValue('31/02/2010');
 await page.getByRole('button',{name:'Je serai présent',exact:true}).click();
 await expect(page.locator('#mErr')).toContainText('date de naissance valide');expect(state.presenceSaves).toBeUndefined();
 // Écran réduit par le clavier : champ et boutons atteignables dans la fenêtre défilante.
 await page.setViewportSize({width:320,height:320});await dob.fill('07032010');
 await expect(dob).toHaveValue('07/03/2010');
 await page.getByRole('button',{name:'Je serai présent',exact:true}).click();
 await expect(page.locator('#modal')).toBeHidden();await expect(page.locator('#pop')).toContainText('✓ présent');
 expect(state.presenceSaves).toHaveLength(1);expect(state.presenceSaves[0].dob).toBe('2010-03-07');
 expect(errors).toEqual([]);
});

test('debrief capitaine : confirmation durable, relecture et texte conservé après un échec',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});await page.goto('/capitaine.html');
 const txt=page.locator('#debTxt');await expect(txt).toBeVisible();
 await page.locator('#scA').fill('7');await page.locator('#scB').fill('7');await txt.fill('Belle rencontre, *bravo* à tous 😅');
 await page.locator('#debSave').click();await expect(page.locator('#debStatus')).toContainText('Debrief enregistré le 04/10/2026');
 await expect(page.locator('#debStatus')).toContainText('publié sur l’accueil');
 expect(state.debriefs[0].texte).toBe('Belle rencontre, *bravo* à tous 😅');
 await page.reload();await expect(txt).toHaveValue('Belle rencontre, *bravo* à tous 😅');
 await expect(page.locator('#debStatus')).toContainText('Debrief enregistré');
 state.debriefError=true;await txt.fill('Texte modifié conservé même en cas d’erreur.');await page.locator('#debSave').click();
 await expect(page.locator('#debErr')).toContainText('Enregistrement refusé');await expect(txt).toHaveValue('Texte modifié conservé même en cas d’erreur.');
 await expect(page.locator('#debSave')).toBeEnabled();expect(errors).toEqual([]);
});

/* ---------- Championnat de Paris ---------- */
const cdpRep=(joue,non=[])=>({joue,dates:Object.fromEntries([1,2,3,4,5,6,7].map(k=>['j'+k,joue&&!non.includes(k)])),saved_at:'2026-09-29T09:00:00Z',retard:false});
const compoAvec=(eq,g,lics)=>{const c={1:[[null,null,null],[null,null,null],[null,null,null]],2:[[null,null,null],[null,null,null],[null,null,null]],3:[[null,null,null],[null,null,null],[null,null,null]],4:[[null,null,null],[null,null,null]],5:[[null,null,null]]};lics.forEach((l,k)=>{c[eq][g][k]=l;});return c;};

test('CDP joueur : identification, oui puis les vendredis, confirmation ; « non » en un clic',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/cdp.html');
 await expect(page.locator('.nv-tiles a.nv-tile.on')).toContainText('de Paris');
 await expect(page.locator('#cdates .cdate')).toHaveCount(7);await expect(page.locator('#ceqs .ceq')).toHaveCount(5);
 await expect(page.locator('#cpt')).toHaveText('dans 21 jours');
 await page.getByRole('button',{name:'Indiquer mes dispos'}).click();
 await expect(page.locator('#cbg')).toBeVisible();
 // recherche par prénom et/ou nom : un clic remplit la licence, reste la date de naissance
 const qq=page.getByRole('combobox',{name:'Ton prénom ou ton nom'});
 await qq.fill('exem');await expect(page.locator('#cList li[data-i]')).toHaveCount(5);
 await qq.fill('sam exem');await expect(page.locator('#cList li[data-i]')).toHaveCount(1);
 await qq.fill('alex');await page.getByRole('option',{name:/Alex EXEMPLE1/}).click();
 await expect(page.locator('#cMoi')).toContainText('licence '+state.players[0].lic);
 const dob=page.getByLabel('Date de naissance');await expect(dob).toBeFocused();
 await dob.fill('01022010');await expect(dob).toHaveValue('01/02/2010');
 await page.getByRole('button',{name:'Continuer'}).click();
 await expect(page.locator('#cErr1')).toContainText('Il te reste 2 essais');
 await dob.fill('07032010');await page.getByRole('button',{name:'Continuer'}).click();
 await expect(page.locator('#cName')).toHaveText('Alex EXEMPLE1');
 await expect(page.locator('#cSave')).toBeDisabled();   // rien n'est choisi d'office
 await page.locator('#cOui').click();await expect(page.locator('#cRows .drow')).toHaveCount(7);
 await page.getByRole('button',{name:/8 janvier 2027 : pas disponible/}).click();
 await page.locator('#cSave').click();
 await expect(page.locator('#cStep3')).toBeVisible();await expect(page.locator('#cBilan')).toContainText('6 vendredis sur 7');
 expect(state.cdpSaves[0]).toEqual({licence:state.players[0].lic,dob:'2010-03-07',joue:true,dates:{j1:true,j2:false,j3:true,j4:true,j5:true,j6:true,j7:true}});
 await page.locator('#cEdit').click();await page.locator('#cNon').click();await expect(page.locator('#cRows')).toBeHidden();
 await page.locator('#cSave').click();await expect(page.locator('#cBilan')).toHaveText('Tu ne joues pas le CDP cette saison.');
 expect(state.cdpSaves[1].joue).toBe(false);expect(Object.values(state.cdpSaves[1].dates).some(Boolean)).toBe(false);
 await page.keyboard.press('Escape');await expect(page.locator('#cbg')).toBeHidden();
 expect(errors).toEqual([]);
});

test('CDP sportive : tableau des dispos, compteurs par vendredi et filtres',async({page,context})=>{
 const state=fixture(),errors=[];const L=state.players.map(p=>p.lic);
 state.cdpReponses={[L[0]]:cdpRep(true),[L[1]]:cdpRep(true,[2]),[L[2]]:cdpRep(false)};
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/cdp-dispos.html');
 await expect(page.locator('.subnav.spo')).toContainText('Compositions CDP');
 await expect(page.locator('#cpt .cj')).toHaveCount(7);
 await expect(page.locator('#cpt .cj').nth(0)).toContainText('2');await expect(page.locator('#cpt .cj').nth(1)).toContainText('manque 35');
 await expect(page.locator('#chRep')).toHaveText('3 réponses sur 5');
 await page.getByRole('button',{name:/Pas répondu/}).click();await expect(page.locator('#tbody tr')).toHaveCount(2);
 await page.getByRole('button',{name:/Ne jouent pas/}).click();await expect(page.locator('#tbody tr')).toHaveCount(1);
 await expect(page.locator('#tbody')).toContainText('Chris EXEMPLE3');
 await page.getByRole('button',{name:/^Tous/}).click();await page.getByLabel('Chercher un joueur').fill('sam');
 await expect(page.locator('#tbody tr')).toHaveCount(1);await expect(page.locator('#tbody tr .tot')).toHaveText('6/7');
 expect(errors).toEqual([]);
});

test('CDP sportive : glisser-déposer, clic puis case, règles en direct et enregistrement',async({page,context})=>{
 const state=fixture(),errors=[];const L=state.players.map(p=>p.lic);
 state.cdpReponses=Object.fromEntries(L.map(l=>[l,cdpRep(true)]));
 // J1 à J3 : Alex et Sam en équipe 1 trois fois, donc brûlés pour l'équipe 2 ;
 // Jo une fois en équipe 1 puis deux fois en équipe 2 : les matchs se cumulent, brûlé pour les équipes 3 à 5 seulement
 state.cdpCompos=Object.fromEntries([1,2,3].map(k=>{const c=compoAvec(1,0,k===1?[L[0],L[1],L[3]]:[L[0],L[1]]);if(k>1)c[2][0][0]=L[3];
  return [k,{id:k,journee:k,statut:'envoyee',created_at:'2026-09-20T10:00:00Z',auteur:'Test',compo:c}];}));
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/cdp-compo.html?j=4');
 await expect(page.locator('#hJ')).toHaveText('J4');
 await expect(page.locator('#lDisp [data-carte]')).toHaveCount(5);
 await expect(page.locator('#lDisp [data-carte="'+L[0]+'"]')).toContainText('brûlé pour les équipes 2 à 5');
 await expect(page.locator('#lDisp [data-carte="'+L[3]+'"]')).toContainText('brûlé pour les équipes 3 à 5');
 // glisser-déposer : Alex en PE2 groupe 1
 await page.locator('#lDisp [data-carte="'+L[0]+'"]').dragTo(page.locator('[data-case="2-0-0"]'));
 await expect(page.locator('[data-case="2-0-0"]')).toContainText('Alex EXEMPLE1');
 // clic puis case : Sam dans le même groupe → deux brûlés
 await page.locator('#lDisp [data-carte="'+L[1]+'"]').click();await expect(page.locator('#aide')).toContainText('Sam EXEMPLE2 sélectionné');
 await page.locator('[data-case="2-0-1"]').click();
 await expect(page.locator('.eq').nth(1).locator('.cg').first()).toHaveClass(/ko/);
 await expect(page.locator('.eq').nth(1)).toContainText('2 brûlés dans ce groupe');
 await expect(page.locator('#chAl')).toContainText('alerte');
 // l'inverse : case vide puis joueur. Nova (moins de points) en groupe 1, Chris en groupe 2 : ordre faux (art. 8)
 await page.locator('[data-case="1-0-0"]').click();await page.locator('#lDisp [data-carte="'+L[4]+'"]').click();
 await page.locator('[data-case="1-1-0"]').click();await page.locator('#lDisp [data-carte="'+L[2]+'"]').click();
 await expect(page.locator('.eq').first()).toContainText('a plus de points que Nova EXEMPLE5');
 // retirer Sam : l'alerte de brûlage disparaît
 await page.getByRole('button',{name:'Retirer Sam EXEMPLE2 de l’équipe'}).click();
 await expect(page.locator('.eq').nth(1)).not.toContainText('2 brûlés');
 await page.locator('#bSave').click();await expect(page.locator('#svSt')).toContainText('Brouillon enregistré');
 await expect(page.locator('#bSave')).toBeDisabled();expect(state.cdpCompoSaves).toHaveLength(1);
 const s=state.cdpCompoSaves[0];expect(s.journee).toBe(4);expect(s.expected_id).toBe(0);expect(s.statut).toBe('brouillon');
 expect(s.compo['2'][0]).toEqual([L[0],null,null]);expect(s.compo['1'][0][0]).toBe(L[4]);expect(s.compo['1'][1][0]).toBe(L[2]);
 expect(errors).toEqual([]);
});

test('CDP sportive : un enregistrement concurrent est signalé, rien n’est écrasé sans choix',async({page,context})=>{
 const state=fixture(),errors=[];const L=state.players.map(p=>p.lic);
 state.cdpReponses=Object.fromEntries(L.map(l=>[l,cdpRep(true)]));state.cdpConflict=true;
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/cdp-compo.html?j=1');
 await page.locator('#lDisp [data-carte="'+L[0]+'"]').click();await page.locator('[data-case="5-0-0"]').click();
 await page.locator('#bSave').click();
 await expect(page.locator('#conflit')).toBeVisible();await expect(page.locator('#conflit')).toContainText('par Minh');
 await expect(page.locator('[data-case="5-0-0"]')).toContainText('Alex EXEMPLE1');   // la saisie reste à l'écran
 await page.getByRole('button',{name:'Garder la mienne et enregistrer'}).click();
 await expect(page.locator('#conflit')).toBeHidden();
 expect(state.cdpCompoSaves).toHaveLength(2);expect(state.cdpCompoSaves[1].expected_id).toBe(41);
 expect(errors).toEqual([]);
});

test('sous-sportive CDP : les outils du Championnat de Paris seulement, son espace capitaine conservé',async({page,context})=>{
 const state=fixture(),errors=[];state.role='cdp';state.cdpReponses={};
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/cdp-dispos.html');
 await expect(page.locator('#main')).toBeVisible();await expect(page.locator('#gateMsg')).toBeHidden();
 const sub=page.locator('.subnav.spo');await expect(sub).toContainText('Compositions CDP');await expect(sub).not.toContainText('Compos journée');
 await expect(page.locator('#hdr')).toContainText('Sous-sportive CDP');
 await page.goto('/sportive/cdp-compo.html');await expect(page.locator('#main')).toBeVisible();
 for(const p of ['/sportive/journee.html','/sportive/acces.html','/sportive/debriefs.html','/sportive/suivi-dispos.html']){
  await page.goto(p);await expect(page.locator('#gateMsg')).toBeVisible();
 }
 // la maquette rattache l'équipe M11 au lien : ses onglets capitaine restent, aucun onglet sportive
 await page.goto('/index.html');await expect(page.locator('.subnav.cap')).toContainText('Mon équipe');
 await expect(page.locator('#hdr')).not.toContainText('Compos journée');
 expect(errors).toEqual([]);
});

test('Accès : un lien capitaine devenu sous-sportive CDP reste celui de son équipe, et la fin de phase ne lui retire que l’équipe',async({page,context})=>{
 const state=fixture(),errors=[];
 state.liens=[{id:35,role:'cdp',equipe:'F1',nom:'Marion MERIC',actif:true,created_at:'2026-09-16T10:00:00Z',last_used_at:'2026-10-04T16:13:00Z',appareils:1,ips:1},
  {id:36,role:'capitaine',equipe:'M11',nom:'Alex EXEMPLE1',actif:true,created_at:'2026-09-16T10:00:00Z',last_used_at:null,appareils:0,ips:0}];
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/acces.html');
 const f1=page.locator('#capList .lr').filter({has:page.locator('.tn',{hasText:/^F1$/})});
 await expect(f1).toContainText('Marion MERIC');await expect(f1).toContainText('sous-sportive CDP');await expect(f1.locator('.st')).toContainText('actif');
 await expect(page.locator('#cdpList')).toContainText('Marion MERIC');await expect(page.locator('#cdpList select.eqsel')).toHaveValue('F1');
 page.once('dialog',d=>d.accept());await page.locator('#revAll').click();
 await expect.poll(()=>(state.lienOps||[]).length).toBe(2);
 expect(state.lienOps).toEqual([['spo/liens/revoquer',{id:36}],['spo/liens/equipe',{id:35,equipe:null}]]);
 expect(errors).toEqual([]);
});

test('capitaine · poule : classement moyen joué de chaque adversaire, tous ses joueurs et le badge brûlé',async({page,context})=>{
 const state=fixture(),errors=[];
 const opp=state.site.DATA.M11.teams.find(t=>/PUTEAUX/.test(t.name));
 const pl=(nom,prenom,cls,vic)=>({nom,prenom,cls,vic});
 opp.journees=[{journee:1,date:'18 sept. 2026',opponent:'BOURG LA REINE 2',played_games:14,match_score:25,opp_score:17,players:[pl('ALPHA','Ana',1200,3),pl('BETA','Bob',1100,1),pl('GAMMA','Gus',1000,0)]},
  {journee:2,date:'2 oct. 2026',opponent:'BOULOGNE BILLANCOURT AC 11',played_games:14,match_score:24,opp_score:18,players:[pl('ALPHA','Ana',1200,2),pl('DELTA','Dan',1300,2)]}];
 state.brulages={built:'2026-10-05T06:10:00Z',equipes:{[opp.name]:{brules:[{nom:'BETA',prenom:'Bob',rencontres:[{j:2,eq:1},{j:3,eq:2}]}],lues:[1,2],manquantes:[]}}};
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/capitaine.html?tab=poule');
 const row=page.locator('#opps .orow[data-j="2"]');
 await expect(row.locator('.av')).toHaveText('⌀ 1160');   // (1200+1100+1000+1200+1300)/5
 await row.click();
 const sc=page.locator('#scout');
 await expect(sc).toContainText('Joueurs alignés en 26/27');const al=sc.locator('[data-bloc="alignes"]');await expect(al.locator('.card2')).toHaveCount(4);   // vus une seule fois compris
 const bob=al.locator('.card2',{hasText:'Bob Beta'});
 await expect(bob.locator('.tag.lose')).toHaveText('brûlé');await expect(bob).toHaveClass(/brule/);
 await expect(bob.locator('.tag.lose')).toHaveAttribute('title',/J2 en équipe 1, J3 en équipe 2.*ne peut plus jouer en équipe 3/);
 await expect(al.locator('.card2',{hasText:'Gus Gamma'})).toContainText('1 feuille');
 await expect(sc).toContainText('1 brûlé');await expect(sc).toContainText('Brûlage vérifié sur les feuilles');
 expect(errors).toEqual([]);
});

test('CDP joueur : recherche au clavier, « ce n’est pas moi », et saisie manuelle de la licence',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/cdp.html');await page.locator('#cdpGo').click();
 const qq=page.getByRole('combobox',{name:'Ton prénom ou ton nom'});await expect(qq).toBeFocused();
 await qq.fill('nova');await qq.press('ArrowDown');await qq.press('Enter');
 await expect(page.locator('#cMoiNom')).toHaveText('Nova EXEMPLE5');
 await page.getByRole('button',{name:'Ce n\'est pas moi'}).click();
 await expect(qq).toBeVisible();await expect(qq).toHaveValue('');
 await qq.fill('zzz');await expect(page.locator('#cList')).toContainText('Aucun licencié trouvé');
 await page.getByRole('button',{name:'Je ne me trouve pas : saisir ma licence'}).click();
 const lic=page.getByLabel('N° de licence');await expect(lic).toBeVisible();
 await page.getByRole('button',{name:'Continuer'}).click();await expect(page.locator('#cErr1')).toHaveText('Saisis ton numéro de licence.');
 await lic.fill(state.players[3].lic);await page.getByLabel('Date de naissance').fill('07032010');
 await page.getByRole('button',{name:'Continuer'}).click();await expect(page.locator('#cName')).toHaveText('Jo EXEMPLE4');
 expect(errors).toEqual([]);
});

test('dispos du championnat : on cherche son nom, la licence suit ; la dernière licence revient en carte',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/index.html');
 const qq=page.locator('#iQ');await qq.fill('chris');
 await page.getByRole('option',{name:/Chris EXEMPLE3/}).click();
 await expect(page.locator('#iMoi')).toContainText('Chris EXEMPLE3');await expect(page.locator('#iDob')).toBeFocused();
 await page.locator('#iDob').fill('07032010');await page.locator('#iGo').click();
 await expect(page.locator('#mName')).toHaveText('Chris EXEMPLE3');
 expect(state.entrees.at(-1)).toEqual({licence:state.players[2].lic,dob:'2010-03-07'});
 // retour sur la page : la licence mémorisée revient sous forme de carte, il ne reste que la date
 await page.goto('/index.html');await expect(page.locator('#iMoi')).toBeVisible();await expect(page.locator('#iMoiNom')).toHaveText('Chris EXEMPLE3');
 await page.getByRole('button',{name:'Ce n\'est pas moi'}).click();await expect(qq).toBeVisible();await expect(qq).toBeFocused();
 // mauvaise date : la modale garde la personne choisie et dit combien d'essais restent
 await qq.fill('jo exe');await qq.press('Enter');await page.locator('#iDob').fill('01012011');await page.locator('#iGo').click();
 await expect(page.locator('#mErr')).toContainText('Il te reste 2 essais');await expect(page.locator('#mMoiNom')).toHaveText('Jo EXEMPLE4');
 expect(errors).toEqual([]);
});

test('critérium : la recherche accepte prénom et nom dans n’importe quel ordre ; confirmer ne demande que la date',async({page,context})=>{
 const state=fixture(),errors=[];await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/criterium.html');
 const carte=page.locator('#vue [data-sel]').first();await expect(carte).toBeVisible();
 await carte.click();await page.getByRole('button',{name:'Confirmer ma présence',exact:true}).click();
 await expect(page.locator('#mLic')).toHaveCount(0);await expect(page.getByLabel('Date de naissance')).toBeFocused();
 await expect(page.locator('#modal')).toContainText('licence ');
 await page.getByLabel('Date de naissance').fill('01012010');await page.getByRole('button',{name:'Je serai présent',exact:true}).click();
 await expect(page.locator('#mErr')).toHaveText('Date de naissance incorrecte. Il te reste 2 essais.');
 await page.getByRole('button',{name:'Ce n\'est pas moi'}).click();
 await expect(page.locator('#modal')).toBeHidden();await expect(page.locator('#q')).toBeFocused();
 expect(errors).toEqual([]);
});

test('CDP sportive : un licencié absent du scoring s’affiche sous son nom, pas sous sa licence',async({page,context})=>{
 const state=fixture(),errors=[];
 state.playersIndex=[{lic:'90000099',nom:'BOILLOT LE GOFFIC',prenom:'Alexandre',officiel:500,mensuel:500}];
 state.cdpReponses={'90000099':cdpRep(true,[2,3,5,6])};
 await install(context,state);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/sportive/cdp-dispos.html');
 await expect(page.locator('#tbody')).toContainText('Alexandre BOILLOT LE GOFFIC');
 await expect(page.locator('#tbody')).not.toContainText('Licence 90000099');
 // et il se trouve par son nom sur la page publique
 await page.goto('/cdp.html');await page.locator('#cdpGo').click();
 await page.getByRole('combobox',{name:'Ton prénom ou ton nom'}).fill('boillot');
 await expect(page.getByRole('option',{name:/Alexandre BOILLOT LE GOFFIC/})).toBeVisible();
 expect(errors).toEqual([]);
});
