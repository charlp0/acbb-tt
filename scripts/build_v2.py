#!/usr/bin/env python3
"""Génère sportive/index-v2.html (page scénario) depuis sportive/index.html.
Le drag & drop et le panneau viennent du module commun de index.html (mode V2
auto-détecté via V2_TAGS). La V2 charge le dernier scénario depuis scenarios_log
(repli : tags figés scripts/v2_tags.json) et enregistre dans scenarios_log — jamais tags_log.
Usage : python3 scripts/build_v2.py  (depuis la racine du repo)"""
import json, re, sys

src = open('sportive/index.html').read()
v2tags = json.load(open('scripts/v2_tags.json'))
s = src

def rep(a, b, label, count=1):
    global s
    n = s.count(a)
    if count and n != count:
        sys.exit(f"ABORT {label}: {n} occurrence(s), {count} attendue(s)")
    s = s.replace(a, b)

# --- titre + nav ---
s = re.sub(r'<title>.*?</title>', '<title>Compo V2 — Scénario</title>', s, count=1)
rep('<a href="index.html" class="active">🎯 Scoring &amp; compos</a>',
    '<a href="index.html">🎯 Scoring &amp; compos</a>', 'nav v1')
rep('<a href="index-v2.html" style="opacity:.55" title="Scénario de composition A">🧪 V2</a>',
    '<a href="index-v2.html" class="active">🧪 V2 · scénario</a>', 'nav v2')

# --- bandeau scénario ---
rep('<div class="section-h">Équipes 2026/2027 — niveau moyen des titulaires (tags)</div>',
    '<div style="margin:2px 0 16px;padding:11px 15px;border:1px solid var(--orange);border-radius:11px;'
    'background:rgba(242,106,27,.10);display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
    '<span style="font-family:\'Saira Condensed\',sans-serif;font-weight:800;font-style:italic;text-transform:uppercase;'
    'color:var(--orange);font-size:19px;line-height:1">V2 · Scénario</span>'
    '<span style="font-size:12px;color:var(--dim)">Bac à sable partagé : glisse-dépose les joueurs, puis '
    '<b>💾 Enregistrer le scénario</b> pour le partager. La V1 reste la compo officielle (jamais modifiée ici).</span>'
    '<a href="index.html" style="margin-left:auto;font-size:12px;color:var(--orange);text-decoration:none;font-weight:600">← Revenir à la V1</a></div>'
    '<div class="section-h">Équipes 2026/2027 — niveau moyen des titulaires (tags)</div>', 'banner')

# --- tags figés (repli) + overrides réduits ---
force_old = """const FORCE_STATUS={   // rouge forcé manuellement (blessé / indispo)
  'ARGUT|DANIEL':'blessé — indisponible pour le moment',
  'FONTAINE|SEBASTIEN':'indisponible pour le moment',
  'MERIC|MARION':'placée en réserve (rouge manuel)',
  'ADMI|JOHARA':'placée en réserve (rouge manuel)'
};"""
rep(force_old,
    'const V2_TAGS=' + json.dumps(v2tags, ensure_ascii=False) + ';\n'
    "const FORCE_STATUS={ 'ARGUT|DANIEL':'blessé — indisponible pour le moment' };", 'FORCE_STATUS')
rep("const POOL_ADD={};   // pools désormais portés par les vrais tags (bascule scénario V2 -> officiel, 27/08)",
    'const POOL_ADD={};', 'POOL_ADD')

# --- neutraliser les écritures V1 (tags_log / brouillon / partage réglages) ---
rep('function schedParams(){ clearTimeout(_prmT); _prmT=setTimeout(pushParams,2500); }',
    'function schedParams(){/* V2 : pas de partage des réglages */}', 'schedParams')
rep("function draftSave(){try{localStorage.setItem('acbb_tags_draft',JSON.stringify({keys:[...DIRTY],tags:Object.fromEntries([...DIRTY].map(k=>[k,TAGS[k]||null]))}));}catch(e){}}",
    'function draftSave(){/* V2 : pas de brouillon */}', 'draftSave')
