"""Fin de phase : projection des 3 dernières journées de chaque poule à partir des feuilles FFTT (data/site.json).

Deux estimateurs, affichés séparément puis combinés à parts égales (décision Charles, 08/11/2026) :
  A. Confrontations directes et transitivité : un rating par équipe (Bradley-Terry sur les parties gagnées,
     pondéré par l'écart de score). Une rencontre jouée avec un alignement très différent de l'habitude
     (renfort ponctuel, équipe incomplète) pèse moins : la transitivité ne vaut qu'à effectif comparable.
  B. Modèle joueur : probabilité de gagner une partie selon l'écart de points, courbe logistique calibrée sur
     toutes les parties de la saison (toutes poules), corrigée d'une « forme » individuelle (victoires
     observées vs attendues, fortement rétrécie). L'alignement d'une rencontre à venir est tiré parmi les
     alignements déjà vus de l'équipe.
Le classement final est simulé 10 000 fois (points 3/2/1, départage art. 14 : mini-championnat entre ex æquo,
puis parties). Sortie : data/fin_de_phase.json, lu par sportive/fin-de-phase.html (qui rejoue les mêmes
calculs en JS pour les scénarios de renfort — shared/fin-de-phase.js doit rester l'exact pendant de ce fichier).
"""
import datetime
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'data/site.json'
OUT = ROOT / 'data/fin_de_phase.json'
NSIM = 10000
PTS = {'V': 3, 'N': 2, 'D': 1}
# Ordre des simples en formule 4 joueurs (règlement IDF art. 2 : AW BX CY DZ AX BW DY CZ · doubles · AY CW DX BZ).
SINGLES = [(0, 0), (1, 1), (2, 2), (3, 3), (0, 1), (1, 0), (3, 2), (2, 3), (0, 2), (2, 0), (3, 1), (1, 3)]
# Équipes gérées : tout sauf la Pro B (M1, hors site).
EXCLUS = {'M1'}

