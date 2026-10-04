# -*- coding: utf-8 -*-
"""Critérium Fédéral — échelons RÉGIONAL (R1/R2) et NATIONAL (N2) : PDF -> criterium2627.json

Le départemental vient du CD92 (scripts/criterium_pdf.py). Le régional et le national
viennent de la ligue Île-de-France et de la FFTT, publiés sur fftt-idf.com/criterium-federal.
Trois formats, un par fichier :

  · « Liste Globale »       : une page par catégorie R1/R2, lignes
                              « rang licence NOM Prénom Club Cat. Clst [montante] »
  · « Qualifiés N2 … »      : lignes « rang lig cd licence NOM Prénom Association JJ/MM/AAAA points … »
  · « Salles Régionales » et les deux convocations : salles et horaires, repris en dur
                              ci-dessous — ce sont des tableaux de quelques lignes, stables
                              sur le tour, et les parser aurait été plus fragile que les lire.

Découpage nom / prénom / club : on s'ancre sur la suite de mots TOUT EN CAPITALES en tête
(le nom, « MARTIN GARNIER »), le mot suivant étant le prénom, le reste le club. Le club peut
lui aussi être en capitales (« BOULOGNE BILLANCOURT AC »), d'où l'ancrage en tête et non en queue.

Usage : python3 scripts/criterium_reg_nat_pdf.py <tour> <liste_globale.pdf> <n2_...pdf> [n2_...pdf ...]
"""
import json, os, re, sys, unicodedata, datetime
import pdfplumber

CLUB_ACBB_NOM = 'BOULOGNE BILLANCOURT AC'
SORTIE = 'data/criterium2627.json'

# Salles et horaires — « Salles Régionales » (samedi 10/10 pointage 9h30 début 10h ;
# dimanche 11/10 pointage 9h début 10h) et les deux convocations N2.
SALLES_R = {
  ('R1', 'BENJAMINES'):       ('Ponthierry (77) — Salle Jean-Pierre Pelletier, rue du Stade, 77310 St Fargeau Ponthierry', '10/10/2026', '9h30', '10h00'),
  ('R1', 'MINIMES FILLES'):   ('Combs-la-Ville (77) — Gymnase Le Paloisel, avenue Le Paloisel', '10/10/2026', '9h30', '10h00'),
  ('R1', 'CADETTES'):         ('Corbeil-Essonnes (91) — Gymnase de la Nacelle, rue de la Nacelle', '10/10/2026', '9h30', '10h00'),
  ('R1', 'BENJAMINS'):        ('Viry-Châtillon (91) — Gymnase du Bellay, avenue du Bellay', '10/10/2026', '9h30', '10h00'),
  ('R2', 'BENJAMINS'):        ('Viry-Châtillon (91) — Gymnase du Bellay, avenue du Bellay', '10/10/2026', '9h30', '10h00'),
  ('R1', 'MINIMES GARÇONS'):  ('Montmorency (95) — Complexe sportif des Champeaux, chemin de la Butte aux Pères', '10/10/2026', '9h30', '10h00'),
  ('R2', 'MINIMES GARÇONS'):  ('Montmorency (95) — Complexe sportif des Champeaux, chemin de la Butte aux Pères', '10/10/2026', '9h30', '10h00'),
  ('R1', 'CADETS'):           ('Corbeil-Essonnes (91) — Gymnase de la Nacelle, rue de la Nacelle', '10/10/2026', '9h30', '10h00'),
  ('R2', 'CADETS'):           ('Corbeil-Essonnes (91) — Gymnase de la Nacelle, rue de la Nacelle', '10/10/2026', '9h30', '10h00'),
  ('R1', 'JUNIORS FILLES'):   ('Viry-Châtillon (91) — Gymnase du Bellay, 27 avenue du Bellay', '11/10/2026', '9h00', '10h00'),
  ('R1', 'JUNIORS GARÇONS'):  ('Montmorency (95) — Complexe sportif des Champeaux, chemin de la Butte aux Pères', '11/10/2026', '9h00', '10h00'),
  ('R2', 'JUNIORS GARÇONS'):  ('Montmorency (95) — Complexe sportif des Champeaux, chemin de la Butte aux Pères', '11/10/2026', '9h00', '10h00'),
  ('R1', 'SENIORS DAMES'):    ("Saint-Cyr-l'École (78) — Complexe sportif Pierre Mazeaud (3ᵉ étage), 5 rue de Lattre de Tassigny", '11/10/2026', '9h00', '10h00'),
  ('R2', 'SENIORS DAMES'):    ("Saint-Cyr-l'École (78) — Complexe sportif Pierre Mazeaud (3ᵉ étage), 5 rue de Lattre de Tassigny", '11/10/2026', '9h00', '10h00'),
  ('R1', 'SENIORS MESSIEURS'):('Viry-Châtillon (91) — Gymnase du Bellay, 27 avenue du Bellay', '11/10/2026', '9h00', '10h00'),
  ('R2', 'SENIORS MESSIEURS'):('Corbeil-Essonnes (91) — Gymnase de la Nacelle, rue de la Nacelle', '11/10/2026', '9h00', '10h00'),
}
SALLE_N2_JEUNES  = ('Le Mans (72) — Salle de tennis de table, 51 rue Garnier Pages, 72000 Le Mans', '10/10/2026', '9h30', '10h30')
SALLE_N2_SENIORS = ('Draveil (91) — Salle Alborghetti, 53 rue Ferdinand Buisson, 91210 Draveil', '10/10/2026', '9h00', '10h30')

