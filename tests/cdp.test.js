const test=require('node:test'),assert=require('node:assert/strict');
const CDP=require('../shared/cdp.js');
const P={a:1822,b:1811,c:1703,d:1698,e:1660,f:1637,g:1624,h:1617,i:1600,j:1594,k:1587,l:1586,m:1577,n:1539,o:1525,p:1500,q:1465,r:1430};
const pe=(g1,g2,g3)=>({...CDP.compoVide(),1:[g1,g2,g3]});
test('36 places, 5 équipes, 7 vendredis',()=>{
  assert.equal(CDP.PLACES,36);assert.equal(CDP.EQUIPES.length,5);assert.equal(CDP.JOURNEES.length,7);
  CDP.JOURNEES.forEach(x=>assert.equal(new Date(x.date+'T12:00:00Z').getUTCDay(),5));   // tous des vendredis
});
test('historique : seules les journées antérieures comptent',()=>{
  const compos={1:{compo:{1:[['m','n',null]]}},2:{compo:{1:[['m','n',null]]}},3:{compo:{1:[['m',null,null]]}},4:{compo:{1:[['n',null,null]]}}};
  const h=CDP.historique(compos,4);
  assert.deepEqual(h.m,{1:3});assert.deepEqual(h.n,{1:2});
});
test('brûlage (art. 12) : 3 matchs cumulés dans les équipes de numéro inférieur',()=>{
  assert.equal(CDP.brulePour({1:3},2),3);assert.equal(CDP.brulePour({1:2},2),null);
  assert.equal(CDP.brulePour({3:3},3),null);assert.equal(CDP.brulePour({3:3},4),3);
  assert.equal(CDP.premierBrule({3:3}),4);
  // l'exemple de Charles : 1 match en équipe 1 et 2 en équipe 2 → encore qualifié en 2, brûlé en 3, 4 et 5
  const ex={1:1,2:2};
  assert.equal(CDP.brulePour(ex,2),null);assert.equal(CDP.brulePour(ex,3),3);assert.equal(CDP.premierBrule(ex),3);
  // à un match du brûlage, et ce que change un match de plus
  assert.equal(CDP.aUnMatch({1:2}),true);assert.equal(CDP.aUnMatch({1:1,3:1}),true);assert.equal(CDP.aUnMatch({5:2}),false);
  assert.equal(CDP.bruleApres({2:2},2),3);assert.equal(CDP.bruleApres({1:1,3:1},3),4);assert.equal(CDP.bruleApres({1:1},1),null);
  assert.equal(CDP.bruleApres({1:3},1),null);   // déjà brûlé partout au-dessus : rien de neuf
});
test('deux brûlés dans un même groupe de l’équipe 2 : erreur sur ce groupe',()=>{
  const c=CDP.compoVide();c[2][1]=['m','n','o'];
  const r=CDP.controler(c,P,{m:{1:3},n:{1:3}});
  assert.equal(r.equipes[2].groupes[1].alertes.filter(a=>a.type==='brulage').length,1);
  const un=CDP.controler(c,P,{m:{1:3}});
  assert.equal(un.equipes[2].groupes[1].alertes.filter(a=>a.type==='brulage').length,0);
  // en équipe 3 : m (1 en équipe 1 + 2 en équipe 2) et n (3 en équipe 2) sont tous deux brûlés
  const c3=CDP.compoVide();c3[3][0]=['m','n','o'];
  const r3=CDP.controler(c3,P,{m:{1:1,2:2},n:{2:3}});
  assert.deepEqual(r3.equipes[3].groupes[0].alertes.find(a=>a.type==='brulage').licences,['m','n']);
});
test('ordre des groupes (art. 8) : un joueur plus fort en dessous est une erreur, l’ordre interne est libre',()=>{
  const ok=CDP.controler(pe(['c','a','b'],['d','e','f'],['g','h','i']),P,{});
  assert.equal(ok.equipes[1].groupes.flatMap(g=>g.alertes).filter(a=>a.type==='ordre').length,0);
  const ko=CDP.controler(pe(['a','b','c'],['d','e','i'],['f','g','h']),P,{});
  const al=ko.equipes[1].groupes[2].alertes.find(a=>a.type==='ordre');
  assert.ok(al);assert.equal(al.fort,'f');assert.equal(al.faible,'i');
});
test('absents (art. 9) : un seul, et dans le groupe le plus faible',()=>{
  const bon=CDP.controler(pe(['a','b','c'],['d','e','f'],['g','h',null]),P,{});
  assert.equal(bon.equipes[1].absents,1);assert.ok(bon.equipes[1].note);
  const mal=CDP.controler(pe(['a','b',null],['d','e','f'],['g','h','i']),P,{});
  assert.ok(mal.equipes[1].groupes[0].alertes.some(a=>a.type==='absent'));
  const deux=CDP.controler(pe(['a','b','c'],['d','e',null],['g','h',null]),P,{});
  assert.ok(deux.equipes[1].groupes[2].alertes.some(a=>a.type==='absents'));
});
test('un joueur dans deux équipes, ou qui s’est dit indisponible',()=>{
  const c=CDP.compoVide();c[1][0]=['a','b','c'];c[2][0]=['a','j','k'];
  const r=CDP.controler(c,P,{},{b:false});
  assert.ok(r.equipes[2].groupes[0].alertes.some(a=>a.type==='double'));
  assert.ok(r.equipes[1].groupes[0].alertes.some(a=>a.type==='indispo'&&a.licence==='b'));
});
