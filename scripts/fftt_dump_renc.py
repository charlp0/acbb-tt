#!/usr/bin/env python3
"""Diagnostic FFTT : inventorie les formats du champ « classement » (xca/xcb) des feuilles
de rencontre (xml_chp_renc), sur TOUTES les poules où l'ACBB a une équipe.

But : voir comment la fédération encode les joueurs NUMÉROTÉS (n° national) par rapport aux
joueurs classés aux points, afin de ne plus afficher « 523 pts » pour un N523.
Lecture seule : aucune écriture, aucun commit.
"""
import re, html, collections, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def tg(s, t):
    m = re.search('<' + t + '>(.*?)</' + t + '>', s, re.S)
    return m.group(1).strip() if m else ''

STD = re.compile(r'^[MF]\s+\d+\s*pts$', re.I)          # format courant : « M 1537pts »
vals = collections.Counter(); hors = collections.Counter(); exemples = {}
eq = fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
vus = set()
for b in re.findall(r'<equipe>(.*?)</equipe>', eq, re.S):
    ldiv = tg(b, 'libdivision'); lienD = tg(b, 'liendivision')
    if not lienD or ldiv in vus: continue
    vus.add(ldiv)
    cal = fb.get("xml_result_equ.php?" + html.unescape(lienD))
    n = 0
    for t in re.findall(r'<tour>(.*?)</tour>', cal, re.S):
        if not (tg(t, 'scorea') or '').isdigit(): continue
        m = re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', t)
        if not m: continue
        r = fb.get("xml_chp_renc.php?" + html.unescape(m.group(1)))
        for bloc in re.findall(r'<joueur>(.*?)</joueur>', r, re.S):
            for tag in ('xca', 'xcb'):
                v = tg(bloc, tag)
                if not v: continue
                vals[v] += 1
                if not STD.match(v):
                    hors[v] += 1
                    exemples.setdefault(v, (ldiv, tg(bloc, 'xja' if tag == 'xca' else 'xjb')))
        n += 1
        if n >= 2: break        # 2 rencontres par division suffisent
print(f"divisions balayées : {len(vus)} · valeurs de classement lues : {sum(vals.values())}")
print(f"\n=== valeurs NE SUIVANT PAS le format « M 1537pts » : {len(hors)} formes distinctes ===")
for v, c in hors.most_common(40):
    d, j = exemples[v]
    print(f"  {v!r:28} ×{c:<4} ex. {j} — {d}")
if not hors:
    print("  (aucune : toutes les valeurs suivent le format standard)")
print("\n=== 8 valeurs standard, pour référence ===")
for v, c in list(vals.most_common())[:8]:
    print(f"  {v!r} ×{c}")
