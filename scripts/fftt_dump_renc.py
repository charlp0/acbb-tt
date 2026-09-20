#!/usr/bin/env python3
"""Outil de diagnostic : affiche la STRUCTURE BRUTE d'une feuille de rencontre FFTT
(xml_chp_renc) pour comprendre comment la fédération encode le classement des joueurs
— points, ou numéro national pour les joueurs numérotés.

Usage (dans GitHub Actions, où FFTT_ID / FFTT_PWD existent) :
  python3 scripts/fftt_dump_renc.py [POULE]     # POULE = clé ACBB, ex. M2 (défaut) ou M3
"""
import os, re, sys, html, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def tg(s, t):
    m = re.search('<' + t + '>(.*?)</' + t + '>', s, re.S)
    return m.group(1).strip() if m else ''

cible = (sys.argv[1] if len(sys.argv) > 1 else 'M2').upper()
spec2 = importlib.util.spec_from_file_location("fs", "scripts/fftt_site.py")

# on relit META depuis fftt_site.py sans l'exécuter (il génère tout le site)
src = open('scripts/fftt_site.py', encoding='utf-8').read()
meta = dict(re.findall(r"'([MF]\d+)':\(\"(.*?)\"", src))
print(f"poule cible : {cible} → {meta.get(cible,'?')}")

eq = fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
lien = None
for b in re.findall(r'<equipe>(.*?)</equipe>', eq, re.S):
    lib = tg(b, 'libequipe'); ldiv = tg(b, 'libdivision')
    # filtre strict : bonne division ET bon genre (sinon « Nationale 2 » attrape aussi les dames)
    want = meta.get(cible, '')
    if want and want.split(' Poule')[0].split('_')[-1].strip() not in ldiv: continue
    if cible.startswith('M') and 'Dames' in ldiv: continue
    if cible.startswith('F') and 'Dames' not in ldiv: continue
    print('  équipe retenue :', lib, '|', ldiv)
    lienD = tg(b, 'liendivision')
    if not lienD: continue
    cal = fb.get("xml_result_equ.php?" + html.unescape(lienD))
    for t in re.findall(r'<tour>(.*?)</tour>', cal, re.S):
        if not (tg(t, 'scorea') or '').isdigit(): continue
        m = re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', t)
        if m: lien = html.unescape(m.group(1)); break
    if lien: break

if not lien:
    sys.exit("aucune rencontre jouée trouvée pour cette poule")

r = fb.get("xml_chp_renc.php?" + lien)
print("\n=== balises présentes dans <joueur> ===")
blocs = re.findall(r'<joueur>(.*?)</joueur>', r, re.S)
print("nb blocs joueur :", len(blocs))
if blocs:
    print("balises :", sorted(set(re.findall(r'<(\w+)>', blocs[0]))))
print("\n=== 4 premiers blocs, bruts ===")
for b in blocs[:4]:
    print("  " + re.sub(r'\s+', ' ', b.strip())[:300])
print("\n=== autres balises de premier niveau dans la réponse ===")
haut = re.sub(r'<joueur>.*?</joueur>', '', r, flags=re.S)
print(sorted(set(re.findall(r'<(\w+)>', haut)))[:40])
