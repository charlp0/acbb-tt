# -*- coding: utf-8 -*-
"""Sonde : parties du critérium fédéral des joueurs ACBB d'un tour, lues dans le flux provisoire
xml_partie.php?numlic= (dispo le soir même). Joueurs et groupes pris dans data/criterium2627.json.
Env : TOUR (défaut 1), DIVS (défaut "D1,D2"), GENRE (défaut M), NIVEAU (défaut D), AGE (défaut ELITE, * = toutes). Lecture seule."""
import os, re, sys, json, time, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
TOUR = os.environ.get('TOUR', '1'); DIVS = set((os.environ.get('DIVS') or 'D1,D2').split(','))
GENRE = os.environ.get('GENRE', 'M'); NIVEAU = os.environ.get('NIVEAU', 'D'); AGE = os.environ.get('AGE', 'ELITE')  # ELITE = seniors ; '*' = toutes catégories

def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
def num(s):
    m = re.search(r'\d+(?:[.,]\d+)?', s or ''); return float(m.group(0).replace(',', '.')) if m else None
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

d = json.load(open('data/criterium2627.json', encoding='utf-8'))
tour = d['tours'][TOUR]
groups = [g for g in tour['groupes'] if g.get('niveau') == NIVEAU and g.get('genre') == GENRE and g.get('div') in DIVS and (AGE == '*' or g.get('age') == AGE)]
print('Tour %s — %d groupe(s) : %s' % (TOUR, len(groups), ', '.join(g['nom'] for g in groups)))
resume = []
for g in groups:
    date = g.get('date', '')
    for p in g['joueurs']:
        if not p.get('acbb') or not p.get('lic'): continue
        lic, base = p['lic'], float(p.get('clt') or 0)
        print('\n== %s %s (%s, n°%s, %s pts) — %s' % (p['nom'], p['pre'], p.get('cat', ''), p.get('pos'), p.get('clt'), g['nom']))
        try:
            r = fb.get('xml_partie.php?numlic=%s' % lic); time.sleep(0.05)
        except Exception as e:
            print('  erreur API :', e); continue
        parts = [b for b in re.findall(r'<partie>(.*?)</partie>', r, re.S) if tg(b, 'date') == date and 'crit' in tg(b, 'epreuve').lower()]
        if not parts:
            print('  aucune partie de critérium datée du %s dans le flux (pas encore remontée, absent ou forfait).' % date); resume.append((p, 0, 0, 0.0, 0)); continue
        parts.sort(key=lambda b: num(tg(b, 'idpartie')) or 0)
        v = dd = 0; solde = 0.0; ff = 0
        for b in parts:
            adv, cls = tg(b, 'nom'), num(tg(b, 'classement'))
            win = (tg(b, 'victoire') or '').upper().startswith('V'); forf = (tg(b, 'forfait') or '0').strip() == '1'
            coef = num(tg(b, 'coefchamp')) or 1.0
            pp = None if (forf or cls is None or not base) else pts(base, cls, win) * coef
            if forf: ff += 1
            elif win: v += 1
            else: dd += 1
            if pp is not None: solde += pp
            print('  %-3s %-30s %5s  %+6s  %s' % ('V' if win else 'D', adv[:30], ('%.0f' % cls) if cls else '?', ('%.2f' % pp) if pp is not None else '—', 'FORFAIT' if forf else ''))
        print('  → %dV-%dD%s, solde %+.2f (×%.1f)' % (v, dd, (' + %d forfait' % ff) if ff else '', solde, coef))
        resume.append((p, v, dd, solde, ff))
print('\n== Résumé')
print('  %-26s %-5s %5s  %-5s %8s' % ('joueur', 'cat', 'pts', 'V-D', 'solde'))
for p, v, dd, solde, ff in sorted(resume, key=lambda x: -x[3]):
    print('  %-26s %-5s %5s  %-5s %+8.2f%s' % ((p['nom'] + ' ' + p['pre'])[:26], p.get('cat', ''), p.get('clt'), '%d-%d' % (v, dd), solde, ' (+%d ff)' % ff if ff else ''))
