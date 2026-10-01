const test=require('node:test'),assert=require('node:assert/strict');
const PART=require('../shared/participations.js'), RULES=require('../shared/regles.js');
const players=[{lic:'101',nom:'TEST',pre:'Alex',men:1000},{lic:'102',nom:'SECOND',pre:'Sam',men:1100}];
const byKey=Object.fromEntries(players.map(p=>[p.lic,p]));
function pool(t,exempt=false){return {acbb:t,division:'D1',poule:+t.slice(1),cal:[{j:1,date:'18/09/2026',exempt},{j:2,date:'02/10/2026'}]};}
function sheet(t,j,ps=players){return {[t]:{teams:[{acbb:true,journees:[{journee:j,match_score:22,opp_score:20,players:ps.map(p=>({nom:p.nom,prenom:p.pre}))}]}]}};}
function model(extra={}){return PART.create({today:'2026-09-30',players,poules:{M9:pool('M9'),M11:pool('M11')},...extra});}
test('J1 réelle M11 remplace le plan M9, même si la feuille M9 manque',()=>{
 const m=model({site:{DATA:sheet('M11',1)},plans:{1:{M9:{p:['101'],st:'sent'}}}});
 assert.deepEqual(m.history('101',2).map(x=>x.t),['M11']);
 assert.deepEqual(m.assignments('101',1).map(x=>x.t),['M11']);
 assert.equal(m.parcours('101','M9').joue,1);
 assert(m.missing(2,'M').some(x=>x.t==='M9'));
});
test('un plan seul ne prouve ni participation ni absence',()=>{
 const m=model({plans:{1:{M9:{p:['101'],st:'sent'}}}});
 assert.equal(m.history('101',2).length,0);
 assert.equal(m.parcours('101','M9').jours[0].unknown,true);
});
test('dames et messieurs restent indépendants',()=>{
 const m=model({site:{DATA:{...sheet('M11',1),...sheet('F3',1)}},poules:{M11:pool('M11'),F3:pool('F3')}});
 assert.equal(m.history('101',2,'M').length,1);
 assert.equal(m.parcours('101','M11').joue,1);
 assert.deepEqual(m.parcours('101','M11').jours[0].tous,['M11']);
});
test('exemption déclarée compte pour les règles, pas pour les matchs disputés',()=>{
 const m=model({poules:{M15:pool('M15',true)},plans:{1:{M15:{p:['101'],st:'sent'}}}});
 assert.equal(m.history('101',2)[0].source,'exemption');
 assert.equal(m.parcours('101','M15').joue,0);
 assert.equal(m.parcours('101','M15').exemptions,1);
});
test('un brouillon ou une exemption future ne devient pas une participation',()=>{
 for(const [today,st] of [['2026-09-30','draft'],['2026-09-01','sent']]){
  const m=model({today,poules:{M15:pool('M15',true)},plans:{1:{M15:{p:['101'],st}}}});
  assert.equal(m.history('101',2).length,0);
 }
});
test('un homonyme au seul nom de famille ne peut pas être attribué',()=>{
 const m=model({site:{DATA:sheet('M11',1,[{nom:'TEST',pre:'UnAutre'}])}});
 assert.equal(m.history('101',2).length,0);assert.equal(m.unknown.length,1);
});
test('la règle J2 lit les vraies feuilles et inclut une exemption',()=>{
 const m=model({poules:{M9:pool('M9',true),M11:pool('M11')},plans:{1:{M9:{p:['101','102'],st:'sent'}},2:{M11:{p:['101','102']}}}});
 const issues=RULES.check({model:m,t:'M11',j:2,players:byKey,poules:{M9:pool('M9',true),M11:pool('M11')},extras:{}});
 assert(issues.some(i=>i.code==='brulage'&&i.lvl==='err'&&i.keys.length===2));
});
test('un même joueur listé deux fois sur une journée ne vaut pas deux journées de brûlage',()=>{
 const m=model({site:{DATA:{...sheet('M9',1),...sheet('M11',1)}}});
 assert.equal(PART.historyRules(m,'101','M15',2,{}).burned,false);
});
test('sexe absent et statuts privés absents produisent des vérifications',()=>{
 const m=model({plans:{2:{M3:{p:['101','102']}}}});
 const a=RULES.check({model:m,t:'M3',j:2,division:'R1',players:byKey});
 assert(a.some(i=>i.code==='feminines'&&i.lvl==='warn'));
 assert(a.some(i=>i.code==='ex'&&i.lvl==='warn'));
});
test('trois féminines en régionale déclenchent le quota, indépendamment des noms',()=>{
 const ps=[...players,{lic:'103',nom:'THIRD',pre:'Chris',men:1200}];
 const m=model({players:ps,plans:{2:{M3:{p:ps.map(p=>p.lic)}}}});
 const a=RULES.check({model:m,t:'M3',j:2,division:'R1',players:Object.fromEntries(ps.map(p=>[p.lic,p])),sexes:{101:'F',102:'F',103:'F'},extras:{}});
 assert(a.some(i=>i.code==='feminines'&&i.lvl==='err'));
});
test('M1 J1 manquante ne rend pas incertains les joueurs confirmés ailleurs',()=>{
 const pools={M1:pool('M1'),M11:pool('M11')};
 const m=model({poules:pools,site:{DATA:sheet('M11',1)},plans:{2:{M11:{p:['101','102']}}}});
 assert.deepEqual(m.missing(2,'M').map(x=>x.t),['M1']);
 assert.deepEqual(m.missingFor('101',2,'M'),[]);
 assert.equal(PART.historyRules(m,'101','M11',2,pools).incomplete,false);
 assert(!RULES.check({model:m,t:'M11',j:2,players:byKey,poules:pools,extras:{}}).some(i=>i.code==='source'));
});
test('une alerte de source vise uniquement le joueur sans participation confirmée',()=>{
 const pools={M1:pool('M1'),M11:pool('M11')};
 const m=model({poules:pools,site:{DATA:sheet('M11',1,[players[0]])},
   plans:{1:{M1:{p:['102'],st:'sent'}},2:{M11:{p:['101','102']}}}});
 const warning=RULES.check({model:m,t:'M11',j:2,players:byKey,poules:pools,extras:{}}).find(i=>i.code==='source');
 assert.deepEqual(warning.keys,['102']);
 assert.match(warning.msg,/Sam SECOND/);assert.doesNotMatch(warning.msg,/Alex TEST/);
 assert.equal(PART.historyRules(m,'102','M11',2,pools).incomplete,true);
 // Le plan envoyé ne remplace pas la feuille réelle manquante.
 assert.equal(m.history('102',2,'M').length,0);
});
test('une exemption confirmée résout le manque individuel sans ajouter de match disputé',()=>{
 const m=model({poules:{M1:pool('M1'),M15:pool('M15',true)},plans:{1:{M15:{p:['101'],st:'sent'}}}});
 assert.deepEqual(m.missingFor('101',2,'M'),[]);
 assert.equal(m.parcours('101','M15').joue,0);
 assert.equal(m.parcours('101','M15').inconnus,0);
});
test('une preuve ne complète ni une autre journée ni un autre championnat',()=>{
 const m=model({poules:{M1:pool('M1'),M11:pool('M11'),F3:pool('F3')},site:{DATA:sheet('M11',1)}});
 assert(m.missingFor('101',3,'M').every(x=>x.j===2));
 assert(m.missingFor('101',2,'F').some(x=>x.t==='F3'));
});
test('une non-participation confirmée lève uniquement le doute du joueur et de la journée concernés',()=>{
 const m=model({poules:{M1:pool('M1'),M11:pool('M11'),F3:pool('F3')},
  nonParticipations:[{k:'TEST|Alex',j:1,championnat:'M',saison:'2026/2027',phase:1,confirmed:true}]});
 const pc=m.parcours('101','M11');
 assert.equal(pc.joue,0);assert.equal(pc.jours[0].t,null);assert.equal(pc.inconnus,0);
 assert.equal(m.history('101',2).length,0); // NJ n'est jamais une participation réglementaire.
 assert(m.missingFor('102',2,'M').length);
 assert(m.missingFor('101',2,'F').length);
 assert(m.missingFor('101',3,'M').every(x=>x.j===2));
});
test('une confirmation NJ future, non validée ou d’une autre saison/phase ne masque aucune feuille manquante',()=>{
 const n={k:'101',j:1,championnat:'M',saison:'2026/2027',phase:1,confirmed:true};
 for(const extra of [{confirmed:false},{saison:'2025/2026'},{phase:2}]){
  assert(model({nonParticipations:[{...n,...extra}]}).parcours('101','M11').inconnus>0);
 }
 assert(model({today:'2026-09-01',nonParticipations:[n]}).missingFor('101',2,'M').length>0);
});
test('une feuille réelle ultérieure prime sur une déclaration NJ',()=>{
 const m=model({nonParticipations:[{k:'101',j:1,championnat:'M',saison:'2026/2027',phase:1,confirmed:true}],site:{DATA:sheet('M11',1)}});
 assert.equal(m.parcours('101','M11').joue,1);assert.equal(m.parcours('101','M11').jours[0].t,'M11');
 assert.equal(PART.historyRules(m,'101','M15',2,{}).descendedJ2,true);
});
