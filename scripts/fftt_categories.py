#!/usr/bin/env python3
"""Récupère la catégorie d'âge FFTT de chaque licencié (xml_licence_b, champ <cat>)
et écrit data/categories.json : { "licence": "M1|M2|C1|C2|J1..J4|B1|B2|P|S" }.
Tout ce qui est au-dessus de junior (seniors, vétérans) est normalisé en "S".
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
OVERRIDES = {'9254353': 'S'}   # Grégoire STEMLER

idx = json.load(open('data/players_index.json'))
out = {}
for i, p in enumerate(idx):
    lic = str(p.get('lic') or '')
    if not lic.isdigit(): continue
    xml = fb.get(f"xml_licence_b.php?licence={lic}")
    cat = norm(fb.tag(xml, 'cat'))
    if cat: out[lic] = cat
    if (i+1) % 40 == 0: print(f"  {i+1}/{len(idx)}")
    time.sleep(0.12)

out.update(OVERRIDES)
json.dump(out, open('data/categories.json', 'w'), ensure_ascii=False)
from collections import Counter
print(f"data/categories.json : {len(out)} joueurs — répartition {dict(Counter(out.values()))}")
