/* En-tête commun : les trois compétitions du club en tuiles, puis la barre du rôle connu par le jeton
   (capitaine bleu, sportive orange). */
(function(){
  const base=(document.currentScript.getAttribute('data-base')||'.');
  /* Une tuile par compétition, l'ouverte en orange : les petites pastilles d'avant se rataient (refonte du 04/10/2026).
     Les pages passent encore leurs anciens libellés d'onglet (« Accueil », « Équipes », « Critérium ») : ALIAS les
     rattache à la bonne tuile. « Joueurs » est archivé : sa page reste joignable par ses liens, hors de la barre. */
  const COMPETS=[
    {id:'cpe',  nom:['Championnat','par équipe'], href:'index.html',     sous:'Saison 2026/27 · Phase 1'},
    {id:'crit', nom:['Critérium','fédéral'],      href:'criterium.html', sous:'Compétition individuelle · 4 tours'},
    {id:'paris',nom:['Championnat','de Paris'],   soon:true,             sous:'Saison 2026/27'}
  ];
  const ALIAS={'Accueil':'cpe','Équipes':'cpe','Championnat par équipe':'cpe','Critérium':'crit','Critérium fédéral':'crit'};
  const CAP=[['Mon équipe','capitaine.html'],['Ma poule','capitaine.html?tab=poule']];
  // Onglets sportive groupés par usage : la journée (le quotidien), la saison (référence), l'administration.
  const SPO_GROUPS=[
    ['Journée',[['Compos journée','sportive/journee.html'],['Suivi des dispos','sportive/suivi-dispos.html'],['Debriefs','sportive/debriefs.html']]],
    ['Saison',[['Scoring & compos','sportive/index.html'],['Poules 26/27','sportive/poules.html'],['Contraintes','sportive/contraintes.html']]],
    ['Admin',[['Accès','sportive/acces.html']]]
  ];
  const SPO=SPO_GROUPS.flatMap(g=>g[1]);
  // Les pages sportive passent encore leur onglet avec un emoji (« 📅 Compos journée ») : on compare sans.
  const sansSigne=s=>String(s||'').replace(/^[^\p{L}\p{N}]+/u,'').trim();
  // Tout outil capitaine ou sportive relève du championnat par équipe : sa tuile reste allumée.
  const ROLE=CAP.map(x=>x[0]).concat(SPO_GROUPS.flatMap(g=>g[1].map(x=>x[0])));
  function pill(label,href,cls,on){ return '<a class="pill'+(cls?' '+cls:'')+(on?' on':'')+'" href="'+base+'/'+href+'"'+(on?' aria-current="page"':'')+'>'+ACBB.esc(label)+'</a>'; }
  function tuile(c,on){
    const nom='<span class="tname">'+c.nom[0]+' <span>'+c.nom[1]+'</span></span>';
    if(c.soon) return '<span class="tile soon"><span class="trow"><span class="tlab">'+c.sous+'</span><span class="tsoon">Coming soon</span></span>'+nom+'</span>';
    return '<a class="tile'+(on?' on':'')+'" href="'+base+'/'+c.href+'"'+(on?' aria-current="page"':'')+'><span class="tlab">'+c.sous+'</span>'+nom+'</a>';
  }
  window.renderNav=function(opts){
    opts=Object.assign({},opts||{}); ['name','team'].forEach(k=>{opts[k]=ACBB.esc(opts[k]||'');}); const here=sansSigne(opts.active||''); const role=opts.role||''; const team=opts.team||'';
    const ici=ALIAS[here]||(ROLE.includes(here)?'cpe':'');
    const tiles='<nav class="tiles" aria-label="Compétitions">'+COMPETS.map(c=>tuile(c,ici===c.id)).join('')+'</nav>';
    let sub='';
    if(role==='capitaine') sub='<nav class="subnav cap" aria-label="Espace capitaine">'+CAP.map(([l,h])=>pill(l,h,'cap',here===l)).join('')+'</nav>';
    if(role==='sportive'){
      // Sportive qui est aussi capitaine : ses deux onglets bleus précèdent les onglets sportive.
      const capPart=team?'<span class="grp"><span class="lab">Capitaine '+team+'</span>'+CAP.map(([l,h])=>pill(l,h,'cap',here===l)).join('')+'</span><span class="sep"></span>':'';
      sub='<nav class="subnav spo" aria-label="Espace sportive">'+capPart+SPO_GROUPS.map(([g,items])=>'<span class="grp"><span class="lab">'+g+'</span>'+items.map(([l,h])=>pill(l,h,'spo',here===l)).join('')+'</span>').join('<span class="sep"></span>')+'</nav>';
    }
    const right=role==='capitaine'?'<span class="pill cap">Capitaine'+(team?' · '+team:'')+'</span>':role==='sportive'?'<span class="pill spo">Sportive'+(opts.name?' · '+opts.name:'')+(team?' · capitaine '+team:'')+'</span>':'<span class="lab" style="align-self:center">Saison 2026/27 · Phase 1</span>';
    const el=document.getElementById('hdr'); if(!el) return;
    el.className='hdr';
    el.innerHTML='<div class="hdr1"><a class="brand" href="'+base+'/index.html"><img src="'+base+'/logo.png" alt="ACBB"><span><span class="b1">ACBB TT</span><br><span class="b2">Tennis de table · Boulogne-Billancourt</span></span></a><div class="row">'+right+'</div></div>'+tiles+sub;
    if(role==='sportive'){
      fetch(base+'/data/freshness.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>{
        const stale=Object.entries(data.sources||{}).filter(([,s])=>!s.collected_at||Date.now()-Date.parse(s.collected_at)>18*3600000||!Number.isFinite(Date.parse(s.collected_at)));
        const missing=((data.coverage||{}).pending_sheets||[]).length;
        if(stale.length||missing){const note=document.createElement('div');note.className='tag warn';note.style.margin='8px';
          note.textContent=(stale.length?'Mise à jour à vérifier : '+stale.map(([n])=>n).join(', '):'')+(stale.length&&missing?' · ':'')+(missing?missing+' feuille(s) FFTT encore attendue(s)':'');el.appendChild(note);}
      }).catch(()=>{const note=document.createElement('div');note.className='tag warn';note.textContent='Date de mise à jour non vérifiable';el.appendChild(note);});
    }
  };
})();
