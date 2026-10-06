#!/usr/bin/env python3
"""Brûlage des adversaires (règlement FFTT II.112) -> data/brulages2627.json.

Pour chaque équipe adverse de nos poules (data/site.json), lit les feuilles de la phase en cours de toutes
les équipes de son club de numéro inférieur (plus fortes) et liste les joueurs qui y ont déjà disputé
2 rencontres : ils ne peuvent plus jouer dans cette équipe jusqu'à la fin de la phase. Même règle que pour
nos compos (shared/participations.js, historyRules) : une rencontre par journée, la plus forte équipe compte.

Le club de chaque équipe vient des feuilles de nos poules (champ « club » de site.json, écrit par
fftt_site.py). Noms seulement : aucune licence n'est publiée. Limite connue : une feuille d'exemption
(II.112.2) n'est pas fournie par l'API, elle n'est donc pas comptée.
Usage : python3 scripts/fftt_brulages.py   (FFTT_ID / FFTT_PWD)
"""
import os, re, html, json, time, datetime, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import fftt_site as fs
fb = fs.fb
FILS = 5

def numero(nom):
    """« PUTEAUX TT CSM 3 » -> 3, « SM MONTROUGE (5) » -> 5 (la FFTT note ainsi certaines équipes) ;
    un nom sans numéro final est l'équipe 1."""
    m = re.search(r'\(?(\d+)\)?\s*$', nom or '')
    return int(m.group(1)) if m else 1

# Seul le championnat par équipes compte pour le brûlage (II.112) : un club engage aussi des équipes dans d'autres
# compétitions (« D92_Championnat Dimanche Matin », « D92_Championnat du Jeudi soir »…) aux noms presque identiques
# (« SM MONTROUGE 1 » à côté de « SM MONTROUGE  1 »). Constaté sur Montrouge le 06/10/2026.
EPREUVE = re.compile(r"Championnats? de France par [eé]quipes", re.I)

def date_iso(d):
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', d or '')
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

def equipes_club(club, genre):
    """Équipes de la phase en cours d'un club : [{nom, n, cx, d1, org}]."""
    r = fb.get(f"xml_equipe.php?numclu={club}&type={genre}")
    out = []
    for b in re.findall(r'<equipe>(.*?)</equipe>', r, re.S):
        if not EPREUVE.search(fs.tg(b, 'libepr')): continue   # autre compétition : ne compte pas
        lib = fs.tg(b, 'libequipe')
        m = re.match(r'^(.*?)\s*-\s*Phase\s*(\d+)\s*$', lib)
        nom, phase = (m.group(1), int(m.group(2))) if m else (lib, 1)
        lm = re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>', b)
        if not lm: continue
        q = dict(urllib.parse.parse_qsl(html.unescape(lm.group(1))))
        if not q.get('cx_poule') or not q.get('D1'): continue
        out.append({'nom': nom.strip(), 'n': numero(nom), 'phase': phase,
                    'cx': q['cx_poule'], 'd1': q['D1'], 'org': q.get('organisme_pere', '')})
    if not out: return []
    ph = max(e['phase'] for e in out)
    return [e for e in out if e['phase'] == ph]

def feuilles_equipe(e, aujourdhui):
    """Participations d'une équipe : [(journée, [joueurs])] pour chaque rencontre déjà jouée."""
    cal = fb.get(f"xml_result_equ.php?cx_poule={e['cx']}&D1={e['d1']}&organisme_pere={e['org']}")
    k = fb.nrm(e['nom']); out = []
    for t in re.findall(r'<tour>(.*?)</tour>', cal, re.S):
        ea, eb = fs.tg(t, 'equa'), fs.tg(t, 'equb')
        if k not in (fb.nrm(ea), fb.nrm(eb)): continue
        jn = re.search(r'tour\s*n°?\s*(\d+)', fs.tg(t, 'libelle'))
        if not jn: continue
        d = date_iso(fs.tg(t, 'datereelle') or fs.tg(t, 'dateprevue'))
        if d and d > aujourdhui: continue                      # pas encore jouée : pas de feuille
        lm = re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', t)
        if not lm: continue
        lineup = fs.fetch_renc(html.unescape(lm.group(1))).get(k, ([], 0, 0))[0]
        joueurs = [p for p in lineup if p.get('nom') and p['nom'] != 'Joueur absent']
        if joueurs: out.append((int(jn.group(1)), joueurs))   # figurer sur la feuille suffit (II.112)
        time.sleep(0.1)
    return out

