/* ============================================================================
   Mesure d'audience — GoatCounter (sans cookie, sans identifiant personnel)

   Le compteur vivait sur chaque page de l'ancien site. La bascule du 16/09/2026
   a remplacé ces pages sans reprendre le mouchard : seules 4 pages comptaient
   encore. Ce module le remet partout, en une ligne par page, pour qu'une page
   ajoutée plus tard n'ait plus qu'à l'inclure.

   Vie privée. Le chemin envoyé est construit ICI, explicitement : chemin +
   chaîne de requête, JAMAIS le fragment. C'est essentiel — le jeton d'accès des
   capitaines et de la sportive voyage dans le fragment (#t=...). GoatCounter ne
   l'enverrait pas non plus par défaut, mais on ne veut pas que cette garantie
   dépende du comportement d'un script tiers.

   Usage :
     <script src="shared/track.js?v=1" defer></script>
   Pour compter plus tard (page dont le titre n'est connu qu'après chargement
   des données, comme la fiche joueur) :
     <script>window.ACBB_TRACK_MANUAL=true;</script>
     <script src="shared/track.js?v=1"></script>
     ... puis, une fois le titre posé :  ACBB_TRACK.compter();
   ========================================================================== */
(function(){
  var ENDPOINT='https://acbb-tt.goatcounter.com/count';

  /* Chemin compté : on repart de l'URL, on retire le drapeau de débogage local
     (dev=1) qui ne dit rien de l'audience, et on laisse tomber le fragment. */
  function chemin(){
    try{
      var u=new URL(location.href);
      u.searchParams.delete('dev');
      var q=u.searchParams.toString();
      return u.pathname+(q?'?'+q:'');
    }catch(e){ return location.pathname; }
  }

  /* count.js est chargé en asynchrone : on réessaie un court moment, puis on
     abandonne sans bruit (bloqueur de pub, réseau coupé — jamais d'erreur visible). */
  function compter(n){
    n=n||0;
    if(window.goatcounter&&window.goatcounter.count){
      try{ window.goatcounter.count({path:chemin(),title:document.title}); }catch(e){}
      return;
    }
    if(n<50) setTimeout(function(){ compter(n+1); },200);
  }

  window.goatcounter=window.goatcounter||{};
  window.goatcounter.no_onload=true;          // c'est nous qui déclenchons, avec notre chemin
  window.ACBB_TRACK={compter:compter,chemin:chemin};

  var s=document.createElement('script');
  s.async=true; s.src='//gc.zgo.at/count.js';
  s.setAttribute('data-goatcounter',ENDPOINT);
  (document.head||document.documentElement).appendChild(s);

  if(!window.ACBB_TRACK_MANUAL){
    if(document.readyState==='complete') compter();
    else window.addEventListener('load',function(){ compter(); });
  }
})();
