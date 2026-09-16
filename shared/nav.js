/* En-tête commun : onglets publics + onglets du rôle connu par le jeton (capitaine bleu, sportive orange). */
(function(){
  const base=(document.currentScript.getAttribute('data-base')||'.');
  const PUB=[['Accueil','index.html'],['Équipes','equipe.html'],['Joueurs','joueurs.html']];
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
    opts=opts||{}; const here=opts.active||''; const role=opts.role||''; const team=opts.team||'';
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
    el.innerHTML='<div class="hdr1"><a class="brand" href="'+base+'/index.html"><img src="'+base+'/../logo.png" alt="ACBB"><span><span class="b1">ACBB TT</span><br><span class="b2">Tennis de table · Boulogne-Billancourt</span></span></a><nav class="nav">'+nav+'</nav><div class="row">'+right+'</div></div>'+sub;
  };
})();
