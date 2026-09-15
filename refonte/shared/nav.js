/* En-tête commun : onglets publics + onglets du rôle connu par le jeton (capitaine bleu, sportive orange). */
(function(){
  const base=(document.currentScript.getAttribute('data-base')||'.');
  const PUB=[['Accueil','index.html'],['Équipes','equipe.html'],['Joueurs','joueurs.html']];
  const CAP=[['Mon équipe','capitaine.html'],['Ma poule','capitaine.html?tab=poule']];
  const SPO=[['🎯 Scoring & compos','sportive/index.html'],['🏆 Poules 26/27','sportive/poules.html'],['📊 Suivi des dispos','sportive/suivi-dispos.html'],['📋 Contraintes','sportive/contraintes.html'],['📅 Compos journée','sportive/journee.html'],['📝 Debriefs','sportive/debriefs.html'],['🔗 Accès','sportive/acces.html']];
  function pill(label,href,cls,on){ return '<a class="pill'+(cls?' '+cls:'')+(on?' on':'')+'" href="'+base+'/'+href+'">'+label+'</a>'; }
  window.renderNav=function(opts){
    opts=opts||{}; const here=opts.active||''; const role=opts.role||''; const team=opts.team||'';
    let nav=PUB.map(([l,h])=>pill(l,h,'',here===l)).join('');
    if(role==='capitaine') nav+=CAP.map(([l,h])=>pill(l,h,'cap',here===l)).join('');
    if(role==='sportive') nav+=SPO.map(([l,h])=>pill(l,h,'spo',here===l)).join('');
    const right=role==='capitaine'?'<span class="pill cap">Capitaine'+(team?' · '+team:'')+'</span>':role==='sportive'?'<span class="pill spo">Sportive'+(opts.name?' · '+opts.name:'')+'</span>':'<span class="lab" style="align-self:center">Saison 2026/27 · Phase 1</span>';
    const el=document.getElementById('hdr'); if(!el) return;
    el.className='hdr';
    el.innerHTML='<a class="brand" href="'+base+'/index.html"><img src="'+base+'/../logo.png" alt="ACBB"><span><span class="b1">ACBB TT</span><br><span class="b2">Tennis de table · Boulogne-Billancourt</span></span></a><nav class="nav">'+nav+'</nav><div class="row">'+right+'</div>';
  };
})();
