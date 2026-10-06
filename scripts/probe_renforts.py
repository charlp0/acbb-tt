#!/usr/bin/env python3
"""Sonde ponctuelle : qui peut renforcer une équipe adverse (règlement II.112).
Lit les feuilles de la phase des équipes plus fortes du club de CIBLE (nom exact de site.json) et sépare les
joueurs encore autorisés à descendre (moins de 2 rencontres plus haut) des brûlés. Lancer via « Sonde API FFTT »."""
import os, json, datetime
import fftt_brulages as B
fb = B.fb
cible = os.environ.get('CIBLE', 'SM MONTROUGE  3')
site = json.load(open('data/site.json'))
t = next(t for v in site['DATA'].values() for t in v['teams'] if fb.nrm(t['name']) == fb.nrm(cible))
n = B.numero(t['name']); genre = 'M'
eqs = sorted((e for e in B.equipes_club(t['club'], genre) if e['n'] < n), key=lambda e: e['n'])
part = {}
for e in eqs:
    fe = B.feuilles_equipe(e, datetime.date.today().isoformat())
    print(f"Équipe {e['n']} — {e['nom']} : {len(fe)} feuille(s)")
    for j, joueurs in sorted(fe):
        print(f"  J{j} : " + ', '.join(f"{p.get('prenom', '')} {p['nom']} ({p.get('cls')})" for p in joueurs))
        for p in joueurs:
            k = (p['nom'] + '|' + (p.get('prenom') or '')).upper()
            r = part.setdefault(k, {'nom': p['nom'], 'prenom': p.get('prenom') or '', 'cls': p.get('cls'), 'j': {}})
            r['j'][j] = min(r['j'].get(j, 99), e['n']); r['cls'] = p.get('cls')
pts = lambda r: r['cls'] if isinstance(r['cls'], int) else 0
ok = sorted((r for r in part.values() if len(r['j']) < 2), key=lambda r: -pts(r))
ko = sorted((r for r in part.values() if len(r['j']) >= 2), key=lambda r: -pts(r))
print(f"\nPEUVENT ENCORE JOUER EN ÉQUIPE {n} ({len(ok)}) :")
for r in ok: print(f"  {r['prenom']} {r['nom']} ({r['cls']}) — " + ', '.join(f"J{j} éq.{x}" for j, x in sorted(r['j'].items())))
print(f"BRÛLÉS POUR L'ÉQUIPE {n} ({len(ko)}) :")
for r in ko: print(f"  {r['prenom']} {r['nom']} ({r['cls']}) — " + ', '.join(f"J{j} éq.{x}" for j, x in sorted(r['j'].items())))
print(f"\nÉquipe {n} actuelle : " + ', '.join(f"{p.get('prenom')} {p['nom']} ({p.get('cls')})" for j in t['journees'][:2] for p in j.get('players', [])[:0]))
