const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const L=require('../shared/lieux.js');
const read=f=>JSON.parse(fs.readFileSync('data/'+f));
test('les quatre journées Bartholdi ne renvoient plus à la piscine',()=>{
 const salles=read('salles2627.json').salles,lieux=read('lieux.json'),poules=read('poules2627.json').poules;
 for(const [t,j] of [['M9',6],['M12',3],['M14',1],['M15',3]]){
  const result=L.resolve({t,j,salles,lieux,poule:poules.find(p=>p.acbb===t)});
  assert.match(result.txt,/Bartholdi/);assert.doesNotMatch(result.txt,/piscine/i);assert(result.needsConfirmation);
 }
});
test('un lieu de rencontre explicite prime sur la salle de club',()=>{
 const o={t:'M3',j:2,poule:{cal:[{j:2,dom:false,opp:1}],teams:[{pos:1,name:'CLUB 1'}]},adverses:{'CLUB 1':{num:'123',adresse:'Ancienne adresse'}}};
 assert.equal(L.resolve({...o,salles:{M3:{cal:[{j:2,venue:'Lieu confirmé'}]}}}).txt,'Lieu confirmé');
 assert.equal(L.resolve(o).source,'club');assert.equal(L.resolve(o).clubId,'123');
 assert.equal(L.resolve({...o,t:'M2'}),null);
});
test('les digicodes ne sortent pas dans une adresse publiée',()=>{
 assert.equal(L.clean('Salle digicode 9999 rue Exemple'),'Salle rue Exemple');
});
