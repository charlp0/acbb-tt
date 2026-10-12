# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : comment sont exposés les groupes multiples d'un tour régional ?
Liste des tours (action=poule) de quelques divisions de ligue, puis essai des cx_tableau voisins."""
import os, re, sys, html, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def get(ep):
    try:
        r = requests.get(fb.BASE + ep + '&' + fb.auth(), timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(0.15); return r.text if r.status_code == 200 else ''
    except Exception: return ''
def tg(x, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', x, re.S); return m.group(1).strip() if m else ''
sq = lambda s: re.sub(r'\s+', ' ', s)
for div, lib in ((232846, 'R2 -13 M'), (232906, 'R2 -15 M'), (233245, 'R2 -19 M'), (232844, 'R1 -19 M'), (232845, 'R1 -15 M'), (233001, 'D92 D1 Elite M')):
    r = get('xml_result_indiv.php?action=poule&epr=18367&res_division=%d' % div)
    tours = [(sq(tg(t, 'libelle')), tg(t, 'date'), html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', tg(t, 'lien')))) for t in re.findall(r'<tour>(.*?)</tour>', r, re.S)]
    print('\n## %s (%d) : %d tours' % (lib, div, len(tours)))
    for t in tours: print('   ', t)
    t1 = [t for t in tours if t[0].upper().startswith('T1')]
    if div == 232846 and t1:
        cx = int(re.search(r'cx_tableau=(\d+)', t1[0][2]).group(1))
        print('   voisins de cx_tableau %d :' % cx)
        for c in range(cx - 12, cx + 13):
            rr = get('xml_result_indiv.php?action=classement&epr=18367&res_division=%d&cx_tableau=%d' % (div, c))
            rows = re.findall(r'<classement>(.*?)</classement>', rr, re.S)
            if rows: print('     cx %d → %d classés, ACBB=%s, ex: %s' % (c, len(rows), 'BOULOGNE' in rr.upper(), ', '.join(tg(x, 'nom') for x in rows[:3])))
    if div == 232846 and t1:
        rr = get('xml_result_indiv.php?action=partie&' + t1[0][2]); print('   parties T1 Gr1 :', len(re.findall(r'<partie>', rr)), '| ALLEGRE dans les parties :', 'ALLEGRE' in rr.upper(), '| libellés :', sorted(set(re.findall(r'<libelle>(.*?)</libelle>', rr)))[:8])
