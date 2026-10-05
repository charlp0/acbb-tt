const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../shared/cherche-joueur.js');
const idx=[{lic:'1',nom:'LE CORRE',pre:'Erwan'},{lic:'2',nom:'MERIC',pre:'Marion'},{lic:'3',nom:'DE ROLLAND',pre:'Marie-Laure'},
  {lic:'4',nom:'CHAUVEL DE COSNAC',pre:'Astrid'},{lic:'5',nom:'CHAUVEL',pre:'Sylvain'},{lic:'6',nom:'MARCADÉ',pre:'Timothée'}].map(C.entree);
const noms=q=>C.chercher(idx,q).map(x=>x.pre+' '+x.nom);
test('prénom, nom, ou les deux dans n’importe quel ordre, sans accents ni majuscules',()=>{
  assert.deepEqual(noms('meric'),['Marion MERIC']);assert.deepEqual(noms('marion meric'),['Marion MERIC']);assert.deepEqual(noms('MERIC mar'),['Marion MERIC']);
  assert.deepEqual(noms('marie laure'),['Marie-Laure DE ROLLAND']);assert.deepEqual(noms('timothee marcade'),['Timothée MARCADÉ']);
});
test('nom composé collé, et les débuts de nom passent en premier',()=>{
  assert.deepEqual(noms('lecorre'),['Erwan LE CORRE']);
  assert.deepEqual(noms('chauvel'),['Sylvain CHAUVEL','Astrid CHAUVEL DE COSNAC']);
  assert.deepEqual(noms('mar'),['Marie-Laure DE ROLLAND','Timothée MARCADÉ','Marion MERIC']);
});
test('rien d’autre : pas de résultat pour une saisie vide ou inconnue',()=>{
  assert.deepEqual(noms(''),[]);assert.deepEqual(noms('zzz'),[]);
  assert.equal(C.trouve('Marion','MERIC',''),true);assert.equal(C.trouve('Marion','MERIC','mer mar'),true);assert.equal(C.trouve('Marion','MERIC','lec'),false);
});
