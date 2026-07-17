# -*- coding: utf-8 -*-
"""
Poules régionales phase 1 2026/2027 avec équipe ACBB.
Sources poules :
- PDF Ligue IDF "2026-2027 - CdF - Poules Phase 1 V.26-07-10" (poules regionales)
- PDF CD92 "POULES CHPT EQUIPES PHASE 1_26_27_v 13 07 2026" (departemental,
  attribution verifiee par coordonnees pdfplumber : F3=PRD p2, M7=PR p3,
  M6=PR p4, M10/M11/M8/M9=D1 p1-4, M15/M17/M12/M13/M16/M14=D2 p1-6)
(V.26-07-10 : en R3M p1, VINCENNOIS TT 2 remplace ADAMOIS TT 1 — seul changement ACBB vs V.26-07-09)
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
    s = re.sub(r'\bT T\b', 'TT', s)
    s = re.sub(r'\bE P\b', 'EP', s)
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
    # ---- National (sources : captures Cyril 16/07 + PDF calendrier Pro B)
    dict(division='Pro B Messieurs', poule=None, acbb='M1', genre='M', pos=None, teams=[
        (1, 'LILLE METROPOLE TT', '', '59'), (2, 'PROVILLE ASL', '', '59'),
        (3, 'CAEN TTC', '', '14'), (4, 'PONTOISE-CERGY AS', '', '95'),
        (5, 'AMIENS STT', '', '80'), (6, 'FREJUS ASML', '', '83'),
        (7, 'COURBEVOIE SPORT TT', '', '92'), (8, 'LE HAVRE ATT', '', '76'),
        (9, 'BOULOGNE-BILLANCOURT AC', '', '92'), (10, 'PAYS COMPIEGNOIS TT', '', '60'),
        (11, 'NANTES TT', '', '44'), (12, 'MIRAMAS AS TT', '', '13')],
       # grille 12 équipes (ACBB=9), aller J1-J11 sept->dec, dates FFTT variables (mar/ven/dim)
       fixtures=[(1,'sept.','PONTOISE-CERGY AS',False),(2,'sept.','CAEN TTC',True),
                 (3,'oct.','PROVILLE ASL',False),(4,'oct.','LILLE METROPOLE TT',True),
                 (5,'nov.','NANTES TT',False),(6,'nov.','PAYS COMPIEGNOIS TT',True),
                 (7,'nov.','MIRAMAS AS TT',False),(8,'nov.','LE HAVRE ATT',False),
                 (9,'dec.','COURBEVOIE SPORT TT',True),(10,'dec.','FREJUS ASML',False),
                 (11,'dec.','AMIENS STT',True)]),
    dict(division='Nationale 1 Messieurs', poule=2, acbb='M2', genre='M', pos=3, teams=[
        (1, 'NICE CAVIGAL', 1, '06'), (2, 'DOUAI TT', 1, '59'),
        (3, 'BOULOGNE BILLANCOURT AC', 2, '92'), (4, 'ISTRES TT', 1, '13'),
        (5, 'BORDEAUX CAM', 1, '33'), (6, 'SAINT QUENTIN TT', 1, '02'),
        (7, '4S TOURS', 2, '37'), (8, 'AVION TT', 1, '62')]),
    dict(division='Nationale 2 Dames', poule=3, acbb='F1', genre='F', pos=7, teams=[
        (1, 'MAIZIERES LES METZ', 2, '57'), (2, 'AL GRAND QUEVILLY / GRAVIGNY TT', 2, '76'),
        (3, 'AC PLERIN', 1, '22'), (4, 'SAINT MAUR VGA', 1, '94'),
        (5, 'VALENCIENNES USTT', 1, '59'), (6, 'BOIS-GUILLAUME / HONGUEMAR-LANDIN', 1, '76'),
        (7, 'BOULOGNE BILLANCOURT AC / MARLY', 1, '92'), (8, 'LILLE METROPOLE TT', 1, '59')]),
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
        (5, 'VINCENNOIS TT', 2, '94'), (6, 'PONTAULT UMS TT', 5, '77'),
        (7, 'BOULOGNE BILLANCOURT AC', 5, '92'), (8, 'STAINS ES-PIERREFITTE AS', 1, '93')]),
    # ---- Départemental 92 (PDF CD92 v13/07/2026) — dép='92' partout
    dict(division='Pré-Régionale Dames (92)', poule=2, acbb='F3', genre='F', pos=7, cal='sam', teams=[
        (1, 'CSM CLAMART', 1, '92'), (2, 'RUEIL ATHLETIC', 3, '92'),
        (3, 'TTMC CHATILLON', 2, '92'), (4, 'COURBEVOIE STT', 5, '92'),
        (5, 'ES NANTERRE', 1, '92'), (7, 'BOULOGNE BILLAN', 3, '92'),
        (8, 'SCEAUX TT', 1, '92')]),
    dict(division='Pré-Régionale Messieurs (92)', poule=3, acbb='M7', genre='M', pos=5, teams=[
        (1, 'BOIS COLOMBES S', 5, '92'), (2, 'CLAMART CSM', 4, '92'),
        (3, 'TTMC CHATILLON', 5, '92'), (4, 'CS CLICHY TT', 1, '92'),
        (5, 'BOULOGNE BILLAN', 7, '92'), (6, 'LEVALLOIS SPORT', 11, '92'),
        (7, 'NEUILLY ASPN', 5, '92'), (8, 'ISSEENNE E P', 4, '92')]),
    dict(division='Pré-Régionale Messieurs (92)', poule=4, acbb='M6', genre='M', pos=1, teams=[
        (1, 'BOULOGNE BILLAN', 6, '92'), (2, 'ASNIERES TT', 4, '92'),
        (3, 'TTMC CHATILLON', 6, '92'), (4, 'COURBEVOIE STT', 9, '92'),
        (5, 'SM MONTROUGE', 1, '92'), (6, 'USM MALAKOFF', 4, '92'),
        (7, 'RUEIL ATHLETIC', 6, '92'), (8, 'SCEAUX TT', 2, '92')]),
    dict(division='D1 Messieurs (92)', poule=1, acbb='M10', genre='M', pos=6, teams=[
        (1, 'MEUDON AS', 4, '92'), (2, 'PLESSIS ROBINS.', 4, '92'),
        (3, 'TTMC CHATILLON', 8, '92'), (4, 'NANTERRE ES', 2, '92'),
        (5, 'SM MONTROUGE', 2, '92'), (6, 'BOULOGNE BILLAN', 10, '92'),
        (7, 'STADE DE VANVES', 1, '92'), (8, 'ISSEENNE E P', 7, '92')]),
    dict(division='D1 Messieurs (92)', poule=2, acbb='M11', genre='M', pos=7, teams=[
        (1, 'PUTEAUX TT CSM', 3, '92'), (2, 'ASNIERES TT', 5, '92'),
        (3, 'RUEIL ATHLETIC', 11, '92'), (4, 'ISSEENNE E P', 6, '92'),
        (5, 'MEUDON AS', 3, '92'), (6, 'PLESSIS ROBINS.', 3, '92'),
        (7, 'BOULOGNE BILLAN', 11, '92'), (8, 'BOURG LA REINE', 2, '92')]),
    dict(division='D1 Messieurs (92)', poule=3, acbb='M8', genre='M', pos=5, teams=[
        (1, 'BOIS COLOMBES S', 7, '92'), (2, 'PLESSIS ROBINS.', 2, '92'),
        (3, 'AS FONTENAY TT', 1, '92'), (4, 'CHATENAY ASVTT', 4, '92'),
        (5, 'BOULOGNE BILLAN', 8, '92'), (6, 'LEVALLOIS SPORT', 13, '92'),
        (7, 'RUEIL ATHLETIC', 10, '92'), (8, 'SCEAUX TT', 3, '92')]),
    dict(division='D1 Messieurs (92)', poule=4, acbb='M9', genre='M', pos=2, teams=[
        (1, 'BOIS COLOMBES S', 6, '92'), (2, 'BOULOGNE BILLAN', 9, '92'),
        (3, 'TTMC CHATILLON', 7, '92'), (4, 'CHATENAY ASVTT', 5, '92'),
        (5, 'SM MONTROUGE', 3, '92'), (6, 'LEVALLOIS SPORT', 14, '92'),
        (7, 'RUEIL ATHLETIC', 8, '92'), (8, 'NANTERRE ES', 3, '92')]),
    dict(division='D2 Messieurs (92)', poule=1, acbb='M15', genre='M', pos=1, teams=[
        (1, 'BOULOGNE BILLAN', 15, '92'), (2, 'USM MALAKOFF', 6, '92'),
        (3, 'RUEIL ATHLETIC', 13, '92'), (4, 'COURBEVOIE STT', 13, '92'),
        (5, 'ANTONY SPORT TT', 5, '92'), (6, 'PLESSIS ROBINS.', 5, '92'),
        (7, 'NEUILLY ASPN', 11, '92')]),
    dict(division='D2 Messieurs (92)', poule=2, acbb='M17', genre='M', pos=2, teams=[
        (1, 'MEUDON AS', 6, '92'), (2, 'BOULOGNE BILLAN', 17, '92'),
        (3, 'COLOMBIENNE ES', 4, '92'), (4, 'COURBEVOIE STT', 15, '92'),
        (5, 'BOIS COLOMBES S', 8, '92'), (6, 'CLAMART CSM', 8, '92'),
        (7, 'RUEIL ATHLETIC', 16, '92')]),
    dict(division='D2 Messieurs (92)', poule=3, acbb='M12', genre='M', pos=3, teams=[
        (1, 'ANTONY SPORT TT', 6, '92'), (2, 'VILLENEUVE LA G', 1, '92'),
        (3, 'BOULOGNE BILLAN', 12, '92'), (4, 'BOURG LA REINE', 3, '92'),
        (5, 'ASNIERES TT', 9, '92'), (6, 'PLESSIS ROBINS.', 7, '92'),
        (7, 'STADE DE VANVES', 2, '92')]),
    dict(division='D2 Messieurs (92)', poule=4, acbb='M13', genre='M', pos=6, teams=[
        (1, 'SM MONTROUGE', 4, '92'), (2, 'USM MALAKOFF', 5, '92'),
        (3, 'VOLTIGEURS', 5, '92'), (4, 'CS CLICHY TT', 5, '92'),
        (5, 'BOIS COLOMBES S', 10, '92'), (6, 'BOULOGNE BILLAN', 13, '92'),
        (7, 'AS FONTENAY TT', 3, '92')]),
    dict(division='D2 Messieurs (92)', poule=5, acbb='M16', genre='M', pos=3, teams=[
        (1, 'ANTONY SPORT TT', 8, '92'), (2, 'LEVALLOIS SPORT', 16, '92'),
        (3, 'BOULOGNE BILLAN', 16, '92'), (4, 'CHATENAY ASVTT', 6, '92'),
        (5, 'PUTEAUX TT CSM', 5, '92'), (6, 'CLAMART CSM', 7, '92'),
        (7, 'LA GARENNE COLO', 4, '92')]),
    dict(division='D2 Messieurs (92)', poule=6, acbb='M14', genre='M', pos=3, teams=[
        (1, 'ASNIERES TT', 10, '92'), (2, 'VILLENEUVE LA G', 2, '92'),
        (3, 'BOULOGNE BILLAN', 14, '92'), (4, 'COURBEVOIE STT', 14, '92'),
        (5, 'PUTEAUX TT CSM', 4, '92'), (6, 'VOLTIGEURS', 2, '92'),
        (7, 'RUEIL ATHLETIC', 14, '92')]),
]

# Grille des rencontres (identique aux 4 divisions, receveur en premier)
GRID = [
    [(1,8),(2,7),(3,6),(4,5)], [(7,1),(6,2),(5,3),(8,4)],
    [(1,6),(2,5),(3,4),(8,7)], [(5,1),(4,2),(3,8),(6,7)],
    [(1,4),(2,3),(7,5),(8,6)], [(3,1),(2,8),(4,7),(5,6)],
    [(1,2),(7,3),(6,4),(8,5)],
]
DATES = ['19/09/2026', '03/10/2026', '17/10/2026', '07/11/2026',
         '21/11/2026', '05/12/2026', '12/12/2026']          # samedis (régional + dames)
DATES_VEN = ['18/09/2026', '02/10/2026', '16/10/2026', '06/11/2026',
             '20/11/2026', '04/12/2026', '11/12/2026']      # vendredis (départemental M)

out = {'source': 'Ligue IDF V.26-07-10 + CD92 v13/07/2026', 'dates': DATES, 'poules': []}
for P in POULES:
    dept92 = '(92)' in P['division']
    dates = DATES if (not dept92 or P.get('cal') == 'sam') else DATES_VEN
    teams = []
    for pos, club, num, dep in P['teams']:
        hit = find(P['genre'], club, num)
        acbb = club.startswith('BOULOGNE')
        teams.append({'pos': pos, 'name': (f'{club} {num}' if num != '' else club), 'dept': dep, 'acbb': acbb,
                      's25': ({'avg': hit['avg'], 'div': hit['div'], 'rank': hit['rank'],
                               'nm': hit['nm']} if hit else None)})
    filled = {t['pos'] for t in teams}
    cal = []
    if P.get('fixtures'):
        for j, dl, opp_name, dom in P['fixtures']:
            cal.append({'j': j, 'date': dl, 'oppName': opp_name, 'dom': dom})
    elif P['pos'] is not None:
        for ji, matches in enumerate(GRID):
            for a, b in matches:
                if P['pos'] in (a, b):
                    opp = b if a == P['pos'] else a
                    cal.append({'j': ji + 1, 'date': dates[ji], 'opp': opp,
                                'dom': a == P['pos'], 'exempt': opp not in filled})
    out['poules'].append({'division': P['division'], 'poule': P['poule'],
                          'acbb': P['acbb'], 'teams': teams, 'cal': cal})

dst = os.path.join(ROOT, 'data/poules2627.json')
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
known = sum(1 for p in out['poules'] for t in p['teams'] if t['s25'])
tot = sum(len(p['teams']) for p in out['poules'])
print(f"OK -> {dst} · {known}/{tot} équipes avec niveau 25/26 · {len(out['poules'])} poules")
