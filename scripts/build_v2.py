#!/usr/bin/env python3
"""Génère sportive/index-v2.html (scénario compo, lecture seule) depuis sportive/index.html.
Tags du scénario : scripts/v2_tags.json. Ajoute le drag & drop desktop + panneau d'alertes.
Usage : python3 scripts/build_v2.py  (depuis la racine du repo)"""
import json, re, sys

src = open('sportive/index.html').read()
v2tags = json.load(open('scripts/v2_tags.json'))
s = src

def rep(a, b, label, count=1):
    global s
    n = s.count(a)
    if count and n != count:
        sys.exit(f"ABORT {label}: {n} occurrence(s) trouvée(s), {count} attendue(s)")
    s = s.replace(a, b)

# --- titre + nav ---
s = re.sub(r'<title>.*?</title>', '<title>Compo V2 — Scénario</title>', s, count=1)
rep('<a href="index.html" class="active">🎯 Scoring &amp; compos</a>',
    '<a href="index.html">🎯 Scoring &amp; compos</a>', 'nav v1')
rep('<a href="index-v2.html" style="opacity:.55" title="Scénario de composition alternatif (lecture seule)">🧪 V2</a>',
    '<a href="index-v2.html" class="active">🧪 V2 · scénario</a>', 'nav v2')

# --- bandeau scénario ---
rep('<div class="section-h">Équipes 2026/2027 — niveau moyen des titulaires (tags)</div>',
    '<div style="margin:2px 0 16px;padding:11px 15px;border:1px solid var(--orange);border-radius:11px;'
    'background:rgba(242,106,27,.10);display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
    '<span style="font-family:\'Saira Condensed\',sans-serif;font-weight:800;font-style:italic;text-transform:uppercase;'
    'color:var(--orange);font-size:19px;line-height:1">V2 · Scénario</span>'
    '<span style="font-size:12px;color:var(--dim)">Composition de travail — <b>non enregistrée</b>. '
    'Glisse-dépose un joueur d\'une carte à l\'autre pour tester. La V1 reste la compo officielle.</span>'
    '<a href="index.html" style="margin-left:auto;font-size:12px;color:var(--orange);text-decoration:none;font-weight:600">← Revenir à la V1</a></div>'
    '<div class="section-h">Équipes 2026/2027 — niveau moyen des titulaires (tags)</div>', 'banner')

# --- tags figés + overrides réduits ---
force_old = """const FORCE_STATUS={   // rouge forcé manuellement (blessé / indispo)
  'ARGUT|DANIEL':'blessé — indisponible pour le moment',
  'FONTAINE|SEBASTIEN':'indisponible pour le moment',
  'MERIC|MARION':'placée en réserve (rouge manuel)',
  'ADMI|JOHARA':'placée en réserve (rouge manuel)'
};"""
rep(force_old,
    'const V2_TAGS=' + json.dumps(v2tags, ensure_ascii=False) + ';\n'
    "const FORCE_STATUS={ 'ARGUT|DANIEL':'blessé — indisponible pour le moment' };", 'FORCE_STATUS')
rep("const POOL_ADD={ 'MERIC|MARION':'PR', 'ADMI|JOHARA':'D2', 'SUEDE|SAMUEL':'PR', 'LENNON|CLEMENCE':'D1', 'LIZAMBARD|MILO':'D2', 'LEBOURG|VIRGINIE':'PR' };",
    'const POOL_ADD={};', 'POOL_ADD')

# --- neutraliser les écritures ---
rep('function schedParams(){ clearTimeout(_prmT); _prmT=setTimeout(pushParams,2500); }',
    'function schedParams(){/* V2 : pas de partage */}', 'schedParams')
rep("function draftSave(){try{localStorage.setItem('acbb_tags_draft',JSON.stringify({keys:[...DIRTY],tags:Object.fromEntries([...DIRTY].map(k=>[k,TAGS[k]||null]))}));}catch(e){}}",
    'function draftSave(){/* V2 : pas de brouillon */}', 'draftSave')
rep("document.getElementById('saveTags').addEventListener('click',saveTags);",
    "document.getElementById('saveTags').addEventListener('click',function(){alert('Page V2 (scénario) — lecture seule. Les modifs ne sont pas enregistrées.');});", 'saveBind')
rep('e.preventDefault(); if(DIRTY.size) saveTags();', 'e.preventDefault(); /* V2 */', 'ctrlS')