# Quotas de montée/descente par division, phase 1 2026/27. `down` = places condamnées, `risk` = place suivante
# dont une fraction `frac` descend (dépend des descentes de la division supérieure ; règlement IDF art. 17 :
# « les descentes sont fonction des descentes des divisions supérieures », aucun dernier ne se maintient).
# PR/D1/D2 : schéma de la réforme CD92 phase 2 (Xavier C., 05/09/2026) ; en D2 aucune montée en D1 en phase 2.
QUOTAS = [
    ('FED_Nationale 1', {'code': 'N1', 'up': 4, 'upLabel': 'N1A', 'down': 2, 'risk': 0, 'frac': 0.0, 'note': 'Nationale 1 : les 4 premiers de poule jouent en N1A en phase 2 (Charles, 08/11/2026), les autres en N1B ; 7ᵉ et 8ᵉ descendent (à confirmer).'}),
    ('FED_Nationale 2', {'code': 'N2', 'up': 1, 'down': 2, 'risk': 0, 'frac': 0.0, 'note': 'Nationale 2 : 1ʳᵉ de poule qualifiée, 7ᵉ et 8ᵉ descendent (à confirmer sur le règlement fédéral).'}),
    ('L08_R1', {'code': 'R1', 'up': 1, 'down': 1, 'risk': 1, 'frac': 0.5, 'note': 'Régionale (Ligue IDF) : le 1ᵉʳ monte, le 8ᵉ descend ; le 7ᵉ descend selon les descentes de la division supérieure (≈ 1 sur 2).'}),
    ('L08_R2', {'code': 'R2', 'up': 1, 'down': 1, 'risk': 1, 'frac': 0.5, 'note': 'Régionale (Ligue IDF) : le 1ᵉʳ monte, le 8ᵉ descend ; le 7ᵉ descend selon les descentes de la division supérieure (≈ 1 sur 2).'}),
    ('L08_R3', {'code': 'R3', 'up': 1, 'down': 1, 'risk': 1, 'frac': 0.5, 'note': 'Régionale (Ligue IDF) : le 1ᵉʳ monte, le 8ᵉ descend ; le 7ᵉ descend selon les descentes de la division supérieure (≈ 1 sur 2).'}),
    ('D92_Pre-Regionale Dames', {'code': 'PRD', 'up': 1, 'down': 4, 'risk': 0, 'frac': 0.0, 'note': 'PR Dames 92 (avenant du 14/09/2026) : barrage pour la montée, les 4 dernières de chaque poule descendent en D1 féminine.'}),
    ('D92_Pré-Regionale', {'code': 'PR', 'up': 1, 'down': 4, 'risk': 0, 'frac': 0.0, 'note': 'PR 92, réforme phase 2 (PR 4 → 3 poules) : le 1ᵉʳ monte en R3, les 4 derniers descendent en D1 (Cyril et Minh, 08/11/2026 : « 3 à 4 descentes selon les descentes de régionale », on retient 4).'}),
    ('D92_D1', {'code': 'D1', 'up': 1, 'down': 2, 'risk': 1, 'frac': 0.67, 'note': 'D1 92, réforme phase 2 (6 → 5 poules) : le 1ᵉʳ monte en PR, 7ᵉ et 8ᵉ descendent en D2, quatre 6ᵉ sur six aussi.'}),
    ('D92_D2', {'code': 'D2', 'up': 0, 'down': 4, 'risk': 1, 'frac': 0.33, 'note': 'D2 92, réforme phase 2 (création de la D3) : aucune montée en D1 ; 1ᵉʳ et 2ᵉ maintenus, 8 des 12 3ᵉ aussi, 4ᵉ à 7ᵉ descendent en D3.'}),
]
# Objectifs fixés par la sportive (Charles, 08/11/2026 : M3 et M9 maintien ajoutés le soir même) ; les autres équipes : auto (montée si 1ʳᵉ ou 2ᵉ et montée possible).
OBJECTIFS = {'M2': 'montee', 'M3': 'maintien', 'M4': 'maintien', 'M6': 'maintien', 'M9': 'maintien', 'M5': 'montee', 'M7': 'montee'}  # M2 : « montée » = top 4 → N1A


def sigmoid(d, s):
    """Probabilité de gagner une partie avec `d` points d'écart ; `s` = écart valant 10 contre 1."""
    return 1.0 / (1.0 + 10 ** (-d / s))


def quotas_for(pool_name):
    for prefix, q in QUOTAS:
        if pool_name.startswith(prefix):
            return q
    return {'code': '?', 'up': 1, 'down': 2, 'risk': 0, 'frac': 0.0, 'note': 'Division inconnue : 1 montée, 2 descentes par défaut.'}


def reels(players, row=None):
    """Joueurs réellement alignés. Sans parties jouées sur la feuille (championnats nationaux : la FFTT ne
    publie que le score), les victoires individuelles valent 0 par défaut et ne sont pas des observations."""
    indiv = bool(row is None or row.get('played_games'))
    return [dict(p, vic=(p.get('vic') if indiv else None)) for p in (players or [])
            if p.get('nom') and p['nom'] != 'Joueur absent' and isinstance(p.get('cls'), (int, float))]


def parties_from_sheets(ja, jb):
    """Parties gagnées (a, b) d'une rencontre à partir des deux feuilles. Les victoires individuelles font foi
    (elles incluent les simples gagnés par forfait) ; sinon, le score publié s'il est déjà en parties."""
    def side(j):
        if j and j.get('played_games') and j.get('players') and any(p.get('vic') is not None for p in j['players']):
            return sum(int(p.get('vic') or 0) for p in j['players']) + int(j.get('doubles') or 0)
        return None
    wa, wb = side(ja), side(jb)
    if wa is not None and wb is not None and wa + wb <= 14:
        return wa, wb
    j = ja or jb
    A, B = j.get('match_score'), j.get('opp_score')
    if A is None or B is None:
        return None
    A, B = int(A), int(B)
    if j is jb:
        A, B = B, A
    if A + B == 42 and A >= 14 and B >= 14:
        return A - 14, B - 14
    return A, B


