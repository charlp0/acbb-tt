#!/usr/bin/env python3
"""Joueurs du club réintégrés à la main dans un tour du critérium fédéral.

Cas d'usage : un joueur oublié par la ligue ou remis dans l'effectif par le comité après la
diffusion des listes (mail du CD92 ou de la ligue faisant foi). Il est ajouté sans position
(« + » sur le site) au groupe indiqué, et réappliqué à chaque régénération du tour par
criterium_pdf.py (départemental) et criterium_reg_nat_pdf.py (régional, national).

Application directe au fichier publié, sans relire les PDF :
    python3 scripts/criterium_ajouts.py <tour>
"""
import json, sys

SORTIE = 'data/criterium2627.json'

# tour -> liste d'ajouts ; `groupe` = champ `nom` du groupe (ex. « R2 CADETS », « D1 ELITE DAMES »)
AJOUTS = {
    '2': [
        # oublié par la ligue au T2 après son forfait excusé au T1 ; confirmé par Cyril le 04/11/2026
        {'niveau': 'R', 'groupe': 'R2 CADETS', 'nom': 'VERDIER', 'pre': 'Mahé',
         'club': 'BOULOGNE BILLANCOURT AC', 'cat': 'C2', 'cats': '', 'clt': 1594, 'lic': '9253816'},
        # remise dans l'effectif du T2 par le CD92 (mail de Lydie du 05/11/2026 transmis par Cyril)
        {'niveau': 'D', 'groupe': 'D1 ELITE DAMES', 'nom': 'HAREL', 'pre': 'Marie',
         'club': 'BOULOGNE BILLANCOURT AC', 'cat': 'S', 'cats': '-40', 'clt': 500, 'lic': '4930753'},
    ],
}

def appliquer(groupes, tour, niveaux=None):
    """Ajoute au bon groupe les joueurs prévus pour ce tour (idempotent). `niveaux` limite
    l'application aux échelons passés (ex. {'D'} quand seul le départemental est régénéré)."""
    n = 0
    for a in AJOUTS.get(str(tour), []):
        if niveaux and a['niveau'] not in niveaux: continue
        g = next((x for x in groupes if x.get('niveau', 'D') == a['niveau'] and x['nom'] == a['groupe']), None)
        if g is None: sys.exit('ajout manuel : groupe %s « %s » introuvable au tour %s' % (a['niveau'], a['groupe'], tour))
        if any(j['nom'] == a['nom'] and j['pre'] == a['pre'] for j in g['joueurs']): continue
        g['joueurs'].append({'pos': None, 'ajoute': True, 'nom': a['nom'], 'pre': a['pre'], 'club': a['club'],
                             'cat': a.get('cat', ''), 'cats': a.get('cats', ''), 'clt': a['clt'], 'acbb': True,
                             'lic': a['lic']})
        n += 1
    return n

def main():
    if len(sys.argv) != 2: sys.exit('usage : criterium_ajouts.py <tour>')
    tour = sys.argv[1]
    doc = json.load(open(SORTIE))
    t = doc['tours'].get(tour) or sys.exit('tour %s absent de %s' % (tour, SORTIE))
    n = appliquer(t['groupes'], tour)
    if n:
        json.dump(doc, open(SORTIE, 'w'), ensure_ascii=False, indent=1, sort_keys=False)
    print('%s : tour %s · %d joueur(s) ajouté(s) à la main' % (SORTIE, tour, n))

if __name__ == '__main__':
    main()
