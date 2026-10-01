(function(root,factory){
  const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ACBB_LIEUX=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const clean=s=>String(s||'').replace(/\s*digicode[^0-9]*\d+\s*/ig,' ').replace(/\s+/g,' ').trim();
  const inScope=t=>/^M(?:[3-9]|1[0-7])$/.test(t)||t==='F2'||t==='F3';
  function resolve(o){
    const cal=((o.poule||{}).cal||[]).find(c=>+c.j===+o.j);
    if(!cal||cal.exempt)return null;
    const saved=(((o.salles||{})[o.t]||{}).cal||[]).find(c=>+c.j===+o.j)||{};
    const place=saved.lieu_id&&((o.lieux||{}).lieux||{})[saved.lieu_id];
    if(saved.lieu_id&&!place)return {label:saved.salle||'',txt:'',source:'inconnue',needsConfirmation:true};
    if(place)return {label:saved.salle||place.nom,txt:clean([place.nom,place.adresse,place.cp,place.ville].filter(Boolean).join(', ')),
      source:'planning',needsConfirmation:!!place.a_confirmer,note:place.note||''};
    if(saved.venue)return {label:saved.salle||'',txt:clean(saved.venue),source:'planning',needsConfirmation:false};
    if(cal.dom)return {label:saved.salle||'',txt:'',source:'inconnue',needsConfirmation:true};
    if(!inScope(o.t))return null;
    const opponent=typeof cal.opp==='number'?(o.poule.teams||[]).find(t=>+t.pos===+cal.opp):null;
    const names=[opponent&&opponent.name,opponent&&opponent.fftt,cal.oppName].filter(Boolean);
    const candidates=names.map(n=>(o.adverses||{})[n]).filter(Boolean);
    const nums=[...new Set(candidates.map(a=>a.num))];
    if(nums.length!==1)return null; // aliases contradictoires : ne pas choisir une adresse
    const a=candidates[0];
    return {label:a.salle||'',txt:clean([a.salle,a.adresse,a.cp,a.ville].filter(Boolean).join(', ')),source:'club',clubId:a.num,
      needsConfirmation:true,note:'Salle déclarée du club à la FFTT — sauf avis contraire'};
  }
  return {resolve,inScope,clean};
});
