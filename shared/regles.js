/* Les pages partagent les mêmes contrôles. Une absence de données est une
 * alerte « à vérifier », jamais une validation implicite. */
(function(root,factory){
  const part=typeof module==='object'&&module.exports?require('./participations.js'):root.ACBB_PART;
  const api=factory(part);
  if(typeof module==='object'&&module.exports) module.exports=api; else root.ACBB_RULES=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(PART){
  'use strict';
  const MIN={N1:{pts:1800},N2:{pts:1600},N3:{pts:1400},PN:{pts:1100,n:3},R1:{pts:900,n:3},R2:{pts:700,n:3},N1D:{pts:1100},N2D:{pts:900,n:2}};
  function check(o){
    const {model,t,j}=o, players=o.players||{}, pool=o.poules||{}, division=o.division||(pool[t]||{}).division;
    const c=o.lineup||model.lineup(t,j)||{p:[]}, keys=(c.p||[]).map(model.canonical), out=[];
    const add=(code,lvl,msg,ks)=>out.push({code,lvl,msg,keys:ks||[]});
    const label=k=>{const p=players[k];return p?((p.pre||p.prenom||'')+' '+p.nom).trim():k;};
    const uncertain=keys.map(k=>({k,missing:model.missingFor(k,j,t[0])})).filter(x=>x.missing.length);
    if(uncertain.length){
      const missing=[...new Set(uncertain.flatMap(x=>x.missing.map(m=>m.t+' J'+m.j)))];
      add('source','warn','Historique à vérifier pour '+uncertain.map(x=>label(x.k)).join(', ')
        +' — feuilles non confirmées : '+missing.join(', '),uncertain.map(x=>x.k));
    }
    if(c.source==='fftt'&&!c.complete) add('source','warn','Feuille FFTT : des identités restent à rapprocher');
    const size=o.size||4;
    if(keys.length>size) add('effectif','err','Trop de joueurs ('+keys.length+'/'+size+')',keys);
    const cal=model.calendar(t,j);
    if(cal&&cal.exempt&&!keys.length) add('exemption','warn','Feuille d’exemption à renseigner : elle compte pour le brûlage');
    const statuses=keys.map(k=>[k,PART.historyRules(model,k,t,j,pool)]);
    statuses.forEach(([k,r])=>{
      if(r.burned) add('brulage','err',label(k)+' brûlé : deux participations en '+t[0]+r.limit+' ou plus fort', [k]);
      r.samePool.forEach(e=>add('brulage','err',label(k)+' a déjà joué en '+e.t+' (même poule)',[k]));
      const elsewhere=model.assignments(k,j).filter(e=>e.t!==t&&e.t[0]===t[0]);
      if(elsewhere.length) add('doublon','err',label(k)+' également aligné en '+elsewhere.map(e=>e.t).join(', ')+' pour la même journée du championnat',[k]);
    });
    const descended=statuses.filter(x=>x[1].descendedJ2).map(x=>x[0]);
    if(descended.length>1) add('brulage','err','Règle J2 (II.112.1) : '+descended.length+' joueurs descendus d’une équipe supérieure en J1 (max 1)',descended);
    const min=MIN[division];
    if(min&&keys.length){
      const pts=k=>Number((players[k]||{}).officiel||(players[k]||{}).men)||null;
      const unknown=keys.filter(k=>pts(k)==null), low=keys.filter(k=>pts(k)!=null&&pts(k)<min.pts), high=keys.length-unknown.length-low.length;
      if(!min.n){
        low.forEach(k=>add('minimum','err',label(k)+' : '+pts(k)+' pts, minimum '+division+' : '+min.pts+' pts',[k]));
        if(unknown.length) add('minimum','warn','Classement minimum '+division+' : points manquants',unknown);
      } else if(high<min.n){
        add('minimum',high+unknown.length+Math.max(0,size-keys.length)<min.n?'err':'warn',
          'Classement minimum '+division+' : '+high+'/'+min.n+' joueurs à '+min.pts+' pts ou plus'+(unknown.length?' (points manquants)':''),low.concat(unknown));
      }
    }
    if(t[0]==='M'&&['R1','R2','R3'].includes(division)){
      const sex=k=>{const p=players[k]||{};return (o.sexes||{})[String(p.lic||k)]||null;};
      const women=keys.filter(k=>sex(k)==='F'), unknown=keys.filter(k=>!['F','M'].includes(sex(k)));
      if(women.length>2) add('feminines','err','Régionale messieurs : '+women.length+' féminines (max 2)',women);
      else if(unknown.length) add('feminines','warn','Quota de féminines à vérifier : sexe non renseigné',unknown);
    }
    if(!o.extras) add('ex','warn','Statuts extra-communautaires indisponibles : quota à vérifier');
    else {
      const ex=new Set(Object.values(o.extras.ex||{}).map(model.canonical)), q=new Set(Object.values(o.extras.a_confirmer||{}).map(model.canonical));
      const certain=keys.filter(k=>ex.has(k)), maybe=keys.filter(k=>q.has(k));
      if(certain.length>1) add('ex','err','II.609 : '+certain.length+' joueurs extra-communautaires (max 1)',certain);
      else if(certain.length+maybe.length>1) add('ex','warn','Quota extra-communautaire à vérifier : statuts non confirmés',maybe);
    }
    return out;
  }
  return {check,minimums:MIN};
});
