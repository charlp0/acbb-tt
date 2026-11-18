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
  // Engagement définitif de Cyril et Marion (mail du 09/11/2026), poules de la ligue parues le 17/11/2026 :
  // deux Promo Excellence, une Promotion d'Honneur, l'équipe 4 placée en Division 1 par la ligue (« ancienne D1 »), l'équipe 5 en Division 2.
  // L'équipe « Honneur » prévue en octobre n'existe plus. Même forme côté serveur : CDP_FORME dans supabase/functions/api/index.ts.
  const EQUIPES=[
    {n:1,nom:'Promo Excellence 1',court:'PE1',groupes:3,tables:5},
    {n:2,nom:'Promo Excellence 2',court:'PE2',groupes:3,tables:5},
    {n:3,nom:'Promo Honneur',court:'PH',groupes:2,tables:3},
    {n:4,nom:'Division 1 · équipe 4',court:'D1·4',groupes:1,tables:2},
    {n:5,nom:'Division 2 · équipe 5',court:'D2·5',groupes:1,tables:2}
  ];
  /* Poules et calendrier de chaque équipe ACBB (fftt-idf.com, « Poules Championnat de Paris 2026-2027 », 17/11/2026).
     Art. 3 du règlement : « le premier indiqué dans le calendrier reçoit » → dom = ACBB reçoit (salle de la Piscine).
     Adresses des salles adverses : annuaire des clubs de la ligue 26/27 ; Limay donnée par Cyril le 18/11/2026. Données publiques, sans composition. */
  const POULES={
    1:{division:"Promo Excellence",poule:3,position:3,equipes:["Franconville 1", "Méry US TT 1", "ACBB 1", "Achères CLOC 1", "La Frette 1", "Triel TT 1", "Vaux TTC 1", "Asnières TT 1"],cal:[{j:1,adv:"Triel TT 1",dom:true,adresse:""},{j:2,adv:"La Frette 1",dom:false,adresse:"Salle municipale Albert Marquet, avenue des Lilas, 95530 La Frette-sur-Seine"},{j:3,adv:"Achères CLOC 1",dom:true,adresse:""},{j:4,adv:"Asnières TT 1",dom:true,adresse:""},{j:5,adv:"Méry US TT 1",dom:false,adresse:"Gymnase, rue des Remises (face au collège J.-Y. Cousteau), 95540 Méry-sur-Oise"},{j:6,adv:"Franconville 1",dom:true,adresse:""},{j:7,adv:"Vaux TTC 1",dom:false,adresse:"Gymnase Julien Crespo, parking de la gare, 78740 Vaux-sur-Seine"}]},
    2:{division:"Promo Excellence",poule:4,position:7,equipes:["Élancourt CTT 1", "Montesson TT 1", "Poissy USC 1", "Vélizy CTT 1", "Malakoff USM 1", "Essarts AGSE 1", "ACBB 2", "Saint-Rémy TT 1"],cal:[{j:1,adv:"Montesson TT 1",dom:false,adresse:"Gymnase F. Buisson, rue Henri Dunant, 78360 Montesson"},{j:2,adv:"Élancourt CTT 1",dom:true,adresse:""},{j:3,adv:"Saint-Rémy TT 1",dom:false,adresse:"Complexe sportif des Trois Rivières, salle P. Vaillagou, rue des Écoles, 78470 Saint-Rémy-lès-Chevreuse"},{j:4,adv:"Essarts AGSE 1",dom:false,adresse:"Complexe culturel et sportif, 1 place Jean Ferrat, 78690 Les Essarts-le-Roi"},{j:5,adv:"Malakoff USM 1",dom:true,adresse:""},{j:6,adv:"Vélizy CTT 1",dom:false,adresse:"Espace Jean-Lucien Vazeille (2e sous-sol), 21 rue du Général Exelmans, 78140 Vélizy-Villacoublay"},{j:7,adv:"Poissy USC 1",dom:true,adresse:""}]},
    3:{division:"Promotion d'Honneur",poule:7,position:3,equipes:["Pecq US 1", "Gargenville CO 1", "ACBB 3", "Mauloise US 2", "Marly-le-Roi US 2", "Beynes TTC 1", "Vaux TTC 2", "Montigny AS 1"],cal:[{j:1,adv:"Beynes TTC 1",dom:true,adresse:""},{j:2,adv:"Marly-le-Roi US 2",dom:false,adresse:"Gymnase des Maigrets, chemin des Moines, 78160 Marly-le-Roi"},{j:3,adv:"Mauloise US 2",dom:true,adresse:""},{j:4,adv:"Montigny AS 1",dom:true,adresse:""},{j:5,adv:"Gargenville CO 1",dom:false,adresse:"Sous-sol de la place des Fêtes, rue Pasteur / place du 8 Mai 1945, 78440 Gargenville"},{j:6,adv:"Pecq US 1",dom:true,adresse:""},{j:7,adv:"Vaux TTC 2",dom:false,adresse:"Gymnase Julien Crespo, parking de la gare, 78740 Vaux-sur-Seine"}]},
    4:{division:"Division 1",poule:8,position:7,equipes:["Mesnil-Saint-Denis AS 2", "Plaisirois CP 2", "Conflans US 3", "Mauloise US 3", "SQY Ping 3", "Andrésy-Maurecourt 3", "ACBB 4", "Vélizy CTT 2"],cal:[{j:1,adv:"Plaisirois CP 2",dom:false,adresse:"Gymnase M.-T. Eyquem, 71 rue René Bazin, 78370 Plaisir"},{j:2,adv:"Mesnil-Saint-Denis AS 2",dom:true,adresse:""},{j:3,adv:"Vélizy CTT 2",dom:false,adresse:"Espace Jean-Lucien Vazeille (2e sous-sol), 21 rue du Général Exelmans, 78140 Vélizy-Villacoublay"},{j:4,adv:"Andrésy-Maurecourt 3",dom:false,adresse:"Cosec Jean Moulin, rue des Ormeteaux, 78570 Andrésy"},{j:5,adv:"SQY Ping 3",dom:true,adresse:""},{j:6,adv:"Mauloise US 3",dom:false,adresse:"Gymnase Charpentier, chemin du Radet, 78580 Maule"},{j:7,adv:"Conflans US 3",dom:true,adresse:""}]},
    5:{division:"Division 2",poule:8,position:7,equipes:["Bois-d'Arcy AS 3", "Essarts AGSE 3", "Mantaise AS 1", "Limay ALJ 2", "Marly-le-Roi US 4", "Voltigeurs 3", "ACBB 5", "Rueil Athletic 5"],cal:[{j:1,adv:"Essarts AGSE 3",dom:false,adresse:"Complexe culturel et sportif, 1 place Jean Ferrat, 78690 Les Essarts-le-Roi"},{j:2,adv:"Bois-d'Arcy AS 3",dom:true,adresse:""},{j:3,adv:"Rueil Athletic 5",dom:false,adresse:"Complexe omnisports Alain Mimoun, 41 rue Voltaire, 92500 Rueil-Malmaison"},{j:4,adv:"Voltigeurs 3",dom:false,adresse:"Voltigeurs de Billancourt, 11 rue de Clamart, 92100 Boulogne-Billancourt"},{j:5,adv:"Marly-le-Roi US 4",dom:true,adresse:""},{j:6,adv:"Limay ALJ 2",dom:false,adresse:"Gymnase des Fosses Rouges, allée du Château d’eau, 78520 Limay (fermeture à minuit)"},{j:7,adv:"Mantaise AS 1",dom:true,adresse:""}]}
  };
  const PLACES=EQUIPES.reduce((s,e)=>s+3*e.groupes,0);   // 30
  // « brûlé pour … » : les équipes de numéro T et au-delà, par leur nom court
  function pourEquipes(T){ const l=EQUIPES.filter(e=>e.n>=T).map(e=>e.court); return l.length===1?'la '+l[0]:l.length===2?l.join(' et '):'les équipes '+T+' à '+EQUIPES[EQUIPES.length-1].n+' ('+l.join(', ')+')'; }

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
  const CDP={ECHEANCE,JOURNEES,EQUIPES,POULES,PLACES,pourEquipes,compoVide,historique,brulePour,premierBrule,bruleApres,aUnMatch,controler};
  if(typeof module!=='undefined'&&module.exports) module.exports=CDP; else racine.CDP=CDP;
})(typeof window!=='undefined'?window:globalThis);
