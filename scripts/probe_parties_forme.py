# -*- coding: utf-8 -*-
"""Sonde : que renvoie vraiment la FFTT sur les parties d'un joueur ?

Le premier passage des bilans a rendu 0 victoire et 0 defaite pour 1 069 licences,
sans la moindre erreur reseau. Donc les reponses arrivent mais ne contiennent pas ce
que j'attends. Cette sonde regarde la forme brute, sur trois licences tirees de la
table deposee — aucune licence n'est imprimee, seulement la structure et les dates.
"""
import json, os, re, sys, urllib.request, importlib.util, collections
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
SB = "https://vhhmageufrcenruywawg.supabase.co"

k = os.environ['SUPA_SERVICE_KEY']
req = urllib.request.Request(
    SB + '/rest/v1/scenarios_log?select=tags&slot=eq.criterium_lic&order=id.desc&limit=1',
    headers={'apikey': k, 'Authorization': 'Bearer ' + k})
with urllib.request.urlopen(req) as r: tbl = json.load(r)[0]['tags']['lic']
lics = sorted({l for grp in tbl.values() for l in grp.values()})
print('%d licences dans la table' % len(lics))

for lic in lics[:3]:
    print('\n' + '=' * 70)
    for ep in ('xml_partie_mysql.php?licence=%s', 'xml_partie.php?licence=%s'):
        nom = ep.split('.php')[0]
        try: brut = fb.get(ep % lic)
        except Exception as e: print('%-18s ERREUR %s' % (nom, e)); continue
        bal = collections.Counter(re.findall(r'<([a-zA-Z0-9_]+)>', brut or ''))
        dates = re.findall(r'<date>([^<]*)</date>', brut or '')
        print('%-18s %d octets · balises %s' % (nom, len(brut or ''), dict(bal.most_common(6))))
        print('%-18s %d dates · de %s a %s' % ('', len(dates), min(dates) if dates else '—', max(dates) if dates else '—'))
        if dates:
            ans = collections.Counter(d[-4:] for d in dates if len(d) >= 4)
            print('%-18s annees : %s' % ('', dict(sorted(ans.items()))))
        bloc = re.search(r'<partie>(.*?)</partie>', brut or '', re.S)
        if bloc: print('%-18s 1re partie : %s' % ('', re.sub(r'\s+', ' ', bloc.group(1))[:300]))
        elif brut: print('%-18s debut brut : %s' % ('', re.sub(r'\s+', ' ', brut)[:300]))
