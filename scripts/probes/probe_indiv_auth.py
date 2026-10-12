# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : nos identifiants ont-ils accès à xml_division / xml_result_indiv ?
Test avec des identifiants factices : 401 « Script non autorisé » = bloqué ; autre chose = autorisé."""
import os, re, sys, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
for ep in ['xml_division.php?organisme=116&epreuve=1&type=I',
           'xml_result_indiv.php?action=classement&epr=1&res_division=1',
           'xml_result_indiv.php?action=partie&epr=1&res_division=1',
           'xml_result_equ.php?action=classement&auto=1&D1=1&cx_poule=1&organisme_pere=116',
           'xml_liste_joueur.php?club=%s' % fb.CLUB,
           'xml_histo_classement.php?numlic=7824630']:
    url = fb.BASE + ep + '&' + fb.auth()
    try:
        r = requests.get(url, timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(0.3)
        print('### %s → HTTP %s | %s' % (ep, r.status_code, re.sub(r'\s+', ' ', r.text)[:260]))
    except Exception as e: print('### %s → EXCEPTION %s' % (ep, e))
