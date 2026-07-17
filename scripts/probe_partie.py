# -*- coding: utf-8 -*-
"""Sonde one-shot : xml_partie / xml_partie_mysql servent-ils encore 2025/26 ?
Test sur la licence de Virginie Le Bourg (9260920). Usage CI (FFTT_ID/FFTT_PWD)."""
import re, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
LIC = '9260920'
for ep, param in (('xml_partie.php', 'numlic'), ('xml_partie_mysql.php', 'licence')):
    try:
        r = fb.get(f"{ep}?{param}={LIC}")
        parties = re.findall(r'<partie>(.*?)</partie>', r, re.S)
        dates = sorted(set(re.findall(r'<date>(.*?)</date>', r)))
        eprs = sorted(set(re.findall(r'<epreuve>(.*?)</epreuve>', r)))
        print(f"== {ep} : {len(parties)} parties")
        print(f"   dates : {dates[:3]} ... {dates[-3:] if len(dates)>3 else ''}")
        print(f"   epreuves : {eprs}")
    except Exception as e:
        print(f"== {ep} : ERREUR {e}")
