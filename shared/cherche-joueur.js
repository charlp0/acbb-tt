/* Recherche d'un licencié du club par prénom et/ou nom (06/10/2026).
   La personne tape quelques lettres et choisit sa ligne : sa licence est remplie, il ne lui reste que sa date de
   naissance, seul élément vérifié par le serveur (avec sa limite d'essais). Liste : data/scoring.json, déjà publique.
   Utilisé par cdp.html (dispos CDP), index.html (dispos du championnat par équipe) et criterium.html (« Trouve-toi »).
   Testé par tests/cherche-joueur.test.js et les parcours de tests/browser.spec.js. */
(function(racine){
  // minuscules, sans accents, ponctuation → espaces : « Marie-Laure DE ROLLAND » → « marie laure de rolland »
  const nrm=x=>String(x==null?'':x).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9]+/g,' ').trim();
  function entree(p){
    const nom=String(p.nom||''), pre=String(p.pre||p.prenom||''), f=nrm(pre+' '+nom);
    return {lic:String(p.lic||''),nom,pre,pts:p.men||p.pts||null,mots:f.split(' '),plein:f,inv:nrm(nom+' '+pre),colle:f.replace(/ /g,'')};
  }
  /* Chaque mot tapé doit commencer un mot du nom ou du prénom (« mar mer », « meric », « jean serge ») ;
     à partir de 3 lettres, il peut aussi se trouver dans le nom collé (« lecorre » → LE CORRE). */
  function correspond(x,q){
    const ws=nrm(q).split(' ').filter(Boolean); if(!ws.length) return false;
    return ws.every(m=>x.mots.some(y=>y.indexOf(m)===0)||(m.length>=3&&x.colle.indexOf(m)>=0));
  }
  const trouve=(pre,nom,q)=>!nrm(q)||correspond(entree({pre,nom}),q);
  function chercher(idx,q,max){
    const w=nrm(q); if(!w||!idx) return [];
    return idx.filter(x=>correspond(x,w))
      .map(x=>({x,r:(x.plein.indexOf(w)===0||x.inv.indexOf(w)===0)?0:1}))
      .sort((a,b)=>a.r-b.r||a.x.nom.localeCompare(b.x.nom,'fr')||a.x.pre.localeCompare(b.x.pre,'fr'))
      .slice(0,max||8).map(y=>y.x);
  }
  /* Liste : players_index.json = TOUS les licenciés du club (597), scoring.json = les compétiteurs suivis, dont on
     garde les points. Un jeune absent du scoring doit pouvoir se trouver (Alexandre Boillot Le Goffic, 06/10/2026). */
  const charges={};
  const lire=u=>fetch(u,{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);
  function fusion(sc,ix){
    const m=new Map();
    ((sc&&sc.players)||[]).forEach(p=>{ if(p.lic&&p.nom) m.set(String(p.lic),p); });
    (Array.isArray(ix)?ix:[]).forEach(p=>{ if(p.lic&&p.nom&&!m.has(String(p.lic))) m.set(String(p.lic),{lic:p.lic,nom:p.nom,pre:p.prenom,pts:p.officiel||p.mensuel||null}); });
    return [...m.values()].map(entree);
  }
  function liste(base){
    base=base||'.';
    if(!charges[base]) charges[base]=Promise.all([lire(base+'/data/scoring.json'),lire(base+'/data/players_index.json')])
      .then(([sc,ix])=>{ const idx=fusion(sc,ix); if(!idx.length) throw new Error('liste vide'); return idx; });
    return charges[base];
  }
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const CROIX='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"></path></svg>';

  /* Monte le choix d'identité dans `box` : recherche (liste déroulante accessible), carte « c'est moi » une fois
     choisi, et repli sur la saisie de la licence. Options : prefix (ids : <p>Q, <p>List, <p>Moi, <p>MoiNom, <p>MoiLic,
     <p>Lic), base (chemin du site), flottant (liste par-dessus la page), compact (carte sur une ligne), lienDans (où
     placer le lien « Je ne me trouve pas »), apres(joueur) (appelé après un choix, pour passer à la date). */
  function identite(box,o){
    o=o||{}; const p=o.prefix||'cj';
    box.innerHTML='<div class="cj-cherche"><label class="cj-l" for="'+p+'Q"><span class="lab">Ton prénom ou ton nom</span></label>'
      +'<div class="cj-champ"><input id="'+p+'Q" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="'+p+'List" placeholder="ex. Marion Meric" autocomplete="off" autocapitalize="words" spellcheck="false">'
      +'<ul id="'+p+'List" class="cj-list'+(o.flottant?' flottant':'')+'" role="listbox" aria-label="Licenciés du club" hidden></ul></div></div>'
      +'<div class="cj-moi'+(o.compact?' compact':'')+'" id="'+p+'Moi" hidden><span class="cj-id"><b id="'+p+'MoiNom"></b><span class="lab" id="'+p+'MoiLic"></span></span>'
      +(o.compact?'<button type="button" class="cj-x" aria-label="Ce n\'est pas moi" title="Ce n\'est pas moi">'+CROIX+'</button>':'<button type="button" class="btn cj-x">Ce n\'est pas moi</button>')+'</div>'
      +'<label class="cj-lic" hidden><span class="lab">N° de licence</span><input id="'+p+'Lic" type="text" inputmode="numeric" placeholder="ex. 9246007" autocomplete="off" maxlength="10"></label>'
      +'<button type="button" class="cj-lnk">Je ne me trouve pas : saisir ma licence</button>';
    const $=s=>box.querySelector(s);
    const q=$('#'+p+'Q'), ul=$('#'+p+'List'), moi=$('.cj-moi'), licBox=$('.cj-lic'), lic=$('#'+p+'Lic'), lien=$('.cj-lnk'), cherche=$('.cj-cherche');
    if(o.lienDans) o.lienDans.appendChild(lien);
    let idx=null, manuel=false, actif=-1, trouves=[], choisi=null;
    const pret=liste(o.base).then(i=>{ idx=i; return i; }).catch(()=>{ idx=null; mode(true); lien.hidden=true; return null; });
    const ouvert=on=>{ ul.hidden=!on; q.setAttribute('aria-expanded',String(on)); if(!on) q.removeAttribute('aria-activedescendant'); };
    function dessiner(){
      const t=q.value.trim(); actif=-1;
      if(nrm(t).length<2){ ouvert(false); return; }
      trouves=chercher(idx,t,8);
      ul.innerHTML=trouves.length?trouves.map((x,i)=>'<li role="option" id="'+p+'Opt'+i+'" data-i="'+i+'" aria-selected="false">'+esc(x.pre+' '+x.nom)+(x.pts?'<span class="pt">'+x.pts+' pts</span>':'')+'</li>').join('')
        :'<li class="none" role="option" aria-disabled="true">Aucun licencié trouvé · <button type="button" class="cj-lnk" data-man="1">saisir ma licence</button></li>';
      ouvert(true);
    }
    function surligner(i){ const os=ul.querySelectorAll('li[data-i]'); if(!os.length) return; actif=(i+os.length)%os.length;
      os.forEach((x,k)=>x.setAttribute('aria-selected',String(k===actif))); q.setAttribute('aria-activedescendant',p+'Opt'+actif); os[actif].scrollIntoView({block:'nearest'}); }
    function choisir(x,suite){
      choisi=x; manuel=false; lic.value=x.lic; ouvert(false);
      $('#'+p+'MoiNom').textContent=x.pre+' '+x.nom; $('#'+p+'MoiLic').textContent='licence '+x.lic;
      cherche.hidden=true; licBox.hidden=true; moi.hidden=false; lien.hidden=true;
      if(suite!==false&&o.apres) o.apres(x);
    }
    function mode(on){ manuel=on; choisi=null; ouvert(false); moi.hidden=true; cherche.hidden=on; licBox.hidden=!on;
      lien.hidden=false; lien.textContent=on?'Chercher mon nom dans la liste':'Je ne me trouve pas : saisir ma licence'; if(on) lic.value=''; }
    function vider(){ q.value=''; mode(false); if(!idx){ mode(true); lien.hidden=true; } }
    q.addEventListener('input',()=>{ if(idx) dessiner(); else pret.then(()=>{ if(idx) dessiner(); }); });
    q.addEventListener('keydown',e=>{
      if(e.key==='ArrowDown'){ e.preventDefault(); if(ul.hidden) dessiner(); surligner(actif+1); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); surligner(actif-1); }
      else if(e.key==='Enter'){ e.preventDefault(); if(!ul.hidden&&trouves.length) choisir(trouves[actif>=0?actif:0]); }
      else if(e.key==='Escape'&&!ul.hidden){ e.preventDefault(); e.stopPropagation(); ouvert(false); }
    });
    q.addEventListener('blur',()=>setTimeout(()=>ouvert(false),150));
    ul.addEventListener('mousedown',e=>{ const x=e.target.closest('li[data-i]'); if(x){ e.preventDefault(); choisir(trouves[+x.dataset.i]); return; }
      if(e.target.closest('[data-man]')){ e.preventDefault(); mode(true); lic.focus(); } });
    moi.querySelector('.cj-x').addEventListener('click',()=>{ vider(); q.focus(); });
    lien.addEventListener('click',()=>{ mode(!manuel); (manuel?lic:q).focus(); });
    lic.addEventListener('input',()=>{ lic.value=lic.value.replace(/\D/g,'').slice(0,10); });
    return {
      licence:()=>lic.value.trim(),
      manuel:()=>manuel,
      choisi:()=>choisi,
      champ:()=>manuel?lic:q,                       // le champ à remplir (recherche ou licence)
      vider,
      // licence connue d'avance (dernière saisie mémorisée, échec à reprendre) : la carte si le joueur est dans la liste
      preselection(l){ l=String(l||''); if(!l) return pret; return pret.then(()=>{ const x=idx&&idx.find(y=>y.lic===l); if(x) choisir(x,false); else { mode(true); lic.value=l; } }); }
    };
  }
  const API={nrm,entree,correspond,trouve,chercher,liste,identite,fusion};
  if(typeof module!=='undefined'&&module.exports) module.exports=API; else racine.ACBB_CHERCHE=API;
})(typeof window!=='undefined'?window:globalThis);
