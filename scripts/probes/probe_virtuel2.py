# -*- coding: utf-8 -*-
"""Sonde : comment la FFTT estime-t-elle les parties non homologuées dans ses points « virtuels » ?
Pour trois licences (cibles appli FFTT du 31/10/2026 : Mourre 1067.0, d'Avout 843.8, Allegre-Guillaume 998.3),
liste les parties de xml_partie absentes de xml_partie_mysql, et teste plusieurs hypothèses de calcul :
niveau du joueur = officiel / mensuel / virtuel glissant ; niveau adverse = <classement> de xml_partie / pointm
actuel de l'adversaire (si <licence> est bien la sienne). Lecture seule."""
import os, re, sys, importlib.util, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
CIBLES = {'9263353': (783, 818.6, 1067.0), '9265882': (675, 772.1, 843.8), '9257190': (859, 889.8, 998.3)}
def num(s):
    m = re.search(r'(\d+)\s*pts', s or '', re.I)
    if m: return int(m.group(1))
    s = (s or '').split(' - ')[-1]
    try: return int(re.sub(r'\D', '', s) or 0)
    except Exception: return 0
def dkey(d): return fb.dn(d)
for lic, (off, pointm, cible) in CIBLES.items():
    print('\n#################', lic, 'officiel', off, 'mensuel', pointm, 'cible virtuel', cible, '=> à estimer :', round(cible - pointm, 1))
    lb = fb.get('xml_licence_b.php?licence=%s' % lic)
    print('  xml_licence_b brut (300 car.) :', re.sub(r'\s+', ' ', lb)[:300])
    allp = fb.get('xml_partie.php?numlic=%s' % lic)
    pm = fb.get('xml_partie_mysql.php?licence=%s' % lic)
    homol = {fb.tag(b, 'idpartie') for b in re.findall(r'<partie>(.*?)</partie>', pm, re.S)}
    parts = []
    for b in re.findall(r'<partie>(.*?)</partie>', allp, re.S):
        d = fb.tag(b, 'date')
        if not d or fb.dn(d) < fb.SEASON_START: continue
        if fb.tag(b, 'idpartie') in homol: continue
        parts.append({'date': d, 'epr': fb.tag(b, 'epreuve')[:28], 'opp': fb.tag(b, 'nom')[:22], 'cls': num(fb.tag(b, 'classement')),
                      'clsraw': fb.tag(b, 'classement'), 'coef': float(fb.tag(b, 'coefchamp') or 1), 'won': fb.tag(b, 'victoire') == 'V',
                      'lic': fb.tag(b, 'licence'), 'forfait': fb.tag(b, 'forfait')})
    parts.sort(key=lambda p: dkey(p['date']))
    print('  %d parties non homologuées' % len(parts))
    # pointm actuel de l'adversaire si <licence> le désigne
    cache = {}
    for p in parts:
        l = p['lic']
        if l and l not in cache and l != lic:
            x = fb.get('xml_licence_b.php?licence=%s' % l); time.sleep(0.1)
            cache[l] = (fb.tag(x, 'nom'), fb.tag(x, 'point'), fb.tag(x, 'pointm'), fb.tag(x, 'initm'))
        p['adv'] = cache.get(l)
    for p in parts[:40]:
        print('   %s %-28s %-22s cls=%-18s coef=%s %s lic=%s adv=%s' % (p['date'], p['epr'], p['opp'], p['clsraw'][:18], p['coef'], 'V' if p['won'] else 'D', p['lic'], p['adv']))
    def total(my_mode, opp_mode):
        my = {'off': off, 'men': pointm}[my_mode] if my_mode != 'run' else pointm
        s = 0.0
        for p in parts:
            adv = p['cls']
            if opp_mode == 'pointm' and p['adv'] and p['adv'][2]: adv = float(p['adv'][2])
            if opp_mode == 'point' and p['adv'] and p['adv'][1]: adv = float(p['adv'][1])
            g = fb.grille(my, adv, p['won'], p['coef'])
            s += g
            if my_mode == 'run': my += g
        return round(s, 1)
    print('  hypothèses (somme estimée, cible %s) :' % round(cible - pointm, 1))
    for mm in ('off', 'men', 'run'):
        for om in ('cls', 'point', 'pointm'):
            print('     joueur=%-4s adversaire=%-7s -> %s' % (mm, om, total(mm, om)))
