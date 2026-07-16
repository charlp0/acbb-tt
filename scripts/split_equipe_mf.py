# -*- coding: utf-8 -*-
"""
Scinde la catégorie 'Championnat par équipe' des fiches joueur en
Masculin / Féminin pour les joueuses concernées (one-shot, 16/07/2026).

L'épreuve exacte n'ayant pas été conservée par match (categorize() fusionne),
la classification est reconstruite par recoupement : un match de championnat
joué à une date où la joueuse figure sur une feuille de rencontre DAMES
archivée (data/archive/2025-2026/phase-*/. . .DAMES/) est Féminin, sinon
Masculin. Les archives couvrent PN D (F1), R1 D (F2), PR D 92 (F3/F4).

Stats recalculées par catégorie ; delta perf recalculé avec le mensuel du
mois du match (timeline), comme fftt_build. Le bloc 'detail' (manches/doubles,
non séparable rétroactivement) reste sur la catégorie majoritaire.
Usage : python3 scripts/split_equipe_mf.py
"""
import json, glob, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def nrm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z]', '', s)

# dates de feuilles DAMES par joueuse
dames = {}
for f in glob.glob(os.path.join(ROOT, 'data/archive/2025-2026/phase-*/*DAMES*/poule-*.json')):
    d = json.load(open(f))
    for r in d['rencontres']:
        for side in ('compo_a', 'compo_b'):
            for p in (r.get(side) or []):
                dames.setdefault(nrm(p['nom']), set()).add(r['date'])

MOIS = {'Sept': 9, 'Oct': 10, 'Nov': 11, 'Déc': 12, 'Jan': 1, 'Fév': 2,
        'Mars': 3, 'Avr': 4, 'Mai': 5, 'Juin': 6}

def mensuel_at(prof, date):
    """mensuel au mois du match, depuis la timeline (comme fftt_build)."""
    try:
        m = int(date.split('/')[1])
    except Exception:
        return None
    tl = prof.get('timeline') or []
    best = None
    for e in tl:
        if MOIS.get(e['m']) == m:
            best = e['v']
    if best is None and tl:
        best = tl[-1]['v']
    return best

def rebuild(matches, prof, label):
    c = {'key': None, 'label': label, 'V': 0, 'D': 0, 'pg': 0.0, 'pl': 0.0,
         'perf': 0, 'cperf': 0, 'best': None, 'worst': None, 'matches': matches}
    for m in matches:
        if m['won']: c['V'] += 1
        else: c['D'] += 1
        if m['pts'] > 0: c['pg'] += m['pts']
        else: c['pl'] += m['pts']
        my = mensuel_at(prof, m['date'])
        if my is None: continue
        gap = round((m.get('opp_cls') or 0) - my)
        rec = {'delta': gap, 'opp': m['opp'], 'opp_cls': m.get('opp_cls'),
               'my': round(my), 'date': m['date'], 'comp': label}
        if m['won'] and gap > 0: c['perf'] += 1
        if (not m['won']) and gap < 0: c['cperf'] += 1
        if m['won'] and (c['best'] is None or gap > c['best']['delta']): c['best'] = rec
        if (not m['won']) and (c['worst'] is None or (-gap) > c['worst']['delta']):
            c['worst'] = {**rec, 'delta': -gap}
    c['pg'] = round(c['pg'], 1); c['pl'] = round(c['pl'], 1)
    c['solde'] = round(c['pg'] + c['pl'], 1)
    n = c['V'] + c['D']; c['winpct'] = round(100 * c['V'] / n) if n else 0
    return c

split_n = 0; relab_n = 0
for f in glob.glob(os.path.join(ROOT, 'data/players/*.json')):
    prof = json.load(open(f))
    key = nrm((prof.get('nom') or '') + (prof.get('prenom') or ''))
    # les archives stockent "NOM Prenom" d'un bloc
    fdates = None
    for k, v in dames.items():
        if k == key or (len(key) > 6 and (k in key or key in k)):
            fdates = v; break
    if not fdates: continue
    comps = prof.get('competitions') or []
    eq = next((c for c in comps if c['key'] == 'equipe'), None)
    if not eq: continue
    fm = [m for m in eq['matches'] if m['date'] in fdates]
    mm = [m for m in eq['matches'] if m['date'] not in fdates]
    if not fm: continue
    idx = comps.index(eq)
    if not mm:  # tout féminin -> simple renommage
        eq['label'] = 'Championnat par équipe · Féminin'
        relab_n += 1
    else:
        cm = rebuild(mm, prof, 'Championnat par équipe · Masculin'); cm['key'] = 'equipe'
        cf = rebuild(fm, prof, 'Championnat par équipe · Féminin'); cf['key'] = 'equipe_f'
        if 'detail' in eq:  # non séparable -> catégorie majoritaire
            (cm if len(mm) >= len(fm) else cf)['detail'] = eq['detail']
        comps[idx:idx + 1] = [cm, cf]
        split_n += 1
    prof['competitions'] = comps
    json.dump(prof, open(f, 'w', encoding='utf-8'), ensure_ascii=False)

print(f"OK — {split_n} fiche(s) scindée(s) M/F, {relab_n} renommée(s) 100% Féminin")
