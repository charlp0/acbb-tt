/* En-tête commun : onglets publics + onglets du rôle connu par le jeton (capitaine bleu, sportive orange). */
(function(){
  const base=(document.currentScript.getAttribute('data-base')||'.');
  const PUB=[['Accueil','index.html'],['Équipes','equipe.html'],['Joueurs','joueurs.html'],['Critérium','criterium.html']];
  const CAP=[['Mon équipe','capitaine.html'],['Ma poule','capitaine.html?tab=poule']];
  // Onglets sportive groupés par usage : la journée (le quotidien), la saison (référence), l'administration.
  const SPO_GROUPS=[
    ['Journée',[['📅 Compos journée','sportive/journee.html'],['📊 Suivi des dispos','sportive/suivi-dispos.html'],['📝 Debriefs','sportive/debriefs.html']]],
    ['Saison',[['🎯 Scoring & compos','sportive/index.html'],['🏆 Poules 26/27','sportive/poules.html'],['📋 Contraintes','sportive/contraintes.html']]],
    ['Admin',[['🔗 Accès','sportive/acces.html']]]
  ];
  const SPO=SPO_GROUPS.flatMap(g=>g[1]);
  function pill(label,href,cls,on){ return '<a class="pill'+(cls?' '+cls:'')+(on?' on':'')+'" href="'+base+'/'+href+'">'+label+'</a>'; }
  window.renderNav=function(opts){
    opts=Object.assign({},opts||{}); ['name','team'].forEach(k=>{opts[k]=ACBB.esc(opts[k]||'');}); const here=opts.active||''; const role=opts.role||''; const team=opts.team||'';
    const nav=PUB.map(([l,h])=>pill(l,h,'',here===l)).join('');
    let sub='';
    if(role==='capitaine') sub='<nav class="subnav cap">'+CAP.map(([l,h])=>pill(l,h,'cap',here===l)).join('')+'</nav>';
    if(role==='sportive'){
      // Sportive qui est aussi capitaine : ses deux onglets bleus précèdent les onglets sportive.
      const capPart=team?'<span class="grp"><span class="lab">Capitaine '+team+'</span>'+CAP.map(([l,h])=>pill(l,h,'cap',here===l)).join('')+'</span><span class="sep"></span>':'';
      sub='<nav class="subnav spo">'+capPart+SPO_GROUPS.map(([g,items])=>'<span class="grp"><span class="lab">'+g+'</span>'+items.map(([l,h])=>pill(l,h,'spo',here===l)).join('')+'</span>').join('<span class="sep"></span>')+'</nav>';
    }
    const right=role==='capitaine'?'<span class="pill cap">Capitaine'+(team?' · '+team:'')+'</span>':role==='sportive'?'<span class="pill spo">Sportive'+(opts.name?' · '+opts.name:'')+(team?' · capitaine '+team:'')+'</span>':'<span class="lab" style="align-self:center">Saison 2026/27 · Phase 1</span>';
    const el=document.getElementById('hdr'); if(!el) return;
    el.className='hdr';
    el.innerHTML='<div class="hdr1"><a class="brand" href="'+base+'/index.html"><img src="'+base+'/logo.png" alt="ACBB"><span><span class="b1">ACBB TT</span><br><span class="b2">Tennis de table · Boulogne-Billancourt</span></span></a><nav class="nav">'+nav+'</nav><div class="row">'+right+'</div></div>'+sub;
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
