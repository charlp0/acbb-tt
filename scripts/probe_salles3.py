# -*- coding: utf-8 -*-
"""Diagnostic : pourquoi ces équipes ne se rapprochent-elles pas ?
Pour chaque nom non résolu, on montre CE QU'ON A (libellé PDF CD92 + libellé FFTT
de site.json) et CE QUE LA FFTT PROPOSE (clubs candidats + leurs libellés d'équipe).
Charles tranche à la lecture ; rien n'est écrit."""
import json, re, time, unicodedata, importlib.util

spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

DEPS = ['75', '77', '78', '91', '92', '93', '94', '95']
MANQUE = ['AS FONTENAY TT 1','AS FONTENAY TT 3','ATT XV 1','COLOMBIENNE ES 4',
          'ISSEENNE E P 4','ISSEENNE E P 6','ISSEENNE E P 7','LAGNY SMTT 1',
          'PING PARIS 14 1','SAINT MAUR VGA US 2','STAINS ES-PIERREFITTE AS 1','VITRY ES 1']
# celles qui bloquent réellement une adresse de déplacement
BLOQUANTES = {'ATT XV 1','SAINT MAUR VGA US 2','LAGNY SMTT 1','STAINS ES-PIERREFITTE AS 1','PING PARIS 14 1'}

def mots(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii','ignore').decode().upper()
    return [m for m in re.split(r'[^A-Z0-9]+', s) if m]
def tags(b): return dict(re.findall(r'<([a-zA-Z0-9_]+)>(.*?)</\1>', b, re.S))

clubs = []
for d in DEPS:
    r = fb.get("xml_club_b.php?dep=%s" % d); time.sleep(0.08)
    for b in re.findall(r'<club>(.*?)</club>', r, re.S):
        t = tags(b)
        if t.get('numero'): clubs.append({'num': t['numero'], 'nom': t.get('nom') or '', 'dep': d})

site = json.load(open('data/site.json')); DATA = site.get('DATA') or {}
nomsFFTT = {}
for k, v in DATA.items():
    for t in (v.get('teams') or []):
        if t.get('name'): nomsFFTT.setdefault(k, []).append(t['name'])

cache = {}
def equipes(num):
    if num not in cache:
        r = fb.get("xml_equipe.php?numclu=%s&type=A" % num); time.sleep(0.06)
        cache[num] = sorted({l.split(' - ')[0].strip() for l in re.findall(r'<libequipe>(.*?)</libequipe>', r, re.S)})
    return cache[num]

for nom in MANQUE:
    num = (mots(nom) or [''])[-1]
    print("=" * 72)
    print("NOTRE LIBELLE : %s%s" % (nom, "   <<< BLOQUE UNE ADRESSE" if nom in BLOQUANTES else ""))
    # ce que site.json (FFTT) porte pour la meme poule
    proches = sorted({n for ns in nomsFFTT.values() for n in ns
                      if (mots(n) or [''])[-1] == num and set(mots(n)) & (set(mots(nom)) - {num})})
    print("  vu dans site.json :", ', '.join(proches) if proches else '—')
    # clubs candidats : n'importe quel mot en commun, meme generique
    cands = [c for c in clubs if set(m for m in mots(nom) if len(m) >= 3) & set(mots(c['nom']))]
    if not cands: print("  aucun club candidat en IdF (le nom du club differe totalement)")
    for c in cands[:6]:
        eq = [e for e in equipes(c['num']) if (mots(e) or [''])[-1] == num]
        print("  club %s (%s, dep %s) -> equipes n°%s : %s" % (c['nom'], c['num'], c['dep'], num, ', '.join(eq) or '—'))
