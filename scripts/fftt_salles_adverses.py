# -*- coding: utf-8 -*-
"""Salles des adversaires DÉPARTEMENTAUX et RÉGIONAUX, depuis l'API FFTT.

Demandé par un capitaine (Guillaume Pierron, 27/09/2026) : les adresses des
déplacements manquaient. Le PDF des poules CD92 n'en couvre que la moitié, et
rien en régional. Périmètre décidé par Charles : départemental + régional
seulement — le national disperse les adversaires bien au-delà de l'Île-de-France.

Rapprochement : JAMAIS sur le nom du club, qui est ambigu. On liste les clubs
d'IdF (xml_club_b par département), puis les équipes de chaque club candidat
(xml_equipe), et on ne retient un club que si l'un de ses libellés d'équipe
correspond EXACTEMENT au nom de l'équipe adverse. Les poules portent le libellé
du PDF CD92 et site.json celui de la FFTT, qui diffèrent souvent dans l'ordre
des mots (« USM MALAKOFF 5 » / « MALAKOFF USM 5 ») : on essaie les deux.

⚠️ Ce qu'on obtient est la salle DÉCLARÉE PAR LE CLUB, pas le lieu confirmé de
la rencontre : un club peut recevoir ailleurs (notre F1 joue bien une journée à
Marly). Les adresses tenues à la main dans salles2627.json restent prioritaires.

Sortie : data/salles_adverses.json   { "<nom d'équipe>": {salle, adresse, cp, ville, lat, lon, club, maj} }
"""
import json, re, time, unicodedata, importlib.util, datetime, os

from team_identity import unique_alias

spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

DEPS = ['75', '77', '78', '91', '92', '93', '94', '95']
REG  = ['M3', 'M4', 'M5', 'F2']
DEP  = ['M6','M7','M8','M9','M10','M11','M12','M13','M14','M15','M16','M17','F3']

def mots(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return [m for m in re.split(r'[^A-Z0-9]+', s) if m]

def tags(b):
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>(.*?)</\1>', b, re.S))

def norme(s):   # comparaison de libellés : on ignore ponctuation et casse
    return ' '.join(mots(s))

# --- clubs d'Île-de-France -------------------------------------------------
clubs = []
for d in DEPS:
    r = fb.get("xml_club_b.php?dep=%s" % d); time.sleep(0.1)
    for b in re.findall(r'<club>(.*?)</club>', r, re.S):
        t = tags(b)
        if t.get('numero'): clubs.append({'num': t['numero'], 'nom': t.get('nom') or '', 'dep': d})
print("clubs IdF : %d" % len(clubs))

# --- adversaires à résoudre, avec leurs deux libellés ----------------------
poules = {q['acbb']: q for q in json.load(open('data/poules2627.json'))['poules']}
site = json.load(open('data/site.json')); DATA = site.get('DATA') or {}
cible = {}                      # nom affiché -> {alias possibles}
for e in REG + DEP:
    q = poules.get(e) or {}
    alias_site = [t.get('name') for t in ((DATA.get(e) or {}).get('teams') or []) if t.get('name')]
    for t in (q.get('teams') or []):
        n = t.get('name') or ''
        if not n or 'BOULOGNE BILLAN' in n.upper(): continue
        al = {n}
        if t.get('fftt'): al.add(t['fftt'])
        # Le libellé explicite est prioritaire ; seul un rapprochement unique
        # de tous les mots distinctifs ET du numéro peut ajouter un alias.
        hit = unique_alias(n, alias_site)
        if hit: al.add(hit)
        cible.setdefault(n, set()).update(al)
print("adversaires à résoudre : %d" % len(cible))

GEN = {'TT','AS','US','CS','ES','AC','CSM','USM','SC','ATT','UMS','SMTT','VGA','ESP','STT','CTT','SM','TTM','TTMC','EP','ASTT','PPC','CTTA','MJC','ASC'}

# Correspondances forcées : numéro de club donné à la main quand le rapprochement
# automatique échoue. Numéros fournis par Charles le 29/09/2026 après lecture du
# diagnostic (scripts/probes/probe_salles3.py). Les noms FFTT de ces clubs ne partagent
# aucun mot distinctif avec le libellé de nos poules, aucune heuristique ne les
# trouverait — d'où la saisie manuelle, qui reste la seule voie sûre.
FORCE = {
    'ATT XV 1':                   '08751260',   # Assoc. Tennis de Table Paris XVe
    'PING PARIS 14 1':            '08751456',
    'STAINS ES-PIERREFITTE AS 1': '08931032',
    'SAINT MAUR VGA US 2':        '08940976',
    'LAGNY SMTT 1':               '08770166',   # club identifié, mais aucune salle déclarée à la FFTT
}
cache = {}
def equipes(num):
    if num not in cache:
        r = fb.get("xml_equipe.php?numclu=%s&type=A" % num); time.sleep(0.08)
        cache[num] = {norme(l.split(' - ')[0]) for l in re.findall(r'<libequipe>(.*?)</libequipe>', r, re.S)}
    return cache[num]

fiches, out, rate = {}, {}, []
for nom, alias in sorted(cible.items()):
    cles = {norme(a) for a in alias}
    distinct = {m for a in alias for m in mots(a) if len(m) >= 3 and m not in GEN and not m.isdigit()}
    if nom in FORCE:
        c = {'num': FORCE[nom], 'nom': '(forcé)'}
    else:
        cands = [c2 for c2 in clubs if distinct & set(mots(c2['nom']))]
        trouve = [c2 for c2 in cands[:25] if cles & equipes(c2['num'])]
        if len(trouve) != 1:
            rate.append((nom, len(cands), len(trouve))); continue
        c = trouve[0]
    if c['num'] not in fiches:
        r = fb.get("xml_club_detail.php?club=%s" % c['num']); time.sleep(0.08)
        b = re.findall(r'<club>(.*?)</club>', r, re.S)
        fiches[c['num']] = tags(b[0]) if b else {}
    d = fiches[c['num']]
    adr = ' '.join(x for x in [d.get('adressesalle1'), d.get('adressesalle2'), d.get('adressesalle3')] if x and x.strip())
    if not (d.get('nomsalle') or adr):
        rate.append((nom, 0, -1)); continue
    out[nom] = {'salle': d.get('nomsalle') or '', 'adresse': adr.strip(),
                'cp': d.get('codepsalle') or '', 'ville': d.get('villesalle') or '',
                'lat': d.get('latitude') or '', 'lon': d.get('longitude') or '',
                'club': d.get('nom') or c['nom'], 'num': c['num'],
                'team_id': c['num']+':'+(mots(nom) or [''])[-1],
                'source': 'fftt_club', 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}

res = {'maj': datetime.date.today().isoformat(),
       'source': "API FFTT xml_club_b + xml_equipe + xml_club_detail — salle DÉCLARÉE du club, "
                 "pas le lieu confirmé de la rencontre ; départemental et régional uniquement",
       'salles': out}
os.makedirs('data', exist_ok=True)
json.dump(res, open('data/salles_adverses.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
print("=" * 60)
print("data/salles_adverses.json : %d equipes sur %d (%d %%)" % (len(out), len(cible), round(100*len(out)/max(1,len(cible)))))
print("NON RESOLUS (%d) :" % len(rate))
for n, nc, nt in rate: print("   %-30s candidats=%d exacts=%s" % (n, nc, 'fiche vide' if nt == -1 else nt))
