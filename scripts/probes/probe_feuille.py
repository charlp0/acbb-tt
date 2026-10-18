#!/usr/bin/env python3
"""Sonde : la feuille de rencontre FFTT complète d'une de nos équipes pour une journée (noms, classements,
sets de chaque partie), pour écrire un debrief. Usage : EQUIPE=M11 JOURNEE=3 python3 scripts/probes/probe_feuille.py
Aucun numéro de licence n'est imprimé (journal d'Actions public)."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import re, html, json
import fftt_site as fs
fb = fs.fb
eq, jn = os.environ.get('EQUIPE', 'M11'), int(os.environ.get('JOURNEE', '3'))
# coordonnées de la poule : même résolution que fftt_site (division + n° de poule)
P = {p['acbb']: p for p in json.load(open('data/poules2627.json'))['poules']}
pool = P[eq]
r = fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
cx = None
for b in re.findall(r'<equipe>(.*?)</equipe>', r, re.S):
    libdiv = fs.tg(b, 'libdivision'); lib = fs.tg(b, 'libequipe')
    pm = re.search(r'[Pp]oule\s*(\d+)', libdiv)
    if not pm or int(pm.group(1)) != int(pool['poule']): continue
    if not any(tok in libdiv.replace('_', ' ') for tok in (pool['division'].split(' ')[0],)): continue
    acbb = next((t['name'] for t in pool['teams'] if t.get('acbb')), '')
    if fb.nrm(re.sub(r' - Phase \d+$', '', lib)) != fb.nrm(acbb): continue
    m = re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>', b)
    cx = dict(x.split('=') for x in html.unescape(m.group(1)).split('&')); break
if not cx: sys.exit(f"poule de {eq} introuvable")
cal = fb.get(f"xml_result_equ.php?cx_poule={cx['cx_poule']}&D1={cx['D1']}&organisme_pere={cx['organisme_pere']}")
for t in re.findall(r'<tour>(.*?)</tour>', cal, re.S):
    ea, eb = fs.tg(t, 'equa'), fs.tg(t, 'equb')
    n = re.search(r'tour\s*n°?\s*(\d+)', fs.tg(t, 'libelle'))
    if not n or int(n.group(1)) != jn or not (fs.is_acbb(ea) or fs.is_acbb(eb)): continue
    print(f"J{jn} · {ea} {fs.tg(t,'scorea')} – {fs.tg(t,'scoreb')} {eb} · {fs.tg(t,'datereelle') or fs.tg(t,'dateprevue')}")
    lm = re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', t)
    if not lm: print("  pas de feuille"); break
    f = fb.get("xml_chp_renc.php?" + html.unescape(lm.group(1)))
    print("  joueurs :")
    for jb in re.findall(r'<joueur>(.*?)</joueur>', f, re.S):
        print("   ", fs.tg(jb, 'xja'), '(', fs.tg(jb, 'xca'), ')  vs  ', fs.tg(jb, 'xjb'), '(', fs.tg(jb, 'xcb'), ')')
    print("  parties (ordre de la feuille) :")
    for i, p in enumerate(re.findall(r'<partie>(.*?)</partie>', f, re.S), 1):
        print(f"    {i:2d}. {fs.tg(p,'ja')} {fs.tg(p,'scorea')} – {fs.tg(p,'scoreb')} {fs.tg(p,'jb')} · sets {fs.tg(p,'detail')}")
    break
