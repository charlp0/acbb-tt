# -*- coding: utf-8 -*-
"""Sonde 2 : peut-on retrouver, de façon SÛRE, la salle de chaque adversaire
départemental et régional ?

Méthode voulue : ne jamais rapprocher sur le nom du club (ambigu), mais sur le
nom EXACT de l'équipe. On liste les clubs d'Île-de-France (xml_club_b par
département), puis les équipes de chaque club candidat (xml_equipe), et on ne
retient un club que si l'un de ses libellés d'équipe correspond exactement au
nom que porte notre poule. La fiche club (xml_club_detail) donne alors la salle.

Le script n'écrit rien : il mesure le taux de résolution et imprime les échecs.
"""
import json, re, time, unicodedata, importlib.util, collections

spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

DEPS = ['75', '77', '78', '91', '92', '93', '94', '95']
REG  = ['M3', 'M4', 'M5', 'F2']                      # régional
DEP  = ['M6','M7','M8','M9','M10','M11','M12','M13','M14','M15','M16','M17','F3']   # départemental

def nrm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', ' ', s).split()

def tags(b):
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>(.*?)</\1>', b, re.S))

# 1. tous les clubs d'IdF
clubs = []
for d in DEPS:
    r = fb.get("xml_club_b.php?dep=%s" % d); time.sleep(0.1)
    n = 0
    for b in re.findall(r'<club>(.*?)</club>', r, re.S):
        t = tags(b); clubs.append({'num': t.get('numero'), 'nom': t.get('nom'), 'dep': d}); n += 1
    print("  dep %s : %d clubs" % (d, n))
print("TOTAL clubs IdF : %d" % len(clubs))

# 2. les adversaires à résoudre
P = {q['acbb']: q for q in json.load(open('data/poules2627.json'))['poules']}
cible = {}
for e in REG + DEP:
    q = P.get(e) or {}
    for t in (q.get('teams') or []):
        n = t.get('name') or ''
        if 'BOULOGNE BILLAN' in n.upper(): continue
        cible.setdefault(n, 'régional' if e in REG else 'départemental')
print("adversaires distincts à résoudre : %d" % len(cible))

# 3. candidats par recouvrement de mots, puis confirmation sur le nom EXACT de l'équipe
cache = {}
def equipes(num):
    if num in cache: return cache[num]
    r = fb.get("xml_equipe.php?numclu=%s&type=A" % num); time.sleep(0.08)
    libs = set()
    for lib in re.findall(r'<libequipe>(.*?)</libequipe>', r, re.S):
        libs.add(lib.split(' - ')[0].strip().upper())
    cache[num] = libs
    return libs

ok, rate = {}, []
for nom, niveau in sorted(cible.items()):
    mots = set(nrm(nom)) - {'TT', 'AS', 'US', 'CS', 'ES', 'AC', 'CSM', 'USM', 'SC', 'ATT', 'UMS', 'SMTT', 'VGA', 'ESP', 'STT', 'CTT'}
    mots = {m for m in mots if len(m) >= 3 and not m.isdigit()}
    cands = [c for c in clubs if mots & set(nrm(c['nom']))]
    trouve = [c for c in cands[:12] if nom.upper() in equipes(c['num'])]
    if len(trouve) == 1: ok[nom] = (trouve[0], niveau)
    else: rate.append((nom, niveau, len(cands), len(trouve)))

print("=" * 70)
tot = collections.Counter(v for v in cible.values())
res = collections.Counter(v[1] for v in ok.values())
for niv in ['départemental', 'régional']:
    print("%-14s : %d resolus sur %d" % (niv, res[niv], tot[niv]))
print("=" * 70)
print("NON RESOLUS (%d) : nom | niveau | clubs candidats | correspondances exactes" % len(rate))
for n, niv, nc, nt in rate: print("   %-28s %-14s %d %d" % (n, niv, nc, nt))
print("=" * 70)
print("EXEMPLES DE SALLES TROUVEES")
for nom, (c, niv) in list(ok.items())[:6]:
    r = fb.get("xml_club_detail.php?club=%s" % c['num']); time.sleep(0.08)
    d = tags(re.findall(r'<club>(.*?)</club>', r, re.S)[0]) if '<club>' in r else {}
    print("   %-26s -> %s, %s %s %s" % (nom, d.get('nomsalle', '?'), d.get('adressesalle1', '?'),
                                        d.get('codepsalle', ''), d.get('villesalle', '')))
