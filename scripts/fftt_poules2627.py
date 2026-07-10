# -*- coding: utf-8 -*-
"""
Poules régionales phase 1 2026/2027 avec équipe ACBB.
Source poules : PDF officiel Ligue IDF "2026-2027 - CdF - Poules Phase 1 V.26-07-09"
(saisi manuellement — vérifié 4/4 poules ACBB : R1D p2, R1M p4, R2M p3, R3M p1).
Niveau moyen 25/26 : compos phase 2 archivées (data/archive/2025-2026/phase-2/).
⚠️ Le champ `division` des fichiers d'archive est buggé (toujours "Poule 4") —
   utiliser le dossier + champ `poule`.
Sortie : data/poules2627.json. Usage : python3 scripts/fftt_poules2627.py
"""
import json, re, glob, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def nrm(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().upper()
    s = re.sub(r'\bST\b', 'SAINT', s)
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

DIVLBL = {
    'L08PNDAMES': 'PN Dames', 'L08R1DAMES': 'R1 Dames',
    'L08R2MESSIEURS': 'R2 M', 'L08R3MESSIEURS': 'R3 M',
    'D92D1MESSIEURS': 'D1 (92)', 'D92D2MESSIEURS': 'D2 (92)',
    'D92PREREGIONALEDAMES': 'PR Dames (92)', 'D92PREREGIONALEMESSIEURS': 'PR (92)',
}

# ---- Index des équipes archivées phase 2 : moyenne compos + classement final
idx = {}
for f in glob.glob(os.path.join(ROOT, 'data/archive/2025-2026/phase-2/*/poule-*.json')):
    folder = os.path.basename(os.path.dirname(f))
    d = json.load(open(f))
    genre = 'F' if 'DAMES' in folder else 'M'
    lbl = f"{DIVLBL.get(folder, folder)} p{d['poule']}"
    pts, nm = {}, {}
    for r in d['rencontres']:
        for side, team in (('compo_a', r['equa']), ('compo_b', r['equb'])):
            if not team: continue
            pl = [p['pts'] for p in (r.get(side) or []) if p.get('pts')]
            if pl:
                pts.setdefault(team, []).extend(pl)
                nm[team] = nm.get(team, 0) + 1
    rank = {c['equipe']: int(c['clt']) for c in d['classement']}
    for team, v in pts.items():
        m = re.match(r'^(.*?)\s*\(?(\d+)\)?$', team.strip())
        club, num = (m.group(1), int(m.group(2))) if m else (team, 1)
        rk = rank.get(team)
        # Art. 14 : ACBB 3 finit 1er de R2 p4 (confrontation directe), pas 2e
        if team == 'BOULOGNE BILLANCOURT 3': rk = 1
        idx[(genre, nrm(club), num)] = {
            'avg': round(sum(v) / len(v)), 'nm': nm[team],
            'div': lbl, 'rank': rk, 'src': team,
        }

def find(genre, club, num):
    k = (genre, nrm(club), num)
    if k in idx: return idx[k]
    T = set(nrm(club).split()); best, bs = None, 0.0
    for (g, ak, an), v in idx.items():
        if g != genre or an != num: continue
        A = set(ak.split())
        sc = len(T & A) / max(1, len(T | A))
        if sc > bs: bs, best = sc, v
    return best if best and bs >= 0.5 else None

# ---- Poules ACBB (PDF V.26-07-09) — (pos, nom PDF, n° équipe, dépt)
POULES = [
    dict(division='Régionale 1 Dames', poule=2, acbb='F2', genre='F', pos=7, teams=[
        (1, 'ESP REUILLY', 2, '75'), (2, 'ATT XV', 1, '75'),
        (3, 'IVRY US TT', 1, '94'), (4, 'SAINT MAUR VGA US', 2, '94'),
        (5, 'BRETIGNY CS', 1, '91'), (6, 'PALAISEAU US', 2, '91'),
        (7, 'BOULOGNE BILLANCOURT AC', 2, '92'), (8, 'SQY PING', 2, '78')]),
    dict(division='Régionale 1 Messieurs', poule=4, acbb='M3', genre='M', pos=3, teams=[
        (1, 'COMBS SENART TT', 2, '77'), (2, 'LEVALLOIS SPORT', 6, '92'),
        (3, 'BOULOGNE BILLANCOURT AC', 3, '92'), (4, 'JOSASSIEN TT', 1, '78'),
        (5, 'MEUDON AS', 1, '92'), (6, 'CHATILLON TTM', 2, '92'),
        (7, 'NOISY LE GRAND', 3, '93'), (8, 'BEAUCHAMP CTT', 1, '95')]),
    dict(division='Régionale 2 Messieurs', poule=3, acbb='M4', genre='M', pos=3, teams=[
        (1, 'MENUCOURT', 1, '95'), (2, 'LAGNY SMTT', 1, '77'),
        (3, 'BOULOGNE BILLANCOURT AC', 4, '92'), (4, 'CHESNAY 78 AS', 4, '78'),
        (5, 'THIAIS AS TT', 3, '94'), (6, 'VERSAILLES SCTT', 3, '78'),
        (7, 'MONTMAGNY-GROSLAY', 1, '95'), (8, 'PARIS IX ATT', 2, '75')]),
    dict(division='Régionale 3 Messieurs', poule=1, acbb='M5', genre='M', pos=7, teams=[
        (1, 'COMBS SENART TT', 3, '77'), (2, 'ATT XV', 1, '75'),
        (3, 'VITRY ES', 1, '94'), (4, 'PING PARIS 14', 1, '75'),
        (5, 'ADAMOIS TT', 1, '95'), (6, 'PONTAULT UMS TT', 5, '77'),
        (7, 'BOULOGNE BILLANCOURT AC', 5, '92'), (8, 'STAINS ES-PIERREFITTE AS', 1, '93')]),
]

# Grille des rencontres (identique aux 4 divisions, receveur en premier)
GRID = [
    [(1,8),(2,7),(3,6),(4,5)], [(7,1),(6,2),(5,3),(8,4)],
    [(1,6),(2,5),(3,4),(8,7)], [(5,1),(4,2),(3,8),(6,7)],
    [(1,4),(2,3),(7,5),(8,6)], [(3,1),(2,8),(4,7),(5,6)],
    [(1,2),(7,3),(6,4),(8,5)],
]
DATES = ['19/09/2026', '03/10/2026', '17/10/2026', '07/11/2026',
         '21/11/2026', '05/12/2026', '12/12/2026']

out = {'source': 'Poules Phase 1 V.26-07-09 (Ligue IDF)', 'dates': DATES, 'poules': []}
for P in POULES:
    teams = []
    for pos, club, num, dep in P['teams']:
        hit = find(P['genre'], club, num)
        acbb = club.startswith('BOULOGNE')
        teams.append({'pos': pos, 'name': f'{club} {num}', 'dept': dep, 'acbb': acbb,
                      's25': ({'avg': hit['avg'], 'div': hit['div'], 'rank': hit['rank'],
                               'nm': hit['nm']} if hit else None)})
    cal = []
    for ji, matches in enumerate(GRID):
        for a, b in matches:
            if P['pos'] in (a, b):
                opp = b if a == P['pos'] else a
                cal.append({'j': ji + 1, 'date': DATES[ji], 'opp': opp,
                            'dom': a == P['pos']})
    out['poules'].append({'division': P['division'], 'poule': P['poule'],
                          'acbb': P['acbb'], 'teams': teams, 'cal': cal})

dst = os.path.join(ROOT, 'data/poules2627.json')
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
known = sum(1 for p in out['poules'] for t in p['teams'] if t['s25'])
print(f"OK -> {dst} · {known}/32 équipes avec niveau 25/26")
