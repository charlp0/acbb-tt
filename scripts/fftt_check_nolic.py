#!/usr/bin/env python3
"""Vérifie sur la FFTT si les joueurs saisis 'sans licence' (MUT_HARD) ont désormais une licence / un classement.
Cherche par nom dans la liste des licenciés du club (xml_liste_joueur_o) puis lit xml_licence_b. Identifiants via env FFTT_ID/FFTT_PWD."""
import re, json, importlib.util, unicodedata
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py"); fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def tg(s, t):
    m = re.search('<' + t + '>(.*?)</' + t + '>', s, re.S); return m.group(1).strip() if m else ''
def nk(s): return re.sub(r'[^A-Z]', '', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper())
sc = json.load(open('data/scoring.json'))['players']
targets = [(p['nom'], p['pre']) for p in sc if not p.get('lic')]
print("Joueurs sans licence dans scoring.json :", targets)
lst = fb.get(f"xml_liste_joueur_o.php?club={fb.CLUB}")
found = {}
for blk in re.findall(r'<joueur>(.*?)</joueur>', lst, re.S):
    nom, pre, lic, pts = tg(blk, 'nom'), tg(blk, 'prenom'), tg(blk, 'licence'), tg(blk, 'points')
    for tn, tp in targets:
        if nk(nom) == nk(tn) and nk(pre)[:3] == nk(tp)[:3]:
            found[(tn, tp)] = (lic, pts, nom, pre)
for t in targets:
    if t in found:
        lic, pts, nom, pre = found[t]
        lb = fb.get(f"xml_licence_b.php?licence={lic}")
        print(f"✅ {pre} {nom} : licence {lic} · points liste {pts} · officiel(point) {tg(lb,'point')} · mensuel(pointm) {tg(lb,'pointm')} · cat {tg(lb,'cat')} · mutation {tg(lb,'mutation') or '-'} · validée {tg(lb,'validation') or '-'}")
    else:
        print(f"❌ {t[1]} {t[0]} : toujours introuvable dans la liste des licenciés du club")
print(f"(liste club : {len(re.findall(r'<joueur>', lst))} licenciés)")
