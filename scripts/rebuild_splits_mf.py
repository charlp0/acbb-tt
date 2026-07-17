# -*- coding: utf-8 -*-
"""
Reconstruit les 'victoires par équipe' des fiches joueur en FUSIONNANT les
phases 1 et 2 (retour Virginie 17/07/2026), et range les équipes F dans la
vue Féminin (equipe_f) au lieu de la vue Masculin.

Source : feuilles archivées data/archive/2025-2026/phase-*/ (toutes divisions,
Dames et Messieurs). Pour chaque feuille où figure un joueur ACBB, on note
(joueur, date) -> équipe (Fn si dossier DAMES, Mn sinon). On joint ensuite les
matchs de championnat du profil (date + won) pour compter V/T par équipe.

Manches/doubles/5 manches/set serré : non disponibles en phase 1 (détail des
feuilles non archivé) -> restent tels quels (phase 2), libellés côté page.
Usage : python3 scripts/rebuild_splits_mf.py
"""
import json, glob, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def nrm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z]', '', s)

# effectif ACBB (pour corriger les feuilles à orientation inversée — piège equa/equb)
ROSTER = set()
for f in glob.glob(os.path.join(ROOT, 'data/players/*.json')):
    p = json.load(open(f))
    ROSTER.add(nrm((p.get('nom') or '') + (p.get('prenom') or '')))

def roster_score(compo):
    return sum(1 for p in (compo or []) if nrm(p['nom']) in ROSTER)

# (joueur nrm, date) -> équipe ACBB
by_player_date = {}
for f in glob.glob(os.path.join(ROOT, 'data/archive/2025-2026/phase-*/*/poule-*.json')):
    folder = os.path.basename(os.path.dirname(f))
    genre = 'F' if 'DAMES' in folder else 'M'
    d = json.load(open(f))
    for r in d['rencontres']:
        sides = [('compo_a', r['equa']), ('compo_b', r['equb'])]
        acbb = [(sd, t) for sd, t in sides if t and t.upper().startswith('BOULOGNE')]
        if len(acbb) != 1: continue
        side, team = acbb[0]
        other = 'compo_b' if side == 'compo_a' else 'compo_a'
        # la compo ACBB = celle qui contient le plus de noms de l'effectif
        sa, sb = roster_score(r.get(side)), roster_score(r.get(other))
        compo = r.get(side) if sa >= sb else r.get(other)
        m = re.search(r'(\d+)\s*$', team)
        if not m: continue
        tk = genre + m.group(1)
        for p in (compo or []):
            by_player_date[(nrm(p['nom']), r['date'])] = tk

print(f"{len(by_player_date)} apparitions ACBB indexées (ph1+ph2, M+F)")

nsplit = 0
for f in glob.glob(os.path.join(ROOT, 'data/players/*.json')):
    prof = json.load(open(f))
    key = nrm((prof.get('nom') or '') + (prof.get('prenom') or ''))
    comps = prof.get('competitions') or []
    eqs = [c for c in comps if c['key'] in ('equipe', 'equipe_f')]
    if not eqs: continue
    # V/T par équipe, toutes phases, depuis les matchs du joueur
    agg = {}
    for c in eqs:
        for m in c['matches']:
            tk = by_player_date.get((key, m['date']))
            if not tk:  # nom archive "NOM Prenom" parfois abrégé -> tolérance suffixe
                for (k2, d2), v2 in by_player_date.items():
                    if d2 == m['date'] and (k2 in key or key in k2) and len(k2) > 6:
                        tk = v2; break
            if not tk: continue
            a = agg.setdefault(tk, [0, 0])
            a[1] += 1
            if m['won']: a[0] += 1
    if not agg: continue
    msp = [{'team': k, 'w': v[0], 't': v[1]} for k, v in sorted(agg.items()) if k[0] == 'M']
    fsp = [{'team': k, 'w': v[0], 't': v[1]} for k, v in sorted(agg.items()) if k[0] == 'F']
    ch = False
    for c in eqs:
        est_f = c['key'] == 'equipe_f' or 'Féminin' in (c.get('label') or '')
        sp = fsp if est_f else msp
        if sp:
            c.setdefault('detail', {})['splits'] = sp
            ch = True
        elif 'detail' in c and c['detail'].get('splits'):
            del c['detail']['splits']
            if not c['detail']: del c['detail']
            ch = True
    if ch:
        json.dump(prof, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
        nsplit += 1

print(f"OK — splits toutes-phases réécrits sur {nsplit} fiches (M et F séparés)")
