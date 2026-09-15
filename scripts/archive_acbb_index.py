#!/usr/bin/env python3
"""Index compact des rencontres de l'ACBB en 2025/26 (phases 1 et 2), dérivé de data/archive/2025-2026.

Sortie : data/archive/2025-2026/acbb-vs.json
  { "maj": "AAAA-MM-JJ", "saison": "2025-2026",
    "rencontres": [ { "phase": 1|2, "div": "D1"|"D2"|"PR"|"PRD"|"PN D"|"R1 D"|"R2"|"R3", "poule": 4,
                      "date": "06/02/2026", "acbb": "M8", "acbb_nom": "BOULOGNE BILLAN 8",
                      "opp": "CLICHY CS 1", "opp_club": "CLICHYCS" (clé normalisée sans numéro),
                      "sa": 18, "sb": 24  (score ACBB puis adversaire),
                      "opp_compo": ["HABERT Patrick 1268", ...] } ] }

Sert à la fiche adversaire de refonte/sportive/poules.html (section « historique contre l'ACBB »).
Le navigateur ne peut pas lister les 339 fichiers de l'archive : cet index est le seul fichier chargé.
Relancer si l'archive change (elle est figée : la saison 2025/26 n'est plus servie par l'API FFTT).
"""
import glob, json, os, re, unicodedata, datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'archive', '2025-2026')
DIV = {
    'D92D1MESSIEURS': 'D1', 'D92D2MESSIEURS': 'D2', 'D92PREREGIONALEMESSIEURS': 'PR', 'D92PREREGIONALEDAMES': 'PR D',
    'L08PNDAMES': 'PN D', 'L08R1DAMES': 'R1 D', 'L08R2MESSIEURS': 'R2', 'L08R3MESSIEURS': 'R3',
}

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()
    return re.sub(r'[^A-Z0-9]', '', s)

def club_key(name):
    """clé club = nom normalisé sans le numéro d'équipe final"""
    return norm(re.sub(r'\s*\d+\s*$', '', name or ''))

def team_num(name):
    m = re.search(r'(\d+)\s*$', name or '')
    return int(m.group(1)) if m else None

def is_acbb(name):
    return 'BOULOGNE' in (name or '').upper()

out = []
for f in sorted(glob.glob(os.path.join(ROOT, 'phase-*', '*', 'poule-*.json'))):
    parts = f.replace('\\', '/').split('/')
    phase = int(parts[-3].split('-')[1]); divkey = parts[-2]
    if divkey not in DIV:
        continue
    genre = 'F' if 'DAMES' in divkey else 'M'
    j = json.load(open(f, encoding='utf-8'))
    for r in j.get('rencontres', []):
        a, b = r.get('equa', ''), r.get('equb', '')
        if is_acbb(a) == is_acbb(b):
            continue  # aucune ou deux équipes ACBB (jamais dans une même poule en 25/26)
        acbb_first = is_acbb(a)
        acbb_nom, opp = (a, b) if acbb_first else (b, a)
        sa, sb = (r.get('scorea'), r.get('scoreb')) if acbb_first else (r.get('scoreb'), r.get('scorea'))
        compo = r.get('compo_b' if acbb_first else 'compo_a') or []
        try:
            sa, sb = int(sa), int(sb)
        except (TypeError, ValueError):
            sa, sb = None, None
        n = team_num(acbb_nom)
        out.append({
            'phase': phase, 'div': DIV[divkey], 'poule': j.get('poule'), 'date': r.get('date'),
            'acbb': (genre + str(n)) if n else None, 'acbb_nom': acbb_nom,
            'opp': opp, 'opp_club': club_key(opp), 'opp_num': team_num(opp),
            'sa': sa, 'sb': sb,
            'opp_compo': [((c.get('nom') or '').strip() + ' ' + str(c.get('pts') or '')).strip() for c in compo],
        })

out.sort(key=lambda x: (x['phase'], x['div'], x['date'] or ''))
dest = os.path.join(ROOT, 'acbb-vs.json')
json.dump({'maj': datetime.date.today().isoformat(), 'saison': '2025-2026', 'source': 'data/archive/2025-2026 (scripts/archive_acbb_index.py)',
           'rencontres': out}, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'rencontres ->', dest)
