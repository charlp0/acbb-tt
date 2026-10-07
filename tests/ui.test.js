const test=require('node:test'),assert=require('node:assert/strict');
const UI=require('../shared/ui.js');
test('parseFR / fmtDate : dates jj/mm/aaaa valides et invalides',()=>{
  const d=UI.parseFR('26/09/2026');
  assert.equal(d.getFullYear(),2026);assert.equal(d.getMonth(),8);assert.equal(d.getDate(),26);
  for(const v of ['2026-09-26','1/9/2026','26/09/26','',undefined,null]) assert.equal(UI.parseFR(v),null);
  assert.equal(UI.fmtDate('26/09/2026'),'sam. 26/09');   // un samedi
  assert.equal(UI.fmtDate('02/10/2026'),'ven. 02/10');   // les rencontres ACBB tombent le vendredi
  assert.equal(UI.fmtDate(''),'à fixer');assert.equal(UI.fmtDate(undefined),'à fixer');
  assert.equal(UI.fmtDate('mar. 29/09'),'mar. 29/09');   // déjà mise en forme (Pro B) : rendue telle quelle
});
test('shortName : particules, sigles, nombres et traits d’union',()=>{
  assert.equal(UI.shortName('BOULOGNE BILLANCOURT 11'),'Boulogne Billancourt 11');
  assert.equal(UI.shortName('ASNIERES TT 5'),'Asnieres TT 5');          // TT : ≤ 3 lettres → capitales
  assert.equal(UI.shortName('VGA ST MAUR 3'),'VGA St Maur 3');          // VGA : 3 lettres ; ST : particule
  assert.equal(UI.shortName('ISSY-LES-MOULINEAUX 2'),'Issy-Les-Moulineaux 2');   // LES : particule « Les »
  assert.equal(UI.shortName('SCTT 1'),'SCTT 1');                        // sans voyelle → capitales
  assert.equal(UI.shortName('PPCM 1'),'PPCM 1');                        // sigle connu
  assert.equal(UI.shortName('  LE PERREUX  '),'Le Perreux');
  assert.equal(UI.shortName(''),'');assert.equal(UI.shortName(null),'');
});
test('sameTeam : même club et même numéro malgré une graphie tronquée ou accentuée',()=>{
  assert.equal(UI.sameTeam('BOULOGNE BILLAN 11','BOULOGNE BILLANCOURT 11'),true);
  assert.equal(UI.sameTeam('Boulogne-Billancourt 11','BOULOGNE BILLANCOURT 11'),true);   // normalisation
  assert.equal(UI.sameTeam('ASNIÈRES TT 5','ASNIERES TT 5'),true);                        // accents
  assert.equal(UI.sameTeam('BOULOGNE BILLANCOURT 11','BOULOGNE BILLANCOURT 12'),false);
  assert.equal(UI.sameTeam('ACBB 11','ASNIERES 11'),false);
  assert.equal(UI.sameTeam('VGA 3','VGA SAINT MAUR 3'),false);   // premier mot trop court pour rapprocher
  assert.equal(UI.sameTeam('','BOULOGNE 1'),false);assert.equal(UI.sameTeam(null,null),false);
  assert.equal(UI.normName(' Boulogne-Billancourt  11 '),'BOULOGNE BILLANCOURT 11');
});
test('fmtTs / fmtTsCourt / fmtDT : horodatages ISO',()=>{
  const iso='2026-09-26T18:05:00';   // heure locale, sans fuseau : indépendant de la machine
  assert.equal(UI.fmtTs(iso),'26/09/2026 à 18h05');
  assert.equal(UI.fmtTsCourt(iso),'26/09 à 18h05');
  assert.equal(UI.fmtDT(iso),'26/09 18h05');
  assert.equal(UI.fmtTs(''),'');assert.equal(UI.fmtTs(null),'');assert.equal(UI.fmtTs('n/a'),'n/a');
  assert.equal(UI.fmtTsCourt('n/a'),'');assert.equal(UI.fmtTsCourt(undefined),'');
  assert.equal(UI.fmtDT(undefined),'');assert.equal(UI.fmtDT('n/a'),'');
});
test('errText : codes de l’API d’entrée joueur',()=>{
  assert.match(UI.errText({status:404,body:{error:'licence_inconnue'}}),/^Licence inconnue/);
  assert.equal(UI.errText({status:401,body:{error:'date_incorrecte',restants:2}}),'Date de naissance incorrecte. Il te reste 2 essais.');
  assert.equal(UI.errText({status:401,body:{error:'date_incorrecte',restants:1}}),'Date de naissance incorrecte. Il te reste 1 essai.');
  assert.equal(UI.errText({status:401,body:{error:'date_incorrecte'}}),'Date de naissance incorrecte.');
  assert.equal(UI.errText({status:429,body:{error:'trop_essais',retry_s:200}}),'Trop de tentatives. Réessaie dans 4 minutes.');
  assert.equal(UI.errText({status:429,body:{error:'trop_essais'}}),'Trop de tentatives. Réessaie dans 1 minute.');
  assert.match(UI.errText({status:403,body:{error:'appareil_limite'}}),/6 licences/);
  assert.equal(UI.errText({status:500,body:{}}),'Erreur serveur (500). Réessaie dans quelques minutes.');
  assert.equal(UI.errText(new TypeError('Failed to fetch')),'Serveur indisponible. Vérifie ta connexion et réessaie dans quelques minutes.');
});
test('gateErrTxt : lien invalide, serveur, lien capitaine',()=>{
  assert.equal(UI.gateErrTxt({message:'403',body:{error:'jeton_invalide'}},''),'lien invalide ou révoqué — demande un nouveau lien à la sportive');
  assert.equal(UI.gateErrTxt({message:'403',body:{error:'role_incorrect'}},'capitaine'),'lien invalide ou révoqué — demande un nouveau lien à la sportive');
  assert.equal(UI.gateErrTxt({message:'Failed to fetch'},''),'serveur : Failed to fetch');
  assert.equal(UI.gateErrTxt(null,'capitaine'),'ton lien est un lien capitaine');
  assert.equal(UI.gateErrTxt(null,''),'');
});
test('busy : libellé provisoire et bouton désactivé, puis libellé d’origine',()=>{
  const b={textContent:'Enregistrer',disabled:false,dataset:{}};
  UI.busy(b,true,'envoi…');assert.equal(b.textContent,'envoi…');assert.equal(b.disabled,true);
  UI.busy(b,false);assert.equal(b.textContent,'Enregistrer');assert.equal(b.disabled,false);
  UI.busy(b,true);assert.equal(b.textContent,'…');
  UI.busy(null,true);   // sans bouton : rien ne casse
});
