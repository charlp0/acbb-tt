/* Arbitrage explicite des éditions concurrentes. Aucun « dernier arrivé gagne ». */
(function(){
  const clone=o=>JSON.parse(JSON.stringify(o));
  const diff=(base,next)=>Object.fromEntries([...new Set([...Object.keys(base||{}),...Object.keys(next||{})])]
    .filter(k=>k!=='_meta'&&JSON.stringify((base||{})[k])!==JSON.stringify((next||{})[k]))
    .map(k=>[k,(next||{})[k]||null]));
  const documentOf=(kind,row)=>kind==='contraintes'?Object.fromEntries(((row&&row.tags&&row.tags.liste)||[]).map(c=>[c.id,c])):((row&&row.tags)||{});
  function describe(value){
    if(!value)return 'Supprimé';
    if(value.type&&window.ACBB_CONTR)return ACBB_CONTR.titre(value)+(value.note?' · '+value.note:'');
    if(value.k!=null||value.cap!=null)return 'Poids de la tendance : '+value.k+' · plafond : '+value.cap;
    return [value.r==='T'?'Titulaire':value.r==='R'?'Remplaçant':'',value.e,value.d,value.e2?'également '+value.e2:''].filter(Boolean).join(' · ')||'Sans affectation';
  }
  function choose(keys,current,mine,label){
    return new Promise(resolve=>{
      const d=document.createElement('dialog');d.style.cssText='max-width:680px;width:calc(100% - 28px);max-height:85vh;overflow:auto;background:var(--panel);color:var(--ink);border:1px solid var(--orange);border-radius:12px;padding:20px';
      const e=ACBB.esc;
      d.innerHTML='<h2>Modifications simultanées</h2><p>Ces éléments ont changé depuis ton ouverture. Choisis la version à conserver pour chacun.</p>'+keys.map((k,i)=>
        '<section><b>'+e(label?label(k):k)+'</b><p>Version partagée : '+e(describe(current[k]))+'</p><p>Ta modification : '+e(describe(mine[k]))+'</p><select data-choice="'+i+'"><option value="shared">Conserver la version partagée</option><option value="mine">Conserver ma modification</option></select></section>').join('')+
        '<p><button data-cancel>Annuler, garder mon brouillon</button> <button data-apply>Enregistrer mes choix</button></p>';
      const close=v=>{d.close();d.remove();resolve(v);};
      d.querySelector('[data-cancel]').onclick=()=>close(null);
      d.oncancel=ev=>{ev.preventDefault();close(null);};
      d.querySelector('[data-apply]').onclick=()=>{const choices={};keys.forEach((k,i)=>choices[k]=d.querySelector('[data-choice="'+i+'"]').value);close(choices);};
      document.body.appendChild(d);d.showModal();
    });
  }
  async function save(o){
    let changes=clone(o.changes),expected=o.expected||0;
    for(;;){
      try{return await ACBB.api('spo/documents',{kind:o.kind,expected_id:expected,changes,note:o.note||''});}
      catch(error){
        const b=error.body;if(error.status!==409||!b||!b.current)throw error;
        const current=documentOf(o.kind,b.current),choices=await choose(b.conflicts,current,changes,o.label);
        if(!choices)throw new Error('Brouillon conservé, aucun enregistrement');
        Object.keys(choices).forEach(k=>{if(choices[k]==='shared')delete changes[k];});
        if(!Object.keys(changes).length)return {ok:true,row:b.current,unchanged:true};
        expected=b.current.id;
      }
    }
  }
  window.ACBB_EDIT={diff,documentOf,save};
})();