def result(wa, wb):
    return 'V' if wa > wb else 'D' if wa < wb else 'N'


def build_pool(key, pool, standings):
    """Rencontres jouées (scores en parties, alignements) et à venir d'une poule."""
    teams = [t['name'] for t in pool['teams']]
    rows = {t['name']: {j['journee']: j for j in t['journees']} for t in pool['teams']}
    played, remaining, seen = [], [], set()
    for t in pool['teams']:
        for j in t['journees']:
            a, b, jj = t['name'], j.get('opponent'), int(j['journee'])
            if not b or b not in rows:
                continue
            k = (jj, frozenset([a, b]))
            if k in seen:
                continue
            seen.add(k)
            jb = rows[b].get(jj)
            if j.get('players') and jb and jb.get('players'):
                pr = parties_from_sheets(j, jb)
                if pr is None:
                    continue
                played.append({'j': jj, 'a': a, 'b': b, 'wa': pr[0], 'wb': pr[1], 'la': reels(j['players'], j), 'lb': reels(jb['players'], jb)})
            elif j.get('match_score') is None:
                remaining.append({'j': jj, 'a': a, 'b': b})
    played.sort(key=lambda m: m['j'])
    remaining.sort(key=lambda m: m['j'])
    acbb = next((t['name'] for t in pool['teams'] if t.get('acbb')), None)
    # Lieu : connu pour l'équipe ACBB (calendrier FFTT « Dom »/« Ext » de site.json), inconnu entre deux adversaires.
    cal = next((t.get('calendar') or {} for t in pool['teams'] if t.get('acbb')), {})
    for m in remaining:
        c = cal.get(str(m['j'])) or {}
        if acbb in (m['a'], m['b']) and c.get('domext') in ('Dom', 'Ext'):
            other = m['b'] if m['a'] == acbb else m['a']
            m['home'] = acbb if c['domext'] == 'Dom' else other
        else:
            m['home'] = None
    return {'key': key, 'pool': pool['pool'], 'level': pool.get('level'), 'teams': teams, 'acbb': acbb,
            'played': played, 'remaining': remaining, 'standings': standings or []}


def calibrate(pools):
    """Écart de points valant 10 contre 1, par maximum de vraisemblance sur toutes les parties de simple."""
    obs = []
    for P in pools.values():
        for m in P['played']:
            for mine, theirs in ((m['la'], m['lb']), (m['lb'], m['la'])):
                if len(mine) != 4 or len(theirs) < 3:
                    continue
                avg = sum(p['cls'] for p in theirs) / len(theirs)
                for p in mine:
                    if p.get('vic') is not None:
                        obs.append((p['cls'] - avg, int(p['vic']), 3))
    if not obs:
        return 475.0, 0
    def ll(s):
        tot = 0.0
        for d, v, n in obs:
            p = min(max(sigmoid(d, s), 1e-4), 1 - 1e-4)
            tot += v * math.log(p) + (n - v) * math.log(1 - p)
        return tot
    best = max((ll(s), s) for s in range(200, 901, 5))
    return float(best[1]), len(obs) * 3


