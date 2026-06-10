/* ACBB TT — Encart "Signaler une erreur" + modale (formulaire Formspree).
   Auto-injecté sur toutes les pages qui incluent <script src="report.js" defer></script>.
   ⚠️ Remplace ENDPOINT par ton URL Formspree (https://formspree.io/f/xxxxxxx). */
(function(){
  "use strict";
  var ENDPOINT = "https://formspree.io/f/xjgdopjr";

  var css = `
  .rep-bar{display:flex;align-items:center;justify-content:center;gap:7px;width:100%;
    padding:8px 14px;font-family:"Space Grotesk",system-ui,sans-serif;font-size:12px;font-weight:500;
    color:#F6F5F3;background:rgba(242,106,27,0.12);border:none;border-bottom:1px solid rgba(255,255,255,0.08);
    cursor:pointer;text-align:center;line-height:1.3}
  .rep-bar:hover{background:rgba(242,106,27,0.20)}
  .rep-bar b{color:#F26A1B;font-weight:700}
  .rep-bar .ico{font-size:13px}
  .rep-ov{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.62);backdrop-filter:blur(4px);
    display:none;align-items:flex-end;justify-content:center}
  .rep-ov.open{display:flex}
  @media(min-width:560px){.rep-ov{align-items:center}}
  .rep-card{width:100%;max-width:480px;max-height:92vh;overflow:auto;background:#141416;color:#F6F5F3;
    border:1px solid rgba(255,255,255,0.16);border-radius:18px 18px 0 0;padding:22px 20px 26px;
    font-family:"Space Grotesk",system-ui,sans-serif;animation:repIn .22s ease}
  @media(min-width:560px){.rep-card{border-radius:18px}}
  @keyframes repIn{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
  .rep-h{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:4px}
  .rep-h h3{font-family:"Saira Condensed",system-ui,sans-serif;font-style:italic;font-weight:800;
    text-transform:uppercase;font-size:22px;letter-spacing:0.4px;margin:0}
  .rep-h h3 em{color:#F26A1B;font-style:italic}
  .rep-x{background:none;border:none;color:#9a9a98;font-size:26px;line-height:1;cursor:pointer;padding:0 2px}
  .rep-x:hover{color:#F6F5F3}
  .rep-sub{color:rgba(246,245,243,0.6);font-size:12.5px;margin-bottom:16px;line-height:1.45}
  .rep-f{display:flex;flex-direction:column;gap:13px}
  .rep-l{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
    color:rgba(246,245,243,0.6);margin-bottom:6px}
  .rep-l .opt{color:rgba(246,245,243,0.34);font-weight:500;text-transform:none;letter-spacing:0}
  .rep-i,.rep-t,.rep-s{width:100%;background:#1E1E22;border:1px solid rgba(255,255,255,0.16);border-radius:11px;
    color:#F6F5F3;font-family:inherit;font-size:14px;padding:11px 13px;outline:none}
  .rep-i:focus,.rep-t:focus,.rep-s:focus{border-color:#F26A1B}
  .rep-t{resize:vertical;min-height:96px}
  .rep-btn{margin-top:4px;width:100%;padding:13px;border:none;border-radius:99px;background:#F26A1B;color:#fff;
    font-family:"Saira Condensed",system-ui,sans-serif;font-style:italic;font-weight:800;text-transform:uppercase;
    letter-spacing:0.6px;font-size:16px;cursor:pointer}
  .rep-btn:hover{filter:brightness(1.08)}
  .rep-btn:disabled{opacity:0.55;cursor:default}
  .rep-ok{text-align:center;padding:18px 6px}
  .rep-ok .big{font-size:42px}
  .rep-ok h3{font-family:"Saira Condensed",system-ui,sans-serif;font-style:italic;font-weight:800;
    text-transform:uppercase;font-size:24px;margin:10px 0 6px}
  .rep-ok p{color:rgba(246,245,243,0.6);font-size:13px}
  .rep-err{color:#FCA5A5;font-size:12.5px;display:none}
  .rep-priv{font-size:10.5px;line-height:1.5;color:rgba(246,245,243,0.40);text-align:center;margin-top:12px}
  .rep-priv b{color:rgba(246,245,243,0.6);font-weight:600}
  .rep-foot{margin-top:34px;padding:22px 18px 32px;border-top:1px solid rgba(255,255,255,0.08);
    font-family:"Space Grotesk",system-ui,sans-serif;font-size:11px;line-height:1.65;
    color:rgba(246,245,243,0.52);text-align:center;max-width:600px;margin-left:auto;margin-right:auto}
  .rep-foot b{color:rgba(246,245,243,0.72);font-weight:600}
  .rep-foot a{color:#F26A1B;text-decoration:none;cursor:pointer}`;

  var TYPES = ["Classement / niveau faux","Résultat ou match faux","Match manquant ou en trop","Faute de nom / orthographe","Autre"];

  function ctx(){
    // pré-remplit la page/joueur concerné
    try{
      var n = document.getElementById('idName');
      if(n && n.textContent.trim()) return n.textContent.replace(/\s+/g,' ').trim()+" — "+location.href;
    }catch(e){}
    return (document.title||'')+" — "+location.href;
  }

  function build(){
    var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);

    var bar=document.createElement('button'); bar.className='rep-bar'; bar.type='button';
    bar.innerHTML='<span class="ico">⚠️</span> Une info erronée ou un bug ? <b>Signale-le →</b>';
    document.body.insertBefore(bar, document.body.firstChild);

    var ov=document.createElement('div'); ov.className='rep-ov'; ov.setAttribute('role','dialog'); ov.setAttribute('aria-modal','true');
    ov.innerHTML =
      '<div class="rep-card">'+
        '<div class="rep-h"><h3>Signaler <em>une erreur</em></h3><button class="rep-x" type="button" aria-label="Fermer">×</button></div>'+
        '<div class="rep-sub">Merci de nous aider à garder le site juste ! Décris ce qui ne va pas, on corrige vite. 🏓</div>'+
        '<form class="rep-f" novalidate>'+
          '<div><label class="rep-l">Page ou joueur concerné</label>'+
            '<input class="rep-i" name="page" type="text"></div>'+
          '<div><label class="rep-l">Type de problème</label>'+
            '<select class="rep-s" name="type">'+TYPES.map(function(t){return '<option>'+t+'</option>';}).join('')+'</select></div>'+
          '<div><label class="rep-l">Décris le problème</label>'+
            '<textarea class="rep-t" name="message" required placeholder="Ce qui est affiché vs ce qui devrait être…"></textarea></div>'+
          '<div><label class="rep-l">Ton email <span class="opt">(optionnel)</span></label>'+
            '<input class="rep-i" name="email" type="email" placeholder="pour qu’on te réponde"></div>'+
          '<div class="rep-err"></div>'+
          '<button class="rep-btn" type="submit">Envoyer le signalement</button>'+
          '<div class="rep-priv">🔒 On ne collecte que ce que tu écris ici. Ces infos servent <b>uniquement à corriger le site</b> — jamais revendues ni partagées. Suppression sur simple demande.</div>'+
        '</form>'+
        '<div class="rep-ok" style="display:none"><div class="big">✅</div><h3>Merci !</h3><p>Ton signalement est bien parti. On corrige ça dès que possible.</p></div>'+
      '</div>';
    document.body.appendChild(ov);

    var foot=document.createElement('footer'); foot.className='rep-foot';
    foot.innerHTML='Site non officiel réalisé par un passionné · Données des compétitions issues de la '+
      '<b>FFTT</b> (sources publiques) · Aucune donnée personnelle revendue ou exploitée commercialement · '+
      'Une question ou une demande de retrait ? <a class="rep-foot-link">Utilise « Signaler »</a>.';
    document.body.appendChild(foot);

    var card=ov.querySelector('.rep-card'), form=ov.querySelector('.rep-f'),
        okBox=ov.querySelector('.rep-ok'), errBox=ov.querySelector('.rep-err'),
        btn=ov.querySelector('.rep-btn'), pageInput=ov.querySelector('[name=page]');

    function open(){ pageInput.value=ctx(); ov.classList.add('open'); document.body.style.overflow='hidden'; }
    function close(){ ov.classList.remove('open'); document.body.style.overflow=''; }
    bar.addEventListener('click', open);
    var fl=foot.querySelector('.rep-foot-link'); if(fl) fl.addEventListener('click', open);
    ov.querySelector('.rep-x').addEventListener('click', close);
    ov.addEventListener('click', function(e){ if(e.target===ov) close(); });
    document.addEventListener('keydown', function(e){ if(e.key==='Escape' && ov.classList.contains('open')) close(); });

    form.addEventListener('submit', function(e){
      e.preventDefault();
      errBox.style.display='none';
      if(!form.message.value.trim()){ errBox.textContent='Merci de décrire le problème.'; errBox.style.display='block'; return; }
      if(ENDPOINT.indexOf('REMPLACER')>=0){ errBox.textContent='Formulaire pas encore configuré (endpoint manquant).'; errBox.style.display='block'; return; }
      btn.disabled=true; btn.textContent='Envoi…';
      var data=new FormData(form);
      data.append('_subject','Signalement ACBB TT');
      fetch(ENDPOINT,{method:'POST',body:data,headers:{'Accept':'application/json'}})
        .then(function(r){ if(!r.ok) throw new Error('http'); return r.json().catch(function(){return {};}); })
        .then(function(){ form.style.display='none'; okBox.style.display='block'; setTimeout(close,2600); })
        .catch(function(){ errBox.textContent='Oups, envoi impossible. Réessaie ou écris à charles@mwm.io.'; errBox.style.display='block'; })
        .finally(function(){ btn.disabled=false; btn.textContent='Envoyer le signalement'; });
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
