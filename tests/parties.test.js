const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
// shared/api.js est un script navigateur : on le charge dans un bac à sable qui ne fournit que window.
const ctx={window:{}}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'..','shared','api.js'),'utf8'),ctx);
const parties=ctx.window.ACBB.parties;
const feuille=(ms,os,g,vics,doubles=0)=>({match_score:ms,opp_score:os,played_games:g,doubles,players:vics.map(v=>({vic:v}))});

test('rencontre complète en 14 parties : 22 – 20 FFTT = 8 – 6',()=>{
  assert.deepEqual([...parties(feuille(22,20,14,[2,2,2,2]))],[8,6]);
  assert.deepEqual([...parties(feuille(28,14,14,[4,4,3,3],0))],[14,0]);
});
test('une partie gagnée par forfait : M9 J2, 23 – 18 FFTT = 9 – 5, pas 23 – 18',()=>{
  assert.deepEqual([...parties(feuille(23,18,13,[2,2,2,1],1))],[9,5]);
});
test('rencontre écourtée sans compte entier : on garde la feuille (M5 J1, 11 – 2 et non 26 – 12)',()=>{
  assert.deepEqual([...parties(feuille(26,12,13,[3,3,3,2],0))],[11,2]);
});
test('score déjà publié en parties (national) : gardé tel quel, jamais ramené à 0 – 0',()=>{
  assert.deepEqual([...parties(feuille(7,7,14,[2,2,2,1],0))],[7,7]);
  assert.deepEqual([...parties(feuille(8,1,9,[2,2,2,2],0))],[8,1]);
});
test('sans feuille : ancienne règle (total 42 : retirer 14), sinon tel quel',()=>{
  assert.deepEqual([...parties({match_score:25,opp_score:17})],[11,3]);
  assert.deepEqual([...parties({match_score:1,opp_score:8})],[1,8]);
});
test('pas de score publié : rien, même si la feuille existe',()=>{
  assert.equal(parties({played_games:6,players:[{vic:2}],match_score:null,opp_score:null}),null);
  assert.equal(parties({}),null);
});
test('appel historique à deux nombres inchangé',()=>{
  assert.deepEqual([...parties(22,20)],[8,6]);
  assert.deepEqual([...parties(8,1)],[8,1]);
  assert.equal(parties(null,3),null);
});
