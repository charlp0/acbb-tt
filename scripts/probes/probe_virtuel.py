# -*- coding: utf-8 -*-
"""Sonde : l'API SPID expose-t-elle les points « virtuels » (ou « premium ») d'une licence ?
Affiche TOUTES les balises de xml_licence_b et xml_joueur pour trois licences, puis compte les parties
de xml_partie (saison en cours, validées ou non) et de xml_partie_mysql (homologuées, avec pointres).
Lecture seule. Lancer via « Sonde API FFTT » (identifiants en secrets GitHub)."""
import os, re, sys, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
LICS = (os.environ.get('LIC') or '9263353,9265882,9257190').split(',')
def alltags(xml):
    return [(t, v.strip()) for t, v in re.findall(r'<([a-z_]+)>(.*?)</\1>', xml, re.S) if t not in ('liste', 'licence_b', 'joueur')]
for lic in LICS:
    print('\n#################', lic)
    for ep in ('xml_licence_b.php?licence=%s', 'xml_joueur.php?licence=%s'):
        xml = fb.get(ep % lic)
        print('== ' + ep.split('.')[0])
        for t, v in alltags(xml): print('  %-12s %s' % (t, v[:60]))
    allp = fb.get('xml_partie.php?numlic=%s' % lic)
    blocs = re.findall(r'<partie>(.*?)</partie>', allp, re.S)
    saison = [b for b in blocs if (fb.tag(b, 'date') and fb.dn(fb.tag(b, 'date')) >= fb.SEASON_START)]
    print('== xml_partie : %d parties, %d de la saison, balises : %s' % (len(blocs), len(saison), sorted(set(re.findall(r'<([a-z_]+)>', saison[0] if saison else '')))))
    V = sum(1 for b in saison if fb.tag(b, 'victoire') == 'V'); print('   saison : %dV / %dD' % (V, len(saison) - V))
    pm = fb.get('xml_partie_mysql.php?licence=%s' % lic)
    hb = re.findall(r'<partie>(.*?)</partie>', pm, re.S)
    hs = [b for b in hb if fb.tag(b, 'date') and fb.dn(fb.tag(b, 'date')) >= fb.SEASON_START]
    print('== xml_partie_mysql : %d homologuées cette saison, somme pointres = %.1f' % (len(hs), sum(float(fb.tag(b, 'pointres') or 0) for b in hs)))
    if hs: print('   balises :', sorted(set(re.findall(r'<([a-z_]+)>', hs[0]))))
