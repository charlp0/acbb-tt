# -*- coding: utf-8 -*-
"""Sonde : points et parties de la saison en cours pour une licence (défaut 7824630, env LIC).
Lit xml_licence_b (pointm = points mensuels), xml_joueur (point / apoint / valcla / valinit)
et xml_partie.php?numlic= (parties de la saison en cours, avec coefchamp), puis recalcule le
solde avec le barème FFTT × coefchamp. Lecture seule, ne modifie rien."""
import os, re, sys, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # scripts/ : fftt_quality etc.
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
LIC = os.environ.get('LIC') or (sys.argv[1] if len(sys.argv) > 1 else '7824630')

def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
def show(title, xml, tagsel):
    print('\n== ' + title)
    for t in tagsel:
        v = tg(xml, t)
        if v != '': print('  %-10s %s' % (t, v))

lic_b = fb.get('xml_licence_b.php?licence=%s' % LIC)
show('xml_licence_b', lic_b, ['licence','nom','prenom','nomclub','point','pointm','apointm','initm','cat','echelon','place','validation'])
jou = fb.get('xml_joueur.php?licence=%s' % LIC)
show('xml_joueur', jou, ['licence','nom','prenom','club','clast','aclast','point','apoint','valcla','valinit','clglob','aclglob','rangreg','rangdep','categ'])

VA = [(24,6),(49,7),(99,8),(149,10),(199,13),(299,17),(399,22),(499,28),(10**9,40)]
VN = [(24,6),(49,5.5),(99,5),(149,4),(199,3),(299,2),(399,1),(499,0.5),(10**9,0)]
DN = [(24,-5),(49,-4.5),(99,-4),(149,-3),(199,-2),(299,-1),(399,-0.5),(499,0),(10**9,0)]
DA = [(24,-5),(49,-6),(99,-7),(149,-8),(199,-10),(299,-12.5),(399,-16),(499,-20),(10**9,-29)]
def bar(tab, e):
    for lim, v in tab:
        if e <= lim: return v
def pts(my, adv, gagne):
    e = adv - my
    if gagne: return bar(VA, e) if e >= 0 else bar(VN, -e)
    return bar(DN, e) if e >= 0 else bar(DA, -e)
def num(s):
    m = re.search(r'\d+(?:[.,]\d+)?', s or ''); return float(m.group(0).replace(',', '.')) if m else None

base = num(os.environ.get('MYPTS') or '') or num(tg(lic_b, 'initm')) or num(tg(jou, 'valinit')) or num(tg(jou, 'apoint')) or 1042.0
print('\nBase de calcul (points officiels) : %s' % base)

r = fb.get('xml_partie.php?numlic=%s' % LIC)
parts = re.findall(r'<partie>(.*?)</partie>', r, re.S)
print('\n== xml_partie.php?numlic= : %d parties' % len(parts))
if parts: print('  balises :', sorted(set(re.findall(r'<([a-z]+)>', parts[0]))))
tot = {}; grand = 0.0
print('  %-10s %-28s %5s %-32s %5s %3s %3s %7s' % ('date','adversaire','clt','épreuve','coef','V/D','FF','points'))
for b in parts:
    date, adv, cls, epr = tg(b,'date'), tg(b,'nom'), tg(b,'classement'), tg(b,'epreuve')
    coef = num(tg(b,'coefchamp')) or 1.0
    v = (tg(b,'victoire') or '').upper().startswith('V'); ff = (tg(b,'forfait') or '0').strip() == '1'
    c = num(cls); p = None
    if c is not None and not ff: p = pts(base, c, v) * coef
    if p is not None: tot[epr] = tot.get(epr, 0.0) + p; grand += p
    print('  %-10s %-28s %5s %-32s %5s %3s %3s %7s' % (date, adv[:28], cls, epr[:32], coef, 'V' if v else 'D', 'FF' if ff else '', '' if p is None else '%+.2f' % p))
print('\n== Solde recalculé (barème FFTT × coefchamp) par épreuve :')
for k, v in tot.items(): print('  %-34s %+.2f' % (k[:34], v))
print('  %-34s %+.2f  → virtuel ≈ %.2f' % ('TOTAL', grand, base + grand))
