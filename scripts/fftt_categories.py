#!/usr/bin/env python3
"""Récupère, pour chaque licencié, la catégorie d'âge FFTT (xml_licence_b, champ <cat>)
et le sexe (champ <sexe>), et écrit deux fichiers :
  - data/categories.json : { "licence": "M1|M2|C1|C2|J1..J4|B1|B2|P|S" } — au-dessus de junior = "S"
  - data/sexes.json      : { "licence": "M"|"F" }
Le sexe sert à la règle « 2 joueuses au maximum en régional messieurs » (M3, M4, M5) vérifiée
dans sportive/journee.html. Le fichier livré le 26/09/2026 a été généré depuis l'export licences
du club (colonne « Sexe », 573 joueurs) faute d'accès aux identifiants FFTT en local ; ce script
le régénère depuis l'API et doit rester la source. Il ne perd jamais une entrée existante : les
licences que l'API ne renseigne pas gardent leur valeur connue.
Identifiants via env FFTT_ID / FFTT_PWD (jamais en dur)."""
import json, re, time, importlib.util

spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

JEUNE = re.compile(r'^(B[12]|M[12]|C[12]|J[1-4]|P[0-9]?)$')

def norm(cat):
    c = (cat or '').strip().upper()
    if not c: return None
    return c if JEUNE.match(c) else 'S'

# corrections manuelles (cat absente ou fausse côté FFTT)
OVERRIDES = {'9254353': 'S',            # Grégoire STEMLER (cat absente côté FFTT)
             'ARGUT|DANIEL': 'S',        # mutés sans licence : clé NOM|PRENOM normalisée
             'BOTELLA|MILO': 'S', '9411975': 'S'}

# on repart des fichiers existants : une licence que l'API ne renseigne pas garde sa valeur connue
def charge(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return {}

idx = json.load(open('data/players_index.json'))
# aussi les licenciés présents uniquement dans scoring.json (mutations avec licence)
sc = json.load(open('data/scoring.json'))['players']
lics = {str(p.get('lic') or '') for p in idx} | {str(p.get('lic') or '') for p in sc}
lics = sorted(l for l in lics if l.isdigit())
out = charge('data/categories.json')
sexes = charge('data/sexes.json')
vus = 0
for i, lic in enumerate(lics):
    if not lic.isdigit(): continue
    xml = fb.get(f"xml_licence_b.php?licence={lic}")
    cat = norm(fb.tag(xml, 'cat'))
    if cat: out[lic] = cat
    sx = (fb.tag(xml, 'sexe') or '').strip().upper()[:1]
    if sx in ('M', 'F'): sexes[lic] = sx; vus += 1
    if (i+1) % 40 == 0: print(f"  {i+1}/{len(lics)}")
    time.sleep(0.12)

out.update(OVERRIDES)
json.dump(out, open('data/categories.json', 'w'), ensure_ascii=False)
json.dump(sexes, open('data/sexes.json', 'w'), ensure_ascii=False, sort_keys=True)
from collections import Counter
print(f"data/categories.json : {len(out)} joueurs — répartition {dict(Counter(out.values()))}")
print(f"data/sexes.json      : {len(sexes)} joueurs — {dict(Counter(sexes.values()))} ({vus} renseignés par l'API)")
if not vus:
    print("  ⚠️  aucun <sexe> lu : vérifier le nom du champ dans xml_licence_b avant de se fier au fichier")
