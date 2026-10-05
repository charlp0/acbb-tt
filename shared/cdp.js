/* Championnat de Paris Île-de-France — calendrier, équipes et règles de composition.
   Règlement CDP du 15/06/2026. Module pur : utilisé par cdp.html et les pages sportive,
   testé par tests/cdp.test.js. Aucune lecture réseau ici. */
(function(racine){
  const ECHEANCE='2026-10-21';                       // réponse attendue avant ce mercredi
  const JOURNEES=[
    {j:1,date:'2026-11-27'},{j:2,date:'2027-01-08'},{j:3,date:'2027-02-05'},{j:4,date:'2027-03-19'},
    {j:5,date:'2027-04-02'},{j:6,date:'2027-05-14'},{j:7,date:'2027-06-04'}
  ];
  // Numérotées dans l'ordre des divisions (art. 12) : le numéro sert au brûlage.
  const EQUIPES=[
    {n:1,nom:'Promo Excellence 1',court:'PE1',groupes:3,tables:5},
    {n:2,nom:'Promo Excellence 2',court:'PE2',groupes:3,tables:5},
    {n:3,nom:'Honneur',court:'HO',groupes:3,tables:5},
    {n:4,nom:'Promo Honneur',court:'PH',groupes:2,tables:3},
    {n:5,nom:'Division 2',court:'D2',groupes:1,tables:2}
  ];
  const PLACES=EQUIPES.reduce((s,e)=>s+3*e.groupes,0);   // 36

  function compoVide(){ const c={}; EQUIPES.forEach(e=>{ c[e.n]=Array.from({length:e.groupes},()=>[null,null,null]); }); return c; }

  /* Participations par licence et par numéro d'équipe, comptées sur les compositions des
     journées ANTÉRIEURES à `avant` : { licence: { "1": 3, "2": 1 } }. */
  function historique(compos,avant){
    const h={};
    Object.keys(compos||{}).forEach(k=>{
      const j=+k; if(!(j<avant)) return;
      const c=(compos[k]&&compos[k].compo)||compos[k]||{};
      Object.keys(c).forEach(eq=>(c[eq]||[]).forEach(g=>(g||[]).forEach(l=>{ if(!l) return; (h[l]=h[l]||{}); h[l][eq]=(h[l][eq]||0)+1; })));
    });
    return h;
  }
  /* Art. 12, lecture validée par Charles le 05/10/2026 : les matchs se CUMULENT sur toutes les équipes de numéro
     inférieur. 1 match en équipe 1 et 2 en équipe 2 = 3 : brûlé pour les équipes 3, 4 et 5, pas pour la 2.
     Le règlement admet tout de même un brûlé par groupe de 3 à partir de l'équipe 2 (contrôlé plus bas). */
  function avant(hj,T){ return Object.keys(hj||{}).reduce((s,t)=>s+(+t<T?(+hj[t]||0):0),0); }
  // brûlé pour l'équipe T : rend le nombre de matchs cumulés dans les équipes de numéro inférieur (3 ou plus), sinon null
  function brulePour(hj,T){ const n=avant(hj,T); return n>=3?n:null; }
  function premierBrule(hj){ for(let T=2;T<=5;T++) if(brulePour(hj,T)) return T; return null; }
  // un match de plus en équipe n : première équipe pour laquelle il deviendrait brûlé (il l'est alors jusqu'à la 5), sinon null
  function bruleApres(hj,n){ for(let T=n+1;T<=5;T++){ const k=avant(hj,T); if(k===2) return T; } return null; }
  // à un match du brûlage : 2 matchs cumulés dans les équipes 1 à 4 (ceux de l'équipe 5 ne comptent jamais)
  function aUnMatch(hj){ return avant(hj,5)===2; }

  /* Contrôle d'une composition. points : { licence: points de la licence } ; hist : historique() ;
     dispo : { licence: true|false } pour la journée (facultatif). Rend les alertes par équipe et
     par groupe, et un total. Une alerte « erreur » fait perdre la rencontre si on l'envoie ainsi. */
  function controler(compo,points,hist,dispo){
    const res={equipes:{},erreurs:0,avertissements:0,places:0};
    const vus={};
    EQUIPES.forEach(e=>(compo[e.n]||[]).forEach((g,gi)=>(g||[]).forEach(l=>{ if(l){ res.places++; (vus[l]=vus[l]||[]).push(e.n+'-'+(gi+1)); } })));
    EQUIPES.forEach(e=>{
      const gs=(compo[e.n]||[]).map(g=>(g||[]).slice(0,3));
      const R={groupes:gs.map(()=>({alertes:[]})),absents:0,note:null};
      const err=(gi,type,txt,extra)=>{ R.groupes[gi].alertes.push(Object.assign({niveau:'erreur',type,txt},extra||{})); res.erreurs++; };
      const avert=(gi,type,txt,extra)=>{ R.groupes[gi].alertes.push(Object.assign({niveau:'avert',type,txt},extra||{})); res.avertissements++; };
      // brûlage (art. 12) : à partir de l'équipe 2, un seul brûlé par groupe de 3
      if(e.n>=2) gs.forEach((g,gi)=>{ const b=g.filter(l=>l&&brulePour(hist[l],e.n)); if(b.length>=2) err(gi,'brulage',b.length+' brûlés dans ce groupe, un seul est admis (art. 12).',{licences:b}); });
      // ordre des groupes (art. 8) : chaque joueur du groupe g+1 a au plus les points de chacun du groupe g
      for(let gi=0;gi<gs.length-1;gi++){
        const haut=gs[gi].filter(Boolean), bas=gs[gi+1].filter(Boolean); if(!haut.length||!bas.length) continue;
        const faible=haut.reduce((m,l)=>(points[l]||0)<(points[m]||0)?l:m), fort=bas.reduce((m,l)=>(points[l]||0)>(points[m]||0)?l:m);
        if((points[fort]||0)>(points[faible]||0)) err(gi+1,'ordre','plus de points qu’un joueur du groupe '+(gi+1)+' : à inverser (art. 8).',{fort,faible});
      }
      // absents (art. 9) : au plus un, dans le groupe le plus faible
      const vides=[]; gs.forEach((g,gi)=>{ for(let k=0;k<3;k++) if(!g[k]) vides.push(gi); });
      R.absents=vides.length;
      const der=gs.length-1;
      if(vides.length===1&&vides[0]===der) R.note='1 absent, autorisé : il est dans le groupe le plus faible (art. 9).';
      else if(vides.length===1) err(vides[0],'absent','Un absent doit se trouver dans le groupe le plus faible, le groupe '+gs.length+' (art. 9).');
      else if(vides.length>=2) err(der,'absents',vides.length+' absents : la rencontre serait perdue par pénalité (art. 9).');
      // un joueur, une seule équipe (art. 12) ; et prévenir si un joueur s'est dit indisponible
      gs.forEach((g,gi)=>g.forEach(l=>{
        if(l&&vus[l]&&vus[l].length>1) err(gi,'double','Un joueur ne figure que dans une seule équipe par journée (art. 12).',{licence:l});
        if(l&&dispo&&dispo[l]===false) avert(gi,'indispo','A indiqué ne pas être disponible ce vendredi.',{licence:l});
      }));
      res.equipes[e.n]=R;
    });
    return res;
  }
  const CDP={ECHEANCE,JOURNEES,EQUIPES,PLACES,compoVide,historique,brulePour,premierBrule,bruleApres,aUnMatch,controler};
  if(typeof module!=='undefined'&&module.exports) module.exports=CDP; else racine.CDP=CDP;
})(typeof window!=='undefined'?window:globalThis);
