# -*- coding: utf-8 -*-
"""Sonde (lecture seule) : classements de critérium fédéral des divisions où joue un licencié ACBB.
xml_result_indiv.php?action=classement&epr=0&res_division=<id> rend <classement><rang/nom/clt/club/points>.
Sans xml_epreuve (bloqué), on balaie les identifiants de division (env RANGES, défaut
"233800-236200") et on garde les divisions contenant le club. WORKERS fils (défaut 6), progression affichée."""
import os, re, sys, importlib.util, requests, time, collections
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
CLUB = os.environ.get('CLUB_NOM', 'BOULOGNE BILLANCOURT')
RANGES = os.environ.get('RANGES', '233800-236200')
WORKERS = int(os.environ.get('WORKERS', '6'))
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
def fetch(div):
    url = fb.BASE + 'xml_result_indiv.php?action=classement&epr=0&res_division=%d&' % div + fb.auth()
    for _ in range(2):
        try:
            r = requests.get(url, timeout=25); r.encoding = 'ISO-8859-1'
            if r.status_code == 200: return div, r.text
            time.sleep(0.3)
        except Exception: time.sleep(0.5)
    return div, ''
ids = []
for part in RANGES.split(','):
    a, b = part.split('-'); ids += list(range(int(a), int(b) + 1))
t0 = time.time(); hits = {}
done = 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for div, txt in ex.map(fetch, ids):
        done += 1
        if done % 250 == 0: print('  … %d/%d ids, %d hits, %.0f s' % (done, len(ids), len(hits), time.time() - t0), flush=True)
        if CLUB.upper() in txt.upper():
            hits[div] = txt; print('  HIT division %d' % div, flush=True)
print('balayage de %d ids en %.0f s → %d divisions avec %s' % (len(ids), time.time() - t0, len(hits), CLUB))
resume = []
for div in sorted(hits):
    rows = [(tg(c, 'rang'), tg(c, 'nom'), tg(c, 'clt'), tg(c, 'club'), tg(c, 'points')) for c in re.findall(r'<classement>(.*?)</classement>', hits[div], re.S)]
    n = len(rows); clts = [int(x[2]) for x in rows if x[2].isdigit()]
    print('\n== division %d — %d classés — points %s→%s' % (div, n, max(clts) if clts else '?', min(clts) if clts else '?'))
    for rang, nom, clt, club, pts in rows:
        star = '★' if CLUB.upper() in club.upper() else ' '
        print('  %s %4s  %-28s %5s  %-32s %s' % (star, rang, nom[:28], clt, club[:32], pts))
        if star == '★': resume.append((div, rang, nom, clt, pts, n))
print('\n== Résumé ACBB (division, rang/nb, nom, pts, points de tour)')
for div, rang, nom, clt, pts, n in resume: print('  %d  %4s/%-3d  %-28s %5s  %s' % (div, rang, n, nom, clt, pts))
