# -*- coding: utf-8 -*-
"""Sonde exploratoire (lecture seule) : les résultats individuels du critérium fédéral sont-ils
exposés par l'API (xml_epreuve / xml_division / xml_result_indiv) ? On cherche l'organisme 92,
l'épreuve critérium, la division D1 Élite Messieurs, puis les tableaux et le classement."""
import os, re, sys, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
def get(q):
    try:
        r = fb.get(q); print('\n### GET %s → %d car.' % (q, len(r))); return r
    except Exception as e:
        print('\n### GET %s → ERREUR %s' % (q, e)); return ''
def tags(x): return sorted(set(re.findall(r'<([a-zA-Z0-9_]+)>', x)))

# 1) organismes départementaux
r = get('xml_organisme.php?type=D')
orgs = re.findall(r'<organisme>(.*?)</organisme>', r, re.S)
print('organismes D :', len(orgs), '| balises :', tags(r)[:12])
cd92 = None
for o in orgs:
    lib = tg(o, 'libelle'); 
    if 'SEINE' in lib.upper() and 'HAUT' in lib.upper(): cd92 = o; print('  → ', lib, '| id', tg(o, 'id'), '| code', tg(o, 'code'))
org_id = tg(cd92, 'id') if cd92 else os.environ.get('ORG', '')
# 2) épreuves individuelles de l'organisme
r = get('xml_epreuve.php?organisme=%s&type=I' % org_id)
eprs = re.findall(r'<epreuve>(.*?)</epreuve>', r, re.S)
print('épreuves I :', len(eprs), '| balises :', tags(r))
for e in eprs: print('  ', tg(e, 'idepreuve'), '|', tg(e, 'libelle'), '|', tg(e, 'typepreuve'), '|', tg(e, 'idtypeepreuve'))
crit = [e for e in eprs if 'CRIT' in tg(e, 'libelle').upper()]
if not crit: crit = eprs[:1]
for e in crit[:2]:
    idepr = tg(e, 'idepreuve')
    # 3) divisions de l'épreuve
    r = get('xml_division.php?organisme=%s&epreuve=%s&type=I' % (org_id, idepr))
    divs = re.findall(r'<division>(.*?)</division>', r, re.S)
    print('divisions :', len(divs), '| balises :', tags(r))
    for d in divs[:60]: print('  ', tg(d, 'iddivision'), '|', tg(d, 'libelle'))
    cible = [d for d in divs if 'D1' in tg(d, 'libelle').upper() and 'MESS' in tg(d, 'libelle').upper()] or divs[:1]
    for d in cible[:1]:
        iddiv = tg(d, 'iddivision'); print('\n--- division cible :', tg(d, 'libelle'), iddiv)
        for action in ('tableau', 'poule', 'classement', 'partie'):
            r = get('xml_result_indiv.php?action=%s&epr=%s&res_division=%s' % (action, idepr, iddiv))
            print('   balises :', tags(r)); print('   extrait :', re.sub(r'\s+', ' ', r[:900]))
            if action == 'tableau':
                tabs = re.findall(r'<tableau>(.*?)</tableau>', r, re.S)
                for t in tabs[:6]:
                    print('   tableau :', re.sub(r'\s+', ' ', t)[:200])
                    cx = tg(t, 'cx_tableau') or tg(t, 'idtableau') or tg(t, 'id')
                    if cx:
                        rr = get('xml_result_indiv.php?action=classement&epr=%s&res_division=%s&cx_tableau=%s' % (idepr, iddiv, cx))
                        print('     balises :', tags(rr)); print('     extrait :', re.sub(r'\s+', ' ', rr[:1200]))
