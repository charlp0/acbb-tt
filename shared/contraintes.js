/* ACBB TT — contraintes internes de composition (module partagé).
   La liste est éditable par la sportive dans sportive/contraintes.html et enregistrée dans scenarios_log,
   slot « contraintes » (journal : la dernière ligne fait foi, l'auteur est signé par le serveur).
   Elle est vérifiée dans Compos journée (par journée : domicile/extérieur, adversaire) et dans Scoring & compos
   (titulaires tagués, sans journée). Sans ligne enregistrée : DEFAUTS = les 4 règles validées le 27/08/2026.
   Les règlements FFTT (brûlage, N1, II.609…) ne sont pas ici : ils restent codés dans les pages. */
(function(){
  var SLOT='contraintes';
  var TYPES={
    ensemble:  {lab:'Toujours ensemble',       col:'blue',   help:'Les joueurs listés doivent être alignés dans la même équipe (avertissement si un seul est aligné).'},
    separes:   {lab:'Jamais ensemble',         col:'red',    help:'Aucun joueur du groupe A ne doit être aligné avec un joueur du groupe B.'},
    domicile:  {lab:'Domicile de préférence',  col:'gold',   help:'Avertissement quand le joueur est aligné sur une rencontre à l’extérieur.'},
    adversaire:{lab:'Veut jouer contre…',      col:'orange', help:'Le joueur doit être aligné dans l’équipe choisie la journée où elle rencontre cet adversaire.'},
    rappel:    {lab:'Rappel libre',            col:'grey',   help:'Affiché dans la liste, sans vérification automatique.'}
  };
  var ANT={k:'9257190',nom:'ALLEGRE-GUILLAUME',pre:'Antoine'}, BAP={k:'9257191',nom:'ALLEGRE-GUILLAUME',pre:'Baptiste'};
  var DEFAUTS=[
    {id:'allegre', type:'ensemble', joueurs:[ANT,BAP], note:'Organisation des parents, demande de Laura.', par:'Charles', le:'2026-08-27'},
    {id:'intins',  type:'ensemble', joueurs:[{k:'5412783',nom:'INTINS',pre:'David'},{k:'9248896',nom:'INTINS',pre:'Arthur'}], note:'Même équipe.', par:'Charles', le:'2026-08-27'},
    {id:'mandel',  type:'separes',  joueurs:[{k:'9215542',nom:'MANDELMILECH',pre:'Adrien'}], joueurs2:[ANT,BAP], note:'Adrien ne doit pas être aligné avec Baptiste ou Antoine.', par:'Charles', le:'2026-08-27'},
    {id:'emiliano',type:'domicile', joueurs:[{k:'9261122',nom:'BAR VANEGAS',pre:'Emiliano'}], note:'De préférence les journées à domicile seulement.', par:'Charles', le:'2026-08-27'}
  ];
  var clone=function(o){ return JSON.parse(JSON.stringify(o)); };
  var nrmK=function(s){ return String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().replace(/[^A-Z0-9]/g,''); };
  var fk=function(o){ return nrmK(o.nom)+'|'+nrmK(o.pre); };
  var court=function(o){ return ((o.pre||'').charAt(0)?(o.pre||'').charAt(0)+'. ':'')+(o.nom||''); };
  var long_=function(o){ return ((o.pre||'')+' '+(o.nom||'')).trim(); };
  var lst=function(a,f,sep){ return (a||[]).map(f).join(sep||', '); };
  /* un joueur de contrainte (k = licence ou « NOM|Prénom », sinon nom+prénom) correspond-il à la clé k d'une compo ? */
  function isP(cp,k,BYKEY){
    if(cp.k!=null&&String(cp.k)===String(k)) return true;
    var p=BYKEY&&BYKEY[k]; if(p&&fk(p)===fk(cp)) return true;
    return !cp.k&&String(k).indexOf('|')>0&&nrmK(String(k).split('|')[0])+'|'+nrmK(String(k).split('|')[1])===fk(cp);
  }
  var present=function(list,P,BYKEY){ return (list||[]).filter(function(cp){ return P.some(function(k){ return isP(cp,k,BYKEY); }); }); };
  var absent=function(list,P,BYKEY){ return (list||[]).filter(function(cp){ return !P.some(function(k){ return isP(cp,k,BYKEY); }); }); };
  var keysOf=function(list,P,BYKEY){ return P.filter(function(k){ return (list||[]).some(function(cp){ return isP(cp,k,BYKEY); }); }); };
  var joueursDe=function(c){ return (c.joueurs||[]).concat(c.joueurs2||[]); };

  /* calendrier : adversaire d'une équipe ACBB à une journée / journée où elle rencontre un adversaire donné (poules2627.json) */
  function advOf(POULES,t,j){
    var P=POULES&&POULES[t]; if(!P) return null;
    var cl=(P.cal||[]).filter(function(c){ return c.j===j; })[0]; if(!cl||cl.exempt) return null;
    var o=(P.teams||[]).filter(function(x){ return x.pos===cl.opp; })[0]; return o?o.name:null;
  }
  function journeeAdv(POULES,t,adv){
    var P=POULES&&POULES[t]; if(!P) return null;
    var o=(P.teams||[]).filter(function(x){ return nrmK(x.name)===nrmK(adv); })[0]; if(!o) return null;
    var cl=(P.cal||[]).filter(function(c){ return c.opp===o.pos&&!c.exempt; })[0]; if(!cl) return null;
    return {j:cl.j,date:cl.date,dom:!!cl.dom,adv:o.name};
  }

  /* libellés */
  function titre(c){
    var A=c.joueurs||[], B=c.joueurs2||[];
    switch(c.type){
      case 'ensemble':   return lst(A,long_,' et ')+' dans la même équipe';
      case 'separes':    return lst(A,long_)+' jamais avec '+lst(B,long_,' ou ');
      case 'domicile':   return 'Éviter '+lst(A,long_,' et ')+' en déplacement';
      case 'adversaire': return lst(A,long_,' et ')+' veut jouer contre '+(c.adversaire||'?')+' avec '+(c.equipe||'?');
      default:           return c.titre||c.note||'Rappel';
    }
  }
  function courtLab(c){ // pour la légende du vérificateur
    var A=c.joueurs||[], B=c.joueurs2||[];
    switch(c.type){
      case 'ensemble':   return lst(A,court,' + ')+' ensemble';
      case 'separes':    return lst(A,court)+' ≠ '+lst(B,court,' / ');
      case 'domicile':   return lst(A,court)+' à domicile';
      case 'adversaire': return lst(A,court)+' vs '+(c.adversaire||'?')+' ('+(c.equipe||'?')+')';
      default:           return (c.titre||c.note||'Rappel').slice(0,60);
    }
  }
  function valider(c,POULES){
    var T=TYPES[c.type]; if(!T) return 'type inconnu';
    var nA=(c.joueurs||[]).length, nB=(c.joueurs2||[]).length;
    if(c.type==='ensemble'&&nA<2) return 'il faut au moins deux joueurs';
    if(c.type==='separes'&&(!nA||!nB)) return 'il faut au moins un joueur dans chaque groupe';
    if(c.type==='domicile'&&!nA) return 'il faut au moins un joueur';
    if(c.type==='adversaire'){ if(!nA) return 'il faut au moins un joueur'; if(!c.equipe) return 'choisis l’équipe'; if(!c.adversaire) return 'choisis l’adversaire'; if(POULES&&!journeeAdv(POULES,c.equipe,c.adversaire)) return 'cet adversaire n’est pas dans la poule de '+c.equipe; }
    if(c.type==='rappel'&&!(c.note||c.titre)) return 'écris le rappel';
    return null;
  }

  /* vérification : ctx = {t, j (null = hors journée : Scoring), P (clés de la compo), dom (true/false/null), adv (nom adverse|null), BYKEY, POULES, ou(cp) → où est le joueur absent (texte|null)}
     → [{cid, lvl:'warn'|'info', msg, keys}] */
  function check(liste,ctx){
    var out=[], P=(ctx.P||[]).map(String), BYKEY=ctx.BYKEY||{};
    (liste||[]).forEach(function(c){
      var add=function(lvl,msg,keys){ out.push({cid:c.id,lvl:lvl,msg:msg,keys:keys||[]}); };
      var A=c.joueurs||[], B=c.joueurs2||[];
      var ou=function(cp){ var w=ctx.ou?ctx.ou(cp):null; return court(cp)+(w?' ('+w+')':''); };
      if(c.type==='ensemble'){
        var pr=present(A,P,BYKEY), ab=absent(A,P,BYKEY);
        if(pr.length&&ab.length) add('warn',lst(A,court,' et ')+' doivent jouer ensemble — '+(ab.length>1?'manquent':'manque')+' : '+lst(ab,ou),keysOf(pr,P,BYKEY));
      } else if(c.type==='separes'){
        var pa=present(A,P,BYKEY), pb=present(B,P,BYKEY);
        if(pa.length&&pb.length) add('warn',lst(pa,court)+' ne doit jamais jouer avec '+lst(pb,court),keysOf(pa.concat(pb),P,BYKEY));
      } else if(c.type==='domicile'){
        var pd=present(A,P,BYKEY);
        if(pd.length){ if(ctx.dom===false) add('warn',lst(pd,court)+' à l’extérieur — à éviter (préférer le domicile)',keysOf(pd,P,BYKEY)); else if(ctx.j==null) add('info',lst(pd,court)+' : de préférence à domicile — à vérifier journée par journée (Compos journée)'); }
      } else if(c.type==='adversaire'){
        if(ctx.t!==c.equipe) return;
        var r=ctx.POULES?journeeAdv(ctx.POULES,c.equipe,c.adversaire):null;
        var ab2=absent(A,P,BYKEY); if(!ab2.length) return;
        if(ctx.j!=null){ if(ctx.adv&&nrmK(ctx.adv)===nrmK(c.adversaire)) add('warn',lst(ab2,court)+' souhaite jouer contre '+c.adversaire+' — pas aligné en '+c.equipe+' ce jour ('+lst(ab2,ou)+')'); }
        else add('info',lst(ab2,court)+' souhaite jouer contre '+c.adversaire+(r?' (J'+r.j+', '+r.date+(r.dom?', domicile':', extérieur')+')':'')+' : à prévoir dans la compo '+c.equipe);
      }
    });
    return out;
  }

  /* lecture / écriture (via le proxy sportive : select/insert scenarios_log) */
  var QUERY='select=id,tags,author,created_at&slot=eq.'+SLOT+'&order=id.desc&limit=1';
  function fromRows(rows){
    var r=(Array.isArray(rows)?rows:((rows&&rows.rows)||[]))[0];
    if(r&&r.tags&&Array.isArray(r.tags.liste)) return {liste:r.tags.liste,meta:{id:r.id,author:r.author,at:r.created_at,by:(r.tags._meta||{}).by||''},defaut:false};
    return {liste:clone(DEFAUTS),meta:null,defaut:true};
  }
  function payload(liste,by){ return {slot:SLOT,author:'Contraintes',tags:{liste:liste,_meta:{saved:new Date().toISOString(),by:by||'',n:liste.length}}}; }
  function newId(){ return 'c'+Date.now().toString(36)+Math.random().toString(36).slice(2,6); }

  window.ACBB_CONTR={SLOT:SLOT,TYPES:TYPES,QUERY:QUERY,defauts:function(){ return clone(DEFAUTS); },nrmK:nrmK,fk:fk,court:court,long:long_,isP:isP,joueursDe:joueursDe,advOf:advOf,journeeAdv:journeeAdv,titre:titre,courtLab:courtLab,valider:valider,check:check,fromRows:fromRows,payload:payload,newId:newId};
})();
