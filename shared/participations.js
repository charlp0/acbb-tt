/* Source commune : une feuille réelle ne réécrit jamais le plan enregistré.
 * Une feuille manquante reste inconnue ; un plan n'est pas une participation.
 * Utilisable dans le navigateur, les tests Node et la fonction serveur. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.ACBB_PART=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  // M1 (Pro B) est gérée hors du site : aucune feuille n'est attendue dans
  // cet outil, et ses plans éventuels ne font pas partie de ses contrôles.
  const team=t=>/^[MF]\d+$/.test(t||'')&&t!=='M1';
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[^A-Z0-9]/g,'');
  const key=p=>String(p.key||p.lic||p.licence||((p.nom||'')+'|'+(p.pre||p.prenom||'')));
  const name=p=>norm(p.nom)+'|'+norm(p.pre||p.prenom);
  function identities(players){
    const aliases=new Map(), names=new Map();
    function add(map,a,k){ if(a) map.set(a,map.has(a)&&map.get(a)!==k?null:k); }
    (players||[]).forEach(p=>{
      const k=key(p), n=name(p);
      [k,p.lic,p.licence,p.key,n,'SN-'+n.replace('|','-')].forEach(a=>add(aliases,String(a||''),k));
      add(names,n,k);
    });
    function resolve(p){
      const id=p.licence||p.lic||p.key;
      if(id&&aliases.get(String(id))) return aliases.get(String(id));
      const exact=names.get(name(p)); if(exact) return exact;
      // Prénom d'usage abrégé (Milo / Milosav), uniquement si le nom ET le préfixe
      // de prénom donnent un seul candidat. Jamais un rapprochement au nom seul.
      const a=norm(p.nom), b=norm(p.pre||p.prenom);
      if(b.length<3) return null;
      const matches=(players||[]).filter(x=>{
        const c=norm(x.pre||x.prenom);
        return norm(x.nom)===a&&c.length>=3&&(c.startsWith(b)||b.startsWith(c));
      });
      return matches.length===1?key(matches[0]):null;
    }
    function canonical(k){
      k=String(k); if(aliases.get(k)) return aliases.get(k);
      if(k.includes('|')) return names.get(k.split('|').map(norm).join('|'))||k;
      return k;
    }
    return {resolve,canonical};
  }
  function dateISO(s){
    const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(s||'');
    return m?m[3]+'-'+m[2]+'-'+m[1]:(/^\d{4}-\d{2}-\d{2}/.test(s||'')?s.slice(0,10):null);
  }
  function create(options){
    const o=options||{}, ids=identities(o.players||[]), plans=o.plans||{}, confirmed=o.confirmedPlans||plans;
    const calendars=Array.isArray(o.poules)?Object.fromEntries(o.poules.map(p=>[p.acbb,p])):(o.poules||{});
    const poules=Object.fromEntries(Object.entries(calendars).filter(([t])=>team(t)));
    const context={saison:o.saison||'2026/2027',phase:o.phase||1};
    const sheets={}, events=[], unknown=[];
    const today=o.today||new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Paris'});
    // Confirmations privées explicites de non-participation. Ni une indisponibilité,
    // ni l'absence d'un joueur dans une composition prévue ne constitue cette preuve.
    const nonParticipations=(o.nonParticipations||[]).filter(n=>n.confirmed===true&&n.saison===context.saison&&n.phase===context.phase
      &&['M','F'].includes(n.championnat)&&Number.isInteger(n.j)&&n.j>=1
      &&Object.entries(poules).some(([t,p])=>t[0]===n.championnat&&(p.cal||[]).some(c=>+c.j===n.j&&dateISO(c.date)&&dateISO(c.date)<today)))
      .map(n=>({...n,k:ids.canonical(n.k)}));
    Object.entries((o.site&&o.site.DATA)||{}).forEach(([t,pool])=>{
      if(!team(t)) return;
      const own=(pool.teams||[]).find(x=>x.acbb); if(!own) return;
      (own.journees||[]).forEach(row=>{
        if((row.match_score==null&&!(row.played_games>0))||!Array.isArray(row.players)||!row.players.length) return;
        const j=+row.journee; if(!Number.isInteger(j)||j<1) return;
        const raw=row.players.filter(p=>p.nom&&norm(p.nom)!=='JOUEURABSENT');
        const resolved=raw.map(ids.resolve), p=[...new Set(resolved.filter(Boolean))];
        const s={t,j,p,source:'fftt',complete:resolved.every(Boolean),row};
        sheets[t+':'+j]=s;
        resolved.forEach((k,i)=>{if(!k) unknown.push({t,j,reason:'identite',name:name(raw[i])});});
        p.forEach(k=>events.push({...context,championnat:t[0],k,t,j,source:'fftt',reel:true,played:true}));
      });
    });
    function calendar(t,j){return ((poules[t]||{}).cal||[]).find(c=>+c.j===+j)||null;}
    function plan(t,j){const c=(plans[j]||{})[t];return c?{...c,p:[...new Set((c.p||[]).map(ids.canonical))]}:null;}
    Object.keys(poules).filter(team).forEach(t=>{
      (poules[t].cal||[]).forEach(c=>{
        const original=(confirmed[c.j]||{})[t];
        const p=original?{...original,p:(original.p||[]).map(ids.canonical)}:null, d=dateISO(c.date);
        if(c.exempt&&d&&d<today&&p&&p.p.length&&['valid','sent'].includes(p.st)&&!sheets[t+':'+c.j]){
          const s={t,j:+c.j,p:p.p,source:'exemption',complete:true,played:false};
          sheets[t+':'+c.j]=s;
          s.p.forEach(k=>events.push({...context,championnat:t[0],k,t,j:+c.j,source:'exemption',reel:false,played:false}));
        }
      });
    });
    function lineup(t,j,includePlan=true){
      if(!team(t)) return null;
      const s=sheets[t+':'+j]; if(s) return s;
      const p=includePlan?plan(t,j):null;
      return p?{...p,t,j:+j,source:'plan',complete:false}:null;
    }
    function history(k,before,genre){
      k=ids.canonical(k);
      return events.filter(e=>e.k===k&&e.j<before&&(!genre||e.t[0]===genre)).sort((a,b)=>a.j-b.j||a.t.localeCompare(b.t));
    }
    function missing(before,genre){
      const out=[];
      Object.keys(poules).filter(t=>team(t)&&(!genre||t[0]===genre)).forEach(t=>{
        (poules[t].cal||[]).forEach(c=>{
          if(+c.j>=before) return;
          const s=sheets[t+':'+c.j];
          if(!s||!s.complete) out.push({t,j:+c.j,reason:s?'identite':c.exempt?'declaration_exemption':'feuille'});
        });
      });
      return out;
    }
    function missingFor(k,before,genre){
      k=ids.canonical(k);
      const confirmed=history(k,before,genre);
      // Une participation confirmée (exemption comprise) établit l'équipe du
      // joueur pour cette journée et ce championnat. Le manque d'une autre
      // feuille ne rend pas à nouveau cet historique individuel inconnu.
      return missing(before,genre).filter(m=>!confirmed.some(e=>e.j===m.j&&e.championnat===m.t[0])
        &&!nonParticipations.some(n=>n.k===k&&n.j===m.j&&n.championnat===m.t[0]));
    }
    function assignments(k,j,includePlan=true){
      k=ids.canonical(k);
      const actual=events.filter(e=>e.k===k&&e.j===+j);
      const out=actual.slice();
      // Dès qu'il existe une participation confirmée dans un championnat, les
      // vieux plans de ce joueur dans ce même championnat ne font plus foi.
      if(includePlan) Object.keys(plans[j]||{}).filter(team).forEach(t=>{
        if(sheets[t+':'+j]||actual.some(e=>e.t[0]===t[0])) return;
        const p=plan(t,j); if(p&&p.p.includes(k)) out.push({...context,championnat:t[0],k,t,j:+j,source:'plan',played:false});
      });
      return out;
    }
    function rounds(t){
      return ((poules[t]||{}).cal||[]).filter(c=>sheets[t+':'+c.j]||(dateISO(c.date)&&dateISO(c.date)<today)).map(c=>+c.j).sort((a,b)=>a-b);
    }
    function parcours(k,t){
      const js=rounds(t), jours=js.map(j=>{
        const es=history(k,j+1,t[0]).filter(e=>e.j===j), all=es.map(e=>e.t);
        const own=es.find(e=>e.t===t)||es[0];
        return {j,t:own?own.t:null,tous:all,played:es.some(e=>e.played),exempt:!!own&&!own.played,unknown:missingFor(k,j+1,t[0]).some(m=>m.j===j)};
      });
      return {joue:jours.filter(x=>x.played).length,avec:jours.filter(x=>x.played&&x.t===t).length,total:js.length,
        inconnus:jours.filter(x=>x.unknown).length,exemptions:jours.filter(x=>x.exempt).length,
        ailleurs:jours.filter(x=>x.t&&x.t!==t).map(x=>({j:x.j,t:x.t})),jours};
    }
    return {context,events,sheets,unknown,canonical:ids.canonical,resolve:ids.resolve,calendar,lineup,history,missing,missingFor,assignments,rounds,parcours};
  }
  function historyRules(model,k,t,j,poules){
    const h=model.history(k,j,t[0]), perRound=new Map();
    h.forEach(e=>perRound.set(e.j,Math.min(perRound.get(e.j)||Infinity,+e.t.slice(1))));
    const ns=[...perRound.values()].sort((a,b)=>a-b), n=+t.slice(1);
    const pool=(poules||{})[t];
    return {burned:ns.length>=2&&n>ns[1],limit:ns[1]||null,
      descendedJ2:+j===2&&h.some(e=>+e.t.slice(1)<n),
      samePool:h.filter(e=>{
        const other=(poules||{})[e.t];
        return e.t!==t&&pool&&other&&pool.poule!=null&&pool.division===other.division&&pool.poule===other.poule;
      }),incomplete:model.missingFor(k,j,t[0]).length>0};
  }
  return {create,identities,historyRules,norm,dateISO,key};
});
