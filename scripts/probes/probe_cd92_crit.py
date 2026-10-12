# -*- coding: utf-8 -*-
"""Sonde (lecture seule) : divisions du critérium fédéral du CD92 (organisme 116) via xml_division
(autorisé) en testant l'épreuve 18367 vue dans les liens de tours, puis par balayage d'identifiants
d'épreuve ; pour chaque division : tours (action=poule), classement du T1 (cx_tableau) et joueurs ACBB.
Env : ORGS (116,16,1 = CD92, ligue IDF, FFTT), EPR (18367 = critérium 2026-27), SCAN (18000-18800), CLUB_NOM."""
import os, re, sys, html, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
ORGS = (os.environ.get('ORGS') or '116,16,1').split(','); ORG = ORGS[0]; EPR = os.environ.get('EPR', '18367'); CLUB = os.environ.get('CLUB_NOM', 'BOULOGNE BILLANCOURT')
a, b = (os.environ.get('SCAN') or '18000-18800').split('-')
def get(ep, pause=0.15):
    for _ in range(3):
        try:
            r = requests.get(fb.BASE + ep + ('&' if '?' in ep else '?') + fb.auth(), timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(pause)
            if r.status_code == 200: return r.text
            if r.status_code == 400: return ''
        except Exception: time.sleep(0.5)
    return ''
def tg(x, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', x, re.S); return m.group(1).strip() if m else ''
sq = lambda s: re.sub(r'\s+', ' ', s)
def divisions(org, epr):
    r = get('xml_division.php?organisme=%s&epreuve=%s&type=I' % (org, epr))
    return [(tg(d, 'iddivision'), sq(tg(d, 'libelle'))) for d in re.findall(r'<division>(.*?)</division>', r, re.S)]
found = {}
for org in ORGS:
    divs = divisions(org, EPR); print('épreuve %s, organisme %s → %d divisions' % (EPR, org, len(divs)), flush=True)
    if divs: found[(org, EPR)] = divs
if (ORG, EPR) not in found:
    print('balayage des épreuves %s-%s pour l\'organisme %s …' % (a, b, ORG), flush=True)
    for epr in range(int(a), int(b) + 1):
        divs = divisions(ORG, epr)
        if divs: print('  épreuve %d → %d divisions : %s' % (epr, len(divs), '; '.join(l for _, l in divs[:6])), flush=True); found[(ORG, str(epr))] = divs
for (org, epr), divs in found.items():
    print('\n#### organisme %s, épreuve %s : %d divisions' % (org, epr, len(divs)), flush=True)
    for iddiv, lib in divs: print('   %s  %s' % (iddiv, lib))
    for iddiv, lib in divs:
        tours = [(sq(tg(t, 'libelle')), tg(t, 'date'), html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', tg(t, 'lien')))) for t in re.findall(r'<tour>(.*?)</tour>', get('xml_result_indiv.php?action=poule&epr=%s&res_division=%s' % (epr, iddiv)), re.S)]
        t1 = [t for t in tours if t[0].upper().startswith('T1') or t[1] in ('09/10/2026', '10/10/2026', '11/10/2026')] or tours[-1:]
        if not t1: print('\n== %s (%s) : aucun tour' % (lib, iddiv)); continue
        for grp in t1:
            lien = grp[2]; cx = re.search(r'cx_tableau=(\d+)', lien)
            r = get('xml_result_indiv.php?action=classement&' + lien) if cx else ''
            rows = [(tg(c, 'rang'), tg(c, 'nom'), tg(c, 'clt'), tg(c, 'club'), tg(c, 'points')) for c in re.findall(r'<classement>(.*?)</classement>', r, re.S)]
            acbb = [x for x in rows if CLUB.upper() in x[3].upper()]
            print('\n== %s (div %s) — %s %s — %d classés, %d ACBB' % (lib, iddiv, grp[0], grp[1], len(rows), len(acbb)), flush=True)
            for rang, nom, clt, club, pts in rows:
                if (acbb and 'ELITE' in lib.upper() and 'MESS' in lib.upper() and len(rows) <= 40) or CLUB.upper() in club.upper():
                    print('  %s %4s/%-3d %-28s %5s %-30s %s' % ('★' if CLUB.upper() in club.upper() else ' ', rang, len(rows), nom[:28], clt, club[:30], pts))