# --- bootstrap figé ---
boot_old = """/* chargement initial : Supabase (dernière version), repli data/tags.json */
(async function(){
  try{
    const g=await fetch(SB_URL+'/rest/v1/tags_log?select=tags&order=id.desc&limit=1',{headers:SB_HD});
    if(!g.ok)throw 0;
    const a=await g.json(); if(a.length&&a[0].tags)TAGS=a[0].tags;
  }catch(e){
    try{const r=await fetch('../data/tags.json',{cache:'no-cache'});const j=await r.json();if(j&&j.tags)TAGS=j.tags;}catch(_){ }
  }
  if(TAGS._params){ applyParams(TAGS._params); delete TAGS._params; }
  draftLoad(); updateSaveBar(); render();
})();"""
rep(boot_old,
    '/* V2 — composition figée (scénario). Aucune lecture/écriture Supabase. */\n'
    '(function(){ TAGS=JSON.parse(JSON.stringify(V2_TAGS)); if(TAGS._params){delete TAGS._params;} updateSaveBar(); render(); })();', 'bootstrap')

# --- attributs drag & drop dans le rendu ---
rep("""    return '<div class="tm-card">'
      +'<div class="tm-top"><span class="tm-name" style="color:hsl('+teamHue(k)+',75%,72%)">'+k+'</span>'""",
    """    return '<div class="tm-card" data-team="'+k+'">'
      +'<div class="tm-top"><span class="tm-name" style="color:hsl('+teamHue(k)+',75%,72%)">'+k+'</span>'""", 'card team')
rep("""    return '<div class="tm-card">'
      +'<div class="tm-top"><span class="tm-name" style="color:rgb('+c+')">Pool '+esc(dv)+'</span>'""",
    """    return '<div class="tm-card" data-pool="'+esc(dv)+'">'
      +'<div class="tm-top"><span class="tm-name" style="color:rgb('+c+')">Pool '+esc(dv)+'</span>'""", 'card pool')
rep("'<div class=\"tm-p\"><span class=\"nmn'",
    "'<div class=\"tm-p\" draggable=\"true\" data-k=\"'+esc(pkey(p))+'\"><span class=\"nmn'",
    'tm-p draggable', count=2)