# catégorie FFTT -> (âge affiché, genre), pour ranger comme le départemental
AGE = {'BENJAMINES': ('-11', 'F'), 'BENJAMINS': ('-11', 'M'),
       'MINIMES FILLES': ('-13', 'F'), 'MINIMES GARÇONS': ('-13', 'M'), 'MINIMES GARCONS': ('-13', 'M'),
       'CADETTES': ('-15', 'F'), 'CADETS': ('-15', 'M'),
       'JUNIORS FILLES': ('-19', 'F'), 'JUNIORS GARÇONS': ('-19', 'M'), 'JUNIORS GARCONS': ('-19', 'M'),
       'SENIORS DAMES': ('ELITE', 'F'), 'SENIORS MESSIEURS': ('ELITE', 'M')}
ORDRE = ['-11', '-13', '-15', '-19', 'ELITE']
LIB = {('ELITE', 'F'): 'Élite Dames', ('ELITE', 'M'): 'Élite Messieurs'}

RE_TITRE = re.compile(r'^QUALIFI[ÉE]{1,2}S?\s+(R[12])\s+(.+?)\s*-\s*TOUR', re.I)
RE_JOUEUR_R = re.compile(r'^(\d{1,3})\s+(\d{6,8})\s+(.+?)\s+([A-Z]\d?|V\d{2}|S)\s+(\d{3,4})(?:\s+\S+)?\s*$')
RE_JOUEUR_N = re.compile(r'^(\d{1,3})\s+\d{2}\s+\d{2}\s+(\d{6,8})\s+(.+?)\s+\d{2}/\d{2}/\d{4}\s+(\d{3,4})\b')

def coupe(bloc):
    """« MARTIN GARNIER Camille E. P. DE LOGNES » -> nom, prénom, club."""
    mots = bloc.split()
    def caps(m):
        return unicodedata.normalize('NFD', m).encode('ascii', 'ignore').decode().replace('-', '').isupper()
    i = 0
    while i < len(mots) and caps(mots[i]) and len(mots[i]) > 1:
        i += 1
    if i == 0 or i >= len(mots):
        return bloc, '', ''
    return ' '.join(mots[:i]), mots[i], ' '.join(mots[i + 1:])

def lire_regional(chemin):
    groupes, courant = [], None
    with pdfplumber.open(chemin) as pdf:
        for page in pdf.pages:
            for l in (page.extract_text() or '').split('\n'):
                l = l.strip()
                t = RE_TITRE.match(l)
                if t:
                    div, cat = t.group(1).upper(), t.group(2).upper().strip()
                    age, genre = AGE.get(cat, ('', ''))
                    salle, date, pointage, debut = SALLES_R.get((div, cat), ('', '', '', ''))
                    courant = {'nom': div + ' ' + cat, 'niveau': 'R', 'div': div, 'age': age, 'genre': genre,
                               'cat': LIB.get((age, genre)) or (age + ' ans ' + ('Filles' if genre == 'F' else 'Garçons')),
                               'salle': salle, 'date': date, 'pointage': pointage, 'debut': debut,
                               'contact': '', 'joueurs': []}
                    groupes.append(courant); continue
                m = RE_JOUEUR_R.match(l)
                if m and courant is not None:
                    pos, lic, bloc, cat2, clt = m.groups()
                    nom, pre, club = coupe(bloc)
                    acbb = club.upper().startswith('BOULOGNE BILLANCOURT')
                    j = {'pos': int(pos), 'ajoute': False, 'nom': nom, 'pre': pre, 'club': club,
                         'cat': cat2, 'cats': '', 'clt': int(clt), 'acbb': acbb}
                    if acbb: j['lic'] = lic
                    j['_lic'] = lic          # retiré avant écriture, cf. separer_licences()
                    courant['joueurs'].append(j)
    return [g for g in groupes if g['joueurs']]

