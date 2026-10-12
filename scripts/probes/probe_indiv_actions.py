# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : que rendent les actions partie / poule / tableau / classement de
xml_result_indiv pour (a) une division avec classement publié, (b) une division « <liste/> »,
(c) un id en erreur 400 ? Sert à distinguer « division existante non clôturée » de « id inexistant »."""
import os, re, sys, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
sq = lambda s: re.sub(r'\s+', ' ', s)
for div in (233806, 233802, 233805, 233853, 233801):
    for action in ('classement', 'partie', 'poule', 'tableau', 'initial'):
        ep = 'xml_result_indiv.php?action=%s&epr=0&res_division=%d' % (action, div)
        try:
            r = requests.get(fb.BASE + ep + '&' + fb.auth(), timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(0.25)
            n = len(re.findall(r'<(classement|partie|poule|tableau|joueur)>', r.text))
            print('%d %-10s → HTTP %s, %5d car., %3d nœuds | %s' % (div, action, r.status_code, len(r.text), n, sq(r.text)[40:420]))
        except Exception as e: print(div, action, 'EXC', e)
