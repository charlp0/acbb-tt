#!/usr/bin/env python3
"""Classements des poules de Régionale 3 Messieurs (Ligue IDF) → data/r3_92.json.

Sert à estimer le nombre d'équipes des Hauts-de-Seine qui descendront de R3 en PR à l'issue de la
phase 1 : c'est le « X » dont dépendent les descentes en PR, D1 et D2 (règlement CD92 2026/27,
art. IV.2 : 14, 16 et 10 descentes si X = 4, une de plus ou de moins par équipe du 92 au-delà
ou en deçà). Lu par scripts/fin_de_phase.py ; relancé par results.yml après chaque collecte.

Méthode : la poule de R3 de l'ACBB (xml_equipe, liendivision) donne la division D1 et
l'organisme ; les autres poules portent les cx_poule voisins (1 → 16). Le département d'une équipe
se lit sur le numéro de club FFTT (08 92 0049 : ligue 08, département 92).
"""
import datetime
import importlib.util
import json
import os
import re
import sys
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))   # fftt_build importe fftt_quality
spec = importlib.util.spec_from_file_location('fb', ROOT / 'scripts/fftt_build.py')
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
OUT = ROOT / 'data/r3_92.json'
tg = fb.tag


def coords_r3():
    eq = fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
    for mm in re.finditer(r'<equipe>(.*?)</equipe>', eq, re.S):
        b = mm.group(1); libdiv = tg(b, 'libdivision')
        if 'R3' in libdiv and 'Messieurs' in libdiv:
            m = re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>', b)
            p = dict(x.split('=') for x in html.unescape(m.group(1)).split('&'))
            return p['D1'], p['organisme_pere'], int(p['cx_poule']), libdiv
    raise RuntimeError('poule de R3 de l’ACBB introuvable dans xml_equipe')


def classement(cx, d1, org):
    r = fb.get(f"xml_result_equ.php?cx_poule={cx}&D1={d1}&organisme_pere={org}&action=classement")
    rows = []
    for c in re.findall(r'<classement>(.*?)</classement>', r, re.S):
        numero = re.sub(r'\D', '', tg(c, 'numero'))
        rows.append({'poule': int(tg(c, 'poule') or 0), 'clt': int(tg(c, 'clt') or 0), 'equipe': tg(c, 'equipe'), 'pts': int(tg(c, 'pts') or 0),
                     'joue': int(tg(c, 'joue') or 0), 'numero': numero, 'dept': numero[2:4] if len(numero) >= 4 else ''})
    return rows


def main():
    if not fb.APPID or not fb.MDP:
        sys.exit('FFTT_ID / FFTT_PWD manquants')
    d1, org, cx_acbb, libdiv = coords_r3()
    print(f"R3 : {libdiv} | D1={d1} organisme={org} cx_poule ACBB={cx_acbb}")
    if os.environ.get('R3_92_DUMP') == '1':
        raw = fb.get(f"xml_result_equ.php?cx_poule={cx_acbb}&D1={d1}&organisme_pere={org}&action=classement")
        print('brut classement poule ACBB :', len(raw), 'car.', raw[:600].replace('\n', ' '))
    # cx_poule est un identifiant interne (1503039 pour la poule 1 de l'ACBB) : les poules d'une même division
    # portent des identifiants voisins. On balaye autour, on garde une réponse par numéro de poule.
    poules = {}
    for delta in list(range(0, 41)) + list(range(-1, -41, -1)):
        if len(poules) >= 16:
            break
        rows = classement(cx_acbb + delta, d1, org)
        if not rows:
            continue
        num = rows[0].get('poule') or len(poules) + 1
        if num in poules:
            continue
        poules[num] = {'cx': cx_acbb + delta, 'poule': num, 'equipes': rows}
    poules = [poules[k] for k in sorted(poules)]
    # Équipes du 92 en zone de descente : 8ᵉ = descente sûre, 7ᵉ = selon les descentes de R2 (≈ 1 sur 2).
    sur = [(p['cx'], e['equipe']) for p in poules for e in p['equipes'] if e['dept'] == '92' and e['clt'] == len(p['equipes'])]
    risque = [(p['cx'], e['equipe']) for p in poules for e in p['equipes'] if e['dept'] == '92' and e['clt'] == len(p['equipes']) - 1]
    doc = {'built': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'division': libdiv, 'D1': d1, 'organisme': org,
           'poules': poules, 'n92': sum(1 for p in poules for e in p['equipes'] if e['dept'] == '92'),
           'descentes_92': {'sures': sur, 'a_risque': risque, 'estimation': len(sur) + 0.5 * len(risque)}}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print(f"r3_92.json : {len(poules)} poules de R3, {doc['n92']} équipes du 92, descentes sûres {len(sur)} + à risque {len(risque)} → X ≈ {doc['descentes_92']['estimation']}")
    for p in poules:
        print(f"  poule {p['poule']} (cx {p['cx']}) : " + ' · '.join(f"{e['clt']}. {e['equipe']} ({e['dept']}) {e['pts']}" for e in p['equipes']))
    if os.environ.get('R3_92_DUMP') == '1':
        print('<<<R3_92_JSON>>>'); print(json.dumps(doc, ensure_ascii=False)); print('<<<END>>>')


if __name__ == '__main__':
    main()
