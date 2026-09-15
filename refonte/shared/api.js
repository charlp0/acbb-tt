/* ACBB TT — client API commun (refonte 2026/27)
   Toutes les données sensibles passent par la fonction serveur : aucune lecture directe de la base depuis le navigateur. */
(function(){
  const API='https://vhhmageufrcenruywawg.supabase.co/functions/v1/api';
  const ANON='sb_publishable_NuRpgtxqVQ87R6K8txw57Q_oBUt4qay'; // clé publique : sert uniquement à joindre la fonction, elle n'ouvre aucune table
  function deviceId(){ try{ let d=localStorage.getItem('acbb_device'); if(!d){ d=crypto.randomUUID(); localStorage.setItem('acbb_device',d);} return d; }catch(e){ return 'nodevice'; } }
  function token(){ try{ const h=location.hash.match(/(?:^#|[#&])t=([A-Za-z0-9_-]{16,})/); if(h){ localStorage.setItem('acbb_token',h[1]); history.replaceState(null,'',location.pathname+location.search); } return localStorage.getItem('acbb_token')||''; }catch(e){ return ''; } }
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
  async function json(path){ const r=await fetch(path,{cache:'no-cache'}); if(!r.ok) throw new Error(path); return r.json(); }
  window.ACBB={api,upload,token,deviceId,toast,esc,json,API};
})();
