# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : réponses HTTP telles quelles des points d'entrée « épreuves
individuelles » (xml_organisme, xml_epreuve, xml_division, xml_result_indiv), sans le filtre
require_xml, pour voir les codes d'erreur et les balises réelles."""
import os, re, sys, importlib.util, requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def raw(ep, n=700):
    url = fb.BASE + ep + ("&" if "?" in ep else "?") + fb.auth()
    try:
        r = requests.get(url, timeout=25); r.encoding = 'ISO-8859-1'
        body = re.sub(r'\s+', ' ', r.text)
        print('\n### %s → HTTP %s, %d car.' % (ep, r.status_code, len(r.text)))
        print('    ' + body[:n])
        return r.text
    except Exception as e:
        print('\n### %s → EXCEPTION %s' % (ep, e)); return ''
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''

r = raw('xml_organisme.php?type=D', 400)
orgs = re.findall(r'<organisme>(.*?)</organisme>', r, re.S)
cd92 = [o for o in orgs if 'SEINE' in tg(o,'libelle').upper() and 'HAUT' in tg(o,'libelle').upper()]
print('organismes :', len(orgs), '| 92 :', [re.sub(r'\s+',' ',o)[:160] for o in cd92])
org = tg(cd92[0], 'id') if cd92 else ''
raw('xml_organisme.php?type=L', 300)
r = raw('xml_epreuve.php?organisme=%s&type=I' % org, 1500)
eprs = re.findall(r'<epreuve>(.*?)</epreuve>', r, re.S)
for e in eprs: print('   épreuve :', re.sub(r'\s+',' ',e)[:200])
crit = [e for e in eprs if 'CRIT' in tg(e,'libelle').upper()] or eprs[:1]
idepr = tg(crit[0], 'idepreuve') if crit else ''
r = raw('xml_division.php?organisme=%s&epreuve=%s&type=I' % (org, idepr), 2500)
divs = re.findall(r'<division>(.*?)</division>', r, re.S)
for d in divs: print('   division :', re.sub(r'\s+',' ',d)[:160])
cible = [d for d in divs if 'D1' in tg(d,'libelle').upper() and 'MESS' in tg(d,'libelle').upper()] or divs[:1]
iddiv = tg(cible[0], 'iddivision') if cible else ''
print('\n--- cible : épreuve %s, division %s' % (idepr, iddiv))
for action in ('tableau', 'poule', 'classement', 'partie'):
    raw('xml_result_indiv.php?action=%s&epr=%s&res_division=%s' % (action, idepr, iddiv), 1500)
raw('xml_result_indiv.php?action=classement&epr=%s&res_division=%s&cx_tableau=' % (idepr, iddiv), 600)
# variante : tableaux listés par la division ?
raw('xml_division.php?organisme=%s&epreuve=%s&type=I&iddivision=%s' % (org, idepr, iddiv), 600)
