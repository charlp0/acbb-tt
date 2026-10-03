# -*- coding: utf-8 -*-
"""Sonde : l'API FFTT donne-t-elle de quoi afficher V/D, perfs et contres ?

Charles veut, pour chaque joueur d'une poule du critérium, son bilan depuis le début
de saison avec la distinction de l'appli FFTT : victoires « normales », performances,
défaites « normales », contres. Avant de promettre quoi que ce soit, on regarde ce
qu'une partie porte vraiment : y a-t-il le classement de l'adversaire au moment du
match, et le gain de points ? Sans eux, perf et contre ne se déduisent pas sans
inventer une règle.
"""
import re, time, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

LICS = [('7824630', 'Charles PERROT'), ('9238431', 'Louis REUSEAU')]
for lic, qui in LICS:
    print("=" * 84); print("%s — %s" % (lic, qui))
    for ep in ("xml_partie_mysql.php?licence=%s" % lic, "xml_partie.php?numlic=%s" % lic):
        r = fb.get(ep); time.sleep(0.2)
        blocs = re.findall(r'<partie>(.*?)</partie>', r, re.S)
        print("  %-42s %5d caracteres · %3d parties" % (ep.split('?')[0], len(r or ''), len(blocs)))
        if blocs:
            champs = re.findall(r'<([a-zA-Z0-9_]+)>', blocs[0])
            print("     champs :", champs)
            for b in blocs[:3]:
                d = dict(re.findall(r'<([a-zA-Z0-9_]+)>([^<]*)</\1>', b))
                print("     ", " | ".join("%s=%s" % kv for kv in d.items())[:190])
