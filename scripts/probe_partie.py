# -*- coding: utf-8 -*-
"""Sonde 2 : correspondance codechamp -> catégorie de compétition.
Croise les parties mysql (codechamp) avec les catégories déjà connues des fiches."""
import json, re, unicodedata, importlib.util, collections
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def nrm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z]', '', s)
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
# échantillon varié : Virginie (vétérans+challenge+équipes M/F), Rostin (jeune),
# Perrot (critérium+paris), Lescaudron (tout), Savan (gros volume)
LICS = ['9260920', '9261240', '7824630', '7523006', '9256836']
mat = collections.Counter(); ex = {}
for lic in LICS:
    try: prof = json.load(open(f'data/players/{lic}.json'))
    except Exception: continue
    cat = {}
    for c in prof.get('competitions', []):
        for m in c['matches']:
            cat[(m['date'], nrm(m['opp']))] = c['key']
    r = fb.get(f"xml_partie_mysql.php?licence={lic}")
    for b in re.findall(r'<partie>(.*?)</partie>', r, re.S):
        code = tg(b, 'codechamp'); date = tg(b, 'date'); adv = tg(b, 'advnompre')
        k = cat.get((date, nrm(adv)), '?')
        mat[(code, k)] += 1
        if (code, k) not in ex: ex[(code, k)] = f"{date} vs {adv}"
print("code | catégorie fiche | n | exemple")
for (code, k), n in sorted(mat.items()):
    print(f"  {code:>4} | {k:<10} | {n:>3} | {ex[(code,k)]}")
