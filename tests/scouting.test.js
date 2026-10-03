const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};
vm.runInNewContext(fs.readFileSync('shared/scouting.js','utf8'),context);
const scout=context.window.ACBB_SCOUT;

test('scouting : feuille sans score global, niveau conservé et aucun score inventé',()=>{
 const row={journee:2,played_games:5,opponent:'ACBB 14',players:[{nom:'EXEMPLE',prenom:'Alex',cls:1100,vic:1}]};
 const team={name:'ADVERSE 4',journees:[row]};
 const site={DATA:{M14:{teams:[team]}},STANDINGS:{}};
 const html=scout.html({site,poule:{acbb:'M14'},team});
 assert.match(html,/score en attente/);
 assert.match(html,/EXEMPLE/);
 assert.match(html,/1100/);
 assert.doesNotMatch(html,/NaN|undefined|score moy\.|0 – 0/);
 assert.equal(scout.niveau(scout.jouees(team)),1100);
 assert.equal(scout.parties(null,null),null);
 // Une liste de noms seule, sans partie jouée, n'est pas un historique réel.
 row.played_games=0;
 assert.equal(scout.jouees(team).length,0);
});
