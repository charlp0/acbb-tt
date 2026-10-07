/* Petites fonctions d'affichage communes aux pages : dates françaises, noms de clubs, horodatages,
   messages d'erreur, boutons occupés. Module pur (ni réseau ni DOM à l'import), testé par tests/ui.test.js.
   Chargé par les pages juste après shared/api.js ; les scripts de page gardent leurs noms d'origine
   par alias (const fmtDate=ACBB_UI.fmtDate;). */
(function(racine){
  // Abréviations des jours, indexées comme Date#getDay() (dimanche = 0).
  const JOURS=['dim.','lun.','mar.','mer.','jeu.','ven.','sam.'];
  // « jj/mm/aaaa » → Date locale à minuit, sinon null (pas de contrôle des bornes : « 31/02/2026 » glisse en mars).
  function parseFR(d){ const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(d||''); return m?new Date(+m[3],+m[2]-1,+m[1]):null; }
  // Date de rencontre « jj/mm/aaaa » → « ven. 26/09 » ; une valeur libre ou vide est rendue telle quelle (« à fixer »).
  function fmtDate(d){ const dt=parseFR(d); if(!dt) return d||'à fixer'; return JOURS[dt.getDay()]+' '+d.slice(0,5); }
  // Particules des noms de clubs, gardées en minuscules…
  const PART={LE:'Le',LA:'La',LES:'Les',DE:'de',DU:'du',DES:'des',ST:'St',STE:'Ste',SUR:'sur',EN:'en',ET:'et'};
  // … et sigles de clubs, gardés en capitales.
  const ACR=new Set(['ASML','ASPN','SCTT','USMT','ESTT','CSTT','ACBB','ASPTT','ASMB','AVTT','TTMC','PPCM','SLTT','ASTT','ESCP','ASGB']);
  // Un mot de nom de club : nombre tel quel, particule, sigle (≤ 3 lettres, sans voyelle ou connu) en capitales, sinon Capitale initiale.
  function capWord(w){ const u=w.toUpperCase(); if(/^\d+$/.test(w)||!w) return w; if(PART[u]) return PART[u]; if(u.length<=3||ACR.has(u)||!/[AEIOUY]/.test(u)) return u; return u[0]+u.slice(1).toLowerCase(); }
  // « BOULOGNE BILLANCOURT 11 » → « Boulogne Billancourt 11 », mot à mot (traits d'union compris).
  function shortName(n){ return String(n||'').trim().split(/\s+/).map(w=>w.split('-').map(capWord).join('-')).join(' '); }
  // Nom d'équipe normalisé pour comparer : capitales sans accents, lettres, chiffres et espaces seulement.
  function normName(s){ return String(s||'').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^A-Z0-9 ]/g,' ').replace(/\s+/g,' ').trim(); }
  // Même équipe sous deux graphies : même numéro final et même premier mot (≥ 4 lettres), ex. « BOULOGNE BILLAN 11 » ≈ « BOULOGNE BILLANCOURT 11 ».
  function sameTeam(a,b){ a=normName(a); b=normName(b); if(!a||!b) return false; if(a===b) return true; const na=a.match(/(\d+)$/),nb=b.match(/(\d+)$/); const fa=a.split(' ')[0],fb=b.split(' ')[0]; return !!(na&&nb&&na[1]===nb[1]&&fa===fb&&fa.length>=4); }
  const p2=n=>(n<10?'0':'')+n;
  // Horodatage ISO → « 26/09/2026 à 20h30 » ; vide s'il est absent, rendu tel quel s'il n'est pas une date.
  function fmtTs(iso){ if(!iso) return ''; const d=new Date(iso); if(isNaN(d)) return String(iso); return p2(d.getDate())+'/'+p2(d.getMonth()+1)+'/'+d.getFullYear()+' à '+p2(d.getHours())+'h'+p2(d.getMinutes()); }
  // Horodatage ISO → « 26/09 à 20h30 » (sans l'année) ; vide s'il n'est pas une date.
  function fmtTsCourt(iso){ const d=new Date(iso); if(isNaN(d)) return ''; return p2(d.getDate())+'/'+p2(d.getMonth()+1)+' à '+p2(d.getHours())+'h'+p2(d.getMinutes()); }
  // Horodatage ISO → « 26/09 20h30 » (locale fr-FR) ; vide s'il est absent ou invalide.
  function fmtDT(iso){ if(!iso) return ''; const d=new Date(iso); if(isNaN(d)) return ''; return d.toLocaleDateString('fr-FR',{day:'2-digit',month:'2-digit'})+' '+d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}).replace(':','h'); }
  // Message lisible pour une erreur de l'entrée joueur (licence + date de naissance) renvoyée par l'API.
  function errText(err){
    const code=(err&&err.body&&err.body.error)||(err&&err.message)||'';
    const b=(err&&err.body)||{};
    if(code==='licence_inconnue') return 'Licence inconnue. Vérifie ton numéro (il figure sur ta licence FFTT) ou demande à ton capitaine.';
    if(code==='date_incorrecte') return 'Date de naissance incorrecte.'+(b.restants!=null?' Il te reste '+b.restants+' essai'+(b.restants>1?'s':'')+'.':'');
    if(code==='trop_essais'){ const s=+b.retry_s||0; const mn=Math.max(1,Math.ceil(s/60)); return 'Trop de tentatives. Réessaie dans '+mn+' minute'+(mn>1?'s':'')+'.'; }
    if(code==='appareil_limite') return 'Cet appareil a déjà servi à saisir pour 6 licences différentes. Utilise ton propre téléphone ou demande à ton capitaine.';
    if(err&&err.status) return 'Erreur serveur ('+err.status+'). Réessaie dans quelques minutes.';
    return 'Serveur indisponible. Vérifie ta connexion et réessaie dans quelques minutes.';
  }
  // Message du bandeau « Accès réservé » des pages sportive : lien invalide ou révoqué, erreur serveur, ou lien capitaine.
  function gateErrTxt(err,role){ return err?((err.body&&/jeton_invalide|jeton_requis|role_incorrect/.test(err.body.error||''))?'lien invalide ou révoqué — demande un nouveau lien à la sportive':'serveur : '+err.message):(role==='capitaine'?'ton lien est un lien capitaine':''); }
  // Bouton occupé : libellé provisoire et désactivé le temps d'une requête, puis libellé d'origine.
  function busy(b,on,txt){ if(!b) return; if(on){ b.dataset.txt=b.textContent; b.textContent=txt||'…'; b.disabled=true; } else { b.textContent=b.dataset.txt||b.textContent; b.disabled=false; } }
  const UI={JOURS,PART,ACR,parseFR,fmtDate,capWord,shortName,normName,sameTeam,fmtTs,fmtTsCourt,fmtDT,errText,gateErrTxt,busy};
  if(typeof module!=='undefined'&&module.exports) module.exports=UI; else racine.ACBB_UI=UI;
})(typeof window!=='undefined'?window:globalThis);
