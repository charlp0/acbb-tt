const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../shared/contraintes.js');
const A={k:'1',nom:'ALLEGRE-GUILLAUME',pre:'Antoine'}, B={k:'2',nom:'ALLEGRE-GUILLAUME',pre:'Baptiste'};
const liste=[{id:'x',type:'lieu',journee:4,joueurs:[A,B]}];
const BYKEY={'1':{nom:'ALLEGRE-GUILLAUME',pre:'Antoine'},'2':{nom:'ALLEGRE-GUILLAUME',pre:'Baptiste'},'3':{nom:'AUTRE',pre:'Zoé'}};
const lieux={M9:{venue:'Gymnase A',dom:false,opp:'CHATENAY 5'},M11:{venue:'Gymnase B',dom:false,opp:'PLESSIS 3'},M10:{venue:'Gymnase A',dom:false,opp:'CHATENAY 6'},M12:{venue:'',dom:false,opp:'INCONNU'}};
const ctx=(t,P,ou)=>({t,j:4,P,BYKEY,equipeDe:cp=>ou[cp.k]||null,lieuDe:o=>lieux[o]||null});
test('même équipe : rien à dire',()=>{ assert.deepEqual(C.check(liste,ctx('M9',['1','2'],{})),[]); });
test('deux équipes au même endroit : rien à dire',()=>{ assert.deepEqual(C.check(liste,ctx('M9',['1'],{'2':'M10'})),[]); });
test('deux équipes dans des salles différentes : erreur sur la journée visée',()=>{
  const out=C.check(liste,ctx('M9',['1'],{'2':'M11'}));
  assert.equal(out.length,1);assert.equal(out[0].lvl,'err');assert.match(out[0].msg,/A\. ALLEGRE-GUILLAUME \(M9, chez CHATENAY 5\) et B\. ALLEGRE-GUILLAUME \(M11, chez PLESSIS 3\) doivent impérativement jouer au même endroit en J4/);
  assert.deepEqual(out[0].keys,['1']);
});
test('lieu inconnu : avertissement, pas d’erreur ; autre journée : rien',()=>{
  assert.equal(C.check(liste,ctx('M9',['1'],{'2':'M12'}))[0].lvl,'warn');
  assert.deepEqual(C.check(liste,{...ctx('M9',['1'],{'2':'M11'}),j:3}),[]);
});
test('un frère non aligné : avertissement ; hors journée (Scoring) : information',()=>{
  const out=C.check(liste,ctx('M9',['1'],{}));assert.equal(out.length,1);assert.equal(out[0].lvl,'warn');assert.match(out[0].msg,/pas aligné : B\. ALLEGRE-GUILLAUME/);
  const info=C.check(liste,{t:'M9',j:null,P:['1','2'],BYKEY});assert.equal(info[0].lvl,'info');
});
test('libellés et validation du type lieu',()=>{
  assert.equal(C.titre(liste[0]),'Antoine ALLEGRE-GUILLAUME et Baptiste ALLEGRE-GUILLAUME au même endroit (J4)');
  assert.equal(C.valider({type:'lieu',joueurs:[A]}),'il faut au moins deux joueurs');assert.equal(C.valider(liste[0]),null);
});
