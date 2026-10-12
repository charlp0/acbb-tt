# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : identifiant d'organisme via les liens de division des équipes
du club (organisme_pere), puis xml_epreuve → xml_division → xml_result_indiv pour le critérium."""
import os, re, sys, html, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def raw(ep, n=700, quiet=False):
    url = fb.BASE + ep + ("&" if "?" in ep else "?") + fb.auth()
    try:
        r = requests.get(url, timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(0.2)
        body = re.sub(r'\s+', ' ', r.text)
        if not quiet: print('\n### %s → HTTP %s, %d car.\n    %s' % (ep, r.status_code, len(r.text), body[:n]))
        return r.text
    except Exception as e:
        print('\n### %s → EXCEPTION %s' % (ep, e)); return ''
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
def tags(x): return sorted(set(re.findall(r'<([a-zA-Z0-9_]+)>', x)))

r = raw('xml_equipe.php?numclu=%s&type=A' % fb.CLUB, 300, quiet=True)
orgs = {}
for b in re.findall(r'<equipe>(.*?)</equipe>', r, re.S):
    lien = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', tg(b, 'liendivision')))
    m = re.search(r'organisme_pere=(\d+)', lien)
    if m: orgs.setdefault(m.group(1), set()).add(tg(b, 'libdivision')[:40])
print('organisme_pere trouvés :'); 
for k, v in orgs.items(): print('  ', k, '→', sorted(v)[:4])
for org, libs in orgs.items():
    r = raw('xml_epreuve.php?organisme=%s&type=I' % org, 600)
    eprs = re.findall(r'<epreuve>(.*?)</epreuve>', r, re.S)
    print('   balises :', tags(r))
    for e in eprs[:40]: print('   épreuve :', re.sub(r'\s+',' ',e)[:220])
    crit = [e for e in eprs if 'CRIT' in tg(e,'libelle').upper()]
    for e in crit[:1]:
        idepr = tg(e, 'idepreuve')
        r = raw('xml_division.php?organisme=%s&epreuve=%s&type=I' % (org, idepr), 400)
        divs = re.findall(r'<division>(.*?)</division>', r, re.S)
        print('   balises :', tags(r), '| divisions :', len(divs))
        for d in divs[:80]: print('   division :', re.sub(r'\s+',' ',d)[:200])
        cible = [d for d in divs if re.search(r'D1', tg(d,'libelle').upper()) and 'MESS' in tg(d,'libelle').upper()] or divs[:1]
        for d in cible[:1]:
            iddiv = tg(d, 'iddivision'); print('\n--- cible :', tg(d,'libelle'), '| epr', idepr, '| div', iddiv)
            for action in ('tableau', 'poule', 'classement', 'partie'):
                rr = raw('xml_result_indiv.php?action=%s&epr=%s&res_division=%s' % (action, idepr, iddiv), 2500)
                print('   balises :', tags(rr))
                if action == 'tableau':
                    for t in re.findall(r'<tableau>(.*?)</tableau>', rr, re.S)[:8]:
                        print('   tableau :', re.sub(r'\s+',' ',t)[:300])
