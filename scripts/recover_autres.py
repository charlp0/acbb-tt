# -*- coding: utf-8 -*-
"""
Récupère les parties 25/26 absentes des fiches (vétérans, challenge de clubs…)
via xml_partie_mysql — le seul endpoint qui sert encore la saison passée
(découverte sonde 17/07/2026 ; xml_partie est coupé depuis la bascule).

Pour chaque joueur de players_index : diff (date + adversaire) entre les
parties mysql et celles déjà présentes dans les compétitions de la fiche ;
les manquantes vont dans une catégorie 'autre' (« Autres compétitions »),
stats et saison recalculées. Usage CI (FFTT_ID/FFTT_PWD).
"""
import json, re, glob, os, unicodedata, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def nrm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z]', '', s)

def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S)
    return m.group(1).strip() if m else ''

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

idx = json.load(open('data/players_index.json'))
touched = 0; added_tot = 0
for pi in idx:
    lic = str(pi['lic'])
    path = f'data/players/{lic}.json'
    if not os.path.exists(path): continue
    prof = json.load(open(path))
    comps = prof.get('competitions') or []
    have = {}
    for c in comps:
        for m in c['matches']:
            k = (m['date'], nrm(m['opp']))
            have[k] = have.get(k, 0) + 1
    try:
        r = fb.get(f"xml_partie_mysql.php?licence={lic}")
    except Exception as e:
        print(f"!! {lic} : {e}"); continue
    import difflib
    missing = []
    for b in re.findall(r'<partie>(.*?)</partie>', r, re.S):
        date = tg(b,'date'); adv = tg(b,'advnompre')
        k = (date, nrm(adv))
        if have.get(k, 0) > 0:
            have[k] -= 1; continue
        # tolérance encodage mysql (accents cassés) : match flou même date
        fz = None
        for (d2, n2), cnt in have.items():
            if cnt > 0 and d2 == date and difflib.SequenceMatcher(None, n2, k[1]).ratio() >= 0.85:
                fz = (d2, n2); break
        if fz:
            have[fz] -= 1; continue
        cla = tg(b,'advclaof')
        try: ocls = int(cla) * 100 if cla and int(cla) < 200 else int(cla or 0)
        except Exception: ocls = 0
        try: pts = float(tg(b,'pointres') or 0)
        except Exception: pts = 0.0
        missing.append({'date': date, 'opp': adv, 'opp_cls': ocls,
                        'won': tg(b,'vd') == 'V', 'pts': round(pts, 2)})
    if not missing: continue
    # catégorie 'autre'
    autre = next((c for c in comps if c['key'] == 'autre'), None)
    if not autre:
        autre = {'key':'autre','label':'Autres compétitions','V':0,'D':0,'pg':0.0,'pl':0.0,
                 'perf':0,'cperf':0,'best':None,'worst':None,'matches':[]}
        comps.append(autre)
    for m in missing:
        autre['matches'].append(m)
        if m['won']: autre['V'] += 1
        else: autre['D'] += 1
        if m['pts'] > 0: autre['pg'] += m['pts']
        else: autre['pl'] += m['pts']
        my = mensuel_at(prof, m['date'])
        if my is not None and m['opp_cls']:
            gap = round(m['opp_cls'] - my)
            rec = {'delta': gap, 'opp': m['opp'], 'opp_cls': m['opp_cls'],
                   'my': round(my), 'date': m['date'], 'comp': 'Autres compétitions'}
            if m['won'] and gap > 0: autre['perf'] += 1
            if (not m['won']) and gap < 0: autre['cperf'] += 1
            if m['won'] and (autre['best'] is None or gap > autre['best']['delta']): autre['best'] = rec
            if (not m['won']) and (autre['worst'] is None or (-gap) > autre['worst']['delta']):
                autre['worst'] = {**rec, 'delta': -gap}
    autre['pg'] = round(autre['pg'],1); autre['pl'] = round(autre['pl'],1)
    autre['solde'] = round(autre['pg'] + autre['pl'],1)
    n = autre['V'] + autre['D']; autre['winpct'] = round(100*autre['V']/n) if n else 0
    # saison recalculée depuis l'ensemble des compétitions
    sa = prof.get('saison') or {}
    V = sum(c['V'] for c in comps); D = sum(c['D'] for c in comps)
    sa['V'] = V; sa['D'] = D; sa['parties'] = V + D
    sa['winpct'] = round(100*V/(V+D)) if V+D else 0
    sa['perfs'] = sum(c.get('perf',0) for c in comps)
    sa['contre_perfs'] = sum(c.get('cperf',0) for c in comps)
    prof['saison'] = sa; prof['competitions'] = comps
    json.dump(prof, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    touched += 1; added_tot += len(missing)
    print(f"+ {prof.get('prenom','')} {prof.get('nom','')} ({lic}) : {len(missing)} parties ajoutées")
print(f"OK — {added_tot} parties récupérées sur {touched} fiches")
