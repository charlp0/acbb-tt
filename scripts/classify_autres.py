# -*- coding: utf-8 -*-
"""
Éclate la catégorie 'Autres compétitions' en vraies catégories via codechamp
(xml_partie_mysql) : V -> Championnat Vétérans, + -> Challenge de clubs.
Les codes restants (#, H : épreuves jeunes non identifiées) restent en 'autre'.
Usage CI (FFTT_ID/FFTT_PWD).
"""
import json, re, glob, os, unicodedata, difflib, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def nrm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z]', '', s)
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''

MOIS = {'Sept':9,'Oct':10,'Nov':11,'Déc':12,'Jan':1,'Fév':2,'Mars':3,'Avr':4,'Mai':5,'Juin':6}
def mensuel_at(prof, date):
    try: m = int(date.split('/')[1])
    except Exception: return None
    tl = prof.get('timeline') or []
    best = None
    for e in tl:
        if MOIS.get(e['m']) == m: best = e['v']
    if best is None and tl: best = tl[-1]['v']
    return best

NEW = {'V': ('veterans', 'Championnat Vétérans'), '+': ('challenge', 'Challenge de clubs')}

def build_comp(key, label, matches, prof):
    c = {'key':key,'label':label,'V':0,'D':0,'pg':0.0,'pl':0.0,'perf':0,'cperf':0,
         'best':None,'worst':None,'matches':matches}
    for m in matches:
        if m['won']: c['V'] += 1
        else: c['D'] += 1
        if m['pts'] > 0: c['pg'] += m['pts']
        else: c['pl'] += m['pts']
        my = mensuel_at(prof, m['date'])
        if my is None or not m.get('opp_cls'): continue
        gap = round(m['opp_cls'] - my)
        rec = {'delta':gap,'opp':m['opp'],'opp_cls':m['opp_cls'],'my':round(my),'date':m['date'],'comp':label}
        if m['won'] and gap > 0: c['perf'] += 1
        if (not m['won']) and gap < 0: c['cperf'] += 1
        if m['won'] and (c['best'] is None or gap > c['best']['delta']): c['best'] = rec
        if (not m['won']) and (c['worst'] is None or (-gap) > c['worst']['delta']): c['worst'] = {**rec,'delta':-gap}
    c['pg']=round(c['pg'],1); c['pl']=round(c['pl'],1); c['solde']=round(c['pg']+c['pl'],1)
    n=c['V']+c['D']; c['winpct']=round(100*c['V']/n) if n else 0
    return c

touched = 0
for f in glob.glob('data/players/*.json'):
    prof = json.load(open(f))
    comps = prof.get('competitions') or []
    autre = next((c for c in comps if c['key'] == 'autre'), None)
    if not autre or not autre['matches']: continue
    lic = str(prof.get('lic'))
    try:
        r = fb.get(f"xml_partie_mysql.php?licence={lic}")
    except Exception as e:
        print(f"!! {lic}: {e}"); continue
    codes = {}
    for b in re.findall(r'<partie>(.*?)</partie>', r, re.S):
        codes.setdefault((tg(b,'date'), nrm(tg(b,'advnompre'))), tg(b,'codechamp'))
    def code_of(m):
        k = (m['date'], nrm(m['opp']))
        if k in codes: return codes[k]
        for (d2, n2), cd in codes.items():
            if d2 == m['date'] and difflib.SequenceMatcher(None, n2, k[1]).ratio() >= 0.85:
                return cd
        return '?'
    buckets = {}
    rest = []
    for m in autre['matches']:
        cd = code_of(m)
        if cd in NEW: buckets.setdefault(cd, []).append(m)
        else: rest.append(m)
    if not buckets: continue
    ncomps = [c for c in comps if c['key'] not in ('autre',) + tuple(k for k,_ in NEW.values())]
    for cd, ms in buckets.items():
        key, label = NEW[cd]
        ncomps.append(build_comp(key, label, ms, prof))
    if rest:
        ncomps.append(build_comp('autre', 'Autres compétitions', rest, prof))
    prof['competitions'] = ncomps
    json.dump(prof, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    touched += 1
    parts = ' · '.join(f"{NEW[cd][0]}:{len(ms)}" for cd, ms in buckets.items())
    print(f"+ {prof.get('prenom','')} {prof.get('nom','')} : {parts}" + (f" · autre:{len(rest)}" if rest else ""))
print(f"OK — {touched} fiches reclassées")
