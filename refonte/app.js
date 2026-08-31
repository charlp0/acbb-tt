/* ACBB TT — Refonte 26/27 : couche de données commune (prototype fonctionnel).
   Sources réelles : data/poules2627.json (poules + calendriers FFTT), data/scoring.json (joueurs 26/27),
   data/categories.json, data/resultats2627.json (scores, rempli après chaque journée),
   Supabase debriefs_log (débriefs référents). Aucune compo à venir n'est exposée ici. */
(function(){
  var SB='https://vhhmageufrcenruywawg.supabase.co';
  var KEY='sb_publishable_NuRpgtxqVQ87R6K8txw57Q_oBUt4qay';
  var HD={'apikey':KEY};
  var ORDER=['M1','M2','M3','M4','M5','M6','M7','M8','M9','M10','M11','M12','M13','M14','M15','M16','M17','F1','F2','F3'];
  function nrm(s){return (s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().replace(/[^A-Z0-9]/g,'');}
  function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
  function teamHue(k){var i=ORDER.indexOf(k);return i<0?24:Math.round(i*137.5)%360;}
  function divShort(d){
    d=d||'';
    if(/Pro B/i.test(d))return'Pro B';
    if(/Nationale 1/i.test(d))return'N1';
    if(/Nationale 2/i.test(d))return'N2';
    if(/Pr(é|e)-?Nationale/i.test(d))return'PN';
    if(/R(é|e)gionale? 1|R1/i.test(d))return'R1';
    if(/R(é|e)gionale? 2|R2/i.test(d))return'R2';
    if(/R(é|e)gionale? 3|R3/i.test(d))return'R3';
    if(/Pr(é|e)-?R(é|e)gional/i.test(d))return'PR';
    if(/D(é|e)partementale? 1|D1/i.test(d))return'D1';
    if(/D(é|e)partementale? 2|D2/i.test(d))return'D2';
    return d.slice(0,4);
  }
  var DIVC={'Pro B':'250,204,21','N1':'242,106,27','N2':'251,146,60','PN':'244,114,182','R1':'61,214,140','R2':'61,214,140','R3':'61,214,140','PR':'96,165,250','D1':'167,139,250','D2':'148,163,184'};
  function divColor(s){return DIVC[s]||'244,114,182';}

  var _p=null;
  function load(){
    if(_p)return _p;
    _p=Promise.all([
      fetch('../data/poules2627.json',{cache:'no-cache'}).then(function(r){return r.json();}),
      fetch('../data/scoring.json',{cache:'no-cache'}).then(function(r){return r.json();}),
      fetch('../data/categories.json',{cache:'no-cache'}).then(function(r){return r.ok?r.json():{};}).catch(function(){return{};}),
      fetch('../data/resultats2627.json',{cache:'no-cache'}).then(function(r){return r.ok?r.json():{resultats:{}};}).catch(function(){return{resultats:{}};}),
      fetch(SB+'/rest/v1/debriefs_log?select=journee,equipe,auteur,texte,created_at&order=id.asc',{headers:HD}).then(function(r){return r.ok?r.json():[];}).catch(function(){return[];})
    ]).then(function(res){
      var poules=res[0], scoring=res[1], cats=res[2], results=(res[3]&&res[3].resultats)||{}, drows=res[4];
      var byTeam={};
      (poules.poules||[]).forEach(function(p){ if(p.acbb) byTeam[p.acbb]=p; });
      var teams=ORDER.filter(function(k){return byTeam[k];});
      var debriefs={};
      drows.forEach(function(d){ debriefs[d.equipe+'|'+d.journee]=d; });   // le plus récent gagne (ordre asc)
      // adversaire d'une équipe pour une journée
      function oppOf(team,j){
        var p=byTeam[team]; if(!p)return null;
        var c=(p.cal||[]).find(function(x){return x.j===j;});
        if(!c)return null;
        var name=c.oppName, s25=null, pos=null;
        if(!name&&c.opp!=null){
          var t=(p.teams||[]).find(function(x){return x.pos===c.opp;});
          if(t){name=t.name;s25=t.s25;pos=t.pos;}
        }
        return {name:name||'?', dom:!!c.dom, date:c.date, exempt:!!c.exempt, s25:s25, division:p.division, poule:p.poule};
      }
      function resOf(team,j){
        var r=results[team]; return (r&&r[String(j)])||null;   // {us,them}
      }
      // date affichable par journée (globale)
      var DATES=(poules.dates||[]).map(function(d){return d.slice(0,5);});
      // journée courante : première sans résultat ; avant saison = 1
      var cur=1;
      for(var j=1;j<=7;j++){ var any=teams.some(function(t){return resOf(t,j);}); if(any)cur=j; else break; }
      return {byTeam:byTeam, teams:teams, scoring:(scoring.players||[]), cats:cats, results:results,
              debriefs:debriefs, oppOf:oppOf, resOf:resOf, DATES:DATES, cur:cur};
    });
    return _p;
  }

  function chrome(active){
    var nav=[['index.html','Accueil'],['equipes.html','Équipes'],['joueur.html','Joueurs'],['saison-2526.html','Saison 25/26']];
    var h='<div style="position: sticky; top: 0; z-index: 999; background: #F26A1B; color: #0B0B0D; font-family: \'JetBrains Mono\', monospace; font-size: 10px; font-weight: 800; text-align: center; padding: 5px 10px">🧪 PROTOTYPE FONCTIONNEL — vraies données (poules, joueurs, débriefs) · scores à partir du 18/09 · <a href="../accueil.html" style="color: #0B0B0D">vrai site</a></div>';
    h+='<div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); max-width: 1440px; margin: 0 auto">';
    h+='<a href="index.html" style="display: flex; align-items: center; gap: 9px; text-decoration: none; color: inherit"><span style="width: 32px; height: 32px; border-radius: 8px; background: #fff; display: inline-flex; align-items: center; justify-content: center; font-family: \'Saira Condensed\', sans-serif; font-style: italic; font-weight: 800; color: #0B0B0D; font-size: 12px">AC</span><span><b style="font-size: 12px; display: block">ACBB TT</b><span style="font-size: 8.5px; color: rgba(246,245,243,0.6); font-family: \'JetBrains Mono\', monospace; text-transform: uppercase">Saison 2026/2027</span></span></a>';
    h+='<div style="display: flex; gap: 3px; flex-wrap: wrap">';
    nav.forEach(function(n){
      var on=n[0]===active;
      h+='<a href="'+n[0]+'" style="padding: 7px 11px; border-radius: 99px; font-size: 11px; font-weight: 600; text-decoration: none; '+(on?'background: #F26A1B; color: #fff':'color: #D4D3CF')+'">'+n[1]+'</a>';
    });
    h+='</div></div>';
    return h;
  }

  window.App={SB:SB,KEY:KEY,HD:HD,ORDER:ORDER,nrm:nrm,esc:esc,teamHue:teamHue,divShort:divShort,divColor:divColor,load:load,chrome:chrome};
})();
