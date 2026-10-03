# -*- coding: utf-8 -*-
"""Groupes du Critérium Fédéral départemental (CD92) : PDF -> data/criterium2627.json

Le comité publie, une à deux semaines avant chaque tour, deux PDF (jeunes, puis
-19 ans et adultes). Même principe que les poules du championnat : la source est
un PDF, on le convertit une fois et le site lit le JSON.

Structure du PDF, parfaitement régulière, un bloc par groupe :
    D1 -19 FILLES
    LEVALLOIS - Gymnase Eric Srecki – 152 rue Danton
    Fin du Pointage : 8H30  Début de la Compétition : 9H00  En cas d'absence ...
    Licence Nom Prénom No club Club Cat. Cat S Clt
    1 9259716 LENNON Clémence 08920049 BOULOGNE BILLANCOURT AC J2 -17 952

Le nom et le club contiennent des espaces : on s'ancre sur les deux nombres sûrs,
la licence (6 à 8 chiffres) et le numéro de club (8 chiffres). Le nom est en
capitales et le prénom capitalisé, d'où la coupure au dernier mot tout en
majuscules. La première colonne vaut un rang, ou « FEJ » (joueur ajouté).

Usage :  python3 scripts/criterium_pdf.py <tour> <date> <pdf> [pdf...]
Exemple : python3 scripts/criterium_pdf.py 1 11/10/2026 ~/Downloads/..._Jeunes.pdf ~/Downloads/..._M19.pdf
"""
import json, os, re, sys, unicodedata, datetime
import pdfplumber

CLUB_ACBB = '08920049'
SORTIE = 'data/criterium2627.json'

RE_GROUPE  = re.compile(r'^(D\d|N\d|R\d|PN|ELITE)[^\n]{0,60}$')
RE_SALLE   = re.compile(r'^[A-ZÀ-Ÿ][^\n]*[-–][^\n]+$')
# Les deux PDF n'écrivent pas l'heure pareil : « 8H30 » côté adultes, « 13 H 30 » côté jeunes.
RE_HORAIRE = re.compile(r'Fin du Pointage\s*:\s*(\d{1,2}\s*[Hh]\s*\d{0,2})'
                        r'.*?Comp[ée]tition\s*:\s*(\d{1,2}\s*[Hh]\s*\d{0,2})'
                        r'(?:.*?pr[ée]venir\s*:\s*(\S+))?', re.I)
def heure(t):
    m = re.match(r'(\d{1,2})\s*[Hh]\s*(\d{0,2})', t or '')
    return '%dh%02d' % (int(m.group(1)), int(m.group(2) or 0)) if m else (t or '')
RE_JOUEUR  = re.compile(r'^(\d{1,3}|FEJ)\s+(\d{6,8})\s+(.+?)\s+(\d{8})\s+(.+?)\s+(\S+)\s+(\S+)\s+(\d+)\s*$')

def coupe_nom(bloc):
    """« LENNON Clémence » -> ('LENNON', 'Clémence') ; gère « DE BONNECHOSE Isabelle »."""
    mots = bloc.split()
    maj = [i for i, m in enumerate(mots)
           if unicodedata.normalize('NFD', m).encode('ascii', 'ignore').decode().isupper()]
    if not maj:
        return bloc, ''
    i = max(maj)
    return ' '.join(mots[:i + 1]), ' '.join(mots[i + 1:])

AGES = ['-11', '-13', '-15', '-19', 'ELITE']
LIB  = {'F': {'ELITE': 'Élite Dames'}, 'M': {'ELITE': 'Élite Messieurs'}}

