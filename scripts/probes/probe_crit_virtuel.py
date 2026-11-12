# -*- coding: utf-8 -*-
"""Sonde (lecture seule) : points officiels, mensuels et « virtuels » recalculés des joueurs d'un groupe du
critérium fédéral, à partir des noms (data/criterium2627.json, tour et groupe en env : TOUR=2, GROUPE=D2 ELITE MESSIEURS,
NUM = rang du groupe portant ce nom, 1 par défaut ; ou NOMS='NOM|Prenom;NOM|Prenom' pour une liste à la main).
Licence retrouvée par xml_liste_joueur (nom + prénom), points via xml_licence_b / xml_joueur, parties de la saison via
xml_partie.php?numlic= ; virtuel = points officiels + Σ barème FFTT × coefchamp. Rien n'est écrit. Sortie entre <<<CRIT_JSON>>> et <<<END>>>."""
import os, re, sys, json, html, importlib.util, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
TOUR = os.environ.get('TOUR', '2'); GROUPE = os.environ.get('GROUPE', 'D2 ELITE MESSIEURS'); NUM = int(os.environ.get('NUM', '1'))
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return html.unescape(m.group(1).strip()) if m else ''
def norm(s): return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()
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

if os.environ.get('NOMS'):
    noms = [tuple(x.split('|')) for x in os.environ['NOMS'].split(';') if '|' in x]
else:
    d = json.load(open('data/criterium2627.json'))
    grs = [g for g in d['tours'][TOUR]['groupes'] if norm(g['nom']) == norm(GROUPE)]
    g = grs[NUM - 1]; print('groupe :', g['nom'], '|', g['salle'], '|', len(g['joueurs']), 'joueurs')
    noms = [(p['nom'], p['pre']) for p in g['joueurs']]

out = []
for nom, pre in noms:
    r = fb.get('xml_liste_joueur.php?nom=%s&prenom=%s' % (norm(nom).replace(' ', '%20'), pre.replace(' ', '%20')))
    cands = [(tg(b, 'licence'), tg(b, 'nom'), tg(b, 'prenom'), tg(b, 'club'), tg(b, 'clast')) for b in re.findall(r'<joueur>(.*?)</joueur>', r, re.S)]
    cands = [c for c in cands if norm(c[1]) == norm(nom) and norm(c[2]) == norm(pre)] or cands
    row = {'nom': nom, 'pre': pre, 'lic': None}
    if not cands: row['erreur'] = 'introuvable'; out.append(row); print('?', nom, pre, 'introuvable'); continue
    lic = cands[0][0]; row['lic'] = lic; row['club'] = cands[0][3]; row['cands'] = len(cands)
    lb = fb.get('xml_licence_b.php?licence=%s' % lic); jo = fb.get('xml_joueur.php?licence=%s' % lic)
    row['officiel'] = num(tg(jo, 'valcla')) or num(tg(lb, 'point')); row['mensuel'] = num(tg(lb, 'pointm')); row['cat'] = tg(lb, 'cat'); row['init'] = num(tg(lb, 'initm')) or num(tg(jo, 'valinit'))
    base = row['officiel'] or 0
    parts = re.findall(r'<partie>(.*?)</partie>', fb.get('xml_partie.php?numlic=%s' % lic), re.S)
    solde = 0.0; v = d_ = 0; crit = []
    for b in parts:
        c = num(tg(b, 'classement')); ff = (tg(b, 'forfait') or '0').strip() == '1'; vic = (tg(b, 'victoire') or '').upper().startswith('V')
        coef = num(tg(b, 'coefchamp')) or 1.0
        if c is None or ff: continue
        solde += pts(base, c, vic) * coef; v += vic; d_ += (not vic)
        if 'crit' in tg(b, 'epreuve').lower(): crit.append(('V' if vic else 'D', int(c)))
    row.update({'parties': len(parts), 'V': v, 'D': d_, 'solde': round(solde, 1), 'virtuel': round(base + solde, 1), 'crit': crit})
    out.append(row); print('%-22s %-12s %s off %s men %s virt %s (%dV/%dD)' % (nom[:22], pre[:12], lic, row['officiel'], row['mensuel'], row['virtuel'], v, d_), flush=True)
print('<<<CRIT_JSON>>>'); print(json.dumps(out, ensure_ascii=False)); print('<<<END>>>')
