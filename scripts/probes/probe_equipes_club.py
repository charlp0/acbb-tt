#!/usr/bin/env python3
"""Sonde ponctuelle : champs bruts de xml_equipe.php pour quelques clubs adverses (épreuve, division, poule),
pour ne compter dans le brûlage que les équipes du championnat par équipes. Lancer via « Sonde API FFTT »."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # scripts/ : fftt_site, fftt_brulages, fftt_quality (et fftt_build via importlib)
import re, html, urllib.parse
import fftt_site as fs
fb = fs.fb
for club in ('08921182', '08920001', '08920049'):
    for typ in ('M', 'A'):
        r = fb.get(f"xml_equipe.php?numclu={club}&type={typ}")
        print(f"== club {club} type={typ}")
        for b in re.findall(r'<equipe>(.*?)</equipe>', r, re.S):
            champs = {t: fs.tg(b, t) for t in ('libequipe', 'libdivision', 'idepr', 'libepr', 'idequipe')}
            lm = re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>', b)
            q = dict(urllib.parse.parse_qsl(html.unescape(lm.group(1)))) if lm else {}
            print('  ' + ' | '.join(f"{k}={v}" for k, v in champs.items()) + f" | D1={q.get('D1')} cx={q.get('cx_poule')} org={q.get('organisme_pere')}")
        print('  balises vues :', sorted(set(re.findall(r'<([a-z_]+)>', r)))[:20])
