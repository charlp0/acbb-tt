# -*- coding: utf-8 -*-
"""Sonde : existe-t-il un point d'entree FFTT qui porte la saison 26/27 ?

xml_partie_mysql ne connait rien apres le 30/06/2026 sur 1 069 licences. Avant de
conclure que la federation ne publie pas encore cette saison, essayer les autres
ecritures : xml_partie.php prend peut-etre « numlic » et non « licence ».
Aucune licence n'est imprimee.
"""
import json, os, re, urllib.request, importlib.util, collections
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
SB = "https://vhhmageufrcenruywawg.supabase.co"
k = os.environ['SUPA_SERVICE_KEY']
req = urllib.request.Request(
    SB + '/rest/v1/scenarios_log?select=tags&slot=eq.criterium_lic&order=id.desc&limit=1',
    headers={'apikey': k, 'Authorization': 'Bearer ' + k})
with urllib.request.urlopen(req) as r: tbl = json.load(r)[0]['tags']['lic']
lics = sorted({l for g in tbl.values() for l in g.values()})

def cle(d):
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', d or '')
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (0, 0, 0)

EP = ['xml_partie.php?numlic=%s', 'xml_partie.php?licence=%s',
      'xml_partie_mysql.php?numlic=%s', 'xml_partie_mysql.php?licence=%s',
      'xml_partie_mysql.php?licence=%s&...']
for lic in lics[:4]:
    print('\n' + '=' * 72)
    for ep in EP[:4]:
        nom = ep.split('=')[0]
        try: brut = fb.get(ep % lic)
        except Exception as e: print('  %-34s ERREUR : %s' % (nom, e)); continue
        dates = re.findall(r'<date>([^<]*)</date>', brut or '')
        bal = collections.Counter(re.findall(r'<([a-zA-Z0-9_]+)>', brut or ''))
        tard = max(dates, key=cle) if dates else '—'
        apres = [d for d in dates if cle(d) >= (2026, 7, 1)]
        print('  %-34s %4d parties · + recente %s · %d depuis le 01/07/2026' % (nom, len(dates), tard, len(apres)))
        if not dates: print('  %-34s balises : %s' % ('', dict(bal.most_common(5)) or 'aucune'))
        if apres: print('  %-34s EXEMPLE : %s' % ('', re.sub(r'\s+',' ',re.search(r'<partie>(.*?)</partie>', brut, re.S).group(1))[:260]))
