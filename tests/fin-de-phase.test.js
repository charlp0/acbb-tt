const test=require('node:test');
const assert=require('node:assert');
const fs=require('node:fs');
const FDP=require('../shared/fin-de-phase.js');

// Même alignement de contrôle que tests/test_fin_de_phase.py : Python et JS doivent donner la même espérance.
const LA=[{cls:1600,adj:20},{cls:1500,adj:0},{cls:1450,adj:-30},{cls:1400,adj:0}];
const LB=[{cls:1550,adj:0},{cls:1500,adj:10},{cls:1480,adj:0},{cls:1300,adj:0}];
const EXPECTED_SINGLES_S400=6.3933;

test('espérance de simples identique au moteur Python',()=>{
  assert.ok(Math.abs(FDP.expectedSingles(LA,LB,400)-EXPECTED_SINGLES_S400)<1e-3);
  assert.ok(FDP.expectedSingles(LA,LB.slice(0,3),400)>EXPECTED_SINGLES_S400+0.5);
});

test('départage art. 14 : confrontation directe avant l’écart total de parties',()=>{
  const teams=['A','B','C'], pts={A:10,B:10,C:4};
  const mini={A:{B:[1,-2],C:[3,10]},B:{A:[3,2],C:[3,4]},C:{A:[1,-10],B:[1,-4]}};
  assert.deepStrictEqual(FDP.rankTeams(teams,pts,mini,{A:8,B:6,C:-14}),['B','A','C']);
  assert.deepStrictEqual(FDP.rankTeams(teams,pts,{A:{},B:{},C:{}},{A:8,B:6,C:-14}),['A','B','C']);
});

test('brûlage II.112 : deux journées en équipe plus forte brûlent pour l’équipe visée',()=>{
  assert.strictEqual(FDP.brulage([{j:1,n:3},{j:2,n:3}],5,5).burned,true);
  assert.strictEqual(FDP.brulage([{j:1,n:3},{j:2,n:6}],5,5).burned,false);   // une seule journée au-dessus
  assert.strictEqual(FDP.brulage([{j:1,n:3},{j:6,n:3}],5,5).burned,false);   // la J6 est après la journée visée
  assert.strictEqual(FDP.brulage([],5,5).burned,false);
});

test('simulation : un renfort fort relève les chances et la graine rend le calcul reproductible',()=>{
  const doc=JSON.parse(fs.readFileSync('data/fin_de_phase.json','utf8'));
  const T=doc.teams.M5; T.key='M5';
  const base=FDP.simulate(T,{s:doc.s,nsim:800,seed:7});
  const again=FDP.simulate(T,{s:doc.s,nsim:800,seed:7});
  assert.strictEqual(base.pObjectif,again.pObjectif);
  const renfort=[{nom:'BOUDJADJA',pre:'Mohamed Sofiane',cls:2267,adj:0}];
  const scen=FDP.simulate(T,{s:doc.s,nsim:800,seed:7,override:(j,team,lineup)=>team===T.acbb?FDP.withRenforts(lineup,renfort):null});
  assert.ok(scen.pObjectif>base.pObjectif,'le renfort doit augmenter la probabilité de montée');
  Object.values(base.teams).forEach(t=>assert.ok(Math.abs(t.ranks.reduce((a,b)=>a+b,0)-1)<1e-9));
  const l=FDP.withRenforts(LA,renfort);
  assert.strictEqual(l.length,4); assert.strictEqual(l[0].nom,'BOUDJADJA'); assert.strictEqual(l[3].cls,1450);
});
