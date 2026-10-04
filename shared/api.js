/* ACBB TT — client API commun (refonte 2026/27)
   Toutes les données sensibles passent par la fonction serveur : aucune lecture directe de la base depuis le navigateur. */
(function(){
  const API='https://vhhmageufrcenruywawg.supabase.co/functions/v1/api';
  const ANON='sb_publishable_NuRpgtxqVQ87R6K8txw57Q_oBUt4qay'; // clé publique : sert uniquement à joindre la fonction, elle n'ouvre aucune table
  /* Jeton et identifiant d'appareil sont gardés EN MÉMOIRE pour toute la durée de la page.
     Ils restent recopiés dans localStorage, mais ne dépendent plus de lui : le navigateur intégré
     de WhatsApp (et les modes privés) peuvent vider le stockage pendant qu'un onglet est ouvert,
     et chaque envoi partait alors sans jeton — un capitaine perdait l'enregistrement de son debrief
     après coup, alors que la page s'était bien ouverte (cas German Rodriguez, 21/09/2026). */
  let TOK='', DEV='';
  function deviceId(){
    if(DEV) return DEV;
    try{ DEV=localStorage.getItem('acbb_device')||''; }catch(e){}
    if(!DEV){ try{ DEV=crypto.randomUUID(); }catch(e){ DEV='dev-'+Math.random().toString(36).slice(2)+Date.now().toString(36); } }
    try{ localStorage.setItem('acbb_device',DEV); }catch(e){}
    return DEV;
  }
  function token(){
    try{
      const h=location.hash.match(/(?:^#|[#&])t=([A-Za-z0-9_-]{16,})/);
      if(h){ TOK=h[1]; try{ localStorage.setItem('acbb_token',TOK); }catch(e){}
             try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){} }
    }catch(e){}
    if(!TOK){ try{ TOK=localStorage.getItem('acbb_token')||''; }catch(e){} }
    return TOK;
  }
  async function api(route, body, opts){
    opts=opts||{};
    const h={'Content-Type':'application/json','apikey':ANON,'Authorization':'Bearer '+ANON,'x-acbb-token':token(),'x-acbb-device':deviceId()};
    const r=await fetch(API+'/'+route.replace(/^\//,''),{method:body===undefined?'GET':'POST',headers:h,body:body===undefined?undefined:JSON.stringify(body)});
    let j=null; try{ j=await r.json(); }catch(e){}
    if(!r.ok){ const err=new Error((j&&j.error)||('HTTP '+r.status)); err.status=r.status; err.body=j; throw err; }
    return j;
  }
  async function upload(route, file, fields){ // multipart (photo debrief)
    const fd=new FormData(); fd.append('file',file); Object.keys(fields||{}).forEach(k=>fd.append(k,fields[k]));
    const r=await fetch(API+'/'+route,{method:'POST',headers:{'apikey':ANON,'Authorization':'Bearer '+ANON,'x-acbb-token':token(),'x-acbb-device':deviceId()},body:fd});
    const j=await r.json().catch(()=>null); if(!r.ok) throw new Error((j&&j.error)||('HTTP '+r.status)); return j;
  }
  function toast(msg,ms){ let t=document.querySelector('.toast'); if(!t){ t=document.createElement('div'); t.className='toast'; document.body.appendChild(t);} t.textContent=msg; t.hidden=false; clearTimeout(t._h); t._h=setTimeout(()=>{t.hidden=true},ms||2600); }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  /* Score d'une rencontre : le club raisonne en PARTIES GAGNÉES (14 – 0), la FFTT publie des
     POINTS DE RENCONTRE (28 – 14 = 14 + parties, total 42 en formule 4 joueurs). On convertit donc les
     scores venant des feuilles FFTT ; tout score dont le total n'est pas 42 est laissé tel quel. */
  /* Score d'une rencontre en PARTIES GAGNÉES, l'unité du club (8 – 6).
     La FFTT publie souvent un score en points : 2 la partie gagnée, 1 la partie perdue jouée, 0 au
     forfait. Sur 14 parties jouées, 8 – 6 y devient 22 – 20, d'où la règle « total 42 : retirer 14 ».
     Elle échoue dès qu'une rencontre n'a pas ses 14 parties jouées : la M9 en J2 (9 – 5, dont une
     partie gagnée par forfait) s'affichait 23 – 18, la M5 en J1 26 – 12 au lieu de 12 – 2, et le
     debrief préremplissait ces chiffres. Passer la JOURNÉE de data/site.json plutôt que deux nombres :
     la feuille (victoires individuelles, doubles, parties jouées) permet de retrouver le compte exact.
     Garde-fou : quand le score publié vaut déjà un nombre de parties (championnats nationaux), on le
     garde tel quel, sinon le calcul ramènerait un 7 – 7 à 0 – 0. Deux nombres seuls : ancienne règle. */
  function parties(a,b){
    if(a&&typeof a==='object'){
      const j=a; if(j.match_score==null||j.opp_score==null) return null;
      const A=+j.match_score, B=+j.opp_score; if(!isFinite(A)||!isFinite(B)) return null;
      const g=+j.played_games||0;
      if(g>0&&Array.isArray(j.players)){
        if(A+B<=g+4) return [A,B];                       // déjà en parties
        const wp=j.players.reduce((s,p)=>s+(+(p&&p.vic)||0),0)+(+j.doubles||0), lp=g-wp;
        const W=(A-lp)/2, L=(B-wp)/2, okW=Number.isInteger(W)&&W>=0, okL=Number.isInteger(L)&&L>=0;
        if(okW&&okL) return [W,L];
        // Un forfait inscrit sur la feuille AVEC un score ne fausse qu'un côté : le côté resté
        // entier est exact, l'autre se lit sur la feuille. M5 J1 : Paris XV à trois, simples
        // forfaités notés joués, double forfaité absent — 12 – 2, et non 11 – 2.
        if(okW) return [W,lp];
        if(okL) return [wp,L];
        if(A+B===42&&A>=14&&B>=14) return [A-14,B-14];
        return (wp>=0&&lp>=0)?[wp,lp]:null;
      }
      return parties(A,B);
    }
    if(a==null||b==null) return null;
    a=+a; b=+b; if(!isFinite(a)||!isFinite(b)) return null;
    return (a+b===42&&a>=14&&b>=14)?[a-14,b-14]:[a,b];
  }
  async function json(path){ const r=await fetch(path,{cache:'no-cache'}); if(!r.ok) throw new Error(path); return r.json(); }
  window.ACBB={api,upload,token,deviceId,toast,esc,json,parties,API};
})();
