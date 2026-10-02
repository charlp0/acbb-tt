# -*- coding: utf-8 -*-
"""Verification ciblee : la licence d'Anthony LE GALL (7520188) est-elle validee ?
La sonde precedente ne renvoyait ni type ni date de validation pour lui, alors que
les 21 autres joueurs concernes sont en type T avec une date. Avant d'annoncer a
Charles qu'un joueur ne peut pas jouer ce soir, on verifie sur la reponse brute."""
import re, time, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
for lic, qui in [('7520188','LE GALL Anthony'), ('9243175','CINOTTI Pierre (temoin : fiche normale)')]:
    r = fb.get("xml_licence_b.php?licence=%s" % lic); time.sleep(0.2)
    print("=" * 72); print("%s — %s" % (lic, qui))
    print("reponse brute :"); print(re.sub(r'>\s*<', '>\n<', (r or '').strip())[:1200])
# l'autre endpoint, pour recouper
print("=" * 72)
print("recoupement xml_liste_joueur_o (liste des licencies du club) :")
r = fb.get("xml_liste_joueur_o.php?club=%s" % fb.CLUB)
for b in re.findall(r'<joueur>(.*?)</joueur>', r, re.S):
    d = dict(re.findall(r'<([a-zA-Z0-9_]+)>([^<]*)</\1>', b))
    if d.get('licence') in ('7520188',):
        print("   ", " | ".join("%s=%s" % kv for kv in sorted(d.items())))