def fit_ratings(P, s):
    """Modèle A : rating par équipe (points) par maximum a posteriori sur les parties gagnées.
    Poids d'une rencontre : 0,5 par partie (les 14 parties d'une rencontre ne sont pas indépendantes),
    réduit quand un alignement s'écarte de la moyenne habituelle de l'équipe (renfort ponctuel ou équipe réduite)."""
    teams = P['teams']
    usual = {}
    for t in teams:
        avgs = [sum(p['cls'] for p in (m['la'] if m['a'] == t else m['lb'])) / len(m['la'] if m['a'] == t else m['lb'])
                for m in P['played'] if t in (m['a'], m['b']) and len(m['la'] if m['a'] == t else m['lb'])]
        usual[t] = sorted(avgs)[len(avgs) // 2] if avgs else None
    obs = []
    for m in P['played']:
        w = 0.5
        for t, lineup in ((m['a'], m['la']), (m['b'], m['lb'])):
            if lineup and usual[t] is not None:
                dev = abs(sum(p['cls'] for p in lineup) / len(lineup) - usual[t])
                w *= 1.0 if dev <= 60 else max(0.3, math.exp(-(dev - 60) / 150))
            if len(lineup) == 3:
                w *= 0.7
        obs.append((m['a'], m['b'], m['wa'], m['wb'], w))
    r = {t: 0.0 for t in teams}
    k = math.log(10) / s
    prior = 1.0 / (250.0 ** 2)  # a priori N(0, 250 pts)
    lr = 2000.0
    for _ in range(400):
        g = {t: -prior * r[t] for t in teams}
        for a, b, wa, wb, w in obs:
            p = sigmoid(r[a] - r[b], s)
            grad = w * k * ((wa + wb) * (wa / (wa + wb) - p)) if wa + wb else 0.0
            g[a] += grad
            g[b] -= grad
        for t in teams:
            r[t] += lr * g[t]
        mean = sum(r.values()) / len(r)
        for t in teams:
            r[t] -= mean
    return {t: round(v, 1) for t, v in r.items()}, obs


def player_form(pools, s):
    """Modèle B : « forme » par joueur (nom|prénom|club) = écart entre victoires observées et attendues,
    converti en points et rétréci (a priori ± 100 pts). Sans parties individuelles (nationaux) : 0."""
    acc = defaultdict(lambda: [0.0, 0.0, 0, 0])  # résidu, information, parties, victoires
    k = math.log(10) / s
    for P in pools.values():
        for m in P['played']:
            for mine, theirs, club in ((m['la'], m['lb'], m['a']), (m['lb'], m['la'], m['b'])):
                if len(theirs) < 3:
                    continue
                avg = sum(p['cls'] for p in theirs) / len(theirs)
                for p in mine:
                    if p.get('vic') is None or len(mine) != 4:
                        continue
                    pw = sigmoid(p['cls'] - avg, s)
                    a = acc[(p['nom'], p.get('prenom', ''), club)]
                    a[0] += int(p['vic']) - 3 * pw
                    a[1] += 3 * pw * (1 - pw)
                    a[2] += 3
                    a[3] += int(p['vic'])
    tau = 100.0 * k  # écart-type a priori en logit
    form = {}
    for key, (res, info, n, v) in acc.items():
        d_logit = res / (info + 1.0 / tau ** 2) if info else 0.0
        form[key] = {'adj': round(max(-150.0, min(150.0, d_logit / k))), 'parties': n, 'vic': v}
    return form


def lineups_of(P, team, form):
    out = []
    for m in P['played']:
        lineup = m['la'] if m['a'] == team else m['lb'] if m['b'] == team else None
        if not lineup:
            continue
        out.append([{'nom': p['nom'], 'pre': p.get('prenom', ''), 'cls': p['cls'],
                     'adj': form.get((p['nom'], p.get('prenom', ''), team), {}).get('adj', 0),
                     'parties': form.get((p['nom'], p.get('prenom', ''), team), {}).get('parties', 0),
                     'vic': form.get((p['nom'], p.get('prenom', ''), team), {}).get('vic', 0)} for p in lineup])
    return out


def expected_singles(la, lb, s):
    """Espérance de simples gagnés par A (déterministe, sert de contrôle Python ↔ JS)."""
    sa = [p['cls'] + p.get('adj', 0) for p in la]
    sb = [p['cls'] + p.get('adj', 0) for p in lb]
    tot = 0.0
    for i, j in SINGLES:
        if i >= len(sa):
            continue
        if j >= len(sb):
            tot += 1.0
            continue
        tot += sigmoid(sa[i] - sb[j], s)
    return tot


def sim_match_b(la, lb, s, rnd):
    sa = [p['cls'] + p.get('adj', 0) for p in la]
    sb = [p['cls'] + p.get('adj', 0) for p in lb]
    wa = wb = 0
    for i, j in SINGLES:
        if i >= len(sa) and j >= len(sb):
            continue
        if i >= len(sa):
            wb += 1
            continue
        if j >= len(sb):
            wa += 1
            continue
        if rnd.random() < sigmoid(sa[i] - sb[j], s):
            wa += 1
        else:
            wb += 1
    ma, mb = sum(sa) / len(sa), sum(sb) / len(sb)
    pd = sigmoid(ma - mb, s)
    for d in range(2):
        if d == 1 and (len(sa) < 4 or len(sb) < 4):
            if len(sa) < 4 and len(sb) < 4:
                continue
            if len(sa) < 4:
                wb += 1
            else:
                wa += 1
            continue
        if rnd.random() < pd:
            wa += 1
        else:
            wb += 1
    return wa, wb


def sim_match_a(ra, rb, s, rnd):
    p = sigmoid(ra - rb, s)
    wa = sum(1 for _ in range(14) if rnd.random() < p)
    return wa, 14 - wa


def rank_teams(teams, pts, mini, diff):
    """Classement art. 14 : points, puis points dans les rencontres entre ex æquo, puis parties (écart) dans
    ces rencontres, puis écart de parties total. `mini[a][b]` = (points, écart de parties) de a contre b."""
    def key_group(group):
        if len(group) == 1:
            return [group]
        sub_pts = {t: sum(mini[t][u][0] for u in group if u != t and u in mini[t]) for t in group}
        sub_diff = {t: sum(mini[t][u][1] for u in group if u != t and u in mini[t]) for t in group}
        ordered = sorted(group, key=lambda t: (-sub_pts[t], -sub_diff[t], -diff[t], t))
        out, cur = [], [ordered[0]]
        for t in ordered[1:]:
            u = cur[0]
            if (sub_pts[t], sub_diff[t], diff[t]) == (sub_pts[u], sub_diff[u], diff[u]):
                cur.append(t)
            else:
                out.append(cur)
                cur = [t]
        out.append(cur)
        return out
    order = sorted(teams, key=lambda t: -pts[t])
    ranking = []
    i = 0
    while i < len(order):
        group = [order[i]]
        while i + len(group) < len(order) and pts[order[i + len(group)]] == pts[order[i]]:
            group.append(order[i + len(group)])
        for sub in key_group(group):
            ranking.extend(sub)
        i += len(group)
    return ranking


def simulate(P, ratings, lineups, s, objectif_team, quota, rnd, nsim=NSIM, mix=0.5, overrides=None):
    """Classement final simulé. `overrides[(j, team)]` = alignement imposé (scénario de renfort)."""
    teams = P['teams']
    base_pts = {t: 0 for t in teams}
    base_diff = {t: 0 for t in teams}
    base_mini = {t: {} for t in teams}
    for m in P['played']:
        ra, rb = result(m['wa'], m['wb']), result(m['wb'], m['wa'])
        base_pts[m['a']] += PTS[ra]
        base_pts[m['b']] += PTS[rb]
        base_diff[m['a']] += m['wa'] - m['wb']
        base_diff[m['b']] += m['wb'] - m['wa']
        base_mini[m['a']][m['b']] = (PTS[ra], m['wa'] - m['wb'])
        base_mini[m['b']][m['a']] = (PTS[rb], m['wb'] - m['wa'])
    # Points officiels FFTT si disponibles (forfaits, pénalités) : ils priment sur le recomptage.
    official = {row['name']: row for row in P['standings']}
    for t in teams:
        if t in official and official[t].get('pts') is not None:
            base_pts[t] = int(official[t]['pts'])
    n = len(teams)
    rank_count = {t: [0] * n for t in teams}
    match_out = [{'V': 0, 'N': 0, 'D': 0, 'A': {'V': 0, 'N': 0, 'D': 0}, 'B': {'V': 0, 'N': 0, 'D': 0}} for _ in P['remaining']]
    # Impact : objectif atteint selon le résultat (vu de l'équipe `a`) de chaque rencontre restante.
    cond = [{'V': [0, 0], 'N': [0, 0], 'D': [0, 0]} for _ in P['remaining']]
    goal_hits = 0
    for _ in range(nsim):
        pts = dict(base_pts)
        diff = dict(base_diff)
        mini = {t: dict(base_mini[t]) for t in teams}
        results = []
        for idx, m in enumerate(P['remaining']):
            use_a = rnd.random() < mix
            la = (overrides or {}).get((m['j'], m['a'])) or rnd.choice(lineups[m['a']]) if lineups[m['a']] else None
            lb = (overrides or {}).get((m['j'], m['b'])) or rnd.choice(lineups[m['b']]) if lineups[m['b']] else None
            if use_a or la is None or lb is None:
                ra_ = ratings[m['a']] + (lineup_shift(la, lineups[m['a']]) if la else 0)
                rb_ = ratings[m['b']] + (lineup_shift(lb, lineups[m['b']]) if lb else 0)
                wa, wb = sim_match_a(ra_, rb_, s, rnd)
                model = 'A'
            else:
                wa, wb = sim_match_b(la, lb, s, rnd)
                model = 'B'
            ra, rb = result(wa, wb), result(wb, wa)
            match_out[idx][ra] += 1
            match_out[idx][model][ra] += 1
            pts[m['a']] += PTS[ra]
            pts[m['b']] += PTS[rb]
            diff[m['a']] += wa - wb
            diff[m['b']] += wb - wa
            mini[m['a']][m['b']] = (PTS[ra], wa - wb)
            mini[m['b']][m['a']] = (PTS[rb], wb - wa)
            results.append(ra)
        ranking = rank_teams(teams, pts, mini, diff)
        for pos, t in enumerate(ranking):
            rank_count[t][pos] += 1
        if objectif_team:
            pos = ranking.index(objectif_team) + 1
            hit = goal_reached(pos, n, quota, P['objectif'])
            goal_hits += hit
            for idx, ra in enumerate(results):
                cond[idx][ra][0] += hit
                cond[idx][ra][1] += 1
    return rank_count, match_out, cond, goal_hits


def goal_reached(pos, n, quota, objectif):
    if objectif == 'montee':
        return 1 if pos <= quota['up'] else 0
    return 1 if pos <= n - quota['down'] - quota['risk'] else 0


def lineup_shift(lineup, lineups):
    """Modèle A avec alignement imposé : décalage du rating par l'écart de moyenne avec les alignements vus."""
    if not lineup or not lineups:
        return 0.0
    usual = sum(sum(p['cls'] + p.get('adj', 0) for p in l) / len(l) for l in lineups) / len(lineups)
    cur = sum(p['cls'] + p.get('adj', 0) for p in lineup) / len(lineup)
    return cur - usual


def descent_probability(rank_dist, n, quota):
    down = sum(rank_dist[n - quota['down']:]) if quota['down'] else 0.0
    if quota['risk']:
        down += quota['frac'] * rank_dist[n - quota['down'] - 1]
    return down


def main(site_path=SITE, out_path=OUT, nsim=NSIM, seed=2026):
    site = json.loads(Path(site_path).read_text())
    pools = {}
    for key, pool in site['DATA'].items():
        if key in EXCLUS or not pool.get('teams'):
            continue
        pools[key] = build_pool(key, pool, (site.get('STANDINGS') or {}).get(key))
    s, nparties = calibrate(pools)
    form = player_form(pools, s)
    rnd = random.Random(seed)
    out_teams = {}
    for key, P in pools.items():
        quota = quotas_for(P['pool'])
        n = len(P['teams'])
        standings_pos = {row['name']: row.get('pos') for row in P['standings']}
        auto = 'montee' if quota['up'] and (standings_pos.get(P['acbb']) or 99) <= 2 else 'maintien'
        P['objectif'] = OBJECTIFS.get(key, auto)
        ratings, _ = fit_ratings(P, s)
        lineups = {t: lineups_of(P, t, form) for t in P['teams']}
        rank_count, match_out, cond, goal_hits = simulate(P, ratings, lineups, s, P['acbb'], quota, rnd, nsim)
        teams_out = []
        for t in P['teams']:
            dist = [c / nsim for c in rank_count[t]]
            seen = []
            for l in lineups[t]:
                for p in l:
                    if not any(q['nom'] == p['nom'] and q['pre'] == p['pre'] for q in seen):
                        seen.append(p)
            seen.sort(key=lambda p: -(p['cls'] + p['adj']))
            teams_out.append({'name': t, 'acbb': t == P['acbb'], 'rating': ratings[t],
                              'pos': standings_pos.get(t), 'pts': next((r.get('pts') for r in P['standings'] if r['name'] == t), None),
                              'ranks': [round(x, 4) for x in dist],
                              'pUp': round(sum(dist[:quota['up']]), 4) if quota['up'] else 0.0,
                              'pDown': round(descent_probability(dist, n, quota), 4),
                              'avg': round(sum(sum(p['cls'] for p in l) / len(l) for l in lineups[t]) / len(lineups[t])) if lineups[t] else None,
                              'lineups': lineups[t], 'players': seen})
        remaining = []
        for idx, m in enumerate(P['remaining']):
            o = match_out[idx]
            tot = sum(o[r] for r in 'VND') or 1
            ta, tb = sum(o['A'].values()) or 1, sum(o['B'].values()) or 1
            row = {'j': m['j'], 'a': m['a'], 'b': m['b'], 'home': m.get('home'),
                   'p': {r: round(o[r] / tot, 4) for r in 'VND'},
                   'pA': {r: round(o['A'][r] / ta, 4) for r in 'VND'},
                   'pB': {r: round(o['B'][r] / tb, 4) for r in 'VND'}}
            if P['acbb']:
                imp = {}
                for r in 'VND':
                    hits, cnt = cond[idx][r]
                    imp[r] = round(hits / cnt, 4) if cnt else None
                row['impact'] = imp
                vals = [v for v in imp.values() if v is not None]
                row['swing'] = round(max(vals) - min(vals), 4) if len(vals) > 1 else 0.0
            remaining.append(row)
        played = [{'j': m['j'], 'a': m['a'], 'b': m['b'], 'wa': m['wa'], 'wb': m['wb']} for m in P['played']]
        out_teams[key] = {'pool': P['pool'], 'level': P['level'], 'acbb': P['acbb'], 'n': n, 'objectif': P['objectif'],
                          'pObjectif': round(goal_hits / nsim, 4) if P['acbb'] else None,
                          'quota': quota, 'standings': P['standings'], 'teams': teams_out, 'played': played, 'remaining': remaining}
    doc = {'built': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_built': site.get('built'),
           'season': site.get('season'), 'nsim': nsim, 's': s, 'nparties': nparties, 'mix': 0.5,
           'methode': 'A = ratings Bradley-Terry sur les parties (confrontations directes, transitivité) ; B = modèle joueur (logistique calibrée + forme) ; combinaison 50/50 ; classement art. 14 IDF.',
           'teams': out_teams}
    Path(out_path).write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n')
    return doc


if __name__ == '__main__':
    doc = main()
    print(f"fin_de_phase.json : {len(doc['teams'])} équipes, s = {doc['s']:.0f} pts pour 10:1 ({doc['nparties']} parties), {doc['nsim']} simulations")
    for key in sorted(doc['teams'], key=lambda k: (k[0], int(k[1:]))):
        T = doc['teams'][key]
        me = next(t for t in T['teams'] if t['acbb'])
        print(f"{key:4} {T['quota']['code']:3} {str(me['pos'] or '?'):>2}e {me['pts'] or 0:>2} pts | montée {me['pUp']:5.0%} descente {me['pDown']:5.0%} | objectif {T['objectif']:8} {T['pObjectif']:5.0%} | rating {me['rating']:+6.0f}")