# --- module drag & drop + panneau d'alertes ---
DND = """
<script>
/* ===== V2 : drag & drop du scénario (desktop) ===== */
(function(){
  var st=document.createElement('style');
  st.textContent='.tm-p[draggable=\\'true\\']{cursor:grab}'
   +'.tm-p.dragging{opacity:.35}'
   +'.tm-card.dropok{outline:2px dashed var(--orange);outline-offset:2px}'
   +'#v2Panel{position:fixed;right:14px;bottom:14px;z-index:9998;width:300px;background:#17171B;'
   +'border:1px solid rgba(255,255,255,.18);border-radius:13px;padding:13px 15px;'
   +'font-family:"Space Grotesk",system-ui,sans-serif;font-size:12px;color:#F6F5F3;box-shadow:0 10px 30px rgba(0,0,0,.5)}'
   +'#v2Panel .ttl{font-weight:700;margin-bottom:6px}'
   +'#v2Panel .btns{margin-top:10px;display:flex;gap:8px}'
   +'#v2Panel button{flex:1;padding:6px 8px;border-radius:8px;border:1px solid rgba(255,255,255,.22);'
   +'background:#232328;color:#F6F5F3;font-family:inherit;font-size:11.5px;cursor:pointer}'
   +'#v2Panel button:hover{border-color:var(--orange);color:var(--orange)}';
  document.head.appendChild(st);

  var panel=document.createElement('div'); panel.id='v2Panel'; panel.style.display='none';
  panel.innerHTML='<div class="ttl">🧪 Scénario — drag &amp; drop</div>'
   +'<div id="v2Last" style="color:var(--dim);min-height:14px"></div>'
   +'<div id="v2Alerts" style="margin-top:7px;display:flex;flex-direction:column;gap:3px;line-height:1.45"></div>'
   +'<div class="btns"><button id="v2Undo" type="button">↶ Annuler</button>'
   +'<button id="v2Reset" type="button">↺ Réinitialiser</button></div>';
  document.body.appendChild(panel);
  // n'afficher le panneau qu'une fois le mot de passe passé
  var gateT=setInterval(function(){
    var g=document.getElementById('gpw');
    if(!g||!g.offsetParent){ panel.style.display='block'; refresh(); clearInterval(gateT); }
  },700);

  var hist=[];
  var CIBLES={M6:6,M7:6,M8:6,M9:6,M10:5,M11:5};
  function effectifs(){
    var out={};
    Object.keys(CIBLES).forEach(function(t){
      var tit=D.filter(function(p){var g=TAGS[pkey(p)];return g&&g.e===t&&g.r==='T';});
      var moy=tit.length?Math.round(tit.reduce(function(a,p){return a+(p.men||0);},0)/tit.length):0;
      out[t]={n:tit.length,moy:moy};
    });
    return out;
  }
  function refresh(msg){
    if(msg!==undefined)document.getElementById('v2Last').textContent=msg;
    var e=effectifs(), li=[];
    Object.keys(CIBLES).forEach(function(t){
      var n=e[t].n, c=CIBLES[t];
      if(n<4) li.push('🔴 '+t+' : '+n+' titulaires — injouable (< 4)');
      else if(n<c) li.push('🟠 '+t+' : '+n+' tit. (cible '+c+')');
      else if(n>c) li.push('🟠 '+t+' : '+n+' tit. (cible '+c+' — surplus)');
    });
    document.getElementById('v2Alerts').innerHTML =
      li.length?li.map(function(x){return '<div>'+x+'</div>';}).join('')
      :'<div style="color:#4ADE80">✓ Effectifs conformes (6·6 PR / 6·6·5·5 D1)</div>';
  }
  function move(k,team,pool){
    var p=D.find(function(x){return pkey(x)===k;}); if(!p)return;
    hist.push(JSON.stringify(TAGS));
    var dest;
    if(team){ TAGS[k]={d:TEAMDIV[team]||'',e:team,r:'T'}; dest=team; }
    else { TAGS[k]={d:pool,r:'R'}; dest='pool '+pool; }
    render();
    var e=effectifs(); var extra=(e[dest]?(' — '+dest+' : '+e[dest].n+' tit., moy '+e[dest].moy):'');
    refresh((p.pre?p.pre[0]+'. ':'')+p.nom+' → '+dest+extra);
  }
  window.__v2move=move; // hook de test

  var dragKey=null;
  document.addEventListener('dragstart',function(ev){
    var el=ev.target.closest?ev.target.closest('.tm-p[data-k]'):null; if(!el)return;
    dragKey=el.dataset.k; el.classList.add('dragging');
    ev.dataTransfer.effectAllowed='move';
    try{ev.dataTransfer.setData('text/plain',dragKey);}catch(e){}
  });
  document.addEventListener('dragend',function(){
    dragKey=null;
    document.querySelectorAll('.tm-p.dragging').forEach(function(x){x.classList.remove('dragging');});
    document.querySelectorAll('.tm-card.dropok').forEach(function(x){x.classList.remove('dropok');});
  });
  document.addEventListener('dragover',function(ev){
    if(!dragKey)return;
    var card=ev.target.closest?ev.target.closest('.tm-card[data-team],.tm-card[data-pool]'):null;
    if(card){ev.preventDefault();ev.dataTransfer.dropEffect='move';card.classList.add('dropok');}
  });
  document.addEventListener('dragleave',function(ev){
    var card=ev.target.closest?ev.target.closest('.tm-card'):null; if(card)card.classList.remove('dropok');
  });
  document.addEventListener('drop',function(ev){
    var card=ev.target.closest?ev.target.closest('.tm-card[data-team],.tm-card[data-pool]'):null;
    if(!card||!dragKey)return;
    ev.preventDefault(); card.classList.remove('dropok');
    var k=dragKey; dragKey=null;
    move(k,card.dataset.team||null,card.dataset.pool||null);
  });
  document.getElementById('v2Undo').addEventListener('click',function(){
    if(!hist.length)return;
    TAGS=JSON.parse(hist.pop()); render(); refresh('annulé ↶');
  });
  document.getElementById('v2Reset').addEventListener('click',function(){
    TAGS=JSON.parse(JSON.stringify(V2_TAGS)); delete TAGS._params; hist=[]; render(); refresh('scénario réinitialisé ↺');
  });
})();
</script>"""

if '</body>' in s:
    s = s.replace('</body>', DND + '\n</body>', 1)
else:
    s += DND

open('sportive/index-v2.html', 'w').write(s)
print('index-v2.html généré —', len(s), 'octets,', len(v2tags), 'tags')