def classer(groupes):
    """Découpe « D2 -13 GARCONS » en division et catégorie d'âge, pour que la page puisse
    ranger par ÂGE d'abord (la grosse catégorie) puis par division — c'est ainsi qu'un joueur
    se cherche, pas l'inverse.

    Deux groupes s'appellent « D3-11 Groupe 3 » et « D3 -19 Groupe 3 », sans le genre : le PDF
    les place juste après le groupe de garçons du même âge et de la même division, et sa page
    de synthèse les range bien sous « GARCONS ». On hérite donc du groupe précédent plutôt que
    de deviner sur les prénoms."""
    precedent = None
    for g in groupes:
        n = g['nom'].upper()
        m = re.match(r'^(D\d)\s*(.*)$', n)
        g['div'] = m.group(1) if m else ''
        reste = (m.group(2) if m else n).strip()
        age = next((a for a in AGES if reste.startswith(a)), '')
        genre = 'F' if ('FILLE' in reste or 'DAME' in reste) else ('M' if ('GARCON' in reste or 'MESSIEUR' in reste) else '')
        if not genre and precedent and precedent['age'] == age and precedent['div'] == g['div']:
            genre = precedent['genre']
        g['age'], g['genre'] = age, genre
        g['cat'] = LIB.get(genre, {}).get(age) or (
            (age + ' ans ' + ('Filles' if genre == 'F' else 'Garçons')) if age and genre else (reste.title() or g['nom']))
        g['rang'] = (AGES.index(age) if age in AGES else 9, 0 if genre == 'F' else 1)
        precedent = g

def lire(chemin):
    groupes, courant = [], None
    with pdfplumber.open(chemin) as pdf:
        for page in pdf.pages:
            for ligne in (page.extract_text() or '').split('\n'):
                l = ligne.strip()
                if not l:
                    continue
                m = RE_JOUEUR.match(l)
                if m and courant is not None:
                    rang, lic, bloc, numclub, club, cat, cats, clt = m.groups()
                    nom, pre = coupe_nom(bloc)
                    acbb = numclub == CLUB_ACBB
                    j = {'pos': None if rang == 'FEJ' else int(rang), 'ajoute': rang == 'FEJ',
                         'nom': nom, 'pre': pre, 'club': club.strip(),
                         'cat': cat, 'cats': cats, 'clt': int(clt), 'acbb': acbb}
                    # Le PDF du comité porte le numéro de licence de TOUS les joueurs, dont 700 et
                    # quelques d'autres clubs. Le fichier produit ici est publié sur le site : on ne
                    # garde la licence que pour les nôtres, seule utile (rapprochement et confirmation
                    # de présence). Pour un adversaire, nom, club, catégorie et classement suffisent.
                    if acbb: j['lic'] = lic
                    courant['joueurs'].append(j)
                    continue
                if l.startswith('Licence Nom') or l.startswith('CRITERIUM'):
                    continue
                h = RE_HORAIRE.search(l)
                if h and courant is not None:
                    courant['pointage'], courant['debut'] = heure(h.group(1)), heure(h.group(2))
                    if h.group(3): courant['contact'] = h.group(3).rstrip('.')
                    continue
                if RE_GROUPE.match(l) and 'Gymnase' not in l and 'Salle' not in l:
                    courant = {'nom': l, 'salle': '', 'pointage': '', 'debut': '', 'contact': '', 'joueurs': []}
                    groupes.append(courant)
                    continue
                if courant is not None and not courant['salle'] and not courant['joueurs'] and RE_SALLE.match(l):
                    courant['salle'] = l
    return [g for g in groupes if g['joueurs']]

def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__.strip().splitlines()[-2])
    tour, date, pdfs = sys.argv[1], sys.argv[2], sys.argv[3:]
    groupes = []
    for p in pdfs:
        g = lire(os.path.expanduser(p))
        print("  %-52s %2d groupes, %3d joueurs" % (os.path.basename(p)[:52], len(g), sum(len(x['joueurs']) for x in g)))
        groupes += g
    classer(groupes)
    for i, g in enumerate(groupes):
        g['id'] = 't%s-g%02d' % (tour, i + 1)
    try:
        with open(SORTIE) as f: doc = json.load(f)
    except Exception:
        doc = {'source': "PDF « GROUPES DEPART CRIT FED » du CD92 (cdtt92@gmail.com), un fichier jeunes et un fichier -19 ans/adultes par tour", 'tours': {}}
    doc['maj'] = datetime.date.today().isoformat()
    doc['tours'][str(tour)] = {'date': date, 'groupes': groupes}
    with open(SORTIE, 'w') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=False)
    acbb = sum(1 for g in groupes for j in g['joueurs'] if j['acbb'])
    print("%s : tour %s · %d groupes · %d joueurs dont %d ACBB"
          % (SORTIE, tour, len(groupes), sum(len(g['joueurs']) for g in groupes), acbb))

if __name__ == '__main__':
    main()