rep("document.getElementById('saveTags').addEventListener('click',saveTags);",
    "document.getElementById('saveTags').addEventListener('click',function(){ if(window.__v2save)window.__v2save(); });", 'saveBind')
rep('e.preventDefault(); if(DIRTY.size) saveTags();',
    'e.preventDefault(); if(window.__v2save)window.__v2save();', 'ctrlS')

# --- bootstrap : dernier scénario partagé, repli tags figés ---
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
boot_new = """/* V2 — scénario (slot v2) : dernier scénario partagé, replis successifs */
(async function(){
  var base=V2_TAGS;
  async function gets(u){try{const g=await fetch(u,{headers:SB_HD});if(g.ok){const a=await g.json();if(a.length&&a[0].tags)return a[0].tags;}}catch(e){}return null;}
  var t=await gets(SB_URL+'/rest/v1/scenarios_log?select=tags&slot=eq.v2&order=id.desc&limit=1')
      ||await gets(SB_URL+'/rest/v1/scenarios_log?select=tags&order=id.desc&limit=1');
  if(t)base=t;
  TAGS=JSON.parse(JSON.stringify(base)); delete TAGS._params;
  window.__V2BASELINE=JSON.stringify(TAGS); window.__V2SLOT='v2';
  updateSaveBar(); render();
  if(window.__v2refresh)window.__v2refresh();
})();"""
rep(boot_old, boot_new, 'bootstrap')

rep('<a href="suivi-dispos.html">📊 Suivi des dispos</a>',
    '<a href="suivi-dispos-v2.html">📊 Suivi des dispos (V2)</a>', 'nav suivi->v2')

open('sportive/index-v2.html', 'w').write(s)
print('index-v2.html généré —', len(s), 'octets,', len(v2tags), 'tags de repli')


# ================= suivi-dispos-v2.html =================
s2 = open('sportive/suivi-dispos.html').read()

def rep2(a, b, label, count=1):
    global s2
    n = s2.count(a)
    if count and n != count:
        sys.exit(f"ABORT suivi {label}: {n} occurrence(s), {count} attendue(s)")
    s2 = s2.replace(a, b)

rep2('<title>ACBB TT — Suivi des dispos (interne)</title>',
     '<title>ACBB TT — Suivi dispos · Scénario V2</title>', 'titre')
rep2("""<a href="index.html">🎯 Scoring &amp; compos</a>""",
     """<a href="index-v2.html">🧪 V2 · scénario</a>""", 'nav scoring')
rep2("""<a href="suivi-dispos.html" class="active">📊 Suivi des dispos</a>
  <a href="suivi-dispos-v2.html" style="opacity:.55" title="Suivi basé sur le scénario V2">🧪 V2</a>""",
     """<a href="suivi-dispos.html">📊 Suivi officiel</a>
  <a href="suivi-dispos-v2.html" class="active">📊 Suivi · scénario V2</a>""", 'nav suivi')
rep2("fetch(SB+'/rest/v1/tags_log?select=tags&order=id.desc&limit=1',{headers:HD}).then(function(r){return r.ok?r.json():[];})",
     "fetch(SB+'/rest/v1/scenarios_log?select=tags&slot=eq.v2&order=id.desc&limit=1',{headers:HD})"
     ".then(function(r){return r.ok?r.json():fetch(SB+'/rest/v1/scenarios_log?select=tags&order=id.desc&limit=1',{headers:HD})"
     ".then(function(r2){return r2.ok?r2.json():[];});})", 'source tags')
rep2('<div class="meta" id="hMeta">chargement…</div>',
     '<div style="margin:8px 0 4px;padding:9px 13px;border:1px solid var(--orange);border-radius:10px;'
     'background:rgba(242,106,27,.10);font-size:12px;color:var(--dim)">'
     '<b style="color:var(--orange)">🧪 Basé sur le scénario V2</b> — matrice et relances calculées sur la '
     'compo scénario (dernier enregistrement), pas la compo officielle.</div>'
     '<div class="meta" id="hMeta">chargement…</div>', 'bandeau')

open('sportive/suivi-dispos-v2.html', 'w').write(s2)
print('suivi-dispos-v2.html généré —', len(s2), 'octets')