def main():
    if not fb.APPID or not fb.MDP: sys.exit("FFTT_ID / FFTT_PWD manquants")
    site = json.load(open('data/site.json'))
    aujourdhui = datetime.date.today().isoformat()
    # 1. les équipes adverses de nos poules, avec leur club et leur championnat (messieurs / dames)
    cibles = {}
    for key, pool in site.get('DATA', {}).items():
        genre = 'F' if key.startswith('F') else 'M'
        for t in pool.get('teams', []):
            if t.get('acbb'): continue
            cibles.setdefault(t['name'], {'club': t.get('club'), 'genre': genre, 'n': numero(t['name'])})
    sans_club = sorted(n for n, c in cibles.items() if not c['club'])
    besoins = {}
    for c in cibles.values():
        if c['club'] and c['n'] > 1:
            besoins[(c['club'], c['genre'])] = max(besoins.get((c['club'], c['genre']), 0), c['n'])
    print(f"{len(cibles)} équipes adverses · {len(besoins)} clubs à lire · sans n° de club : {len(sans_club)}")
    if cibles and len(sans_club) == len(cibles):
        sys.exit("site.json ne porte aucun n° de club : lancer d'abord « Résultats équipes FFTT » (fftt_site.py)")
    # 2. les équipes plus fortes de ces clubs, puis leurs feuilles de la phase
    def lire_club(cg):
        club, genre = cg
        try: eqs = equipes_club(club, genre)
        except Exception as ex: return cg, None, str(ex)
        return cg, [e for e in eqs if e['n'] < besoins[cg]], None
    with ThreadPoolExecutor(FILS) as pool:
        clubs = list(pool.map(lire_club, besoins))
    a_lire = [(cg, e) for cg, eqs, err in clubs if eqs for e in eqs]
    erreurs_club = [cg for cg, eqs, err in clubs if eqs is None]
    def lire_equipe(item):
        cg, e = item
        try: return cg, e, feuilles_equipe(e, aujourdhui), None
        except Exception as ex: return cg, e, None, str(ex)
    with ThreadPoolExecutor(FILS) as pool:
        lus = list(pool.map(lire_equipe, a_lire))
    # 3. participations par club : joueur -> {journée: numéro de l'équipe la plus forte}
    part = {}; lues = {}; ko = {}
    for cg, e, fe, err in lus:
        if fe is None: ko.setdefault(cg, set()).add(e['n']); continue
        lues.setdefault(cg, set()).add(e['n'])
        for j, joueurs in fe:
            for p in joueurs:
                k = (p['nom'] + '|' + (p.get('prenom') or '')).upper()
                r = part.setdefault(cg, {}).setdefault(k, {'nom': p['nom'], 'prenom': p.get('prenom') or '', 'j': {}})
                r['j'][j] = min(r['j'].get(j, 99), e['n'])
    # 4. brûlés pour chaque équipe adverse : 2 journées ou plus dans des équipes de numéro inférieur
    equipes = {}
    for nom, c in sorted(cibles.items()):
        cg = (c['club'], c['genre'])
        if not c['club'] or c['n'] <= 1: continue
        brules = []
        for r in part.get(cg, {}).values():
            js = sorted((j, t) for j, t in r['j'].items() if t < c['n'])
            if len(js) >= 2:
                brules.append({'nom': r['nom'], 'prenom': r['prenom'], 'rencontres': [{'j': j, 'eq': t} for j, t in js]})
        brules.sort(key=lambda b: (b['nom'], b['prenom']))
        # équipes plus fortes qui existent mais n'ont pas pu être lues (club entier illisible : toutes)
        manq = list(range(1, c['n'])) if cg in erreurs_club else sorted(n for n in ko.get(cg, set()) if n < c['n'])
        equipes[nom] = {'brules': brules, 'lues': sorted(n for n in lues.get(cg, set()) if n < c['n']), 'manquantes': manq}
    out = {'built': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'season': fb.SAISON,
           'regle': "II.112 : 2 rencontres de la phase dans des équipes de numéro inférieur", 'equipes': equipes}
    nb = sum(len(v['brules']) for v in equipes.values())
    print(f"{len(a_lire)} équipes supérieures lues ({sum(1 for x in lus if x[2] is not None)} réussies) · "
          f"{nb} joueurs brûlés sur {len(equipes)} équipes · clubs illisibles : {len(erreurs_club)}")
    if a_lire and not any(x[2] is not None for x in lus):
        sys.exit("Aucune feuille lue : rien n'est écrit (API indisponible ?)")
    try: avant = json.load(open('data/brulages2627.json')).get('equipes')
    except Exception: avant = None
    if avant == equipes:   # rien de neuf : pas de réécriture, donc pas de publication pour rien
        print("Inchangé — data/brulages2627.json conservé."); return
    json.dump(out, open('data/brulages2627.json', 'w'), ensure_ascii=False)
    print("OK — data/brulages2627.json écrit.")

if __name__ == '__main__': main()