def lire_national(chemin):
    groupes, courant = [], None
    seniors = 'Seniors' in os.path.basename(chemin)
    with pdfplumber.open(chemin) as pdf:
        for page in pdf.pages:
            for l in (page.extract_text() or '').split('\n'):
                l = l.strip()
                h = re.match(r'^(JUNIORS|CADET(?:TE)?S|MINIMES|BENJAMIN(?:E)?S|Seniors)\s*(GARCONS|GARÇONS|FILLES|DAMES|MESSIEURS)?', l, re.I)
                if h and not RE_JOUEUR_N.match(l):
                    base = h.group(1).upper(); suf = (h.group(2) or '').upper()
                    cle = ('SENIORS DAMES' if base == 'SENIORS' else (base + (' ' + suf if suf else '')))
                    cle = cle.replace('GARCONS', 'GARÇONS')
                    if cle not in AGE and base in ('CADETTES', 'BENJAMINES'): cle = base
                    age, genre = AGE.get(cle, ('', ''))
                    if not age: continue
                    salle, date, pointage, debut = SALLE_N2_SENIORS if seniors else SALLE_N2_JEUNES
                    courant = {'nom': 'N2 ' + cle, 'niveau': 'N', 'div': 'N2', 'age': age, 'genre': genre,
                               'cat': LIB.get((age, genre)) or (age + ' ans ' + ('Filles' if genre == 'F' else 'Garçons')),
                               'salle': salle, 'date': date, 'pointage': pointage, 'debut': debut,
                               'date_fin': '11/10/2026',  # convocations du tour 1 : samedi ET dimanche
                               'contact': '', 'joueurs': []}
                    groupes.append(courant); continue
                m = RE_JOUEUR_N.match(l)
                if m and courant is not None:
                    pos, lic, bloc, clt = m.groups()
                    nom, pre, club = coupe(bloc)
                    acbb = club.upper().startswith('BOULOGNE BILLANCOURT')
                    j = {'pos': int(pos), 'ajoute': False, 'nom': nom, 'pre': pre, 'club': club,
                         'cat': '', 'cats': '', 'clt': int(clt), 'acbb': acbb}
                    if acbb: j['lic'] = lic
                    j['_lic'] = lic          # retiré avant écriture, cf. separer_licences()
                    courant['joueurs'].append(j)
    return [g for g in groupes if g['joueurs']]

def separer_licences(groupes, chemin='data/_criterium_lic.json'):
    """Même principe que pour le départemental : les licences des joueurs des autres clubs
    sortent du fichier publié vers une table PRIVÉE indexée par groupe et position, qui sert
    uniquement à interroger la FFTT pour les bilans."""
    import json as _json, os as _os
    table = {}
    for g in groupes:
        for j in g['joueurs']:
            lic = j.pop('_lic', None)
            if lic: table.setdefault(g['id'], {})[str(j.get('pos') or 0)] = lic
    anc = {}
    if _os.path.exists(chemin):
        try: anc = _json.load(open(chemin))
        except Exception: anc = {}
    anc.update(table)
    _json.dump(anc, open(chemin, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    return sum(len(v) for v in table.values())

def main():
    if len(sys.argv) < 3: sys.exit('usage : criterium_reg_nat_pdf.py <tour> <pdf> [pdf...]')
    tour, pdfs = sys.argv[1], sys.argv[2:]
    nouveaux = []
    for p in pdfs:
        p = os.path.expanduser(p); base = os.path.basename(p)
        g = lire_national(p) if 'Qualifiés N2' in base or 'Qualifies N2' in base else lire_regional(p)
        print('  %-56s %2d catégories, %4d joueurs' % (base[:56], len(g), sum(len(x['joueurs']) for x in g)))
        nouveaux += g
    doc = json.load(open(SORTIE))
    t = doc['tours'][str(tour)]
    # on remplace les échelons R et N, on ne touche jamais au départemental
    t['groupes'] = [x for x in t['groupes'] if x.get('niveau', 'D') == 'D'] + nouveaux
    for g in t['groupes']:
        g.setdefault('niveau', 'D')
        g['rang'] = [ORDRE.index(g['age']) if g.get('age') in ORDRE else 9,
                     0 if g.get('genre') == 'F' else 1,
                     {'D': 0, 'R': 1, 'N': 2}.get(g['niveau'], 9)]
    for i, g in enumerate(t['groupes']): g['id'] = 't%s-g%02d' % (tour, i + 1)
    nlic = separer_licences(t['groupes'])
    doc['maj'] = datetime.date.today().isoformat()
    doc['source'] = ("PDF « GROUPES DEPART CRIT FED » du CD92 pour le départemental ; "
                     "listes et salles de la ligue Île-de-France (fftt-idf.com/criterium-federal) "
                     "et convocations FFTT pour le régional et le national")
    json.dump(doc, open(SORTIE, 'w'), ensure_ascii=False, indent=1, sort_keys=False)
    from collections import Counter
    c = Counter(g['niveau'] for g in t['groupes'])
    acbb = Counter(g['niveau'] for g in t['groupes'] for j in g['joueurs'] if j['acbb'])
    print('%s : tour %s · %d catégories %s · joueurs ACBB %s · %d licences mises de côté'
          % (SORTIE, tour, len(t['groupes']), dict(c), dict(acbb), nlic))

if __name__ == '__main__':
    main()
